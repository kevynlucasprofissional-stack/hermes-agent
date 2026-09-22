"""SCRATCH — verified fixture recipe: real kanban task -> certified EXECUTE -> VERIFIED.

Drives `TaskCompiler._execute_route` directly (not through the provider boundary):
the CapabilityRouter, the RoutingCertificate, the CertifiedDispatcher and the
OperationalKernel all run for real.  Nothing is monkeypatched; the only fakes are
the physical tool dispatcher (which records and ACKs) and the owner-supplied
verification evidence (which the kernel accepts as equivalent to a real readback).
"""
from __future__ import annotations

from datetime import datetime, timezone

from workstation.artifacts import ArtifactStore
from workstation.contracts import IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.intent import OperationIntent
from workstation.control_plane.ir import CALL, EXISTS
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.control_plane.verification import (
    VerificationContract,
    VerificationEvidence,
    VerificationLifecycle,
)
from workstation.execution_policy import EvidenceStrength
from workstation.kanban import WorkstationKanbanBridge
from workstation.operational_capabilities import (
    CapabilityLifecycle,
    OperationalCapability,
    OperationalCapabilityRegistry,
)
from workstation.task_compiler import TaskCompiler

SESSION_ID = "route-fixture-session"
BROWSER_TASK_ID = "browser-task-fixture"
CAP_ID = "route.fixture.navigate"
CAP_VERSION = "1.0.0"
PRIMITIVE = "browser_navigate"
OPERATION_ID = "op-route-fixture"
TARGET = "example.com"
PROMPT = "first open the site then extract and save the data to a file"
POSTCONDITION = EXISTS("route_artifact")


def _validated_verifier():
    """`is_sufficient_for` requires VALIDATED + observer + source + trust + coverage."""
    return VerificationContract(
        covered_predicates=(POSTCONDITION.fingerprint(),),
        observer="owner.readback",
        source_kind="source_of_record",
        minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        allowed_trust=("trusted_owner",),
        lifecycle=VerificationLifecycle.VALIDATED,
    )


def test_scratch_route_fixture_executes_and_verifies():
    from hermes_cli import kanban_db
    from hermes_cli.kanban_db_connect import connect

    # ---- 1. a REAL kanban task (same DB DurableTaskStore opens) -------------
    bridge = WorkstationKanbanBridge()
    envelope = MessageEnvelope(MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, SESSION_ID, PROMPT)
    task_id = bridge.promote_request_if_multistep(PROMPT, session_id=SESSION_ID, envelope=envelope)
    assert task_id, "multistep promotion must create a real kanban task"

    conn = connect()
    try:
        task = kanban_db.get_task(conn, task_id)
    finally:
        conn.close()
    assert task is not None and task.session_id == SESSION_ID
    # `claim_task` already opened a run, so current_run_id needs no manual INSERT.
    assert task.current_run_id is not None, "claim_task must have opened a task run"
    run_id = str(task.current_run_id)

    # ---- 2. capability in the DEFAULT registry location ---------------------
    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    cap = OperationalCapability(
        id=CAP_ID,
        name="Route fixture navigate",
        version=CAP_VERSION,
        route="native_browser",
        lifecycle=CapabilityLifecycle.PROMOTED,
        # provenance stays empty: `learned` is provenance['source']=='experience_compiler'.
        formal_contract=CapabilityFormalContract(
            operation_family="browser.navigate",
            target_family=TARGET,
            typed_preconditions=[],
            typed_postconditions=[POSTCONDITION],
            effect_footprint=[CALL("browser.navigate", TARGET)],
            authority_required=AuthorityScope(
                level=AuthorityLevel.EXTERNAL_REVERSIBLE,
                allowed_actions={"browser.navigate"},
                allowed_resources={TARGET},
            ),
            verifier=_validated_verifier(),
        ),
        # `browser_navigate` reaches the fallback browser branch of
        # execute_primitive -> scoped_dispatch -> our dispatch fn.
        implementation={"steps": [{
            "id": "navigate",
            "primitive": PRIMITIVE,
            "args": {"url": "$inputs.url"},
        }]},
    )
    registry.register(cap)

    # ---- 3. compiler: trusted authority is the ONLY trust root --------------
    # A kanban Task carries no authority_scope attribute on this revision, so
    # `_execute_route`'s task lookup cannot supply it; compiler.trusted_authority
    # is the sanctioned source (read first, before the task lookup).
    compiler = TaskCompiler(artifacts=store)
    compiler.trusted_authority = AuthorityScope(
        level=AuthorityLevel.EXTERNAL_REVERSIBLE,
        allowed_actions={"browser.navigate"},
        allowed_resources={TARGET},
    )

    # ---- 4. request: intent + evidence fenced to the real task/run ----------
    intent = OperationIntent(
        id="intent-route-fixture",
        target=TARGET,
        goal=POSTCONDITION,
        effect_budget=[CALL("browser.navigate", TARGET)],
        metadata={"operation_family": "browser.navigate", "target_family": TARGET},
    )
    fingerprint = POSTCONDITION.fingerprint()
    evidence = VerificationEvidence(
        evidence_id="ev-route-fixture",
        observer="owner.readback",
        source_kind="source_of_record",
        value=fingerprint,
        evidence_strength=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        trust_class="trusted_owner",
        observer_failure_domain="filesystem",
        observed_at=datetime.now(timezone.utc).isoformat(),
        read_after_write=True,
        covered_predicates=(fingerprint,),
        task_id=task_id,
        run_id=run_id,
        operation_id=OPERATION_ID,
    )
    request = {
        "operation_intent": intent.to_dict(),
        "semantic_state": {},
        "verification_expected": fingerprint,
        "verification_evidence": [evidence],
        "capability_inputs": {"url": f"https://{TARGET}/"},
        "expected_task_id": task_id,
        "expected_run_id": run_id,
        "operation_id": OPERATION_ID,
    }

    dispatched = []

    def dispatch(name, args, *rest):
        # _execute_capability wraps this as dispatch(name, args, browser_task_id, call_id).
        dispatched.append((name, dict(args)))
        return {"ok": True, "url": args.get("url")}

    result = compiler._execute_route(
        request,
        task_id=BROWSER_TASK_ID,
        session_id=SESSION_ID,
        dispatch=dispatch,
        canonical_task_id=task_id,
    )

    # ---- 5. canonical success criteria --------------------------------------
    assert result["routing_decision"] == "EXECUTE", result
    assert result["success"] is True, result
    assert result["verification_result"]["status"] == "VERIFIED", result
    assert result["verification_result"]["accepted"] is True, result
    # the physical primitive really ran, exactly once, with interpolated args
    assert [name for name, _ in dispatched] == [PRIMITIVE], dispatched
    assert dispatched[0][1] == {"url": f"https://{TARGET}/"}, dispatched
    # certified dispatch reached its own terminal state
    assert result["dispatch_record"]["status"] == "COMMITTED", result["dispatch_record"]
    assert result["capability_id"] == CAP_ID and result["certificate_hash"], result
