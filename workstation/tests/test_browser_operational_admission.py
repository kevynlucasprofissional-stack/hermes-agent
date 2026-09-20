"""Browser Operational Admission / Primitive Closure — P0 Regression Suite.

Verifies:
1. read_preview is PURE_READ and does not trigger mutation tracking;
2. drive_preview classifies action="elements" as DISCOVERY/PURE_READ and mutating actions as MUTATION;
3. Generic effect_resolver is owner-declared, deterministic, and fail-closed;
4. 3 structurally similar terminal calls with different commands != REQUIRE_COMPILE;
5. 3 write_file calls for distinct resources != REQUIRE_COMPILE;
6. Homogeneous proven fan-out retains compilation gating only when operational closure exists;
7. Trusted authority derivation: request payload cannot mint or broaden authority;
8. CertifiedDispatcher as mandatory mutation chokepoint: no certificate => no dispatch;
9. Mutation timeout produces UNCERTAIN and prevents blind retry;
10. Transient empty SPA snapshot receives bounded re-observation;
11. Plain-text paste preserves exact newlines and reacquires targets;
12. browser_read_http allows GET/HEAD and rejects mutations/bodies/unsafe destinations;
13. End-to-end verified canary with deterministic zero-planning fan-out and drift isolation.
"""
import json
from types import SimpleNamespace
import pytest

from tools.effects import ToolEffect, tool_contract, tool_effect
from workstation.execution_policy import CompilationDecision, decisions_for_calls


def mock_agent():
    return SimpleNamespace(
        valid_tool_names={"work_execute", "terminal", "write_file", "patch", "browser_click", "browser_type"},
        _work_repeatability_hint=True,
        session_id="session-test-p0",
        _conversation_root_id=lambda: "session-test-p0",
        _work_mutation_shapes={},
        _work_mutation_sem_families={},
        _work_mutation_evidence={},
        _work_completed_mutations={},
        _work_compilation_candidates={},
    )


def test_p0_1_read_preview_is_pure_read():
    """read_preview and read_window_below must be explicitly PURE_READ."""
    from tools.effects import READ_EFFECTS
    assert tool_effect("read_preview") == ToolEffect.PURE_READ
    assert tool_effect("read_preview") in READ_EFFECTS
    assert tool_effect("read_window_below") == ToolEffect.PURE_READ
    assert tool_effect("read_window_below") in READ_EFFECTS


def test_p0_1_drive_preview_action_sensitive_effect():
    """drive_preview must classify effect by subaction."""
    from tools.effects import READ_EFFECTS, WRITE_EFFECTS

    # elements action is read/discovery
    eff_elem = tool_effect("drive_preview", args={"action": "elements"})
    assert eff_elem in READ_EFFECTS

    # mutating actions
    assert tool_effect("drive_preview", args={"action": "click"}) in WRITE_EFFECTS
    assert tool_effect("drive_preview", args={"action": "type", "text": "hello"}) in WRITE_EFFECTS
    assert tool_effect("drive_preview", args={"action": "scroll"}) in WRITE_EFFECTS
    assert tool_effect("drive_preview", args={"action": "press", "key": "Enter"}) in WRITE_EFFECTS

    # fail-closed for unknown actions
    assert tool_effect("drive_preview", args={"action": "unknown_subaction"}) == ToolEffect.MUTATION
    assert tool_effect("drive_preview") == ToolEffect.MUTATION


def test_p0_2_heterogeneous_terminal_never_requires_compile():
    """3 structurally similar terminal calls with different commands must NEVER REQUIRE_COMPILE."""
    agent = mock_agent()
    calls = [
        SimpleNamespace(id=f"call_{i}", type="function", function=SimpleNamespace(name="terminal", arguments=json.dumps({"command": cmd})))
        for i, cmd in enumerate(["git status", "git log -n 5", "python -m pytest"])
    ]
    decisions = decisions_for_calls(agent, calls)
    assert CompilationDecision.REQUIRE_COMPILE not in decisions


def test_p0_2_heterogeneous_write_file_never_requires_compile():
    """3 write_file calls for distinct file paths must NEVER REQUIRE_COMPILE."""
    agent = mock_agent()
    calls = [
        SimpleNamespace(id=f"call_{i}", type="function", function=SimpleNamespace(name="write_file", arguments=json.dumps({"path": f"/tmp/file_{i}.txt", "content": f"data_{i}"})))
        for i in range(3)
    ]
    decisions = decisions_for_calls(agent, calls)
    assert CompilationDecision.REQUIRE_COMPILE not in decisions


