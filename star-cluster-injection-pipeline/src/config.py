"""
Configuration module for star cluster injection pipeline.

Provides a template-based configuration system for setting up injections.
"""

import json
import yaml
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
import numpy as np


@dataclass
class ClusterConfig:
    """Configuration for a single cluster or cluster population."""
    
    # Generation method
    method: str = 'smooth'  # 'smooth' or 'discrete'
    
    # Spatial profile
    profile_type: str = 'plummer'  # 'plummer', 'king', 'eff', 'sersic'
    
    # Magnitude range
    mag_min: float = 19.0
    mag_max: float = 25.0
    
    # Half-light radius range (in pixels)
    r_half_min: float = 2.0
    r_half_max: float = 30.0
    
    # Profile-specific parameters
    concentration_min: float = 10.0  # For King profile
    concentration_max: float = 100.0
    gamma_min: float = 2.2  # For EFF profile
    gamma_max: float = 3.5
    sersic_n_min: float = 1.0  # For Sersic profile
    sersic_n_max: float = 4.0
    
    # Discrete star parameters
    n_stars_min: int = 50
    n_stars_max: int = 500
    imf: str = 'kroupa'  # 'kroupa', 'chabrier', 'salpeter'
    age_gyr_min: float = 0.1
    age_gyr_max: float = 10.0
    distance_pc: float = 10000.0


@dataclass 
class InjectionConfig:
    """Full configuration for an injection run."""
    
    # Run identification
    run_name: str = 'injection_run'
    description: str = ''
    
    # Data source (RSP Butler)
    repo: str = 'dp02'
    collection: str = '2.2i/runs/DP0.2'
    tract: int = 4431
    patch: int = 17
    band: str = 'i'
    
    # Number of clusters to inject
    n_clusters: int = 100
    
    # Cluster configuration
    cluster_config: ClusterConfig = field(default_factory=ClusterConfig)
    
    # Injection parameters
    edge_buffer: int = 100  # Pixels from edge to avoid
    add_noise: bool = True  # Add Poisson noise
    use_actual_psf: bool = True  # Use PSF from coadd (vs generic)
    
    # Random seed for reproducibility
    seed: int = 42
    
    # Output options
    save_injected_image: bool = True
    save_catalog: bool = True
    output_dir: str = './injection_output'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        d = asdict(self)
        return d
    
    def to_json(self, filepath: str = None) -> str:
        """Convert config to JSON string, optionally save to file."""
        json_str = json.dumps(self.to_dict(), indent=2)
        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_str)
        return json_str
    
    def to_yaml(self, filepath: str = None) -> str:
        """Convert config to YAML string, optionally save to file."""
        yaml_str = yaml.dump(self.to_dict(), default_flow_style=False)
        if filepath:
            with open(filepath, 'w') as f:
                f.write(yaml_str)
        return yaml_str
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'InjectionConfig':
        """Create config from dictionary."""
        cluster_config_dict = d.pop('cluster_config', {})
        cluster_config = ClusterConfig(**cluster_config_dict)
        return cls(cluster_config=cluster_config, **d)
    
    @classmethod
    def from_json(cls, filepath: str) -> 'InjectionConfig':
        """Load config from JSON file."""
        with open(filepath, 'r') as f:
            d = json.load(f)
        return cls.from_dict(d)
    
    @classmethod
    def from_yaml(cls, filepath: str) -> 'InjectionConfig':
        """Load config from YAML file."""
        with open(filepath, 'r') as f:
            d = yaml.safe_load(f)
        return cls.from_dict(d)


# =============================================================================
# PRE-DEFINED CONFIGURATION TEMPLATES
# =============================================================================

def get_template_smooth_plummer() -> InjectionConfig:
    """Template for smooth Plummer profile injection."""
    return InjectionConfig(
        run_name='smooth_plummer',
        description='Smooth Plummer profile clusters',
        n_clusters=100,
        cluster_config=ClusterConfig(
            method='smooth',
            profile_type='plummer',
            mag_min=19.0,
            mag_max=25.0,
            r_half_min=3.0,
            r_half_max=25.0
        )
    )


def get_template_smooth_king() -> InjectionConfig:
    """Template for smooth King profile injection."""
    return InjectionConfig(
        run_name='smooth_king',
        description='Smooth King profile clusters (globular-like)',
        n_clusters=100,
        cluster_config=ClusterConfig(
            method='smooth',
            profile_type='king',
            mag_min=19.0,
            mag_max=25.0,
            r_half_min=3.0,
            r_half_max=25.0,
            concentration_min=20.0,
            concentration_max=100.0
        )
    )


def get_template_discrete_kroupa() -> InjectionConfig:
    """Template for discrete star injection with Kroupa IMF."""
    return InjectionConfig(
        run_name='discrete_kroupa',
        description='Discrete stars with Kroupa IMF',
        n_clusters=50,
        cluster_config=ClusterConfig(
            method='discrete',
            profile_type='plummer',
            mag_min=18.0,
            mag_max=24.0,
            r_half_min=5.0,
            r_half_max=30.0,
            n_stars_min=100,
            n_stars_max=500,
            imf='kroupa',
            age_gyr_min=0.5,
            age_gyr_max=5.0
        )
    )


def get_template_completeness_grid() -> InjectionConfig:
    """Template for completeness analysis with uniform grid sampling."""
    return InjectionConfig(
        run_name='completeness_grid',
        description='Grid sampling for completeness analysis',
        n_clusters=500,
        cluster_config=ClusterConfig(
            method='smooth',
            profile_type='plummer',
            mag_min=18.0,
            mag_max=27.0,
            r_half_min=2.0,
            r_half_max=50.0
        ),
        seed=12345
    )


TEMPLATES = {
    'smooth_plummer': get_template_smooth_plummer,
    'smooth_king': get_template_smooth_king,
    'discrete_kroupa': get_template_discrete_kroupa,
    'completeness_grid': get_template_completeness_grid,
}


def get_template(name: str) -> InjectionConfig:
    """Get a pre-defined configuration template by name."""
    if name not in TEMPLATES:
        raise ValueError(f"Unknown template: {name}. Available: {list(TEMPLATES.keys())}")
    return TEMPLATES[name]()


def list_templates() -> List[str]:
    """List available configuration templates."""
    return list(TEMPLATES.keys())
