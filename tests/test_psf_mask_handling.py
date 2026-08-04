import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.inject import inject_clusters_rubin_psf, inspect_psf_mask


class TestPsfMaskHandling(unittest.TestCase):
    def test_inspect_psf_mask_flags_inexact_region(self):
        mask = np.zeros((5, 5), dtype=np.int32)
        mask_dict = {'INEXACT_PSF': 2, 'EDGE': 5}
        mask[3, 2] = (1 << 2)

        status = inspect_psf_mask(mask, mask_dict, 2, 3)

        self.assertTrue(status['available'])
        self.assertTrue(status['flagged'])
        self.assertEqual(status['reasons'], ['INEXACT_PSF'])
        self.assertTrue(status['flags']['INEXACT_PSF'])
        self.assertFalse(status['flags']['EDGE'])

    def test_injection_records_psf_mask_flags(self):
        image = np.zeros((51, 51), dtype=float)
        mask = np.zeros((51, 51), dtype=np.int32)
        mask_dict = {'INEXACT_PSF': 1}
        mask[25, 25] = (1 << 1)
        catalog = [{
            'id': 1,
            'x': 25,
            'y': 25,
            'profile_type': 'plummer',
            'r_half': 4.0,
            'magnitude': 22.0,
            'age_gyr': 1.0,
            'concentration': 10.0,
        }]

        injected, info, _, _ = inject_clusters_rubin_psf(
            image=image,
            catalog=catalog,
            psf_obj=None,
            bbox_x_min=0,
            bbox_y_min=0,
            mask_array=mask,
            mask_plane_dict=mask_dict,
            use_actual_psf=False,
            add_noise=False,
            verbose=False,
        )

        self.assertEqual(injected.shape, image.shape)
        self.assertEqual(len(info), 1)
        self.assertTrue(info[0]['psf_mask_flagged'])
        self.assertTrue(info[0]['psf_mask_inexact'])
        self.assertEqual(info[0]['psf_mask_reasons'], 'INEXACT_PSF')

    def test_injection_can_skip_flagged_psf_regions(self):
        image = np.zeros((51, 51), dtype=float)
        mask = np.zeros((51, 51), dtype=np.int32)
        mask_dict = {'INEXACT_PSF': 1}
        mask[25, 25] = (1 << 1)
        catalog = [{
            'id': 1,
            'x': 25,
            'y': 25,
            'profile_type': 'plummer',
            'r_half': 4.0,
            'magnitude': 22.0,
            'age_gyr': 1.0,
            'concentration': 10.0,
        }]

        injected, info, _, _ = inject_clusters_rubin_psf(
            image=image,
            catalog=catalog,
            psf_obj=None,
            bbox_x_min=0,
            bbox_y_min=0,
            mask_array=mask,
            mask_plane_dict=mask_dict,
            use_actual_psf=False,
            skip_bad_psf_regions=True,
            add_noise=False,
            verbose=False,
        )

        self.assertEqual(injected.shape, image.shape)
        self.assertEqual(info, [])


if __name__ == '__main__':
    unittest.main()