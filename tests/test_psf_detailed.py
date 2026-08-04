"""
Detailed PSF tests to verify PSF convolution is working correctly.

This tests:
1. PSF shape and normalization
2. Point source convolution
3. Extended source convolution
4. Flux conservation
5. Comparison: discrete stars vs smooth profile

Run with: python tests/test_psf_detailed.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

from src.light_profiles import PlummerProfile, KingProfile, mag_to_flux

# Check for GalSim
try:
    import galsim
    from src.psf_convolution import convolve_with_psf, create_rubin_psf, HAS_GALSIM
except ImportError:
    HAS_GALSIM = False
    print("ERROR: GalSim not installed. Install with: pip install galsim")
    sys.exit(1)


def main():
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'plots')
    os.makedirs(output_dir, exist_ok=True)
    
    print("="*70)
    print("DETAILED PSF VERIFICATION TESTS")
    print("="*70)
    
    # Rubin-like PSF parameters
    PSF_FWHM_ARCSEC = 0.7  # Typical seeing
    PIXEL_SCALE = 0.2  # arcsec/pixel
    PSF_FWHM_PIXELS = PSF_FWHM_ARCSEC / PIXEL_SCALE  # ~3.5 pixels
    
    print(f"\nPSF Parameters:")
    print(f"  FWHM: {PSF_FWHM_ARCSEC} arcsec = {PSF_FWHM_PIXELS:.2f} pixels")
    print(f"  Pixel scale: {PIXEL_SCALE} arcsec/pixel")
    
    # =========================================================================
    # TEST 1: PSF Image Properties
    # =========================================================================
    print("\n[TEST 1] PSF Image Properties...")
    
    fig, axes = plt.subplots(1, 4, figsize=(18, 4))
    
    psf_size = (51, 51)
    psf_img = create_rubin_psf(PSF_FWHM_PIXELS, psf_size)
    
    # PSF image
    ax = axes[0]
    im = ax.imshow(psf_img, cmap='hot', origin='lower')
    ax.set_title(f'PSF Image\nFWHM={PSF_FWHM_PIXELS:.1f}px')
    plt.colorbar(im, ax=ax)
    
    # PSF log scale
    ax = axes[1]
    im = ax.imshow(psf_img, cmap='hot', origin='lower', 
                   norm=LogNorm(vmin=psf_img.max()*1e-4, vmax=psf_img.max()))
    ax.set_title('PSF (log scale)')
    plt.colorbar(im, ax=ax)
    
    # Radial profile
    ax = axes[2]
    center = psf_size[0] // 2
    r = np.arange(0, center)
    radial = psf_img[center, center:center+len(r)]
    ax.semilogy(r, radial / radial.max(), 'b-', lw=2, label='Measured')
    
    # Theoretical Gaussian for comparison
    sigma = PSF_FWHM_PIXELS / 2.355
    gaussian = np.exp(-r**2 / (2*sigma**2))
    ax.semilogy(r, gaussian, 'r--', lw=2, label='Gaussian')
    ax.axvline(PSF_FWHM_PIXELS/2, color='gray', linestyle=':', label='HWHM')
    ax.set_xlabel('Radius (pixels)')
    ax.set_ylabel('Normalized Intensity')
    ax.set_title('PSF Radial Profile')
    ax.legend()
    
    # Check normalization
    ax = axes[3]
    ax.text(0.5, 0.7, f'PSF Sum: {np.sum(psf_img):.6f}', ha='center', transform=ax.transAxes, fontsize=14)
    ax.text(0.5, 0.5, f'Peak: {psf_img.max():.6f}', ha='center', transform=ax.transAxes, fontsize=14)
    ax.text(0.5, 0.3, f'Expected sum: 1.0', ha='center', transform=ax.transAxes, fontsize=14)
    ax.axis('off')
    ax.set_title('Normalization Check')
    
    plt.suptitle('TEST 1: PSF Properties', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'psf_test1_properties.png'), dpi=150)
    print(f"  PSF sum: {np.sum(psf_img):.6f} (should be 1.0)")
    print(f"  Saved: psf_test1_properties.png")
    plt.close()
    
    # =========================================================================
    # TEST 2: Point Source Convolution
    # =========================================================================
    print("\n[TEST 2] Point Source Convolution...")
    
    fig, axes = plt.subplots(2, 4, figsize=(18, 9))
    
    img_size = (101, 101)
    center = 50
    
    # Create point sources with different magnitudes
    magnitudes = [18, 20, 22, 24]
    
    for i, mag in enumerate(magnitudes):
        flux = mag_to_flux(mag)
        
        # Create delta function (point source)
        point_source = np.zeros(img_size)
        point_source[center, center] = flux
        
        # Convolve with PSF
        convolved = convolve_with_psf(point_source, fwhm=PSF_FWHM_PIXELS)
        
        # Before convolution
        ax = axes[0, i]
        vmax = flux if flux < 1e6 else 1e6
        im = ax.imshow(point_source, cmap='hot', origin='lower', vmin=0, vmax=vmax)
        ax.set_title(f'm={mag}\nflux={flux:.1f}')
        plt.colorbar(im, ax=ax, shrink=0.8)
        
        # After convolution
        ax = axes[1, i]
        im = ax.imshow(convolved, cmap='hot', origin='lower', 
                      norm=LogNorm(vmin=0.01, vmax=convolved.max()))
        flux_ratio = np.sum(convolved) / flux
        ax.set_title(f'Convolved\nflux ratio={flux_ratio:.3f}')
        plt.colorbar(im, ax=ax, shrink=0.8)
        
        print(f"  m={mag}: input flux={flux:.1f}, output flux={np.sum(convolved):.1f}, ratio={flux_ratio:.4f}")
    
    axes[0, 0].set_ylabel('Point Source (input)')
    axes[1, 0].set_ylabel('PSF Convolved (output)')
    
    plt.suptitle('TEST 2: Point Source Convolution - Flux should be conserved', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'psf_test2_point_source.png'), dpi=150)
    print(f"  Saved: psf_test2_point_source.png")
    plt.close()
    
    # =========================================================================
    # TEST 3: Extended Source (Smooth Profile) Convolution
    # =========================================================================
    print("\n[TEST 3] Extended Source Convolution...")
    
    fig, axes = plt.subplots(2, 4, figsize=(18, 9))
    
    r_halfs = [2, 5, 10, 20]
    
    for i, r_half in enumerate(r_halfs):
        profile = PlummerProfile(r_half=r_half, age=1.0, central_brightness=100)
        img = profile.generate_2d(img_size)
        convolved = convolve_with_psf(img, fwhm=PSF_FWHM_PIXELS)
        
        # Before
        ax = axes[0, i]
        im = ax.imshow(img, cmap='hot', origin='lower', norm=LogNorm(vmin=0.01, vmax=img.max()))
        ax.set_title(f'r_half={r_half}px\npeak={img.max():.1f}')
        plt.colorbar(im, ax=ax, shrink=0.8)
        
        # After
        ax = axes[1, i]
        im = ax.imshow(convolved, cmap='hot', origin='lower', norm=LogNorm(vmin=0.01, vmax=img.max()))
        flux_ratio = np.sum(convolved) / np.sum(img)
        peak_ratio = convolved.max() / img.max()
        ax.set_title(f'Convolved\nflux={flux_ratio:.3f}, peak={peak_ratio:.2f}')
        plt.colorbar(im, ax=ax, shrink=0.8)
        
        print(f"  r_half={r_half}px: flux_ratio={flux_ratio:.4f}, peak_ratio={peak_ratio:.3f}")
    
    axes[0, 0].set_ylabel('Intrinsic Profile')
    axes[1, 0].set_ylabel('PSF Convolved')
    
    plt.suptitle('TEST 3: Extended Source Convolution - Smaller sources affected more', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'psf_test3_extended.png'), dpi=150)
    print(f"  Saved: psf_test3_extended.png")
    plt.close()
    
    # =========================================================================
    # TEST 4: Comparison - Current Approach vs Discrete Stars
    # =========================================================================
    print("\n[TEST 4] Smooth Profile vs Discrete Stars...")
    
    fig, axes = plt.subplots(2, 4, figsize=(18, 9))
    
    img_size = (151, 151)
    center = 75
    r_half = 15
    total_mag = 18  # Total cluster magnitude
    
    # --- Method A: Smooth Profile (Current Approach) ---
    profile = PlummerProfile(r_half=r_half, age=1.0, magnitude=total_mag)
    smooth_intrinsic = profile.generate_2d(img_size)
    smooth_convolved = convolve_with_psf(smooth_intrinsic, fwhm=PSF_FWHM_PIXELS)
    
    # --- Method B: Discrete Stars ---
    n_stars = 100
    total_flux = mag_to_flux(total_mag)
    
    # Generate star magnitudes from a simple distribution
    # (In reality, use a proper luminosity function)
    np.random.seed(42)
    star_fluxes = np.random.exponential(total_flux / n_stars, n_stars)
    star_fluxes = star_fluxes * (total_flux / np.sum(star_fluxes))  # Normalize to total
    
    # Place stars according to Plummer distribution
    # Plummer: P(r) ~ (1 + r^2/a^2)^(-5/2), so cumulative -> inverse sampling
    a = r_half / np.sqrt(np.sqrt(2) - 1)  # Plummer scale radius
    u = np.random.uniform(0, 1, n_stars)
    r_stars = a * np.sqrt(u**(-2/3) - 1)
    r_stars = np.clip(r_stars, 0, img_size[0]//2 - 5)  # Clip to image
    theta = np.random.uniform(0, 2*np.pi, n_stars)
    x_stars = center + r_stars * np.cos(theta)
    y_stars = center + r_stars * np.sin(theta)
    
    # Create discrete star image
    discrete_intrinsic = np.zeros(img_size)
    for x, y, flux in zip(x_stars, y_stars, star_fluxes):
        xi, yi = int(round(x)), int(round(y))
        if 0 <= xi < img_size[1] and 0 <= yi < img_size[0]:
            discrete_intrinsic[yi, xi] += flux
    
    # Convolve discrete stars
    discrete_convolved = convolve_with_psf(discrete_intrinsic, fwhm=PSF_FWHM_PIXELS)
    
    # Plot results
    # Row 1: Intrinsic
    ax = axes[0, 0]
    im = ax.imshow(smooth_intrinsic, cmap='hot', origin='lower', 
                   norm=LogNorm(vmin=0.1, vmax=smooth_intrinsic.max()))
    ax.set_title(f'Smooth Profile\n(intrinsic)')
    plt.colorbar(im, ax=ax, shrink=0.8)
    
    ax = axes[0, 1]
    im = ax.imshow(discrete_intrinsic, cmap='hot', origin='lower',
                   norm=LogNorm(vmin=0.1, vmax=max(discrete_intrinsic.max(), 1)))
    ax.scatter(x_stars, y_stars, s=5, c='cyan', alpha=0.5)
    ax.set_title(f'Discrete Stars (n={n_stars})\n(intrinsic)')
    plt.colorbar(im, ax=ax, shrink=0.8)
    
    ax = axes[0, 2]
    diff_intrinsic = smooth_intrinsic - discrete_convolved  # Compare smooth to convolved discrete
    im = ax.imshow(diff_intrinsic, cmap='RdBu', origin='lower', 
                   vmin=-np.abs(diff_intrinsic).max(), vmax=np.abs(diff_intrinsic).max())
    ax.set_title('Difference\n(smooth - discrete_conv)')
    plt.colorbar(im, ax=ax, shrink=0.8)
    
    ax = axes[0, 3]
    r = np.linspace(0, 60, 100)
    smooth_radial = smooth_intrinsic[center, center:center+60]
    ax.semilogy(np.arange(len(smooth_radial)), smooth_radial, 'b-', lw=2, label='Smooth')
    # Azimuthal average for discrete
    y_grid, x_grid = np.ogrid[:img_size[0], :img_size[1]]
    r_grid = np.sqrt((x_grid - center)**2 + (y_grid - center)**2)
    bins = np.arange(0, 60, 2)
    discrete_radial = []
    for b in bins[:-1]:
        mask = (r_grid >= b) & (r_grid < b+2)
        discrete_radial.append(np.mean(discrete_intrinsic[mask]))
    ax.semilogy(bins[:-1]+1, discrete_radial, 'r--', lw=2, label='Discrete (avg)')
    ax.set_xlabel('Radius (pixels)')
    ax.set_ylabel('Surface Brightness')
    ax.set_title('Radial Profiles')
    ax.legend()
    
    # Row 2: Convolved
    ax = axes[1, 0]
    im = ax.imshow(smooth_convolved, cmap='hot', origin='lower',
                   norm=LogNorm(vmin=0.1, vmax=smooth_convolved.max()))
    ax.set_title(f'Smooth Convolved\nflux={np.sum(smooth_convolved):.0f}')
    plt.colorbar(im, ax=ax, shrink=0.8)
    
    ax = axes[1, 1]
    im = ax.imshow(discrete_convolved, cmap='hot', origin='lower',
                   norm=LogNorm(vmin=0.1, vmax=discrete_convolved.max()))
    ax.set_title(f'Discrete Convolved\nflux={np.sum(discrete_convolved):.0f}')
    plt.colorbar(im, ax=ax, shrink=0.8)
    
    ax = axes[1, 2]
    diff_convolved = smooth_convolved - discrete_convolved
    im = ax.imshow(diff_convolved, cmap='RdBu', origin='lower',
                   vmin=-np.abs(diff_convolved).max(), vmax=np.abs(diff_convolved).max())
    ax.set_title('Difference (convolved)')
    plt.colorbar(im, ax=ax, shrink=0.8)
    
    ax = axes[1, 3]
    smooth_conv_radial = smooth_convolved[center, center:center+60]
    ax.semilogy(np.arange(len(smooth_conv_radial)), smooth_conv_radial, 'b-', lw=2, label='Smooth')
    discrete_conv_radial = []
    for b in bins[:-1]:
        mask = (r_grid >= b) & (r_grid < b+2)
        discrete_conv_radial.append(np.mean(discrete_convolved[mask]))
    ax.semilogy(bins[:-1]+1, discrete_conv_radial, 'r--', lw=2, label='Discrete')
    ax.set_xlabel('Radius (pixels)')
    ax.set_ylabel('Surface Brightness')
    ax.set_title('Convolved Radial Profiles')
    ax.legend()
    
    plt.suptitle(f'TEST 4: Smooth Profile vs Discrete Stars (m={total_mag}, r_half={r_half}px)', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'psf_test4_smooth_vs_discrete.png'), dpi=150)
    print(f"  Smooth total flux: {np.sum(smooth_convolved):.1f}")
    print(f"  Discrete total flux: {np.sum(discrete_convolved):.1f}")
    print(f"  Saved: psf_test4_smooth_vs_discrete.png")
    plt.close()
    
    # =========================================================================
    # TEST 5: Injection into Mock Background
    # =========================================================================
    print("\n[TEST 5] Injection into Mock Background...")
    
    fig, axes = plt.subplots(2, 4, figsize=(18, 9))
    
    np.random.seed(42)
    img_size = (201, 201)
    sky_level = 100
    noise_std = 15
    background = np.random.normal(loc=sky_level, scale=noise_std, size=img_size)
    
    # Inject clusters of different brightnesses
    test_mags = [18, 20, 22, 24]
    
    for i, mag in enumerate(test_mags):
        profile = PlummerProfile(r_half=12, age=1.0, magnitude=mag)
        cluster = profile.generate_2d(img_size)
        cluster_conv = convolve_with_psf(cluster, fwhm=PSF_FWHM_PIXELS)
        injected = background + cluster_conv
        
        # Cluster only
        ax = axes[0, i]
        im = ax.imshow(cluster_conv, cmap='hot', origin='lower',
                      norm=LogNorm(vmin=0.1, vmax=max(cluster_conv.max(), 1)))
        ax.set_title(f'm={mag}\npeak={cluster_conv.max():.1f}')
        plt.colorbar(im, ax=ax, shrink=0.8)
        
        # Injected
        ax = axes[1, i]
        vmin, vmax = sky_level - 3*noise_std, sky_level + cluster_conv.max()*0.5
        ax.imshow(injected, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
        ax.set_title(f'Injected\nS/N peak ~ {cluster_conv.max()/noise_std:.1f}')
        
        # Add circle at r_half
        circle = plt.Circle((100, 100), 12, fill=False, color='red', lw=2)
        ax.add_patch(circle)
    
    axes[0, 0].set_ylabel('Cluster Only')
    axes[1, 0].set_ylabel('Injected')
    
    plt.suptitle(f'TEST 5: Injection Visibility (sky={sky_level}, noise={noise_std})', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'psf_test5_injection.png'), dpi=150)
    print(f"  Saved: psf_test5_injection.png")
    plt.close()
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "="*70)
    print("PSF TEST SUMMARY")
    print("="*70)
    print(f"\nAll plots saved to: {os.path.abspath(output_dir)}")
    print("\nPlots generated:")
    print("  1. psf_test1_properties.png    - PSF shape and normalization")
    print("  2. psf_test2_point_source.png  - Point source flux conservation")
    print("  3. psf_test3_extended.png      - Extended source convolution")
    print("  4. psf_test4_smooth_vs_discrete.png - Smooth vs discrete stars")
    print("  5. psf_test5_injection.png     - Injection visibility test")
    print("\n" + "="*70)


if __name__ == '__main__':
    main()
