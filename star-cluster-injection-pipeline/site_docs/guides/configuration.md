# Configuration

The pipeline behavior is controlled through config objects and YAML presets.

## Core Controls

Typical parameters you will tune:

- Number of clusters per run.
- Magnitude range and half-light radius range.
- Profile type (`plummer`, `king`, `eff`, `sersic`).
- Random seed for reproducibility.
- PSF behavior (actual PSF object vs fallback FWHM).
- Active bands for multiband runs.

## YAML-Based Configuration

Starter config: `configs/injection_config.yaml`

Use YAML when you need reproducible run recipes across collaborators and compute environments.

## Practical Defaults

For early testing:

- `n_clusters`: 10 to 50
- Magnitude range: 20 to 24
- `r_half` range: 3 to 20 px
- Fixed seed for debugging, variable seed for production completeness studies

## Single-Band Vs Multi-Band

Single-band is ideal for algorithm debugging and fast iteration.

Multi-band runs are recommended when:

- Detection logic uses color information.
- You need realistic cross-band recovery statistics.
- You want physically aligned injections at shared pixel coordinates.

## Reproducibility Checklist

1. Save the full config used for each run.
2. Record code commit hash.
3. Save seed strategy (single, sequence, or randomized).
4. Keep run metadata alongside output catalogs.
