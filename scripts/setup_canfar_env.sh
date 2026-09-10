#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PATH="${VENV_PATH:-$REPO_ROOT/.venv-canfar}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ACTIVATE_PATH="$VENV_PATH/bin/activate-canfar"

echo "[canfar-setup] repo: $REPO_ROOT"
echo "[canfar-setup] venv: $VENV_PATH"
echo "[canfar-setup] python: $PYTHON_BIN"

cd "$REPO_ROOT"

"$PYTHON_BIN" -m venv "$VENV_PATH"
source "$VENV_PATH/bin/activate"
python -m pip install --upgrade pip
pip install -e .

cat > "$ACTIVATE_PATH" <<EOF
# Source this file to activate the INJECT CANFAR environment.
source "$VENV_PATH/bin/activate"
EOF
chmod +x "$ACTIVATE_PATH"

python - <<'PY'
import inject

required = ["ClusterConfig", "InjectionConfig", "InjectionPipeline"]
missing = [name for name in required if not hasattr(inject, name)]
if missing:
    raise SystemExit(f"[canfar-setup] Missing expected INJECT symbols: {missing}")

print(f"[canfar-setup] INJECT import OK from {inject.__file__}")
PY

python scripts/canfar_parallel_10x1000.py --mode mock --dry-run --n-iterations 1 --n-per-iter 1 >/dev/null

echo
echo "[canfar-setup] CANFAR setup complete."
echo "[canfar-setup] Terminal use:"
echo "source \"$ACTIVATE_PATH\""
echo "[canfar-setup] Condor PYTHON_BIN:"
echo "$VENV_PATH/bin/python"