"""Tests that guard the installable package surface."""

from pathlib import Path
import tomllib

import star_cluster_injection


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_public_wrapper_exposes_version_and_lazy_config_import():
    assert star_cluster_injection.__version__ == "0.1.0"
    assert star_cluster_injection.InjectionConfig.__name__ == "InjectionConfig"


def test_pyproject_points_console_script_at_public_package():
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["injection-pipeline"] == "star_cluster_injection.cli:main"


def test_public_package_directory_exists():
    assert (PROJECT_ROOT / "src" / "star_cluster_injection" / "__init__.py").exists()
