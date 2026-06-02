# Performance, Memory & PSF Caching

This document describes the performance and memory-management features built
into the batch injection pipeline (`src/pipeline.py`, `src/inject.py`) and
how to use them on the Rubin Science Platform (RSP).

---

## 1. Why this matters

A naive batch run of **10 iterations × 1,000 clusters** on a 1500×1500 coadd
hits three walls:

| Resource | Naive cost                                                       |
| -------- | ---------------------------------------------------------------- |
| RAM      | 10 × 1500² × 8 B = **~180 MB** of injected images + ~200 MB of stamps |
| Wall     | PSF re-evaluated for every cluster, every iteration              |
| Risk     | Crash at iter 8/10 = total data loss                             |

At full-coadd scale (4000×4000) the image RAM alone is ~1.2 GB — enough to
OOM-kill a standard RSP container.

The pipeline addresses each of these directly.

---

## 2. Fixes implemented

### High priority

| # | Problem                                  | Fix                                                                            | Location                              |
| - | ---------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------- |
| 1 | `injected_image` held in RAM per iter    | `store_images=False` (default); only iter-0 kept, others `del`-ed immediately  | `pipeline.py` `run_batch` / `_run_one` |
| 2 | Stamps accumulate in RAM                 | `entry.pop('stamp', None)` right after injection                               | `pipeline.py` `_run_one`              |
| 3 | No checkpointing                         | `checkpoint_dir=...` writes per-iter CSVs as soon as each iter completes       | `pipeline.py` `_run_one`              |
| 4 | `run_batch` mutates `config.seed`/`n_clusters` | Restored immediately after `generate_catalog()` (still in main thread)   | `pipeline.py` `run_batch`             |
| 5 | All output via `print()`                 | Module-level `logger` with timestamps; `print` only for status banners        | `pipeline.py` top of file             |

### Medium priority

