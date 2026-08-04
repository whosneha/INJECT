# Customization

INJECT is most valuable when users tune it to their own science case rather than treating it as a fixed recipe.

## What You Can Customize

- Cluster profile family: `king`, `plummer`, `eff`, `sersic`.
- Cluster generation method: smooth extended profiles or discrete stars.
- Magnitude, half-light radius, concentration, and age ranges.
- Single-band or multiband execution.
- PSF strategy: actual Rubin PSF objects or analytic fallback FWHM.
- Whether bad Rubin PSF regions are flagged only or skipped entirely.
- Batch size, iteration count, and cache settings.
- Detection pipeline integration and output storage conventions.

Current packaged data-loading scope:

- Butler-backed Rubin workflows are coadd-based.
- Multiband Butler loading is supported across the configured active bands.
- If you already have a single-visit image array in memory, you can still inject into it through `load_data(image=...)`.
- Native Butler-backed single-visit or `calexp` loading is not yet exposed as a first-class workflow in this repo.

## Most Important Tradeoffs

- Smooth vs discrete:
  Smooth is faster and easier for sweeps. Discrete is heavier but better when stellar granularity matters.
- TAP vs Butler:
  TAP is lighter-weight and easier to run remotely. Butler/RSP is better when you need Rubin-native PSF fidelity.
- Record vs skip flagged PSF regions:
  Recording preserves more samples. Skipping can reduce systematic contamination in PSF-sensitive conclusions.

## Typical Customization Patterns

### Faint-cluster recovery

- Push `mag_max` fainter.
- Increase repetition count.
- Save per-bin completeness outputs.

### Compact-vs-extended comparison

- Sweep `r_half`.
- Hold profile type fixed first.
- Compare recovery across several detector thresholds.

### Profile-family comparison

- Run matched campaigns for `plummer`, `king`, `eff`, and `sersic`.
- Keep the random-seed strategy documented.
- Interpret recovery differences against profile morphology, not just total counts.

## Safe Defaults For New Users

- `method="smooth"`
- `profile_type="plummer"`
- `n_clusters=10` to `50`
- `mag_min=20`, `mag_max=24`
- `r_half_min=3`, `r_half_max=12`
- `skip_bad_psf_regions=False` until you have enough statistics to justify filtering
