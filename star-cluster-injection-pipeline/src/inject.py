"""
Main injection module for star cluster injection pipeline.


Supports two cluster generation methods:
1. Smooth: Extended source with analytical profile
2. Discrete: Individual stars with positions and magnitudes

Hi here I am testing the additon of a change just so that I can show you how to make changes to github!

Let's try together , can put in something as easy as a comment. you can see my change in a comment ahah!
"""

import numpy as np
from .light_profiles import PlummerProfile, KingProfile, EFFProfile, SersicProfile
from .cluster_models import create_cluster, DiscreteStarCluster



# Check for GalSim (required for proper PSF convolution) NEED TO REMOVE THIS BECUASe the psf is solved!
try:
    import galsim
    HAS_GALSIM = True
except ImportError:
    HAS_GALSIM = False
    print("Warning: GalSim not installed. PSF convolution will be limited.")

# Check for LSST stack
try:
    from lsst.afw.image import ExposureF, ImageF
    from lsst.geom import Point2D, Point2I, Box2I, Extent2I
    from lsst.afw.math import Warper
    HAS_LSST = True
except ImportError:
    HAS_LSST = False

from src.psf_convolution import get_psf_from_coadd, convolve_with_psf

# ...existing code...

def get_psf_image_at_position(exposure, position):
    """
    Extract PSF as a GalSim InterpolatedImage at a specific position from a Rubin coadd.

    Parameters
    ----------
    exposure : lsst.afw.image.ExposureF
        The coadd exposure.
    position : lsst.geom.Point2D
        Position in CUTOUT pixel coordinates (0-indexed).
        The bbox offset is applied internally.

    Returns
    -------
    psf_gs : galsim.InterpolatedImage
        GalSim PSF object normalized to unit flux.
    fwhm_px : float
        PSF FWHM at this position in pixels.
    """
    if not HAS_LSST:
        raise RuntimeError("LSST stack required for PSF extraction")

    psf_obj = exposure.getPsf()

    # Convert cutout coords -> focal plane coords using bbox offset
    bbox      = exposure.getBBox()
    focal_x   = position.getX() + bbox.getMinX()
    focal_y   = position.getY() + bbox.getMinY()
    focal_pos = Point2D(focal_x, focal_y)

    try:
        # Use computeImage (not computeKernelImage) to match notebook approach
        psf_image = psf_obj.computeImage(focal_pos)
        psf_array = psf_image.array.astype(np.float64)

        # Normalise to unit sum
        psf_sum = psf_array.sum()
        if psf_sum > 0:
            psf_array /= psf_sum

        # Wrap as GalSim InterpolatedImage
        gs_img = galsim.Image(psf_array, scale=PIXEL_SCALE_DEFAULT)
        psf_gs = galsim.InterpolatedImage(gs_img, normalization='flux')

        # Measure FWHM at this position
        shape   = psf_obj.computeShape(focal_pos)
        fwhm_px = shape.getDeterminantRadius() * 2.355

        return psf_gs, fwhm_px

    except Exception as e:
        print(f"Warning: Could not compute PSF at focal plane ({focal_x:.0f}, {focal_y:.0f}): {e}")
        return None, None

# ...existing code...

def _create_gaussian_psf(fwhm, size=41):
    """Create a simple Gaussian PSF as fallback."""
    sigma = fwhm / 2.355
    y, x = np.ogrid[:size, :size]
    center = size // 2
    r2 = (x - center)**2 + (y - center)**2
    psf = np.exp(-r2 / (2 * sigma**2))
    return psf / np.sum(psf)


def _gaussian_psf_galsim(fwhm_px, pixel_scale):
    """Create a GalSim Gaussian PSF as fallback."""
    return galsim.Gaussian(fwhm=fwhm_px * pixel_scale)


PIXEL_SCALE_DEFAULT = 0.2  # arcsec/pixel (Rubin standard)


