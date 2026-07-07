# Notebook Guide

The project includes notebooks for onboarding, full-pipeline runs, PSF-specific workflows, and diagnostic analysis. This page groups them by use case so users can find the right starting point quickly.

## Notebook Code Previews

These are representative code cells shown directly in the docs page.

<div class="notebook-snippet-grid">
	<section class="notebook-snippet-card">
		<h3>simple_inject.ipynb</h3>
		<p>Minimal single-image injection workflow.</p>
		<pre><code class="language-python">from src.data_access import RubinDataAccess
from src.inject import create_injection_catalog, inject_from_catalog

data = RubinDataAccess(mode="tap", token=RUBIN_TOKEN)
image, meta = data.load_coadd(ra=55.0, dec=-30.0, size_arcsec=120, band="i")

catalog = create_injection_catalog(
    n_clusters=10,
    image_shape=image.shape,
    mag_range=(20.0, 24.0),
    r_half_range=(3.0, 20.0),
    profile_type="plummer",
    seed=42,
)

injected_image, info = inject_from_catalog(
    image,
    catalog,
    psf_fwhm=data.get_psf_fwhm(meta),
)</code></pre>
	</section>

	<section class="notebook-snippet-card">
		<h3>simple_batch_injection_demo.ipynb</h3>
		<p>Canonical 10 x 1000 pooled completeness workflow.</p>
		<pre><code class="language-bash">python scripts/canfar_parallel_10x1000.py \
  --config-file configs/canfar_parallel_10x1000.example.json \
  --detector-spec src.detection:run_cluster_detection \
  --n-workers 8 \
  --output-dir canfar_outputs/batch_10x1000</code></pre>
	</section>

	<section class="notebook-snippet-card">
		<h3>simple_multiband_injection_demo.ipynb</h3>
		<p>Run matching injections across multiple bands.</p>
		<pre><code class="language-python">bands = ["g", "r", "i"]

for band in bands:
    !python scripts/run_injection.py \
      --token $RUBIN_TOKEN \
      --ra 55.0 --dec -30.0 \
      --band {band} \
      --n-clusters 20 \
      --output-dir plots/multiband/{band}</code></pre>
	</section>
</div>

## Suggested Learning Path

1. [tutorial_injection.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/tutorial_injection.ipynb): conceptual walkthrough.
2. [simple_inject.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/simple_inject.ipynb): minimal injection demo.
3. [simple_multiband_injection_demo.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/simple_multiband_injection_demo.ipynb): multiband extension.
4. [simple_batch_injection_demo.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/simple_batch_injection_demo.ipynb): 10 x 1000 pooled workflow.
5. [full_pipeline_rubin_psf.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/full_pipeline_rubin_psf.ipynb): realistic PSF workflow.

## Notebook Catalog

### Quickstart And Onboarding

| Notebook | Best for | Notes |
| --- | --- | --- |
| [tutorial_injection.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/tutorial_injection.ipynb) | First conceptual pass | Good starting point for new users. |
| [simple_inject.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/simple_inject.ipynb) | Fastest single-run demo | Minimal injection example. |
| [simple_rubin_mci_demo.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/simple_rubin_mci_demo.ipynb) | Rubin detection example | Small MCI-style demonstration. |

### Full Pipeline Workflows

| Notebook | Best for | Notes |
| --- | --- | --- |
| [full_pipeline_demo.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/full_pipeline_demo.ipynb) | General end-to-end walkthrough | Broader pipeline example. |
| [full_pipeline_galsim.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/full_pipeline_galsim.ipynb) | GalSim-centered workflow | Useful for simulation-oriented testing. |
| [full_pipeline_actual_psf.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/full_pipeline_actual_psf.ipynb) | Realistic PSF path | Focuses on actual PSF usage. |
| [full_pipeline_rubin_psf.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/full_pipeline_rubin_psf.ipynb) | Best high-fidelity Rubin example | Strong reference for PSF-aware runs. |
| [injection_pipeline_rsp.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/injection_pipeline_rsp.ipynb) | RSP-specific execution | Useful when running directly in Rubin environment. |

