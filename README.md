# INJECT

INJECT is a Rubin/LSST-oriented star cluster injection pipeline for running injection-recovery experiments, testing detection behavior, and estimating completeness under user-controlled assumptions.

The main Python package and documentation source live in [`star-cluster-injection-pipeline/`](star-cluster-injection-pipeline/).

## What This Repository Contains

- A pip-installable Python package for synthetic star-cluster injection.
- Command-line and Python workflows for mock data, TAP access, and Rubin Butler/RSP usage.
- MkDocs / Read the Docs documentation for installation, use cases, customization, and testing.
- Deployment scaffolding for package builds and Harbor-ready container builds.

## Quick Start

Clone the repository and install the package from the project directory:

```bash
git clone https://github.com/whosneha/INJECT.git
cd INJECT/star-cluster-injection-pipeline
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev,docs]"
```

Run a first local mock-data injection:

```bash
injection-pipeline --n-clusters 10 --band i --profile plummer --method smooth
```

This writes output files to `star-cluster-injection-pipeline/outputs/` by default.

## Common Run Modes

Token-based TAP access:

```bash
cd star-cluster-injection-pipeline
injection-pipeline --token YOUR_TOKEN --ra 55.0 --dec -30.0 --band i --n-clusters 10
```

Rubin Butler / RSP access:

```bash
cd star-cluster-injection-pipeline
injection-pipeline \
  --repo /repo/main \
  --collection YOUR_COLLECTION \
  --tract 9615 \
  --patch 30 \
  --band i \
  --n-clusters 10
```

## Python Usage

```python
import numpy as np
from star_cluster_injection import InjectionConfig, InjectionPipeline

image = np.random.normal(100, 15, (500, 500))
config = InjectionConfig(n_clusters=25, band="i")

pipeline = InjectionPipeline(config)
pipeline.load_data(image=image)
catalog = pipeline.generate_catalog()
```

## Validation And Build Commands

From `star-cluster-injection-pipeline/`:

```bash
pytest
python -m build --no-isolation
mkdocs build
python -m twine check dist/star_cluster_injection_pipeline-0.1.0.tar.gz dist/star_cluster_injection_pipeline-0.1.0-py3-none-any.whl
```

## Documentation

- Package README: [`star-cluster-injection-pipeline/README.md`](star-cluster-injection-pipeline/README.md)
- Installation guide: [`star-cluster-injection-pipeline/site_docs/getting-started/installation.md`](star-cluster-injection-pipeline/site_docs/getting-started/installation.md)
- Use cases: [`star-cluster-injection-pipeline/site_docs/guides/use-cases.md`](star-cluster-injection-pipeline/site_docs/guides/use-cases.md)
- Customization guide: [`star-cluster-injection-pipeline/site_docs/guides/customization.md`](star-cluster-injection-pipeline/site_docs/guides/customization.md)
- Deployment guide: [`star-cluster-injection-pipeline/site_docs/guides/deployment.md`](star-cluster-injection-pipeline/site_docs/guides/deployment.md)

## Repository Layout

```text
INJECT/
├── README.md
└── star-cluster-injection-pipeline/
    ├── pyproject.toml
    ├── README.md
    ├── src/
    ├── tests/
    ├── site_docs/
    ├── notebooks/
    ├── configs/
    └── Dockerfile
```
