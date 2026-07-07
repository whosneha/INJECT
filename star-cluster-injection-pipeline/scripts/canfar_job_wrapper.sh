#!/usr/bin/env bash
set -euo pipefail

# Required env vars for batch launch
: "${TASKS_FILE:?Set TASKS_FILE to task JSON path}"
: "${JOB_INDEX:?Set JOB_INDEX to task index (usually Condor ProcId)}"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_ROOT="${OUTPUT_ROOT:-$REPO_ROOT/canfar_outputs}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[canfar-wrapper] repo: $REPO_ROOT"
echo "[canfar-wrapper] task index: $JOB_INDEX"
echo "[canfar-wrapper] tasks file: $TASKS_FILE"
echo "[canfar-wrapper] output root: $OUTPUT_ROOT"

cd "$REPO_ROOT"

"$PYTHON_BIN" scripts/canfar_run_tasks.py \
  --tasks-file "$TASKS_FILE" \
  --task-index "$JOB_INDEX" \
  --output-root "$OUTPUT_ROOT"
