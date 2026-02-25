"""
Unified injection script for star cluster injection pipeline.
Auto-detects environment (RSP vs remote) and uses appropriate data access.

Usage:
    # On RSP (Butler access):
    python run_injection.py --tract 9615 --patch 30 --band i --n-clusters 10
    
    # Remote with TAP (requires token):
    python run_injection.py --token YOUR_TOKEN --ra 55.0 --dec -30.0 --n-clusters 10
    
Get your token from: https://data.lsst.cloud/auth/tokens
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_access import RubinDataAccess, HAS_LSST
from src.inject import create_injection_catalog, inject_from_catalog
from src.light_profiles import PlummerProfile, KingProfile


def main():
    parser = argparse.ArgumentParser(
        description='Inject star clusters into Rubin images',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # On RSP with Butler:
    python run_injection.py --repo /repo/main --collection LSSTComCam/runs/DRP/... \\
                            --tract 9615 --patch 30 --band i
    
    # Remote with TAP service:
    python run_injection.py --token YOUR_TOKEN --ra 55.0 --dec -30.0
        """
    )
    
    # Common arguments
    parser.add_argument('--n-clusters', type=int, default=10, help='Number of clusters to inject')
    parser.add_argument('--band', default='i', help='Filter band (u,g,r,i,z,y)')
    parser.add_argument('--profile', default='plummer', choices=['plummer', 'king', 'eff', 'sersic'],
                       help='Light profile type')
    parser.add_argument('--mag-min', type=float, default=20.0, help='Minimum magnitude')
    parser.add_argument('--mag-max', type=float, default=24.0, help='Maximum magnitude')
    parser.add_argument('--r-half-min', type=float, default=3.0, help='Minimum half-light radius (pixels)')
    parser.add_argument('--r-half-max', type=float, default=20.0, help='Maximum half-light radius (pixels)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--no-noise', action='store_true', help='Disable Poisson noise')
    
    # Add method argument
    parser.add_argument('--method', default='smooth', choices=['smooth', 'discrete'],
                       help='Cluster generation method: smooth (extended source) or discrete (individual stars)')
    parser.add_argument('--n-stars-min', type=int, default=50, help='Min stars per cluster (discrete mode)')
    parser.add_argument('--n-stars-max', type=int, default=500, help='Max stars per cluster (discrete mode)')
    parser.add_argument('--imf', default='kroupa', choices=['kroupa', 'chabrier', 'salpeter'],
                       help='Initial mass function (discrete mode)')
    
    # RSP/Butler arguments
    parser.add_argument('--repo', type=str, help='Butler repository path (RSP mode)')
    parser.add_argument('--collection', type=str, help='Butler collection name (RSP mode)')
    parser.add_argument('--tract', type=int, help='Tract number (RSP mode)')
    parser.add_argument('--patch', type=int, help='Patch number (RSP mode)')
    
    # TAP/Remote arguments
    parser.add_argument('--token', type=str, help='Rubin access token (TAP mode)')
    parser.add_argument('--ra', type=float, help='Center RA in degrees (TAP mode)')
    parser.add_argument('--dec', type=float, help='Center Dec in degrees (TAP mode)')
    parser.add_argument('--size', type=float, default=120, help='Cutout size in arcseconds (TAP mode)')
    
    args = parser.parse_args()
    
    # Output directory (use existing plots folder)
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'plots')
    os.makedirs(output_dir, exist_ok=True)
    
    # ============ DETERMINE MODE AND INITIALIZE ============
    if args.token is not None:
        mode = 'tap'
        print("Using TAP service (remote access)")
        data_access = RubinDataAccess(mode='tap', token=args.token)
    elif HAS_LSST and args.repo is not None:
        mode = 'rsp'
        print("Using Butler (RSP access)")
        data_access = RubinDataAccess(mode='rsp', repo=args.repo, collection=args.collection)
    elif HAS_LSST:
        mode = 'rsp'
        print("Detected RSP environment, using Butler")
        data_access = RubinDataAccess(mode='rsp')
    else:
        print("No data access available. Using mock data for demonstration.")
        mode = 'mock'
        data_access = None
    
    # ============ LOAD IMAGE ============
    print("\nLoading image...")
    
    if mode == 'rsp':
        if args.tract is None or args.patch is None:
            parser.error("RSP mode requires --tract and --patch")
        data_id = {'tract': args.tract, 'patch': args.patch, 'band': args.band}
        image, metadata = data_access.load_coadd(data_id=data_id)
        location_str = f"tract={args.tract}, patch={args.patch}"
        
    elif mode == 'tap':
        if args.ra is None or args.dec is None:
            parser.error("TAP mode requires --ra and --dec")
        image, metadata = data_access.load_coadd(
            ra=args.ra, dec=args.dec, size_arcsec=args.size, band=args.band
        )
        location_str = f"RA={args.ra:.4f}, Dec={args.dec:.4f}"
        
    else:  # mock mode
        np.random.seed(args.seed)
        image = np.random.normal(loc=100, scale=15, size=(500, 500))
        metadata = {'psf_fwhm_pixels': 3.5, 'mode': 'mock'}
        location_str = "mock data"
    
    print(f"Image shape: {image.shape}")
    print(f"Location: {location_str}")
    
    # Get PSF FWHM
    if data_access is not None:
        psf_fwhm = data_access.get_psf_fwhm(metadata)
    else:
        psf_fwhm = metadata.get('psf_fwhm_pixels', 3.5)
    print(f"PSF FWHM: {psf_fwhm:.2f} pixels")
    
    # ============ CREATE INJECTION CATALOG ============
    print(f"\nCreating catalog with {args.n_clusters} clusters...")
    print(f"  Method: {args.method}")
    
    catalog = create_injection_catalog(
        n_clusters=args.n_clusters,
        image_shape=image.shape,
        mag_range=(args.mag_min, args.mag_max),
        r_half_range=(args.r_half_min, args.r_half_max),
        profile_type=args.profile,
        method=args.method,  # <-- Use the method argument
        n_stars_range=(args.n_stars_min, args.n_stars_max),
        imf=args.imf,
        edge_buffer=50,
        seed=args.seed
    )
    
    print("\nInjection Catalog:")
    print("-" * 60)
    for entry in catalog:
        print(f"  ID {entry['id']:3d}: x={entry['x']:5.0f}, y={entry['y']:5.0f}, "
              f"mag={entry['magnitude']:.1f}, r_h={entry['r_half']:.1f} px")
    
    # ============ INJECT CLUSTERS ============
    print("\nInjecting clusters...")
    
    # Get exposure for RSP mode (for actual PSF)
    exposure = metadata.get('exposure') if mode == 'rsp' else None
    
    injected_image, injection_info = inject_from_catalog(
        image,
        catalog,
        psf_fwhm=psf_fwhm,
        exposure=exposure,
        add_noise=not args.no_noise
    )
    
    # ============ VISUALIZE ============
    print("\nGenerating visualization...")
    
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    
    vmin, vmax = np.percentile(image, [1, 99])
    
    axes[0].imshow(image, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
    axes[0].set_title(f'Original Image\n{location_str}')
    
    axes[1].imshow(injected_image, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
    axes[1].set_title(f'With {args.n_clusters} Injected Clusters')
    for entry in catalog:
        axes[1].scatter(entry['x'], entry['y'], s=80, facecolors='none',
                       edgecolors='red', linewidth=1.5)
    
    diff = injected_image - image
    diff_pos = np.maximum(diff, 0.1)
    im = axes[2].imshow(diff_pos, cmap='hot', origin='lower',
                        norm=LogNorm(vmin=0.1, vmax=max(diff.max(), 1)))
    axes[2].set_title('Injected Clusters Only')
    plt.colorbar(im, ax=axes[2], label='Flux')
    
    for ax in axes:
        ax.set_xlabel('X (pixels)')
        ax.set_ylabel('Y (pixels)')
    
    plt.suptitle(f'Star Cluster Injection Pipeline - {args.band}-band', fontsize=14)
    plt.tight_layout()
    
    output_path = os.path.join(output_dir, 'injection_result.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()
    
    # ============ SAVE CATALOG ============
    catalog_path = os.path.join(output_dir, 'injection_catalog.json')
    
    save_data = {
        'metadata': {
            'mode': mode,
            'band': args.band,
            'image_shape': list(image.shape),
            'psf_fwhm_pixels': float(psf_fwhm),
            'n_clusters': args.n_clusters,
            'location': location_str,
            'profile_type': args.profile
        },
        'catalog': injection_info
    }
    
    with open(catalog_path, 'w') as f:
        json.dump(save_data, f, indent=2, default=float)
    print(f"Saved: {catalog_path}")
    
    print("\nDone!")
    
    return injected_image, injection_info


if __name__ == '__main__':
    main()
