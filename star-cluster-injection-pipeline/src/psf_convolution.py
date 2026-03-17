"""
PSF extraction and convolution utilities for Rubin coadd images.

The deepCoadd PSF is spatially varying — you must evaluate it at a specific
pixel position using exposure.getPsf().computeImage(Point2D(x, y)).
"""

import numpy as np
from scipy.signal import fftconvolve


def get_psf_from_coadd(exposure, position):
    """
    Extract the PSF kernel image from a Rubin deepCoadd at a given position.

    Parameters
    ----------
    exposure : lsst.afw.image.ExposureF
        The deepCoadd exposure loaded via Butler.
    position : lsst.geom.Point2D
        Pixel position at which to evaluate the PSF.

    Returns
    -------
    psf_array : np.ndarray
        2D PSF kernel image, normalized to sum=1.
    """
    psf_obj = exposure.getPsf()
    if psf_obj is None:
        raise RuntimeError("Exposure has no PSF model attached.")

    # computeImage returns an afw Image at the given position
    psf_image = psf_obj.computeImage(position)
    psf_array = psf_image.array.copy().astype(np.float64)

    # Normalize so the PSF sums to 1 (flux-preserving convolution)
    total = psf_array.sum()
    if total > 0:
        psf_array /= total

    return psf_array


def get_psf_fwhm_from_coadd(exposure, position):
    """
    Compute the PSF FWHM in pixels from a Rubin deepCoadd at a given position.

    Uses computeShape() which returns adaptive moments (Ixx, Iyy, Ixy).
    FWHM ≈ 2.355 * sigma, where sigma = sqrt((Ixx + Iyy) / 2).

    Parameters
    ----------
    exposure : lsst.afw.image.ExposureF
    position : lsst.geom.Point2D

    Returns
    -------
    fwhm_pixels : float
    """
    psf_obj = exposure.getPsf()
    if psf_obj is None:
        raise RuntimeError("Exposure has no PSF model attached.")

    shape = psf_obj.computeShape(position)
    # Adaptive second moments
    ixx = shape.getIxx()
    iyy = shape.getIyy()
    sigma = np.sqrt((ixx + iyy) / 2.0)
    fwhm = 2.355 * sigma
    return fwhm


def get_psf_size_from_coadd(exposure, position):
    """
    Return detailed PSF shape information at a position.

    Returns
    -------
    info : dict with keys 'fwhm_px', 'fwhm_arcsec', 'sigma_px',
           'ixx', 'iyy', 'ixy', 'ellipticity', 'kernel_shape'
    """
    psf_obj = exposure.getPsf()
    shape = psf_obj.computeShape(position)
    psf_image = psf_obj.computeImage(position)

    ixx = shape.getIxx()
    iyy = shape.getIyy()
    ixy = shape.getIxy()
    sigma = np.sqrt((ixx + iyy) / 2.0)
    fwhm_px = 2.355 * sigma

    # Ellipticity from moments
    e1 = (ixx - iyy) / (ixx + iyy) if (ixx + iyy) > 0 else 0.0
    e2 = 2.0 * ixy / (ixx + iyy) if (ixx + iyy) > 0 else 0.0
    ellipticity = np.sqrt(e1**2 + e2**2)

    return {
        'fwhm_px': fwhm_px,
        'fwhm_arcsec': fwhm_px * 0.2,  # Rubin pixel scale
        'sigma_px': sigma,
        'ixx': ixx,
        'iyy': iyy,
        'ixy': ixy,
        'ellipticity': ellipticity,
        'kernel_shape': psf_image.array.shape,
    }


def convolve_with_psf(cluster_stamp, psf_kernel, mode='same'):
    """
    Convolve a 2D cluster stamp with a PSF kernel using FFT convolution.

    Parameters
    ----------
    cluster_stamp : np.ndarray
        2D array of the synthetic cluster (before PSF smearing).
    psf_kernel : np.ndarray
        2D PSF kernel (should be normalized to sum=1).
    mode : str
        'same' to return array of same shape as cluster_stamp.

    Returns
    -------
    convolved : np.ndarray
    """
    # Ensure both are float64 for precision
    stamp = np.asarray(cluster_stamp, dtype=np.float64)
    kernel = np.asarray(psf_kernel, dtype=np.float64)

    # Re-normalize kernel just in case
    ksum = kernel.sum()
    if ksum > 0:
        kernel = kernel / ksum

    convolved = fftconvolve(stamp, kernel, mode=mode)
    return convolved


def sample_psf_across_image(exposure, n_samples=9):
    """
    Sample the PSF at a grid of positions across the image to show
    spatial variation. Useful for diagnostics.

    Parameters
    ----------
    exposure : lsst.afw.image.ExposureF
    n_samples : int
        Total number of sample points (will be sqrt(n) x sqrt(n) grid).

    Returns
    -------
    samples : list of dict, each with 'x', 'y', 'fwhm_px', 'psf_array'
    """
    from lsst.geom import Point2D

    ny, nx = exposure.image.array.shape
    n_side = int(np.ceil(np.sqrt(n_samples)))
    margin = 100  # stay away from edges

    xs = np.linspace(margin, nx - margin, n_side)
    ys = np.linspace(margin, ny - margin, n_side)

    samples = []
    for y in ys:
        for x in xs:
            pos = Point2D(float(x), float(y))
            try:
                psf_arr = get_psf_from_coadd(exposure, pos)
                fwhm = get_psf_fwhm_from_coadd(exposure, pos)
                samples.append({
                    'x': float(x), 'y': float(y),
                    'fwhm_px': fwhm,
                    'psf_array': psf_arr,
                })
            except Exception as e:
                print(f"  PSF sample failed at ({x:.0f}, {y:.0f}): {e}")

    return samples
