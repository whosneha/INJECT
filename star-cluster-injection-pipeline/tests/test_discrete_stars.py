"""
Tests for discrete star cluster generation.

Run with: python tests/test_discrete_stars.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

from src.cluster_models import (
    DiscreteStarCluster, create_cluster,
    kroupa_imf, chabrier_imf, salpeter_imf,
    plummer_positions, king_positions
)
from src.light_profiles import PlummerProfile
from src.inject import create_injection_catalog, inject_from_catalog

# Check for GalSim
try:
    from src.psf_convolution import convolve_with_psf, HAS_GALSIM
except ImportError:
    HAS_GALSIM = False


def main():
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'plots')
    os.makedirs(output_dir, exist_ok=True)
    
    print("="*70)
    print("DISCRETE STAR CLUSTER TESTS")
    print("="*70)
    
    # =========================================================================
    # TEST 1: Initial Mass Functions
    # =========================================================================
    print("\n[TEST 1] Initial Mass Functions...")
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    n_stars = 10000
    mass_bins = np.logspace(-1, 2, 50)
    
    imfs = [
        ('Kroupa', kroupa_imf(n_stars, seed=42)),
        ('Chabrier', chabrier_imf(n_stars, seed=42)),
        ('Salpeter', salpeter_imf(n_stars, seed=42)),
    ]
    
    for ax, (name, masses) in zip(axes, imfs):
        ax.hist(masses, bins=mass_bins, histtype='step', lw=2, label=name)
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlabel('Mass (M$_\\odot$)')
        ax.set_ylabel('Count')
        ax.set_title(f'{name} IMF\nM_total={np.sum(masses):.0f} M$_\\odot$')
        ax.axvline(np.median(masses), color='r', linestyle='--', label=f'Median={np.median(masses):.2f}')
        ax.legend()
    
    plt.suptitle('TEST 1: Initial Mass Functions', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'discrete_test1_imf.png'), dpi=150)
    print(f"  Saved: discrete_test1_imf.png")
    plt.close()
    
    # =========================================================================
    # TEST 2: Spatial Distributions
    # =========================================================================
    print("\n[TEST 2] Spatial Distributions...")
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    n_stars = 1000
    r_half = 20
    
    # Plummer
    r_plum, theta_plum = plummer_positions(n_stars, r_half, seed=42)
    x_plum = r_plum * np.cos(theta_plum)
    y_plum = r_plum * np.sin(theta_plum)
    
    ax = axes[0, 0]
    ax.scatter(x_plum, y_plum, s=1, alpha=0.5)
    circle = plt.Circle((0, 0), r_half, fill=False, color='r', lw=2, label=f'r_half={r_half}')
    ax.add_patch(circle)
    ax.set_xlim(-100, 100)
    ax.set_ylim(-100, 100)
    ax.set_aspect('equal')
    ax.set_title('Plummer - Positions')
    ax.legend()
    
    ax = axes[1, 0]
    ax.hist(r_plum, bins=50, histtype='step', lw=2, density=True)
    ax.axvline(r_half, color='r', linestyle='--', label=f'r_half={r_half}')
    ax.set_xlabel('Radius (pixels)')
    ax.set_ylabel('Density')
    ax.set_title('Plummer - Radial Distribution')
    ax.legend()
    
    # King
    r_c = r_half / (np.sqrt(30) * 0.5)  # Assuming c=30
    r_t = r_c * 30
    r_king, theta_king = king_positions(n_stars, r_c, r_t, seed=42)
    x_king = r_king * np.cos(theta_king)
    y_king = r_king * np.sin(theta_king)
    
    ax = axes[0, 1]
    ax.scatter(x_king, y_king, s=1, alpha=0.5)
    circle1 = plt.Circle((0, 0), r_half, fill=False, color='r', lw=2, label=f'r_half={r_half}')
    circle2 = plt.Circle((0, 0), r_t, fill=False, color='b', lw=1, linestyle='--', label=f'r_t={r_t:.0f}')
    ax.add_patch(circle1)
    ax.add_patch(circle2)
    ax.set_xlim(-150, 150)
    ax.set_ylim(-150, 150)
    ax.set_aspect('equal')
    ax.set_title('King (c=30) - Positions')
    ax.legend()
    
    ax = axes[1, 1]
    ax.hist(r_king, bins=50, histtype='step', lw=2, density=True)
    ax.axvline(r_half, color='r', linestyle='--', label=f'r_half={r_half}')
    ax.axvline(r_t, color='b', linestyle=':', label=f'r_t={r_t:.0f}')
    ax.set_xlabel('Radius (pixels)')
    ax.set_ylabel('Density')
    ax.set_title('King - Radial Distribution')
    ax.legend()
    
    # Comparison
    ax = axes[0, 2]
    ax.hist(r_plum, bins=50, histtype='step', lw=2, density=True, label='Plummer')
    ax.hist(r_king, bins=50, histtype='step', lw=2, density=True, label='King')
    ax.axvline(r_half, color='gray', linestyle='--', label=f'r_half={r_half}')
    ax.set_xlabel('Radius (pixels)')
    ax.set_ylabel('Density')
    ax.set_title('Radial Distribution Comparison')
    ax.legend()
    
    ax = axes[1, 2]
    ax.text(0.5, 0.5, f'Plummer median r: {np.median(r_plum):.1f}\nKing median r: {np.median(r_king):.1f}',
            ha='center', va='center', transform=ax.transAxes, fontsize=14)
    ax.axis('off')
    
    plt.suptitle('TEST 2: Spatial Distributions', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'discrete_test2_spatial.png'), dpi=150)
    print(f"  Saved: discrete_test2_spatial.png")
    plt.close()
    
    # =========================================================================
    # TEST 3: Discrete Star Cluster Generation
    # =========================================================================
    print("\n[TEST 3] Discrete Star Cluster Generation...")
    
    fig, axes = plt.subplots(2, 4, figsize=(18, 9))
    
    # Create discrete cluster
    cluster = DiscreteStarCluster(
        n_stars=200,
        r_half=15,
        total_magnitude=18,
        profile_type='plummer',
        imf='kroupa',
        age_gyr=1.0,
        seed=42
    )
    
    props = cluster.get_properties()
    print(f"  Created cluster: {props['n_stars']} stars, r_half={props['r_half']}")
    print(f"  Total magnitude: {props['total_magnitude']:.2f}")
    print(f"  Mass range: [{props['mass_range'][0]:.2f}, {props['mass_range'][1]:.2f}] Msun")
    
    # Star positions
    ax = axes[0, 0]
    ax.scatter(cluster.x_offset, cluster.y_offset, c=cluster.magnitudes, 
               s=20, cmap='viridis_r', alpha=0.7)
    circle = plt.Circle((0, 0), cluster.r_half, fill=False, color='r', lw=2)
    ax.add_patch(circle)
    ax.set_xlim(-50, 50)
    ax.set_ylim(-50, 50)
    ax.set_aspect('equal')
    ax.set_xlabel('X offset (pixels)')
    ax.set_ylabel('Y offset (pixels)')
    ax.set_title(f'Star Positions\n(n={cluster.n_stars}, colored by mag)')
    
    # Mass distribution
    ax = axes[0, 1]
    ax.hist(cluster.masses, bins=30, edgecolor='black')
    ax.set_xlabel('Mass (M$_\\odot$)')
    ax.set_ylabel('Count')
    ax.set_title('Mass Distribution')
    
    # Magnitude distribution
    ax = axes[0, 2]
    ax.hist(cluster.magnitudes, bins=30, edgecolor='black')
    ax.set_xlabel('Magnitude')
    ax.set_ylabel('Count')
    ax.set_title('Magnitude Distribution')
    
    # Flux distribution
    ax = axes[0, 3]
    ax.hist(np.log10(cluster.fluxes), bins=30, edgecolor='black')
    ax.set_xlabel('log10(Flux)')
    ax.set_ylabel('Count')
    ax.set_title('Flux Distribution')
    
    # 2D image (no PSF)
    img_size = (101, 101)
    discrete_img = cluster.generate_2d(img_size)
    
    ax = axes[1, 0]
    im = ax.imshow(discrete_img, cmap='hot', origin='lower',
                   norm=LogNorm(vmin=0.1, vmax=discrete_img.max()))
    ax.set_title('Discrete Stars (no PSF)')
    plt.colorbar(im, ax=ax, shrink=0.8)
    
    # 2D image (with PSF)
    if HAS_GALSIM:
        discrete_conv = convolve_with_psf(discrete_img, fwhm=3.5)
        ax = axes[1, 1]
        im = ax.imshow(discrete_conv, cmap='hot', origin='lower',
                      norm=LogNorm(vmin=0.1, vmax=discrete_conv.max()))
        ax.set_title('Discrete Stars (PSF convolved)')
        plt.colorbar(im, ax=ax, shrink=0.8)
    else:
        axes[1, 1].text(0.5, 0.5, 'GalSim not installed', ha='center', va='center',
                       transform=axes[1, 1].transAxes)
    
    # Smooth profile for comparison
    smooth = PlummerProfile(r_half=15, age=1.0, magnitude=18)
    smooth_img = smooth.generate_2d(img_size)
    
    ax = axes[1, 2]
    im = ax.imshow(smooth_img, cmap='hot', origin='lower',
                   norm=LogNorm(vmin=0.1, vmax=smooth_img.max()))
    ax.set_title('Smooth Profile (same mag)')
    plt.colorbar(im, ax=ax, shrink=0.8)
    
    # Radial profile comparison
    ax = axes[1, 3]
    center = 50
    r = np.arange(0, 40)
    
    # Azimuthal average for discrete
    y_grid, x_grid = np.ogrid[:img_size[0], :img_size[1]]
    r_grid = np.sqrt((x_grid - center)**2 + (y_grid - center)**2)
    bins = np.arange(0, 40, 2)
    discrete_radial = []
    for b in bins[:-1]:
        mask = (r_grid >= b) & (r_grid < b+2)
        discrete_radial.append(np.mean(discrete_img[mask]))
    
    ax.semilogy(bins[:-1]+1, discrete_radial, 'b-', lw=2, label='Discrete')
    ax.semilogy(r, smooth_img[center, center:center+len(r)], 'r--', lw=2, label='Smooth')
    ax.axvline(15, color='gray', linestyle=':', label='r_half')
    ax.set_xlabel('Radius (pixels)')
    ax.set_ylabel('Surface Brightness')
    ax.set_title('Radial Profile Comparison')
    ax.legend()
    
    plt.suptitle('TEST 3: Discrete Star Cluster Generation', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'discrete_test3_cluster.png'), dpi=150)
    print(f"  Saved: discrete_test3_cluster.png")
    plt.close()
    
    # =========================================================================
    # TEST 4: Smooth vs Discrete Injection
    # =========================================================================
    print("\n[TEST 4] Smooth vs Discrete Injection Comparison...")
    
    fig, axes = plt.subplots(2, 4, figsize=(18, 9))
    
    np.random.seed(42)
    img_size = (201, 201)
    background = np.random.normal(loc=100, scale=10, size=img_size)
    
    # Create catalogs with same properties
    base_params = {
        'x': 100, 'y': 100, 'magnitude': 19, 'r_half': 15,
        'profile_type': 'plummer', 'id': 0
    }
    
    smooth_catalog = [{**base_params, 'method': 'smooth'}]
    discrete_catalog = [{**base_params, 'method': 'discrete', 'n_stars': 150, 'imf': 'kroupa', 'age_gyr': 1.0}]
    
    # Inject
    psf_fwhm = 3.5 if HAS_GALSIM else None
    
    smooth_img, smooth_info = inject_from_catalog(background, smooth_catalog, psf_fwhm=psf_fwhm, add_noise=False)
    discrete_img, discrete_info = inject_from_catalog(background, discrete_catalog, psf_fwhm=psf_fwhm, add_noise=False)
    
    vmin, vmax = np.percentile(background, [1, 99])
    
    # Row 1: Cluster only
    ax = axes[0, 0]
    ax.imshow(background, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
    ax.set_title('Background')
    
    ax = axes[0, 1]
    smooth_cluster = smooth_img - background
    im = ax.imshow(smooth_cluster, cmap='hot', origin='lower', norm=LogNorm(vmin=0.1, vmax=smooth_cluster.max()))
    ax.set_title(f'Smooth Cluster\nflux={np.sum(smooth_cluster):.0f}')
    plt.colorbar(im, ax=ax, shrink=0.8)
    
    ax = axes[0, 2]
    discrete_cluster = discrete_img - background
    im = ax.imshow(discrete_cluster, cmap='hot', origin='lower', norm=LogNorm(vmin=0.1, vmax=max(discrete_cluster.max(), 1)))
    ax.set_title(f'Discrete Cluster\nflux={np.sum(discrete_cluster):.0f}')
    plt.colorbar(im, ax=ax, shrink=0.8)
    
    ax = axes[0, 3]
    diff = smooth_cluster - discrete_cluster
    im = ax.imshow(diff, cmap='RdBu', origin='lower', vmin=-np.abs(diff).max(), vmax=np.abs(diff).max())
    ax.set_title('Difference (smooth - discrete)')
    plt.colorbar(im, ax=ax, shrink=0.8)
    
    # Row 2: Injected images
    ax = axes[1, 0]
    ax.imshow(background, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
    ax.set_title('Background')
    
    ax = axes[1, 1]
    ax.imshow(smooth_img, cmap='gray', origin='lower', vmin=vmin, vmax=vmax*1.5)
    ax.scatter(100, 100, s=100, facecolors='none', edgecolors='red', lw=2)
    ax.set_title('Smooth Injected')
    
    ax = axes[1, 2]
    ax.imshow(discrete_img, cmap='gray', origin='lower', vmin=vmin, vmax=vmax*1.5)
    ax.scatter(100, 100, s=100, facecolors='none', edgecolors='red', lw=2)
    ax.set_title('Discrete Injected')
    
    # Radial comparison
    ax = axes[1, 3]
    center = 100
    r = np.arange(0, 50)
    ax.semilogy(r, smooth_cluster[center, center:center+len(r)], 'b-', lw=2, label='Smooth')
    
    # Azimuthal average for discrete
    y_grid, x_grid = np.ogrid[:img_size[0], :img_size[1]]
    r_grid = np.sqrt((x_grid - center)**2 + (y_grid - center)**2)
    bins = np.arange(0, 50, 2)
    discrete_radial = []
    for b in bins[:-1]:
        mask = (r_grid >= b) & (r_grid < b+2)
        discrete_radial.append(np.mean(discrete_cluster[mask]))
    ax.semilogy(bins[:-1]+1, discrete_radial, 'r--', lw=2, label='Discrete (avg)')
    ax.axvline(15, color='gray', linestyle=':', label='r_half')
    ax.set_xlabel('Radius (pixels)')
    ax.set_ylabel('Surface Brightness')
    ax.set_title('Radial Profile Comparison')
    ax.legend()
    
    for ax in axes.flat:
        ax.set_xlabel('X (pixels)')
        ax.set_ylabel('Y (pixels)')
    
    plt.suptitle('TEST 4: Smooth vs Discrete Injection (same total magnitude)', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'discrete_test4_comparison.png'), dpi=150)
    print(f"  Saved: discrete_test4_comparison.png")
    plt.close()
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "="*70)
    print("DISCRETE STAR TESTS COMPLETE")
    print("="*70)
    print(f"\nAll plots saved to: {os.path.abspath(output_dir)}")
    print("\nPlots generated:")
    print("  1. discrete_test1_imf.png      - Initial Mass Functions")
    print("  2. discrete_test2_spatial.png  - Spatial Distributions")
    print("  3. discrete_test3_cluster.png  - Cluster Generation")
    print("  4. discrete_test4_comparison.png - Smooth vs Discrete")
    print("="*70)


if __name__ == '__main__':
    main()
