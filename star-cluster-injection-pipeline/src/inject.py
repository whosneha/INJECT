import numpy as np

try:
    import galsim
    HAS_GALSIM = True
except ImportError:
    HAS_GALSIM = False

try:
    from lsst.geom import Point2D
    HAS_LSST = True
except ImportError:
    HAS_LSST = False

from .light_profiles import (
    KingProfile, PlummerProfile, EFFProfile, SersicProfile, mag_to_flux
)


# ---------------------------------------------------------------------------
# PSF Cache (simple LRU with quantization)
# ---------------------------------------------------------------------------

class PSFCache:
    """
    Simple LRU cache for PSF objects to avoid recomputing nearby positions.
    
    Uses quantized position keys (grid cells) to increase hit rate.
    """
    def __init__(self, max_entries=500, grid_size=8):
        """
        max_entries: max number of PSFs to keep in cache
        grid_size: quantization in pixels (e.g., 8 means 8x8 pixel cells)
        """
        self.max_entries = max_entries
        self.grid_size = grid_size
        self.cache = {}  # key: (band, qx, qy) -> value: (psf_gs, fwhm_px)
        self.access_order = []  # track insertion order for LRU
        self.hits = 0
        self.misses = 0
    
    def _quantize_key(self, band, x, y):
        """Convert position to quantized grid cell key."""
        qx = int(x // self.grid_size)
        qy = int(y // self.grid_size)
        return (band, qx, qy)
    
    def get(self, band, x, y):
        """Retrieve PSF from cache. Returns (psf_gs, fwhm_px) or None if miss."""
        key = self._quantize_key(band, x, y)
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None
    
    def put(self, band, x, y, psf_gs, fwhm_px):
        """Store PSF in cache. Evicts oldest entry if full."""
        key = self._quantize_key(band, x, y)
        if key in self.cache:
            return  # already cached
        
        if len(self.cache) >= self.max_entries:
            # Evict oldest
            oldest_key = self.access_order.pop(0)
            del self.cache[oldest_key]
        
        self.cache[key] = (psf_gs, fwhm_px)
        self.access_order.append(key)
    
    def stats(self):
        """Return cache hit/miss stats."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0
        return {
            'hits': self.hits,
            'misses': self.misses,
            'total': total,
            'hit_rate_pct': hit_rate,
            'entries_stored': len(self.cache),
            'max_entries': self.max_entries,
        }
    
    def reset(self):
        """Clear cache and stats."""
        self.cache.clear()
        self.access_order.clear()
        self.hits = 0
        self.misses = 0


# ---------------------------------------------------------------------------
# Profile stamp builder
# ---------------------------------------------------------------------------

def make_profile_image(entry, pixel_scale=0.2, zero_point=27.0):
    """
    Build an intrinsic 2D cluster stamp from a catalog entry dict.

    Parameters
    ----------
    entry : dict
        Keys used: profile_type, r_half, magnitude, age_gyr, concentration
    pixel_scale : float
    zero_point  : float

    Returns
    -------
    image_2d   : ndarray (float64) normalised to sum=1
    stamp_size : int (always odd)
    """
    profile_type = entry.get('profile_type', 'plummer').lower()
    r_half       = float(entry.get('r_half',      5.0))
    magnitude    = float(entry.get('magnitude',   22.0))
    age          = float(entry.get('age_gyr',      1.0))
    conc         = float(entry.get('concentration', 10.0))

    stamp_size = max(51, int(10 * r_half))
    if stamp_size % 2 == 0:
        stamp_size += 1
    shape = (stamp_size, stamp_size)

    kwargs = dict(r_half=r_half, age=age, magnitude=magnitude, zero_point=zero_point)

    if profile_type == 'king':
        prof = KingProfile(concentration=conc, **kwargs)
    elif profile_type == 'plummer':
        prof = PlummerProfile(**kwargs)
    elif profile_type == 'eff':
        gamma = conc if conc > 2.01 else 2.5
        prof = EFFProfile(gamma=gamma, **kwargs)
    elif profile_type == 'sersic':
        n = conc if conc >= 0.3 else 1.0
        prof = SersicProfile(sersic_n=n, **kwargs)
    else:
        raise ValueError(f'Unknown profile_type: "{profile_type}". '
                         'Choose from king, plummer, eff, sersic.')

    image_2d = prof.generate_2d(shape).astype(np.float64)
    total = image_2d.sum()
    if total > 0:
        image_2d /= total

    return image_2d, stamp_size


# ---------------------------------------------------------------------------
# PSF fetcher
# ---------------------------------------------------------------------------

def get_actual_psf(psf_obj, cutout_x, cutout_y,
                   bbox_x_min, bbox_y_min, pixel_scale=0.2):
    """
    Fetch the Rubin CoaddPsf at a cutout pixel position.

    Converts cutout coords -> focal plane coords using the bbox offset,
    then returns a GalSim InterpolatedImage.

    Parameters
    ----------
    psf_obj    : lsst CoaddPsf
    cutout_x/y : float  -- position in cutout pixel coordinates
    bbox_x_min : int    -- coadd bounding box x offset
    bbox_y_min : int    -- coadd bounding box y offset
    pixel_scale: float

    Returns
    -------
    psf_gs  : galsim.InterpolatedImage
    fwhm_px : float  -- PSF FWHM at this position in pixels
    """
    if not HAS_LSST:
        raise RuntimeError('LSST stack not available.')
    if not HAS_GALSIM:
        raise RuntimeError('GalSim not available.')

    focal_x = float(cutout_x) + bbox_x_min
    focal_y = float(cutout_y) + bbox_y_min
    point   = Point2D(focal_x, focal_y)

    psf_image = psf_obj.computeImage(point)
    psf_array = psf_image.array.astype(np.float64)
    psf_sum   = psf_array.sum()
    if psf_sum > 0:
        psf_array /= psf_sum

    gs_img = galsim.Image(psf_array, scale=pixel_scale)
    psf_gs = galsim.InterpolatedImage(gs_img, normalization='flux')

    shape   = psf_obj.computeShape(point)
    fwhm_px = shape.getDeterminantRadius() * 2.355

    return psf_gs, fwhm_px


# ---------------------------------------------------------------------------
# Main injection function
# ---------------------------------------------------------------------------

def inject_clusters_rubin_psf(image, catalog,
                               psf_obj,
                               bbox_x_min,
                               bbox_y_min,
                               psf_fwhm_fallback=3.5,
                               pixel_scale=0.2,
                               zero_point=27.0,
                               add_noise=True,
                               use_actual_psf=True,
                               rng_seed=42,
                               verbose=True,
                               use_psf_cache=False,
                               psf_cache=None):
    """
    Inject star clusters into a 2D image using the Rubin CoaddPsf.

    For each cluster in the catalog:
      1. make_profile_image()  -> 2D stamp from light_profiles
      2. get_actual_psf()      -> CoaddPsf kernel at that position (or cached)
         (falls back to galsim.Gaussian if PSF fetch fails or use_actual_psf=False)
      3. galsim.Convolve()     -> PSF-convolved stamp
      4. Scale to correct total flux
      5. Optional Poisson-like noise
      6. Add to image with boundary clipping

    Parameters
    ----------
    image              : 2D ndarray
    catalog            : list[dict]  -- from InjectionPipeline.generate_catalog()
    psf_obj            : lsst CoaddPsf  -- from coadd.getPsf()
    bbox_x_min         : int  -- coadd bounding box x offset
    bbox_y_min         : int  -- coadd bounding box y offset
    psf_fwhm_fallback  : float  -- Gaussian FWHM in pixels (fallback only)
    pixel_scale        : float  -- arcsec/pixel
    zero_point         : float  -- AB magnitude zero point
    add_noise          : bool
    use_actual_psf     : bool   -- set False to always use Gaussian
    rng_seed           : int
    use_psf_cache      : bool   -- enable PSF caching (default False)
    psf_cache          : PSFCache or None  -- pass pre-made cache or let function create one
    verbose            : bool

    Returns
    -------
    injected_image : 2D ndarray  (same dtype as input)
    injection_info : list[dict]  -- one dict per successfully injected cluster
    timing : dict  -- timing breakdown for each stage
    cache_stats : dict or None  -- PSF cache statistics (if caching enabled)
    injected_image : 2D ndarray  (same dtype as input)
    injection_info : list[dict]  -- one dict per successfully injected cluster
    """
    import time
    
    ny, nx   = image.shape
    injected = image.copy().astype(np.float64)
    rng_np   = np.random.default_rng(rng_seed)

    gaussian_fallback = (galsim.Gaussian(fwhm=psf_fwhm_fallback * pixel_scale)
                         if HAS_GALSIM else None)

    injection_info = []
    n_ok = n_failed = n_psf_fallback = 0
    
    # Initialize PSF cache if requested
    if use_psf_cache and psf_cache is None:
        psf_cache = PSFCache(max_entries=500, grid_size=8)
    
    # Timing dictionaries
    timing = {
        'profile_build': 0.0,
        'psf_fetch': 0.0,
        'convolution': 0.0,
        'placement': 0.0,
    }

    if verbose:
        psf_mode = 'Rubin CoaddPsf' if use_actual_psf else 'Gaussian (forced)'
        print(f'  PSF mode     : {psf_mode}  (fallback FWHM={psf_fwhm_fallback:.2f} px)')
        print(f'  Bbox offset  : ({bbox_x_min}, {bbox_y_min})')
        print(f'  N clusters   : {len(catalog)}')
        print(f'  PSF cache    : {"enabled" if use_psf_cache else "disabled"}')
        print()

    for i, entry in enumerate(catalog):
        try:
            cx = int(round(entry['x']))
            cy = int(round(entry['y']))

            # -- 1. Build intrinsic stamp --
            t0 = time.time()
            profile_arr, stamp_size = make_profile_image(
                entry, pixel_scale=pixel_scale, zero_point=zero_point
            )
            timing['profile_build'] += time.time() - t0

            # -- 2 & 3. Convolve with PSF --
            if HAS_GALSIM:
                gs_cluster = galsim.InterpolatedImage(
                    galsim.Image(profile_arr, scale=pixel_scale),
                    normalization='flux'
                )

                psf_gs   = None
                fwhm_here = psf_fwhm_fallback
                psf_used  = 'gaussian_fallback'

                if use_actual_psf and HAS_LSST:
                    t0 = time.time()
                    
                    # Try cache first
                    cached_psf = None
                    if use_psf_cache and psf_cache is not None:
                        cached_psf = psf_cache.get('i', cx, cy)  # band hardcoded as 'i' for now
                    
                    if cached_psf is not None:
                        psf_gs, fwhm_here = cached_psf
                        psf_used = 'rubin_cached'
                    else:
                        # Compute actual PSF
                        try:
                            psf_gs, fwhm_here = get_actual_psf(
                                psf_obj, cx, cy, bbox_x_min, bbox_y_min, pixel_scale
                            )
                            psf_used = 'rubin'
                            
                            # Store in cache
                            if use_psf_cache and psf_cache is not None:
                                psf_cache.put('i', cx, cy, psf_gs, fwhm_here)
                        except Exception as e:
                            n_psf_fallback += 1
                            if verbose and n_psf_fallback <= 5:
                                print(f'  PSF fallback at ({cx},{cy}): '
                                      f'{str(e).splitlines()[0]}')
                            psf_gs   = gaussian_fallback
                            fwhm_here = psf_fwhm_fallback
                            psf_used  = 'gaussian_fallback'
                    
                    timing['psf_fetch'] += time.time() - t0

                if psf_gs is None:
                    psf_gs   = gaussian_fallback
                    psf_used  = 'gaussian_fallback'

                t0 = time.time()
                convolved = galsim.Convolve([gs_cluster, psf_gs])
                out_img   = galsim.Image(stamp_size, stamp_size, scale=pixel_scale)
                convolved.drawImage(image=out_img, method='no_pixel')
                stamp = out_img.array.copy().astype(np.float64)
                timing['convolution'] += time.time() - t0
            else:
                # No GalSim: use scipy fftconvolve with a Gaussian kernel
                from scipy.signal import fftconvolve
                from scipy.ndimage import gaussian_filter
                sigma_px = psf_fwhm_fallback / 2.355
                stamp    = gaussian_filter(profile_arr, sigma=sigma_px)
                fwhm_here = psf_fwhm_fallback
                psf_used  = 'scipy_gaussian_fallback'

            # -- 4. Scale to correct total flux --
            total_flux = mag_to_flux(entry['magnitude'], zero_point=zero_point)
            stamp_sum  = stamp.sum()
            if stamp_sum > 0:
                stamp *= total_flux / stamp_sum

            # -- 5. Optional noise --
            if add_noise:
                noise_sigma = np.sqrt(np.clip(stamp, 0, None))
                stamp += rng_np.normal(
                    0.0, np.where(noise_sigma > 0, noise_sigma, 1e-10)
                )

            # -- 6. Place into image with boundary clipping --
            t0 = time.time()
            sh, sw = stamp.shape
            y0 = cy - sh // 2;  y1 = y0 + sh
            x0 = cx - sw // 2;  x1 = x0 + sw
            iy0 = max(y0, 0);   iy1 = min(y1, ny)
            ix0 = max(x0, 0);   ix1 = min(x1, nx)

            if iy0 >= iy1 or ix0 >= ix1:
                continue

            sy0 = iy0 - y0;  sy1 = sy0 + (iy1 - iy0)
            sx0 = ix0 - x0;  sx1 = sx0 + (ix1 - ix0)
            injected[iy0:iy1, ix0:ix1] += stamp[sy0:sy1, sx0:sx1]
            timing['placement'] += time.time() - t0

            info = dict(entry)
            info.update({
                'stamp'       : stamp,
                'stamp_flux'  : float(stamp.sum()),
                'total_flux'  : total_flux,
                'psf_fwhm_px' : fwhm_here,
                'psf_used'    : psf_used,
            })
            injection_info.append(info)
            n_ok += 1

        except Exception as exc:
            n_failed += 1
            if verbose and n_failed <= 10:
                print(f'  Cluster {i} (id={entry.get("id","?")}) failed: {exc}')

    if verbose:
        print('Injection complete.')
        print(f'  Successful        : {n_ok}')
        print(f'  Failed            : {n_failed}')
        print(f'  PSF fallback used : {n_psf_fallback}')
        print()
        print('Timing breakdown (seconds):')
        total_time = sum(timing.values())
        for stage, t in timing.items():
            pct = (t / total_time * 100) if total_time > 0 else 0
            print(f'  {stage:20s}: {t:8.2f}  ({pct:5.1f}%)')
        print(f'  {"TOTAL":20s}: {total_time:8.2f}')
        
        if use_psf_cache and psf_cache is not None:
            stats = psf_cache.stats()
            print()
            print('PSF Cache stats:')
            print(f'  Cache hits        : {stats["hits"]}')
            print(f'  Cache misses      : {stats["misses"]}')
            print(f'  Hit rate          : {stats["hit_rate_pct"]:.1f}%')
            print(f'  Entries stored    : {stats["entries_stored"]} / {stats["max_entries"]}')

    return injected.astype(image.dtype), injection_info, timing, (psf_cache.stats() if psf_cache else None)