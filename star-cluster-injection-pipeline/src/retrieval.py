"""
Retrieval and completeness analysis module.

Provides tools to:
1. Match injected clusters with detected sources
2. Calculate completeness as a function of various parameters
3. Generate completeness curves and maps
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import json


@dataclass
class MatchResult:
    """Result of matching an injected cluster to detections."""
    injection_id: int
    detected: bool
    match_distance: float = np.nan
    detected_mag: float = np.nan
    detected_flux: float = np.nan
    mag_offset: float = np.nan  # detected - injected
    

class ClusterRetrieval:
    """
    Class for matching injected clusters with detected sources
    and computing completeness statistics.
    """
    
    def __init__(self, injection_catalog: List[Dict], detection_catalog: List[Dict] = None):
        """
        Initialize retrieval analysis.
        
        Parameters:
        -----------
        injection_catalog : list of dict
            Catalog of injected clusters with keys: 'id', 'x', 'y', 'magnitude', 'r_half', etc.
        detection_catalog : list of dict, optional
            Catalog of detected sources with keys: 'x', 'y', 'flux' or 'magnitude'
        """
        self.injection_catalog = injection_catalog
        self.detection_catalog = detection_catalog
        self.matches = None
        
    def set_detection_catalog(self, detection_catalog: List[Dict]):
        """Set or update the detection catalog."""
        self.detection_catalog = detection_catalog
        self.matches = None  # Reset matches
        
    def match_detections(self, match_radius: float = 5.0, 
                         detection_x_key: str = 'x',
                         detection_y_key: str = 'y',
                         detection_mag_key: str = 'magnitude',
                         detection_flux_key: str = 'flux') -> List[MatchResult]:
        """
        Match injected clusters with detected sources.
        
        Parameters:
        -----------
        match_radius : float
            Maximum distance (in pixels) for a match
        detection_x_key : str
            Key for x coordinate in detection catalog
        detection_y_key : str
            Key for y coordinate in detection catalog
        detection_mag_key : str
            Key for magnitude in detection catalog
        detection_flux_key : str
            Key for flux in detection catalog (used if mag not available)
        
        Returns:
        --------
        matches : list of MatchResult
            Match results for each injected cluster
        """
        if self.detection_catalog is None:
            raise ValueError("Detection catalog not set. Call set_detection_catalog() first.")
        
        # Build detection positions array
        det_x = np.array([d[detection_x_key] for d in self.detection_catalog])
        det_y = np.array([d[detection_y_key] for d in self.detection_catalog])
        
        # Get detection magnitudes/fluxes
        if detection_mag_key in self.detection_catalog[0]:
            det_mag = np.array([d[detection_mag_key] for d in self.detection_catalog])
        elif detection_flux_key in self.detection_catalog[0]:
            det_flux = np.array([d[detection_flux_key] for d in self.detection_catalog])
            det_mag = -2.5 * np.log10(det_flux) + 27.0  # Approximate
        else:
            det_mag = np.full(len(self.detection_catalog), np.nan)
        
        matches = []
        
        for inj in self.injection_catalog:
            inj_x, inj_y = inj['x'], inj['y']
            inj_mag = inj['magnitude']
            inj_id = inj['id']
            
            # Calculate distances to all detections
            distances = np.sqrt((det_x - inj_x)**2 + (det_y - inj_y)**2)
            
            # Find closest match within radius
            min_idx = np.argmin(distances)
            min_dist = distances[min_idx]
            
            if min_dist <= match_radius:
                match = MatchResult(
                    injection_id=inj_id,
                    detected=True,
                    match_distance=min_dist,
                    detected_mag=det_mag[min_idx],
                    detected_flux=self.detection_catalog[min_idx].get(detection_flux_key, np.nan),
                    mag_offset=det_mag[min_idx] - inj_mag
                )
            else:
                match = MatchResult(
                    injection_id=inj_id,
                    detected=False
                )
            
            matches.append(match)
        
        self.matches = matches
        return matches
    
    def compute_completeness(self, parameter: str = 'magnitude', 
                             bins: np.ndarray = None,
                             n_bins: int = 10) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute completeness as a function of a parameter.
        
        Parameters:
        -----------
        parameter : str
            Parameter to bin by: 'magnitude', 'r_half', 'x', 'y', etc.
        bins : ndarray, optional
            Bin edges. If None, computed automatically.
        n_bins : int
            Number of bins if bins not specified
        
        Returns:
        --------
        bin_centers : ndarray
            Center of each bin
        completeness : ndarray
            Completeness fraction in each bin
        completeness_err : ndarray
            Binomial error on completeness
        """
        if self.matches is None:
            raise ValueError("No matches computed. Call match_detections() first.")
        
        # Get parameter values
        values = np.array([self.injection_catalog[m.injection_id][parameter] 
                          for m in self.matches])
        detected = np.array([m.detected for m in self.matches])
        
        # Create bins
        if bins is None:
            bins = np.linspace(values.min(), values.max(), n_bins + 1)
        
        # Compute completeness in each bin
        bin_centers = 0.5 * (bins[:-1] + bins[1:])
        completeness = np.zeros(len(bin_centers))
        completeness_err = np.zeros(len(bin_centers))
        n_injected = np.zeros(len(bin_centers))
        n_detected = np.zeros(len(bin_centers))
        
        for i in range(len(bin_centers)):
            mask = (values >= bins[i]) & (values < bins[i+1])
            n_inj = np.sum(mask)
            n_det = np.sum(detected[mask])
            
            n_injected[i] = n_inj
            n_detected[i] = n_det
            
            if n_inj > 0:
                completeness[i] = n_det / n_inj
                # Binomial error
                completeness_err[i] = np.sqrt(completeness[i] * (1 - completeness[i]) / n_inj)
            else:
                completeness[i] = np.nan
                completeness_err[i] = np.nan
        
        return bin_centers, completeness, completeness_err
    
    def compute_completeness_2d(self, param1: str = 'magnitude', 
                                 param2: str = 'r_half',
                                 bins1: np.ndarray = None,
                                 bins2: np.ndarray = None,
                                 n_bins1: int = 8,
                                 n_bins2: int = 8) -> Dict[str, np.ndarray]:
        """
        Compute 2D completeness map.
        
        Parameters:
        -----------
        param1 : str
            First parameter (e.g., 'magnitude')
        param2 : str
            Second parameter (e.g., 'r_half')
        bins1, bins2 : ndarray, optional
            Bin edges for each parameter
        n_bins1, n_bins2 : int
            Number of bins if not specified
        
        Returns:
        --------
        result : dict
            Dictionary with keys: 'completeness', 'bin_centers1', 'bin_centers2',
            'n_injected', 'n_detected'
        """
        if self.matches is None:
            raise ValueError("No matches computed. Call match_detections() first.")
        
        values1 = np.array([self.injection_catalog[m.injection_id][param1] 
                           for m in self.matches])
        values2 = np.array([self.injection_catalog[m.injection_id][param2] 
                           for m in self.matches])
        detected = np.array([m.detected for m in self.matches])
        
        if bins1 is None:
            bins1 = np.linspace(values1.min(), values1.max(), n_bins1 + 1)
        if bins2 is None:
            bins2 = np.linspace(values2.min(), values2.max(), n_bins2 + 1)
        
        bin_centers1 = 0.5 * (bins1[:-1] + bins1[1:])
        bin_centers2 = 0.5 * (bins2[:-1] + bins2[1:])
        
        completeness = np.zeros((len(bin_centers1), len(bin_centers2)))
        n_injected = np.zeros_like(completeness)
        n_detected = np.zeros_like(completeness)
        
        for i in range(len(bin_centers1)):
            for j in range(len(bin_centers2)):
                mask = ((values1 >= bins1[i]) & (values1 < bins1[i+1]) &
                       (values2 >= bins2[j]) & (values2 < bins2[j+1]))
                
                n_inj = np.sum(mask)
                n_det = np.sum(detected[mask])
                
                n_injected[i, j] = n_inj
                n_detected[i, j] = n_det
                
                if n_inj > 0:
                    completeness[i, j] = n_det / n_inj
                else:
                    completeness[i, j] = np.nan
        
        return {
            'completeness': completeness,
            'bin_centers1': bin_centers1,
            'bin_centers2': bin_centers2,
            'bins1': bins1,
            'bins2': bins2,
            'param1': param1,
            'param2': param2,
            'n_injected': n_injected,
            'n_detected': n_detected
        }
    
    def get_50_percent_limit(self, parameter: str = 'magnitude',
                              bins: np.ndarray = None) -> float:
        """
        Find the parameter value where completeness drops to 50%.
        
        Parameters:
        -----------
        parameter : str
            Parameter to analyze
        bins : ndarray, optional
            Bin edges
        
        Returns:
        --------
        limit : float
            Parameter value at 50% completeness (interpolated)
        """
        bin_centers, completeness, _ = self.compute_completeness(parameter, bins)
        
        # Remove NaN values
        valid = ~np.isnan(completeness)
        if not np.any(valid):
            return np.nan
        
        bin_centers = bin_centers[valid]
        completeness = completeness[valid]
        
        # Find where completeness crosses 50%
        above_50 = completeness >= 0.5
        if np.all(above_50) or np.all(~above_50):
            return np.nan
        
        # Interpolate
        idx = np.where(np.diff(above_50.astype(int)))[0]
        if len(idx) == 0:
            return np.nan
        
        idx = idx[0]
        x1, x2 = bin_centers[idx], bin_centers[idx+1]
        y1, y2 = completeness[idx], completeness[idx+1]
        
        limit = x1 + (0.5 - y1) * (x2 - x1) / (y2 - y1)
        return limit
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics of the retrieval analysis.
        
        Returns:
        --------
        stats : dict
            Summary statistics
        """
        if self.matches is None:
            raise ValueError("No matches computed. Call match_detections() first.")
        
        detected = np.array([m.detected for m in self.matches])
        
        stats = {
            'n_injected': len(self.matches),
            'n_detected': int(np.sum(detected)),
            'overall_completeness': np.mean(detected),
            'mag_50_limit': self.get_50_percent_limit('magnitude'),
            'r_half_50_limit': self.get_50_percent_limit('r_half'),
        }
        
        # Add mean offsets for detected sources
        mag_offsets = [m.mag_offset for m in self.matches if m.detected and not np.isnan(m.mag_offset)]
        if mag_offsets:
            stats['mean_mag_offset'] = np.mean(mag_offsets)
            stats['std_mag_offset'] = np.std(mag_offsets)
        
        return stats
    
    def save_results(self, filepath: str):
        """Save retrieval results to JSON file."""
        if self.matches is None:
            raise ValueError("No matches computed.")
        
        results = {
            'summary': self.get_summary_statistics(),
            'matches': [
                {
                    'injection_id': m.injection_id,
                    'detected': m.detected,
                    'match_distance': float(m.match_distance) if not np.isnan(m.match_distance) else None,
                    'detected_mag': float(m.detected_mag) if not np.isnan(m.detected_mag) else None,
                    'mag_offset': float(m.mag_offset) if not np.isnan(m.mag_offset) else None,
                }
                for m in self.matches
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
    
    @classmethod
    def load_results(cls, injection_catalog: List[Dict], results_filepath: str) -> 'ClusterRetrieval':
        """Load retrieval results from file."""
        with open(results_filepath, 'r') as f:
            results = json.load(f)
        
        retrieval = cls(injection_catalog)
        retrieval.matches = [
            MatchResult(
                injection_id=m['injection_id'],
                detected=m['detected'],
                match_distance=m['match_distance'] if m['match_distance'] else np.nan,
                detected_mag=m['detected_mag'] if m['detected_mag'] else np.nan,
                mag_offset=m['mag_offset'] if m['mag_offset'] else np.nan,
            )
            for m in results['matches']
        ]
        
        return retrieval


# =============================================================================
# DETECTION CATALOG INTERFACE
# =============================================================================

DETECTION_REQUIRED_KEYS = ['x', 'y']

DETECTION_OPTIONAL_KEYS = {
    'flux':        'Total source flux in image units',
    'magnitude':   'Apparent magnitude (if photometrically calibrated)',
    'r_half':      'Measured half-light radius in pixels',
    'ellipticity': 'Source ellipticity (0=circular)',
    'snr':         'Detection signal-to-noise ratio',
    'area':        'Number of pixels in detection footprint',
    'flag':        'Quality flag (0=good)',
}

DETECTION_FORMAT_EXAMPLE = """
Expected detection catalog format (list of dicts):

