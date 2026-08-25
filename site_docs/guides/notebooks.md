# Notebook Guide

The active notebook set has been trimmed down to four maintained entry points. Older exploratory, poster, benchmark, and legacy-path notebooks have been moved to `notebooks/archive/`.

## Setup

Use the same Python environment as your package install and prefer the installed notebook kernel over any `sys.path` setup inside the notebook.

Typical RSP flow:

1. Clone or copy the repository into your workspace.
2. Install it into your venv.
3. Register and select that kernel in JupyterLab.
4. Open one of the active notebooks below.

Normal imports should look like:

```python
from src import InjectionConfig, InjectionPipeline
```

For save locations, prefer:

```python
from src import notebook_output_dir

RUN_OUTPUT_DIR = notebook_output_dir("my_run")
```

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

- `notebooks/archive/` contains older notebooks kept for historical reference.
- Archived notebooks are not part of the maintained onboarding path.
- If one of those older notebooks becomes important again, it should be refreshed before being promoted back into the active set.