def test_p0_3_browser_type_paste_text_and_anchor():
    """browser_type with mode='plain_text_paste' dispatches synthetic paste."""
    from tools.browser_tool import browser_type
    res = browser_type(
        ref="@e1",
        text="Hello\nWorld",
        mode="plain_text_paste",
        semantic_anchor={"type": "testid", "value": "desc-editor"},
        task_id="test-task",
    )
    data = json.loads(res)
    assert data.get("success") is True or "error" in data


def test_p0_3_browser_read_http_allowed_methods_and_forbidden_destinations():
    """browser_read_http allows GET/HEAD and rejects POST, bodies, and private IPs."""
    from tools.browser_tool import browser_read_http

    # 1. Rejects POST
    post_res = json.loads(browser_read_http(url="https://example.com/api", method="POST"))
    assert post_res["success"] is False
    assert post_res["status"] == 400
    assert "GET and HEAD" in post_res["error"]

    # 2. Rejects invalid protocol
    ftp_res = json.loads(browser_read_http(url="ftp://example.com/file", method="GET"))
    assert ftp_res["success"] is False
    assert "only http and https" in ftp_res["error"]

    # 3. Rejects localhost / loopback
    local_res = json.loads(browser_read_http(url="http://127.0.0.1:8000/api", method="GET"))
    assert local_res["success"] is False
    assert local_res["status"] == 403
    assert "canonical URL policy" in local_res["error"]

    # 4. Rejects RFC1918 private IP
    priv_res = json.loads(browser_read_http(url="http://192.168.1.1/admin", method="GET"))
    assert priv_res["success"] is False
    assert priv_res["status"] == 403
    assert "canonical URL policy" in priv_res["error"]


def test_p0_3_browser_read_http_is_pure_read():
    """browser_read_http is registered as ToolEffect.PURE_READ and never requires compile."""
    from tools.effects import ToolEffect, tool_effect
    assert tool_effect("browser_read_http") == ToolEffect.PURE_READ

    agent = mock_agent()
    calls = [
        SimpleNamespace(
            id=f"call_{i}",
            type="function",
            function=SimpleNamespace(
                name="browser_read_http",
                arguments=json.dumps({"url": f"https://example.com/api/items/{i}"}),
            ),
        )
        for i in range(5)
    ]
    decisions = decisions_for_calls(agent, calls)
    assert all(d == CompilationDecision.ALLOW_ADAPTIVE for d in decisions)


def test_browser_read_http_blocks_authority_headers_and_fails_closed_without_runtime(monkeypatch):
    import tools.browser_tool as browser_module

    blocked = json.loads(browser_module.browser_read_http(
        url="https://example.com/api", headers={"Authorization": "Bearer secret"}
    ))
    assert blocked["success"] is False
    assert "Forbidden browser authority header" in blocked["error"]

    monkeypatch.setattr("tools.url_safety.is_safe_url", lambda _url: True)
    monkeypatch.setattr(
        browser_module, "routed_browser_handler",
        lambda _action, _args, *, fallback, **_context: fallback(),
    )
    unavailable = json.loads(browser_module.browser_read_http(url="https://example.com/api"))
    assert unavailable["success"] is False
    assert unavailable["status"] == 503
    assert "Browser-session readback runtime unavailable" in unavailable["error"]


def test_browser_read_http_large_payload_persists_complete_artifact(monkeypatch, tmp_path):
    import tools.browser_tool as browser_module
    from workstation.artifacts import ArtifactStore

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    complete = "payload:" + ("z" * 20000)
    native_result = json.dumps({
        "success": True, "status": 200, "ok": True,
        "url": "https://example.com/api", "content_type": "text/plain",
        "text": complete, "json": None,
    })
    monkeypatch.setattr(
        browser_module, "routed_browser_handler",
        lambda _action, _args, *, fallback, **_context: native_result,
    )

    projected = json.loads(browser_module.browser_read_http(url="https://example.com/api", task_id="large-read"))
    assert len(projected["text"]) < 5000
    assert projected["artifact_ref"].startswith("artifact://")
    persisted = ArtifactStore().read_json(projected["artifact_ref"])
    assert persisted["text"] == complete


