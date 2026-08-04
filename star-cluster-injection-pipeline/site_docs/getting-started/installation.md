# Installation

## Prerequisites

- Python 3.9+
- `pip`
- `git`
- Optional for notebook workflows: JupyterLab or Jupyter Notebook

## 1. Clone The Repository

```bash
git clone <your-repo-url>
cd INJECT/star-cluster-injection-pipeline
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

## 4. Verify The Installation

```bash
python -c "import star_cluster_injection as sci; print(sci.__version__)"
injection-pipeline --version
```

## 5. Optional Tooling Layers

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
python -m build
```

## Common Setup Issues

!!! warning "Package installs but scientific imports fail"
    Confirm the active environment has the runtime dependencies from `requirements.txt` or install via `pip install -e ".[dev]"`.

!!! warning "Notebook kernel cannot import project modules"
    Select the same Python environment used for installation, then restart the notebook kernel.

!!! warning "Rubin Butler imports fail locally"
    That is expected outside an RSP environment. Use TAP-mode workflows or mock data examples when running remotely.

!!! warning "`pip install` refuses to write into the system interpreter"
    Create and activate a virtual environment first. This is the expected workflow on modern Python distributions.
