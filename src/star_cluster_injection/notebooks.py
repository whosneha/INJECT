"""Notebook helpers for installed-package workflows."""

from pathlib import Path


def editable_repo_root(_package_file: Path | None = None) -> Path | None:
    """Return the checkout root when running from an editable install."""
    package_file = (_package_file or Path(__file__)).resolve()
    search_root = package_file.parent

    for candidate in (search_root, *search_root.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "notebooks").is_dir():
            return candidate

    return None


def notebook_output_dir(
    run_name: str,
    *,
    create: bool = True,
    _cwd: Path | None = None,
    _package_file: Path | None = None,
) -> Path:
    """Return a stable output directory without requiring notebook path hacks."""
    repo_root = editable_repo_root(_package_file)
    cwd = (_cwd or Path.cwd()).resolve()

    if repo_root is not None:
        base_dir = repo_root / "plots"
    elif cwd.name == "notebooks" and (cwd.parent / "pyproject.toml").is_file():
        base_dir = cwd.parent / "plots"
    else:
        base_dir = cwd / "plots"

    output_dir = base_dir / run_name
    if create:
        output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir
