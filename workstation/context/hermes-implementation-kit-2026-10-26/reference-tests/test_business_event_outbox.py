import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reference-code'))
from business_event_outbox import install_outbox_schema, enqueue, claim_next, settle, ClaimedEvent


def db():
    x = sqlite3.connect(':memory:')
    install_outbox_schema(x)
    return x


def test_exact_event_route_duplicate_is_rejected():
    x=db()
    params=dict(source='trello',event_id='act1',route_id='daily',payload_ref='trello:act1')
    assert enqueue(x,**params)
    assert not enqueue(x,**params)


def test_claimed_event_is_not_claimed_twice_after_crash():
    x=db()
    enqueue(x,source='trello',event_id='act1',route_id='daily',payload_ref='trello:act1')
    first=claim_next(x)
    assert first is not None
    assert claim_next(x) is None
    # No stale-claim auto recovery: explicit human/source reconciliation required.


def test_valid_terminal_requires_matching_token_and_no_repeat():
    x=db()
    enqueue(x,source='trello',event_id='act1',route_id='daily',payload_ref='trello:act1')
    item=claim_next(x)
    wrong=ClaimedEvent(item.source,item.event_id,item.route_id,item.payload_ref,'bad-token')
    assert settle(x,wrong,state='DELIVERED') is False
    assert settle(x,item,state='UNCERTAIN')
    assert not settle(x,item,state='DELIVERED')
    assert claim_next(x) is None


def test_separate_routes_have_distinct_claims():
    x=db()
    for route in ['daily','alert']:
        assert enqueue(x,source='trello',event_id='act1',route_id=route,payload_ref='trello:act1')
    assert claim_next(x) is not None
    assert claim_next(x) is not None
    assert claim_next(x) is None
