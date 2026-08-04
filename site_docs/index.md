# Star Cluster Injection Pipeline

<div class="hero">
  <div class="hero-kicker">Documentation</div>
  <h1>Star Cluster Injection Pipeline</h1>
  <p>Install the package, run injection-recovery experiments, compare detection behavior, and document completeness in a reproducible way.</p>
  <a class="hero-btn" href="getting-started/installation/">Installation</a>
</div>

## What is INJECT?
- INJECT is a Rubin/LSST-oriented injection pipeline for artificial star clusters.
- It supports both smooth light-profile injections and discrete-star cluster generation.
- It is built for injection-recovery science: generate a truth catalog, inject into data, run your detector, and measure recovery or completeness as a function of the parameters you care about.
- It is intentionally customizable so users can vary profile family, magnitude range, size range, PSF behavior, band selection, batching strategy, and downstream detection logic.

## Pipeline Overview

<figure class="flowchart-figure">
  <img src="assets/flowchart.svg" alt="Pipeline flowchart showing Rubin images, synthetic cluster catalog, detection, and outputs" />
</figure>

## What Users Usually Do

- Use TAP-mode cutouts from a local or non-RSP environment for lightweight runs.
- Treat that TAP/local path as the main easy-entry workflow; it uses fallback PSF handling rather than Rubin-native PSF computation.
- Follow the simple single-run workflow shown in `simple_rubin_mci_demo.ipynb`.
- Follow the pooled repeated-run workflow shown in `simple_batch_injection_demo.ipynb`.
- Use Butler/RSP mode for higher-fidelity PSF-aware runs on Rubin infrastructure.
- Save configuration snapshots and outputs so science comparisons stay reproducible.

## Who This Is For

- Astronomers prototyping injection-recovery studies and completeness measurements.
- Pipeline developers building reproducible simulation workflows.
- Collaborators who need notebook-first examples and script automation.

## Doesn't Rubin already have an INJECT tool?

- Rubin already includes injection tooling, including visit-level pipeline workflows.
- This project is best understood as a complementary cluster-injection and benchmarking package with a notebook-friendly Python API.
- The main differentiators here are profile choice, discrete-star generation, parameter sweeps, multiband experimentation, and user-controlled downstream benchmarking.
- This project also makes it easier to plug in your own detection method and evaluate recovery with your own science-driven measurement choices.

## Scope Notes

- The packaged Rubin-facing workflow in this repo is coadd-first.
- Single-band and multiband workflows are both supported.
- Users can inject into arbitrary 2D image arrays through the Python API.
- Native Butler-backed single-visit loading is not yet implemented as a first-class packaged workflow.

## Quick Links

- [Installation](getting-started/installation.md)
- [Quickstart](getting-started/quickstart.md)
- [Use Cases](guides/use-cases.md)
- [Customization](guides/customization.md)
- [Pipeline Workflows](guides/pipeline-workflows.md)
- [Deployment](guides/deployment.md)
- [PSF Caching and Performance](guides/psf-caching.md)
