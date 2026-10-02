"""Continuous dataset generation and evaluation splitting for System-1 (Laya).

Derives structured training/validation/held-out examples from real verified
transitions, ExecutionJournal events, and LearningReview artifacts.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DatasetSample:
    """A single training/evaluation instance for System-1 decisions."""

    sample_id: str
    task_id: str
    run_id: str
    operation_id: str
    task_phase: str
    objective: str
    state: Dict[str, Any]
    questions: Dict[str, Any]
    expected_answers: Dict[str, Any]
    confidence_target: float = 1.0
    split: str = "train"  # train | validation | held_out
    verification_status: str = "UNVERIFIED"
    provenance: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now)

    def to_laya_format(self) -> Dict[str, Any]:
        """Convert sample to format expected by Laya dataset/fine-tuning."""
        return {
            "state": self.state,
            "questions": self.questions,
            "expected": self.expected_answers,
            "metadata": {
                "sample_id": self.sample_id,
                "task_id": self.task_id,
                "run_id": self.run_id,
                "operation_id": self.operation_id,
                "split": self.split,
                "verification_status": self.verification_status,
                "provenance": self.provenance,
            },
        }


class System1DatasetBuilder:
    """Constructs versioned, leakage-free dataset partitions for Laya."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        held_out_ratio: float = 0.15,
        artifact_store=None,
    ):
        self.output_dir = output_dir or Path("workstation/system1/dataset")
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.held_out_ratio = held_out_ratio
        self._samples: List[DatasetSample] = []
        from workstation.artifacts import ArtifactStore
        self.artifacts = artifact_store or ArtifactStore()
        self.reconstruct()

    def reconstruct(self):
        """Artifacts are the source; this bounded in-memory list is rebuildable."""
        from itertools import islice
        found = {}
        for directory in islice(self.artifacts.root.iterdir(), 4096):
            if directory.is_dir():
                for path in islice(directory.glob("system1_sample_*.json"), 8192):
                    if path.name.endswith(".meta.json"):
                        continue
                    body = json.loads(path.read_text(encoding="utf-8"))
                    sample = DatasetSample(**body)
                    found[sample.sample_id] = sample
        self._samples = list(found.values())
        return len(self._samples)

    def _persist_sample(self, sample):
        from workstation.recipes import digest
        body = asdict(sample)
        self.artifacts.store(sample.task_id or "system1_proposals", "system1_sample_" + digest(body) + ".json",
            body, schema="hermes.system1_dataset_sample.v1")
        self._samples = [s for s in self._samples if s.sample_id != sample.sample_id] + [sample]

    def ingest_invocation(self, ref):
        body = self.artifacts.read_json(ref)
        task, run, operation = body.get("task_id"), str(body.get("run_id") or ""), body.get("operation_id")
        verified = self._verified_invocation([ref], task, run, operation)
        sample = self.add_capability_routing_sample(task or "", run, operation or "", "Canonical capability outcome", {},
            [body["capability_id"]], body["capability_id"],
            verification_status="VERIFIED_SUCCESS" if verified else "UNCERTAIN", persist=False)
        sample.sample_id = "invocation_" + body["invocation_id"]
        sample.provenance.update(source="OperationalKernel", source_refs=[ref],
            evidence_refs=body.get("verification_evidence_refs", []), canonical_verifier_grounded=bool(verified))
        self._persist_sample(sample)
        return sample

    def _determine_split(self, task_id: str) -> str:
        """Deterministic task-level split assignment to prevent run-level data leakage."""
        hash_val = int(hashlib.md5(task_id.encode("utf-8")).hexdigest(), 16) % 100
        train_thresh = int(self.train_ratio * 100)
        val_thresh = int((self.train_ratio + self.val_ratio) * 100)

        if hash_val < train_thresh:
            return "train"
        elif hash_val < val_thresh:
            return "validation"
        return "held_out"

    def add_capability_routing_sample(
        self,
        task_id: str,
        run_id: str,
        operation_id: str,
        objective: str,
        state: Dict[str, Any],
        candidate_capabilities: List[str],
        chosen_capability: str,
        verification_status: str = "UNVERIFIED",
        persist: bool = True,
    ) -> DatasetSample:
        """Build sample for capability selection/ranking."""
        from workstation.system1.schemas import build_candidate_ranking_schema

        questions = build_candidate_ranking_schema(candidate_capabilities)
        sample = DatasetSample(
            sample_id=f"cap_{task_id}_{operation_id}",
            task_id=task_id,
            run_id=run_id,
            operation_id=operation_id,
            task_phase="execution",
            objective=objective,
            state={"objective": objective, "state": state, "candidates": candidate_capabilities},
            questions=questions,
            expected_answers={"preferred_candidate": chosen_capability},
            split=self._determine_split(task_id),
            verification_status=verification_status,
            provenance={"task_id": task_id, "run_id": run_id, "operation_id": operation_id},
        )
        self._samples.append(sample)
        if persist:
            self._persist_sample(sample)
        return sample

    def add_progress_sample(
        self,
        task_id: str,
        run_id: str,
        operation_id: str,
        objective: str,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        delta: Dict[str, Any],
        progress_class: str,
        verification_status: str = "UNVERIFIED",
    ) -> DatasetSample:
        """Build sample for progress classification."""
        from workstation.system1.schemas import STANDARD_SCHEMAS

        questions = STANDARD_SCHEMAS["progress_class"]
        sample = DatasetSample(
            sample_id=f"prog_{task_id}_{operation_id}",
            task_id=task_id,
            run_id=run_id,
            operation_id=operation_id,
            task_phase="verification",
            objective=objective,
            state={
                "objective": objective,
                "before": before_state,
                "after": after_state,
                "delta": delta,
            },
            questions=questions,
            expected_answers={"progress_class": progress_class},
            split=self._determine_split(task_id),
            verification_status=verification_status,
            provenance={"task_id": task_id, "run_id": run_id},
        )
        self._samples.append(sample)
        self._persist_sample(sample)
        return sample

    def add_reasoning_gap_sample(
        self,
        task_id: str,
        run_id: str,
        operation_id: str,
        objective: str,
        state: Dict[str, Any],
        ambiguity_kind: str,
        needs_system2: str,
    ) -> DatasetSample:
        """Build sample for reasoning gap / System-2 necessity."""
        from workstation.system1.schemas import STANDARD_SCHEMAS

        questions = {
            **STANDARD_SCHEMAS["ambiguity_kind"],
            **STANDARD_SCHEMAS["needs_system2"],
        }
        sample = DatasetSample(
            sample_id=f"gap_{task_id}_{operation_id}",
            task_id=task_id,
            run_id=run_id,
            operation_id=operation_id,
            task_phase="planning",
            objective=objective,
            state={"objective": objective, "state": state},
            questions=questions,
            expected_answers={
                "ambiguity_kind": ambiguity_kind,
                "needs_system2": needs_system2,
            },
            split=self._determine_split(task_id),
            verification_status="UNVERIFIED",
            provenance={"task_id": task_id, "run_id": run_id},
        )
        self._samples.append(sample)
        self._persist_sample(sample)
        return sample

    def ingest_learning_review(self, review: Any) -> List[DatasetSample]:
        """Convert actions and outcomes from a LearningReview into training samples."""
        samples: List[DatasetSample] = []
        task_id = getattr(review, "task_id", "") or ""
        run_id = getattr(review, "run_id", "") or ""
        actions = getattr(review, "actions", []) or []
        for idx, act in enumerate(actions):
            # The real producer emits strings (memory/skill summaries). Such a
            # summary is a proposal, not an executable capability or truth label.
            action = act if isinstance(act, dict) else {"action_kind": "review_summary", "shape": type(act).__name__}
            operation_id = action.get("operation_id") or getattr(review, "operation_id", "")
            refs = action.get("evidence_refs") or getattr(review, "evidence_refs", [])
            invocation = self._verified_invocation(refs, task_id, run_id, operation_id)
            verified = invocation is not None and getattr(review, "status", "") == "success"
            sample = self.add_capability_routing_sample(task_id, run_id, operation_id, "Learning review proposal", {},
                [invocation["capability_id"]] if verified else ["NO_MATCH"],
                invocation["capability_id"] if verified else "NO_MATCH",
                verification_status="VERIFIED_SUCCESS" if verified else "FAILED" if getattr(review, "status", "") == "error" else "UNVERIFIED_REVIEW", persist=False)
            sample.sample_id = "review_" + hashlib.sha256(json.dumps([task_id, run_id, operation_id, idx, refs, action], sort_keys=True, default=str).encode()).hexdigest()[:24]
            sample.provenance.update(source="LearningReview", source_refs=list(refs), action_shape=type(act).__name__,
                review_status=getattr(review, "status", ""), canonical_verifier_grounded=verified,
                evidence_refs=invocation["verification_evidence_refs"] if verified else [])
            samples.append(sample)
            self._persist_sample(sample)
        return samples

    def _verified_invocation(self, refs, task_id, run_id, operation_id):
        if not task_id or not run_id or not operation_id:
            return None
        for ref in refs:
            try:
                resolved = self.artifacts.resolve_structured(ref)
                body = resolved.get("content") or {}
                if (resolved.get("schema") == "hermes.capability_invocation.v1"
                    and body.get("task_id") == task_id and str(body.get("run_id")) == str(run_id)
                    and body.get("operation_id") == operation_id
                    and body.get("verified") is True and body.get("verifier_status") == "VERIFIED"
                    and body.get("freshness_satisfied") is True and body.get("verifier_fingerprint")
                    and body.get("covered_predicates") and body.get("verification_evidence_refs")
                    and all(self.artifacts.resolve_ref(e) for e in body["verification_evidence_refs"])):
                    proof = self.artifacts.resolve_structured(body.get("verification_record_ref", ""))
                    record = proof.get("content") or {}
                    if proof.get("schema") != "hermes.canonical_verification.v1":
                        continue
                    from workstation.control_plane.verification import evaluate_verification
                    if (record.get("task_id") != task_id or str(record.get("run_id")) != str(run_id)
                        or record.get("operation_id") != operation_id):
                        continue
                    result = evaluate_verification(record["contract"], record["expected"], record["evidence"],
                        required_predicates=set(body["covered_predicates"]), expected_task_id=task_id,
                        expected_run_id=str(run_id), expected_operation_id=operation_id,
                        mutation_failure_domains=set(record.get("mutation_failure_domains", [])),
                        mutation_observed_at=record.get("mutation_observed_at", ""),
                        now=datetime.fromisoformat(record["result"]["evaluated_at"]))
                    if result.verified and result.verifier_fingerprint == body["verifier_fingerprint"]:
                        return body
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return None

    def export_partitions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Export dataset grouped by split."""
        partitions: Dict[str, List[Dict[str, Any]]] = {
            "train": [],
            "validation": [],
            "held_out": [],
            "proposals": [],
            "counterevidence": [],
        }
        for sample in self._samples:
            eligible = (sample.verification_status == "VERIFIED_SUCCESS" and sample.task_id and sample.run_id
                and sample.operation_id and sample.provenance.get("canonical_verifier_grounded")
                and self._verified_invocation(sample.provenance.get("source_refs", []), sample.task_id, sample.run_id, sample.operation_id))
            negative = sample.verification_status.lower() in {"failed", "uncertain", "interrupted", "authority_superseded"}
            partition = sample.split if eligible else "counterevidence" if negative else "proposals"
            partitions[partition].append(sample.to_laya_format())
        return partitions

    def write_to_disk(self, target_dir: Optional[Path] = None) -> Dict[str, Path]:
        """Write jsonl files for train, validation, and held_out splits."""
        dest = target_dir or self.output_dir
        dest.mkdir(parents=True, exist_ok=True)
        paths = {}
        partitions = self.export_partitions()
        for split_name, samples in partitions.items():
            out_file = dest / f"{split_name}.jsonl"
            with open(out_file, "w", encoding="utf-8") as f:
                for s in samples:
                    f.write(json.dumps(s, ensure_ascii=False) + "\n")
            paths[split_name] = out_file
        return paths
