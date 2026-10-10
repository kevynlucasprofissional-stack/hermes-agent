import fs from 'node:fs'
import path from 'node:path'
import { registerHooks } from 'node:module'
import { pathToFileURL } from 'node:url'
import { pinnedPackageRoot } from './prepare-packaging-tools.mjs'

const source = path.resolve(import.meta.dirname, '../../..')
const builder = pinnedPackageRoot(source, 'app-builder-lib')
if (JSON.parse(fs.readFileSync(path.join(builder, 'package.json'), 'utf8')).version !== '27.0.0-alpha.6') {
  throw new Error('Revalidate prepared WiX adapter for the installed app-builder-lib')
}
const target = pathToFileURL(path.join(builder, 'dist/targets/win/MsiTarget.js')).href
const supplier = new URL('./prepared-wix.mjs', import.meta.url).href
// Only the pinned MSI target is redirected. No dependency files are rewritten,
// and the replacement cannot acquire bytes or fall back to a download.
registerHooks({
  resolve(specifier, context, nextResolve) {
    if (context.parentURL === target && specifier === '../../util/electronGet.js') {
      return { url: supplier, shortCircuit: true }
    }
    return nextResolve(specifier, context)
  },
})
