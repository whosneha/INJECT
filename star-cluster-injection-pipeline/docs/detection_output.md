# INJECT Pipeline — Expected Output Reference

## Pipeline Flow

```
Real Image (deepCoadd)
        ↓
inject_clusters_galsim()
        ↓
Injected Image  +  injection_info (list of dicts)
        ↓
YOUR detection pipeline
        ↓
detections (list of dicts)
        ↓
ClusterRetrieval.match_detections()
        ↓
Completeness Curves + Recovery Plots
```

---

## 1. injection_info — What the Injector Produces

After running `inject_clusters_galsim()` you get `injection_info`,
a list of dicts with one entry per successfully injected cluster.

```python
injection_info = [
    {
        # ── Position ──────────────────────────────────────────────────
        'x':              142.3,    # float  — injected centroid x (pixels)
        'y':              876.1,    # float  — injected centroid y (pixels)

        # ── Photometry ────────────────────────────────────────────────
        'magnitude':       22.3,    # float  — injected apparent magnitude
        'flux':          1234.5,    # float  — total flux in image units
        'total_flux':    1234.5,    # float  — same as flux (for cross-check)
        'stamp_flux':    1230.1,    # float  — actual sum of drawn stamp

        # ── Morphology ────────────────────────────────────────────────
        'r_half':           4.2,    # float  — half-light radius (pixels)
        'concentration':   15.0,    # float  — King c = r_t/r_c
                                    #          EFF gamma, or Sersic n

        # ── Profile ───────────────────────────────────────────────────
        'profile_type':  'king',    # str    — 'king','plummer','eff','sersic'
        'method':        'smooth',  # str    — 'smooth' or 'discrete'

        # ── Metadata ──────────────────────────────────────────────────
        'id':                 0,    # int    — cluster index
        'age_gyr':          1.0,    # float  — stellar population age (Gyr)

        # ── The stamp itself ──────────────────────────────────────────
        'stamp': np.ndarray,        # 2D array — PSF-convolved stamp
                                    #            shape: (stamp_size, stamp_size)
    },
    # ... one dict per injected cluster
]
```

---

## 2. detections — What YOUR Detection Pipeline Must Produce

This is the format your detection pipeline must output.
Pass it directly to `ClusterRetrieval`.

```python
detections = [
    {
        # ── REQUIRED (pipeline will fail without these) ────────────────
        'x':            142.3,    # float  — detected centroid x (pixels)
        'y':            876.1,    # float  — detected centroid y (pixels)

        # ── OPTIONAL: unlocks completeness vs magnitude ────────────────
        'flux':        1234.5,    # float  — measured total flux
        'magnitude':     22.3,    # float  — measured apparent magnitude

        # ── OPTIONAL: unlocks completeness vs size ─────────────────────
        'r_half':         4.2,    # float  — measured half-light radius (pixels)
        'ellipticity':   0.12,    # float  — ellipticity (0=circular, 1=line)

        # ── OPTIONAL: unlocks completeness vs SNR ──────────────────────
        'snr':            8.4,    # float  — peak signal-to-noise ratio

        # ── OPTIONAL: quality control ──────────────────────────────────
        'flag':             0,    # int    — 0=good, anything else=bad
        'area':            45,    # int    — footprint area in pixels²
    },
    # ... one dict per detected source
]
```

---

## 3. What Each Optional Key Unlocks

| Key | Type | Unlocks |
|---|---|---|
| `x`, `y` | float, **required** | Spatial matching to injections |
| `magnitude` | float | Completeness vs magnitude curve |
| `r_half` | float | Completeness vs half-light radius curve |
| `magnitude` + `r_half` | both | 2D completeness map |
| `snr` | float | Completeness vs SNR curve |
| `flux` | float | Flux recovery / photometric offset plots |
| `ellipticity` | float | Morphology recovery plots |
| `flag` | int | Automatic quality filtering |
| `area` | int | Size cross-check plots |

---

## 4. Retrieval Summary — Expected Output

```
=== Retrieval Summary ===
  Injected         : 100
  Recovered        : 55
  Missed           : 45
  Completeness     : 55.0%
  50% mag limit    : 23.91
  50% size limit   : 7.19 px

=== Photometric Accuracy ===
  Mean mag offset  : -0.252 mag    ← negative = underestimating flux
  Std  mag offset  :  0.392 mag
```

---

## 5. Completeness Plots — Expected Output

### 5a — Completeness vs Magnitude
```
Completeness
1.0 ┤████████████
0.9 ┤            ██████
0.8 ┤                  ████
0.5 ┤- - - - - - - - - - - -★- - -  ← 50% limit ~ mag 23.9
0.2 ┤                          ████
0.0 ┤                              ████
    └────────────────────────────────────
    20    21    22    23    24    25    26
                  Magnitude
```
Bright clusters (low mag) → high completeness ~100%
Faint clusters (high mag) → completeness drops to 0%

### 5b — Completeness vs Half-light Radius
```
Completeness
1.0 ┤████████████
0.8 ┤            ████
0.5 ┤- - - - - - - -★- - -  ← 50% limit ~ 7.2 px
0.2 ┤                  ████
0.0 ┤                      ████
    └────────────────────────────
    2    4    6    8    10
         Half-light Radius (px)
```
Compact clusters (small r_half) → easier to detect
Extended clusters (large r_half) → harder to detect (surface brightness drops)

### 5c — 2D Completeness Map
```
r_half │  mag=21  mag=22  mag=23  mag=24  mag=25
───────┼──────────────────────────────────────────
10 px  │  100%     95%     70%     30%      5%
 7 px  │  100%     98%     80%     45%     10%
 5 px  │  100%    100%     90%     60%     20%
 3 px  │  100%    100%     95%     75%     35%
 2 px  │  100%    100%     98%     85%     50%
```
Green = recovered, Red = missed

---

## 6. Quick Validation Checklist

Before passing detections to `ClusterRetrieval`, verify:

- [ ] `detections` is a `list`
- [ ] Each element is a `dict`
- [ ] Every dict has `'x'` and `'y'` as floats in pixel coordinates
- [ ] `x` and `y` are in the same coordinate system as the injected image
- [ ] (optional) `magnitude` is in the same zero-point system (default ZP=27.0)
- [ ] (optional) `r_half` is in **pixels**, not arcseconds
- [ ] (optional) `flag == 0` means good detection

```python
# Run this to verify your catalog before passing to ClusterRetrieval
from detection_output_format import validate_detections
validate_detections(your_detections)
```