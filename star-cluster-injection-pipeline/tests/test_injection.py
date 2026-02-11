import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

from src.light_profiles import KingProfile, EFFProfile, PlummerProfile, SersicProfile, mag_to_flux

# Check if GalSim is available
try:
    import galsim
    HAS_GALSIM = True
except ImportError:
    HAS_GALSIM = False
    print("Warning: GalSim not installed. PSF convolution tests will be skipped.")


class TestKingProfile(unittest.TestCase):

    def setUp(self):
        self.profile = KingProfile(r_half=10.0, concentration=30.0, age=1.0)

    def test_profile_creation(self):
        self.assertIsNotNone(self.profile)

    def test_brightness_at_center(self):
        b_center = self.profile.compute_brightness(0)
        self.assertGreater(b_center, 0)

    def test_brightness_decreases(self):
        b0 = self.profile.compute_brightness(0)
        b1 = self.profile.compute_brightness(5)
        b2 = self.profile.compute_brightness(10)
        self.assertGreater(b0, b1)
        self.assertGreater(b1, b2)

    def test_brightness_zero_beyond_tidal(self):
        b_beyond = self.profile.compute_brightness(self.profile.r_t + 1)
        self.assertEqual(b_beyond, 0.0)

    def test_2d_generation(self):
        img = self.profile.generate_2d((101, 101))
        self.assertEqual(img.shape, (101, 101))
        self.assertEqual(img[50, 50], img.max())

    def test_magnitude_sets_flux(self):
        """Test that specifying magnitude correctly sets total flux."""
        mag = 20.0
        profile = KingProfile(r_half=10.0, concentration=30.0, age=1.0, magnitude=mag)
        self.assertAlmostEqual(profile.magnitude, mag, places=1)

    def test_varying_r_half(self):
        """Test that varying r_half changes the profile size."""
        p1 = KingProfile(r_half=5.0, concentration=30.0, age=1.0)
        p2 = KingProfile(r_half=20.0, concentration=30.0, age=1.0)
        # Larger r_half should have larger core radius
        self.assertGreater(p2.r_c, p1.r_c)


class TestEFFProfile(unittest.TestCase):

    def setUp(self):
        self.profile = EFFProfile(r_half=10.0, gamma=3.0, age=0.1)

    def test_brightness_at_center(self):
        self.assertGreater(self.profile.compute_brightness(0), 0)

    def test_half_light_radius(self):
        r_h = self.profile.half_light_radius()
        self.assertAlmostEqual(r_h, 10.0)

    def test_magnitude_sets_flux(self):
        mag = 18.0
        profile = EFFProfile(r_half=10.0, gamma=3.0, age=0.1, magnitude=mag)
        self.assertAlmostEqual(profile.magnitude, mag, places=1)


class TestPlummerProfile(unittest.TestCase):

    def setUp(self):
        self.profile = PlummerProfile(r_half=10.0, age=5.0)

    def test_brightness_at_center(self):
        self.assertGreater(self.profile.compute_brightness(0), 0)

    def test_half_light_radius(self):
        self.assertAlmostEqual(self.profile.half_light_radius(), 10.0)


class TestMagnitudeVariation(unittest.TestCase):
    """Test that magnitude variations work correctly."""

    def test_brighter_magnitude_means_more_flux(self):
        """Smaller magnitude = brighter = more flux."""
        p_bright = PlummerProfile(r_half=10.0, age=1.0, magnitude=18.0)
        p_faint = PlummerProfile(r_half=10.0, age=1.0, magnitude=22.0)
        self.assertGreater(p_bright.total_flux, p_faint.total_flux)
        self.assertGreater(p_bright.central_brightness, p_faint.central_brightness)

    def test_magnitude_flux_relationship(self):
        """Test 5 mag difference = 100x flux difference."""
        p1 = PlummerProfile(r_half=10.0, age=1.0, magnitude=20.0)
        p2 = PlummerProfile(r_half=10.0, age=1.0, magnitude=25.0)
        flux_ratio = p1.total_flux / p2.total_flux
        self.assertAlmostEqual(flux_ratio, 100.0, places=0)


