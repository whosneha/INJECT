# Pipeline Workflows

## Workflow A: Packaged CLI Run

Use `injection-pipeline` when you want a quick, repeatable run from terminal.

```bash
injection-pipeline --n-clusters 100 --band i --method smooth
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

## PSF Fidelity: RSP vs TAP

- RSP/Butler workflows can use Rubin CoaddPsf objects (spatially varying PSF).
- TAP workflows outside RSP use cutouts plus PSF FWHM metadata and then analytic PSF fallback during injection.
- In the RSP path, the pipeline records Rubin PSF-quality mask flags at each injection position when mask data are available.
- By default, the pipeline still uses the local Rubin PSF model if it is computable, even in `INEXACT_PSF`-type regions. Enable `skip_bad_psf_regions=True` when you want those positions excluded from injection.

For PSF-sensitive science conclusions, use TAP for large-scale throughput tests, then validate key results with the RSP/Butler PSF path.

## Output Management Pattern

Recommended per experiment:

- One run directory.
- Versioned config snapshot.
- Injected truth catalog.
- Detection output catalog.
- Completeness tables.
- Diagnostic plots.

This makes reruns and paper-figure generation much easier later.
