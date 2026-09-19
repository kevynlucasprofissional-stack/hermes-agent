"""Deterministic consolidation into the existing OperationalCapability format."""
from dataclasses import asdict
from collections import Counter
import json
import re

from workstation.operational_capabilities import OperationalCapability, CapabilityLifecycle
from workstation.recipes import digest
from .models import TransitionOutcome, TransitionSample, CausalGrade, normalized
from .segmentation import align_traces, NodeClass, segments
from .generalization import anti_unify, infer_action_model
from .causal import dependency_graph, operational_slice, observational_grade
from .promotion import ExperiencePromotionPolicy, derive_formal_contract

_PRIMITIVES = {'browser_navigate', 'browser_snapshot', 'browser_click', 'browser_type', 'browser_press',
    'browser_scroll', 'browser_extract_items', 'navigate', 'snapshot', 'click', 'fill', 'press', 'scroll',
    'wait', 'fs_write', 'fs_stat', 'fs_read', 'fs_copy', 'fs_move', 'fs_mkdir', 'fs_hash',
    'write_file', 'read_file', 'hash_file', 'stat', 'copy', 'move', 'mkdir', 'process_observe'}
_READ = {'read_only', 'PURE_READ', 'DISCOVERY'}


class ExperienceCompiler:
    def __init__(self, registry, corpus=None):
        self.registry, self.corpus = registry, corpus
        self._attempts, self._dedupes, self._promotions = 0, 0, 0
        self._reductions, self._grades = [], Counter()

    @property
    def metrics(self):
        caps = self.registry.list_capabilities()
        captured = len(self.corpus.refs) if self.corpus else 0
        return {'transition_samples_captured': captured,
            'candidate_yield_rate': (self._attempts - self._dedupes) / captured if captured else None,
            'promotion_rate': self._promotions / self._attempts if self._attempts else 0,
            'dedupe_rate': self._dedupes / self._attempts if self._attempts else 0,
            'operational_slice_reduction': sum(self._reductions)/len(self._reductions) if self._reductions else 0,
            'causal_grade_distribution': dict(Counter(int(c.causal_grade) for c in caps)),
            'replay_pass': sum(e.get('kind') == 'controlled_replay' and e.get('passed') is True for c in caps for e in c.validation_evidence),
            'replay_fail': sum(e.get('kind') == 'controlled_replay' and e.get('passed') is False for c in caps for e in c.validation_evidence),
            'counterexample_refinements': sum(c.learning_metadata.get('counterexample_refinements', 0) for c in caps),
            'drift_quarantine_rate': sum(c.drift_state == 'quarantined' for c in caps)/len(caps) if caps else None,
            'capability_coverage': None, 'operational_novelty_rate': None,
            'atomic_reuse': sum(len(c.dependencies) for c in caps),
            'llm_calls_per_verified_outcome': None}

    def compile(self, traces, failures=()):
        self._attempts += 1
        if len(traces) + len(failures) > 64 or any(len(t) > 128 for t in [*traces, *failures]):
            raise ValueError('compilation budget exceeded')
        traces = [[TransitionSample.from_dict(s.to_dict()) for s in t] for t in traces]
        failures = [[TransitionSample.from_dict(s.to_dict()) for s in t] for t in failures]
        successes = [t for t in traces if t and t[-1].outcome == TransitionOutcome.VERIFIED_SUCCESS]
        failures = [*failures, *[t for t in traces if t and t[-1].outcome == TransitionOutcome.FAILED]]
        if not successes:
            raise ValueError('verified semantic experience required')
        if any(s.outcome in {TransitionOutcome.FAILED, TransitionOutcome.INTERRUPTED} for t in successes for s in t):
            raise ValueError('failed/interrupted path cannot be generalized as successful experience')
        if len(successes) > 64 or any(len(t) > 128 for t in successes):
            raise ValueError('compilation budget exceeded')
        contracts = {digest(sorted({digest((s.operation.canonical_route, s.provenance.runtime,
                                   s.operation.scope, s.operation.effect_class))
                             for s in t if s.operation.effect_class not in _READ})) for t in successes}
        if len(contracts) != 1:
            raise ValueError('incompatible route/runtime/effect scope')
        model = infer_action_model(successes, failures)
        if not model.effects:
            raise ValueError('no stable verified semantic effect')
        slices = [[t[i] for i in operational_slice(dependency_graph(t, model.effects))] for t in successes]
        self._reductions.append(1-sum(map(len, slices))/sum(map(len, successes)))
        nodes = align_traces(slices)
        if any(n.classification == NodeClass.ANOMALOUS and any(s.operation.effect_class not in _READ
                for s in n.samples.values()) for n in nodes):
            raise ValueError('unexplained mutable branch requires reasoning')
        nodes = [n for n in nodes if n.classification not in {NodeClass.OPTIONAL, NodeClass.ANOMALOUS}]
        examples = []
        for t_index in range(len(successes)):
            steps = []
            for i, node in enumerate(nodes):
                sample = node.samples.get(t_index) or next(iter(node.samples.values()))
                op = sample.operation
                if op.primitive not in _PRIMITIVES:
                    raise ValueError('unsupported trusted primitive: ' + op.primitive)
                args = normalized(op.parameters)
                if re.search(r'\$(?:item|inputs|steps|deps|prev|context)\.', json.dumps(args)):
                    raise ValueError('unbound observed parameter requires owner binding evidence')
                anchor = args.pop('semantic_anchor', None) or op.target_instance
                if op.primitive in {'browser_click', 'browser_type', 'click', 'fill'}:
                    if not anchor or anchor.get('type') not in {'testid', 'role_name', 'text'}:
                        raise ValueError('reacquirable semantic anchor required')
                    args['anchor'] = anchor
                step = {'id': 'learned_' + str(i), 'primitive': op.primitive, 'args': args}
                if node.condition:
                    step['when'] = node.condition
                if i == len(nodes)-1:
                    step['verifier'] = True
                steps.append(step)
            examples.append({'steps': steps})
        generalized = anti_unify(examples)
        flat = [s for t in successes for s in t]
        effects = {s.operation.effect_class for s in flat}
        effect = 'external_mutation' if 'external_mutation' in effects else 'state_mutation' if effects - _READ else 'read_only'
        routes = {s.operation.canonical_route for s in flat}
        route = next(iter(routes)) if len(routes) == 1 else 'composite'
        scopes = {s.operation.canonical_route: s.operation.scope for s in flat}
        scope = next(iter(scopes.values())) if len(scopes) == 1 else {'backends': scopes}
        evidence_samples = [*flat, *[s for t in failures for s in t]]
        taint = sorted({x for s in evidence_samples for x in s.provenance.taint})
        trust = 'trusted_runtime' if all(s.provenance.trust_class == 'trusted_runtime' for s in evidence_samples) else 'untrusted'
        preconditions = [{'type': 'semantic_predicate', 'key': k, 'expected': v} for k, v in sorted(model.preconditions.items())]
        postconditions = [{'type': 'semantic_predicate', 'key': k, 'expected': v} for k, v in sorted(model.effects.items())]
        semantic = digest({'route': route, 'scope': scope, 'effect': effect,
            'families': sorted({s.operation.operation_family for s in flat}), 'effects': model.effects,
            'targets': sorted({s.operation.target_family for s in flat}), 'version': 1})
        compatible = digest({'implementation': generalized.template, 'schema': generalized.schema,
            'relations': generalized.relations, 'preconditions': preconditions, 'postconditions': postconditions,
            'runtime': sorted({s.provenance.runtime for s in flat}), 'scope': scope, 'effect': effect})
        # Exact semantic + compatibility deduplication; similarity never admits execution.
        for existing in self.registry.list_capabilities():
            if existing.semantic_fingerprint == semantic and existing.compatibility_fingerprint == compatible:
                self._dedupes += 1
                if existing.lifecycle == CapabilityLifecycle.PROMOTED:
                    if model.unresolved_counterexamples:
                        return self.registry.record_drift(existing.id, 'new unresolved experience counterexample', version=existing.version)
                    return existing
                existing.causal_grade = max(existing.causal_grade,
                    observational_grade(successes, failure_discriminated=model.failure_discriminated))
                existing.trust_class = 'trusted_runtime' if existing.trust_class == trust == 'trusted_runtime' else 'untrusted'
                existing.taint = sorted(set(existing.taint) | set(taint))
                existing.source_trace_refs = sorted(set(existing.source_trace_refs) |
                    {s.provenance.sample_ref for s in evidence_samples if s.provenance.sample_ref})
                metadata = existing.learning_metadata
                metadata['run_ids'] = sorted(set(metadata.get('run_ids', [])) |
                    {s.provenance.run_id for s in flat if s.provenance.run_id})
                metadata['authority_origins'] = sorted(set(metadata.get('authority_origins', [])) |
                    {s.provenance.authority_origin.value for s in evidence_samples})
                metadata['parameterization_quality'] = len(metadata['run_ids']) >= 2
                metadata['unresolved_counterexamples'] = max(metadata.get('unresolved_counterexamples', 0), model.unresolved_counterexamples)
                metadata['drift_rate'] = max(metadata.get('drift_rate', 0), len(failures)/(len(successes)+len(failures)))
                metadata['provenance_complete'] = metadata.get('provenance_complete', False) and all(
                    s.provenance.task_id and s.provenance.run_id and s.provenance.operation_id for s in evidence_samples)
                metadata['evidence_strength'] = min(metadata.get('evidence_strength', 0),
                    min(int(t[-1].verification.evidence_strength) for t in successes))
                metadata['sample_refs'] = sorted(set(metadata.get('sample_refs', [])) |
                    {s.to_dict()['sample_id'] for s in evidence_samples})
                return self.registry.register(existing)
        grade = observational_grade(successes, failure_discriminated=model.failure_discriminated)
        self._grades[int(grade)] += 1
        raw_size = sum(len(json.dumps([s.to_dict() for s in t])) for t in successes)
        model_size = len(json.dumps(generalized.template)) + len(json.dumps(generalized.schema))
        utility = raw_size - model_size - len(successes)*64 - 256
        if utility <= 0:
            raise ValueError('nonpositive reuse/compression utility')
        cap = OperationalCapability('experience_' + compatible[:24], 'Verified ' + nodes[-1].primitive,
            input_schema=generalized.schema, effect=effect, route=route, scope=scope,
            preconditions=preconditions, postconditions=postconditions,
            verifier_contract={'effects': model.effects, 'minimum_evidence': min(int(t[-1].verification.evidence_strength) for t in successes)},
            implementation=generalized.template, provenance={'source': 'experience_compiler',
                'origins': [asdict(s.provenance) for s in evidence_samples]}, semantic_fingerprint=semantic,
            compatibility_fingerprint=compatible, causal_grade=grade, trust_class=trust, taint=taint,
            source_trace_refs=sorted({r for s in evidence_samples for r in s.verification.evidence_refs} |
                {s.provenance.sample_ref for s in evidence_samples if s.provenance.sample_ref}),
            learning_metadata={'effects': model.effects, 'preconditions': model.preconditions,
                'relations': generalized.relations, 'bindings': generalized.bindings,
                'semantic_closure': True, 'parameterization_quality': len(successes) >= 2,
                'evidence_strength': min(int(t[-1].verification.evidence_strength) for t in successes),
                'run_ids': sorted({s.provenance.run_id for s in flat if s.provenance.run_id}),
                'authority_origins': sorted({s.provenance.authority_origin.value for s in evidence_samples}),
                'provenance_complete': all(s.provenance.task_id and s.provenance.run_id and s.provenance.operation_id for s in evidence_samples),
                'utility': utility, 'drift_rate': len(failures)/(len(successes)+len(failures)),
                'unresolved_counterexamples': model.unresolved_counterexamples,
                'node_classes': [n.classification.value for n in nodes],
                'sample_refs': [s.to_dict()['sample_id'] for s in evidence_samples],
                'operation_families': sorted({s.operation.operation_family for s in flat if s.operation.operation_family}),
                'target_families': sorted({s.operation.target_family for s in flat if s.operation.target_family})})
        fc = derive_formal_contract(cap)
        if fc is not None:
            cap.formal_contract = fc
            cap.family_id = f"{fc.operation_family}:{fc.target_family}"
        return self.registry.register(cap)

    def mine(self):
        if self.corpus is None:
            return []
        groups = {}
        def family(segment):
            terminal = next((s for s in reversed(segment) if s.operation.effect_class not in _READ), segment[-1])
            return digest((terminal.operation.operation_family, terminal.operation.target_family,
                terminal.operation.canonical_route, terminal.operation.scope, terminal.provenance.runtime))
        for trace in self.corpus.traces():
            for segment in segments(trace):
                groups.setdefault(family(segment), [[], []])[0].append(segment)
            for index, sample in enumerate(trace):
                if sample.outcome in {TransitionOutcome.FAILED, TransitionOutcome.INTERRUPTED}:
                    negative = trace[:index+1]
                    groups.setdefault(family(negative), [[], []])[1].append(negative)
                    break
        result = []
        for traces, failures in groups.values():
            try:
                result.append(self.compile(traces, failures))
            except ValueError:
                continue  # Insufficient/unexplained evidence stays in corpus, not a procedure.
        return result

    def promote(self, cap):
        admission = ExperiencePromotionPolicy().evaluate(cap)
        if not admission.admitted:
            return admission
        if cap.formal_contract is None:
            fc = derive_formal_contract(cap)
            if fc is not None:
                cap.formal_contract = fc
                cap.family_id = f"{fc.operation_family}:{fc.target_family}"
        self.registry.register(cap)
        promoted = self.registry.promote(cap.id, version=cap.version)
        cap.lifecycle = promoted.lifecycle
        self._promotions += 1
        return admission
