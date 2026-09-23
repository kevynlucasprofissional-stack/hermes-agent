"""Trusted effect authority bridge: production grant path for pre-reasoning reuse.

``workstation.integrations.hermes.effect_authority`` converts trusted ingress
(``MessageEnvelope``) plus canonical task/session identity into a control-plane
``AuthorityScope`` ceiling. The request/intent may narrow it, never expand it.

These tests pin the conservative H-080A policy:
- authenticated HUMAN + CREATE_WORK + bound active matching task → LOCAL_MUTATION;
- everything else degrades to READ;
- EXTERNAL_REVERSIBLE/IRREVERSIBLE are never implicitly granted;
- narrowing is monotonic (request cannot expand the trusted ceiling).
"""

from __future__ import annotations

from types import SimpleNamespace

from workstation.contracts import IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.integrations.hermes.effect_authority import (
    TrustedAuthorityContext,
    trusted_effect_authority,
    trusted_effect_authority_from_agent,
)

SESSION = "authority-session"
BODY = "First write the file then verify the content"


def _envelope(
    origin=MessageOrigin.HUMAN,
    authority=IntentAuthority.CREATE_WORK,
    session_id=SESSION,
    content=BODY,
):
    return MessageEnvelope(origin, authority, session_id, content)


def _task(session_id=SESSION, body=BODY, status="running"):
    return SimpleNamespace(id="t-auth", session_id=session_id, body=body, status=status)


def test_human_create_work_matching_task_gets_local_mutation_ceiling():
    scope = trusted_effect_authority(TrustedAuthorityContext(
        envelope=_envelope(), canonical_task=_task(), session_id=SESSION,
    ))
    assert scope.level == AuthorityLevel.LOCAL_MUTATION


def test_observation_only_gets_read():
    scope = trusted_effect_authority(TrustedAuthorityContext(
        envelope=_envelope(authority=IntentAuthority.OBSERVATION_ONLY),
        canonical_task=_task(), session_id=SESSION,
    ))
    assert scope.level == AuthorityLevel.READ


def test_update_work_gets_read():
    scope = trusted_effect_authority(TrustedAuthorityContext(
        envelope=_envelope(authority=IntentAuthority.UPDATE_WORK),
        canonical_task=_task(), session_id=SESSION,
    ))
    assert scope.level == AuthorityLevel.READ


def test_wrong_session_gets_read():
    scope = trusted_effect_authority(TrustedAuthorityContext(
        envelope=_envelope(), canonical_task=_task(), session_id="other-session",
    ))
    assert scope.level == AuthorityLevel.READ


def test_task_body_mismatch_gets_read():
    scope = trusted_effect_authority(TrustedAuthorityContext(
        envelope=_envelope(), canonical_task=_task(body="something else"), session_id=SESSION,
    ))
    assert scope.level == AuthorityLevel.READ


def test_finished_task_gets_read():
    for status in ("done", "cancelled"):
        scope = trusted_effect_authority(TrustedAuthorityContext(
            envelope=_envelope(), canonical_task=_task(status=status), session_id=SESSION,
        ))
        assert scope.level == AuthorityLevel.READ


def test_delegated_agent_without_trusted_origin_gets_read():
    scope = trusted_effect_authority(TrustedAuthorityContext(
        envelope=_envelope(origin=MessageOrigin.AGENT, authority=IntentAuthority.DELEGATE_WORK),
        canonical_task=_task(), session_id=SESSION,
    ))
    assert scope.level == AuthorityLevel.READ


def test_connector_origin_gets_read():
    scope = trusted_effect_authority(TrustedAuthorityContext(
        envelope=_envelope(origin=MessageOrigin.CONNECTOR, authority=IntentAuthority.DELEGATE_WORK),
        canonical_task=_task(), session_id=SESSION,
    ))
    assert scope.level == AuthorityLevel.READ


def test_missing_envelope_gets_read():
    scope = trusted_effect_authority(TrustedAuthorityContext(
        envelope=None, canonical_task=_task(), session_id=SESSION,
    ))
    assert scope.level == AuthorityLevel.READ


def test_external_irreversible_never_implicitly_granted():
    scope = trusted_effect_authority(TrustedAuthorityContext(
        envelope=_envelope(), canonical_task=_task(), session_id=SESSION,
    ))
    assert scope.level != AuthorityLevel.EXTERNAL_IRREVERSIBLE
    assert scope.level != AuthorityLevel.EXTERNAL_REVERSIBLE
    assert scope.level == AuthorityLevel.LOCAL_MUTATION


def test_request_cannot_expand_trusted_ceiling():
    trusted = trusted_effect_authority(TrustedAuthorityContext(
        envelope=_envelope(), canonical_task=_task(), session_id=SESSION,
    ))
    requested = AuthorityScope(
        level=AuthorityLevel.EXTERNAL_IRREVERSIBLE,
        allowed_actions={"*"}, allowed_resources={"*"},
    )
    effective = trusted.narrow(requested)
    assert int(effective.level) <= int(AuthorityLevel.LOCAL_MUTATION)


def test_trusted_ceiling_narrows_requested_scope():
    trusted = trusted_effect_authority(TrustedAuthorityContext(
        envelope=_envelope(), canonical_task=_task(), session_id=SESSION,
    ))
    requested = AuthorityScope(
        level=AuthorityLevel.READ, allowed_actions=set(), allowed_resources=set(),
    )
    effective = trusted.narrow(requested)
    assert effective.level == AuthorityLevel.READ


def test_from_agent_reads_envelope_and_task(monkeypatch):
    from hermes_cli import kanban_db

    task = _task()
    monkeypatch.setattr(kanban_db, "get_task", lambda conn, task_id: task)
    monkeypatch.setattr(
        "workstation.kanban.WorkstationKanbanBridge.get_connection",
        lambda self: SimpleNamespace(close=lambda: None),
    )
    agent = SimpleNamespace(
        _message_envelope=_envelope(),
        _canonical_work_task_id="t-auth",
    )
    scope = trusted_effect_authority_from_agent(agent, SESSION, canonical_task=task)
    assert scope.level == AuthorityLevel.LOCAL_MUTATION
