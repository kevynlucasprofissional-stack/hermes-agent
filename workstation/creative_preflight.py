"""P05 Creative Preflight: minimal parameter gate for design tasks.

Identifies when a missing specification will materially change the output
and asks exactly one bounded question via the existing clarify tool.
Never blocks point commands ("Abra o PhotoCraft") or requests that already
carry sufficient dimensions. Defaults are reversible; silent dimension
choices that could invalidate the work are forbidden.

The response is persisted on the current TaskRun, not in permanent memory.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CreativePreflightResult:
    """Outcome of a creative preflight check."""

    needs_clarification: bool
    question: str | None = None
    choices: list[str] | None = None
    default: str | None = None
    reason: str = ""
    detected_dimensions: dict[str, str] | None = None


# Matches explicit pixel dimensions like "1080x1440", "1920×1080", "1080 x 1440"
_DIMENSION_PATTERN = re.compile(
    r"\b(\d{2,5})\s*[xX×]\s*(\d{2,5})\b"
)

# Commands that bypass preflight entirely (point actions, not design tasks)
_BYPASS_PATTERNS = [
    re.compile(r"^(?:por favor )?(?:abre|abra|abrir|open) (?:o |a )?"
               r"(photo ?craft|effect ?craft|film ?craft)(?: por favor)?$", re.IGNORECASE),
    re.compile(r"^(?:por favor )?(?:fecha|feche|fechar|close) (?:o |a )?"
               r"(documento|aba|tab|janela|window)(?: por favor)?$", re.IGNORECASE),
    re.compile(r"^(?:salva|salve|salvar|save|exporta|exporte|exportar)(?: por favor)?$", re.IGNORECASE),
]

# Design task indicators that may need dimension clarification
_DESIGN_TASK_PATTERNS = [
    re.compile(r"\b(cri[ae]r?|create|fa[cç]a|fazer|make|desenha?r?|design|monta?r?)\b.*"
               r"\b(convite|poster|banner|flyer|cartaz|story|feed|post|"
               r"apresenta[cç][aã]o|slide|thumbnail|capa|cover|card)\b", re.IGNORECASE),
    re.compile(r"\b(invitation|poster|banner|flyer|story|feed|thumbnail|"
               r"presentation|slide|cover|card)\b.*\b(create|make|design|build)\b", re.IGNORECASE),
]

# Format/destination choices for common design tasks
_FORMAT_CHOICES = [
    "Feed Instagram/Facebook (1080×1080)",
    "Story/Reels (1080×1920)",
    "Post retrato LinkedIn (1080×1350)",
    "Impressão A4 vertical (2480×3508)",
]


def _has_explicit_dimensions(text: str) -> bool:
    """Check if the message already contains pixel dimensions."""
    return bool(_DIMENSION_PATTERN.search(text))


def _is_point_command(text: str) -> bool:
    """Check if this is a point action that should bypass preflight."""
    normalized = text.strip().rstrip(".!?")
    return any(p.fullmatch(normalized) for p in _BYPASS_PATTERNS)


def _is_design_task(text: str) -> bool:
    """Check if this looks like a design task that may need dimensions."""
    return any(p.search(text) for p in _DESIGN_TASK_PATTERNS)


def check_creative_preflight(content: str, task_context: dict[str, Any] | None = None) -> CreativePreflightResult:
    """Evaluate whether a creative request needs a clarifying question.

    Returns a result indicating whether to ask, what to ask, and why.
    The caller is responsible for dispatching the clarify tool call;
    this function is pure and has no side effects.
    """
    if not isinstance(content, str) or not content.strip():
        return CreativePreflightResult(needs_clarification=False, reason="empty_content")

    # Point commands never trigger preflight
    if _is_point_command(content):
        return CreativePreflightResult(needs_clarification=False, reason="point_command_bypass")

    # Already has dimensions — proceed without asking
    if _has_explicit_dimensions(content):
        dims = _DIMENSION_PATTERN.search(content)
        detected = {"width": dims.group(1), "height": dims.group(2)} if dims else None
        return CreativePreflightResult(
            needs_clarification=False,
            reason="dimensions_already_specified",
            detected_dimensions=detected,
        )

    # Check if prior turns in this TaskRun already answered format
    if task_context:
        prior_format = task_context.get("creative_format") or task_context.get("format")
        prior_dimensions = task_context.get("creative_dimensions") or task_context.get("dimensions")
        if prior_format or prior_dimensions:
            return CreativePreflightResult(
                needs_clarification=False,
                reason="format_answered_in_prior_turn",
                detected_dimensions={"source": "task_context"},
            )

    # Design task without dimensions — ask one bounded question
    if _is_design_task(content):
        return CreativePreflightResult(
            needs_clarification=True,
            question="Qual é o formato ou destino deste material? Isso define as dimensões corretas do documento.",
            choices=_FORMAT_CHOICES,
            default=_FORMAT_CHOICES[0],
            reason="design_task_missing_dimensions",
        )

    # Not a recognized design task — don't block
    return CreativePreflightResult(needs_clarification=False, reason="not_design_task")


def build_clarify_payload(result: CreativePreflightResult) -> list[dict[str, Any]] | None:
    """Convert a preflight result into a clarify tool questions array.

    Returns None if no clarification is needed.
    """
    if not result.needs_clarification or not result.question:
        return None
    payload: dict[str, Any] = {"question": result.question}
    if result.choices:
        choices = list(result.choices)
        if result.default and choices and choices[0] != result.default:
            choices.remove(result.default)
            choices.insert(0, result.default)
        payload["choices"] = choices
    return [payload]