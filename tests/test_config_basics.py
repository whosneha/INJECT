"""Lightweight unit tests that do not require the scientific stack."""

from src.config import ClusterConfig, InjectionConfig


def test_active_bands_defaults_to_single_band():
    config = InjectionConfig(band="r")

    assert config.active_bands == ["r"]


def test_active_bands_prefers_multiband_configuration():
    config = InjectionConfig(band="i", bands=["g", "r", "i"])

    assert config.active_bands == ["g", "r", "i"]


def test_cluster_config_rejects_unknown_profile():
    try:
        ClusterConfig(profile_type="invalid-profile")
    except AssertionError as exc:
        assert "Unknown profile_type" in str(exc)
    else:
        raise AssertionError("ClusterConfig accepted an invalid profile type.")
