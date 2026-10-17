import unittest
from p2_receipt_gate import evaluate

class GateTests(unittest.TestCase):
    def test_legacy_receipt_with_real_ids_and_test_files_rejected(self):
        d={'schema':'hermes.ol_mvp.p1c_result.v1','task_id':'real','run_id':'real', 'native_browser':True,
           'items_compiled':2,'evidence_refs':['workstation/tests/test_P1C_strict_read_acceptance.py'], 'real_llm_calls':None}
        r=evaluate(d)
        self.assertEqual(r['status'], 'REQUIRES_RECONCILIATION')
        self.assertIn('task_id_placeholder',r['reasons'])
        self.assertIn('no_canonical_artifact_refs',r['reasons'])
        self.assertIn('compiled_adoption_unproven',r['reasons'])
        self.assertIn('native_electron_run_unproven',r['reasons'])
    def test_structurally_complete_never_claims_runtime_evidence(self):
        d={'schema':'hermes.ol_mvp.p1c_result.v1','task_id':'t-99','run_id':'r-1', 'evidence_refs':['artifact://tasks/t-99/receipt.json'], 'items_compiled':0, 'real_llm_calls':0}
        r=evaluate(d)
        self.assertEqual(r['status'],'STRUCTURE_ONLY')
        self.assertFalse(r['artifact_integrity_checked'])
        self.assertFalse(r['real_electron_execution_verified'])
    def test_missing_second_run_rejected(self):
        d={'schema':'workstation.ol_mvp.p1c.evidence.v1','first_run':{'task_id':'t-2','run_id':'r-2','items':[]}}
        r=evaluate(d)
        self.assertIn('second_run_unbound',r['reasons'])
        self.assertIn('fewer_than_three_items',r['reasons'])
    def test_unknown_schema_rejected(self):
        self.assertIn('unsupported_schema',evaluate({'schema':'v0'})['reasons'])
    def test_non_object_rejected(self):
        self.assertEqual(evaluate([])['status'],'INVALID')

if __name__=='__main__': unittest.main()
