#!/usr/bin/env python3
"""
CANFAR/CADC batch runner for the canonical workflow:
10 iterations x 1000 injections per iteration, with user detector hook,
then combined recovery/completeness summary across all iterations.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

try:
    import yaml
except ImportError:
    yaml = None

# Ensure project root is importable when run as script
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config import ClusterConfig, InjectionConfig
from src.data_access import RubinDataAccess, HAS_LSST
from src.pipeline import InjectionPipeline
from src.retrieval import ClusterRetrieval


def parse_json_dict(text: str | Dict[str, Any] | None) -> Dict[str, Any]:
    if not text:
        return {}
    if isinstance(text, dict):
        return text
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("--detector-kwargs must decode to a JSON object")
    return value


def load_config_file(path: str | None) -> Dict[str, Any]:
    if not path:
        return {}

    cfg_path = Path(path).expanduser().resolve()
    suffix = cfg_path.suffix.lower()

    with open(cfg_path, "r", encoding="utf-8") as f:
        if suffix == ".json":
            cfg = json.load(f)
        elif suffix in (".yaml", ".yml"):
            if yaml is None:
                raise RuntimeError("YAML config requested but PyYAML is not installed")
            cfg = yaml.safe_load(f)
        else:
            raise ValueError("Config file must be .json, .yaml, or .yml")

    if not isinstance(cfg, dict):
        raise ValueError("Config file must contain a top-level object")
    return cfg


def collect_cli_overrides(argv: List[str]) -> set[str]:
    """Collect CLI flags explicitly provided by user (for config precedence)."""
    provided = set()
    for token in argv:
        if not token.startswith("--"):
            continue
        key = token[2:].split("=", 1)[0].replace("-", "_")
        provided.add(key)
    return provided


def apply_config_defaults(args, cfg: Dict[str, Any], cli_overrides: set[str]) -> None:
    """Apply config values only where CLI did not explicitly provide a value."""
    for key, value in cfg.items():
        norm_key = key.replace("-", "_")
        if not hasattr(args, norm_key):
            continue
        if norm_key in cli_overrides:
            continue
        setattr(args, norm_key, value)


def load_callable(spec: str) -> Callable:
    """Load callable from 'module.submodule:function_name'."""
    if ":" not in spec:
        raise ValueError("Detector spec must be 'module:function'")
    module_name, fn_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    fn = getattr(module, fn_name, None)
    if fn is None or not callable(fn):
        raise ValueError(f"Could not load callable '{fn_name}' from '{module_name}'")
    return fn


def normalize_detections(raw: Any) -> List[Dict[str, Any]]:
    """Normalize detector output to list[dict] with x,y keys."""
    if raw is None:
        return []

    if isinstance(raw, list):
        dets = raw
    elif hasattr(raw, "to_dict"):
        try:
            dets = raw.to_dict(orient="records")
        except TypeError:
            dets = raw.to_dict("records")
    else:
        raise TypeError("Detector must return list[dict] or a DataFrame-like object")

    out = []
    for d in dets:
        if not isinstance(d, dict):
            continue
        if "x" in d and "y" in d:
            out.append(d)
        elif "xcentroid" in d and "ycentroid" in d:
            c = dict(d)
            c["x"] = c["xcentroid"]
            c["y"] = c["ycentroid"]
            out.append(c)
    return out


def write_rows_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    """Write list[dict] to CSV using only standard library."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("")
        return

    fieldnames = sorted({k for row in rows for k in row.keys()})
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_detector(detector_spec: str, detector_kwargs: Dict[str, Any], psf_fwhm: float) -> Callable:
    detector = load_callable(detector_spec)
    sig = inspect.signature(detector)
    takes_psf_fwhm = "psf_fwhm" in sig.parameters

    def _wrapped(image):
        kwargs = dict(detector_kwargs)
        if takes_psf_fwhm:
            kwargs["psf_fwhm"] = psf_fwhm
        raw = detector(image, **kwargs)
        return normalize_detections(raw)

    return _wrapped


def resolve_token(args) -> str | None:
    if args.token:
        return args.token
    if args.token_env:
        return os.environ.get(args.token_env)
    return None


