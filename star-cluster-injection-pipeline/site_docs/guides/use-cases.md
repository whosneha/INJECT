# Use Cases

This project is most useful when you know what scientific or technical question you are trying to answer. The pipeline supports several common modes of use.

## Detector Benchmarking

Use INJECT when you want to ask, "What kinds of clusters does my detector recover reliably?"

Recommended setup:

- One band first, then multiband once the pipeline is stable.
- Fixed seeds while tuning.
- Modest injection counts for fast iteration.
- Saved truth and detection catalogs for every run.

## Completeness Studies

Use INJECT when you need recovery fractions as a function of magnitude, size, age, or profile type.

Recommended setup:

- Wider parameter ranges.
- Repeated batches over the same footprint or matched footprints.
- Clear bookkeeping for each run directory.
- Post-processing that groups results by the science variables you care about.

## PSF-Sensitive Validation

Use INJECT when PSF realism is part of the scientific question, especially in Rubin/RSP environments.

Recommended setup:

- Butler/RSP access if available.
- `use_actual_psf=True`.
- PSF mask flag recording enabled.
- Separate summaries for flagged and unflagged injection positions.

## Remote Rubin Access Without Full Stack

Use TAP-mode workflows when you need to work from a laptop or non-RSP environment.

Recommended setup:

- Token-based access.
- Smaller cutouts.
- Analytic or metadata-driven PSF fallback.
- Notebook-first exploration before large runs.

## Batch Campaigns On Shared Compute

Use the batch scripts and `InjectionPipeline.run_batch(...)` when you need many repeated injections.

Recommended setup:

- Per-run config snapshots.
- One output directory per campaign.
- A detector callable that is versioned and documented.
- Resource planning for PSF caching and output storage.
