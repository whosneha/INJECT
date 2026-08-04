# PSF Caching and Performance

PSF extraction can dominate runtime in repeated injection workflows. The pipeline includes shared cache support to reduce repeated PSF evaluations.

This matters most on RSP, where Rubin-native PSF evaluation is part of the primary science workflow.

## Why Caching Helps

In batch studies, many injections sample nearby image regions iteration after iteration. A cache reuses previously computed PSF kernels for quantized spatial locations.

A naive run with repeated Rubin PSF evaluation pays three costs:

- RAM pressure from holding too many intermediate images or stamps.
- Wall-time cost from recomputing PSFs for nearby positions again and again.
- Recovery risk if a long notebook kernel dies before results are checkpointed.

## Key Parameters

- `use_psf_cache`: enable or disable caching.
- `psf_cache_grid`: spatial quantization in pixels.
- `psf_cache_size`: max cache entries before LRU eviction.

## How The Cache Works

`get_actual_psf()` evaluates the local Rubin PSF at the injection position. On repeated batch runs, that can become the dominant runtime cost.

The cache reuses previously evaluated PSFs using quantized spatial keys:

```python
from src.inject import PSFCache

cache = PSFCache(
    max_entries=2000,
    grid_size=8,
)
```

Conceptually, the cache key is:

```python
(band, x // grid_size, y // grid_size)
```

That means nearby injections in the same band can share the same PSF stamp when the local Rubin PSF varies smoothly enough for the science use case.

## Practical Tuning

Start with:

- `psf_cache_grid = 8`
- `psf_cache_size = 2000`

Then adjust based on:

- Memory budget
- PSF spatial variability
- Required photometric fidelity

Increase `psf_cache_grid` only when you are confident the PSF is varying slowly enough across the field. Decrease it if you are doing more PSF-sensitive tests and want less reuse per cell.

## Monitoring Strategy

Track per-iteration timing and cache hit metrics. You should see warm-up cost in early iterations followed by faster steady-state execution.

In repeated runs over the same field, the cache hit rate should usually rise after the first iteration once common regions have been populated.

## Memory Management Pattern

The performance story is not only about PSF reuse.

- `store_images=False` avoids keeping every injected image in memory.
- Per-cluster `stamp` arrays should be discarded unless you explicitly need them for diagnostics.
- `checkpoint_dir=...` lets long runs survive notebook or kernel interruptions.

These choices matter more as you scale from tutorial-sized runs to repeated RSP campaigns.

## Recommended RSP Batch Pattern

```python
iterations = pipe.run_batch(
    n_iterations=10,
    n_per_iter=1000,
    psf_obj=pipe.psf_objs["i"],
    bbox_x_min=pipe.bboxes["i"][0],
    bbox_y_min=pipe.bboxes["i"][1],
    checkpoint_dir="./ckpts/run1",
    store_images=False,
    use_psf_cache=True,
    psf_cache_grid=8,
    psf_cache_size=2000,
    n_workers=1,
)
```

Start conservatively on RSP, then tune `n_workers`, cache size, and checkpoint layout once you know your CPU and memory budget.

## Caveats

- Cache entries are tied to the current PSF object and field geometry. Reset the cache if you change exposures or load a different coadd.
- The cache is only relevant for Rubin-native PSF evaluation. TAP and local runs use the GalSim-based fallback path instead.
- Parallel speedups depend on your actual RSP container allocation. More workers are not always faster.

## Benchmarking References

See the notebooks:

- `PSF_Caching_Benchmark_Analysis.ipynb`
- `PSF_Caching_RealData_Benchmark.ipynb`

Use identical seeds and catalog ranges when comparing with and without caching.
