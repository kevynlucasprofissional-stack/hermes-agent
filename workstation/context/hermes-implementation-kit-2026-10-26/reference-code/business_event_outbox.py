"""Reference-only durable event outbox, without a second scheduler.

The intended consumer resolves a *pre-authorized* route to the existing Hermes
execute_job_for_event(). A CLAIMED action is NEVER retried automatically after a
crash: an authorized reconciler must first decide if side effects occurred.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from uuid import uuid4

VALID_TERMINALS = {"DELIVERED", "UNCERTAIN", "FAILED_SAFE"}


@dataclass(frozen=True)
class ClaimedEvent:
    source: str
    event_id: str
    route_id: str
    payload_ref: str
    claim_token: str


def install_outbox_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS business_event_outbox (
            source TEXT NOT NULL,
            event_id TEXT NOT NULL,
            route_id TEXT NOT NULL,
            payload_ref TEXT NOT NULL,
            state TEXT NOT NULL CHECK (state IN ('PENDING','CLAIMED','DELIVERED','UNCERTAIN','FAILED_SAFE')),
            claim_token TEXT,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (source, event_id, route_id)
        );
        CREATE INDEX IF NOT EXISTS ix_business_event_outbox_pending
        ON business_event_outbox(state, created_at);
    """)


def _id(value: str, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 256 or '\x00' in value:
        raise ValueError(f'invalid {label}')
    return value


def enqueue(conn: sqlite3.Connection, *, source: str, event_id: str, route_id: str, payload_ref: str) -> bool:
    """Bounded insert without storing third-party text; returns False for duplicate."""
    source = _id(source, 'source'); event_id = _id(event_id, 'event_id')
    route_id = _id(route_id, 'route_id'); payload_ref = _id(payload_ref, 'payload_ref')
    with conn:
        row = conn.execute(
            "INSERT OR IGNORE INTO business_event_outbox "
            "(source,event_id,route_id,payload_ref,state) VALUES (?,?,?,?,'PENDING')",
            (source, event_id, route_id, payload_ref))
        return row.rowcount == 1


def claim_next(conn: sqlite3.Connection) -> ClaimedEvent | None:
    """Atomically reserve one PENDING event. Never auto-reclaim CLAIMED/UNCERTAIN."""
    if conn.in_transaction:
        raise RuntimeError('must claim outside an existing transaction')
    token = uuid4().hex
    try:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute("SELECT source,event_id,route_id,payload_ref FROM business_event_outbox "
                           "WHERE state='PENDING' ORDER BY created_at,source,event_id LIMIT 1").fetchone()
        if row is None:
            conn.commit()
            return None
        conn.execute("UPDATE business_event_outbox SET state='CLAIMED',claim_token=?, "
                     "attempt_count=attempt_count+1,updated_at=CURRENT_TIMESTAMP "
                     "WHERE source=? AND event_id=? AND route_id=? AND state='PENDING'",
                     (token, row[0], row[1], row[2]))
        conn.commit()
        return ClaimedEvent(*row, token)
    except Exception:
        conn.rollback()
        raise


def settle(conn: sqlite3.Connection, item: ClaimedEvent, *, state: str) -> bool:
    """Trusted dispatcher decides terminal state only after sufficient evidence."""
    if state not in VALID_TERMINALS:
        raise ValueError('invalid terminal state')
    with conn:
        cur = conn.execute(
            'UPDATE business_event_outbox SET state=?,updated_at=CURRENT_TIMESTAMP '
            'WHERE source=? AND event_id=? AND route_id=? AND claim_token=? AND state=\'CLAIMED\'',
            (state, item.source, item.event_id, item.route_id, item.claim_token))
        return cur.rowcount == 1