def convolve_with_psf_galsim(image, psf_array, pixel_scale=1.0):
    """
    Convolve an image with a PSF using GalSim.
    
    This follows the Rubin injection tutorial approach.
    
    Parameters:
    -----------
    image : ndarray
        Input 2D image
    psf_array : ndarray
        2D PSF image (should sum to 1)
    pixel_scale : float
        Pixel scale in arcsec/pixel
    
    Returns:
    --------
    convolved : ndarray
        Convolved image
    """
    if not HAS_GALSIM:
        from scipy.signal import fftconvolve
        return fftconvolve(image, psf_array, mode='same')

    ny, nx = image.shape

    # Wrap cluster image as GalSim InterpolatedImage
    gs_cluster_img = galsim.Image(image.astype(np.float64), scale=pixel_scale)
    cluster_gs     = galsim.InterpolatedImage(gs_cluster_img, normalization='flux')

    # Wrap PSF as GalSim InterpolatedImage
    gs_psf_img = galsim.Image(psf_array.astype(np.float64), scale=pixel_scale)
    psf_gs     = galsim.InterpolatedImage(gs_psf_img, normalization='flux')

    # Convolve
    convolved = galsim.Convolve([cluster_gs, psf_gs])

    # Draw result
    result = galsim.Image(nx, ny, scale=pixel_scale)
    convolved.drawImage(image=result, method='no_pixel')

    return result.array


def inject_cluster(image, position, profile, psf_fwhm=None, exposure=None,
                   add_noise=True, pixel_scale=0.2, return_stamps=False):
    """
    Inject a synthetic star cluster into an image.
    
    Uses the actual Rubin CoaddPsf (via GalSim InterpolatedImage + Convolve)
    when an exposure is provided, with a Gaussian fallback otherwise.
    
    Parameters:
    -----------
    image : ndarray
        Input image array
    position : tuple
        (y, x) pixel position for cluster center
    profile : object
        Light profile object (PlummerProfile, etc.) or DiscreteStarCluster
    psf_fwhm : float, optional
        PSF FWHM in pixels (fallback if no exposure)
    exposure : lsst.afw.image.ExposureF, optional
        Rubin coadd exposure for actual PSF
    add_noise : bool
        Whether to add Poisson noise
    pixel_scale : float
        Pixel scale in arcsec/pixel (default 0.2 for Rubin)
    return_stamps : bool
        If True, also return the intrinsic and convolved stamps
    
    Returns:
    --------
    injected_image : ndarray
        Image with injected cluster
    cluster_image : ndarray
        The cluster-only image (for diagnostics)
    stamps : dict (only if return_stamps=True)
        Dictionary containing:
        - 'intrinsic': The intrinsic cluster stamp (before PSF)
        - 'convolved': The PSF-convolved stamp (before noise)
        - 'final': The final stamp (with noise if added)
        - 'psf': The PSF array used for convolution (if available)
        - 'psf_fwhm_px': Measured PSF FWHM at injection position (pixels)
    """
    ny, nx = image.shape
    cy, cx = int(position[0]), int(position[1])

    # Check bounds
    if not (0 <= cx < nx and 0 <= cy < ny):
        print(f"Warning: Position ({cx}, {cy}) outside image. Skipping.")
        if return_stamps:
            return image.copy(), np.zeros_like(image), {}
        return image.copy(), np.zeros_like(image)

    # Determine stamp size based on cluster size
    stamp_size = max(51, int(10 * profile.r_half) | 1)
    half_stamp = stamp_size // 2

    # Generate intrinsic cluster model (normalised to sum=1)
    intrinsic_stamp = profile.generate_2d((stamp_size, stamp_size)).astype(np.float64)
    total = intrinsic_stamp.sum()
    if total > 0:
        intrinsic_stamp /= total

    stamps = {
        'intrinsic':    intrinsic_stamp.copy(),
        'position':     (cy, cx),
        'stamp_size':   stamp_size,
        'psf':          None,
        'psf_fwhm_px':  None,
        'convolved':    None,
        'final':        None,
    }

    # ---- PSF selection and convolution ----------------------------------------
    rng = np.random.default_rng()

    if exposure is not None and HAS_LSST and HAS_GALSIM:
        # Use actual Rubin CoaddPsf via GalSim InterpolatedImage
        pos = Point2D(float(cx), float(cy))
        psf_gs, fwhm_px = get_psf_image_at_position(exposure, pos)

        if psf_gs is None:
            # get_psf_image_at_position already printed a warning; use fallback
            fallback_fwhm = psf_fwhm if psf_fwhm is not None else 3.5
            psf_gs   = _gaussian_psf_galsim(fallback_fwhm, pixel_scale)
            fwhm_px  = fallback_fwhm

        stamps['psf_fwhm_px'] = fwhm_px

        # Wrap intrinsic stamp as GalSim InterpolatedImage
        gs_cluster_img = galsim.Image(intrinsic_stamp, scale=pixel_scale)
        cluster_gs     = galsim.InterpolatedImage(gs_cluster_img, normalization='flux')

        # Convolve cluster with actual PSF
        convolved_gs = galsim.Convolve([cluster_gs, psf_gs])
        out_img      = galsim.Image(stamp_size, stamp_size, scale=pixel_scale)
        convolved_gs.drawImage(image=out_img, method='no_pixel')
        cluster_stamp = out_img.array.copy().astype(np.float64)

    elif HAS_GALSIM and psf_fwhm is not None:
        # Gaussian fallback via GalSim
        psf_array = _create_gaussian_psf(psf_fwhm, 41)
        stamps['psf']        = psf_array.copy()
        stamps['psf_fwhm_px'] = psf_fwhm
        cluster_stamp = convolve_with_psf_galsim(intrinsic_stamp, psf_array, pixel_scale)

    else:
        # No PSF convolution
        cluster_stamp = intrinsic_stamp.copy()

    stamps['convolved'] = cluster_stamp.copy()

    # Scale to correct total flux (profile already normalised to sum=1,
    # drawImage preserves flux so cluster_stamp.sum() ≈ 1 after convolution)
    stamp_sum = cluster_stamp.sum()
    if stamp_sum > 0:
        # Re-normalise in case convolution changed total slightly
        cluster_stamp /= stamp_sum
        # Then scale by the intrinsic flux from the profile
        total_flux = intrinsic_stamp.sum() if total > 0 else 1.0
        cluster_stamp *= total_flux

    # Add Poisson noise if requested
    if add_noise and np.any(cluster_stamp > 0):
        noise_sigma = np.sqrt(np.clip(cluster_stamp, 0, None))
        cluster_stamp += rng.normal(
            0.0, np.where(noise_sigma > 0, noise_sigma, 1e-10)
        )

    stamps['final'] = cluster_stamp.copy()

    # ...existing code...
    
    # Calculate insertion bounds
    y_start = max(0, cy - half_stamp)
    y_end = min(ny, cy + half_stamp + 1)
    x_start = max(0, cx - half_stamp)
    x_end = min(nx, cx + half_stamp + 1)
    
    # Calculate stamp bounds
    stamp_y_start = half_stamp - (cy - y_start)
    stamp_y_end = half_stamp + (y_end - cy)
    stamp_x_start = half_stamp - (cx - x_start)
    stamp_x_end = half_stamp + (x_end - cx)
    
    # Create output
    injected_image = image.copy()
    
    # Add cluster to image
    injected_image[y_start:y_end, x_start:x_end] += \
        cluster_stamp[stamp_y_start:stamp_y_end, stamp_x_start:stamp_x_end]
    
    # Create diagnostic image
    cluster_image = np.zeros_like(image)
    cluster_image[y_start:y_end, x_start:x_end] = \
        cluster_stamp[stamp_y_start:stamp_y_end, stamp_x_start:stamp_x_end]
    
    if return_stamps:
        return injected_image, cluster_image, stamps
    return injected_image, cluster_image


