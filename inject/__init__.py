"""Internal package interface for INJECT.

The implementation modules live in this package. Imports are resolved lazily so
lightweight metadata or configuration access does not require the full runtime
scientific stack up front.
"""

from importlib import import_module

__version__ = "0.1.0"
__author__ = "Sneha Nair"
__license__ = "MIT"

_EXPORTS = {
    "ClusterConfig": ("inject.config", "ClusterConfig"),
    "InjectionConfig": ("inject.config", "InjectionConfig"),
    "apparent_magnitude_from_absolute": ("inject.config", "apparent_magnitude_from_absolute"),
    "distance_modulus": ("inject.config", "distance_modulus"),
    "KingProfile": ("inject.light_profiles", "KingProfile"),
    "PlummerProfile": ("inject.light_profiles", "PlummerProfile"),
    "EFFProfile": ("inject.light_profiles", "EFFProfile"),
    "SersicProfile": ("inject.light_profiles", "SersicProfile"),
    "mag_to_flux": ("inject.light_profiles", "mag_to_flux"),
    "make_profile_image": ("inject.inject", "make_profile_image"),
    "get_actual_psf": ("inject.inject", "get_actual_psf"),
    "inject_clusters_rubin_psf": ("inject.inject", "inject_clusters_rubin_psf"),
    "inspect_psf_mask": ("inject.inject", "inspect_psf_mask"),
    "PSFCache": ("inject.inject", "PSFCache"),
    "InjectionPipeline": ("inject.pipeline", "InjectionPipeline"),
    "run_cluster_detection": ("inject.detection", "run_cluster_detection"),
    "matched_filter_detect": ("inject.detection", "matched_filter_detect"),
    "compute_completeness_curve": ("inject.completeness", "compute_completeness_curve"),
    "ClusterRetrieval": ("inject.retrieval", "ClusterRetrieval"),
    "save_catalog": ("inject.io", "save_catalog"),
    "load_results": ("inject.io", "load_results"),
    "editable_repo_root": ("inject.notebooks", "editable_repo_root"),
    "notebook_output_dir": ("inject.notebooks", "notebook_output_dir"),
}

__all__ = sorted([*_EXPORTS.keys(), "__author__", "__license__", "__version__"])


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
