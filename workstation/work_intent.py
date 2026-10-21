"""One transient operational decision, reusing canonical classifiers."""
from dataclasses import dataclass, field
import hashlib

from workstation.contracts import AcceptanceContract, MessageEnvelope, RiskLevel


# Whole utterances only: questions, negation, alternatives and extra effects must
# remain reasoning work. Recognition is independent of permission/capability.
_OPEN_COMMANDS = {
    f"{verb} {article}{name}": (family, target)
    for verb, article in (("abre", "o "), ("abra", "o "), ("abrir", "o "),
                          ("abre", ""), ("abra", ""), ("abrir", ""), ("open", ""))
    for name, family, target in (("trello", "browser.open_site", "https://trello.com/"),
                                 ("hyperframe", "creative.hyperframes.open", "hyperframes"),
                                 ("hyperframes", "creative.hyperframes.open", "hyperframes"))
}


def recognize_current_command(content: str) -> tuple[str, str] | None:
    if not isinstance(content, str):
        return None
    res = _OPEN_COMMANDS.get(" ".join(content.casefold().strip().rstrip(".!").split()))
    if res is not None:
        return res
    from workstation.creative_web_app_spec import recognize_open_creative_app
    app = recognize_open_creative_app(content)
    if app is not None:
        return ("creative.web_app.open", app.key)
    return None


def current_command_objective(envelope: MessageEnvelope, task_id: str, run_id: str) -> dict | None:
    """Propose a bounded goal; the existing router owns authority and execution."""
    command = recognize_current_command(envelope.content)
    if not envelope.can_create_work or command is None:
        return None
    from urllib.parse import urlsplit
    from workstation.control_plane.intent import OperationIntent
    from workstation.control_plane.ir import AND, CALL, EQ, SET
    family, target = command
    native = family in {"browser.open_site", "creative.web_app.open"}
    if family == "browser.open_site":
        parsed = urlsplit(target)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            return None
        # The native Browser owner verifies host/page_family/recovery_state.
        # An intent against an opaque "url" field cannot be certified against
        # that learned contract. Describe the exact native effects without
        # broadening the requested destination or bypassing its owner.
        host = parsed.hostname
        page_family = parsed.path or "/"
        goal = AND(EQ("host", host), EQ("page_family", page_family), EQ("recovery_state", "live"))
        effect_budget = [
            SET("url", target),
            SET("host", host),
            SET("page_family", page_family),
            SET("recovery_state", "live"),
            # The user's allowlisted open-site request explicitly budgets
            # navigation on this exact host, never arbitrary Browser calls.
            CALL("browser.navigate", host),
        ]
        inputs = {}
    elif family == "creative.web_app.open":
        host = "127.0.0.1"
        page_family = "/"
        goal = AND(EQ("host", host), EQ(f"creative.{target}.ready", True))
        effect_budget = [
            SET("host", host),
            SET(f"creative.{target}.ready", True),
            CALL("browser.navigate", host),
        ]
        inputs = {"engine": target}
    else:
        goal = EQ("creative.studio.ready", True)
        effect_budget = [SET("creative.studio.ready", True)]
        inputs = {"engine": target}
    operation_id = "op_current_" + hashlib.sha256(
        f"{task_id}:{run_id}:{envelope.content}".encode()).hexdigest()[:24]
    intent = OperationIntent(id=operation_id, target="native_browser" if native else "creative_studio",
        goal=goal, effect_budget=effect_budget,
        metadata={"operation_family": family, "recognition": "deterministic_alias"})
    return {"operation_id": operation_id, "operation_intent": intent.to_dict(),
            # Fixed named-site commands are fully bound by the typed goal/effect.
            # Do not inject an undeclared url input into a promoted capability.
            "inputs": inputs}


@dataclass(slots=True)
class WorkIntent:
    execution_class: str
    requires_task: bool
    requires_browser: bool
    requires_worker: bool
    durability: str
    risk: RiskLevel
    acceptance_policy: AcceptanceContract
    handoff_policy: str = "explicit"
    repeatability_hint: bool = False
    constraints: dict = field(default_factory=dict)
    admission_kind: str = "conversation"


def work_intent(envelope: MessageEnvelope, structured: dict | None = None) -> WorkIntent:
    from workstation.kanban import is_multistep_request
    from workstation.task_compiler import batch_intent, classify
    kind = classify(structured or {}).value
    steps = (structured or {}).get("steps", [])
    command = recognize_current_command(envelope.content)
    browser = command is not None or any(str(s.get("tool", "")).startswith("browser_") for s in steps)
    durable = bool(structured and any(structured.get(k) for k in ("steps", "items", "operation_intent", "capability_id")))
    durable = durable or batch_intent(envelope.content) or is_multistep_request(envelope.content)
    if isinstance(envelope.metadata, dict) and envelope.metadata.get("explicit_force_work") is True:
        durable = True
    # P05 Creative Preflight: attach clarification metadata when a design task
    # lacks dimensions. The router/caller dispatches the clarify tool; this
    # function remains pure and never blocks point commands or dimensioned requests.
    creative_preflight_payload = None
    if durable and command is None and envelope.can_create_work:
        try:
            from workstation.creative_preflight import build_clarify_payload, check_creative_preflight
            task_context = (structured or {}).get("task_context") if isinstance(structured, dict) else None
            preflight_result = check_creative_preflight(envelope.content, task_context=task_context)
            creative_preflight_payload = build_clarify_payload(preflight_result)
        except Exception:  # health: allow BLE001 -- preflight failure must never block intent classification
            creative_preflight_payload = None
    requires_task = bool(envelope.can_create_work and durable)
    admission_kind = "durable_task" if requires_task else "point_action" if command is not None else "conversation"
    intent = WorkIntent(kind, requires_task, browser, False, "durable" if durable else "turn",
                        RiskLevel.MEDIUM if durable else RiskLevel.LOW,
                        AcceptanceContract(), repeatability_hint=durable,
                        constraints=(structured or {}).get("constraints", {}),
                        admission_kind=admission_kind)
    if creative_preflight_payload is not None:
        intent.constraints["creative_preflight"] = creative_preflight_payload
    return intent


