# Deployment

This project is now set up for three practical delivery paths that satisfy the current release goal: a pip-installable Python package, a Rubin Science Platform install, and a container build that can be pushed to Harbor once credentials are available.

## Path 1: Pip-Installable Package

Build the package locally:

```bash
pip install -e ".[dev]"
python -m build
```

Recommended release checks:

- `pytest`
- `python -m build`
- `twine check dist/*`
- `mkdocs build`

## Path 2: Rubin Science Platform

Use this path for Butler-backed notebooks and coadd-based workflows on RSP.

RSP already provides Rubin Science Pipelines in `/opt/lsst/software/stack`. INJECT uses that platform stack; do not try to install `lsst_distrib` from PyPI.

### Standard Rubin Kernel

Use this first if you want the simplest notebook path:

```bash
setup lsst_distrib
cd INJECT
python -m pip install --user -e ".[jupyter]"
```

Then select the standard Rubin Science Pipelines kernel in RSP JupyterLab.

### Project Venv Kernel

Use this if you want an isolated INJECT environment and a named `Python (inject-rsp)` kernel.

From an RSP terminal in the cloned repository:

```bash
bash scripts/setup_rsp_env.sh
```

For a complete reset and reinstall procedure, see [Rubin Science Platform Venv](../getting-started/rsp-venv.md).

The setup script:

- loads the Rubin stack with `setup lsst_distrib`
- creates `~/venvs/inject-rsp` using `--system-site-packages`
- installs INJECT with its runtime dependencies and `jupyter` extras
- writes `~/venvs/inject-rsp/bin/activate-rsp` for future terminal sessions
- registers the `Python (inject-rsp)` Jupyter kernel

Use the environment later with:

```bash
source ~/venvs/inject-rsp/bin/activate-rsp
```

In RSP JupyterLab, select `Python (inject-rsp)` before running Butler-backed notebooks.

## Path 3: Harbor-Ready Container

A repository `Dockerfile` is included so the pipeline can be built as a container image.

Example build:

```bash
docker build -t harbor.canfar.net/candiapl/inject:0.1.0 .
```

Example push once Harbor credentials are configured:

```bash
docker login harbor.canfar.net
docker push harbor.canfar.net/candiapl/inject:0.1.0
```

## Arc Filesystem Or Shared-Compute Deployment

If the preferred delivery model is non-containerized:

- Build a wheel with `python -m build`.
- Copy `dist/` artifacts plus configs and docs to the target Arc project area.
- Create a virtual environment on the target system.
- Install from the built wheel rather than from a mutable checkout.

## What Still Requires External Access

- Actually publishing to Harbor.
- Actually copying artifacts into Arc project storage.
- Publishing to PyPI.
- Contributing code into Astropy.

Those steps are outside this workspace, but the repository now includes the packaging and deployment scaffolding needed to perform them cleanly.