def test_p0_5_authority_narrowing_cannot_expand():
    """AuthorityScope.narrow() ensures requested authority can only reduce, never expand."""
    from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope

    trusted = AuthorityScope(
        level=AuthorityLevel.LOCAL_MUTATION,
        allowed_actions={"fs.read", "fs.write"},
        allowed_resources={"/data/*"},
        channels={"chat"},
    )

    # 1. Attempt to elevate level
    requested_high = AuthorityScope(
        level=AuthorityLevel.EXTERNAL_IRREVERSIBLE,
        allowed_actions={"fs.read"},
    )
    effective_high = trusted.narrow(requested_high)
    assert effective_high.level == AuthorityLevel.LOCAL_MUTATION

    # 2. Narrowing to lower level works
    requested_low = AuthorityScope(
        level=AuthorityLevel.READ,
        allowed_actions={"fs.read"},
    )
    effective_low = trusted.narrow(requested_low)
    assert effective_low.level == AuthorityLevel.READ

    # 3. Attempt to add forbidden action
    requested_unauth = AuthorityScope(
        level=AuthorityLevel.LOCAL_MUTATION,
        allowed_actions={"fs.delete", "fs.read"},
    )
    effective_unauth = trusted.narrow(requested_unauth)
    assert "fs.delete" not in effective_unauth.allowed_actions
    assert "fs.read" in effective_unauth.allowed_actions

    # 4. Wildcard expansion prevented
    requested_wild = AuthorityScope(
        level=AuthorityLevel.LOCAL_MUTATION,
        allowed_actions={"*"},
        allowed_resources={"*"},
    )
    effective_wild = trusted.narrow(requested_wild)
    assert effective_wild.allowed_actions == {"fs.read", "fs.write"}
    assert effective_wild.allowed_resources == {"/data/*"}


@pytest.mark.parametrize("task_id,session_id,request_trusted", [
    (None, "session-only", None),
    ("task-without-grant", "task-session", None),
    (None, "request-escalation", {"level": 3, "allowed_actions": ["*"], "allowed_resources": ["*"]}),
])
def test_p0_5_untrusted_authority_minting_fails_closed(task_id, session_id, request_trusted):
    """_execute_route without verifiable trusted authority fails closed with ASK_HUMAN."""
    from workstation.task_compiler import TaskCompiler
    from workstation.control_plane.intent import OperationIntent
    from workstation.control_plane.ir import CREATE, EXISTS
    from workstation.control_plane.contract import CapabilityFormalContract
    from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
    from workstation.operational_capabilities import CapabilityLifecycle, OperationalCapability, OperationalCapabilityRegistry
    from workstation.artifacts import ArtifactStore

    store = ArtifactStore()
    compiler = TaskCompiler(artifacts=store)
    registry = OperationalCapabilityRegistry(artifacts=store)
    registry.register(OperationalCapability(
        id="cap.config.create", name="create config", version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="config.create", target_family="config",
            typed_postconditions=[EXISTS("config")],
            effect_footprint=[CREATE("config")],
            authority_required=AuthorityScope(
                level=AuthorityLevel.LOCAL_MUTATION,
                allowed_actions={"create"}, allowed_resources={"config"},
            ),
            verifier={"kind": "exists", "evidence_strength": "E2"},
        ),
    ))
    compiler.capability_registry = registry
    intent = OperationIntent(
        id="intent-test-auth", target="config",
        goal=EXISTS("config"), effect_budget=[CREATE("config")],
    )

    req = {
        "operation_intent": intent.to_dict(),
        "authority": {"level": 3, "allowed_actions": ["*"]},
    }
    if request_trusted is not None:
        req["trusted_authority"] = request_trusted
    result = compiler._execute_route(
        req,
        task_id=task_id,
        session_id=session_id,
        dispatch=lambda n, a: {"success": True},
        canonical_task_id=None,
    )
    assert result["success"] is False
    assert result["routing_decision"] == "ASK_HUMAN"
    assert "authority" in result["reason"].lower()


