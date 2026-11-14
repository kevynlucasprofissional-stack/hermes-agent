/**
 * P06 isolated opt-in page watch engine.
 * NOT wired to the live Browser runtime: P02/P04 and Browser/UI gates remain HOLD.
 * Reads structural counts only. Does not collect DOM text, attributes or input values.
 */
import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'

export type PageWatchRule = 'presence' | 'child_count'
export interface PageWatchConfig {
  id: string
  session_id: string
  tab_id: string
  origin: string
  selector?: string
  rule: PageWatchRule
  route_id: string
  enabled: boolean
}

export type PageWatchProbeState = 'ok' | 'origin_mismatch' | 'auth_required' | 'unsupported' | 'unavailable'
export interface PageWatchProbe {
  state: PageWatchProbeState
  origin: string
  count: number
}

export interface PageChangedEvent {
  type: 'page_changed'
  source: 'page_watch'
  event_id: string
  watch_id: string
  session_id: string
  tab_id: string
  origin: string
  route_id: string
  fingerprint: string
  previous: number
  current: number
  observed_at: string
}

export type PageWatchPauseReason = 'logout' | 'login' | 'human_takeover' | 'tab_closed'
  | 'renderer_crash' | 'session_ended' | 'origin_mismatch' | 'auth_required'
  | 'unsupported' | 'unavailable' | 'delivery_error' | 'disabled'

export interface PageWatchStatus {
  id: string
  status: 'watching' | 'paused'
  reason: PageWatchPauseReason | null
  lastEvent: PageChangedEvent | null
  lastCount: number | null
}

