"""Bounded adaptive observations; artifacts/journal/memory retain ownership."""
import re
import json
import uuid
from datetime import datetime, timezone
from tools.effects import tool_effect
from workstation.recipes import sanitize, digest
from workstation.routing import canonical_route_for_tool

_TRANSIENT = {'ref', 'node_id', 'nodeId', 'tab_id', 'tabId', 'webContentsId', 'webcontents_id', 'web_contents_id', 'WebContentsId'}


def durable_arguments(value):
    value = sanitize(value)
    if isinstance(value, dict):
        return {k: ('$item.text' if k == 'text' else durable_arguments(v)) for k, v in value.items() if k not in _TRANSIENT}
    if isinstance(value, list):
        return [durable_arguments(v) for v in value[:64]]
    if isinstance(value, str):
        return '[REACQUIRE]' if re.search(r'@e\d+\b', value) else value[:1024]
    return value


def record_trace(agent, name, args, raw, *, duration_ms=None):
    from workstation.artifacts import ArtifactStore
    from workstation.batch_detection import structural_signature
    from workstation.execution_policy import semantic_operation_fingerprint
    from agent.tool_guardrails import classify_tool_failure
    from workstation.journal import ExecutionJournal
    from workstation.contracts import ExecutionEventKind
    owner = getattr(agent, '_canonical_work_task_id', None) or agent._conversation_root_id() or agent.session_id
    artifacts = ArtifactStore()
    output = artifacts.store(owner, 'trace_result_' + digest(sanitize(raw)) + '.json', sanitize(raw))
    arguments = durable_arguments(args)
    try:
        decoded = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        decoded = None
    selected_runtime = 'internal' if isinstance(decoded, dict) and decoded.get('runtime') == 'electron-chromium' else None
    traces = getattr(agent, '_work_procedure_trace', [])
    before_ref = traces[-1]['after_state_ref'] if traces else None
    if selected_runtime == 'internal' and isinstance(decoded.get('target'), dict) and not arguments.get('semantic_anchor'):
        from workstation.experience_compiler.state_abstraction import semantic_anchor
        anchor = semantic_anchor(decoded['target'])
        if anchor:
            arguments['semantic_anchor'] = durable_arguments(anchor)
    if selected_runtime == 'internal' and args.get('ref') and not arguments.get('semantic_anchor') and before_ref:
        from workstation.routines import semantic_browser_elements
        before = artifacts.read_json(before_ref)
        elements = semantic_browser_elements(before) if isinstance(before, dict) else []
        element = next((e for e in elements if e.get('ref') == args['ref']), None)
        if element:
            if element.get('testid'):
                arguments['semantic_anchor'] = {'type': 'testid', 'value': element['testid']}
            elif element.get('name'):
                arguments['semantic_anchor'] = {'type': 'role_name', 'value': f"{element.get('role') or element.get('tag', 'element')}:{element['name']}"}
            elif element.get('label') and sum(e.get('role') == element.get('role') and e.get('label') == element['label'] for e in elements) == 1:
                arguments['semantic_anchor'] = {'type': 'role_name', 'value': element['role'] + ':' + element['label']}
    route = canonical_route_for_tool(name, runtime=selected_runtime)
    from urllib.parse import urlsplit
    before_data = artifacts.read_json(before_ref) if before_ref else {}
    url = arguments.get('url') or (before_data.get('url') if isinstance(before_data, dict) else None)
    parsed = urlsplit(url or '')
    scope = {'host': parsed.hostname, 'path_family': re.sub(r'/\d+(?=/|$)', '/:number', parsed.path or '/')} if parsed.hostname else {}
    sem_fp = semantic_operation_fingerprint(name, arguments, route=route, scope=scope)
    op_fp = sem_fp or structural_signature(name, arguments)
    is_console = name in {'browser_console', 'console'} or arguments.get('action') == 'console'
    trace_action = 'opaque_adaptive_execution' if is_console else name.removeprefix('browser_')
    trace_replayable = False if is_console else (not any(k in args for k in _TRANSIENT) or bool(arguments.get('semantic_anchor')))
    record = {'tool': name, 'action': trace_action,
        'execution_class': 'opaque_adaptive_execution' if is_console else 'semantic',
        'route': canonical_route_for_tool(name, runtime=selected_runtime), 'operation_fingerprint': op_fp,
        'semantic_fingerprint': sem_fp,
        'arguments': arguments, 'semantic_anchor': arguments.get('semantic_anchor'),
        'before_state_ref': before_ref, 'after_state_ref': output.ref,
        'outcome': 'failed' if classify_tool_failure(name, raw if isinstance(raw, str) else json.dumps(raw))[0] else 'executed_unverified',
        'effect': tool_effect(name, args=arguments).value, 'duration_ms': duration_ms,
        'task_id': getattr(agent, '_canonical_work_task_id', None),
        'run_id': getattr(agent, '_canonical_work_run_id', None),
        'operation_id': (
            getattr(agent, '_current_operation_id', None)
            or (args.get('operation_id') if isinstance(args, dict) else None)
            or (decoded.get('operation_id') if isinstance(decoded, dict) else None)
            or ('observation_' + uuid.uuid4().hex)
        ),
        'operation_index': len(traces),
        'captured_at': datetime.now(timezone.utc).isoformat(),
        'scope': scope,
        'runtime': decoded.get('runtime', route) if isinstance(decoded, dict) else route,
        'provider_usage': sanitize(getattr(agent, '_current_provider_usage', None)),
        'replayable': trace_replayable}
    if len(traces) >= 64:
        agent._work_procedure_trace_truncated = True
        return
    traces.append(record)
    agent._work_procedure_trace = traces
    from workstation.experience_compiler.state_abstraction import abstract_state, sample_from_trace
    provenance = None
    if (name == 'browser_navigate' and route == 'native_browser'
            and record['task_id'] and record['run_id'] and record['outcome'] == 'executed_unverified'):
        from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope, authority_covers
        from workstation.contracts import MessageOrigin
        from workstation.experience_compiler.models import AuthorityOrigin, Provenance
        from workstation.integrations.hermes.effect_authority import trusted_effect_authority_from_agent

        authority = trusted_effect_authority_from_agent(agent, agent.session_id)
        envelope = getattr(agent, '_message_envelope', None)
        required = AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION,
            allowed_actions={'browser_navigate'}, allowed_resources={'native_browser'})
        if authority_covers(authority, required) and envelope is not None:
            origin = AuthorityOrigin.USER if envelope.origin == MessageOrigin.HUMAN else AuthorityOrigin.SYSTEM
            grant = {'task_id': record['task_id'], 'run_id': str(record['run_id']),
                     'session_id': agent.session_id, 'authority_origin': origin.value,
                     'authority_scope': required.to_dict()}
            authority_ref = artifacts.store(owner, 'trace_authority_' + digest(grant) + '.json',
                                            grant, schema='hermes.trace_authority.v1').ref
            provenance = Provenance(task_id=record['task_id'], run_id=str(record['run_id']),
                operation_id=record['operation_id'], runtime=record['runtime'],
                authority_origin=origin, trust_class='trusted_runtime',
                authority_ref=authority_ref, authority_scope=required.to_dict())
    sample = sample_from_trace(record,
        before=abstract_state(route, before_data, before_ref),
        after=abstract_state(route, decoded, output.ref), provenance=provenance)
    sample.provenance.operation_index = record['operation_index']
    sample_ref = artifacts.store(owner, 'transition_' + digest(sample.to_dict()) + '.json', sample.to_dict(),
        schema='hermes.transition_sample.v1')
    record['transition_ref'] = sample_ref.ref
    ref = artifacts.store(owner, 'trace_' + digest(record) + '.json', record)
    ExecutionJournal(owner, agent.session_id).record(ExecutionEventKind.ACTION,
        'adaptive observation captured; semantic verification required', metadata={'trace_ref': ref.ref,
        'operation_fingerprint': record['operation_fingerprint'], 'run_id': record['run_id'],
        'transition_ref': sample_ref.ref})


