"""RED tests proposed for P1C: prevent accepting another/imaginary operation.

NOT currently wired into CI. Copy this file into workstation/tests/
when implementing the fail-closed fix in ExperienceCorpus.accept_work_item.
Expected to be RED against PR #94 due to fallback-to-last/fabricated samples.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from workstation.artifacts import ArtifactStore
from workstation.experience_compiler.corpus import ExperienceCorpus
from workstation.experience_compiler.progressive import capture_progressive


class StrictReadAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.artifacts = ArtifactStore(Path(self.tmp.name) / "artifacts")
        self.task_id = "p1c-strict-task"
        self.run_id = "p1c-strict-run"
        self.corpus = ExperienceCorpus(self.artifacts)

    def sample(self, op_id):
        raw_ref = self.artifacts.store(
            self.task_id, f"raw_{op_id}.json", {"items": [], "success": True},
            schema="workstation.raw_tool_result.v1",
        ).ref
        sample_ref = capture_progressive(
            self.artifacts, task_id=self.task_id, run_id=self.run_id,
            operation_id=op_id, primitive="browser_extract_items",
            route="native_browser", outcome="observed", raw_result_ref=raw_ref,
            operation_family="browser_extract_items",
            target_family="native_browser", effect_class="read_only",
            state={"success": True},
        )
        self.assertIsNotNone(sample_ref)
        self.corpus.refresh_task(self.task_id)
        return raw_ref, sample_ref

    def receipt(self, op_id, raw_ref, sample_ref):
        body = {
            "task_id": self.task_id, "run_id": self.run_id,
            "operation_id": op_id, "raw_result_ref": raw_ref,
            "transition_ref": sample_ref,
            "trust_class": "trusted_runtime",
            "independent_readback": True, "status": "VERIFIED",
            "observer": "workstation.browser_live_dom",
            "source_kind": "browser_live_dom",
            "observed_at": "2026-10-16T21:00:00+00:00",
            "projection": {
                "shape": "native_browser.card_fields.v1",
                "semantic_predicates": {
                    "read.output_shape": "native_browser.card_fields.v1",
                    "read.fields_complete": True,
                },
            },
        }
        return self.artifacts.store(
            self.task_id, f"readback_{op_id}.json", body,
            schema="hermes.browser_card_readback.v1",
        ).ref

    def test_receipt_without_any_matching_sample_must_not_fabricate_one(self):
        raw = self.artifacts.store(
            self.task_id, "raw_fake.json", {"success": True},
            schema="workstation.raw_tool_result.v1",
        ).ref
        receipt = self.receipt("op-not-observed", raw, "artifact://tasks/p1c-strict-task/none.json")
        self.assertIsNone(self.corpus.accept_work_item(self.task_id, self.run_id, receipt))

    def test_receipt_for_different_operation_must_not_use_latest_sample(self):
        raw, sample_ref = self.sample("op-observed")
        receipt = self.receipt("op-other", raw, sample_ref)
        self.assertIsNone(self.corpus.accept_work_item(self.task_id, self.run_id, receipt))

    def test_receipt_wrong_raw_ref_does_not_accept_matching_operation(self):
        _raw, sample_ref = self.sample("op-A")
        different_raw = self.artifacts.store(
            self.task_id, "raw_other.json", {"success": True},
            schema="workstation.raw_tool_result.v1",
        ).ref
        receipt = self.receipt("op-A", different_raw, sample_ref)
        self.assertIsNone(self.corpus.accept_work_item(self.task_id, self.run_id, receipt))


if __name__ == "__main__":
    unittest.main()
