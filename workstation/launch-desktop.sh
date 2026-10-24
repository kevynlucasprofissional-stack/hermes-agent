#!/usr/bin/env bash
# Hermes Workstation Desktop Launcher Wrapper - WITH PERSISTENT LOGS

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PM_STORE="${HERMES_RUNTIME_DIR:-$HOME/.hermes/tools}"
PM_PYTHON="${HERMES_PM_PYTHON:-}"
if [ -z "$PM_PYTHON" ]; then
    PM_PYTHON="$(find "$PM_STORE" -name python3 -print -quit 2>/dev/null)"
fi
if [ -z "$PM_PYTHON" ] || [ ! -x "$PM_PYTHON" ]; then
    echo "ERROR: Hermes PM Python not found. Run workstation/start.sh." >&2
    read -r -p "Press Enter to close this terminal..." || true
    exit 1
fi
VENV_ROOT="$ROOT/.venv"
VENV_PYTHON="$VENV_ROOT/bin/python"

cd "$ROOT"

echo "=== Hermes Workstation Desktop Launcher ==="
echo "Root: $ROOT"
echo "Timestamp: $(date)"
echo ""

# Compose PM environment
ENV_SCRIPT=$(PYTHONHOME= PYTHONPATH="$ROOT" "$PM_PYTHON" -m pm.environments --format sh 2>/dev/null)
if [ -z "$ENV_SCRIPT" ]; then
    echo "ERROR: Could not compose pm environment" >&2
    echo ""
    echo "=== Press Enter to close this terminal and copy logs above ==="
    read -p ""
    exit 1
fi

eval "$ENV_SCRIPT"

export VIRTUAL_ENV="$VENV_ROOT"
export HERMES_PYTHON="$VENV_PYTHON"
export PATH="$VENV_ROOT/bin:$PATH"
export HERMES_WORKSTATION_BROWSER=1
export HERMES_DESKTOP_CDP_PORT=off

if ! node "$ROOT/apps/desktop/scripts/assert-root-install.mjs"; then
    echo "ERROR: Node install incomplete. Run: bash $ROOT/workstation/start.sh" >&2
    read -r -p "Press Enter to close this terminal..." || true
    exit 1
fi

echo "Environment ready. Starting Hermes Desktop..."
echo "Vite dev server: http://127.0.0.1:5174"
echo "Renderer CDP: off (internal Browser CDP enabled)"
echo ""

cd "$ROOT/apps/desktop"
npm run dev

# Keep terminal open on error - THIS IS THE KEY CHANGE
EXIT_CODE=$?
echo ""
echo "========================================"
echo "=== Process exited with code: $EXIT_CODE ==="
echo "=== Timestamp: $(date) ==="
echo "========================================"
echo ""
echo "COPY THE LOGS ABOVE BEFORE CLOSING"
echo ""
read -p "Press Enter to close this terminal..."
exit $EXIT_CODE