from dataclasses import replace

import pytest

from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from workstation.creative_project_store import load_creative_revision, save_creative_revision
from workstation.creative_remotion_source import RemotionInvitation, remotion_native_files


def test_remotion_source_preserves_text_and_engine_across_revisions(tmp_path):
    token = set_hermes_home_override(tmp_path / "profile")
    try:
        invitation = RemotionInvitation("<script>text, not code</script>", "Human design", "08 October")
        native = remotion_native_files()
        first = save_creative_revision(invitation.to_source(), engine="remotion", native_files=native)
        second = save_creative_revision(replace(invitation, subtitle="Agent variation").to_source(),
            project_id=first.project_id, parent_revision=first.revision_id, engine="remotion", native_files=native)
        assert load_creative_revision(second.project_id, second.revision_id).engine == "remotion"
        assert second.parent_revision == first.revision_id
        import json
        assert RemotionInvitation.from_source(json.loads(first.source_path.read_bytes())) == invitation
        with pytest.raises(ValueError, match="engine cannot change"):
            save_creative_revision({}, project_id=first.project_id, parent_revision=first.revision_id)
        human_source = first.source_path.parent / "Invitation.tsx"
        human_source.write_text("// human edit retained", encoding="utf-8")
        with pytest.raises(ValueError, match="native source was changed"):
            save_creative_revision(invitation.to_source(), project_id=first.project_id,
                parent_revision=first.revision_id, engine="remotion", native_files=native)
        assert human_source.read_text(encoding="utf-8") == "// human edit retained"
    finally:
        reset_hermes_home_override(token)


def test_invalid_timeline_geometry_and_executable_fields_refuse_before_save():
    invitation = RemotionInvitation("Hermes", "Invitation", "08 October")
    for candidate in (replace(invitation, fps=True), replace(invitation, width=361),
                      replace(invitation, duration_seconds=31), replace(invitation, logo_radius=float("nan")),
                      replace(invitation, accent="url(https://example.com)")):
        with pytest.raises(ValueError):
            candidate.to_source()
    source = invitation.to_source()
    source["props"]["script"] = "arbitrary code"
    with pytest.raises(ValueError, match="property"):
        RemotionInvitation.from_source(source)
