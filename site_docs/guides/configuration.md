# Configuration

The pipeline behavior is controlled through `InjectionConfig`, `ClusterConfig`, and YAML-style parameter presets.

## Configuration Surfaces

- `InjectionConfig`: run-wide behavior such as band selection, number of clusters, PSF strategy, and output handling.
- `ClusterConfig`: the cluster population itself, including magnitude range, radius range, age range, and profile family.
- CLI arguments or scripts: useful for one-off runs and quick experiments.
- YAML or JSON files: useful for reproducible campaigns and shared compute execution.

## Core Controls

- Number of clusters per run.
- Magnitude range and half-light radius range.
- Profile type (`plummer`, `king`, `eff`, `sersic`).
- Injection method (`smooth` or `discrete`).
- Random seed for reproducibility.
- PSF behavior (actual PSF object vs fallback FWHM).
- Active bands for multiband runs.
- Whether flagged Rubin PSF regions are recorded or skipped.

## Example Python Configuration

```python
from star_cluster_injection import ClusterConfig, InjectionConfig

config = InjectionConfig(
    run_name="paper_draft_rsp_i_band",
    band="i",
    n_clusters=250,
    cutout_size=1500,
    use_actual_psf=True,
    skip_bad_psf_regions=False,
    cluster_config=ClusterConfig(
        profile_type="plummer",
        mag_min=20.0,
        mag_max=25.0,
        r_half_min=2.0,
        r_half_max=12.0,
    ),
)
```

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

## Parameter Strategy By Stage

- Early development: small `n_clusters`, fixed seed, one band, mock data or TAP access.
- Detector benchmarking: wider magnitude and size ranges with several repeated runs.
- Production completeness: batch execution, saved config snapshots, and explicit output directories.
- PSF-sensitive studies: Butler/RSP access, PSF mask flag recording, and post-run auditing of flagged regions.

## Reproducibility Checklist

1. Save the full config used for each run.
2. Record code commit hash.
3. Save seed strategy (single, sequence, or randomized).
4. Keep run metadata alongside output catalogs.
