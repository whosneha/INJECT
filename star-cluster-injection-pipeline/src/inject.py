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
                   add_noise=True, pixel_scale=0.2, return_stamps=False):
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
        - 'psf': The PSF used for convolution (if available)
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
    
    # Generate intrinsic cluster model
    intrinsic_stamp = profile.generate_2d((stamp_size, stamp_size))
    
    # Store stamps for output
    stamps = {
        'intrinsic': intrinsic_stamp.copy(),
        'position': (cy, cx),
        'stamp_size': stamp_size,
        'psf': None,
        'convolved': None,
        'final': None
    }
    
    # Get PSF and convolve
    cluster_stamp = intrinsic_stamp.copy()
    
    if exposure is not None and HAS_LSST:
        # Use actual Rubin PSF from the coadd
        pos = Point2D(float(cx), float(cy))
        try:
            psf_array = get_psf_image_at_position(exposure, pos)
            stamps['psf'] = psf_array.copy()
            cluster_stamp = convolve_with_psf_galsim(cluster_stamp, psf_array, pixel_scale)
        except Exception as e:
            print(f"PSF convolution failed: {e}, using fallback")
            if psf_fwhm is not None:
                psf_array = _create_gaussian_psf(psf_fwhm, 41)
                stamps['psf'] = psf_array.copy()
                cluster_stamp = convolve_with_psf_galsim(cluster_stamp, psf_array, pixel_scale)
    elif psf_fwhm is not None:
        # Use generic Gaussian PSF
        psf_array = _create_gaussian_psf(psf_fwhm, 41)
        stamps['psf'] = psf_array.copy()
        cluster_stamp = convolve_with_psf_galsim(cluster_stamp, psf_array, pixel_scale)
    
    stamps['convolved'] = cluster_stamp.copy()
    
    # Add Poisson noise if requested
    if add_noise and np.any(cluster_stamp > 0):
        positive_mask = cluster_stamp > 0
        noisy_stamp = cluster_stamp.copy()
        noisy_stamp[positive_mask] = np.random.poisson(
            cluster_stamp[positive_mask].astype(np.float64)
        ).astype(np.float64)
        cluster_stamp = noisy_stamp
    
    stamps['final'] = cluster_stamp.copy()
    
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
            pos = Point2D(float(x), float(y))
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


def inject_from_catalog(image, catalog, psf_fwhm=None, exposure=None, 
                        add_noise=True, pixel_scale=0.2, save_stamps=False):
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
        else:  # discrete
            profile = create_cluster(
                method='discrete',
                n_stars=entry['n_stars'],
                r_half=entry['r_half'],
                total_magnitude=entry['magnitude'],
                profile_type=profile_type,
                imf=entry.get('imf', 'kroupa'),
                age_gyr=entry.get('age_gyr', 1.0),
                metallicity=entry.get('metallicity', 0.02),
                concentration=entry.get('concentration', 30),
                gamma=entry.get('gamma', 2.5),
                distance_pc=entry.get('distance_pc', 10000),
                band=entry.get('band', 'i'),
                mass_min=entry.get('mass_min', 0.1),
                mass_max=entry.get('mass_max', 100.0),
                binary_fraction=entry.get('binary_fraction', 0.0),
                seed=entry['id']
            )
        
        # Inject with stamp saving
        position = (entry['y'], entry['x'])
        result = inject_cluster(
            injected_image, position, profile,
            psf_fwhm=psf_fwhm, exposure=exposure,
            add_noise=add_noise, pixel_scale=pixel_scale,
            return_stamps=save_stamps
        )
        
        if save_stamps:
            injected_image, cluster_image, stamps = result
        else:
            injected_image, cluster_image = result
            stamps = None
        
        # Record info
        info = entry.copy()
        info['total_flux_injected'] = float(np.sum(cluster_image))
        info['peak_brightness'] = float(np.max(cluster_image))
        
        if save_stamps and stamps is not None:
            info['stamps'] = stamps
        
        if method == 'discrete' and isinstance(profile, DiscreteStarCluster):
            info['cluster_properties'] = profile.get_properties()
        
        injection_info.append(info)
    
    return injected_image, injection_info


# Legacy function aliases
def prepare_injection(image, profile):
    """Prepare an image for injection (placeholder)."""
    return image.copy()