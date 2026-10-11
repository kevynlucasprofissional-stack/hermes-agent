import { lstat, realpath } from 'node:fs/promises'
import path from 'node:path'

export function inside(parent, child, paths = path) {
  const relative = paths.relative(paths.resolve(parent), paths.resolve(child))
  return relative === '' || (!paths.isAbsolute(relative) && relative !== '..' && !relative.startsWith(`..${paths.sep}`))
}

export async function canonicalPath(value) {
  const absolute = path.resolve(value)
  try {
    return await realpath(absolute)
  } catch (error) {
    if (error.code !== 'ENOENT') throw error
    // A dangling link must not be mistaken for a new directory.
    try {
      await lstat(absolute)
      throw new Error('path contains an unresolved filesystem link')
    } catch (statError) {
      if (statError.code !== 'ENOENT') throw statError
    }
    const parent = path.dirname(absolute)
    if (parent === absolute) throw error
    return path.join(await canonicalPath(parent), path.basename(absolute))
  }
}

export async function resolveTestHome(testHome, defaultHome) {
  const [home, standardHome] = await Promise.all([canonicalPath(testHome), canonicalPath(defaultHome)])
  if (inside(standardHome, home)) throw new Error('test home must not be the default ~/.hermes tree')
  return home
}

export async function resolveRunPaths({ testHome, defaultHome, controllerFile, output }) {
  const home = await resolveTestHome(testHome, defaultHome)
  const controller = await canonicalPath(controllerFile)
  const destination = await canonicalPath(output)
  const expectedController = path.join(home, 'workstation', 'Runtime', 'browser-control.json')
  if (path.relative(expectedController, controller) !== '') {
    throw new Error('--controller-file must be the descriptor inside --test-home')
  }
  if (!inside(home, destination)) throw new Error('--output must stay inside --test-home')
  return { testHome: home, controllerFile: controller, output: destination }
}

export function fixtureUrl(config, scenario, extra = {}) {
  const url = new URL(`/scenario/${scenario}`, config.baseUrl)
  url.searchParams.set('run_id', config.runId)
  for (const [key, value] of Object.entries(extra)) url.searchParams.set(key, String(value))
  return url.toString()
}

export function findElement(body, testid) {
  return body?.result?.elements?.find(element => element.testid === testid) ?? null
}
