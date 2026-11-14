const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const { spawn, spawnSync } = require('node:child_process')
const esbuild = require('esbuild')

async function main() {
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-system1-native-'))
  const repo = path.resolve(__dirname, '../../..')
  const exe = path.resolve(__dirname, '../node_modules/electron/dist/electron.exe')
  const entry = path.join(__dirname, 'workstation-system1-native-snapshot.ts')
  const output = path.join(scratch, 'native-system1.cjs')
  try {
    await esbuild.build({
      entryPoints: [entry], outfile: output, bundle: true, platform: 'node',
      format: 'cjs', target: 'node22', external: ['electron'], logLevel: 'error',
    })
    const env = {...process.env,
      HERMES_HOME: path.join(scratch, 'home'),
      HERMES_WORKSTATION_HOME: path.join(scratch, 'workstation'),
      HERMES_WORKSTATION_BROWSER_PROFILE: path.join(scratch, 'browser-profile'),
      HERMES_WORKSTATION_BROWSER_CONTROL_FILE: path.join(scratch, 'control.json'),
      HERMES_WORKSTATION_BROWSER_SESSION_STATE_FILE: path.join(scratch, 'browser-session.json'),
    }
    delete env.ELECTRON_RUN_AS_NODE
    const run = await new Promise((resolve, reject) => {
      const child = spawn(exe, [output], {
        env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
      })
      let stdout = '', stderr = '', timedOut = false
      const timeout = setTimeout(() => { timedOut = true; child.kill() }, 25000)
      child.stdout.on('data', chunk => {stdout += chunk})
      child.stderr.on('data', chunk => {stderr += chunk})
      child.on('error', reject)
      child.on('close', code => {clearTimeout(timeout); resolve({code, stdout, stderr, timedOut})})
    })
    const line = run.stdout.split(/\r?\n/).find(s => s.startsWith('SYSTEM1_NATIVE_SNAPSHOT_E2E='))
    if (run.code !== 0 || run.timedOut || !line) {
      throw Error('ELECTRON_NATIVE_FAILED=' + JSON.stringify({
        code: run.code, timedOut: run.timedOut,
        stderr: run.stderr.slice(-800), stdout: run.stdout.slice(-800),
      }))
    }
    const payload = JSON.parse(line.slice('SYSTEM1_NATIVE_SNAPSHOT_E2E='.length))
    const python = process.env.HERMES_PYTHON || path.resolve(repo, '.venv/Scripts/python.exe')
    const check = spawnSync(python, ['-m', 'workstation.benchmarks.system1_browser_native_probe'], {
      cwd: repo, encoding: 'utf8', input: JSON.stringify(payload),
      env: {...process.env, HERMES_HOME: path.join(scratch, 'home'),
        HERMES_WORKSTATION_HOME: path.join(scratch, 'workstation')},
    })
    if (check.status !== 0) {
      throw Error('SYSTEM1_SELECTOR_FAILED=' + JSON.stringify({
        status: check.status, stderr: check.stderr?.slice(-1200), stdout: check.stdout,
      }))
    }
    const proof = JSON.parse(check.stdout.trim().split(/\r?\n/).at(-1))
    console.log('SYSTEM1_NATIVE_FASTPATH_RESULT=' + JSON.stringify(proof))
    if (!proof.verified || !proof.native_browser_task || !proof.no_user_focus) {
      process.exitCode = 2
    }
    if (process.env.HERMES_LAYA_QUAL_PYTHON) {
      const live = spawnSync(process.env.HERMES_LAYA_QUAL_PYTHON,
        ['-m', 'workstation.benchmarks.system1_laya_hermes_smoke', '--native-stdin'], {
          cwd: repo, encoding: 'utf8', input: JSON.stringify(payload), timeout: 120000,
          env: {...process.env, HF_HUB_OFFLINE: '1', TRANSFORMERS_OFFLINE: '1',
            OMP_NUM_THREADS: '4', HERMES_HOME: path.join(scratch, 'home'),
            HERMES_WORKSTATION_HOME: path.join(scratch, 'workstation')},
        })
      const proofLine = (live.stdout || '').split(/\r?\n/).find(s => s.startsWith('SYSTEM1_LAYA_HERMES_PROOF='))
      if (live.status !== 0 || !proofLine) {
        throw Error('NATIVE_SYSTEM1_LAYA_FAILED=' + JSON.stringify({
          status: live.status, signal: live.signal, stderr: live.stderr?.slice(-1800),
          stdout: live.stdout?.slice(-600),
        }))
      }
      const layaProof = JSON.parse(proofLine.slice('SYSTEM1_LAYA_HERMES_PROOF='.length))
      console.log('SYSTEM1_NATIVE_LAYA_RESULT=' + JSON.stringify(layaProof))
      if (!layaProof.source_snapshot_native || !layaProof.source_verified ||
          !layaProof.decision_receipt_ref_present || layaProof.receipt_status !== 'verified' ||
          layaProof.verified_ref !== '@e1') process.exitCode = 2
    }
  } finally {
    fs.rmSync(scratch, {recursive: true, force: true, maxRetries: 8, retryDelay: 120})
  }
}

main().catch(err => {
  console.error('SYSTEM1_NATIVE_FASTPATH_ERROR=' + String(err?.stack || err))
  process.exitCode = 2
})
