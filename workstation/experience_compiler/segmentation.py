"""Deterministic boundary signals and occurrence-aware sequence alignment."""
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum

from .models import TransitionOutcome
from workstation.recipes import digest


class NodeClass(str, Enum):
    CORE = 'core'
    CONDITIONAL = 'conditional'
    OPTIONAL = 'optional'
    ANOMALOUS = 'anomalous/recovery'


@dataclass
class BoundaryScore:
    index: int
    signals: list[str]
    score: int


@dataclass
class AlignedNode:
    primitive: str
    samples: dict = field(default_factory=dict)
    classification: NodeClass = NodeClass.CORE
    condition: dict = field(default_factory=dict)


def boundaries(samples, recurrence=()):
    scores = []
    for i, sample in enumerate(samples):
        signals = list(sample.operation.boundary_signals)
        if sample.delta.added or sample.delta.changed or sample.delta.removed:
            signals.append('semantic_delta')
        if sample.operation.effect_class not in {'read_only', 'PURE_READ', 'DISCOVERY'}:
            signals.append('effect')
        if sample.verification.verified_predicates:
            signals.append('verification')
        if i and sample.operation.canonical_route != samples[i-1].operation.canonical_route:
            signals.append('backend_transition')
        if sample.state_before.semantic_predicates.get('page_family') != sample.state_after.semantic_predicates.get('page_family'):
            signals.append('page_family_transition')
        if sample.operation.operation_family in recurrence:
            signals.append('recurrence')
        if sample.outcome == TransitionOutcome.INTERRUPTED:
            signals.append('handoff')
        signals = sorted(set(signals))
        scores.append(BoundaryScore(i, signals, len(signals)))
    return scores


def segments(samples):
    """Only verified semantic closure emits a segment; an ACK cannot close it."""
    result, start = [], 0
    for boundary in boundaries(samples):
        sample = samples[boundary.index]
        semantic_change = any(s.delta.added or s.delta.changed or s.delta.removed
                              for s in samples[start:boundary.index+1])
        if ('verification' in boundary.signals and semantic_change
                and sample.outcome == TransitionOutcome.VERIFIED_SUCCESS):
            result.append(samples[start:boundary.index+1])
            start = boundary.index + 1
    return result


def _key(sample):
    op = sample.operation
    anchor = op.target_instance or op.parameters.get('semantic_anchor') or {}
    return (op.primitive, op.canonical_route, op.target_family, op.effect_class, digest(anchor))


def align_traces(traces):
    if not traces or any(len(t) > 128 for t in traces) or len(traces) > 64:
        raise ValueError('alignment requires bounded nonempty traces')
    nodes = [AlignedNode(s.operation.primitive, {0: s}) for s in traces[0]]
    for t_index, trace in enumerate(traces[1:], 1):
        keys = [_key(next(iter(n.samples.values()))) for n in nodes]
        matcher = SequenceMatcher(a=keys, b=[_key(s) for s in trace], autojunk=False)
        updated = []
        for tag, a, b, c, d in matcher.get_opcodes():
            if tag == 'equal':
                for node, sample in zip(nodes[a:b], trace[c:d]):
                    node.samples[t_index] = sample
                    updated.append(node)
            else:
                updated.extend(nodes[a:b])
                updated.extend(AlignedNode(s.operation.primitive, {t_index: s}) for s in trace[c:d])
        nodes = updated
    for node in nodes:
        if any(s.outcome in {TransitionOutcome.FAILED, TransitionOutcome.INTERRUPTED} for s in node.samples.values()):
            node.classification = NodeClass.ANOMALOUS
        elif len(node.samples) == len(traces):
            node.classification = NodeClass.CORE
        else:
            present = set(node.samples)
            candidates = next(iter(node.samples.values())).state_before.semantic_predicates
            for key, val in sorted(candidates.items()):
                if not isinstance(val, bool):
                    continue
                absent_states = [s.state_before.semantic_predicates for i, t in enumerate(traces)
                                 if i not in present for s in t if key in s.state_before.semantic_predicates]
                if (all(s.state_before.semantic_predicates.get(key) == val for s in node.samples.values())
                        and absent_states and all(p[key] != val for p in absent_states)):
                    node.classification, node.condition = NodeClass.CONDITIONAL, {key: val}
                    break
            else:
                node.classification = NodeClass.OPTIONAL if all(s.operation.effect_class in {'read_only', 'PURE_READ', 'DISCOVERY'}
                    for s in node.samples.values()) else NodeClass.ANOMALOUS
    return nodes
