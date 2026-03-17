"""
PSF convolution module following Rubin Observatory practices.

Reference: https://pipelines.lsst.io/modules/lsst.source.injection/
"""

import numpy as np

try:
    import galsim
    HAS_GALSIM = True
except ImportError:
    HAS_GALSIM = False

try:
    from lsst.afw.image import Image as afwImage
    from lsst.geom import Point2D
    HAS_LSST = True
    
    # Import the PSF error type
    try:
        from lsst.meas.algorithms import CoaddPsf
        from lsst.pex.exceptions import InvalidParameterError
        HAS_LSST = True
    except (ImportError, AttributeError, Exception):
        CoaddPsf = None
        InvalidParameterError = Exception
        HAS_LSST = False
except ImportError:
    HAS_LSST = False


def get_psf_from_coadd(exposure, position, fallback_fwhm=3.5):
    """
    Extract PSF from a Rubin coadd at a specific position.

    Following DP02_12a_PSF_Data_Products tutorial:
      psf = calexp.getPsf()
      psfImg = psf.computeImage(coord)   # PSF image centered at 'coord'
      array = psfImg.array / psfImg.array.sum()

    Parameters:
    -----------
    exposure : lsst.afw.image.ExposureF
    position : lsst.geom.Point2D
    fallback_fwhm : float

    Returns:
    --------
    psf_array : ndarray  (normalized)
    """
    if not HAS_LSST:
        return _gaussian_psf(fallback_fwhm, (41, 41))

    psf = exposure.getPsf()

    try:
        # computeImage returns a PSF image centered at the given pixel position
        # (this is what the DP0.2 PSF tutorial uses)
        psf_image = psf.computeImage(position)
        psf_array = psf_image.array.copy()

    except Exception as e:
        print(f"Warning: PSF unavailable at ({position.getX():.0f}, {position.getY():.0f}): {e}")

        valid_pos = _find_valid_psf_position(exposure, position)
        if valid_pos is not None:
            print(f"  Using PSF from ({valid_pos.getX():.0f}, {valid_pos.getY():.0f})")
            psf_image = psf.computeImage(valid_pos)
            psf_array = psf_image.array.copy()
        else:
            print(f"  Using fallback Gaussian (FWHM={fallback_fwhm})")
            return _gaussian_psf(fallback_fwhm, (41, 41))

    # Normalize (tutorial: array / array.sum())
    psf_array = psf_array / np.sum(psf_array)
    return psf_array


def _find_valid_psf_position(exposure, position, max_radius=200):
    """Search for a nearby position where PSF can be computed."""
    if not HAS_LSST:
        return None

    psf = exposure.getPsf()
    x, y = position.getX(), position.getY()

    for radius in range(10, max_radius, 20):
        for angle in np.linspace(0, 2*np.pi, 8, endpoint=False):
            test_x = x + radius * np.cos(angle)
            test_y = y + radius * np.sin(angle)
            test_pos = Point2D(test_x, test_y)
            try:
                psf.computeImage(test_pos)
                return test_pos
            except:
                continue

    return None


def get_psf_fwhm_from_coadd(exposure, position, fallback_fwhm=3.5):
    """
    Get PSF FWHM at a position.

    Following DP02_12a_PSF_Data_Products tutorial:
      shape = psf.computeShape(coord)
      sigma = shape.getDeterminantRadius()   # <-- tutorial uses getDeterminantRadius
      fwhm  = sigma * 2 * sqrt(2 * ln(2))   # = sigma * 2.355

    Parameters:
    -----------
    exposure : lsst.afw.image.ExposureF
    position : lsst.geom.Point2D
    fallback_fwhm : float

    Returns:
    --------
    fwhm : float  (pixels)
    """
    if not HAS_LSST:
        return fallback_fwhm

    try:
        psf = exposure.getPsf()
        shape = psf.computeShape(position)
        # getDeterminantRadius = (Ixx*Iyy - Ixy^2)^(1/4), the correct
        # effective sigma for a 2-D Gaussian (used in the DP0.2 PSF tutorial)
        sigma = shape.getDeterminantRadius()
        fwhm  = sigma * 2.0 * np.sqrt(2.0 * np.log(2.0))   # ≈ 2.355 * sigma
        return float(fwhm)
    except Exception as e:
        print(f"Warning: could not compute PSF FWHM: {e}")
        return fallback_fwhm


