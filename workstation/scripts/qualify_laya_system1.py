"""Reproducible H-081 evidence: python -m workstation.scripts.qualify_laya_system1 --live.

Uses the supported environment, real owner paths and file-isolated tests. A local
report never certifies GitHub exact-head CI or native Desktop release qualification.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
GATES = {
    "vendor_provenance": "test_laya_vendor_provenance.py",
    "real_typed_contract": "test_laya_real_contract.py",
    "bounded_candidate_influence": "test_system1_capability_routing.py",
    "authority_safety": "test_system1_safety.py",
    "no_system2_verified_recovery": "test_taskcompiler_system1_recovery.py",
    "abstention_handoff": "test_system1_reasoning_handoff.py",
    "supersession_uncertain_reconciliation": "test_taskcompiler_supersession_e2e.py",
    "nonresumable_authority": "test_taskrun_authority_supersession.py",
    "verifier_grounded_learning": "test_system1_learning_review_bridge.py",
    "durable_progressive_experience": "test_progressive_experience_capture.py",
    "dataset_reconstruction": "test_system1_dataset_builder.py",
    "receipt_downstream_lineage": "test_system1_receipts_provenance.py",
    "owner_telemetry": "test_system1_telemetry.py",
}


def run(command, env):
    started = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, encoding="utf-8", errors="replace", capture_output=True)
    evidence = {"command": command, "exit_code": result.returncode,
                "duration_seconds": round(time.monotonic() - started, 3)}
    summary = re.search(r"Summary: (\d+) files, (\d+) tests passed, (\d+) failed(?:, (\d+) skipped)?", result.stdout)
    if summary:
        evidence.update(dict(zip(("files", "passed", "failures", "skipped"), (int(v or 0) for v in summary.groups()))))
    return result, evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Load/download the real checkpoint (explicit opt-in)")
    parser.add_argument("--full", action="store_true", help="Also run the complete Workstation regression")
    parser.add_argument("--output", type=Path, default=ROOT / "workstation/qualification/h081-local.json")
    args = parser.parse_args()
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env["HERMES_LAYA_LIVE_TEST"] = "1" if args.live else "0"
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    report = {"schema": "hermes.h081.qualification.v1", "tested_head": head,
              "created_at": datetime.now(timezone.utc).isoformat(), "python": sys.version,
              "live_checkpoint_enabled": args.live, "gates": {}, "exact_head_ci": "external_pending"}
    from workstation.system1.provenance import get_laya_provenance, verify_laya_provenance
    try:
        verify_laya_provenance()
        report["provenance"] = get_laya_provenance().to_dict()
    except Exception as exc:
        report["provenance"] = {"error_type": type(exc).__name__}
    with tempfile.TemporaryDirectory(prefix="hermes-h081-qualification-") as temp:
        temp = Path(temp)
        for name, file in GATES.items():
            junit = temp / (name + ".xml")
            command = [sys.executable, "-m", "pytest", "workstation/tests/" + file,
                       "-q", "-p", "no:cacheprovider", "--basetemp=" + str(temp / name), "--junitxml=" + str(junit)]
            result, evidence = run(command, env)
            if junit.exists():
                suite = ET.parse(junit).getroot()
                totals = {key: sum(int(s.get(key, "0")) for s in suite.iter("testsuite"))
                          for key in ("tests", "failures", "errors", "skipped")}
                totals["passed"] = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
                evidence.update(totals)
                evidence["properties"] = {prop.get("name"): prop.get("value") for prop in suite.iter("property")}
            evidence["status"] = "passed" if result.returncode == 0 else "failed"
            report["gates"][name] = evidence
            print(name + ": " + evidence["status"], flush=True)
            if result.returncode:
                print(result.stdout[-6000:] + result.stderr[-2000:], flush=True)
        for name, command in {
            "strict_seam_audit": [sys.executable, "workstation/scripts/audit_hermes_seams.py", "--strict"],
            **({"full_workstation": [sys.executable, "scripts/run_tests_parallel.py", "workstation/tests",
                   "-j", "4", "--file-timeout", "900", "--file-retries", "0", "-p", "no:cacheprovider"]} if args.full else {}),
        }.items():
            result, evidence = run(command, env)
            evidence["status"] = "passed" if result.returncode == 0 else "failed"
            report["gates"][name] = evidence
            print(name + ": " + evidence["status"], flush=True)
            if result.returncode:
                print(result.stdout[-6000:] + result.stderr[-2000:], flush=True)
    failed = any(gate["status"] != "passed" for gate in report["gates"].values()) or "error_type" in report["provenance"]
    report["status"] = "FAILED" if failed else "LOCAL_GATES_PASSED" if args.live else "FOCUSED_CONTRACTS_PASSED_LIVE_PENDING"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(str(args.output), flush=True)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
