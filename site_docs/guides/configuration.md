# Configuration

The pipeline behavior is controlled through `InjectionConfig`, `ClusterConfig`, and lightweight JSON/YAML parameter presets used by scripts and shared run recipes.

## Configuration Surfaces

- `InjectionConfig`: run-wide behavior such as band selection, number of clusters, PSF strategy, and output handling.
- `ClusterConfig`: the cluster population itself, including magnitude range, radius range, age range, and profile family.
- CLI arguments or scripts: useful for one-off runs and quick experiments.
- YAML or JSON files: useful for reproducible campaigns, script inputs, and shared compute execution.

## Core Controls

- Number of clusters per run.
- Apparent AB magnitude range and half-light radius range.
- Profile type (`plummer`, `king`, `eff`, `sersic`).
- Injection method (`smooth` or `discrete`).
- Random seed for reproducibility.
- PSF behavior (actual PSF object vs fallback FWHM).
- Active bands for multiband runs.
- Whether flagged Rubin PSF regions are recorded or skipped.

## Example Python Configuration

```python
from inject import ClusterConfig, InjectionConfig

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

## Apparent Magnitudes And Distance Modulus

`ClusterConfig.mag_min` and `ClusterConfig.mag_max` are apparent AB magnitudes in the image band. The pipeline injects sources into an observed image, so the injected flux is controlled by how bright the cluster appears to Rubin, not by its intrinsic absolute magnitude.

Do not use a fixed distance modulus for all users. Choose one for the target system or science case, then convert physical absolute magnitudes into apparent magnitudes:

$$
m = M + \mu + A_\mathrm{band}
$$

where $M$ is absolute magnitude, $\mu$ is distance modulus, and $A_\mathrm{band}$ is optional band-specific extinction.

The config still receives apparent magnitude values either way:

| Starting point | What you put in `ClusterConfig` |
| --- | --- |
| You already know the observed brightness range to test | Put those apparent AB magnitudes directly into `mag_min` and `mag_max` |
| You know the physical absolute-magnitude range and target distance | Convert first, then put the resulting apparent AB magnitudes into `mag_min` and `mag_max` |

Direct apparent-magnitude setup:

```python
cluster_config = ClusterConfig(
    profile_type="king",
    mag_min=20.0,
    mag_max=26.0,
    r_half_min=2.0,
    r_half_max=10.0,
)
```

This injects clusters with observed magnitudes between 20 and 26 in the selected band.

Distance-modulus setup:

```python
from inject import (
    ClusterConfig,
    InjectionConfig,
    apparent_magnitude_from_absolute,
    distance_modulus,
)

mu = distance_modulus(800_000)  # distance in parsecs

cluster_config = ClusterConfig(
    profile_type="king",
    mag_min=apparent_magnitude_from_absolute(-6.0, distance_modulus_value=mu),
    mag_max=apparent_magnitude_from_absolute(-2.0, distance_modulus_value=mu),
    r_half_min=2.0,
    r_half_max=10.0,
)

config = InjectionConfig(
    run_name="m31_like_clusters",
    band="i",
    cluster_config=cluster_config,
)
```

For `distance_pc=800_000`, `distance_modulus(800_000)` is about 24.52, so this is equivalent to an apparent-magnitude range of roughly 18.52 to 22.52 before extinction.

For quick detector tests, it is fine to choose apparent magnitudes directly, such as `mag_min=20.0` and `mag_max=26.0`. For science runs tied to a specific galaxy, satellite, or distance bin, record the assumed distance modulus and extinction alongside the run configuration.

## YAML-Based Configuration

Starter config: `configs/injection_config.yaml`

Use YAML when you need a compact human-readable run recipe across collaborators and compute environments.

This starter file is a field-aligned preset for the current `InjectionConfig` and `ClusterConfig` structure. It is meant as a clean template to copy and adapt, not as proof of a generic `InjectionConfig.from_yaml(...)` loader in the core API.

## Practical Defaults

For early testing:

- `n_clusters`: 10 to 50
- Magnitude range: 20 to 24
- `r_half` range: 3 to 20 px
- Fixed seed for debugging, variable seed for production completeness studies

## Single-Band Vs Multi-Band

Users can choose one band, a specific combination of bands, or all Rubin bands.

Single-band runs use `band`:

```python
config = InjectionConfig(
    band="i",
)
```

Matched multiband runs use `bands`. When `bands` is provided, it overrides the single `band` value:

```python
config = InjectionConfig(
    bands=["g", "r", "i"],
)
```

All Rubin optical bands are just the full explicit list:

```python
config = InjectionConfig(
    bands=["u", "g", "r", "i", "z", "y"],
)
```

`config.active_bands` always returns the list the pipeline will use. Valid band names are `u`, `g`, `r`, `i`, `z`, and `y`.

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
