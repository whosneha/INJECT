from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ClusterConfig:
    """Configuration for cluster parameter space."""
    profile_type      : str   = 'king'    # king | plummer | eff | sersic
    method            : str   = 'smooth'  # smooth | discrete
    mag_min           : float = 20.0
    mag_max           : float = 26.0
    r_half_min        : float = 2.0       # pixels
    r_half_max        : float = 10.0      # pixels
    concentration_min : float = 5.0       # King c, EFF gamma, or Sersic n
    concentration_max : float = 30.0
    age_min_gyr       : float = 1.0       # Gyr
    age_max_gyr       : float = 13.0      # Gyr

    def __post_init__(self):
        assert self.mag_min < self.mag_max,     'mag_min must be < mag_max'
        assert self.r_half_min < self.r_half_max, 'r_half_min must be < r_half_max'
        assert self.profile_type in ('king', 'plummer', 'eff', 'sersic'), \
            f'Unknown profile_type: {self.profile_type}'


@dataclass
class InjectionConfig:
    """Top-level configuration for the injection pipeline."""
    run_name            : str          = 'injection_run'
    n_clusters          : int          = 100
    seed                : int          = 42
    edge_buffer         : int          = 50      # pixels
    add_noise           : bool         = True
    use_actual_psf      : bool         = True    # False -> Gaussian fallback always
    save_injected_image : bool         = False
    output_dir          : str          = 'outputs'
    cluster_config      : ClusterConfig = field(default_factory=ClusterConfig)
    # Butler / coadd info (optional, stored for provenance)
    tract               : Optional[int] = None
    patch               : Optional[int] = None
    band                : Optional[str] = None
    pixel_scale         : float         = 0.2    # arcsec/pixel
    zero_point          : float         = 27.0

    def __repr__(self):
        cc = self.cluster_config
        return (
            f'InjectionConfig(\n'
            f'  run_name    = {self.run_name}\n'
            f'  n_clusters  = {self.n_clusters}\n'
            f'  seed        = {self.seed}\n'
            f'  edge_buffer = {self.edge_buffer} px\n'
            f'  add_noise   = {self.add_noise}\n'
            f'  use_actual_psf = {self.use_actual_psf}\n'
            f'  tract/patch/band = {self.tract}/{self.patch}/{self.band}\n'
            f'  profile     = {cc.profile_type}  method={cc.method}\n'
            f'  mag         = [{cc.mag_min}, {cc.mag_max}]\n'
            f'  r_half      = [{cc.r_half_min}, {cc.r_half_max}] px\n'
            f'  conc        = [{cc.concentration_min}, {cc.concentration_max}]\n'
            f'  age         = [{cc.age_min_gyr}, {cc.age_max_gyr}] Gyr\n'
            f')'
        )
