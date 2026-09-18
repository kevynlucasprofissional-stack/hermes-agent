"""Formal capability contract definition for certified executability verification."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from workstation.control_plane.ir import Effect, Predicate
from workstation.control_plane.lattice import AuthorityScope


@dataclass
class CapabilityFormalContract:
    """Formal, verifiable contract declared by or derived for an OperationalCapability."""

    operation_family: str = ""
    target_family: str = ""
    typed_preconditions: list[Predicate] = field(default_factory=list)
    typed_postconditions: list[Predicate] = field(default_factory=list)
    effect_footprint: list[Effect] = field(default_factory=list)
    authority_required: AuthorityScope = field(default_factory=AuthorityScope)
    preserves: list[Predicate] = field(default_factory=list)
    verifier: dict[str, Any] = field(default_factory=dict)
    event_contract: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_family": self.operation_family,
            "target_family": self.target_family,
            "typed_preconditions": [p.to_dict() for p in self.typed_preconditions],
            "typed_postconditions": [p.to_dict() for p in self.typed_postconditions],
            "effect_footprint": [e.to_dict() for e in self.effect_footprint],
            "authority_required": self.authority_required.to_dict(),
            "preserves": [p.to_dict() for p in self.preserves],
            "verifier": dict(self.verifier),
            "event_contract": dict(self.event_contract) if self.event_contract else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityFormalContract:
        pre_raw = data.get("typed_preconditions", [])
        post_raw = data.get("typed_postconditions", [])
        eff_raw = data.get("effect_footprint", [])
        preserves_raw = data.get("preserves", [])

        return cls(
            operation_family=str(data.get("operation_family", "")),
            target_family=str(data.get("target_family", "")),
            typed_preconditions=[Predicate.from_dict(p) if isinstance(p, dict) else p for p in pre_raw],
            typed_postconditions=[Predicate.from_dict(p) if isinstance(p, dict) else p for p in post_raw],
            effect_footprint=[Effect.from_dict(e) if isinstance(e, dict) else e for e in eff_raw],
            authority_required=(
                AuthorityScope.from_dict(data["authority_required"])
                if isinstance(data.get("authority_required"), dict)
                else data.get("authority_required") or AuthorityScope()
            ),
            preserves=[Predicate.from_dict(p) if isinstance(p, dict) else p for p in preserves_raw],
            verifier=dict(data.get("verifier", {})),
            event_contract=dict(data["event_contract"]) if data.get("event_contract") else None,
        )
