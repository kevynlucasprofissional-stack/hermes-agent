"""Regressions for deterministic named-site intents and native-browser contracts."""

from workstation.contracts import IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.control_plane.intent import OperationIntent
from workstation.control_plane.ir import AND, CALL, EQ, SET, entails, effect_contained
from workstation.work_intent import current_command_objective


def test_named_trello_navigation_projects_native_browser_state_contract():
    envelope = MessageEnvelope(MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, "session-a", "Abre o Trello.")
    result = current_command_objective(envelope, "task-a", "run-a")
    assert result is not None
    intent = OperationIntent.from_dict(result["operation_intent"])
    assert intent.target == "native_browser"
    # Fixed allowlisted navigation binds destination in the contract, not as
    # an unsolicited parameter to a compiled zero-input capability.
    assert result["inputs"] == {}
    postconditions = [EQ("host", "trello.com"), EQ("page_family", "/"), EQ("recovery_state", "live")]
    effect_footprint = [SET("host", "trello.com"), SET("page_family", "/"), SET("recovery_state", "live")]
    assert entails(AND(*postconditions), intent.goal)
    assert all(effect_contained(e, intent.effect_budget) for e in effect_footprint)
    assert not entails(AND(EQ("host", "wrong.test")), intent.goal)
    assert SET("host", "wrong.test") not in intent.effect_budget
    # General SET effect containment is path-based, so the exact hostname
    # must remain an independently proven goal (never inferred from budget).


def test_unrecognized_or_untrusted_command_cannot_produce_native_intent():
    for content in ("Abra um site qualquer.", "Não abre o Trello.", "Abra o Trello e apague tudo."):
        envelope = MessageEnvelope(MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, "session-a", content)
        assert current_command_objective(envelope, "task", "run") is None
    envelope = MessageEnvelope(MessageOrigin.RUNTIME, IntentAuthority.OBSERVATION_ONLY, "session-a", "Abre o Trello.")
    assert current_command_objective(envelope, "task", "run") is None

def test_named_site_command_explicitly_budgets_only_its_external_navigation_effect():
    from workstation.control_plane.lattice import (
        AuthorityLevel, AuthorityScope, can_execute_effect,
    )

    envelope = MessageEnvelope(MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK,
                               "session-a", "Abra o Trello")
    objective = current_command_objective(envelope, "task", "run")
    intent = OperationIntent.from_dict(objective["operation_intent"])
    permitted = CALL("browser.navigate", "trello.com")
    other = CALL("browser.navigate", "wrong.test")
    assert effect_contained(permitted, intent.effect_budget)
    assert not effect_contained(other, intent.effect_budget)
    read_only = AuthorityScope(level=AuthorityLevel.READ)
    scoped = AuthorityScope(
        level=AuthorityLevel.EXTERNAL_REVERSIBLE,
        allowed_actions={"browser.navigate"},
        allowed_resources={"trello.com"},
    )
    assert not can_execute_effect(permitted, intent, read_only)
    assert can_execute_effect(permitted, intent, scoped)
    assert not can_execute_effect(other, intent, scoped)


def test_named_creative_web_app_intent_contracts():
    for name in ("PhotoCraft", "EffectCraft", "FilmCraft"):
        envelope = MessageEnvelope(MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK,
                                   "session-c", f"Abra o {name}")
        objective = current_command_objective(envelope, "task-c", "run-c")
        assert objective is not None
        intent = OperationIntent.from_dict(objective["operation_intent"])
        assert intent.target == "native_browser"
        engine_key = name.lower()
        assert objective["inputs"] == {"engine": engine_key}
        postconditions = [EQ("host", "127.0.0.1"), EQ(f"creative.{engine_key}.ready", True)]
        effect_footprint = [SET("host", "127.0.0.1"), SET(f"creative.{engine_key}.ready", True)]
        assert entails(AND(*postconditions), intent.goal)
        assert all(effect_contained(e, intent.effect_budget) for e in effect_footprint)
        assert effect_contained(CALL("browser.navigate", "127.0.0.1"), intent.effect_budget)