detections = [
    {
        # REQUIRED
        'x':          1042.3,    # centroid x in pixels
        'y':          876.1,     # centroid y in pixels

        # OPTIONAL but used in analysis plots
        'flux':       1234.5,    # total flux (image units)
        'magnitude':  22.3,      # apparent magnitude
        'r_half':     4.2,       # half-light radius (pixels)
        'ellipticity':0.12,      # ellipticity
        'snr':        8.4,       # peak S/N
        'area':       45,        # footprint area (pixels^2)
        'flag':       0,         # quality flag (0=good)
    },
    ...
]

Common sources for this catalog:
  - LSST SourceDetectionTask output (convert SourceCatalog to list of dicts)
  - SExtractor output (read with astropy.io.ascii)
  - sep (Python SExtractor) output
  - Custom matched-filter detection output
"""


def validate_detection_catalog(detections):
    """
    Validate that a detection catalog has the required format.

    Parameters:
    -----------
    detections : list of dict
        Detection catalog to validate

    Returns:
    --------
    valid : bool
    report : str
        Human-readable validation report
    """
    if not isinstance(detections, list):
        return False, "detections must be a list of dicts"
    if len(detections) == 0:
        return True, "WARNING: empty detection catalog"

    report_lines = [f"Detection catalog: {len(detections)} sources"]

    # Check required keys
    missing = [k for k in DETECTION_REQUIRED_KEYS if k not in detections[0]]
    if missing:
        return False, f"Missing required keys: {missing}\n\n{DETECTION_FORMAT_EXAMPLE}"

    report_lines.append(f"  ✓ Required keys present: {DETECTION_REQUIRED_KEYS}")

    # Check which optional keys are present
    present_optional = [k for k in DETECTION_OPTIONAL_KEYS if k in detections[0]]
    missing_optional = [k for k in DETECTION_OPTIONAL_KEYS if k not in detections[0]]

    report_lines.append(f"  ✓ Optional keys present : {present_optional}")
    if missing_optional:
        report_lines.append(f"  ⚠ Optional keys missing: {missing_optional}")
        report_lines.append("    (analysis plots will be limited without these)")

    # Basic range checks
    xs = [d['x'] for d in detections]
    ys = [d['y'] for d in detections]
    report_lines.append(f"  x range: [{min(xs):.1f}, {max(xs):.1f}]")
    report_lines.append(f"  y range: [{min(ys):.1f}, {max(ys):.1f}]")

    return True, "\n".join(report_lines)


def load_detections_from_lsst(source_catalog, photo_calib=None):
    """
    Convert an LSST SourceCatalog to the pipeline detection format.

    Parameters:
    -----------
    source_catalog : lsst.afw.table.SourceCatalog
        Output of SourceDetectionTask or SourceMeasurementTask
    photo_calib : lsst.afw.image.PhotoCalib, optional
        For converting flux to magnitude

    Returns:
    --------
    detections : list of dict
    """
    detections = []
    for src in source_catalog:
        entry = {
            'x':   src.getX(),
            'y':   src.getY(),
            'flux': float(src.getPsfInstFlux()) if src.getPsfInstFlux() > 0 else 0.0,
            'area': int(src.getFootprint().getArea()),
            'flag': int(src.get('base_PixelFlags_flag')),
        }
        # Add magnitude if calibration available
        if photo_calib is not None and entry['flux'] > 0:
            try:
                entry['magnitude'] = photo_calib.instFluxToMagnitude(entry['flux'])
            except Exception:
                pass
        # Add shape info if measured
        try:
            shape = src.getShape()
            entry['r_half'] = float(shape.getTraceRadius())
            entry['ellipticity'] = float(1 - shape.getMinor() / shape.getMajor())
        except Exception:
            pass
        detections.append(entry)
    return detections


def load_detections_from_sep(sep_output, pixel_scale=0.2):
    """
    Convert sep (Python SExtractor) output to pipeline detection format.

    Parameters:
    -----------
    sep_output : structured ndarray
        Output of sep.extract()
    pixel_scale : float
        Arcsec/pixel

    Returns:
    --------
    detections : list of dict
    """
    detections = []
    for src in sep_output:
        entry = {
            'x':           float(src['x']),
            'y':           float(src['y']),
            'flux':        float(src['flux']),
            'area':        int(src['npix']) if 'npix' in src.dtype.names else 0,
            'ellipticity': float(src['ellipticity']) if 'ellipticity' in src.dtype.names else np.nan,
            'flag':        int(src['flag']),
        }
        if 'a' in src.dtype.names:
            entry['r_half'] = float(src['a'])  # semi-major axis as proxy
        detections.append(entry)
    return detections


def load_detections_from_json(filepath):
    """Load detections saved as a JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def load_detections_from_fits(filepath, x_col='x', y_col='y', **col_map):
    """
    Load detections from a FITS table.

    Parameters:
    -----------
    filepath : str
    x_col, y_col : str
        Column names for x and y positions
    col_map : dict
        Mapping from FITS column names to pipeline key names
        e.g. flux_col='FLUX_AUTO', r_half_col='FLUX_RADIUS'
    """
    from astropy.io import fits
    with fits.open(filepath) as hdul:
        table = hdul[1].data

    detections = []
    for i in range(len(table)):
        entry = {
            'x': float(table[x_col][i]),
            'y': float(table[y_col][i]),
        }
        for fits_col, pipe_key in col_map.items():
            if fits_col in table.names:
                entry[pipe_key] = float(table[fits_col][i])
        detections.append(entry)
    return detections


