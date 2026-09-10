#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASKS_FILE="${TASKS_FILE:-$REPO_ROOT/configs/canfar_tasks.json}"
OUTPUT_ROOT="${OUTPUT_ROOT:-$REPO_ROOT/canfar_outputs}"
SUBMIT_FILE="${SUBMIT_FILE:-$REPO_ROOT/scripts/canfar_submit.condor}"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv-canfar/bin/python}"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tasks-file)
            TASKS_FILE="$2"
            shift 2
            ;;
        --output-root)
            OUTPUT_ROOT="$2"
            shift 2
            ;;
        --python-bin)
            PYTHON_BIN="$2"
            shift 2
            ;;
        --submit-file)
            SUBMIT_FILE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

cd "$REPO_ROOT"

if [[ ! -f "$TASKS_FILE" ]]; then
    echo "Tasks file not found: $TASKS_FILE" >&2
    exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Python executable not found or not executable: $PYTHON_BIN" >&2
    echo "Run bash scripts/setup_canfar_env.sh first, or pass --python-bin." >&2
    exit 1
fi

N_TASKS=$("$PYTHON_BIN" - <<PY
import json
from pathlib import Path

path = Path("$TASKS_FILE").expanduser().resolve()
payload = json.loads(path.read_text(encoding="utf-8"))
tasks = payload.get("tasks", payload) if isinstance(payload, dict) else payload
if not isinstance(tasks, list) or not tasks:
    raise SystemExit("tasks file must contain a non-empty task list")
print(len(tasks))
PY
)

mkdir -p "$OUTPUT_ROOT" "$REPO_ROOT/logs"

echo "[canfar-submit] tasks file: $TASKS_FILE"
echo "[canfar-submit] tasks: $N_TASKS"
echo "[canfar-submit] output root: $OUTPUT_ROOT"
echo "[canfar-submit] python: $PYTHON_BIN"
echo "[canfar-submit] submit file: $SUBMIT_FILE"

CMD=(
    condor_submit "$SUBMIT_FILE"
    -append "TASKS_FILE=$TASKS_FILE"
    -append "N_TASKS=$N_TASKS"
    -append "OUTPUT_ROOT=$OUTPUT_ROOT"
    -append "PYTHON_BIN=$PYTHON_BIN"
)

printf '[canfar-submit] command:'
printf ' %q' "${CMD[@]}"
printf '\n'

if [[ "$DRY_RUN" -eq 1 ]]; then
    exit 0
fi

"${CMD[@]}"