def prepare_turn_work(agent, content, envelope: MessageEnvelope | None = None) -> WorkIntent:
    """Bind trusted ingress to canonical work without changing the prompt or schema."""
    from workstation.contracts import MessageOrigin, IntentAuthority
    from workstation.task_compiler import batch_intent
    root = getattr(agent, "_conversation_root_id", lambda: None)()
    session_id = str(root or getattr(agent, "session_id", None) or "")
    if envelope is None:
        envelope = MessageEnvelope(MessageOrigin.RUNTIME, IntentAuthority.OBSERVATION_ONLY,
                                   session_id, content if isinstance(content, str) else "")
    if not isinstance(envelope, MessageEnvelope) or envelope.session_id != session_id:
        raise ValueError("Message envelope must belong to the owning conversation")
    intent = work_intent(envelope)
    agent._message_envelope = envelope
    agent._work_intent = intent
    agent._work_repeatability_hint = batch_intent(envelope.content)
    # A conversation is not the work lease. The old TaskRun cannot leak into
    # a new turn that only asks a question or performs a one-shot action.
    if not intent.requires_task:
        # Point actions do not CREATE work. An explicitly attached, still-live
        # canonical TaskRun may nevertheless execute its own exact objective.
        # This exception never adopts a different run or unrelated conversation.
        prebound_task = getattr(agent, "_canonical_work_task_id", None)
        prebound_run = getattr(agent, "_canonical_work_run_id", None)
        prior_turn_id = getattr(agent, "_canonical_work_turn_id", None)
        keep_explicit = False
        if (prebound_task and prebound_run is not None and envelope.can_create_work
                # Neither absent nor empty lineage identifies the current turn.
                and envelope.correlation_id
                and prior_turn_id == envelope.correlation_id):
            from hermes_cli import kanban_db
            from workstation.kanban import WorkstationKanbanBridge
            with WorkstationKanbanBridge().get_connection() as conn:
                live = kanban_db.get_task(conn, prebound_task)
            keep_explicit = bool(
                live is not None and live.session_id == session_id
                and live.body == envelope.content and live.status == "running"
                and str(live.current_run_id) == str(prebound_run)
            )
        if not keep_explicit and hasattr(agent, "_canonical_work_task_id"):
            agent._canonical_work_task_id = None
            agent._canonical_work_run_id = None
        agent._work_blocked_task_id = None
        return intent

    from workstation.kanban import WorkstationKanbanBridge
    from hermes_cli import kanban_db
    bridge = WorkstationKanbanBridge()
    current_id = getattr(agent, "_canonical_work_task_id", None)
    current_run_id = None
    blocked_id = None
    if current_id:
        with bridge.get_connection() as conn:
            current = kanban_db.get_task(conn, current_id)
        if current is None or current.session_id != session_id or current.body != envelope.content:
            current_id = None
        elif current.status in {"blocked", "cancelled", "done", "archived", "scheduled"}:
            blocked_id = current_id if current.status == "blocked" else None
            current_id = None
        elif current.status == "running":
            # A legitimately pinned in-flight execution survives repeated entry
            # only when run, objective, session and trusted turn lineage agree.
            # No new run is adopted merely because it belongs to this session.
            pinned_run = getattr(agent, "_canonical_work_run_id", None)
            pinned_turn = getattr(agent, "_canonical_work_turn_id", None)
            if (pinned_run is not None
                    and str(current.current_run_id) == str(pinned_run)
                    and envelope.can_create_work
                    # A missing turn correlation cannot prove a run belongs
                    # to this turn; fail closed rather than adopting an old run.
                    and envelope.correlation_id
                    and pinned_turn == envelope.correlation_id):
                current_run_id = current.current_run_id
            else:
                blocked_id = current_id
                current_id = None
        else:
            current_run_id = current.current_run_id
    if current_id is None and blocked_id is None:
        # Restore unfinished work without lending a previous TaskRun's lease.
        # Completed work is excluded: the same objective can be requested again.
        with bridge.get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM tasks WHERE session_id=? AND body=? "
                "AND created_by='workstation' "
                "AND status IN ('triage','todo','ready','running','blocked','scheduled') "
                "ORDER BY created_at DESC, id DESC LIMIT 1",
                (session_id, envelope.content),
            ).fetchone()
            existing = kanban_db.get_task(conn, row[0]) if row else None
        if existing is not None:
            if existing.status in {"triage", "todo", "ready"} and existing.current_run_id is None:
                current_id = existing.id
            else:
                blocked_id = existing.id
    if current_id is None and blocked_id is None:
        created = bridge.promote_request_if_multistep(
            envelope.content, session_id=session_id, envelope=envelope,
            acceptance_contract=intent.acceptance_policy, defer_execution=True)
        if created:
            with bridge.get_connection() as conn:
                current = kanban_db.get_task(conn, created)
            if current and current.session_id == session_id and current.body == envelope.content:
                if current.status in {"triage", "todo", "ready"} and current.current_run_id is None:
                    current_id = created
                else:
                    blocked_id = created
    agent._canonical_work_task_id = current_id
    agent._canonical_work_run_id = current_run_id
    agent._canonical_work_turn_id = envelope.correlation_id
    agent._work_blocked_task_id = blocked_id
    return intent