const VALID_ID = /^[A-Za-z0-9_-]{1,80}$/
const SIMPLE_SELECTOR = /^(?:#[a-z][a-z0-9_-]{0,50}|\.[a-z][a-z0-9_-]{0,50}|\[data-watch-(?:item|status|count)(?:="[a-z0-9_-]{1,40}")?\])$/i
const PRIVATE_SELECTOR = /password|credential|secret|token|auth|login|logout|cookie|session|private|message|chat|conversation|email|address|phone|payment|card|textarea|input|text|user|account|otp|key/i

export function validatePageWatchConfig(raw: unknown): PageWatchConfig {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {throw new Error('invalid_page_watch')}
  const config = raw as Record<string, unknown>

  for (const id of ['id', 'session_id', 'tab_id', 'route_id']) {
    if (typeof config[id] !== 'string' || !VALID_ID.test(config[id])) {
      throw new Error('invalid_page_watch_identity')
    }
  }

  if (typeof config.origin !== 'string' || config.origin.length > 250) {throw new Error('invalid_page_watch_origin')}
  let url: URL

  try { url = new URL(config.origin) } catch { throw new Error('invalid_page_watch_origin') }

  if (!['https:', 'http:'].includes(url.protocol) ||
      url.username || url.password || url.search || url.hash ||
      url.pathname !== '/' || config.origin !== url.origin) {
    throw new Error('invalid_page_watch_origin')
  }

  if (typeof config.selector !== 'string' || !SIMPLE_SELECTOR.test(config.selector)
      || PRIVATE_SELECTOR.test(config.selector)) {
    throw new Error('unsafe_page_watch_selector')
  }

  if (config.rule !== 'presence' && config.rule !== 'child_count') {throw new Error('invalid_page_watch_rule')}

  if (typeof config.enabled !== 'boolean') {throw new Error('invalid_page_watch_enabled')}

  return {
    id: config.id as string, session_id: config.session_id as string,
    tab_id: config.tab_id as string, origin: url.origin,
    selector: config.selector, rule: config.rule, route_id: config.route_id as string,
    enabled: config.enabled
  }
}

/** Standalone, profile-root-supplied config persistence. Not task state or live observer state. */
export class PageWatchConfigStore {
  constructor(private readonly authorizedPath: string) {}

  load(): PageWatchConfig[] {
    if (!fs.existsSync(this.authorizedPath)) {return []}
    const raw = fs.readFileSync(this.authorizedPath, 'utf8')

    if (raw.length > 64_000) {throw new Error('page_watch_config_too_large')}
    const doc: unknown = JSON.parse(raw)

    if (!doc || typeof doc !== 'object' || Array.isArray(doc)) {throw new Error('invalid_page_watch_document')}
    const d = doc as Record<string, unknown>

    if (d.version !== 1 || !Array.isArray(d.watches) || d.watches.length > 16) {
      throw new Error('invalid_page_watch_document')
    }

    const watches = d.watches.map(validatePageWatchConfig)

    if (new Set(watches.map(w => w.id)).size !== watches.length) {
      throw new Error('duplicate_page_watch')
    }

    return watches
  }

  save(watches: readonly PageWatchConfig[]): void {
    if (watches.length > 16) {throw new Error('too_many_page_watches')}
    const validated = watches.map(validatePageWatchConfig)

    if (new Set(validated.map(w => w.id)).size !== validated.length) {
      throw new Error('duplicate_page_watch')
    }

    const serialized = JSON.stringify({ version: 1, watches: validated }) + '\n'

    if (serialized.length > 64_000) {throw new Error('page_watch_config_too_large')}
    const parent = path.dirname(this.authorizedPath)
    fs.mkdirSync(parent, { recursive: true, mode: 0o700 })
    const tempfile = this.authorizedPath + '.' + crypto.randomBytes(6).toString('hex') + '.tmp'

    try {
      fs.writeFileSync(tempfile, serialized, { encoding: 'utf8', mode: 0o600, flag: 'wx' })
      fs.renameSync(tempfile, this.authorizedPath)
    } finally {
      fs.rmSync(tempfile, { force: true })
    }
  }
}

/** Executed only against the exact, explicitly selected tab in an Electron isolated world. */
export function buildPageWatchProbe(configInput: PageWatchConfig): string {
  const config = validatePageWatchConfig(configInput)

  return `(() => {
    const EXPECTED_ORIGIN = ${JSON.stringify(config.origin)};
    const SELECTOR = ${JSON.stringify(config.selector)};
    const RULE = ${JSON.stringify(config.rule)};
    const WATCH_ID = ${JSON.stringify(config.id)};
    if (location.origin !== EXPECTED_ORIGIN) {
      return { state: 'origin_mismatch', origin: location.origin, count: 0 };
    }
    if (document.querySelectorAll('input[type="password"]').length > 0) {
      return { state: 'auth_required', origin: location.origin, count: 0 };
    }
    if (!document.documentElement || typeof MutationObserver !== 'function') {
      return { state: 'unavailable', origin: location.origin, count: 0 };
    }
    let store = window.__hermesPageWatchP06;
    if (!store || store.owner !== WATCH_ID || store.root !== document.documentElement) {
      if (store && store.observer) store.observer.disconnect();
      store = { owner: WATCH_ID, root: document.documentElement, revision: 0, observer: null };
      store.observer = new MutationObserver(records => {
        if (records.length) store.revision += 1;
      });
      store.observer.observe(document.documentElement, { childList: true, subtree: true });
      window.__hermesPageWatchP06 = store;
    }
    let nodes;
    try { nodes = document.querySelectorAll(SELECTOR); }
    catch (_) { return { state: 'unsupported', origin: location.origin, count: 0 }; }
    if (nodes.length > 1) {
      return { state: 'unsupported', origin: location.origin, count: 0 };
    }
    const el = nodes.length ? nodes[0] : null;
    if (el && (
      el.isContentEditable ||
      (typeof el.matches === 'function' && el.matches('input,textarea,select,[contenteditable],iframe,frame,[role="textbox"]')) ||
      (typeof el.querySelector === 'function' && el.querySelector('input,textarea,select,[contenteditable],iframe,frame,[role="textbox"]'))
    )) {
      return { state: 'unsupported', origin: location.origin, count: 0 };
    }
    const count = RULE === 'presence' ? (el ? 1 : 0) :
      (el ? (el.children ? el.children.length : 0) : 0);
    if (!Number.isSafeInteger(count) || count < 0 || count > 1000) {
      return { state: 'unsupported', origin: location.origin, count: 0 };
    }
    return { state: 'ok', origin: location.origin, count };
  })()`
}

type ProbeFn = () => Promise<PageWatchProbe>
type StopFn = () => void | Promise<void>
interface RunningWatch {
  config: PageWatchConfig
  probe: ProbeFn
  stop: StopFn | null
  epoch: number
  sequence: number
  lastCount: number
  pending: { count: number; since: number } | null
  status: PageWatchStatus
  timer: ReturnType<typeof setInterval> | null
}
export interface PageWatchOptions {
  now?: () => number
  debounceMs?: number
  onEvent?: (event: PageChangedEvent) => void
  reserveEventId?: (request: {watch_id:string;activation_key:string;observation_key:string;origin:string;route_id:string;previous:number;current:number}) => Promise<string> | string
}

export class PageWatchCoordinator {
  private readonly watches = new Map<string, RunningWatch>()
  // Activation nonce is NOT a per-observation event identity. Production uses
  // reserveEventId for durable SQLite sequence and replay deduplication.
  private readonly activationKey = crypto.randomBytes(16).toString('hex')
  private readonly reserveEventId?: PageWatchOptions['reserveEventId']
  private readonly now: () => number
  private readonly debounceMs: number
  private readonly onEvent: (event: PageChangedEvent) => void

  constructor(options: PageWatchOptions = {}) {
    this.now = options.now ?? Date.now
    this.debounceMs = Math.min(5000, Math.max(100, options.debounceMs ?? 350))
    this.onEvent = options.onEvent ?? (() => undefined)
    this.reserveEventId = options.reserveEventId
  }

  async arm(raw: PageWatchConfig, probe: ProbeFn, stop?: StopFn): Promise<PageWatchStatus> {
    const config = validatePageWatchConfig(raw)

    if (!config.enabled) {throw new Error('page_watch_disabled')}

    for (const existing of this.watches.values()) {
      if (existing.status.status === 'watching' && existing.config.id !== config.id &&
          existing.config.tab_id === config.tab_id && existing.config.origin === config.origin) {
        throw new Error('tab and origin already watched')
      }
    }

    const old = this.watches.get(config.id)

    if (old) {this.pause(config.id, 'disabled')}
    const initial = await probe()

    if (initial.state !== 'ok' || initial.origin !== config.origin ||
        !Number.isSafeInteger(initial.count) || initial.count < 0 || initial.count > 1000) {
      throw new Error('page_watch_initial_probe_rejected')
    }

    const running: RunningWatch = {
      config, probe, stop: stop ?? null, epoch: (old?.epoch ?? 0) + 1, sequence: 0,
      lastCount: initial.count, pending: null, timer: null,
      status: { id: config.id, status: 'watching', reason: null, lastEvent: null, lastCount: initial.count },
    }

    this.watches.set(config.id, running)

    return { ...running.status }
  }

  status(id: string): PageWatchStatus {
    const entry = this.watches.get(id)

    if (!entry) {throw new Error('page_watch_unknown')}

    return { ...entry.status }
  }

  setProbe(id: string, probe: ProbeFn): void {
    const entry = this.watches.get(id)

    if (!entry) {throw new Error('page_watch_unknown')}
    entry.probe = probe
  }

  async probeOnce(id: string): Promise<PageWatchStatus> {
    const entry = this.watches.get(id)

    if (!entry) {throw new Error('page_watch_unknown')}

    if (entry.status.status !== 'watching') {return this.status(id)}
    const epoch = entry.epoch
    let observed: PageWatchProbe

    try {observed = await entry.probe()} catch {
      this.pause(id, 'renderer_crash')

      return this.status(id)
    }

    if (entry.epoch !== epoch || entry.status.status !== 'watching') {return this.status(id)}

    if (!observed || observed.state !== 'ok' || observed.origin !== entry.config.origin ||
        !Number.isSafeInteger(observed.count) || observed.count < 0 || observed.count > 1000) {
      const reason: PageWatchPauseReason = observed?.state === 'auth_required' ? 'auth_required' :
        observed?.state === 'origin_mismatch' || observed?.origin !== entry.config.origin ? 'origin_mismatch' :
          observed?.state === 'unsupported' ? 'unsupported' : 'unavailable'

      this.pause(id, reason)

      return this.status(id)
    }

    if (observed.count === entry.lastCount) {
      entry.pending = null

      return this.status(id)
    }

    const now = this.now()

    if (!entry.pending || entry.pending.count !== observed.count) {
      entry.pending = { count: observed.count, since: now }

      return this.status(id)
    }

    if (now - entry.pending.since < this.debounceMs) {return this.status(id)}
    const previous = entry.lastCount
    const nextSequence = entry.sequence + 1

    const fingerprint = crypto.createHash('sha256').update(JSON.stringify([
      entry.config.origin, entry.config.id, entry.config.rule, observed.count
    ])).digest('hex')

    const event_id = crypto.createHash('sha256').update(JSON.stringify([
      entry.config.id, entry.config.tab_id, this.activationKey, entry.epoch, nextSequence, previous, observed.count, fingerprint
    ])).digest('hex')

    let authoritativeId = event_id

    try {
      if (this.reserveEventId) {
        authoritativeId = await this.reserveEventId({
          watch_id: entry.config.id,
          activation_key: this.activationKey,
          observation_key: `${entry.epoch}:${nextSequence}`,
          origin: entry.config.origin, route_id: entry.config.route_id,
          previous, current: observed.count
        })
      }
    } catch {
      this.pause(id, 'delivery_error')

      return this.status(id)
    }

    if (entry.epoch !== epoch || entry.status.status !== 'watching'
        || entry.sequence >= nextSequence || entry.lastCount !== previous) {return this.status(id)}

    if (!/^[a-f0-9]{64}$/.test(authoritativeId)) {
      this.pause(id, 'delivery_error')

      return this.status(id)
    }

    entry.lastCount = observed.count
    entry.pending = null
    entry.sequence = nextSequence

    const event: PageChangedEvent = {
      type: 'page_changed', source: 'page_watch', event_id: authoritativeId,
      watch_id: entry.config.id, session_id: entry.config.session_id,
      tab_id: entry.config.tab_id, origin: entry.config.origin,
      route_id: entry.config.route_id, fingerprint, previous, current: observed.count,
      observed_at: new Date(now).toISOString()
    }

    entry.status.lastEvent = event
    entry.status.lastCount = observed.count

    try {this.onEvent(event)} catch {this.pause(id, 'delivery_error')}

    return this.status(id)
  }

  /** Bounded periodic reconciliation: never starts automatically on restore. */
  startPolling(id: string, intervalMs = 2000): void {
    const entry = this.watches.get(id)

    if (!entry || entry.status.status !== 'watching') {throw new Error('page_watch_not_active')}

    if (intervalMs < 1000 || intervalMs > 30_000) {throw new Error('page_watch_poll_interval')}

    if (entry.timer) {return}
    entry.timer = setInterval(() => {void this.probeOnce(id)}, intervalMs)
    entry.timer.unref?.()
  }

  pause(id: string, reason: PageWatchPauseReason): void {
    const entry = this.watches.get(id)

    if (!entry) {return}
    entry.epoch++  // in-flight probes lose authority immediately

    if (entry.timer) {clearInterval(entry.timer); entry.timer = null}
    entry.pending = null

    try {
      const stopping = entry.stop?.()

      if (stopping && typeof stopping.catch === 'function') {void stopping.catch(() => undefined)}
    } catch { /* fail closed: host remains paused */ }

    entry.status.status = 'paused'
    entry.status.reason = reason
  }

  navigation(tab_id: string, target: string): void {
    let origin = ''

    try {origin = new URL(target).origin} catch {origin = ''}

    for (const [id, entry] of this.watches) {
      if (entry.config.tab_id === tab_id && origin !== entry.config.origin) {
        this.pause(id, 'origin_mismatch')
      }
    }
  }

  tabLifecycle(tab_id: string, reason: PageWatchPauseReason): void {
    for (const [id, entry] of this.watches) {
      if (entry.config.tab_id === tab_id) {this.pause(id, reason)}
    }
  }
}

/** Called by the owning WebContents on pause before discarding navigation context. */
export function buildPageWatchDisconnect(configInput: PageWatchConfig): string {
  const config = validatePageWatchConfig(configInput)

  return `(() => {
    if (location.origin !== ${JSON.stringify(config.origin)}) return false;
    const state = window.__hermesPageWatchP06;
    if (!state || state.owner !== ${JSON.stringify(config.id)}) return false;
    if (state.observer) state.observer.disconnect();
    delete window.__hermesPageWatchP06;
    return true;
  })()`
}
