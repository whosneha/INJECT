import numpy as np


def _one_to_one_spatial_assignment(left_xy, right_xy, match_radius):
    """Return maximum-cardinality, minimum-distance pairs inside a radius."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import min_weight_full_bipartite_matching
    from scipy.spatial import cKDTree

    if not len(left_xy) or not len(right_xy):
        return {}
    right_xy = np.asarray(right_xy, dtype=float)
    tree = cKDTree(right_xy)
    n_left = len(left_xy)
    n_right = len(right_xy)
    unmatched_cost = (n_left + 1) * (match_radius + 1.0)
    rows, columns, costs = [], [], []
    for left_index, point in enumerate(np.asarray(left_xy, dtype=float)):
        for right_index in tree.query_ball_point(point, match_radius):
            distance = float(np.linalg.norm(right_xy[right_index] - point))
            rows.append(left_index)
            columns.append(right_index)
            costs.append(distance + 1e-12)
        rows.append(left_index)
        columns.append(n_right + left_index)
        costs.append(unmatched_cost)

    matrix = coo_matrix(
        (costs, (rows, columns)), shape=(n_left, n_right + n_left),
    ).tocsr()
    assigned_left, assigned_right = min_weight_full_bipartite_matching(matrix)
    return {
        int(left): int(right)
        for left, right in zip(assigned_left, assigned_right)
        if right < n_right
    }


class ClusterRetrieval:
    """
    Matches injected clusters to detections and computes completeness.

    Parameters
    ----------
    injection_info : list[dict]  -- from inject_clusters_rubin_psf
    detections     : list[dict]  -- from your detector (must have x, y keys)
    """

    def __init__(self, injection_info, detections):
        self.injection_info = injection_info
        self.detections     = detections
        self._matched       = None   # list[dict] -- matched injections

    @classmethod
    def from_matched(cls, injection_info):
        """Combine already matched truth rows without cross-matching runs again."""
        rows = list(injection_info)
        if any(not isinstance(row.get('detected'), (bool, np.bool_)) for row in rows):
            raise ValueError('Every row must have a boolean detected flag from matching.')
        retrieval = cls(rows, [])
        retrieval._matched = rows
        return retrieval

    # ------------------------------------------------------------------
    def match_detections(self, match_radius=5.0, baseline_detections=None):
        """
        Make one-to-one spatial matches within ``match_radius`` pixels.

        The assignment first maximizes the number of matches, then minimizes
        their total separation. Each detection can recover at most one injection.
        Optionally provide detections from the original, uninjected image. Injections
        near an original source, or matched to a post-injection detection associated
        with an original source, are marked as background-confounded and do not count
        as clean recoveries.

        Parameters
        ----------
        match_radius : float  -- pixels
        """
        if not np.isfinite(match_radius) or match_radius < 0:
            raise ValueError('match_radius must be finite and nonnegative pixels')

        injections = self.injection_info
        n_injections = len(injections)
        if n_injections == 0:
            self._matched = injections
            return

        for info in injections:
            info.update(
                detected=False, det_x=np.nan, det_y=np.nan,
                det_magnitude=np.nan, det_r_half=np.nan,
                det_flux=np.nan, det_snr=np.nan,
                detection_index=-1, match_distance_px=np.nan,
                background_confounded=False, recovery_status='missed',
            )

        valid_detections = [
            (index, detection) for index, detection in enumerate(self.detections)
            if np.isfinite(detection.get('x', np.nan))
            and np.isfinite(detection.get('y', np.nan))
        ]
        if not valid_detections:
            self._matched = injections
            return

        detection_indices, detections = zip(*valid_detections)
        detection_xy = np.array([[detection['x'], detection['y']] for detection in detections])
        injection_xy = np.array([[info['x'], info['y']] for info in injections], dtype=float)
        valid_injections = np.isfinite(injection_xy).all(axis=1)
        n_detections = len(detections)
        valid_injection_indices = np.flatnonzero(valid_injections)
        assigned = _one_to_one_spatial_assignment(
            injection_xy[valid_injections], detection_xy, match_radius,
        )
        injection_to_detection = {
            int(valid_injection_indices[left]): right for left, right in assigned.items()
        }

        baseline_xy = np.empty((0, 2), dtype=float)
        baseline_tree = None
        baseline_post_detections = set()
        if baseline_detections is not None:
            valid_baseline = [
                detection for detection in baseline_detections
                if np.isfinite(detection.get('x', np.nan))
                and np.isfinite(detection.get('y', np.nan))
            ]
            if valid_baseline:
                baseline_xy = np.array([[row['x'], row['y']] for row in valid_baseline])
                from scipy.spatial import cKDTree
                baseline_tree = cKDTree(baseline_xy)
                baseline_assigned = _one_to_one_spatial_assignment(
                    baseline_xy, detection_xy, match_radius,
                )
                baseline_post_detections = set(baseline_assigned.values())

        for injection_index, info in enumerate(injections):
            column = injection_to_detection.get(injection_index)
            near_original_source = (
                valid_injections[injection_index]
                and baseline_tree is not None
                and bool(baseline_tree.query_ball_point(injection_xy[injection_index], match_radius))
            )
            matched_original_detection = column in baseline_post_detections if column is not None else False
            confounded = bool(near_original_source or matched_original_detection)
            info['background_confounded'] = confounded
            if confounded:
                info['recovery_status'] = 'background_confounded'
            elif column is not None:
                info['recovery_status'] = 'recovered'
                info['detected'] = True
            else:
                info['recovery_status'] = 'missed'

            if column is None:
                continue

            info = injections[injection_index]
            detection = detections[column]
            distance = float(np.linalg.norm(
                detection_xy[column] - injection_xy[injection_index]
            ))
            info.update(
                det_x=float(detection['x']),
                det_y=float(detection['y']),
                det_magnitude=detection.get('magnitude', np.nan),
                det_r_half=detection.get('r_half', np.nan),
                det_flux=detection.get('flux', np.nan),
                det_snr=detection.get('snr', np.nan),
                detection_index=int(detection_indices[column]),
                match_distance_px=distance,
            )

        self._matched = injections

    # ------------------------------------------------------------------
    def get_summary_statistics(self):
        """
        Return a summary dict of recovery statistics.

        Returns
        -------
        dict with keys:
          n_injected, n_detected, overall_completeness,
          mag_50_limit, r_half_50_limit,
          mean_mag_offset, std_mag_offset
        """
        self._check_matched()
        n_inj = len(self._matched)
        n_det = sum(1 for i in self._matched if i.get('detected', False))
        n_confounded = sum(1 for i in self._matched if i.get('background_confounded', False))
        n_eligible = n_inj - n_confounded

        mag_offsets = [
            i['det_magnitude'] - i['magnitude']
            for i in self._matched
            if i.get('detected') and not np.isnan(i.get('det_magnitude', np.nan))
        ]

        return {
            'n_injected'          : n_inj,
            'n_detected'          : n_det,
            'n_background_confounded': n_confounded,
            'n_clean_eligible'    : n_eligible,
            'overall_completeness': n_det / n_inj if n_inj > 0 else np.nan,
            'clean_completeness'  : n_det / n_eligible if n_eligible > 0 else np.nan,
            'mag_50_limit'        : self.get_50_percent_limit('magnitude'),
            'r_half_50_limit'     : self.get_50_percent_limit('r_half'),
            'mean_mag_offset'     : float(np.mean(mag_offsets))  if mag_offsets else np.nan,
            'std_mag_offset'      : float(np.std(mag_offsets))   if mag_offsets else np.nan,
        }

    # ------------------------------------------------------------------
    def compute_completeness(self, parameter, bins):
        """
        Completeness as a function of one injection parameter.

        Parameters
        ----------
        parameter : str   -- key in injection_info dicts (e.g. 'magnitude', 'r_half')
        bins      : array -- bin edges

        Returns
        -------
        bin_centers  : ndarray
        completeness : ndarray
        errors       : ndarray  -- 1-sigma binomial
        """
        self._check_matched()
        bins        = np.asarray(bins)
        bin_centers = 0.5 * (bins[:-1] + bins[1:])
        completeness = np.full(len(bin_centers), np.nan)
        errors       = np.full(len(bin_centers), np.nan)

        for k, (lo, hi) in enumerate(zip(bins[:-1], bins[1:])):
            inbin = [i for i in self._matched
                     if lo <= i.get(parameter, np.nan) < hi]
            eligible = [i for i in inbin if not i.get('background_confounded', False)]
            n_eligible = len(eligible)
            n_det = sum(1 for i in eligible if i.get('detected', False))
            if n_eligible > 0:
                p = n_det / n_eligible
                completeness[k] = p
                errors[k]       = np.sqrt(p * (1 - p) / n_eligible)

        return bin_centers, completeness, errors

    # ------------------------------------------------------------------
    def get_50_percent_limit(self, parameter):
        """
        Interpolate the parameter value at which completeness crosses 50%.

        Returns nan if it cannot be determined.
        """
        bins = self._default_bins(parameter)
        bc, comp, _ = self.compute_completeness(parameter, bins)
        valid = ~np.isnan(comp)
        if valid.sum() < 2:
            return np.nan
        try:
            # find where completeness crosses 0.5 (from bright/small side)
            for j in range(len(comp) - 1):
                if not np.isnan(comp[j]) and not np.isnan(comp[j+1]):
                    if (comp[j] >= 0.5 >= comp[j+1]) or (comp[j] <= 0.5 <= comp[j+1]):
                        # linear interpolation
                        frac = (0.5 - comp[j]) / (comp[j+1] - comp[j])
                        return float(bc[j] + frac * (bc[j+1] - bc[j]))
        except Exception:
            pass
        return float(np.interp(0.5, comp[valid][::-1], bc[valid][::-1],
                               left=np.nan, right=np.nan))

    # ------------------------------------------------------------------
    def compute_completeness_2d(self, param1, param2, bins1, bins2):
        """
        2D completeness map over two parameters.

        Returns
        -------
        dict with keys:
          completeness  : 2D ndarray (len(bins1)-1, len(bins2)-1)
          n_injected    : 2D ndarray
          bin_centers1  : 1D ndarray
          bin_centers2  : 1D ndarray
        """
        self._check_matched()
        bins1 = np.asarray(bins1)
        bins2 = np.asarray(bins2)
        nb1   = len(bins1) - 1
        nb2   = len(bins2) - 1
        comp  = np.full((nb1, nb2), np.nan)
        n_inj = np.zeros((nb1, nb2), dtype=int)
        n_confounded = np.zeros((nb1, nb2), dtype=int)
        n_eligible = np.zeros((nb1, nb2), dtype=int)

        for i, (lo1, hi1) in enumerate(zip(bins1[:-1], bins1[1:])):
            for j, (lo2, hi2) in enumerate(zip(bins2[:-1], bins2[1:])):
                inbin = [
                    x for x in self._matched
                    if lo1 <= x.get(param1, np.nan) < hi1
                    and lo2 <= x.get(param2, np.nan) < hi2
                ]
                eligible = [x for x in inbin if not x.get('background_confounded', False)]
                n_inj[i, j] = len(inbin)
                n_confounded[i, j] = len(inbin) - len(eligible)
                n_eligible[i, j] = len(eligible)
                n_det = sum(1 for x in eligible if x.get('detected', False))
                if eligible:
                    comp[i, j] = n_det / len(eligible)

        return {
            'completeness' : comp,
            'n_injected'   : n_inj,
            'n_background_confounded': n_confounded,
            'n_eligible'   : n_eligible,
            'bin_centers1' : 0.5 * (bins1[:-1] + bins1[1:]),
            'bin_centers2' : 0.5 * (bins2[:-1] + bins2[1:]),
        }

    # ------------------------------------------------------------------
    def _check_matched(self):
        if self._matched is None:
            raise RuntimeError('Call match_detections() first.')

    def _default_bins(self, parameter, n=15):
        vals = [i.get(parameter, np.nan) for i in self.injection_info]
        vals = [v for v in vals if not np.isnan(v)]
        if not vals:
            return np.linspace(0, 1, n + 1)
        return np.linspace(min(vals), max(vals), n + 1)