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
    verification_status: str = "VERIFIED_SUCCESS"
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
                "split": self.split,
                "verification_status": self.verification_status,
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
    ):
        self.output_dir = output_dir or Path("workstation/system1/dataset")
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.held_out_ratio = held_out_ratio
        self._samples: List[DatasetSample] = []

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
        verification_status: str = "VERIFIED_SUCCESS",
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
        verification_status: str = "VERIFIED_SUCCESS",
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
            verification_status="VERIFIED_SUCCESS",
            provenance={"task_id": task_id, "run_id": run_id},
        )
        self._samples.append(sample)
        return sample

    def ingest_learning_review(self, review: Any) -> List[DatasetSample]:
        """Convert actions and outcomes from a LearningReview into training samples."""
        samples: List[DatasetSample] = []
        task_id = getattr(review, "session_id", "session_unknown") or "session_unknown"
        run_id = getattr(review, "run_id", "run_unknown") or "run_unknown"
        actions = getattr(review, "actions", []) or []
        for idx, act in enumerate(actions):
            if isinstance(act, dict):
                tool = act.get("tool") or act.get("action") or "unknown"
                sample = self.add_capability_routing_sample(
                    task_id=task_id,
                    run_id=run_id,
                    operation_id=f"op_{idx}",
                    objective=act.get("description", "Execute review action"),
                    state=act.get("parameters", {}),
                    candidate_capabilities=[tool, "no_match", "abstain"],
                    chosen_capability=tool,
                    verification_status="VERIFIED_SUCCESS" if getattr(review, "status", "") == "success" else "UNCERTAIN",
                )
                samples.append(sample)
        return samples

    def export_partitions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Export dataset grouped by split."""
        partitions: Dict[str, List[Dict[str, Any]]] = {
            "train": [],
            "validation": [],
            "held_out": [],
        }
        for sample in self._samples:
            partitions[sample.split].append(sample.to_laya_format())
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
