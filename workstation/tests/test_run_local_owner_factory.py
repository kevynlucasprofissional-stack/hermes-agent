"""Regression coverage for the real Hermes run-local owner factory."""

from __future__ import annotations

import contextlib
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from workstation.integrations.hermes import run_local_adoption as module


class RunLocalOwnerWiringTests(unittest.TestCase):
    def test_card_extraction_requires_owner_readback_support(self):
        owner = module.build_run_adoption_owner(self.agent)
        self.assertTrue(owner.supports("browser_extract_items"))
        self.assertTrue(owner.can_readback("browser_extract_items"))

    def setUp(self):
        self.operations = []
        self.files = {}
        self.agent = SimpleNamespace(
            _canonical_work_task_id="task-A",
            _canonical_work_run_id="1",
            session_id="session-A",
        )

        def inner(tool, args, task_id, operation_id):
            self.operations.append((task_id, tool, dict(args)))
            if tool == "read_file":
                return json.dumps({"content": self.files.get(args["path"], "")})
            if tool == "write_file":
                self.files[args["path"]] = args["content"]
                return json.dumps({"ok": True})
            return json.dumps({})

        self.patches = [
            patch(
                "workstation.integrations.hermes.scoped_execution.workstation_durable_dispatch",
                return_value=inner,
            ),
            patch(
                "workstation.integrations.hermes.scoped_execution.workstation_scoped_execution",
                side_effect=lambda *a: contextlib.nullcontext(),
            ),
            patch.object(
                module,
                "ArtifactStore",
                return_value=SimpleNamespace(
                    store=lambda *a, **kw: SimpleNamespace(
                        ref="artifact://isolated-readback"
                    )
                ),
            ),
            patch(
                "workstation.experience_compiler.lifecycle.get_validation_environment_provider",
                return_value=object(),
            ),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_real_factory_dispatches_independent_write_file_readback(self):
        owner = module.build_run_adoption_owner(self.agent)
        self.assertTrue(owner.supports("write_file"))
        self.assertTrue(owner.can_readback("write_file"))
        owner.dispatch("write_file", {"path": "file.txt", "content": "alpha"})
        result = owner.readback(
            "write_file", {"path": "file.txt", "content": "alpha"}, {"ok": True}
        )
        self.assertEqual(result["ok"], True)
        self.assertEqual(
            [event[1] for event in self.operations], ["write_file", "read_file"]
        )

    def test_negative_readback_does_not_validate_divergent_file(self):
        owner = module.build_run_adoption_owner(self.agent)
        self.files["file.txt"] = "tampered"
        result = owner.readback(
            "write_file", {"path": "file.txt", "content": "expected"}, None
        )
        self.assertFalse(result["ok"])

    def test_owner_rebuilt_when_task_run_changes(self):
        original = module.build_run_adoption_owner(self.agent)
        self.agent._canonical_work_task_id = "task-B"
        self.agent._canonical_work_run_id = "2"
        next_owner = module.build_run_adoption_owner(self.agent)
        self.assertIsNot(original, next_owner)
        next_owner.dispatch("write_file", {"path": "another.txt", "content": "second"})
        self.assertEqual(self.operations[-1][0], "task-B")
        self.assertIs(next_owner, module.build_run_adoption_owner(self.agent))

    def test_legacy_cached_owner_without_taskrun_binding_is_not_reused(self):
        old_owner = SimpleNamespace(dispatch=lambda *_: None)
        self.agent._run_adoption_owner = old_owner
        actual = module.build_run_adoption_owner(self.agent)
        self.assertIsNot(actual, old_owner)
        self.assertEqual(actual._bound_task_run, ("task-A", "1"))

    def test_stale_owner_cannot_dispatch_into_a_later_taskrun(self):
        owner = module.build_run_adoption_owner(self.agent)
        self.agent._canonical_work_task_id = "task-B"
        self.agent._canonical_work_run_id = "2"
        with self.assertRaisesRegex(RuntimeError, "taskrun_identity_changed"):
            owner.dispatch("write_file", {"path": "stale.txt", "content": "unsafe"})
        self.assertEqual(self.operations, [])

    def test_stale_owner_cannot_issue_readback_after_run_change(self):
        owner = module.build_run_adoption_owner(self.agent)
        self.agent._canonical_work_run_id = "2"
        with self.assertRaisesRegex(RuntimeError, "taskrun_identity_changed"):
            owner.readback("write_file", {"path": "stale.txt", "content": "unsafe"}, None)
        self.assertEqual(self.operations, [])

    def test_readback_is_not_claimed_for_unverified_raw_only_primitives(self):
        owner = module.build_run_adoption_owner(self.agent)
        self.assertFalse(owner.can_readback("browser_snapshot"))
        self.assertFalse(owner.can_readback("trello_api_get"))


if __name__ == "__main__":
    unittest.main()
