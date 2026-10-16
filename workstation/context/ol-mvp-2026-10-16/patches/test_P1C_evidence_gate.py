"""Pure unit tests for P1C receipt structure; NOT a native Electron E2E."""
import unittest

from P1C_evidence_gate import SCHEMA, assess


def item(n, route="adaptive"):
    return {
        "item_id": f"w{n}", "card_id": f"c{n}", "operation_id": f"o{n}",
        "route": route, "source": "canonical_runtime", "status": "VERIFIED",
        "readback_ref": f"artifact://tasks/t/read_{n}.json",
        "raw_result_ref": f"artifact://tasks/t/raw_{n}.json",
    }


def manifest():
    return {
        "schema": SCHEMA, "execution_surface": "electron_native",
        "evidence_origin": "canonical_runtime",
        "first_run": {
            "task_id": "t", "run_id": "r1", "entrypoint": "desktop_chat",
            "items": [item(1), item(2, "compiled"), item(3, "compiled")],
            "candidate_ref": "artifact://tasks/t/candidate.json",
            "qualified_offer_ref": "artifact://tasks/t/offer.json",
            "adoption_receipt_ref": "artifact://tasks/t/adopt.json",
            "qualification_mode": "DIRECT_AUTHORIZED",
        },
        "second_run": {
            "task_id": "t2", "run_id": "r2", "entrypoint": "native_work_execute",
            "items": [item(4, "compiled"), item(5, "compiled"), item(6, "compiled")],
            "capability_lookup_ref": "artifact://tasks/t2/lookup.json",
            "adoption_receipt_ref": "artifact://tasks/t2/adopt.json",
        },
        "provider_usage": {"real_llm_calls": None, "provider_usage_ref": None},
    }


class P1CEvidenceGateTests(unittest.TestCase):
    def test_structurally_complete_does_not_claim_authenticity(self):
        result = assess(manifest())
        self.assertEqual(result["status"], "READY_FOR_HUMAN_EVIDENCE_REVIEW")
        self.assertEqual(result["evidence_authenticity"], "NOT_CHECKED")
        self.assertFalse(result["real_provider_usage_supported"])
        self.assertFalse(result["stage_a_qualified"])

    def test_mock_dispatch_and_all_adaptive_do_not_qualify(self):
        sample = manifest()
        sample["evidence_origin"] = "synthetic_fixture"
        sample["first_run"]["items"] = [item(1), item(2), item(3)]
        result = assess(sample)
        self.assertEqual(result["status"], "PARTIAL_OR_HOLD")
        self.assertIn("inflight_reuse_not_demonstrated", result["reasons"])

    def test_candidate_without_adoption_receipt_does_not_qualify(self):
        sample = manifest()
        sample["first_run"]["adoption_receipt_ref"] = None
        self.assertIn("real_adoption_receipt_missing", assess(sample)["reasons"])

    def test_run_two_must_be_distinct(self):
        sample = manifest()
        sample["second_run"]["task_id"] = "t"
        sample["second_run"]["run_id"] = "r1"
        self.assertIn("second_run_identity_not_new", assess(sample)["reasons"])

    def test_shadow_does_not_qualify_direct(self):
        sample = manifest()
        sample["first_run"]["qualification_mode"] = "SHADOW"
        self.assertIn("direct_qualification_unverified", assess(sample)["reasons"])

    def test_duplicate_or_unverified_work_item_rejected(self):
        sample = manifest()
        sample["first_run"]["items"][1]["item_id"] = "w1"
        self.assertIn("first_run_missing_canonical_three_items", assess(sample)["reasons"])
        sample = manifest()
        sample["first_run"]["items"][1]["readback_ref"] = None
        self.assertIn("first_run_missing_canonical_three_items", assess(sample)["reasons"])


if __name__ == "__main__":
    unittest.main()
