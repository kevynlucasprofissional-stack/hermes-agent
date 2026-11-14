"""Site-agnostic browser to canonical Kanban readback.

The trusted host binds exact input calls and one commit to a resource,
monotonic revision and expected fields. No UI ACK/DOM can certify persistence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from urllib.parse import urlsplit
from typing import Any, Callable

from workstation.artifacts import ArtifactStore
from workstation.contracts import EvidenceRef
from workstation.execution_policy import EvidenceStrength
from workstation.native_browser_evidence import _origin


@dataclass(frozen=True, slots=True)
class BrowserReadbackContract:
    """Constructed in trusted runtime code; never from model output."""
    commit_call_id: str
    input_call_ids: tuple[str, ...]
    read_path: str
    resource_id: str
    expected_fields: tuple[tuple[str, str | int | bool], ...]
    revision_before: int
    revision_after: int
    expected_origin: str | None = None
    # Recovery is opt-in from trusted host code, never model arguments.
    uncertain_operation_id: str | None = None
    remote_operation_id: str | None = None

    def validate(self) -> None:
        if (not self.commit_call_id or not self.input_call_ids
                or len(set(self.input_call_ids)) != len(self.input_call_ids)
                or self.commit_call_id in self.input_call_ids
                or not all(isinstance(x, str) and x for x in self.input_call_ids)):
            raise ValueError("invalid_browser_operation_contract")
        if not isinstance(self.resource_id, str) or not 0 < len(self.resource_id) <= 128:
            raise ValueError("invalid_browser_resource_identity")
        if (not isinstance(self.read_path, str)
                or re.fullmatch(r"/[A-Za-z0-9_./-]{0,200}", self.read_path) is None
                or "/../" in self.read_path or self.read_path.endswith("/..")
                or self.read_path.startswith("//")):
            raise ValueError("invalid_browser_readback_path")
        if (type(self.revision_before) is not int or type(self.revision_after) is not int
                or self.revision_before < 0
                or self.revision_after <= self.revision_before):
            raise ValueError("browser_revision_must_advance")
        if (not self.expected_fields or len(self.expected_fields) > 8
                or len(set(key for key, _ in self.expected_fields)) != len(self.expected_fields)):
            raise ValueError("invalid_browser_expected_fields")
        for key, value in self.expected_fields:
            if (not isinstance(key, str)
                    or re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", key) is None
                    or type(value) not in (str, int, bool)
                    or isinstance(value, str) and len(value) > 4096):
                raise ValueError("invalid_browser_expected_field")
        if self.expected_origin is not None:
            parsed = urlsplit(self.expected_origin)
            if (_origin(self.expected_origin) is None or parsed.path not in {"", "/"}
                    or parsed.query or parsed.fragment or parsed.username or parsed.password):
                raise ValueError("invalid_browser_trusted_origin")
        if (self.uncertain_operation_id is None) != (self.remote_operation_id is None):
            raise ValueError("browser_uncertain_recovery_requires_causal_ids")
        if self.uncertain_operation_id is not None:
            if (re.fullmatch(r"[A-Za-z0-9_-]{1,128}", self.uncertain_operation_id) is None
                    or re.fullmatch(r"[a-f0-9]{32}", self.remote_operation_id or "") is None):
                raise ValueError("invalid_browser_uncertain_recovery_ids")
        fields = dict(self.expected_fields)
        if (type(fields.get("revision")) is not int
                or fields["revision"] != self.revision_after):
            raise ValueError("browser_revision_predicate_required")


@dataclass(frozen=True, slots=True)
class TrustedBrowserReadbackExpectation:
    """Host-pinned resource and expected state, before model tool execution."""
    task_id: str
    session_id: str
    run_id: str
    expected_origin: str
    read_path: str
    resource_id: str
    expected_fields: tuple[tuple[str, str | int | bool], ...]
    revision_before: int
    revision_after: int
    remote_operation_id: str | None = None


def bind_trusted_browser_expectation(
    expectation: TrustedBrowserReadbackExpectation | None,
    observations: list[dict] | None,
    *, task_id: str, session_id: str, run_id: str,
) -> BrowserReadbackContract | None:
    """Bind actual tool call IDs; never create expected values from model text."""
    if (not isinstance(expectation, TrustedBrowserReadbackExpectation)
            or (expectation.task_id, expectation.session_id, expectation.run_id)
               != (task_id, session_id, run_id)
            or not isinstance(observations, list)):
        return None
    edits = [row for row in observations if isinstance(row, dict)
             and row.get("tool") in {"browser_type", "browser_click"}]
    if (len(edits) != 2
            or [row.get("tool") for row in edits] != ["browser_type", "browser_click"]
            or edits[0].get("status") != "completed"):
        return None
    uncertain_id = None
    if edits[1].get("status") != "completed":
        if (edits[1].get("status") != "failed"
                or edits[1].get("browser_uncertain_error") != "browser_input_delivery_unverified"
                or expectation.remote_operation_id is None):
            return None
        # Recover the original native admission ID, never an ID supplied by
        # the model or a new identifier that could authorize replay.
        try:
            from tools.browser_workstation import _workstation_home
            state = json.loads((_workstation_home() / "Runtime" / "browser-session.json")
                               .read_text(encoding="utf-8"))
            found = [op for op in (state.get("operationAdmissions") or {}).values()
                     if isinstance(op, dict) and op.get("action") == "browser_click"
                     and op.get("taskId") == task_id and op.get("sessionId") == session_id
                     and str(op.get("runId")) == run_id
                     and op.get("acknowledged") is not True and not op.get("terminal")]
        except (OSError, ValueError, KeyError, TypeError):
            return None
        if len(found) != 1:
            return None
        uncertain_id = found[0].get("operationId")
    candidate = BrowserReadbackContract(
        commit_call_id=edits[1].get("call_id"),
        input_call_ids=(edits[0].get("call_id"),),
        read_path=expectation.read_path,
        resource_id=expectation.resource_id,
        expected_fields=expectation.expected_fields,
        revision_before=expectation.revision_before,
        revision_after=expectation.revision_after,
        expected_origin=expectation.expected_origin,
        uncertain_operation_id=uncertain_id,
        remote_operation_id=expectation.remote_operation_id if uncertain_id else None,
    )
    try:
        candidate.validate()
    except (ValueError, TypeError):
        return None
    return candidate


def _observation(row: dict, *, task_id: str, session_id: str,
                 run_id: str, store: ArtifactStore) -> dict | None:
    proof = row.get("native_browser_evidence")
    if not isinstance(proof, dict) or not proof.get("evidence_ref"):
        return None
    try:
        verified = store.resolve_structured(proof["evidence_ref"])
        payload = verified["content"]
        fields = (("task_id", task_id), ("session_id", session_id),
                  ("run_id", run_id), ("call_id", row.get("call_id")),
                  ("action", row.get("tool")), ("operation_id", proof.get("operation_id")),
                  ("tab_id", proof.get("tab_id")), ("status", "observed"),
                  ("ack", True), ("fresh_observation", True),
                  ("evidence_strength", int(EvidenceStrength.SAME_SESSION_SEMANTIC_OBSERVATION)))
        if (verified["sha256"] != proof.get("sha256")
                or not isinstance(payload, dict)
                or any(payload.get(k) != v for k, v in fields)
                or any(proof.get(k) != payload.get(k) for k in (
                    "task_id", "session_id", "run_id", "call_id", "action",
                    "operation_id", "tab_id", "status", "ack", "fresh_observation",
                    "evidence_strength"))):
            return None
        return payload
    except (OSError, ValueError, KeyError, TypeError):
        return None


def verify_native_browser_receipts(
    observations: list[dict] | None, *, task_id: str, session_id: str,
    run_id: str, trace_truncated: bool,
    contract: BrowserReadbackContract | None,
    read_http: Callable[[str], Any] | None = None,
    store: ArtifactStore | None = None,
    owner_path=None,
) -> tuple[list[EvidenceRef], list[dict], list[str]]:
    """One explicit transaction. Reject unknown actions and uncovered commits."""
    if (trace_truncated or not isinstance(observations, list) or not observations
            or not isinstance(contract, BrowserReadbackContract)):
        return [], [], ["Browser observation or trusted contract is incomplete"]
    try:
        contract.validate()
    except ValueError as exc:
        return [], [], [str(exc)]
    store = store or ArtifactStore()
    seen: set[str] = set()
    inputs: dict[str, int] = {}
    input_tab_id: str | None = None
    commit: dict | None = None
    commit_pos = -1
    uncertain_commit = False
    navigations = 0
    issues: list[str] = []
    for pos, row in enumerate(observations):
        if not isinstance(row, dict):
            issues.append("Failed or incomplete tool operation")
            continue
        if row.get("status") != "completed":
            # A lost native click ACK is not evidence of failure or success.
            # Only the trusted contract + owner admission + remote operation
            # ID may resolve it, without a second click or synthetic ACK.
            if (row.get("tool") == "browser_click"
                    and row.get("call_id") == contract.commit_call_id
                    and row.get("status") == "failed"
                    and row.get("browser_uncertain_error") == "browser_input_delivery_unverified"
                    and contract.uncertain_operation_id is not None):
                uncertain_commit = True
                commit_pos = pos
            else:
                issues.append("Failed or incomplete tool operation")
            continue
        call_id = row.get("call_id")
        if not isinstance(call_id, str) or not call_id or call_id in seen:
            issues.append("Unbound or duplicate tool call")
            continue
        seen.add(call_id)
        tool = row.get("tool")
        if (row.get("effect") in {"PURE_READ", "DISCOVERY"}
                and tool not in {"browser_click", "browser_type", "browser_navigate",
                                 "browser_batch_actions", "browser_press", "browser_file_upload"}):
            continue
        if tool == "browser_navigate":
            # Opening the target before editing is setup, not a second commit.
            # The later same-origin GET still has to prove the actual save.
            navigations += 1
            if navigations > 1 or inputs or commit is not None:
                issues.append("Unexpected browser navigation in write transaction")
            continue
        if tool == "browser_type" and call_id in contract.input_call_ids:
            input_proof = _observation(row, task_id=task_id, session_id=session_id,
                                       run_id=run_id, store=store)
            if input_proof is None:
                issues.append("Browser input lacks owner-bound observation")
            else:
                if input_tab_id is not None and input_tab_id != input_proof["tab_id"]:
                    issues.append("Browser input owner tab changed")
                input_tab_id = input_proof["tab_id"]
            inputs[call_id] = pos
        elif tool == "browser_click" and call_id == contract.commit_call_id:
            commit_pos = pos
            commit = _observation(row, task_id=task_id, session_id=session_id,
                                  run_id=run_id, store=store)
            if commit is None:
                issues.append("Browser commit lacks owner-bound observation")
        else:
            issues.append("Uncovered or unknown mutating browser effect")
    if (set(inputs) != set(contract.input_call_ids) or commit_pos < 0
            or any(pos >= commit_pos for pos in inputs.values())):
        issues.append("Browser operation sequence incomplete or out of order")
    if (commit is None and not uncertain_commit) or issues:
        return [], [], list(dict.fromkeys(issues))
    if read_http is None:
        from tools.browser_workstation import call_workstation_browser
        def read_http(path: str) -> Any:
            return call_workstation_browser(
                "browser_read_http",
                {"url": path, "method": "GET",
                 "headers": {"Cache-Control": "no-store", "Accept": "application/json"}},
                task_id=task_id, session_id=session_id, run_id=run_id,
                kanban_card_id=task_id, model_facing=False,
            )
    try:
        raw = read_http(contract.read_path)
        response = json.loads(raw) if isinstance(raw, str) else raw
        body = response.get("json") if isinstance(response, dict) else None
        if (not isinstance(response, dict) or response.get("status") != 200
                or response.get("ok") is not True
                or "application/json" not in str(response.get("content_type", "")).lower()
                or not isinstance(body, dict)
                or body.get("id") != contract.resource_id
                or body.get("revision") != contract.revision_after
                or any(type(body.get(key)) is not type(value) or body.get(key) != value
                       for key, value in contract.expected_fields)
                or urlsplit(str(response.get("url") or "")).path != contract.read_path
                or urlsplit(str(response.get("url") or "")).query
                or (uncertain_commit and
                    body.get("last_operation_id") != contract.remote_operation_id)):
            return [], [], ["External readback resource, field, operation or revision mismatch"]
        from tools.browser_workstation import _workstation_home
        path = owner_path or (_workstation_home() / "Runtime" / "browser-session.json")
        state = json.loads(path.read_text(encoding="utf-8"))
        if uncertain_commit:
            if not input_tab_id or not contract.uncertain_operation_id:
                return [], [], ["Original Browser input or uncertain operation is unbound"]
            # This is the SAME pre-dispatch owner admission; no click ACK is
            # synthesized. Exact remote operation ID proves the submitted
            # mutation, not merely coincidentally matching title/revision.
            commit = {"operation_id": contract.uncertain_operation_id,
                      "tab_id": input_tab_id}
        adm = (state.get("operationAdmissions") or {}).get(commit["operation_id"])
        tasks = [t for t in state["browserTasks"]["tasks"]
                 if isinstance(t, dict) and t.get("taskId") == task_id]
        tabs = [t for t in state["tabs"]
                if isinstance(t, dict) and t.get("id") == commit["tab_id"]]
        if (len(tasks) != 1 or len(tabs) != 1
                or tasks[0].get("sessionHost") != session_id
                or str(tasks[0].get("runId")) != run_id
                or tabs[0].get("browserTaskId") != task_id
                or tabs[0].get("recoveryState") != "live"
                or not isinstance(adm, dict)
                or (adm.get("acknowledged") is True if uncertain_commit
                    else adm.get("acknowledged") is not True)
                or (uncertain_commit and adm.get("terminal") is not None)
                or adm.get("operationId") != commit["operation_id"]
                or adm.get("taskId") != task_id or adm.get("sessionId") != session_id
                or str(adm.get("runId")) != run_id or adm.get("action") != "browser_click"
                or adm.get("tabId") != commit["tab_id"]
                or (not uncertain_commit and
                    (tasks[0].get("lastReceipt") or {}).get("operationId") != commit["operation_id"])
                or _origin(response.get("url")) != _origin(tabs[0].get("safeUrl"))
                or (contract.expected_origin is not None and
                    _origin(response.get("url")) != _origin(contract.expected_origin))):
            return [], [], ["External readback owner or origin changed"]
        audited = {
            "task_id": task_id, "session_id": session_id, "run_id": run_id,
            "operation_id": commit["operation_id"], "call_id": contract.commit_call_id,
            "input_call_ids": list(contract.input_call_ids), "tab_id": commit["tab_id"],
            "action": "browser_click", "owner_ack": not uncertain_commit,
            "covered_predicates": [key for key, _ in contract.expected_fields],
            "source_kind": "browser_authenticated_same_origin_get",
            "resource_id_sha256": hashlib.sha256(contract.resource_id.encode()).hexdigest(),
            "revision_before": contract.revision_before,
            "revision_after": contract.revision_after,
            "evidence_strength": int(EvidenceStrength.SEMANTIC_PERSISTED_READBACK),
            "observed_at": datetime.now(timezone.utc).isoformat(), "read_after_write": True,
        }
        saved = store.store(
            task_id, "browser_http_readback_" +
            hashlib.sha256(commit["operation_id"].encode()).hexdigest()[:20] + ".json",
            audited, schema="hermes.browser_persisted_readback.v1",
        )
        resolved = store.resolve_structured(saved.ref)
        if resolved["sha256"] != saved.sha256 or resolved["content"] != audited:
            return [], [], ["Browser readback artifact did not persist"]
        ref = EvidenceRef("browser_persisted_readback", saved.ref, sha256=saved.sha256,
                          task_id=task_id, run_id=run_id, operation_id=commit["operation_id"],
                          verifier="native_browser_external_readback")
        verifier = {"verifier": "native_browser_external_readback", "passed": True,
                    "evidence_ref": saved.ref, "task_id": task_id, "run_id": run_id,
                    "operation_id": commit["operation_id"],
                    "source_kind": audited["source_kind"],
                    "owner_ack": audited["owner_ack"],
                    "evidence_strength": audited["evidence_strength"],
                    "covered_predicates": audited["covered_predicates"],
                    "read_after_write": True}
        return [ref], [verifier], []
    except Exception:
        return [], [], ["Authorized Browser GET or owner readback unavailable"]
