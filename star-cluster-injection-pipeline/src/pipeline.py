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

                logger.info(f'  Loaded band {band}: shape={self.images[band].shape}')

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
                             use_psf_cache      = True,
                             psf_cache_grid     = 8,
                             psf_cache_size     = 2000,
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
            logger.info(f'{"="*50}')
            logger.info(f'  Running band: {band}')
            logger.info(f'{"="*50}')

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
                use_psf_cache     = use_psf_cache,
                psf_cache_grid    = psf_cache_grid,
                psf_cache_size    = psf_cache_size,
                band              = band,
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
                  use_psf_cache     = True,    # share one PSF cache across iterations
                  psf_cache_grid    = 8,       # px quantization for cache keys
                  psf_cache_size    = 2000,    # max entries before LRU eviction
                  band              = 'default',
                  verbose           = True):
        """
        Run N iterations of injection + detection.

        Parameters
        ----------
        store_images   : bool
            If True, keep injected_image in each iteration dict.
            WARNING: memory cost = n_iterations × image_size × 8 bytes.
            Default False — only the iter-0 image is kept for plotting,
            all others are deleted immediately.
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
        use_psf_cache  : bool
            If True (default), build one shared PSFCache across all
            iterations. Same image regions are re-sampled iteration after
            iteration, so the cache hit rate climbs sharply after iter 0
            warms it up. Disable only for debugging.
        psf_cache_grid : int
            Pixel quantization size for cache keys. Larger = coarser =
            higher hit rate but lower spatial fidelity. 8 px is a good
            default for Rubin coadds (PSF varies on ~100 px scales).
        psf_cache_size : int
            Max number of PSF entries before LRU eviction. 2000 covers
            a ~360×360 px patch at grid=8.
        band : str
            Cache key namespace — important when running multiband so
            different bands don't collide on the same (x,y).

        Returns
        -------
        iterations : list[dict], one per iteration, keys:
            iteration, injection_info, detections, timing, cache_stats,
            injected_image (only if store_images=True, or iter==0)
        """
        from .inject import inject_clusters_rubin_psf, PSFCache

        if n_workers == -1:
            n_workers = os.cpu_count()
            logger.info(f'n_workers=-1 → using all {n_workers} CPUs')

        if checkpoint_dir is not None:
            os.makedirs(checkpoint_dir, exist_ok=True)

        # One shared PSF cache for the whole batch — across 10 iterations the
        # same image regions get sampled repeatedly, so the hit rate climbs
        # fast after iteration 0 warms the cache.
        shared_psf_cache = (PSFCache(max_entries=psf_cache_size,
                                     grid_size=psf_cache_grid)
                            if use_psf_cache else None)

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
                'use_psf_cache'    : use_psf_cache,
                'psf_cache'        : shared_psf_cache,
                'band'             : band,
                'verbose'          : verbose,
            })

        # ------------------------------------------------------------------
        # Worker — fully self-contained, no reference to self inside
        # ------------------------------------------------------------------
        def _run_one(args):
            from .inject import inject_clusters_rubin_psf
            import time as _time

            it = args['iteration']

            # Print the header before injection starts so user sees progress
            logger.info(f'--- Iteration {it + 1}/{n_iterations} ---')
            t_iter_start = _time.time()

            result_tuple = inject_clusters_rubin_psf(
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
                verbose           = args['verbose'],
                use_psf_cache     = args['use_psf_cache'],
                psf_cache         = args['psf_cache'],
                band              = args['band'],
            )

            # inject_clusters_rubin_psf returns 4-tuple (new) or 2-tuple (legacy)
            if len(result_tuple) == 4:
                injected_image, injection_info, timing, cache_stats = result_tuple
            else:
                injected_image, injection_info = result_tuple
                timing, cache_stats = {}, None

            # Drop stamps immediately after injection
            for entry in injection_info:
                entry.pop('stamp', None)
                entry['iteration'] = it

            detections = []
            if args['detector_fn'] is not None:
                detections = args['detector_fn'](injected_image)
                for d in detections:
                    d['iteration'] = it

            logger.info(f'  iter {it}: injected={len(injection_info)}  '
                        f'detected={len(detections)}  '
                        f'wall={_time.time()-t_iter_start:.1f}s')

            # Checkpoint to disk
            if args['checkpoint_dir'] is not None:
                inj_path = os.path.join(args['checkpoint_dir'],
                                        f'injection_iter{it:03d}.csv')
                det_path = os.path.join(args['checkpoint_dir'],
                                        f'detections_iter{it:03d}.csv')
                pd.DataFrame(injection_info).to_csv(inj_path, index=False)
                if detections:
                    pd.DataFrame(detections).to_csv(det_path, index=False)
                logger.info(f'  checkpoint saved -> {inj_path}')

            result = {
                'iteration'      : it,
                'injection_info' : injection_info,
                'detections'     : detections,
                'timing'         : timing,
                'cache_stats'    : cache_stats,
            }
            if args['store_images']:
                result['injected_image'] = injected_image
            else:
                # Only keep iter-0 image (for plotting); free everything else
                result['injected_image'] = injected_image if it == 0 else None
                if it != 0:
                    del injected_image

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

        logger.info('Batch complete.')
        logger.info(f'  Total injected : {len(self.injection_info)}')
        logger.info(f'  Total detected : {len(self.detection_catalog)}')

        if shared_psf_cache is not None:
            stats = shared_psf_cache.stats()
            logger.info(f'  PSF cache      : {stats["hits"]} hits / '
                        f'{stats["misses"]} misses '
                        f'({stats["hit_rate_pct"]:.1f}% hit rate, '
                        f'{stats["entries_stored"]} entries)')

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
    def _resolve_psf_context(self, band=None, psf_obj=None,
                             bbox_x_min=None, bbox_y_min=None,
                             psf_fwhm_fallback=3.5):
        """Resolve PSF and bbox context from loaded Rubin data when available."""
        active_band = band or self.config.active_bands[0]

        if psf_obj is None and hasattr(self, 'psf_objs'):
            psf_obj = self.psf_objs.get(active_band)

        if (bbox_x_min is None or bbox_y_min is None) and hasattr(self, 'bboxes'):
            bx, by = self.bboxes.get(active_band, (0, 0))
            if bbox_x_min is None:
                bbox_x_min = bx
            if bbox_y_min is None:
                bbox_y_min = by

        return {
            'band': active_band,
            'psf_obj': psf_obj,
            'bbox_x_min': 0 if bbox_x_min is None else bbox_x_min,
            'bbox_y_min': 0 if bbox_y_min is None else bbox_y_min,
            'psf_fwhm_fallback': psf_fwhm_fallback,
        }

    # ------------------------------------------------------------------
    def inject(self, catalog=None, band=None, psf_obj=None,
               bbox_x_min=None, bbox_y_min=None,
               psf_fwhm_fallback=3.5, rng_seed=None,
               drop_stamps=True, verbose=True):
        """
        Run one simple injection pass and store the results on the pipeline.

        Parameters
        ----------
        catalog : list[dict] or None
            Injection catalog. If None, generate_catalog() is used.
        band, psf_obj, bbox_x_min, bbox_y_min, psf_fwhm_fallback
            Optional Rubin PSF context. If omitted, loaded Butler products
            are used when available.
        rng_seed : int or None
            Random seed forwarded to inject_clusters_rubin_psf.
        drop_stamps : bool
            Remove large stamp arrays from injection_info after injection.

        Returns
        -------
        injected_image, injection_info
        """
        from .inject import inject_clusters_rubin_psf

        if self.image is None:
            raise RuntimeError('Call load_data(...) before inject().')

        context = self._resolve_psf_context(
            band=band,
            psf_obj=psf_obj,
            bbox_x_min=bbox_x_min,
            bbox_y_min=bbox_y_min,
            psf_fwhm_fallback=psf_fwhm_fallback,
        )

        if catalog is None:
            catalog = self.generate_catalog()

        result = inject_clusters_rubin_psf(
            image=self.image,
            catalog=catalog,
            psf_obj=context['psf_obj'],
            bbox_x_min=context['bbox_x_min'],
            bbox_y_min=context['bbox_y_min'],
            psf_fwhm_fallback=context['psf_fwhm_fallback'],
            pixel_scale=self.config.pixel_scale,
            zero_point=self.config.zero_point,
            add_noise=self.config.add_noise,
            use_actual_psf=self.config.use_actual_psf,
            rng_seed=self.config.seed if rng_seed is None else rng_seed,
            verbose=verbose,
        )

        if len(result) == 4:
            injected_image, injection_info, _, _ = result
        else:
            injected_image, injection_info = result

        if drop_stamps:
            for entry in injection_info:
                entry.pop('stamp', None)

        self._catalog = catalog
        self.injected_image = injected_image
        self.injection_info = injection_info
        return injected_image, injection_info

    # ------------------------------------------------------------------
    def detect_with(self, detector_fn, image=None, **detector_kwargs):
        """
        Run a user-provided detection function on the injected image.

        The callable must return a list of dicts with at least x and y keys.
        """
        image_to_detect = self.injected_image if image is None else image
        if image_to_detect is None:
            raise RuntimeError('No injected image available. Run inject() first or pass image=.')

        detections = detector_fn(image_to_detect, **detector_kwargs)
        self.detection_catalog = detections
        return detections

    # ------------------------------------------------------------------
    def analyze(self, detections=None, match_radius=5.0):
        """
        Match detections back to injections and return summary statistics.
        """
        from .retrieval import ClusterRetrieval

        if detections is not None:
            self.detection_catalog = detections

        if not self.injection_info:
            raise RuntimeError('No injections available. Run inject() first.')

        self.retrieval = ClusterRetrieval(self.injection_info, self.detection_catalog)
        self.retrieval.match_detections(match_radius=match_radius)
        return self.retrieval.get_summary_statistics()

    # ------------------------------------------------------------------
    def make_plots(self, output_dir=None, plots=None, show=True, save=True,
                   n_stamps=6, stamp_half_size=28, psf_grid_fwhm=None,
                   poster_style=False):
        """
        Make and save pipeline plots from one consistent API call.

        Notes
        -----
        - `plots` controls which plots are displayed.
        - All available plots are still saved when `save=True`.
        - Postage stamp triptychs are always saved.
        """
        import matplotlib.pyplot as plt
        from matplotlib.colors import SymLogNorm
        from .plotting import (
            plot_position_map,
            plot_completeness_1d,
            plot_completeness_2d,
            plot_psf_fwhm_map,
        )
        from .visualization import plot_injection_summary as viz_plot_injection_summary

        all_plot_keys = {
            'injection_summary',
            'before_after',
            'position_map',
            'completeness_1d',
            'completeness_2d',
            'psf_fwhm_hist',
            'psf_fwhm_map',
        }
        display_keys = set(all_plot_keys if plots is None else plots)

        out_dir = output_dir or self.config.output_dir
        if save:
            os.makedirs(out_dir, exist_ok=True)

        figures = {}
        saved = {}

        style = {
            'figure.dpi': 140,
            'savefig.dpi': 350 if poster_style else 150,
            'font.size': 20 if poster_style else 11,
            'axes.titlesize': 28 if poster_style else 12,
            'axes.labelsize': 22 if poster_style else 10,
            'xtick.labelsize': 18 if poster_style else 9,
            'ytick.labelsize': 18 if poster_style else 9,
            'legend.fontsize': 16 if poster_style else 9,
        }

        with plt.rc_context(style):
            # 1) Injection summary plot
            if self.image is not None and self.injected_image is not None and self.injection_info:
                show_this = 'injection_summary' in display_keys and show
                save_path = os.path.join(out_dir, 'injection_summary.png') if save else None
                viz_plot_injection_summary(
                    self.image,
                    self.injected_image,
                    self.injection_info,
                    save_path=save_path,
                    show=show_this,
                )
                if save_path is not None:
                    saved['injection_summary'] = save_path

                # before/after/difference panel
                if 'before_after' in all_plot_keys:
                    fig, axes = plt.subplots(1, 3, figsize=(24, 8) if poster_style else (12, 4),
                                             constrained_layout=True)
                    vmin, vmax = np.percentile(self.image, [1, 99])
                    diff = self.injected_image.astype(np.float64) - self.image.astype(np.float64)
                    dv = max(np.nanpercentile(np.abs(diff), 99), 1e-6)

                    axes[0].imshow(self.image, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
                    axes[0].set_title('Original')
                    axes[1].imshow(self.injected_image, cmap='gray', origin='lower', vmin=vmin, vmax=vmax)
                    axes[1].set_title('Injected')
                    axes[2].imshow(diff, cmap='RdBu_r', origin='lower', vmin=-dv, vmax=dv)
                    axes[2].set_title('Difference')
                    for ax in axes:
                        ax.set_xticks([])
                        ax.set_yticks([])

                    if save:
                        path = os.path.join(out_dir, 'before_after.png')
                        fig.savefig(path, dpi=style['savefig.dpi'], bbox_inches='tight')
                        saved['before_after'] = path

                    if show and 'before_after' in display_keys:
                        plt.show()
                    else:
                        plt.close(fig)
                    figures['before_after'] = fig

            # 2) Retrieval-dependent plots
            if self.retrieval is not None:
                if 'position_map' in all_plot_keys:
                    fig, _ = plot_position_map(
                        self.retrieval._matched,
                        self.injected_image if self.injected_image is not None else self.image,
                    )
                    if save:
                        path = os.path.join(out_dir, 'position_map.png')
                        fig.savefig(path, dpi=style['savefig.dpi'], bbox_inches='tight')
                        saved['position_map'] = path
                    if show and 'position_map' in display_keys:
                        plt.show()
                    else:
                        plt.close(fig)
                    figures['position_map'] = fig

                if 'completeness_1d' in all_plot_keys:
                    fig, _ = plot_completeness_1d(
                        self.retrieval,
                        self.config,
                        pixel_scale=self.config.pixel_scale,
                    )
                    if save:
                        path = os.path.join(out_dir, 'completeness_1d.png')
                        fig.savefig(path, dpi=style['savefig.dpi'], bbox_inches='tight')
                        saved['completeness_1d'] = path
                    if show and 'completeness_1d' in display_keys:
                        plt.show()
                    else:
                        plt.close(fig)
                    figures['completeness_1d'] = fig

                if 'completeness_2d' in all_plot_keys:
                    fig, _ = plot_completeness_2d(self.retrieval, self.config)
                    if save:
                        path = os.path.join(out_dir, 'completeness_2d.png')
                        fig.savefig(path, dpi=style['savefig.dpi'], bbox_inches='tight')
                        saved['completeness_2d'] = path
                    if show and 'completeness_2d' in display_keys:
                        plt.show()
                    else:
                        plt.close(fig)
                    figures['completeness_2d'] = fig

            # 3) PSF plots from injection metadata
            psf_vals = [e.get('psf_fwhm_px', np.nan) for e in self.injection_info]
            psf_vals = np.array([v for v in psf_vals if not np.isnan(v)])
            if len(psf_vals) > 0 and 'psf_fwhm_hist' in all_plot_keys:
                fig, ax = plt.subplots(figsize=(11, 7) if poster_style else (7, 4))
                ax.hist(psf_vals, bins=20, color='steelblue', edgecolor='white', lw=0.8)
                ax.axvline(np.median(psf_vals), ls='--', color='tomato', lw=1.5,
                           label=f'Median = {np.median(psf_vals):.3f} px')
                ax.set_xlabel('PSF FWHM at injection position (pixels)')
                ax.set_ylabel('Count')
                ax.set_title('Distribution of PSF FWHM Across Injection Positions')
                ax.legend()
                if save:
                    path = os.path.join(out_dir, 'injection_psf_fwhm.png')
                    fig.savefig(path, dpi=style['savefig.dpi'], bbox_inches='tight')
                    saved['psf_fwhm_hist'] = path
                if show and 'psf_fwhm_hist' in display_keys:
                    plt.show()
                else:
                    plt.close(fig)
                figures['psf_fwhm_hist'] = fig

            if psf_grid_fwhm is not None and 'psf_fwhm_map' in all_plot_keys:
                fig, _ = plot_psf_fwhm_map(psf_grid_fwhm, pixel_scale=self.config.pixel_scale)
                if save:
                    path = os.path.join(out_dir, 'psf_fwhm_map.png')
                    fig.savefig(path, dpi=style['savefig.dpi'], bbox_inches='tight')
                    saved['psf_fwhm_map'] = path
                if show and 'psf_fwhm_map' in display_keys:
                    plt.show()
                else:
                    plt.close(fig)
                figures['psf_fwhm_map'] = fig

            # 4) Postage stamp triptychs are always saved
            if self.image is not None and self.injected_image is not None and self.injection_info:
                for idx, info in enumerate(self.injection_info[:n_stamps]):
                    x0 = int(round(info['x']))
                    y0 = int(round(info['y']))
                    y_min = max(0, y0 - stamp_half_size)
                    y_max = min(self.image.shape[0], y0 + stamp_half_size + 1)
                    x_min = max(0, x0 - stamp_half_size)
                    x_max = min(self.image.shape[1], x0 + stamp_half_size + 1)

                    s0 = self.image[y_min:y_max, x_min:x_max]
                    s1 = self.injected_image[y_min:y_max, x_min:x_max]
                    sd = s1.astype(np.float64) - s0.astype(np.float64)
                    svmin, svmax = np.percentile(np.concatenate([s0.ravel(), s1.ravel()]), [1, 99])
                    sdmax = max(np.nanpercentile(np.abs(sd), 99.5), 1e-6)

                    fig, axes = plt.subplots(1, 3, figsize=(18, 6), constrained_layout=True)
                    axes[0].imshow(s0, cmap='gray', origin='lower', vmin=svmin, vmax=svmax)
                    axes[0].set_title('Original Stamp')
                    axes[1].imshow(s1, cmap='gray', origin='lower', vmin=svmin, vmax=svmax)
                    axes[1].set_title('Injected Stamp')
                    axes[2].imshow(
                        sd,
                        cmap='coolwarm',
                        origin='lower',
                        norm=SymLogNorm(linthresh=max(sdmax / 30, 1e-6), vmin=-sdmax, vmax=sdmax),
                    )
                    axes[2].set_title('Difference')
                    for ax in axes:
                        ax.set_xticks([])
                        ax.set_yticks([])

                    fig.suptitle(
                        f"Stamp {idx + 1}: (x, y)=({info['x']:.1f}, {info['y']:.1f}), m={info['magnitude']:.2f}",
                        fontsize=26 if poster_style else 12,
                    )
                    path = os.path.join(out_dir, f'postage_stamp_{idx + 1:02d}.png')
                    fig.savefig(path, dpi=style['savefig.dpi'], bbox_inches='tight')
                    saved[f'postage_stamp_{idx + 1:02d}'] = path
                    if show and 'postage_stamps' in display_keys:
                        plt.show()
                    else:
                        plt.close(fig)

        return {
            'figures': figures,
            'saved': saved,
        }

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