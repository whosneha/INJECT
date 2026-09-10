"""Lightweight unit tests that do not require the scientific stack."""

from inject.config import (
    ClusterConfig,
    InjectionConfig,
    apparent_magnitude_from_absolute,
    distance_modulus,
)


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


def test_distance_modulus_for_m31_like_distance():
    assert round(distance_modulus(800_000), 2) == 24.52


def test_apparent_magnitude_from_absolute_uses_distance_and_extinction():
    apparent_mag = apparent_magnitude_from_absolute(
        -6.0,
        distance_pc=800_000,
        extinction=0.1,
    )

    assert round(apparent_mag, 2) == 18.62


def test_apparent_magnitude_from_absolute_requires_one_distance_input():
    try:
        apparent_magnitude_from_absolute(-6.0)
    except ValueError as exc:
        assert "exactly one" in str(exc)
    else:
        raise AssertionError("Accepted missing distance information.")
