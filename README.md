# Star Cluster Injection Pipeline

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

INJECT is a Rubin/LSST-oriented pipeline for injecting artificial star clusters into imaging data, running recovery experiments, and estimating completeness under user-controlled assumptions.

## Recommended Operating Mode

The main intended usability for this project is on the Rubin Science Platform (RSP), especially when you want realistic Rubin PSF handling.

- Use RSP / Butler workflows when PSF fidelity matters.
- Use TAP or a fully local workflow when you need lightweight remote access or demo-style runs.
- In TAP or local mode, the pipeline falls back to GalSim-based PSF calculations rather than Rubin-native PSF computation.

## What It Supports

- Smooth or discrete-star cluster generation.
- Multiple light-profile families: King, Plummer, EFF, and Sersic.
- Rubin Butler/RSP access for the primary science workflow.
- Token-based TAP access for lighter-weight cutout access and demos.
- PSF-aware injections with Rubin mask-flag tracking on RSP.
- Batch workflows for repeated injection-recovery studies.
- MkDocs/Read the Docs documentation and a pip-installable package layout.

## Installation

```bash
git clone https://github.com/whosneha/INJECT.git
cd INJECT
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev,docs]"
```

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

Suggested RSP-oriented notebooks:

- [tutorial_injection.ipynb](https://github.com/whosneha/INJECT/blob/main/notebooks/tutorial_injection.ipynb): conceptual walkthrough and first orientation.
- [injection_pipeline_rsp.ipynb](https://github.com/whosneha/INJECT/blob/main/notebooks/injection_pipeline_rsp.ipynb): RSP-specific execution pattern.
- [full_pipeline_rubin_psf.ipynb](https://github.com/whosneha/INJECT/blob/main/notebooks/full_pipeline_rubin_psf.ipynb): best reference for Rubin-PSF-aware runs.
- [multi_injection_pipeline_with_diagnostics_rsp.ipynb](https://github.com/whosneha/INJECT/blob/main/notebooks/multi_injection_pipeline_with_diagnostics_rsp.ipynb): repeated runs plus diagnostics on RSP.

Typical RSP notebook setup flow:

1. Open a JupyterLab session on RSP.
2. Clone this repository into your workspace.
3. Create or activate a notebook environment with the package installed.
4. Start from one of the RSP notebook examples above.
5. Use Butler-backed data loading when you want Rubin-native PSF handling.

If you stay fully local or use TAP instead, you should treat those modes as convenience or demo paths, not the primary high-fidelity science path.

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
