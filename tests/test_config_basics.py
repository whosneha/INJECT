"""Lightweight unit tests that do not require the scientific stack."""

import math

from inject.config import (
    ClusterConfig,
    InjectionConfig,
    apparent_magnitude_from_absolute,
    distance_modulus,
    physical_radius_to_pixels,
)


def test_active_bands_defaults_to_single_band():
    config = InjectionConfig(band="r")

    assert config.active_bands == ["r"]


def test_active_bands_prefers_multiband_configuration():
    config = InjectionConfig(band="i", bands=["g", "r", "i"])

    assert config.active_bands == ["g", "r", "i"]


def test_active_bands_supports_all_rubin_bands():
    config = InjectionConfig(bands=["u", "g", "r", "i", "z", "y"])

    assert config.active_bands == ["u", "g", "r", "i", "z", "y"]


def test_active_bands_rejects_empty_band_list():
    config = InjectionConfig(bands=[])

    try:
        config.active_bands
    except ValueError as exc:
        assert "at least one band" in str(exc)
    else:
        raise AssertionError("Accepted an empty band list.")


def test_active_bands_rejects_unknown_band():
    config = InjectionConfig(bands=["g", "not-a-band"])

    try:
        config.active_bands
    except ValueError as exc:
        assert "Unknown Rubin band" in str(exc)
    else:
        raise AssertionError("Accepted an unknown Rubin band.")


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


def test_physical_radius_to_pixels_uses_distance_and_pixel_scale():
    from inject import physical_radius_to_pixels as public_conversion

    radius = public_conversion(4.0, distance_pc=1_000_000, pixel_scale=0.2)

    assert math.isclose(radius, 4.125296124941927, rel_tol=1e-12)
    assert math.isclose(
        physical_radius_to_pixels(4.0, distance_pc=1_000_000, pixel_scale=0.1),
        2 * radius,
    )


def test_distance_changes_size_and_flux_consistently():
    near_radius = physical_radius_to_pixels(4.0, distance_pc=1_000_000, pixel_scale=0.2)
    far_radius = physical_radius_to_pixels(4.0, distance_pc=2_000_000, pixel_scale=0.2)
    near_mag = apparent_magnitude_from_absolute(-7.5, distance_pc=1_000_000)
    far_mag = apparent_magnitude_from_absolute(-7.5, distance_pc=2_000_000)

    assert math.isclose(far_radius / near_radius, 0.5)
    assert math.isclose(10 ** (-0.4 * (far_mag - near_mag)), 0.25)


def test_physical_radius_to_pixels_rejects_nonpositive_or_nonfinite_inputs():
    for name in ('radius_pc', 'distance_pc', 'pixel_scale'):
        for value in (0.0, -1.0, float('nan'), float('inf')):
            parameters = dict(radius_pc=4.0, distance_pc=1_000_000, pixel_scale=0.2)
            parameters[name] = value
            try:
                physical_radius_to_pixels(**parameters)
            except ValueError as exc:
                assert name in str(exc)
            else:
                raise AssertionError(f'Accepted invalid {name}: {value}')
