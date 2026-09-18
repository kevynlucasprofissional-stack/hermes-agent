"""Dependency support is observational; replay/ablation are separate interventions."""
from dataclasses import dataclass
from copy import deepcopy
import time

from .models import CausalGrade


@dataclass(frozen=True)
class DependencyEdge:
    source: int
    target: int
    kind: str


@dataclass
class DependencyGraph:
    nodes: list
    edges: list[DependencyEdge]
    roots: list[int]


def dependency_graph(trace, postcondition):
    if not trace or len(trace) > 128:
        raise ValueError('bounded trace required')
    edges, producers, operations = [], {}, {}
    latest_target, latest_effect = None, None
    for i, sample in enumerate(trace):
        op = sample.operation
        for kind, dependencies in op.dependencies.items():
            if kind not in {'data', 'control', 'target_resolution', 'effect', 'verification'}:
                raise ValueError('unknown dependency type')
            for dependency in dependencies:
                if dependency not in operations:
                    raise ValueError('unresolved dependency')
                edges.append(DependencyEdge(operations[dependency], i, kind))
        for key, value in sample.state_before.semantic_predicates.items():
            if key in producers and producers[key][1] == value:
                edges.append(DependencyEdge(producers[key][0], i, 'control'))
        mutating = op.effect_class not in {'read_only', 'PURE_READ', 'DISCOVERY'}
        if mutating:
            if latest_target is not None:
                edges.append(DependencyEdge(latest_target, i, 'target_resolution'))
            if latest_effect is not None:
                edges.append(DependencyEdge(latest_effect, i, 'effect'))
            latest_effect = i
        if op.primitive in {'navigate', 'browser_navigate'}:
            latest_target = i
        for key, value in {**sample.delta.added, **{k: v[1] for k, v in sample.delta.changed.items()}}.items():
            producers[key] = (i, value)
        operations[sample.provenance.operation_id or op.primitive] = i
    final = len(trace)-1
    for key, value in postcondition.items():
        if key in producers and producers[key][1] == value and producers[key][0] != final:
            edges.append(DependencyEdge(producers[key][0], final, 'verification'))
    if latest_effect is not None and latest_effect != final:
        edges.append(DependencyEdge(latest_effect, final, 'verification'))
    return DependencyGraph(trace, sorted(set(edges), key=lambda e: (e.target, e.source, e.kind)), [final])


def operational_slice(graph):
    kept, pending = set(graph.roots), list(graph.roots)
    while pending:
        target = pending.pop()
        for edge in graph.edges:
            if edge.target == target and edge.source not in kept:
                kept.add(edge.source)
                pending.append(edge.source)
    return sorted(kept)


def observational_grade(traces, *, failure_discriminated=False):
    if failure_discriminated:
        return CausalGrade.FAILURE_DISCRIMINATED
    runs = {s.provenance.run_id for t in traces for s in t if s.provenance.run_id}
    return CausalGrade.RECURRENT_SUCCESS if len(traces) > 1 else CausalGrade.OBSERVED_ONCE


@dataclass(frozen=True)
class SafeEnvironment:
    """Owner-supplied fixture with reset-per-attempt runner, never model input.

    Runner must honor the monotonic deadline and reconstruct isolated state for
    every attempt. Policy admission is mandatory even inside a test fixture.
    """
    kind: str
    identity: str
    policy_admission: object
    resets_each_attempt: bool = True

    def admit(self, capability, action):
        safe_kinds = {'temp_filesystem', 'test_fixture', 'sandbox', 'test_repository', 'read_only'}
        if (self.kind not in safe_kinds or not self.identity or not self.resets_each_attempt
                or capability.effect not in {'read_only', 'state_mutation', 'pure_read', 'mutation', 'PURE_READ', 'DISCOVERY', 'MUTATION'}
                or capability.learning_metadata.get('risk', 'ordinary') != 'ordinary'
                or capability.scope.get('external')
                or not callable(self.policy_admission)
                or not self.policy_admission(capability, action)):
            raise PermissionError('unsafe or policy-denied causal intervention')


def _verified(capability, result):
    effects = capability.learning_metadata.get('effects', {})
    return (isinstance(result, dict) and result.get('passed') is True
            and result.get('evidence_strength', 0) >= 1 and bool(result.get('evidence_refs'))
            and bool(effects) and all(k in result.get('predicates', {}) and result['predicates'][k] == v
                                     for k, v in effects.items()))


def controlled_replay(capability, environment, runner, *, deadline_seconds=10):
    environment.admit(capability, 'replay')
    result_cap = deepcopy(capability)
    deadline = time.monotonic() + min(60, max(0, deadline_seconds))
    result = runner(deepcopy(capability.implementation['steps']), deadline)
    passed = time.monotonic() <= deadline and _verified(capability, result)
    result_cap.validation_evidence.append({'kind': 'controlled_replay', 'environment': environment.identity,
        'passed': passed, 'result': result, 'compatibility_fingerprint': capability.compatibility_fingerprint})
    if passed:
        result_cap.causal_grade = max(result_cap.causal_grade, CausalGrade.REPLAY_VALIDATED)
    else:
        # A failed intervention invalidates earlier replay admission of this revision.
        result_cap.causal_grade = min(result_cap.causal_grade, CausalGrade.FAILURE_DISCRIMINATED)
    return result_cap


