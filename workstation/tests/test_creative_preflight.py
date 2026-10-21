"""P05 Creative Preflight: unit tests for the minimal parameter gate.

Pure-function tests — no agent, no browser, no IO. Validates that the
preflight asks exactly when needed and never blocks point commands or
requests that already carry sufficient dimensions.
"""
from __future__ import annotations

import pytest

from workstation.creative_preflight import (
    CreativePreflightResult,
    build_clarify_payload,
    check_creative_preflight,
)


class TestPointCommandBypass:
    """Point commands must never trigger preflight."""

    @pytest.mark.parametrize("command", [
        "Abre o PhotoCraft",
        "abra o photocraft",
        "Abrir o EffectCraft",
        "open FilmCraft",
        "Fecha o documento",
        "feche a aba",
        "Salva",
        "exporte",
    ])
    def test_point_commands_bypass(self, command: str) -> None:
        result = check_creative_preflight(command)
        assert not result.needs_clarification
        assert result.reason == "point_command_bypass"


class TestExplicitDimensions:
    """Requests with pixel dimensions must proceed without asking."""

    @pytest.mark.parametrize("request_text", [
        "Crie um convite 1080x1440",
        "Faça um banner 1920×1080 para o feed",
        "Criar poster 2480 x 3508",
        "Design de thumbnail 1280X720",
    ])
    def test_dimensions_detected(self, request_text: str) -> None:
        result = check_creative_preflight(request_text)
        assert not result.needs_clarification
        assert result.reason == "dimensions_already_specified"
        assert result.detected_dimensions is not None

    def test_dimensions_extracted_correctly(self) -> None:
        result = check_creative_preflight("Crie um convite 1080x1440")
        assert result.detected_dimensions == {"width": "1080", "height": "1440"}


class TestDesignTaskClarification:
    """Design tasks without dimensions must ask one bounded question."""

    @pytest.mark.parametrize("request_text", [
        "Crie um convite de aniversário",
        "Faça um banner para o Instagram",
        "Criar um poster promocional",
        "Monta um story para o lançamento",
        "Design de thumbnail para vídeo",
    ])
    def test_design_task_asks_format(self, request_text: str) -> None:
        result = check_creative_preflight(request_text)
        assert result.needs_clarification
        assert result.question is not None
        assert result.choices is not None
        assert len(result.choices) >= 2
        assert result.reason == "design_task_missing_dimensions"

    def test_clarify_payload_structure(self) -> None:
        result = check_creative_preflight("Crie um convite de aniversário")
        payload = build_clarify_payload(result)
        assert payload is not None
        assert len(payload) == 1
        assert "question" in payload[0]
        assert "choices" in payload[0]


class TestPriorTurnContext:
    """Format answered in prior turns must not re-ask."""

    def test_prior_format_bypasses(self) -> None:
        context = {"creative_format": "Story/Reels (1080×1920)"}
        result = check_creative_preflight("Agora crie o convite", task_context=context)
        assert not result.needs_clarification
        assert result.reason == "format_answered_in_prior_turn"

    def test_prior_dimensions_bypasses(self) -> None:
        context = {"dimensions": "1080x1440"}
        result = check_creative_preflight("Faça o banner agora", task_context=context)
        assert not result.needs_clarification
        assert result.reason == "format_answered_in_prior_turn"


class TestNonDesignTasks:
    """Non-design requests must never be blocked by preflight."""

    @pytest.mark.parametrize("request_text", [
        "Abra o Trello",
        "Pesquise sobre marketing digital",
        "Me mostre as tarefas pendentes",
        "Qual é a previsão do tempo?",
        "Liste os arquivos do projeto",
    ])
    def test_non_design_tasks_pass_through(self, request_text: str) -> None:
        result = check_creative_preflight(request_text)
        assert not result.needs_clarification
        assert result.reason == "not_design_task"


class TestEdgeCases:
    """Boundary conditions and malformed input."""

    def test_empty_content(self) -> None:
        result = check_creative_preflight("")
        assert not result.needs_clarification
        assert result.reason == "empty_content"

    def test_none_content(self) -> None:
        result = check_creative_preflight(None)  # type: ignore[arg-type]
        assert not result.needs_clarification

    def test_whitespace_only(self) -> None:
        result = check_creative_preflight("   ")
        assert not result.needs_clarification

    def test_build_clarify_payload_returns_none_when_no_clarification(self) -> None:
        result = check_creative_preflight("Abre o PhotoCraft")
        assert build_clarify_payload(result) is None