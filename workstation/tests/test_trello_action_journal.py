import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reference-code'))
from workstation.trello_action_journal import append_batch, install_schema, load_checkpoint, read_events


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


def test_checkpoint_never_regresses_under_stale_parallel_poller():
    conn = db()
    append_batch(conn, 'board-1', [event(i='c1')], completed_checkpoint='c1')
    append_batch(conn, 'board-1', [event(i='c9')], completed_checkpoint='c9')
    stale = append_batch(conn, 'board-1', [event(i='c2')], completed_checkpoint='c2')
    assert load_checkpoint(conn, 'board-1') == 'c9'
    assert stale.checkpoint == 'c9'


def test_read_events_projects_board_id_and_utc_day_without_raw_text():
    from workstation.trello_action_journal import read_events_for_day
    conn = db()
    append_batch(conn, 'board-1', [
        event(i='a1', data={'card': {'id': 'card-1', 'desc': 'SECRET'}, 'text': 'SECRET_COMMENT'})
    ])
    events = read_events(conn, 'board-1')
    assert events[0]['board_id'] == 'board-1'
    assert 'SECRET' not in str(events)
    assert all(row['board_id'] == 'board-1' for row in read_events_for_day(conn, 'board-1', '2026-10-26'))
    assert read_events_for_day(conn, 'board-1', '2026-10-25') == []
    with pytest.raises(ValueError, match='day'):
        read_events_for_day(conn, 'board-1', '2026-99-99')


def test_persistence_after_restart_on_same_sqlite_file(tmp_path):
    filename = tmp_path / 'canonical-kanban-test.db'
    first = sqlite3.connect(filename)
    install_schema(first)
    append_batch(first, 'board-1', [event(i='a1')], completed_checkpoint='a1')
    first.close()
    second = sqlite3.connect(filename)
    install_schema(second)
    assert load_checkpoint(second, 'board-1') == 'a1'
    assert len(read_events(second, 'board-1')) == 1
    assert append_batch(second, 'board-1', [event(i='a1')], completed_checkpoint='a1').inserted == 0
    assert len(read_events(second, 'board-1')) == 1
    second.close()


def test_invalid_timestamp_cannot_advance_cursor_or_insert():
    conn = db()
    with pytest.raises(ValueError, match='event_time'):
        append_batch(conn, 'board-1', [event(date='not-a-date')], completed_checkpoint='c9')
    assert load_checkpoint(conn, 'board-1') is None
    assert read_events(conn, 'board-1') == []


def test_attacker_supplied_nested_metadata_does_not_leak_through_ids():
    conn = db()
    append_batch(conn, 'board-1', [
        event(idMemberCreator={'token': 'SECRET_ACTOR'}, data={
            'card': {'id': {'password': 'SECRET_CARD'}},
            'listBefore': {'id': 'ok-list'}, 'text': 'SECRET_COMMENT'
        })
    ])
    assert 'SECRET_' not in str(read_events(conn, 'board-1'))


def test_day_query_includes_exact_utc_midnight_boundary():
    from workstation.trello_action_journal import read_events_for_day
    conn = db()
    append_batch(conn, 'board-1', [
        event(i='midnight-1', date='2026-10-26T00:00:00Z'),
        event(i='before-1', date='2026-10-25T23:59:59Z'),
    ])
    rows = read_events_for_day(conn, 'board-1', '2026-10-26')
    assert [row['action_id'] for row in rows] == ['midnight-1']


def test_schema_migration_preserves_existing_canonical_tasks_table():
    conn = sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT)')
    conn.execute("INSERT INTO tasks VALUES ('legacy-1','Preserve me')")
    conn.commit()
    install_schema(conn)
    install_schema(conn)
    assert conn.execute("SELECT title FROM tasks WHERE id='legacy-1'").fetchone() == ('Preserve me',)
    assert conn.execute("SELECT COUNT(*) FROM trello_activity_event").fetchone()[0] == 0
    # Reverse migration SQL (operator-only) touches ONLY Trello tables:
    conn.executescript('DROP INDEX IF EXISTS ix_trello_activity_time;'
                       'DROP TABLE IF EXISTS trello_activity_event;'
                       'DROP TABLE IF EXISTS trello_activity_checkpoint;')
    assert conn.execute("SELECT title FROM tasks WHERE id='legacy-1'").fetchone() == ('Preserve me',)


def test_sql_write_failure_rolls_back_event_and_checkpoint_atomically():
    conn = db()
    conn.executescript("""
        CREATE TRIGGER trello_test_reject BEFORE INSERT ON trello_activity_event
        WHEN NEW.action_id='bad-action'
        BEGIN SELECT RAISE(ABORT, 'test failure'); END;
    """)
    with pytest.raises(sqlite3.DatabaseError):
        append_batch(conn, 'board-1', [event(i='ok-action'), event(i='bad-action')], completed_checkpoint='c9')
    assert read_events(conn, 'board-1') == []
    assert load_checkpoint(conn, 'board-1') is None
