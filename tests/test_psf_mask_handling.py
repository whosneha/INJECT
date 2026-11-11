import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

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

    def test_native_exposures_are_retained_only_for_requested_bands(self):
        config = SimpleNamespace(active_bands=['g', 'r'], cutout_size=3)
        exposures = {}
        for band in config.active_bands:
            image = np.zeros((5, 5), dtype=np.float32)
            mask = np.zeros((5, 5), dtype=np.int32)
            exposures[band] = SimpleNamespace(
                image=SimpleNamespace(array=image),
                variance=SimpleNamespace(array=image.copy()),
                mask=SimpleNamespace(array=mask, getMaskPlaneDict=lambda: {}),
                getPsf=lambda: object(),
                getBBox=lambda: SimpleNamespace(getMinX=lambda: 0, getMinY=lambda: 0),
            )
        butler = Mock()
        butler.get.side_effect = lambda _name, dataId: exposures[dataId['band']]
        pipe = InjectionPipeline(config)

        pipe.load_data(
            butler=butler, data_id={'tract': 1}, dataset_type='deep_coadd',
            native_bands=['r'],
        )

        self.assertEqual(pipe.native_exposures, {'r': exposures['r']})
        self.assertEqual(set(pipe.images), {'g', 'r'})

    def test_native_injection_updates_only_a_clone_and_returns_variance_and_mask(self):
        class FakeExposure:
            def __init__(self, image, variance, mask):
                self.image = SimpleNamespace(array=image)
                self.variance = SimpleNamespace(array=variance)
                self.mask = SimpleNamespace(array=mask)

            def clone(self):
                return FakeExposure(
                    self.image.array.copy(), self.variance.array.copy(), self.mask.array.copy(),
                )

            def getBBox(self):
                return SimpleNamespace(getMinX=lambda: 10, getMinY=lambda: 20)

            def getWcs(self):
                return SimpleNamespace(pixelToSky=lambda point: ('sky', point.x, point.y))

            def getPhotoCalib(self):
                return SimpleNamespace(magnitudeToInstFlux=lambda magnitude, point: 123.0)

        original_image = np.zeros((8, 8), dtype=np.float32)
        original_variance = np.ones((8, 8), dtype=np.float32)
        original_mask = np.zeros((8, 8), dtype=np.int32)
        source = FakeExposure(original_image, original_variance, original_mask)

        def fake_rubin_inject(exposure, objects, *, inject_variance, add_noise, noise_seed):
            objects = list(objects)
            self.assertTrue(inject_variance)
            self.assertFalse(add_noise)
            self.assertEqual(noise_seed, 17)
            self.assertEqual(len(objects), 1)
            exposure.image.array[3, 2] += 12
            exposure.variance.array[3, 2] += 7
            exposure.mask.array[3, 2] |= 1
            return [5], [SimpleNamespace(area=lambda: 1)], [False], [False]

        lsst_module = types.ModuleType('lsst')
        lsst_module.__path__ = []
        geom_module = types.ModuleType('lsst.geom')
        geom_module.Point2D = lambda x, y: SimpleNamespace(x=x, y=y)
        source_module = types.ModuleType('lsst.source')
        source_module.__path__ = []
        injection_module = types.ModuleType('lsst.source.injection')
        injection_module.inject_galsim_objects_into_exposure = fake_rubin_inject
        lsst_module.geom = geom_module
        lsst_module.source = source_module
        source_module.injection = injection_module

        pipe = InjectionPipeline(SimpleNamespace(
            active_bands=['g'], cutout_size=8, pixel_scale=0.2, zero_point=27.0,
        ))
        pipe.native_exposures = {'g': source}
        pipe.images = {'g': original_image.copy()}
        pipe.variances = {'g': original_variance.copy()}
        catalog = [{
            'id': 1, 'x': 2, 'y': 3, 'magnitude': 22.0, 'r_half': 2.0,
            'concentration': 10.0, 'age_gyr': 1.0, 'profile_type': 'king',
            'total_flux': 10.0, 'stamp_flux': 9.0, 'total_flux_injected': 8.0,
            'stamp': np.ones((3, 3)),
        }]

        with patch.dict(sys.modules, {
            'lsst': lsst_module,
            'lsst.geom': geom_module,
            'lsst.source': source_module,
            'lsst.source.injection': injection_module,
        }):
            injected, info = pipe.inject_with_rubin(
                catalog=catalog, band='g', add_noise=False, noise_seed=17,
            )

        np.testing.assert_array_equal(source.image.array, original_image)
        np.testing.assert_array_equal(source.variance.array, original_variance)
        np.testing.assert_array_equal(source.mask.array, original_mask)
        self.assertEqual(injected[3, 2], 12)
        self.assertEqual(pipe.injected_variance[3, 2], 8)
        self.assertEqual(pipe.injected_mask[3, 2], 1)
        self.assertEqual(pipe.native_variance_delta[3, 2], 7)
        self.assertTrue(pipe.native_mask_changed[3, 2])
        self.assertEqual(pipe.native_injection_summary, {'attempted': 1, 'injected': 1, 'skipped': 0})
        self.assertIsNot(pipe.native_injected_exposures['g'], source)
        self.assertEqual(info[0]['psf_used'], 'rubin_native')
        self.assertTrue(info[0]['native_variance_injected'])
        self.assertEqual(info[0]['total_flux'], 123.0)
        self.assertNotIn('total_flux_injected', info[0])
        self.assertNotIn('stamp_flux', info[0])
        self.assertNotIn('stamp', info[0])


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