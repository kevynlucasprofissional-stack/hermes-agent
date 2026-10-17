"""Fresh commands reach the existing router without a historical objective."""
from types import SimpleNamespace

from agent.operational_resolution import OperationalOutcome, OperationalResolutionContext
from workstation.contracts import IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.ir import EQ, SET
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.durable_tasks import DurableTaskStore
from workstation.integrations.hermes.operational_resolution import workstation_operational_resolution
from workstation.operational_capabilities import (
    CapabilityLifecycle, OperationalCapability, OperationalCapabilityRegistry,
)
from workstation.work_intent import prepare_turn_work


def admit(text, authority=IntentAuthority.CREATE_WORK):
    agent = SimpleNamespace(session_id="fresh-command", _conversation_root_id=lambda: "fresh-command",
        _interrupt_requested=False, _tool_guardrails=None, _work_capabilities={},
        _work_user_constraints={}, _current_provider_usage=None, _work_completed_mutations={},
        _work_mutation_evidence={}, _workstation_event_bus=None, valid_tool_names=set())
    envelope = MessageEnvelope(MessageOrigin.HUMAN, authority, agent.session_id, text)
    return agent, prepare_turn_work(agent, text, envelope)


def consult(agent):
    return workstation_operational_resolution(OperationalResolutionContext(
        agent=agent, session_id=agent.session_id,
        task_id=str(getattr(agent, "_canonical_work_task_id", "") or ""), turn_id="fresh-turn",
        user_message=agent._message_envelope.content, messages=[], api_call_count=0, iteration=0))


def test_one_shot_trello_command_is_not_a_durable_kanban_task():
    agent, work = admit("Abre o Trello.")
    assert not work.requires_task and work.requires_browser
    assert work.admission_kind == "point_action"
    assert getattr(agent, "_canonical_work_task_id", None) is None
    # A capability's existence must not auto-mint a TaskRun or effect authority.
    OperationalCapabilityRegistry().register(OperationalCapability(
        id="test.open_trello", name="open Trello", version="1",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="browser.open_site", target_family="native_browser",
            typed_postconditions=[EQ("host", "trello.com"), EQ("page_family", "/"), EQ("recovery_state", "live")],
            effect_footprint=[SET("host", "trello.com"), SET("page_family", "/"), SET("recovery_state", "live")],
            authority_required=AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE,
                allowed_actions={"navigate"}, allowed_resources={"native_browser"}),
            verifier={"kind": "value", "evidence_strength": "E2"})))
    assert consult(agent) is None
    store = DurableTaskStore()
    try:
        assert store.get_connection().execute("SELECT COUNT(*) FROM work_plans").fetchone()[0] == 0
    finally:
        store.close()


def test_ambiguous_observed_uninstalled_and_cancelled_commands_do_not_dispatch():
    for text in ("Abre o Trello ou o Hyperframe.", "Não abre o Trello.",
                 "Como abre o Trello?", "Abre o Trello e apaga tudo."):
        agent, work = admit(text)
        assert not work.requires_task
        assert consult(agent) is None
    observed, work = admit("Abre o Trello.", IntentAuthority.OBSERVATION_ONLY)
    assert not work.requires_task and consult(observed) is None
    fresh, work = admit("Abre o Trello.")
    assert not work.requires_task
    assert consult(fresh) is None, "missing installed capability falls back to reasoning"
    fresh._interrupt_requested = True
    assert consult(fresh) is None


def test_one_shot_browser_failure_handoffs_without_creating_task():
    """Native prefab failures are not silently retried through task execution."""
    from unittest.mock import patch
    from workstation.prefabs.integration import prepare_user_navigation
    agent, work = admit("Abre o Trello.")
    assert not work.requires_task
    agent._prefab_navigation_intent = prepare_user_navigation(agent._message_envelope)
    assert agent._prefab_navigation_intent
    agent.valid_tool_names = {"browser_navigate", "browser_snapshot"}
    with patch("workstation.integrations.hermes.scoped_execution.workstation_durable_dispatch",
               return_value=lambda *a: "{}"):
        with patch("workstation.prefabs.integration.navigate",
                   side_effect=RuntimeError("Controller connection lost")):
            resolution = consult(agent)
    assert resolution is not None
    assert resolution.outcome is OperationalOutcome.HANDOFF
    assert resolution.reason == "prefab_dispatch_uncertain"
    assert consult(agent) is None  # consumed once; no retry
    assert getattr(agent, "_canonical_work_task_id", None) is None


def test_fresh_hyperframe_command_falls_back_safely_without_studio_capability():
    """P1.5 RED lock: 'Abre o Hyperframe.' must not dispatch terminal/skill search.

    No creative capability is installed in this context, so resolution must fall
    back to reasoning (None) — never EXECUTED, never a terminal/skill-search
    side effect from the pre-reasoning path.
    """
    agent, work = admit("Abre o Hyperframe.")
    assert not work.requires_task and work.admission_kind == "point_action"
    # No creative capability is installed: the router must refuse without
    # effects and the boundary must fall back to reasoning (None) — never
    # EXECUTED from the pre-reasoning path without owner-certified readback.
    resolution = consult(agent)
    assert resolution is None
    # Ambiguous Hyperframe variants stay reasoning work.
    for text in ("Abre o Hyperframe ou o Trello.", "Como abre o Hyperframe?",
                 "Abre o Hyperframe e apaga tudo."):
        ambiguous, ambiguous_work = admit(text)
        assert not ambiguous_work.requires_task
        assert consult(ambiguous) is None


