"""
Batch injection + detection framework.

Use case
--------
You want to inject 10,000 clusters but injecting+detecting all of them at
once is too dense (sources overlap, detection saturates). Instead, run
N_BATCHES = 10 batches of BATCH_SIZE = 1000 clusters each on a fresh copy
of the same image, run detection on each batch, then aggregate the
recovery / completeness statistics across batches.

Outputs are the same kind the RSP notebook produces (postage stamps,
injection summary, completeness curve, recovery summary), just averaged
over batches with error bars from batch-to-batch scatter.
"""

from __future__ import annotations
import os, json
import numpy as np
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple, Any

from .inject import create_injection_catalog, inject_from_catalog
from .retrieval import ClusterRetrieval
from .detection import run_cluster_detection


# -----------------------------------------------------------------------------
# Default detection function — wraps run_cluster_detection (MCI pipeline)
# -----------------------------------------------------------------------------
def default_detection_fn(injected_image: np.ndarray,
                         psf_fwhm: float = 3.5,
                         **kwargs) -> List[Dict]:
    """Default detection: matched-filter + MCI (Saifollahi+2025, Thilker+2022)."""
    return run_cluster_detection(
        injected_image, psf_fwhm=psf_fwhm,
        threshold_sigma=kwargs.get('threshold_sigma', 3.0),
        r_half_scales=kwargs.get('r_half_scales', None),
        mci_max=kwargs.get('mci_max', 0.9),
        snr_min=kwargs.get('snr_min', 3.0),
        r_half_min=kwargs.get('r_half_min', 1.0),
        ellipticity_max=kwargs.get('ellipticity_max', 0.6),
        pixel_scale=kwargs.get('pixel_scale', 0.2),
        use_multiscale=kwargs.get('use_multiscale', True),
        use_mci=kwargs.get('use_mci', True),
        verbose=False,
    )


