# Notebook Guide

The project includes many notebooks for different levels of depth.

## Suggested Learning Path

1. `tutorial_injection.ipynb`: conceptual walkthrough.
2. `simple_inject.ipynb`: minimal injection demo.
3. `simple_multiband_injection_demo.ipynb`: multiband extension.
4. `full_pipeline_demo.ipynb`: broader pipeline example.
5. `full_pipeline_rubin_psf.ipynb`: realistic PSF workflow.

## Notebook Setup Tips

- Use the same Python environment as your package install.
- Restart kernel after dependency changes.
- Keep relative paths anchored to `star-cluster-injection-pipeline`.

## Good Notebook Habits For Reproducibility

- Put all key run parameters in one top cell.
- Print seed and config before execution.
- Save outputs with timestamped or hash-tagged filenames.
- Export key charts to `plots/` for later comparison.

## Common Pitfalls

- Mixed kernels causing import errors.
- Running cells out of order and using stale in-memory state.
- Accidentally changing config in one cell and forgetting downstream effects.

## From Notebook To Script

When your notebook run is stable:

1. Move parameter block into YAML or CLI args.
2. Move core execution into a script.
3. Keep notebook for interpretation and visualization only.

This split improves repeatability and reduces accidental drift.
