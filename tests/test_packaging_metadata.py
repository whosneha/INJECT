"""Tests that guard the installable package surface."""

from pathlib import Path
import tomllib

import inject


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_public_package_exposes_version_and_lazy_config_import():
    assert inject.__version__ == "0.1.0"
    assert inject.InjectionConfig.__name__ == "InjectionConfig"


def test_pyproject_points_console_script_at_public_package():
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["injection-pipeline"] == "inject.cli:main"


def test_pyproject_does_not_cap_numpy_below_v2():
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    numpy_spec = next(dep for dep in pyproject["project"]["dependencies"] if dep.startswith("numpy"))

    assert "<2" not in numpy_spec


def test_public_package_directory_exists():
    assert (PROJECT_ROOT / "inject" / "__init__.py").exists()
