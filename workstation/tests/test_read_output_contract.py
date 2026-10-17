"""P1B isolated candidate tests; do not confuse with native TaskRun integration."""
import unittest

from workstation.experience_compiler.read_output_contract import (
    READ_SHAPE,
    UnverifiedRead,
    guarded_projection,
    prepare_read_shape,
)


DOM_ROWS = [
    {"id": "ol-card-a", "list": "A fazer", "title": "Planejar pauta semanal", "description": "Conferir temas e fontes"},
    {"id": "ol-card-b", "list": "Em andamento", "title": "Revisar legenda", "description": "Verificar texto e CTA"},
    {"id": "ol-card-c", "list": "Revisao", "title": "Publicar carrossel", "description": "Confirmar arte final"},
]
EXTRACTED = {
    "success": True, "result": {"success": True, "items": [
        {"attributes": {"data-card-id": row["id"], "data-list": row["list"]},
         "text": row["title"] + row["description"]} for row in DOM_ROWS
    ]}
}
RECEIPT = {
    "task_id": "t", "run_id": "r", "operation_id": "o",
    "raw_result_ref": "artifact://tasks/t/raw.json",
    "observer": "workstation.browser_live_dom",
    "source_kind": "browser_live_dom",
    "trust_class": "trusted_runtime",
    "independent_readback": True, "status": "VERIFIED",
}


class ReadOutputContractTests(unittest.TestCase):
    def test_verified_shape_does_not_store_card_text(self):
        p = guarded_projection(EXTRACTED, DOM_ROWS, task_id="t", run_id="r",
            operation_id="o", raw_result_ref="artifact://tasks/t/raw.json",
            owner_readback_receipt=RECEIPT)
        self.assertEqual(p["semantic_predicates"]["read.output_shape"], READ_SHAPE)
        self.assertEqual(p["semantic_predicates"]["read.fields_complete"], True)
        self.assertEqual(p["result_count"], 3)
        self.assertNotIn("Planejar", str(p))
        self.assertNotIn("ol-card-a", str(p))

    def test_different_card_content_same_generalizable_contract(self):
        updated = [dict(row, id=row["id"]+"-2", title=row["title"]+" 2") for row in DOM_ROWS]
        extracted = {"items": [
            {"attributes": {"data-card-id": row["id"], "data-list": row["list"]},
             "text": row["title"]+row["description"]} for row in updated
        ]}
        a, b = prepare_read_shape(EXTRACTED, DOM_ROWS), prepare_read_shape(extracted, updated)
        self.assertEqual(a["semantic_predicates"], b["semantic_predicates"])
        self.assertNotEqual(a["result_digest"], b["result_digest"])

    def test_missing_or_wrong_readback_fails_closed(self):
        bad = [dict(r) for r in DOM_ROWS]
        bad[0]["title"] = "Texto divergente"
        with self.assertRaises(UnverifiedRead):
            prepare_read_shape(EXTRACTED, bad)
        with self.assertRaises(UnverifiedRead):
            prepare_read_shape(EXTRACTED, bad[:-1])

    def test_mismatched_identity_or_verifier_is_not_admitted(self):
        for patch in ({"run_id": "another"}, {"trust_class": "untrusted"},
                      {"status": "INCONCLUSIVE"}, {"independent_readback": False}):
            receipt = {**RECEIPT, **patch}
            with self.assertRaises(UnverifiedRead):
                guarded_projection(EXTRACTED, DOM_ROWS, task_id="t", run_id="r",
                    operation_id="o", raw_result_ref="artifact://tasks/t/raw.json",
                    owner_readback_receipt=receipt)

    def test_duplicate_cards_or_missing_result_rejected(self):
        with self.assertRaises(UnverifiedRead):
            prepare_read_shape({"items": EXTRACTED["result"]["items"][:2] + [
                EXTRACTED["result"]["items"][0]]}, DOM_ROWS)
        with self.assertRaises(UnverifiedRead):
            prepare_read_shape({"items": []}, [])


if __name__ == "__main__":
    unittest.main()
