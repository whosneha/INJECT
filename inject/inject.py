"""Core injection routines for synthetic star clusters.

This module implements the primary injection logic, including:
- Cluster image generation (convolved with PSF or Gaussian).
- Position selection and edge avoidance.
- PSF quality flag inspection and optional skipping of bad regions.
- Injection into FITS images with noise and realistic backgrounds.

Functions:
    make_profile_image: Generate a cluster image from a light profile.
    get_actual_psf: Retrieve PSF kernel at a specific position (Rubin/RSP).
    inspect_psf_mask: Query and decode PSF quality flags from Rubin mask arrays.
    inject_clusters_rubin_psf: Main routine to inject clusters into images with
        support for PSF convolution, mask flagging, and bad region skipping.

Key Features:
    - Supports multiple light profile types (King, Plummer, EFF, Sersic).
    - PSF convolution via GalSim (if available) or scipy.signal.convolve.
    - Rubin mask plane awareness (INEXACT_PSF, SENSOR_EDGE, etc.).
    - Per-injection PSF quality annotation for completeness analysis.
    - Configurable bad region skipping vs. flagging and injection strategy.
"""

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
from .psf_convolution import convolve_with_psf, create_rubin_psf


DEFAULT_PSF_BAD_MASK_PLANES = (
    'INEXACT_PSF',
    'SENSOR_EDGE',
    'CLIPPED',
    'REJECTED',
    'NO_DATA',
    'EDGE',
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


def inspect_psf_mask(mask_array, mask_plane_dict, cutout_x, cutout_y,
                     mask_planes=DEFAULT_PSF_BAD_MASK_PLANES):
    """Inspect Rubin mask planes at a cutout position for PSF-quality flags."""
    status = {
        'available': False,
        'flagged': False,
        'reasons': [],
        'mask_value': None,
        'flags': {},
    }

    if mask_array is None or mask_plane_dict is None:
        return status

    cx = int(round(cutout_x))
    cy = int(round(cutout_y))
    if cy < 0 or cx < 0 or cy >= mask_array.shape[0] or cx >= mask_array.shape[1]:
        return status

    mask_value = int(mask_array[cy, cx])
    reasons = []
    flags = {}
    for plane in mask_planes:
        bit = mask_plane_dict.get(plane)
        is_set = bool(bit is not None and (mask_value & (1 << bit)) != 0)
        flags[plane] = is_set
        if is_set:
            reasons.append(plane)

    status.update({
        'available': True,
        'flagged': bool(reasons),
        'reasons': reasons,
        'mask_value': mask_value,
        'flags': flags,
    })
    return status


# ---------------------------------------------------------------------------
# Public compatibility helpers used by tests and scripts
# ---------------------------------------------------------------------------

def create_injection_catalog(n_clusters=10, image_shape=(100, 100),
                             mag_range=(20.0, 24.0),
                             r_half_range=(3.0, 15.0),
                             profile_type='plummer', method='smooth',
                             n_stars_range=(50, 500), imf='kroupa',
                             edge_buffer=20, seed=None):
    """Create a simple injection catalog with basic parameters used by tests."""
    if isinstance(image_shape, int):
        image_shape = (image_shape, image_shape)
    ny, nx = image_shape
    rng = np.random.default_rng(seed)
    catalog = []

    for i in range(int(n_clusters)):
        entry = {
            'id': i,
            'x': float(rng.uniform(edge_buffer, nx - edge_buffer)),
            'y': float(rng.uniform(edge_buffer, ny - edge_buffer)),
            'magnitude': float(rng.uniform(mag_range[0], mag_range[1])),
            'r_half': float(rng.uniform(r_half_range[0], r_half_range[1])),
            'profile_type': profile_type,
            'method': method,
        }
        if method == 'discrete':
            entry['n_stars'] = int(rng.integers(n_stars_range[0], n_stars_range[1] + 1))
            entry['imf'] = imf
        catalog.append(entry)

    return catalog


def inject_cluster(image, position, profile, psf_fwhm=None, add_noise=False,
                   zero_point=27.0, rng_seed=None):
    """Inject a single cluster profile stamp into an image."""
    image = np.asarray(image, dtype=np.float64)
    ny, nx = image.shape
    y0, x0 = int(round(position[1])), int(round(position[0]))

    stamp_size = 51 if profile is None else max(31, int(10 * getattr(profile, 'r_half', 5.0)))
    if stamp_size % 2 == 0:
        stamp_size += 1

    if profile is not None:
        profile_image = profile.generate_2d((stamp_size, stamp_size))
        profile_image = np.asarray(profile_image, dtype=np.float64)
        profile_image /= profile_image.sum() if profile_image.sum() > 0 else 1.0
        total_flux = mag_to_flux(getattr(profile, 'magnitude', 22.0), zero_point=zero_point)
        profile_image *= total_flux / profile_image.sum()
    else:
        profile_image = np.zeros((stamp_size, stamp_size), dtype=np.float64)
        profile_image[stamp_size // 2, stamp_size // 2] = 1.0
        total_flux = 1.0

    if psf_fwhm is not None and psf_fwhm > 0:
        psf_kernel = create_rubin_psf(psf_fwhm, size=stamp_size)
        convolved = convolve_with_psf(profile_image, psf_kernel)
    else:
        convolved = profile_image

    if add_noise:
        rng = np.random.default_rng(rng_seed)
        noise = rng.normal(0.0, np.sqrt(np.clip(convolved, 0.0, None)))
        convolved = convolved + noise

    y_start = y0 - stamp_size // 2
    x_start = x0 - stamp_size // 2
    y_end = y_start + stamp_size
    x_end = x_start + stamp_size

    canvas = image.copy()
    sy0 = max(0, -y_start)
    sx0 = max(0, -x_start)
    ey0 = min(stamp_size, ny - y_start)
    ex0 = min(stamp_size, nx - x_start)
    if ey0 > sy0 and ex0 > sx0:
        canvas[max(y_start, 0):min(y_end, ny), max(x_start, 0):min(x_end, nx)] += convolved[sy0:ey0, sx0:ex0]

    return canvas, convolved


def inject_from_catalog(image, catalog, psf_fwhm=None, exposure=None,
                        add_noise=False, zero_point=27.0):
    """Inject a catalog of cluster entries into an image."""
    injected = np.asarray(image, dtype=np.float64).copy()
    info = []

    for entry in catalog:
        profile_type = entry.get('profile_type', 'plummer').lower()
        if profile_type == 'king':
            profile = KingProfile(r_half=float(entry.get('r_half', 5.0)),
                                  magnitude=float(entry.get('magnitude', 22.0)),
                                  concentration=float(entry.get('concentration', 10.0)), age=1.0)
        elif profile_type == 'eff':
            profile = EFFProfile(r_half=float(entry.get('r_half', 5.0)),
                                 magnitude=float(entry.get('magnitude', 22.0)),
                                 gamma=float(entry.get('gamma', 2.5)), age=1.0)
        elif profile_type == 'sersic':
            profile = SersicProfile(r_half=float(entry.get('r_half', 5.0)),
                                    magnitude=float(entry.get('magnitude', 22.0)),
                                    sersic_n=float(entry.get('sersic_n', 2.0)), age=1.0)
        else:
            profile = PlummerProfile(r_half=float(entry.get('r_half', 5.0)),
                                     magnitude=float(entry.get('magnitude', 22.0)), age=1.0)

        injected, stamp = inject_cluster(
            injected,
            position=(entry.get('x', 0), entry.get('y', 0)),
            profile=profile,
            psf_fwhm=psf_fwhm,
            add_noise=add_noise,
            zero_point=zero_point,
        )
        info.append({**entry, 'stamp_flux': float(stamp.sum())})

    return injected.astype(image.dtype), info


# ---------------------------------------------------------------------------
# Main injection function
# ---------------------------------------------------------------------------

def inject_clusters_rubin_psf(image, catalog,
                               psf_obj,
                               bbox_x_min,
                               bbox_y_min,
                               mask_array=None,
                               mask_plane_dict=None,
                               psf_fwhm_fallback=3.5,
                               pixel_scale=0.2,
                               zero_point=27.0,
                               add_noise=True,
                               use_actual_psf=True,
                               record_psf_mask_flags=True,
                               skip_bad_psf_regions=False,
                               psf_bad_mask_planes=DEFAULT_PSF_BAD_MASK_PLANES,
                               rng_seed=42,
                               verbose=True,
                               use_psf_cache=False,
                               psf_cache=None,
                               band='default'):
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
    mask_array         : 2D ndarray or None -- coadd mask cutout aligned to image
    mask_plane_dict    : dict or None -- Rubin mask plane name -> bit index
    psf_fwhm_fallback  : float  -- Gaussian FWHM in pixels (fallback only)
    pixel_scale        : float  -- arcsec/pixel
    zero_point         : float  -- AB magnitude zero point
    add_noise          : bool
    use_actual_psf     : bool   -- set False to always use Gaussian
    record_psf_mask_flags : bool
        If True, record PSF-related mask-plane flags in injection_info.
    skip_bad_psf_regions : bool
        If True, skip injections landing in flagged mask-plane regions.
    psf_bad_mask_planes : tuple[str, ...]
        Mask planes treated as PSF-quality failures for annotation/skipping.
    rng_seed           : int
    use_psf_cache      : bool   -- enable PSF caching (default False)
    psf_cache          : PSFCache or None  -- pass pre-made cache or let function create one
    verbose            : bool

    Returns
    -------
    injected_image : 2D ndarray  (same dtype as input)
    injection_info : list[dict]  -- one dict per successfully injected cluster
    timing         : dict          -- per-stage wall-clock seconds
    cache_stats    : dict or None  -- PSF cache statistics (if caching enabled)
    """
    import time
    
    ny, nx   = image.shape
    injected = image.copy().astype(np.float64)
    rng_np   = np.random.default_rng(rng_seed)

    gaussian_fallback = (galsim.Gaussian(fwhm=psf_fwhm_fallback * pixel_scale)
                         if HAS_GALSIM else None)

    injection_info = []
    n_ok = n_failed = n_psf_fallback = n_psf_mask_flagged = n_psf_mask_skipped = 0
    
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
        if mask_array is not None and mask_plane_dict is not None:
            print(f'  PSF mask QA  : enabled  (skip flagged={skip_bad_psf_regions})')
        print()

    for i, entry in enumerate(catalog):
        try:
            cx = int(round(entry['x']))
            cy = int(round(entry['y']))

            mask_status = inspect_psf_mask(
                mask_array,
                mask_plane_dict,
                cx,
                cy,
                mask_planes=psf_bad_mask_planes,
            )
            if mask_status['flagged']:
                n_psf_mask_flagged += 1
                if skip_bad_psf_regions:
                    n_psf_mask_skipped += 1
                    if verbose and n_psf_mask_skipped <= 5:
                        reasons = ','.join(mask_status['reasons'])
                        print(f'  Skipping flagged PSF region at ({cx},{cy}): {reasons}')
                    continue

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
                        cached_psf = psf_cache.get(band, cx, cy)
                    
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
                                psf_cache.put(band, cx, cy, psf_gs, fwhm_here)
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
            if record_psf_mask_flags:
                flags = mask_status.get('flags', {})
                info.update({
                    'psf_mask_flagged': mask_status.get('flagged', False),
                    'psf_mask_reasons': ','.join(mask_status.get('reasons', [])),
                    'psf_mask_value': mask_status.get('mask_value'),
                    'psf_mask_inexact': flags.get('INEXACT_PSF', False),
                    'psf_mask_sensor_edge': flags.get('SENSOR_EDGE', False),
                    'psf_mask_clipped': flags.get('CLIPPED', False),
                    'psf_mask_rejected': flags.get('REJECTED', False),
                    'psf_mask_no_data': flags.get('NO_DATA', False),
                    'psf_mask_edge': flags.get('EDGE', False),
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
        if mask_array is not None and mask_plane_dict is not None:
            print(f'  PSF mask flagged  : {n_psf_mask_flagged}')
            print(f'  PSF mask skipped  : {n_psf_mask_skipped}')
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