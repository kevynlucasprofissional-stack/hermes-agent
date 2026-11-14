"""One native HTTP303 / lost-ACK reproduction. Never retries a mutation."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
from uuid import uuid4

from workstation.scripts import browser_kanban_native_e2e_p2 as p2
from workstation.tests.fixtures.browser_kanban_qa_fixture import make_server


def main() -> int:
    root = Path(tempfile.gettempdir()) / ("hermes-p3-native-" + uuid4().hex[:10])
    root.mkdir(parents=True, exist_ok=False)
    report = {"qa_dir": str(root), "utc": datetime.now(timezone.utc).isoformat(),
              "fixture": "form_POST_303", "attempted_clicks": 0}
    original_dispatch = p2.browser._dispatch
    original_server = p2.make_server
    p2.make_server = lambda db: make_server(db, submit_navigates=True)
    def capture(action, args, **kwargs):
        if action == "browser_click":
            report["attempted_clicks"] += 1
            report["click_operation_id"] = kwargs.get("operation_id")
            report["task_id"] = kwargs.get("task_id")
            report["run_id"] = kwargs.get("run_id")
            report["session_id"] = kwargs.get("session_id")
        return original_dispatch(action, args, **kwargs)
    p2.browser._dispatch = capture
    try:
        try:
            p2._run(root, report)
        except Exception as exc:
            report["native_error_type"] = type(exc).__name__
            report["native_error_code"] = getattr(exc, "error_code", None)
            report["native_error"] = str(exc)[:180]
        if (root / "fixture.sqlite").exists():
            with sqlite3.connect(root / "fixture.sqlite") as conn:
                report["fixture_state"] = conn.execute(
                    "SELECT title,revision FROM qa_item WHERE id=1").fetchone()
                report["post_count"] = conn.execute(
                    "SELECT COUNT(*) FROM qa_applied_operations").fetchone()[0]
        if (root / "kanban-qa.db").exists() and report.get("task_id"):
            from hermes_cli import kanban_db
            with sqlite3.connect(root / "kanban-qa.db") as conn:
                conn.row_factory = sqlite3.Row
                row = kanban_db.get_task(conn, report["task_id"])
                report["task_status"] = row.status if row else None
        if report.get("click_operation_id"):
            from tools.browser_workstation import _workstation_home
            owner = _workstation_home() / "Runtime" / "browser-session.json"
            if owner.exists():
                state = json.loads(owner.read_text(encoding="utf-8"))
                admission = (state.get("operationAdmissions") or {}).get(report["click_operation_id"])
                if admission:
                    report["owner_admission"] = {
                        k: admission.get(k) for k in (
                            "operationId", "action", "taskId", "sessionId", "runId",
                            "tabId", "acknowledged", "terminal")}
        report["reproduced_lost_ack"] = (
            report.get("attempted_clicks") == 1 and report.get("post_count") == 1
            and report.get("fixture_state", [None, 0])[1] == 1
            and report.get("native_error_code") is not None
            and (report.get("owner_admission") or {}).get("acknowledged") is not True)
    finally:
        p2.browser._dispatch = original_dispatch
        p2.make_server = original_server
        (root / "report-p3.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, default=str))
    return 0 if report.get("reproduced_lost_ack") else 2


if __name__ == "__main__":
    raise SystemExit(main())