def run_source_detection(image: np.ndarray, 
                         threshold: float = 5.0,
                         min_area: int = 5) -> List[Dict]:
    """
    Simple source detection for testing.
    In practice, use LSST's detection pipeline.
    
    Parameters:
    -----------
    image : ndarray
        Image to search
    threshold : float
        Detection threshold in sigma above background
    min_area : int
        Minimum number of connected pixels
    
    Returns:
    --------
    detections : list of dict
        Detected sources with 'x', 'y', 'flux'
    """
    try:
        from scipy import ndimage
        from scipy.ndimage import label
    except ImportError:
        raise ImportError("scipy required for source detection")
    
    # Estimate background
    background = np.median(image)
    noise = np.std(image)
    
    # Threshold
    detection_map = image > (background + threshold * noise)
    
    # Label connected regions
    labeled, n_sources = label(detection_map)
    
    detections = []
    for i in range(1, n_sources + 1):
        mask = labeled == i
        if np.sum(mask) >= min_area:
            # Find centroid
            y_coords, x_coords = np.where(mask)
            flux = np.sum(image[mask]) - background * np.sum(mask)
            
            if flux > 0:
                # Flux-weighted centroid
                weights = image[mask] - background
                weights = np.maximum(weights, 0)
                if np.sum(weights) > 0:
                    x_cent = np.average(x_coords, weights=weights)
                    y_cent = np.average(y_coords, weights=weights)
                else:
                    x_cent = np.mean(x_coords)
                    y_cent = np.mean(y_coords)
                
                detections.append({
                    'x': x_cent,
                    'y': y_cent,
                    'flux': flux,
                    'area': int(np.sum(mask))
                })
    
    return detections
