"""
Main pipeline runner for star cluster injection.

Provides a high-level interface for running injections from config files.
"""

import numpy as np
import json
import os
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

from .config import InjectionConfig, ClusterConfig
from .inject import create_injection_catalog, inject_from_catalog
from .cluster_models import create_cluster
from .retrieval import ClusterRetrieval, run_source_detection


class InjectionPipeline:
    """
    Main pipeline class for running star cluster injections.
    """
    
    def __init__(self, config: InjectionConfig):
        """
        Initialize the pipeline with a configuration.
        
        Parameters:
        -----------
        config : InjectionConfig
            Configuration object
        """
        self.config = config
        self.image = None
        self.metadata = None
        self.exposure = None
        self.catalog = None
        self.injected_image = None
        self.injection_info = None
        self.retrieval = None
        
    @classmethod
    def from_config_file(cls, filepath: str) -> 'InjectionPipeline':
        """Create pipeline from a config file (JSON or YAML)."""
        if filepath.endswith('.json'):
            config = InjectionConfig.from_json(filepath)
        elif filepath.endswith('.yaml') or filepath.endswith('.yml'):
            config = InjectionConfig.from_yaml(filepath)
        else:
            raise ValueError("Config file must be .json or .yaml")
        return cls(config)
    
    def load_data(self, butler=None, exposure=None, image=None):
        """
        Load data for injection.
        
        Parameters:
        -----------
        butler : Butler, optional
            LSST Butler instance (for RSP)
        exposure : ExposureF, optional
            Pre-loaded exposure
        image : ndarray, optional
            Pre-loaded image array (for testing)
        """
        if exposure is not None:
            self.exposure = exposure
            self.image = exposure.image.array.copy()
            self.metadata = {
                'exposure': exposure,
                'psf': exposure.getPsf(),
                'wcs': exposure.getWcs(),
                'mode': 'rsp'
            }
        elif butler is not None:
            data_id = {
                'tract': self.config.tract,
                'patch': self.config.patch,
                'band': self.config.band
            }
            self.exposure = butler.get('deepCoadd', dataId=data_id)
            self.image = self.exposure.image.array.copy()
            self.metadata = {
                'exposure': self.exposure,
                'psf': self.exposure.getPsf(),
                'wcs': self.exposure.getWcs(),
                'mode': 'rsp'
            }
        elif image is not None:
            self.image = image.copy()
            self.exposure = None
            self.metadata = {'mode': 'mock'}
        else:
            raise ValueError("Must provide butler, exposure, or image")
        
        print(f"Loaded image with shape: {self.image.shape}")
        
    def generate_catalog(self) -> List[Dict]:
        """
        Generate injection catalog based on configuration.
        
        Returns:
        --------
        catalog : list of dict
            Injection catalog
        """
        cc = self.config.cluster_config
        
        self.catalog = create_injection_catalog(
            n_clusters=self.config.n_clusters,
            image_shape=self.image.shape,
            mag_range=(cc.mag_min, cc.mag_max),
            r_half_range=(cc.r_half_min, cc.r_half_max),
            profile_type=cc.profile_type,
            method=cc.method,
            n_stars_range=(cc.n_stars_min, cc.n_stars_max),
            imf=cc.imf,
            edge_buffer=self.config.edge_buffer,
            seed=self.config.seed
        )
        
        # Add profile-specific parameters based on ranges
        np.random.seed(self.config.seed + 1000)  # Different seed for these
        for entry in self.catalog:
            if cc.profile_type == 'king':
                entry['concentration'] = np.random.uniform(cc.concentration_min, cc.concentration_max)
            elif cc.profile_type == 'eff':
                entry['gamma'] = np.random.uniform(cc.gamma_min, cc.gamma_max)
            elif cc.profile_type == 'sersic':
                entry['sersic_n'] = np.random.uniform(cc.sersic_n_min, cc.sersic_n_max)
            
            if cc.method == 'discrete':
                entry['age_gyr'] = np.random.uniform(cc.age_gyr_min, cc.age_gyr_max)
        
        print(f"Generated catalog with {len(self.catalog)} clusters")
        return self.catalog
    
    def run_injection(self) -> Tuple[np.ndarray, List[Dict]]:
        """
        Run the injection.
        
        Returns:
        --------
        injected_image : ndarray
            Image with injected clusters
        injection_info : list of dict
            Information about each injection
        """
        if self.image is None:
            raise ValueError("No image loaded. Call load_data() first.")
        if self.catalog is None:
            self.generate_catalog()
        
        # Determine PSF source
        exposure = self.exposure if self.config.use_actual_psf else None
        psf_fwhm = 3.5 if exposure is None else None  # Fallback FWHM
        
        print(f"Injecting {len(self.catalog)} clusters...")
        print(f"  Method: {self.config.cluster_config.method}")
        print(f"  Profile: {self.config.cluster_config.profile_type}")
        print(f"  PSF: {'actual coadd PSF' if exposure else 'generic (FWHM=3.5)'}")
        
        self.injected_image, self.injection_info = inject_from_catalog(
            self.image,
            self.catalog,
            psf_fwhm=psf_fwhm,
            exposure=exposure,
            add_noise=self.config.add_noise
        )
        
        print("Injection complete!")
        return self.injected_image, self.injection_info
    
    def run_detection(self, detection_catalog: List[Dict] = None,
                      threshold: float = 5.0) -> List[Dict]:
        """
        Run source detection on injected image.
        
        Parameters:
        -----------
        detection_catalog : list of dict, optional
            Pre-computed detection catalog (e.g., from LSST pipeline)
        threshold : float
            Detection threshold for simple detection
        
        Returns:
        --------
        detections : list of dict
            Detected sources
        """
        if detection_catalog is not None:
            self.detection_catalog = detection_catalog
        else:
            print(f"Running simple source detection (threshold={threshold}σ)...")
            self.detection_catalog = run_source_detection(
                self.injected_image, 
                threshold=threshold
            )
            print(f"  Found {len(self.detection_catalog)} sources")
        
        return self.detection_catalog
    
    def run_retrieval(self, match_radius: float = 5.0) -> ClusterRetrieval:
        """
        Match injected clusters with detections and compute completeness.
        
        Parameters:
        -----------
        match_radius : float
            Maximum distance for matching (pixels)
        
        Returns:
        --------
        retrieval : ClusterRetrieval
            Retrieval analysis object
        """
        if not hasattr(self, 'detection_catalog') or self.detection_catalog is None:
            raise ValueError("No detections available. Call run_detection() first.")
        
        print("Running retrieval analysis...")
        self.retrieval = ClusterRetrieval(self.injection_info, self.detection_catalog)
        self.retrieval.match_detections(match_radius=match_radius)
        
        stats = self.retrieval.get_summary_statistics()
        print(f"  Completeness: {stats['overall_completeness']:.1%}")
        print(f"  50% magnitude limit: {stats['mag_50_limit']:.2f}")
        
        return self.retrieval
    
    def run_full_pipeline(self, detection_catalog: List[Dict] = None,
                          match_radius: float = 5.0) -> Dict[str, Any]:
        """
        Run the complete pipeline: inject → detect → retrieve.
        
        Parameters:
        -----------
        detection_catalog : list of dict, optional
            Pre-computed detections
        match_radius : float
            Matching radius
        
        Returns:
        --------
        results : dict
            Full pipeline results
        """
        # Run injection
        self.run_injection()
        
        # Run detection
        self.run_detection(detection_catalog)
        
        # Run retrieval
        self.run_retrieval(match_radius)
        
        # Compile results
        results = {
            'config': self.config.to_dict(),
            'summary': self.retrieval.get_summary_statistics(),
            'n_injected': len(self.injection_info),
            'n_detected_sources': len(self.detection_catalog),
        }
        
        return results
    
    def save_results(self, output_dir: str = None):
        """
        Save all results to disk.
        
        Parameters:
        -----------
        output_dir : str, optional
            Output directory (defaults to config.output_dir)
        """
        if output_dir is None:
            output_dir = self.config.output_dir
        
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save config
        config_path = os.path.join(output_dir, f'{self.config.run_name}_config.json')
        self.config.to_json(config_path)
        print(f"Saved config: {config_path}")
        
        # Save injection catalog
        if self.injection_info is not None:
            catalog_path = os.path.join(output_dir, f'{self.config.run_name}_catalog.json')
            # Convert to JSON-serializable format
            serializable_info = []
            for info in self.injection_info:
                entry = {k: v for k, v in info.items() 
                        if k not in ['star_catalog', 'cluster_properties']}
                entry = {k: (float(v) if isinstance(v, (np.floating, np.integer)) else v)
                        for k, v in entry.items()}
                serializable_info.append(entry)
            
            with open(catalog_path, 'w') as f:
                json.dump(serializable_info, f, indent=2)
            print(f"Saved catalog: {catalog_path}")
        
        # Save retrieval results
        if self.retrieval is not None:
            retrieval_path = os.path.join(output_dir, f'{self.config.run_name}_retrieval.json')
            self.retrieval.save_results(retrieval_path)
            print(f"Saved retrieval: {retrieval_path}")
        
        # Save injected image as FITS (optional)
        if self.config.save_injected_image and self.injected_image is not None:
            try:
                from astropy.io import fits
                fits_path = os.path.join(output_dir, f'{self.config.run_name}_injected.fits')
                hdu = fits.PrimaryHDU(self.injected_image)
                hdu.writeto(fits_path, overwrite=True)
                print(f"Saved image: {fits_path}")
            except ImportError:
                print("astropy not available, skipping FITS output")
