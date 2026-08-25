"""
Rubin TAP service query module for accessing data outside RSP.
Uses pyvo for TAP queries with token authentication.
"""

import numpy as np
import warnings

try:
    import pyvo
    from pyvo.auth import CredentialStore
    HAS_PYVO = True
except ImportError:
    HAS_PYVO = False
    warnings.warn("pyvo not installed. Install with: pip install pyvo")

try:
    from astropy.io import fits
    from astropy.wcs import WCS
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    HAS_ASTROPY = True
except ImportError:
    HAS_ASTROPY = False
    warnings.warn("astropy not installed. Install with: pip install astropy")


class RubinDataQuery:
    """
    Query Rubin data using TAP service with token authentication.
    
    This allows access to Rubin data from outside the RSP using
    a personal access token.
    """
    
    # Rubin TAP service URL
    TAP_URL = "https://data.lsst.cloud/api/tap"
    
    def __init__(self, token=None):
        """
        Initialize the TAP service connection.
        
        Parameters:
        -----------
        token : str
            Rubin Science Platform access token.
            Get yours from: https://data.lsst.cloud/auth/tokens
        """
        self.token = token
        self.tap_service = None
        self.credential_store = None
        
        if not HAS_PYVO:
            raise ImportError("pyvo is required. Install with: pip install pyvo")
        
        if token is not None:
            self._initialize_tap_service()
    
    def _initialize_tap_service(self):
        """Initialize the TAP service with authentication."""
        try:
            # Set up credential store with token
            self.credential_store = CredentialStore()
            self.credential_store.set_password("ivo://ivoa.net/sso#BasicAA", self.token)
            
            # Create TAP service with credentials
            self.tap_service = pyvo.dal.TAPService(
                self.TAP_URL,
                credential=self.credential_store.get("ivo://ivoa.net/sso#BasicAA")
            )
            print("Successfully connected to Rubin TAP service")
            
        except Exception as e:
            print(f"Failed to initialize TAP service: {e}")
            # Try alternative authentication method
            try:
                self.tap_service = pyvo.dal.TAPService(self.TAP_URL)
                # Set auth header directly
                self.tap_service._session.headers['Authorization'] = f'Bearer {self.token}'
                print("Connected using Bearer token authentication")
            except Exception as e2:
                print(f"Alternative auth also failed: {e2}")
                self.tap_service = None
    
    def query_objects(self, ra, dec, radius_arcmin=5.0, table='dp02_dc2_catalogs.Object'):
        """
        Query objects within a radius of given coordinates.
        
        Parameters:
        -----------
        ra : float
            Right ascension in degrees
        dec : float
            Declination in degrees
        radius_arcmin : float
            Search radius in arcminutes
        table : str
            Catalog table to query
        
        Returns:
        --------
        results : astropy.table.Table
            Query results
        """
        if self.tap_service is None:
            raise RuntimeError("TAP service not initialized. Check your token.")
        
        query = f"""
        SELECT objectId, coord_ra, coord_dec, 
               g_cModelFlux, r_cModelFlux, i_cModelFlux,
               g_psfFlux, r_psfFlux, i_psfFlux,
               refExtendedness
        FROM {table}
        WHERE CONTAINS(POINT('ICRS', coord_ra, coord_dec),
                       CIRCLE('ICRS', {ra}, {dec}, {radius_arcmin/60.0})) = 1
        """
        
        print(f"Querying objects at RA={ra:.4f}, Dec={dec:.4f}, radius={radius_arcmin}'...")
        results = self.tap_service.search(query)
        print(f"Found {len(results)} objects")
        
        return results.to_table()
    
    def get_image_cutout(self, ra, dec, size_arcsec=60, band='i'):
        """
        Get an image cutout from the Rubin image service.
        
        Parameters:
        -----------
        ra : float
            Center RA in degrees
        dec : float
            Center Dec in degrees
        size_arcsec : float
            Cutout size in arcseconds
        band : str
            Filter band (u, g, r, i, z, y)
        
        Returns:
        --------
        image_data : ndarray
            Image array
        wcs : WCS
            World Coordinate System
        header : dict
            FITS header information
        """
        if self.tap_service is None:
            raise RuntimeError("TAP service not initialized. Check your token.")
        
        # Query for available images at this location
        size_deg = size_arcsec / 3600.0
        
        query = f"""
        SELECT access_url, s_ra, s_dec, t_exptime, em_min, em_max,
               lsst_band, lsst_tract, lsst_patch
        FROM ivoa.ObsCore
        WHERE CONTAINS(POINT('ICRS', s_ra, s_dec),
                       CIRCLE('ICRS', {ra}, {dec}, {size_deg})) = 1
        AND lsst_band = '{band}'
        AND dataproduct_type = 'image'
        LIMIT 10
        """
        
        print(f"Searching for {band}-band images at RA={ra:.4f}, Dec={dec:.4f}...")
        
        try:
            results = self.tap_service.search(query)
            
            if len(results) == 0:
                print("No images found at this location")
                return None, None, None
            
            # Get the first available image
            access_url = results[0]['access_url']
            print(f"Found image, downloading from: {access_url[:50]}...")
            
            # Download the image
            image_data, wcs, header = self._download_image(access_url, ra, dec, size_arcsec)
            
            return image_data, wcs, header
            
        except Exception as e:
            print(f"Error querying images: {e}")
            return None, None, None
    
    def _download_image(self, url, ra, dec, size_arcsec):
        """Download image from URL with cutout parameters."""
        import requests
        from io import BytesIO
        
        # Add cutout parameters to URL
        cutout_url = f"{url}?POS={ra},{dec}&SIZE={size_arcsec/3600.0}"
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        response = requests.get(cutout_url, headers=headers)
        
        if response.status_code != 200:
            raise RuntimeError(f"Failed to download image: {response.status_code}")
        
        # Parse FITS data
        with fits.open(BytesIO(response.content)) as hdul:
            image_data = hdul[0].data.copy()
            header = dict(hdul[0].header)
            wcs = WCS(hdul[0].header)
        
        return image_data, wcs, header
    
    def get_coadd_info(self, tract, patch, band='i'):
        """
        Get information about a specific coadd.
        
        Parameters:
        -----------
        tract : int
            Tract number
        patch : int or str
            Patch number/identifier
        band : str
            Filter band
        
        Returns:
        --------
        info : dict
            Coadd information
        """
        if self.tap_service is None:
            raise RuntimeError("TAP service not initialized.")
        
        query = f"""
        SELECT access_url, s_ra, s_dec, s_region,
               lsst_tract, lsst_patch, lsst_band,
               t_exptime, s_resolution
        FROM ivoa.ObsCore
        WHERE lsst_tract = {tract}
        AND lsst_patch = '{patch}'
        AND lsst_band = '{band}'
        AND dataproduct_type = 'image'
        """
        
        results = self.tap_service.search(query)
        
        if len(results) == 0:
            return None
        
        return dict(results[0])
    
    def get_psf_info(self, ra, dec, band='i'):
        """
        Get PSF information at a specific location.
        
        Note: This queries catalog data to estimate PSF properties.
        For actual PSF images, you need Butler access on RSP.
        
        Parameters:
        -----------
        ra : float
            RA in degrees
        dec : float
            Dec in degrees
        band : str
            Filter band
        
        Returns:
        --------
        psf_info : dict
            PSF information including estimated FWHM
        """
        if self.tap_service is None:
            raise RuntimeError("TAP service not initialized.")
        
        # Query point sources to estimate PSF from their measured sizes
        query = f"""
        SELECT objectId, coord_ra, coord_dec,
               {band}_psfFlux, {band}_psfFluxErr,
               {band}_ixxPSF, {band}_iyyPSF, {band}_ixyPSF
        FROM dp02_dc2_catalogs.Object
        WHERE CONTAINS(POINT('ICRS', coord_ra, coord_dec),
                       CIRCLE('ICRS', {ra}, {dec}, 0.05)) = 1
        AND refExtendedness < 0.5
        AND {band}_psfFlux > 1000
        LIMIT 100
        """
        
        try:
            results = self.tap_service.search(query)
            
            if len(results) == 0:
                return {'fwhm_pixels': 3.5, 'fwhm_arcsec': 0.7, 'source': 'default'}
            
            table = results.to_table()
            
            # Estimate PSF FWHM from second moments
            ixx = np.nanmedian(table[f'{band}_ixxPSF'])
            iyy = np.nanmedian(table[f'{band}_iyyPSF'])
            
            # FWHM = 2.355 * sigma, sigma = sqrt((ixx + iyy) / 2)
            sigma = np.sqrt((ixx + iyy) / 2)
            fwhm_arcsec = 2.355 * sigma * 0.2  # Assuming 0.2 arcsec/pixel
            fwhm_pixels = fwhm_arcsec / 0.2
            
            return {
                'fwhm_pixels': fwhm_pixels,
                'fwhm_arcsec': fwhm_arcsec,
                'ixx': ixx,
                'iyy': iyy,
                'n_sources': len(table),
                'source': 'measured'
            }
            
        except Exception as e:
            print(f"Error estimating PSF: {e}")
            return {'fwhm_pixels': 3.5, 'fwhm_arcsec': 0.7, 'source': 'default'}
