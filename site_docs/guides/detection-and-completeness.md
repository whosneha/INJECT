# Detection and Completeness

Injection-only metrics are not enough; the full science loop is injection plus recovery.

## Detection Stage

After injecting clusters, run your detector and store candidate catalogs with clear schema:

- ID (if available)
- Pixel coordinates
- Flux or magnitude estimate
- Quality flags / SNR

The detector is intentionally user-supplied. The pipeline is designed so you can plug in your own callable cleanly rather than rewriting the injection machinery.

Typical pattern:

```python
detections = my_detector(injected_image)
```

or in batch mode:

```python
iterations = pipe.run_batch(..., detector_fn=my_detector)
```

## Detector Plug-In Contract

There are two common ways to call a user detector:

- `pipe.run_batch(..., detector_fn=my_detector)`
- `pipe.detect_with(my_detector, image=..., **detector_kwargs)`

Required input contract:

- In batch mode, your detector must accept the injected image as its first positional argument: `my_detector(image)`.
- In direct detection mode, your detector must accept the injected image as its first positional argument and may also accept extra keyword arguments: `my_detector(image, **kwargs)`.
- `image` will be a 2D array in the same pixel coordinate system used for injection.

Required output contract:

- Return `list[dict]`.
- Each dict must contain at least:
  - `x`: detected x position in pixels
  - `y`: detected y position in pixels

Minimal valid example:

```python
def my_detector(image):
    return [
        {"x": 143.2, "y": 287.5},
        {"x": 412.0, "y": 98.4},
    ]
```

Valid richer example:

```python
def my_detector(image, threshold=5.0):
    return [
        {"x": 143.2, "y": 287.5, "snr": 7.1, "flux": 1530.0, "flag": 0},
        {"x": 412.0, "y": 98.4, "snr": 5.4, "r_half": 3.8, "ellipticity": 0.12},
    ]
```

## Truth Matching

Match detections against injected truth entries using configurable radius and quality filters.

Recommended logging:

- Match radius used
- Ambiguous matches count
- Unmatched injection count
- Unmatched detection count

## Expected Injector Output

After injection, the pipeline returns `injection_info`, a list of dictionaries with one entry per injected cluster.

Typical fields include:

- `x`, `y`: injected centroid in pixel coordinates.
- `magnitude`, `flux`, `total_flux`, `stamp_flux`: photometric truth values.
- `r_half`, `concentration`: morphology inputs.
- `profile_type`, `method`: generation choices.
- `id`, `age_gyr`: bookkeeping and population metadata.
- `stamp`: the injected PSF-convolved stamp when retained for diagnostics.

For large runs, keeping `stamp` for every entry is usually not desirable unless you are doing explicit debugging.

## Expected Detection Catalog Shape

Your detector output should at minimum provide:

- `x`
- `y`

Strongly recommended optional fields:

- `flux` or `magnitude`
- `r_half`
- `snr`
- `flag`
- `area`
- `ellipticity`

These optional fields unlock richer completeness and recovery summaries.

## What Optional Detection Fields Unlock

| Field | Why it matters |
| --- | --- |
| `magnitude` | Completeness versus magnitude |
| `r_half` | Completeness versus size |
| `magnitude` and `r_half` together | 2D completeness maps |
| `snr` | Completeness versus detection significance |
| `flux` | Flux-recovery or photometric-offset analysis |
| `ellipticity` | Morphology-recovery checks |
| `flag` | Quality filtering |
| `area` | Sanity checks against footprint size |

## Completeness Curves

Compute completeness as:

$$
C(m) = \frac{N_{\mathrm{recovered}}(m)}{N_{\mathrm{injected}}(m)}
$$

You can also bin by size, concentration, or local background for richer diagnostics.

## Reporting Pattern

For each experiment, export:

- Completeness vs magnitude
- Completeness vs half-light radius
- Optional 2D completeness surfaces
- Confidence intervals per bin

## Retrieval Summary Pattern

Useful summary outputs include:

- Number injected
- Number recovered
- Number missed
- Overall completeness
- Approximate 50% completeness limits in magnitude and size
- Mean and scatter of photometric offsets for recovered objects

This kind of summary is especially helpful when comparing multiple detector configurations or RSP fields.

## Validation Checklist

1. Confirm enough injections per bin.
2. Verify detector threshold consistency across runs.
3. Test sensitivity to matching radius.
4. Document all cuts before comparison.
5. If using Rubin coadds, decide whether injections in `INEXACT_PSF`, `SENSOR_EDGE`, `CLIPPED`, `REJECTED`, `NO_DATA`, or `EDGE` regions should be kept, flagged, or excluded.
6. Confirm that `x` and `y` are in the same pixel coordinate system as the injected image.
7. Confirm that any reported `r_half` values are in pixels, not arcseconds.
8. Confirm that any reported magnitudes use the same zero-point convention as the truth catalog.

## Rubin PSF-Quality Flags

When running on RSP/Butler coadds, the pipeline can annotate each injected source with Rubin mask-plane flags that indicate potentially unreliable PSF regions.

- Default behavior: keep the injection and record the flags in `injection_info`.
- Strict behavior: set `skip_bad_psf_regions=True` to exclude those locations before injection.
- Fallback behavior: when Rubin-native PSF evaluation cannot be used, the injection code can fall back to the GalSim-based PSF approximation path.

This keeps throughput studies aligned with Rubin's local PSF model while still exposing where the PSF was marked inexact or edge-affected.
