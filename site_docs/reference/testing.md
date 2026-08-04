# Testing

## Run The Test Suite

```bash
pytest
```

To run a focused subset:

```bash
pytest tests/test_config_basics.py
```

## Test Layers

- Lightweight configuration and packaging checks.
- Injection behavior and profile generation.
- PSF mask handling.
- Discrete-star and PSF diagnostic tests.

Representative test files:

- `tests/test_config_basics.py`
- `tests/test_packaging_metadata.py`
- `tests/test_injection.py`
- `tests/test_psf_mask_handling.py`

## Current Gaps To Fill Next

- Deterministic multiband alignment regression tests.
- Cache-on vs cache-off numerical consistency tests.
- Detection-retrieval integration tests with fixed seeds.
- CLI smoke tests in an environment with runtime dependencies installed.

## Reproducible Testing Pattern

1. Fix random seeds in all stochastic branches.
2. Keep deterministic tolerances for floating-point comparisons.
3. Validate both metadata and array-level outcomes where practical.
4. Separate lightweight package checks from full scientific-stack integration tests.
