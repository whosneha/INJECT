import os
import logging
import numpy as np
import pandas as pd
import concurrent.futures
from copy import deepcopy

# -- Fix: force logger to print in Jupyter notebooks --
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        fmt='%(asctime)s  %(levelname)s  %(message)s',
        datefmt='%H:%M:%S',
    ))
    logger.addHandler(handler)

logger.propagate = False   # prevent duplicate messages


class InjectionPipeline:
    """
    Orchestrates catalog generation, injection, and saving results.

    Usage
    -----
    pipe = InjectionPipeline(config)
    pipe.load_data(image=image)
    catalog = pipe.generate_catalog()

    # single run
    pipe.injected_image    = injected_image
    pipe.injection_info    = injection_info
    pipe.detection_catalog = detections
    pipe.save_results()

    # batch run (sequential)
    iterations = pipe.run_batch(n_iterations=10, n_per_iter=1000, ...)

    # batch run (parallel — check your RSP allocation first!)
    iterations = pipe.run_batch(n_iterations=10, n_per_iter=1000,
                                n_workers=4, ...)
    """

    def __init__(self, config):
        self.config            = config
        self.image             = None
        self.injected_image    = None
        self.injection_info    = []
        self.detection_catalog = []
        self.retrieval         = None
        self._catalog          = None

    # ------------------------------------------------------------------
    def load_data(self, image=None, butler=None, data_id=None):
        """
        Load image data.

        Single band (existing behaviour):
            pipe.load_data(image=BASE_IMAGE)
            pipe.load_data(butler=butler, data_id={'tract':3828,'patch':24,'band':'i'})

        Multi-band:
            pipe.load_data(butler=butler, data_id={'tract':3828,'patch':24})
            # loads all bands in config.active_bands automatically
        """
        if image is not None:
            # existing single-image path — unchanged
            self.image     = image
            self.images    = {self.config.band: image}
            self.psf_objs  = {}
            return

        if butler is not None and data_id is not None:
            self.images   = {}
            self.psf_objs = {}
            self.bboxes   = {}

            for band in self.config.active_bands:
                bid   = {**data_id, 'band': band}
                coadd = butler.get('deepCoadd', dataId=bid)

                CUTOUT = self.config.cutout_size   # add this to InjectionConfig
                self.images[band]   = coadd.image.array[:CUTOUT, :CUTOUT].copy()
                self.psf_objs[band] = coadd.getPsf()
                bbox                = coadd.getBBox()
                self.bboxes[band]   = (bbox.getMinX(), bbox.getMinY())

                print(f'  Loaded band {band}: shape={self.images[band].shape}')

            # default image = first band (keeps single-band code working)
            self.image = self.images[self.config.active_bands[0]]
            return

        raise ValueError('Provide either image= or butler= + data_id=')


    def run_batch_multiband(self, n_iterations, n_per_iter,
                             psf_fwhm_fallbacks = None,
                             detector_fn        = None,
                             store_images       = False,
                             checkpoint_dir     = None,
                             n_workers          = 1,
                             verbose            = True):
        """
        Run batch injection across ALL loaded bands using the SAME
        random catalog each iteration — so cluster positions are
        identical across bands (physically correct).

        Parameters
        ----------
        psf_fwhm_fallbacks : dict or None
            Per-band fallback FWHM e.g. {'g': 3.8, 'r': 3.5, 'i': 4.0}
            If None, uses config.psf_fwhm_fallback for all bands.

        Returns
        -------
        dict[band -> list[iteration_dicts]]
            Same structure as run_batch() but keyed by band.
        """
        if not hasattr(self, 'images') or len(self.images) == 0:
            raise RuntimeError('No images loaded. Call load_data(butler=...) first.')

        if psf_fwhm_fallbacks is None:
            psf_fwhm_fallbacks = {b: self.config.psf_fwhm_fallback
                                  for b in self.config.active_bands}

        results = {}   # band -> list of iteration dicts

        for band in self.config.active_bands:
            print(f'\n{"="*50}')
            print(f'  Running band: {band}')
            print(f'{"="*50}')

            # Temporarily swap image/psf to this band
            self.image = self.images[band]
            bbox_x, bbox_y = self.bboxes.get(band, (0, 0))

            results[band] = self.run_batch(
                n_iterations      = n_iterations,
                n_per_iter        = n_per_iter,
                psf_obj           = self.psf_objs.get(band),
                bbox_x_min        = bbox_x,
                bbox_y_min        = bbox_y,
                psf_fwhm_fallback = psf_fwhm_fallbacks[band],
                detector_fn       = detector_fn,
                store_images      = store_images,
                checkpoint_dir    = (os.path.join(checkpoint_dir, band)
                                     if checkpoint_dir else None),
                n_workers         = n_workers,
                verbose           = verbose,
            )

        return results

    # ------------------------------------------------------------------
    def generate_catalog(self, rng=None):
        """
        Generate a randomised injection catalog from the cluster config.

        Returns
        -------
        catalog : list[dict]
            Keys: id, x, y, magnitude, r_half, concentration, age_gyr, profile_type
        """
        if self.image is None:
            raise RuntimeError('Call load_data(image=...) before generate_catalog().')

        cfg = self.config
        cc  = cfg.cluster_config
        ny, nx = self.image.shape

        rng = np.random.default_rng(cfg.seed if rng is None else rng)
        buf = cfg.edge_buffer

        catalog = []
        for i in range(cfg.n_clusters):
            catalog.append({
                'id'           : i,
                'x'            : int(rng.integers(buf, nx - buf)),
                'y'            : int(rng.integers(buf, ny - buf)),
                'magnitude'    : float(rng.uniform(cc.mag_min,           cc.mag_max)),
                'r_half'       : float(rng.uniform(cc.r_half_min,        cc.r_half_max)),
                'concentration': float(rng.uniform(cc.concentration_min, cc.concentration_max)),
                'age_gyr'      : float(rng.uniform(cc.age_min_gyr,       cc.age_max_gyr)),
                'profile_type' : cc.profile_type,
            })

        self._catalog = catalog
        return catalog

    # ------------------------------------------------------------------
    def run_batch(self, n_iterations, n_per_iter,
                  psf_obj, bbox_x_min, bbox_y_min,
                  psf_fwhm_fallback = 3.5,
                  detector_fn       = None,
                  store_images      = False,
                  checkpoint_dir    = None,
                  n_workers         = 1,       # 1=sequential, -1=all CPUs, N=N threads
                  verbose           = True):
        """
        Run N iterations of injection + detection.

        Parameters
        ----------
        store_images   : bool
            If True, keep injected_image in each iteration dict.
            WARNING: memory cost = n_iterations × image_size × 8 bytes.
            Default False — only the last image is kept for plotting.
        checkpoint_dir : str or None
            If set, saves each iteration's catalogs to this directory
            as they complete. Safe to resume after a crash.
        n_workers      : int
            Number of parallel threads.
              1  = sequential, safest, easiest to debug (default)
             -1  = use all available CPUs
              N  = use N threads
            Uses threads (not processes) so the Rubin Butler/PSF objects
            don't need to be pickled — they are read-only and safe to share
            across threads.
            NOTE: check your RSP CPU allocation before setting > 4.

        Returns
        -------
        iterations : list[dict], one per iteration, keys:
            iteration, injection_info, detections,
            injected_image (only if store_images=True)
        """
        from .inject import inject_clusters_rubin_psf

        if n_workers == -1:
            n_workers = os.cpu_count()
            logger.info(f'n_workers=-1 → using all {n_workers} CPUs')

        if checkpoint_dir is not None:
            os.makedirs(checkpoint_dir, exist_ok=True)

        # ------------------------------------------------------------------
        # Build all per-iteration args up front.
        # Config is read here (main thread) so worker never touches self.config.
        # ------------------------------------------------------------------
        original_seed = self.config.seed
        original_n    = self.config.n_clusters

        iter_args = []
        for iteration in range(n_iterations):
            self.config.seed       = iteration
            self.config.n_clusters = n_per_iter
            catalog = self.generate_catalog()
            self.config.seed       = original_seed
            self.config.n_clusters = original_n

            iter_args.append({
                'iteration'        : iteration,
                'catalog'          : catalog,
                'image'            : self.image,
                'psf_obj'          : psf_obj,
                'bbox_x_min'       : bbox_x_min,
                'bbox_y_min'       : bbox_y_min,
                'psf_fwhm_fallback': psf_fwhm_fallback,
                'pixel_scale'      : self.config.pixel_scale,
                'zero_point'       : self.config.zero_point,
                'add_noise'        : self.config.add_noise,
                'use_actual_psf'   : self.config.use_actual_psf,
                'detector_fn'      : detector_fn,
                'store_images'     : store_images,
                'checkpoint_dir'   : checkpoint_dir,
                'verbose'          : verbose,    # ← add this
            })

        # ------------------------------------------------------------------
        # Worker — fully self-contained, no reference to self inside
        # ------------------------------------------------------------------
        def _run_one(args):
            from .inject import inject_clusters_rubin_psf

            it = args['iteration']

            # Print the header before injection starts so user sees progress
            print(f'\n--- Iteration {it + 1}/{n_iterations} ---')

            injected_image, injection_info = inject_clusters_rubin_psf(
                image             = args['image'],
                catalog           = args['catalog'],
                psf_obj           = args['psf_obj'],
                bbox_x_min        = args['bbox_x_min'],
                bbox_y_min        = args['bbox_y_min'],
                psf_fwhm_fallback = args['psf_fwhm_fallback'],
                pixel_scale       = args['pixel_scale'],
                zero_point        = args['zero_point'],
                add_noise         = args['add_noise'],
                use_actual_psf    = args['use_actual_psf'],
                rng_seed          = it,
                verbose           = args['verbose'],   # ← pass through
            )

            # Drop stamps immediately after injection
            for entry in injection_info:
                entry.pop('stamp', None)
                entry['iteration'] = it

            detections = []
            if args['detector_fn'] is not None:
                detections = args['detector_fn'](injected_image)
                for d in detections:
                    d['iteration'] = it

            print(f'  Detections: {len(detections)}')

            # Checkpoint to disk
            if args['checkpoint_dir'] is not None:
                inj_path = os.path.join(args['checkpoint_dir'],
                                        f'injection_iter{it:03d}.csv')
                det_path = os.path.join(args['checkpoint_dir'],
                                        f'detections_iter{it:03d}.csv')
                pd.DataFrame(injection_info).to_csv(inj_path, index=False)
                if detections:
                    pd.DataFrame(detections).to_csv(det_path, index=False)
                logger.info(f'Checkpoint saved -> {inj_path}')

            result = {
                'iteration'      : it,
                'injection_info' : injection_info,
                'detections'     : detections,
            }
            if args['store_images']:
                result['injected_image'] = injected_image
            else:
                result['injected_image'] = injected_image if it == 0 else None

            return result

        # ------------------------------------------------------------------
        # Sequential or parallel execution
        # ------------------------------------------------------------------
        if n_workers == 1:
            logger.info(f'Running {n_iterations} iterations sequentially')
            raw_results = [_run_one(a) for a in iter_args]
        else:
            logger.info(f'Running {n_iterations} iterations across {n_workers} threads')
            raw_results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=n_workers) as ex:
                futures = {ex.submit(_run_one, a): a['iteration']
                           for a in iter_args}
                for fut in concurrent.futures.as_completed(futures):
                    try:
                        raw_results.append(fut.result())
                    except Exception as e:
                        it = futures[fut]
                        logger.error(f'Iteration {it} FAILED: {e}')

        # Sort by iteration (parallel completion order is non-deterministic)
        iterations = sorted(raw_results, key=lambda r: r['iteration'])

        # Keep only last available injected image for quick plotting
        if not store_images:
            last_img = next(
                (r['injected_image'] for r in reversed(iterations)
                 if r.get('injected_image') is not None), None
            )
            self.injected_image = last_img
            for r in iterations:
                r.pop('injected_image', None)

        self.injection_info    = [e for r in iterations for e in r['injection_info']]
        self.detection_catalog = [d for r in iterations for d in r['detections']]

         
        print(f'\nBatch complete.')
        print(f'  Total injected : {len(self.injection_info)}')
        print(f'  Total detected : {len(self.detection_catalog)}')

        return iterations

    # ------------------------------------------------------------------
    def _save_checkpoint(self, checkpoint_dir, iteration,
                         injection_info, detections):
        """Save one iteration's results to disk immediately after completion."""
        inj_path = os.path.join(checkpoint_dir,
                                f'injection_iter{iteration:03d}.csv')
        det_path = os.path.join(checkpoint_dir,
                                f'detections_iter{iteration:03d}.csv')

        pd.DataFrame(injection_info).to_csv(inj_path, index=False)
        if detections:
            pd.DataFrame(detections).to_csv(det_path, index=False)

        logger.info(f'Checkpoint saved -> {inj_path}')

    # ------------------------------------------------------------------
    def save_results(self):
        """Save injection catalog, injected image (optional), and detection catalog."""
        os.makedirs(self.config.output_dir, exist_ok=True)
        out = self.config.output_dir

        if self.injection_info:
            path = os.path.join(out, 'injection_catalog.csv')
            pd.DataFrame(self.injection_info).to_csv(path, index=False)
            logger.info(f'Saved injection catalog  -> {path}')

        if self.config.save_injected_image and self.injected_image is not None:
            try:
                from astropy.io import fits
                path = os.path.join(out, 'injected_image.fits')
                fits.writeto(path, self.injected_image.astype(np.float32),
                             overwrite=True)
                logger.info(f'Saved injected image     -> {path}')
            except ImportError:
                path = os.path.join(out, 'injected_image.npy')
                np.save(path, self.injected_image)
                logger.info(f'Saved injected image     -> {path}')

        if self.detection_catalog:
            path = os.path.join(out, 'detection_catalog.csv')
            pd.DataFrame(self.detection_catalog).to_csv(path, index=False)
            logger.info(f'Saved detection catalog  -> {path}')

        logger.info(f'All outputs in: {out}/')