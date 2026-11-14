"""Collect real backend/turn evidence for the System 1 live session.

Read-only: reads the running backend's interpreter probe, the kanban task record
and the workstation telemetry ledger. Writes a JSON evidence file next to this
script. Never mutates sessions, leases, ledgers or browser state.

Run with the LIVE backend interpreter (.venv) so the laya probe reflects the
backend that actually serves the human messages:

    C:\\Github\\hermes-agent\\.venv\\Scripts\\python.exe \
        workstation/benchmarks/system1_live_session/collect_turn_evidence_20261107.py --since <iso8601>
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SESSION_ID = "20261107_175035_62899b"
TASK_ID = "t_1863c0f1"


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")


def laya_probe() -> dict:
    spec = importlib.util.find_spec("laya")
    version = None
    if spec is not None:
        try:
            import laya  # noqa: PLC0415

            version = getattr(laya, "__version__", None)
        except Exception as exc:  # pragma: no cover
            version = f"import_error: {type(exc).__name__}: {exc}"
    return {
        "interpreter": sys.executable,
        "python": sys.version.split()[0],
        "laya_importable": spec is not None,
        "laya_version": version,
    }


def provider_registration_probe() -> dict:
    """Ask the backend interpreter which system1 provider, if any, registers."""
    code = (
        "import json\n"
        "try:\n"
        "    from agent.system1_decision import decide_system1\n"
        "    import agent.system1_decision as m\n"
        "    p = getattr(m, '_PROVIDER', None)\n"
        "    print(json.dumps({'registered': p is not None, 'provider': type(p).__name__ if p else None}))\n"
        "except Exception as exc:\n"
        "    print(json.dumps({'registered': False, 'error': f'{type(exc).__name__}: {exc}'}))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=str(REPO), timeout=180
    )
    tail = (out.stdout or "").strip().splitlines()[-1:] or ["{}"]
    try:
        return json.loads(tail[0])
    except ValueError:
        return {"registered": None, "raw": tail[0][:200], "stderr": (out.stderr or "")[-200:]}


def kanban_task() -> dict:
    path = hermes_home() / "kanban.db"
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    row = con.execute(
        "select id,title,status,session_id,current_run_id,created_by,completion_contract,created_at "
        "from tasks where id=?",
        (TASK_ID,),
    ).fetchone()
    return dict(row) if row else {}


def telemetry(since: str | None) -> dict:
    path = hermes_home() / "workstation" / "telemetry" / "telemetry.sqlite"
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    params: list = [SESSION_ID]
    sql = (
        "select event_type,count(*) n,coalesce(sum(provider_calls),0) provider_calls,"
        "coalesce(sum(tool_calls),0) tool_calls,coalesce(sum(input_tokens),0) input_tokens,"
        "coalesce(sum(output_tokens),0) output_tokens,coalesce(sum(duration_ms),0) duration_ms "
        "from events where session_id=?"
    )
    if since:
        sql += " and occurred_at>=?"
        params.append(since)
    sql += " group by event_type order by n desc"
    groups = [dict(r) for r in con.execute(sql, params)]
    system1 = [
        dict(r)
        for r in con.execute(
            "select occurred_at,status,provider_calls,duration_ms,payload_json from events "
            "where event_type='SYSTEM1_COMPLETED' and session_id=? order by occurred_at desc limit 5",
            (SESSION_ID,),
        )
    ]
    provider_calls = [
        dict(r)
        for r in con.execute(
            "select occurred_at,turn_id,call_id,provider_calls,duration_ms,input_tokens,output_tokens,status "
            "from events where event_type='PROVIDER_CALLED' and session_id=?"
            + (" and occurred_at>=?" if since else "")
            + " order by occurred_at",
            [SESSION_ID] + ([since] if since else []),
        )
    ]
    browser_ops = [
        dict(r)
        for r in con.execute(
            "select occurred_at,operation_id,status,duration_ms,route,payload_json from events "
            "where event_type='BROWSER_OPERATION_OBSERVED' and session_id=?"
            + (" and occurred_at>=?" if since else "")
            + " order by occurred_at",
            [SESSION_ID] + ([since] if since else []),
        )
    ]
    return {
        "window_since": since,
        "event_groups": groups,
        "system1_completed": system1,
        "provider_calls": provider_calls,
        "browser_operations": browser_ops,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=None, help="ISO8601 UTC lower bound for the turn window")
    ap.add_argument("--note", default=None)
    args = ap.parse_args()

    evidence = {
        "schema": "hermes.system1.live_session.evidence.v1",
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "session_id": SESSION_ID,
        "task_id": TASK_ID,
        "fastpath_flag": os.environ.get("HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED"),
        "hermes_python_env": os.environ.get("HERMES_PYTHON"),
        "backend_interpreter_probe": laya_probe(),
        "provider_registration": provider_registration_probe(),
        "kanban_task": kanban_task(),
        "telemetry": telemetry(args.since),
        "note": args.note,
    }
    out = Path(__file__).with_name("evidence_preflight_20261107.json" if not args.since else "evidence_turn_20261107.json")
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "flag": evidence["fastpath_flag"],
        "laya_importable": evidence["backend_interpreter_probe"]["laya_importable"],
        "provider_registration": evidence["provider_registration"],
        "task": {k: evidence["kanban_task"].get(k) for k in ("id", "status", "session_id", "current_run_id")},
        "provider_calls": len(evidence["telemetry"]["provider_calls"]),
        "tool_events": {g["event_type"]: g["n"] for g in evidence["telemetry"]["event_groups"]},
        "system1_completed": len(evidence["telemetry"]["system1_completed"]),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
