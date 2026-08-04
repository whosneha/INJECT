#!/usr/bin/env python3
"""
Launch task-based injection jobs for CANFAR/CADC compute nodes.

This script reads a JSON task list and executes one task by index by
calling scripts/run_injection.py with the corresponding arguments.

Typical use on HTCondor:
  python scripts/canfar_run_tasks.py \
    --tasks-file configs/canfar_tasks.json \
    --task-index "$JOB_INDEX" \
    --output-root "$PWD/canfar_outputs"
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _build_base_command(repo_root: Path) -> list[str]:
    run_script = repo_root / "scripts" / "run_injection.py"
    return [sys.executable, str(run_script)]


def _add_arg(cmd: list[str], flag: str, value) -> None:
    if value is None:
        return
    cmd.extend([flag, str(value)])


def _task_name(task: dict, idx: int) -> str:
    raw = task.get("name", f"task_{idx:04d}")
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in raw)
    return safe or f"task_{idx:04d}"


def build_command(repo_root: Path, task: dict, output_dir: Path, dry_run: bool = False) -> list[str]:
    cmd = _build_base_command(repo_root)

    # Common injection arguments
    _add_arg(cmd, "--n-clusters", task.get("n_clusters", 10))
    _add_arg(cmd, "--band", task.get("band", "i"))
    _add_arg(cmd, "--profile", task.get("profile", "plummer"))
    _add_arg(cmd, "--method", task.get("method", "smooth"))
    _add_arg(cmd, "--mag-min", task.get("mag_min", 20.0))
    _add_arg(cmd, "--mag-max", task.get("mag_max", 24.0))
    _add_arg(cmd, "--r-half-min", task.get("r_half_min", 3.0))
    _add_arg(cmd, "--r-half-max", task.get("r_half_max", 20.0))
    _add_arg(cmd, "--seed", task.get("seed", 42))
    _add_arg(cmd, "--n-stars-min", task.get("n_stars_min", 50))
    _add_arg(cmd, "--n-stars-max", task.get("n_stars_max", 500))
    _add_arg(cmd, "--imf", task.get("imf", "kroupa"))

    if bool(task.get("no_noise", False)):
        cmd.append("--no-noise")

    mode = str(task.get("mode", "auto")).lower()

    if mode == "tap":
        # Use token from env var by default for safer secret handling.
        token_env = task.get("token_env", "RUBIN_TOKEN")
        token_value = os.environ.get(token_env)
        if not token_value and not dry_run:
            raise RuntimeError(
                f"TAP task requires token in environment variable {token_env}."
            )
        if not token_value and dry_run:
            token_value = "DRY_RUN_TOKEN_PLACEHOLDER"
        _add_arg(cmd, "--token", token_value)
        _add_arg(cmd, "--ra", task.get("ra"))
        _add_arg(cmd, "--dec", task.get("dec"))
        _add_arg(cmd, "--size", task.get("size", 120))

    elif mode == "rsp":
        _add_arg(cmd, "--repo", task.get("repo"))
        _add_arg(cmd, "--collection", task.get("collection"))
        _add_arg(cmd, "--tract", task.get("tract"))
        _add_arg(cmd, "--patch", task.get("patch"))

    elif mode in ("auto", "mock"):
        # For auto/mock, run_injection.py handles fallback behavior.
        pass
    else:
        raise ValueError(f"Unsupported task mode: {mode}")

    _add_arg(cmd, "--output-dir", output_dir)
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one CANFAR injection task by index")
    parser.add_argument("--tasks-file", required=True, help="JSON file with task list")
    parser.add_argument("--task-index", type=int, required=True, help="0-based task index")
    parser.add_argument(
        "--output-root",
        default="canfar_outputs",
        help="Root directory where task output folders are created",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print command only, do not execute",
    )

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    tasks_path = Path(args.tasks_file).expanduser().resolve()
    with open(tasks_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, dict):
        tasks = payload.get("tasks", [])
    elif isinstance(payload, list):
        tasks = payload
    else:
        raise ValueError("Tasks file must contain a list or a dict with key 'tasks'.")

    if not tasks:
        raise ValueError("No tasks found in tasks file.")

    idx = args.task_index
    if idx < 0 or idx >= len(tasks):
        raise IndexError(f"task-index {idx} out of range [0, {len(tasks)-1}]")

    task = tasks[idx]
    name = _task_name(task, idx)

    output_root = Path(args.output_root).expanduser().resolve()
    output_dir = output_root / f"{idx:04d}_{name}"
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = build_command(repo_root, task, output_dir, dry_run=args.dry_run)

    print(f"[canfar] Running task index={idx} name={name}")
    print(f"[canfar] Output directory: {output_dir}")
    print("[canfar] Command:")
    print(" ".join(cmd))

    if args.dry_run:
        return 0

    result = subprocess.run(cmd, check=False)
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
