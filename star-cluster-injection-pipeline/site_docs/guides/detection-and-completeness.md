# Detection and Completeness

Injection-only metrics are not enough; the full science loop is injection plus recovery.

## Detection Stage

After injecting clusters, run your detector and store candidate catalogs with clear schema:

- ID (if available)
- Pixel coordinates
- Flux or magnitude estimate
- Quality flags / SNR

## Truth Matching

Match detections against injected truth entries using configurable radius and quality filters.

Recommended logging:

- Match radius used
- Ambiguous matches count
- Unmatched injection count
- Unmatched detection count

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

## Validation Checklist

1. Confirm enough injections per bin.
2. Verify detector threshold consistency across runs.
3. Test sensitivity to matching radius.
4. Document all cuts before comparison.
