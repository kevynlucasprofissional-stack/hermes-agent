"""Durable, source-identified business event outbox in the existing authorized SQLite.

This is NOT a scheduler. A lease expiry never automatically requeues an effect.
Persistence contains metadata references only, not Trello descriptions or secrets.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from uuid import uuid4

_STATES = frozenset({"PENDING", "CLAIMED", "DELIVERED", "UNCERTAIN", "FAILED_SAFE"})
_TERMINALS = frozenset({"DELIVERED", "UNCERTAIN", "FAILED_SAFE"})
_IDENT = re.compile(r"^[A-Za-z0-9_:.-]{1,256}$")


def _id(value: str, label: str) -> str:
    if not isinstance(value, str) or not _IDENT.fullmatch(value):
        raise ValueError(f"invalid {label}")
    return value


def _time(value: datetime | str) -> str:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid observed_at") from exc
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("invalid observed_at")
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _now(now: datetime | None = None) -> str:
    return _time(now if now is not None else datetime.now(timezone.utc))


@dataclass(frozen=True)
class BusinessEventEnvelope:
    source: str
    event_id: str
    event_type: str
    object_id: str
    observed_at: str
    payload_ref: str

    def __post_init__(self) -> None:
        for field in ("source", "event_id", "event_type", "object_id", "payload_ref"):
            _id(getattr(self, field), field)
        _time(self.observed_at)


@dataclass(frozen=True)
class ClaimedEvent:
    source: str
    event_id: str
    route_id: str
    payload_ref: str
    claim_token: str
    job_id: str = ""
    event_type: str = ""
    object_id: str = ""
    observed_at: str = ""


def install_outbox_schema(conn: sqlite3.Connection) -> None:
    """Additive migration; owner supplies canonical connection; no parallel DB.

    Supports the earlier, reference-only outbox schema without dropping rows.
    """
    if conn.in_transaction:
        raise RuntimeError("migration requires no active transaction")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS business_event_outbox (
      source TEXT NOT NULL, event_id TEXT NOT NULL, route_id TEXT NOT NULL,
      payload_ref TEXT NOT NULL,
      event_type TEXT NOT NULL DEFAULT '',
      object_id TEXT NOT NULL DEFAULT '',
      observed_at TEXT NOT NULL DEFAULT '',
      job_id TEXT NOT NULL DEFAULT '',
      state TEXT NOT NULL CHECK(state IN
        ('PENDING','CLAIMED','DELIVERED','UNCERTAIN','FAILED_SAFE')),
      claim_token TEXT,
      attempt_count INTEGER NOT NULL DEFAULT 0,
      claimed_at TEXT, lease_until TEXT,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY(source,event_id,route_id)
    );
    CREATE TABLE IF NOT EXISTS business_event_decision (
      seq INTEGER PRIMARY KEY AUTOINCREMENT,
      source TEXT NOT NULL, event_id TEXT NOT NULL, route_id TEXT NOT NULL,
      decision TEXT NOT NULL,
      from_state TEXT,
      to_state TEXT,
      attempt_count INTEGER NOT NULL,
      at TEXT NOT NULL
    );
    """)
    existing = {r[1] for r in conn.execute("PRAGMA table_info(business_event_outbox)")}
    for column in ("event_type", "object_id", "observed_at", "job_id"):
        if column not in existing:
            conn.execute(f"ALTER TABLE business_event_outbox ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
    for column in ("claimed_at", "lease_until"):
        if column not in existing:
            conn.execute(f"ALTER TABLE business_event_outbox ADD COLUMN {column} TEXT")
    conn.executescript("""
    CREATE INDEX IF NOT EXISTS ix_business_event_outbox_pending
      ON business_event_outbox(state, created_at);
    CREATE INDEX IF NOT EXISTS ix_business_event_outbox_route
      ON business_event_outbox(route_id,state);
    CREATE INDEX IF NOT EXISTS ix_business_event_decision
      ON business_event_decision(source,event_id,route_id,seq);
    """)


def _audit(conn: sqlite3.Connection, *, source: str, event_id: str,
           route_id: str, decision: str, previous: str | None,
           state: str | None, attempt: int, at: str) -> None:
    conn.execute(
        "INSERT INTO business_event_decision "
        "(source,event_id,route_id,decision,from_state,to_state,attempt_count,at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (source,event_id,route_id,decision,previous,state,attempt,at),
    )


def _begin(conn: sqlite3.Connection) -> None:
    if conn.in_transaction:
        raise RuntimeError("outbox operations require a connection without active transaction")
    conn.execute("BEGIN IMMEDIATE")


def enqueue(conn: sqlite3.Connection, envelope: BusinessEventEnvelope, *,
            route_id: str, job_id: str, now: datetime | None = None) -> bool:
    """Insert once per (source,event_id,route_id); reject payload/job substitution."""
    if not isinstance(envelope, BusinessEventEnvelope):
        raise ValueError("trusted BusinessEventEnvelope required")
    route_id, job_id = _id(route_id, "route_id"), _id(job_id, "job_id")
    at = _now(now)
    try:
        _begin(conn)
        cursor = conn.execute(
            "INSERT OR IGNORE INTO business_event_outbox "
            "(source,event_id,route_id,payload_ref,event_type,object_id,observed_at,job_id,state) "
            "VALUES (?,?,?,?,?,?,?,?,'PENDING')",
            (envelope.source,envelope.event_id,route_id,envelope.payload_ref,
             envelope.event_type,envelope.object_id,_time(envelope.observed_at),job_id),
        )
        created = cursor.rowcount == 1
        existing = conn.execute(
            "SELECT payload_ref,event_type,object_id,observed_at,job_id,state,attempt_count "
            "FROM business_event_outbox WHERE source=? AND event_id=? AND route_id=?",
            (envelope.source,envelope.event_id,route_id),
        ).fetchone()
        if not created and existing[:5] != (envelope.payload_ref,envelope.event_type,
                                             envelope.object_id,_time(envelope.observed_at),job_id):
            raise ValueError("conflicting business event identity")
        _audit(conn, source=envelope.source,event_id=envelope.event_id,route_id=route_id,
               decision="ENQUEUED" if created else "DUPLICATE_IGNORED",
               previous=None if created else existing[5], state=existing[5],
               attempt=existing[6], at=at)
        conn.commit()
        return created
    except Exception:
        conn.rollback()
        raise


def claim_next(conn: sqlite3.Connection, *, route_id: str | None = None,
               now: datetime | None = None, lease_seconds: int = 60) -> ClaimedEvent | None:
    """Exclusive SQLite reservation. Only PENDING is eligible; no auto-redelivery."""
    if type(lease_seconds) is not int or not 1 <= lease_seconds <= 3600:
        raise ValueError("invalid lease")
    if route_id is not None:
        route_id = _id(route_id, "route_id")
    when = _now(now)
    until = _time(datetime.fromisoformat(when.replace("Z","+00:00")) + timedelta(seconds=lease_seconds))
    token = uuid4().hex  # claim identity only; event identity is NEVER random
    try:
        _begin(conn)
        where = "state='PENDING'"
        args: tuple[Any,...] = ()
        if route_id is not None:
            where += " AND route_id=?"
            args = (route_id,)
        row = conn.execute(
            "SELECT source,event_id,route_id,payload_ref,job_id,event_type,object_id,observed_at,attempt_count "
            f"FROM business_event_outbox WHERE {where} "
            "ORDER BY created_at,source,event_id,route_id LIMIT 1", args,
        ).fetchone()
        if row is None:
            conn.commit()
            return None
        updated = conn.execute(
            "UPDATE business_event_outbox "
            "SET state='CLAIMED', claim_token=?, attempt_count=attempt_count+1, "
            "claimed_at=?,lease_until=?,updated_at=CURRENT_TIMESTAMP "
            "WHERE source=? AND event_id=? AND route_id=? AND state='PENDING'",
            (token, when, until, row[0],row[1],row[2]),
        )
        if updated.rowcount != 1:
            raise RuntimeError("lost exclusive event claim")
        _audit(conn,source=row[0],event_id=row[1],route_id=row[2],decision="CLAIM_ACQUIRED",
               previous="PENDING",state="CLAIMED",attempt=row[8]+1,at=when)
        conn.commit()
        return ClaimedEvent(row[0],row[1],row[2],row[3],token,
                            job_id=row[4],event_type=row[5],object_id=row[6],observed_at=row[7])
    except Exception:
        conn.rollback()
        raise


def settle(conn: sqlite3.Connection, item: ClaimedEvent, *, state: str,
           evidence_ref: str | None = None,
           independent_verifier: Callable[[ClaimedEvent,str],bool] | None = None,
           now: datetime | None = None) -> bool:
    """Terminalize only this claim. DELIVERED needs separate verifiable evidence.

    The current Cron interface does not supply an event-correlated receipt, so
    ordinary dispatch results MUST use UNCERTAIN, never DELIVERED.
    """
    if state not in _TERMINALS:
        raise ValueError("invalid terminal state")
    if state == "DELIVERED":
        if (not evidence_ref or independent_verifier is None
                or not independent_verifier(item, _id(evidence_ref,"evidence_ref"))):
            raise ValueError("independent delivery evidence is required")
    when = _now(now)
    try:
        _begin(conn)
        current = conn.execute(
            "SELECT attempt_count FROM business_event_outbox "
            "WHERE source=? AND event_id=? AND route_id=? AND claim_token=? AND state='CLAIMED'",
            (item.source,item.event_id,item.route_id,item.claim_token),
        ).fetchone()
        if not current:
            conn.commit()
            return False
        conn.execute(
            "UPDATE business_event_outbox SET state=?, lease_until=NULL,updated_at=CURRENT_TIMESTAMP "
            "WHERE source=? AND event_id=? AND route_id=? AND claim_token=? AND state='CLAIMED'",
            (state,item.source,item.event_id,item.route_id,item.claim_token),
        )
        _audit(conn,source=item.source,event_id=item.event_id,route_id=item.route_id,
               decision="SETTLED_"+state,previous="CLAIMED",state=state,
               attempt=current[0],at=when)
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise


def expire_claims(conn: sqlite3.Connection, *, now: datetime | None = None,
                  route_id: str | None = None) -> int:
    """Reconcile timed-out claims to UNCERTAIN, NEVER PENDING or a second attempt."""
    when = _now(now)
    route_filter = " AND route_id=?" if route_id is not None else ""
    args = (when, _id(route_id, "route_id")) if route_id is not None else (when,)
    try:
        _begin(conn)
        rows = conn.execute(
            "SELECT source,event_id,route_id,attempt_count FROM business_event_outbox "
            "WHERE state='CLAIMED' AND lease_until IS NOT NULL AND lease_until<=?" + route_filter,
            args,
        ).fetchall()
        for source,event_id,route_id,attempt in rows:
            conn.execute(
                "UPDATE business_event_outbox SET state='UNCERTAIN',lease_until=NULL,"
                "updated_at=CURRENT_TIMESTAMP WHERE source=? AND event_id=? AND route_id=? AND state='CLAIMED'",
                (source,event_id,route_id),
            )
            _audit(conn,source=source,event_id=event_id,route_id=route_id,
                   decision="LEASE_EXPIRED_UNCERTAIN",previous="CLAIMED",state="UNCERTAIN",
                   attempt=attempt,at=when)
        conn.commit()
        return len(rows)
    except Exception:
        conn.rollback()
        raise


def read_delivery(conn: sqlite3.Connection, source: str, event_id: str,
                  route_id: str) -> dict[str, Any] | None:
    keys = ("source","event_id","route_id","payload_ref","event_type","object_id",
            "observed_at","job_id","state","attempt_count","claimed_at","lease_until")
    row = conn.execute(
        "SELECT "+",".join(keys)+" FROM business_event_outbox "
        "WHERE source=? AND event_id=? AND route_id=?",
        (_id(source,"source"),_id(event_id,"event_id"),_id(route_id,"route_id")),
    ).fetchone()
    return dict(zip(keys,row)) if row else None


def read_decisions(conn: sqlite3.Connection, *, source: str, event_id: str,
                   limit: int = 100) -> list[dict[str,Any]]:
    if type(limit) is not int or not 1 <= limit <= 250:
        raise ValueError("invalid limit")
    columns = ("route_id","decision","from_state","to_state","attempt_count","at")
    rows = conn.execute(
        "SELECT "+",".join(columns)+" FROM business_event_decision "
        "WHERE source=? AND event_id=? ORDER BY seq LIMIT ?",
        (_id(source,"source"),_id(event_id,"event_id"),limit),
    ).fetchall()
    return [dict(zip(columns,row)) for row in rows]


def reconcile_uncertain(
    conn: sqlite3.Connection,
    *, source: str, event_id: str, route_id: str,
    state: str, evidence_ref: str,
    independent_verifier: Callable[[dict[str, Any],str,str],bool] | None,
    now: datetime | None = None,
) -> bool:
    """Explicit owner-approved *observation*, never replay.

    A verifier must independently establish either delivered (with a durable,
    event-correlated receipt) or provably no effect (FAILED_SAFE). Mere
    claimed/success flags from Cron are not sufficient proof.
    """
    if state not in {"DELIVERED", "FAILED_SAFE"}:
        raise ValueError("reconciliation requires independently verified terminal state")
    if not evidence_ref or independent_verifier is None:
        raise ValueError("independent delivery evidence is required")
    evidence_ref = _id(evidence_ref,"evidence_ref")
    source,event_id,route_id=(_id(source,"source"),_id(event_id,"event_id"),_id(route_id,"route_id"))
    prior=read_delivery(conn,source,event_id,route_id)
    if prior is None or prior["state"] != "UNCERTAIN":
        return False
    if independent_verifier(prior,state,evidence_ref) is not True:
        raise ValueError("independent evidence verification rejected")
    when=_now(now)
    try:
        _begin(conn)
        changed=conn.execute(
            "UPDATE business_event_outbox SET state=?,updated_at=CURRENT_TIMESTAMP "
            "WHERE source=? AND event_id=? AND route_id=? AND state='UNCERTAIN'",
            (state,source,event_id,route_id),
        )
        if changed.rowcount != 1:
            conn.commit()
            return False
        _audit(conn,source=source,event_id=event_id,route_id=route_id,
               decision="RECONCILED_"+state,previous="UNCERTAIN",
               state=state,attempt=prior["attempt_count"],at=when)
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
