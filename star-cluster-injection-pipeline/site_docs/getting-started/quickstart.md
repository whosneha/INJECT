# Quickstart

This quickstart walks through a full basic run from raw image array to saved outputs.

## Run A Scripted Injection

From `star-cluster-injection-pipeline`:

```bash
python scripts/run_injection.py \
  --n-clusters 10 \
  --band i \
  --profile plummer \
  --method smooth
```

This produces output artifacts under `plots/` including:

- `injection_result.png`
- `injection_catalog.json`

## TAP Mode Example

```bash
python scripts/run_injection.py \
  --token YOUR_TOKEN \
  --ra 55.0 \
  --dec -30.0 \
  --size 120 \
  --band i \
  --n-clusters 25
```

## RSP / Butler Example

```bash
python scripts/run_injection.py \
  --repo /repo/main \
  --collection YOUR_COLLECTION \
  --tract 9615 \
  --patch 30 \
  --band i \
  --n-clusters 25
```

## What To Inspect First

1. Confirm injected locations in `plots/injection_result.png`.
2. Open `plots/injection_catalog.json` and verify the metadata section.
3. Compare input ranges (magnitude, `r_half`) against your science goals.

## Minimal Python Example

```python
import numpy as np
from src.pipeline import InjectionPipeline
from src.config import InjectionConfig

image = np.random.normal(100, 15, (500, 500))
cfg = InjectionConfig()

pipe = InjectionPipeline(cfg)
pipe.load_data(image=image)
catalog = pipe.generate_catalog()

print(f"Generated {len(catalog)} synthetic clusters")
```

## Next Steps

- Move to [Configuration](../guides/configuration.md) to tune simulation parameters.
- Use [Pipeline Workflows](../guides/pipeline-workflows.md) for batch and multiband runs.
- Review [Detection and Completeness](../guides/detection-and-completeness.md) for downstream analysis.
