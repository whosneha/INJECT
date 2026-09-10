#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PATH="${VENV_PATH:-$HOME/venvs/inject-rsp}"
KERNEL_NAME="${KERNEL_NAME:-inject-rsp}"
KERNEL_DISPLAY_NAME="${KERNEL_DISPLAY_NAME:-Python (inject-rsp)}"
KERNEL_DIR="${HOME}/.local/share/jupyter/kernels/${KERNEL_NAME}"
LAUNCHER_PATH="${VENV_PATH}/bin/${KERNEL_NAME}-kernel"
ACTIVATE_RSP_PATH="${VENV_PATH}/bin/activate-rsp"

echo "[inject-setup] repo: $REPO_ROOT"
echo "[inject-setup] venv: $VENV_PATH"
echo "[inject-setup] kernel: $KERNEL_DISPLAY_NAME"

cd "$REPO_ROOT"

set +u
source /opt/lsst/software/stack/loadLSST.bash
setup lsst_distrib
set -u

mkdir -p "$(dirname "$VENV_PATH")"
python -m venv --system-site-packages "$VENV_PATH"
source "$VENV_PATH/bin/activate"
python -m pip install --upgrade pip
pip install -e ".[jupyter]"

cat > "$ACTIVATE_RSP_PATH" <<EOF
# Source this file to load the Rubin stack and activate the INJECT venv.
set +u
source /opt/lsst/software/stack/loadLSST.bash
setup lsst_distrib
set -u
source "$VENV_PATH/bin/activate"
EOF
chmod +x "$ACTIVATE_RSP_PATH"

cat > "$LAUNCHER_PATH" <<EOF
#!/usr/bin/env bash
set -euo pipefail
source "$ACTIVATE_RSP_PATH"
exec python -m ipykernel_launcher "\$@"
EOF
chmod +x "$LAUNCHER_PATH"

mkdir -p "$KERNEL_DIR"
cat > "$KERNEL_DIR/kernel.json" <<EOF
{
  "argv": [
    "$LAUNCHER_PATH",
    "-f",
    "{connection_file}"
  ],
  "display_name": "$KERNEL_DISPLAY_NAME",
  "language": "python",
  "metadata": {
    "debugger": true
  }
}
EOF

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

bash -lc "set +u && source /opt/lsst/software/stack/loadLSST.bash && setup lsst_distrib && set -u && source \"$VENV_PATH/bin/activate\" && python -c \"from lsst.daf.butler import Butler; print('[inject-setup] Butler import OK inside kernel environment')\""
bash -lc "set +u && source /opt/lsst/software/stack/loadLSST.bash && setup lsst_distrib && set -u && source \"$VENV_PATH/bin/activate\" && python -c \"import inject; print('[inject-setup] Kernel imports INJECT from ' + inject.__file__)\""

echo
echo "[inject-setup] RSP setup complete."
echo "[inject-setup] Terminal use:"
echo "source \"$ACTIVATE_RSP_PATH\""
echo "[inject-setup] Notebook use:"
echo "Select kernel: $KERNEL_DISPLAY_NAME"
