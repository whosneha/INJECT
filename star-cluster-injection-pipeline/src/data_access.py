from lsst.daf.butler import Butler

def load_coadd_image(coadd_id, butler: Butler):
    """Load a coadded image using the Rubin Butler."""
    return butler.get(coadd_id)

def load_visit_image(visit_id, butler: Butler):
    """Load an individual visit image using the Rubin Butler."""
    return butler.get(visit_id)