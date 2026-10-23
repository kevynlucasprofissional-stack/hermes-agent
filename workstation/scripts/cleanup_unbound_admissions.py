"""One-shot cleanup: remove residual 'unbound' runId admissions from browser-session.json.

Usage: python workstation/scripts/cleanup_unbound_admissions.py [--dry-run]

This script is idempotent and safe to re-run. It creates a .bak backup before
modifying the ledger file. Admissions with runId='unbound' are removed because
they were created by the pre-fix fallback and can never be reconciled.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def _ledger_path() -> Path:
    local_app_data = Path.home() / "AppData" / "Local"
    if not local_app_data.exists():
        # Fallback for non-Windows or custom HERMES_HOME setups
        hermes_home = Path(__file__).resolve().parents[2]
        return hermes_home / "Runtime" / "browser-session.json"
    return local_app_data / "HermesWorkstation" / "Runtime" / "browser-session.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup unbound runId admissions")
    parser.add_argument("--dry-run", action="store_true", help="Print what would change without writing")
    args = parser.parse_args()

    ledger = _ledger_path()
    if not ledger.exists():
        print(f"Ledger not found: {ledger}")
        return 0

    raw = ledger.read_text(encoding="utf-8")
    try:
        state = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Ledger is not valid JSON: {exc}")
        return 1

    if not isinstance(state, dict):
        print("Ledger root is not a dict; skipping.")
        return 0

    admissions = state.get("operationAdmissions")
    if not isinstance(admissions, dict) or not admissions:
        print("No operationAdmissions found; nothing to clean.")
        return 0

    unbound_keys = [k for k, v in admissions.items()
                    if isinstance(v, dict) and v.get("runId") == "unbound"]

    if not unbound_keys:
        print(f"No unbound admissions found in {ledger}. Clean.")
        return 0

    print(f"Found {len(unbound_keys)} unbound admission(s):")
    for key in unbound_keys:
        entry = admissions[key]
        print(f"  - {key}: action={entry.get('action')}, taskId={entry.get('taskId')}")

    if args.dry_run:
        print("\n[dry-run] No changes written.")
        return 0

    # Backup before mutation
    backup = ledger.with_suffix(".json.bak")
    shutil.copy2(ledger, backup)
    print(f"\nBackup written to {backup}")

    for key in unbound_keys:
        del admissions[key]

    state["operationAdmissions"] = admissions if admissions else {}
    ledger.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Removed {len(unbound_keys)} unbound admission(s). Ledger updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())