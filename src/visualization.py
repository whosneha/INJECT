"""
Visualization module for star cluster injection pipeline.

Provides functions for:
- Plotting postage stamps (intrinsic, PSF, convolved)
- Creating injection summary plots
- Completeness visualization
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import os


def plot_postage_stamps(stamps, cluster_id=None, save_path=None, show=True):
    """
    Plot the postage stamps for a single injected cluster.
    
    Parameters:
    -----------
    stamps : dict
        Dictionary containing 'intrinsic', 'psf', 'convolved', 'final' arrays
    cluster_id : int, optional
        Cluster ID for title
    save_path : str, optional
        Path to save the figure
    show : bool
        Whether to display the plot
    """
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    
    # Intrinsic (before PSF)
    ax = axes[0]
    if stamps.get('intrinsic') is not None:
        img = stamps['intrinsic']
        im = ax.imshow(img, cmap='hot', origin='lower',
                      norm=LogNorm(vmin=max(0.01, img.max()*1e-4), vmax=img.max()))
        ax.set_title(f'Intrinsic Profile\npeak={img.max():.2f}')
        plt.colorbar(im, ax=ax, shrink=0.8)
    else:
        ax.text(0.5, 0.5, 'N/A', ha='center', va='center', transform=ax.transAxes)
        ax.set_title('Intrinsic Profile')
    
    # PSF
    ax = axes[1]
    if stamps.get('psf') is not None:
        psf = stamps['psf']
        im = ax.imshow(psf, cmap='hot', origin='lower')
        ax.set_title(f'PSF\nsum={np.sum(psf):.3f}')
        plt.colorbar(im, ax=ax, shrink=0.8)
    else:
        ax.text(0.5, 0.5, 'No PSF', ha='center', va='center', transform=ax.transAxes)
        ax.set_title('PSF')
    
    # Convolved (after PSF, before noise)
    ax = axes[2]
    if stamps.get('convolved') is not None:
        img = stamps['convolved']
        im = ax.imshow(img, cmap='hot', origin='lower',
                      norm=LogNorm(vmin=max(0.01, img.max()*1e-4), vmax=img.max()))
        ax.set_title(f'PSF Convolved\npeak={img.max():.2f}')
        plt.colorbar(im, ax=ax, shrink=0.8)
    else:
        ax.text(0.5, 0.5, 'N/A', ha='center', va='center', transform=ax.transAxes)
        ax.set_title('PSF Convolved')
    
    # Final (with noise)
    ax = axes[3]
    if stamps.get('final') is not None:
        img = stamps['final']
        im = ax.imshow(img, cmap='hot', origin='lower',
                      norm=LogNorm(vmin=max(0.01, img.max()*1e-4), vmax=img.max()))
        ax.set_title(f'Final (with noise)\npeak={img.max():.2f}')
        plt.colorbar(im, ax=ax, shrink=0.8)
    else:
        ax.text(0.5, 0.5, 'N/A', ha='center', va='center', transform=ax.transAxes)
        ax.set_title('Final')
    
    for ax in axes:
        ax.set_xlabel('X (pixels)')
        ax.set_ylabel('Y (pixels)')
    
    title = 'Cluster Postage Stamps'
    if cluster_id is not None:
        title += f' - ID {cluster_id}'
    plt.suptitle(title, fontsize=14)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()


def plot_all_stamps(injection_info, output_dir, max_clusters=20, show=False):
    """
    Plot postage stamps for all injected clusters.
    
    Parameters:
    -----------
    injection_info : list of dict
        Injection info from inject_from_catalog with stamps
    output_dir : str
        Directory to save plots
    max_clusters : int
        Maximum number of clusters to plot
    show : bool
        Whether to display plots
    """
    os.makedirs(output_dir, exist_ok=True)
    
    n_plotted = 0
    for info in injection_info:
        if 'stamps' not in info or info['stamps'] is None:
            continue
        
        cluster_id = info.get('id', n_plotted)
        save_path = os.path.join(output_dir, f'stamps_cluster_{cluster_id:04d}.png')
        
        plot_postage_stamps(
            info['stamps'],
            cluster_id=cluster_id,
            save_path=save_path,
            show=show
        )
        
        n_plotted += 1
        if n_plotted >= max_clusters:
            break
    
    print(f"Plotted {n_plotted} cluster stamps to {output_dir}")


def plot_stamp_grid(injection_info, n_cols=5, n_rows=4, save_path=None, show=True):
    """
    Plot a grid of cluster stamps for quick overview.
    
    Parameters:
    -----------
    injection_info : list of dict
        Injection info with stamps
    n_cols, n_rows : int
        Grid dimensions
    save_path : str, optional
        Path to save figure
    show : bool
        Whether to display
    """
    n_clusters = min(len(injection_info), n_cols * n_rows)
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3*n_cols, 3*n_rows))
    axes = axes.flatten()
    
    for i, ax in enumerate(axes):
        if i < n_clusters:
            info = injection_info[i]
            stamps = info.get('stamps', {})
            
            # Show convolved stamp
            img = stamps.get('convolved') or stamps.get('final') or stamps.get('intrinsic')
            
            if img is not None:
                ax.imshow(img, cmap='hot', origin='lower',
                         norm=LogNorm(vmin=max(0.01, img.max()*1e-4), vmax=img.max()))
                ax.set_title(f"ID {info.get('id', i)}\nm={info.get('magnitude', 0):.1f}", fontsize=9)
            else:
                ax.text(0.5, 0.5, 'No stamp', ha='center', va='center', transform=ax.transAxes)
        
        ax.set_xticks([])
        ax.set_yticks([])
    
    plt.suptitle(f'Injected Cluster Stamps (n={n_clusters})', fontsize=14)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()


def plot_injection_summary(image, injected_image, injection_info, save_path=None, show=True):
    """
    Create a summary plot of the injection.
    
    Parameters:
    -----------
    image : ndarray
        Original image
    injected_image : ndarray
        Image with injections
    injection_info : list of dict
        Injection catalog with results
    save_path : str, optional
        Path to save figure
    show : bool
        Whether to display
    """
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    
    vmin, vmax = np.percentile(image, [1, 99])
    
    # Original
    ax = axes[0, 0]
    ax.imshow(image, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
    ax.set_title('Original Image')
    
    # Injected
    ax = axes[0, 1]
    ax.imshow(injected_image, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
    for info in injection_info:
        ax.scatter(info['x'], info['y'], s=50, facecolors='none', edgecolors='red', lw=1)
    ax.set_title(f'Injected ({len(injection_info)} clusters)')
    
    # Difference
    ax = axes[0, 2]
    diff = injected_image - image
    im = ax.imshow(diff, cmap='hot', origin='lower',
                   norm=LogNorm(vmin=0.1, vmax=max(diff.max(), 1)))
    ax.set_title('Difference')
    plt.colorbar(im, ax=ax, shrink=0.8)
    
    # Magnitude distribution
    ax = axes[1, 0]
    mags = [info['magnitude'] for info in injection_info]
    ax.hist(mags, bins=20, edgecolor='black')
    ax.set_xlabel('Magnitude')
    ax.set_ylabel('Count')
    ax.set_title('Magnitude Distribution')
    
    # Size distribution
    ax = axes[1, 1]
    sizes = [info['r_half'] for info in injection_info]
    ax.hist(sizes, bins=20, edgecolor='black', color='orange')
    ax.set_xlabel('Half-light Radius (pixels)')
    ax.set_ylabel('Count')
    ax.set_title('Size Distribution')
    
    # Flux injected
    ax = axes[1, 2]
    fluxes = [info.get('total_flux_injected', 0) for info in injection_info]
    ax.scatter(mags, np.log10(np.array(fluxes) + 1), alpha=0.7)
    ax.set_xlabel('Magnitude')
    ax.set_ylabel('log10(Flux Injected)')
    ax.set_title('Flux vs Magnitude')
    
    for ax in axes.flat:
        if ax.get_xlabel() == '':
            ax.set_xlabel('X (pixels)')
            ax.set_ylabel('Y (pixels)')
    
    plt.suptitle('Injection Summary', fontsize=14)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved: {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()