| # | Problem                | Fix                                                                              | Location                  |
| - | ---------------------- | -------------------------------------------------------------------------------- | ------------------------- |
| 6 | No parallelism         | `n_workers` arg → `ThreadPoolExecutor` (threads, since lsst objects aren't picklable) | `pipeline.py` `run_batch` |
| 7 | PSF queries are slow   | `PSFCache` (LRU + grid quantization), shared across all iterations               | `inject.py` `PSFCache`    |

---

## 3. PSF caching — how it works

`get_actual_psf()` calls `psf_obj.computeImage(point)` once per cluster.
At 10,000 clusters this dominates wall time on RSP (each call materializes
a 21×21 PSF stamp from the coadd's variable PSF model).

The Rubin PSF varies smoothly on ~100 px scales, so neighbouring clusters
inside an ~8 px grid cell can safely reuse the same PSF stamp with no
science impact. The `PSFCache` class implements that:

```python
from src.inject import PSFCache

cache = PSFCache(
    max_entries = 2000,   # LRU-evict beyond this many entries
    grid_size   = 8,      # pixels — quantization cell
)
```

Cache key: `(band, x // grid, y // grid)`. The `band` namespace prevents
collisions when running multiband. `max_entries=2000` at `grid_size=8`
covers a ~360×360 pixel patch with full residency.

Across 10 iterations the same image regions are sampled repeatedly, so the
hit rate climbs sharply once the cache is warm. In benchmarks on
synthetic Gaussian PSFs we see >80% hit rate after iter 1.

The cache is **shared across all iterations of a batch** by `run_batch` —
this is where the bulk of the speedup comes from.

### Tuning knobs

| Knob              | Default | When to change                                                  |
| ----------------- | ------- | --------------------------------------------------------------- |
| `use_psf_cache`   | `True`  | Disable only for A/B benchmarking or debugging                  |
| `psf_cache_grid`  | `8`     | Increase (16, 32) for very smooth PSFs; decrease for sharp variations |
| `psf_cache_size`  | `2000`  | Increase for full-coadd runs; decrease if memory-tight          |

### Caveats / scope

- Caching is keyed on quantized position, NOT on the PSF object itself.
  If you swap `psf_obj` between iterations (different visits or
  re-loaded coadds), call `cache.reset()` first.
- Caching is only active when `use_actual_psf=True` and the LSST stack
  is available. The Gaussian fallback path doesn't need a cache.

---

## 4. Memory fixes — how they work

### Injected images

Default behaviour (`store_images=False`): only the iter-0 image is kept
on the pipeline instance for plotting. All later iterations explicitly
`del injected_image` before the function returns, so the GC reclaims
~12 MB (or ~64 MB for full coadds) every iteration.

Set `store_images=True` only when you actually need every image (e.g.
making a movie of detections across iterations).

### Stamps

`inject_clusters_rubin_psf` populates `injection_info[i]['stamp']` with
the full convolved 2D stamp. For 10k clusters at 51×51 that's ~200 MB
sitting in RAM for the duration of the run.

`_run_one` strips these *immediately* after the function returns:

```python
for entry in injection_info:
    entry.pop('stamp', None)
```

If you want to keep stamps for diagnostics, save them to disk in
the detector callback before returning.

---

## 5. Checkpointing

```python
iterations = pipe.run_batch(
    n_iterations  = 10,
    n_per_iter    = 1000,
    ...,
    checkpoint_dir = '/scratch/runs/2026-05-19_run1',
)
```

After each iteration, two CSVs are written:

```
checkpoint_dir/
    injection_iter000.csv
    detections_iter000.csv
    injection_iter001.csv
    ...
```

If the kernel dies at iter 8/10, iters 0–7 are already on disk. Reload
with `pandas.read_csv` and re-run only the missing iterations.

---

## 6. Logging

Top of `pipeline.py`:

```python
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# StreamHandler with HH:MM:SS timestamps, no propagation
```

All per-iteration progress is emitted via `logger.info(...)`, so output
on RSP includes timestamps that make it easy to diagnose where a long
run slowed down. To increase verbosity for debugging:

```python
import logging
logging.getLogger('src.pipeline').setLevel(logging.DEBUG)
```

---

## 7. Parallelism

```python
iterations = pipe.run_batch(..., n_workers=4)
```

- `n_workers=1` (default): sequential, easiest to debug.
- `n_workers=N`: `ThreadPoolExecutor(max_workers=N)`.
- `n_workers=-1`: use `os.cpu_count()`.

Threads — not processes — because `lsst.afw.image.ExposureF` and
`CoaddPsf` are not picklable. They are read-only inside the worker, so
no locking is needed. The `PSFCache` writes are guarded only by the GIL,
which is sufficient for the put/get pattern (worst case: redundant fill,
no corruption).

**Before bumping `n_workers` on RSP**: check your CPU allocation. RSP
default containers typically have 2-4 cores; oversubscribing makes things
slower, not faster.

---

## 8. Recommended call from a notebook

```python
from src.pipeline import InjectionPipeline
from src.config   import InjectionConfig

pipe = InjectionPipeline(InjectionConfig(...))
pipe.load_data(butler=butler, data_id={'tract': 3828, 'patch': 24, 'band': 'i'})

iterations = pipe.run_batch(
    n_iterations    = 10,
    n_per_iter      = 1000,
    psf_obj         = pipe.psf_objs['i'],
    bbox_x_min      = pipe.bboxes['i'][0],
    bbox_y_min      = pipe.bboxes['i'][1],
    psf_fwhm_fallback = 3.5,
    detector_fn     = my_detector,
    store_images    = False,          # default — saves ~180 MB
    checkpoint_dir  = './ckpts/run1', # safe-resume on crash
    use_psf_cache   = True,           # default
    band            = 'i',
    n_workers       = 1,              # bump after verifying RSP CPU budget
    verbose         = True,
)

# Last cache stats are also visible in iterations[-1]['cache_stats']
```

---

## 9. Benchmark

See `notebooks/PSF_Caching_Benchmark_Analysis.ipynb` for a runnable
before/after comparison. Typical speedup on a 50-cluster synthetic run:
**~3–5× wall time reduction**, with cache hit rate around 70–90%.
Real Rubin coadds with spatially varying PSFs will show different
absolute numbers but the trend is the same.

---

## 10. Still out of scope

- **Distributed parallelism (Dask)** — only worth doing once `n_workers`
  threads no longer help. Discuss with the team before adding the dep.
- **Interpolated PSF (not just nearest-cell)** — would slightly improve
  fidelity at the cost of complexity. Not justified at current Rubin
  PSF smoothness.
