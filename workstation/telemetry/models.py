from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class TelemetryEventType(str, Enum):
    TURN_STARTED = "TURN_STARTED"
    TURN_FINISHED = "TURN_FINISHED"
    PROVIDER_CALLED = "PROVIDER_CALLED"
    ROUTING_DECIDED = "ROUTING_DECIDED"
    LLM_WOKEN = "LLM_WOKEN"
    CAPABILITY_SELECTED = "CAPABILITY_SELECTED"
    CAPABILITY_EXECUTION_STARTED = "CAPABILITY_EXECUTION_STARTED"
    CAPABILITY_EXECUTION_FINISHED = "CAPABILITY_EXECUTION_FINISHED"
    MUTATION_DISPATCHED = "MUTATION_DISPATCHED"
    MUTATION_ACKNOWLEDGED = "MUTATION_ACKNOWLEDGED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    OUTCOME_ACCEPTED = "OUTCOME_ACCEPTED"
    EXPERIENCE_ACCEPTED = "EXPERIENCE_ACCEPTED"
    EXPERIENCE_REJECTED = "EXPERIENCE_REJECTED"
    CAPABILITY_CANDIDATE_CREATED = "CAPABILITY_CANDIDATE_CREATED"
    VERIFIER_VALIDATION_COMPLETED = "VERIFIER_VALIDATION_COMPLETED"
    CONTROLLED_REPLAY_COMPLETED = "CONTROLLED_REPLAY_COMPLETED"
    CAPABILITY_PROMOTED = "CAPABILITY_PROMOTED"
    CAPABILITY_QUARANTINED = "CAPABILITY_QUARANTINED"
    GOAL_SATISFIED = "GOAL_SATISFIED"


@dataclass(frozen=True, slots=True)
class TelemetryEventV1:
    event_type: TelemetryEventType
    occurred_at: str
    recorded_at: str
    source_owner: str
    schema_version: int = 1
    event_id: str = field(default_factory=lambda: uuid4().hex)
    session_id: str | None = None
    task_id: str | None = None
    run_id: str | None = None
    turn_id: str | None = None
    operation_id: str | None = None
    capability_id: str | None = None
    capability_version: str | None = None
    route: str | None = None
    phase: str | None = None
    status: str | None = None
    reason_code: str | None = None
    duration_ms: float | None = None
    provider_calls: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    tool_calls: int | None = None
    evidence_refs: tuple[str, ...] = ()
    build_sha: str | None = None
    workstation_version: str | None = None
    environment: str | None = None
    dedupe_key: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["event_type"] = self.event_type.value
        value["evidence_refs"] = list(self.evidence_refs)
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TelemetryEventV1":
        data = dict(value)
        data["event_type"] = TelemetryEventType(data["event_type"])
        data["evidence_refs"] = tuple(data.get("evidence_refs") or ())
        return cls(**data)
