"""One-shot native Chromium -> isolated Kanban + HTTP/SQLite QA.

NO retries of browser_type/click. Uses the existing authenticated Electron
controller, never CDP/Playwright/global mouse. Does not restart or mutate any
production Kanban board. May create one dedicated QA BrowserTask in the owner's
persisted browser-session state; existing tabs are not closed or modified.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import threading
import time
from urllib.request import urlopen
from uuid import uuid4

from hermes_cli import kanban_db
from tools import browser_workstation as browser
from workstation.browser_operation_readback import BrowserReadbackContract
from workstation.contracts import AcceptanceContract, IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.integrations.hermes.completion_admission import workstation_completion_admission
from workstation.integrations.hermes.tool_observer import (
    workstation_pre_dispatch_hook, workstation_raw_post_tool_observer,
)
from workstation.kanban import WorkstationKanbanBridge
from workstation.tests.fixtures.browser_kanban_qa_fixture import make_server
from types import SimpleNamespace


def _http_state(url):
    with urlopen(url + "api/item", timeout=4) as response:
        assert response.status == 200
        return json.load(response)


def _extract_refs(browser_data):
    elements = browser_data.get("elements")
    if not isinstance(elements, list):
        return None, None
    textbox = next((e.get("ref") for e in elements if isinstance(e, dict)
                    and e.get("role") in {"textbox", "input"}
                    and (e.get("label") == "Titulo" or e.get("name") == "title"
                         or e.get("tag") in {"input", "textarea"})), None)
    save = next((e.get("ref") for e in elements if isinstance(e, dict)
                 and e.get("role") == "button"
                 and "Salvar" in str(e.get("label") or "")), None)
    return textbox, save


def _run(tmp, report):
    from workstation.artifacts import ArtifactStore
    os.environ["HERMES_HOME"] = str(tmp / "hermes-isolated")
    os.environ["HERMES_KANBAN_DB"] = str(tmp / "kanban-qa.db")
    # Keep the real Electron control descriptor; never set WORKSTATION_HOME.
    os.environ.pop("HERMES_WORKSTATION_HOME", None)
    bridge = WorkstationKanbanBridge()
    assert kanban_db.kanban_db_path().resolve() == Path(os.environ["HERMES_KANBAN_DB"]).resolve()
    # Check controller authority without mutating any tabs.
    health = browser._request_json("GET", "/health", timeout=5)
    state = health.get("state") or {}
    assert health.get("success") and health.get("runtime") == "electron-chromium"
    assert state.get("ready") and state.get("controlReady")
    assert state.get("controlOwner") == "agent" and not state.get("paused")
    assert not state.get("humanControlLease")
    report["controller_checked"] = True

    server = make_server(tmp / "fixture.sqlite")
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    url = f"http://127.0.0.1:{server.server_port}/"
    try:
        baseline = _http_state(url)
        assert baseline == {"id": "qa-1", "title": "Inicial", "revision": 0}
        report["baseline_revision"] = baseline["revision"]
        session = "qa-browser-p2-" + uuid4().hex[:10]
        prompt = "QA autorizado: preencher e salvar um formulário local, verificar persistência independente"
        envelope = MessageEnvelope(
            MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK,
            session, prompt, correlation_id="qa-" + uuid4().hex[:12],
            metadata={"explicit_force_work": True},
        )
        task = bridge.promote_request_if_multistep(
            prompt, session_id=session, envelope=envelope, force=True,
            acceptance_contract=AcceptanceContract(policy="evidence",
                required_verifiers=["native_browser_external_readback"]),
        )
        assert task
        with bridge.get_connection() as conn:
            running = kanban_db.get_task(conn, task)
            assert running.status == "running" and running.current_run_id
            run = str(running.current_run_id)
        report["qa_task_created"] = True

        kwargs = dict(task_id=task, session_id=session, kanban_card_id=task,
                      run_id=run, model_facing=False)
        nav_id = "op_browser_navigate_" + uuid4().hex[:12]
        raw = json.loads(browser._dispatch(
            "browser_navigate", {"url": url}, operation_id=nav_id, **kwargs))
        assert raw.get("success") is True and raw.get("runtime") == "electron-chromium", (
            "Native navigation not acknowledged: " + str(raw.get("status") or raw.get("code")))
        report["native_navigation"] = True
        snapshot = json.loads(browser._dispatch("browser_snapshot", {"full": False}, **kwargs))
        textbox, save = _extract_refs(snapshot)
        assert textbox and save, "QA form refs not available in native Browser snapshot"
        report["qa_form_refs"] = True

        agent = SimpleNamespace(
            session_id=session, _conversation_root_id=lambda: session,
            _canonical_work_task_id=task, _canonical_work_run_id=run,
            _work_tool_observations=[], _work_mutation_evidence={},
            _work_mutation_shapes={}, _work_completed_mutations={},
            _work_mutation_sem_families={}, _work_capabilities={},
            valid_tool_names=set(),
        )
        desired = "QA P2 native " + uuid4().hex[:8]
        def action_once(action, args, call_id):
            context = {"agent": agent, "dispatched": True}
            workstation_pre_dispatch_hook(action, args, call_id, context)
            op_id = "op_" + action + "_" + uuid4().hex[:12]
            # If this raises after dispatch, do NOT retry the effect.
            result = browser._dispatch(action, dict(args), operation_id=op_id, **kwargs)
            workstation_raw_post_tool_observer(
                action, args, call_id, result, 0.25, context)
            parsed = json.loads(result)
            entry = next((row for row in agent._work_tool_observations
                          if row.get("call_id") == call_id), {})
            proof = entry.get("native_browser_evidence") or {}
            if (parsed.get("success") is not True or
                    proof.get("status") != "observed" or
                    entry.get("status") != "completed"):
                raise RuntimeError("native receipt not observed safely")
            return parsed, proof

        type_call = "qa-type-" + uuid4().hex[:10]
        click_call = "qa-save-" + uuid4().hex[:10]
        action_once("browser_type", {"ref": textbox, "text": desired}, type_call)
        report["native_type_observed"] = True

        # The native owner can remap refs after DOM changes; obtain new refs.
        refresh = json.loads(browser._dispatch("browser_snapshot", {"full": False}, **kwargs))
        _, save_ref = _extract_refs(refresh)
        assert save_ref, "Save button ref disappeared; no commit was dispatched"
        click_sent = False
        try:
            click_sent = True
            action_once("browser_click", {"ref": save_ref}, click_call)
        finally:
            report["native_click_dispatched_once"] = click_sent
        report["native_click_observed"] = True

        persisted = _http_state(url)
        report["fresh_server_revision"] = persisted.get("revision")
        assert persisted == {"id": "qa-1", "title": desired, "revision": 1}
        # Trusted expected state is bound by this QA driver, not model output.
        agent._work_browser_readback_contract = BrowserReadbackContract(
            commit_call_id=click_call, input_call_ids=(type_call,),
            read_path="/api/item", resource_id="qa-1",
            expected_fields=(("title", desired), ("revision", 1)),
            revision_before=0, revision_after=1,
        )
        admission = workstation_completion_admission(task, run, {
            "agent": agent, "session_id": session,
            "turn_result": {"completed": True, "failed": False,
                            "interrupted": False, "final_response": "QA native form persisted"},
        })
        report["canonical_admitted"] = admission.admitted
        if not admission.admitted:
            report["canonical_reason"] = admission.reason
            raise RuntimeError("canonical Kanban rejected Browser E2E readback")
        with sqlite3.connect(tmp / "kanban-qa.db") as db:
            db.row_factory = sqlite3.Row
            kanban_task = kanban_db.get_task(db, task)
            task_run = kanban_db.latest_run(db, task)
            assert kanban_task.status == "done" and task_run.status == "done"
            outcome = task_run.metadata["workstation"]["outcome"]
            assert outcome["status"] == "verified_completed"
            assert outcome["verifier_results"][0]["verifier"] == "native_browser_external_readback"
            assert outcome["evidence_refs"]
            report["canonical_sqlite_done"] = True
        with sqlite3.connect(tmp / "fixture.sqlite") as db:
            assert db.execute("SELECT title,revision FROM qa_item WHERE id=1").fetchone() == (
                desired, 1)
            assert db.execute("SELECT COUNT(*) FROM qa_applied_operations").fetchone()[0] == 1
        report["fixture_sqlite_persisted"] = True
        return True
    finally:
        server.shutdown()
        server.server_close()
        t.join(timeout=3)


def main():
    root = Path(tempfile.gettempdir()) / ("hermes-p2-native-" + uuid4().hex[:10])
    root.mkdir(parents=True, exist_ok=False)
    report = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "isolation": "temp_kanban_and_fixture_sqlite",
        "chromium_native_real": False,
    }
    ok = False
    try:
        ok = _run(root, report)
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error_reason"] = str(exc)[:260]
    finally:
        report["chromium_native_real"] = bool(report.get("native_click_observed"))
        report["status"] = "verified_completed" if ok else "not_verified"
        out = root / "report.json"
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"qa_dir": str(root), **report}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
