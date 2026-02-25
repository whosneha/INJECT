"""
PSF convolution module using GalSim for realistic Rubin-like PSF modeling.
Supports both generic PSFs and actual Rubin coadd PSFs.
"""

import numpy as np

try:
    import galsim
    HAS_GALSIM = True
except ImportError:
    HAS_GALSIM = False

# Check for LSST stack (only available on RSP)
try:
    from lsst.afw.image import Image as afwImage
    from lsst.afw.math import Warper
    HAS_LSST = True
except ImportError:
    HAS_LSST = False


def get_psf_from_coadd(exposure, position):
    """
    Extract the PSF from a Rubin coadd at a specific position.
    
    This must be run on the Rubin Science Platform where the LSST stack is available.
    
    Parameters:
    -----------
    exposure : lsst.afw.image.ExposureF
        The coadd exposure from Butler
    position : lsst.geom.Point2D
        Position in pixel coordinates where to evaluate the PSF
    
    Returns:
    --------
    psf_image : ndarray
        2D PSF image at the specified position
    """
    if not HAS_LSST:
        raise RuntimeError("LSST stack not available. Run this on the Rubin Science Platform.")
    
    # Get the PSF model from the exposure
    psf_model = exposure.getPsf()
    
    # Compute the PSF image at the given position
    psf_image = psf_model.computeImage(position)
    
    # Convert to numpy array
    psf_array = psf_image.array.copy()
    
    # Normalize to sum to 1
    psf_array = psf_array / np.sum(psf_array)
    
    return psf_array


def get_psf_fwhm_from_coadd(exposure, position):
    """
    Get the PSF FWHM from a Rubin coadd at a specific position.
    
    Parameters:
    -----------
    exposure : lsst.afw.image.ExposureF
        The coadd exposure
    position : lsst.geom.Point2D
        Position in pixel coordinates
    
    Returns:
    --------
    fwhm : float
        PSF FWHM in pixels
    """
    if not HAS_LSST:
        raise RuntimeError("LSST stack not available. Run this on the Rubin Science Platform.")
    
    psf_model = exposure.getPsf()
    shape = psf_model.computeShape(position)
    
    # Convert second moments to FWHM
    # FWHM ≈ 2.355 * sigma, and sigma = sqrt(trace/2) for circular PSF
    sigma = np.sqrt(shape.getTraceRadius())
    fwhm = 2.355 * sigma
    
    return fwhm


def convolve_with_coadd_psf(image, exposure, position):
    """
    Convolve an image with the actual PSF from a Rubin coadd.
    
    Parameters:
    -----------
    image : ndarray
        Input 2D image to convolve
    exposure : lsst.afw.image.ExposureF
        The coadd exposure containing the PSF model
    position : lsst.geom.Point2D
        Position where to evaluate the PSF
    
    Returns:
    --------
    convolved : ndarray
        Convolved image
    """
    # Get the actual PSF at this position
    psf_array = get_psf_from_coadd(exposure, position)
    
    # Use GalSim for the convolution
    if HAS_GALSIM:
        return _convolve_galsim_with_psf_image(image, psf_array)
    else:
        return _convolve_fft(image, psf_array)


def _convolve_galsim_with_psf_image(image, psf_array):
    """Convolve using GalSim with a PSF image array."""
    ny, nx = image.shape
    pixel_scale = 1.0
    
    # Create GalSim objects
    gal_image = galsim.Image(image, scale=pixel_scale)
    psf_image = galsim.Image(psf_array, scale=pixel_scale)
    
    intrinsic = galsim.InterpolatedImage(gal_image, scale=pixel_scale)
    psf = galsim.InterpolatedImage(psf_image, scale=pixel_scale)
    
    # Convolve
    convolved = galsim.Convolve([intrinsic, psf])
    
    # Draw result
    result_image = galsim.Image(nx, ny, scale=pixel_scale)
    convolved.drawImage(image=result_image, scale=pixel_scale)
    
    return result_image.array


def _convolve_fft(image, psf_array):
    """Convolve using FFT (fallback method)."""
    from scipy.signal import fftconvolve
    
    # Pad PSF to avoid edge effects
    convolved = fftconvolve(image, psf_array, mode='same')
    return convolved


