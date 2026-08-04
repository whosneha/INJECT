# CLI and Scripts Reference

## Packaged CLI: `injection-pipeline`

### Core Arguments

- `--n-clusters`: number of synthetic clusters to inject.
- `--band`: Rubin filter (`u`, `g`, `r`, `i`, `z`, `y`).
- `--profile`: one of `plummer`, `king`, `eff`, `sersic`.
- `--method`: `smooth` or `discrete`.
- `--seed`: random seed for reproducible catalogs.

### Catalog Property Ranges

- `--mag-min`, `--mag-max`
- `--r-half-min`, `--r-half-max`
- `--n-stars-min`, `--n-stars-max` (discrete mode)
- `--imf` (discrete mode)

### Data Access Modes

- TAP mode: provide `--token`, `--ra`, `--dec`.
- RSP Butler mode: provide `--repo`, `--collection`, `--tract`, `--patch`.
- Mock mode: automatic fallback when Rubin stack is unavailable.

### Examples

```bash
injection-pipeline --n-clusters 50 --band i --method smooth
```

```bash
injection-pipeline --token YOUR_TOKEN --ra 55.0 --dec -30.0 --band i
```

## Script Entry Point: `scripts/run_injection.py`

The repository still includes `scripts/run_injection.py` for script-first workflows and notebooks that shell out to a file path rather than the packaged console entry point.

## Output Locations

By default, packaged CLI outputs are written under `outputs/`, including image diagnostics and JSON catalogs.
