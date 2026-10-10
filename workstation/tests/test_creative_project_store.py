import json

import pytest

from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from workstation.creative_project_store import load_creative_revision, save_creative_revision


def test_revisions_preserve_source_and_reopen_only_in_owning_profile(tmp_path):
    token = set_hermes_home_override(tmp_path / "a")
    try:
        first = save_creative_revision({"title": "human source"})
        original = first.source_path.read_bytes()
        second = save_creative_revision({"title": "agent variation"},
                                       project_id=first.project_id, parent_revision=first.revision_id)
        assert first.source_path.read_bytes() == original
        assert second.parent_revision == first.revision_id
        assert second.source_path != first.source_path
        token_b = set_hermes_home_override(tmp_path / "b")
        try:
            with pytest.raises(ValueError, match="missing"):
                load_creative_revision(first.project_id, first.revision_id)
            assert not (tmp_path / "b").exists()
        finally:
            reset_hermes_home_override(token_b)
        assert load_creative_revision(first.project_id, first.revision_id) == first
        assert json.loads(second.source_path.read_bytes())["title"] == "agent variation"
    finally:
        reset_hermes_home_override(token)


def test_external_edits_invalid_paths_and_incomplete_revisions_are_never_overwritten(tmp_path):
    token = set_hermes_home_override(tmp_path / "a")
    try:
        first = save_creative_revision({"title": "original"})
        first.source_path.write_text('{"title":"human edit"}', encoding="utf-8")
        before = set(first.manifest_path.parent.parent.iterdir())
        with pytest.raises(ValueError, match="changed outside"):
            save_creative_revision({"title": "replacement"}, project_id=first.project_id,
                                   parent_revision=first.revision_id)
        assert set(first.manifest_path.parent.parent.iterdir()) == before
        assert json.loads(first.source_path.read_bytes())["title"] == "human edit"
        with pytest.raises(ValueError, match="identifier"):
            load_creative_revision("../escape", first.revision_id)
        first.manifest_path.unlink()
        with pytest.raises(ValueError, match="missing"):
            load_creative_revision(first.project_id, first.revision_id)
    finally:
        reset_hermes_home_override(token)


def test_hyperframes_native_project_persistence_and_etag_conflict_detection(tmp_path):
    token = set_hermes_home_override(tmp_path / "creative_profile")
    try:
        from workstation.creative_project_store import CreativeConflictError

        hf_metadata = {"width": 1920, "height": 1080, "fps": 30, "duration": 120}
        native_files = {
            "index.html": b"<!DOCTYPE html><html><body><div id='root'>Title</div></body></html>",
            "hyperframes.json": json.dumps(hf_metadata).encode("utf-8"),
        }

        # Save initial HyperFrames revision
        rev1 = save_creative_revision(
            hf_metadata,
            engine="hyperframes",
            native_files=native_files,
        )
        assert rev1.engine == "hyperframes"
        assert rev1.etag.startswith('"')
        assert len(rev1.native_files) == 2
        
        # Read back and verify integrity
        loaded1 = load_creative_revision(rev1.project_id, rev1.revision_id)
        assert loaded1 == rev1
        assert (loaded1.manifest_path.parent / "index.html").read_bytes() == native_files["index.html"]

        # Human edit to index.html with matching etag
        updated_native = {
            "index.html": b"<!DOCTYPE html><html><body><div id='root'>Human Edited Title</div></body></html>",
            "hyperframes.json": json.dumps(hf_metadata).encode("utf-8"),
        }
        rev2 = save_creative_revision(
            hf_metadata,
            project_id=rev1.project_id,
            parent_revision=rev1.revision_id,
            engine="hyperframes",
            native_files=updated_native,
            if_match=rev1.etag,
        )
        assert rev2.parent_revision == rev1.revision_id
        assert rev2.etag != rev1.etag

        # Concurrent edit attempting to use stale rev1.etag must fail with CreativeConflictError (409)
        with pytest.raises(CreativeConflictError, match="409 Conflict: ETag mismatch"):
            save_creative_revision(
                hf_metadata,
                project_id=rev1.project_id,
                parent_revision=rev2.revision_id,
                engine="hyperframes",
                native_files=updated_native,
                if_match=rev1.etag,  # Stale ETag!
            )

        # Incomplete native files must fail validation
        with pytest.raises(ValueError, match="must include index.html and hyperframes.json"):
            save_creative_revision(
                hf_metadata,
                engine="hyperframes",
                native_files={"only_one_file.txt": b"missing required files"},
            )
    finally:
        reset_hermes_home_override(token)
