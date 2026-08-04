# Star Cluster Injection Pipeline

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

INJECT is a Rubin/LSST-oriented pipeline for injecting artificial star clusters into imaging data, running recovery experiments, and estimating completeness under user-controlled assumptions.

## What It Supports

- Smooth or discrete-star cluster generation.
- Multiple light-profile families: King, Plummer, EFF, and Sersic.
- Rubin Butler/RSP access or token-based TAP access.
- PSF-aware injections with Rubin mask-flag tracking.
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
python -m build
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
- Use cases: [site_docs/guides/use-cases.md](site_docs/guides/use-cases.md)
- Customization guide: [site_docs/guides/customization.md](site_docs/guides/customization.md)
- Testing reference: [site_docs/reference/testing.md](site_docs/reference/testing.md)