def candidate_steps(traces):
    """Only semantic actions can enter existing promotion; never arbitrary code."""
    steps = []
    for trace in traces:
        if (
            trace.get('execution_class') == 'opaque_adaptive_execution'
            or trace.get('action') == 'opaque_adaptive_execution'
            or trace.get('tool') in {'browser_console', 'console'}
            or trace['outcome'] != 'executed_unverified'
            or not trace.get('replayable', True)
        ):
            return []
        anchor = trace.get('semantic_anchor') or {}
        action = trace['action']
        if action in {'snapshot', 'extract_items'}:
            continue
        if action not in {'navigate', 'click', 'type', 'press', 'scroll'}:
            return []
        if action != 'navigate' and not anchor:
            return []
        if anchor and (anchor.get('type') not in {'role_name', 'testid', 'text'} or anchor.get('value') == '[REACQUIRE]'):
            return []
        steps.append({'action': action, 'target': anchor.get('value', trace['arguments'].get('url', '')),
            'anchor_type': anchor.get('type', 'selector'), 'fallback_anchors': [anchor] if anchor else [],
            'value': trace['arguments'].get('text', trace['arguments'].get('key', ''))})
    return steps


def learn_verified_trace(memory, traces, outcome, contract, *, scope, fingerprint):
    """Only acceptance-backed observations seed a versioned routine candidate."""
    from workstation.routines import RoutinePromotionService
    steps = candidate_steps(traces)
    if not steps:
        return None
    candidate = RoutinePromotionService(memory).experience_candidate(outcome, contract,
        site=scope.get('host', scope['route']), steps=steps, repeatable=True)
    if candidate:
        candidate.scope = sanitize(scope)
        candidate.capability_fingerprint = fingerprint
        candidate.preconditions = list(scope.get('preconditions', []))
        return memory.update_procedure(candidate)
    return None


def trace_compatibility(traces):
    """Derive exact host/path and schema fingerprint from executed native work."""
    from urllib.parse import urlparse
    from workstation.recipes import recipe_fingerprint
    native = [t for t in traces if t['route'] == 'native_browser']
    urls = [t['arguments'].get('url') for t in native if t['action'] == 'navigate']
    if not urls or not candidate_steps(native):
        return {}
    parsed = [urlparse(url) for url in urls]
    if any(p.scheme not in {'http', 'https'} or p.hostname != parsed[0].hostname or p.path != parsed[0].path for p in parsed):
        return {}
    scope = {'route': 'native_browser', 'host': parsed[0].hostname, 'path_family': parsed[0].path or '/'}
    graph = {'setup': [], 'fan_out': [{'tool': t['tool'], 'args': t['arguments']} for t in native], 'finalize': []}
    return {'scope': scope, 'fingerprint': recipe_fingerprint(graph, scope),
            'preconditions': [json.dumps({'url': urls[0], 'wall_detected': False}, sort_keys=True)]}
