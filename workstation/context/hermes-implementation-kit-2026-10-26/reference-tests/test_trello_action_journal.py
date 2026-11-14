import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reference-code'))
from trello_action_journal import append_batch, install_schema, load_checkpoint, read_events


def event(i='act-1', **more):
    return {'id': i, 'type': 'updateCard', 'date': '2026-10-26T18:00:00Z',
            'idMemberCreator': 'actor-7', 'data': {'card': {'id': 'card-1'},
            'listBefore': {'id': 'todo'}, 'listAfter': {'id': 'done'},
            'text': 'SHOULD NOT BE SAVED'}, **more}


def db():
    conn = sqlite3.connect(':memory:')
    install_schema(conn)
    return conn


def test_duplicate_action_is_deduplicated_and_checkpoint_kept():
    conn = db()
    assert append_batch(conn, 'board-1', [event()], completed_checkpoint='c1').inserted == 1
    assert append_batch(conn, 'board-1', [event()], completed_checkpoint='c2').duplicates == 1
    assert load_checkpoint(conn, 'board-1') == 'c2'
    assert len(read_events(conn, 'board-1')) == 1


def test_failed_validation_does_not_advance_checkpoint_or_write_partial_rows():
    conn = db()
    append_batch(conn, 'board-1', [], completed_checkpoint='c0')
    with pytest.raises(ValueError, match='action_id'):
        append_batch(conn, 'board-1', [event(), event(i='')], completed_checkpoint='c1')
    assert load_checkpoint(conn, 'board-1') == 'c0'
    assert read_events(conn, 'board-1') == []


def test_whitelisted_metadata_does_not_persist_message_bodies():
    conn = db()
    append_batch(conn, 'board-1', [event(data={'card': {'id': 'card-1'}, 'text': 'SECRET_COMMENT'})])
    assert 'SECRET_COMMENT' not in str(read_events(conn, 'board-1'))


def test_events_can_coexist_across_boards_and_paging_is_bounded():
    conn = db()
    append_batch(conn, 'board-1', [event()])
    append_batch(conn, 'board-2', [event()])
    assert len(read_events(conn, 'board-1')) == 1
    assert len(read_events(conn, 'board-2')) == 1
    with pytest.raises(ValueError, match='invalid limit'):
        read_events(conn, 'board-1', limit=999999)


def test_existing_transaction_requires_explicit_owner_and_rolls_back():
    conn = db()
    conn.execute('BEGIN')
    with pytest.raises(RuntimeError):
        append_batch(conn, 'board-1', [event()])
    conn.rollback()