def convolve_with_coadd_psf(image, exposure, position, fallback_fwhm=3.5):
    """
    Convolve image with actual PSF from coadd.
    
    Parameters:
    -----------
    image : ndarray
        Input image
    exposure : lsst.afw.image.ExposureF
        Coadd exposure
    position : lsst.geom.Point2D
        Position for PSF evaluation
    fallback_fwhm : float
        Fallback FWHM if PSF unavailable
    
    Returns:
    --------
    convolved : ndarray
        Convolved image
    """
    psf_array = get_psf_from_coadd(exposure, position, fallback_fwhm)
    
    if HAS_GALSIM:
        return _convolve_galsim(image, psf_array)
    else:
        return _convolve_fft(image, psf_array)


def _convolve_galsim(image, psf_array):
    """Convolve using GalSim."""
    ny, nx = image.shape
    pixel_scale = 1.0
    
    gal_image = galsim.Image(image, scale=pixel_scale)
    psf_image = galsim.Image(psf_array, scale=pixel_scale)
    
    source = galsim.InterpolatedImage(gal_image, scale=pixel_scale)
    psf = galsim.InterpolatedImage(psf_image, scale=pixel_scale)
    
    convolved = galsim.Convolve([source, psf])
    
    result = galsim.Image(nx, ny, scale=pixel_scale)
    convolved.drawImage(image=result, scale=pixel_scale)
    
    return result.array


def _convolve_fft(image, psf_array):
    """Convolve using FFT."""
    from scipy.signal import fftconvolve
    return fftconvolve(image, psf_array, mode='same')


def _gaussian_psf(fwhm, shape):
    """Create Gaussian PSF."""
    ny, nx = shape
    sigma = fwhm / 2.355
    y, x = np.ogrid[:ny, :nx]
    cy, cx = ny // 2, nx // 2
    r2 = (x - cx)**2 + (y - cy)**2
    psf = np.exp(-r2 / (2 * sigma**2))
    return psf / np.sum(psf)


def convolve_with_psf(image, fwhm, psf_type='moffat', beta=4.765):
    """
    Convolve with a generic PSF model.
    
    Parameters:
    -----------
    image : ndarray
        Input image
    fwhm : float
        PSF FWHM in pixels
    psf_type : str
        'moffat', 'gaussian', or 'kolmogorov'
    beta : float
        Moffat beta parameter
    
    Returns:
    --------
    convolved : ndarray
        Convolved image
    """
    if not HAS_GALSIM:
        from scipy.ndimage import gaussian_filter
        sigma = fwhm / 2.355
        return gaussian_filter(image, sigma=sigma)
    
    ny, nx = image.shape
    pixel_scale = 1.0
    
    if psf_type == 'moffat':
        psf = galsim.Moffat(fwhm=fwhm, beta=beta)
    elif psf_type == 'gaussian':
        psf = galsim.Gaussian(fwhm=fwhm)
    elif psf_type == 'kolmogorov':
        psf = galsim.Kolmogorov(fwhm=fwhm)
    else:
        raise ValueError(f"Unknown PSF type: {psf_type}")
    
    gal_image = galsim.Image(image, scale=pixel_scale)
    source = galsim.InterpolatedImage(gal_image, scale=pixel_scale)
    
    convolved = galsim.Convolve([source, psf])
    
    result = galsim.Image(nx, ny, scale=pixel_scale)
    convolved.drawImage(image=result, scale=pixel_scale)
    
    return result.array


def create_rubin_psf(fwhm_pixels, shape, pixel_scale=1.0):
    """
    Create a Rubin-like PSF (Moffat profile).
    
    Parameters:
    -----------
    fwhm_pixels : float
        FWHM in pixels
    shape : tuple
        Output shape (ny, nx)
    pixel_scale : float
        Pixel scale
    
    Returns:
    --------
    psf : ndarray
        Normalized PSF image
    """
    if not HAS_GALSIM:
        return _gaussian_psf(fwhm_pixels, shape)
    
    ny, nx = shape
    psf = galsim.Moffat(fwhm=fwhm_pixels, beta=4.765)
    
    psf_image = galsim.Image(nx, ny, scale=pixel_scale)
    psf.drawImage(image=psf_image, scale=pixel_scale)
    
    psf_array = psf_image.array
    return psf_array / np.sum(psf_array)


# Backwards compatibility
def is_position_valid_for_psf(exposure, position):
    """Check if PSF can be computed at position."""
    if not HAS_LSST:
        return True
    try:
        exposure.getPsf().computeKernelImage(position)
        return True
    except:
        return False


def get_valid_psf_region(exposure):
    """Get approximate valid region for PSF computation."""
    if not HAS_LSST:
        return None
    
    from lsst.geom import Box2I, Point2I, Extent2I
    
    bbox = exposure.getBBox()
    margin = 100
    
    return Box2I(
        Point2I(bbox.getMinX() + margin, bbox.getMinY() + margin),
        Extent2I(bbox.getWidth() - 2*margin, bbox.getHeight() - 2*margin)
    )
