from agent.background_review import LearningReview
from workstation.artifacts import ArtifactStore
from workstation.system1.dataset import System1DatasetBuilder
from workstation.control_plane.verification import VerificationEvidence, evaluate_verification
from workstation.control_plane.ir import EQ
from workstation.execution_policy import EvidenceStrength
from workstation.tests.test_system1_capability_routing import _validated_verifier


def test_review_success_is_not_truth_and_real_action_shape_is_normalized(tmp_path):
    builder = System1DatasetBuilder(artifact_store=ArtifactStore(tmp_path))
    samples = builder.ingest_learning_review(LearningReview(task_id="t", run_id="r", status="success",
        actions=["saved skill", {"tool": "danger", "operation_id": "op"}]))
    assert len(samples) == 2
    assert all(s.verification_status == "UNVERIFIED_REVIEW" for s in samples)
    partitions = builder.export_partitions()
    assert not partitions["train"] and not partitions["validation"] and not partitions["held_out"]
    assert len(partitions["proposals"]) == 2
    assert samples[0].provenance["action_shape"] == "str"
    assert samples[1].operation_id == "op" and samples[1].task_id == "t"
    assert not builder.ingest_learning_review(LearningReview(status="empty"))
    error = builder.ingest_learning_review(LearningReview(status="error", actions=["partial action"]))
    assert error[0].verification_status == "FAILED"
    assert len(builder.export_partitions()["counterevidence"]) == 1


def test_review_uses_canonical_verifier_invocation_with_matching_lineage(tmp_path):
    store = ArtifactStore(tmp_path)
    goal = EQ("done", True)
    evidence_ref = store.store("t", "readback.json", {"done": True}).ref
    evidence = VerificationEvidence(evidence_id="source", artifact_ref=evidence_ref, observer="owner.readback",
        source_kind="source_of_record", value={"done": True}, trust_class="trusted_owner",
        evidence_strength=EvidenceStrength.SEMANTIC_PERSISTED_READBACK, covered_predicates=(goal.fingerprint(),),
        task_id="t", run_id="r", operation_id="op")
    verdict = evaluate_verification(_validated_verifier(goal), {"done": True}, [evidence],
        required_predicates={goal.fingerprint()}, expected_task_id="t", expected_run_id="r", expected_operation_id="op")
    assert verdict.verified
    proof_ref = store.store("t", "verification_op.json", {"task_id": "t", "run_id": "r", "operation_id": "op",
        "contract": _validated_verifier(goal).to_dict(), "expected": {"done": True}, "evidence": [evidence.to_dict()],
        "result": verdict.to_dict()}, schema="hermes.canonical_verification.v1").ref
    body = {"task_id": "t", "run_id": "r", "operation_id": "op", "capability_id": "approved-cap",
        "verified": verdict.verified, "verifier_status": verdict.status.value,
        "verifier_fingerprint": verdict.verifier_fingerprint, "freshness_satisfied": verdict.freshness_satisfied,
        "covered_predicates": list(verdict.covered_predicates), "verification_evidence_refs": list(verdict.evidence_refs), "verification_record_ref": proof_ref}
    ref = store.store("t", "invocation_test.json", body, schema="hermes.capability_invocation.v1").ref
    builder = System1DatasetBuilder(artifact_store=store)
    review = LearningReview(task_id="t", run_id="r", operation_id="op", actions=["review finished"], evidence_refs=[ref])
    sample = builder.ingest_learning_review(review)[0]
    assert sample.verification_status == "VERIFIED_SUCCESS"
    assert sample.expected_answers["preferred_candidate"] == "approved-cap"
    assert sample.provenance["source_refs"] == [ref]
    assert sample.provenance["evidence_refs"] == [evidence_ref]
    assert sum(len(builder.export_partitions()[s]) for s in ("train", "validation", "held_out")) == 1
    review.run_id = "wrong-run"
    assert builder.ingest_learning_review(review)[0].verification_status == "UNVERIFIED_REVIEW"
    review.run_id = "r"
    review.status = "error"
    assert builder.ingest_learning_review(review)[0].verification_status == "FAILED"
