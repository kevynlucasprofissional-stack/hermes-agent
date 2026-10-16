"""Tests for browser_extract_items progressive capture, corpus acceptance, and compilation."""

import json
import tempfile
import unittest
from pathlib import Path

from workstation.artifacts import ArtifactStore
from workstation.experience_compiler.corpus import ExperienceCorpus
from workstation.experience_compiler.compiler import ExperienceCompiler
from workstation.experience_compiler.models import TransitionOutcome
from workstation.experience_compiler.progressive import capture_progressive
from workstation.operational_capabilities import CapabilityLifecycle, OperationalCapabilityRegistry
from workstation.control_plane.lattice import AuthorityLevel


class BrowserExtractCompilationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.artifacts = ArtifactStore(self.tmp_path / "artifacts")
        self.task_id = "task-extract-test"
        self.run_id = "run-1"
        self.op_id = "op-extract-1"
        self.registry = OperationalCapabilityRegistry(self.artifacts, root=self.tmp_path / "capabilities")
        self.corpus = ExperienceCorpus(self.artifacts)
        self.compiler = ExperienceCompiler(self.registry, self.corpus)

    def tearDown(self):
        self.tmp.cleanup()

    def _setup_verified_card_sample(self, op_id="op-extract-1", card_id="card-1"):
        # 1. Store raw result
        raw_result = {
            "success": True,
            "cached": False,
            "runtime": "electron-chromium",
            "task_id": self.task_id,
            "tab_id": "tab-1",
            "url": "https://example.test/cards",
            "count": 1,
            "items": [{
                "tag": "ARTICLE",
                "text": f"Title {card_id} Description {card_id}",
                "attributes": {"data-card-id": card_id, "data-list": "Todo"},
            }],
        }
        raw_ref = self.artifacts.store(
            self.task_id,
            f"raw_{op_id}.json",
            raw_result,
            schema="workstation.raw_tool_result.v1",
        ).ref

        # 2. Capture progressive observation
        trans_ref = capture_progressive(
            self.artifacts,
            task_id=self.task_id,
            run_id=self.run_id,
            operation_id=op_id,
            primitive="browser_extract_items",
            route="native_browser",
            outcome="observed",
            raw_result_ref=raw_ref,
            operation_family="browser_extract_items",
            target_family="native_browser",
            effect_class="read_only",
            state=raw_result,
        )

        # 3. Store owner readback receipt
        receipt = {
            "task_id": self.task_id,
            "run_id": self.run_id,
            "operation_id": op_id,
            "raw_result_ref": raw_ref,
            "transition_ref": trans_ref,
            "browser_task_id": self.task_id,
            "observer": "workstation.browser_live_dom",
            "source_kind": "browser_live_dom",
            "trust_class": "trusted_runtime",
            "independent_readback": True,
            "status": "VERIFIED",
            "observed_at": "2026-10-16T18:00:00Z",
            "tab_id": "tab-1",
            "url": "https://example.test/cards",
            "observation_consistency": "non_atomic_parent_bracket",
            "projection": {
                "shape": "native_browser.card_fields.v1",
                "semantic_predicates": {
                    "read.output_shape": "native_browser.card_fields.v1",
                    "read.fields_complete": True,
                },
                "proposed_verified_predicates": {
                    "read.output_shape": "native_browser.card_fields.v1",
                    "read.fields_complete": True,
                },
                "result_digest": "abcdef123456",
                "result_count": 1,
            },
        }
        readback_ref = self.artifacts.store(
            self.task_id,
            f"card_readback_{op_id}.json",
            receipt,
            schema="hermes.browser_card_readback.v1",
        ).ref

        return raw_ref, trans_ref, readback_ref

    def test_corpus_accept_work_item_projects_verified_predicates(self):
        raw_ref, _trans_ref, readback_ref = self._setup_verified_card_sample()

        accepted_ref = self.corpus.accept_work_item(self.task_id, self.run_id, readback_ref)
        self.assertIsNotNone(accepted_ref)

        accepted_data = self.artifacts.read_json(accepted_ref)
        self.assertEqual(accepted_data["outcome"], TransitionOutcome.VERIFIED_SUCCESS.value)
        self.assertEqual(accepted_data["raw_result_ref"], raw_ref)

        # Invariant: Output shape and fields_complete are captured, NO raw titles/descriptions
        state_after = accepted_data["state_after"]["semantic_predicates"]
        self.assertEqual(state_after.get("read.output_shape"), "native_browser.card_fields.v1")
        self.assertEqual(state_after.get("read.fields_complete"), True)
        self.assertNotIn("Title card-1", json.dumps(state_after))
        self.assertNotIn("card-1", json.dumps(state_after))

        # Verification proof
        verification = accepted_data["verification"]
        self.assertEqual(verification["status"], "VERIFIED")
        self.assertEqual(verification["verifier"], "browser_card_readback")
        self.assertIn(readback_ref, verification["evidence_refs"])

    def test_compiler_mines_read_only_capability_candidate(self):
        # Setup 2 samples for parameterization / utility
        self._setup_verified_card_sample(op_id="op-1", card_id="card-1")
        self.corpus.accept_work_item(self.task_id, self.run_id, f"artifact://tasks/{self.task_id}/card_readback_op-1.json")

        self._setup_verified_card_sample(op_id="op-2", card_id="card-2")
        self.corpus.accept_work_item(self.task_id, self.run_id, f"artifact://tasks/{self.task_id}/card_readback_op-2.json")

        mined = self.compiler.mine(task_id=self.task_id, run_id=self.run_id)
        self.assertEqual(len(mined), 1)

        cap = mined[0]
        self.assertEqual(cap.lifecycle, CapabilityLifecycle.DISCOVERED)
        self.assertEqual(cap.effect, "read_only")
        self.assertEqual(cap.route, "native_browser")

        # Invariant: Formal contract exists with browser_extract_items:native_browser
        self.assertIsNotNone(cap.formal_contract)
        self.assertEqual(cap.family_id, "browser_extract_items:native_browser")
        self.assertEqual(cap.formal_contract.authority_required.level, AuthorityLevel.READ)
        self.assertEqual(list(cap.formal_contract.effect_footprint), [])

        # Postconditions must include read.* output contract
        post_keys = {p["key"] for p in cap.postconditions}
        self.assertIn("read.output_shape", post_keys)
        self.assertIn("read.fields_complete", post_keys)

    def test_compilability_monitor_mines_candidate_in_run(self):
        from workstation.experience_compiler.compilability_monitor import OnlineCompilabilityMonitor

        self._setup_verified_card_sample(op_id="op-1", card_id="card-1")
        self.corpus.accept_work_item(self.task_id, self.run_id, f"artifact://tasks/{self.task_id}/card_readback_op-1.json")
        self._setup_verified_card_sample(op_id="op-2", card_id="card-2")
        self.corpus.accept_work_item(self.task_id, self.run_id, f"artifact://tasks/{self.task_id}/card_readback_op-2.json")

        monitor = OnlineCompilabilityMonitor(
            registry=self.registry,
            corpus=self.corpus,
            artifacts=self.artifacts,
            compiler=self.compiler,
        )

        candidates = monitor.mine_candidate_in_run(self.task_id, self.run_id)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].family_id, "browser_extract_items:native_browser")
        self.assertEqual(candidates[0].effect, "read_only")
