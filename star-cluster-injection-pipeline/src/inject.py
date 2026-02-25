"""
Main injection module for star cluster injection pipeline.
"""

import numpy as np
from .light_profiles import PlummerProfile, KingProfile, EFFProfile, SersicProfile
from .psf_convolution import convolve_with_psf, HAS_GALSIM

try:
    from lsst.afw.image import ExposureF
    from lsst.geom import Point2D, SpherePoint, degrees
    from .psf_convolution import convolve_with_coadd_psf, get_psf_from_coadd
    HAS_LSST = True
except ImportError:
    HAS_LSST = False


def inject_cluster(image, position, profile, psf_fwhm=None, exposure=None, add_noise=True):
    """
    Inject a synthetic star cluster into an image.
    
    Parameters:
    -----------
    image : ndarray
        Input image (will be modified in place if copy=False)
    position : tuple
        (y, x) pixel position for cluster center
    profile : object
        Light profile object (PlummerProfile, KingProfile, etc.)
    psf_fwhm : float, optional
        PSF FWHM in pixels (for generic PSF convolution)
    exposure : lsst.afw.image.ExposureF, optional
        Rubin coadd exposure (for using actual PSF). Takes precedence over psf_fwhm.
    add_noise : bool
        Whether to add Poisson noise to the injected cluster
    
    Returns:
    --------
    injected_image : ndarray
        Image with injected cluster
    cluster_image : ndarray
        The cluster-only image (for diagnostics)
    """
    ny, nx = image.shape
    cy, cx = position
    
    # Determine stamp size (5x the half-light radius, minimum 51 pixels)
    stamp_size = max(51, int(10 * profile.r_half) | 1)  # Ensure odd
    half_stamp = stamp_size // 2
    
    # Generate the cluster model
    cluster_stamp = profile.generate_2d((stamp_size, stamp_size))
    
    # Convolve with PSF
    if exposure is not None and HAS_LSST:
        # Use actual Rubin PSF from the coadd
        pos = Point2D(cx, cy)
        cluster_stamp = convolve_with_coadd_psf(cluster_stamp, exposure, pos)
    elif psf_fwhm is not None and HAS_GALSIM:
        # Use generic PSF
        cluster_stamp = convolve_with_psf(cluster_stamp, fwhm=psf_fwhm)
    
    # Add Poisson noise if requested
    if add_noise and np.any(cluster_stamp > 0):
        # Poisson noise: variance = signal
        noise = np.random.poisson(np.maximum(cluster_stamp, 0).astype(int)).astype(float)
        cluster_stamp = noise
    
    # Compute bounds for insertion
    y_start = max(0, cy - half_stamp)
    y_end = min(ny, cy + half_stamp + 1)
    x_start = max(0, cx - half_stamp)
    x_end = min(nx, cx + half_stamp + 1)
    
    # Compute corresponding bounds in the stamp
    stamp_y_start = half_stamp - (cy - y_start)
    stamp_y_end = half_stamp + (y_end - cy)
    stamp_x_start = half_stamp - (cx - x_start)
    stamp_x_end = half_stamp + (x_end - cx)
    
    # Create output image
    injected_image = image.copy()
    
    # Add the cluster to the image
    injected_image[y_start:y_end, x_start:x_end] += \
        cluster_stamp[stamp_y_start:stamp_y_end, stamp_x_start:stamp_x_end]
    
    # Create full-size cluster image for diagnostics
    cluster_image = np.zeros_like(image)
    cluster_image[y_start:y_end, x_start:x_end] = \
        cluster_stamp[stamp_y_start:stamp_y_end, stamp_x_start:stamp_x_end]
    
    return injected_image, cluster_image


def prepare_injection(image, profile):
    """
    Prepare an image for injection (placeholder for any preprocessing).
    
    Parameters:
    -----------
    image : ndarray
        Input image
    profile : object
        Light profile object
    
    Returns:
    --------
    prepared_image : ndarray
        Prepared image (currently just returns a copy)
    """
    return image.copy()


def create_injection_catalog(n_clusters, image_shape, 
                             mag_range=(18, 25), 
                             r_half_range=(2, 30),
                             profile_type='plummer',
                             edge_buffer=50,
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
    edge_buffer : int
        Minimum distance from image edges
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
    for i in range(n_clusters):
        # Random position
        y = np.random.randint(edge_buffer, ny - edge_buffer)
        x = np.random.randint(edge_buffer, nx - edge_buffer)
        
        # Random magnitude (uniform in mag = uniform in log flux)
        mag = np.random.uniform(*mag_range)
        
        # Random half-light radius (log-uniform distribution)
        log_r_half = np.random.uniform(np.log10(r_half_range[0]), 
                                        np.log10(r_half_range[1]))
        r_half = 10 ** log_r_half
        
        entry = {
            'id': i,
            'x': x,
            'y': y,
            'magnitude': mag,
            'r_half': r_half,
            'profile_type': profile_type,
        }
        
        # Add profile-specific parameters
        if profile_type == 'king':
            entry['concentration'] = np.random.uniform(10, 100)
        elif profile_type == 'eff':
            entry['gamma'] = np.random.uniform(2.2, 3.5)
        elif profile_type == 'sersic':
            entry['sersic_n'] = np.random.uniform(1, 4)
        
        catalog.append(entry)
    
    return catalog


def inject_from_catalog(image, catalog, psf_fwhm=None, exposure=None, add_noise=True):
    """
    Inject multiple clusters from a catalog.
    
    Parameters:
    -----------
    image : ndarray
        Input image
    catalog : list of dict
        Cluster catalog from create_injection_catalog
    psf_fwhm : float, optional
        PSF FWHM for generic convolution
    exposure : optional
        Rubin coadd exposure for actual PSF
    add_noise : bool
        Whether to add Poisson noise
    
    Returns:
    --------
    injected_image : ndarray
        Image with all clusters injected
    injection_info : list
        List of injection results/diagnostics
    """
    injected_image = image.copy()
    injection_info = []
    
    for entry in catalog:
        # Create the appropriate profile
        profile_type = entry.get('profile_type', 'plummer')
        
        if profile_type == 'plummer':
            profile = PlummerProfile(
                r_half=entry['r_half'],
                age=1.0,
                magnitude=entry['magnitude']
            )
        elif profile_type == 'king':
            profile = KingProfile(
                r_half=entry['r_half'],
                concentration=entry.get('concentration', 30),
                age=1.0,
                magnitude=entry['magnitude']
            )
        elif profile_type == 'eff':
            profile = EFFProfile(
                r_half=entry['r_half'],
                gamma=entry.get('gamma', 2.5),
                age=1.0,
                magnitude=entry['magnitude']
            )
        elif profile_type == 'sersic':
            profile = SersicProfile(
                r_half=entry['r_half'],
                sersic_n=entry.get('sersic_n', 2),
                age=1.0,
                magnitude=entry['magnitude']
            )
        else:
            raise ValueError(f"Unknown profile type: {profile_type}")
        
        # Inject the cluster
        position = (entry['y'], entry['x'])
        injected_image, cluster_image = inject_cluster(
            injected_image, position, profile,
            psf_fwhm=psf_fwhm, exposure=exposure, add_noise=add_noise
        )
        
        # Store injection info
        info = entry.copy()
        info['total_flux_injected'] = np.sum(cluster_image)
        info['peak_brightness'] = np.max(cluster_image)
        injection_info.append(info)
    
    return injected_image, injection_info