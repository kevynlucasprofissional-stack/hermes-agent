"""Contract tests for shared-checkout coordination (no real Git writes)."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "multi_agent_coordination.py"
spec = importlib.util.spec_from_file_location("multi_agent_coordination", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SharedCheckoutCoordinationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_claim_status_and_release(self) -> None:
        item = module.claim(self.root, "agent-one", "creative", ["apps/desktop/src/app/creative-workspace"], "Editor")
        self.assertEqual(item["status"], "ACTIVE")
        self.assertEqual(len(module.read_claims(module.state_root(self.root))), 1)
        module.release(self.root, "agent-one", "creative")
        self.assertEqual(module.read_claims(module.state_root(self.root)), [])

    def test_same_lane_cannot_be_stolen(self) -> None:
        module.claim(self.root, "agent-one", "creative", ["apps/desktop/src/app/creative-workspace"], "Editor")
        with self.assertRaisesRegex(RuntimeError, "already claimed"):
            module.claim(self.root, "agent-two", "creative", ["workstation/docs"], "Other")

    def test_claims_reject_subdirectory_overlap(self) -> None:
        module.claim(self.root, "agent-one", "browser", ["apps/desktop/src/app/browser"], "Browser")
        with self.assertRaisesRegex(RuntimeError, "Path conflict"):
            module.claim(self.root, "agent-two", "creative", ["apps/desktop/src/app/browser/index.tsx"], "UI")

    def test_unrelated_claims_can_coexist(self) -> None:
        module.claim(self.root, "agent-one", "browser", ["apps/desktop/src/app/browser"], "Browser")
        module.claim(self.root, "agent-two", "creative", ["apps/desktop/src/app/creative-workspace"], "Editor")
        self.assertEqual(len(module.read_claims(module.state_root(self.root))), 2)

    def test_nonowner_cannot_update_or_release(self) -> None:
        module.claim(self.root, "agent-one", "browser", ["apps/desktop/src/app/browser"], "Browser")
        with self.assertRaisesRegex(RuntimeError, "Owner mismatch"):
            module.update(self.root, "agent-two", "browser", "BLOCKED", "no")
        with self.assertRaisesRegex(RuntimeError, "Only agent-one"):
            module.release(self.root, "agent-two", "browser")

    def test_heartbeat_persists_next_action(self) -> None:
        module.claim(self.root, "agent-one", "browser", ["apps/desktop/src/app/browser"], "Browser")
        row = module.update(self.root, "agent-one", "browser", "READY_FOR_REVIEW", "run browser tests")
        self.assertEqual(row["next_action"], "run browser tests")
        self.assertEqual(module.read_claims(module.state_root(self.root))[0]["status"], "READY_FOR_REVIEW")

    def test_rejects_parent_traversal(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            module.claim(self.root, "agent-one", "browser", ["../secret"], "Unsafe")

    def test_incomplete_claim_is_visible_not_stolen(self) -> None:
        folder = module.state_root(self.root)
        (folder / "creative.claim").mkdir(parents=True)
        self.assertEqual(module.read_claims(folder)[0]["status"], "INCOMPLETE_CLAIM")
        with self.assertRaisesRegex(RuntimeError, "already claimed"):
            module.claim(self.root, "agent-one", "creative", ["apps/desktop"], "No steal")


if __name__ == "__main__":
    unittest.main()