def reduce_slice(capability, environment, runner, *, max_attempts=16, deadline_seconds=10):
    environment.admit(capability, 'ablation')
    cap = deepcopy(capability)
    deadline = time.monotonic() + min(60, max(0, deadline_seconds))
    attempts, steps, removed = 0, deepcopy(cap.implementation['steps']), 0
    evidence = []
    # Deterministic one-deletion ddmin baseline; verifier nodes stay pinned.
    index = 0
    while index < len(steps)-1 and attempts < min(max_attempts, 128) and time.monotonic() < deadline:
        if steps[index].get('verifier'):
            index += 1
            continue
        trial = steps[:index] + steps[index+1:]
        result = runner(deepcopy(trial), deadline)
        attempts += 1
        passed = time.monotonic() <= deadline and _verified(cap, result)
        evidence.append({'removed': steps[index].get('id', index), 'passed': passed, 'result': result})
        if passed:
            steps = trial
            removed += 1
        else:
            index += 1
    cap.implementation['steps'] = steps
    if removed:
        from workstation.recipes import digest
        from workstation.operational_capabilities import CapabilityLifecycle
        previous = cap.compatibility_fingerprint
        cap.compatibility_fingerprint = digest({'previous': previous, 'reduced_steps': steps})
        if cap.lifecycle == CapabilityLifecycle.PROMOTED:
            parts = [int(p) for p in cap.version.split('.')]
            parts[-1] += 1
            cap.version = '.'.join(map(str, parts))
            cap.lifecycle = CapabilityLifecycle.DISCOVERED
        cap.validation_evidence = [e for e in cap.validation_evidence if e.get('kind') != 'controlled_replay']
        final_result = next(e['result'] for e in reversed(evidence) if e['passed'])
        cap.validation_evidence.append({'kind': 'controlled_replay', 'environment': environment.identity,
            'passed': True, 'result': final_result, 'compatibility_fingerprint': cap.compatibility_fingerprint,
            'source': 'safe_ablation_readback'})
    cap.validation_evidence.append({'kind': 'safe_ablation', 'attempts': attempts, 'removed': removed,
                                   'environment': environment.identity, 'trials': evidence})
    if attempts and cap.causal_grade >= CausalGrade.REPLAY_VALIDATED:
        cap.causal_grade = CausalGrade.ABLATION_SUPPORTED
    return cap


def validate_cross_context(capability, interventions):
    """Owner-supplied materially distinct fixtures; passive diversity cannot grant C5."""
    interventions = list(interventions)
    if not 2 <= len(interventions) <= 8 or len({env.identity for env, _ in interventions}) != len(interventions):
        raise ValueError('distinct bounded controlled contexts required')
    cap = deepcopy(capability)
    passed = True
    for environment, runner in interventions:
        cap = controlled_replay(cap, environment, runner)
        passed = passed and cap.validation_evidence[-1]['passed']
    if passed:
        cap.causal_grade = CausalGrade.CROSS_CONTEXT_INVARIANT
    else:
        cap.causal_grade = min(cap.causal_grade, CausalGrade.FAILURE_DISCRIMINATED)
    return cap


def refine_counterexample(capability, counterexample, positive_states):
    from .generalization import _intersection
    from workstation.operational_capabilities import CapabilityLifecycle
    cap = deepcopy(capability)
    common = _intersection(positive_states)
    refinements = {k: v for k, v in common.items() if k in counterexample and counterexample[k] != v}
    if not refinements:
        raise ValueError('counterexample not discriminated; adaptive reasoning required')
    parts = [int(p) for p in cap.version.split('.')]
    parts[-1] += 1
    cap.version = '.'.join(map(str, parts))
    cap.lifecycle = CapabilityLifecycle.DISCOVERED
    cap.causal_grade = CausalGrade.FAILURE_DISCRIMINATED
    cap.drift_state = 'healthy'
    cap.learning_metadata['preconditions'] = {**cap.learning_metadata.get('preconditions', {}), **refinements}
    cap.preconditions = [{'type': 'semantic_predicate', 'key': k, 'expected': v}
                         for k, v in sorted(cap.learning_metadata['preconditions'].items())]
    cap.learning_metadata['refined_from'] = capability.version
    cap.learning_metadata['counterexample_refinements'] = cap.learning_metadata.get('counterexample_refinements', 0) + 1
    cap.validation_evidence = []
    cap.promotion_policy_version = ''
    from workstation.recipes import digest
    cap.compatibility_fingerprint = digest({'previous': capability.compatibility_fingerprint,
                                          'preconditions': cap.preconditions, 'version': cap.version})
    return cap
