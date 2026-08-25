#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PATH="${VENV_PATH:-$REPO_ROOT/.venv}"

echo "[inject-setup] repo: $REPO_ROOT"
echo "[inject-setup] venv: $VENV_PATH"

cd "$REPO_ROOT"

python3 -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"
python -m pip install --upgrade pip
pip install -e ".[dev,jupyter]"
python - <<'PY'
import src

required = ["ClusterConfig", "InjectionConfig", "InjectionPipeline", "notebook_output_dir"]
missing = [name for name in required if not hasattr(src, name)]
src_file = getattr(src, "__file__", None)

if src_file is None or missing:
    raise SystemExit(
        "[inject-setup] Expected the INJECT package at repo/src/__init__.py, "
        f"but imported src from {src_file!r} with missing symbols: {missing}"
    )

print(f"[inject-setup] INJECT import OK from {src_file}")
PY

echo
echo "[inject-setup] Local setup complete."
echo "[inject-setup] Next time, activate it with:"
echo "source \"$VENV_PATH/bin/activate\""
