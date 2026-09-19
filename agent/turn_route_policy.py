from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
import logging
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)


class ConstraintViolation(RuntimeError):
    """Base exception for turn-scoped constraint violations."""
    pass


class RouteConstraintViolation(ConstraintViolation):
    """Raised when an operation attempts a route prohibited by the current TurnRoutePolicy."""
    def __init__(self, route: str, reason: str):
        super().__init__(f"Route '{route}' blocked: {reason}")
        self.route = route
        self.reason = reason


def _route_matches(route: str, pattern: str) -> bool:
    return route == pattern or route.startswith(pattern + ".")


def require_allowed_route(route: str, constraints: Mapping[str, Any]) -> None:
    """Validate route against bounded route constraints."""
    forbidden = constraints.get("forbidden_routes", [])
    allowed = constraints.get("allowed_routes")

    for patterns in (forbidden, allowed):
        if patterns is not None and (
            not isinstance(patterns, list)
            or len(patterns) > 64
            or any(not isinstance(p, str) or not p or len(p) > 256 for p in patterns)
        ):
            raise ConstraintViolation("Invalid bounded route constraints")

    if any(_route_matches(route, p) for p in (forbidden or [])):
        raise ConstraintViolation(f"Route forbidden by task constraints: {route}")

    if allowed is not None and not any(_route_matches(route, p) for p in allowed):
        raise ConstraintViolation(f"Route forbidden by task constraints: {route}")


@dataclass(frozen=True)
class TurnRoutePolicy:
    """Turn-scoped execution route constraint policy.
    
    A single policy applied uniformly across:
    - primary LLM provider
    - auxiliary LLM provider
    - browser dispatch
    - terminal / system dispatch
    - tool / MCP dispatch
    """
    allowed_routes: tuple[str, ...] = ()
    forbidden_routes: tuple[str, ...] = ()
    mutation_allowed_routes: tuple[str, ...] = ()
    mutation_forbidden_routes: tuple[str, ...] = ()

    def is_route_allowed(self, route: str) -> bool:
        if self.forbidden_routes and any(_route_matches(route, p) for p in self.forbidden_routes):
            return False
        if self.allowed_routes and not any(_route_matches(route, p) for p in self.allowed_routes):
            return False
        return True

    def is_mutation_allowed(self, route: str) -> bool:
        if not self.is_route_allowed(route):
            return False
        if self.mutation_forbidden_routes and any(_route_matches(route, p) for p in self.mutation_forbidden_routes):
            return False
        if self.mutation_allowed_routes and not any(_route_matches(route, p) for p in self.mutation_allowed_routes):
            return False
        return True

    def require_route(self, route: str, is_mutation: bool = False) -> None:
        if not self.is_route_allowed(route):
            raise RouteConstraintViolation(route, f"route '{route}' is not in allowed routes: {self.allowed_routes}")
        if is_mutation and not self.is_mutation_allowed(route):
            raise RouteConstraintViolation(route, f"mutation on route '{route}' is not allowed")


_current_turn_route_policy: ContextVar[Optional[TurnRoutePolicy]] = ContextVar(
    "current_turn_route_policy",
    default=None,
)


def get_current_turn_route_policy() -> Optional[TurnRoutePolicy]:
    return _current_turn_route_policy.get()


def set_current_turn_route_policy(policy: Optional[TurnRoutePolicy]):
    return _current_turn_route_policy.set(policy)
