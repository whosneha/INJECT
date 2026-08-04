"""
Template detector hook for canfar_parallel_10x1000.py.

Implement detect(image, **kwargs) and return list[dict] with at least x,y keys.
"""

from __future__ import annotations

import numpy as np
from skimage.feature import peak_local_max


def detect(image, threshold_abs: float = 130.0, min_distance: int = 5, **kwargs):
    """Simple peak finder template. Replace with your own detection pipeline."""
    if image is None:
        return []

    coords = peak_local_max(
        np.asarray(image),
        threshold_abs=threshold_abs,
        min_distance=min_distance,
        exclude_border=False,
    )

    out = []
    for y, x in coords:
        out.append({"x": float(x), "y": float(y)})
    return out