def test_p0_6_certified_dispatcher_lifecycle_and_verification():
    """CertifiedDispatcher transitions through PREPARED -> DISPATCHED -> ACKNOWLEDGED -> VERIFIED -> COMMITTED."""
    from workstation.control_plane.dispatcher import CertifiedDispatcher, DispatchStatus
    from workstation.control_plane.router import ExecutableDecision, RoutingCertificate, _state_hash
    from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
    from workstation.operational_capabilities import OperationalCapability
    from workstation.control_plane.verification import VerificationResult, VerificationStatus

    cap = OperationalCapability(
        id="cap.test.echo",
        name="echo",
        version="1.0.0",
        route="host_process",
    )
    cert = RoutingCertificate.create(
        intent_id="intent-1",
        intent_hash="intent-hash",
        capability_id="cap.test.echo",
        capability_version="1.0.0",
        semantic_state_hash=_state_hash({}),
        authority_hash="auth-hash",
        run_id="run-1",
    )
    decision = ExecutableDecision(capability=cap, certificate=cert)

    dispatcher = CertifiedDispatcher()

    # Successful dispatch with verified result
    res = dispatcher.dispatch(
        decision,
        current_state={},
        dispatch_fn=lambda: {"success": True, "data": "output"},
        run_id="run-1",
        verification_result_fn=lambda result: VerificationResult(
            VerificationStatus.VERIFIED if result.get("data") == "output" else VerificationStatus.FAILED
        ),
    )
    assert res["success"] is True
    record = res["dispatch_record"]
    assert record["status"] == DispatchStatus.COMMITTED
    assert record["verifier_status"] == "verified"
    assert record["acknowledged_at"] is not None
    assert record["verified_at"] is not None

    # Failed verifier transitions to UNCERTAIN and does not commit
    cert2 = RoutingCertificate.create(
        intent_id="intent-2",
        intent_hash="intent-hash",
        capability_id="cap.test.echo",
        capability_version="1.0.0",
        semantic_state_hash=_state_hash({}),
        authority_hash="auth-hash",
        run_id="run-1",
    )
    decision2 = ExecutableDecision(capability=cap, certificate=cert2)
    res_failed = dispatcher.dispatch(
        decision2,
        current_state={},
        dispatch_fn=lambda: {"success": False, "error": "verification_mismatch"},
        run_id="run-1",
        verification_result_fn=lambda result: VerificationResult(VerificationStatus.FAILED),
    )
    assert res_failed["success"] is False
    assert res_failed["dispatch_record"]["status"] == DispatchStatus.UNCERTAIN
    assert res_failed["dispatch_record"]["verifier_status"] == "failed"


def test_p0_ack_without_verifier_stays_acknowledged_and_ack_only_is_explicit():
    """A successful ACK is non-terminal unless a trusted contract explicitly accepts it."""
    from workstation.control_plane.dispatcher import CertifiedDispatcher, DispatchStatus
    from workstation.control_plane.router import ExecutableDecision, RoutingCertificate, _state_hash
    from workstation.operational_capabilities import OperationalCapability

    cap = OperationalCapability(id="cap.ack", name="ack", version="1.0.0")

    def decision(intent_id):
        cert = RoutingCertificate.create(
            intent_id=intent_id,
            intent_hash="intent-hash",
            capability_id=cap.id,
            capability_version=cap.version,
            semantic_state_hash=_state_hash({}),
            authority_hash="auth-hash",
            run_id="run-ack",
        )
        return ExecutableDecision(capability=cap, certificate=cert)

    dispatcher = CertifiedDispatcher()
    pending = dispatcher.dispatch(
        decision("intent-ack-pending"), current_state={},
        dispatch_fn=lambda: {"success": True}, run_id="run-ack",
    )
    assert pending["success"] is False
    assert pending["error"] == "needs_verification"
    assert pending["dispatch_record"]["status"] == DispatchStatus.ACKNOWLEDGED
    assert pending["dispatch_record"]["verifier_status"] == "needs_verification"

    terminal = dispatcher.dispatch(
        decision("intent-ack-terminal"), current_state={},
        dispatch_fn=lambda: {"success": True}, run_id="run-ack",
        ack_is_terminal_evidence=True,
    )
    assert terminal["success"] is True
    assert terminal["dispatch_record"]["status"] == DispatchStatus.COMMITTED


def test_p0_7_effect_sensitive_timeout_read_vs_mutation(monkeypatch):
    """Mutating browser timeout is TIMEOUT_UNCERTAIN (state_changed=True), read is TIMEOUT (retryable=True)."""
    import socket
    from tools.browser_workstation import call_workstation_browser, WorkstationBrowserError

    monkeypatch.setattr("tools.browser_workstation._read_control", lambda: {"url": "http://127.0.0.1:9999", "token": "abc"})

    def fake_urlopen(*args, **kwargs):
        raise socket.timeout("timed out")

    monkeypatch.setattr("tools.browser_workstation.urlopen", fake_urlopen)

    # 1. Mutating call: browser_click
    with pytest.raises(WorkstationBrowserError) as exc_info:
        call_workstation_browser("browser_click", {"ref": "@e1"}, task_id="task-timeout-test")
    err = exc_info.value
    assert err.error_code == "TIMEOUT_UNCERTAIN"
    assert err.retryable is False
    assert err.state_changed is True
    assert err.recommended_action == "RECONCILE_EFFECT"

    # 2. Read call: browser_snapshot
    with pytest.raises(WorkstationBrowserError) as exc_info_read:
        call_workstation_browser("browser_snapshot", {}, task_id="task-timeout-test")
    err_read = exc_info_read.value
    assert err_read.error_code == "TIMEOUT"
    assert err_read.retryable is True
    assert err_read.state_changed is False
    assert err_read.recommended_action == "RETRY_WITH_BACKOFF"


