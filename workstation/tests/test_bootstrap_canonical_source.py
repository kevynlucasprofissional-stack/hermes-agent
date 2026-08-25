from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_normal_installer_never_invokes_source_mutators() -> None:
    install = read("workstation/install.ps1")

    assert "fix_electron_compat.py" not in install
    assert "Applying Hermes Workstation core integration" not in install
    assert '"--check"' in install
    assert "apply_core_integration.py" in install
    assert "Assert-CheckoutUnchanged" in install


def test_normal_installer_prepares_isolated_dependencies_by_default() -> None:
    install = read("workstation/install.ps1")

    assert "Ensure-WorkstationVenv" in install
    assert '-m pip install -e "."' in install
    assert 'Invoke-NativeChecked -Command "npm" -Arguments @("ci")' in install
    assert "if (-not $SkipDependencies)" in install
    assert "Prepare-RuntimeDirectories" in install


def test_windows_workflow_tests_committed_tree_without_repairing_it() -> None:
    workflow = read(".github/workflows/workstation-browser-windows.yml")

    assert "fix_electron_compat.py" not in workflow
    assert "apply_core_integration.py --root . --check" in workflow
    assert "apply_core_integration.py --root .\n" not in workflow
    assert "workstation\\install.cmd" in workflow
    assert "git status --porcelain=v1 --untracked-files=all" in workflow
    assert "Desktop typecheck" in workflow
    assert "Desktop UI tests" in workflow
    assert "Browser runtime Electron tests" in workflow


def test_electron_compatibility_fix_is_committed_not_installer_generated() -> None:
    runtime = read("apps/desktop/electron/workstation-browser-runtime.ts")

    assert "entry.view.webContents.close()" in runtime
    assert "entry.view.webContents.destroy()" not in runtime
