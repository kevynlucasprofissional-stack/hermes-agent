import pytest
from workstation.page_watch_event_bridge import check_page_event_candidate, page_watch_outbox_gate


def fixture():
    return {
        "source": "page_watch", "type": "page_changed", "event_id": "a"*64,
        "watch_id": "watch1", "session_id": "sess1", "tab_id": "tab1",
        "origin": "https://fixture.example", "route_id": "route1",
        "fingerprint": "b"*64, "observed_at": "2026-10-27T18:00:00.000Z",
        "previous": 2, "current": 3,
    }


def test_page_changed_fails_closed_because_p04_only_qualified_trello():
    data = page_watch_outbox_gate(fixture(), "route1")
    assert data["state"] == "HOLD"
    assert data["reason"] == "P04_PAGE_WATCH_SOURCE_NOT_QUALIFIED"
    assert set(data) == {"state", "reason", "source", "event_id", "route_id"}


def test_event_never_accepts_private_text():
    row = fixture()
    row["comment"] = "password=secret"
    with pytest.raises(ValueError, match="invalid_page_watch_event"):
        check_page_event_candidate(row, "route1")


@pytest.mark.parametrize("field,value", [
    ("source", "trello"), ("type", "createCard"),
    ("route_id", "otherroute"), ("origin", "https://fixture.example/login"),
    ("event_id", "bad"), ("fingerprint", "c"*65),
    ("watch_id", "private user email"), ("current", -1),
    ("observed_at", "unknown"),
])
def test_invalid_event_fails_closed(field, value):
    row = fixture()
    row[field] = value
    with pytest.raises((ValueError, PermissionError)):
        page_watch_outbox_gate(row, "route1")


def test_does_not_call_p04_even_if_existing_cron_job_was_provided(monkeypatch):
    from workstation import business_event_outbox
    invoked = []
    monkeypatch.setattr(business_event_outbox, "enqueue",
                        lambda *args, **kwargs: invoked.append((args,kwargs)))
    assert page_watch_outbox_gate(fixture(), "route1")["state"] == "HOLD"
    assert invoked == []
