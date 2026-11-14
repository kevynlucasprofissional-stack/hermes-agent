"""One real AIAgent turn -> native Electron browser -> QA Kanban.

QA fixture + Kanban DB are temporary. Model chooses tools through the regular
agent lifecycle, not by this script. Never retries browser mutations.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
from uuid import uuid4
from urllib.request import urlopen

from hermes_cli.config import load_config_readonly
from workstation.tests.fixtures.browser_kanban_qa_fixture import make_server


def _run(root: Path, report: dict) -> None:
    from hermes_constants import get_hermes_home
    original_home = Path(get_hermes_home())
    # Keep the authenticated provider configuration and environment of the
    # already authorized user without copying any secret to the QA directory.
    from dotenv import load_dotenv
    load_dotenv(original_home / ".env", override=False)
    config = load_config_readonly().get("model") or {}
    provider = str(config.get("provider") or "")
    model = str(config.get("default") or "")
    base_url = str(config.get("base_url") or "")
    if provider != "deepseek" or not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("Configured DeepSeek model not available for isolated QA")
    if not model or not base_url:
        raise RuntimeError("Model configuration unavailable")

    os.environ["HERMES_HOME"] = str(root / "hermes-isolated")
    os.environ["HERMES_KANBAN_DB"] = str(root / "kanban-qa.db")
    os.environ["HERMES_SESSION_SOURCE"] = "desktop"
    # Intentionally never set HERMES_WORKSTATION_HOME: reuse existing Electron.
    from workstation.integrations.hermes.adapter import install_workstation_adapter
    install_workstation_adapter()
    from agent.pre_dispatch import (
        register_pre_authorized_dispatch_hook,
        unregister_pre_authorized_dispatch_hook,
    )
    from workstation.browser_operation_readback import TrustedBrowserReadbackExpectation
    from workstation.kanban import WorkstationKanbanBridge
    from workstation.tests.fixtures.browser_kanban_qa_fixture import make_server
    from tools import browser_workstation as browser
    from run_agent import AIAgent
    from hermes_cli import kanban_db

    health = browser._request_json("GET", "/health", timeout=5)
    state = health.get("state") or {}
    if not (health.get("runtime") == "electron-chromium"
            and state.get("controlOwner") == "agent"
            and state.get("controlReady") is True
            and not state.get("paused")
            and not state.get("humanControlLease")):
        raise RuntimeError("Native Chromium owner is not currently agent-controlled")
    report["native_owner_ready"] = True

    server = make_server(root / "fixture.sqlite")
    service = threading.Thread(target=server.serve_forever, daemon=True)
    service.start()
    port = server.server_port
    url = f"http://127.0.0.1:{port}/"
    title = "QA Agent Hermes " + uuid4().hex[:8]
    session = "qa-agent-entry-" + uuid4().hex[:11]
    report["fixture_url"] = url
    calls = Counter()
    durations = {}
    original_request = browser._request_json
    agent = None

    def measured_request(method, suffix, payload=None, **kwargs):
        if method != "POST" or suffix != "/v1/action" or not isinstance(payload, dict):
            return original_request(method, suffix, payload, **kwargs)
        action = str(payload.get("action") or "unknown")
        start = time.perf_counter()
        calls[action] += 1
        try:
            return original_request(method, suffix, payload, **kwargs)
        finally:
            durations[action] = durations.get(action, 0.0) + (
                time.perf_counter() - start) * 1000

    browser._request_json = measured_request

    def trusted_host_expectation(name, args, call_id, context):
        active = context.get("agent")
        if active is None or name not in {"browser_navigate", "browser_type", "browser_click"}:
            return
        task = getattr(active, "_canonical_work_task_id", None)
        run = getattr(active, "_canonical_work_run_id", None)
        if not task or run is None:
            return
        if getattr(active, "_work_browser_readback_expectation", None) is None:
            active._work_browser_readback_expectation = TrustedBrowserReadbackExpectation(
                task_id=str(task), session_id=session, run_id=str(run),
                expected_origin=url.rstrip("/"), read_path="/api/item",
                resource_id="qa-1",
                expected_fields=(("title", title), ("revision", 1)),
                revision_before=0, revision_after=1,
            )
            report["host_contract_armed_before_action"] = True

    register_pre_authorized_dispatch_hook(trusted_host_expectation)
    start = time.perf_counter()
    try:
        agent = AIAgent(
            provider=provider, model=model, base_url=base_url,
            api_key=os.environ["DEEPSEEK_API_KEY"],
            platform="desktop", session_id=session,
            enabled_toolsets=["browser", "desktop_ui"],
            max_iterations=8, max_tokens=1700, run_budget_seconds=120,
            skip_memory=True, skip_context_files=True,
            skip_background_review=True, quiet_mode=True,
        )
        if "work_execute" not in agent.valid_tool_names:
            raise RuntimeError("Desktop QA agent lacks canonical work_execute tool")
        report["canonical_work_tool_available"] = True
        prompt = (
            "Execute esta tarefa QA local autorizada em uma única sequência: "
            f"PRIMEIRO abra {url} no browser nativo integrado do Hermes; "
            f"DEPOIS digite exatamente '{title}' no campo Titulo; "
            "POR FIM clique em Salvar exatamente uma vez. "
            "Não utilize terminal nem navegador externo. Use browser_navigate, "
            "browser_type e browser_click; browser_snapshot só se necessário. "
            "Nunca repita o clique, mesmo em caso de timeout. "
            "Conclua com uma frase curta sobre o resultado."
        )
        result = agent.run_conversation(
            prompt, task_id="qa-turn-" + uuid4().hex[:9],
        )
        report["agent_turn_completed"] = result.get("completed") is True
        report["agent_turn_failed"] = result.get("failed") is True
        report["model_api_calls"] = result.get("api_calls")
        report["agent_work_outcome"] = (result.get("work_outcome") or {}).get("status")
        report["agent_response_preview"] = str(result.get("final_response") or "")[:200]
        observations = getattr(agent, "_work_tool_observations", None) or []
        report["model_tools_observed"] = [row.get("tool") for row in observations]
        report["tool_evidence"] = [
            {"action": row.get("tool"), "status": row.get("status"),
             "effect": row.get("effect"),
             "native_receipt": (row.get("native_browser_evidence") or {}).get("status")}
            for row in observations
        ]
        report["host_expectation_bound"] = isinstance(
            getattr(agent, "_work_browser_readback_expectation", None),
            TrustedBrowserReadbackExpectation,
        )
        report["agent_task_id"] = getattr(agent, "_canonical_work_task_id", None)
        report["agent_run_id"] = str(getattr(agent, "_canonical_work_run_id", "") or "")
        with urlopen(url + "api/item", timeout=4) as response:
            remote = json.load(response)
        report["fresh_qa_revision"] = remote.get("revision")
        report["fixture_matches_expected"] = remote == {
            "id": "qa-1", "title": title, "revision": 1,
        }
        with sqlite3.connect(root / "fixture.sqlite") as db:
            report["fixture_applied_operations"] = db.execute(
                "SELECT COUNT(*) FROM qa_applied_operations").fetchone()[0]
        task_id = report["agent_task_id"]
        with sqlite3.connect(root / "kanban-qa.db") as db:
            db.row_factory = sqlite3.Row
            task = kanban_db.get_task(db, task_id) if task_id else None
            task_run = kanban_db.latest_run(db, task_id) if task_id else None
            report["canonical_task_status"] = task.status if task else "missing"
            report["canonical_run_status"] = task_run.status if task_run else "missing"
            ws = ((task_run.metadata or {}).get("workstation") or {}) if task_run else {}
            outcome = ws.get("outcome") or {}
            report["canonical_verifiers"] = [
                item.get("verifier") for item in outcome.get("verifier_results", [])
            ]
            report["canonical_evidence_refs_count"] = len(
                outcome.get("evidence_refs") or [])
            report["canonical_acceptance"] = ws.get("acceptance_approved") is True
        report["status"] = (
            "verified_completed" if
            report["fixture_matches_expected"]
            and report["fixture_applied_operations"] == 1
            and report["canonical_task_status"] == "done"
            and report["canonical_run_status"] == "done"
            and report["canonical_acceptance"]
            and "native_browser_external_readback" in report["canonical_verifiers"]
            else "not_verified"
        )
    finally:
        report["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 1)
        report["browser_actions"] = dict(calls)
        report["browser_action_ms"] = {k: round(v, 1) for k, v in durations.items()}
        unregister_pre_authorized_dispatch_hook(trusted_host_expectation)
        browser._request_json = original_request
        if agent is not None:
            try:
                agent.close()
            except Exception:
                pass
        server.shutdown()
        server.server_close()
        service.join(timeout=3)


def main() -> int:
    root = Path(tempfile.gettempdir()) / ("hermes-native-agent-qa-" + uuid4().hex[:10])
    root.mkdir(parents=True, exist_ok=False)
    report = {"at": datetime.now(timezone.utc).isoformat(),
              "qa_dir": str(root), "status": "not_verified",
              "test": "real_AIAgent_run_conversation_native_Electron_temp_DB"}
    try:
        _run(root, report)
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error_preview"] = str(exc)[:160]
    finally:
        (root / "report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "verified_completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
