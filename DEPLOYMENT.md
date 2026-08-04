# Deployment Notes

This repository is prepared for the two deployment paths that are feasible from this codebase without external credentials:

1. A pip-installable Python package.
2. A Harbor-ready container image.

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

## Non-Containerized Deployment To Arc

Build a wheel locally:

```bash
python -m build
```

Copy the wheel and supporting config files to the Arc project area, then install there inside a fresh virtual environment:

```bash
pip install dist/star_cluster_injection_pipeline-0.1.0-py3-none-any.whl
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