@unittest.skipUnless(HAS_GALSIM, "GalSim not installed")
class TestPSFConvolution(unittest.TestCase):
    """Test PSF convolution using GalSim."""

    def setUp(self):
        self.profile = PlummerProfile(r_half=10.0, age=1.0, magnitude=20.0)
        # Rubin-like PSF: ~0.7 arcsec FWHM, assuming 0.2 arcsec/pixel
        self.psf_fwhm_arcsec = 0.7
        self.pixel_scale = 0.2  # arcsec/pixel
        self.psf_fwhm_pixels = self.psf_fwhm_arcsec / self.pixel_scale  # ~3.5 pixels

    def test_psf_convolution(self):
        """Test that PSF convolution produces valid output."""
        from src.psf_convolution import convolve_with_psf
        
        img = self.profile.generate_2d((101, 101))
        convolved = convolve_with_psf(img, fwhm=self.psf_fwhm_pixels)
        
        self.assertEqual(convolved.shape, img.shape)
        self.assertGreater(np.sum(convolved), 0)

    def test_convolution_conserves_flux(self):
        """Test that convolution approximately conserves total flux."""
        from src.psf_convolution import convolve_with_psf
        
        img = self.profile.generate_2d((101, 101))
        convolved = convolve_with_psf(img, fwhm=self.psf_fwhm_pixels)
        
        flux_original = np.sum(img)
        flux_convolved = np.sum(convolved)
        self.assertAlmostEqual(flux_original, flux_convolved, delta=flux_original * 0.01)

    def test_convolution_broadens_profile(self):
        """Test that PSF convolution broadens the profile."""
        from src.psf_convolution import convolve_with_psf
        
        img = self.profile.generate_2d((101, 101))
        convolved = convolve_with_psf(img, fwhm=self.psf_fwhm_pixels)
        
        # Center should be dimmer after convolution (flux spread out)
        self.assertLess(convolved[50, 50], img[50, 50])


