"""
Main injection module for star cluster injection pipeline.

Follows the Rubin source injection tutorial approach:
https://pipelines.lsst.io/modules/lsst.source.injection/

Supports two cluster generation methods:
1. Smooth: Extended source with analytical profile
2. Discrete: Individual stars with positions and magnitudes
"""

import numpy as np
from .light_profiles import PlummerProfile, KingProfile, EFFProfile, SersicProfile
from .cluster_models import create_cluster, DiscreteStarCluster

# Check for GalSim (required for proper PSF convolution)
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


def get_psf_image_at_position(exposure, position):
    """
    Extract PSF image at a specific position from a Rubin coadd.
    
    Follows the Rubin tutorial approach for PSF extraction.
    
    Parameters:
    -----------
    exposure : lsst.afw.image.ExposureF
        The coadd exposure
    position : lsst.geom.Point2D
        Position in pixel coordinates
    
    Returns:
    --------
    psf_array : ndarray
        2D PSF image, normalized to sum to 1
    """
    if not HAS_LSST:
        raise RuntimeError("LSST stack required for PSF extraction")
    
    psf_model = exposure.getPsf()
    
    try:
        # Compute PSF image at the specified position
        psf_image = psf_model.computeKernelImage(position)
        psf_array = psf_image.array.copy()
        
        # Normalize to sum to 1
        psf_array = psf_array / np.sum(psf_array)
        return psf_array
        
    except Exception as e:
        print(f"Warning: Could not compute PSF at {position}: {e}")
        # Return a simple Gaussian PSF as fallback
        return _create_gaussian_psf(fwhm=3.5, size=41)


def _create_gaussian_psf(fwhm, size=41):
    """Create a simple Gaussian PSF as fallback."""
    sigma = fwhm / 2.355
    y, x = np.ogrid[:size, :size]
    center = size // 2
    r2 = (x - center)**2 + (y - center)**2
    psf = np.exp(-r2 / (2 * sigma**2))
    return psf / np.sum(psf)


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
        # Fallback to scipy FFT convolution
        from scipy.signal import fftconvolve
        return fftconvolve(image, psf_array, mode='same')
    
    ny, nx = image.shape
    
    # Create GalSim image objects
    gal_image = galsim.Image(image, scale=pixel_scale)
    psf_image = galsim.Image(psf_array, scale=pixel_scale)
    
    # Create InterpolatedImages
    source = galsim.InterpolatedImage(gal_image, scale=pixel_scale)
    psf = galsim.InterpolatedImage(psf_image, scale=pixel_scale, flux=1.0)
    
    # Convolve
    convolved = galsim.Convolve([source, psf])
    
    # Draw result
    result = galsim.Image(nx, ny, scale=pixel_scale)
    convolved.drawImage(image=result, scale=pixel_scale, method='no_pixel')
    
    return result.array


def inject_cluster(image, position, profile, psf_fwhm=None, exposure=None, 
                   add_noise=True, pixel_scale=0.2):
    """
    Inject a synthetic star cluster into an image.
    
    Follows the Rubin source injection tutorial methodology.
    
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
    
    Returns:
    --------
    injected_image : ndarray
        Image with injected cluster
    cluster_image : ndarray
        The cluster-only image (for diagnostics)
    """
    ny, nx = image.shape
    cy, cx = int(position[0]), int(position[1])
    
    # Check bounds
    if not (0 <= cx < nx and 0 <= cy < ny):
        print(f"Warning: Position ({cx}, {cy}) outside image. Skipping.")
        return image.copy(), np.zeros_like(image)
    
    # Determine stamp size based on cluster size
    stamp_size = max(51, int(10 * profile.r_half) | 1)
    half_stamp = stamp_size // 2
    
    # Generate intrinsic cluster model
    cluster_stamp = profile.generate_2d((stamp_size, stamp_size))
    
    # Get PSF and convolve
    if exposure is not None and HAS_LSST:
        # Use actual Rubin PSF from the coadd
        pos = Point2D(float(cx), float(cy))
        try:
            psf_array = get_psf_image_at_position(exposure, pos)
            cluster_stamp = convolve_with_psf_galsim(cluster_stamp, psf_array, pixel_scale)
        except Exception as e:
            print(f"PSF convolution failed: {e}, using fallback")
            if psf_fwhm is not None:
                psf_array = _create_gaussian_psf(psf_fwhm, 41)
                cluster_stamp = convolve_with_psf_galsim(cluster_stamp, psf_array, pixel_scale)
    elif psf_fwhm is not None:
        # Use generic Gaussian PSF
        psf_array = _create_gaussian_psf(psf_fwhm, 41)
        cluster_stamp = convolve_with_psf_galsim(cluster_stamp, psf_array, pixel_scale)
    
    # Add Poisson noise if requested
    if add_noise and np.any(cluster_stamp > 0):
        # Only add noise to positive values
        positive_mask = cluster_stamp > 0
        noisy_stamp = cluster_stamp.copy()
        noisy_stamp[positive_mask] = np.random.poisson(
            cluster_stamp[positive_mask].astype(np.float64)
        ).astype(np.float64)
        cluster_stamp = noisy_stamp
    
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
    
    return injected_image, cluster_image


