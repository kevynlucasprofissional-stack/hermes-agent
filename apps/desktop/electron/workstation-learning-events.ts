/**
 * HLM-MVP privacy-by-construction event normalization.
 * INERT: caller must verify explicit consent, allowlisted origin, browser tab
 * identity, authorized Electron IPC sender and active human lease *before*
 * invoking this pure function. No raw DOM object, input values, page content,
 * clipboard or URL query/hash is accepted or returned.
 */
export interface RawHumanBrowserGesture {
  eventId: string
  tabId: string
  documentEpoch: string
  relativeTimeMs: number
  kind: 'click' | 'pointerdown' | 'pointerup' | 'shortcut'
  x?: number
  y?: number
  viewportWidth?: number
  viewportHeight?: number
  role?: string
  accessibleName?: string
  elementTag?: string
  inputType?: string
  isEditable?: boolean
  containerBreadcrumb?: string
  currentValue?: string
  unit?: string
  valueUnit?: string
  domDelta?: DomMutationDelta
  key?: string
  ctrl?: boolean
  meta?: boolean
  alt?: boolean
  shift?: boolean
  frame_number?: number
  snapshot_ref?: string
}

export type DomMutationEffectKind =
  | 'modal_opened'
  | 'state_toggled'
  | 'item_added'
  | 'item_removed'
  | 'none'

export interface DomMutationDelta {
  effectKind: DomMutationEffectKind
  summary?: string
}

export interface SafeHumanBrowserGestureTarget {
  role: string
  accessible_name?: string
  accessibleName?: string
  container_breadcrumb?: string
  containerBreadcrumb?: string
  current_value?: string
  currentValue?: string
  unit?: string
  valueUnit?: string
}

export interface SafeHumanBrowserGesture {
  schema: 'hermes.human_gesture.v1'
  event_id: string
  browser_tab_id: string
  document_epoch: string
  time_ms: number
  kind: RawHumanBrowserGesture['kind']
  normalized_position?: { x: number; y: number }
  target?: SafeHumanBrowserGestureTarget
  shortcut?: string
  dom_delta?: DomMutationDelta
  domDelta?: DomMutationDelta
  actor: 'human'
  frame_number?: number
  snapshot_ref?: string
}

const SENSITIVE = /password|passcode|secret|token|key|credential|authorization|cookie|otp|recovery|private|account|session|api|payment|card|email|address/i

const allowedRoles = new Set([
  'button',
  'menuitem',
  'tab',
  'checkbox',
  'radio',
  'slider',
  'option',
  'switch',
  'link',
  'canvas',
  'dialog',
  'combobox',
  'spinbutton'
])

const allowedKeys = new Set(['Enter','Escape','Backspace','Delete','Tab','ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Space','Home','End','PageUp','PageDown',...'1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')])
const NON_TEXT_INPUT_TYPES = new Set(['range', 'number', 'checkbox', 'radio', 'button', 'submit', 'reset', 'color'])

function clamp(n: number): number { return Math.min(1, Math.max(0, n)) }

function isValidRawGesture(raw: RawHumanBrowserGesture): boolean {
  if (!raw.eventId || !raw.tabId || !raw.documentEpoch) {return false}

  if (!Number.isFinite(raw.relativeTimeMs) || raw.relativeTimeMs < 0) {return false}

  return true
}

function isEditableTarget(raw: RawHumanBrowserGesture): boolean {
  if (raw.isEditable) {return true}
  const tag = raw.elementTag?.toLowerCase()

  if (tag === 'textarea') {return true}

  const inputType = raw.inputType?.toLowerCase()

  if (inputType) {
    if (!NON_TEXT_INPUT_TYPES.has(inputType)) {
      return true
    }
  } else if (tag === 'input') {
    return true
  }

  return false
}

function extractShortcut(raw: RawHumanBrowserGesture): string | null {
  if (!(raw.ctrl || raw.meta || raw.alt)) {return null}
  const key = raw.key?.length === 1 ? raw.key.toUpperCase() : raw.key

  if (!key || !allowedKeys.has(key)) {return null}

  return [raw.ctrl ? 'Ctrl' : null, raw.meta ? 'Meta' : null, raw.alt ? 'Alt' : null, raw.shift ? 'Shift' : null, key]
    .filter(Boolean)
    .join('+')
}

