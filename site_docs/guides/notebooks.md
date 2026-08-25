# Notebook Guide

The active notebook set is intentionally small and focused on the four maintained entry points below.

## Setup

Use the same Python environment as your package install and prefer the installed notebook kernel over any `sys.path` setup inside the notebook.

Simple rule:

- terminal run: activate the same venv you installed into
- notebook run: select the same Jupyter kernel you registered from that venv

On RSP, the usual pattern is:

1. Run `source /opt/lsst/software/stack/loadLSST.bash`
2. Run `setup lsst_distrib`
3. Create `~/venvs/inject-rsp`
4. Install `INJECT`
5. Select `Python (inject-rsp)` in JupyterLab

Normal imports should look like:

```python
from src import InjectionConfig, InjectionPipeline
```

For save locations, prefer:

```python
from src import notebook_output_dir

RUN_OUTPUT_DIR = notebook_output_dir("my_run")
```

## Maintenance Status

- The four notebooks listed below are the maintained entry points for current workflows.
- Older exploratory notebooks were moved to `notebooks/archive/`.
- Files in `notebooks/archive/` are kept for reference, but they are not the recommended starting point and may still reflect older assumptions.

## Active Notebooks

### 1. Simple Single-Run

- [simple_rubin_mci_demo.ipynb](https://github.com/whosneha/INJECT/blob/main/notebooks/simple_rubin_mci_demo.ipynb)
- Best for a first end-to-end Rubin coadd injection run.

### 2. Batch Completeness

- [simple_batch_injection_demo.ipynb](https://github.com/whosneha/INJECT/blob/main/notebooks/simple_batch_injection_demo.ipynb)
- Best for repeated pooled runs and completeness studies.

### 3. Multiband

- [simple_multiband_injection_demo.ipynb](https://github.com/whosneha/INJECT/blob/main/notebooks/simple_multiband_injection_demo.ipynb)
- Best for matched injections across multiple bands.

### 4. Early-Release Smoke Test

- [dp2_early_release_injection_smoke_test.ipynb](https://github.com/whosneha/INJECT/blob/main/notebooks/dp2_early_release_injection_smoke_test.ipynb)
- Best for quickly checking that a new Butler repo/collection/data ID works with the current injection path.

## Suggested Order

1. `simple_rubin_mci_demo.ipynb`
2. `simple_batch_injection_demo.ipynb`
3. `simple_multiband_injection_demo.ipynb`
4. `dp2_early_release_injection_smoke_test.ipynb`

## Notes

- Use the same package install and kernel across all four notebooks.
- Prefer `src.notebook_output_dir(...)` or `config.output_dir` over hard-coded repo paths.
- `dp2_early_release_injection_smoke_test.ipynb` requires Rubin Butler and is meant for RSP-backed kernels, not a plain local notebook environment.