def create_injection_catalog(n_clusters, image_shape, 
                             mag_range=(18, 25), 
                             r_half_range=(2, 30),
                             profile_type='plummer',
                             method='smooth',
                             # Discrete star parameters
                             n_stars_range=(50, 500),
                             n_stars_fixed=None,
                             imf='kroupa',
                             age_gyr_range=(0.1, 10.0),
                             age_gyr_fixed=None,
                             metallicity_range=(0.001, 0.04),
                             metallicity_fixed=None,
                             distance_pc_range=(5000, 50000),
                             distance_pc_fixed=None,
                             mass_range=(0.1, 100.0),
                             binary_fraction=0.3,
                             band='i',
                             # Other parameters
                             edge_buffer=50,
                             exposure=None,
                             seed=None):
    """
    Create a catalog of clusters to inject.
    
    Parameters:
    -----------
    n_clusters : int
        Number of clusters to inject
    image_shape : tuple
        Shape of the target image (ny, nx)
    mag_range : tuple
        (min_mag, max_mag) for uniform magnitude distribution
    r_half_range : tuple
        (min_r_half, max_r_half) in pixels
    profile_type : str
        Type of profile: 'plummer', 'king', 'eff', 'sersic'
    method : str
        'smooth' for extended source, 'discrete' for individual stars
    
    --- Discrete star parameters ---
    n_stars_range : tuple
        (min_stars, max_stars) - randomized per cluster
    n_stars_fixed : int, optional
        If set, all clusters have this many stars
    imf : str
        Initial mass function: 'kroupa', 'chabrier', 'salpeter'
    age_gyr_range : tuple
        (min_age, max_age) in Gyr - randomized per cluster
    age_gyr_fixed : float, optional
        If set, all clusters have this age
    metallicity_range : tuple
        (min_Z, max_Z) - randomized per cluster (solar=0.02)
    metallicity_fixed : float, optional
        If set, all clusters have this metallicity
    distance_pc_range : tuple
        (min_dist, max_dist) in parsecs
    distance_pc_fixed : float, optional
        If set, all clusters at this distance
    mass_range : tuple
        (min_mass, max_mass) stellar mass range in Msun
    binary_fraction : float
        Fraction of stars that are binaries (0-1)
    band : str
        Photometric band for magnitudes
    
    --- Other parameters ---
    edge_buffer : int
        Minimum distance from image edges
    exposure : optional
        If provided, check PSF validity
    seed : int, optional
        Random seed for reproducibility
    
    Returns:
    --------
    catalog : list of dict
        List of cluster parameters
    """
    if seed is not None:
        np.random.seed(seed)
    
    ny, nx = image_shape
    
    catalog = []
    attempts = 0
    max_attempts = n_clusters * 10
    
    while len(catalog) < n_clusters and attempts < max_attempts:
        attempts += 1
        
        # Random position avoiding edges
        y = np.random.randint(edge_buffer, ny - edge_buffer)
        x = np.random.randint(edge_buffer, nx - edge_buffer)
        
        # Check PSF validity if exposure provided
        if exposure is not None and HAS_LSST:
            # ── FIX: use focal plane coords for PSF validity check ────────────
            # Raw cutout coords (x, y) cannot be passed directly to the PSF.
            # The CoaddPsf bbox does not start at (0,0) — must add the offset.
            bbox    = exposure.getBBox()
            focal_x = float(x) + bbox.getMinX()
            focal_y = float(y) + bbox.getMinY()
            pos     = Point2D(focal_x, focal_y)
            # ── END FIX ──────────────────────────────────────────────────────
            try:
                exposure.getPsf().computeKernelImage(pos)
            except:
                continue

        # Random magnitude (uniform)
        mag = np.random.uniform(*mag_range)
        
        # Random half-light radius (log-uniform)
        log_r_half = np.random.uniform(np.log10(r_half_range[0]), 
                                        np.log10(r_half_range[1]))
        r_half = 10 ** log_r_half
        
        entry = {
            'id': len(catalog),
            'x': x,
            'y': y,
            'magnitude': mag,
            'r_half': r_half,
            'profile_type': profile_type,
            'method': method,
        }
        
        # Profile-specific parameters
        if profile_type == 'king':
            entry['concentration'] = np.random.uniform(10, 100)
        elif profile_type == 'eff':
            entry['gamma'] = np.random.uniform(2.2, 3.5)
        elif profile_type == 'sersic':
            entry['sersic_n'] = np.random.uniform(1, 4)
        
        # Discrete star parameters - with randomization options
        if method == 'discrete':
            # Number of stars
            if n_stars_fixed is not None:
                entry['n_stars'] = n_stars_fixed
            else:
                entry['n_stars'] = np.random.randint(n_stars_range[0], n_stars_range[1] + 1)
            
            # IMF
            entry['imf'] = imf
            
            # Age
            if age_gyr_fixed is not None:
                entry['age_gyr'] = age_gyr_fixed
            else:
                # Log-uniform distribution for age
                log_age = np.random.uniform(np.log10(age_gyr_range[0]), 
                                            np.log10(age_gyr_range[1]))
                entry['age_gyr'] = 10 ** log_age
            
            # Metallicity
            if metallicity_fixed is not None:
                entry['metallicity'] = metallicity_fixed
            else:
                # Log-uniform distribution for metallicity
                log_Z = np.random.uniform(np.log10(metallicity_range[0]), 
                                          np.log10(metallicity_range[1]))
                entry['metallicity'] = 10 ** log_Z
            
            # Distance
            if distance_pc_fixed is not None:
                entry['distance_pc'] = distance_pc_fixed
            else:
                # Log-uniform distribution for distance
                log_d = np.random.uniform(np.log10(distance_pc_range[0]), 
                                          np.log10(distance_pc_range[1]))
                entry['distance_pc'] = 10 ** log_d
            
            # Other discrete parameters
            entry['mass_min'] = mass_range[0]
            entry['mass_max'] = mass_range[1]
            entry['binary_fraction'] = binary_fraction
            entry['band'] = band
            
            # Calculate [Fe/H] for convenience
            entry['feh'] = np.log10(entry['metallicity'] / 0.02)
        
        catalog.append(entry)
    
    if len(catalog) < n_clusters:
        print(f"Warning: Only {len(catalog)}/{n_clusters} valid positions found")
    
    return catalog