def generate_plots():
    """Generate publication-quality plots for PI presentation."""
    
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'plots')
    os.makedirs(output_dir, exist_ok=True)
    
    # Set up nice plotting style
    try:
        plt.style.use('seaborn-v0_8-whitegrid')
    except:
        plt.style.use('seaborn-whitegrid')
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.labelsize'] = 14
    plt.rcParams['axes.titlesize'] = 14
    
    # =========== PLOT 1: Varying Magnitude ===========
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    magnitudes = [18, 20, 22, 24]
    r_half = 15.0
    
    # 1a: Radial profiles at different magnitudes
    ax = axes[0, 0]
    r = np.linspace(0, 80, 500)
    colors = plt.cm.plasma(np.linspace(0.2, 0.9, len(magnitudes)))
    
    for mag, color in zip(magnitudes, colors):
        profile = PlummerProfile(r_half=r_half, age=1.0, magnitude=mag)
        ax.semilogy(r, profile.compute_brightness(r), color=color, lw=2.5, 
                   label=f'm = {mag} (flux = {profile.total_flux:.1f})')
    
    ax.set_xlabel('Radius (pixels)')
    ax.set_ylabel('Surface Brightness')
    ax.set_title(f'Plummer Profile: Varying Magnitude (r_half = {r_half} px)')
    ax.legend()
    ax.set_xlim(0, 80)
    ax.set_ylim(1e-2, 1e5)
    
    # 1b: 2D images at different magnitudes
    ax = axes[0, 1]
    img_size = (101, 101)
    combined = np.zeros(img_size)
    
    positions = [(25, 25), (75, 25), (25, 75), (75, 75)]
    for mag, pos in zip(magnitudes, positions):
        profile = PlummerProfile(r_half=10.0, age=1.0, magnitude=mag)
        img = profile.generate_2d(img_size, center=pos)
        combined += img
    
    im = ax.imshow(combined, cmap='hot', norm=LogNorm(vmin=1, vmax=combined.max()), origin='lower')
    ax.set_title('Four Clusters with m = 18, 20, 22, 24')
    ax.set_xlabel('X (pixels)')
    ax.set_ylabel('Y (pixels)')
    plt.colorbar(im, ax=ax, label='Surface Brightness')
    
    # Add magnitude labels
    for mag, pos in zip(magnitudes, positions):
        ax.annotate(f'm={mag}', xy=(pos[1], pos[0]), color='white', fontsize=10,
                   ha='center', va='bottom', fontweight='bold')
    
    # =========== Varying Half-Light Radius ===========
    r_halfs = [5, 10, 20, 40]
    magnitude = 20.0
    
    # 2a: Radial profiles at different r_half
    ax = axes[1, 0]
    r = np.linspace(0, 100, 500)
    colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(r_halfs)))
    
    for rh, color in zip(r_halfs, colors):
        profile = PlummerProfile(r_half=rh, age=1.0, magnitude=magnitude)
        ax.semilogy(r, profile.compute_brightness(r), color=color, lw=2.5,
                   label=f'r_half = {rh} px')
        ax.axvline(rh, color=color, linestyle=':', alpha=0.5)
    
    ax.set_xlabel('Radius (pixels)')
    ax.set_ylabel('Surface Brightness')
    ax.set_title(f'Plummer Profile: Varying Half-Light Radius (m = {magnitude})')
    ax.legend()
    ax.set_xlim(0, 100)
    ax.set_ylim(1e-3, 1e3)
    
    # 2b: 2D images at different r_half
    ax = axes[1, 1]
    img_size = (151, 151)
    combined = np.zeros(img_size)
    
    positions = [(35, 35), (115, 35), (35, 115), (115, 115)]
    for rh, pos in zip(r_halfs, positions):
        profile = PlummerProfile(r_half=rh, age=1.0, magnitude=magnitude)
        img = profile.generate_2d(img_size, center=pos)
        combined += img
    
    im = ax.imshow(combined, cmap='viridis', norm=LogNorm(vmin=0.1, vmax=combined.max()), origin='lower')
    ax.set_title(f'Four Clusters with r_half = 5, 10, 20, 40 px (same magnitude)')
    ax.set_xlabel('X (pixels)')
    ax.set_ylabel('Y (pixels)')
    plt.colorbar(im, ax=ax, label='Surface Brightness')
    
    for rh, pos in zip(r_halfs, positions):
        ax.annotate(f'r_h={rh}', xy=(pos[1], pos[0]), color='white', fontsize=10,
                   ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'magnitude_rhalf_variation.png'), dpi=150, bbox_inches='tight')
    plt.savefig(os.path.join(output_dir, 'magnitude_rhalf_variation.pdf'), bbox_inches='tight')
    print(f"Saved: magnitude_rhalf_variation.png/pdf")
    plt.close()
    
    # =========== PLOT 3: Combined Parameter Space ===========
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    magnitudes = [19, 21, 23]
    r_halfs = [8, 20]
    
    for i, rh in enumerate(r_halfs):
        for j, mag in enumerate(magnitudes):
            ax = axes[i, j]
            profile = PlummerProfile(r_half=rh, age=1.0, magnitude=mag)
            img = profile.generate_2d((101, 101))
            
            im = ax.imshow(img, cmap='hot', norm=LogNorm(vmin=0.01, vmax=img.max()), origin='lower')
            ax.set_title(f'm = {mag}, r_half = {rh} px\nFlux = {profile.total_flux:.1f}')
            ax.set_xlabel('X (pixels)')
            ax.set_ylabel('Y (pixels)')
            plt.colorbar(im, ax=ax, shrink=0.8)
    
    plt.suptitle('Star Cluster Parameter Space: Magnitude vs Half-Light Radius', fontsize=16, y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'parameter_space_grid.png'), dpi=150, bbox_inches='tight')
    plt.savefig(os.path.join(output_dir, 'parameter_space_grid.pdf'), bbox_inches='tight')
    print(f"Saved: parameter_space_grid.png/pdf")
    plt.close()
    
    # =========== PLOT 4: Profile Comparison ===========
    fig, ax = plt.subplots(figsize=(10, 7))
    
    r_half = 15.0
    mag = 20.0
    r = np.linspace(0.1, 100, 500)
    
    king = KingProfile(r_half=r_half, concentration=30.0, age=10.0, magnitude=mag)
    eff = EFFProfile(r_half=r_half, gamma=2.5, age=0.1, magnitude=mag)
    plummer = PlummerProfile(r_half=r_half, age=5.0, magnitude=mag)
    sersic = SersicProfile(r_half=r_half, sersic_n=2.0, age=1.0, magnitude=mag)
    
    ax.semilogy(r, king.compute_brightness(r), 'b-', lw=2.5, label=f'King (c={king.concentration})')
    ax.semilogy(r, eff.compute_brightness(r), 'r--', lw=2.5, label=f'EFF (γ={eff.gamma})')
    ax.semilogy(r, plummer.compute_brightness(r), 'g:', lw=2.5, label='Plummer')
    ax.semilogy(r, sersic.compute_brightness(r), 'm-.', lw=2.5, label=f'Sérsic (n={sersic.sersic_n})')
    
    ax.axvline(r_half, color='gray', linestyle='--', alpha=0.7, label=f'r_half = {r_half} px')
    
    ax.set_xlabel('Radius (pixels)')
    ax.set_ylabel('Surface Brightness')
    ax.set_title(f'Profile Comparison: Same r_half ({r_half} px) and Magnitude ({mag})')
    ax.set_xlim(0, 100)
    ax.set_ylim(1e-3, 1e3)
    ax.legend(loc='upper right', fontsize=11)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'profile_comparison.png'), dpi=150, bbox_inches='tight')
    plt.savefig(os.path.join(output_dir, 'profile_comparison.pdf'), bbox_inches='tight')
    print(f"Saved: profile_comparison.png/pdf")
    plt.close()
    
    # =========== PLOT 5: Mock Injection with Varying Parameters ===========
    # Use direct flux scaling instead of magnitude for clearer visualization
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    np.random.seed(42)
    img_size = (201, 201)
    sky_level = 100
    noise_level = 10
    background = np.random.normal(loc=sky_level, scale=noise_level, size=img_size)
    
    # Row 1: Varying brightness (using central_brightness directly for control)
    axes[0, 0].imshow(background, cmap='gray', origin='lower', vmin=70, vmax=250)
    axes[0, 0].set_title(f'Background\n(sky={sky_level}, noise={noise_level})')
    
    # Use high central brightness values that are clearly above noise
    bright_values = [500, 50]  # Very bright vs moderately bright
    for ax, cb in zip(axes[0, 1:], bright_values):
        cluster = PlummerProfile(r_half=15, age=1.0, central_brightness=cb)
        cluster_img = cluster.generate_2d(img_size)
        injected = background + cluster_img
        vmax = sky_level + cb * 0.5
        ax.imshow(injected, cmap='gray', origin='lower', vmin=70, vmax=vmax)
        ax.set_title(f'Injected: I_0 = {cb}\n(peak = {cluster_img.max():.0f})')
    
    # Row 2: Varying size (same total flux)
    axes[1, 0].imshow(background, cmap='gray', origin='lower', vmin=70, vmax=250)
    axes[1, 0].set_title(f'Background\n(sky={sky_level}, noise={noise_level})')
    
    # Same central brightness, different sizes
    r_halfs_demo = [5, 25]
    for ax, rh in zip(axes[1, 1:], r_halfs_demo):
        cluster = PlummerProfile(r_half=rh, age=1.0, central_brightness=200)
        cluster_img = cluster.generate_2d(img_size)
        injected = background + cluster_img
        ax.imshow(injected, cmap='gray', origin='lower', vmin=70, vmax=300)
        ax.set_title(f'Injected: r_half = {rh} px\n(peak = {cluster_img.max():.0f})')
    
    for ax in axes.flat:
        ax.set_xlabel('X (pixels)')
        ax.set_ylabel('Y (pixels)')
    
    plt.suptitle('Injection Examples: Varying Brightness (top) and Size (bottom)', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'injection_variations.png'), dpi=150, bbox_inches='tight')
    plt.savefig(os.path.join(output_dir, 'injection_variations.pdf'), bbox_inches='tight')
    print(f"Saved: injection_variations.png/pdf")
    plt.close()
    
    # =========== PLOT 6-8: PSF Convolution ===========
    if HAS_GALSIM:
        from src.psf_convolution import convolve_with_psf, create_rubin_psf
        
        # Rubin-like PSF parameters
        psf_fwhm_arcsec = 0.7  # typical seeing
        pixel_scale = 0.2  # Rubin pixel scale in arcsec/pixel
        psf_fwhm_pixels = psf_fwhm_arcsec / pixel_scale  # ~3.5 pixels
        
        # =========== PLOT 6: PSF effect on COMPACT clusters ===========
        fig, axes = plt.subplots(2, 4, figsize=(18, 9))
        
        img_size = (101, 101)
        center = 50
        
        # Create PSF image for display
        psf_img = create_rubin_psf(psf_fwhm_pixels, img_size)
        
        # Use SMALL r_half values where PSF matters more
        profiles = [
            (PlummerProfile(r_half=2.0, age=1.0, central_brightness=100), 'Plummer (r_h=2px)'),
            (PlummerProfile(r_half=5.0, age=1.0, central_brightness=100), 'Plummer (r_h=5px)'),
            (PlummerProfile(r_half=15.0, age=1.0, central_brightness=100), 'Plummer (r_h=15px)'),
        ]
        
        # Row 1: Intrinsic profiles
        ax = axes[0, 0]
        im = ax.imshow(psf_img, cmap='hot', norm=LogNorm(vmin=1e-6, vmax=psf_img.max()), origin='lower')
        ax.set_title(f'Rubin PSF\nFWHM = {psf_fwhm_arcsec}" ({psf_fwhm_pixels:.1f} px)')
        ax.set_xlabel('X (pixels)')
        ax.set_ylabel('Y (pixels)')
        plt.colorbar(im, ax=ax, shrink=0.8)
        
        for i, (profile, name) in enumerate(profiles):
            ax = axes[0, i+1]
            img = profile.generate_2d(img_size)
            im = ax.imshow(img, cmap='hot', norm=LogNorm(vmin=1e-3, vmax=img.max()), origin='lower')
            ax.set_title(f'Intrinsic: {name}')
            ax.set_xlabel('X (pixels)')
            ax.set_ylabel('Y (pixels)')
            plt.colorbar(im, ax=ax, shrink=0.8)
        
        # Row 2: Convolved profiles
        ax = axes[1, 0]
        ax.text(0.5, 0.5, f'PSF FWHM:\n{psf_fwhm_arcsec} arcsec\n{psf_fwhm_pixels:.1f} pixels\n\nSmaller clusters\nare more affected!', 
                ha='center', va='center', fontsize=12, transform=ax.transAxes)
        ax.set_title('Convolution Info')
        ax.axis('off')
        
        for i, (profile, name) in enumerate(profiles):
            ax = axes[1, i+1]
            img = profile.generate_2d(img_size)
            convolved = convolve_with_psf(img, fwhm=psf_fwhm_pixels)
            im = ax.imshow(convolved, cmap='hot', norm=LogNorm(vmin=1e-3, vmax=img.max()), origin='lower')
            ax.set_title(f'Convolved: {name}')
            ax.set_xlabel('X (pixels)')
            ax.set_ylabel('Y (pixels)')
            plt.colorbar(im, ax=ax, shrink=0.8)
        
        plt.suptitle('PSF Convolution: Intrinsic vs Observed (smaller clusters affected more)', fontsize=16, y=1.02)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'psf_convolution_2d.png'), dpi=150, bbox_inches='tight')
        plt.savefig(os.path.join(output_dir, 'psf_convolution_2d.pdf'), bbox_inches='tight')
        print(f"Saved: psf_convolution_2d.png/pdf")
        plt.close()
        
        # =========== PLOT 7: Radial Profile Comparison ===========
        fig, axes = plt.subplots(1, 3, figsize=(16, 5))
        
        r_halfs = [2, 5, 15]  # Small to large
        
        for ax, r_half in zip(axes, r_halfs):
            profile = PlummerProfile(r_half=r_half, age=1.0, central_brightness=100)
            
            img = profile.generate_2d(img_size)
            convolved = convolve_with_psf(img, fwhm=psf_fwhm_pixels)
            
            # Extract radial profiles
            r = np.arange(0, center)
            intrinsic_radial = img[center, center:center+len(r)]
            convolved_radial = convolved[center, center:center+len(r)]
            
            ax.semilogy(r, intrinsic_radial, 'b-', lw=2.5, label='Intrinsic')
            ax.semilogy(r, convolved_radial, 'r--', lw=2.5, label='Convolved')
            ax.axvline(r_half, color='blue', linestyle=':', alpha=0.7, label=f'r_half = {r_half} px')
            ax.axvline(psf_fwhm_pixels/2, color='gray', linestyle='--', alpha=0.7, 
                      label=f'PSF HWHM = {psf_fwhm_pixels/2:.1f} px')
            
            # Calculate and show the change
            peak_ratio = convolved_radial[0] / intrinsic_radial[0]
            ax.text(0.95, 0.95, f'Peak ratio: {peak_ratio:.2f}', transform=ax.transAxes,
                   ha='right', va='top', fontsize=11, bbox=dict(boxstyle='round', facecolor='wheat'))
            
            ax.set_xlabel('Radius (pixels)')
            ax.set_ylabel('Surface Brightness')
            ax.set_title(f'r_half = {r_half} px')
            ax.legend(fontsize=10, loc='lower left')
            ax.set_xlim(0, 40)
            ax.set_ylim(1e-2, intrinsic_radial.max() * 2)
        
        plt.suptitle('Radial Profile: PSF Effect is Strongest for Compact Clusters', fontsize=14)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'psf_convolution_radial.png'), dpi=150, bbox_inches='tight')
        plt.savefig(os.path.join(output_dir, 'psf_convolution_radial.pdf'), bbox_inches='tight')
        print(f"Saved: psf_convolution_radial.png/pdf")
        plt.close()
        
        # =========== PLOT 8: Mock Injection with PSF ===========
        fig, axes = plt.subplots(2, 4, figsize=(18, 9))
        
        np.random.seed(42)
        img_size = (151, 151)
        sky_level = 100
        noise_level = 10
        background = np.random.normal(loc=sky_level, scale=noise_level, size=img_size)
        
        # Row 1: Compact cluster (r_half=3) - PSF matters a lot
        cluster_compact = PlummerProfile(r_half=3, age=1.0, central_brightness=300)
        compact_intrinsic = cluster_compact.generate_2d(img_size)
        compact_convolved = convolve_with_psf(compact_intrinsic, fwhm=psf_fwhm_pixels)
        
        axes[0, 0].imshow(background, cmap='gray', origin='lower', vmin=70, vmax=200)
        axes[0, 0].set_title('Background')
        
        axes[0, 1].imshow(compact_intrinsic, cmap='hot', origin='lower', 
                         norm=LogNorm(vmin=0.1, vmax=compact_intrinsic.max()))
        axes[0, 1].set_title(f'Compact Cluster (r_h=3px)\nIntrinsic (peak={compact_intrinsic.max():.0f})')
        
        axes[0, 2].imshow(compact_convolved, cmap='hot', origin='lower',
                         norm=LogNorm(vmin=0.1, vmax=compact_intrinsic.max()))
        axes[0, 2].set_title(f'PSF Convolved\n(peak={compact_convolved.max():.0f})')
        
        injected_compact = background + compact_convolved
        axes[0, 3].imshow(injected_compact, cmap='gray', origin='lower', vmin=70, vmax=250)
        axes[0, 3].set_title('Final Injected')
        
        # Row 2: Extended cluster (r_half=15) - PSF matters less
        cluster_extended = PlummerProfile(r_half=15, age=1.0, central_brightness=300)
        extended_intrinsic = cluster_extended.generate_2d(img_size)
        extended_convolved = convolve_with_psf(extended_intrinsic, fwhm=psf_fwhm_pixels)
        
        axes[1, 0].imshow(background, cmap='gray', origin='lower', vmin=70, vmax=200)
        axes[1, 0].set_title('Background')
        
        axes[1, 1].imshow(extended_intrinsic, cmap='hot', origin='lower', 
                         norm=LogNorm(vmin=0.1, vmax=extended_intrinsic.max()))
        axes[1, 1].set_title(f'Extended Cluster (r_h=15px)\nIntrinsic (peak={extended_intrinsic.max():.0f})')
        
        axes[1, 2].imshow(extended_convolved, cmap='hot', origin='lower',
                         norm=LogNorm(vmin=0.1, vmax=extended_intrinsic.max()))
        axes[1, 2].set_title(f'PSF Convolved\n(peak={extended_convolved.max():.0f})')
        
        injected_extended = background + extended_convolved
        axes[1, 3].imshow(injected_extended, cmap='gray', origin='lower', vmin=70, vmax=250)
        axes[1, 3].set_title('Final Injected')
        
        for ax in axes.flat:
            ax.set_xlabel('X (pixels)')
            ax.set_ylabel('Y (pixels)')
        
        plt.suptitle(f'Injection Pipeline: Compact (top) vs Extended (bottom) Clusters\nPSF FWHM = {psf_fwhm_pixels:.1f} pixels', fontsize=14)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'injection_with_psf.png'), dpi=150, bbox_inches='tight')
        plt.savefig(os.path.join(output_dir, 'injection_with_psf.pdf'), bbox_inches='tight')
        print(f"Saved: injection_with_psf.png/pdf")
        plt.close()
        
    else:
        print("Skipping PSF convolution plots (GalSim not installed)")
    
    print(f"\nAll plots saved to: {os.path.abspath(output_dir)}")


if __name__ == '__main__':
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Generate plots if tests pass
    if result.wasSuccessful():
        print("\n" + "="*60)
        print("Generating plots for PI presentation...")
        print("="*60 + "\n")
        generate_plots()
    else:
        print("\nFix test failures before generating plots.")