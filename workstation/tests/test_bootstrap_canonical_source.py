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


def test_one_click_dogfood_launcher_runs_canonical_phases_once() -> None:
    launcher = read("START-HERMES-WORKSTATION.bat")
    bootstrap = read("workstation/scripts/oneclick_bootstrap.ps1")

    assert 'workstation\\scripts\\oneclick_bootstrap.ps1' in launcher
    assert 'Invoke-Step -Name "[3/4] Running strict Workstation doctor..."' in bootstrap
    assert 'Invoke-Step -Name "[4/4] Starting Hermes Work..."' in bootstrap
    assert '@("-SkipInstall")' in bootstrap
    assert 'Invoke-WithWorkstationInstallLock' in bootstrap


def test_direct_start_delegates_to_cached_one_click_install_gate() -> None:
    start = read("workstation/start.ps1")

    assert "[switch]$SkipInstall" in start
    assert "if (-not $SkipInstall)" in start
    assert 'scripts\\oneclick_bootstrap.ps1' in start
    assert "-File $BootstrapScript" in start
    assert "exit $LASTEXITCODE" in start
    assert "& $InstallScript" not in start


def test_windows_workflow_tests_committed_tree_without_repairing_it() -> None:
    workflow = read(".github/workflows/workstation-browser-windows.yml")

    assert "fix_electron_compat.py" not in workflow
    assert "apply_core_integration.py --root . --check" in workflow
    assert "apply_core_integration.py --root .\n" not in workflow
    assert "workstation\\install.cmd" in workflow
    # START-HERMES-WORKSTATION.bat is a local-only launcher that delegates to
    # oneclick_bootstrap.ps1; the CI workflow invokes install.cmd / doctor.cmd
    # directly and does not reference the .bat file.
    # The workflow references playwright configs and e2e specs by exact path,
    # not via glob patterns in a paths: trigger block.
    assert "playwright.config.ts" in workflow
    assert "playwright.dashboard.config.ts" in workflow
    assert "git status --porcelain=v1 --untracked-files=all" in workflow
    assert "Production dependency audit" in workflow
    assert "npm audit --omit=dev --audit-level=moderate" in workflow
    assert "Desktop typecheck" in workflow
    assert "Desktop UI tests" in workflow
    assert "Browser runtime Electron tests" in workflow
    assert "Desktop production build" in workflow
    assert "Assert build kept checkout clean" in workflow
    assert "Prepare Workstation validation dependencies" in workflow
    # The workflow now uses pm.build_env for isolated validation environments
    # instead of uv sync --locked directly.
    assert "pm.build_env" in workflow
    assert "--extra workstation-laya" in workflow
    assert 'pip install -e ".[dev,anthropic]"' not in workflow
    assert "Emit clean-machine install evidence" in workflow
    assert "Allocate isolated Workstation home" in workflow
    assert "HERMES_WORKSTATION_HOME=$cleanHome" in workflow
    assert "$env:GITHUB_ENV" in workflow
    assert "workstation_home = $env:HERMES_WORKSTATION_HOME" in workflow
    assert "Clean Workstation home is missing" in workflow
    assert "workstation.release_qualification" in workflow
    assert "id: release_qualification" in workflow
    assert "steps.release_qualification.outcome" in workflow
    assert "Workstation reconnect soak" in workflow
    assert "--duration 180" in workflow
    assert "--iterations 3000" in workflow
    assert "--sessions 4" in workflow
    assert "max_live_memory_records" in workflow
    assert "memoryBound" in workflow
    assert "steps.workstation_soak.outcome" in workflow
    assert "name: workstation-soak" in workflow
    assert "Native Browser runtime reconnect soak" in workflow
    assert "id: native_browser_runtime_soak" in workflow
    assert "H011_DURATION_MS" in workflow
    assert "H011_CHILD_ITERATIONS" in workflow
    assert "steps.native_browser_runtime_soak.outcome" in workflow
    assert "name: workstation-native-browser-soak" in workflow
    assert "Headless backend multi-session reconnect soak" in workflow
    assert "id: headless_backend_soak" in workflow
    assert "H012_DURATION_MS" in workflow
    assert "H012_RESTARTS" in workflow
    assert "steps.headless_backend_soak.outcome" in workflow
    assert "name: workstation-headless-backend-soak" in workflow
    assert "Install Dashboard smoke browsers" in workflow
    assert "Dashboard cross-engine smoke" in workflow
    assert "Desktop unpacked package" in workflow
    assert "Packaged Desktop GUI E2E" in workflow
    assert "Integrated Desktop Browser headless load E2E" in workflow
    assert "id: desktop_browser_load_e2e" in workflow
    assert "HERMES_DESKTOP_E2E_HEADLESS" in workflow
    assert "steps.dashboard_cross_engine.outcome" in workflow
    assert "steps.desktop_packaged_build.outcome" in workflow
    assert "steps.packaged_gui_e2e.outcome" in workflow
    assert "steps.desktop_browser_load_e2e.outcome" in workflow
    # upload-artifact is pinned to a specific SHA, not @v4 tag
    assert "actions/upload-artifact@" in workflow


