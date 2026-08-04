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

For development, testing, and docs work:

```bash
pip install -e ".[dev,docs]"
```

For notebook-heavy work:

```bash
pip install -e ".[dev,docs,jupyter]"
```

## 4. RSP Notebook Setup

If you are working on RSP, the most useful entry point is usually a Jupyter notebook rather than a CLI-first run.

Recommended workflow:

1. Start a JupyterLab session on RSP.
2. Clone this repository into your workspace.
3. Open a terminal in the repository root.
4. Install the package into the notebook environment.
5. Start from one of the RSP-oriented example notebooks.

Recommended notebooks:

- `notebooks/tutorial_injection.ipynb`
- `notebooks/injection_pipeline_rsp.ipynb`
- `notebooks/full_pipeline_rubin_psf.ipynb`
- `notebooks/multi_injection_pipeline_with_diagnostics_rsp.ipynb`

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
