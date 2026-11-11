import numpy as np
import pytest

from inject.retrieval import ClusterRetrieval


def test_a_detection_recovers_at_most_one_injection():
    injections = [dict(x=10.0, y=10.0), dict(x=11.0, y=10.0)]
    detections = [dict(x=10.2, y=10.0)]

    ClusterRetrieval(injections, detections).match_detections(match_radius=2.0)

    assert sum(row['detected'] for row in injections) == 1
    matched = [row for row in injections if row['detected']]
    assert matched[0]['detection_index'] == 0
    assert matched[0]['match_distance_px'] == pytest.approx(0.2)


def test_assignment_maximizes_matches_before_minimizing_distance():
    injections = [dict(x=0.0, y=0.0), dict(x=1.5, y=0.0)]
    detections = [dict(x=0.9, y=0.0), dict(x=-1.0, y=0.0)]

    ClusterRetrieval(injections, detections).match_detections(match_radius=1.1)

    assert all(row['detected'] for row in injections)
    assert {row['detection_index'] for row in injections} == {0, 1}


def test_sources_outside_radius_and_invalid_detections_are_not_matched():
    injections = [dict(x=0.0, y=0.0), dict(x=10.0, y=10.0)]
    detections = [dict(x=np.nan, y=0.0), dict(x=0.5, y=0.0)]

    ClusterRetrieval(injections, detections).match_detections(match_radius=1.0)

    assert [row['detected'] for row in injections] == [True, False]
    assert injections[1]['detection_index'] == -1
    assert np.isnan(injections[1]['match_distance_px'])


def test_empty_detections_mark_all_injections_missed():
    injections = [dict(x=1.0, y=2.0), dict(x=3.0, y=4.0)]

    ClusterRetrieval(injections, []).match_detections(match_radius=5.0)

    assert all(not row['detected'] for row in injections)
    assert all(row['detection_index'] == -1 for row in injections)


def test_match_radius_must_be_finite_and_nonnegative():
    for radius in (-1.0, np.inf, np.nan):
        with pytest.raises(ValueError, match='finite and nonnegative'):
            ClusterRetrieval([], []).match_detections(match_radius=radius)


def test_baseline_sources_are_confounded_not_counted_as_clean_recoveries():
    injections = [
        dict(x=10.0, y=10.0, magnitude=20.0, r_half=1.0),
        dict(x=30.0, y=30.0, magnitude=20.5, r_half=1.5),
    ]
    baseline = [dict(x=10.2, y=10.0)]
    detections = [dict(x=10.1, y=10.0), dict(x=30.2, y=30.0)]

    ClusterRetrieval(injections, detections).match_detections(
        match_radius=1.0, baseline_detections=baseline,
    )

    assert injections[0]['background_confounded']
    assert not injections[0]['detected']
    assert injections[0]['recovery_status'] == 'background_confounded'
    assert injections[1]['detected']
    assert injections[1]['recovery_status'] == 'recovered'

    stats = ClusterRetrieval.from_matched(injections).get_summary_statistics()
    assert stats['n_injected'] == 2
    assert stats['n_background_confounded'] == 1
    assert stats['n_clean_eligible'] == 1
    assert stats['overall_completeness'] == 0.5
    assert stats['clean_completeness'] == 1.0

    _, completeness, _ = ClusterRetrieval.from_matched(injections).compute_completeness(
        'magnitude', [19.0, 21.0],
    )
    assert completeness[0] == 1.0
    result = ClusterRetrieval.from_matched(injections).compute_completeness_2d(
        'magnitude', 'r_half', [19.0, 21.0], [0.0, 2.0],
    )
    assert result['completeness'][0, 0] == 1.0
    assert result['n_injected'][0, 0] == 2
    assert result['n_eligible'][0, 0] == 1
    assert result['n_background_confounded'][0, 0] == 1
