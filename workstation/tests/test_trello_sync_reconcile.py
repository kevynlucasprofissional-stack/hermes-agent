"""Field-wise Trello sync planning without guessing missing remote data."""
import pytest
from workstation.trello_sync_reconcile import compare_card


def decide(local, remote, baseline=None, observed=None, open_verified=True):
    return compare_card(
        local=local, remote=remote, baseline=baseline,
        observed_fields=observed if observed is not None else ["name"], remote_open_verified=open_verified,
    )


def test_matching_first_observation_does_not_queue_external_effect():
    p = decide({"name": "A"}, {"name": "A"})
    assert p["fields"]["name"]["action"] == "equal"
    assert not p["push"] and not p["pull"] and not p["conflicts"]
    assert p["ready_for_external_write"] is False


def test_first_run_disagreement_preserves_both_versions_without_override():
    p = decide({"name": "Local"}, {"name": "Trello"})
    assert p["status"] == "conflict"
    assert p["conflicts"] == ["name"]
    assert p["fields"]["name"] == {
        "action": "conflict", "reason": "no_verified_baseline",
        "local": "Local", "remote": "Trello", "baseline": None,
    }


def test_remote_only_change_is_pull_after_verified_common_baseline():
    p = decide({"name": "Antes"}, {"name": "Novo"},
               baseline={"name": "Antes"})
    assert p["pull"] == ["name"] and p["push"] == []
    assert p["fields"]["name"]["remote"] == "Novo"


def test_local_only_change_is_push_candidate_not_execution():
    p = decide({"name": "Novo"}, {"name": "Antes"},
               baseline={"name": "Antes"})
    assert p["push"] == ["name"]
    assert p["ready_for_external_write"] is False


def test_two_sided_change_is_conflict_per_field_only():
    p = decide({"name": "Local", "description": "Antiga"},
               {"name": "Trello", "description": "Nova"},
               baseline={"name": "Original", "description": "Antiga"},
               observed=["name", "description"])
    assert p["conflicts"] == ["name"]
    assert p["pull"] == ["description"]
    assert p["fields"]["name"]["baseline"] == "Original"


def test_missing_remote_or_local_field_is_deferred_not_deleted():
    p = decide({"name": "Local", "description": "Exists"}, {"name": "Local"},
               observed=["name", "description"])
    assert p["fields"]["description"]["action"] == "defer"
    assert p["fields"]["description"]["reason"] == "field_unavailable"


@pytest.mark.parametrize("changed", ["remote", "local"])
def test_closed_or_unverified_card_never_pulls_or_pushes(changed):
    local = {"name": "New" if changed == "local" else "Old"}
    remote = {"name": "New" if changed == "remote" else "Old"}
    p = decide(local, remote, baseline={"name": "Old"}, open_verified=False)
    assert p["fields"]["name"]["action"] == "defer"
    assert not p["pull"] and not p["push"]


def test_same_change_both_sides_not_conflict():
    p = decide({"name": "Novo"}, {"name": "Novo"}, baseline={"name": "Antigo"})
    assert p["fields"]["name"]["action"] == "equal"


def test_explicit_null_is_a_value_not_missing():
    p = decide({"due": None}, {"due": None}, observed=["due"])
    assert p["fields"]["due"]["action"] == "equal"


@pytest.mark.parametrize("fields", [[], ["id"], ["name", "name"], ["comments_json"]])
def test_refuses_invalid_or_unobserved_fields(fields):
    with pytest.raises(ValueError):
        decide({"name": "A"}, {"name": "A"}, observed=fields)


def test_rejects_binary_gigantic_and_bool_values():
    for invalid in (b"payload", True, "x" * 20001):
        with pytest.raises(ValueError):
            decide({"name": invalid}, {"name": "A"})


def test_review_history_is_durable_and_idempotent(tmp_path):
    from workstation.trello_sync_reconcile import read_reviews, save_review

    card_id = "6aeb662086d13678d3a28f64"
    url = "https://trello.com/c/gZy747hA/944"
    plan = decide({"name": "Local"}, {"name": "Trello"})
    assert read_reviews(tmp_path, card_id) == []
    created = save_review(
        tmp_path, run_id="qa-trello-20261107", card_id=card_id,
        source_url=url, plan=plan,
    )
    assert created["status"] == "recorded"
    assert save_review(
        tmp_path, run_id="qa-trello-20261107", card_id=card_id,
        source_url=url, plan=plan,
    )["status"] == "unchanged"
    rows = read_reviews(tmp_path, card_id)
    assert len(rows) == 1
    assert rows[0]["plan"]["fields"]["name"]["local"] == "Local"
    assert rows[0]["plan"]["fields"]["name"]["remote"] == "Trello"
    # Same run cannot silently overwrite a review that already exists.
    changed = decide({"name": "Changed"}, {"name": "Trello"})
    assert save_review(
        tmp_path, run_id="qa-trello-20261107", card_id=card_id,
        source_url=url, plan=changed,
    )["error"] == "same_run_changed"
    assert read_reviews(tmp_path, card_id) == rows
    # No new copy of the imported Trello database.
    assert not (tmp_path / "workstation" / "datasets" / "trello.sqlite").exists()


def test_review_store_rejects_untrusted_identity_and_effectful_plan(tmp_path):
    from workstation.trello_sync_reconcile import save_review

    plan = decide({"name": "A"}, {"name": "A"})
    params = {"run_id": "review", "card_id": "6aeb662086d13678d3a28f64",
              "source_url": "https://trello.com/c/gZy747hA/944", "plan": plan}
    for variant in (
        {**params, "card_id": "../../../../tmp/bad"},
        {**params, "source_url": "http://localhost/admin"},
        {**params, "run_id": "../unsafe"},
        {**params, "plan": {**plan, "ready_for_external_write": True}},
    ):
        with pytest.raises(ValueError):
            save_review(tmp_path, **variant)