def create_rubin_psf(fwhm_pixels, shape, pixel_scale=1.0):
    """
    Create a Rubin-like PSF image.
    
    Parameters:
    -----------
    fwhm_pixels : float
        PSF FWHM in pixels
    shape : tuple
        Output image shape (ny, nx)
    pixel_scale : float
        Pixel scale (only used for GalSim internals, can be 1.0 for pixel units)
    
    Returns:
    --------
    psf_image : ndarray
        2D PSF image normalized to sum to 1
    """
    if not HAS_GALSIM:
        # Fallback to simple Gaussian if GalSim not available
        return _gaussian_psf(fwhm_pixels, shape)
    
    ny, nx = shape
    
    # Rubin PSF is well-approximated by a Kolmogorov profile for atmospheric seeing
    # plus an optical component. For simplicity, use a Moffat profile which is
    # commonly used to model ground-based PSFs.
    # Moffat beta ~ 4.765 approximates a Kolmogorov profile
    
    fwhm_arcsec = fwhm_pixels * pixel_scale
    
    # Create Moffat PSF (good approximation for ground-based seeing)
    psf = galsim.Moffat(fwhm=fwhm_arcsec, beta=4.765)
    
    # Draw the PSF image
    psf_image = galsim.Image(nx, ny, scale=pixel_scale)
    psf.drawImage(image=psf_image, scale=pixel_scale)
    
    # Normalize
    psf_array = psf_image.array
    psf_array = psf_array / np.sum(psf_array)
    
    return psf_array


def _gaussian_psf(fwhm_pixels, shape):
    """Fallback Gaussian PSF if GalSim not available."""
    ny, nx = shape
    sigma = fwhm_pixels / 2.355  # FWHM to sigma
    
    y, x = np.ogrid[:ny, :nx]
    cy, cx = ny // 2, nx // 2
    r2 = (x - cx)**2 + (y - cy)**2
    
    psf = np.exp(-r2 / (2 * sigma**2))
    return psf / np.sum(psf)


def convolve_with_psf(image, fwhm, psf_type='moffat', beta=4.765):
    """
    Convolve an image with a PSF using GalSim.
    
    Parameters:
    -----------
    image : ndarray
        Input 2D image to convolve
    fwhm : float
        PSF FWHM in pixels
    psf_type : str
        Type of PSF: 'moffat', 'gaussian', or 'kolmogorov'
    beta : float
        Moffat beta parameter (only used if psf_type='moffat')
    
    Returns:
    --------
    convolved : ndarray
        Convolved image with same shape as input
    """
    if not HAS_GALSIM:
        # Fallback to scipy convolution
        return _convolve_scipy(image, fwhm)
    
    ny, nx = image.shape
    pixel_scale = 1.0  # Work in pixel units
    
    # Create the PSF
    if psf_type == 'moffat':
        psf = galsim.Moffat(fwhm=fwhm * pixel_scale, beta=beta)
    elif psf_type == 'gaussian':
        psf = galsim.Gaussian(fwhm=fwhm * pixel_scale)
    elif psf_type == 'kolmogorov':
        psf = galsim.Kolmogorov(fwhm=fwhm * pixel_scale)
    else:
        raise ValueError(f"Unknown PSF type: {psf_type}")
    
    # Create GalSim image from numpy array
    gal_image = galsim.Image(image, scale=pixel_scale)
    
    # Create an InterpolatedImage from the input
    intrinsic = galsim.InterpolatedImage(gal_image, scale=pixel_scale)
    
    # Convolve
    convolved = galsim.Convolve([intrinsic, psf])
    
    # Draw the result
    result_image = galsim.Image(nx, ny, scale=pixel_scale)
    convolved.drawImage(image=result_image, scale=pixel_scale)
    
    return result_image.array


def _convolve_scipy(image, fwhm):
    """Fallback convolution using scipy if GalSim not available."""
    from scipy.ndimage import gaussian_filter
    sigma = fwhm / 2.355
    return gaussian_filter(image, sigma=sigma)


def create_composite_rubin_psf(fwhm_atm, fwhm_opt, shape, pixel_scale=1.0):
    """
    Create a more realistic Rubin PSF with atmospheric and optical components.
    
    Parameters:
    -----------
    fwhm_atm : float
        Atmospheric seeing FWHM in pixels
    fwhm_opt : float
        Optical PSF FWHM in pixels (typically ~0.4" for Rubin)
    shape : tuple
        Output image shape
    pixel_scale : float
        Pixel scale
    
    Returns:
    --------
    psf_image : ndarray
        Combined PSF image
    """
    if not HAS_GALSIM:
        # Simple approximation: add in quadrature
        fwhm_total = np.sqrt(fwhm_atm**2 + fwhm_opt**2)
        return _gaussian_psf(fwhm_total, shape)
    
    ny, nx = shape
    
    # Atmospheric component (Kolmogorov)
    atm = galsim.Kolmogorov(fwhm=fwhm_atm * pixel_scale)
    
    # Optical component (Gaussian approximation)
    opt = galsim.Gaussian(fwhm=fwhm_opt * pixel_scale)
    
    # Combine
    psf = galsim.Convolve([atm, opt])
    
    # Draw
    psf_image = galsim.Image(nx, ny, scale=pixel_scale)
    psf.drawImage(image=psf_image, scale=pixel_scale)
    
    psf_array = psf_image.array
    return psf_array / np.sum(psf_array)
