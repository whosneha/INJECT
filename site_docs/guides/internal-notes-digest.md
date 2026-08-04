# Internal Notes Digest

This page summarizes important points from the project-internal markdown notes so they are visible in the website navigation.

## Detection Output Notes

- Keep detection artifacts saved with run metadata.
- Preserve enough detail to audit matching logic and threshold choices.
- Maintain stable output schema across experiments.

## PSF Caching Notes

- Cache warm-up behavior is expected in early iterations.
- Throughput gains improve as repeated PSF lookups accumulate.
- Cache grid and size should be tuned against science tolerance and memory limits.

## Workplan Highlights

- Continue integrating robust detection/retrieval evaluation.
- Expand reproducible benchmark coverage.
- Keep notebook examples aligned with production APIs.

## Recommendation

When project notes evolve, copy key conclusions into this page so docs users do not need to inspect internal planning files.
