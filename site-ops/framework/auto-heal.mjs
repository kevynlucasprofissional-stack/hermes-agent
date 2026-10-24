import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'

import { getMapPaths, getSiteOpsRoot } from './map-loader.mjs'

// A remap is useful only for a known pre-effect selector failure.
// Infrastructure, authorization and uncertain-effect errors must not be retried here.
const SELECTOR_FAILURE = /(?:input not found in site map|could not resolve selector|selector (?:not found|missing|stale)|stale[_ -]?selector)/i
const HEAL_COOLDOWN_MS = 30_000
let lastHealTime = 0

export async function withAutoHealing(operationName, operationFn, options = {}) {
  const { sitePattern, siteSlug } = options

  try {
    return await operationFn()
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    if (!SELECTOR_FAILURE.test(message) || !sitePattern || !siteSlug) throw error

    const now = Date.now()
    const elapsed = now - lastHealTime
    if (elapsed < HEAL_COOLDOWN_MS) {
      const remaining = Math.round((HEAL_COOLDOWN_MS - elapsed) / 1000)
      throw new Error(`[AUTO-HEAL] Heal skipped: cooldown active (${remaining}s remaining). Original error: ${message}`)
    }
    lastHealTime = now

    const started = performance.now()
    const root = getSiteOpsRoot()
    const deepMapScript = resolve(root, 'scripts', 'site-deep-map.mjs')
    if (!existsSync(deepMapScript)) throw new Error(`[AUTO-HEAL] Deep map script not found: ${deepMapScript}`)

    // execFileSync passes arguments literally, without shell interpolation.
    const invoke = (command) => JSON.parse(String(execFileSync(process.execPath,
      [deepMapScript, command, sitePattern], { encoding: 'utf8', timeout: 60_000 })))

    const init = invoke('init')
    const slug = init?.slug
    if (init?.initialized !== true || typeof slug !== 'string' || !/^[a-z0-9-]+$/.test(slug)) {
      throw new Error('[AUTO-HEAL] Deep map initialization returned an invalid site slug')
    }

    const scan = invoke('scan')
    if (scan?.scanned !== true) throw new Error('[AUTO-HEAL] Deep map scan was not confirmed')

    // site-deep-map uses the target URL hostname (not the playbook slug).
    const artifactPath = resolve(root, '..', 'workstation', 'dogfood', 'artifacts', `site-map-${slug}.json`)
    if (!existsSync(artifactPath)) throw new Error(`[AUTO-HEAL] Remapped artifact not found: ${artifactPath}`)
    const mapContent = readFileSync(artifactPath, 'utf8')
    const map = JSON.parse(mapContent)
    if (!map?.screens?.main || !Array.isArray(map.screens.main.elements)) {
      throw new Error('[AUTO-HEAL] Remapped artifact has no valid main screen')
    }

    // The workspace override takes precedence and is also read by loadSiteMap.
    const overridePath = getMapPaths(siteSlug).workspaceLocal
    mkdirSync(dirname(overridePath), { recursive: true })
    writeFileSync(overridePath, mapContent, 'utf8')

    console.error(`[AUTO-HEAL] status=remapped operations=2 retry=1 duration_ms=${Math.round(performance.now() - started)}`)
    // One bounded retry. A failure here is returned to the owner, never healed again.
    return await operationFn()
  }
}
