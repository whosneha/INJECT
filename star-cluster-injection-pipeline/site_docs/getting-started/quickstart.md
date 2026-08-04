# Quickstart

This quickstart walks through a first packaged run and a minimal Python usage pattern.

## Run A First Injection

From `star-cluster-injection-pipeline`:

```bash
injection-pipeline \
  --n-clusters 10 \
  --band i \
  --profile plummer \
  --method smooth
```

This produces output artifacts under `outputs/` including:

- `injection_result.png`
- `injection_catalog.json`

## TAP Mode Example

```bash
injection-pipeline \
  --token YOUR_TOKEN \
  --ra 55.0 \
  --dec -30.0 \
  --size 120 \
  --band i \
  --n-clusters 25
```

## RSP / Butler Example

```bash
injection-pipeline \
  --repo /repo/main \
  --collection YOUR_COLLECTION \
  --tract 9615 \
  --patch 30 \
  --band i \
  --n-clusters 25
```

## What To Inspect First

1. Confirm injected locations in `outputs/injection_result.png`.
2. Open `outputs/injection_catalog.json` and verify the metadata section.
3. Compare input ranges (magnitude, `r_half`) against your science goals.

## Minimal Python Example

```python
import numpy as np
from star_cluster_injection import InjectionConfig, InjectionPipeline

image = np.random.normal(100, 15, (500, 500))
cfg = InjectionConfig()

pipe = InjectionPipeline(cfg)
pipe.load_data(image=image)
catalog = pipe.generate_catalog()

print(f"Generated {len(catalog)} synthetic clusters")
```

## Next Steps

- Read [Use Cases](../guides/use-cases.md) to choose the right operating mode.
- Move to [Configuration](../guides/configuration.md) to tune simulation parameters.
- Use [Pipeline Workflows](../guides/pipeline-workflows.md) for batch and multiband runs.
- Review [Detection and Completeness](../guides/detection-and-completeness.md) for downstream analysis.
