"""Turn-scoped route constraints, established before any planner/provider call."""
from dataclasses import dataclass
from contextlib import contextmanager
from contextvars import ContextVar
import json
import re
from urllib.parse import urlparse

from agent.turn_route_policy import ConstraintViolation, require_allowed_route

_current: ContextVar = ContextVar("turn_route_constraints", default=None)


@contextmanager
def scoped_turn_constraints():
    token = _current.set(None)
    try:
        yield
    finally:
        _current.reset(token)


def publish_turn_constraints(context):
    _current.set(context)


def guard_auxiliary_route(provider, base_url=""):
    context = _current.get()
    if context is not None:
        if context.routes and provider in {"auto", "moa"}:
            raise ConstraintViolation("Composite auxiliary route requires an explicit permitted provider")
        context.require_provider(provider, base_url)


def user_constraints(prompt):
    if not isinstance(prompt, str):
        return {}
    constraints = {}
    candidates = [prompt] + re.findall(r"```(?:json)?\s*(.*?)```", prompt, re.S)
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            parsed = parsed.get("constraints", parsed)
            if isinstance(parsed, dict):
                constraints.update({k: parsed[k] for k in ("allowed_routes", "forbidden_routes", "mutation_allowed_routes", "mutation_forbidden_routes") if k in parsed})
    for key, raw in re.findall(r'\b((?:mutation_)?allowed_routes|(?:mutation_)?forbidden_routes)\s*=\s*(\[[^\n]*?\])', prompt):
        constraints[key] = json.loads(raw)
    for values in constraints.values():
        if not isinstance(values, list) or len(values) > 64 or any(not isinstance(v, str) or not v or len(v) > 256 for v in values):
            raise ConstraintViolation("Invalid bounded turn constraints")
    lower = prompt.lower()
    forbidden = set(constraints.get("forbidden_routes", []))
    for route, phrase in (("openai_api", r"openai[_ ]api|api[^\n]{0,20}openai"), ("browserclaw", "browserclaw")):
        if re.search(r"(?:não use|nao use|do not use|never use)[^\n]{0,60}(?:" + phrase + ")", lower):
            forbidden.add(route)
    if forbidden:
        constraints["forbidden_routes"] = sorted(forbidden)
    if re.search(r"(?:somente|apenas|only)\s+(?:o |a |the )?(?:navegador|browser|chatgpt web)", lower):
        constraints["allowed_routes"] = ["native_browser"]
    for values in constraints.values():
        if not isinstance(values, list) or len(values) > 64 or any(not isinstance(v, str) or not v or len(v) > 256 for v in values):
            raise ConstraintViolation("Invalid bounded turn constraints")
    return constraints


def provider_route(provider, base_url=""):
    name = (provider or "").strip().lower()
    host = urlparse(str(base_url or "")).hostname or ""
    if name in {"openai", "openai-api", "openai_api"} or host == "api.openai.com":
        return "openai_api"
    return name or "unknown_provider"


@dataclass(frozen=True)
class TurnConstraintContext:
    routes: dict

    @classmethod
    def from_user(cls, prompt):
        return cls(user_constraints(prompt))

    def require_provider(self, provider, base_url=""):
        if self.routes and provider == "moa":
            raise ConstraintViolation("Cannot prove routes of a composite provider under turn constraints")
        require_allowed_route(provider_route(provider, base_url), self.routes)

    def select_before_call(self, agent):
        while True:
            try:
                self.require_provider(getattr(agent, "provider", ""), getattr(agent, "base_url", ""))
                return
            except ConstraintViolation:
                if not agent._try_activate_fallback():
                    raise ConstraintViolation("No provider satisfies turn constraints")


def guard_provider_call(agent):
    context = getattr(agent, "_turn_constraints", None)
    if context is not None:
        context.require_provider(getattr(agent, "provider", ""), getattr(agent, "base_url", ""))


BROWSER_TOOL_NAMES = frozenset({
    "browser_navigate", "browser_snapshot", "browser_click", "browser_type",
    "browser_press", "browser_scroll", "browser_extract_items", "browser_console",
    "browser_get_images", "browser_back", "browser_close", "browser_tab",
})


def canonical_route_for_tool(name: str, *, runtime: str | None = None) -> str:
    from tools.effects import tool_contract
    _, metadata = tool_contract(name)
    routes = metadata.get("routes") or []
    if name in BROWSER_TOOL_NAMES and (runtime == "internal" or runtime is None):
        return "native_browser"
    if runtime and runtime != "internal":
        return runtime
    if len(routes) == 1:
        return routes[0]
    return f"tool.{name}"


def guard_tool_call(agent, function_name: str, function_args: dict) -> None:
    context = getattr(agent, "_turn_constraints", None)
    if context is None or function_name == "work_execute":
        return
    from tools.effects import tool_contract
    target = function_args.get("name", "") if function_name == "tool_call" else function_name
    _, contract = tool_contract(target)
    require_allowed_route(canonical_route_for_tool(target), context.routes)
    for route in contract.get("routes") or []:
        require_allowed_route(route, context.routes)
