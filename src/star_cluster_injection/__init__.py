"""Public package interface for the Star Cluster Injection Pipeline.

This wrapper keeps the existing internal ``src`` package working while exposing
the cleaner ``star_cluster_injection`` import path for users and packaging.
"""

from importlib import import_module

__version__ = "0.1.0"
__author__ = "Sneha Nair"
__license__ = "MIT"

_EXPORTS = {
    "ClusterConfig": ("src.config", "ClusterConfig"),
    "InjectionConfig": ("src.config", "InjectionConfig"),
    "KingProfile": ("src.light_profiles", "KingProfile"),
    "PlummerProfile": ("src.light_profiles", "PlummerProfile"),
    "EFFProfile": ("src.light_profiles", "EFFProfile"),
    "SersicProfile": ("src.light_profiles", "SersicProfile"),
    "mag_to_flux": ("src.light_profiles", "mag_to_flux"),
    "make_profile_image": ("src.inject", "make_profile_image"),
    "get_actual_psf": ("src.inject", "get_actual_psf"),
    "inject_clusters_rubin_psf": ("src.inject", "inject_clusters_rubin_psf"),
    "inspect_psf_mask": ("src.inject", "inspect_psf_mask"),
    "PSFCache": ("src.inject", "PSFCache"),
    "InjectionPipeline": ("src.pipeline", "InjectionPipeline"),
    "run_cluster_detection": ("src.detection", "run_cluster_detection"),
    "matched_filter_detect": ("src.detection", "matched_filter_detect"),
    "compute_completeness_curve": ("src.completeness", "compute_completeness_curve"),
    "ClusterRetrieval": ("src.retrieval", "ClusterRetrieval"),
    "save_catalog": ("src.io", "save_catalog"),
    "load_results": ("src.io", "load_results"),
}

__all__ = sorted([*_EXPORTS.keys(), "__author__", "__license__", "__version__"])


def __getattr__(name):
    """Resolve public exports lazily so metadata imports stay lightweight."""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