def inject_from_catalog(image, catalog, exposure=None, add_noise=True,
                        pixel_scale=0.2, save_stamps=False,
                        psf_mode='none', psf_kernel=None):
    """
    Inject synthetic clusters into an image from a catalog.

    Parameters
    ----------
    image : np.ndarray
        Original image array.
    catalog : list of dict
        Injection catalog entries.
    exposure : lsst.afw.image.ExposureF, optional
        Coadd exposure (needed for spatially_varying PSF mode).
    add_noise : bool
        Whether to add Poisson noise to injected flux.
    pixel_scale : float
        Pixel scale in arcsec/pixel.
    save_stamps : bool
        Whether to save individual cluster stamps in injection_info.
    psf_mode : str
        'none' — no PSF convolution (raw analytical profile).
        'fixed' — convolve every cluster with the same psf_kernel.
        'spatially_varying' — evaluate PSF at each cluster position from exposure.
    psf_kernel : np.ndarray or None
        PSF kernel to use when psf_mode='fixed'. Must be normalized to sum=1.

    Returns
    -------
    injected_image : np.ndarray
    injection_info : list of dict
    """
    injected_image = image.copy().astype(np.float64)
    injection_info = []

    for entry in catalog:
        # ...existing code to generate raw cluster stamp...
        # This produces: stamp (2D array), cx, cy, and other metadata
        # The exact variable names depend on your existing implementation.
        # Below we assume your existing code creates `stamp` before adding to image.

        stamp, stamp_info = inject_cluster(
            entry, exposure=exposure, pixel_scale=pixel_scale,
            save_stamp=save_stamps
        )

        # ---- PSF convolution ----
        if psf_mode == 'spatially_varying' and exposure is not None:
            # ── FIX: use focal plane coords ───────────────────────────────────
            bbox    = exposure.getBBox()
            focal_x = float(entry['x']) + bbox.getMinX()
            focal_y = float(entry['y']) + bbox.getMinY()
            pos     = Point2D(focal_x, focal_y)
            # ── END FIX ──────────────────────────────────────────────────────
            try:
                local_psf = get_psf_from_coadd(exposure, pos)
                stamp     = convolve_with_psf(stamp, local_psf)
            except Exception as e:
                print(f"  Warning: PSF convolution failed for cluster {entry.get('id','?')}: {e}")
                stamp_info['psf_convolved'] = False
        elif psf_mode == 'fixed' and psf_kernel is not None:
            stamp = convolve_with_psf(stamp, psf_kernel)
            stamp_info['psf_convolved'] = True
        else:
            stamp_info['psf_convolved'] = False

        # ---- Add noise if requested ----
        if add_noise:
            noise = np.random.poisson(np.clip(stamp, 0, None)).astype(np.float64) - stamp
            stamp = stamp + noise

        # ---- Place stamp into image ----
        cx_int, cy_int = int(round(entry['x'])), int(round(entry['y']))
        sh, sw = stamp.shape
        hy, hx = sh // 2, sw // 2

        # Compute placement bounds with edge clipping
        y0_img = max(0, cy_int - hy)
        y1_img = min(injected_image.shape[0], cy_int - hy + sh)
        x0_img = max(0, cx_int - hx)
        x1_img = min(injected_image.shape[1], cx_int - hx + sw)

        y0_stmp = y0_img - (cy_int - hy)
        y1_stmp = y0_stmp + (y1_img - y0_img)
        x0_stmp = x0_img - (cx_int - hx)
        x1_stmp = x0_stmp + (x1_img - x0_img)

        injected_image[y0_img:y1_img, x0_img:x1_img] += stamp[y0_stmp:y1_stmp, x0_stmp:x1_stmp]

        # ---- Record info ----
        stamp_info['total_flux_injected'] = float(stamp.sum())
        stamp_info['peak_brightness'] = float(stamp.max())
        stamp_info['x'] = entry['x']
        stamp_info['y'] = entry['y']
        stamp_info['magnitude'] = entry['magnitude']
        stamp_info['r_half'] = entry['r_half']
        if save_stamps:
            stamp_info['stamp'] = stamp

        injection_info.append(stamp_info)

    return injected_image.astype(image.dtype), injection_info