function extractNormalizedPosition(raw: RawHumanBrowserGesture): { x: number; y: number } | undefined {
  const { x, y, viewportWidth, viewportHeight } = raw

  if (!Number.isFinite(x) || !Number.isFinite(y)) {return undefined}

  if (!Number.isFinite(viewportWidth) || !Number.isFinite(viewportHeight)) {return undefined}

  if ((viewportWidth ?? 0) <= 0 || (viewportHeight ?? 0) <= 0) {return undefined}

  return {
    x: Math.round(1000 * clamp((x ?? 0) / (viewportWidth ?? 1))) / 1000,
    y: Math.round(1000 * clamp((y ?? 0) / (viewportHeight ?? 1))) / 1000
  }
}

function resolveRawRole(raw: RawHumanBrowserGesture): string {
  const explicit = raw.role?.toLowerCase().trim()

  if (explicit) {return explicit}

  const tag = raw.elementTag?.toLowerCase()

  if (tag === 'canvas') {return 'canvas'}

  if (tag === 'select') {return 'combobox'}

  if (tag === 'input') {
    if (raw.inputType === 'range') {return 'slider'}

    if (raw.inputType === 'number') {return 'spinbutton'}
  }

  return ''
}

function attachTargetMetadata(output: SafeHumanBrowserGestureTarget, raw: RawHumanBrowserGesture): void {
  const name = raw.accessibleName?.trim()

  if (name && name.length <= 80 && !SENSITIVE.test(name)) {
    output.accessible_name = name
    output.accessibleName = name
  }

  if (raw.containerBreadcrumb) {
    const breadcrumb = raw.containerBreadcrumb.trim()

    if (breadcrumb && breadcrumb.length <= 120 && !SENSITIVE.test(breadcrumb)) {
      output.container_breadcrumb = breadcrumb
      output.containerBreadcrumb = breadcrumb
    }
  }

  if (raw.currentValue !== undefined) {
    const val = String(raw.currentValue).trim()

    if (val && val.length <= 60 && !SENSITIVE.test(val)) {
      output.current_value = val
      output.currentValue = val
    }
  }

  const unit = raw.unit || raw.valueUnit

  if (unit) {
    const u = String(unit).trim()

    if (u && u.length <= 20 && !SENSITIVE.test(u)) {
      output.unit = u
      output.valueUnit = u
    }
  }
}

function extractTarget(raw: RawHumanBrowserGesture): SafeHumanBrowserGestureTarget | undefined {
  const role = resolveRawRole(raw)

  if (!allowedRoles.has(role)) {return undefined}

  const output: SafeHumanBrowserGestureTarget = { role }
  attachTargetMetadata(output, raw)

  return output
}

export function normalizeHumanGesture(raw: RawHumanBrowserGesture): SafeHumanBrowserGesture | null {
  if (!isValidRawGesture(raw) || isEditableTarget(raw)) {return null}

  const output: SafeHumanBrowserGesture = {
    schema: 'hermes.human_gesture.v1',
    event_id: raw.eventId.slice(0, 100),
    browser_tab_id: raw.tabId.slice(0, 100),
    document_epoch: raw.documentEpoch.slice(0, 100),
    time_ms: Math.round(raw.relativeTimeMs),
    kind: raw.kind,
    actor: 'human'
  }

  if (raw.kind === 'shortcut') {
    const shortcut = extractShortcut(raw)

    if (!shortcut) {return null}
    output.shortcut = shortcut

    return output
  }

  const pos = extractNormalizedPosition(raw)

  if (pos) {output.normalized_position = pos}

  const target = extractTarget(raw)

  if (target) {output.target = target}

  if (raw.domDelta) {
    const effectKind = raw.domDelta.effectKind || 'none'

    const summary = raw.domDelta.summary && !SENSITIVE.test(raw.domDelta.summary)
      ? raw.domDelta.summary.slice(0, 150)
      : undefined

    const delta: DomMutationDelta = { effectKind, summary }
    output.dom_delta = delta
    output.domDelta = delta
  }

  if (typeof raw.frame_number === 'number') {
    output.frame_number = raw.frame_number
  }

  if (typeof raw.snapshot_ref === 'string') {
    output.snapshot_ref = raw.snapshot_ref
  }

  return output
}
