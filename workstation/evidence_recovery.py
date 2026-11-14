"""Bounded read-only reconciliation for uncertain external Kanban effects.

A child task never repeats a write. When the child really completes, the
source owner is independently reprobed and the original parent is concluded
through the canonical acceptance gate. Unknown effects cannot be certified.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import logging
import sqlite3

_log = logging.getLogger(__name__)
_TABLE = "workstation_evidence_recovery"


def _ensure_table(conn):
    conn.execute(f"""CREATE TABLE IF NOT EXISTS {_TABLE}(
        parent_task_id TEXT PRIMARY KEY,
        child_task_id TEXT UNIQUE NOT NULL,
        origin_session_id TEXT NOT NULL,
        original_run_id TEXT NOT NULL,
        descriptors_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL)""")


def _descriptor(item):
    if not isinstance(item, dict) or item.get("no_effect") is True:
        # Definitive pre-send refusal: no external write exists to recover.
        return None
    if item.get("effect") not in {"MUTATION", "IDEMPOTENT_WRITE"}:
        return None
    if item.get("status") not in {"started", "completed", "failed", "unknown"}:
        return None
    tool = item.get("tool")
    info = item.get("recovery_descriptor")
    from workstation.external_readback import SUPPORTED
    if tool in SUPPORTED and isinstance(info, dict) and info.get("tool") == tool:
        if tool == "workstation_db_trello_api_push":
            if not info.get("card_id") or not info.get("review_run_id"):
                return None
            return {k: info[k] for k in ("tool", "card_id", "review_run_id")}
        if tool == "whatsapp_send_message" and info.get("operation_id"):
            return {"tool": tool, "operation_id": info["operation_id"]}
    return None


def schedule_recovery(*, task_id: str, session_id: str, run_id: int,
                      observed_tools: list[dict] | None, pending: list[str],
                      board=None) -> str | None:
    """Child is ready to probe; parent awaits it, rather than being parked."""
    if not observed_tools or not pending:
        return None
    descriptors = []
    for item in observed_tools:
        if not isinstance(item, dict):
            return None
        if item.get("effect") in {"PURE_READ", "DISCOVERY"}:
            # A failed source read cannot be erased by a recovered mutation.
            if item.get("status") != "completed":
                return None
            continue
        if item.get("effect") not in {"MUTATION", "IDEMPOTENT_WRITE"}:
            # Interactive/unknown effects cannot borrow unrelated proof.
            return None
        descriptor = _descriptor(item)
        if descriptor is None:
            return None
        descriptors.append(descriptor)
    if not descriptors:
        return None
    from workstation.kanban import WorkstationKanbanBridge
    from workstation.contracts import DiscoveredTask, AcceptanceContract
    from hermes_cli import kanban_db
    bridge = WorkstationKanbanBridge(board=board)
    with bridge.get_connection() as conn:
        _ensure_table(conn)
        row = conn.execute(
            f"SELECT child_task_id FROM {_TABLE} WHERE parent_task_id=?", (task_id,)
        ).fetchone()
        if row:
            # A previous child cannot be rescheduled as though it were new
            # work. When the source becomes available, the resumed parent is
            # reconciled by try_recover_running_parent, never by replay.
            return None
        parent = kanban_db.get_task(conn, task_id)
        if (parent is None or parent.session_id != session_id
                or parent.current_run_id != int(run_id) or parent.status != "running"):
            return None

    names = ", ".join(sorted(set(d["tool"] for d in descriptors)))
    followup = DiscoveredTask(
        title=f"Verificar evidências externas de {task_id}",
        parent_task_id=task_id, discovered_by="workstation",
        origin_session_id=session_id, required_for_parent=True,
        reason=(
            f"Investigação somente leitura da tarefa {task_id} / execução {run_id}. "
            f"Operações: {names}. "
            f"Alvos seguros para consulta: {json.dumps(descriptors, ensure_ascii=False)}. "
            "Primeiro consulte a fonte autorizada e os recibos persistidos; "
            "depois confirme a situação e reporte as divergências. "
            "Não reenvie mensagens, não faça PUT/POST/PATCH/DELETE, não execute "
            "o objetivo original e não repita operações incertas. "
            "O sistema verificará novamente a fonte antes de finalizar o pai."
        ),
    )
    child = bridge.record_discovered_followup(task_id, followup)
    with bridge.get_connection() as conn:
        _ensure_table(conn)
        parent = kanban_db.get_task(conn, task_id)
        # Dependency creates TODO rather than a stuck human BLOCKED card.
        if not parent or parent.status != "todo":
            raise RuntimeError("recovery_child_parent_dependency_not_established")
        conn.execute(
            f"INSERT OR IGNORE INTO {_TABLE} "
            "(parent_task_id,child_task_id,origin_session_id,original_run_id,"
            "descriptors_json,status,created_at) VALUES (?,?,?,?,?,'pending',?)",
            (task_id, child, session_id, str(run_id),
             json.dumps(descriptors, sort_keys=True),
             datetime.now(timezone.utc).isoformat()),
        )
        conn.execute(
            "INSERT OR IGNORE INTO task_acceptance_contracts(task_id,contract_json)"
            " VALUES (?,?)",
            (child, json.dumps(asdict(AcceptanceContract(policy="advisory")))),
        )
        conn.commit()
    return child


def enforce_recovery_scope(task_id: str | None, tool: str, args: dict | None) -> None:
    if not task_id:
        return
    from workstation.kanban import WorkstationKanbanBridge
    from tools.effects import READ_EFFECTS, tool_effect
    try:
        with WorkstationKanbanBridge().get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (_TABLE,),
            ).fetchone()
            if not row:
                return
            role = conn.execute(
                f"SELECT CASE WHEN child_task_id=? THEN 'child' ELSE 'parent' END "
                f"FROM {_TABLE} WHERE (child_task_id=? OR parent_task_id=?) "
                "AND status IN ('pending','needs_verifier') LIMIT 1",
                (task_id, task_id, task_id),
            ).fetchone()
    except (sqlite3.Error, OSError):
        # If the recovery record cannot be checked, no unsafe bypass.
        raise PermissionError("evidence_recovery_authority_unavailable")
    if role and tool_effect(tool, args=args) not in READ_EFFECTS:
        raise PermissionError(
            "evidence_recovery_read_only: original external mutation may already exist"
        )


def _owner_reprobe(descriptor: dict, *, task_id: str, original_run_id: str,
                   session_id: str, child_id: str):
    from workstation.artifacts import ArtifactStore
    from workstation.contracts import EvidenceRef
    tool = descriptor["tool"]
    if tool == "workstation_db_trello_api_push":
        from workstation.trello_sync_api import _remote, get_intent, QA_BOARD_ID
        from workstation.prefabs.trello import Credential, TrelloClient
        intent = get_intent(None, descriptor["card_id"], descriptor["review_run_id"])
        if (not intent or intent.get("state") not in {"verified", "uncertain"}
                or not intent.get("operation_id") or not intent.get("target_title")):
            return None
        # An UNCERTAIN intent is reconcilable only if it crossed the PUT
        # dispatch boundary. "local_changed_after_intent" is pre-dispatch
        # uncertainty: it must never be promoted to a successful mutation.
        if intent["state"] == "uncertain":
            if (intent.get("failure_reason") not in {
                    "api_put_result_unknown", "api_response_unverified",
                    "api_readback_mismatch", "api_readback_unavailable"}
                    or not isinstance(intent.get("remote_before"), str)
                    or intent["remote_before"] == intent["target_title"]):
                return None
        observed = _remote(TrelloClient(credential=Credential.from_secret_scope()),
                           descriptor["card_id"])
        if (observed.get("idBoard") != QA_BOARD_ID
                or observed.get("name") != intent["target_title"]):
            return None
        op_id = intent["operation_id"]
        resource_hash = hashlib.sha256(observed["name"].encode()).hexdigest()
        origin = "authenticated_remote_get"
    elif tool == "whatsapp_send_message":
        from workstation.external_readback import _whatsapp_row
        row = _whatsapp_row(descriptor["operation_id"])
        if (not row or str(row.get("task_id")) != task_id
                or str(row.get("session_id")) != session_id
                or str(row.get("run_id")) != original_run_id
                or row.get("state") != "CONFIRMED" or row.get("sent") != 1
                or row.get("ack_label") not in {"sent", "delivered", "read"}
                or not isinstance(row.get("message_data_id"), str)
                or not row["message_data_id"].startswith("sha256:")):
            return None
        op_id = row["operation_id"]
        resource_hash = row["message_digest"]
        origin = "persisted_causal_browser_receipt"
    else:
        return None
    payload = {
        "task_id": task_id, "session_id": session_id,
        "original_run_id": original_run_id, "recovery_child_id": child_id,
        "operation_id": op_id, "tool": tool, "resource_hash": resource_hash,
        "source_kind": origin,
    }
    store = ArtifactStore()
    name = hashlib.sha256((child_id + op_id).encode()).hexdigest()
    saved = store.store(task_id, f"recovered_external_{name}.json", payload,
                        schema="hermes.external_recovery_v1")
    verified = store.resolve_structured(saved.ref)
    if verified.get("content") != payload or verified.get("sha256") != saved.sha256:
        return None
    label = "recovered_" + tool
    ref = EvidenceRef("recovered_external_readback", saved.ref, sha256=saved.sha256,
                      task_id=task_id, run_id=original_run_id,
                      operation_id=op_id, verifier=label)
    check = {"verifier": label, "passed": True, "evidence_ref": saved.ref,
             "task_id": task_id, "original_run_id": original_run_id,
             "operation_id": op_id, "source_kind": origin}
    return ref, check


def on_recovery_child_completed(*, task_id: str, board=None, **_kwargs):
    """Called AFTER child's canonical DONE commit, with no mutation retry."""
    from workstation.kanban import WorkstationKanbanBridge
    from workstation.contracts import BrowserTaskReport, OutcomeStatus
    from hermes_cli import kanban_db
    bridge = WorkstationKanbanBridge(board=board)
    with bridge.get_connection() as conn:
        if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (_TABLE,)
        ).fetchone():
            return
        row = conn.execute(
            f"SELECT parent_task_id,origin_session_id,original_run_id,"
            f"descriptors_json,status FROM {_TABLE} WHERE child_task_id=?",
            (task_id,),
        ).fetchone()
        if not row or row["status"] != "pending":
            return
        child = kanban_db.get_task(conn, task_id)
        child_run = kanban_db.latest_run(conn, task_id)
        metadata = child_run.metadata if child_run and isinstance(child_run.metadata, dict) else {}
        ws = metadata.get("workstation") or {}
        if (child is None or child.status != "done" or
                ws.get("acceptance_approved") is not True or
                ws.get("outcome", {}).get("status") != "verified_completed"):
            return
        parent_id, session_id, original_run = (
            row["parent_task_id"], row["origin_session_id"], row["original_run_id"]
        )
        descriptors = json.loads(row["descriptors_json"])
    evidence, checks = [], []
    try:
        for descriptor in descriptors:
            receipt = _owner_reprobe(
                descriptor, task_id=parent_id, original_run_id=original_run,
                session_id=session_id, child_id=task_id,
            )
            if receipt is None:
                raise ValueError("source_readback_not_verified")
            ref, check = receipt
            evidence.append(ref)
            checks.append(check)
    except Exception:
        _log.warning("Read-only child finished but original external state is not verified",
                     exc_info=True)
        with bridge.get_connection() as conn:
            conn.execute(
                f"UPDATE {_TABLE} SET status='needs_verifier' "
                "WHERE child_task_id=? AND status='pending'", (task_id,),
            )
            kanban_db.block_task(
                conn, parent_id, reason="Recovery has no verified source readback",
                kind="capability",
            )
        return
    with bridge.get_connection() as conn:
        parent = kanban_db.get_task(conn, parent_id)
        if not parent or parent.status != "ready" or parent.session_id != session_id:
            return
        claimed = kanban_db.claim_task(
            conn, parent_id, claimer=f"workstation:recovered:{task_id}",
        )
        if not claimed or not claimed.current_run_id:
            return
        new_run = claimed.current_run_id
    report = BrowserTaskReport(
        parent_id, session_id, parent.body or parent.title,
        f"Recovered {len(checks)} external operation(s) by independent owner readback.",
        True, evidence=evidence, verifier_results=checks,
        deliverables=[ref.uri for ref in evidence],
        outcome_status=OutcomeStatus.VERIFIED_COMPLETED,
        run_id=str(new_run),
    )
    accepted = bridge.complete_task_with_report(parent_id, report,
                                                expected_run_id=int(new_run))
    if accepted:
        with bridge.get_connection() as conn:
            conn.execute(
                f"UPDATE {_TABLE} SET status='completed' WHERE parent_task_id=?",
                (parent_id,),
            )
            conn.commit()


