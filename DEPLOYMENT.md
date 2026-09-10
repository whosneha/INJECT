# Deployment Notes

This repository is prepared for the two deployment paths that are feasible from this codebase without external credentials:

1. A pip-installable Python package.
2. A Harbor-ready container image.
3. A Rubin Science Platform install, either in the standard Rubin kernel or an optional user virtual environment.

## Package Build

```bash
cd INJECT
pip install -e ".[dev]"
python -m build
twine check dist/*
```

## Containerized Deployment To Harbor

Build the image:

```bash
cd INJECT
docker build -t harbor.canfar.net/candiapl/inject:0.1.0 .
```

Push once Harbor credentials are configured:

```bash
docker login harbor.canfar.net
docker push harbor.canfar.net/candiapl/inject:0.1.0
```

## Rubin Science Platform Deployment

RSP already provides Rubin Science Pipelines in `/opt/lsst/software/stack`. INJECT should use that stack; do not try to install `lsst_distrib` from PyPI.

For the simplest notebook path, use the standard Rubin Science Pipelines kernel and install INJECT into your RSP user environment:

```bash
setup lsst_distrib
cd INJECT
python -m pip install --user -e ".[jupyter]"
```

If you want a separate INJECT environment and a named notebook kernel, use the project venv setup.

Run this from a cloned copy of the repository inside RSP:

```bash
cd INJECT
bash scripts/setup_rsp_env.sh
```

The script creates `~/venvs/inject-rsp` with `--system-site-packages`, installs INJECT with its runtime requirements and Jupyter extras, writes `~/venvs/inject-rsp/bin/activate-rsp`, and registers a `Python (inject-rsp)` Jupyter kernel that loads `lsst_distrib` before Python starts.

Use it later in terminals with:

```bash
source ~/venvs/inject-rsp/bin/activate-rsp
```

For notebooks, select the `Python (inject-rsp)` kernel in RSP JupyterLab.

## Non-Containerized Deployment To Arc

Build a wheel locally:

```bash
python -m build
```

Copy the wheel and supporting config files to the Arc project area, then install there inside a fresh virtual environment:

```bash
pip install dist/inject_pipeline-0.1.0-py3-none-any.whl
```

## Suggested Verification

```bash
pytest
mkdocs build
injection-pipeline --version
```

## External Steps Still Required

- Actual Harbor push.
- Actual Arc filesystem copy.
- Any PyPI publication.
- Any Astropy contribution work.
