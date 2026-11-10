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


def test_batch_plot_retrieval_preserves_independent_round_matches():
    from inject import ClusterRetrieval

    rows = [
        dict(x=100, y=100, magnitude=22.0, r_half=4.0, detected=True, iteration=0),
        dict(x=100, y=100, magnitude=22.0, r_half=4.0, detected=False, iteration=1),
    ]
    retrieval = ClusterRetrieval.from_matched(iter(rows))

    stats = retrieval.get_summary_statistics()
    assert stats['n_injected'] == 2
    assert stats['n_detected'] == 1
    assert stats['overall_completeness'] == 0.5
    assert [row['detected'] for row in rows] == [True, False]
    _, completeness, _ = retrieval.compute_completeness('magnitude', [21, 23])
    assert completeness[0] == 0.5
    grid = retrieval.compute_completeness_2d('magnitude', 'r_half', [21, 23], [3, 5])
    assert grid['n_injected'][0, 0] == 2
    assert grid['completeness'][0, 0] == 0.5


def test_batch_plot_retrieval_rejects_unmatched_rows():
    from inject import ClusterRetrieval

    for row in (dict(x=1, y=1), dict(x=1, y=1, detected=None)):
        try:
            ClusterRetrieval.from_matched([row])
        except ValueError as exc:
            assert 'detected flag' in str(exc)
        else:
            raise AssertionError('Accepted unmatched truth rows.')
