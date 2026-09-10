# Overleaf Materials

This folder contains Overleaf-ready LaTeX documentation for the INJECT project.

## Files

- `inject_science_overview.tex`: science-use-case and pipeline overview document for collaborators, proposals, methods notes, or paper planning.

## How To Use In Overleaf

1. Create a new blank Overleaf project.
2. Upload `inject_science_overview.tex`.
3. Set it as the main document if Overleaf does not do so automatically.
4. Compile with pdfLaTeX.

The LaTeX document is intentionally self-contained. It does not depend on local figures, notebooks, or MkDocs assets.

## Relationship To Read The Docs

The public documentation site is built from `site_docs/` with MkDocs and configured by `.readthedocs.yaml`. This Overleaf document is separate from the Read the Docs site unless you explicitly add the generated PDF or source file to `site_docs/` and link it from the MkDocs navigation.