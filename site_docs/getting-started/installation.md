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
python -c "from src import InjectionConfig; print('INJECT import OK')"
pytest
```

## RSP Setup

Simple setup:

```bash
bash scripts/setup_rsp_env.sh
```

Then use it later with:

- terminal: `source ~/venvs/inject-rsp/bin/activate`
- notebook: `Kernel` -> `Change Kernel` -> `Python (inject-rsp)`

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

Check the install:

```bash
source ~/venvs/inject-rsp/bin/activate
python -c "from lsst.daf.butler import Butler; print('Butler import OK')"
python -c "from src import InjectionConfig; print('INJECT import OK')"
```

Use it later:

- In a terminal: `source ~/venvs/inject-rsp/bin/activate`
- In JupyterLab: open the notebook and choose `Kernel` -> `Change Kernel` -> `Python (inject-rsp)`
- Open notebooks from the same `INJECT` checkout you installed from

## Common Setup Issues

!!! warning "`ModuleNotFoundError: No module named 'lsst.daf'` in a notebook"
    Use the RSP setup above. That notebook needs Rubin Butler, so a plain local venv will not work.

!!! warning "The notebook cannot import `src`"
    Select the same kernel you installed into and restart the kernel.

## Recommended Starting Points

- `notebooks/simple_rubin_mci_demo.ipynb`
- `notebooks/simple_batch_injection_demo.ipynb`
- `notebooks/simple_multiband_injection_demo.ipynb`
- `notebooks/dp2_early_release_injection_smoke_test.ipynb`
