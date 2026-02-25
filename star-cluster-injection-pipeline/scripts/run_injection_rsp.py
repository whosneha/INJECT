"""
Example script to run the injection pipeline on the Rubin Science Platform.

Run this in a Jupyter notebook or as a script on RSP.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

# Import the injection pipeline
import sys
sys.path.insert(0, '/path/to/star-cluster-injection-pipeline')  # Update this path

from src.inject import inject_cluster, create_injection_catalog, inject_from_catalog
from src.light_profiles import PlummerProfile, KingProfile
from src.data_access import get_butler, load_coadd_image, pixel_to_sky

# LSST imports (only available on RSP)
from lsst.daf.butler import Butler
from lsst.geom import Point2D


def main():
    # ============ CONFIGURATION ============
    # Update these for your specific use case
    REPO = '/repo/main'  # Or your specific repo
    COLLECTION = 'LSSTComCam/runs/DRP/...'  # Update with actual collection
    
    DATA_ID = {
        'tract': 9615,
        'patch': 30,
        'band': 'i'
    }
    
    N_CLUSTERS = 10
    OUTPUT_DIR = './injection_results'
    
    # ============ LOAD DATA ============
    print("Loading Butler...")
    butler = Butler(REPO, collections=COLLECTION)
    
    print(f"Loading coadd for {DATA_ID}...")
    exposure = butler.get('deepCoadd', dataId=DATA_ID)
    
    # Get the image array
    image = exposure.image.array.copy()
    print(f"Image shape: {image.shape}")
    
    # ============ CREATE INJECTION CATALOG ============
    print(f"Creating catalog with {N_CLUSTERS} clusters...")
    catalog = create_injection_catalog(
        n_clusters=N_CLUSTERS,
        image_shape=image.shape,
        mag_range=(20, 24),
        r_half_range=(3, 20),
        profile_type='plummer',
        seed=42
    )
    
    # Print catalog summary
    print("\nInjection Catalog:")
    print("-" * 60)
    for entry in catalog:
        ra, dec = pixel_to_sky(exposure, entry['x'], entry['y'])
        print(f"  ID {entry['id']:3d}: x={entry['x']:5.0f}, y={entry['y']:5.0f}, "
              f"mag={entry['magnitude']:.1f}, r_h={entry['r_half']:.1f} px")
    
    # ============ INJECT CLUSTERS ============
    print("\nInjecting clusters using actual coadd PSF...")
    injected_image, injection_info = inject_from_catalog(
        image, 
        catalog, 
        exposure=exposure,  # Use actual PSF from coadd
        add_noise=True
    )
    
    # ============ VISUALIZE ============
    print("\nGenerating visualization...")
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    # Original image
    vmin, vmax = np.percentile(image, [1, 99])
    axes[0].imshow(image, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
    axes[0].set_title('Original Coadd')
    
    # Injected image
    axes[1].imshow(injected_image, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
    axes[1].set_title('With Injected Clusters')
    
    # Mark injection positions
    for entry in catalog:
        axes[1].scatter(entry['x'], entry['y'], s=100, facecolors='none', 
                       edgecolors='red', linewidth=2)
    
    # Difference image
    diff = injected_image - image
    axes[2].imshow(diff, cmap='hot', origin='lower', 
                   norm=LogNorm(vmin=0.1, vmax=diff.max()))
    axes[2].set_title('Injected Clusters Only')
    
    for ax in axes:
        ax.set_xlabel('X (pixels)')
        ax.set_ylabel('Y (pixels)')
    
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/injection_result.png', dpi=150)
    plt.show()
    
    # ============ SAVE RESULTS ============
    print(f"\nSaving results to {OUTPUT_DIR}...")
    
    # Save the catalog
    import json
    with open(f'{OUTPUT_DIR}/injection_catalog.json', 'w') as f:
        json.dump(injection_info, f, indent=2, default=float)
    
    print("Done!")
    
    return injected_image, injection_info


if __name__ == '__main__':
    main()
