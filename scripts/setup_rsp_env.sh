#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PATH="${VENV_PATH:-$HOME/venvs/inject-rsp}"
KERNEL_NAME="${KERNEL_NAME:-inject-rsp}"
KERNEL_DISPLAY_NAME="${KERNEL_DISPLAY_NAME:-Python (inject-rsp)}"

echo "[inject-setup] repo: $REPO_ROOT"
echo "[inject-setup] venv: $VENV_PATH"
echo "[inject-setup] kernel: $KERNEL_DISPLAY_NAME"

cd "$REPO_ROOT"

source /opt/lsst/software/stack/loadLSST.bash
setup lsst_distrib

python -m venv --system-site-packages "$VENV_PATH"
source "$VENV_PATH/bin/activate"
python -m pip install --upgrade pip
pip install -e ".[jupyter]"
python -m ipykernel install --user --name "$KERNEL_NAME" --display-name "$KERNEL_DISPLAY_NAME"

python -c "from lsst.daf.butler import Butler; print('[inject-setup] Butler import OK')"
python - <<'PY'
import inject

required = ["ClusterConfig", "InjectionConfig", "InjectionPipeline", "notebook_output_dir"]
missing = [name for name in required if not hasattr(inject, name)]
package_file = getattr(inject, "__file__", None)

if package_file is None or missing:
    raise SystemExit(
        "[inject-setup] Expected the INJECT package at repo/inject/__init__.py, "
        f"but imported inject from {package_file!r} with missing symbols: {missing}"
    )

print(f"[inject-setup] INJECT import OK from {package_file}")
PY

echo
echo "[inject-setup] RSP setup complete."
echo "[inject-setup] Terminal use:"
echo "source \"$VENV_PATH/bin/activate\""
echo "[inject-setup] Notebook use:"
echo "Select kernel: $KERNEL_DISPLAY_NAME"
