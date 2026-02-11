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

## Notebooks

Explore the provided Jupyter notebooks for tutorials and examples on how to use the pipeline effectively.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.