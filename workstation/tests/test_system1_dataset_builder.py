from agent.background_review import LearningReview
from workstation.artifacts import ArtifactStore
from workstation.system1.dataset import System1DatasetBuilder


def test_artifact_reconstruction_and_task_split_without_positive_self_certification(tmp_path):
    store = ArtifactStore(tmp_path)
    builder = System1DatasetBuilder(artifact_store=store)
    builder.ingest_learning_review(LearningReview(task_id="t", run_id="r", operation_id="op", actions=["skill saved"]))
    # An arbitrary supplied VERIFIED_SUCCESS string cannot bypass canonical evidence.
    builder.add_progress_sample("t", "r", "op2", "progress", {}, {"done": True}, {}, "progressing", "VERIFIED_SUCCESS")
    before = builder.export_partitions()
    restored = System1DatasetBuilder(artifact_store=ArtifactStore(tmp_path))
    assert restored.export_partitions() == before
    assert not before["train"] and not before["validation"] and not before["held_out"]
    assert len(before["proposals"]) == 2
    assert restored._determine_split("t") == builder._determine_split("t")
    # JSONL is a generated export; deleting/recreating it cannot lose corpus truth.
    paths = restored.write_to_disk(tmp_path / "export")
    assert paths["proposals"].read_text().count("\n") == 2
    assert System1DatasetBuilder(artifact_store=store).export_partitions() == before
