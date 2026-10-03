"""Durable Decision Receipts for System-1 decisions.

Records the evidence, provenance, candidate-ordering and downstream linkage
without bloating conversation transcripts.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from workstation.artifacts import ArtifactStore


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


from pathlib import Path


@dataclass
class DecisionReceipt:
    """Durable receipt recording a System-1 decision and its lineage."""

    receipt_id: str = field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:12]}")
    request_ref: str = ""
    result_ref: str = ""
    domain: str = ""
    schema_id: str = ""
    state_digest: str = ""
    request_hash: str = ""
    state_ref: str = ""
    candidate_set_ref: str = ""
    candidate_set_hash: str = ""

    task_id: str = ""
    run_id: str = ""
    operation_id: str = ""

    influence_mode: str = "direct"
    selected_candidate: Optional[str] = None
    fallback_taken: bool = False

    provider: str = "laya"
    model: str = "multilingual"
    model_revision: Optional[str] = None
    calibration_id: str = ""
    question_schema_version: str = "1.0.0"
    laya_version: str = ""
    laya_source_sha: str = ""
    laya_source_path: str = ""
    checkpoint_digest: Optional[str] = None

    confidence: Dict[str, float] = field(default_factory=dict)
    confidences: Dict[str, float] = field(default_factory=dict)
    answers: Dict[str, Any] = field(default_factory=dict)
    decisions: Dict[str, Any] = field(default_factory=dict)
    calibrated_confidences: Dict[str, float] = field(default_factory=dict)
    probabilities: Dict[str, Any] = field(default_factory=dict)
    abstentions: list[str] = field(default_factory=list)

    downstream_certificate_ref: Optional[str] = None
    downstream_verification_ref: Optional[str] = None

    latency_ms: float = 0.0
    created_at: str = field(default_factory=_utc_now)
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.answers and self.decisions:
            self.answers = self.decisions
        elif not self.decisions and self.answers:
            self.decisions = self.answers
        if not self.confidence and self.confidences:
            self.confidence = self.confidences
        elif not self.confidences and self.confidence:
            self.confidences = self.confidence

    def receipt_hash(self) -> str:
        import hashlib
        data = {
            "receipt_id": self.receipt_id,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "operation_id": self.operation_id,
            "provider": self.provider,
            "answers": self.answers,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DecisionReceipt:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def persist_decision_receipt(
    receipt: DecisionReceipt,
    artifact_store: Optional[Any] = None,
) -> Any:
    """Persist a DecisionReceipt to ArtifactStore or file path and return reference."""
    if isinstance(artifact_store, (str, Path)):
        p = Path(artifact_store)
        if p.is_dir():
            target = p / f"decision_receipt_{receipt.receipt_id}.json"
        else:
            target = p
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(receipt.to_dict(), indent=2), encoding="utf-8")
        return target

    store = artifact_store or ArtifactStore()
    task_id = receipt.task_id or "system1"
    filename = f"decision_receipt_{receipt.receipt_id}.json"
    artifact_ref = store.store(
        task_id=task_id,
        name=filename,
        content=receipt.to_dict(),
        media_type="application/json",
        schema="system1.decision_receipt.v1",
        summary={
            "provider": receipt.provider,
            "influence_mode": receipt.influence_mode,
            "fallback_taken": receipt.fallback_taken,
            "selected_candidate": receipt.selected_candidate,
            "latency_ms": receipt.latency_ms,
        },
    )
    return artifact_ref.ref


def load_decision_receipt(
    ref: Any,
    artifact_store: Optional[Any] = None,
) -> Optional[DecisionReceipt]:
    """Load a DecisionReceipt from ArtifactStore or file path."""
    if isinstance(ref, (str, Path)) and Path(ref).is_file():
        try:
            data = json.loads(Path(ref).read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return DecisionReceipt.from_dict(data)
        except Exception:
            pass

    store = artifact_store or ArtifactStore()
    try:
        data = store.read_json(ref)
        if isinstance(data, dict):
            return DecisionReceipt.from_dict(data)
    except Exception:
        pass
    return None


def link_decision_receipt(ref, store, *, task_id=None, run_id=None, operation_id=None, certificate_ref=None, verification_ref=None):
    receipt = load_decision_receipt(ref, store)
    if receipt is None:
        return False
    for field, expected in (("task_id", task_id), ("run_id", run_id), ("operation_id", operation_id)):
        actual = getattr(receipt, field)
        if actual and expected is not None and str(actual) != str(expected):
            raise ValueError("DecisionReceipt downstream lineage mismatch")
    if certificate_ref:
        receipt.downstream_certificate_ref = certificate_ref
        certificate = store.read_json(certificate_ref)
        receipt.details["provider_preferred_candidate"] = receipt.selected_candidate
        receipt.selected_candidate = certificate.get("capability_id") or receipt.selected_candidate
    if verification_ref:
        receipt.downstream_verification_ref = verification_ref
    persist_decision_receipt(receipt, store)
    return True
