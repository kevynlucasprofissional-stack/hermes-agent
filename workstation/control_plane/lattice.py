"""Authority Lattice and Capability Effect Scope evaluation.

Implements the fundamental invariant:
CanExecute(E) = IntentAllows(E) AND AuthorityAllows(E) AND PolicyAllows(E) (NEVER OR).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Sequence

from workstation.control_plane.ir import (
    CALL, CREATE, DELETE, MOVE, SEND, SET, Effect, effect_contained
)
from workstation.control_plane.intent import OperationIntent


class AuthorityLevel(IntEnum):
    READ = 0
    LOCAL_MUTATION = 1
    EXTERNAL_REVERSIBLE = 2
    EXTERNAL_IRREVERSIBLE = 3


@dataclass
class AuthorityScope:
    """Represents a bounded authorization envelope."""

    level: AuthorityLevel = AuthorityLevel.READ
    allowed_actions: set[str] = field(default_factory=set)
    allowed_resources: set[str] = field(default_factory=set)
    channels: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "allowed_actions": sorted(self.allowed_actions),
            "allowed_resources": sorted(self.allowed_resources),
            "channels": sorted(self.channels),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuthorityScope:
        return cls(
            level=AuthorityLevel(data.get("level", 0)),
            allowed_actions=set(data.get("allowed_actions", [])),
            allowed_resources=set(data.get("allowed_resources", [])),
            channels=set(data.get("channels", [])),
        )

    def narrow(self, requested: AuthorityScope) -> AuthorityScope:
        """Narrow trusted authority with requested scope.

        Invariant: requested authority can ONLY reduce permissions, never expand them.
        effective.level = min(trusted.level, requested.level)
        effective.allowed_actions = trusted & requested
        effective.allowed_resources = trusted & requested
        """
        effective_level = AuthorityLevel(min(int(self.level), int(requested.level)))

        if "*" in self.allowed_actions:
            effective_actions = set(requested.allowed_actions)
        elif "*" in requested.allowed_actions:
            effective_actions = set(self.allowed_actions)
        else:
            effective_actions = {
                a for a in requested.allowed_actions
                if _action_subsumed(a, self.allowed_actions)
            }

        if "*" in self.allowed_resources:
            effective_resources = set(requested.allowed_resources)
        elif "*" in requested.allowed_resources:
            effective_resources = set(self.allowed_resources)
        else:
            effective_resources = {
                r for r in requested.allowed_resources
                if _resource_subsumed(r, self.allowed_resources)
            }

        if not self.channels:
            effective_channels = set()
        elif "*" in self.channels:
            effective_channels = set(requested.channels)
        elif "*" in requested.channels:
            effective_channels = set(self.channels)
        else:
            effective_channels = set(self.channels) & set(requested.channels)

        return AuthorityScope(
            level=effective_level,
            allowed_actions=effective_actions,
            allowed_resources=effective_resources,
            channels=effective_channels,
        )


def authority_narrow(trusted: AuthorityScope, requested: AuthorityScope) -> AuthorityScope:
    """Narrow trusted authority with requested scope."""
    return trusted.narrow(requested)


def _resource_subsumed(resource: str, allowed_set: set[str]) -> bool:
    if "*" in allowed_set:
        return True
    for a in allowed_set:
        if resource == a or resource.startswith(a + "/") or resource.startswith(a + "."):
            return True
    return False


def _action_subsumed(action: str, allowed_set: set[str]) -> bool:
    if "*" in allowed_set:
        return True
    for a in allowed_set:
        if action == a or action.startswith(a + "."):
            return True
    return False


def authority_covers(granted: AuthorityScope, required: AuthorityScope) -> bool:
    """Return True if granted authority strictly covers required authority."""
    if granted.level < required.level:
        return False
    for req_action in required.allowed_actions:
        if not _action_subsumed(req_action, granted.allowed_actions):
            return False
    for req_res in required.allowed_resources:
        if not _resource_subsumed(req_res, granted.allowed_resources):
            return False
    if required.channels:
        if "*" not in granted.channels and not required.channels.issubset(granted.channels):
            return False
    return True


def authority_join(a: AuthorityScope, b: AuthorityScope) -> AuthorityScope:
    """Join two authority scopes, taking the upper bound (higher risk) and union of scopes."""
    return AuthorityScope(
        level=max(a.level, b.level),
        allowed_actions=set(a.allowed_actions) | set(b.allowed_actions),
        allowed_resources=set(a.allowed_resources) | set(b.allowed_resources),
        channels=set(a.channels) | set(b.channels),
    )


def join_all(scopes: Sequence[AuthorityScope]) -> AuthorityScope:
    if not scopes:
        return AuthorityScope(level=AuthorityLevel.READ)
    res = scopes[0]
    for s in scopes[1:]:
        res = authority_join(res, s)
    return res


def extract_effect_authority_requirements(effect: Effect) -> AuthorityScope:
    """Determine minimum AuthorityScope required by a single Effect."""
    if isinstance(effect, SET):
        return AuthorityScope(
            level=AuthorityLevel.LOCAL_MUTATION,
            allowed_actions={"set"},
            allowed_resources={effect.path},
        )
    if isinstance(effect, CREATE):
        return AuthorityScope(
            level=AuthorityLevel.LOCAL_MUTATION,
            allowed_actions={"create"},
            allowed_resources={effect.resource},
        )
    if isinstance(effect, DELETE):
        return AuthorityScope(
            level=AuthorityLevel.EXTERNAL_IRREVERSIBLE,
            allowed_actions={"delete"},
            allowed_resources={effect.resource},
        )
    if isinstance(effect, MOVE):
        return AuthorityScope(
            level=AuthorityLevel.LOCAL_MUTATION,
            allowed_actions={"move"},
            allowed_resources={effect.source, effect.destination},
        )
    if isinstance(effect, CALL):
        # External calls default to EXTERNAL_REVERSIBLE unless destructive
        destructive = any(d in effect.operation_family.lower() for d in ("delete", "destroy", "drop", "terminate", "wipe"))
        level = AuthorityLevel.EXTERNAL_IRREVERSIBLE if destructive else AuthorityLevel.EXTERNAL_REVERSIBLE
        return AuthorityScope(
            level=level,
            allowed_actions={effect.operation_family},
            allowed_resources={effect.target},
        )
    if isinstance(effect, SEND):
        return AuthorityScope(
            level=AuthorityLevel.EXTERNAL_IRREVERSIBLE,
            allowed_actions={"send"},
            allowed_resources={effect.target},
            channels={effect.channel},
        )
    return AuthorityScope(level=AuthorityLevel.READ)


def can_execute_effect(
    effect: Effect,
    intent: OperationIntent,
    authority: AuthorityScope,
    policy_eval: Callable[[Effect], bool] | None = None,
) -> bool:
    """Evaluate if effect can execute under Intent, Authority, and Policy.
    
    CanExecute(E) = IntentAllows(E) AND AuthorityAllows(E) AND PolicyAllows(E).
    """
    # 1. Intent check: effect must be within Intent's EffectBudget
    intent_allows = effect_contained(effect, intent.effect_budget)
    if not intent_allows:
        return False

    # 2. Authority check: granted authority must cover effect requirements
    required = extract_effect_authority_requirements(effect)
    authority_allows = authority_covers(authority, required)
    if not authority_allows:
        return False

    # 3. Policy check: Scoped policy engine / gate must allow
    if policy_eval is not None:
        if not policy_eval(effect):
            return False

    return True
