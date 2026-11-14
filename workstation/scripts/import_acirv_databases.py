"""Explicit ACIRV SQLite snapshot importer for Hermes Workstation.

Usage:
  python workstation/scripts/import_acirv_databases.py --tasks "C:\\path\\tarefas.db" --whatsapp "C:\\path\\whatsapp_control.db"

No changes are made to source databases. A new snapshot is created under
HERMES_HOME/workstation/datasets/. Never import the empty WhatsApp stub DB.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workstation.acirv_datasets import import_sources  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Import ACIRV relational SQLite snapshots")
    parser.add_argument("--tasks", type=Path, required=True, help="Existing tarefas.db")
    parser.add_argument("--whatsapp", type=Path, required=True, help="Nonempty canonical WhatsApp database")
    args = parser.parse_args()
    result = import_sources({"tarefas": args.tasks, "whatsapp": args.whatsapp})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
