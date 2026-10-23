// site-ops/framework/auto-heal.mjs
// Auto-Heal — Generic site map healing logic.
// When an operation fails due to selector or DOM drift, triggers re-mapping,
// updates local override map, and retries.

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { execSync } from 'node:child_process'
import { getSiteOpsRoot, saveLocalMapOverride } from './map-loader.mjs'

const __dirname = dirname(fileURLToPath(import.meta.url))

// State tracking for cooldown and loop prevention
const healHistory = new Map() // siteSlug -> { lastHealTime: number, healCount: number }

export function getHealStats(siteSlug = 'whatsapp-web') {
  return healHistory.get(siteSlug) || { lastHealTime: 0, healCount: 0 }
}

export function resetHealCooldown(siteSlug = 'whatsapp-web') {
  healHistory.delete(siteSlug)
}

export function triggerSiteReMap(sitePattern = 'web.whatsapp.com', siteSlug = 'whatsapp-web', customScript = null) {
  const root = getSiteOpsRoot()
  const scriptPath = customScript || resolve(root, 'scripts', 'site-deep-map.mjs')

  if (!existsSync(scriptPath)) {
    throw new Error(`site-deep-map script not found at: ${scriptPath}`)
  }

  console.error(`[AUTO-HEAL] Re-mapping site matching "${sitePattern}" using ${scriptPath}...`)

  // Step 1: Initialize mapping
  execSync(`node "${scriptPath}" init "${sitePattern}"`, { stdio: 'inherit' })

  // Step 2: Scan elements on the current screen
  execSync(`node "${scriptPath}" scan "${sitePattern}"`, { stdio: 'inherit' })

  // Find generated artifact
  const workspaceRoot = resolve(root, '..')
  const artifactPath = resolve(workspaceRoot, 'workstation', 'dogfood', 'artifacts', `site-map-${siteSlug}.json`)

  if (!existsSync(artifactPath)) {
    const fallbackPath = resolve(process.cwd(), 'workstation', 'dogfood', 'artifacts', `site-map-${siteSlug}.json`)
    if (existsSync(fallbackPath)) {
      return readFileSync(fallbackPath, 'utf-8')
    }
    throw new Error(`Re-map completed but artifact not found at: ${artifactPath}`)
  }

  return readFileSync(artifactPath, 'utf-8')
}

export async function withAutoHealing(operationName, operationFn, options = {}) {
  const sitePattern = options.sitePattern || 'web.whatsapp.com'
  const siteSlug = options.siteSlug || (sitePattern.includes('whatsapp') ? 'whatsapp-web' : sitePattern.replace(/[^a-z0-9]/gi, '-').toLowerCase())
  const cooldownMs = options.cooldownMs ?? 30000
  const maxHealsPerSession = options.maxHealsPerSession ?? 3

  try {
    return await operationFn()
  } catch (err) {
    console.error(`[AUTO-HEAL] Operation "${operationName}" failed: ${err.message}`)

    const stats = getHealStats(siteSlug)
    const now = Date.now()
    if (now - stats.lastHealTime < cooldownMs) {
      const waitRemaining = Math.ceil((cooldownMs - (now - stats.lastHealTime)) / 1000)
      console.error(`[AUTO-HEAL] Healing cooldown active (${waitRemaining}s remaining). Skipping re-map.`)
      throw err
    }

    if (stats.healCount >= maxHealsPerSession) {
      console.error(`[AUTO-HEAL] Escalation: Max heals (${stats.healCount}) reached for session. User guidance required.`)
      throw new Error(`Operation "${operationName}" failed. Auto-healing escalated after ${stats.healCount} previous attempts: ${err.message}`)
    }

    console.error('[AUTO-HEAL] Triggering re-mapping...')
    healHistory.set(siteSlug, { lastHealTime: now, healCount: stats.healCount + 1 })

    try {
      if (options.deepMapScript && options.deepMapArgs) {
        for (const cmdArgs of options.deepMapArgs) {
          execSync(`node ${options.deepMapScript} ${cmdArgs.join(' ')}`, { stdio: 'inherit' })
        }
        if (options.localMapPath && options.artifactsDir) {
          const artifactMapPath = resolve(options.artifactsDir, `site-map-${siteSlug}.json`)
          if (existsSync(artifactMapPath)) {
            const newMap = readFileSync(artifactMapPath, 'utf-8')
            if (!existsSync(dirname(options.localMapPath))) {
              mkdirSync(dirname(options.localMapPath), { recursive: true })
            }
            writeFileSync(options.localMapPath, newMap)
          }
        }
      } else {
        const newMapContent = triggerSiteReMap(sitePattern, siteSlug, options.deepMapScript)
        const savedPath = saveLocalMapOverride(siteSlug, newMapContent)
        console.error(`[AUTO-HEAL] Site map updated and saved to: ${savedPath}. Retrying operation...`)
      }
    } catch (healErr) {
      console.error(`[AUTO-HEAL] Re-mapping failed: ${healErr.message}`)
      throw err
    }

    // Retry operation once
    try {
      return await operationFn()
    } catch (retryErr) {
      throw new Error(`Operation "${operationName}" failed even after re-mapping: ${retryErr.message}`)
    }
  }
}
