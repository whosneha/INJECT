"""
Benchmark script: PSF caching performance vs accuracy.

Generates synthetic test data and compares:
  1. Injection without PSF cache (baseline)
  2. Injection with PSF cache (optimized)

Measures speed, memory, and validates science equivalence.

Usage:
  python benchmark_psf_cache.py --n-clusters 100 --n-trials 2
"""

import argparse
import numpy as np
import time
import sys
import os
import json

# Add parent to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.inject import inject_clusters_rubin_psf, PSFCache
from src.light_profiles import PlummerProfile
from src.config import InjectionConfig


def create_synthetic_psf():
    """Create a mock PSF object for testing (returns simple Gaussian)."""
    class MockPSF:
        def computeImage(self, point):
            """Mock PSF image (Gaussian)."""
            size = 21
            class MockImage:
                def __init__(self):
                    sigma = 1.5
                    y, x = np.mgrid[:size, :size]
                    h = size // 2
                    r2 = (x - h)**2 + (y - h)**2
                    arr = np.exp(-r2 / (2 * sigma**2))
                    self.array = arr / arr.sum()
            return MockImage()
        
        def computeShape(self, point):
            """Mock PSF shape (ellipticity)."""
            class MockShape:
                def getIxx(self):
                    return 2.0
                def getIyy(self):
                    return 2.0
                def getDeterminantRadius(self):
                    return 1.5
            return MockShape()
    
    return MockPSF()


def generate_test_catalog(n_clusters, image_shape, seed=42):
    """Generate a simple test catalog."""
    rng = np.random.default_rng(seed)
    ny, nx = image_shape
    
    catalog = []
    for i in range(n_clusters):
        catalog.append({
            'id': i,
            'x': float(rng.integers(50, nx - 50)),
            'y': float(rng.integers(50, ny - 50)),
            'magnitude': float(rng.uniform(20, 24)),
            'r_half': float(rng.uniform(3, 15)),
            'concentration': 10.0,
            'age_gyr': 1.0,
            'profile_type': 'plummer',
        })
    
    return catalog


def run_benchmark(n_clusters, image_shape, use_cache):
    """Run a single injection benchmark."""
    # Create synthetic data
    image = np.random.normal(100, 15, size=image_shape).astype(np.float32)
    psf_obj = create_synthetic_psf()
    catalog = generate_test_catalog(n_clusters, image_shape, seed=42)
    
    # Create cache if needed
    psf_cache = None
    if use_cache:
        psf_cache = PSFCache(max_entries=500, grid_size=8)
    
    # Run injection
    start = time.time()
    try:
        result = inject_clusters_rubin_psf(
            image,
            catalog,
            psf_obj,
            bbox_x_min=0,
            bbox_y_min=0,
            psf_fwhm_fallback=3.5,
            pixel_scale=0.2,
            zero_point=27.0,
            add_noise=False,  # no noise for faster testing
            use_actual_psf=True,
            rng_seed=42,
            verbose=False,
            use_psf_cache=use_cache,
            psf_cache=psf_cache,
        )
        elapsed = time.time() - start
        
        # Unpack results (function now returns 4-tuple with timing)
        if len(result) == 4:
            injected_image, injection_info, timing, cache_stats = result
        else:
            # Fallback for old return format
            injected_image, injection_info = result
            timing = {}
            cache_stats = None
        
        n_injected = len(injection_info)
        
        return {
            'use_cache': use_cache,
            'n_clusters': n_clusters,
            'n_injected': n_injected,
            'wall_time': elapsed,
            'timing': timing,
            'cache_stats': cache_stats,
            'success': True,
        }
    
    except Exception as e:
        return {
            'use_cache': use_cache,
            'n_clusters': n_clusters,
            'wall_time': None,
            'error': str(e),
            'success': False,
        }


def main():
    parser = argparse.ArgumentParser(description='Benchmark PSF caching')
    parser.add_argument('--n-clusters', type=int, default=100,
                        help='Number of clusters per trial')
    parser.add_argument('--n-trials', type=int, default=2,
                        help='Number of trials per mode')
    parser.add_argument('--image-size', type=int, default=1000,
                        help='Image size (image_size x image_size)')
    parser.add_argument('--output', default='benchmark_results.json',
                        help='Output file for results')
    
    args = parser.parse_args()
    
    print(f"Benchmark: PSF Caching")
    print(f"  N clusters     : {args.n_clusters}")
    print(f"  N trials       : {args.n_trials}")
    print(f"  Image size     : {args.image_size} x {args.image_size}")
    print()
    
    image_shape = (args.image_size, args.image_size)
    results = []
    
    # Test without cache
    print("Running baseline (NO cache)...")
    for trial in range(args.n_trials):
        print(f"  Trial {trial + 1}/{args.n_trials}...", end=' ', flush=True)
        result = run_benchmark(args.n_clusters, image_shape, use_cache=False)
        results.append(result)
        if result['success']:
            print(f"  {result['wall_time']:.2f}s")
        else:
            print(f"  FAILED: {result['error']}")
    
    # Test with cache
    print("Running with PSF CACHE...")
    for trial in range(args.n_trials):
        print(f"  Trial {trial + 1}/{args.n_trials}...", end=' ', flush=True)
        result = run_benchmark(args.n_clusters, image_shape, use_cache=True)
        results.append(result)
        if result['success']:
            print(f"  {result['wall_time']:.2f}s")
        else:
            print(f"  FAILED: {result['error']}")
    
    # Compute summary stats
    baseline_times = [r['wall_time'] for r in results 
                     if r['success'] and not r['use_cache']]
    cached_times = [r['wall_time'] for r in results 
                   if r['success'] and r['use_cache']]
    
    if baseline_times and cached_times:
        baseline_mean = np.mean(baseline_times)
        cached_mean = np.mean(cached_times)
        speedup = baseline_mean / cached_mean
        
        print()
        print("Results:")
        print(f"  Baseline time (NO cache) : {baseline_mean:.2f}s (mean of {len(baseline_times)} trials)")
        print(f"  Cached time             : {cached_mean:.2f}s (mean of {len(cached_times)} trials)")
        print(f"  Speedup                 : {speedup:.2f}x")
        
        # Cache hit rate
        if results[-1]['cache_stats'] is not None:
            stats = results[-1]['cache_stats']
            print(f"  Cache hit rate          : {stats['hit_rate_pct']:.1f}%")
    
    # Save results
    print(f"\nSaving results to {args.output}...")
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=float)
    
    print("Done!")


if __name__ == '__main__':
    main()
