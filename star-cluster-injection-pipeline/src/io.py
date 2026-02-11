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