def parse_args():
    parser = argparse.ArgumentParser(
        description="CANFAR batch workflow: 10x1000 injections + user detector + combined summary"
    )

    parser.add_argument(
        "--config-file",
        default="",
        help="Optional JSON/YAML config file. CLI flags override file values.",
    )

    # Workflow defaults requested by user
    parser.add_argument("--n-iterations", type=int, default=10)
    parser.add_argument("--n-per-iter", type=int, default=1000)
    parser.add_argument("--n-workers", type=int, default=4)

    # Detector hook
    parser.add_argument(
        "--detector-spec",
        default="src.detection:run_cluster_detection",
        help="Python callable as module:function",
    )
    parser.add_argument(
        "--detector-kwargs",
        default="",
        help="JSON object of kwargs passed to detector function",
    )

    # Injection parameters
    parser.add_argument("--profile", default="plummer", choices=["plummer", "king", "eff", "sersic"])
    parser.add_argument("--method", default="smooth", choices=["smooth", "discrete"])
    parser.add_argument("--mag-min", type=float, default=20.0)
    parser.add_argument("--mag-max", type=float, default=24.0)
    parser.add_argument("--r-half-min", type=float, default=3.0)
    parser.add_argument("--r-half-max", type=float, default=20.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--band", default="i")
    parser.add_argument("--no-noise", action="store_true")

    # Data access
    parser.add_argument("--mode", default="auto", choices=["auto", "rsp", "tap", "mock"])
    parser.add_argument("--repo", type=str, default=None)
    parser.add_argument("--collection", type=str, default=None)
    parser.add_argument("--tract", type=int, default=None)
    parser.add_argument("--patch", type=int, default=None)

    parser.add_argument("--token", type=str, default=None)
    parser.add_argument("--token-env", type=str, default="RUBIN_TOKEN")
    parser.add_argument("--ra", type=float, default=None)
    parser.add_argument("--dec", type=float, default=None)
    parser.add_argument("--size", type=float, default=120.0)

    # Output
    parser.add_argument("--output-dir", default="canfar_outputs/batch_10x1000")
    parser.add_argument("--checkpoint-dir", default="")
    parser.add_argument("--match-radius", type=float, default=5.0)
    parser.add_argument("--dry-run", action="store_true")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg_file_values = load_config_file(args.config_file)
    cli_overrides = collect_cli_overrides(sys.argv[1:])
    apply_config_defaults(args, cfg_file_values, cli_overrides)

    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_dir = args.checkpoint_dir.strip()
    if checkpoint_dir:
        checkpoint_path = Path(checkpoint_dir).expanduser().resolve()
    else:
        checkpoint_path = out_dir / "iterations"
    checkpoint_path.mkdir(parents=True, exist_ok=True)

    det_kwargs = parse_json_dict(args.detector_kwargs)

    token = resolve_token(args)
    mode = args.mode

    if mode == "mock":
        data_access = None
        image = None
        metadata = {"psf_fwhm_pixels": 3.5, "mode": "mock"}
    else:
        auto_mode = mode
        if auto_mode == "auto" and (not HAS_LSST) and token is not None:
            auto_mode = "tap"

        if auto_mode == "tap" and token is None:
            raise RuntimeError("TAP mode requires --token or token env var")

        data_access = RubinDataAccess(
            mode=auto_mode,
            token=token,
            repo=args.repo,
            collection=args.collection,
        )

        if data_access.mode == "rsp":
            if args.tract is None or args.patch is None:
                raise RuntimeError("RSP mode requires --tract and --patch")
            image, metadata = data_access.load_coadd(
                data_id={"tract": args.tract, "patch": args.patch, "band": args.band}
            )
        elif data_access.mode == "tap":
            if args.ra is None or args.dec is None:
                raise RuntimeError("TAP mode requires --ra and --dec")
            image, metadata = data_access.load_coadd(
                ra=args.ra,
                dec=args.dec,
                size_arcsec=args.size,
                band=args.band,
            )
        else:
            raise RuntimeError(f"Unsupported data access mode: {data_access.mode}")

    if image is None:
        import numpy as np

        np.random.seed(args.seed)
        image = np.random.normal(loc=100.0, scale=15.0, size=(500, 500))

    if data_access is not None:
        psf_fwhm = float(data_access.get_psf_fwhm(metadata))
    else:
        psf_fwhm = float(metadata.get("psf_fwhm_pixels", 3.5))

    cluster_cfg = ClusterConfig(
        profile_type=args.profile,
        method=args.method,
        mag_min=args.mag_min,
        mag_max=args.mag_max,
        r_half_min=args.r_half_min,
        r_half_max=args.r_half_max,
    )
    cfg = InjectionConfig(
        run_name="canfar_10x1000",
        band=args.band,
        n_clusters=args.n_per_iter,
        seed=args.seed,
        add_noise=not args.no_noise,
        use_actual_psf=(data_access is not None and metadata.get("mode") == "rsp"),
        psf_fwhm_fallback=psf_fwhm,
        output_dir=str(out_dir),
        cluster_config=cluster_cfg,
    )

    detector_fn = build_detector(args.detector_spec, det_kwargs, psf_fwhm)

    psf_obj = metadata.get("psf") if isinstance(metadata, dict) else None
    bbox = metadata.get("bbox") if isinstance(metadata, dict) else None
    bbox_x = bbox.getMinX() if bbox is not None else 0
    bbox_y = bbox.getMinY() if bbox is not None else 0

    run_info = {
        "mode": metadata.get("mode") if isinstance(metadata, dict) else "mock",
        "n_iterations": args.n_iterations,
        "n_per_iter": args.n_per_iter,
        "n_workers": args.n_workers,
        "detector_spec": args.detector_spec,
        "detector_kwargs": det_kwargs,
        "psf_fwhm_pixels": psf_fwhm,
        "output_dir": str(out_dir),
        "checkpoint_dir": str(checkpoint_path),
        "band": args.band,
    }

    if args.dry_run:
        print(json.dumps(run_info, indent=2))
        return 0

    pipe = InjectionPipeline(cfg)
    pipe.load_data(image=image)

    iterations = pipe.run_batch(
        n_iterations=args.n_iterations,
        n_per_iter=args.n_per_iter,
        psf_obj=psf_obj,
        bbox_x_min=bbox_x,
        bbox_y_min=bbox_y,
        psf_fwhm_fallback=psf_fwhm,
        detector_fn=detector_fn,
        checkpoint_dir=str(checkpoint_path),
        n_workers=args.n_workers,
        use_psf_cache=True,
        psf_cache_grid=8,
        psf_cache_size=2000,
        band=args.band,
        verbose=True,
    )

    # Combined analysis across all iterations (same as notebook pooling pattern)
    retrieval = ClusterRetrieval(pipe.injection_info, pipe.detection_catalog)
    retrieval.match_detections(match_radius=args.match_radius)
    summary = retrieval.get_summary_statistics()

    per_iter_rows = []
    for it in iterations:
        inj = it.get("injection_info", [])
        det = it.get("detections", [])
        ret_it = ClusterRetrieval(inj, det)
        ret_it.match_detections(match_radius=args.match_radius)
        stats_it = ret_it.get_summary_statistics()
        per_iter_rows.append(
            {
                "iteration": it.get("iteration"),
                "n_injected": stats_it.get("n_injected"),
                "n_detected": stats_it.get("n_detected"),
                "overall_completeness": stats_it.get("overall_completeness"),
            }
        )

    write_rows_csv(pipe.injection_info, out_dir / "combined_injection_info.csv")
    write_rows_csv(pipe.detection_catalog, out_dir / "combined_detections.csv")
    write_rows_csv(per_iter_rows, out_dir / "per_iteration_summary.csv")

    payload = {
        "run": run_info,
        "summary": summary,
        "totals": {
            "n_iterations_completed": len(iterations),
            "n_injected_total": len(pipe.injection_info),
            "n_detected_total": len(pipe.detection_catalog),
        },
    }
    with open(out_dir / "combined_summary.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("\nSaved:")
    print(f"  - {out_dir / 'combined_injection_info.csv'}")
    print(f"  - {out_dir / 'combined_detections.csv'}")
    print(f"  - {out_dir / 'per_iteration_summary.csv'}")
    print(f"  - {out_dir / 'combined_summary.json'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
