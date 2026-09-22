"""Pre-reasoning operational resolution boundary.

An operational supervisor — a work-execution runtime, a workflow engine, a
first-party product layer — can answer one question *before* the turn loop spends
a reasoning round on the provider LLM:

    Is this turn already advanced far enough that another round of reasoning
    would only rediscover something the operational plane already knows?

The harness owns only the contract:

* the context handed to a provider is read-only turn identity (session, task,
  turn, iteration, the assembled transcript);
* a provider answers with :class:`OperationalResolution` — either
  ``CONTINUE_REASONING`` (the default; the loop proceeds to the provider) or a
  terminal outcome (``SATISFIED`` / ``EXECUTED`` / ``WAIT`` / ``HANDOFF``) plus
  the text that closes the turn for the user;
* the harness knows nothing about how a provider decided. A provider cannot
  grant itself authority, change loop state, or make the harness dispatch
  anything the harness would not otherwise have dispatched.

This is the harness-level counterpart of ``turn_admission`` / ``tool_batch_admission``:
those bound identity *before* a turn and admitted a batch *after* the model
spoke. This one sits between the two, at the narrowest point whose purpose is to
call the model.

Provider contract (binding):

1. **Total, not optimistic.** A provider answers ``CONTINUE_REASONING`` for every
   condition it does not positively resolve. Raising is reserved for defects:
   the harness logs at ERROR and degrades to reasoning — an optimizer bug must
   never break a turn, and the degraded direction is always "reason", never
   "act".
2. **No terminal outcome without proof.** ``SATISFIED``/``EXECUTED`` may only be
   returned once the provider has itself established the outcome through its own
   certified dispatch and independently verified it. Tool acknowledgement,
   repetition, model output and classifier confidence are not proof.
3. **Never dispatch and then raise.** If a provider cannot classify the outcome
   of an effect it already started, it returns a terminal ``WAIT``/``HANDOFF``
   so the uncertainty stays owned by the durable journal instead of silently
   falling through to a reasoning round that could dispatch it twice.
4. **Observation is idempotent.** The boundary is consulted on every iteration of
   a turn; being asked must not mutate durable state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class OperationalOutcome(str, Enum):
    """What the operational plane can answer before a reasoning round is spent."""

    CONTINUE_REASONING = "CONTINUE_REASONING"
    SATISFIED = "SATISFIED"
    EXECUTED = "EXECUTED"
    WAIT = "WAIT"
    HANDOFF = "HANDOFF"


@dataclass(frozen=True)
class OperationalResolutionContext:
    """Read-only turn identity handed to operational resolution providers.

    ``messages`` is the live transcript list the loop is about to project into a
    request. Providers must not mutate it — the loop owns it, and it is passed
    for inspection only.
    """

    agent: Any
    session_id: str
    task_id: str
    turn_id: str
    user_message: Any
    messages: Any
    api_call_count: int
    iteration: int


@dataclass
class OperationalResolution:
    """A provider's answer for one resolution step."""

    outcome: OperationalOutcome = OperationalOutcome.CONTINUE_REASONING
    final_response: Optional[str] = None
    reason: str = ""
    provider: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.outcome is not OperationalOutcome.CONTINUE_REASONING


# Signature: (context) -> Optional[OperationalResolution]
OperationalResolutionProvider = Callable[[OperationalResolutionContext], Optional[OperationalResolution]]

_providers: list[OperationalResolutionProvider] = []

# Resolution accounting. ``unknown`` is never folded into zero: a step that was
# never consulted is a miss in coverage, not a hit.
_metrics: Dict[str, int] = {
    "steps": 0,
    "attempts": 0,
    "hits": 0,
    "misses": 0,
    "errors": 0,
    "self_reported": 0,
}


def register_operational_resolution_provider(provider: OperationalResolutionProvider) -> None:
    if provider not in _providers:
        _providers.append(provider)


def unregister_operational_resolution_provider(provider: OperationalResolutionProvider) -> None:
    if provider in _providers:
        _providers.remove(provider)


def operational_resolution_providers() -> tuple[OperationalResolutionProvider, ...]:
    return tuple(_providers)


def operational_resolution_metrics() -> Dict[str, int]:
    """Counters since the last reset. ``attempts`` counts provider consultations."""
    return dict(_metrics)


def reset_operational_resolution() -> None:
    """Drop providers and counters. For lifecycle/test teardown, not for turns."""
    _providers.clear()
    for key in _metrics:
        _metrics[key] = 0


def _provider_name(provider: Any) -> str:
    return getattr(provider, "__name__", None) or repr(provider)


def resolve_operational_step(context: OperationalResolutionContext) -> OperationalResolution:
    """Ask every operational provider, in registration order, for a terminal answer.

    Returns the first terminal resolution, or ``CONTINUE_REASONING`` when nothing
    resolves the step. Providers see the same context and are consulted until one
    answers terminally; a provider that raises is logged at ERROR and skipped, so
    a defective provider degrades the step to reasoning instead of failing the
    turn.
    """
    _metrics["steps"] += 1
    if not _providers:
        return OperationalResolution()

    for provider in list(_providers):
        _metrics["attempts"] += 1
        name = _provider_name(provider)
        try:
            resolution = provider(context)
        except Exception:
            _metrics["errors"] += 1
            logger.error(
                "Operational resolution provider %s raised; degrading this step to reasoning",
                name,
                exc_info=True,
            )
            continue
        if resolution is None:
            continue
        if not isinstance(resolution, OperationalResolution):
            _metrics["errors"] += 1
            logger.error(
                "Operational resolution provider %s returned %r, not OperationalResolution; "
                "degrading this step to reasoning",
                name,
                type(resolution).__name__,
            )
            continue
        if not resolution.provider:
            resolution.provider = name
        if resolution.is_terminal and not resolution.final_response:
            # A terminal outcome with nothing to say would end the turn on an
            # empty reply. Treat it as an unsound answer, not as a resolution.
            _metrics["errors"] += 1
            logger.error(
                "Operational resolution provider %s returned terminal outcome %s without "
                "final_response; degrading this step to reasoning",
                name,
                resolution.outcome.value,
            )
            continue
        if resolution.is_terminal:
            _metrics["hits"] += 1
            logger.info(
                "Operational resolution: %s by %s (%s)",
                resolution.outcome.value,
                name,
                resolution.reason or "no reason given",
            )
            return resolution
        _metrics["self_reported"] += 1

    _metrics["misses"] += 1
    return OperationalResolution()
