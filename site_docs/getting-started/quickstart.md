# Quickstart

This quickstart walks through a first packaged run and a minimal Python usage pattern.

## Run A First Injection

From the repository root:

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

On RSP, do this from a copy of the repository that lives in your RSP workspace. A typical setup is:

```bash
cd ~/repos
git clone https://github.com/whosneha/INJECT.git
cd INJECT
bash scripts/setup_rsp_env.sh
```

Open the RSP JupyterLab terminal through `File` -> `New` -> `Terminal`, run the commands above there, then select the `Python (inject-rsp)` kernel before opening notebooks from the cloned `INJECT/` folder. For later terminal sessions, run `source ~/venvs/inject-rsp/bin/activate-rsp` from any shell.

If your latest work is only on your laptop, upload or copy the repo into RSP first, then run the install command from that copied folder.

Once installed, notebook cells can import and call the package functions directly:

```python
from inject import InjectionConfig, InjectionPipeline
```

Band selection is controlled in `InjectionConfig`:

```python
single_band = InjectionConfig(band="i")
three_bands = InjectionConfig(bands=["g", "r", "i"])
all_bands = InjectionConfig(bands=["u", "g", "r", "i", "z", "y"])
```

Use one band for quick tests, a subset for matched-color workflows, or all six bands for full multiband completeness runs.

For notebook output folders, prefer:

```python
from inject import notebook_output_dir

RUN_OUTPUT_DIR = notebook_output_dir("quickstart_demo")
```

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
from inject import InjectionConfig, InjectionPipeline

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
- Use [Notebook Guide](../guides/notebooks.md) for the maintained notebook set and archive status.
- Review [Detection and Completeness](../guides/detection-and-completeness.md) for downstream analysis.
