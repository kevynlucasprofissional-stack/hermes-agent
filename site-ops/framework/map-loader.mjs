// site-ops/framework/map-loader.mjs
// Site Map Resolution: Baseline maps vs local auto-healed overrides.

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))

export function getSiteOpsRoot() {
  if (process.env.HERMES_SITE_OPS) {
    return resolve(process.env.HERMES_SITE_OPS)
  }
  return resolve(__dirname, '..')
}

export function getMapPaths(siteSlug = 'whatsapp-web') {
  const root = getSiteOpsRoot()
  const baselinePath = resolve(root, 'maps', `${siteSlug}.json`)

  // Local override resolution: prefer workspace .claude, fallback to user home .claude
  const workspaceRoot = resolve(root, '..')
  const workspaceLocalPath = resolve(workspaceRoot, '.claude', 'site-maps', `${siteSlug}.local.json`)
  const userHome = process.env.USERPROFILE || process.env.HOME || ''
  const homeLocalPath = userHome ? resolve(userHome, '.claude', 'site-maps', `${siteSlug}.local.json`) : null

  let localOverridePath = workspaceLocalPath
  if (!existsSync(workspaceLocalPath) && homeLocalPath && existsSync(homeLocalPath)) {
    localOverridePath = homeLocalPath
  }

  return {
    root,
    baseline: baselinePath,
    localOverride: localOverridePath,
    workspaceLocal: workspaceLocalPath,
    homeLocal: homeLocalPath
  }
}

export function loadSiteMap(siteSlug = 'whatsapp-web') {
  const paths = getMapPaths(siteSlug)
  if (existsSync(paths.localOverride)) {
    return JSON.parse(readFileSync(paths.localOverride, 'utf-8'))
  }
  if (existsSync(paths.baseline)) {
    return JSON.parse(readFileSync(paths.baseline, 'utf-8'))
  }
  throw new Error(`Site map not found for "${siteSlug}". Looked at: ${paths.localOverride}, ${paths.baseline}. Run site-deep-map.mjs first.`)
}

export function saveLocalMapOverride(siteSlug = 'whatsapp-web', mapData) {
  const paths = getMapPaths(siteSlug)
  const targetPath = paths.localOverride
  const targetDir = dirname(targetPath)
  if (!existsSync(targetDir)) {
    mkdirSync(targetDir, { recursive: true })
  }
  const content = typeof mapData === 'string' ? mapData : JSON.stringify(mapData, null, 2)
  writeFileSync(targetPath, content, 'utf-8')
  return targetPath
}

export function saveBaselineMap(siteSlug = 'whatsapp-web', mapData) {
  const paths = getMapPaths(siteSlug)
  const targetDir = dirname(paths.baseline)
  if (!existsSync(targetDir)) {
    mkdirSync(targetDir, { recursive: true })
  }
  const content = typeof mapData === 'string' ? mapData : JSON.stringify(mapData, null, 2)
  writeFileSync(paths.baseline, content, 'utf-8')
  return paths.baseline
}
