# Pipeline Workflows

## Workflow A: TAP/Local Single-Run Workflow

Use TAP queries plus a local or non-RSP environment when you want the main lightweight workflow.

This path does not use Rubin-native PSF computation. It uses the GalSim-based fallback path driven by the TAP metadata or local settings.

```bash
injection-pipeline --token YOUR_TOKEN --ra 55.0 --dec -30.0 --band i --n-clusters 25
```

Best for:

- Development outside RSP
- Lightweight demos
- Exploratory local runs
- Following the pattern in `simple_rubin_mci_demo.ipynb`

## Workflow B: Main Notebook Examples

The two main example workflows are:

- `simple_rubin_mci_demo.ipynb` for the simple single-run pattern
- `simple_batch_injection_demo.ipynb` for the pooled repeated-run pattern

Use notebooks under `notebooks/` when you need visual debugging and iterative analysis.

Recommended sequence for most users:

1. `simple_rubin_mci_demo.ipynb`
2. `simple_batch_injection_demo.ipynb`
3. `simple_multiband_injection_demo.ipynb`
4. `full_pipeline_rubin_psf.ipynb`

If you are doing real Rubin PSF-aware science, start with the RSP-oriented notebooks first:

1. `tutorial_injection.ipynb`
2. `injection_pipeline_rsp.ipynb`
3. `full_pipeline_rubin_psf.ipynb`
4. `multi_injection_pipeline_with_diagnostics_rsp.ipynb`

## Workflow C: Batch Injection With Shared PSF Cache

Batch execution through `InjectionPipeline.run_batch(...)` supports shared PSF cache reuse and matches the pattern used in `simple_batch_injection_demo.ipynb`.

Use this for:

- Large completeness studies
- Repeated injections over a fixed footprint
- Throughput benchmarking
- Detector plug-in workflows where you pass your own `detector_fn`

Example pattern:

```python
iterations = pipe.run_batch(
    n_iterations=10,
    n_per_iter=100,
    psf_obj=pipe.psf_objs["i"],
    bbox_x_min=pipe.bboxes["i"][0],
    bbox_y_min=pipe.bboxes["i"][1],
    detector_fn=my_detector,
)
```

Detector expectations for this workflow:

- The detector callable must accept the injected image as its first argument.
- In `run_batch(...)`, the pipeline calls it as `detector_fn(injected_image)`.
- The detector must return `list[dict]` with at least `x` and `y` for each detection.

## Workflow D: Multiband Batch

`run_batch_multiband(...)` keeps injected cluster positions aligned across all active bands.

That is useful when:

- You compare detection consistency across filters.
- You train or test methods that rely on multiband morphology.
- You need one truth table interpreted consistently in each band.

Band configuration is explicit:

- Use `band="i"` for a single-band run.
- Use `bands=["g", "r", "i"]` when you want matched multiband runs.

## PSF Fidelity: RSP vs TAP

- RSP/Butler workflows can use Rubin CoaddPsf objects (spatially varying PSF).
- TAP workflows outside RSP use cutouts plus PSF FWHM metadata and then analytic/GalSim fallback during injection.
- In the RSP path, the pipeline records Rubin PSF-quality mask flags at each injection position when mask data are available.
- By default, the pipeline still uses the local Rubin PSF model if it is computable, even in `INEXACT_PSF`-type regions. Enable `skip_bad_psf_regions=True` when you want those positions excluded from injection.
- When Rubin-native PSF evaluation is unavailable, the injection path falls back to the GalSim-based approximation controlled by `psf_fwhm_fallback`.

In other words, users can choose between:

- keeping and flagging PSF-problematic positions,
- masking them out with `skip_bad_psf_regions=True`,
- or using the GalSim-style fallback path when Rubin-native PSF evaluation cannot be used.

For PSF-sensitive science conclusions, use TAP for lightweight development and throughput tests, then validate key results with the RSP/Butler PSF path.

## Coadds vs Single Visits

- The packaged Butler/RSP workflow in this repo currently loads `deepCoadd` products.
- That means the native Rubin-facing path here is coadd-first rather than visit-first.
- If you want to inject into a single visit today, the supported route is to provide the image array directly through the Python API.
- Native Butler-backed visit or `calexp` loading is not yet implemented as a first-class workflow.

## Output Management Pattern

Recommended per experiment:

- One run directory.
- Versioned config snapshot.
- Injected truth catalog.
- Detection output catalog.
- Completeness tables.
- Diagnostic plots.

This makes reruns and paper-figure generation much easier later.