def inject_multiband(images_dict, catalog, exposures=None, add_noise=True,
                     pixel_scale=0.2, save_stamps=False,
                     psf_mode='none', psf_kernel=None):
    """
    Inject clusters into multiple bands.

    Parameters
    ----------
    images_dict : dict of {band: np.ndarray}
    catalog : list of dict (must have band-specific magnitude keys)
    exposures : dict of {band: ExposureF}, optional
    add_noise, pixel_scale, save_stamps : as above
    psf_mode : str — 'none', 'fixed', 'spatially_varying'
    psf_kernel : np.ndarray or None — used when psf_mode='fixed'

    Returns
    -------
    injected_images : dict of {band: np.ndarray}
    injection_info : dict of {band: list of dict}
    """
    injected_images = {}
    injection_info_all = {}

    for band, img in images_dict.items():
        exp = exposures.get(band) if exposures else None

        # For spatially_varying mode, each band uses its own exposure's PSF
        band_psf_mode = psf_mode
        band_psf_kernel = psf_kernel

        # If fixed mode but we have per-band exposures, could upgrade to spatially_varying
        # For now, pass through as-is

        band_catalog = []
        for entry in catalog:
            band_entry = entry.copy()
            # Use band-specific magnitude if available
            mag_key = f'magnitude_{band}'
            if mag_key in entry:
                band_entry['magnitude'] = entry[mag_key]
            band_catalog.append(band_entry)

        injected_images[band], injection_info_all[band] = inject_from_catalog(
            img, band_catalog,
            exposure=exp,
            add_noise=add_noise,
            pixel_scale=pixel_scale,
            save_stamps=save_stamps,
            psf_mode=band_psf_mode,
            psf_kernel=band_psf_kernel,
        )
        print(f'  ✓ {band}-band: {len(injection_info_all[band])} clusters injected')

    return injected_images, injection_info_all