### Batch, Parallel, And Recovery Studies

| Notebook | Best for | Notes |
| --- | --- | --- |
| [simple_batch_injection_demo.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/simple_batch_injection_demo.ipynb) | Canonical 10 x 1000 run pattern | Matches the pooled completeness workflow. |
| [multi_injection_rubin_psf.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/multi_injection_rubin_psf.ipynb) | Multi-injection analysis | Good for repeated recovery tests. |
| [multi_injection_pipeline_with_diagnostics_rsp.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/multi_injection_pipeline_with_diagnostics_rsp.ipynb) | Batch + diagnostics on RSP | Useful when comparing iteration-level outputs. |
| [example_completeness.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/example_completeness.ipynb) | Completeness curve interpretation | Smaller focused analysis notebook. |

### Multiband Workflows

| Notebook | Best for | Notes |
| --- | --- | --- |
| [simple_multiband_injection_demo.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/simple_multiband_injection_demo.ipynb) | First multiband run | Recommended starting point for multiband users. |
| [full_pipeline_rubin_psf_poster.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/full_pipeline_rubin_psf_poster.ipynb) | Presentation-oriented multiband outputs | Good for figures and outreach. |

### PSF And Performance Diagnostics

| Notebook | Best for | Notes |
| --- | --- | --- |
| [test_psf_extraction.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/test_psf_extraction.ipynb) | Verifying PSF extraction | Use when debugging PSF inputs. |
| [PSF_Caching_Benchmark_Analysis.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/PSF_Caching_Benchmark_Analysis.ipynb) | Cache benchmark analysis | Focused on speedups and cache behavior. |
| [PSF_Caching_RealData_Benchmark.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/PSF_Caching_RealData_Benchmark.ipynb) | Real-data benchmark | Compare performance on realistic image products. |

### Plotting And Figure Production

| Notebook | Best for | Notes |
| --- | --- | --- |
| [injection_demo_plots.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/injection_demo_plots.ipynb) | Demo-quality figures | Useful for documentation or talks. |
| [poster_stamp_figures.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/poster_stamp_figures.ipynb) | Postage stamp figure generation | Good for presentation summaries. |

### Experimental Or Scratch Notebooks

These are useful for development history, but are usually not the best first stop for new users:

- [injecter_tester.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/injecter_tester.ipynb)
- [test_injection_rsp.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/test_injection_rsp.ipynb)
- [tester111.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/tester111.ipynb)
- [Untitled-1.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/Untitled-1.ipynb)

## Notebook Setup Tips

- Use the same Python environment as your package install.
- Restart kernel after dependency changes.
- Keep relative paths anchored to `star-cluster-injection-pipeline`.

## Best Notebook By Goal

- Learn the pipeline: [tutorial_injection.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/tutorial_injection.ipynb)
- Run a minimal example: [simple_inject.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/simple_inject.ipynb)
- Do multiband injections: [simple_multiband_injection_demo.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/simple_multiband_injection_demo.ipynb)
- Reproduce the pooled 10 x 1000 workflow: [simple_batch_injection_demo.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/simple_batch_injection_demo.ipynb)
- Study PSF performance: [PSF_Caching_Benchmark_Analysis.ipynb](https://github.com/whosneha/INJECT/blob/main/star-cluster-injection-pipeline/notebooks/PSF_Caching_Benchmark_Analysis.ipynb)

## Good Notebook Habits For Reproducibility

- Put all key run parameters in one top cell.
- Print seed and config before execution.
- Save outputs with timestamped or hash-tagged filenames.
- Export key charts to `plots/` for later comparison.

## Common Pitfalls

- Mixed kernels causing import errors.
- Running cells out of order and using stale in-memory state.
- Accidentally changing config in one cell and forgetting downstream effects.

## From Notebook To Script

When your notebook run is stable:

1. Move parameter block into YAML or CLI args.
2. Move core execution into a script.
3. Keep notebook for interpretation and visualization only.

This split improves repeatability and reduces accidental drift.
