"""Typed, deterministic verification contracts and evaluation.

This module owns no persistence, scheduling, registry, or observation lifecycle.  It
only answers whether supplied evidence satisfies an owner-declared proof contract.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from workstation.execution_policy import EvidenceStrength


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"
    CONFLICT = "CONFLICT"
    STALE = "STALE"


class VerificationLifecycle(str, Enum):
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    QUARANTINED = "QUARANTINED"


class VerificationRelation(str, Enum):
    EXACT = "EXACT"
    STRUCTURAL_JSON = "STRUCTURAL_JSON"
    ORDERED_SEQUENCE = "ORDERED_SEQUENCE"
    SET_EQUAL = "SET_EQUAL"
    MULTISET_EQUAL = "MULTISET_EQUAL"
    NUMERIC_TOLERANCE = "NUMERIC_TOLERANCE"
    DATETIME_INSTANT = "DATETIME_INSTANT"
    URL_CANONICAL = "URL_CANONICAL"
    OWNER_CANONICAL = "OWNER_CANONICAL"


@dataclass(frozen=True)
class VerificationContract:
    schema_version: str = "1.0.0"
    covered_predicates: tuple[str, ...] = ()
    effect_classes: tuple[str, ...] = ()
    observer: str = ""
    source_kind: str = "unknown"
    resource_binding: dict[str, Any] = field(default_factory=dict)
    extractor_path: str = ""
    relation: VerificationRelation = VerificationRelation.EXACT
    relation_parameters: dict[str, Any] = field(default_factory=dict)
    canonicalizer_id: str = ""
    canonicalizer_version: str = ""
    minimum_evidence: EvidenceStrength = EvidenceStrength.TOOL_ACK_ONLY
    allowed_trust: tuple[str, ...] = ()
    mutation_failure_domains: tuple[str, ...] = ()
    allowed_observer_failure_domains: tuple[str, ...] = ()
    require_distinct_failure_domain: bool = False
    temporal_basis: str = "none"
    max_age_seconds: float | None = None
    require_read_after_write: bool = False
    settling_policy: dict[str, Any] = field(default_factory=dict)
    disagreement_policy: str = "conflict"
    lifecycle: VerificationLifecycle = VerificationLifecycle.CANDIDATE
    validation_evidence_refs: tuple[str, ...] = ()
    validation_receipts: tuple[dict[str, Any], ...] = ()
    ack_is_terminal_evidence: bool = False
    transition_claim: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["relation"] = self.relation.value
        data["minimum_evidence"] = int(self.minimum_evidence)
        data["lifecycle"] = self.lifecycle.value
        data["fingerprint"] = self.fingerprint()
        return data

    def _fingerprint_payload(self) -> dict[str, Any]:
        data = asdict(self)
        data["relation"] = self.relation.value
        data["minimum_evidence"] = int(self.minimum_evidence)
        data["lifecycle"] = self.lifecycle.value
        return data

    def fingerprint(self) -> str:
        raw = json.dumps(self._fingerprint_payload(), sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "VerificationContract":
        raw = dict(data or {})
        typed = bool(raw.get("schema_version") and raw.get("relation"))
        covered = raw.get("covered_predicates", raw.get("predicates", ()))
        effects = raw.get("effect_classes", raw.get("effects", ()))
        if isinstance(effects, dict):
            effects = tuple(str(k) for k in effects)
        lifecycle = raw.get("lifecycle", "CANDIDATE") if typed else "CANDIDATE"
        return cls(
            schema_version=str(raw.get("schema_version", "legacy-0")),
            covered_predicates=tuple(map(str, covered or ())),
            effect_classes=tuple(map(str, effects or ())),
            observer=str(raw.get("observer", raw.get("tool", raw.get("capability", "")))),
            source_kind=str(raw.get("source_kind", raw.get("source", "unknown"))),
            resource_binding=dict(raw.get("resource_binding", raw.get("binding", {})) or {}),
            extractor_path=str(raw.get("extractor_path", raw.get("path", ""))),
            relation=VerificationRelation(str(raw.get("relation", "EXACT")).upper()),
            relation_parameters=dict(raw.get("relation_parameters", raw.get("parameters", {})) or {}),
            canonicalizer_id=str(raw.get("canonicalizer_id", "")),
            canonicalizer_version=str(raw.get("canonicalizer_version", "")),
            minimum_evidence=EvidenceStrength(int(raw.get("minimum_evidence", 0))),
            allowed_trust=tuple(map(str, raw.get("allowed_trust", raw.get("trust_requirement", ())) or ())),
            mutation_failure_domains=tuple(map(str, raw.get("mutation_failure_domains", ()) or ())),
            allowed_observer_failure_domains=tuple(map(str, raw.get("allowed_observer_failure_domains", ()) or ())),
            require_distinct_failure_domain=bool(raw.get("require_distinct_failure_domain", False)),
            temporal_basis=str(raw.get("temporal_basis", "none")),
            max_age_seconds=raw.get("max_age_seconds"),
            require_read_after_write=bool(raw.get("require_read_after_write", False)),
            settling_policy=dict(raw.get("settling_policy", {}) or {}),
            disagreement_policy=str(raw.get("disagreement_policy", "conflict")),
            lifecycle=VerificationLifecycle(str(lifecycle).upper()),
            validation_evidence_refs=tuple(map(str, raw.get("validation_evidence_refs", ()) or ())),
            validation_receipts=tuple(dict(v) for v in raw.get("validation_receipts", ()) or ()),
            ack_is_terminal_evidence=bool(raw.get("ack_is_terminal_evidence", False)),
            transition_claim=bool(raw.get("transition_claim", False)),
        )

    def is_sufficient_for(
        self, *, required_predicates: set[str] | None = None,
        mutation: bool = False, temporal_required: bool = False,
    ) -> tuple[bool, tuple[str, ...]]:
        reasons: list[str] = []
        if self.lifecycle != VerificationLifecycle.VALIDATED:
            reasons.append("verifier_not_validated")
        if not self.observer:
            reasons.append("observer_unknown")
        if self.source_kind in {"", "unknown", "executor_self_report"}:
            reasons.append("source_unknown")
        if mutation and self.minimum_evidence < EvidenceStrength.SEMANTIC_PERSISTED_READBACK:
            reasons.append("persisted_evidence_insufficient")
        if mutation and not self.allowed_trust:
            reasons.append("trust_requirement_unknown")
        missing = set(required_predicates or ()) - set(self.covered_predicates)
        if missing:
            reasons.append("predicate_coverage_insufficient")
        if temporal_required and self.temporal_basis == "none":
            reasons.append("temporal_basis_missing")
        if self.relation == VerificationRelation.OWNER_CANONICAL and (
            not self.canonicalizer_id or not self.canonicalizer_version
        ):
            reasons.append("owner_canonicalizer_unversioned")
        return not reasons, tuple(reasons)


@dataclass(frozen=True)
class VerificationEvidence:
    evidence_id: str
    observer: str
    source_kind: str
    value: Any
    evidence_strength: EvidenceStrength = EvidenceStrength.TOOL_ACK_ONLY
    trust_class: str = "untrusted"
    observer_failure_domain: str = ""
    resource_id: str = ""
    resource_version: str = ""
    observed_at: str = ""
    read_after_write: bool = False
    covered_predicates: tuple[str, ...] = ()
    artifact_ref: str = ""
    verifier_fingerprint: str = ""
    task_id: str = ""
    run_id: str = ""
    operation_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence_strength"] = int(self.evidence_strength)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerificationEvidence":
        raw = dict(data)
        raw["evidence_strength"] = EvidenceStrength(int(raw.get("evidence_strength", 0)))
        raw["covered_predicates"] = tuple(raw.get("covered_predicates", ()))
        return cls(**raw)


@dataclass(frozen=True)
class VerificationResult:
    status: VerificationStatus
    verifier_fingerprint: str = ""
    evidence_refs: tuple[str, ...] = ()
    covered_predicates: tuple[str, ...] = ()
    freshness_satisfied: bool = False
    relation_satisfied: bool = False
    source_admissible: bool = False
    fault_domain_admissible: bool = False
    transition_proven: bool = False
    reason: str = ""
    evaluated_at: str = ""

    @property
    def verified(self) -> bool:
        return self.status == VerificationStatus.VERIFIED

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["accepted"] = self.verified
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerificationResult":
        raw = dict(data)
        raw.pop("accepted", None)
        raw["status"] = VerificationStatus(str(raw.get("status", "INCONCLUSIVE")).upper())
        raw["evidence_refs"] = tuple(raw.get("evidence_refs", ()))
        raw["covered_predicates"] = tuple(raw.get("covered_predicates", ()))
        return cls(**raw)


_OWNER_CANONICALIZERS: dict[tuple[str, str], Callable[[Any], Any]] = {}


def register_owner_canonicalizer(owner_id: str, version: str, fn: Callable[[Any], Any]) -> None:
    if not owner_id or not version or not callable(fn):
        raise ValueError("owner canonicalizer requires stable id, version, and callable")
    _OWNER_CANONICALIZERS[(owner_id, version)] = fn


def _json_value(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _instant(value: Any) -> datetime:
    text = str(value).replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def relation_matches(contract: VerificationContract, expected: Any, observed: Any) -> bool:
    relation = contract.relation
    if relation == VerificationRelation.EXACT:
        return type(expected) is type(observed) and expected == observed
    if relation == VerificationRelation.STRUCTURAL_JSON:
        return _json_value(expected) == _json_value(observed)
    if relation == VerificationRelation.ORDERED_SEQUENCE:
        return isinstance(expected, (list, tuple)) and isinstance(observed, (list, tuple)) and list(expected) == list(observed)
    if relation == VerificationRelation.SET_EQUAL:
        return set(expected) == set(observed)
    if relation == VerificationRelation.MULTISET_EQUAL:
        return Counter(expected) == Counter(observed)
    if relation == VerificationRelation.NUMERIC_TOLERANCE:
        bound = contract.relation_parameters.get("absolute_tolerance")
        return bound is not None and float(bound) >= 0 and abs(float(expected) - float(observed)) <= float(bound)
    if relation == VerificationRelation.DATETIME_INSTANT:
        return _instant(expected).astimezone(timezone.utc) == _instant(observed).astimezone(timezone.utc)
    if relation == VerificationRelation.URL_CANONICAL:
        def canonical_url(value: Any) -> tuple[Any, ...]:
            p = urlsplit(str(value))
            path = p.path or "/"
            if contract.relation_parameters.get("strip_trailing_slash", False) and path != "/":
                path = path.rstrip("/")
            query = urlencode(sorted(parse_qsl(p.query, keep_blank_values=True)))
            return (p.scheme.lower(), p.hostname.lower() if p.hostname else "", p.port, path, query, "" if contract.relation_parameters.get("ignore_fragment") else p.fragment)
        return canonical_url(expected) == canonical_url(observed)
    if relation == VerificationRelation.OWNER_CANONICAL:
        fn = _OWNER_CANONICALIZERS.get((contract.canonicalizer_id, contract.canonicalizer_version))
        return bool(fn) and fn(expected) == fn(observed)
    return False


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return _instant(value).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def evaluate_verification(
    contract: VerificationContract | dict[str, Any], expected: Any,
    evidence: list[VerificationEvidence | dict[str, Any]], *,
    required_predicates: set[str] | None = None,
    mutation_failure_domains: set[str] | None = None,
    mutation_observed_at: str = "", now: datetime | None = None,
    transition_required: bool | None = None,
    expected_operation_id: str | None = None,
    expected_run_id: str | None = None,
    expected_task_id: str | None = None,
) -> VerificationResult:
    c = contract if isinstance(contract, VerificationContract) else VerificationContract.from_dict(contract)
    evs = [e if isinstance(e, VerificationEvidence) else VerificationEvidence.from_dict(e) for e in evidence]
    stamp = (now or datetime.now(timezone.utc)).isoformat()
    refs = tuple(e.artifact_ref or e.evidence_id for e in evs)
    required = set(required_predicates or c.covered_predicates)
    sufficient, reasons = c.is_sufficient_for(required_predicates=required, mutation=bool(mutation_failure_domains), temporal_required=(c.temporal_basis != "none"))
    if not sufficient:
        return VerificationResult(VerificationStatus.INCONCLUSIVE, c.fingerprint(), refs, reason=",".join(reasons), evaluated_at=stamp)
    if not evs:
        return VerificationResult(VerificationStatus.INCONCLUSIVE, c.fingerprint(), reason="no_evidence", evaluated_at=stamp)
    if c.resource_binding:
        expected_res_id = (
            c.resource_binding.get("resource_id")
            or c.resource_binding.get("id")
            or c.resource_binding.get("uri")
            or c.resource_binding.get("path")
        )
        for e in evs:
            if not e.resource_id:
                return VerificationResult(VerificationStatus.INCONCLUSIVE, c.fingerprint(), refs, reason="resource_binding_missing", evaluated_at=stamp)
            if expected_res_id is not None and str(e.resource_id) != str(expected_res_id):
                return VerificationResult(VerificationStatus.INCONCLUSIVE, c.fingerprint(), refs, reason="resource_binding_mismatch", evaluated_at=stamp)
            expected_res_ver = (
                c.resource_binding.get("resource_version")
                or c.resource_binding.get("version")
                or c.resource_binding.get("expected_version")
            )
            if expected_res_ver is not None and str(e.resource_version) != str(expected_res_ver):
                return VerificationResult(VerificationStatus.STALE, c.fingerprint(), refs, reason="resource_version_mismatch", evaluated_at=stamp)
    if any(e.verifier_fingerprint and e.verifier_fingerprint != c.fingerprint() for e in evs):
        return VerificationResult(VerificationStatus.STALE, c.fingerprint(), refs, reason="verifier_fingerprint_drift", evaluated_at=stamp)
    if any(e.observer != c.observer or e.source_kind != c.source_kind for e in evs):
        return VerificationResult(VerificationStatus.INCONCLUSIVE, c.fingerprint(), refs, reason="observer_or_source_mismatch", evaluated_at=stamp)
    if any(e.evidence_strength < c.minimum_evidence or (c.allowed_trust and e.trust_class not in c.allowed_trust) for e in evs):
        return VerificationResult(VerificationStatus.INCONCLUSIVE, c.fingerprint(), refs, reason="evidence_or_trust_insufficient", evaluated_at=stamp)
    domains = set(mutation_failure_domains or c.mutation_failure_domains)
    fault_ok = all(
        (not c.allowed_observer_failure_domains or e.observer_failure_domain in c.allowed_observer_failure_domains)
        and (not c.require_distinct_failure_domain or bool(e.observer_failure_domain) and e.observer_failure_domain not in domains)
        for e in evs
    )
    if not fault_ok:
        return VerificationResult(VerificationStatus.INCONCLUSIVE, c.fingerprint(), refs, source_admissible=True, reason="correlated_failure_domain", evaluated_at=stamp)
    fresh = True
    mutation_time = _parse_time(mutation_observed_at)
    now_dt = now or datetime.now(timezone.utc)
    for e in evs:
        observed = _parse_time(e.observed_at)
        if c.require_read_after_write and not e.read_after_write:
            fresh = False
        if c.temporal_basis in {"revision", "etag", "generation", "version"} and not e.resource_version:
            fresh = False
        if mutation_time and observed and observed < mutation_time:
            fresh = False
        if c.max_age_seconds is not None and (not observed or (now_dt - observed).total_seconds() > c.max_age_seconds):
            fresh = False
    if not fresh:
        return VerificationResult(VerificationStatus.STALE, c.fingerprint(), refs, source_admissible=True, fault_domain_admissible=True, reason="freshness_requirement_failed", evaluated_at=stamp)
    matches = [relation_matches(c, expected, e.value) for e in evs]
    normalized_values = {json.dumps(e.value, sort_keys=True, default=str) for e in evs}
    if len(normalized_values) > 1 and c.disagreement_policy == "conflict":
        return VerificationResult(VerificationStatus.CONFLICT, c.fingerprint(), refs, freshness_satisfied=True, source_admissible=True, fault_domain_admissible=True, reason="admissible_sources_disagree", evaluated_at=stamp)
    covered = set().union(*(set(e.covered_predicates) for e in evs))
    if required - covered:
        return VerificationResult(VerificationStatus.INCONCLUSIVE, c.fingerprint(), refs, tuple(sorted(covered)), True, all(matches), True, True, reason="predicate_coverage_insufficient", evaluated_at=stamp)
    if not all(matches):
        return VerificationResult(VerificationStatus.FAILED, c.fingerprint(), refs, tuple(sorted(covered)), True, False, True, True, reason="relation_rejected", evaluated_at=stamp)
    needs_transition = c.transition_claim if transition_required is None else transition_required
    if needs_transition:
        if not expected_operation_id:
            return VerificationResult(VerificationStatus.INCONCLUSIVE, c.fingerprint(), refs, tuple(sorted(covered)), True, True, True, True, False, "state_satisfied_transition_unproven:expected_operation_id_missing", stamp)
        if not all(e.operation_id == expected_operation_id for e in evs):
            return VerificationResult(VerificationStatus.INCONCLUSIVE, c.fingerprint(), refs, tuple(sorted(covered)), True, True, True, True, False, "state_satisfied_transition_unproven:operation_id_mismatch", stamp)
        transition_proven = True
    else:
        transition_proven = True
    return VerificationResult(VerificationStatus.VERIFIED, c.fingerprint(), refs, tuple(sorted(covered)), True, True, True, True, transition_proven, "verified", stamp)


def validate_verifier_sensitivity(receipts: list[dict[str, Any]]) -> tuple[bool, tuple[str, ...]]:
    """Require held-out success plus at least one discriminative negative control."""
    kinds = {(str(r.get("kind")), bool(r.get("passed"))) for r in receipts}
    reasons: list[str] = []
    if not any(k in {"positive_replay", "controlled_replay", "equivalent_representation"} and passed for k, passed in kinds):
        reasons.append("missing_positive_validation")
    negative_kinds = {"negative_control", "mutation_withheld", "wrong_effect", "stale_observation", "conflicting_source", "meaningful_difference"}
    if not any(k in negative_kinds and passed for k, passed in kinds):
        reasons.append("missing_discriminative_negative_control")
    discovery_refs = {str(r.get("evidence_ref")) for r in receipts if r.get("phase") == "discovery"}
    validation_refs = {str(r.get("evidence_ref")) for r in receipts if r.get("phase") == "validation"}
    if discovery_refs & validation_refs:
        reasons.append("discovery_validation_evidence_reused")
    return not reasons, tuple(reasons)


def validate_verifier_candidate(
    contract: VerificationContract, receipts: list[dict[str, Any]],
) -> tuple[VerificationContract, tuple[str, ...]]:
    """Return a new immutable contract; historical receipts are never rewritten."""
    valid, reasons = validate_verifier_sensitivity(receipts)
    lifecycle = VerificationLifecycle.VALIDATED if valid else VerificationLifecycle.QUARANTINED
    refs = tuple(str(r.get("evidence_ref")) for r in receipts if r.get("evidence_ref"))
    return replace(
        contract,
        lifecycle=lifecycle,
        validation_evidence_refs=refs,
        validation_receipts=tuple(dict(r) for r in receipts),
    ), reasons


def verifier_drifted(expected_fingerprint: str, current: VerificationContract) -> bool:
    return bool(expected_fingerprint) and expected_fingerprint != current.fingerprint()
