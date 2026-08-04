# Deployment

This project is now set up for two practical delivery paths that satisfy the current release goal: a pip-installable Python package and a container build that can be pushed to Harbor once credentials are available.

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

## Path 2: Harbor-Ready Container

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
