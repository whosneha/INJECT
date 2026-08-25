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

Use one venv just for this project, then register that venv as a Jupyter kernel.

Create it once:

```bash
git clone https://github.com/whosneha/INJECT.git
cd INJECT
python -m venv --system-site-packages ~/venvs/inject-rsp
source ~/venvs/inject-rsp/bin/activate
python -m pip install --upgrade pip
pip install -e ".[jupyter]"
python -m ipykernel install --user --name inject-rsp --display-name "Python (inject-rsp)"
```

Use it later from a terminal:

```bash
cd ~/path/to/INJECT
source ~/venvs/inject-rsp/bin/activate
python -c "import src; print(src.__version__)"
```

Use it later from JupyterLab:

1. Open the notebook from your `INJECT` checkout.
2. Choose `Kernel` -> `Change Kernel` -> `Python (inject-rsp)`.
3. Restart the kernel and run from the top.

If you are working from a cloned repo with local edits, open notebooks from that same repo checkout and use the `Python (inject-rsp)` kernel.

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

### Butler Notebook Requirement

Not every notebook needs Rubin Butler, but `dp2_early_release_injection_smoke_test.ipynb` does.

If you see:

```python
ModuleNotFoundError: No module named 'lsst.daf'
```

that usually means the notebook is running in the wrong kernel or outside RSP. A plain local venv can import `src`, but it will not provide Rubin Butler modules unless it can see the Rubin stack.

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
