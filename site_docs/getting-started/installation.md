# Installation

## Choose A Setup Path

- Local setup: use this for development, tests, and non-Butler runs.
- RSP setup: use this for Rubin Butler notebooks and coadd-based workflows.

## Local Setup

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

Check the install:

```bash
python -c "from inject import InjectionConfig; print('INJECT import OK')"
pytest
```

## RSP Setup

RSP already provides the Rubin Science Pipelines environment in `/opt/lsst/software/stack`. You do not need a virtual environment just to import Rubin Butler; the important step is using a kernel or terminal where `lsst_distrib` has been set up.

### Option A: Standard Rubin Kernel

Use this first if you want the simplest RSP notebook path:

```bash
setup lsst_distrib
git clone https://github.com/whosneha/INJECT.git
cd INJECT
python -m pip install --user -e ".[jupyter]"
```

Then run notebooks with the standard Rubin Science Pipelines kernel.

### Option B: Project Venv Kernel

Use this if you want an isolated INJECT environment and a named `Python (inject-rsp)` kernel:

```bash
bash scripts/setup_rsp_env.sh
```

For a full clean-install walkthrough, including removing old kernels and verifying notebook imports, see [Rubin Science Platform Venv](rsp-venv.md).

Then use it later with:

- terminal: `source ~/venvs/inject-rsp/bin/activate-rsp`
- notebook: `Kernel` -> `Change Kernel` -> `Python (inject-rsp)`

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

Check the install:

```bash
source ~/venvs/inject-rsp/bin/activate-rsp
python -c "from lsst.daf.butler import Butler; print('Butler import OK')"
python -c "from inject import InjectionConfig; print('INJECT import OK')"
```

The setup script installs INJECT with the runtime dependencies from `pyproject.toml` plus the `jupyter` extra. Rubin's `lsst_distrib` comes from the RSP stack, not from PyPI.

It also writes `~/venvs/inject-rsp/bin/activate-rsp` and a Jupyter kernel launcher that runs `setup lsst_distrib` before starting Python, so Butler-backed notebooks inherit the Rubin environment automatically.

Use it later:

- In a terminal: `source ~/venvs/inject-rsp/bin/activate-rsp`
- In JupyterLab: open the notebook and choose `Kernel` -> `Change Kernel` -> `Python (inject-rsp)`
- Open notebooks from the same `INJECT` checkout you installed from

## Common Setup Issues

!!! warning "`ModuleNotFoundError: No module named 'lsst.daf'` in a notebook"
    Use an RSP kernel that loads `lsst_distrib`. Switch to the standard Rubin Science Pipelines kernel, or rerun `bash scripts/setup_rsp_env.sh` so the custom `Python (inject-rsp)` kernel gets the Rubin stack launcher.

!!! warning "The notebook cannot import `inject`"
    Select the same kernel you installed into and restart the kernel.

## Recommended Starting Points

- `notebooks/simple_rubin_mci_demo.ipynb`
- `notebooks/simple_batch_injection_demo.ipynb`
- `notebooks/simple_multiband_injection_demo.ipynb`
- `notebooks/dp2_early_release_injection_smoke_test.ipynb`
