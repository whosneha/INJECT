"""
Data access module for Rubin data.
Supports both RSP Butler access and remote TAP service access.

PSF Handling:
- RSP mode: Uses actual PSF from coadd exposure (spatially varying)
- TAP mode: Estimates PSF FWHM from catalog (approximate, not actual PSF image)
"""

import numpy as np

# Check for LSST stack (only available on RSP)
try:
    from lsst.daf.butler import Butler
    from lsst.geom import Point2D, SpherePoint, degrees, Box2I, Point2I, Extent2I
    from lsst.afw.image import ExposureF
    HAS_LSST = True
except ImportError:
    HAS_LSST = False

# Import TAP query module
try:
    from .rubin_query import RubinDataQuery, HAS_PYVO
except ImportError:
    HAS_PYVO = False
    RubinDataQuery = None


# Export HAS_LSST for other modules
__all__ = ['RubinDataAccess', 'HAS_LSST', 'HAS_PYVO', 'load_coadd_image', 'get_butler']


class RubinDataAccess:
    """
    Unified data access class for Rubin data.
    
    Supports two modes:
    1. RSP mode: Direct Butler access (requires LSST stack)
       - Full access to images, PSF models, variance, WCS
       - Actual PSF from coadd (spatially varying)
    
    2. TAP mode: Remote TAP service with token authentication
       - Image cutouts via SODA
       - PSF estimated from catalog data (approximate)
    """
    
    def __init__(self, mode='auto', token=None, repo=None, collection=None):
        """
        Initialize data access.
        
        Parameters:
        -----------
        mode : str
            'rsp' for Butler access, 'tap' for TAP service, 'auto' to detect
        token : str
            Access token for TAP service (required for mode='tap')
        repo : str
            Butler repository path (for mode='rsp')
        collection : str
            Butler collection name (for mode='rsp')
        """
        self.mode = mode
        self.token = token
        self.butler = None
        self.tap_query = None
        
        # Auto-detect mode
        if mode == 'auto':
            if HAS_LSST:
                self.mode = 'rsp'
                print("Detected RSP environment, using Butler access")
            elif HAS_PYVO and token is not None:
                self.mode = 'tap'
                print("Using TAP service with token authentication")
            else:
                raise RuntimeError(
                    "No data access available. Either run on RSP or provide a token for TAP access."
                )
        
        # Initialize appropriate backend
        if self.mode == 'rsp':
            if not HAS_LSST:
                raise RuntimeError("LSST stack not available. Run on RSP or use mode='tap'.")
            if repo and collection:
                self.butler = Butler(repo, collections=collection)
        
        elif self.mode == 'tap':
            if not HAS_PYVO:
                raise RuntimeError("pyvo not installed. Install with: pip install pyvo")
            if token is None:
                raise ValueError("Token required for TAP access")
            self.tap_query = RubinDataQuery(token=token)
            if self.tap_query.tap_service is None:
                raise RuntimeError("Failed to initialize TAP service. Check your token.")
    
    def load_coadd(self, data_id=None, ra=None, dec=None, size_arcsec=120, band='i'):
        """
        Load a coadd image.
        
        Parameters:
        -----------
        data_id : dict
            Butler data ID (for RSP mode): {'tract': X, 'patch': Y, 'band': Z}
        ra : float
            Center RA in degrees (for TAP mode)
        dec : float
            Center Dec in degrees (for TAP mode)
        size_arcsec : float
            Cutout size in arcseconds (for TAP mode)
        band : str
            Filter band
        
        Returns:
        --------
        image : ndarray
            Image array
        metadata : dict
            Image metadata including WCS info
        """
        if self.mode == 'rsp':
            return self._load_coadd_butler(data_id)
        else:
            return self._load_coadd_tap(ra, dec, size_arcsec, band)
    
    def _load_coadd_butler(self, data_id):
        """Load coadd using Butler (RSP mode)."""
        if self.butler is None:
            raise RuntimeError("Butler not initialized. Provide repo and collection.")
        
        exposure = self.butler.get('deepCoadd', dataId=data_id)
        
        image = exposure.image.array.copy()
        
        metadata = {
            'exposure': exposure,
            'wcs': exposure.getWcs(),
            'psf': exposure.getPsf(),
            'variance': exposure.variance.array.copy(),
            'bbox': exposure.getBBox(),
            'mode': 'rsp'
        }
        
        return image, metadata
    
    def _load_coadd_tap(self, ra, dec, size_arcsec, band):
        """Load coadd cutout using TAP service."""
        if self.tap_query is None:
            raise RuntimeError("TAP service not initialized.")
        
        image_data, wcs, header = self.tap_query.get_image_cutout(
            ra, dec, size_arcsec, band
        )
        
        if image_data is None:
            raise RuntimeError(f"Failed to get image cutout at RA={ra}, Dec={dec}")
        
        # Get PSF info for this location
        psf_info = self.tap_query.get_psf_info(ra, dec, band)
        
        metadata = {
            'wcs': wcs,
            'header': header,
            'psf_fwhm_pixels': psf_info['fwhm_pixels'],
            'psf_fwhm_arcsec': psf_info['fwhm_arcsec'],
            'ra': ra,
            'dec': dec,
            'band': band,
            'mode': 'tap'
        }
        
        return image_data, metadata
    
    def get_psf_fwhm(self, metadata, position=None):
        """
        Get PSF FWHM at a position.
        
        Parameters:
        -----------
        metadata : dict
            Metadata from load_coadd
        position : tuple
            (x, y) pixel position (for RSP mode with spatially varying PSF)
        
        Returns:
        --------
        fwhm_pixels : float
            PSF FWHM in pixels
        """
        if metadata['mode'] == 'rsp' and 'psf' in metadata:
            # Get actual PSF from exposure
            psf_model = metadata['psf']
            if position is not None:
                from lsst.geom import Point2D
                pos = Point2D(position[0], position[1])
                shape = psf_model.computeShape(pos)
                sigma = np.sqrt(shape.getTraceRadius())
                return 2.355 * sigma
            else:
                # Return approximate FWHM
                return 3.5  # Default for Rubin
        
        elif metadata['mode'] == 'tap':
            return metadata.get('psf_fwhm_pixels', 3.5)
        
        else:
            return 3.5  # Default
    
    def pixel_to_sky(self, metadata, x, y):
        """Convert pixel coordinates to sky coordinates."""
        wcs = metadata.get('wcs')
        if wcs is None:
            raise RuntimeError("No WCS information available")
        
        if metadata['mode'] == 'rsp':
            sky = wcs.pixelToSky(Point2D(x, y))
            return sky.getRa().asDegrees(), sky.getDec().asDegrees()
        else:
            # Astropy WCS
            ra, dec = wcs.pixel_to_world_values(x, y)
            return float(ra), float(dec)
    
    def sky_to_pixel(self, metadata, ra, dec):
        """Convert sky coordinates to pixel coordinates."""
        wcs = metadata.get('wcs')
        if wcs is None:
            raise RuntimeError("No WCS information available")
        
        if metadata['mode'] == 'rsp':
            sky = SpherePoint(ra * degrees, dec * degrees)
            pixel = wcs.skyToPixel(sky)
            return pixel.x, pixel.y
        else:
            # Astropy WCS
            x, y = wcs.world_to_pixel_values(ra, dec)
            return float(x), float(y)


# Convenience functions for backward compatibility
def load_coadd_image(butler_or_path, data_id=None):
    """Legacy function - use RubinDataAccess instead."""
    if HAS_LSST:
        if isinstance(butler_or_path, str):
            raise RuntimeError("String paths not supported. Pass a Butler instance.")
        butler = butler_or_path
        exposure = butler.get('deepCoadd', dataId=data_id)
        return exposure
    else:
        raise RuntimeError("LSST stack not available. Use RubinDataAccess with TAP mode.")


def get_butler(repo, collection):
    """Legacy function - use RubinDataAccess instead."""
    if not HAS_LSST:
        raise RuntimeError("LSST stack not available. Run on RSP.")
    return Butler(repo, collections=collection)