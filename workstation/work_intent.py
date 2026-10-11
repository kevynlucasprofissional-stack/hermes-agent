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
    return _OPEN_COMMANDS.get(" ".join(content.casefold().strip().rstrip(".!").split()))


def current_command_objective(envelope: MessageEnvelope, task_id: str, run_id: str) -> dict | None:
    """Propose a bounded goal; the existing router owns authority and execution."""
    command = recognize_current_command(envelope.content)
    if not envelope.can_create_work or command is None:
        return None
    from workstation.control_plane.intent import OperationIntent
    from workstation.control_plane.ir import EQ, SET
    family, target = command
    native = family == "browser.open_site"
    path = "url" if native else "creative.studio.ready"
    value = target if native else True
    operation_id = "op_current_" + hashlib.sha256(
        f"{task_id}:{run_id}:{envelope.content}".encode("utf-8")).hexdigest()[:24]
    intent = OperationIntent(id=operation_id, target="native_browser" if native else "creative_studio",
        goal=EQ(path, value), effect_budget=[SET(path, value)],
        metadata={"operation_family": family, "recognition": "deterministic_alias"})
    return {"operation_id": operation_id, "operation_intent": intent.to_dict(),
            "inputs": {"url": target} if native else {"engine": target}}


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


def work_intent(envelope: MessageEnvelope, structured: dict | None = None) -> WorkIntent:
    from workstation.kanban import is_multistep_request
    from workstation.task_compiler import batch_intent, classify
    kind = classify(structured or {}).value
    steps = (structured or {}).get("steps", [])
    command = recognize_current_command(envelope.content)
    browser = command is not None or any(str(s.get("tool", "")).startswith("browser_") for s in steps)
    durable = structured is not None or batch_intent(envelope.content)
    requires_task = envelope.can_create_work and (command is not None or durable or is_multistep_request(envelope.content))
    return WorkIntent(kind, requires_task, browser, False, "durable" if durable else "turn",
                      RiskLevel.MEDIUM if durable else RiskLevel.LOW,
                      AcceptanceContract(), repeatability_hint=durable,
                      constraints=(structured or {}).get("constraints", {}))


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
    if intent.requires_task:
        from workstation.kanban import WorkstationKanbanBridge
        from hermes_cli import kanban_db
        bridge = WorkstationKanbanBridge()
        current_id = getattr(agent, "_canonical_work_task_id", None)
        current_run_id = getattr(agent, "_canonical_work_run_id", None)
        if current_id:
            conn = bridge.get_connection()
            try:
                current = kanban_db.get_task(conn, current_id)
                if (current is None or current.session_id != session_id or current.status in {"done", "cancelled"}
                        or current.body != envelope.content):
                    current_id = None
                    current_run_id = None
                else:
                    current_run_id = current.current_run_id
            finally:
                conn.close()
        if current_id is None:
            current_id = bridge.promote_request_if_multistep(envelope.content, session_id=session_id, envelope=envelope,
                                                           force=recognize_current_command(envelope.content) is not None,
                                                           acceptance_contract=intent.acceptance_policy)
            if current_id:
                conn = bridge.get_connection()
                try:
                    current = kanban_db.get_task(conn, current_id)
                    if current:
                        current_run_id = current.current_run_id
                finally:
                    conn.close()
        agent._canonical_work_task_id = current_id
        agent._canonical_work_run_id = current_run_id
    return intent
