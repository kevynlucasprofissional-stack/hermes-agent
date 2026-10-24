#!/usr/bin/env bash
# ============================================================================
# Hermes Workstation Doctor - Linux
# Equivalent to workstation/doctor.ps1
# ============================================================================

set -e

STRICT=false
for arg in "$@"; do
    case "$arg" in
        --strict) STRICT=true ;;
        *) echo "Unknown argument: $arg" >&2; exit 1 ;;
    esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_ROOT="$ROOT/.venv"
VENV_PYTHON="$VENV_ROOT/bin/python"

FAILURES=0

echo -e "\033[0;36mHermes Workstation Doctor\033[0m"
echo "Root: $ROOT"
echo ""

register_failure() {
    if [ "$STRICT" = true ]; then
        FAILURES=$((FAILURES + 1))
    fi
}

show_cmd_version() {
    local name="$1"
    shift
    local args=("$@")

    if ! command -v "$name" &> /dev/null; then
        echo -e "\033[0;33m[MISSING] $name\033[0m"
        register_failure
        return
    fi

    local raw
    raw=$("$name" "${args[@]}" 2>&1 | head -1)
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo -e "\033[0;32m[OK] $name: $raw\033[0m"
    else
        echo -e "\033[0;31m[FAIL] $name: exit $exit_code\033[0m"
        register_failure
    fi
}

# Check essential commands
show_cmd_version git --version
show_cmd_version node -p "process.versions.node"
show_cmd_version npm --version

# Python checks
echo ""
echo "=== Python Environment ==="

if [ -f "$VENV_PYTHON" ]; then
    PY_VERSION=$("$VENV_PYTHON" -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo -e "\033[0;32m[OK] .venv Python: $PY_VERSION\033[0m"
        if [[ "$PY_VERSION" != 3.14.* ]]; then
            echo -e "\033[0;33m[WARN] .venv Python is not 3.14.x\033[0m"
            register_failure
        fi
    else
        echo -e "\033[0;31m[FAIL] .venv Python exists but failed version check\033[0m"
        register_failure
    fi

    # Test hermes_cli import
    if "$VENV_PYTHON" -c "import hermes_cli; print('OK')" &> /dev/null; then
        echo -e "\033[0;32m[OK] hermes_cli import\033[0m"
    else
        echo -e "\033[0;31m[FAIL] hermes_cli import failed\033[0m"
        register_failure
    fi
else
    echo -e "\033[0;31m[FAIL] .venv not found at $VENV_ROOT\033[0m"
    register_failure
fi

# Check upstream PM tools
echo ""
echo "=== Upstream PM Tools ==="
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version 2>/dev/null | head -1)
    echo -e "\033[0;32m[OK] uv: $UV_VERSION\033[0m"
else
    echo -e "\033[0;33m[MISSING] uv (optional, PM uses its own)\033[0m"
fi

# Check .env
echo ""
echo "=== Configuration ==="
if [ -f "$ROOT/.env" ]; then
    echo -e "\033[0;32m[OK] .env exists\033[0m"
    if [ "$(stat -c '%a' "$ROOT/.env" 2>/dev/null)" = "600" ]; then
        echo -e "\033[0;32m[OK] .env permissions (600)\033[0m"
    else
        echo -e "\033[0;33m[WARN] .env permissions should be 600\033[0m"
    fi
else
    echo -e "\033[0;31m[FAIL] .env not found\033[0m"
    register_failure
fi

# Check skills sync
echo ""
echo "=== Skills ==="
HERMES_SKILLS_DIR="${HERMES_HOME:-$HOME/.hermes}/skills"
if [ -d "$HERMES_SKILLS_DIR" ]; then
    SKILL_COUNT=$(find "$HERMES_SKILLS_DIR" -maxdepth 1 -type d | wc -l)
    echo -e "\033[0;32m[OK] Skills directory exists ($((SKILL_COUNT - 1)) skills)\033[0m"
else
    echo -e "\033[0;33m[MISSING] Skills directory not found\033[0m"
fi

# Summary
echo ""
echo "=== Summary ==="
if [ $FAILURES -eq 0 ]; then
    echo -e "\033[0;32mAll checks passed!\033[0m"
    exit 0
else
    echo -e "\033[0;31m$FAILURES check(s) failed\033[0m"
    if [ "$STRICT" = true ]; then
        exit 1
    else
        exit 0
    fi
fi