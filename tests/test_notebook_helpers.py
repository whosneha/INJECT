from pathlib import Path

from inject.notebooks import editable_repo_root, notebook_output_dir


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_FILE = PROJECT_ROOT / "inject" / "notebooks.py"


def test_editable_repo_root_finds_checkout_root():
    assert editable_repo_root(PACKAGE_FILE) == PROJECT_ROOT


def test_notebook_output_dir_prefers_repo_plots_for_editable_install():
    output_dir = notebook_output_dir(
        "demo-run",
        create=False,
        _cwd=Path("/tmp/ignored"),
        _package_file=PACKAGE_FILE,
    )

    assert output_dir == PROJECT_ROOT / "plots" / "demo-run"


def test_notebook_output_dir_uses_parent_of_notebooks_directory_when_not_installed_editably():
    output_dir = notebook_output_dir(
        "demo-run",
        create=False,
        _cwd=PROJECT_ROOT / "notebooks",
        _package_file=Path("/tmp/site-packages/inject/notebooks.py"),
    )

    assert output_dir == PROJECT_ROOT / "plots" / "demo-run"
