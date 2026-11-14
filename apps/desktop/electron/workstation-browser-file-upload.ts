import fs from 'node:fs'
import path from 'node:path'

import { parse } from 'yaml'

/** Operator-maintained grants in the active profile's config.yaml, never in tool arguments. */
export interface BrowserUploadGrant { allowedRoots: string[]; allowedOrigins?: string[]; maxBytes?: number; maxFiles?: number }
export interface ValidatedBrowserUploadFile { absolutePath: string; basename: string; bytes: number }

export function resolveBrowserUploadGrant(home: string, taskId: string, sessionId: string, runId: string): BrowserUploadGrant {
  if (!taskId || taskId === 'default' || !sessionId || !runId) {throw new Error('upload_scope_required')}
  let config: unknown

  try {
    const configPath = path.join(home, 'config.yaml')

    if (fs.statSync(configPath).size > 65_536) {throw new Error('upload_scope_required')}
    config = parse(fs.readFileSync(configPath, 'utf8'))
  } catch {
    throw new Error('upload_scope_required')
  }

  const browser = (config as { browser?: { workstation?: { upload_grants?: unknown } } } | null)?.browser
  const grants = browser?.workstation?.upload_grants

  if (!Array.isArray(grants)) {throw new Error('upload_scope_required')}
  const now = Date.now()

  const grant = grants.find((candidate: unknown) => {
    if (!candidate || typeof candidate !== 'object') {return false}
    const item = candidate as Record<string, unknown>
    const expiry = typeof item.expires_at === 'string' ? Date.parse(item.expires_at) : Number.NaN

    return item.task_id === taskId && item.session_id === sessionId && item.run_id === runId &&
      Number.isFinite(expiry) && expiry > now && Array.isArray(item.allowed_roots) && item.allowed_roots.length > 0 &&
      Array.isArray(item.allowed_origins) && item.allowed_origins.length > 0
  }) as Record<string, unknown> | undefined

  if (!grant) {throw new Error('upload_scope_required')}

  return {
    allowedRoots: grant.allowed_roots as string[],
    allowedOrigins: grant.allowed_origins as string[],
    maxBytes: typeof grant.max_bytes === 'number' ? grant.max_bytes : undefined,
    maxFiles: typeof grant.max_files === 'number' ? grant.max_files : undefined
  }
}

/** Host-only resolution; absolutePath must NEVER leave CDP-side runtime. */
export function validateBrowserUploadFiles(rawFiles: unknown, grant: BrowserUploadGrant): ValidatedBrowserUploadFile[] {
  const maxFiles = grant.maxFiles ?? 10
  const maxBytes = grant.maxBytes ?? 50 * 1024 * 1024

  if (!Number.isSafeInteger(maxFiles) || maxFiles < 1 || maxFiles > 20 ||
      !Number.isSafeInteger(maxBytes) || maxBytes < 1 || maxBytes > 250 * 1024 * 1024) {
    throw new Error('upload_limit_invalid')
  }

  if (!Array.isArray(grant.allowedRoots) || grant.allowedRoots.length === 0 || grant.allowedRoots.length > 20) {
    throw new Error('upload_scope_required')
  }

  if (!Array.isArray(rawFiles) || rawFiles.length === 0 || rawFiles.length > maxFiles) {
    throw new Error('upload_file_count_invalid')
  }

  const roots = grant.allowedRoots.map(value => {
    if (typeof value !== 'string' || !path.isAbsolute(value) || value.includes('\0')) {throw new Error('upload_scope_invalid')}

    try {
      const real = fs.realpathSync.native(value)

      if (!fs.statSync(real).isDirectory()) {throw new Error('upload_scope_invalid')}

      return real
    } catch { throw new Error('upload_scope_invalid') }
  })

  return rawFiles.map(value => {
    if (typeof value !== 'string' || !path.isAbsolute(value) || value.includes('\0')) {
      throw new Error('upload_path_invalid')
    }

    let real: string
    let stat: fs.Stats

    try {
      real = fs.realpathSync.native(value)
      stat = fs.statSync(real)
    } catch { throw new Error('upload_file_not_found') }

    if (!stat.isFile()) {throw new Error('upload_regular_file_required')}

    if (stat.size > maxBytes) {throw new Error('upload_file_too_large')}

    if (!roots.some(root => {
      const rel = path.relative(root, real)

      return rel !== '' && rel !== '..' && !rel.startsWith('..' + path.sep) && !path.isAbsolute(rel)
    })) {throw new Error('upload_scope_denied')}

    return { absolutePath: real, basename: path.basename(real), bytes: stat.size }
  })
}

/** Fixed, bounded browser script: single main-frame HTML file input only. */
export function browserFileInputExpression(selector: string): string {
  if (typeof selector !== 'string' || !selector || selector.length > 512) {throw new Error('upload_selector_invalid')}

  return `(() => { const nodes = document.querySelectorAll(${JSON.stringify(selector)}); if (nodes.length !== 1) return null; const el = nodes[0]; return el instanceof HTMLInputElement && el.type === 'file' ? el : null })()`
}

/** Require a literal, exact web origin from the operator grant. */
export function validateBrowserUploadOrigin(grant: BrowserUploadGrant, currentUrl: string): void {
  if (!Array.isArray(grant.allowedOrigins) || grant.allowedOrigins.length === 0 || grant.allowedOrigins.length > 20) {
    throw new Error('upload_origin_denied')
  }

  let actual: URL

  try { actual = new URL(currentUrl) }
  catch { throw new Error('upload_origin_denied') }

  if (actual.protocol !== 'https:' && actual.protocol !== 'http:') {throw new Error('upload_origin_denied')}

  const allowed = grant.allowedOrigins.some(origin => {
    if (typeof origin !== 'string') {return false}

    try {
      const expected = new URL(origin)

      return expected.origin === origin && expected.protocol === actual.protocol && expected.origin === actual.origin
    } catch { return false }
  })

  if (!allowed) {throw new Error('upload_origin_denied')}
}
