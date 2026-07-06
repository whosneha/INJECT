# Installation

## Prerequisites

- Python 3.10+
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

## 3. Install Runtime Dependencies

```bash
pip install -U pip
pip install -r requirements.txt
```

## 4. Make Local Package Imports Work

This project currently uses a source layout without a packaged installer. Add the project root to your Python path:

=== "Temporary (current shell)"

    ```bash
    export PYTHONPATH="$PWD"
    ```

=== "Persistent (zsh)"

    ```bash
    echo 'export PYTHONPATH="$PYTHONPATH:$HOME/path/to/INJECT/star-cluster-injection-pipeline"' >> ~/.zshrc
    source ~/.zshrc
    ```

## 5. Verify The Installation

```bash
python -c "import src; print('Import OK')"
pytest -q
```

## Optional: Install Documentation Tooling

```bash
pip install -r docs_requirements.txt
mkdocs serve
```

Then open the local docs URL shown in terminal (usually `http://127.0.0.1:8000`).

## Common Setup Issues

!!! warning "ModuleNotFoundError: No module named 'src'"
    Ensure you are in `star-cluster-injection-pipeline` and have `PYTHONPATH` set to that directory.

!!! warning "Notebook kernel cannot import project modules"
    Select the same Python environment used for installation, then restart the notebook kernel.

!!! warning "Rubin Butler imports fail locally"
    That is expected outside an RSP environment. Use TAP-mode workflows or mock data examples when running remotely.