def test_doctor_has_an_explicit_strict_gate_mode() -> None:
    doctor = read("workstation/doctor.ps1")

    assert "[switch]$Strict" in doctor
    assert "$script:StrictFailureCount" in doctor
    assert "Strict doctor found" in doctor
    assert "exit 1" in doctor
    assert "Strict doctor passed all required checks" in doctor
    assert "function Resolve-WorkstationHome" in doctor
    assert "$env:HERMES_WORKSTATION_HOME" in doctor
    assert "Explicit Workstation home is missing Runtime or Browser directories" in doctor


def test_windows_workflow_does_not_mask_ui_or_platform_failures() -> None:
    workflow = read(".github/workflows/workstation-browser-windows.yml")

    assert "id: desktop_ui_tests" in workflow
    assert "id: desktop_platform_tests" in workflow
    assert workflow.count("continue-on-error: true") >= 2
    assert "Preserve Desktop gate result" in workflow
    assert "steps.desktop_ui_tests.outcome" in workflow
    assert "steps.desktop_platform_tests.outcome" in workflow
    assert "One or more Desktop/Workstation gates failed" in workflow


def test_electron_compatibility_fix_is_committed_not_installer_generated() -> None:
    runtime = read("apps/desktop/electron/workstation-browser-runtime.ts")

    assert "entry.view.webContents.close()" in runtime
    assert "entry.view.webContents.destroy()" not in runtime


def test_native_browser_runtime_soak_is_hidden_and_checks_canonical_reconnect() -> None:
    probe = read("workstation/context/engineering-journal/probes/h011-native-browser-runtime-soak.mjs")

    assert "windowsHide: true" in probe
    assert "show: false" in probe
    assert "browser-session.json" in probe
    assert "runtime.resources()" in probe
    assert "H011_NATIVE_BROWSER_RUNTIME_CLASSIFICATION=VALIDATED" in probe


def test_headless_backend_soak_uses_real_server_and_never_launches_electron() -> None:
    probe = read("workstation/context/engineering-journal/probes/h012-headless-backend-reconnect-soak.py")

    assert '"hermes_cli.main"' in probe
    assert '"serve"' in probe
    assert "HERMES_ISO_CERTIFY_SYNTH_TURN" in probe
    assert "session.resume" in probe
    assert "H012_HEADLESS_BACKEND_CLASSIFICATION=VALIDATED" in probe
    assert "WebContentsView" not in probe


def test_integrated_desktop_browser_load_e2e_is_hidden_and_resolves_workspace_electron() -> None:
    spec = read("apps/desktop/e2e/workstation-headless-load.spec.ts")
    fixtures = read("apps/desktop/e2e/fixtures.ts")
    electron_binary = read("apps/desktop/e2e/electron-binary.ts")
    workflow = read(".github/workflows/workstation-browser-windows.yml")

    assert "setupMockBackend({ headless: true })" in spec
    assert "waitForAppReady(fixture, 120_000, false)" in spec
    assert "HERMES_DESKTOP_E2E_HEADLESS" in fixtures
    assert "HERMES_DESKTOP_E2E_REPORT" in spec
    assert "sustainedLoadEvidence" in spec
    assert "resolveElectronBinary([DESKTOP_ROOT, REPO_ROOT])" in fixtures
    assert "platform === 'win32' ? 'electron.exe' : 'electron'" in electron_binary
    assert "electronDistCandidates(roots: string[]" in electron_binary
    assert '$env:HERMES_DESKTOP_E2E_SUSTAINED_TASKS = "16"' in workflow
    assert '$env:HERMES_DESKTOP_E2E_SUSTAINED_DURATION_MS = "120000"' in workflow
    assert "HERMES_DESKTOP_E2E_REPORT" in workflow
    assert "workstation.desktop_load_evidence" in workflow
    assert "--min-tasks 16" in workflow
    assert "--min-rounds 300" in workflow
    assert "--min-duration-ms 120000" in workflow
    assert "--min-chat-turns 8" in workflow
