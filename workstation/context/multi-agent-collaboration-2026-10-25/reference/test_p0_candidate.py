"""Isolated RED/GREEN regression contract for the prepared P0 patch.

Uses temporary directories; never touches the live registry or Git index.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "multi_agent_coordination_p0", HERE / "multi_agent_coordination_p0.py"
)
assert spec and spec.loader
coord = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coord)


class PreparedCoordinatorP0Tests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)

    def reserve(self, status="ACTIVE"):
        item = coord.claim(
            self.repo, "owner-one", "lane-one", ["tools/browser_workstation.py"], "M3 patch"
        )
        if status != "ACTIVE":
            coord.update(self.repo, "owner-one", "lane-one", status, "handoff")
        return item

    def test_active_claim_blocks_other(self):
        self.reserve()
        result = coord.check_path(self.repo, "tools/browser_workstation.py", "owner-two")
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "OWNED_BY_OTHER_AGENT")

    def test_ready_for_integration_remains_exclusive(self):
        self.reserve("READY_FOR_INTEGRATION")
        result = coord.check_path(self.repo, "tools/browser_workstation.py", "owner-two")
        self.assertFalse(result["allowed"])

    def test_blocked_remains_exclusive(self):
        self.reserve("BLOCKED")
        self.assertFalse(coord.check_path(
            self.repo, "tools/browser_workstation.py", "owner-two"
        )["allowed"])

    def test_owner_can_proceed_when_claim_not_active(self):
        self.reserve("READY_FOR_INTEGRATION")
        self.assertTrue(coord.check_path(
            self.repo, "tools/browser_workstation.py", "owner-one", True
        )["allowed"])

    def test_strict_mode_requires_claim(self):
        self.assertEqual(
            coord.check_path(self.repo, "new_file.py", "any-agent", True)["reason"],
            "CLAIM_REQUIRED",
        )

    def test_legacy_readonly_admission_unchanged_for_unclaimed(self):
        self.assertTrue(coord.check_path(self.repo, "new_file.py")["allowed"])

    def test_release_only_owner_and_then_claim_required(self):
        self.reserve()
        with self.assertRaises(RuntimeError):
            coord.release(self.repo, "owner-two", "lane-one")
        coord.release(self.repo, "owner-one", "lane-one")
        self.assertEqual(
            coord.check_path(self.repo, "tools/browser_workstation.py", "owner-one", True)["reason"],
            "CLAIM_REQUIRED",
        )

    def test_incomplete_record_blocks_all_writes_and_new_claims(self):
        d = coord.state_root(self.repo) / "incomplete.claim"
        d.mkdir(parents=True)
        self.assertEqual(
            coord.check_path(self.repo, "other.py", "any-agent", True)["reason"],
            "REGISTRY_UNAVAILABLE",
        )
        with self.assertRaisesRegex(RuntimeError, "Incomplete or invalid claim"):
            coord.claim(self.repo, "another", "another-lane", ["other.py"], "Task")

    def test_invalid_and_parent_traversal_denied(self):
        self.assertEqual(coord.check_path(self.repo, "../outside.py")["reason"], "INVALID_PATH")
        self.assertEqual(coord.check_path(self.repo, "C:\\Windows\\System32")["reason"], "INVALID_PATH")

    def test_read_status_requires_explicit_release(self):
        self.reserve("DONE")
        result = coord.check_path(self.repo, "tools/browser_workstation.py")
        self.assertFalse(result["allowed"])
        self.assertEqual(result["owner"], "owner-one")

    def test_independent_claims_coexist(self):
        self.reserve()
        coord.claim(self.repo, "owner-two", "lane-two", ["apps/desktop/renderer.ts"], "UI")
        self.assertTrue(coord.check_path(
            self.repo, "apps/desktop/renderer.ts", "owner-two", True
        )["allowed"])
        self.assertFalse(coord.check_path(
            self.repo, "apps/desktop/renderer.ts", "owner-one", True
        )["allowed"])


if __name__ == "__main__":
    unittest.main()
