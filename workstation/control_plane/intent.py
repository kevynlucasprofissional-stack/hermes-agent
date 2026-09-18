"""OperationIntent: declarative, immutable, versioned semantic transformation specification."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any

from workstation.contracts import AcceptanceContract, utc_now
from workstation.control_plane.ir import Effect, Predicate, TRUE


class OperationMode(str, Enum):
    ACHIEVE = "ACHIEVE"
    MAINTAIN = "MAINTAIN"
    OBSERVE = "OBSERVE"
    AVOID = "AVOID"


@dataclass
class OperationIntent:
    """Declares WHAT state transformation must occur, independent of HOW."""

    id: str
    schema_version: int = 1
    mode: OperationMode = OperationMode.ACHIEVE
    target: str = ""
    goal: Predicate = field(default_factory=TRUE)
    invariants: list[Predicate] = field(default_factory=list)
    effect_budget: list[Effect] = field(default_factory=list)
    authority_ref: str = ""
    acceptance: AcceptanceContract | dict[str, Any] = field(default_factory=AcceptanceContract)
    lineage: list[str] = field(default_factory=list)
    context_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        acceptance_dict = (
            self.acceptance.to_dict() if hasattr(self.acceptance, "to_dict")
            else asdict(self.acceptance) if hasattr(self.acceptance, "__dataclass_fields__")
            else dict(self.acceptance)
        )
        return {
            "id": self.id,
            "schema_version": self.schema_version,
            "mode": self.mode.value if isinstance(self.mode, OperationMode) else str(self.mode),
            "target": self.target,
            "goal": self.goal.to_dict() if hasattr(self.goal, "to_dict") else self.goal,
            "invariants": [inv.to_dict() for inv in self.invariants],
            "effect_budget": [eff.to_dict() for eff in self.effect_budget],
            "authority_ref": self.authority_ref,
            "acceptance": acceptance_dict,
            "lineage": list(self.lineage),
            "context_refs": list(self.context_refs),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OperationIntent:
        raw_mode = data.get("mode", OperationMode.ACHIEVE.value)
        try:
            mode = OperationMode(raw_mode)
        except ValueError:
            mode = OperationMode.ACHIEVE

        goal_raw = data.get("goal")
        goal = Predicate.from_dict(goal_raw) if isinstance(goal_raw, dict) else TRUE()

        inv_raw = data.get("invariants", [])
        invariants = [Predicate.from_dict(i) if isinstance(i, dict) else i for i in inv_raw]

        eff_raw = data.get("effect_budget", [])
        effect_budget = [Effect.from_dict(e) if isinstance(e, dict) else e for e in eff_raw]

        acceptance_raw = data.get("acceptance", {})
        if isinstance(acceptance_raw, dict):
            acceptance = AcceptanceContract(
                policy=acceptance_raw.get("policy", "evidence"),
                required_deliverables=list(acceptance_raw.get("required_deliverables", [])),
                required_verifiers=list(acceptance_raw.get("required_verifiers", [])),
            )
        else:
            acceptance = acceptance_raw

        return cls(
            id=str(data.get("id", "")),
            schema_version=int(data.get("schema_version", 1)),
            mode=mode,
            target=str(data.get("target", "")),
            goal=goal,
            invariants=invariants,
            effect_budget=effect_budget,
            authority_ref=str(data.get("authority_ref", "")),
            acceptance=acceptance,
            lineage=list(data.get("lineage", [])),
            context_refs=list(data.get("context_refs", [])),
            metadata=dict(data.get("metadata", {})),
        )


def canonical_operation_intent_json(intent: OperationIntent) -> str:
    """Deterministic, sorted JSON representation of an OperationIntent."""
    return json.dumps(intent.to_dict(), sort_keys=True, separators=(",", ":"))


def operation_intent_hash(intent: OperationIntent) -> str:
    """Stable cryptographic digest of the canonical intent."""
    return hashlib.sha256(canonical_operation_intent_json(intent).encode("utf-8")).hexdigest()


@dataclass(slots=True)
class IntentRevision:
    """Immutable record of semantic intent revision; historical intents are never modified in-place."""

    parent_intent_id: str
    old_hash: str
    new_hash: str
    reason: str
    authority_ref: str
    lineage: list[str]
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        parent_intent: OperationIntent,
        new_intent: OperationIntent,
        reason: str,
        authority_ref: str,
    ) -> IntentRevision:
        old_h = operation_intent_hash(parent_intent)
        new_h = operation_intent_hash(new_intent)
        lineage = list(parent_intent.lineage) + [parent_intent.id]
        return cls(
            parent_intent_id=parent_intent.id,
            old_hash=old_h,
            new_hash=new_h,
            reason=reason,
            authority_ref=authority_ref,
            lineage=lineage,
        )
