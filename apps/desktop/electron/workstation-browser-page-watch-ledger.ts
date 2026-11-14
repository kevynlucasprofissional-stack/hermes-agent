/** P06-R occurrence allocator, using the existing canonical Hermes Kanban SQLite.
 * No new scheduler/database: the caller must supply an already-authorized
 * canonical .db path. Metadata only; no DOM content. */
import crypto from 'node:crypto'
import { DatabaseSync } from 'node:sqlite'

export interface PageWatchOccurrenceRequest {
  watch_id: string; activation_key: string; observation_key: string
  origin: string; route_id: string; previous: number; current: number
}
export interface PageWatchOccurrence {
  event_id: string; sequence: number; state: 'PENDING' | 'ACCEPTED' | 'UNCERTAIN'
}
const ID = /^[A-Za-z0-9_.:-]{1,128}$/
const HASH = /^[a-f0-9]{64}$/

export class PageWatchOccurrenceLedger {
  private readonly db: DatabaseSync
  constructor(canonicalDbPath: string) {
    if (!canonicalDbPath || !/\.db$|\.sqlite$/i.test(canonicalDbPath)) {
      throw new Error('canonical_kanban_db_required')
    }

    this.db = new DatabaseSync(canonicalDbPath, { timeout: 5000 })
    this.db.exec('PRAGMA busy_timeout=5000')
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS page_watch_sequence(
        watch_id TEXT PRIMARY KEY, last_sequence INTEGER NOT NULL CHECK(last_sequence>=0)
      );
      CREATE TABLE IF NOT EXISTS page_watch_occurrence(
        watch_id TEXT NOT NULL, activation_key TEXT NOT NULL,
        observation_key TEXT NOT NULL, sequence INTEGER NOT NULL,
        event_id TEXT NOT NULL UNIQUE, origin TEXT NOT NULL, route_id TEXT NOT NULL,
        previous INTEGER NOT NULL, current INTEGER NOT NULL,
        state TEXT NOT NULL DEFAULT 'PENDING'
          CHECK(state IN ('PENDING','ACCEPTED','UNCERTAIN')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(watch_id, activation_key, observation_key),
        UNIQUE(watch_id, sequence)
      );
    `)
  }
  reserve(req: PageWatchOccurrenceRequest): PageWatchOccurrence {
    for (const field of [req.watch_id, req.activation_key, req.observation_key, req.route_id]) {
      if (!ID.test(field)) {throw new Error('invalid_page_watch_occurrence_identity')}
    }

    if (!/^https?:\/\//.test(req.origin) || new URL(req.origin).origin !== req.origin) {
      throw new Error('invalid_page_watch_occurrence_origin')
    }

    if (req.previous === req.current || ![req.previous, req.current].every(x => Number.isSafeInteger(x) && x>=0 && x<=1000)) {
      throw new Error('invalid_page_watch_occurrence_counts')
    }

    this.db.exec('BEGIN IMMEDIATE')

    try {
      const previous = this.db.prepare(
        'SELECT event_id,sequence,origin,route_id,previous,current,state FROM page_watch_occurrence '+
        'WHERE watch_id=? AND activation_key=? AND observation_key=?'
      ).get(req.watch_id,req.activation_key,req.observation_key) as
        {event_id:string;sequence:number;origin:string;route_id:string;previous:number;current:number;state:PageWatchOccurrence['state']} | undefined

      if (previous) {
        if (previous.origin!==req.origin || previous.route_id!==req.route_id ||
            previous.previous!==req.previous || previous.current!==req.current) {
          throw new Error('conflicting_page_watch_replay')
        }

        this.db.exec('COMMIT')

        return {event_id:previous.event_id,sequence:previous.sequence,state:previous.state}
      }

      this.db.prepare('INSERT OR IGNORE INTO page_watch_sequence VALUES (?,0)').run(req.watch_id)
      this.db.prepare('UPDATE page_watch_sequence SET last_sequence=last_sequence+1 WHERE watch_id=?').run(req.watch_id)

      const seq = this.db.prepare('SELECT last_sequence FROM page_watch_sequence WHERE watch_id=?')
        .get(req.watch_id) as {last_sequence:number}

      const id = crypto.createHash('sha256').update(JSON.stringify([
        'page_watch',req.watch_id,seq.last_sequence,req.activation_key,req.observation_key
      ])).digest('hex')

      this.db.prepare('INSERT INTO page_watch_occurrence '+
        '(watch_id,activation_key,observation_key,sequence,event_id,origin,route_id,previous,current) VALUES (?,?,?,?,?,?,?,?,?)'
      ).run(req.watch_id,req.activation_key,req.observation_key,seq.last_sequence,id,
        req.origin,req.route_id,req.previous,req.current)
      this.db.exec('COMMIT')

      return {event_id:id,sequence:seq.last_sequence,state:'PENDING'}
    } catch(error) {
      this.db.exec('ROLLBACK')
      throw error
    }
  }
  read(id: string): PageWatchOccurrence | null {
    if (!HASH.test(id)) {throw new Error('invalid_event_id')}

    const found = this.db.prepare('SELECT event_id,sequence,state FROM page_watch_occurrence WHERE event_id=?')
      .get(id) as unknown as PageWatchOccurrence | undefined

    return found ?? null
  }
  pending(): string[] {
    return (this.db.prepare("SELECT event_id FROM page_watch_occurrence WHERE state='PENDING' ORDER BY rowid LIMIT 100")
      .all() as {event_id:string}[]).map(item=>item.event_id)
  }
  close():void {this.db.close()}
}