def prepare_injection(image, profile):
    """Prepare an image for injection (placeholder)."""
    return image.copy()


def create_multiband_catalog(n_clusters, image_shape,
                             bands=('g', 'r', 'i'),
                             mag_ranges=None,
                             r_half_range=(2, 30),
                             profile_type='plummer',
                             method='smooth',
                             edge_buffer=50,
                             exposure=None,
                             seed=None):
    """
    Create one positional catalog shared across all bands,
    with per-band magnitudes drawn independently.

    Parameters:
    -----------
    n_clusters : int
        Number of clusters
    image_shape : tuple
        (ny, nx) of image
    bands : tuple of str
        Bands to generate magnitudes for, e.g. ('g', 'r', 'i')
    mag_ranges : dict, optional
        Per-band magnitude ranges, e.g. {'g': (19, 26), 'r': (19, 25), 'i': (18, 25)}.
        If None, uses (19, 25) for all bands.
    r_half_range : tuple
        Half-light radius range in pixels (same for all bands)
    profile_type : str
        Spatial profile type (same for all bands)
    method : str
        'smooth' or 'discrete'
    edge_buffer : int
        Minimum distance from image edges
    exposure : optional
        Exposure for PSF validity check (single band)
    seed : int, optional
        Random seed

    Returns:
    --------
    catalog : list of dict
        Catalog with 'magnitude_<band>' keys for each band,
        plus shared spatial parameters (x, y, r_half, profile_type, method)
    """
    if mag_ranges is None:
        mag_ranges = {b: (19.0, 25.0) for b in bands}

    # Generate base catalog for positions and sizes (use first band for PSF check)
    base_catalog = create_injection_catalog(
        n_clusters=n_clusters,
        image_shape=image_shape,
        mag_range=mag_ranges.get(bands[0], (19, 25)),
        r_half_range=r_half_range,
        profile_type=profile_type,
        method=method,
        edge_buffer=edge_buffer,
        exposure=exposure,
        seed=seed
    )

    # Add per-band magnitudes
    if seed is not None:
        np.random.seed(seed + 99)

    for entry in base_catalog:
        for band in bands:
            lo, hi = mag_ranges.get(band, (19, 25))
            entry[f'magnitude_{band}'] = np.random.uniform(lo, hi)

    print(f"✓ Multiband catalog: {len(base_catalog)} clusters × {len(bands)} bands")
    for band in bands:
        mags = [e[f'magnitude_{band}'] for e in base_catalog]
        print(f"  {band}: mag range [{min(mags):.1f}, {max(mags):.1f}]")

    return base_catalog


# Legacy function aliases
def prepare_injection(image, profile):
    """Prepare an image for injection (placeholder)."""
    return image.copy()