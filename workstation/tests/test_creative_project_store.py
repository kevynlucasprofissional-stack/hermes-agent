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
