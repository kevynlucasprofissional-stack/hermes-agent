"""Bounded System-1 operation/target proposal and QA-only native execution.

A Laya result is NEVER an authority grant. Mutations are possible only for an
explicit human command and the exact loopback QA origin, through the existing
workstation_durable_dispatch with native operation admission and readback.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
import unicodedata
import uuid
from typing import Any, Callable

from agent.system1_decision import DecisionRequest, DecisionResult, decide_system1
from workstation.system1.calibration import default_calibration_policy
from workstation.system1.browser_read_fastpath import _eligible, _normalized
from workstation.system1.contracts import compute_state_hash

_QA_URL = "http://127.0.0.1:18792/interaction"
_CLICK = re.compile(r'^Clique no bot[aã]o "?([^"\n]{2,80})"? na p[aá]gina atual[.!]?$', re.I)
_TYPE = re.compile(r'^Preencha o campo "([^"\n]{2,80})" com "([^"\n]{1,80})" na p[aá]gina atual[.!]?$', re.I)
_REF = re.compile(r"^@e[1-9][0-9]*$")


@dataclass(frozen=True)
class InteractionIntent:
    operation: str  # click | type
    target: str
    text: str = ""  # human-supplied; never sent to the model


@dataclass(frozen=True)
class InteractionProposal:
    status: str  # verified | fallback
    operation: str = ""
    ref: str = ""
    provider: str = ""
    reason: str = ""
    receipt_ref: str = ""


def parse_interaction(text: Any) -> InteractionIntent | None:
    if not isinstance(text, str) or len(text) > 240 or "\n" in text:
        return None
    match = _CLICK.fullmatch(text.strip())
    if match:
        return InteractionIntent("click", match.group(1).strip())
    match = _TYPE.fullmatch(text.strip())
    if match:
        return InteractionIntent("type", match.group(1).strip(), match.group(2))
    return None


def _candidates(snapshot: dict, operation: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen = set()
    for item in snapshot["elements"]:
        if not isinstance(item, dict) or item.get("disabled") is not False:
            continue
        ref, label = item.get("ref"), item.get("label")
        role, tag = str(item.get("role") or "").lower(), str(item.get("tag") or "").lower()
        if not isinstance(ref, str) or not _REF.fullmatch(ref) or ref in seen:
            continue
        if not isinstance(label, str) or not label.strip():
            continue
        if operation == "click" and not (role == "button" or tag == "button"):
            continue
        if operation == "type" and not (role in {"textbox", "searchbox"} and tag in {"input", "textarea"}):
            continue
        seen.add(ref)
        found.append({"ref": ref, "label": label.strip()[:80], "role": role})
    return found


def _same_target(before: dict, after: Any, selected: dict, operation: str) -> bool:
    return (_eligible(after)
            and all(after[key] == before[key] for key in ("task_id", "tab_id", "url", "revision"))
            and selected in _candidates(after, operation))


def propose_interaction(
    observed: dict,
    intent: InteractionIntent,
    readback: Callable[[], dict],
    *,
    decide: Callable[[DecisionRequest], DecisionResult | None] = decide_system1,
) -> InteractionProposal:
    """Only rank permitted operations/refs and independently reobserve the ref."""
    if not _eligible(observed) or intent.operation not in {"click", "type"}:
        return InteractionProposal("fallback", reason="invalid_snapshot_or_intent")
    candidates = _candidates(observed, intent.operation)
    if not candidates or len(candidates) > 18:
        return InteractionProposal("fallback", reason="candidate_limit")
    wanted = _normalized(intent.target)
    exact = [x for x in candidates if _normalized(x["label"]) == wanted]
    partial = [x for x in candidates if wanted in _normalized(x["label"])]
    if len(exact) > 1 or (not exact and len(partial) > 1):
        return InteractionProposal("fallback", reason="ambiguous_target")
    options = {x["ref"]: x["role"] + ": " + x["label"] for x in candidates}
    minimal = {"operation_objective": intent.operation, "target": intent.target,
               "controls": candidates}  # Never include a human-entered field value.
    request = DecisionRequest(
        domain="browser_interaction_proposal",
        schema_id="hermes.system1.browser_interaction.v1",
        task_id=observed["task_id"], state_hash=compute_state_hash(minimal),
        minimal_state=minimal, risk_class="mutation", language="pt",
        questions={
            "operation": {"type": "choice",
                          "instructions": "Choose the operation explicitly requested by the objective.",
                          "criteria": {"click": "Click the requested button",
                                       "type": "Fill the requested text field",
                                       "ABSTAIN": "Cannot classify safely"}},
            "preferred_candidate": {
                "type": "choice",
                "instructions": "Choose the one observed element matching the target label, or abstain.",
                "criteria": {**options, "NO_MATCH": "No matching target",
                             "ABSTAIN": "Ambiguous target"},
            },
        },
        candidate_sets={"candidates": list(options)},
    )
    try:
        decision = decide(request)
    except Exception:
        return InteractionProposal("fallback", reason="model_unavailable")
    if not isinstance(decision, DecisionResult) or decision.request_id != request.request_id:
        return InteractionProposal("fallback", reason="invalid_model_result")
    if decision.fallback_recommended or decision.abstentions:
        return InteractionProposal("fallback", reason="model_abstained")
    if decision.answers.get("operation") != intent.operation:
        return InteractionProposal("fallback", reason="wrong_operation")
    ref = decision.answers.get("preferred_candidate")
    if not isinstance(ref, str) or ref not in options:
        return InteractionProposal("fallback", reason="invalid_model_target")
    for question in ("operation", "preferred_candidate"):
        confidence = decision.confidence.get(question, 0.0)
        if not isinstance(confidence, (int, float)) or not default_calibration_policy.evaluate_confidence(
            question, confidence, model="multilingual", language="pt", risk_class="mutation",
        ):
            return InteractionProposal("fallback", reason="confidence_insufficient")
    selected = next(item for item in candidates if item["ref"] == ref)
    if len(wanted) < 2 or wanted not in _normalized(selected["label"]):
        return InteractionProposal("fallback", reason="unsubstantiated_target")
    try:
        fresh = readback()
    except Exception:
        return InteractionProposal("fallback", reason="pre_effect_readback_failed")
    if not _same_target(observed, fresh, selected, intent.operation):
        return InteractionProposal("fallback", reason="stale_target")
    return InteractionProposal(
        "verified", intent.operation, ref, decision.provider, "system1_proposal",
        str(decision.details.get("receipt_ref", "")),
    )


def _object(raw: Any) -> dict:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return {}
    return raw if isinstance(raw, dict) else {}


def _qa_verified(before: dict, after: dict, intent: InteractionIntent) -> bool:
    if not _eligible(after) or any(after[k] != before[k] for k in ("task_id", "tab_id", "url")):
        return False
    # An effect is not verified merely because the tool returned success.
    payload = json.dumps(after, ensure_ascii=False)
    if intent.operation == "click":
        return "QA-REPORTS-CLICKED-ONCE" in payload
    return "QA-NAME-ENTERED:" + intent.text in payload


def maybe_execute_qa_interaction(context: Any):
    """Run one explicitly requested, journaled QA-only native operation."""
    import os
    if os.environ.get("HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED") != "1":
        return None
    agent = getattr(context, "agent", None)
    if agent is None or getattr(agent, "_interrupt_requested", False) or getattr(agent, "_tool_guardrail_halt_decision", None):
        return None
    envelope = getattr(agent, "_message_envelope", None)
    origin = getattr(getattr(envelope, "origin", None), "value", getattr(envelope, "origin", None))
    authority = getattr(getattr(envelope, "intent_authority", None), "value",
                        getattr(envelope, "intent_authority", None))
    if str(origin).lower() != "human" or str(authority).lower() not in {"create_work", "update_work"}:
        return None
    text = getattr(context, "user_message", None)
    intent = parse_interaction(text)
    if intent is None or text != getattr(envelope, "content", None):
        return None
    session = str(getattr(context, "session_id", "") or "")
    turn_id = str(getattr(context, "turn_id", "") or "")
    if not session or not turn_id or str(getattr(envelope, "session_id", session)) != session:
        return None
    if str(getattr(agent, "session_id", session)) != session:
        return None
    root = getattr(agent, "_conversation_root_id", None)
    if callable(root) and root() and str(root()) != session:
        return None
    if "browser_snapshot" not in getattr(agent, "valid_tool_names", set()):
        return None

    from agent.operational_resolution import OperationalOutcome, OperationalResolution
    from workstation.integrations.hermes.scoped_execution import (
        workstation_durable_dispatch, workstation_scoped_execution,
    )
    dispatch = workstation_durable_dispatch(agent, raw_browser_snapshot=True)

    def read():
        return _object(dispatch("browser_snapshot", {"full": False}, session,
                                "system1_qa_read_" + uuid.uuid4().hex[:16]))

    with workstation_scoped_execution(agent, session, getattr(context, "messages", None)):
        observed = read()
        if observed.get("task_id") != session or observed.get("url") != _QA_URL:
            return None  # NEVER execute on a non-QA URL.
        proposal = propose_interaction(observed, intent, read)
        if proposal.status != "verified":
            # A rejected QA target must not fall through to a reasoning path
            # that might execute the very ambiguous or stale mutation.
            return OperationalResolution(
                outcome=OperationalOutcome.HANDOFF, provider="system1_browser_qa",
                reason="qa_proposal_rejected",
                final_response="Não executei a operação QA: alvo ou decisão não verificados.",
                details={"reason": proposal.reason, "operation": intent.operation},
            )

        native_action = "browser_click" if intent.operation == "click" else "browser_type"
        args = {"ref": proposal.ref}
        if intent.operation == "type":
            args["text"] = intent.text
        call_id = "system1_qa_effect_" + re.sub(r"[^a-zA-Z0-9]", "", session + turn_id)[:48]
        try:
            effect = _object(dispatch(native_action, args, session, call_id))
        except Exception:
            effect = {}
        # Never retry after an effect was requested, regardless of its result.
        try:
            after = read()
        except Exception:
            after = {}
        verified = effect.get("success") is True and _qa_verified(observed, after, intent)
        if not verified:
            return OperationalResolution(
                outcome=OperationalOutcome.HANDOFF, provider="system1_browser_qa",
                reason="qa_effect_uncertain", final_response=(
                    "A operação QA foi solicitada, mas seu efeito não foi comprovado. "
                    "Não repetirei automaticamente. Verifique o estado no Browser."
                ),
                details={"operation": intent.operation, "receipt_ref": proposal.receipt_ref},
            )
        return OperationalResolution(
            outcome=OperationalOutcome.EXECUTED, provider="system1_browser_qa",
            reason="qa_native_mutation_verified",
            final_response=f'Operação QA {intent.operation} executada em {proposal.ref} e verificada.',
            details={"operation": intent.operation, "ref": proposal.ref,
                     "receipt_ref": proposal.receipt_ref, "verified": True},
        )