def test_one_shot_creative_web_app_commands_are_point_actions():
    for text in ("Abre o PhotoCraft.", "Abra o EffectCraft.", "Abrir Photo Craft", "Open Effect Craft"):
        agent, work = admit(text)
        assert not work.requires_task
        assert work.requires_browser
        assert work.admission_kind == "point_action"
        assert getattr(agent, "_canonical_work_task_id", None) is None
        # Without tools in session, falls back to reasoning safely without creating tasks
        assert consult(agent) is None


def test_one_shot_photocraft_fast_path_verified():
    from unittest.mock import patch
    from workstation.creative_web_service import CreativeWebAppLaunchReceipt
    from workstation.prefabs.integration import prepare_user_creative_app

    agent, _work = admit("Abre o PhotoCraft.")
    agent._prefab_creative_app_intent = prepare_user_creative_app(agent._message_envelope)
    assert agent._prefab_creative_app_intent is not None
    assert agent._prefab_creative_app_intent.key == "photocraft"
    agent.valid_tool_names = {"browser_navigate", "browser_snapshot"}

    mock_receipt = CreativeWebAppLaunchReceipt(
        status="verified",
        engine="photocraft",
        url="http://127.0.0.1:8765/",
        port=8765,
        observed_url="http://127.0.0.1:8765/",
        reason="creative_photocraft_open_verified",
        reused=False,
        dispatch_attempted=True,
    )

    with patch("workstation.integrations.hermes.scoped_execution.workstation_durable_dispatch",
               return_value=lambda *a: "{}"):
        with patch("workstation.creative_web_service.open_and_verify_creative_web_app",
                   return_value=mock_receipt):
            res = consult(agent)

    assert res is not None
    assert res.outcome is OperationalOutcome.EXECUTED
    assert res.reason == "creative_photocraft_open_verified"
    assert "8765" in res.final_response
    # Consumed once: second consult returns None
    assert consult(agent) is None


def test_one_shot_creative_web_app_human_lease_handoff():
    from unittest.mock import patch
    from workstation.creative_web_service import CreativeWebAppLaunchReceipt
    from workstation.prefabs.integration import prepare_user_creative_app

    agent, _work = admit("Abre o EffectCraft.")
    agent._prefab_creative_app_intent = prepare_user_creative_app(agent._message_envelope)
    agent.valid_tool_names = {"browser_navigate", "browser_snapshot"}

    mock_receipt = CreativeWebAppLaunchReceipt(
        status="user_control_active",
        engine="effectcraft",
        reason="user_control_active",
        dispatch_attempted=True,
    )

    with patch("workstation.integrations.hermes.scoped_execution.workstation_durable_dispatch",
               return_value=lambda *a: "{}"):
        with patch("workstation.creative_web_service.open_and_verify_creative_web_app",
                   return_value=mock_receipt):
            res = consult(agent)

    assert res is not None
    assert res.outcome is OperationalOutcome.HANDOFF
    assert res.reason == "user_control_active"


def test_one_shot_creative_web_app_missing_dist_handoff():
    from unittest.mock import patch
    from workstation.creative_web_service import CreativeWebAppLaunchReceipt
    from workstation.prefabs.integration import prepare_user_creative_app

    agent, _work = admit("Abre o PhotoCraft.")
    agent._prefab_creative_app_intent = prepare_user_creative_app(agent._message_envelope)
    agent.valid_tool_names = {"browser_navigate", "browser_snapshot"}

    mock_receipt = CreativeWebAppLaunchReceipt(
        status="missing_dist",
        engine="photocraft",
        reason="missing_prebuilt_web_dist:photocraft",
    )

    with patch("workstation.integrations.hermes.scoped_execution.workstation_durable_dispatch",
               return_value=lambda *a: "{}"):
        with patch("workstation.creative_web_service.open_and_verify_creative_web_app",
                   return_value=mock_receipt):
            res = consult(agent)

    assert res is not None
    assert res.outcome is OperationalOutcome.HANDOFF
    assert res.reason == "missing_prebuilt_web_dist"


def test_one_shot_filmcraft_fast_path_verified():
    from unittest.mock import patch
    from workstation.creative_web_service import CreativeWebAppLaunchReceipt
    from workstation.prefabs.integration import prepare_user_creative_app

    agent, _work = admit("Abra o FilmCraft.")
    agent._prefab_creative_app_intent = prepare_user_creative_app(agent._message_envelope)
    assert agent._prefab_creative_app_intent is not None
    assert agent._prefab_creative_app_intent.key == "filmcraft"
    agent.valid_tool_names = {"browser_navigate", "browser_snapshot"}

    mock_receipt = CreativeWebAppLaunchReceipt(
        status="verified",
        engine="filmcraft",
        url="http://127.0.0.1:8767/",
        port=8767,
        observed_url="http://127.0.0.1:8767/",
        reason="creative_filmcraft_open_verified",
        reused=False,
        dispatch_attempted=True,
    )

    with patch("workstation.integrations.hermes.scoped_execution.workstation_durable_dispatch",
               return_value=lambda *a: "{}"):
        with patch("workstation.creative_web_service.open_and_verify_creative_web_app",
                   return_value=mock_receipt):
            res = consult(agent)

    assert res is not None
    assert res.outcome is OperationalOutcome.EXECUTED
    assert res.reason == "creative_filmcraft_open_verified"
    assert "8767" in res.final_response
    assert "FilmCraft" in res.final_response


