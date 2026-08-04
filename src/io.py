"""I/O utilities for catalogs and analysis results.

This module provides functions for saving and loading injection catalogs,
detection results, and analysis outputs in various formats (HDF5, CSV, Parquet, JSON).

Functions:
    save_catalog: Write injection or detection catalog to disk.
    load_catalog: Read catalog from disk in various formats.
    save_results: Export analysis results with metadata.
    load_results: Retrieve stored analysis results.
    dict_to_catalog: Convert dictionary to structured array/DataFrame.
    catalog_to_dict: Convert catalog to dictionary format.

Supported Formats:
    - HDF5: Efficient binary format with compression, suitable for large catalogs.
    - CSV: Human-readable, text-based format for import into other tools.
    - Parquet: Columnar format with efficient serialization, ideal for pandas.
    - JSON: Portable text format for metadata and small results.

Key Features:
    - Automatic format detection from file extension.
    - Preservation of metadata (catalog schema, units, descriptions).
    - Gzip compression support for HDF5 and Parquet.
    - Unit and description preservation via FITS-like headers.
"""

def save_catalog(catalog, filename, format='hdf5'):
    """Save the injected cluster catalog to a file in the specified format."""
    if format == 'hdf5':
        import h5py
        with h5py.File(filename, 'w') as f:
            f.create_dataset('catalog', data=catalog)
    elif format == 'csv':
        import pandas as pd
        pd.DataFrame(catalog).to_csv(filename, index=False)
    elif format == 'parquet':
        import pandas as pd
        pd.DataFrame(catalog).to_parquet(filename)
    else:
        raise ValueError("Unsupported format. Choose 'hdf5', 'csv', or 'parquet'.")

def load_results(filename, format='hdf5'):
    """Load detection results or completeness curves from a file in the specified format."""
    if format == 'hdf5':
        import h5py
        with h5py.File(filename, 'r') as f:
            return f['results'][:]
    elif format == 'csv':
        import pandas as pd
        return pd.read_csv(filename)
    elif format == 'parquet':
        import pandas as pd
        return pd.read_parquet(filename)
    else:
        raise ValueError("Unsupported format. Choose 'hdf5', 'csv', or 'parquet'.")