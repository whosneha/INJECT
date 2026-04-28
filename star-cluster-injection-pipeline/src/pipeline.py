import os
import numpy as np
import pandas as pd


class InjectionPipeline:
    """
    Orchestrates catalog generation, injection, and saving results.

    Usage
    -----
    pipe = InjectionPipeline(config)
    pipe.load_data(image=image)
    catalog = pipe.generate_catalog()

    # inject using inject_clusters_rubin_psf (in notebook or here)
    pipe.injected_image    = injected_image
    pipe.injection_info    = injection_info
    pipe.detection_catalog = detections
    pipe.save_results()
    """

    def __init__(self, config):
        self.config = config
        self.image             = None
        self.injected_image    = None
        self.injection_info    = []
        self.detection_catalog = []
        self.retrieval         = None
        self._catalog          = None

    # ------------------------------------------------------------------
    def load_data(self, image):
        """Load the base image to inject into."""
        self.image = np.array(image, dtype=np.float64)

    # ------------------------------------------------------------------
    def generate_catalog(self, rng=None):
        """
        Generate a randomised injection catalog from the cluster config.

        Returns
        -------
        catalog : list[dict]
            Each dict has keys:
            id, x, y, magnitude, r_half, concentration, age_gyr, profile_type
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
            entry = {
                'id'           : i,
                'x'            : int(rng.integers(buf, nx - buf)),
                'y'            : int(rng.integers(buf, ny - buf)),
                'magnitude'    : float(rng.uniform(cc.mag_min,           cc.mag_max)),
                'r_half'       : float(rng.uniform(cc.r_half_min,        cc.r_half_max)),
                'concentration': float(rng.uniform(cc.concentration_min, cc.concentration_max)),
                'age_gyr'      : float(rng.uniform(cc.age_min_gyr,       cc.age_max_gyr)),
                'profile_type' : cc.profile_type,
            }
            catalog.append(entry)

        self._catalog = catalog
        return catalog
    

    def run_batch(self, n_iterations, n_per_iter,
                  psf_obj, bbox_x_min, bbox_y_min,
                  psf_fwhm_fallback=3.5,
                  detector_fn=None,
                  verbose=True):
        """
        Run N iterations of injection + detection.

        Returns
        -------
        iterations : list[dict]  — one dict per iteration, each with keys:
            'iteration'       : int
            'injection_info'  : list[dict]
            'detections'      : list[dict]
            'injected_image'  : 2D ndarray
        """
        from .inject import inject_clusters_rubin_psf

        iterations = []
        original_n = self.config.n_clusters
        self.config.n_clusters = n_per_iter

        for iteration in range(n_iterations):
            if verbose:
                print(f'\n--- Iteration {iteration + 1}/{n_iterations} ---')

            self.config.seed = iteration
            catalog = self.generate_catalog()

            injected_image, injection_info = inject_clusters_rubin_psf(
                image             = self.image,
                catalog           = catalog,
                psf_obj           = psf_obj,
                bbox_x_min        = bbox_x_min,
                bbox_y_min        = bbox_y_min,
                psf_fwhm_fallback = psf_fwhm_fallback,
                pixel_scale       = self.config.pixel_scale,
                zero_point        = self.config.zero_point,
                add_noise         = self.config.add_noise,
                use_actual_psf    = self.config.use_actual_psf,
                rng_seed          = iteration,
                verbose           = verbose,
            )

            for entry in injection_info:
                entry['iteration'] = iteration

            detections = []
            if detector_fn is not None:
                detections = detector_fn(injected_image)
                for d in detections:
                    d['iteration'] = iteration
                if verbose:
                    print(f'  Detections: {len(detections)}')

            iterations.append({
                'iteration'      : iteration,
                'injection_info' : injection_info,
                'detections'     : detections,
                'injected_image' : injected_image,
            })

        self.config.n_clusters = original_n

        # Flatten for convenience
        self.injection_info    = [e for it in iterations for e in it['injection_info']]
        self.detection_catalog = [d for it in iterations for d in it['detections']]

        if verbose:
            print(f'\nBatch complete.')
            print(f'  Total injected : {len(self.injection_info)}')
            print(f'  Total detected : {len(self.detection_catalog)}')

        return iterations

    # ------------------------------------------------------------------
    def save_results(self):
        """Save injection catalog, injected image (optional), and summary CSV."""
        os.makedirs(self.config.output_dir, exist_ok=True)
        out = self.config.output_dir

        # -- injection catalog --
        if self.injection_info:
            rows = [{k: v for k, v in info.items() if k != 'stamp'}
                    for info in self.injection_info]
            df = pd.DataFrame(rows)
            path = os.path.join(out, 'injection_catalog.csv')
            df.to_csv(path, index=False)
            print(f'Saved injection catalog  -> {path}')

        # -- injected image --
        if self.config.save_injected_image and self.injected_image is not None:
            try:
                from astropy.io import fits
                path = os.path.join(out, 'injected_image.fits')
                fits.writeto(path, self.injected_image.astype(np.float32),
                             overwrite=True)
                print(f'Saved injected image     -> {path}')
            except ImportError:
                np.save(os.path.join(out, 'injected_image.npy'), self.injected_image)
                print(f'Saved injected image (npy) -> {out}/injected_image.npy')

        # -- detection catalog --
        if self.detection_catalog:
            pd.DataFrame(self.detection_catalog).to_csv(
                os.path.join(out, 'detection_catalog.csv'), index=False
            )
            print(f'Saved detection catalog  -> {out}/detection_catalog.csv')

        print(f'All outputs in: {out}/')