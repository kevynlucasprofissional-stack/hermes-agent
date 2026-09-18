"""Compact exception projection over the canonical artifact/checkpoint owners."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from workstation.control_plane.lattice import AuthorityScope
from workstation.recipes import sanitize


@dataclass
class OpenCondition:
    """Explicit, minimal open proposition for semantic adaptation by reasoning layer."""

    condition_type: str
    proposition: str
    known_facts: dict[str, Any] = field(default_factory=dict)
    available_authority: dict[str, Any] | AuthorityScope = field(default_factory=dict)
    remaining_subgraph: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if isinstance(self.available_authority, AuthorityScope):
            data["available_authority"] = self.available_authority.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpenCondition:
        return cls(**data)


@dataclass
class AttentionPacket:
    """Minimal context packet provided to LLM during reasoning handoff.
    
    Contains exact open condition, confirmed prior effects, and available authority,
    preventing massive context bloat or replay hallucinations.
    """

    intent_id: str
    intent_hash: str = ""
    capability_id: str = ""
    capability_version: str = ""
    plan_ids: list[str] = field(default_factory=list)
    completed_until: str = ""
    confirmed_effects: list[dict[str, Any]] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    expected: str = ""
    observed: str = ""
    open_condition: OpenCondition | dict[str, Any] | None = None
    remaining_subgraph: list[dict[str, Any]] = field(default_factory=list)
    available_authority: dict[str, Any] | AuthorityScope = field(default_factory=dict)
    state_refs: list[str] = field(default_factory=list)
    safe_to_resume: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if isinstance(self.open_condition, OpenCondition):
            data["open_condition"] = self.open_condition.to_dict()
        if isinstance(self.available_authority, AuthorityScope):
            data["available_authority"] = self.available_authority.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AttentionPacket:
        cdata = dict(data)
        if isinstance(cdata.get("open_condition"), dict):
            cdata["open_condition"] = OpenCondition.from_dict(cdata["open_condition"])
        return cls(**cdata)


def create_attention_packet(
    intent_id: str,
    open_condition: OpenCondition | dict[str, Any] | None = None,
    *,
    intent_hash: str = "",
    capability_id: str = "",
    capability_version: str = "",
    plan_ids: list[str] | None = None,
    completed_until: str = "",
    confirmed_effects: list[dict[str, Any]] | None = None,
    evidence_refs: list[str] | None = None,
    expected: str = "",
    observed: str = "",
    remaining_subgraph: list[dict[str, Any]] | None = None,
    available_authority: dict[str, Any] | AuthorityScope | None = None,
    state_refs: list[str] | None = None,
    safe_to_resume: bool = True,
) -> AttentionPacket:
    """Helper to assemble a validated AttentionPacket for reasoning handoff."""
    return AttentionPacket(
        intent_id=intent_id,
        intent_hash=intent_hash,
        capability_id=capability_id,
        capability_version=capability_version,
        plan_ids=plan_ids or [],
        completed_until=completed_until,
        confirmed_effects=confirmed_effects or [],
        evidence_refs=evidence_refs or [],
        expected=expected,
        observed=observed,
        open_condition=open_condition,
        remaining_subgraph=remaining_subgraph or [],
        available_authority=available_authority or {},
        state_refs=state_refs or [],
        safe_to_resume=safe_to_resume,
    )


def needs_reasoning(artifacts, owner, *, completed_until, expected, observed,
                    safe_to_resume, context=None):
    body = sanitize({'completed_until': completed_until, 'expected': expected,
                     'observed': observed, 'context': context or {},
                     'safe_to_resume': bool(safe_to_resume)})
    from workstation.recipes import digest
    ref = artifacts.store(owner, 'reasoning_' + digest(body) + '.json', body)
    return {'status': 'NEEDS_REASONING', 'completed_until': completed_until,
            'expected': 'See state_ref for the unresolved contract',
            'observed': 'Runtime requires semantic adaptation or reconciliation',
            'state_ref': ref.ref, 'safe_to_resume': bool(safe_to_resume)}

