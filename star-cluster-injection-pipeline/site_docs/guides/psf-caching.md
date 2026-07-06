# PSF Caching and Performance

PSF extraction can dominate runtime in repeated injection workflows. The pipeline includes shared cache support to reduce repeated PSF evaluations.

## Why Caching Helps

In batch studies, many injections sample nearby image regions iteration after iteration. A cache reuses previously computed PSF kernels for quantized spatial locations.

## Key Parameters

- `use_psf_cache`: enable or disable caching.
- `psf_cache_grid`: spatial quantization in pixels.
- `psf_cache_size`: max cache entries before LRU eviction.

## Practical Tuning

Start with:

- `psf_cache_grid = 8`
- `psf_cache_size = 2000`

Then adjust based on:

- Memory budget
- PSF spatial variability
- Required photometric fidelity

## Monitoring Strategy

Track per-iteration timing and cache hit metrics. You should see warm-up cost in early iterations followed by faster steady-state execution.

## Benchmarking References

See the notebooks:

- `PSF_Caching_Benchmark_Analysis.ipynb`
- `PSF_Caching_RealData_Benchmark.ipynb`

Use identical seeds and catalog ranges when comparing with and without caching.