def create_injection_catalog(n_clusters, image_shape, 
                             mag_range=(18, 25), 
                             r_half_range=(2, 30),
                             profile_type='plummer',
                             method='smooth',
                             n_stars_range=(50, 500),
                             imf='kroupa',
                             age_gyr_range=(0.1, 10.0),
                             edge_buffer=50,
                             exposure=None,
                             seed=None):
    """
    Create a catalog of clusters to inject.
    
    ...existing docstring...
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
            pos = Point2D(float(x), float(y))
            try:
                # Test if PSF can be computed here
                exposure.getPsf().computeKernelImage(pos)
            except:
                continue  # Skip invalid positions
        
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
        
        # Discrete star parameters
        if method == 'discrete':
            entry['n_stars'] = np.random.randint(*n_stars_range)
            entry['imf'] = imf
            entry['age_gyr'] = np.random.uniform(*age_gyr_range)
        
        catalog.append(entry)
    
    if len(catalog) < n_clusters:
        print(f"Warning: Only {len(catalog)}/{n_clusters} valid positions found")
    
    return catalog


def inject_from_catalog(image, catalog, psf_fwhm=None, exposure=None, 
                        add_noise=True, pixel_scale=0.2):
    """
    Inject multiple clusters from a catalog.
    
    ...existing docstring...
    """
    injected_image = image.copy()
    injection_info = []
    
    for i, entry in enumerate(catalog):
        if (i + 1) % 10 == 0:
            print(f"  Injecting cluster {i+1}/{len(catalog)}...")
        
        method = entry.get('method', 'smooth')
        profile_type = entry.get('profile_type', 'plummer')
        
        # Create cluster model
        if method == 'smooth':
            profile = create_cluster(
                method='smooth',
                profile_type=profile_type,
                r_half=entry['r_half'],
                magnitude=entry['magnitude'],
                age=entry.get('age_gyr', 1.0),
                concentration=entry.get('concentration', 30),
                gamma=entry.get('gamma', 2.5),
                sersic_n=entry.get('sersic_n', 2.0)
            )
        else:
            profile = create_cluster(
                method='discrete',
                n_stars=entry['n_stars'],
                r_half=entry['r_half'],
                total_magnitude=entry['magnitude'],
                profile_type=profile_type,
                imf=entry.get('imf', 'kroupa'),
                age_gyr=entry.get('age_gyr', 1.0),
                concentration=entry.get('concentration', 30),
                gamma=entry.get('gamma', 2.5),
                seed=entry['id']
            )
        
        # Inject
        position = (entry['y'], entry['x'])
        injected_image, cluster_image = inject_cluster(
            injected_image, position, profile,
            psf_fwhm=psf_fwhm, exposure=exposure,
            add_noise=add_noise, pixel_scale=pixel_scale
        )
        
        # Record info
        info = entry.copy()
        info['total_flux_injected'] = float(np.sum(cluster_image))
        info['peak_brightness'] = float(np.max(cluster_image))
        
        if method == 'discrete' and isinstance(profile, DiscreteStarCluster):
            info['cluster_properties'] = profile.get_properties()
        
        injection_info.append(info)
    
    return injected_image, injection_info


# Legacy function aliases
def prepare_injection(image, profile):
    """Prepare an image for injection (placeholder)."""
    return image.copy()