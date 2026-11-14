"""P06-R reference prototype only; NOT imported into Hermes runtime.

Use the caller's approved canonical SQLite database, not another scheduler.
The BrowserTask owner must provide stable activation/observation identifiers.
"""
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass

VALID = re.compile(r"^[a-zA-Z0-9_.:-]{1,128}$")


@dataclass(frozen=True)
class Occurrence:
    event_id: str
    watch_id: str
    activation_key: str
    observation_key: str
    sequence: int
    previous: int
    current: int
    route_id: str
    state: str


def migrate(conn: sqlite3.Connection) -> None:
    if conn.in_transaction:
        raise RuntimeError("active transaction")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS p06_watch_sequence(
       watch_id TEXT PRIMARY KEY,
       last_sequence INTEGER NOT NULL CHECK(last_sequence>=0)
    );
    CREATE TABLE IF NOT EXISTS p06_watch_occurrence(
       watch_id TEXT NOT NULL,
       activation_key TEXT NOT NULL,
       observation_key TEXT NOT NULL,
       sequence INTEGER NOT NULL CHECK(sequence>0),
       event_id TEXT NOT NULL UNIQUE,
       previous INTEGER NOT NULL CHECK(previous BETWEEN 0 AND 1000),
       current INTEGER NOT NULL CHECK(current BETWEEN 0 AND 1000),
       route_id TEXT NOT NULL,
       state TEXT NOT NULL DEFAULT 'PENDING'
         CHECK(state IN ('PENDING','OUTBOX_ACCEPTED','UNCERTAIN')),
       PRIMARY KEY(watch_id,activation_key,observation_key),
       UNIQUE(watch_id,sequence)
    );
    CREATE INDEX IF NOT EXISTS ix_p06_watch_pending
      ON p06_watch_occurrence(state,watch_id,sequence);
    """)


def reserve(conn: sqlite3.Connection, *, watch_id: str, activation_key: str,
            observation_key: str, route_id: str, previous: int, current: int) -> Occurrence:
    """BEGIN IMMEDIATE + stable occurrence key -> durable sequence and immutable id.

    A crash after commit leaves PENDING; publish only after commit. Replaying an
    already recorded observation returns exactly the first event id. A new
    activation/observation key creates a new identity even for 1->2 repeated.
    """
    for field in (watch_id,activation_key,observation_key,route_id):
        if not isinstance(field,str) or not VALID.fullmatch(field):
            raise ValueError("untrusted identity")
    if any(type(x) is not int or not 0 <= x <= 1000 for x in (previous,current)) or previous==current:
        raise ValueError("invalid structural counts")
    if conn.in_transaction:
        raise RuntimeError("active transaction")
    conn.execute("BEGIN IMMEDIATE")
    try:
        old=conn.execute(
            "SELECT event_id,sequence,previous,current,route_id,state "
            "FROM p06_watch_occurrence WHERE watch_id=? AND activation_key=? AND observation_key=?",
            (watch_id,activation_key,observation_key)).fetchone()
        if old:
            if (old[2],old[3],old[4])!=(previous,current,route_id):
                raise ValueError("conflicting event replay")
            conn.commit()
            return Occurrence(old[0],watch_id,activation_key,observation_key,
                              old[1],previous,current,route_id,old[5])
        conn.execute("INSERT OR IGNORE INTO p06_watch_sequence VALUES (?,0)",(watch_id,))
        conn.execute("UPDATE p06_watch_sequence SET last_sequence=last_sequence+1 WHERE watch_id=?",(watch_id,))
        seq=conn.execute("SELECT last_sequence FROM p06_watch_sequence WHERE watch_id=?",(watch_id,)).fetchone()[0]
        data=json.dumps(["page_watch",watch_id,seq,activation_key,observation_key],separators=(",",":"))
        eid=hashlib.sha256(data.encode("ascii")).hexdigest()
        conn.execute("INSERT INTO p06_watch_occurrence "
                     "(watch_id,activation_key,observation_key,sequence,event_id,previous,current,route_id)"
                     " VALUES (?,?,?,?,?,?,?,?)",
                     (watch_id,activation_key,observation_key,seq,eid,previous,current,route_id))
        conn.commit()
        return Occurrence(eid,watch_id,activation_key,observation_key,seq,previous,current,route_id,"PENDING")
    except BaseException:
        conn.rollback()
        raise


def pending(conn: sqlite3.Connection, watch_id: str) -> list[Occurrence]:
    if not isinstance(watch_id,str) or not VALID.fullmatch(watch_id):
        raise ValueError("untrusted watch")
    rows=conn.execute("SELECT event_id,watch_id,activation_key,observation_key,sequence,"
                      "previous,current,route_id,state FROM p06_watch_occurrence "
                      "WHERE watch_id=? AND state='PENDING' ORDER BY sequence",(watch_id,)).fetchall()
    return [Occurrence(*row) for row in rows]


def ack_outbox(conn: sqlite3.Connection, event_id: str, *, independent_receipt: bool) -> bool:
    """Only P04's independent acceptance receipt may transition PENDING.

    It is NOT proof of Cron effect delivery, which remains UNCERTAIN in P04.
    """
    if independent_receipt is not True:
        raise PermissionError("independent outbox receipt required")
    if not isinstance(event_id,str) or not re.fullmatch("[a-f0-9]{64}",event_id):
        raise ValueError("invalid event_id")
    if conn.in_transaction:
        raise RuntimeError("active transaction")
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur=conn.execute("UPDATE p06_watch_occurrence SET state='OUTBOX_ACCEPTED' "
                         "WHERE event_id=? AND state='PENDING'",(event_id,))
        conn.commit()
        return cur.rowcount==1
    except BaseException:
        conn.rollback()
        raise
