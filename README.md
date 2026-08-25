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
python -c "import src; print(src.__version__)"
pytest
```

### Rubin Science Platform

Simple setup:

```bash
bash scripts/setup_rsp_env.sh
```

Then use it like this:

- Terminal use:
  `source ~/venvs/inject-rsp/bin/activate`
- Notebook use:
  open the notebook, choose `Kernel` -> `Change Kernel` -> `Python (inject-rsp)`, then restart the kernel

Manual equivalent:

```bash
source /opt/lsst/software/stack/loadLSST.bash
setup lsst_distrib
git clone https://github.com/whosneha/INJECT.git
cd INJECT
python -m venv --system-site-packages ~/venvs/inject-rsp
source ~/venvs/inject-rsp/bin/activate
python -m pip install --upgrade pip
pip install -e ".[jupyter]"
python -m ipykernel install --user --name inject-rsp --display-name "Python (inject-rsp)"
```

Check that the environment works:

```bash
source ~/venvs/inject-rsp/bin/activate
python -c "from lsst.daf.butler import Butler; print('Butler import OK')"
python -c "from src import InjectionConfig; print('INJECT import OK')"
```

You do not need notebook cells that manually search for the repo root or call `sys.path.insert(...)`.

### Butler Notebook Note

`dp2_early_release_injection_smoke_test.ipynb` requires Rubin Butler and should be run on RSP with the `Python (inject-rsp)` kernel.

If you see:

```python
ModuleNotFoundError: No module named 'lsst.daf'
```

the notebook is either using the wrong kernel or the Rubin stack was not set up before the venv was created.

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
