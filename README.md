# Star Cluster Injection Pipeline

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

INJECT is a Rubin/LSST-oriented pipeline for injecting artificial star clusters into imaging data, running recovery experiments, and estimating completeness under user-controlled assumptions.

## Recommended Operating Modes

The two main day-to-day usage patterns in this repo are:

- Use TAP queries plus a local or non-RSP environment for lightweight runs and development. This path does not use Rubin-native PSF computation; it uses the GalSim-based fallback path instead.
- Use RSP / Butler workflows when PSF fidelity matters and you specifically want Rubin-native PSF handling.

## How This Relates To Rubin's Injection Tool

This project is meant to complement Rubin's built-in injection tooling, not duplicate it.

- It is focused on star-cluster injection rather than only simpler source-injection patterns.
- It exposes profile family, size, magnitude range, batching strategy, and downstream benchmarking through a notebook-friendly Python API.
- It supports both smooth profile injections and discrete-star cluster generation.
- It is designed so users can plug in their own detection methods cleanly instead of being locked to one recovery path.
- It lets users inspect problematic PSF locations on RSP, keep and flag them, skip them via mask logic, or rely on the GalSim-style fallback path when Rubin-native PSF evaluation is unavailable.

Rubin's own tooling already supports visit-level and Butler-integrated injection workflows. INJECT's current packaged Rubin-facing workflow is coadd-first and is best described as an easier-to-customize cluster-injection and benchmarking layer rather than a replacement for Rubin's pipeline tooling.

## What It Supports

- Smooth or discrete-star cluster generation.
- Multiple light-profile families: King, Plummer, EFF, and Sersic.
- Rubin Butler/RSP access for the primary science workflow.
- Token-based TAP access for lighter-weight cutout access and demos.
- PSF-aware injections with Rubin mask-flag tracking on RSP.
- Single-band and multiband workflows.
- Batch workflows for repeated injection-recovery studies.
- MkDocs/Read the Docs documentation and a pip-installable package layout.

Current scope note:

- Native Butler-backed Rubin workflows in this repo target coadds.
- Users can still inject into any 2D image array through the Python API.
- Native Butler-backed single-visit or `calexp` loading is not yet implemented as a first-class workflow.

## Installation

```bash
git clone https://github.com/whosneha/INJECT.git
cd INJECT
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev,docs]"
```

At the moment, this project should be installed with `numpy<2`. The package metadata now pins that automatically, but if you already built an environment with NumPy 2.x, downgrade it with `pip install "numpy<2"`.

## First Run

Run a local mock-data injection:

```bash
injection-pipeline --n-clusters 10 --band i --profile plummer --method smooth
```

That writes output files to `outputs/` by default.

For a TAP-mode run:

```bash
injection-pipeline --token YOUR_TOKEN --ra 55.0 --dec -30.0 --band i --n-clusters 10
```

TAP mode is useful for demos and lighter-weight remote work, but PSF computation there uses the GalSim-based fallback path rather than Rubin-native PSF extraction.

For Butler/RSP:

```bash
injection-pipeline \
  --repo /repo/main \
  --collection YOUR_COLLECTION \
  --tract 9615 \
  --patch 30 \
  --band i \
  --n-clusters 10
```

## RSP Notebook Workflow

If you are setting this up for real use, start from an RSP Jupyter notebook rather than the lightweight CLI demos.

Before running anything on RSP, copy this repository into your RSP workspace. The simplest path is to open a terminal in RSP JupyterLab and clone it there.

Typical RSP JupyterLab flow:

1. Launch a JupyterLab session on the Rubin Science Platform.
2. In JupyterLab, open `File` -> `New` -> `Terminal`.
3. In that terminal, clone the repository into your workspace.
4. Install the package from the cloned repository so the notebooks can import and call the pipeline functions.

```bash
cd ~/repos
git clone https://github.com/whosneha/INJECT.git
cd INJECT
pip install -e ".[dev,docs,jupyter]"
```

After that, open notebooks from the cloned `INJECT/` folder in JupyterLab and use imports such as `from star_cluster_injection import InjectionConfig, InjectionPipeline`.

If you are working from an unpushed local copy, upload or copy the repository folder into your RSP workspace first, then open a terminal in that copied folder and run the same install command there.

