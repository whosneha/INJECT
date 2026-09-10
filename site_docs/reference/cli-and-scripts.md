# CLI and Scripts Reference

## Packaged CLI: `injection-pipeline`

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
injection-pipeline --n-clusters 50 --band i --method smooth
```

```bash
injection-pipeline --token YOUR_TOKEN --ra 55.0 --dec -30.0 --band i
```

## Script Entry Point: `scripts/run_injection.py`

The repository still includes `scripts/run_injection.py` for script-first workflows, but the maintained user-facing entry point is the packaged `injection-pipeline` command.

For notebooks, prefer importing from `inject` inside the selected project kernel rather than shelling out to a script path.

## CANFAR Scripts

The CANFAR scripts support task-array execution on HTCondor-style compute resources.

### `scripts/setup_canfar_env.sh`

Creates a project-local virtual environment for CANFAR jobs:

```bash
bash scripts/setup_canfar_env.sh
```

Default environment path:

```text
.venv-canfar
```

Use it later with:

```bash
source .venv-canfar/bin/activate-canfar
```

The setup script installs INJECT in editable mode and verifies that the package imports.

### `scripts/canfar_generate_tasks.py`

Generates a JSON task list for indexed jobs.

RSP/Butler-style task grid:

```bash
python scripts/canfar_generate_tasks.py \
	--mode rsp \
	--repo dp02 \
	--collection 2.2i/runs/DP0.2 \
	--tracts 3828,3829 \
	--patches 24,25 \
	--bands g,r,i \
	--n-clusters 100 \
	--output configs/canfar_tasks.json
```

TAP task grid:

```bash
python scripts/canfar_generate_tasks.py \
	--mode tap \
	--ras 55.0,56.25 \
	--decs -30.0,-30.15 \
	--bands i \
	--token-env RUBIN_TOKEN \
	--output configs/canfar_tasks.json
```

Mock task grid for smoke tests:

```bash
python scripts/canfar_generate_tasks.py \
	--mode mock \
	--bands g,r,i \
	--n-mock-tasks 2 \
	--output configs/canfar_tasks.json
```

### `scripts/canfar_run_tasks.py`

Runs one indexed task from a JSON task list. This is what the Condor wrapper calls.

Dry-run one task before submitting the array:

```bash
python scripts/canfar_run_tasks.py \
	--tasks-file configs/canfar_tasks.json \
	--task-index 0 \
	--output-root canfar_outputs \
	--dry-run
```

### `scripts/canfar_submit_jobs.sh`

Validates a task file, counts the number of tasks, prepares log/output folders, and submits the Condor array:

```bash
bash scripts/canfar_submit_jobs.sh \
	--tasks-file configs/canfar_tasks.json \
	--output-root canfar_outputs
```

Preview the Condor command without submitting:

```bash
bash scripts/canfar_submit_jobs.sh \
	--tasks-file configs/canfar_tasks.json \
	--output-root canfar_outputs \
	--dry-run
```

The helper uses `scripts/canfar_submit.condor` and `scripts/canfar_job_wrapper.sh` underneath.

### `scripts/canfar_parallel_10x1000.py`

Runs the canonical batch workflow: repeated injections, detector execution, pooled matching, and combined summary outputs.

Smoke-test the command without running the full batch:

```bash
python scripts/canfar_parallel_10x1000.py \
	--mode mock \
	--n-iterations 1 \
	--n-per-iter 1 \
	--dry-run
```

## Output Locations

By default, packaged CLI outputs are written under `outputs/`, including image diagnostics and JSON catalogs.

CANFAR task-array outputs are written under `canfar_outputs/` by default. Condor logs are written under `logs/` by default.
