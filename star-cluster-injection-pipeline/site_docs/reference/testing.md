# Testing

## Run The Test Suite

```bash
pytest -q
```

To run a focused subset:

```bash
pytest tests/test_injection.py -q
```

## Current Test Areas

- Injection behavior
- Discrete star generation
- Detailed PSF logic

Representative test files:

- `tests/test_injection.py`
- `tests/test_discrete_stars.py`
- `tests/test_psf_detailed.py`

## Suggested Additions

- Multiband alignment regression tests.
- Cache-on vs cache-off numerical consistency tests.
- Detection-retrieval integration tests with fixed seeds.

## Reproducible Testing Pattern

1. Fix random seeds in all stochastic branches.
2. Keep deterministic tolerances for floating-point comparisons.
3. Validate both metadata and array-level outcomes where practical.
