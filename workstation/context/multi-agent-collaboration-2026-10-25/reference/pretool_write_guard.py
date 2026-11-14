"""Reference read/write admission bridge for Claude / controlled MCP calls.

NOT installed as a global hook. Promote only after P0-A. It does NOT sandbox raw
PowerShell, Git, arbitrary subprocesses or unrestricted MCP file operations.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path


def target_relative(repo: Path, raw_path: str) -> str:
    if not raw_path:
        raise ValueError("Missing write target")
    root = repo.resolve()
    raw = Path(raw_path.replace("\\", "/"))
    resolved = (raw if raw.is_absolute() else root / raw).resolve()
    try:
        rel = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("Write target is outside the authorized checkout") from exc
    if not rel.parts or rel.parts[0].casefold() == ".git":
        raise ValueError("Direct Git metadata modification forbidden")
    return rel.as_posix()


def import_coordinator(repo: Path):
    source = repo / "workstation/scripts/multi_agent_coordination.py"
    spec = importlib.util.spec_from_file_location("multi_agent_coordination_guarded", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Coordinator unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def admission(repo: Path, target: str, agent: str | None, strict: bool) -> dict:
    try:
        path = target_relative(repo, target)
        if strict and not agent:
            return {"allowed": False, "reason": "SESSION_ID_REQUIRED", "path": path}
        return import_coordinator(repo).check_path(repo, path, agent, require_claim=strict)
    except (OSError, ValueError, RuntimeError, ImportError, TypeError) as exc:
        return {"allowed": False, "reason": "ADMISSION_FAILED", "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(os.environ.get(
        "CLAUDE_PROJECT_DIR", Path(__file__).resolve().parents[4]
    )))
    parser.add_argument("--path", help="Explicit target path for external controlled adapters")
    parser.add_argument("--agent", default=os.environ.get("HERMES_COLLAB_AGENT"))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    # Direct --path is suitable for gate integration. Claude Edit/Write JSON
    # tool payload is consumed via stdin when --path is absent.
    try:
        if args.path:
            target = args.path
        else:
            payload = json.load(sys.stdin)
            target = payload.get("tool_input", {}).get("file_path", "")
        result = admission(args.root, target, args.agent, args.strict)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        result = {"allowed": False, "reason": "INVALID_REQUEST", "error": str(exc)}
    if result.get("allowed"):
        return 0
    print("COLLAB_BLOCKED: " + json.dumps(result, ensure_ascii=False), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