Suggested RSP-oriented notebooks:

- [tutorial_injection.ipynb](https://github.com/whosneha/INJECT/blob/main/notebooks/tutorial_injection.ipynb): conceptual walkthrough and first orientation.
- [injection_pipeline_rsp.ipynb](https://github.com/whosneha/INJECT/blob/main/notebooks/injection_pipeline_rsp.ipynb): RSP-specific execution pattern.
- [full_pipeline_rubin_psf.ipynb](https://github.com/whosneha/INJECT/blob/main/notebooks/full_pipeline_rubin_psf.ipynb): best reference for Rubin-PSF-aware runs.
- [multi_injection_pipeline_with_diagnostics_rsp.ipynb](https://github.com/whosneha/INJECT/blob/main/notebooks/multi_injection_pipeline_with_diagnostics_rsp.ipynb): repeated runs plus diagnostics on RSP.

Typical RSP notebook setup flow:

1. Open a JupyterLab session on RSP.
2. Copy or clone this repository into your RSP workspace.
3. Open a terminal in the repository root on RSP.
4. Install the package in that cloned repository so notebook imports work.
5. Open notebooks from the cloned `INJECT/` folder.
6. Start from one of the RSP notebook examples above.
7. Use Butler-backed data loading when you want Rubin-native PSF handling.

If you stay fully local or use TAP instead, you should treat those modes as convenience or demo paths, not the primary high-fidelity science path.

## Main Example Workflows

If you want the examples to match the current notebook usage patterns closely, start here:

- [simple_rubin_mci_demo.ipynb](https://github.com/whosneha/INJECT/blob/main/notebooks/simple_rubin_mci_demo.ipynb): best compact example of the simple single-run detection workflow.
- [simple_batch_injection_demo.ipynb](https://github.com/whosneha/INJECT/blob/main/notebooks/simple_batch_injection_demo.ipynb): main pooled batch workflow for repeated injection and completeness studies.

These two notebooks are the clearest examples of how most users will actually interact with the pipeline.

## Bands And Data Modes

- Single-band runs are supported through `band="i"`-style configuration.
- Multiband runs are supported through `bands=["g", "r", "i"]` and `run_batch_multiband(...)`.
- Butler-backed Rubin loading in the current packaged workflow is coadd-based.
- If you want to work on a single visit today, the supported path is to supply your own 2D image array to `load_data(image=...)` rather than using a native Butler visit loader.

## Detection Plug-In Pattern

The pipeline is designed so users can bring their own detector instead of rewriting the injection code.

In batch workflows, you pass a callable as `detector_fn`, and the pipeline applies it to the injected image before truth matching and completeness analysis.

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

The docs and notebooks describe the expected detection catalog shape so users can plug in their own method cleanly.

## Python API

```python
import numpy as np
from star_cluster_injection import InjectionConfig, InjectionPipeline

image = np.random.normal(100, 15, (500, 500))
config = InjectionConfig(n_clusters=25, band="i")

pipeline = InjectionPipeline(config)
pipeline.load_data(image=image)
catalog = pipeline.generate_catalog()
```

## Testing And Packaging

```bash
pytest
python -m build --no-isolation
mkdocs build
```

## Deployment Paths

This repository now includes two release-ready delivery paths:

- A pip-installable Python package via [pyproject.toml](pyproject.toml).
- A container build via [Dockerfile](Dockerfile) that can be tagged for Harbor.

Additional deployment notes are in [DEPLOYMENT.md](DEPLOYMENT.md) and the docs page [site_docs/guides/deployment.md](site_docs/guides/deployment.md).

## Documentation

- Read the Docs / MkDocs source: [site_docs](site_docs)
- Installation guide: [site_docs/getting-started/installation.md](site_docs/getting-started/installation.md)
- Notebook guide: [site_docs/guides/notebooks.md](site_docs/guides/notebooks.md)
- Use cases: [site_docs/guides/use-cases.md](site_docs/guides/use-cases.md)
- Customization guide: [site_docs/guides/customization.md](site_docs/guides/customization.md)
- Testing reference: [site_docs/reference/testing.md](site_docs/reference/testing.md)
