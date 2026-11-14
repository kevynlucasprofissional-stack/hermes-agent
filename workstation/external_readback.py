"""Read-only, owner-bound proof for explicitly supported external mutations.

Do not interpret dispatch success, HTTP 2xx or model text as persistence.
Supported:
- QA Trello title push: verified intent plus a new authenticated GET
- WhatsApp single send: stored causal delivery receipt from the native executor
Other external effects are not certifiable by this module.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any


SUPPORTED = frozenset({"workstation_db_trello_api_push", "whatsapp_send_message"})


def _decoded(raw: Any) -> dict:
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _trello_probe(args: dict, result: dict) -> dict | None:
    if result.get("ok") is not True or result.get("status") != "verified":
        return None
    from workstation.trello_sync_api import get_intent, _remote, QA_BOARD_ID
    from workstation.prefabs.trello import Credential, TrelloClient
    from workstation.trello_sync_push import shortlink
    card_id, review_run = args.get("card_id"), args.get("review_run_id")
    if not isinstance(card_id, str) or not isinstance(review_run, str):
        return None
    intent = get_intent(None, card_id, review_run)
    if (not intent or intent.get("state") != "verified"
            or intent.get("intent_id") != result.get("intent_id")
            or not isinstance(intent.get("target_title"), str)
            or not isinstance(intent.get("operation_id"), str)):
        return None
    before = _decoded(intent.get("readback_json"))
    client = TrelloClient(credential=Credential.from_secret_scope())
    remote = _remote(client, card_id)  # Fresh authorized GET; never a second PUT.
    if (remote.get("id") != card_id or remote.get("idBoard") != QA_BOARD_ID
            or remote.get("name") != intent["target_title"]
            or before.get("id") != card_id or before.get("name") != remote["name"]
            or shortlink(before["shortUrl"]) != shortlink(remote["shortUrl"])):
        return None
    return {"provider": "trello", "operation_id": intent["operation_id"],
            "resource_id": card_id, "field": "name",
            "expected_sha256": hashlib.sha256(intent["target_title"].encode()).hexdigest(),
            "observed_sha256": hashlib.sha256(remote["name"].encode()).hexdigest(),
            "source_kind": "authenticated_remote_get"}


def _whatsapp_row(operation_id: str) -> dict | None:
    from workstation.integrations.hermes.whatsapp_browser_executor import get_default_db_path
    configured = get_default_db_path()
    if not configured or not Path(configured).is_file():
        return None
    path = Path(configured).resolve()
    # Read-only SQLite connection. No schema writes, send, navigation or retry.
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=3) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT task_id,session_id,run_id,operation_id,message_digest,state,"
            "sent,message_data_id,ack_label,composer_empty_after "
            "FROM whatsapp_send_logs WHERE operation_id=?", (operation_id,)
        ).fetchone()
        return dict(row) if row else None


def _whatsapp_probe(args: dict, result: dict, *, task_id: str, session_id: str,
                    run_id: str, call_id: str) -> dict | None:
    # The model-facing tool schema intentionally omits TaskRun and operation
    # coordinates. Its authorized handler passes tool_call_id to the owner as
    # operation_id. Never infer ownership from model-provided arguments.
    op = call_id
    if (result.get("state") != "CONFIRMED" or result.get("sent") is not True
            or args.get("verify_delivery") is False
            or not isinstance(op, str) or not op
            or (args.get("operation_id") is not None and args["operation_id"] != op)
            or (args.get("task_id") is not None and args["task_id"] != task_id)
            or (args.get("kanban_card_id") is not None and args["kanban_card_id"] != task_id)
            or (args.get("run_id") is not None and str(args["run_id"]) != run_id)
            or (args.get("session_id") is not None and args["session_id"] != session_id)
            or not isinstance(args.get("message"), str)):
        return None
    row = _whatsapp_row(op)
    if not row or any(str(row.get(k)) != str(expected) for k, expected in (
            ("task_id", task_id), ("session_id", session_id),
            ("run_id", run_id), ("operation_id", op))):
        return None
    digest = hashlib.sha256(args["message"].encode("utf-8")).hexdigest()
    if (row.get("message_digest") != digest or row.get("state") != "CONFIRMED"
            or row.get("sent") != 1 or row.get("message_data_id") != result.get("message_data_id")
            or row.get("ack_label") != result.get("ack_label")
            or not isinstance(row.get("message_data_id"), str)
            or not row["message_data_id"].startswith("sha256:")
            or row.get("ack_label") not in {"sent", "delivered", "read"}):
        return None
    return {"provider": "whatsapp", "operation_id": op,
            "resource_id": row["message_data_id"], "field": "delivery_ack",
            "expected_sha256": digest, "observed_sha256": digest,
            "source_kind": "persisted_causal_browser_receipt"}


def capture_external_readback(
    tool: str, args: dict, raw: Any, *, task_id: str | None,
    session_id: str | None, run_id: str | int | None, call_id: str,
) -> dict | None:
    if (tool not in SUPPORTED or not isinstance(args, dict) or not task_id
            or not session_id or run_id is None or not call_id):
        return None
    try:
        result = _decoded(raw)
        if tool == "workstation_db_trello_api_push":
            source = _trello_probe(args, result)
        else:
            source = _whatsapp_probe(args, result, task_id=str(task_id),
                                     session_id=str(session_id), run_id=str(run_id),
                                     call_id=str(call_id))
        if not source:
            return None
        from workstation.artifacts import ArtifactStore
        payload = {**source, "task_id": str(task_id), "session_id": str(session_id),
                   "run_id": str(run_id), "call_id": str(call_id), "tool": tool,
                   "observed_at": datetime.now(timezone.utc).isoformat()}
        store = ArtifactStore()
        basename = hashlib.sha256(
            (tool + ":" + str(call_id) + ":" + source["operation_id"]).encode()
        ).hexdigest()
        saved = store.store(str(task_id), f"external_readback_{basename}.json", payload,
                            schema="hermes.external_mutation_readback.v1")
        reread = store.resolve_structured(saved.ref)
        if reread.get("content") != payload or reread.get("sha256") != saved.sha256:
            return None
        return {"evidence_ref": saved.ref, "sha256": saved.sha256,
                "task_id": str(task_id), "run_id": str(run_id),
                "call_id": str(call_id), "operation_id": source["operation_id"]}
    except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, RuntimeError):
        return None


def verify_external_receipt(item: dict, *, task_id: str, session_id: str,
                            run_id: str):
    """Reprobe authoritative source before accepting the persisted tool receipt."""
    from workstation.artifacts import ArtifactStore
    from workstation.contracts import EvidenceRef
    receipt = item.get("external_readback")
    if (not isinstance(receipt, dict) or not receipt.get("evidence_ref")
            or item.get("status") != "completed"
            or item.get("effect") not in {"MUTATION", "IDEMPOTENT_WRITE"}
            or item.get("tool") not in SUPPORTED):
        return None
    try:
        store = ArtifactStore()
        resolved = store.resolve_structured(receipt["evidence_ref"])
        p = resolved["content"]
        if (not isinstance(p, dict) or p.get("task_id") != task_id
                or p.get("session_id") != session_id or p.get("run_id") != run_id
                or p.get("call_id") != item.get("call_id")
                or p.get("tool") != item.get("tool")
                or p.get("operation_id") != receipt.get("operation_id")
                or resolved.get("sha256") != receipt.get("sha256")):
            return None
        if p["provider"] == "trello":
            from workstation.trello_sync_api import _remote, QA_BOARD_ID
            from workstation.prefabs.trello import Credential, TrelloClient
            fresh = _remote(TrelloClient(credential=Credential.from_secret_scope()),
                            p["resource_id"])
            if (fresh.get("idBoard") != QA_BOARD_ID
                    or hashlib.sha256(fresh["name"].encode()).hexdigest() != p["expected_sha256"]):
                return None
        elif p["provider"] == "whatsapp":
            row = _whatsapp_row(p["operation_id"])
            if (not row or str(row.get("task_id")) != task_id
                    or str(row.get("run_id")) != run_id
                    or str(row.get("session_id")) != session_id
                    or row.get("state") != "CONFIRMED" or row.get("sent") != 1
                    or row.get("message_digest") != p["expected_sha256"]
                    or row.get("message_data_id") != p["resource_id"]):
                return None
        else:
            return None
        verifier = "external_" + p["provider"] + "_readback"
        ref = EvidenceRef("external_mutation_readback", receipt["evidence_ref"],
                          sha256=resolved["sha256"], task_id=task_id, run_id=run_id,
                          operation_id=p["operation_id"], verifier=verifier)
        checked = {"verifier": verifier, "passed": True,
                   "evidence_ref": ref.uri, "task_id": task_id, "run_id": run_id,
                   "operation_id": p["operation_id"], "source_kind": p["source_kind"]}
        return ref, checked
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError, RuntimeError):
        return None
