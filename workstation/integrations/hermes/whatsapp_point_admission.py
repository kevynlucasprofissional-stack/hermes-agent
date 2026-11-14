"""Lazy canonical TaskRun for one authorized, model-selected WhatsApp send.

No AI-generated IDs, no human modal, no work_execute plan for one message.
The same Kanban owner still controls task/run claims and replay.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json

from workstation.contracts import MessageEnvelope
from workstation.task_compiler import current_work_execution_identity, execution_context


@contextmanager
def admitted_whatsapp_point_send(
    agent, args: dict, call_id: str, *,
    tool_family: str = "whatsapp_send_message",
):
    """Bind an authenticated single send to a real claimed TaskRun at dispatch."""
    if tool_family not in {"whatsapp_send_message", "whatsapp_send_batch", "whatsapp_campaign_execute"}:
        raise PermissionError("WHATSAPP_UNSUPPORTED_TOOL_FAMILY")
    # A compiled work_execute step already owns its canonical run.
    if current_work_execution_identity() is not None:
        yield
        return

    envelope = getattr(agent, "_message_envelope", None)
    owner = str(getattr(agent, "_conversation_root_id", lambda: None)()
                or getattr(agent, "session_id", "") or "")
    # The default Desktop TurnIngress need not supply a correlation_id.
    # The conversation loop generates a server-owned current turn ID after
    # admission and before dispatch; never read a model-provided identifier.
    turn_id = (
        (envelope.correlation_id if isinstance(envelope, MessageEnvelope) else None)
        or getattr(agent, "_current_turn_id", None)
    )
    if (not isinstance(envelope, MessageEnvelope)
            or not envelope.can_create_work or envelope.session_id != owner
            or not isinstance(turn_id, str) or not turn_id.strip()
            or not isinstance(call_id, str) or not call_id.strip()):
        raise PermissionError("WHATSAPP_TRUSTED_TURN_REQUIRED")
    campaign = tool_family == "whatsapp_campaign_execute"
    if campaign:
        source_dir = args.get("source_dir") if isinstance(args, dict) else None
        request = str(envelope.content or "").replace("/", "\\").casefold()
        if (not isinstance(source_dir, str) or not source_dir.strip()
                or len(source_dir) > 512
                or source_dir.replace("/", "\\").casefold() not in request):
            raise PermissionError("WHATSAPP_CAMPAIGN_SOURCE_NOT_AUTHORIZED")
    named = isinstance(args, dict) and isinstance(args.get("target_name"), str)
    referenced = isinstance(args, dict) and isinstance(args.get("recipient_ref"), dict)
    if not campaign and (not isinstance(args, dict) or named == referenced
            or (named and ("recipient_ref" in args or "expected_recipient_name" in args))
            or (not named and (not isinstance(args.get("expected_recipient_name"), str)
                               or not args["expected_recipient_name"].strip()))
            or not isinstance(args.get("message"), str)
            or not args["message"].strip()):
        raise ValueError("WHATSAPP_SINGLE_SEND_ARGUMENTS_REQUIRED")
    if named:
        # Name-only discovery must be grounded in the authenticated user's
        # literal request, not a fresh label invented by the model.
        import unicodedata
        def fold(value: str) -> str:
            s = unicodedata.normalize("NFKD", value)
            return "".join(ch for ch in s if not unicodedata.combining(ch)).casefold()
        request_text = envelope.content if isinstance(envelope.content, str) else ""
        if (not 3 <= len(args["target_name"].strip()) <= 100
                or fold(args["target_name"].strip()) not in fold(request_text)):
            raise PermissionError("WHATSAPP_REQUESTED_TARGET_MISMATCH")
    if (getattr(agent, "_whatsapp_point_turn_id", None) == turn_id
            and getattr(agent, "_whatsapp_point_call_id", None)):
        raise PermissionError("WHATSAPP_POINT_ALREADY_DISPATCHED")

    from hermes_cli import kanban_db
    from workstation.kanban import WorkstationKanbanBridge

    bridge = WorkstationKanbanBridge()
    task_id = getattr(agent, "_canonical_work_task_id", None)
    old_turn = getattr(agent, "_canonical_work_turn_id", None)
    # A durable task can be triaged at ingress *before* the runtime stamps
    # its turn ID. An empty old_turn is not an authority grant: the atomic
    # claim below still verifies exact owner, objective and unclaimed status.
    if task_id and old_turn and old_turn != turn_id:
        raise PermissionError("WHATSAPP_STALE_TURN_AUTHORITY")
    if task_id and getattr(agent, "_canonical_work_run_id", None) is not None:
        raise PermissionError("WHATSAPP_RUN_ALREADY_ACTIVE")

    if task_id is None:
        key = "whatsapp-point:" + hashlib.sha256(json.dumps(
            [owner, turn_id, tool_family],
            ensure_ascii=False, separators=(",", ":"),
        ).encode()).hexdigest()
        with bridge.get_connection() as conn:
            # Create once even if two tool workers race for the same turn.
            conn.execute("BEGIN IMMEDIATE")
            task_id = kanban_db.create_task(
                conn, title=("WhatsApp campanha" if tool_family == "whatsapp_campaign_execute"
                             else "WhatsApp lote" if tool_family == "whatsapp_send_batch"
                             else "WhatsApp individual"), body=envelope.content,
                created_by="workstation", session_id=owner,
                workspace_kind="scratch", triage=True, idempotency_key=key,
            )
            conn.commit()

    # start_triaged_task validates session, objective, status and claim via
    # Kanban's existing atomic CAS. Blocked/running tasks aren't reopened.
    try:
        run_id = bridge.start_triaged_task(task_id, session_id=owner,
                                          objective=envelope.content)
    except (RuntimeError, PermissionError) as exc:
        raise PermissionError("WHATSAPP_POINT_RUN_UNCLAIMABLE") from exc
    agent._canonical_work_task_id = task_id
    agent._canonical_work_run_id = run_id
    agent._canonical_work_turn_id = turn_id
    agent._whatsapp_point_call_id = call_id
    agent._whatsapp_point_turn_id = turn_id
    # Kanban ownership follows the conversation root; BrowserTask control and
    # the model-facing tool call use the current (possibly rotated) session.
    live_session = str(getattr(agent, "session_id", "") or "")
    with execution_context(lambda *a, **kw: None, live_session,
                           canonical_task_id=task_id, canonical_run_id=run_id):
        yield


@contextmanager
def admitted_whatsapp_campaign_send(agent, args: dict, call_id: str):
    """Claim a TaskRun only for a campaign path in the trusted user turn."""
    with admitted_whatsapp_point_send(
        agent, args, call_id, tool_family="whatsapp_campaign_execute",
    ):
        yield


@contextmanager
def admitted_whatsapp_batch_send(agent, args: dict, call_id: str):
    """Claim one TaskRun for a short, explicit, user-authored batch.

    Unlike a campaign sourced from a database, every contact and exact body
    must be present in the authenticated current user turn. Reuse the point
    admission and its canonical TaskRun; never mint authority per item.
    """
    import unicodedata

    items = args.get("items") if isinstance(args, dict) else None
    if not isinstance(items, list) or not 2 <= len(items) <= 5:
        raise ValueError("WHATSAPP_BATCH_SIZE_INVALID")
    envelope = getattr(agent, "_message_envelope", None)
    if not isinstance(envelope, MessageEnvelope) or not isinstance(envelope.content, str):
        raise PermissionError("WHATSAPP_TRUSTED_TURN_REQUIRED")

    def fold(value: str) -> str:
        s = unicodedata.normalize("NFKD", value)
        return "".join(c for c in s if not unicodedata.combining(c)).casefold()

    request_text = fold(envelope.content)
    for item in items:
        if not isinstance(item, dict) or set(item) - {
            "target_name", "recipient_ref", "expected_recipient_name", "message",
        }:
            raise ValueError("WHATSAPP_BATCH_ARGUMENTS_INVALID")
        name = item.get("target_name")
        ref = item.get("recipient_ref")
        body = item.get("message")
        if (not isinstance(body, str) or not body.strip() or len(body) > 2000
                or fold(body) not in request_text):
            raise PermissionError("WHATSAPP_BATCH_MESSAGE_NOT_AUTHORIZED")
        if isinstance(name, str) and not ref:
            if not 3 <= len(name.strip()) <= 100 or fold(name.strip()) not in request_text:
                raise PermissionError("WHATSAPP_REQUESTED_TARGET_MISMATCH")
        elif isinstance(ref, dict) and name is None:
            label = item.get("expected_recipient_name")
            if not isinstance(label, str) or not 3 <= len(label.strip()) <= 128:
                raise ValueError("WHATSAPP_BATCH_NAME_REQUIRED")
            is_self = ref.get("source") == "hermes_local" and ref.get("contact_id") == 1
            if (fold(label.strip()) not in request_text
                    and not (is_self and any(x in request_text for x in
                                             ("autochat", "(voce)", "para mim")))):
                raise PermissionError("WHATSAPP_REQUESTED_TARGET_MISMATCH")
        else:
            raise ValueError("WHATSAPP_BATCH_RECIPIENT_AMBIGUOUS")

    # The same host-owned TaskRun authorizes this manifest as a unit.
    with admitted_whatsapp_point_send(
        agent, items[0], call_id, tool_family="whatsapp_send_batch",
    ):
        yield
