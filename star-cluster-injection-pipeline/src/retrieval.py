import numpy as np


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

    # ------------------------------------------------------------------
    def match_detections(self, match_radius=5.0):
        """
        Match each injected cluster to the nearest detection within match_radius.

        Sets detected=True/False on each injection_info entry and stores
        the matched detection properties.

        Parameters
        ----------
        match_radius : float  -- pixels
        """
        if not self.detections:
            for info in self.injection_info:
                info['detected']  = False
                info['det_x']     = np.nan
                info['det_y']     = np.nan
            self._matched = self.injection_info
            return

        det_x = np.array([d['x'] for d in self.detections], dtype=float)
        det_y = np.array([d['y'] for d in self.detections], dtype=float)

        for info in self.injection_info:
            dx  = det_x - info['x']
            dy  = det_y - info['y']
            sep = np.sqrt(dx**2 + dy**2)
            idx = np.argmin(sep)

            if sep[idx] <= match_radius:
                info['detected']  = True
                info['det_x']     = float(det_x[idx])
                info['det_y']     = float(det_y[idx])
                det = self.detections[idx]
                info['det_magnitude'] = det.get('magnitude', np.nan)
                info['det_r_half']    = det.get('r_half',    np.nan)
                info['det_flux']      = det.get('flux',      np.nan)
                info['det_snr']       = det.get('snr',       np.nan)
            else:
                info['detected']  = False
                info['det_x']     = np.nan
                info['det_y']     = np.nan
                info['det_magnitude'] = np.nan
                info['det_r_half']    = np.nan
                info['det_flux']      = np.nan
                info['det_snr']       = np.nan

        self._matched = self.injection_info

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

        mag_offsets = [
            i['det_magnitude'] - i['magnitude']
            for i in self._matched
            if i.get('detected') and not np.isnan(i.get('det_magnitude', np.nan))
        ]

        return {
            'n_injected'          : n_inj,
            'n_detected'          : n_det,
            'overall_completeness': n_det / n_inj if n_inj > 0 else np.nan,
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
            n_inj = len(inbin)
            n_det = sum(1 for i in inbin if i.get('detected', False))
            if n_inj > 0:
                p = n_det / n_inj
                completeness[k] = p
                errors[k]       = np.sqrt(p * (1 - p) / n_inj)

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

        for i, (lo1, hi1) in enumerate(zip(bins1[:-1], bins1[1:])):
            for j, (lo2, hi2) in enumerate(zip(bins2[:-1], bins2[1:])):
                inbin = [
                    x for x in self._matched
                    if lo1 <= x.get(param1, np.nan) < hi1
                    and lo2 <= x.get(param2, np.nan) < hi2
                ]
                n = len(inbin)
                d = sum(1 for x in inbin if x.get('detected', False))
                n_inj[i, j] = n
                if n > 0:
                    comp[i, j] = d / n

        return {
            'completeness' : comp,
            'n_injected'   : n_inj,
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