def try_recover_running_parent(*, task_id: str, session_id: str,
                               run_id: int, board=None):
    """Read-only recovery on a newly claimed parent run after prior HOLD.

    A fresh run never reissues the original external effect. Only a verified
    original child and a fresh owner readback can satisfy canonical acceptance.
    """
    from workstation.kanban import WorkstationKanbanBridge
    from workstation.contracts import BrowserTaskReport, OutcomeStatus
    from hermes_cli import kanban_db
    bridge = WorkstationKanbanBridge(board=board)
    with bridge.get_connection() as conn:
        if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (_TABLE,)
        ).fetchone():
            return None
        row = conn.execute(
            f"SELECT child_task_id,origin_session_id,original_run_id,"
            f"descriptors_json,status FROM {_TABLE} WHERE parent_task_id=?",
            (task_id,),
        ).fetchone()
        parent = kanban_db.get_task(conn, task_id)
        if (not row or row["status"] not in {"pending", "needs_verifier"}
                or not parent or parent.status != "running"
                or parent.session_id != session_id
                or parent.current_run_id != int(run_id)
                or row["origin_session_id"] != session_id):
            return None
        child = kanban_db.get_task(conn, row["child_task_id"])
        child_run = kanban_db.latest_run(conn, row["child_task_id"])
        ws = (child_run.metadata.get("workstation") or {}
              if child_run and isinstance(child_run.metadata, dict) else {})
        if (not child or child.status != "done"
                or ws.get("acceptance_approved") is not True
                or ws.get("outcome", {}).get("status") != "verified_completed"):
            return None
        descriptors = json.loads(row["descriptors_json"])
        original_run_id = row["original_run_id"]
        child_id = row["child_task_id"]
    evidence, checks = [], []
    for descriptor in descriptors:
        try:
            proof = _owner_reprobe(descriptor, task_id=task_id,
                                   original_run_id=original_run_id,
                                   session_id=session_id, child_id=child_id)
        except Exception:
            _log.warning("Resumed source readback is not yet available", exc_info=True)
            return None
        if proof is None:
            return None
        ref, check = proof
        evidence.append(ref)
        checks.append(check)
    if not evidence:
        return None
    report = BrowserTaskReport(
        task_id, session_id, parent.body or parent.title,
        f"Recovered {len(checks)} external operation(s) using owner readback.",
        True, evidence=evidence, verifier_results=checks,
        deliverables=[r.uri for r in evidence],
        outcome_status=OutcomeStatus.VERIFIED_COMPLETED, run_id=str(run_id),
    )
    if not bridge.complete_task_with_report(task_id, report, expected_run_id=int(run_id)):
        return None
    with bridge.get_connection() as conn:
        conn.execute(f"UPDATE {_TABLE} SET status='completed' WHERE parent_task_id=?",
                     (task_id,))
        conn.commit()
    return {"task_id": task_id, "status": "verified_completed",
            "acceptance_approved": True, "run_id": str(run_id),
            "receipt_source": "read_only_recovery"}
