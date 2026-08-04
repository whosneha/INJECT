# Contributing

## Local setup

```bash
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

## Documentation

```bash
mkdocs serve
```

## Packaging checks

```bash
python -m build
twine check dist/*
```

## Astropy note

This repository now satisfies the packaging and deployment-oriented release paths, but it does not itself contain an Astropy upstream contribution. If that requirement becomes the preferred path, it would need to be done as a separate contribution against Astropy.
