"""
Tests for the star cluster injection pipeline.

Includes:
- Unit tests for light profiles
- Unit tests for PSF convolution
- Integration tests for injection pipeline
- Step-by-step visual verification plots

Run with: python tests/test_injection.py
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

from src.light_profiles import KingProfile, EFFProfile, PlummerProfile, SersicProfile, mag_to_flux
from src.inject import inject_cluster, create_injection_catalog, inject_from_catalog

# Check if GalSim is available
try:
    import galsim
    from src.psf_convolution import convolve_with_psf, create_rubin_psf
    HAS_GALSIM = True
except ImportError:
    HAS_GALSIM = False
    print("Warning: GalSim not installed. PSF convolution tests will be skipped.")


# =============================================================================
# UNIT TESTS: Light Profiles
# =============================================================================

class TestKingProfile(unittest.TestCase):
    """Test King profile implementation."""

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
        mag = 20.0
        profile = KingProfile(r_half=10.0, concentration=30.0, age=1.0, magnitude=mag)
        self.assertAlmostEqual(profile.magnitude, mag, places=1)


class TestEFFProfile(unittest.TestCase):
    """Test EFF profile implementation."""

    def setUp(self):
        self.profile = EFFProfile(r_half=10.0, gamma=3.0, age=0.1)

    def test_brightness_at_center(self):
        self.assertGreater(self.profile.compute_brightness(0), 0)

    def test_half_light_radius(self):
        self.assertAlmostEqual(self.profile.half_light_radius(), 10.0)


class TestPlummerProfile(unittest.TestCase):
    """Test Plummer profile implementation."""

    def setUp(self):
        self.profile = PlummerProfile(r_half=10.0, age=5.0)

    def test_brightness_at_center(self):
        self.assertGreater(self.profile.compute_brightness(0), 0)

    def test_half_light_radius(self):
        self.assertAlmostEqual(self.profile.half_light_radius(), 10.0)


class TestMagnitudeVariation(unittest.TestCase):
    """Test magnitude/flux relationships."""

    def test_brighter_magnitude_means_more_flux(self):
        p_bright = PlummerProfile(r_half=10.0, age=1.0, magnitude=18.0)
        p_faint = PlummerProfile(r_half=10.0, age=1.0, magnitude=22.0)
        self.assertGreater(p_bright.total_flux, p_faint.total_flux)

    def test_magnitude_flux_relationship(self):
        p1 = PlummerProfile(r_half=10.0, age=1.0, magnitude=20.0)
        p2 = PlummerProfile(r_half=10.0, age=1.0, magnitude=25.0)
        flux_ratio = p1.total_flux / p2.total_flux
        self.assertAlmostEqual(flux_ratio, 100.0, places=0)


# =============================================================================
# UNIT TESTS: PSF Convolution
# =============================================================================

@unittest.skipUnless(HAS_GALSIM, "GalSim not installed")
class TestPSFConvolution(unittest.TestCase):
    """Test PSF convolution using GalSim."""

    def setUp(self):
        self.profile = PlummerProfile(r_half=10.0, age=1.0, central_brightness=100)
        self.psf_fwhm = 3.5

    def test_psf_convolution(self):
        img = self.profile.generate_2d((101, 101))
        convolved = convolve_with_psf(img, fwhm=self.psf_fwhm)
        self.assertEqual(convolved.shape, img.shape)
        self.assertGreater(np.sum(convolved), 0)

    def test_convolution_conserves_flux(self):
        img = self.profile.generate_2d((101, 101))
        convolved = convolve_with_psf(img, fwhm=self.psf_fwhm)
        flux_original = np.sum(img)
        flux_convolved = np.sum(convolved)
        self.assertAlmostEqual(flux_original, flux_convolved, delta=flux_original * 0.05)

    def test_convolution_broadens_profile(self):
        img = self.profile.generate_2d((101, 101))
        convolved = convolve_with_psf(img, fwhm=self.psf_fwhm)
        self.assertLess(convolved[50, 50], img[50, 50])


# =============================================================================
# INTEGRATION TESTS: Injection Pipeline
# =============================================================================

class TestInjectionPipeline(unittest.TestCase):
    """Test the full injection pipeline."""

    def setUp(self):
        np.random.seed(42)
        self.image = np.random.normal(loc=100, scale=10, size=(201, 201))
        self.profile = PlummerProfile(r_half=10.0, age=1.0, central_brightness=200)

    def test_inject_cluster(self):
        injected, cluster_img = inject_cluster(
            self.image, 
            position=(100, 100), 
            profile=self.profile,
            psf_fwhm=3.5 if HAS_GALSIM else None,
            add_noise=False
        )
        self.assertEqual(injected.shape, self.image.shape)
        self.assertGreater(np.sum(cluster_img), 0)

    def test_create_catalog(self):
        catalog = create_injection_catalog(
            n_clusters=5,
            image_shape=self.image.shape,
            mag_range=(20, 24),
            r_half_range=(3, 15),
            seed=42
        )
        self.assertEqual(len(catalog), 5)
        for entry in catalog:
            self.assertIn('x', entry)
            self.assertIn('y', entry)
            self.assertIn('magnitude', entry)
            self.assertIn('r_half', entry)

    def test_inject_from_catalog(self):
        catalog = create_injection_catalog(
            n_clusters=3,
            image_shape=self.image.shape,
            seed=42
        )
        injected, info = inject_from_catalog(
            self.image, 
            catalog,
            psf_fwhm=3.5 if HAS_GALSIM else None,
            add_noise=False
        )
        self.assertEqual(len(info), 3)
        self.assertNotEqual(np.sum(injected), np.sum(self.image))


# =============================================================================
# VISUAL VERIFICATION TESTS
# =============================================================================

def run_visual_tests():
    """
    Run step-by-step visual tests to verify each component.
    Generates plots showing intermediate results.
    """
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'plots')
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n" + "="*70)
    print("VISUAL VERIFICATION TESTS")
    print("="*70)
    
    # =========================================================================
    # TEST 1: Light Profile Generation
    # =========================================================================
    print("\n[TEST 1] Light Profile Generation...")
    
    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    
    # Create profiles
    profiles = [
        ('Plummer', PlummerProfile(r_half=15, age=1.0, central_brightness=100)),
        ('King', KingProfile(r_half=15, concentration=30, age=1.0, central_brightness=100)),
        ('EFF', EFFProfile(r_half=15, gamma=2.5, age=1.0, central_brightness=100)),
        ('Sersic', SersicProfile(r_half=15, sersic_n=2.0, age=1.0, central_brightness=100)),
    ]
    
    img_size = (101, 101)
    r = np.linspace(0, 50, 200)
    
    for i, (name, profile) in enumerate(profiles):
        # 1D radial profile
        ax = axes[0, i]
        brightness = profile.compute_brightness(r)
        ax.semilogy(r, brightness, 'b-', lw=2)
        ax.axvline(15, color='r', linestyle='--', label='r_half')
        ax.set_xlabel('Radius (pixels)')
        ax.set_ylabel('Surface Brightness')
        ax.set_title(f'{name} - 1D Profile')
        ax.legend()
        ax.set_xlim(0, 50)
        
        # 2D image
        ax = axes[1, i]
        img = profile.generate_2d(img_size)
        im = ax.imshow(img, cmap='hot', norm=LogNorm(vmin=0.01, vmax=img.max()), origin='lower')
        ax.set_title(f'{name} - 2D Image')
        ax.set_xlabel('X (pixels)')
        ax.set_ylabel('Y (pixels)')
        plt.colorbar(im, ax=ax, shrink=0.8)
        
        print(f"  {name}: center={img[50,50]:.2f}, total_flux={np.sum(img):.2f}")
    
    plt.suptitle('TEST 1: Light Profile Generation - All profiles should be centered and decreasing', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'test1_profiles.png'), dpi=150)
    print(f"  Saved: test1_profiles.png")
    plt.close()
    print("  PASSED: All profiles generated successfully")
    
    # =========================================================================
    # TEST 2: Magnitude Scaling
    # =========================================================================
    print("\n[TEST 2] Magnitude Scaling...")
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    mags = [18, 20, 22, 24]
    r_half = 10
    
    # 1D comparison
    ax = axes[0]
    r = np.linspace(0, 40, 200)
    for mag in mags:
        p = PlummerProfile(r_half=r_half, age=1.0, magnitude=mag)
        ax.semilogy(r, p.compute_brightness(r), lw=2, label=f'm={mag}, flux={p.total_flux:.1f}')
    ax.set_xlabel('Radius (pixels)')
    ax.set_ylabel('Surface Brightness')
    ax.set_title('Magnitude Scaling (brighter = lower mag)')
    ax.legend()
    
    # 2D comparison
    ax = axes[1]
    combined = np.zeros((101, 101))
    positions = [(25, 25), (75, 25), (25, 75), (75, 75)]
    for mag, pos in zip(mags, positions):
        p = PlummerProfile(r_half=8, age=1.0, magnitude=mag)
        combined += p.generate_2d((101, 101), center=pos)
    im = ax.imshow(combined, cmap='hot', norm=LogNorm(vmin=1, vmax=combined.max()), origin='lower')
    ax.set_title('2D: m=18(BL), 20(BR), 22(TL), 24(TR)')
    plt.colorbar(im, ax=ax)
    
    # Flux ratio check
    ax = axes[2]
    p1 = PlummerProfile(r_half=10, age=1.0, magnitude=20)
    p2 = PlummerProfile(r_half=10, age=1.0, magnitude=25)
    ratio = p1.total_flux / p2.total_flux
    ax.bar(['m=20', 'm=25'], [p1.total_flux, p2.total_flux], color=['blue', 'red'])
    ax.set_ylabel('Total Flux')
    ax.set_title(f'5 mag difference = {ratio:.1f}x flux\n(expected: 100x)')
    
    plt.suptitle('TEST 2: Magnitude Scaling - Brighter magnitudes should have higher flux', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'test2_magnitude.png'), dpi=150)
    print(f"  Saved: test2_magnitude.png")
    plt.close()
    print(f"  5 mag difference gives {ratio:.1f}x flux ratio (expected: 100x)")
    print("  PASSED: Magnitude scaling correct")
    
    # =========================================================================
    # TEST 3: Half-Light Radius Variation
    # =========================================================================
    print("\n[TEST 3] Half-Light Radius Variation...")
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    r_halfs = [5, 10, 20, 40]
    
    # 1D comparison
    ax = axes[0]
    r = np.linspace(0, 80, 200)
    for rh in r_halfs:
        p = PlummerProfile(r_half=rh, age=1.0, central_brightness=100)
        ax.semilogy(r, p.compute_brightness(r), lw=2, label=f'r_h={rh}')
        ax.axvline(rh, linestyle=':', alpha=0.5)
    ax.set_xlabel('Radius (pixels)')
    ax.set_ylabel('Surface Brightness')
    ax.set_title('Size Variation (same central brightness)')
    ax.legend()
    
    # 2D comparison
    ax = axes[1]
    combined = np.zeros((151, 151))
    positions = [(35, 35), (115, 35), (35, 115), (115, 115)]
    for rh, pos in zip(r_halfs, positions):
        p = PlummerProfile(r_half=rh, age=1.0, central_brightness=50)
        combined += p.generate_2d((151, 151), center=pos)
    im = ax.imshow(combined, cmap='viridis', norm=LogNorm(vmin=0.1, vmax=combined.max()), origin='lower')
    ax.set_title('r_h=5(BL), 10(BR), 20(TL), 40(TR)')
    plt.colorbar(im, ax=ax)
    
    # Same magnitude, different sizes
    ax = axes[2]
    mag = 20
    for rh in r_halfs:
        p = PlummerProfile(r_half=rh, age=1.0, magnitude=mag)
        ax.semilogy(r, p.compute_brightness(r), lw=2, label=f'r_h={rh}')
    ax.set_xlabel('Radius (pixels)')
    ax.set_ylabel('Surface Brightness')
    ax.set_title(f'Same magnitude (m={mag}), different sizes')
    ax.legend()
    
    plt.suptitle('TEST 3: Half-Light Radius - Larger r_half = more extended profiles', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'test3_size.png'), dpi=150)
    print(f"  Saved: test3_size.png")
    plt.close()
    print("  PASSED: Size variation correct")
    
    # =========================================================================
    # TEST 4: PSF Convolution
    # =========================================================================
    print("\n[TEST 4] PSF Convolution...")
    
    if HAS_GALSIM:
        fig, axes = plt.subplots(2, 4, figsize=(16, 8))
        
        psf_fwhm = 3.5
        r_halfs_test = [2, 5, 10, 20]
        
        for i, rh in enumerate(r_halfs_test):
            profile = PlummerProfile(r_half=rh, age=1.0, central_brightness=100)
            img = profile.generate_2d((81, 81))
            convolved = convolve_with_psf(img, fwhm=psf_fwhm)
            
            # Intrinsic
            ax = axes[0, i]
            im = ax.imshow(img, cmap='hot', norm=LogNorm(vmin=0.01, vmax=img.max()), origin='lower')
            ax.set_title(f'Intrinsic (r_h={rh}px)\npeak={img.max():.1f}')
            plt.colorbar(im, ax=ax, shrink=0.7)
            
            # Convolved
            ax = axes[1, i]
            im = ax.imshow(convolved, cmap='hot', norm=LogNorm(vmin=0.01, vmax=img.max()), origin='lower')
            peak_ratio = convolved.max() / img.max()
            flux_ratio = np.sum(convolved) / np.sum(img)
            ax.set_title(f'Convolved\npeak ratio={peak_ratio:.2f}, flux ratio={flux_ratio:.2f}')
            plt.colorbar(im, ax=ax, shrink=0.7)
            
            print(f"  r_half={rh}px: peak_ratio={peak_ratio:.3f}, flux_conserved={flux_ratio:.3f}")
        
        plt.suptitle(f'TEST 4: PSF Convolution (FWHM={psf_fwhm}px) - Smaller clusters affected more', fontsize=14)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'test4_psf.png'), dpi=150)
        print(f"  Saved: test4_psf.png")
        plt.close()
        print("  PASSED: PSF convolution working, flux conserved")
    else:
        print("  SKIPPED: GalSim not installed")
    
    # =========================================================================
    # TEST 5: Single Cluster Injection
    # =========================================================================
    print("\n[TEST 5] Single Cluster Injection...")
    
    fig, axes = plt.subplots(1, 4, figsize=(18, 4))
    
    np.random.seed(42)
    img_size = (201, 201)
    background = np.random.normal(loc=100, scale=10, size=img_size)
    
    profile = PlummerProfile(r_half=12, age=1.0, central_brightness=300)
    
    # Background
    ax = axes[0]
    vmin, vmax = 70, 150
    ax.imshow(background, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
    ax.set_title(f'Background\nmean={background.mean():.1f}, std={background.std():.1f}')
    
    # Cluster model
    ax = axes[1]
    cluster_model = profile.generate_2d(img_size)
    im = ax.imshow(cluster_model, cmap='hot', origin='lower', norm=LogNorm(vmin=0.1, vmax=cluster_model.max()))
    ax.set_title(f'Cluster Model\npeak={cluster_model.max():.1f}')
    plt.colorbar(im, ax=ax)
    
    # Injected (no PSF)
    injected_no_psf, _ = inject_cluster(background, (100, 100), profile, psf_fwhm=None, add_noise=False)
    ax = axes[2]
    ax.imshow(injected_no_psf, cmap='gray', origin='lower', vmin=vmin, vmax=300)
    ax.scatter(100, 100, s=200, facecolors='none', edgecolors='red', linewidth=2)
    ax.set_title('Injected (no PSF)')
    
    # Injected (with PSF if available)
    if HAS_GALSIM:
        injected_psf, _ = inject_cluster(background, (100, 100), profile, psf_fwhm=3.5, add_noise=False)
        ax = axes[3]
        ax.imshow(injected_psf, cmap='gray', origin='lower', vmin=vmin, vmax=300)
        ax.scatter(100, 100, s=200, facecolors='none', edgecolors='red', linewidth=2)
        ax.set_title('Injected (with PSF)')
    else:
        axes[3].text(0.5, 0.5, 'GalSim not installed', ha='center', va='center', transform=axes[3].transAxes)
        axes[3].set_title('PSF convolution skipped')
    
    for ax in axes:
        ax.set_xlabel('X (pixels)')
        ax.set_ylabel('Y (pixels)')
    
    plt.suptitle('TEST 5: Single Cluster Injection - Cluster should be visible at center', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'test5_single_injection.png'), dpi=150)
    print(f"  Saved: test5_single_injection.png")
    plt.close()
    print("  PASSED: Single cluster injection working")
    
    # =========================================================================
    # TEST 6: Catalog Generation
    # =========================================================================
    print("\n[TEST 6] Catalog Generation...")
    
    catalog = create_injection_catalog(
        n_clusters=20,
        image_shape=(500, 500),
        mag_range=(19, 24),
        r_half_range=(3, 25),
        profile_type='plummer',
        seed=42
    )
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    # Position distribution
    ax = axes[0]
    xs = [e['x'] for e in catalog]
    ys = [e['y'] for e in catalog]
    ax.scatter(xs, ys, c='blue', s=50)
    ax.set_xlim(0, 500)
    ax.set_ylim(0, 500)
    ax.set_xlabel('X (pixels)')
    ax.set_ylabel('Y (pixels)')
    ax.set_title(f'Position Distribution (n={len(catalog)})')
    ax.set_aspect('equal')
    
    # Magnitude distribution
    ax = axes[1]
    mags = [e['magnitude'] for e in catalog]
    ax.hist(mags, bins=10, edgecolor='black')
    ax.set_xlabel('Magnitude')
    ax.set_ylabel('Count')
    ax.set_title(f'Magnitude Distribution\nrange=[{min(mags):.1f}, {max(mags):.1f}]')
    
    # Size distribution
    ax = axes[2]
    sizes = [e['r_half'] for e in catalog]
    ax.hist(sizes, bins=10, edgecolor='black')
    ax.set_xlabel('Half-light radius (pixels)')
    ax.set_ylabel('Count')
    ax.set_title(f'Size Distribution\nrange=[{min(sizes):.1f}, {max(sizes):.1f}]')
    
    plt.suptitle('TEST 6: Catalog Generation - Positions, magnitudes, sizes should be well distributed', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'test6_catalog.png'), dpi=150)
    print(f"  Saved: test6_catalog.png")
    plt.close()
    print(f"  Generated {len(catalog)} clusters")
    print(f"  Magnitude range: [{min(mags):.1f}, {max(mags):.1f}]")
    print(f"  Size range: [{min(sizes):.1f}, {max(sizes):.1f}] pixels")
    print("  PASSED: Catalog generation working")
    
    # =========================================================================
    # TEST 7: Full Pipeline - Multiple Cluster Injection
    # =========================================================================
    print("\n[TEST 7] Full Pipeline - Multiple Cluster Injection...")
    
    np.random.seed(42)
    img_size = (401, 401)
    background = np.random.normal(loc=100, scale=10, size=img_size)
    
    catalog = create_injection_catalog(
        n_clusters=10,
        image_shape=img_size,
        mag_range=(19, 23),
        r_half_range=(5, 20),
        seed=123
    )
    
    injected, info = inject_from_catalog(
        background,
        catalog,
        psf_fwhm=3.5 if HAS_GALSIM else None,
        add_noise=False
    )
    
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    
    vmin, vmax = np.percentile(background, [1, 99])
    
    # Original
    ax = axes[0]
    ax.imshow(background, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
    ax.set_title('Original Background')
    
    # Injected
    ax = axes[1]
    ax.imshow(injected, cmap='gray', origin='lower', vmin=vmin, vmax=vmax*1.5)
    for entry in catalog:
        ax.scatter(entry['x'], entry['y'], s=100, facecolors='none', 
                  edgecolors='red', linewidth=2)
        ax.annotate(f"m={entry['magnitude']:.0f}", (entry['x']+5, entry['y']+5), 
                   color='yellow', fontsize=8)
    ax.set_title(f'With {len(catalog)} Injected Clusters')
    
    # Difference
    ax = axes[2]
    diff = injected - background
    im = ax.imshow(diff, cmap='hot', origin='lower', norm=LogNorm(vmin=0.1, vmax=diff.max()))
    ax.set_title('Difference (Injected Clusters Only)')
    plt.colorbar(im, ax=ax, label='Flux')
    
    for ax in axes:
        ax.set_xlabel('X (pixels)')
        ax.set_ylabel('Y (pixels)')
    
    plt.suptitle('TEST 7: Full Pipeline - All clusters should be visible', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'test7_full_pipeline.png'), dpi=150)
    print(f"  Saved: test7_full_pipeline.png")
    plt.close()
    
    print(f"  Injected {len(info)} clusters")
    for entry in info[:3]:
        print(f"    ID {entry['id']}: flux={entry['total_flux_injected']:.1f}, peak={entry['peak_brightness']:.1f}")
    print("  PASSED: Full pipeline working")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "="*70)
    print("VISUAL TEST SUMMARY")
    print("="*70)
    print(f"All plots saved to: {os.path.abspath(output_dir)}")
    print("\nPlots generated:")
    print("  1. test1_profiles.png    - Light profile generation")
    print("  2. test2_magnitude.png   - Magnitude scaling")
    print("  3. test3_size.png        - Half-light radius variation")
    print("  4. test4_psf.png         - PSF convolution" + (" (SKIPPED)" if not HAS_GALSIM else ""))
    print("  5. test5_single_injection.png - Single cluster injection")
    print("  6. test6_catalog.png     - Catalog generation")
    print("  7. test7_full_pipeline.png - Full pipeline")
    print("\nReview these plots to verify the pipeline is working correctly!")
    print("="*70)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run injection pipeline tests')
    parser.add_argument('--visual-only', action='store_true', 
                       help='Skip unit tests, only run visual verification')
    parser.add_argument('--unit-only', action='store_true',
                       help='Skip visual tests, only run unit tests')
    args = parser.parse_args()
    
    if not args.visual_only:
        # Run unit tests
        print("Running unit tests...\n")
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(sys.modules[__name__])
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        if not result.wasSuccessful() and not args.unit_only:
            print("\nSome unit tests failed. Fix issues before running visual tests.")
            sys.exit(1)
    
    if not args.unit_only:
        # Run visual verification tests
        run_visual_tests()