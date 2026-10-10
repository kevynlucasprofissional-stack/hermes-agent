"""Flagship scenario E3 integration test (DF-024, D-041, D-042).

Proves:
- Shared project model between human and AI
- Optimistic concurrency control (ETag 409 conflict detection)
- Conflict reconciliation via re-inspection
- Real action traces entry into canonical ExperienceCorpus via journal/artifacts
"""
import json
from pathlib import Path
import pytest

from gateway.session_context import scoped_current_session_id
from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from tools.approval_context import reset_current_session_key, set_current_session_key
from workstation.artifacts import ArtifactStore
from workstation.config import WorkstationConfig
from workstation.creative_operations import (
    CreativeOperation,
    apply_creative_operation,
    inspect_project,
)
from workstation.creative_project_store import (
    CreativeConflictError,
    save_creative_revision,
)
from workstation.experience_compiler.corpus import ExperienceCorpus
from workstation.journal import ExecutionJournal
from workstation.tests.test_creative_project_runtime import _task


def test_flagship_e3_creative_coedit_concurrency_and_corpus_observation(tmp_path, monkeypatch):
    home = tmp_path / "profile"
    monkeypatch.setenv("HERMES_KANBAN_DB", str(home / "kanban.db"))
    ht = set_hermes_home_override(home)
    st = set_current_session_key("approval-key")
    try:
        with scoped_current_session_id("durable-session"):
            context = _task(home)
            config = WorkstationConfig({"creative": {"enabled": True, "hyperframes_enabled": True}})

            # 1. Human creates initial HyperFrames project
            hf_meta = {"width": 1920, "height": 1080, "fps": 30, "duration": 60}
            initial_html = "<!DOCTYPE html><html><body><div id=\"root\"></div></body></html>"
            native = {
                "index.html": initial_html.encode("utf-8"),
                "hyperframes.json": json.dumps(hf_meta).encode("utf-8"),
            }
            rev_human = save_creative_revision(hf_meta, engine="hyperframes", native_files=native)
            initial_etag = rev_human.etag

            # 2. Agent inspects project
            inspection = inspect_project(rev_human)
            assert inspection["etag"] == initial_etag
            assert inspection["engine"] == "hyperframes"

            # 3. Agent applies typed creative operation
            op_title = CreativeOperation(
                kind="add_element",
                project_id=rev_human.project_id,
                parent_revision_id=rev_human.revision_id,
                if_match=initial_etag,
                params={
                    "tag": "h1",
                    "element_id": "title-e3",
                    "text": "E3 Dogfood Headline",
                    "styles": {"color": "#ff0000", "font-size": "32px"},
                },
            )
            rev_agent1, details1 = apply_creative_operation(config, context, op_title)
            assert rev_agent1.etag != initial_etag
            assert details1["added_element_id"] == "title-e3"

            # 4. Human simultaneously makes a concurrent change or agent uses stale ETag
            stale_op = CreativeOperation(
                kind="add_element",
                project_id=rev_agent1.project_id,
                parent_revision_id=rev_agent1.revision_id,
                if_match=initial_etag,  # Stale ETag!
                params={
                    "tag": "p",
                    "element_id": "sub-stale",
                    "text": "Stale concurrent edit",
                },
            )
            with pytest.raises(CreativeConflictError, match="409 Conflict"):
                apply_creative_operation(config, context, stale_op)

            # 5. Conflict resolution: agent re-inspects to acquire latest ETag and re-applies
            reinspection = inspect_project(rev_agent1)
            fresh_etag = reinspection["etag"]
            assert fresh_etag == rev_agent1.etag

            resolved_op = CreativeOperation(
                kind="add_element",
                project_id=rev_agent1.project_id,
                parent_revision_id=rev_agent1.revision_id,
                if_match=fresh_etag,
                params={
                    "tag": "p",
                    "element_id": "sub-resolved",
                    "text": "Resolved subtitle",
                },
            )
            rev_agent2, details2 = apply_creative_operation(config, context, resolved_op)
            assert rev_agent2.etag != fresh_etag

            # 6. Read back final HTML and verify both edits are preserved
            final_html = (rev_agent2.manifest_path.parent / "index.html").read_text(encoding="utf-8")
            assert 'data-hf-id="title-e3"' in final_html
            assert "E3 Dogfood Headline" in final_html
            assert 'data-hf-id="sub-resolved"' in final_html
            assert "Resolved subtitle" in final_html

            # 7. Trace observation into canonical ExperienceCorpus
            journal = ExecutionJournal(task_id=context.task_id, session_id=context.session_id)
            artifacts = ArtifactStore()
            corpus = ExperienceCorpus(artifacts, discover=False)
            corpus.ingest_journal(journal)

            samples = corpus.query()
            assert len(samples) >= 1
            creative_samples = [s for s in samples if s.operation.canonical_route == "creative_studio"]
            assert len(creative_samples) >= 1
            sample = creative_samples[0]
            assert sample.provenance.task_id == context.task_id
            assert sample.provenance.runtime == "hyperframes-studio"
            assert sample.verification.status == "VERIFIED"
    finally:
        reset_current_session_key(st)
        reset_hermes_home_override(ht)