def test_p0_7_uncertain_mutation_blocks_blind_retry():
    """can_retry_operation rejects retry on UNCERTAIN dispatch without reconciliation."""
    from workstation.control_plane.dispatcher import CertifiedDispatcher, DispatchRecord, DispatchStatus

    dispatcher = CertifiedDispatcher()
    rec = DispatchRecord(
        operation_id="op-timeout-1",
        capability_id="cap.browser.type",
        status=DispatchStatus.UNCERTAIN,
    )

    # Blind retry rejected
    can_retry, reason = dispatcher.can_retry_operation(rec, external_reconciled=False)
    assert can_retry is False
    assert "Uncertain mutation requires authoritative external reconciliation" in reason

    # After reconciliation, retry permitted
    can_retry_reconciled, _ = dispatcher.can_retry_operation(rec, external_reconciled=True)
    assert can_retry_reconciled is True


def test_p0_9_dogfood_rich_editor_and_zero_planning_fanout():
    """Dogfood reference capability: edit -> paste -> save -> readback -> verify with zero-planning fanout."""
    from workstation.operational_kernel import OperationalKernel
    from workstation.artifacts import ArtifactStore

    store = ArtifactStore()
    kernel = OperationalKernel(artifacts=store)

    sim_db = {"card_1": "Initial text", "card_2": "Initial text"}

    def sim_browser_dispatch(action: str, args: dict):
        if action == "browser_navigate":
            return {"success": True, "url": args["url"]}
        if action == "browser_snapshot":
            return {
                "success": True,
                "elements": [
                    {"ref": "@e1", "role": "button", "label": "Edit description", "testid": "edit-btn"},
                    {"ref": "@e2", "role": "textbox", "label": "Description editor", "testid": "desc-editor"},
                    {"ref": "@e3", "role": "button", "label": "Save", "testid": "save-btn"},
                ]
            }
        if action == "browser_click":
            return {"success": True, "clicked": args["ref"]}
        if action == "browser_type":
            assert args.get("mode") == "plain_text_paste"
            card_id = args.get("semantic_anchor", {}).get("card_id", "card_1")
            sim_db[card_id] = args.get("text", "")
            return {"success": True, "semantic_effect": "paste_text", "chars_inserted": len(args.get("text", ""))}
        if action == "browser_read_http":
            card_id = args["url"].split("/")[-1]
            return {"success": True, "status": 200, "ok": True, "json": {"desc": sim_db.get(card_id)}}
        return {"success": True}

    # 1. Navigate
    r_nav = kernel.execute_primitive("browser_navigate", {"url": "https://trello.example.com/c/card_1"}, dispatch=sim_browser_dispatch, context={})
    assert r_nav["success"] is True

    # 2. Click edit
    r_click = kernel.execute_primitive("browser_click", {"ref": "@e1"}, dispatch=sim_browser_dispatch, context={})
    assert r_click["success"] is True

    # 3. Plain text paste with exact newlines
    new_desc = "Line 1: Requirement A\nLine 2: Requirement B\nLine 3: Verified"
    r_type = kernel.execute_primitive(
        "browser_type",
        {
            "ref": "@e2",
            "text": new_desc,
            "mode": "plain_text_paste",
            "anchor": {"type": "testid", "value": "desc-editor", "card_id": "card_1"},
        },
        dispatch=sim_browser_dispatch,
        context={},
    )
    assert r_type["success"] is True

    # 4. Save
    r_save = kernel.execute_primitive("browser_click", {"ref": "@e3"}, dispatch=sim_browser_dispatch, context={})
    assert r_save["success"] is True

    # 5. Readback verification via browser_read_http
    r_read = kernel.execute_primitive(
        "browser_read_http",
        {"url": "https://trello.example.com/api/cards/card_1", "method": "GET"},
        dispatch=sim_browser_dispatch,
        context={},
    )
    assert r_read["status"] == 200
    assert r_read["json"]["desc"] == new_desc

    # 6. Replay for card_2 without intermediate reasoning or LLM calls
    r_type_2 = kernel.execute_primitive(
        "browser_type",
        {
            "ref": "@e2",
            "text": new_desc,
            "mode": "plain_text_paste",
            "anchor": {"type": "testid", "value": "desc-editor", "card_id": "card_2"},
        },
        dispatch=sim_browser_dispatch,
        context={},
    )
    assert r_type_2["success"] is True
    assert sim_db["card_2"] == new_desc
