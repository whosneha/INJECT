# Two-Month Workplan

This plan is tailored to the current star-cluster injection pipeline, with emphasis on rigorous validation, clearer documentation, and a few high-value improvements that should make the project easier to trust, use, and extend.

## Goals

1. Increase confidence in scientific correctness.
2. Make the pipeline easier to run, understand, and reproduce.
3. Improve notebook and document quality so results are easier to share.
4. Add targeted enhancements that reduce runtime friction without expanding scope too much.

## Priority Areas

### 1. Rigorous testing

- Expand unit tests for light profiles, PSF convolution, catalog generation, and I/O.
- Add integration tests for full injection and detection flows.
- Add regression tests for known edge cases and failure modes.
- Add reproducibility checks for seeded catalog generation and batch runs.
- Add multiband consistency tests if multiband workflows are part of the intended use case.
- Add performance smoke tests for PSF caching and batch execution.

### 2. Documentation

- Clean up the main README so setup, usage, and expected outputs are easy to find.
- Add a short “quick start” path for notebook users.
- Document the batch pipeline, checkpoints, cache settings, and multiband behavior.
- Add a testing guide that explains how to run unit, integration, and visual verification tests.
- Improve inline notebook narration so the demo notebooks read like a workflow, not just a sequence of cells.

### 3. Useful improvements

- Add CI-friendly test execution if not already present.
- Standardize outputs and file naming for saved catalogs, checkpoints, and plots.
- Add lightweight benchmarking scripts or notebooks for PSF caching and end-to-end runtime.
- Improve validation around input images, catalog bounds, and configuration values.
- Add clearer logging and summary stats for batch runs.

## Eight-Week Plan

### Weeks 1-2: Baseline and test foundation

- Audit existing tests and identify the highest-risk gaps.
- Add or tighten unit tests around:
  - `mag_to_flux` and magnitude/flux scaling.
  - profile normalization and symmetry.
  - PSF convolution flux conservation.
  - catalog generation bounds and seeded reproducibility.
- Convert any ad hoc verification into repeatable assertions.
- Decide which visual checks should remain manual and which can become automated.

Deliverable:
- A more reliable test suite that can catch basic scientific and numerical regressions.

### Weeks 3-4: Integration and regression testing

- Add end-to-end tests for single-band injection and detection.
- Add tests that cover no-PSF, fallback-PSF, and cache-enabled modes.
- Add regression tests for previously observed bugs or fragile behavior.
- Add tests for edge cases such as:
  - injections near image boundaries,
  - very faint clusters,
  - very compact or very extended profiles,
  - empty or tiny catalogs.
- If multiband work matters, add a test that verifies the same catalog is applied consistently across bands.

Deliverable:
- A test layer that exercises the actual pipeline behavior, not just isolated math.

### Weeks 5-6: Documentation and workflow polish

- Rewrite or expand the main README for:
  - installation,
  - quick start,
  - notebook usage,
  - batch execution,
  - outputs and checkpoints.
- Add a concise developer guide for running tests and understanding the repo structure.
- Update notebook introductions and final summary cells so each notebook states:
  - what it demonstrates,
  - what input data it expects,
  - what outputs to inspect,
  - what limitations remain.
- Clarify performance notes for PSF caching and batch execution.

Deliverable:
- A repo that is easier for a new user to pick up without asking for oral context.

### Weeks 7-8: Targeted enhancements and cleanup

- Add a small benchmarking workflow for before/after comparisons.
- Improve logging and run summaries so long batch jobs are easier to monitor.
- Tighten config validation and error messages.
- Standardize plot and result outputs where that reduces confusion.
- Revisit any notebook or script that still feels too manual and reduce repetitive steps.

Deliverable:
- A more polished and maintainable pipeline with better diagnostics and fewer workflow surprises.

## Stretch Ideas

If time remains after the core work, these are the best next candidates:

- CI automation for tests and notebook smoke checks.
- A small synthetic benchmark dataset for stable regression testing.
- A results summary report that combines completeness curves, detection statistics, and PSF-cache performance.
- A lightweight API cleanup pass so the pipeline interface is easier to use from notebooks and scripts.
- A short tutorial notebook focused on one canonical end-to-end use case.

## Success Criteria

By the end of two months, the project should have:

- Stronger test coverage over the pipeline’s most important behaviors.
- Clearer documentation for new and returning users.
- Better reproducibility and fewer manual steps.
- At least one measurable improvement in usability, diagnostics, or runtime workflow.

## Suggested Weekly Rhythm

- Monday: review priorities, test failures, and open questions.
- Midweek: implement and validate the highest-value change.
- Friday: update docs, run the full relevant test slice, and record what changed.

## Notes

- Keep validation close to the code that changed.
- Prefer repeatable tests over notebook-only verification when possible.
- Avoid widening scope unless a test or benchmark shows a real need.