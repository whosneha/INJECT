# CLI and Scripts Reference

## Main Script: `scripts/run_injection.py`

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
python scripts/run_injection.py --n-clusters 50 --band i --method smooth
```

```bash
python scripts/run_injection.py --token YOUR_TOKEN --ra 55.0 --dec -30.0 --band i
```

## Legacy CLI Module: `src/cli.py`

The repository includes an argparse CLI module with subcommands:

- `inject`
- `detect`
- `completeness`

Use this when integrating specific sub-steps into automation scripts.

## Output Locations

By default, script outputs are written under `plots/`, including image diagnostics and JSON catalogs.
