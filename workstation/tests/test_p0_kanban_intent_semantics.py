"""Durable tasks reflect an actionable request, not topic mentions or punctuation."""
import pytest

from workstation.kanban import is_multistep_request
from workstation.work_intent import work_intent
from workstation.contracts import MessageEnvelope, MessageOrigin, IntentAuthority


@pytest.mark.parametrize("prompt", [
    "Explique o workflow de edição de vídeos.",
    "Me mostre o pipeline do Hermes.",
    "Me ajude a entender o que significa multistep",
    "Descreva o processo passo a passo.",
    "Me mostre 3 workflows de automacao.",
    "Me explique cada tarefa do Kanban.",
])
def test_informational_topics_do_not_create_kanban_work(prompt):
    intent = work_intent(MessageEnvelope(MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK,
                                          "session", prompt))
    assert not intent.requires_task
    assert not is_multistep_request(prompt)


@pytest.mark.parametrize("prompt", [
    "Primeiro analise os arquivos, depois gere um relatório e salve os resultados.",
    "Quero que você investigue, corrija e teste este bug?",
    "Implemente a API e depois escreva testes.",
])
def test_multistage_explicit_requests_are_durable(prompt):
    intent = work_intent(MessageEnvelope(MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK,
                                          "session", prompt))
    assert intent.requires_task

def test_readonly_browser_navigation_with_negated_constraints_is_not_durable():
    """Prohibiting writes cannot manufacture a durable write assignment."""
    prompt = (
        "Open ONLY the local QA page http://127.0.0.1:63050/ using native "
        "browser_navigate. This is a READ-ONLY navigation test. "
        "Do not type in any field, do not click Save, do not post data, "
        "do not create tasks or modify any remote or local information. "
        "Briefly state the page title after navigation."
    )
    intent = work_intent(MessageEnvelope(
        MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, "qa-navigation", prompt,
    ))
    assert not is_multistep_request(prompt)
    assert not intent.requires_task
