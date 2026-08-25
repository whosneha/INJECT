# Project Formalization Summary

This file is a historical project note, not the primary user documentation.

For current install and workflow guidance, use:

- `README.md`
- `site_docs/getting-started/installation.md`
- `site_docs/getting-started/quickstart.md`
- `site_docs/guides/notebooks.md`

## Current State Snapshot

- The active import path is `inject`.
- The packaged CLI entry point is `injection-pipeline`.
- The maintained notebooks are the four top-level files in `notebooks/`.
- Older notebooks have been moved to `notebooks/archive/` for reference only.
- RSP guidance now assumes a per-user venv with `--system-site-packages` and an explicit Jupyter kernel.
- Package metadata now allows `numpy>=1.21.0` without a `<2` upper bound.

## Why This Note Was Reduced

Earlier versions of this summary described intermediate packaging decisions that no longer match the repository, including:

- a legacy wrapper package
- outdated usage examples
- notebook assumptions that required manual path setup

Keeping those details here would conflict with the current docs, so this file now serves only as a lightweight historical pointer.