# -----------------------------------------------------------------------------
# Main batch driver
# -----------------------------------------------------------------------------
def run_batch_injection_detection(
    image: np.ndarray,
    *,
    total_clusters: int = 10_000,
    batch_size: int = 1000,
    n_batches: Optional[int] = None,
    exposure=None,
    psf_fwhm: float = 3.5,
    psf_mode: str = 'spatially_varying',  # 'none' | 'fixed' | 'spatially_varying'
    psf_kernel: Optional[np.ndarray] = None,
    mag_range: Tuple[float, float] = (19.0, 25.0),
    r_half_range: Tuple[float, float] = (3.0, 25.0),
    profile_type: str = 'plummer',
    method: str = 'smooth',
    edge_buffer: int = 100,
    add_noise: bool = True,
    pixel_scale: float = 0.2,
    seed: int = 42,
    detection_fn: Callable[..., List[Dict]] = default_detection_fn,
    detection_kwargs: Optional[Dict[str, Any]] = None,
    match_radius: float = 5.0,
    save_stamps: bool = False,
    keep_images: bool = False,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Run batched injection + detection on the same base image.

    Parameters
    ----------
    image : 2D ndarray
        Base image (the injection is applied to a fresh copy in each batch).
    total_clusters : int
        Total number of clusters across all batches (e.g. 10_000).
    batch_size : int
        Clusters per batch (e.g. 1000).
    n_batches : int, optional
        Overrides total_clusters/batch_size if given.
    exposure : ExposureF, optional
        Required for psf_mode='spatially_varying'.
    psf_mode : 'none'|'fixed'|'spatially_varying'
    psf_kernel : ndarray, optional
        Used when psf_mode='fixed'.
    detection_fn : callable
        Signature: detection_fn(injected_image, psf_fwhm=..., **detection_kwargs)
        Must return a list of dicts compatible with ClusterRetrieval
        (keys at least: 'x','y'; ideally 'snr','flux','r_half').
    detection_kwargs : dict
        Extra kwargs forwarded to detection_fn.
    match_radius : float
        Pixel radius for matching detections to injections.

    Returns
    -------
    results : dict with keys
        'batches'           : list of per-batch dicts (catalog, info, dets, retrieval_stats)
        'aggregated'        : merged injection_info + detections across all batches
        'completeness_mag'  : (mag_centers, mean_completeness, std_completeness)
        'summary'           : grand-total recovery statistics
        'config'            : the call configuration
    """
    if n_batches is None:
        n_batches = max(1, int(np.ceil(total_clusters / batch_size)))
    detection_kwargs = detection_kwargs or {}

    if verbose:
        print(f"=== Batch run: {n_batches} batches × {batch_size} clusters "
              f"= {n_batches * batch_size} total ===")
        print(f"  PSF mode      : {psf_mode}")
        print(f"  Profile/method: {profile_type}/{method}")
        print(f"  Detection fn  : {detection_fn.__name__}")

    rng_master = np.random.SeedSequence(seed)
    batch_seeds = rng_master.spawn(n_batches)

    batches: List[Dict[str, Any]] = []
    all_inj: List[Dict] = []
    all_det: List[Dict] = []

    psf_kwargs = {'psf_mode': psf_mode}
    if psf_mode == 'fixed' and psf_kernel is not None:
        psf_kwargs['psf_kernel'] = psf_kernel

    for b, ss in enumerate(batch_seeds):
        bseed = int(ss.generate_state(1)[0]) % (2**31 - 1)
        if verbose:
            print(f"\n  Batch {b+1}/{n_batches}  seed={bseed}")

        # 1. catalog
        catalog = create_injection_catalog(
            n_clusters=batch_size, image_shape=image.shape,
            mag_range=mag_range, r_half_range=r_half_range,
            profile_type=profile_type, method=method,
            edge_buffer=edge_buffer, exposure=exposure, seed=bseed,
        )

        # 2. inject into a fresh copy
        injected_image, injection_info = inject_from_catalog(
            image, catalog,
            exposure=exposure, add_noise=add_noise,
            pixel_scale=pixel_scale, save_stamps=save_stamps,
            **psf_kwargs,
        )

        # 3. detect
        detections = detection_fn(injected_image, psf_fwhm=psf_fwhm,
                                  **detection_kwargs)

        # 4. retrieve / match
        ret = ClusterRetrieval(injection_info, detections)
        ret.match_detections(match_radius=match_radius)
        stats = ret.get_summary_statistics()

        if verbose:
            print(f"    injected={len(injection_info)}  detected={len(detections)}  "
                  f"completeness={stats.get('overall_completeness', 0):.2%}")

        batch_record = {
            'batch_id': b,
            'seed': bseed,
            'catalog': catalog,
            'injection_info': injection_info,
            'detections': detections,
            'stats': stats,
            'retrieval': ret,
        }
        if keep_images:
            batch_record['injected_image'] = injected_image
        batches.append(batch_record)

        # tag with batch id then merge
        for e in injection_info: e['_batch'] = b
        for d in detections:     d['_batch'] = b
        all_inj.extend(injection_info)
        all_det.extend(detections)

    # ---- Aggregate completeness vs magnitude across batches ----
    mag_edges = np.linspace(mag_range[0], mag_range[1], 13)
    mag_centers = 0.5 * (mag_edges[:-1] + mag_edges[1:])
    per_batch_curves = np.full((n_batches, len(mag_centers)), np.nan)

    for bi, br in enumerate(batches):
        inj = br['injection_info']
        recovered_flag = np.array([bool(e.get('recovered', False)) for e in inj])
        mags = np.array([e.get('magnitude', np.nan) for e in inj])
        for k in range(len(mag_centers)):
            in_bin = (mags >= mag_edges[k]) & (mags < mag_edges[k+1])
            if in_bin.sum() > 0:
                per_batch_curves[bi, k] = recovered_flag[in_bin].mean()

    mean_completeness = np.nanmean(per_batch_curves, axis=0)
    std_completeness  = np.nanstd(per_batch_curves,  axis=0)

    # Grand summary using merged retrieval
    grand_ret = ClusterRetrieval(all_inj, all_det)
    grand_ret.match_detections(match_radius=match_radius)
    grand_summary = grand_ret.get_summary_statistics()

    return {
        'batches': batches,
        'aggregated': {
            'injection_info': all_inj,
            'detections':     all_det,
            'retrieval':      grand_ret,
        },
        'completeness_mag': {
            'mag_centers': mag_centers,
            'mean':        mean_completeness,
            'std':         std_completeness,
            'per_batch':   per_batch_curves,
        },
        'summary': grand_summary,
        'config': {
            'n_batches': n_batches, 'batch_size': batch_size,
            'total_clusters': n_batches * batch_size,
            'psf_mode': psf_mode, 'profile_type': profile_type,
            'method': method, 'mag_range': mag_range,
            'r_half_range': r_half_range, 'match_radius': match_radius,
            'seed': seed, 'timestamp': datetime.now().isoformat(),
        },
    }


# -----------------------------------------------------------------------------
# Plot helpers (matched to RSP notebook style)
# -----------------------------------------------------------------------------
def plot_batch_completeness(results: Dict[str, Any], ax=None, title=None):
    """Plot mean completeness vs magnitude with batch-to-batch error band."""
    import matplotlib.pyplot as plt
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 5))

    cm = results['completeness_mag']
    mc, mu, sd = cm['mag_centers'], cm['mean'], cm['std']

    ax.plot(mc, mu, 'o-', lw=2, color='C0', label='Mean across batches')
    ax.fill_between(mc, np.clip(mu - sd, 0, 1), np.clip(mu + sd, 0, 1),
                    alpha=0.25, color='C0', label='±1σ batch scatter')
    for row in cm['per_batch']:
        ax.plot(mc, row, '-', color='gray', alpha=0.25, lw=0.8)

    ax.axhline(0.5, color='red', ls='--', lw=1, label='50% completeness')
    ax.set_xlabel('Magnitude')
    ax.set_ylabel('Completeness')
    ax.set_ylim(-0.02, 1.05)
    ax.grid(alpha=0.3)
    ax.legend(loc='lower left', fontsize=9)
    cfg = results['config']
    ax.set_title(title or f"Aggregated completeness — "
                 f"{cfg['n_batches']}×{cfg['batch_size']} clusters")
    return ax


def save_batch_results(results: Dict[str, Any], output_dir: str,
                       run_name: str = 'batch_run'):
    """Save JSON-serializable per-batch + aggregated results."""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    def _clean(d):
        out = {}
        for k, v in d.items():
            if isinstance(v, np.ndarray):       out[k] = v.tolist()
            elif isinstance(v, (np.floating,)): out[k] = float(v)
            elif isinstance(v, (np.integer,)):  out[k] = int(v)
            else:                                out[k] = v
        return out

    summary_path = os.path.join(output_dir, f'{run_name}_{ts}_summary.json')
    payload = {
        'config':   results['config'],
        'summary':  _clean(results['summary']),
        'completeness_mag': {
            'mag_centers': results['completeness_mag']['mag_centers'].tolist(),
            'mean':        results['completeness_mag']['mean'].tolist(),
            'std':         results['completeness_mag']['std'].tolist(),
        },
        'per_batch_stats': [_clean(b['stats']) for b in results['batches']],
    }
    with open(summary_path, 'w') as f:
        json.dump(payload, f, indent=2)
    print(f"✓ Saved batch summary: {summary_path}")
    return summary_path
