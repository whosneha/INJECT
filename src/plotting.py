"""
plotting.py — Reusable plotting functions for the injection-recovery pipeline.

All functions return (fig, ax) or (fig, axes) so users can further
customise or save the figure themselves.

Quick usage
-----------
from src.plotting import (
    plot_position_map,
    plot_completeness_1d,
    plot_completeness_2d,
    plot_per_iteration_positions,
    plot_per_iteration_2d,
    plot_psf_fwhm_map,
    plot_injection_summary,
)
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from collections import Counter


# ======================================================================
# 1. Position map — detected vs missed on the base/injected image
# ======================================================================
def plot_position_map(matched, image,
                      title       = None,
                      det_color   = 'lime',
                      miss_color  = 'red',
                      marker_size = 3,
                      alpha       = 0.6,
                      figsize     = (9, 9),
                      cmap        = 'gray',
                      pct_lo      = 1,
                      pct_hi      = 99):
    """
    Overlay injection positions on an image.

    Parameters
    ----------
    matched    : list[dict]  — retrieval._matched, each entry has x, y, detected
    image      : 2D ndarray  — background image to display
    title      : str or None
    det_color  : str         — colour for recovered clusters
    miss_color : str         — colour for missed clusters
    marker_size: float
    alpha      : float       — marker transparency
    figsize    : tuple
    cmap       : str         — matplotlib colormap for the image
    pct_lo/hi  : float       — percentile stretch for image display

    Returns
    -------
    fig, ax
    """
    fig, ax = plt.subplots(figsize=figsize)
    ax.imshow(image, origin='lower', cmap=cmap,
              vmin=np.percentile(image, pct_lo),
              vmax=np.percentile(image, pct_hi))

    for entry in matched:
        color = det_color if entry.get('detected', False) else miss_color
        ax.plot(entry['x'], entry['y'], 'o',
                ms=marker_size, mec=color, mfc='none',
                mew=0.6, alpha=alpha)

    n_det = sum(1 for e in matched if e.get('detected', False))
    n_inj = len(matched)

    ax.scatter([], [], marker='o', edgecolors=det_color,
               facecolors='none', label=f'Detected ({n_det})')
    ax.scatter([], [], marker='o', edgecolors=miss_color,
               facecolors='none', label=f'Missed ({n_inj - n_det})')
    ax.legend(loc='upper right', fontsize=9)
    ax.axis('off')

    if title is None:
        title = (f'Injection positions — {n_det}/{n_inj} recovered '
                 f'({n_det / n_inj:.1%})')
    ax.set_title(title)

    plt.tight_layout()
    return fig, ax


# ======================================================================
# 2. 1D completeness curves — magnitude and/or r_half
# ======================================================================
def plot_completeness_1d(retrieval, config,
                         pixel_scale = 0.2,
                         figsize     = (13, 5),
                         color_mag   = 'tab:blue',
                         color_rh    = 'tab:orange',
                         show_limit  = True):
    """
    Plot completeness vs magnitude and vs half-light radius side by side.

    Parameters
    ----------
    retrieval    : ClusterRetrieval  — after match_detections() called
    config       : InjectionConfig
    pixel_scale  : float             — arcsec/pixel for r_half axis label
    show_limit   : bool              — draw 50% completeness limit line

    Returns
    -------
    fig, (ax_mag, ax_rh)
    """
    stats = retrieval.get_summary_statistics()
    cc    = config.cluster_config

    mag_bins = np.arange(cc.mag_min, cc.mag_max + 0.5, 0.5)
    rh_bins  = np.linspace(cc.r_half_min, cc.r_half_max, 10)

    bc_mag, comp_mag, err_mag = retrieval.compute_completeness('magnitude', mag_bins)
    bc_rh,  comp_rh,  err_rh  = retrieval.compute_completeness('r_half',   rh_bins)

    fig, axes = plt.subplots(1, 2, figsize=figsize)

    # ---- Magnitude (blocky step + 1-sigma band) ----
    axes[0].step(bc_mag, comp_mag, where='mid', color=color_mag, lw=2,
                 label='Completeness')
    axes[0].fill_between(bc_mag, np.clip(comp_mag - err_mag, 0, 1),
                         np.clip(comp_mag + err_mag, 0, 1),
                         step='mid', alpha=0.25, color=color_mag,
                         label='1-sigma binomial error')
    axes[0].axhline(0.5, color='gray', ls='--', lw=1, label='50%')
    axes[0].axhline(0.9, color='gray', ls=':', lw=1, label='90%')
    if show_limit and not np.isnan(stats['mag_50_limit']):
        axes[0].axvline(stats['mag_50_limit'], color='red', ls='--', lw=1,
                        label=f"50% limit = {stats['mag_50_limit']:.2f} mag")
    axes[0].set_xlabel('Injected magnitude (AB)')
    axes[0].set_ylabel('Completeness')
    axes[0].set_ylim(0, 1.05)
    axes[0].set_title(f"Completeness vs Magnitude\n"
                      f"({stats['n_injected']} clusters, "
                      f"overall {stats['overall_completeness']:.1%})")
    axes[0].legend(loc='lower left')

    # ---- Half-light radius (blocky step + 1-sigma band) ----
    ax2 = axes[1]
    ax2.step(bc_rh, comp_rh, where='mid', color=color_rh, lw=2,
             label='Completeness')
    ax2.fill_between(bc_rh, np.clip(comp_rh - err_rh, 0, 1),
                     np.clip(comp_rh + err_rh, 0, 1),
                     step='mid', alpha=0.25, color=color_rh,
                     label='1-sigma binomial error')
    ax2.axhline(0.5, color='gray', ls='--', lw=1, label='50%')
    ax2.axhline(0.9, color='gray', ls=':', lw=1, label='90%')
    if show_limit and not np.isnan(stats['r_half_50_limit']):
        ax2.axvline(stats['r_half_50_limit'], color='red', ls='--', lw=1,
                    label=f"50% limit = {stats['r_half_50_limit']:.2f} px\n"
                          f"= {stats['r_half_50_limit'] * pixel_scale:.2f} arcsec")
    ax2.set_xlabel('Half-light radius (px)')
    ax2.set_ylabel('Completeness')
    ax2.set_ylim(0, 1.05)
    ax2.set_title('Completeness vs Half-light radius')
    ax2.legend(loc='lower left')

    plt.tight_layout()
    return fig, axes


# ======================================================================
# 3. 2D completeness map — magnitude × r_half
# ======================================================================
def plot_completeness_2d(retrieval, config,
                         mag_step   = 1.0,
                         n_rh_bins  = 6,
                         figsize    = (10, 5),
                         cmap       = 'RdYlGn',
                         annotate   = True,
                         title      = None):
    """
    2D completeness heatmap: magnitude × half-light radius.

    Parameters
    ----------
    retrieval  : ClusterRetrieval  — after match_detections() called
    config     : InjectionConfig
    mag_step   : float             — magnitude bin width
    n_rh_bins  : int               — number of r_half bins
    annotate   : bool              — write n_injected in each cell
    title      : str or None

    Returns
    -------
    fig, ax
    """
    cc = config.cluster_config

    mag_bins = np.arange(cc.mag_min, cc.mag_max + mag_step, mag_step)
    rh_bins  = np.linspace(cc.r_half_min, cc.r_half_max, n_rh_bins)

    result = retrieval.compute_completeness_2d(
        'magnitude', 'r_half', mag_bins, rh_bins
    )

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.pcolormesh(result['bin_centers1'], result['bin_centers2'],
                       result['completeness'].T,
                       cmap=cmap, vmin=0, vmax=1)
    plt.colorbar(im, ax=ax, label='Completeness')

    if annotate:
        for i in range(result['n_injected'].shape[0]):
            for j in range(result['n_injected'].shape[1]):
                n = result['n_injected'][i, j]
                if n > 0:
                    ax.text(result['bin_centers1'][i],
                            result['bin_centers2'][j],
                            str(n), ha='center', va='center',
                            fontsize=7, color='k')

    ax.set_xlabel('Injected magnitude (AB)')
    ax.set_ylabel('Half-light radius (px)')

    if title is None:
        stats = retrieval.get_summary_statistics()
        title = (f'2D Completeness Map\n'
                 f'({stats["n_injected"]} total injections)')
    ax.set_title(title)

    plt.tight_layout()
    return fig, ax


# ======================================================================
# 4. Per-iteration position maps (2×2 grid)
# ======================================================================
def plot_per_iteration_positions(iterations, base_image,
                                 ClusterRetrieval,
                                 n_show      = 4,
                                 match_radius= 5.0,
                                 det_color   = 'lime',
                                 miss_color  = 'red',
                                 figsize     = (14, 14),
                                 cmap        = 'gray'):
    """
    2×2 grid of per-iteration position maps.

    Parameters
    ----------
    iterations      : list[dict]  — output of pipe.run_batch()
    base_image      : 2D ndarray
    ClusterRetrieval: class       — pass in from src.retrieval
    n_show          : int         — how many iterations to show (max 4)
    match_radius    : float       — pixels

    Returns
    -------
    fig, axes
    """
    n_show = min(n_show, 4, len(iterations))
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    axes = axes.flatten()

    for idx in range(n_show):
        ax  = axes[idx]
        it  = iterations[idx]
        img = it.get('injected_image', base_image)

        ret_it = ClusterRetrieval(it['injection_info'], it['detections'])
        ret_it.match_detections(match_radius=match_radius)

        ax.imshow(img, origin='lower', cmap=cmap,
                  vmin=np.percentile(img, 1),
                  vmax=np.percentile(img, 99))

        for entry in ret_it._matched:
            color = det_color if entry.get('detected', False) else miss_color
            ax.plot(entry['x'], entry['y'], 'o',
                    ms=4, mec=color, mfc='none', mew=0.8)

        n_det = sum(1 for e in ret_it._matched if e.get('detected', False))
        n_inj = len(it['injection_info'])
        ax.set_title(f'Iteration {idx + 1}  —  {n_det}/{n_inj} '
                     f'({n_det / n_inj:.0%})', fontsize=10)
        ax.axis('off')

    # Hide unused panels
    for idx in range(n_show, 4):
        axes[idx].axis('off')

    axes[0].scatter([], [], marker='o', edgecolors=det_color,
                    facecolors='none', label='Detected')
    axes[0].scatter([], [], marker='o', edgecolors=miss_color,
                    facecolors='none', label='Missed')
    axes[0].legend(loc='upper right', fontsize=9)

    plt.suptitle('Per-iteration injection positions', fontsize=13)
    plt.tight_layout()
    return fig, axes


# ======================================================================
# 5. Per-iteration 2D completeness maps (2×2 grid)
# ======================================================================
def plot_per_iteration_2d(iterations, config,
                          ClusterRetrieval,
                          n_show      = 4,
                          match_radius= 5.0,
                          mag_step    = 1.0,
                          n_rh_bins   = 5,
                          figsize     = (15, 10),
                          cmap        = 'RdYlGn'):
    """
    2×2 grid of per-iteration 2D completeness maps.

    Parameters
    ----------
    iterations      : list[dict]  — output of pipe.run_batch()
    config          : InjectionConfig
    ClusterRetrieval: class       — pass in from src.retrieval
    n_show          : int         — how many iterations to show (max 4)

    Returns
    -------
    fig, axes
    """
    cc = config.cluster_config
    mag_bins = np.arange(cc.mag_min, cc.mag_max + mag_step, mag_step)
    rh_bins  = np.linspace(cc.r_half_min, cc.r_half_max, n_rh_bins)

    n_show = min(n_show, 4, len(iterations))
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    axes = axes.flatten()

    for idx in range(n_show):
        ax  = axes[idx]
        it  = iterations[idx]

        ret_it = ClusterRetrieval(it['injection_info'], it['detections'])
        ret_it.match_detections(match_radius=match_radius)

        result = ret_it.compute_completeness_2d(
            'magnitude', 'r_half', mag_bins, rh_bins
        )

        im = ax.pcolormesh(result['bin_centers1'], result['bin_centers2'],
                           result['completeness'].T,
                           cmap=cmap, vmin=0, vmax=1)
        plt.colorbar(im, ax=ax, label='Completeness')

        for i in range(result['n_injected'].shape[0]):
            for j in range(result['n_injected'].shape[1]):
                n = result['n_injected'][i, j]
                if n > 0:
                    ax.text(result['bin_centers1'][i],
                            result['bin_centers2'][j],
                            str(n), ha='center', va='center', fontsize=7)

        ax.set_xlabel('Magnitude (AB)')
        ax.set_ylabel('r_half (px)')
        ax.set_title(f'Iteration {idx + 1}', fontsize=10)

    for idx in range(n_show, 4):
        axes[idx].axis('off')

    plt.suptitle('Per-iteration 2D completeness maps', fontsize=13)
    plt.tight_layout()
    return fig, axes


# ======================================================================
# 6. PSF FWHM spatial map
# ======================================================================
def plot_psf_fwhm_map(grid_fwhm, pixel_scale=0.2, figsize=(5, 4)):
    """
    Heatmap of PSF FWHM sampled on a grid across the coadd.

    Parameters
    ----------
    grid_fwhm    : 2D ndarray  — FWHM in pixels on NxN grid
    pixel_scale  : float       — arcsec/pixel
    figsize      : tuple

    Returns
    -------
    fig, ax
    """
    median_fwhm = float(np.nanmedian(grid_fwhm))

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(grid_fwhm, origin='lower', cmap='viridis')
    plt.colorbar(im, ax=ax, label='FWHM (px)')
    ax.set_title(f'PSF FWHM spatial map\n'
                 f'median = {median_fwhm:.3f} px  '
                 f'({median_fwhm * pixel_scale:.3f} arcsec)')
    plt.tight_layout()
    return fig, ax


# ======================================================================
# 7. Injection summary — one-shot overview of a completed batch run
# ======================================================================
def plot_injection_summary(retrieval, config, iterations,
                           base_image,
                           ClusterRetrieval,
                           pixel_scale  = 0.2,
                           match_radius = 5.0,
                           figsize      = (16, 10)):
    """
    Single figure summarising a full batch run:
      top-left   : position map (all iterations)
      top-right  : 2D completeness map
      bottom-left : completeness vs magnitude
      bottom-right: completeness vs r_half

    Parameters
    ----------
    retrieval        : ClusterRetrieval — combined, after match_detections()
    config           : InjectionConfig
    iterations       : list[dict]       — run_batch() output
    base_image       : 2D ndarray
    ClusterRetrieval : class
    pixel_scale      : float

    Returns
    -------
    fig
    """
    stats = retrieval.get_summary_statistics()
    cc    = config.cluster_config

    fig = plt.figure(figsize=figsize)
    gs  = gridspec.GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)

    # ---- Top left: position map ----
    ax_pos = fig.add_subplot(gs[0, 0])
    ax_pos.imshow(base_image, origin='lower', cmap='gray',
                  vmin=np.percentile(base_image, 1),
                  vmax=np.percentile(base_image, 99))
    for entry in retrieval._matched:
        color = 'lime' if entry.get('detected', False) else 'red'
        ax_pos.plot(entry['x'], entry['y'], 'o',
                    ms=2, mec=color, mfc='none', mew=0.5, alpha=0.5)
    ax_pos.scatter([], [], marker='o', edgecolors='lime',
                   facecolors='none', label='Detected', s=15)
    ax_pos.scatter([], [], marker='o', edgecolors='red',
                   facecolors='none', label='Missed', s=15)
    ax_pos.legend(loc='upper right', fontsize=7)
    ax_pos.axis('off')
    ax_pos.set_title(f'Positions — {stats["overall_completeness"]:.1%} recovered',
                     fontsize=10)

    # ---- Top right: 2D completeness map ----
    ax_2d  = fig.add_subplot(gs[0, 1])
    mag_bins = np.arange(cc.mag_min, cc.mag_max + 1.0, 1.0)
    rh_bins  = np.linspace(cc.r_half_min, cc.r_half_max, 6)
    result   = retrieval.compute_completeness_2d(
        'magnitude', 'r_half', mag_bins, rh_bins
    )
    im = ax_2d.pcolormesh(result['bin_centers1'], result['bin_centers2'],
                          result['completeness'].T,
                          cmap='RdYlGn', vmin=0, vmax=1)
    plt.colorbar(im, ax=ax_2d, label='Completeness')
    ax_2d.set_xlabel('Magnitude (AB)', fontsize=9)
    ax_2d.set_ylabel('r_half (px)', fontsize=9)
    ax_2d.set_title('2D Completeness Map', fontsize=10)

    # ---- Bottom left: completeness vs magnitude ----
    ax_mag = fig.add_subplot(gs[1, 0])
    bc_mag, comp_mag, err_mag = retrieval.compute_completeness(
        'magnitude', np.arange(cc.mag_min, cc.mag_max + 0.5, 0.5)
    )
    ax_mag.errorbar(bc_mag, comp_mag, yerr=err_mag, fmt='o-', capsize=3)
    ax_mag.axhline(0.5, color='gray', ls='--', lw=1)
    ax_mag.axvline(stats['mag_50_limit'], color='red', ls='--', lw=1,
                   label=f"50% = {stats['mag_50_limit']:.2f}")
    ax_mag.set_xlabel('Magnitude (AB)', fontsize=9)
    ax_mag.set_ylabel('Completeness', fontsize=9)
    ax_mag.set_ylim(0, 1.05)
    ax_mag.set_title('Completeness vs Magnitude', fontsize=10)
    ax_mag.legend(fontsize=8)

    # ---- Bottom right: completeness vs r_half ----
    ax_rh = fig.add_subplot(gs[1, 1])
    bc_rh, comp_rh, err_rh = retrieval.compute_completeness(
        'r_half', np.linspace(cc.r_half_min, cc.r_half_max, 10)
    )
    ax_rh.errorbar(bc_rh, comp_rh, yerr=err_rh,
                   fmt='s-', capsize=3, color='tab:orange')
    ax_rh.axhline(0.5, color='gray', ls='--', lw=1)
    ax_rh.axvline(stats['r_half_50_limit'], color='red', ls='--', lw=1,
                  label=f"50% = {stats['r_half_50_limit']:.2f} px\n"
                        f"= {stats['r_half_50_limit'] * pixel_scale:.2f}\"")
    ax_rh.set_xlabel('Half-light radius (px)', fontsize=9)
    ax_rh.set_ylabel('Completeness', fontsize=9)
    ax_rh.set_ylim(0, 1.05)
    ax_rh.set_title('Completeness vs r_half', fontsize=10)
    ax_rh.legend(fontsize=8)

    fig.suptitle(
        f'Injection-Recovery Summary — {config.run_name}\n'
        f'{stats["n_injected"]} injections · '
        f'{len(iterations)} iterations · '
        f'{stats["overall_completeness"]:.1%} overall completeness',
        fontsize=12, y=1.01
    )

    plt.tight_layout()
    return fig