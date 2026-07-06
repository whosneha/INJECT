# Pipeline Workflows

## Workflow A: Script-First Injections

Use `scripts/run_injection.py` when you want a quick, repeatable run from terminal.

```bash
python scripts/run_injection.py --n-clusters 100 --band i --method smooth
```

Best for:

- Smoke tests
- Parameter sweeps from shell scripts
- Automated runs on shared compute

## Workflow B: Notebook Exploration

Use notebooks under `notebooks/` when you need visual debugging and iterative analysis.

Recommended sequence:

1. `simple_inject.ipynb`
2. `simple_multiband_injection_demo.ipynb`
3. `full_pipeline_rubin_psf.ipynb`
4. `PSF_Caching_Benchmark_Analysis.ipynb`

## Workflow C: Batch Injection With Shared PSF Cache

Batch execution through `InjectionPipeline.run_batch(...)` supports shared PSF cache reuse.

Use this for:

- Large completeness studies
- Repeated injections over a fixed footprint
- Throughput benchmarking

## Workflow D: Multiband Batch

`run_batch_multiband(...)` keeps injected cluster positions aligned across all active bands.

That is useful when:

- You compare detection consistency across filters.
- You train or test methods that rely on multiband morphology.
- You need one truth table interpreted consistently in each band.

## Output Management Pattern

Recommended per experiment:

- One run directory.
- Versioned config snapshot.
- Injected truth catalog.
- Detection output catalog.
- Completeness tables.
- Diagnostic plots.

This makes reruns and paper-figure generation much easier later.
