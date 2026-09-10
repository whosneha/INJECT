# INJECT

INJECT is a Rubin/LSST-oriented star-cluster injection pipeline for reproducible injection, recovery, and completeness studies.

It supports:

- smooth light-profile injections and discrete-star cluster generation
- notebook-first Rubin Science Platform workflows
- local or TAP-style exploratory runs outside Rubin infrastructure
- customizable downstream detection and benchmarking

## Installation

Pick one setup path:

- Local: for non-Butler runs, tests, and general development
- RSP: for Rubin Butler notebooks and coadd-based workflows

### Local

Simple setup:

```bash
bash scripts/setup_local_env.sh
```

Then activate it when you want to work:

```bash
source .venv/bin/activate
```

Manual equivalent:

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
python -c "import inject; print(inject.__version__)"
pytest
```

### Rubin Science Platform

RSP already provides the Rubin Science Pipelines environment. You do not need a virtual environment just to import Rubin Butler; the important step is using a kernel or terminal session where `lsst_distrib` has been set up.

Use the standard RSP Rubin kernel if you only need the platform stack plus this checkout. From an RSP terminal:

```bash
setup lsst_distrib
git clone https://github.com/whosneha/INJECT.git
cd INJECT
python -m pip install --user -e ".[jupyter]"
```

Then open the notebook with the standard Rubin Science Pipelines kernel.

Use the project venv setup if you want an isolated INJECT environment and a named `Python (inject-rsp)` kernel:

```bash
bash scripts/setup_rsp_env.sh
```

Then use it like this:

- Terminal use:
  `source ~/venvs/inject-rsp/bin/activate-rsp`
- Notebook use:
  open the notebook, choose `Kernel` -> `Change Kernel` -> `Python (inject-rsp)`, then restart the kernel

Manual equivalent:

```bash
source /opt/lsst/software/stack/loadLSST.bash
setup lsst_distrib
git clone https://github.com/whosneha/INJECT.git
cd INJECT
mkdir -p ~/venvs
python -m venv --system-site-packages ~/venvs/inject-rsp
source ~/venvs/inject-rsp/bin/activate
python -m pip install --upgrade pip
pip install -e ".[jupyter]"
```

For a custom venv kernel, use `scripts/setup_rsp_env.sh` rather than plain `python -m ipykernel install`; the script writes a kernel launcher that loads the Rubin stack before Python starts.

Check that the environment works:

```bash
source ~/venvs/inject-rsp/bin/activate-rsp
python -c "from lsst.daf.butler import Butler; print('Butler import OK')"
python -c "from inject import InjectionConfig; print('INJECT import OK')"
```

`scripts/setup_rsp_env.sh` does not install Rubin Science Pipelines. It uses the RSP copy in `/opt/lsst/software/stack`, runs `setup lsst_distrib`, installs the INJECT runtime dependencies from `pyproject.toml`, adds the notebook extras, and writes `~/venvs/inject-rsp/bin/activate-rsp`. It also registers a Jupyter kernel that launches with Rubin stack setup already loaded, so Butler-backed notebooks should work without extra notebook-side setup.

You do not need notebook cells that manually search for the repo root or call `sys.path.insert(...)`.

### Butler Notebook Note

`dp2_early_release_injection_smoke_test.ipynb` requires Rubin Butler and should be run on RSP with either the standard Rubin Science Pipelines kernel or the `Python (inject-rsp)` kernel.

If you see:

```python
ModuleNotFoundError: No module named 'lsst.daf'
```

the notebook is using a kernel that has not loaded `lsst_distrib`. Switch to the standard Rubin Science Pipelines kernel, or rerun `bash scripts/setup_rsp_env.sh` and restart with `Python (inject-rsp)`.

## Common Workflows

### Python API

```python
import numpy as np
from inject import InjectionConfig, InjectionPipeline

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

- `inject/`: the active package implementation
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
