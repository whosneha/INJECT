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

echo
echo "[inject-setup] Local setup complete."
echo "[inject-setup] Next time, activate it with:"
echo "source \"$VENV_PATH/bin/activate\""
