import { spawn } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'

import { build } from 'esbuild'

const require = createRequire(import.meta.url)
const desktop = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-creative-fixture-build-'))
const bundled = path.join(temporary, 'fixture.mjs')
const output = path.resolve(process.argv[2] || path.join(desktop, 'test-results', 'creative-native'))
await build({
  entryPoints: [path.join(desktop, 'electron', 'workstation-creative-native.e2e.mts')],
  outfile: bundled, bundle: true, platform: 'node', format: 'esm', external: ['electron']
})
const env = { ...process.env }
delete env.ELECTRON_RUN_AS_NODE
delete env.NODE_OPTIONS
const child = spawn(require('electron'), [bundled, output], { env, stdio: 'inherit', windowsHide: true })
const timeout = setTimeout(() => {
  console.error('Creative native fixture timed out')
  child.kill()
}, 60_000)
const code = await new Promise((resolve, reject) => {
  child.once('error', reject)
  child.once('exit', resolve)
})
clearTimeout(timeout)
process.exitCode = typeof code === 'number' ? code : 1
