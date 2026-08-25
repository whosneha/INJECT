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

=== "Rubin Science Platform"

    ```bash
    python -m venv --system-site-packages ~/venvs/inject-rsp
    source ~/venvs/inject-rsp/bin/activate
    ```

On RSP, `--system-site-packages` is usually the right choice because it lets your personal venv reuse the shared Rubin stack while keeping your own `pip` installs out of the shared environment.

### Project-Specific RSP Venv

If you want one environment dedicated to INJECT on RSP, use this exact pattern:

```bash
cd ~/repos
git clone https://github.com/whosneha/INJECT.git
cd INJECT
python -m venv --system-site-packages ~/venvs/inject-rsp
source ~/venvs/inject-rsp/bin/activate
python -m pip install --upgrade pip
pip install -e ".[jupyter]"
python -m ipykernel install --user --name inject-rsp --display-name "Python (inject-rsp)"
```

From then on:

- in a terminal, activate it with `source ~/venvs/inject-rsp/bin/activate`
- in JupyterLab, select `Kernel` -> `Change Kernel` -> `Python (inject-rsp)`
- open notebooks from the same `INJECT` checkout you installed from

## 3. Install The Package

`pip` is the tool that installs this repository as a Python package into your active environment.

When you run `pip install ...`, it:

- reads the package metadata from `pyproject.toml`
- installs the required dependencies
- makes `src` importable from Python and notebooks
- installs the `injection-pipeline` command-line entry point

The most common install patterns are:

- Standard install from a local clone: `pip install .`
- Editable install for development and notebooks: `pip install -e ".[dev,docs,jupyter]"`
- Direct install from GitHub: `pip install "git+https://github.com/whosneha/INJECT.git"`

For a standard user install:

```bash
python -m pip install --upgrade pip
pip install .
```

This project supports `numpy>=1.21.0` and is no longer capped below NumPy 2.

For development, testing, and docs work:

```bash
pip install -e ".[dev,docs]"
```

For notebook-heavy work:

```bash
pip install -e ".[dev,docs,jupyter]"
```

If you want a notebook kernel tied to this environment:

```bash
python -m ipykernel install --user --name inject-rsp --display-name "Python (inject-rsp)"
```

After that, select the `Python (inject-rsp)` kernel in JupyterLab and import the package normally. You should not need notebook cells that manually search for the repository root or call `sys.path.insert(...)`.

For a quick terminal check on RSP:

```bash
source ~/venvs/inject-rsp/bin/activate
python -c "import sys; print(sys.executable)"
python -c "import src; print(src.__version__)"
python -c "from lsst.daf.butler import Butler; print('Butler import OK')"
```

### One-Time RSP Jupyter Kernel Setup

If you want the shortest reliable setup for RSP notebooks, run this once in an RSP terminal:

```bash
python -m venv --system-site-packages ~/venvs/inject-rsp
source ~/venvs/inject-rsp/bin/activate
pip install -e /path/to/INJECT ipykernel
python -m ipykernel install --user --name inject-rsp --display-name "Python (inject-rsp)"
```

After that, you usually do not need any extra notebook setup beyond selecting the `Python (inject-rsp)` kernel in JupyterLab.

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
python -m venv --system-site-packages ~/venvs/inject-rsp
source ~/venvs/inject-rsp/bin/activate
pip install -e ".[dev,docs,jupyter]"
python -m ipykernel install --user --name inject-rsp --display-name "Python (inject-rsp)"
```

If you are working from local unpublished changes, copy or upload the repository folder into your RSP workspace first, then open a terminal inside that copied folder and run the same install command there.

Recommended workflow:

1. Start a JupyterLab session on RSP.
2. Copy or clone this repository into your workspace.
3. Open a terminal in the repository root on RSP.
4. Install the package into the notebook environment from the cloned repository.
5. Register a dedicated kernel if you want the environment selectable in JupyterLab.
6. Open notebooks from that cloned repository folder.
7. Start from one of the RSP-oriented example notebooks.

Recommended notebooks:

- `notebooks/simple_rubin_mci_demo.ipynb`
- `notebooks/simple_batch_injection_demo.ipynb`
- `notebooks/simple_multiband_injection_demo.ipynb`
- `notebooks/dp2_early_release_injection_smoke_test.ipynb`

Once installed, notebook cells can import the package directly, for example:

```python
from src import InjectionConfig, InjectionPipeline
```

Band and data-mode notes:

- Single-band runs are supported directly.
- Multiband runs are supported through the active-band configuration.
- If you already have a single-visit image array available, you can inject into it through the Python API.
- Native Butler-backed single-visit or `calexp` loading is not yet a packaged first-class workflow.

## 5. Verify The Installation

```bash
python -c "import src; print(src.__version__)"
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
    Select the same Python environment or registered kernel used for installation, then restart the notebook kernel.

!!! warning "Rubin Butler imports fail locally"
    That is expected outside an RSP environment. Use TAP-mode workflows or mock data examples when running remotely.

!!! warning "`ModuleNotFoundError: No module named 'lsst.daf'` in a notebook"
    The notebook is not running with an RSP-backed kernel. On RSP, switch to `Python (inject-rsp)` and restart the kernel. Outside RSP, Butler notebooks will not work unless you separately provide the Rubin stack.

!!! warning "TAP or local runs do not reproduce Rubin-native PSF computation"
    Those modes use the GalSim-based fallback PSF path. Use the RSP notebook workflow when realistic Rubin PSF handling is part of the science goal.

!!! warning "`pip install` refuses to write into the system interpreter"
    Create and activate a virtual environment first. This is the expected workflow on modern Python distributions.
