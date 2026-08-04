"""Console entry point for the packaged Star Cluster Injection Pipeline."""

import argparse
import json
import os


def build_parser():
    """Create the CLI parser used by the packaged entry point."""
    parser = argparse.ArgumentParser(
        description="Inject synthetic star clusters into Rubin/LSST imaging.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  injection-pipeline --n-clusters 25 --band i --profile plummer
  injection-pipeline --token YOUR_TOKEN --ra 55.0 --dec -30.0 --band i
  injection-pipeline --repo /repo/main --collection MY/COLLECTION --tract 9615 --patch 30
        """.strip(),
    )

    parser.add_argument("--n-clusters", type=int, default=10, help="Number of clusters to inject")
    parser.add_argument("--band", default="i", help="Filter band (u,g,r,i,z,y)")
    parser.add_argument(
        "--profile",
        default="plummer",
        choices=["plummer", "king", "eff", "sersic"],
        help="Light profile type",
    )
    parser.add_argument("--mag-min", type=float, default=20.0, help="Minimum magnitude")
    parser.add_argument("--mag-max", type=float, default=24.0, help="Maximum magnitude")
    parser.add_argument("--r-half-min", type=float, default=3.0, help="Minimum half-light radius")
    parser.add_argument("--r-half-max", type=float, default=20.0, help="Maximum half-light radius")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--no-noise", action="store_true", help="Disable Poisson noise")
    parser.add_argument(
        "--method",
        default="smooth",
        choices=["smooth", "discrete"],
        help="Cluster generation method",
    )
    parser.add_argument("--n-stars-min", type=int, default=50, help="Minimum stars per cluster")
    parser.add_argument("--n-stars-max", type=int, default=500, help="Maximum stars per cluster")
    parser.add_argument(
        "--imf",
        default="kroupa",
        choices=["kroupa", "chabrier", "salpeter"],
        help="Initial mass function for discrete mode",
    )
    parser.add_argument("--repo", type=str, help="Butler repository path")
    parser.add_argument("--collection", type=str, help="Butler collection name")
    parser.add_argument("--tract", type=int, help="Tract number")
    parser.add_argument("--patch", type=int, help="Patch number")
    parser.add_argument("--token", type=str, help="Rubin access token for TAP mode")
    parser.add_argument("--ra", type=float, help="Center RA in degrees for TAP mode")
    parser.add_argument("--dec", type=float, help="Center Dec in degrees for TAP mode")
    parser.add_argument("--size", type=float, default=120, help="Cutout size in arcseconds")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Directory for saved figures and catalog outputs",
    )
    parser.add_argument("--version", action="store_true", help="Print package version and exit")
    return parser


def _resolve_output_dir(path):
    output_dir = os.path.abspath(path)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def _load_image_and_metadata(args):
    import numpy as np
    from src.data_access import HAS_LSST, RubinDataAccess

    if args.token is not None:
        mode = "tap"
        data_access = RubinDataAccess(mode="tap", token=args.token)
        if args.ra is None or args.dec is None:
            raise SystemExit("TAP mode requires --ra and --dec.")
        image, metadata = data_access.load_coadd(
            ra=args.ra,
            dec=args.dec,
            size_arcsec=args.size,
            band=args.band,
        )
        location = f"RA={args.ra:.4f}, Dec={args.dec:.4f}"
    elif HAS_LSST and args.repo is not None:
        mode = "rsp"
        data_access = RubinDataAccess(mode="rsp", repo=args.repo, collection=args.collection)
        if args.tract is None or args.patch is None:
            raise SystemExit("RSP mode requires --tract and --patch.")
        image, metadata = data_access.load_coadd(
            data_id={"tract": args.tract, "patch": args.patch, "band": args.band}
        )
        location = f"tract={args.tract}, patch={args.patch}"
    elif HAS_LSST and args.tract is not None and args.patch is not None:
        mode = "rsp"
        data_access = RubinDataAccess(mode="rsp")
        image, metadata = data_access.load_coadd(
            data_id={"tract": args.tract, "patch": args.patch, "band": args.band}
        )
        location = f"tract={args.tract}, patch={args.patch}"
    else:
        mode = "mock"
        data_access = None
        np.random.seed(args.seed)
        image = np.random.normal(loc=100.0, scale=15.0, size=(500, 500))
        metadata = {"psf_fwhm_pixels": 3.5, "mode": "mock"}
        location = "mock data"

    return mode, data_access, image, metadata, location


def _write_outputs(output_dir, image, injected_image, catalog, injection_info, metadata):
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import LogNorm

    vmin, vmax = np.percentile(image, [1, 99])
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    axes[0].imshow(image, cmap="gray", origin="lower", vmin=vmin, vmax=vmax)
    axes[0].set_title("Original image")

    axes[1].imshow(injected_image, cmap="gray", origin="lower", vmin=vmin, vmax=vmax)
    axes[1].set_title("Injected image")
    for entry in catalog:
        axes[1].scatter(
            entry["x"],
            entry["y"],
            s=80,
            facecolors="none",
            edgecolors="red",
            linewidth=1.2,
        )

    diff = np.maximum(injected_image - image, 0.1)
    im = axes[2].imshow(diff, cmap="hot", origin="lower", norm=LogNorm(vmin=0.1, vmax=diff.max()))
    axes[2].set_title("Injection-only signal")
    plt.colorbar(im, ax=axes[2], label="Flux")

    for axis in axes:
        axis.set_xlabel("X (pixels)")
        axis.set_ylabel("Y (pixels)")

    fig.tight_layout()
    figure_path = os.path.join(output_dir, "injection_result.png")
    fig.savefig(figure_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    catalog_path = os.path.join(output_dir, "injection_catalog.json")
    with open(catalog_path, "w", encoding="utf-8") as handle:
        json.dump({"metadata": metadata, "catalog": injection_info}, handle, indent=2, default=float)

    return figure_path, catalog_path


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        from star_cluster_injection import __version__

        print(__version__)
        return 0

    output_dir = _resolve_output_dir(args.output_dir)
    mode, data_access, image, metadata, location = _load_image_and_metadata(args)
    from src.inject import create_injection_catalog, inject_from_catalog

    psf_fwhm = metadata.get("psf_fwhm_pixels", 3.5)
    if data_access is not None:
        psf_fwhm = data_access.get_psf_fwhm(metadata)

    catalog = create_injection_catalog(
        n_clusters=args.n_clusters,
        image_shape=image.shape,
        mag_range=(args.mag_min, args.mag_max),
        r_half_range=(args.r_half_min, args.r_half_max),
        profile_type=args.profile,
        method=args.method,
        n_stars_range=(args.n_stars_min, args.n_stars_max),
        imf=args.imf,
        edge_buffer=50,
        seed=args.seed,
    )

    injected_image, injection_info = inject_from_catalog(
        image,
        catalog,
        psf_fwhm=psf_fwhm,
        exposure=metadata.get("exposure") if mode == "rsp" else None,
        add_noise=not args.no_noise,
    )

    run_metadata = {
        "mode": mode,
        "band": args.band,
        "image_shape": list(image.shape),
        "psf_fwhm_pixels": float(psf_fwhm),
        "n_clusters": args.n_clusters,
        "location": location,
        "profile_type": args.profile,
        "method": args.method,
    }
    figure_path, catalog_path = _write_outputs(
        output_dir,
        image,
        injected_image,
        catalog,
        injection_info,
        run_metadata,
    )

    print(f"Mode: {mode}")
    print(f"Location: {location}")
    print(f"Saved figure: {figure_path}")
    print(f"Saved catalog: {catalog_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
