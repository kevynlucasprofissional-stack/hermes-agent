#!/usr/bin/env bash
# ============================================================================
# Hermes Workstation - Linux One-Click Launcher
# Equivalent to START-HERMES-WORKSTATION.bat + oneclick_bootstrap.ps1
# ============================================================================

set +e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_ROOT="$ROOT/.venv"
VENV_PYTHON="$VENV_ROOT/bin/python"
VENV_PIP="$VENV_ROOT/bin/pip"

SKIP_INSTALL=false
SKIP_PATCH=false

for arg in "$@"; do
    case "$arg" in
        --skip-install) SKIP_INSTALL=true ;;
        --skip-patch) SKIP_PATCH=true ;;
        *) echo "Unknown argument: $arg" >&2; exit 1 ;;
    esac
done

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

WS_SCRIPTS="$ROOT/workstation/scripts"

echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN} HERMES WORKSTATION - LINUX LAUNCHER${NC}"
echo -e "${CYAN}============================================================${NC}"

# ============================================================================
# Step 0: Run upstream setup if needed (setup-hermes.sh)
# ============================================================================
if [ ! -f "$VENV_PYTHON" ] || [ ! -f "$ROOT/.env" ]; then
    echo -e "${CYAN}→${NC} Running upstream setup (setup-hermes.sh)..."
    if [ -f "$ROOT/setup-hermes.sh" ]; then
        bash "$ROOT/setup-hermes.sh" || exit 1
    else
        echo -e "${RED}✗${NC} setup-hermes.sh not found" >&2
        exit 1
    fi
fi

# ============================================================================
# Find PM Python directly from store
# ============================================================================
PM_STORE="${HERMES_RUNTIME_DIR:-$HOME/.hermes/tools}"
PM_PYTHON=$(find "$PM_STORE" -name 'python3' 2>/dev/null | head -1)

if [ -z "$PM_PYTHON" ] || [ ! -x "$PM_PYTHON" ]; then
    PM_PYTHON=$(find "$PM_STORE" -name 'python3.14' -type f 2>/dev/null | head -1)
fi

if [ -z "$PM_PYTHON" ] || [ ! -x "$PM_PYTHON" ]; then
    echo -e "${RED}✗${NC} Could not find PM Python in $PM_STORE" >&2
    exit 1
fi

echo -e "${CYAN}→${NC} Using PM Python: $PM_PYTHON"

run_py() {
    PYTHONHOME= PYTHONPATH="$ROOT" "$PM_PYTHON" "$@"
}

# ============================================================================
# Step 1: Validate Workstation integration
# ============================================================================
echo -e "${CYAN}[1/6]${NC} Validating committed Workstation integration..."
INTEGRATION_OUTPUT=$(run_py "$WS_SCRIPTS/apply_core_integration.py" --root "$ROOT" --check 2>&1)
INTEGRATION_EXIT=$?
if [ "$INTEGRATION_EXIT" -ne 0 ]; then
    echo -e "${RED}✗${NC} Integration validation failed (no shallow/base bypass):" >&2
    echo "$INTEGRATION_OUTPUT" >&2
    exit 1
fi
echo -e "${GREEN}✓${NC} Workstation integration validation passed"

# ============================================================================
# Step 2: Validate Workstation component lock
# ============================================================================
echo -e "${CYAN}[2/6]${NC} Validating Workstation component lock..."
run_py "$WS_SCRIPTS/validate_lock.py"
[ $? -ne 0 ] && { echo -e "${RED}✗${NC} Lock validation failed" >&2; exit 1; }

# ============================================================================
# Step 3: Validate third-party license policy
# ============================================================================
echo -e "${CYAN}[3/6]${NC} Validating third-party license policy..."
run_py "$WS_SCRIPTS/verify_licenses.py"
[ $? -ne 0 ] && { echo -e "${RED}✗${NC} License validation failed" >&2; exit 1; }

# ============================================================================
# Step 4: Assert Node toolchain
# ============================================================================
echo -e "${CYAN}[4/6]${NC} Checking Node.js toolchain..."
"$ROOT/scripts/run-in-hermes-env" node -p "process.versions.node" >/dev/null 2>&1 || { echo -e "${RED}✗${NC} Node.js not found" >&2; exit 1; }
"$ROOT/scripts/run-in-hermes-env" npm --version >/dev/null 2>&1 || { echo -e "${RED}✗${NC} npm not found" >&2; exit 1; }

NODE_VERSION=$("$ROOT/scripts/run-in-hermes-env" node -p "process.versions.node")
NPM_VERSION=$("$ROOT/scripts/run-in-hermes-env" npm --version)
NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
NODE_MINOR=$(echo "$NODE_VERSION" | cut -d. -f2)

[ "$NODE_MAJOR" -lt 22 ] || ([ "$NODE_MAJOR" -eq 22 ] && [ "$NODE_MINOR" -lt 22 ]) && { echo -e "${RED}✗${NC} Node $NODE_VERSION below minimum 22.22.0" >&2; exit 1; }
[ "$NODE_MAJOR" -ne 26 ] && echo -e "${YELLOW}[WARN]${NC} Node $NODE_VERSION ok, but .nvmrc selects Node 26"

echo -e "${GREEN}✓${NC} Node $NODE_VERSION, npm $NPM_VERSION ready"

