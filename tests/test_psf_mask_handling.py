import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from inject.inject import inject_clusters_rubin_psf, inspect_psf_mask
from inject.pipeline import InjectionPipeline


class TestPipelineDataLoading(unittest.TestCase):
    def test_butler_dataset_type_preserves_exposure_context(self):
        for dataset_type, representation in (
            (None, 'exposure'),
            ('deep_coadd', 'exposure'),
            ('deep_coadd', 'stitched'),
            ('deep_coadd', 'cells'),
            ('deep_coadd', 'modern_cells'),
        ):
            with self.subTest(dataset_type=dataset_type, representation=representation):
                config = SimpleNamespace(active_bands=['i', 'r'], cutout_size=3)
                image = np.arange(25).reshape(5, 5)
                mask = np.zeros((5, 5), dtype=np.int32)
                psf = object()
                mask_planes = {'EDGE': 1}
                exposure = SimpleNamespace(
                    image=SimpleNamespace(array=image),
                    mask=SimpleNamespace(array=mask, getMaskPlaneDict=lambda: mask_planes),
                    getPsf=lambda: psf,
                    getBBox=lambda: SimpleNamespace(getMinX=lambda: 100, getMinY=lambda: 200),
                )
                as_exposure = Mock(return_value=exposure)
                stitched = SimpleNamespace(asExposure=as_exposure)
                stitch = Mock(return_value=stitched)
                to_legacy = Mock(return_value=exposure)
                products = {
                    'exposure': exposure,
                    'stitched': stitched,
                    'cells': SimpleNamespace(stitch=stitch),
                    'modern_cells': SimpleNamespace(to_legacy=to_legacy),
                }
                butler = Mock()
                butler.get.return_value = products[representation]
                data_id = {'skymap': 'test', 'tract': 1, 'patch': 2}
                options = {} if dataset_type is None else {'dataset_type': dataset_type}
                pipe = InjectionPipeline(config)

                pipe.load_data(butler=butler, data_id=data_id, **options)

                self.assertEqual(butler.get.call_args_list, [
                    call(dataset_type or 'deepCoadd', dataId={**data_id, 'band': band})
                    for band in config.active_bands
                ])
                self.assertNotIn('band', data_id)
                self.assertIs(pipe.image, pipe.images['i'])
                self.assertEqual(stitch.call_count, 2 if representation == 'cells' else 0)
                self.assertEqual(as_exposure.call_count, 2 if representation in ('stitched', 'cells') else 0)
                self.assertEqual(to_legacy.call_args_list, [call(), call()] if representation == 'modern_cells' else [])
                for band in config.active_bands:
                    np.testing.assert_array_equal(pipe.images[band], image[:3, :3])
                    np.testing.assert_array_equal(pipe.masks[band], mask[:3, :3])
                    self.assertFalse(np.shares_memory(pipe.images[band], image))
                    self.assertFalse(np.shares_memory(pipe.masks[band], mask))
                    self.assertIs(pipe.psf_objs[band], psf)
                    self.assertEqual(pipe.mask_plane_dicts[band], mask_planes)
                    self.assertEqual(pipe.bboxes[band], (100, 200))

    def test_butler_propagates_cell_coadd_conversion_failure(self):
        pipe = InjectionPipeline(SimpleNamespace(active_bands=['i']))
        to_legacy = Mock(side_effect=ValueError('conversion requires valid metadata'))
        butler = Mock()
        butler.get.return_value = SimpleNamespace(to_legacy=to_legacy)

        with self.assertRaisesRegex(ValueError, 'conversion requires valid metadata'):
            pipe.load_data(butler=butler, data_id={'tract': 1}, dataset_type='deep_coadd')
        to_legacy.assert_called_once_with()

    def test_butler_rejects_unsupported_coadd_type(self):
        pipe = InjectionPipeline(SimpleNamespace(active_bands=['i']))
        butler = Mock()
        butler.get.return_value = object()

        with self.assertRaisesRegex(TypeError, 'deep_coadd returned unsupported coadd type builtins.object'):
            pipe.load_data(butler=butler, data_id={'tract': 1}, dataset_type='deep_coadd')


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