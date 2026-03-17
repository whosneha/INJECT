"""
Detection pipeline for star clusters in Rubin coadd images.

Implements methods from:

1. Matched-filter + threshold detection
   Saifollahi et al. 2025 (A&A 697, A10) - injection into Euclid data
   https://scixplorer.org/abs/2025A%26A...697A..10S/abstract

2. Multiple Concentration Index (MCI) for extended source selection
   Thilker et al. 2022 (MNRAS 509, 4094) - PHANGS-HST cluster detection
   https://scixplorer.org/abs/2022MNRAS.509.4094T/abstract

3. Completeness modeling framework
   Hannon et al. 2024 (AJ 168, 38) - neural network completeness
   https://scixplorer.org/abs/2024AJ....168...38H/abstract

The pipeline is designed as a SANDWICH between:
    inject_from_catalog()  →  [this module]  →  ClusterRetrieval()

Detection catalog output format is compatible with ClusterRetrieval.
"""

import numpy as np
from scipy.ndimage import gaussian_filter, label, center_of_mass
from scipy.signal import fftconvolve
from typing import List, Dict, Tuple, Optional


# =============================================================================
# STEP 1: BACKGROUND ESTIMATION
# Saifollahi+2025: use a running median with sigma clipping
# =============================================================================

def estimate_background(image: np.ndarray,
                        box_size: int = 64,
                        sigma_clip: float = 3.0,
                        n_iter: int = 3) -> Tuple[np.ndarray, np.ndarray]:
    """
    Estimate background and RMS map using a sliding box median.

    Following Saifollahi+2025: background is estimated in boxes
    with sigma clipping to reject sources.

    Parameters:
    -----------
    image : ndarray
        Input image
    box_size : int
        Size of background estimation box in pixels
    sigma_clip : float
        Sigma clipping threshold
    n_iter : int
        Number of sigma clipping iterations

    Returns:
    --------
    background : ndarray
        Background map (same shape as image)
    rms : ndarray
        RMS noise map (same shape as image)
    """
    ny, nx = image.shape
    n_boxes_y = max(1, ny // box_size)
    n_boxes_x = max(1, nx // box_size)

    bg_grid  = np.zeros((n_boxes_y, n_boxes_x))
    rms_grid = np.zeros((n_boxes_y, n_boxes_x))

    for i in range(n_boxes_y):
        for j in range(n_boxes_x):
            y0 = i * box_size
            y1 = min((i + 1) * box_size, ny)
            x0 = j * box_size
            x1 = min((j + 1) * box_size, nx)

            box = image[y0:y1, x0:x1].flatten()

            # Iterative sigma clipping
            for _ in range(n_iter):
                med = np.median(box)
                std = np.std(box)
                box = box[np.abs(box - med) < sigma_clip * std]

            bg_grid[i, j]  = np.median(box) if len(box) > 0 else np.median(image[y0:y1, x0:x1])
            rms_grid[i, j] = np.std(box)    if len(box) > 0 else np.std(image[y0:y1, x0:x1])

    # Interpolate back to full image size
    from scipy.ndimage import zoom
    scale_y = ny / n_boxes_y
    scale_x = nx / n_boxes_x
    background = zoom(bg_grid,  (scale_y, scale_x), order=1)[:ny, :nx]
    rms        = zoom(rms_grid, (scale_y, scale_x), order=1)[:ny, :nx]

    # Clip to avoid negative RMS
    rms = np.maximum(rms, 1e-10)

    return background, rms


# =============================================================================
# STEP 2: MATCHED-FILTER DETECTION
# Saifollahi+2025: convolve with cluster-shaped kernel before thresholding
# This boosts extended sources while suppressing point sources and noise
# =============================================================================

def matched_filter_detect(image: np.ndarray,
                          background: np.ndarray,
                          rms: np.ndarray,
                          r_half_pixels: float = 5.0,
                          threshold_sigma: float = 3.0,
                          min_area: int = 3,
                          kernel_type: str = 'plummer') -> Tuple[np.ndarray, np.ndarray]:
    """
    Detect sources using matched-filter convolution.

    From Saifollahi+2025: convolve the background-subtracted image with a
    kernel that matches the expected cluster profile. This enhances the
    signal of extended sources relative to point sources and noise.

    Parameters:
    -----------
    image : ndarray
        Input image
    background : ndarray
        Background map
    rms : ndarray
        RMS noise map
    r_half_pixels : float
        Expected cluster half-light radius in pixels (sets kernel size)
    threshold_sigma : float
        Detection threshold in sigma
    min_area : int
        Minimum number of connected pixels above threshold
    kernel_type : str
        Kernel shape: 'plummer', 'gaussian', 'tophat'

    Returns:
    --------
    snr_map : ndarray
        S/N map after matched filtering
    detection_map : ndarray (bool)
        Boolean map of detections
    """
    # Background subtract
    bkg_sub = image - background

    # Build matched filter kernel
    kernel = _make_kernel(r_half_pixels, kernel_type)

    # Convolve image and noise separately
    # S/N = (image * kernel) / sqrt(noise^2 * kernel^2)
    smoothed_signal = fftconvolve(bkg_sub, kernel, mode='same')
    smoothed_var    = fftconvolve(rms**2,  kernel**2, mode='same')
    snr_map = smoothed_signal / np.sqrt(np.maximum(smoothed_var, 1e-20))

    # Threshold
    detection_map = snr_map > threshold_sigma

    # Remove small regions
    labeled, n = label(detection_map)
    for i in range(1, n + 1):
        if np.sum(labeled == i) < min_area:
            detection_map[labeled == i] = False

    return snr_map, detection_map


def _make_kernel(r_half: float, kernel_type: str = 'plummer',
                 size: int = None) -> np.ndarray:
    """Build a matched filter kernel."""
    if size is None:
        size = max(11, int(6 * r_half) | 1)  # odd size

    cy, cx = size // 2, size // 2
    y, x = np.ogrid[:size, :size]
    r = np.sqrt((x - cx)**2 + (y - cy)**2)

    if kernel_type == 'plummer':
        a = r_half / np.sqrt(np.sqrt(2) - 1)
        kernel = (1 + (r / a)**2)**(-2)
    elif kernel_type == 'gaussian':
        sigma = r_half / 1.1774  # FWHM/2.355 where FWHM=r_half*2*sqrt(2ln2/2)
        kernel = np.exp(-r**2 / (2 * sigma**2))
    elif kernel_type == 'tophat':
        kernel = (r <= r_half).astype(float)
    else:
        raise ValueError(f"Unknown kernel type: {kernel_type}")

    kernel /= kernel.sum()
    return kernel


# =============================================================================
# STEP 3: SOURCE EXTRACTION FROM DETECTION MAP
# Extract centroids, fluxes, shapes from connected regions
# =============================================================================

def extract_sources(image: np.ndarray,
                    background: np.ndarray,
                    snr_map: np.ndarray,
                    detection_map: np.ndarray,
                    pixel_scale: float = 0.2) -> List[Dict]:
    """
    Extract source properties from the detection map.

    Parameters:
    -----------
    image : ndarray
        Original image
    background : ndarray
        Background map
    snr_map : ndarray
        S/N map from matched filtering
    detection_map : ndarray (bool)
        Detection footprint map
    pixel_scale : float
        Arcsec/pixel (for size conversion)

    Returns:
    --------
    sources : list of dict
        Source catalog compatible with ClusterRetrieval
    """
    bkg_sub = image - background
    labeled, n_sources = label(detection_map)
    sources = []

    for i in range(1, n_sources + 1):
        mask = labeled == i

        # Flux-weighted centroid
        flux_map = np.maximum(bkg_sub * mask, 0)
        total_flux = float(np.sum(flux_map))

        if total_flux <= 0:
            continue

        y_coords, x_coords = np.where(mask)
        weights = np.maximum(bkg_sub[mask], 0)

        if weights.sum() > 0:
            x_cent = float(np.average(x_coords, weights=weights))
            y_cent = float(np.average(y_coords, weights=weights))
        else:
            x_cent = float(np.mean(x_coords))
            y_cent = float(np.mean(y_coords))

        # Peak S/N
        peak_snr = float(np.max(snr_map[mask]))

        # Area and approximate r_half
        area = int(np.sum(mask))
        r_half_approx = float(np.sqrt(area / np.pi))

        # Second moments for shape
        ixx, iyy, ixy = _second_moments(bkg_sub, mask, x_cent, y_cent)
        trace_radius = float(np.sqrt((ixx + iyy) / 2)) if (ixx + iyy) > 0 else r_half_approx
        ellipticity = _ellipticity_from_moments(ixx, iyy, ixy)

        source = {
            'x':           x_cent,
            'y':           y_cent,
            'flux':        total_flux,
            'area':        area,
            'snr':         peak_snr,
            'r_half':      trace_radius,
            'ellipticity': ellipticity,
            'ixx':         ixx,
            'iyy':         iyy,
            'ixy':         ixy,
            'flag':        0,
        }

        sources.append(source)

    return sources


def _second_moments(image, mask, x_cent, y_cent):
    """Compute second moments of a source."""
    y_coords, x_coords = np.where(mask)
    weights = np.maximum(image[mask], 0)
    w_sum = weights.sum()

    if w_sum <= 0:
        return 0.0, 0.0, 0.0

    ixx = float(np.sum(weights * (x_coords - x_cent)**2) / w_sum)
    iyy = float(np.sum(weights * (y_coords - y_cent)**2) / w_sum)
    ixy = float(np.sum(weights * (x_coords - x_cent) * (y_coords - y_cent)) / w_sum)
    return ixx, iyy, ixy


def _ellipticity_from_moments(ixx, iyy, ixy):
    """Compute ellipticity from second moments."""
    if ixx + iyy <= 0:
        return 0.0
    q = np.sqrt(max(0, (ixx - iyy)**2 + 4 * ixy**2))
    a2 = (ixx + iyy + q) / 2
    b2 = (ixx + iyy - q) / 2
    if a2 <= 0:
        return 0.0
    return float(1 - np.sqrt(max(0, b2 / a2)))


# =============================================================================
# STEP 4: MULTIPLE CONCENTRATION INDEX (MCI)
# Thilker+2022 (PHANGS-HST): discriminate clusters from stars using
# the ratio of flux in an inner vs outer aperture
# A point source has MCI ~ 1, an extended source has MCI < 1
# =============================================================================

def compute_mci(image: np.ndarray,
                sources: List[Dict],
                inner_radius: float = 1.0,
                outer_radius: float = 3.0) -> List[Dict]:
    """
    Compute Multiple Concentration Index for each source.

    From Thilker+2022 (PHANGS-HST):
    MCI = flux(inner_aperture) / flux(outer_aperture)

    Point sources: MCI close to 1 (most flux in centre)
    Extended sources: MCI < 1 (flux spread to outer aperture)

    We compute two MCIs:
    - inner_MCI: r=1px vs r=3px  (probes core concentration)
    - outer_MCI: r=3px vs r=8px  (probes envelope)

    Parameters:
    -----------
    image : ndarray
        Background-subtracted image
    sources : list of dict
        Source catalog
    inner_radius : float
        Inner aperture radius in pixels
    outer_radius : float
        Outer aperture radius in pixels

    Returns:
    --------
    sources : list of dict
        Updated with 'mci', 'inner_mci', 'outer_mci' keys
    """
    ny, nx = image.shape
    y_grid, x_grid = np.ogrid[:ny, :nx]

    for src in sources:
        cx, cy = src['x'], src['y']
        r_grid = np.sqrt((x_grid - cx)**2 + (y_grid - cy)**2)

        # Three apertures: 1px, 3px, 8px (Thilker+2022 uses 1,3,8 PHANGS pixels)
        # Scale by PSF FWHM in practice
        flux_1 = float(np.sum(image[r_grid <= inner_radius]))
        flux_3 = float(np.sum(image[r_grid <= outer_radius]))
        flux_8 = float(np.sum(image[r_grid <= outer_radius * 2.67]))

        # Inner MCI: how concentrated is the source in the core
        src['inner_mci'] = flux_1 / flux_3  if flux_3 > 0 else 0.0

        # Outer MCI: how much flux is in the envelope
        src['outer_mci'] = flux_3 / flux_8  if flux_8 > 0 else 0.0

        # Combined MCI
        src['mci'] = src['inner_mci'] * src['outer_mci']

    return sources


def select_cluster_candidates(sources: List[Dict],
                               mci_max: float = 0.9,
                               snr_min: float = 3.0,
                               r_half_min: float = 1.0,
                               ellipticity_max: float = 0.5,
                               flag_max: int = 0) -> List[Dict]:
    """
    Select cluster candidates based on MCI and morphology cuts.

    Following Thilker+2022: clusters are extended, so MCI < point_source_MCI.
    Following Saifollahi+2025: apply S/N, size, and shape cuts.

    Parameters:
    -----------
    sources : list of dict
        Source catalog with MCI values
    mci_max : float
        Maximum MCI (lower = more extended = more cluster-like)
        Typical point source MCI ~ 1.0, cluster MCI ~ 0.3-0.8
    snr_min : float
        Minimum detection S/N
    r_half_min : float
        Minimum half-light radius in pixels
    ellipticity_max : float
        Maximum ellipticity (reject highly elongated = artifacts)
    flag_max : int
        Maximum quality flag value

    Returns:
    --------
    candidates : list of dict
    """
    candidates = []
    for src in sources:
        if src.get('snr', 0)         < snr_min:        continue
        if src.get('r_half', 0)      < r_half_min:     continue
        if src.get('ellipticity', 1) > ellipticity_max: continue
        if src.get('flag', 0)        > flag_max:        continue
        if src.get('inner_mci', 1)   > mci_max:        continue
        candidates.append(src)
    return candidates


# =============================================================================
# STEP 5: MULTI-SCALE DETECTION
# Run detection at multiple cluster size scales and merge
# Saifollahi+2025: important for detecting clusters of varying sizes
# =============================================================================

def multiscale_detect(image: np.ndarray,
                      background: np.ndarray,
                      rms: np.ndarray,
                      r_half_scales: List[float] = None,
                      threshold_sigma: float = 3.0,
                      pixel_scale: float = 0.2) -> List[Dict]:
    """
    Run matched-filter detection at multiple cluster size scales.

    Saifollahi+2025 runs detection at multiple scales to capture both
    compact and extended clusters. Sources detected at different scales
    are merged by position.

    Parameters:
    -----------
    image : ndarray
        Input image
    background : ndarray
        Background map
    rms : ndarray
        RMS noise map
    r_half_scales : list of float
        Half-light radii in pixels to try. Default: [2, 5, 10, 20]
    threshold_sigma : float
        Detection threshold
    pixel_scale : float
        Arcsec/pixel

    Returns:
    --------
    sources : list of dict
        Merged multi-scale source catalog
    """
    if r_half_scales is None:
        r_half_scales = [2.0, 5.0, 10.0, 20.0]

    all_sources = []

    for r_half in r_half_scales:
        snr_map, det_map = matched_filter_detect(
            image, background, rms,
            r_half_pixels=r_half,
            threshold_sigma=threshold_sigma
        )
        sources = extract_sources(image, background, snr_map, det_map, pixel_scale)
        for src in sources:
            src['detection_scale'] = r_half
        all_sources.extend(sources)

    # Merge sources detected at multiple scales (within 5px of each other)
    merged = _merge_sources(all_sources, merge_radius=5.0)
    return merged


def _merge_sources(sources: List[Dict], merge_radius: float = 5.0) -> List[Dict]:
    """Merge sources within merge_radius pixels of each other."""
    if not sources:
        return []

    used = np.zeros(len(sources), dtype=bool)
    merged = []

    # Sort by S/N descending
    sources = sorted(sources, key=lambda s: s.get('snr', 0), reverse=True)

    for i, src in enumerate(sources):
        if used[i]:
            continue
        used[i] = True

        # Find all sources within merge_radius
        group = [src]
        for j, other in enumerate(sources):
            if used[j]:
                continue
            dx = src['x'] - other['x']
            dy = src['y'] - other['y']
            if np.sqrt(dx**2 + dy**2) < merge_radius:
                group.append(other)
                used[j] = True

        # Take the highest S/N source from each group
        best = max(group, key=lambda s: s.get('snr', 0))
        merged.append(best)

    return merged


# =============================================================================
# MAIN DETECTION PIPELINE (combines all steps)
# =============================================================================

def run_cluster_detection(image: np.ndarray,
                           psf_fwhm: float = 3.5,
                           threshold_sigma: float = 3.0,
                           r_half_scales: List[float] = None,
                           mci_max: float = 0.9,
                           snr_min: float = 3.0,
                           r_half_min: float = 1.0,
                           ellipticity_max: float = 0.6,
                           box_size: int = 64,
                           pixel_scale: float = 0.2,
                           use_multiscale: bool = True,
                           use_mci: bool = True,
                           verbose: bool = True) -> List[Dict]:
    """
    Full cluster detection pipeline.

    Implements the approach from Saifollahi+2025 (Euclid injection paper)
    and Thilker+2022 (PHANGS-HST MCI method):

    1. Estimate background and RMS (sigma-clipped sliding median)
    2. Matched-filter detection at one or more cluster size scales
    3. Extract source properties (centroid, flux, shape, r_half)
    4. Compute MCI for extended source selection (Thilker+2022)
    5. Apply quality cuts

    Parameters:
    -----------
    image : ndarray
        Input image (injected or original)
    psf_fwhm : float
        PSF FWHM in pixels (used as minimum scale)
    threshold_sigma : float
        Detection threshold in sigma
    r_half_scales : list of float
        Cluster size scales to search (pixels). Default: [2,5,10,20]
    mci_max : float
        Maximum MCI for cluster selection (lower = more extended)
    snr_min : float
        Minimum S/N
    r_half_min : float
        Minimum half-light radius in pixels
    ellipticity_max : float
        Maximum ellipticity
    box_size : int
        Background estimation box size
    pixel_scale : float
        Arcsec/pixel
    use_multiscale : bool
        Use multi-scale detection (recommended)
    use_mci : bool
        Apply MCI selection cut
    verbose : bool
        Print progress

    Returns:
    --------
    detections : list of dict
        Detection catalog compatible with ClusterRetrieval.
        Keys: x, y, flux, snr, r_half, ellipticity, mci, inner_mci, outer_mci, flag
    """
    if r_half_scales is None:
        r_half_scales = [max(2.0, psf_fwhm/2),
                         psf_fwhm,
                         psf_fwhm * 2,
                         psf_fwhm * 4]

    if verbose:
        print(f'Running cluster detection pipeline...')
        print(f'  Image shape     : {image.shape}')
        print(f'  PSF FWHM        : {psf_fwhm:.1f} px')
        print(f'  Threshold       : {threshold_sigma}σ')
        print(f'  Scales          : {[f"{s:.1f}" for s in r_half_scales]} px')
        print(f'  Multi-scale     : {use_multiscale}')
        print(f'  MCI cut         : {use_mci} (mci_max={mci_max})')

    # Step 1: Background
    if verbose: print('  Step 1: Estimating background...')
    background, rms = estimate_background(image, box_size=box_size)
    if verbose: print(f'    BG median={np.median(background):.3f}, RMS median={np.median(rms):.4f}')

    # Step 2: Detection
    if verbose: print('  Step 2: Running matched-filter detection...')
    if use_multiscale:
        sources = multiscale_detect(image, background, rms,
                                     r_half_scales=r_half_scales,
                                     threshold_sigma=threshold_sigma,
                                     pixel_scale=pixel_scale)
    else:
        r_half = r_half_scales[len(r_half_scales)//2]
        snr_map, det_map = matched_filter_detect(
            image, background, rms,
            r_half_pixels=r_half,
            threshold_sigma=threshold_sigma
        )
        sources = extract_sources(image, background, snr_map, det_map, pixel_scale)

    if verbose: print(f'    Found {len(sources)} raw sources')

    # Step 3: MCI
    if use_mci and sources:
        if verbose: print('  Step 3: Computing MCI (Thilker+2022)...')
        bkg_sub = image - background
        sources = compute_mci(bkg_sub, sources,
                               inner_radius=max(1.0, psf_fwhm * 0.5),
                               outer_radius=max(3.0, psf_fwhm * 1.5))

        sources = select_cluster_candidates(sources,
                                             mci_max=mci_max,
                                             snr_min=snr_min,
                                             r_half_min=r_half_min,
                                             ellipticity_max=ellipticity_max)
        if verbose: print(f'    After MCI cut: {len(sources)} candidates')
    else:
        # Basic cuts without MCI
        sources = [s for s in sources
                   if s.get('snr', 0) >= snr_min
                   and s.get('r_half', 0) >= r_half_min
                   and s.get('ellipticity', 1) <= ellipticity_max]

    if verbose: print(f'  ✓ Final catalog: {len(sources)} detections')

    return sources


# =============================================================================
# DIAGNOSTIC PLOTS
# =============================================================================

def plot_detection_diagnostic(image: np.ndarray,
                               background: np.ndarray,
                               rms: np.ndarray,
                               snr_map: np.ndarray,
                               sources: List[Dict],
                               injection_info: List[Dict] = None,
                               figsize=(18, 10)):
    """
    Diagnostic plot showing each step of the detection pipeline.

    Parameters:
    -----------
    image : ndarray
    background : ndarray
    rms : ndarray
    snr_map : ndarray
    sources : list of dict
        Detected sources
    injection_info : list of dict, optional
        Injected cluster positions for comparison
    """
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    from matplotlib.patches import Circle

    fig, axes = plt.subplots(2, 3, figsize=figsize)

    vmin, vmax = np.percentile(image, [1, 99])

    # Original image
    ax = axes[0, 0]
    ax.imshow(image, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
    ax.set_title('Input Image')

    # Background
    ax = axes[0, 1]
    im = ax.imshow(background, cmap='viridis', origin='lower')
    ax.set_title('Estimated Background')
    plt.colorbar(im, ax=ax)

    # RMS map
    ax = axes[0, 2]
    im = ax.imshow(rms, cmap='plasma', origin='lower')
    ax.set_title('RMS Noise Map')
    plt.colorbar(im, ax=ax)

    # Background-subtracted
    ax = axes[1, 0]
    bkg_sub = image - background
    ax.imshow(bkg_sub, cmap='gray', origin='lower',
              vmin=np.percentile(bkg_sub, 1), vmax=np.percentile(bkg_sub, 99))
    ax.set_title('Background Subtracted')

    # S/N map
    ax = axes[1, 1]
    im = ax.imshow(snr_map, cmap='hot', origin='lower', vmin=0, vmax=10)
    ax.set_title(f'S/N Map (matched filter)')
    plt.colorbar(im, ax=ax, label='S/N')

    # Detections overlaid
    ax = axes[1, 2]
    ax.imshow(image, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)

    # Injected positions (if provided)
    if injection_info is not None:
        for inj in injection_info:
            circ = Circle((inj['x'], inj['y']), inj['r_half'],
                           fill=False, color='red', lw=1.5, ls='--', alpha=0.7)
            ax.add_patch(circ)

    # Detected positions
    for src in sources:
        r = max(src.get('r_half', 3), 3)
        circ = Circle((src['x'], src['y']), r,
                       fill=False, color='lime', lw=1.5)
        ax.add_patch(circ)

    from matplotlib.lines import Line2D
    legend = []
    if injection_info:
        legend.append(Line2D([0],[0], color='red', ls='--', lw=1.5, label='Injected'))
    legend.append(Line2D([0],[0], color='lime', lw=1.5, label=f'Detected (n={len(sources)})'))
    ax.legend(handles=legend, loc='upper right', fontsize=8)
    ax.set_title('Detections (green) vs Injected (red dashed)')

    for ax in axes.flat:
        ax.set_xlabel('X (pixels)')
        ax.set_ylabel('Y (pixels)')

    plt.suptitle('Detection Pipeline Diagnostic', fontsize=13)
    plt.tight_layout()
    return fig


def plot_mci_diagram(sources: List[Dict],
                     injection_info: List[Dict] = None,
                     match_radius: float = 5.0):
    """
    MCI diagnostic plot (Thilker+2022 Fig. style).

    Shows inner_MCI vs outer_MCI for all detected sources,
    colored by whether they match an injected cluster.
    """
    import matplotlib.pyplot as plt

    if not sources or 'inner_mci' not in sources[0]:
        print('No MCI data. Run compute_mci() first.')
        return

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    inner_mcis = np.array([s.get('inner_mci', np.nan) for s in sources])
    outer_mcis = np.array([s.get('outer_mci', np.nan) for s in sources])
    snrs       = np.array([s.get('snr', 0) for s in sources])

    # Match detections to injections
    if injection_info is not None:
        matched = np.zeros(len(sources), dtype=bool)
        inj_x = np.array([i['x'] for i in injection_info])
        inj_y = np.array([i['y'] for i in injection_info])
        for k, src in enumerate(sources):
            dist = np.sqrt((inj_x - src['x'])**2 + (inj_y - src['y'])**2)
            if dist.min() < match_radius:
                matched[k] = True
    else:
        matched = np.ones(len(sources), dtype=bool)

    # MCI diagram
    ax = axes[0]
    ax.scatter(inner_mcis[~matched], outer_mcis[~matched],
               c='gray', s=20, alpha=0.5, label='Unmatched')
    ax.scatter(inner_mcis[matched], outer_mcis[matched],
               c='lime', s=40, edgecolors='black', lw=0.5,
               label=f'Matched injections ({matched.sum()})')
    ax.axvline(0.9, color='red', ls='--', lw=1.5, label='MCI=0.9 cut')
    ax.set_xlabel('Inner MCI')
    ax.set_ylabel('Outer MCI')
    ax.set_title('MCI Diagram (Thilker+2022)\nExtended clusters: lower MCI')
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # S/N vs inner MCI
    ax = axes[1]
    sc = ax.scatter(inner_mcis, snrs, c=outer_mcis,
                    cmap='viridis', s=20, alpha=0.7)
    plt.colorbar(sc, ax=ax, label='Outer MCI')
    ax.axvline(0.9, color='red', ls='--', lw=1.5, label='MCI=0.9 cut')
    ax.axhline(3.0, color='orange', ls=':', lw=1.5, label='S/N=3 cut')
    ax.set_xlabel('Inner MCI')
    ax.set_ylabel('Peak S/N')
    ax.set_title('S/N vs MCI\n(colored by outer MCI)')
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    plt.suptitle('MCI Selection Diagnostic', fontsize=13)
    plt.tight_layout()
    return fig
