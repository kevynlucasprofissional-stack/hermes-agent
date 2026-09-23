"""Compile decided, structured work into the existing durable execution path.

No model is called here. Tool execution remains in the agent's scoped dispatcher.
Natural-language ambiguity stays with the planner; this layer never guesses writes.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from enum import Enum
from datetime import datetime, timedelta, timezone
import hashlib
import json
import time
import re
from typing import Any, Callable

from agent.tool_guardrails import classify_tool_failure
from workstation.artifacts import ArtifactStore
from workstation.batch_runner import DurableBatchRunner
from workstation.durable_tasks import DurableTaskStore, WorkItem
from workstation.routing import ConstraintViolation, require_allowed_route
from workstation.reference_plane import ReadCache, blob_references, content_reference
from workstation.tool_verbosity import VerbosityLevel, normalize_verbosity
from tools.effects import ToolEffect, READ_EFFECTS, WRITE_EFFECTS, tool_effect, tool_contract, unwrap_call
from workstation.execution_graph import prepare_graph
from agent.turn_constraints import user_constraints
from workstation.recipes import RecipeStore, recipe_fingerprint, require_browser_scope


class WorkClass(str, Enum):
    INTERACTIVE_REASONING = "INTERACTIVE_REASONING"
    DETERMINISTIC_SINGLE = "DETERMINISTIC_SINGLE"
    DETERMINISTIC_BATCH = "DETERMINISTIC_BATCH"
    BROWSER_TRANSACTION = "BROWSER_TRANSACTION"
    PROMPT_QUEUE = "PROMPT_QUEUE"
    EXCEPTION_REQUIRES_REASONING = "EXCEPTION_REQUIRES_REASONING"


_dispatch_context: ContextVar[Any] = ContextVar("workstation_work_dispatch", default=None)
_constraints: ContextVar[Any] = ContextVar("workstation_work_constraints", default=None)
_execution_active: ContextVar[bool] = ContextVar("workstation_durable_active", default=False)


def batch_intent(prompt: Any) -> bool:
    """Repeatability hint for optimization; never grants or denies mutation authority."""
    if not isinstance(prompt, str):
        return False
    lower = prompt.lower().strip()
    # Grammatical/collection signals, not an enumeration of action verbs.
    first = re.findall(r"\w+", lower)
    directive = bool(first and (re.search(r"(?:ar|er|ir|e|a)$", first[0]) or
                               first[0] in {"create", "generate", "process", "update", "execute", "apply", "send"}))
    cognitive = bool(first and first[0] in {"compare", "explique", "analise", "discuta", "explore", "explain", "discuss"})
    count = re.search(r"\b(?:[2-9]|[1-9][0-9]+)\s+[\w-]+s\b", lower)
    fan_out = re.search(r"\b(?:cada\s+(?:registro|item|arquivo|usuário|usuario)|todos?\s+(?:esses?|estes?|os)|mesma\s+.+\s+ness(?:es|as)|each\s+|all\s+these)", lower)
    structured = False
    for candidate in [prompt] + re.findall(r"```(?:json)?\s*(.*?)```", prompt, re.S):
        try:
            payload = json.loads(candidate)
        except ValueError:
            continue
        entries = payload.get("items", payload.get("records", [])) if isinstance(payload, dict) else payload
        if isinstance(entries, list) and len(entries) > 1 and all(isinstance(i, dict) for i in entries):
            structured = all(set(i) == set(entries[0]) for i in entries)
            if isinstance(payload, dict) and payload.get("steps"):
                return True
    return bool(not cognitive and ((directive and (count or fan_out)) or structured))


def merge_constraints(user: dict, compiled: dict) -> dict:
    from workstation.routing import normalize_route_constraints
    user, compiled = normalize_route_constraints(user), normalize_route_constraints(compiled)
    combined = {k: compiled[k] for k in ("allowed_routes", "forbidden_routes") if k in compiled}
    combined["forbidden_routes"] = sorted(set(user.get("forbidden_routes", [])) | set(compiled.get("forbidden_routes", [])))
    if "allowed_routes" in user:
        if "allowed_routes" not in compiled:
            combined["allowed_routes"] = user["allowed_routes"]
        else:
            combined["allowed_routes"] = sorted({
                a if a == b or a.startswith(b + ".") else b
                for a in user["allowed_routes"] for b in compiled["allowed_routes"]
                if a == b or a.startswith(b + ".") or b.startswith(a + ".")})
    for prefix in ("mutation_",):
        scoped = merge_constraints({k[len(prefix):]: v for k, v in user.items() if k.startswith(prefix)},
                                   {k[len(prefix):]: v for k, v in compiled.items() if k.startswith(prefix)}) if any(
            k.startswith(prefix) for k in (*user, *compiled)) else {}
        combined.update({prefix + k: v for k, v in scoped.items()})
    return combined


def requires_compilation(agent: Any, calls: list) -> bool:
    from workstation.execution_policy import CompilationDecision, decisions_for_calls
    return CompilationDecision.REQUIRE_COMPILE in decisions_for_calls(agent, calls)


def discovery_guidance(agent=None):
    names = getattr(agent, "valid_tool_names", ()) if agent is not None else (
        "read_file", "search_files", "browser_snapshot", "browser_extract_items", "tool_describe")
    allowed = [n for n in sorted(names) if tool_effect(n) in READ_EFFECTS]
    return {"phase": "DISCOVERING", "preflight_status": "PREFLIGHT_REQUIRED",
            "allowed_discovery_actions": allowed,
            "missing_capabilities": ["operation-specific mutation authority"],
            "missing_selectors": ["resolve with browser_snapshot/browser_extract_items when unknown"],
            "missing_readback": ["independent persisted-state source"],
            "missing_verifiers": ["read step with verifies + expected persisted fields"],
            "recovery_protocol": ["preserve confirmed identities; review uncertain effects",
                "discover with read/discovery tools or work_execute action=discover",
                "compile only pending items with real mutation + independent readback",
                "verify representative canary persistence before fan-out",
                "checkpoint each item; resume unconfirmed items; never retry uncertain mutations"],
            "capability_invariant": "Successful read capability does not establish write capability."}


@contextmanager
def execution_context(dispatch: Callable, session_id: str, progress: Callable | None = None,
                      constraints: dict | None = None, provider_usage: dict | None = None,
                      completed_mutations: dict | None = None, event_bus=None, canonical_task_id=None,
                      mutation_evidence=None, capabilities=None):
    token = _dispatch_context.set((dispatch, session_id, {}, [], progress, provider_usage,
        completed_mutations or {}, event_bus, canonical_task_id, mutation_evidence or {},
        capabilities if capabilities is not None else {}))
    constraint_token = _constraints.set(constraints or {})
    try:
        yield
    finally:
        _constraints.reset(constraint_token)
        _dispatch_context.reset(token)


def active_constraints() -> dict:
    return _constraints.get() or {}


def durable_execution_active() -> bool:
    return _execution_active.get()


def capture_raw_result(call_id: str, raw: Any) -> None:
    context = _dispatch_context.get()
    if context is not None and durable_execution_active():
        context[2][call_id] = raw


def take_raw_result(call_id: str, fallback: Any) -> Any:
    context = _dispatch_context.get()
    return context[2].pop(call_id, fallback) if context is not None else fallback


def operational_references() -> list:
    context = _dispatch_context.get()
    return list(context[3]) if context else []


def classify(request: dict) -> WorkClass:
    if request.get("exception"):
        return WorkClass.EXCEPTION_REQUIRES_REASONING
    if not request.get("steps") or not isinstance(request.get("items"), list):
        return WorkClass.INTERACTIVE_REASONING
    if request.get("kind") == "prompt_queue":
        return WorkClass.PROMPT_QUEUE
    if request.get("kind") == "browser_transaction" and any(
        str(s.get("tool", "")).startswith("browser_") for s in request["steps"]
    ):
        return WorkClass.BROWSER_TRANSACTION
    if all(str(s.get("tool", "")).startswith("browser_") for s in request["steps"]):
        return WorkClass.BROWSER_TRANSACTION
    return WorkClass.DETERMINISTIC_BATCH if len(request["items"]) > 1 else WorkClass.DETERMINISTIC_SINGLE


def _bind(value: Any, item: dict, bindings: dict | None = None) -> Any:
    bindings = {"item": item, **(bindings or {})}
    if isinstance(value, str) and value.startswith("$") and value[1:].split(".")[0] in bindings:
        parts = value[1:].split(".")
        result: Any = bindings[parts[0]]
        try:
            for field in parts[1:]:
                result = result[field]
        except (KeyError, IndexError, TypeError):
            raise ValueError(f"invalid binding: {value}") from None
        return result
    if isinstance(value, dict):
        return {k: _bind(v, item, bindings) for k, v in value.items()}
    if isinstance(value, list):
        return [_bind(v, item, bindings) for v in value]
    return value


def _validate(output: Any, expected: dict) -> bool:
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except ValueError:
            return False
    for path, value in expected.items():
        current = output
        try:
            for key in path.split("."):
                current = current[key]
        except (KeyError, TypeError):
            return False
        if current != value:
            return False
    return True


def _decode_output(raw):
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except ValueError:
            pass
    return raw


class TaskCompiler:
    def __init__(self, store: DurableTaskStore | None = None, artifacts: ArtifactStore | None = None, recipes=None,
                 handoffs=None, ora_metrics: Any | None = None):
        self.store = store or DurableTaskStore()
        self.artifacts = artifacts or ArtifactStore()
        self.recipes = recipes or RecipeStore(self.artifacts)
        if handoffs is None:
            from hermes_constants import get_hermes_home
            from workstation.runtime import HumanHandoffManager
            handoffs = HumanHandoffManager(get_hermes_home() / "workstation" / "human_handoffs.json")
        self.handoffs = handoffs
        if ora_metrics is not None:
            self.ora_metrics = ora_metrics
        else:
            from workstation.control_plane.metrics import ORAMetrics
            self.ora_metrics = ORAMetrics()
        from workstation.control_plane.metrics import ORAMetricsCollector
        self.metrics_collector = ORAMetricsCollector(self.ora_metrics)

    def discover(self, request, *, task_id, session_id, dispatch):
        """Preparation only: no frozen plan and no caller-provided effect override."""
        probes = request.get("preflight", [])
        if not session_id or not isinstance(probes, list) or len(probes) > 8:
            raise ValueError("Discovery requires owner and at most 8 read-only probes")
        constraints = merge_constraints(active_constraints(), request.get("constraints", {}))
        for probe in probes:
            name = probe["tool"]
            effect, contract = tool_contract(name)
            if effect not in READ_EFFECTS or name == "tool_call":
                return {**discovery_guidance(), "code": "GUARD_BOOTSTRAP_BLOCKED",
                        "blocked_action": name, "detected_effect": effect.value,
                        "reason": "Discovery cannot dispatch arbitrary execution or mutations; use structured read tools."}
            # Mutation route restrictions do not prohibit independent reads.
            require_allowed_route("native_browser" if name.startswith("browser_") else "tool." + name,
                                  constraints)
            for route in contract.get("routes") or []:
                require_allowed_route(route, constraints)
        results = []
        for index, probe in enumerate(probes):
            raw = dispatch(probe["tool"], probe.get("args", {}), task_id, f"discover_{index}")
            from tools.effects import observe_capability
            context = _dispatch_context.get()
            if context:
                observe_capability(context[10], probe["tool"], probe.get("args", {}), raw)
            ref = content_reference(self.artifacts, session_id, blob_references(self.artifacts, session_id, raw))
            failed = classify_tool_failure(probe["tool"], raw if isinstance(raw, str) else json.dumps(raw))[0]
            results.append({"tool": probe["tool"], "result_ref": ref["artifact_ref"],
                            "verified": not failed and (not probe.get("expect") or _validate(raw, probe["expect"]))})
        return {**discovery_guidance(), "code": "PREFLIGHT_COMPLETE" if probes and all(r["verified"] for r in results)
                else "PREFLIGHT_REQUIRED", "results": results, "plan_frozen": False}

    def execute(self, request: dict, *, task_id: str, session_id: str, dispatch: Callable,
                progress: Callable | None = None, provider_usage: dict | None = None,
                environment: str | None = None, event_bus=None, canonical_task_id: str | None = None) -> dict:
        if request.get("action") == "route" or request.get("operation_intent"):
            return self._execute_route(request, task_id=task_id, session_id=session_id,
                dispatch=dispatch, progress=progress, provider_usage=provider_usage,
                event_bus=event_bus, canonical_task_id=canonical_task_id)
        if request.get("capability_id"):
            return self._execute_capability(request, task_id=task_id, session_id=session_id,
                dispatch=dispatch, canonical_task_id=canonical_task_id)
        recipe_key = request.get("recipe_key")
        if not recipe_key and request.get('operation_fingerprint'):
            from workstation.operational_capabilities import OperationalCapabilityRegistry
            op_reg = OperationalCapabilityRegistry(artifacts=self.artifacts)
            matched_cap = op_reg.find_matching(
                route=request.get('recipe_scope', {}).get('route', 'native_browser') if request.get('recipe_scope') else 'native_browser',
                semantic_fingerprint=request['operation_fingerprint'],
                scope=request.get('recipe_scope'),
                promoted_only=True
            )
            if matched_cap:
                return {**self._execute_capability({**request, 'capability_id': matched_cap.id,
                    'capability_version': matched_cap.version}, task_id=task_id, session_id=session_id,
                    dispatch=dispatch, canonical_task_id=canonical_task_id), 'reused_capability': True}
            match = self.recipes.find_verified(fingerprint=request['operation_fingerprint'],
                scope=request.get('recipe_scope'), mutation_target=request.get('mutation_target'),
                preflight=request.get('preflight', []))
            if match:
                recipe_key = match['recipe_id']
                request = {**request, 'recipe_key': recipe_key}
        recipe = self.recipes.get(recipe_key) if recipe_key else None
        if not recipe and not request.get('steps') and request.get('operation_fingerprint'):
            from workstation.routines import compiled_routine_request
            from workstation.memory import ProceduralMemory
            request = compiled_routine_request(request, ProceduralMemory())
        recipe_reused = bool(recipe and not request.get("steps"))
        if recipe_reused:
            if recipe["status"] != "VERIFIED":
                raise ValueError("recipe_stale: supply a corrected explicit graph for a new canary")
            if request.get("recipe_scope", recipe["scope"]) != recipe["scope"]:
                raise ValueError("recipe_scope_mismatch")
            if request.get("mutation_target", recipe.get("mutation_target")) != recipe.get("mutation_target"):
                raise ValueError("recipe_scope_mismatch: intended mutation target differs from verified recipe")
            request = {**request, "setup_steps": recipe["graph"]["setup"], "steps": recipe["graph"]["fan_out"],
                       "finalize_steps": recipe["graph"]["finalize"], "recipe_scope": recipe["scope"],
                       "preflight": recipe["preflight"], "mutation_target": recipe.get("mutation_target")}
        if recipe_key and not request.get("operation_key"):
            from workstation.recipes import digest
            request = {**request, "operation_key": recipe_key + "." + digest(request.get("items", request.get("items_ref")))[:16]}
        if request.get("items_ref"):
            if "items" in request:
                raise ValueError("Use items or items_ref, not both")
            dataset = self.artifacts.read_json(request["items_ref"])
            if isinstance(dataset, dict):
                dataset = dataset.get("items")
            if not isinstance(dataset, list) or not all(isinstance(i, dict) for i in dataset):
                raise ValueError("items_ref must resolve to structured records")
            request = {**request, "items": dataset, "source_items_ref": request["items_ref"]}
            request.pop("items_ref")
        kind = classify(request)
        if kind in {WorkClass.INTERACTIVE_REASONING, WorkClass.EXCEPTION_REQUIRES_REASONING}:
            raise ValueError("Work requires a decided operation, structured items and verifiable steps")
        # Scope work identity to the owning session and a planner-supplied operation key.
        key = str(request.get("operation_key") or "")
        if not key or not session_id:
            raise ValueError("operation_key and owning session are required")
        identity = hashlib.sha256(f"{session_id}:{task_id}:{key}".encode()).hexdigest()
        durable_id = f"work_{identity}"
        constraints = merge_constraints(active_constraints(), request.get("constraints", {}))
        request = {**request, "constraints": constraints}
        steps = request["steps"]
        graph = prepare_graph(request) if any(k in request for k in ("setup_steps", "finalize_steps")) or any(
            "depends_on" in s or "id" in s or "verifies" in s for s in steps) else None
        canonical_graph = graph or prepare_graph(request)
        from workstation.browser_transaction import transaction_contract
        transaction = transaction_contract(request, canonical_graph)
        if transaction:
            graph = canonical_graph
        intended_target = request.get("mutation_target")
        if intended_target:
            if not isinstance(intended_target, dict) or intended_target.get("scope") not in {"local", "external"}:
                raise ValueError("Invalid intended mutation target")
            if intended_target["scope"] == "external":
                matching = []
                for node in canonical_graph["fan_out"]:
                    effect, owner = tool_contract(node["tool"])
                    target = owner.get("mutation_target") or {}
                    if effect in WRITE_EFFECTS and (target.get("scope") == "external" or
                                                    node["tool"] in {"browser_click", "browser_type", "browser_press"}):
                        if intended_target.get("provider") and target.get("provider") and target["provider"] != intended_target["provider"]:
                            continue
                        matching.append(node["id"])
                if not matching:
                    raise ValueError("External mutation target requires a real mutation step; preparation cannot establish persistence verification")
                from workstation.browser_transaction import evidence_strength
                for mutation in matching:
                    for verifier in sum(canonical_graph.values(), []):
                        if mutation in verifier.get('verifies', []) and verifier['tool'] == 'browser_snapshot':
                            if int(evidence_strength(verifier)) < 2:
                                raise ValueError('External commit requires persisted readback; native browser snapshot is same-session semantic evidence')
        scope = request.get("recipe_scope", {"route": "native_browser" if kind == WorkClass.BROWSER_TRANSACTION else "tool." + steps[0]["tool"]})
        if not isinstance(scope, dict) or not isinstance(scope.get("route"), str):
            raise ValueError("Invalid recipe scope")
        require_allowed_route(scope["route"], constraints)
        preflight = request.get("preflight", [])
        if not isinstance(preflight, list) or len(preflight) > 8:
            raise ValueError("Invalid bounded recipe preflight")
        for probe in preflight:
            if tool_effect(probe["tool"]) not in READ_EFFECTS or not probe.get("expect"):
                raise ValueError("Recipe preflight requires read-only probes with expect")
        if recipe_reused and scope["route"] == "native_browser":
            if not scope.get("host") or not scope.get("path_family") or not preflight:
                raise ValueError("Browser recipe requires scoped host/path family and read-only preflight reporting url")
            for record in request["items"]:
                require_browser_scope(record, scope)
        recipe_hash = recipe_fingerprint(canonical_graph, scope, preflight, intended_target)
        if not recipe_key:
            recipe = self.recipes.find_verified(fingerprint=recipe_hash, scope=scope,
                mutation_target=intended_target, preflight=preflight)
            if recipe:
                recipe_key, recipe_reused = recipe['recipe_id'], True
            else:
                recipe_key = 'auto.' + recipe_hash
        if recipe_reused and recipe["fingerprint"] != recipe_hash:
            self.recipes.invalidate(recipe_key)
            raise ValueError("recipe_fingerprint_mismatch: recipe marked STALE; provide corrected graph")
        mutable_batch = len(request["items"]) > 1 and any(tool_effect(s["tool"]) in WRITE_EFFECTS for s in steps)
        if mutable_batch and not intended_target and any(s["tool"] in {"terminal", "browser_console", "browser_exec", "execute_code"} for s in steps):
            raise ValueError("preflight_required: opaque mutation batch requires intended mutation_target before compilation")
        if mutable_batch:
            mutations = {s["id"] for s in canonical_graph["fan_out"] if tool_effect(s["tool"]) in WRITE_EFFECTS}
            proved = {target for s in canonical_graph["fan_out"] for target in s.get("verifies", [])}
            if mutations - proved:
                raise ValueError("Mutation batch requires an independent persisted-state read verifier for every mutation")
            for verifier in canonical_graph["fan_out"]:
                if verifier.get("verifies") and intended_target and intended_target.get("field"):
                    field = intended_target["field"]
                    readback = verifier.get("readback", {})
                    mapped = readback.get("field") == field and readback.get("path") in verifier["expect"]
                    if not mapped and not any(path.split(".")[-1] == field for path in verifier["expect"]):
                        raise ValueError("Mutation verifier must compare the intended persisted resource field")
                for target_id in verifier.get("verifies", []):
                    mutation = next(s for s in canonical_graph["fan_out"] if s["id"] == target_id)
                    target = tool_contract(mutation["tool"])[1].get("mutation_target") or {}
                    if target.get("scope") == "external" or intended_target and intended_target.get("scope") == "external":
                        if verifier["tool"] in {"read_file", "search_files", "read_terminal"}:
                            raise ValueError("External mutation verifier must read persisted external state, not preparation files")
        if mutable_batch and graph is None:
            graph = canonical_graph
        # Cached procedures still verify each item. Only a matching recipe plus
        # successful persisted preflight can skip the admission canary.
        canary_required = mutable_batch and not (recipe_reused and preflight)
        all_steps = (sum(graph.values(), []) if graph else steps) + preflight
        if kind == WorkClass.PROMPT_QUEUE and not any(s.get("wait") for s in steps):
            raise ValueError("Prompt queue requires a bounded completion wait before advancing")
        if not steps or len(steps) > 64 or len(request["items"]) > 10000:
            raise ValueError("Work exceeds bounded plan limits")
        for step in all_steps:
            tool = step["tool"]
            if tool == "work_execute":
                raise ValueError("Nested durable execution is prohibited")
            effect, contract = tool_contract(tool)
            if effect in {ToolEffect.COGNITIVE, ToolEffect.INTERACTIVE} or tool == "tool_call":
                raise ValueError("Cognitive/indirect steps must be resolved before compiling work")
            from workstation.routing import canonical_route_for_tool, NATIVE_BROWSER_TOOLS
            route = canonical_route_for_tool(tool, runtime='internal' if tool in NATIVE_BROWSER_TOOLS else None)
            if (constraints.get("forbidden_routes") and effect not in READ_EFFECTS and not contract.get("routes")
                    and not tool.startswith("browser_")
                    and any(not r.startswith(("tool.", "native_browser")) for r in constraints["forbidden_routes"])):
                raise ConstraintViolation(f"Cannot prove provider route for constrained tool: {tool}")
            require_allowed_route(route, constraints)
            for declared_route in contract.get("routes") or []:
                require_allowed_route(declared_route, constraints)
            if effect in WRITE_EFFECTS:
                mutation_constraints = {k[len("mutation_"):]: v for k, v in constraints.items() if k.startswith("mutation_")}
                require_allowed_route(route, mutation_constraints)
                for declared_route in contract.get("routes") or []:
                    require_allowed_route(declared_route, mutation_constraints)
            if effect not in READ_EFFECTS and not step.get("expect") and not (transaction and step.get('id') in transaction['interactions']):
                raise ValueError(f"Mutation {tool} requires an explicit result verifier")
            if step.get("wait") and (effect not in READ_EFFECTS or not step.get("expect")):
                raise ValueError("Completion waits require a read-only probe and explicit verifier")
            if step.get("wait", {}).get("event_type"):
                if event_bus is None:
                    raise ValueError("Event waits require the owning runtime event bus")
                if not step["wait"].get("correlation_id"):
                    raise ValueError("Event waits require an explicit correlation_id")
        fingerprint = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        plan = self.store.get_plan(durable_id)
        if plan and (plan.session_id != session_id or plan.metadata.get("fingerprint") != fingerprint):
            raise ValueError("Operation identity conflicts with the persisted plan")
        if plan:
            if plan.metadata.get("circuit", {}).get("status") == "SYSTEMIC_FAILURE_SUSPECTED":
                raise ValueError("systemic_failure_requires_diagnosis: correct the procedure and admit a new canary")
            pinned = plan.metadata.get("recipe", {}).get("fingerprint")
            if pinned and pinned != recipe_hash:
                if recipe_key:
                    self.recipes.invalidate(recipe_key)
                raise ValueError("recipe_fingerprint_mismatch: persisted procedure changed; review before resume")
            if plan.metadata.get("recipe", {}).get("status") == "VERIFIED" and recipe and recipe["status"] != "VERIFIED":
                raise ValueError("recipe_stale: persisted recipe requires review before resume")
            canary_required = plan.metadata.get("canary_required", canary_required)
        objective = self.artifacts.store(durable_id, "objective.json", request)
        metadata = {"classification": kind.value, "constraints": constraints,
                    "objective_ref": objective.ref, "fingerprint": fingerprint,
                    "browser_task_id": task_id, "verbosity": normalize_verbosity(request.get("verbosity")).value}
        from hermes_cli import kanban_db
        conn = self.store.get_connection()
        candidate_id = canonical_task_id or task_id
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        canonical = kanban_db.get_task(conn, candidate_id) if "tasks" in tables else None
        if canonical_task_id and (canonical is None or canonical.session_id != session_id):
            raise ValueError("Canonical task does not belong to the owning conversation")
        metadata["canonical_task_id"] = canonical.id if canonical and canonical.session_id == session_id else None
        metadata["canonical_identity_status"] = "resolved" if metadata["canonical_task_id"] else "unresolved"
        metadata['canonical_run_id'] = str(canonical.current_run_id) if metadata['canonical_task_id'] and canonical.current_run_id is not None else None
        metadata['run_id'] = metadata['canonical_run_id']
        metadata["session_id"] = session_id
        from workstation.journal import execution_provenance
        metadata.update(execution_provenance())
        if environment is not None:
            if environment not in {"production", "dogfood", "benchmark", "test", "e2e", "replay"}:
                raise ValueError("invalid execution environment")
            metadata["environment"] = environment
        metadata["canary_required"] = canary_required
        metadata["recipe"] = {"recipe_id": recipe_key, "status": "VERIFIED" if recipe_reused else "UNVERIFIED",
                              "fingerprint": recipe_hash}
        if graph:
            metadata["graph"] = graph
        if graph and any("_work_phase" in i for i in request["items"]):
            raise ValueError("Reserved graph phase key in item")
        work_payloads = request["items"] if not graph else (
            ([{"_work_phase": "setup"}] if graph["setup"] else []) +
            [{**i, "_work_phase": "fan_out"} for i in request["items"]] +
            ([{"_work_phase": "finalize"}] if graph["finalize"] else []))
        metrics = {"tool_calls": 0, "LLM_interventions": 0, "artifact_bytes": 0,
                   "inline_context_bytes": 0, "work_items_completed": 0, "replans": 0,
                   "cache_hits": 0, "cache_misses": 0, "no_progress_calls": 0}
        metrics.update({"tool_input_bytes": 0, "tool_output_bytes": 0, "latency_ms": 0,
                        "compactions": 0, "state_transitions": 0, "duplicate_calls_blocked": 0,
                        "usage_status": "unknown"})
        metrics.update(dict.fromkeys(("canary_attempts", "canary_successes", "canary_failures",
                                     "recipe_cache_hits", "recipe_cache_misses", "recipe_invalidations",
                                     "failed_fanout_items", "handoff_bytes", "compaction_bytes",
                                     "duplicate_compaction_bytes_suppressed"), 0))
        metrics_uri = f"artifact://tasks/{durable_id}/metrics.json"
        if self.artifacts.resolve_ref(metrics_uri):
            metrics.update(self.artifacts.read_json(metrics_uri))
        for usage_field in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens",
                            "tokens_per_successful_state_transition", "token_usage_scope"):
            metrics.pop(usage_field, None)
        metrics["usage_status"] = "unknown"
        prior_transitions = metrics["state_transitions"]
        if not plan and recipe_key:
            metrics["recipe_cache_hits" if recipe_reused else "recipe_cache_misses"] += 1
        if plan:
            metrics["duplicate_calls_blocked"] += sum(
                i.status.value == "completed" for i in self.store.get_work_items(plan.id)) * len(steps)

        def persist_metrics():
            self.artifacts.store(durable_id, "metrics.json", metrics)
        reads = ReadCache(self.artifacts, durable_id)
        runtime_items = {}
        recipe_invalidated = False

        def items_for_plan(plan_id):
            if plan_id not in runtime_items:
                runtime_items[plan_id] = self.store.get_work_items(plan_id)
            return runtime_items[plan_id]

        def worker(payload: dict, item: WorkItem) -> dict:
            nonlocal recipe_invalidated
            results = []
            phase = payload.get("_work_phase", "fan_out") if graph else "fan_out"
            phase_steps = graph[phase] if graph else steps
            bindings = {"setup": {}, "steps": {}, "finalize": {}}
            if graph:
                for shared in items_for_plan(item.plan_id):
                    if shared.input_payload.get("_work_phase") == "setup":
                        shared = self.store.get_item(shared.id)
                        for idx, node in enumerate(graph["setup"]):
                            ref = shared.checkpoints.get(f"step_{idx}_meta", {}).get("result_ref")
                            if ref:
                                bindings["setup"][node["id"]] = _decode_output(self.artifacts.read(ref))
            fan_items = [i for i in items_for_plan(item.plan_id)
                         if i.input_payload.get("_work_phase", "fan_out") == "fan_out"]
            first_item = bool(fan_items and item.id == fan_items[0].id)
            if first_item and phase == "fan_out":
                for n, probe in enumerate(preflight):
                    checkpoint = f"preflight_{n}"
                    if self.store.get_item(item.id).checkpoints.get(checkpoint + "_meta", {}).get("result_ref"):
                        continue
                    probe_args = _bind(probe.get("args", {}), payload, bindings)
                    require_browser_scope(probe_args, scope)
                    output = dispatch(probe["tool"], probe_args, task_id, f"{item.id}_preflight_{n}")
                    metrics["tool_calls"] += 1
                    evidence = content_reference(self.artifacts, durable_id, blob_references(self.artifacts, durable_id, output))
                    scope_valid = True
                    if probe.get("readiness"):
                        from workstation.browser_readiness import BrowserReadinessContract
                        readiness = BrowserReadinessContract(**probe["readiness"]).evaluate(_decode_output(output))
                        if not readiness["ready"]:
                            if readiness["code"] in {"auth_required", "captcha_required", "unsupported_surface"}:
                                existing = self.store.get_plan(item.plan_id).metadata.get("handoff")
                                handoff = self.handoffs.get(existing["handoff_id"]) if existing else None
                                if handoff is None or handoff.status != "waiting-for-human":
                                    handoff = self.handoffs.request(task_id=task_id, session_id=session_id,
                                        reason=readiness["code"], scope={"plan_id": item.plan_id, "work_item_id": item.id})
                                self.store.update_plan_metadata(item.plan_id, {"handoff": {
                                    "handoff_id": handoff.handoff_id, "status": handoff.status,
                                    "reason": handoff.reason, "diagnostic": readiness["diagnostic"]}})
                                return {"valid": False, "waiting_for_human": True,
                                    "handoff_id": handoff.handoff_id, "code": readiness["code"], "results": [evidence]}
                            return {"valid": False, "code": readiness["code"], "diagnostic": readiness["diagnostic"], "results": [evidence]}
                    if scope["route"] == "native_browser" and scope.get("host"):
                        decoded_probe = _decode_output(output)
                        try:
                            if not isinstance(decoded_probe, dict) or not decoded_probe.get("url"):
                                raise ValueError("Browser preflight must report actual url")
                            require_browser_scope({"url": decoded_probe["url"]}, scope)
                        except ValueError:
                            scope_valid = False
                    if not scope_valid or not _validate(output, _bind(probe["expect"], payload, bindings)):
                        if recipe_key:
                            self.recipes.invalidate(recipe_key)
                            metrics["recipe_invalidations"] += 1
                            recipe_invalidated = True
                            self.store.update_plan_metadata(item.plan_id, {"recipe": {"recipe_id": recipe_key, "status": "STALE", "fingerprint": recipe_hash}})
                        persist_metrics()
                        return {"valid": False, "code": "recipe_stale", "results": [evidence]}
                    self.store.update_item_checkpoint(item.id, checkpoint, metadata={"result_ref": evidence["artifact_ref"]})
                if canary_required and not self.store.get_item(item.id).checkpoints.get("canary_started"):
                    self.store.update_item_checkpoint(item.id, "canary_started")
                    metrics["canary_attempts"] += 1
                    persist_metrics()
            if graph:
                if phase == "finalize":
                    bindings["items_ref"] = self.artifacts.store(durable_id, "fan_out_results.json", [
                        {"item_id": i.id, "result_ref": i.normalized_output_ref} for i in self.store.get_work_items(item.plan_id)
                        if i.input_payload.get("_work_phase") == "fan_out"]).ref
            for index, step in enumerate(phase_steps):
                # Persist each step before advancing; restart never replays a committed step.
                current = self.store.get_item(item.id)
                committed = current.checkpoints.get(f"step_{index}_meta", {})
                if committed.get("result_ref"):
                    metrics["duplicate_calls_blocked"] += 1
                    results.append({"artifact_ref": committed["result_ref"], "verified": True})
                    if graph:
                        bindings["steps"][step["id"]] = _decode_output(self.artifacts.read(committed["result_ref"]))
                        bindings[phase if phase != "fan_out" else "steps"][step["id"]] = bindings["steps"][step["id"]]
                    continue
                if current.checkpoints.get(f"step_{index}_dispatch") and tool_effect(step["tool"]) not in READ_EFFECTS:
                    return {"valid": False, "code": "uncertain_mutation_requires_review", "results": results}
                args = _bind(step.get("args", {}), payload, bindings)
                if step.get('semantic_anchor') and step['tool'] in {'browser_click', 'browser_type'}:
                    from workstation.routines import semantic_browser_elements
                    from workstation.memory import ProcedureStep
                    observation = _decode_output(dispatch('browser_snapshot', {}, task_id, f'{item.id}_{index}_anchor'))
                    metrics['tool_calls'] += 1
                    anchor_ref = content_reference(self.artifacts, durable_id, observation)['artifact_ref']
                    if not isinstance(observation, dict) or (scope.get('host') and not observation.get('url')) or classify_tool_failure('browser_snapshot', json.dumps(observation))[0]:
                        return {'valid': False, 'code': 'unexpected_state', 'results': results,
                                'anchor_state_ref': anchor_ref}
                    require_browser_scope({'url': observation.get('url')} if isinstance(observation, dict) else {}, scope)
                    anchor = ProcedureStep(action=step['tool'], fallback_anchors=[step['semantic_anchor']])
                    target = anchor.resolve_anchor(semantic_browser_elements(observation)) if isinstance(observation, dict) and not observation.get('wall_detected') else None
                    if not target:
                        return {'valid': False, 'code': 'unexpected_state', 'results': results,
                                'anchor_state_ref': anchor_ref}
                    args = {**args, 'ref': target}
                require_browser_scope(args, scope)
                effect, contract = tool_contract(step["tool"])
                if effect in WRITE_EFFECTS and metadata['canonical_task_id']:
                    live_task = kanban_db.get_task(self.store.get_connection(), metadata['canonical_task_id'])
                    pinned_run = self.store.get_plan(item.plan_id).run_id
                    if not live_task or str(live_task.current_run_id) != str(pinned_run) or live_task.status in {'done', 'cancelled'}:
                        return {'valid': False, 'code': 'stale_task_run', 'results': results}
                if effect == ToolEffect.IDEMPOTENT_WRITE and not args.get(contract["idempotency_key"]):
                    return {"valid": False, "code": "idempotency_key_required", "results": results}
                from workstation.batch_detection import call_key, mutation_identity
                from tools.effects import observe_capability, operation_capability
                context = _dispatch_context.get()
                evidence = context[9].get(call_key(step["tool"], args), {}) if context else {}
                capabilities = {**(context[10] if context else {}), **self.store.get_plan(item.plan_id).metadata.get("capabilities", {})}
                if effect in WRITE_EFFECTS and (evidence.get("status") == "uncertain" or
                                               operation_capability(capabilities, step["tool"], args) == "REJECTED"):
                    return {"valid": False, "code": "uncertain_mutation_requires_review", "results": results}
                identity_record = mutation_identity(step["tool"], args,
                    task_id=metadata.get("canonical_task_id") or task_id,
                    run_id=self.store.get_plan(item.plan_id).run_id) if effect in WRITE_EFFECTS else None
                if identity_record:
                    identity_record.update({"status": "uncertain", "persisted": None, "verifier_status": "pending"})
                self.store.update_item_checkpoint(item.id, f"step_{index}_dispatch", metadata={"mutation_identity": identity_record})
                metrics["tool_calls"] += 1
                metrics["tool_input_bytes"] += len(json.dumps(args).encode())
                started = time.monotonic()
                wait = step.get("wait", {})
                subscription = event_bus.subscribe() if wait.get("event_type") else None
                try:
                    adopted_ref = context[6].get(call_key(step["tool"], args)) if context else None
                    if adopted_ref:
                        raw = self.artifacts.read(adopted_ref)
                        metrics["duplicate_calls_blocked"] += 1
                        metrics["tool_calls"] -= 1
                    else:
                        raw = dispatch(step["tool"], args, task_id, f"{item.id}_{index}")
                    deadline = started + min(300, max(0, float(wait.get("timeout_seconds", 30))))
                    max_polls = min(100, max(1, int(wait.get("max_polls", 20))))
                    polls = 1
                    while wait and not _validate(raw, _bind(step["expect"], payload, bindings)):
                        if time.monotonic() >= deadline or polls >= max_polls:
                            break
                        # Intermediate waiting observations belong to the Data Plane.
                        content_reference(self.artifacts, durable_id, blob_references(self.artifacts, durable_id, raw))
                        if subscription is not None:
                            from workstation.runtime import WaitContract
                            contract = WaitContract(wait["event_type"], task_id,
                                (datetime.now(timezone.utc) + timedelta(seconds=max(0, deadline - time.monotonic()))).isoformat(),
                                str(_bind(wait["correlation_id"], payload, bindings)), session_id)
                            try:
                                event_bus.wait(contract, subscription=subscription)
                            except TimeoutError:
                                break
                        else:
                            time.sleep(min(1, max(0, float(wait.get("interval_seconds", 0.2)))))
                        metrics["tool_calls"] += 1
                        raw = dispatch(step["tool"], args, task_id, f"{item.id}_{index}_poll_{polls}")
                        polls += 1
                except InterruptedError:
                    raise
                except Exception:
                    if tool_effect(step["tool"]) in READ_EFFECTS:
                        raise
                    return {"valid": False, "code": "mutation_failed_requires_review", "results": results}
                finally:
                    if subscription is not None:
                        event_bus.unsubscribe(subscription)
                    metrics["latency_ms"] += int((time.monotonic() - started) * 1000)
                    persist_metrics()
                output_bytes = len((raw if isinstance(raw, str) else json.dumps(raw)).encode("utf-8", "surrogatepass"))
                normalized = blob_references(self.artifacts, durable_id, raw)
                try:
                    projection = json.loads(raw) if isinstance(raw, str) else raw
                    if isinstance(projection, dict) and projection.get("cache_hit") and projection.get("status") == "unchanged":
                        raw = self.artifacts.read_json(projection["artifact_ref"])
                except (ValueError, FileNotFoundError):
                    pass
                ref = reads.project(args, normalized) if step["tool"] == "read_file" else content_reference(
                    self.artifacts, durable_id, normalized)
                metrics["artifact_bytes"] += ref["size_bytes"] if not ref["cache_hit"] else 0
                metrics["cache_hits" if ref["cache_hit"] else "cache_misses"] += 1
                metrics["tool_output_bytes"] += output_bytes
                text = raw if isinstance(raw, str) else json.dumps(raw)
                failed, _ = classify_tool_failure(step["tool"], text)
                observe_capability(capabilities, step["tool"], args, raw)
                if context:
                    context[10].update(capabilities)
                self.store.update_plan_metadata(item.plan_id, {"capabilities": capabilities})
                verified = not failed and (not step.get("expect") or _validate(raw, _bind(step["expect"], payload, bindings)))
                if identity_record:
                    identity_record.update({"evidence_ref": ref["artifact_ref"], "status": "executed_unverified" if verified else "uncertain"})
                    self.store.update_item_checkpoint(item.id, f"step_{index}_dispatch", metadata={"mutation_identity": identity_record})
                results.append({"artifact_ref": ref["artifact_ref"], "verified": verified})
                if not verified:
                    metrics["no_progress_calls"] += 1
                    if recipe_reused and recipe_key:
                        self.recipes.invalidate(recipe_key, "QUARANTINED")
                        recipe_invalidated = True
                        metrics["recipe_invalidations"] += 1
                        self.store.update_plan_metadata(item.plan_id, {"recipe": {"recipe_id": recipe_key, "status": "QUARANTINED", "fingerprint": recipe_hash}})
                    return {"valid": False, "results": results, "code": "unexpected_state",
                            "systemic_failure": {
                                "tool": step["tool"], "step_id": step.get("id", str(index)),
                                "failure_code": "unexpected_state", "verifier": step.get("id", str(index)),
                                "procedure_fingerprint": recipe_hash,
                                "capability_fingerprint": recipe_hash,
                                "target_shape": {k: type(v).__name__ for k, v in payload.items()},
                            }}
                if graph:
                    decoded = _decode_output(raw)
                    bindings["steps"][step["id"]] = decoded
                    bindings[phase if phase != "fan_out" else "steps"][step["id"]] = decoded
                self.store.update_item_checkpoint(item.id, f"step_{index}", metadata={"result_ref": ref["artifact_ref"],
                                                  "verified_targets": step.get("verifies", []),
                                                  "mutation_identity": identity_record})
                for target in step.get("verifies", []):
                    target_index = next(i for i, node in enumerate(phase_steps) if node["id"] == target)
                    checkpoint = f"step_{target_index}"
                    target_meta = self.store.get_item(item.id).checkpoints.get(checkpoint + "_meta", {})
                    target_identity = target_meta.get("mutation_identity")
                    if target_identity:
                        from workstation.browser_transaction import evidence_strength
                        _, verifier_owner = tool_contract(step['tool'])
                        # Missing owner metadata never upgrades itself.  Snapshot is
                        # owner-known E1; all other undeclared verifiers fail closed E0.
                        strength = int(evidence_strength(step)) if transaction or 'evidence_strength' in verifier_owner or step['tool'] == 'browser_snapshot' else 0
                        target_identity.update({"persisted": strength >= 2, "status": "persisted" if strength >= 2 else 'semantically_observed', "verifier_status": "verified",
                                                'evidence_strength': strength,
                                                "verification_evidence_ref": ref["artifact_ref"]})
                        self.store.update_item_checkpoint(item.id, checkpoint, metadata={**target_meta, "mutation_identity": target_identity})
                metrics["state_transitions"] += 1
                persist_metrics()
                if progress is not None and (step.get("verifies") or step["tool"] in {"write_file", "patch"}):
                    progress()
            if first_item and canary_required:
                mutations = {s["id"] for s in canonical_graph["fan_out"] if tool_effect(s["tool"]) in WRITE_EFFECTS}
                proved = {target for s in canonical_graph["fan_out"] for target in s.get("verifies", [])}
                if mutations - proved:
                    return {"valid": False, "code": "canary_external_verifier_required", "results": results}
                self.store.update_item_checkpoint(item.id, "canary_verified", metadata={"fingerprint": recipe_hash})
            return {"valid": True, "results": results}

        def can_start(item):
            if recipe_invalidated:
                return False
            all_items = items_for_plan(item.plan_id)
            phase = item.input_payload.get("_work_phase", "fan_out")
            fan = [i for i in all_items if i.input_payload.get("_work_phase", "fan_out") == "fan_out"]
            if phase == "finalize" and any(i.status.value != "completed" for i in self.store.get_work_items(item.plan_id) if i.input_payload.get("_work_phase") != "finalize"):
                return False
            if phase == "fan_out":
                if any(self.store.get_item(i.id).status.value != "completed" for i in all_items if i.input_payload.get("_work_phase") == "setup"):
                    return False
                if fan and item.id != fan[0].id and (canary_required or preflight):
                    first = self.store.get_item(fan[0].id)
                    return first.status.value == "completed" and (not canary_required or first.checkpoints.get("canary_verified") == "ok")
            return True

        token = _constraints.set(constraints)
        execution_token = _execution_active.set(True)
        try:
            from agent.tool_guardrails import ToolCallGuardrailController
            guardrails = ToolCallGuardrailController()
            runner = DurableBatchRunner(durable_id, task_store=self.store, artifact_store=self.artifacts,
                                        max_retries=2, backoff_seconds=0)
            summary = runner.execute_batch(request.get("title", key), work_payloads,
                worker_fn=worker, validator_fn=lambda raw, _: {
                    "valid": raw.get("valid") is True, "reason": raw.get("code", ""),
                    "waiting_for_human": raw.get("waiting_for_human") is True,
                    "handoff_id": raw.get("handoff_id"),
                    "expected_delta": "verified_step", "actual_delta": raw.get("valid") is True},
                session_id=session_id, metadata=metadata,
                stop_on_exception=kind in {WorkClass.BROWSER_TRANSACTION, WorkClass.PROMPT_QUEUE},
                can_start_item=can_start, guardrails=guardrails)
        finally:
            _execution_active.reset(execution_token)
            _constraints.reset(token)
        envelope = summary.to_dict()
        if envelope['needs_reasoning']:
            from workstation.reasoning_handoff import needs_reasoning
            items = self.store.get_work_items(durable_id)
            unresolved = next((i for i in items if i.status.value != 'completed'), None)
            if unresolved:
                checkpoints = unresolved.checkpoints
                committed = [int(k.split('_')[1]) for k, v in checkpoints.items()
                             if re.fullmatch(r'step_\d+_meta', k) and isinstance(v, dict) and v.get('result_ref')]
                safe = not any(k.endswith('_dispatch') and
                    i.checkpoints.get(k + '_meta', {}).get('mutation_identity') and
                    not i.checkpoints.get(k.removesuffix('_dispatch') + '_meta', {}).get('result_ref')
                    for i in items for k in i.checkpoints)
                if self.store.get_plan(durable_id).metadata.get('circuit', {}).get('status') == 'SYSTEMIC_FAILURE_SUSPECTED':
                    safe = False
                if unresolved.validation_result.get('reason') != 'unexpected_state':
                    safe = False
                phase = unresolved.input_payload.get('_work_phase', 'fan_out')
                phase_steps = graph[phase] if graph else steps
                failed_index = next((n for n in range(len(phase_steps)) if n not in committed), None)
                handoff = needs_reasoning(self.artifacts, durable_id,
                    completed_until=f'step_{max(committed)}' if committed else None,
                    expected=phase_steps[failed_index].get('expect') if failed_index is not None else 'verified item',
                    observed={'result_ref': unresolved.raw_output_ref, 'reason': unresolved.validation_result.get('reason')},
                    safe_to_resume=safe, context={'item_id': unresolved.id, 'phase': phase,
                        'failed_index': failed_index, 'recipe_fingerprint': recipe_hash})
                self.store.update_plan_metadata(durable_id, {'reasoning_handoff': handoff})
                envelope.update(handoff)
        mutation_records = self.store.mutation_records(summary.plan_id)
        if mutation_records:
            mutation_ledger = self.artifacts.store(durable_id, "mutation_ledger.json", mutation_records)
            self.store.update_plan_metadata(summary.plan_id, {"mutation_ledger_ref": mutation_ledger.ref})
        envelope["results_ref"] = summary.summary_artifact_ref
        envelope["ledger"] = self.store.operational_ledger(durable_id)
        canary = envelope["ledger"].get("canary", {})
        metrics["canary_successes"] = int(canary_required and canary.get("verified", False))
        metrics["canary_failures"] = int(canary_required and canary.get("status") in {"failed", "uncertain"})
        if recipe_key and canary.get("verified") and all(i.status.value == "completed" for i in self.store.get_work_items(durable_id)):
            verifier_ids = [s["id"] for s in canonical_graph["fan_out"] if s.get("verifies")]
            self.recipes.promote(recipe_key, canonical_graph, scope, preflight, verifier_ids, recipe_hash, intended_target)
            self.store.update_plan_metadata(durable_id, {"recipe": {"recipe_id": recipe_key, "status": "VERIFIED", "fingerprint": recipe_hash}})
            envelope["ledger"] = self.store.operational_ledger(durable_id)
        if graph:
            envelope["completed"] = envelope["ledger"]["items"]["completed"]
            envelope["total"] = len(request["items"])
        if canary_required and not canary.get("verified") and envelope["needs_reasoning"]:
            from workstation.work_contract import correction
            envelope.update({"code": "canary_failed", "message": "Canary did not prove persisted state; remaining fan-out is blocked.",
                             "fix": {"review_exceptions": True, "add_read_verifier": True, "never_retry_uncertain_mutation": True}})
        elif envelope["needs_reasoning"] and envelope["ledger"].get("recipe", {}).get("status") == "STALE":
            from workstation.work_contract import correction
            envelope.update(correction(ValueError("recipe_stale: preflight failed; provide a corrected graph and new canary")))
        metrics["work_items_completed"] = envelope["completed"]
        fan_items = [i for i in self.store.get_work_items(durable_id) if i.input_payload.get("_work_phase", "fan_out") == "fan_out"]
        metrics["failed_fanout_items"] = sum(i.status.value in {"blocked", "failed"} for i in fan_items[1:])
        circuit = self.store.get_plan(durable_id).metadata.get("circuit", {})
        metrics["systemic_failures_detected"] = int(circuit.get("status") == "SYSTEMIC_FAILURE_SUSPECTED")
        metrics["systemic_items_prevented"] = circuit.get("systemic_items_prevented", 0)
        metrics["systemic_failure_amplification"] = circuit.get("failed_items", 0)
        metrics["replans"] = int(envelope["needs_reasoning"] > 0)
        metrics["tool_calls_per_state_transition"] = metrics["tool_calls"] / max(1, metrics["state_transitions"])
        metrics["artifact_bytes"] = sum(a.size_bytes for a in self.artifacts.list_artifacts(durable_id)
                                         if a.name != "metrics.json")
        verified_transitions = len({(i.id, target) for i in self.store.get_work_items(durable_id)
            for k, meta in i.checkpoints.items() if k.endswith("_meta") and isinstance(meta, dict) and meta.get("result_ref")
            for target in meta.get("verified_targets", [])})
        metrics.update({"planner_calls": int(provider_usage is not None), "executor_llm_calls": 0,
                        "verified_state_transitions": verified_transitions, "estimated_cost": None, "cost_status": "unknown"})
        if provider_usage is not None:
            metrics.update({"usage_status": "reported", "token_usage_scope": "compile_request",
                            "input_tokens": provider_usage.get("input_tokens"),
                            "cached_input_tokens": provider_usage.get("cache_read_tokens"),
                            "output_tokens": provider_usage.get("output_tokens"),
                            "reasoning_tokens": provider_usage.get("reasoning_tokens")})
            cached = provider_usage.get("cache_read_tokens")
            total_input = provider_usage.get("input_tokens")
            uncached = max(0, total_input - cached) if total_input is not None and cached is not None else None
            metrics["uncached_input_tokens"] = uncached
            metrics["uncached_input_tokens_per_verified_transition"] = uncached / verified_transitions if uncached is not None and verified_transitions else None
            metrics["uncached_tokens_per_verified_transition"] = metrics["uncached_input_tokens_per_verified_transition"]
            metrics["uncached_tokens_per_completed_item"] = uncached / envelope["completed"] if uncached is not None and envelope["completed"] else None
            transitions = metrics["state_transitions"] - prior_transitions
            if transitions and provider_usage.get("total_tokens") is not None:
                metrics["tokens_per_successful_state_transition"] = provider_usage["total_tokens"] / transitions
            metrics["tokens_per_verified_transition"] = provider_usage.get("total_tokens") / verified_transitions if provider_usage.get("total_tokens") is not None and verified_transitions else None
        else:
            for field in ("input_tokens", "uncached_input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens",
                          "tokens_per_verified_transition", "uncached_tokens_per_verified_transition", "uncached_input_tokens_per_verified_transition", "uncached_tokens_per_completed_item"):
                metrics[field] = None
        metrics["llm_calls_per_completed_item"] = metrics["planner_calls"] / max(1, envelope["completed"])
        metrics['routine_reuse'] = int(bool(request.get('routine_id')))
        metrics["tool_calls_per_completed_item"] = metrics["tool_calls"] / max(1, envelope["completed"])
        envelope["metrics"] = metrics
        if normalize_verbosity(request.get("verbosity")) == VerbosityLevel.FULL:
            manifest = self.artifacts.read_json(summary.summary_artifact_ref)
            envelope["full_results"] = [self.artifacts.read_json(i["result_ref"])
                                        for i in manifest["results"] if i["result_ref"]]
        for _ in range(3):
            metrics["inline_context_bytes"] = len(json.dumps(envelope).encode())
            metrics["bytes_avoided_by_refs"] = max(0, metrics["tool_output_bytes"] - metrics["inline_context_bytes"])
        persist_metrics()
        return envelope

    def _execute_route(self, request, *, task_id, session_id, dispatch, progress=None, provider_usage=None,
                       event_bus=None, canonical_task_id=None):
        from workstation.control_plane.intent import OperationIntent
        from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
        from workstation.control_plane.router import (
            CapabilityRouter,
            ComposedDecision,
            ExecutableDecision,
            HumanDecision,
            ReasoningDecision,
            SatisfiedDecision,
            WaitDecision,
        )
        from workstation.operational_capabilities import OperationalCapabilityRegistry

        raw_intent = request.get("operation_intent")
        if isinstance(raw_intent, OperationIntent):
            intent = raw_intent
        elif isinstance(raw_intent, dict):
            intent = OperationIntent.from_dict(raw_intent)
        else:
            raise ValueError("Route action requires a valid operation_intent")

        semantic_state = request.get("semantic_state") or {}

        # Resolve ambient trusted authority. Model/request data is never a trust root;
        # request["authority"] may only narrow this owner-supplied scope below.
        trusted_authority = None
        if getattr(self, "trusted_authority", None) is not None:
            trusted_authority = getattr(self, "trusted_authority")
        elif canonical_task_id or task_id:
            try:
                from hermes_cli import kanban_db
                from hermes_cli.kanban_db_connect import connect
                conn = connect()

                try:
                    t = kanban_db.get_task(conn, canonical_task_id or task_id)
                    if t and getattr(t, "authority_scope", None):
                        trusted_authority = AuthorityScope.from_dict(t.authority_scope)
                finally:
                    conn.close()
            except Exception:
                pass
        if trusted_authority is None:
            trusted_authority = AuthorityScope(level=AuthorityLevel.READ)

        # Narrow against requested authority if provided
        raw_requested = request.get("authority")
        if raw_requested is not None:
            if isinstance(raw_requested, AuthorityScope):
                requested_scope = raw_requested
            elif isinstance(raw_requested, dict):
                lvl = raw_requested.get("level", AuthorityLevel.READ)
                if isinstance(lvl, int):
                    lvl = AuthorityLevel(lvl)
                requested_scope = AuthorityScope(
                    level=lvl,
                    allowed_actions=set(raw_requested.get("allowed_actions", ["*"])),
                    allowed_resources=set(raw_requested.get("allowed_resources", ["*"])),
                )
            else:
                requested_scope = AuthorityScope(level=AuthorityLevel.READ)
            authority = trusted_authority.narrow(requested_scope)
        else:
            authority = trusted_authority

        registry = getattr(self, "capability_registry", None)
        if registry is None:
            registry = OperationalCapabilityRegistry(artifacts=self.artifacts)
        from workstation.control_plane.composition import CompositionEngine
        from workstation.control_plane.router import CapabilityRouter
        router = getattr(self, "router", None) or CapabilityRouter(registry, composition_engine=CompositionEngine(registry))

        # Runtime truth the caller already observed — outstanding uncertainty,
        # baseline state — is offered to the router rather than decided here. The
        # router owns reconciliation gating; a caller that observes nothing passes
        # nothing and routing behaves exactly as before.
        runtime_state = request.get("runtime_state")
        decision = router.route(intent, semantic_state, authority,
                                runtime_state=runtime_state if isinstance(runtime_state, dict) else None)
        try:
            self.metrics_collector.on_routing_decision(decision)
        except Exception:
            pass

        if isinstance(decision, SatisfiedDecision):
            return {
                "success": True,
                "routing_decision": "SATISFIED",
                "message": "Goal is already satisfied by current semantic state",
                "certificate_hash": "",
            }

        if isinstance(decision, ExecutableDecision):
            cert_hash = decision.certificate.certificate_hash()
            cap_exec_req = {
                **request,
                "capability_id": decision.capability.id,
                "capability_version": decision.capability.version,
                "operation_key": request.get("operation_key") or f"route_{intent.id}",
            }

            from workstation.control_plane.dispatcher import CertifiedDispatcher, DispatchError
            dispatcher = getattr(self, "certified_dispatcher", None)
            if dispatcher is None:
                dispatcher = CertifiedDispatcher(kernel=getattr(self, "kernel", None))

            def _run_exec():
                return self._execute_capability(
                    cap_exec_req,
                    task_id=task_id,
                    session_id=session_id,
                    dispatch=dispatch,
                    canonical_task_id=canonical_task_id,
                )

            try:
                dispatch_res = dispatcher.dispatch(
                    decision,
                    current_state=semantic_state,
                    dispatch_fn=_run_exec,
                    run_id=getattr(self, "canonical_run_id", None) or request.get("run_id"),
                    has_uncertain_mutation=getattr(self, "has_uncertain_mutation", False) or request.get("has_uncertain_mutation", False),
                    authority_scope=authority,
                    verification_result_fn=lambda result: result.get("verification_result", {
                        "status": "INCONCLUSIVE",
                        "reason": "executor_did_not_return_canonical_verification",
                    }) if isinstance(result, dict) else {
                        "status": "INCONCLUSIVE", "reason": "invalid_executor_result"
                    },
                )
                exec_res = dispatch_res.get("result", {})
                if not dispatch_res.get("success", True):
                    return {
                        **exec_res,
                        "success": False,
                        "routing_decision": "ASK_HUMAN",
                        "reason": dispatch_res.get("error", "execution_failed"),
                        "capability_id": decision.capability.id,
                        "certificate_hash": cert_hash,
                        "dispatch_record": dispatch_res.get("dispatch_record"),
                    }
                return {
                    **exec_res,
                    "success": bool(exec_res.get("success", True)),
                    "routing_decision": "EXECUTE",
                    "capability_id": decision.capability.id,
                    "certificate_hash": cert_hash,
                    "dispatch_record": dispatch_res.get("dispatch_record"),
                }
            except DispatchError as exc:
                return {
                    "success": False,
                    "routing_decision": "ASK_HUMAN",
                    "reason": f"certified_dispatch_failed: {exc}",
                    "capability_id": decision.capability.id,
                    "certificate_hash": cert_hash,
                }

        if isinstance(decision, ComposedDecision):
            cert_hash = decision.certificate.certificate_hash()
            from workstation.control_plane.dispatcher import CertifiedDispatcher, DispatchError
            dispatcher = getattr(self, "certified_dispatcher", None)
            if dispatcher is None:
                dispatcher = CertifiedDispatcher(kernel=getattr(self, "kernel", None))

            bindings = request.get("composition_bindings")
            if not isinstance(bindings, dict):
                return {
                    "success": False,
                    "routing_decision": "WAKE_LLM",
                    "reason": "composition_inputs_unbound",
                    "plan": [c.id for c in decision.plan],
                    "certificate_hash": cert_hash,
                    "mutations_dispatched": 0,
                }

            kernel = getattr(self, "kernel", None)
            if kernel is None:
                from workstation.operational_kernel import OperationalKernel
                kernel = OperationalKernel(registry=registry, artifacts=self.artifacts)

            confirmed_steps = []

            def _run_composition():
                for cap in decision.plan:
                    step_inputs = bindings.get(cap.id)
                    if not isinstance(step_inputs, dict):
                        return {
                            "success": False,
                            "status": "NEEDS_REASONING",
                            "reason": "composition_inputs_unbound",
                            "capability_id": cap.id,
                            "confirmed_steps": list(confirmed_steps),
                        }
                    step_result = kernel.execute_capability(
                        cap,
                        step_inputs,
                        dispatch=dispatch,
                        context=request.get("execution_context") or {},
                        owner=str(canonical_task_id or task_id or session_id),
                    )
                    if (not isinstance(step_result, dict)
                            or step_result.get("success") is not True
                            or step_result.get("verification_result", {}).get("status") != "VERIFIED"):
                        return {
                            "success": False,
                            "status": step_result.get("status", "NEEDS_REASONING") if isinstance(step_result, dict) else "NEEDS_REASONING",
                            "reason": step_result.get("reason", "composition_step_not_verified") if isinstance(step_result, dict) else "composition_step_not_verified",
                            "capability_id": cap.id,
                            "confirmed_steps": list(confirmed_steps),
                            "step_result": step_result,
                        }
                    confirmed_steps.append({"id": cap.id, "version": cap.version, "result": step_result})
                # Authoritative final readback of the goal of OperationIntent!
                # child verification != final semantic goal verification.
                final_readback_fn = request.get("final_readback_fn")
                final_state = request.get("semantic_state") or {}
                if callable(final_readback_fn):
                    try:
                        readback_state = final_readback_fn()
                        if isinstance(readback_state, dict):
                            final_state = {**final_state, **readback_state}
                    except Exception as e:
                        return {
                            "success": False,
                            "status": "FINAL_GOAL_VERIFICATION_FAILED",
                            "reason": f"final_readback_error: {e}",
                            "confirmed_steps": list(confirmed_steps),
                        }

                if request.get("goal_verifier_fn"):
                    try:
                        goal_ok = bool(request["goal_verifier_fn"](final_state, confirmed_steps))
                        if not goal_ok:
                            return {
                                "success": False,
                                "status": "FINAL_GOAL_VERIFICATION_FAILED",
                                "reason": "goal_verifier_failed",
                                "confirmed_steps": list(confirmed_steps),
                            }
                    except Exception as e:
                        return {
                            "success": False,
                            "status": "FINAL_GOAL_VERIFICATION_FAILED",
                            "reason": f"goal_verifier_error: {e}",
                            "confirmed_steps": list(confirmed_steps),
                        }
                elif intent and intent.goal:
                    accumulated_state = dict(final_state)
                    for s in confirmed_steps:
                        res = s.get("result", {})
                        if isinstance(res.get("output"), dict):
                            accumulated_state.update(res["output"])
                    if not intent.goal.evaluate(accumulated_state):
                        return {
                            "success": False,
                            "status": "FINAL_GOAL_VERIFICATION_FAILED",
                            "reason": "final_intent_goal_not_satisfied_by_authoritative_state",
                            "confirmed_steps": list(confirmed_steps),
                        }

                final_result = request.get("final_verification_result")
                if callable(request.get("final_verification_result_fn")):
                    final_result = request["final_verification_result_fn"](final_state, confirmed_steps)
                if not isinstance(final_result, dict) or final_result.get("status") != "VERIFIED":
                    return {
                        "success": False,
                        "status": "FINAL_GOAL_VERIFICATION_FAILED",
                        "reason": "final_goal_missing_canonical_verification",
                        "confirmed_steps": list(confirmed_steps),
                        "verification_result": final_result or {"status": "INCONCLUSIVE"},
                    }
                return {"success": True, "plan": [c.id for c in decision.plan], "confirmed_steps": confirmed_steps,
                        "verification_result": final_result}

            try:
                dispatch_res = dispatcher.dispatch(
                    decision,
                    current_state=semantic_state,
                    dispatch_fn=_run_composition,
                    run_id=getattr(self, "canonical_run_id", None) or request.get("run_id"),
                    has_uncertain_mutation=getattr(self, "has_uncertain_mutation", False) or request.get("has_uncertain_mutation", False),
                    authority_scope=authority,
                    verification_result_fn=lambda result: result.get("verification_result", {
                        "status": "INCONCLUSIVE",
                        "reason": "final_goal_missing_canonical_verification",
                    }) if isinstance(result, dict) else {
                        "status": "INCONCLUSIVE", "reason": "invalid_composition_result"
                    },
                )
                composition_result = dispatch_res.get("result", {})
                return {
                    **composition_result,
                    "success": bool(dispatch_res.get("success")),
                    "routing_decision": "COMPOSE",
                    "plan": [c.id for c in decision.plan],
                    "certificate_hash": cert_hash,
                    "dispatch_record": dispatch_res.get("dispatch_record"),
                }
            except DispatchError as exc:
                return {
                    "success": False,
                    "routing_decision": "ASK_HUMAN",
                    "reason": f"certified_dispatch_failed: {exc}",
                    "certificate_hash": cert_hash,
                }

        if isinstance(decision, WaitDecision):
            from workstation.control_plane.waiting import (
                AwaitCondition,
                AwaitConditionStore,
                AwaitContinuation,
            )
            raw_cond = decision.await_condition
            if isinstance(raw_cond, dict):
                cond = AwaitCondition.from_dict(raw_cond)
            else:
                cond = raw_cond

            if cond is not None:
                task_ref = canonical_task_id or task_id
                run_ref = request.get("run_id")
                op_ref = request.get("operation_id") or (intent.id if intent else None)
                intent_id_val = intent.id if intent else None
                intent_hash_val = getattr(intent, "intent_hash", None) if intent else None
                sem_state_val = dict(semantic_state) if semantic_state else {}

                if not getattr(cond, "continuation", None):
                    cond.continuation = AwaitContinuation(
                        task_id=task_ref,
                        run_id=run_ref,
                        operation_id=op_ref,
                        intent_id=intent_id_val,
                        intent_hash=intent_hash_val,
                        last_verified_state=sem_state_val,
                    )
                elif isinstance(cond.continuation, dict):
                    c_dict = dict(cond.continuation)
                    c_dict.setdefault("task_id", task_ref)
                    c_dict.setdefault("run_id", run_ref)
                    c_dict.setdefault("operation_id", op_ref)
                    c_dict.setdefault("intent_id", intent_id_val)
                    c_dict.setdefault("last_verified_state", sem_state_val)
                    cond.continuation = AwaitContinuation.from_dict(c_dict)

                if not cond.task_id and task_ref:
                    cond.task_id = task_ref
                if not cond.run_id and run_ref:
                    cond.run_id = run_ref
                if not cond.operation_id and op_ref:
                    cond.operation_id = op_ref

                # Persist AwaitCondition to AwaitConditionStore (surviving process restart)
                await_store = AwaitConditionStore(artifacts=self.artifacts)
                await_store.save(cond)

            cond_dict = (
                cond.to_dict()
                if hasattr(cond, "to_dict")
                else cond
            )
            return {
                "success": False,
                "routing_decision": "WAIT",
                "await_condition": cond_dict,
                "condition": cond_dict,
                "reason": decision.reason,
                "wait_id": getattr(cond, "wait_id", None),
                "correlation_id": getattr(cond, "correlation_id", None),
                "worker_released": True,
            }

        if isinstance(decision, HumanDecision):
            scope_dict = (
                decision.scope.to_dict()
                if hasattr(decision.scope, "to_dict")
                else decision.scope
            )
            return {
                "success": False,
                "routing_decision": "ASK_HUMAN",
                "reason": decision.reason,
                "scope": scope_dict,
                "missing_authority": scope_dict,
            }

        # ReasoningDecision
        from workstation.reasoning_handoff import needs_reasoning
        open_cond = (
            decision.open_condition.to_dict()
            if hasattr(decision.open_condition, "to_dict")
            else decision.open_condition
        )
        attention = (
            decision.attention_packet.to_dict()
            if hasattr(decision.attention_packet, "to_dict")
            else decision.attention_packet
        )
        context_payload = {
            "intent_id": intent.id,
            "open_condition": open_cond,
            "attention_packet": attention,
            "requires_reconciliation": getattr(decision, "requires_reconciliation", False),
            "reason": decision.reason,
        }
        handoff = needs_reasoning(
            self.artifacts,
            owner=str(canonical_task_id or task_id or session_id),
            completed_until=None,
            expected="Executable capability match",
            observed=decision.reason,
            safe_to_resume=False,
            context=context_payload,
        )
        return {
            **handoff,
            "success": False,
            "routing_decision": "WAKE_LLM",
            "reason": decision.reason,
            "open_condition": open_cond,
            "attention_packet": attention,
            "requires_reconciliation": getattr(decision, "requires_reconciliation", False),
            "context": context_payload,
        }

    def _execute_capability(self, request, *, task_id, session_id, dispatch, canonical_task_id=None):
        from workstation.operational_kernel import OperationalKernel
        from workstation.experience_compiler.promotion import pin_capability, contract_fingerprint
        from workstation.recipes import digest, sanitize
        from hermes_cli import kanban_db
        kernel = OperationalKernel(artifacts=self.artifacts)
        owner = str(canonical_task_id or task_id or session_id)
        conn = self.store.get_connection()
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        canonical = kanban_db.get_task(conn, owner) if 'tasks' in tables else None
        if (canonical_task_id and not canonical) or (canonical and canonical.session_id != session_id):
            raise ValueError('Canonical task does not belong to the owning conversation')
        run_id = str(canonical.current_run_id) if canonical and canonical.current_run_id is not None else None
        inputs = request.get('capability_inputs') or request.get('inputs') or {}
        identity = 'cap_exec_' + digest({'owner': owner, 'run_id': run_id, 'session_id': session_id,
            'capability_id': request['capability_id'], 'inputs': sanitize(inputs),
            'operation_key': request.get('operation_key')})[:24]
        plan = self.store.get_plan(request.get('_capability_plan_id') or identity)
        if plan and plan.session_id != session_id:
            raise ValueError('Capability plan belongs to another conversation')
        if plan and plan.run_id != run_id:
            raise ValueError('stale_task_run: capability resume belongs to a superseded run')
        if plan and plan.metadata.get('capability_result_ref'):
            result = self.artifacts.read_json(plan.metadata['capability_result_ref'])
            return {**result, 'plan_id': plan.id, 'results_ref': plan.metadata['capability_result_ref']}
        selected = kernel.resolver.resolve(request['capability_id'], request.get('capability_version') or '*')
        if not plan:
            objective = self.artifacts.store(identity, 'objective.json', sanitize(request))
            plan = self.store.create_plan(identity, selected.name, [{}], session_id=session_id, run_id=run_id,
                execution_key=identity, metadata={'objective_ref': objective.ref,
                    'canonical_task_id': canonical.id if canonical else None, 'browser_task_id': task_id,
                    'capability_execution': True})
        pin = pin_capability(self.store, plan.id, selected)
        cap = kernel.registry.get(pin['capability_id'], pin['version'])
        if not cap or cap.semantic_fingerprint != pin['semantic_fingerprint'] or cap.compatibility_fingerprint != pin['compatibility_fingerprint']:
            raise ValueError('pinned capability contract changed')
        if pin.get('contract_fingerprint') and contract_fingerprint(cap) != pin['contract_fingerprint']:
            raise ValueError('pinned capability implementation changed')
        for dependency in kernel.resolver.linearize(cap.id, cap.version):
            pin_capability(self.store, plan.id, dependency)
        item = self.store.get_work_items(plan.id)[0]
        constraints = merge_constraints(active_constraints(), request.get('constraints', {}))
        def admit(route, mutating):
            require_allowed_route(route, constraints)
            if mutating:
                require_allowed_route(route, {k.removeprefix('mutation_'): v for k, v in constraints.items() if k.startswith('mutation_')})
            if mutating and canonical:
                live = kanban_db.get_task(self.store.get_connection(), canonical.id)
                if not live or str(live.current_run_id) != str(plan.run_id) or live.status in {'done', 'cancelled'}:
                    raise ValueError('stale_task_run')
        # Browser actions retain the caller's scoped tool dispatcher/approval/lease.
        def scoped_dispatch(name, args):
            return dispatch(name, args, task_id, f'{item.id}_{name}')
        exec_context = {
            'task_id': owner, 'run_id': run_id or '', 'session_id': session_id,
            'enforce_lineage': True,
            'capability_pins': self.store.get_plan(plan.id).metadata['capability_pins'],
            'durable_store': self.store, 'durable_item_id': item.id, 'primitive_admission': admit,
        }
        for k in ('verification_evidence', 'verification_expected', 'observer_fn', 'readback_fn', 'observer_args', 'observed_predicates', 'resource_id', 'resource_version', 'operation_id', 'expected_task_id', 'expected_run_id', 'expected_operation_id'):
            if k in request:
                exec_context[k] = request[k]
        result = kernel.execute_capability(cap, inputs, dispatch=scoped_dispatch, owner=owner, context=exec_context)
        projected_output = blob_references(self.artifacts, owner, sanitize(result.get('output')))
        if len(json.dumps(projected_output, ensure_ascii=False).encode('utf-8', 'surrogatepass')) > 2048:
            projected_output = content_reference(self.artifacts, owner, projected_output, schema='capability_output')
        envelope = {'status': result.get('status', 'COMPLETED'), 'task_id': owner,
            'capability_id': cap.id, 'capability_version': cap.version,
            'output': projected_output, 'savings': result.get('savings', {}),
            'verification': sanitize(result.get('verification') or {'accepted': False, 'source': 'none'}),
            'verification_result': sanitize(result.get('verification_result') or {
                'status': 'INCONCLUSIVE', 'reason': 'missing_canonical_verification_result'
            }),
            'metrics': {'executor_llm_calls': 0}}
        verification = result.get('verification_result') or {}
        terminal_verified = (str(verification.get('status', '')).upper() == 'VERIFIED'
                             and verification.get('accepted') is True)
        ref = self.artifacts.store(owner, plan.id + ('_result.json' if terminal_verified else '_handoff.json'), sanitize(envelope))
        if terminal_verified:
            self.store.mark_item_persisted(item.id, ref.ref)
            self.store.mark_item_validated(item.id, {'valid': True, 'capability_version': cap.version,
                                                    'evidence_ref': ref.ref})
            self.store.complete_item(item.id)
            self.store.update_plan_state(plan.id, 'completed')
            self.store.update_plan_metadata(plan.id, {'capability_result_ref': ref.ref})
        else:
            self.store.update_plan_state(plan.id, 'blocked')
            self.store.mark_item_persisted(item.id, ref.ref)
            envelope.update({k: v for k, v in result.items() if k != 'output'})
        return {**envelope, 'plan_id': plan.id, 'results_ref': ref.ref,
                'execution_acknowledged': bool(result.get('execution_acknowledged', False)),
                'success': terminal_verified}

    def resume(self, plan_id: str, *, session_id: str, dispatch: Callable,
               progress: Callable | None = None, provider_usage: dict | None = None,
               status_only: bool = False, event_bus=None) -> dict:
        plan = self.store.get_plan(plan_id)
        if plan is None or plan.id != plan_id or plan.session_id != session_id:
            raise ValueError("Plan not found in the owning conversation")
        if status_only:
            return self.store.operational_ledger(plan_id)
        if plan.metadata.get('capability_execution'):
            objective = self.artifacts.read_json(plan.metadata['objective_ref'])
            return self._execute_capability({**objective, '_capability_plan_id': plan.id},
                task_id=plan.metadata['browser_task_id'], session_id=session_id, dispatch=dispatch,
                canonical_task_id=plan.metadata.get('canonical_task_id'))
        reasoning = plan.metadata.get('reasoning_handoff') or {}
        if reasoning.get('safe_to_resume'):
            body = self.artifacts.read_json(reasoning['state_ref'])
            item_id = body.get('context', {}).get('item_id')
            if item_id:
                self.store.resume_reasoning_item(item_id)
        handoff_metadata = plan.metadata.get("handoff") or {}
        handoff = self.handoffs.get(handoff_metadata.get("handoff_id", ""))
        if handoff is not None and handoff.status == "ready":
            if handoff.task_id != plan.metadata["browser_task_id"] or handoff.session_id != session_id:
                raise ValueError("Handoff does not belong to this task/session")
            from workstation.durable_tasks import WorkItemStatus
            for item in self.store.get_work_items(plan_id):
                if item.status == WorkItemStatus.WAITING_FOR_USER and item.validation_result.get("handoff_id") == handoff.handoff_id:
                    self.store.resume_waiting_item(item.id)
            self.store.update_plan_metadata(plan_id, {"handoff": {**handoff_metadata, "status": "ready"}})
        objective = self.artifacts.read_json(plan.metadata["objective_ref"])
        return self.execute(objective, task_id=plan.metadata["browser_task_id"], session_id=session_id,
                            dispatch=dispatch, progress=progress, provider_usage=provider_usage, event_bus=event_bus,
                            canonical_task_id=plan.metadata.get("canonical_task_id"))

    def handle_event(
        self,
        event: Any,
        read_authoritative_state: Callable[[], dict[str, Any]],
        resume_fn: Callable[[Any, dict[str, Any]], bool] | None = None,
    ) -> bool:
        """Process an incoming causal event against persistent AwaitConditions.
        
        Enforces Rule 21.2: EVENT WAKES. AUTHORITATIVE STATE CONFIRMS.
        """
        from workstation.control_plane.waiting import AwaitConditionStore, TriggerCoordinator
        store = AwaitConditionStore(artifacts=self.artifacts)
        coordinator = TriggerCoordinator(store=store)
        resumed = coordinator.handle_event(
            event=event,
            read_authoritative_state=read_authoritative_state,
            resume_fn=resume_fn,
        )
        if resumed:
            self.ora_metrics.record_transition(verified=True, reasoned=False)
        return resumed


def execute_compiled_work(args: dict, **kwargs) -> str:
    if args.get("action") == "contract":
        from workstation.work_contract import CONTRACT
        return json.dumps(CONTRACT, ensure_ascii=False)
    context = _dispatch_context.get()
    if context is None:
        return json.dumps({"error": "Durable work requires the scoped agent dispatcher"})
    compiler = TaskCompiler()
    try:
        return _execute_compiled_work(compiler, context, args, kwargs)
    except (ValueError, KeyError, TypeError, ConstraintViolation) as error:
        from workstation.work_contract import correction
        result = correction(error)
        if not isinstance(error, ConstraintViolation) and not args.get('plan_id'):
            from workstation.reasoning_handoff import needs_reasoning
            result.update(needs_reasoning(compiler.artifacts, context[1], completed_until=None,
                expected='decided, compatible executable contract', observed=str(error),
                safe_to_resume=False, context={'phase': 'admission', 'dispatched': False}))
        return json.dumps(result, ensure_ascii=False)
    finally:
        compiler.store.close()


def _execute_compiled_work(compiler, context, args, kwargs):
    dispatch, session_id, _, references, progress, usage, _, event_bus, canonical_task_id, _, _ = context
    if args.get("action") == "discover":
        return json.dumps(compiler.discover(args, task_id=str(kwargs.get("task_id") or session_id),
                                           session_id=session_id, dispatch=dispatch), ensure_ascii=False)
    if args.get("plan_id"):
        envelope = compiler.resume(args["plan_id"], session_id=session_id, dispatch=dispatch,
                                   progress=progress, provider_usage=usage,
                                   status_only=args.get("action") == "status", event_bus=event_bus)
        if args.get("action") == "status":
            references.append({"trusted": True, "version": 1, "source": "KanbanRun", "kind": "durable_work",
                               "id": envelope["plan_id"], "task_id": envelope["task_id"],
                               "owner_session_id": session_id})
            return json.dumps(envelope, ensure_ascii=False)
    else:
        envelope = compiler.execute(args, task_id=str(kwargs.get("task_id") or session_id),
                                    session_id=session_id, dispatch=dispatch, progress=progress,
                                    provider_usage=usage, event_bus=event_bus, canonical_task_id=canonical_task_id)
    references.append({"trusted": True, "version": 1, "source": "KanbanRun", "kind": "durable_work",
                       "id": envelope.get("plan_id", envelope.get("capability_id", "route")),
                       "task_id": envelope.get("task_id", str(kwargs.get("task_id") or session_id)),
                       "owner_session_id": session_id, "result_ref": envelope.get("results_ref")})
    return json.dumps(envelope, ensure_ascii=False)
