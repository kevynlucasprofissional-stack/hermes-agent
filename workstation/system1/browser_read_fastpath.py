"""Read-only BrowserTask target selection; a model never dispatches browser effects.

The indexed action-space idea comes from references/05-System-1/browser-use--jev-ultrafast.
Only canonical browser snapshots can supply candidates. A fresh independent read
validates the candidate; the caller owns authority and all browser operations.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import re
import unicodedata
from typing import Any, Callable, Mapping

from agent.system1_decision import DecisionRequest, DecisionResult, decide_system1
from workstation.system1.calibration import default_calibration_policy
from workstation.system1.schemas import build_candidate_ranking_schema

_FIND = re.compile(
    r"^\s*(?:localize|encontre)\s+(?:o|a)\s+"
    r"(bot[aã]o|aba|link)\s+(.+?)\s+na\s+p[aá]gina\s+atual[.!]?\s*$",
    re.IGNORECASE,
)
_REFS = re.compile(r"^@e[1-9]\d*$")
_KINDS = {"botão": "button", "botao": "button", "aba": "tab", "link": "link"}
_NEUTRALS = {"NO_MATCH", "ABSTAIN"}


@dataclass(frozen=True)
class BrowserLocateReceipt:
    status: str  # verified | fallback
    ref: str = ""
    reason: str = ""
    provider: str = ""


def parse_find_request(text: str) -> tuple[str, str] | None:
    """Recognize a narrow explicit human read. Never interpret click/send intents."""
    if not isinstance(text, str) or len(text) > 180 or "\n" in text:
        return None
    match = _FIND.fullmatch(text)
    if not match:
        return None
    label = match.group(2).strip()
    if not 2 <= len(label) <= 80:
        return None
    return _KINDS[match.group(1).lower()], label


def _normalized(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(c)
    ).strip()


def _eligible(snapshot: Any) -> bool:
    return (
        isinstance(snapshot, dict)
        and snapshot.get("success") is True
        and snapshot.get("runtime") == "electron-chromium"
        and isinstance(snapshot.get("url"), str) and bool(snapshot["url"])
        and isinstance(snapshot.get("task_id"), str) and bool(snapshot["task_id"])
        and isinstance(snapshot.get("tab_id"), str) and bool(snapshot["tab_id"])
        and type(snapshot.get("revision")) is int and snapshot["revision"] >= 0
        and snapshot.get("readiness") == "stable"
        and snapshot.get("truncated") is False
        and snapshot.get("wall_detected") is False
        and isinstance(snapshot.get("elements"), list)
        and bool(snapshot["elements"])
    )


def _candidates(snapshot: Mapping[str, Any], kind: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for element in snapshot["elements"]:
        if not isinstance(element, dict) or element.get("disabled") is not False:
            continue
        ref = element.get("ref")
        role = str(element.get("role") or "").casefold()
        tag = str(element.get("tag") or "").casefold()
        label = element.get("label")
        if not isinstance(ref, str) or not _REFS.fullmatch(ref) or ref in seen:
            continue
        if not isinstance(label, str) or not label.strip():
            continue
        if kind == "button" and role != "button" and tag != "button":
            continue
        if kind == "link" and role != "link" and tag != "a":
            continue
        if kind == "tab" and role != "tab":
            continue
        seen.add(ref)
        result.append({"ref": ref, "role": role, "label": label.strip()[:80]})
    return result


def _same_snapshot(before: dict, after: Any, selected: dict, kind: str) -> bool:
    if not _eligible(after):
        return False
    if any(before[key] != after[key] for key in ("task_id", "tab_id", "revision", "url")):
        return False
    return any(row == selected for row in _candidates(after, kind))


def find_visible_control(
    snapshot: dict[str, Any],
    intent: tuple[str, str],
    fresh_snapshot: Callable[[], dict[str, Any]],
    *,
    decide: Callable[[DecisionRequest], DecisionResult | None] = decide_system1,
) -> BrowserLocateReceipt:
    """Return only an independently re-observed ref; never click or mint authority."""
    if not _eligible(snapshot):
        return BrowserLocateReceipt("fallback", reason="invalid_snapshot")
    kind, objective = intent
    if kind not in {"button", "tab", "link"} or not isinstance(objective, str):
        return BrowserLocateReceipt("fallback", reason="invalid_intent")
    candidates = _candidates(snapshot, kind)
    if not candidates:
        return BrowserLocateReceipt("fallback", reason="no_candidates")
    wanted = _normalized(objective)
    matches = [row for row in candidates if _normalized(row["label"]) == wanted]
    if len(matches) > 1 or (not matches and sum(wanted in _normalized(row["label"]) for row in candidates) > 1):
        return BrowserLocateReceipt("fallback", reason="ambiguous_label")
    if len(matches) == 1:
        selected = matches[0]
        source = "exact_match"
        provider = "deterministic"
    else:
        # A bounded set prevents a model from silently omitting potentially
        # relevant controls from an otherwise complete native snapshot.
        if len(candidates) > 18:
            return BrowserLocateReceipt("fallback", reason="too_many_candidates")
        criteria = {row["ref"]: f'{row["role"]}: {row["label"]}' for row in candidates}
        questions = build_candidate_ranking_schema(list(criteria))
        questions["preferred_candidate"]["criteria"].update(criteria)
        questions["preferred_candidate"]["instructions"] = (
            "Which observed UI element exactly matches the requested read-only target? "
            "Choose ABSTAIN or NO_MATCH if the target cannot be identified."
        )
        from workstation.system1.contracts import compute_state_hash
        minimal = {
            "objective": objective[:80], "kind": kind,
            "controls": candidates,
        }
        request = DecisionRequest(
            domain="browser_read", schema_id="hermes.system1.browser_read.v1",
            task_id=snapshot["task_id"], state_hash=compute_state_hash(minimal),
            minimal_state=minimal, questions=questions,
            candidate_sets={"candidates": list(criteria)},
            risk_class="read_only", language="pt",
        )
        try:
            result = decide(request)
        except Exception:
            return BrowserLocateReceipt("fallback", reason="model_unavailable")
        if (
            not isinstance(result, DecisionResult)
            or result.request_id != request.request_id
            or result.fallback_recommended
            or "preferred_candidate" in result.abstentions
        ):
            return BrowserLocateReceipt("fallback", reason="model_abstained")
        ref = result.answers.get("preferred_candidate")
        if not isinstance(ref, str) or ref not in criteria or ref in _NEUTRALS:
            return BrowserLocateReceipt("fallback", reason="invalid_model_choice")
        conf = result.confidence.get("preferred_candidate", 0.0)
        if not isinstance(conf, (float, int)) or not default_calibration_policy.evaluate_confidence(
            "preferred_candidate", conf, model="multilingual", language="pt", risk_class="read_only"
        ):
            return BrowserLocateReceipt("fallback", reason="model_confidence_unqualified")
        selected = next(row for row in candidates if row["ref"] == ref)
        # Model confidence cannot establish that an unrelated control is the
        # requested target. Only the observed label can substantiate the claim.
        wanted = _normalized(objective)
        if len(wanted) < 2 or wanted not in _normalized(selected["label"]):
            return BrowserLocateReceipt("fallback", reason="model_target_unsubstantiated")
        source = "system1_proposal"
        provider = result.provider

    try:
        fresh = fresh_snapshot()
    except Exception:
        return BrowserLocateReceipt("fallback", reason="readback_unavailable")
    if not _same_snapshot(snapshot, fresh, selected, kind):
        return BrowserLocateReceipt("fallback", reason="stale_or_changed_target")
    return BrowserLocateReceipt("verified", ref=selected["ref"], reason=source, provider=provider)


def maybe_resolve_browser_find(context: Any):
    """Resolve only explicit human element-location requests before System 2.

    The existing scoped dispatcher owns BrowserTask binding, leases and policy.
    This route never asks the controller to click, type, navigate or reconcile.
    Missing proof simply returns control to the ordinary reasoning path.
    """
    # Qualification has not established end-to-end cost/success improvement.
    # Never enable the new production path just because the module is importable.
    if os.environ.get("HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED") != "1":
        return None
    agent = getattr(context, "agent", None)
    if agent is None or getattr(agent, "_interrupt_requested", False):
        return None
    if getattr(agent, "_tool_guardrail_halt_decision", None):
        return None
    envelope = getattr(agent, "_message_envelope", None)
    origin = getattr(getattr(envelope, "origin", None), "value", getattr(envelope, "origin", None))
    authority = getattr(
        getattr(envelope, "intent_authority", None), "value",
        getattr(envelope, "intent_authority", None),
    )
    if str(origin).lower() != "human" or str(authority).lower() not in {
        "create_work", "update_work"
    }:
        return None
    message = getattr(context, "user_message", None)
    if not isinstance(message, str) or message != getattr(envelope, "content", None):
        return None
    intent = parse_find_request(message)
    if intent is None or "browser_snapshot" not in getattr(agent, "valid_tool_names", set()):
        return None
    # A one-shot human lookup has no Kanban TaskRun by design. Its BrowserTask
    # is owned by the authenticated conversation, not a fabricated work lease.
    session_id = str(getattr(context, "session_id", "") or "")
    if not session_id or str(getattr(envelope, "session_id", session_id)) != session_id:
        return None
    root = getattr(agent, "_conversation_root_id", None)
    if callable(root) and root() and str(root()) != session_id:
        return None
    agent_session_id = getattr(agent, "session_id", None)
    if agent_session_id and str(agent_session_id) != session_id:
        return None
    task_id = session_id

    from workstation.integrations.hermes.scoped_execution import (
        workstation_durable_dispatch, workstation_scoped_execution,
    )
    from agent.operational_resolution import OperationalOutcome, OperationalResolution
    import json
    import uuid

    dispatch = workstation_durable_dispatch(agent, raw_browser_snapshot=True)

    def read():
        raw = dispatch(
            "browser_snapshot", {"full": False}, task_id,
            "system1_browser_read_" + uuid.uuid4().hex[:16],
        )
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (TypeError, ValueError):
                return {}
        return raw if isinstance(raw, dict) else {}

    try:
        with workstation_scoped_execution(agent, task_id, getattr(context, "messages", None)):
            observed = read()
            if observed.get("task_id") != task_id:
                return None
            receipt = find_visible_control(observed, intent, read)
    except Exception:
        # A read failure is never permission to retry or perform a mutation.
        return None

    if receipt.status != "verified":
        return None
    kind, label = intent
    names = {"button": "botão", "tab": "aba", "link": "link"}
    return OperationalResolution(
        outcome=OperationalOutcome.SATISFIED,
        final_response=(
            f'Localizei {names[kind]} "{label}" na página atual '
            f'({receipt.ref}). Nenhum clique foi realizado.'
        ),
        reason="system1_browser_read_verified",
        provider="system1_browser_read",
        details={
            "ref": receipt.ref, "operation": "locate_read_only",
            "source": receipt.reason, "model_provider": receipt.provider,
            "verified": True, "task_id": task_id,
        },
    )
