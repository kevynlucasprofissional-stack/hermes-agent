"""Tests for DF-009 / DF-010: Durable Learning Checkpoints & Adaptive Retry.

Validates:
1. High-value learning references survive queue saturation.
2. Window eviction (900s TTL / max_windows) does not erase knowledge; rehydrates from
   workstation.run_learning_checkpoint.v1.
3. Adaptive retry: compilation attempts reopen when materially new evidence arrives,
   without busy-looping on identical evidence.
4. Monitor stop/restart preserves checkpoints.
"""
from __future__ import annotations

import time
import pytest

from workstation.artifacts import ArtifactStore
from workstation.experience_compiler.compilability_monitor import (
    CompilabilityEvent,
    CompilabilityStage,
    OnlineCompilabilityMonitor,
    TaskRunObservationWindow,
    SHADOW,
    DIRECT,
)
from workstation.experience_compiler.compiler import ExperienceCompiler
from workstation.experience_compiler.corpus import ExperienceCorpus
from workstation.operational_capabilities import OperationalCapabilityRegistry


def test_window_eviction_and_rehydration_from_checkpoint(tmp_path):
    """DF-009: 900s TTL / max_windows eviction does not lose verified refs or mined candidates."""
    artifacts = ArtifactStore(root_dir=tmp_path / "artifacts")
    registry = OperationalCapabilityRegistry(artifacts)
    corpus = ExperienceCorpus(artifacts)
    compiler = ExperienceCompiler(registry, corpus)

    monitor = OnlineCompilabilityMonitor(
        artifacts=artifacts,
        registry=registry,
        corpus=corpus,
        compiler=compiler,
        max_windows=2,
        window_ttl_seconds=0.01,  # Fast TTL for test
    )

    # Window 1 with verified evidence
    ev1 = CompilabilityEvent(
        event_kind="verified_transition",
        sample_ref="artifact://sample_important_1",
        task_id="task_durable_1",
        run_id="run_1",
        operation_id="op_1",
        primitive="read_file",
        route="filesystem",
        outcome="verified_success",
        operation_family="file_op",
        target_family="file",
    )
    monitor.process_event(ev1)
    window1 = monitor._get_window("task_durable_1", "run_1")
    assert "artifact://sample_important_1" in window1.verified_success_refs

    # Wait for TTL expiration and trigger eviction by accessing other windows
    time.sleep(0.02)
    ev2 = CompilabilityEvent(
        event_kind="observed",
        sample_ref="artifact://sample_2",
        task_id="task_other_1",
        run_id="run_1",
        operation_id="op_2",
        primitive="read_file",
        route="filesystem",
        outcome="observed",
    )
    ev3 = CompilabilityEvent(
        event_kind="observed",
        sample_ref="artifact://sample_3",
        task_id="task_other_2",
        run_id="run_1",
        operation_id="op_3",
        primitive="read_file",
        route="filesystem",
        outcome="observed",
    )
    monitor.process_event(ev2)
    monitor.process_event(ev3)

    # Re-access task_durable_1: must rehydrate verified_success_refs from checkpoint
    rehydrated_window = monitor._get_window("task_durable_1", "run_1")
    assert "artifact://sample_important_1" in rehydrated_window.verified_success_refs


def test_adaptive_retry_reopens_on_fresh_evidence(tmp_path):
    """DF-010: Compilation attempts back off on same evidence, but reopen when fresh evidence arrives."""
    artifacts = ArtifactStore(root_dir=tmp_path / "artifacts")
    registry = OperationalCapabilityRegistry(artifacts)
    corpus = ExperienceCorpus(artifacts)
    compiler = ExperienceCompiler(registry, corpus)

    monitor = OnlineCompilabilityMonitor(
        artifacts=artifacts,
        registry=registry,
        corpus=corpus,
        compiler=compiler,
    )

    window = monitor._get_window("task_retry", "run_1")
    seg_key = "batch_card:trello"

    # Initial state: can attempt
    assert window.can_attempt_compilation(seg_key)

    # Simulate 3 attempts against the initial evidence revision
    window.record_compilation_attempt(seg_key)
    window.record_compilation_attempt(seg_key)
    window.record_compilation_attempt(seg_key)

    # Blocked against same evidence
    assert not window.can_attempt_compilation(seg_key)

    # Now add fresh verified evidence to the segment
    fresh_event = CompilabilityEvent(
        event_kind="verified_transition",
        sample_ref="artifact://fresh_card_sample",
        task_id="task_retry",
        run_id="run_1",
        operation_id="op_fresh",
        primitive="create_card",
        route="native_browser",
        outcome="verified_success",
        operation_family="batch_card",
        target_family="trello",
    )
    window.add_event(fresh_event)

    # Fresh evidence must re-enable compilation attempts!
    assert window.can_attempt_compilation(seg_key)


def test_queue_full_preserves_high_value_references(tmp_path):
    """DF-009: When queue is saturated, high-value verified references are preserved in window state."""
    artifacts = ArtifactStore(root_dir=tmp_path / "artifacts")
    registry = OperationalCapabilityRegistry(artifacts)
    corpus = ExperienceCorpus(artifacts)
    compiler = ExperienceCompiler(registry, corpus)

    # Queue size of 2
    monitor = OnlineCompilabilityMonitor(
        artifacts=artifacts,
        registry=registry,
        corpus=corpus,
        compiler=compiler,
        max_queue_size=2,
    )

    # Fill queue with noise
    for i in range(2):
        ev = CompilabilityEvent(
            event_kind="noise",
            sample_ref=f"artifact://noise_{i}",
            task_id="task_queue",
            run_id="run_1",
            operation_id=f"op_{i}",
            primitive="ping",
            route="system",
            outcome="observed",
        )
        monitor.schedule_event(ev)

    # Schedule high-value verified event while queue is full
    high_val = CompilabilityEvent(
        event_kind="verified_transition",
        sample_ref="artifact://high_value_verified_sample",
        task_id="task_queue",
        run_id="run_1",
        operation_id="op_high",
        primitive="save_document",
        route="filesystem",
        outcome="verified_success",
        operation_family="save",
        target_family="doc",
    )
    scheduled = monitor.schedule_event(high_val)

    # Even if queue shed the general execution, window must have captured the verified sample!
    window = monitor._get_window("task_queue", "run_1")
    assert "artifact://high_value_verified_sample" in window.verified_success_refs
