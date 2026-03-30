"""
Detection benchmark: concentration indices for star/cluster separation.
Based on PHANGS-HST methodology (Adamo et al. 2024, in prep).
"""

import numpy as np
from scipy import ndimage
from typing import Tuple, Dict, List, Optional
import warnings


class ConcentrationIndexBenchmark:
    """
    Multiple Concentration Index (MCI) for star vs cluster classification.
    
    Measures flux concentration in inner vs outer apertures to distinguish
    point sources (stars) from extended sources (clusters).
    """
    
    def __init__(self, inner_radius=2.0, outer_radius=5.0):
        """
        Parameters
        ----------
        inner_radius : float
            Inner aperture radius in pixels
        outer_radius : float
            Outer aperture radius in pixels
        """
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
    
    def measure_ci_at_position(self, image: np.ndarray, x: float, y: float) -> Dict[str, float]:
        """
        Measure concentration index at a position.
        
        Parameters
        ----------
        image : ndarray
            Image array
        x, y : float
            Source position in pixels
        
        Returns
        -------
        dict
            {ci: concentration_index, inner_flux, outer_flux, total_flux, snr}
        """
        ny, nx = image.shape
        
        # Create aperture masks
        yy, xx = np.ogrid[:ny, :nx]
        r = np.sqrt((xx - x)**2 + (yy - y)**2)
        
        inner_mask = r <= self.inner_radius
        outer_mask = (r > self.inner_radius) & (r <= self.outer_radius)
        
        # Measure flux
        inner_flux = np.sum(image[inner_mask])
        outer_flux = np.sum(image[outer_mask])
        total_flux = inner_flux + outer_flux
        
        if total_flux <= 0:
            return {
                'ci': np.nan,
                'inner_flux': 0,
                'outer_flux': 0,
                'total_flux': 0,
                'snr': 0,
            }
        
        # Concentration index: fraction of flux in inner aperture
        ci = inner_flux / total_flux
        
        # SNR estimate
        snr = np.sqrt(total_flux) if total_flux > 0 else 0
        
        return {
            'ci': float(ci),
            'inner_flux': float(inner_flux),
            'outer_flux': float(outer_flux),
            'total_flux': float(total_flux),
            'snr': float(snr),
        }
    
    def classify(self, ci: float, ci_threshold: float = 0.7) -> str:
        """
        Classify source as star or cluster based on CI.
        
        Parameters
        ----------
        ci : float
            Concentration index
        ci_threshold : float
            Threshold above which source is classified as star
        
        Returns
        -------
        str
            'star' or 'cluster'
        """
        if np.isnan(ci):
            return 'unknown'
        return 'star' if ci > ci_threshold else 'cluster'


class InjectionBenchmark:
    """
    Benchmark injection recovery: detect injected sources and measure accuracy.
    """
    
    def __init__(self, flux_threshold: float = 5.0, min_separation: float = 5.0):
        """
        Parameters
        ----------
        flux_threshold : float
            Minimum flux (in sigma) to detect a source
        min_separation : float
            Minimum separation between detections in pixels
        """
        self.flux_threshold = flux_threshold
        self.min_separation = min_separation
    
    def detect_sources(self, image: np.ndarray, background_rms: Optional[float] = None,
                      return_detection_image: bool = False):
        """
        Simple source detection using threshold.
        
        Parameters
        ----------
        image : ndarray
            Image to detect sources in
        background_rms : float, optional
            Background RMS. If None, estimate from image.
        return_detection_image : bool
            Return detection map?
        
        Returns
        -------
        sources : list of dict
            Detected sources: {x, y, flux, peak}
        detection_image : ndarray, optional
            Detection map
        """
        if background_rms is None:
            # Estimate RMS from image corners
            h, w = image.shape
            corners = np.concatenate([
                image[:50, :50].flatten(),
                image[-50:, -50:].flatten(),
            ])
            background_rms = np.std(corners[corners < np.median(corners)])
        
        # Threshold
        threshold = background_rms * self.flux_threshold
        detected = image > threshold
        
        # Label connected components
        labeled, n_sources = ndimage.label(detected)
        
        sources = []
        for i in range(1, n_sources + 1):
            mask = labeled == i
            if mask.sum() < 3:  # Too small
                continue
            
            yy, xx = np.where(mask)
            x, y = np.mean(xx), np.mean(yy)
            flux = np.sum(image[mask])
            peak = np.max(image[mask])
            
            sources.append({
                'x': float(x),
                'y': float(y),
                'flux': float(flux),
                'peak': float(peak),
                'n_pixels': int(mask.sum()),
            })
        
        # Remove nearby duplicates
        sources = self._remove_duplicates(sources)
        
        if return_detection_image:
            return sources, detected
        return sources
    
    def _remove_duplicates(self, sources: List[Dict]) -> List[Dict]:
        """Remove sources closer than min_separation."""
        if len(sources) <= 1:
            return sources
        
        # Sort by flux (descending)
        sources = sorted(sources, key=lambda s: s['flux'], reverse=True)
        
        kept = [sources[0]]
        for s in sources[1:]:
            # Check distance to all kept sources
            dists = [np.sqrt((s['x'] - k['x'])**2 + (s['y'] - k['y'])**2) for k in kept]
            if min(dists) > self.min_separation:
                kept.append(s)
        
        return kept
    
    def match_catalogs(self, detected_sources: List[Dict], truth_sources: List[Dict],
                      match_radius: float = 5.0) -> Dict[str, List[Dict]]:
        """
        Match detected sources to truth (injected) sources.
        
        Parameters
        ----------
        detected_sources : list of dict
            Sources detected in image
        truth_sources : list of dict
            Injected sources (truth)
        match_radius : float
            Maximum matching radius in pixels
        
        Returns
        -------
        dict
            {matched, missed, false_positives}
        """
        matched = []
        missed = list(truth_sources)
        false_positives = list(detected_sources)
        
        for det in detected_sources:
            for truth in truth_sources:
                dist = np.sqrt((det['x'] - truth['x'])**2 + (det['y'] - truth['y'])**2)
                
                if dist < match_radius:
                    m = {
                        'detected': det,
                        'truth': truth,
                        'distance': float(dist),
                        'flux_ratio': det['flux'] / max(truth.get('flux_injected', truth.get('total_flux', 1)), 1e-10),
                    }
                    matched.append(m)
                    
                    # Remove from missed/false_positives
                    if truth in missed:
                        missed.remove(truth)
                    if det in false_positives:
                        false_positives.remove(det)
                    break
        
        return {
            'matched': matched,
            'missed': missed,
            'false_positives': false_positives,
        }
    
    def compute_metrics(self, match_results: Dict) -> Dict[str, float]:
        """
        Compute detection metrics.
        
        Parameters
        ----------
        match_results : dict
            Output from match_catalogs()
        
        Returns
        -------
        dict
            {completeness, purity, n_matched, n_missed, n_fp}
        """
        n_matched = len(match_results['matched'])
        n_missed = len(match_results['missed'])
        n_fp = len(match_results['false_positives'])
        n_truth = n_matched + n_missed
        n_detected = n_matched + n_fp
        
        completeness = n_matched / max(n_truth, 1)
        purity = n_matched / max(n_detected, 1)
        
        return {
            'completeness': float(completeness),
            'purity': float(purity),
            'n_matched': int(n_matched),
            'n_missed': int(n_missed),
            'n_false_positives': int(n_fp),
            'n_truth': int(n_truth),
            'n_detected': int(n_detected),
        }