# ============================================================================
# Step 5: Prepare isolated dependencies
# ============================================================================
if [ "$SKIP_INSTALL" = false ]; then
    echo -e "${CYAN}[5/6]${NC} Preparing isolated dependencies..."

    if [ ! -f "$VENV_PYTHON" ]; then
        echo -e "${CYAN}→${NC} Creating isolated Python environment: $VENV_ROOT"
        run_py -m venv "$VENV_ROOT" || { echo -e "${RED}✗${NC} Failed to create venv" >&2; exit 1; }
    fi

    VENV_PY_VERSION=$("$VENV_PYTHON" -c "import sys; print('.'.join(map(str, sys.version_info[:3])))")
    VENV_PY_MAJOR=$(echo "$VENV_PY_VERSION" | cut -d. -f1)
    VENV_PY_MINOR=$(echo "$VENV_PY_VERSION" | cut -d. -f2)

    [ "$VENV_PY_MAJOR" -lt 3 ] || [ "$VENV_PY_MAJOR" -gt 3 ] || [ "$VENV_PY_MINOR" -lt 14 ] || [ "$VENV_PY_MINOR" -ge 15 ] && { echo -e "${RED}✗${NC} Venv Python $VENV_PY_VERSION is not 3.14.x" >&2; exit 1; }

    if [ "$SKIP_PATCH" = false ]; then
        if command -v uv &> /dev/null; then
            echo -e "${CYAN}→${NC} Installing Hermes into .venv with uv..."
            uv pip install --python "$VENV_PYTHON" -e .
        else
            echo -e "${CYAN}→${NC} Installing Hermes into .venv with pip..."
            "$VENV_PIP" install -e .
        fi
        [ $? -ne 0 ] && { echo -e "${RED}✗${NC} Hermes installation failed" >&2; exit 1; }
    fi

    # A node_modules directory may survive a truncated npm installation.
    if [ -f "$ROOT/package-lock.json" ] && [ -d "$ROOT/node_modules" ] && \
       "$ROOT/scripts/run-in-hermes-env" node "$ROOT/apps/desktop/scripts/assert-root-install.mjs"; then
        echo -e "${GREEN}✓${NC} Node workspaces integrity verified (skipping npm ci)"
    else
        if [ ! -f "$ROOT/package-lock.json" ]; then
            echo -e "${RED}✗${NC} package-lock.json absent: restore the tracked lockfile" >&2
            exit 1
        fi
        echo -e "${CYAN}→${NC} Node dependencies absent/incomplete; restoring from lockfile..."
        "$ROOT/scripts/run-in-hermes-env" npm ci || {
            echo -e "${RED}✗${NC} npm ci failed; environment not ready" >&2
            exit 1
        }
        "$ROOT/scripts/run-in-hermes-env" node "$ROOT/apps/desktop/scripts/assert-root-install.mjs" || {
            echo -e "${RED}✗${NC} npm ci completed but integrity validation failed" >&2
            exit 1
        }
    fi
else
    echo -e "${YELLOW}[5/6]${NC} Dependency installation skipped"
fi

# ============================================================================
# Step 6: Health checks
# ============================================================================
echo -e "${CYAN}[6/6]${NC} Running health checks..."
if [ "$SKIP_INSTALL" = false ]; then
    "$VENV_PYTHON" -c "import hermes_cli; print('OK: hermes_cli import')" || { echo -e "${RED}✗${NC} hermes_cli import failed" >&2; exit 1; }
fi

# ============================================================================
# Step 7: Run doctor
# ============================================================================
echo -e "${CYAN}[Doctor]${NC} Running strict Workstation doctor..."
bash "$ROOT/workstation/doctor.sh" --strict || { echo -e "${RED}✗${NC} Doctor check failed" >&2; exit 1; }

# ============================================================================
# Step 8: Compose environment and print launch command
# ============================================================================
echo -e "${CYAN}[Launch]${NC} Preparing Hermes Desktop environment..."

ENV_SCRIPT=$(PYTHONHOME= PYTHONPATH="$ROOT" "$PM_PYTHON" -m pm.environments --format sh 2>/dev/null)
[ -z "$ENV_SCRIPT" ] && { echo -e "${RED}✗${NC} Could not compose pm environment" >&2; exit 1; }

eval "$ENV_SCRIPT"

export VIRTUAL_ENV="$VENV_ROOT"
export HERMES_PYTHON="$VENV_PYTHON"
export PATH="$VENV_ROOT/bin:$PATH"
export HERMES_WORKSTATION_BROWSER=1
export HERMES_DESKTOP_CDP_PORT=off

echo -e "${GREEN}✓ Environment ready!${NC}"
echo ""
echo "Python runtime: $VENV_PYTHON"
echo "Node runtime:   $NODE_VERSION"
echo "Dev server:     http://127.0.0.1:5174 (Vite + HMR)"
echo "Renderer CDP:   off (Workstation default; internal Browser CDP remains enabled)"
echo ""
echo -e "${CYAN}To start Hermes Desktop, run in a new terminal:${NC}"
echo ""
echo -e "  ${YELLOW}cd $ROOT/apps/desktop && npm run dev${NC}"
echo ""
echo -e "${CYAN}Or run with the full environment applied:${NC}"
echo ""
echo -e "  ${YELLOW}eval \"\$(PYTHONHOME= PYTHONPATH=\$ROOT $PM_PYTHON -m pm.environments --format sh 2>/dev/null)\"${NC}"
echo -e "  ${YELLOW}export VIRTUAL_ENV=$VENV_ROOT HERMES_PYTHON=$VENV_PYTHON PATH=\$VENV_ROOT/bin:\$PATH HERMES_WORKSTATION_BROWSER=1 HERMES_DESKTOP_CDP_PORT=off${NC}"
echo -e "  ${YELLOW}cd $ROOT/apps/desktop && npm run dev${NC}"
echo ""
echo -e "${GREEN}Setup complete!${NC}"