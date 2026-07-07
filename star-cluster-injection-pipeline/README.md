# Star Cluster Injection Pipeline

This project provides a framework for injecting artificial star clusters into images from the LSST Rubin Observatory data. The pipeline includes functionalities for data access, PSF extraction, light profile definitions, cluster injection, detection testing, completeness analysis, and visualization.

## Project Structure

```
star-cluster-injection-pipeline
├── src
│   ├── __init__.py
│   ├── data_access.py       # Interfaces with Rubin Butler to load images
│   ├── psf_utils.py         # PSF extraction and convolution utilities
│   ├── light_profiles.py     # Definitions of cluster surface brightness profiles
│   ├── inject.py             # Core routines for injecting clusters
│   ├── detection_test.py     # Detection pipeline and comparison routines
│   ├── completeness.py       # Completeness curve computations
│   ├── io.py                 # Save/load functionalities for catalogs and results
│   ├── plotting.py           # Visualization utilities
│   └── cli.py                # Command-line interface for the pipeline
├── notebooks
│   ├── tutorial_injection.ipynb  # Tutorial on using the pipeline
│   └── example_completeness.ipynb # Example of completeness curve analysis
├── tests
│   └── test_injection.py       # Unit tests for injection routines
├── README.md                   # Project documentation
└── requirements.txt            # Python dependencies
```

## Installation

To install the required dependencies, run:

```
pip install -r requirements.txt
```

## Usage

1. **Data Access**: Use `data_access.py` to load coadded images or individual visits from the Rubin Butler.
2. **PSF Extraction**: Utilize `psf_utils.py` to extract PSFs and convolve cluster profiles.
3. **Inject Clusters**: Use `inject.py` to inject artificial clusters into your images.
4. **Detection Testing**: Run detection tests with `detection_test.py` to compare detected clusters with injected ones.
5. **Completeness Analysis**: Compute completeness curves using `completeness.py`.
6. **Visualization**: Generate plots with `plotting.py` to visualize your results.
7. **Command-Line Interface**: Run the pipeline from the command line using `cli.py`.

## CANFAR/CADC Batch Scripts

The repository includes task-based scripts for running injection jobs on remote compute (for example HTCondor on CANFAR/CADC):

- `scripts/canfar_run_tasks.py`: runs one task from a JSON task file.
- `scripts/canfar_job_wrapper.sh`: batch wrapper that reads env vars (`TASKS_FILE`, `JOB_INDEX`).
- `scripts/canfar_submit.condor`: submit template for HTCondor arrays.
- `configs/canfar_tasks.example.json`: example TAP + RSP task list.

### Dry-run a task locally

```bash
python scripts/canfar_run_tasks.py \
	--tasks-file configs/canfar_tasks.example.json \
	--task-index 0 \
	--dry-run
```

### Run one task locally

```bash
export RUBIN_TOKEN="<your_token>"
python scripts/canfar_run_tasks.py \
	--tasks-file configs/canfar_tasks.example.json \
	--task-index 0 \
	--output-root ./canfar_outputs
```

### Submit as an HTCondor array

```bash
mkdir -p logs canfar_outputs
condor_submit scripts/canfar_submit.condor \
	-append "TASKS_FILE=configs/canfar_tasks.example.json" \
	-append "N_TASKS=3" \
	-append "OUTPUT_ROOT=canfar_outputs" \
	-append "PYTHON_BIN=/usr/bin/python3"
```

Each task writes to a unique directory under `canfar_outputs/` and passes `--output-dir` into `scripts/run_injection.py`.

### Canonical workflow: 10 iterations x 1000 injections with user detector

Use `scripts/canfar_parallel_10x1000.py` when you specifically want to run:

- one image
- 10 independent injection iterations
- 1000 synthetic clusters per iteration
- user-provided detection function
- pooled/combined recovery summary at the end

Example:

```bash
export RUBIN_TOKEN="<your_token>"

python scripts/canfar_parallel_10x1000.py \
	--mode tap \
	--ra 55.0 --dec -30.0 --size 120 \
	--band i \
	--n-iterations 10 \
	--n-per-iter 1000 \
	--n-workers 4 \
	--detector-spec scripts.user_detector_template:detect \
	--detector-kwargs '{"threshold_abs":130,"min_distance":5}' \
	--output-dir canfar_outputs/batch_10x1000
```

You can also run from a user-editable config file instead of a long CLI command:

```bash
export RUBIN_TOKEN="<your_token>"
python scripts/canfar_parallel_10x1000.py \
	--config-file configs/canfar_parallel_10x1000.example.json
```

CLI flags always override values in the config file.

PSF note for CANFAR runs:

- `--mode rsp` (Butler/RSP path): uses Rubin CoaddPsf objects (spatially varying PSF).
- `--mode tap` (outside RSP path): uses TAP cutouts + PSF FWHM metadata and falls back to analytic GalSim PSF modeling in injection.

If your science result is highly PSF-sensitive, use TAP for scale testing and validate final measurements with the RSP/Butler PSF path.

### One-block CANFAR setup and run

```bash
cd /path/to/INJECT/star-cluster-injection-pipeline

# Create/activate env (first time)
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Auth for TAP mode
export RUBIN_TOKEN="<your_token>"

# Edit your task config, then run canonical 10 x 1000 workflow
python scripts/canfar_parallel_10x1000.py \
	--mode tap \
	--config-file configs/canfar_parallel_10x1000.example.json
```

The script saves combined artifacts similar to the notebook pooling pattern:

- `combined_injection_info.csv`
- `combined_detections.csv`
- `per_iteration_summary.csv`
- `combined_summary.json`

To plug in your own detector pipeline, point `--detector-spec` to a callable
in `module:function` form. A starter template is provided in
`scripts/user_detector_template.py`.

## Notebooks

Explore the provided Jupyter notebooks for tutorials and examples on how to use the pipeline effectively.

## Documentation Website

A full documentation website is included using MkDocs Material.

1. Install docs dependencies:

```bash
pip install -r docs_requirements.txt
```

2. Run the local docs server:

```bash
mkdocs serve
```

3. Build static docs output:

```bash
mkdocs build
```

Docs source files live in `site_docs/` and navigation/settings are in `mkdocs.yml`.
The Python API reference page is auto-generated from source modules via `mkdocstrings`.

### Publish docs with GitHub Pages

An automated workflow is included at `.github/workflows/docs.yml`.
It builds docs from `star-cluster-injection-pipeline/` and deploys to GitHub Pages on pushes to `main`.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.