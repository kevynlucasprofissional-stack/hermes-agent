"""Observational ontology; OperationalCapability remains the executable object."""
from dataclasses import asdict, dataclass, field
from enum import Enum, IntEnum
import json
import re
from typing import Any

from workstation.execution_policy import EvidenceStrength
from workstation.recipes import sanitize, digest


def normalized(value):
    """Remove live handles and secrets before hashing or persisting observations."""
    value = sanitize(value)
    if isinstance(value, dict):
        return {k: normalized(v) for k, v in sorted(value.items())
                if re.sub(r'[^a-z]', '', k.lower()) not in {
                    'ref', 'nodeid', 'tabid', 'webcontentsid', 'timestamp', 'scroll',
                    'reasoning', 'pagetext', 'prose'}}
    if isinstance(value, (list, tuple)):
        return [normalized(v) for v in value[:128]]
    if isinstance(value, str):
        return re.sub(r'@e\d+\b', '[REACQUIRE]', value)[:2048]
    return value


class TransitionOutcome(str, Enum):
    VERIFIED_SUCCESS = 'verified_success'
    FAILED = 'failed'
    UNCERTAIN = 'uncertain'
    INTERRUPTED = 'interrupted'


class AuthorityOrigin(str, Enum):
    SYSTEM = 'system'
    USER = 'user'
    ENVIRONMENT = 'environment'
    PAGE_PROVIDED = 'page_provided'


class CausalGrade(IntEnum):
    OBSERVED_ONCE = 0
    RECURRENT_SUCCESS = 1
    FAILURE_DISCRIMINATED = 2
    REPLAY_VALIDATED = 3
    ABLATION_SUPPORTED = 4
    CROSS_CONTEXT_INVARIANT = 5


@dataclass
class SemanticState:
    artifact_ref: str | None = None
    semantic_predicates: dict[str, Any] = field(default_factory=dict)


@dataclass
class StateDelta:
    added: dict[str, Any] = field(default_factory=dict)
    removed: dict[str, Any] = field(default_factory=dict)
    changed: dict[str, list[Any]] = field(default_factory=dict)

    @classmethod
    def between(cls, before, after):
        a, b = before.semantic_predicates, after.semantic_predicates
        return cls({k: b[k] for k in sorted(b.keys() - a.keys())},
                   {k: a[k] for k in sorted(a.keys() - b.keys())},
                   {k: [a[k], b[k]] for k in sorted(a.keys() & b.keys()) if a[k] != b[k]})


@dataclass
class Operation:
    primitive: str = ''
    canonical_route: str = ''
    target_instance: dict = field(default_factory=dict)
    target_family: str = ''
    operation_family: str = ''
    parameters: dict = field(default_factory=dict)
    effect_class: str = 'unknown'
    scope: dict = field(default_factory=dict)
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    boundary_signals: list[str] = field(default_factory=list)


@dataclass
class Verification:
    evidence_strength: EvidenceStrength = EvidenceStrength.TOOL_ACK_ONLY
    verifier: str = ''
    verified_predicates: dict = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    status: str = 'INCONCLUSIVE'
    verifier_fingerprint: str = ''
    observer: str = ''
    source_kind: str = 'unknown'
    resource_binding: dict = field(default_factory=dict)
    extractor_path: str = ''
    relation: str = 'EXACT'
    canonicalizer_id: str = ''
    canonicalizer_version: str = ''
    trust_class: str = 'untrusted'
    observer_failure_domain: str = ''
    resource_version: str = ''
    observed_at: str = ''
    validation_receipts: list[dict] = field(default_factory=list)


@dataclass
class Provenance:
    task_id: str | None = None
    run_id: str | None = None
    operation_id: str | None = None
    runtime: str = ''
    source: str = 'adaptive_trace'
    authority_origin: AuthorityOrigin = AuthorityOrigin.ENVIRONMENT
    trust_class: str = 'untrusted'
    taint: list[str] = field(default_factory=list)
    operation_index: int | None = None
    sample_ref: str | None = None
    authority_ref: str | None = None
    authority_scope: dict | None = None


@dataclass
class CapabilityInvocation:
    invocation_id: str = ''
    capability_id: str = ''
    capability_version: str = '1.0.0'
    run_id: str = ''
    task_id: str | None = None
    operation_id: str | None = None
    inputs: dict = field(default_factory=dict)
    state_before: dict = field(default_factory=dict)
    state_after: dict = field(default_factory=dict)
    delta: dict = field(default_factory=dict)
    status: str = 'COMMITTED'
    verified: bool = False
    verifier_status: str = 'INCONCLUSIVE'
    verifier_fingerprint: str = ''
    verification_evidence_refs: list[str] = field(default_factory=list)
    covered_predicates: list[str] = field(default_factory=list)
    freshness_satisfied: bool = False
    verification_reason: str = ''
    authority_scope: dict | None = None
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        d = normalized(asdict(self))
        d['timestamp'] = self.timestamp
        return d

    @classmethod
    def from_dict(cls, data: dict) -> 'CapabilityInvocation':
        ts = data.get('timestamp', 0.0)
        clean = normalized(data)
        clean['timestamp'] = ts
        return cls(**clean)


@dataclass
class Metrics:
    duration_ms: float | None = None
    provider_usage: dict = field(default_factory=dict)


@dataclass
class TransitionSample:
    sample_id: str = ''
    state_before: SemanticState = field(default_factory=SemanticState)
    operation: Operation = field(default_factory=Operation)
    state_after: SemanticState = field(default_factory=SemanticState)
    delta: StateDelta = field(default_factory=StateDelta)
    verification: Verification = field(default_factory=Verification)
    outcome: TransitionOutcome = TransitionOutcome.UNCERTAIN
    provenance: Provenance = field(default_factory=Provenance)
    metrics: Metrics = field(default_factory=Metrics)
    raw_result_ref: str | None = None

    def to_dict(self):
        body = normalized(asdict(self))
        body['sample_id'] = self.sample_id or 'transition_' + digest(body)[:24]
        return body

    def to_json(self):
        return json.dumps(self.to_dict(), sort_keys=True, separators=(',', ':'))

    @classmethod
    def from_dict(cls, body):
        b = normalized(body)
        verification = b.get('verification', {})
        verification['evidence_strength'] = EvidenceStrength(verification.get('evidence_strength', 0))
        provenance = b.get('provenance', {})
        provenance['authority_origin'] = AuthorityOrigin(provenance.get('authority_origin', 'environment'))
        return cls(b.get('sample_id', ''), SemanticState(**b.get('state_before', {})),
                   Operation(**b.get('operation', {})), SemanticState(**b.get('state_after', {})),
                   StateDelta(**b.get('delta', {})), Verification(**verification),
                   TransitionOutcome(b.get('outcome', 'uncertain')), Provenance(**provenance),
                   Metrics(**b.get('metrics', {})), raw_result_ref=b.get('raw_result_ref'))
