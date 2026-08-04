# Installation

## Prerequisites

- Python 3.9+
- `pip`
- `git`
- Optional for notebook workflows: JupyterLab or Jupyter Notebook

## Recommended Usage Model

The main intended science workflow is on the Rubin Science Platform (RSP).

- Use RSP and Butler-backed notebooks when you want Rubin-native PSF handling.
- Use TAP or a fully local install for lighter-weight demos, exploratory runs, or situations where Butler access is unavailable.
- In TAP or local mode, PSF handling falls back to the GalSim-based path rather than Rubin-native PSF computation.
- The packaged Butler-backed workflow in this repo currently targets coadds rather than native visit-level loading.

## 1. Clone The Repository

```bash
git clone <your-repo-url>
cd INJECT
```

## 2. Create And Activate A Virtual Environment

=== "macOS / Linux"

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

=== "Windows (PowerShell)"

    ```powershell
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    ```

## 3. Install The Package

For a standard user install:

```bash
python -m pip install --upgrade pip
pip install .
```

This project currently requires `numpy<2`. The package metadata should enforce that automatically on a fresh install.

For development, testing, and docs work:

```bash
pip install -e ".[dev,docs]"
```

For notebook-heavy work:

```bash
pip install -e ".[dev,docs,jupyter]"
```

If you already created an environment with NumPy 2.x and hit import or binary-compatibility issues, run:

```bash
pip install "numpy<2"
```

## 4. RSP Notebook Setup

If you are working on RSP, the most useful entry point is usually a Jupyter notebook rather than a CLI-first run.

Before you run the notebooks or pipeline on RSP, make sure the repository itself is present in your RSP workspace.

Typical RSP JupyterLab setup flow:

1. Launch a JupyterLab session on RSP.
2. Open `File` -> `New` -> `Terminal`.
3. Clone the GitHub repository into your RSP workspace from that terminal.
4. Install the package from the cloned repository so the notebooks can import the pipeline modules.

If the repo already lives on GitHub:

```bash
cd ~/repos
git clone https://github.com/whosneha/INJECT.git
cd INJECT
pip install -e ".[dev,docs,jupyter]"
```

If you are working from local unpublished changes, copy or upload the repository folder into your RSP workspace first, then open a terminal inside that copied folder and run the same install command there.

Recommended workflow:

1. Start a JupyterLab session on RSP.
2. Copy or clone this repository into your workspace.
3. Open a terminal in the repository root on RSP.
4. Install the package into the notebook environment from the cloned repository.
5. Open notebooks from that cloned repository folder.
6. Start from one of the RSP-oriented example notebooks.

Recommended notebooks:

- `notebooks/tutorial_injection.ipynb`
- `notebooks/injection_pipeline_rsp.ipynb`
- `notebooks/full_pipeline_rubin_psf.ipynb`
- `notebooks/multi_injection_pipeline_with_diagnostics_rsp.ipynb`

Once installed, notebook cells can import the package directly, for example:

```python
from star_cluster_injection import InjectionConfig, InjectionPipeline
```

Band and data-mode notes:

- Single-band runs are supported directly.
- Multiband runs are supported through the active-band configuration.
- If you already have a single-visit image array available, you can inject into it through the Python API.
- Native Butler-backed single-visit or `calexp` loading is not yet a packaged first-class workflow.

## 5. Verify The Installation

```bash
python -c "import star_cluster_injection as sci; print(sci.__version__)"
injection-pipeline --version
```

## 6. Optional Tooling Layers

Documentation:

```bash
mkdocs serve
```

Testing:

```bash
pytest
```

Packaging checks:

```bash
python -m build --no-isolation
```

## Common Setup Issues

!!! warning "Package installs but scientific imports fail"
    Confirm the active environment has the runtime dependencies from `requirements.txt` or install via `pip install -e ".[dev]"`.

!!! warning "Notebook kernel cannot import project modules"
    Select the same Python environment used for installation, then restart the notebook kernel.

!!! warning "Rubin Butler imports fail locally"
    That is expected outside an RSP environment. Use TAP-mode workflows or mock data examples when running remotely.

!!! warning "TAP or local runs do not reproduce Rubin-native PSF computation"
    Those modes use the GalSim-based fallback PSF path. Use the RSP notebook workflow when realistic Rubin PSF handling is part of the science goal.

!!! warning "`pip install` refuses to write into the system interpreter"
    Create and activate a virtual environment first. This is the expected workflow on modern Python distributions.
