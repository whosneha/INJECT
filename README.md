# INJECT

INJECT is a Rubin/LSST-oriented star-cluster injection pipeline for reproducible injection, recovery, and completeness studies.

It supports:

- smooth light-profile injections and discrete-star cluster generation
- notebook-first Rubin Science Platform workflows
- local or TAP-style exploratory runs outside Rubin infrastructure
- customizable downstream detection and benchmarking

## Installation

### Local Development

```bash
git clone https://github.com/whosneha/INJECT.git
cd INJECT
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev,jupyter]"
```

Verify the install:

```bash
python -c "import src; print(src.__version__)"
pytest
```

### Rubin Science Platform

The safest RSP pattern is a per-user virtual environment that can still see the shared Rubin stack. That keeps your installs isolated from other users while avoiding duplicate installs of large Rubin dependencies.

```bash
git clone https://github.com/whosneha/INJECT.git
cd INJECT
python -m venv --system-site-packages ~/venvs/inject-rsp
source ~/venvs/inject-rsp/bin/activate
python -m pip install --upgrade pip
pip install -e ".[jupyter]"
python -m ipykernel install --user --name inject-rsp --display-name "Python (inject-rsp)"
```

Why this helps on RSP:

- `--system-site-packages` lets the venv reuse the platform's Rubin/LSST packages
- `pip install ...` writes into your own venv, not the shared environment
- the dedicated kernel makes notebook imports reproducible and avoids cross-project contamination

If you are working from a cloned repo with local edits, open notebooks from that same repo checkout and select the `Python (inject-rsp)` kernel.

### One-Time RSP Jupyter Setup

You only need to do this once per environment. After that, just select the `Python (inject-rsp)` kernel in JupyterLab and open your notebook normally.

```bash
python -m venv --system-site-packages ~/venvs/inject-rsp
source ~/venvs/inject-rsp/bin/activate
pip install -e /path/to/INJECT ipykernel
python -m ipykernel install --user --name inject-rsp --display-name "Python (inject-rsp)"
```

After that:

- open JupyterLab
- open your notebook
- choose `Kernel` -> `Change Kernel` -> `Python (inject-rsp)`

You do not need notebook cells that manually search for the repo root or call `sys.path.insert(...)`.

## NumPy Compatibility

The package metadata now allows `numpy>=1.21.0` with no `<2` cap.

Why that changed:

- the previous `numpy<2` pin caused conflicts on RSP because the shared Rubin environment may already depend on newer NumPy
- the codebase does not appear to rely on removed pre-2.0 NumPy APIs
- the current test suite passes in this repository with `numpy 2.3.1`

That means installing INJECT in an RSP user venv should no longer try to force a NumPy downgrade that could interfere with Rubin-adjacent packages.

## Common Workflows

### Python API

```python
import numpy as np
from src import InjectionConfig, InjectionPipeline

cfg = InjectionConfig()
image = np.zeros((512, 512), dtype=float)

pipe = InjectionPipeline(cfg)
pipe.load_data(image=image)
catalog = pipe.generate_catalog()
injected_image, injection_info = pipe.run_injection()
```

### CLI

```bash
injection-pipeline --help
```

## Project Layout

- `src/`: the active package implementation
- `tests/`: regression and packaging tests
- `notebooks/`: the four maintained notebooks for current workflows
- `notebooks/archive/`: older exploratory notebooks kept for reference only
- `configs/`: sample configs for local and batch runs
- `site_docs/`: MkDocs documentation source

## Useful Commands

```bash
pytest
mkdocs serve
python -m build --no-isolation
```

## Recommended Starting Points

- `notebooks/simple_rubin_mci_demo.ipynb`
- `notebooks/simple_batch_injection_demo.ipynb`
- `notebooks/simple_multiband_injection_demo.ipynb`
- `notebooks/dp2_early_release_injection_smoke_test.ipynb`
- `site_docs/getting-started/installation.md`
- `site_docs/getting-started/quickstart.md`

Older notebooks remain in `notebooks/archive/`, but they are not maintained as the primary workflow path.

## Notes

- Butler-backed workflows in this repo are currently coadd-first.
- Local non-RSP runs use the fallback GalSim-based PSF path rather than Rubin-native PSF computation.
- Native single-visit Butler loading is not yet a first-class packaged workflow.
