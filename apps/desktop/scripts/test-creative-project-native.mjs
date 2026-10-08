import { spawn } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'

import { build } from 'esbuild'

const require = createRequire(import.meta.url)
const desktop = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repository = path.resolve(desktop, '..', '..')
const python = process.argv[2]
if (!python || !path.isAbsolute(python) || !fs.existsSync(python)) {
  throw new Error('Pass an absolute installed Hermes Python executable for the native project E2E')
}
const sandbox = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-creative-project-native-'))
const bundled = path.join(sandbox, 'fixture.mjs')
await build({ entryPoints: [path.join(desktop, 'electron', 'workstation-creative-project-native.e2e.mts')],
  outfile: bundled, bundle: true, platform: 'node', format: 'esm', external: ['electron'] })
const env = { ...process.env }
delete env.ELECTRON_RUN_AS_NODE
delete env.NODE_OPTIONS
for (const phase of ['create', 'reopen']) {
  const child = spawn(require('electron'), [bundled, sandbox, python, repository, phase],
    { env, stdio: 'inherit', windowsHide: true })
  const timeout = setTimeout(() => child.kill(), 60_000)
  const code = await new Promise((resolve, reject) => {
    child.once('error', reject)
    child.once('exit', resolve)
  })
  clearTimeout(timeout)
  if (code !== 0) {
    process.exitCode = 1
    break
  }
}
console.log(`Creative project E2E evidence: ${path.join(sandbox, 'project-state.json')}`)
