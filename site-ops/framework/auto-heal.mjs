import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { execSync } from 'node:child_process'

// Auto-Heal — Generic site map healing logic
// Extracted from whatsapp-web.mjs

export async function withAutoHealing(operationName, operationFn, options = {}) {
  const { sitePattern, siteSlug } = options
  
  try {
    return await operationFn()
  } catch (err) {
    console.error(`[AUTO-HEAL] Operation "${operationName}" failed: ${err.message}`)
    console.error('[AUTO-HEAL] Triggering re-mapping...')

    // Re-run deep map
    if (sitePattern && siteSlug) {
      const deepMapScript = resolve(dirname(fileURLToPath(import.meta.url)), '../../scripts/site-deep-map.mjs')
      execSync(`node ${deepMapScript} init "${sitePattern}"`, { stdio: 'inherit' })
      execSync(`node ${deepMapScript} scan "${sitePattern}"`, { stdio: 'inherit' })
    }

    // Copy new map from artifacts to local override
    if (siteSlug) {
      const artifactPath = resolve(dirname(fileURLToPath(import.meta.url)), '../../workstation/dogfood/artifacts', `site-map-${siteSlug}.json`)
      const localPath = resolve(dirname(fileURLToPath(import.meta.url)), `../../../.claude/site-maps/${siteSlug}.local.json`)
      
      if (existsSync(artifactPath)) {
        const newMap = readFileSync(artifactPath, 'utf-8')
        const localDir = dirname(localPath)
        if (!existsSync(localDir)) {
          mkdirSync(localDir, { recursive: true })
        }
        writeFileSync(localPath, newMap)
        console.error('[AUTO-HEAL] Site map updated from artifacts. Retrying operation...')
      } else {
        console.error('[AUTO-HEAL] WARNING: Artifact map not found at', artifactPath)
      }
    }

    // Retry once
    try {
      return await operationFn()
    } catch (retryErr) {
      throw new Error(`Operation failed even after re-mapping: ${retryErr.message}`)
    }
  }
}