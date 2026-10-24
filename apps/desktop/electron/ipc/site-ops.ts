import { type ChildProcessWithoutNullStreams, spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { ipcMain, type IpcMainInvokeEvent } from 'electron'

const __dirname = dirname(fileURLToPath(import.meta.url))

// Source modules live under electron/ipc; the bundled entry lives under dist.
// Prefer the packaged payload's explicit location when it is provided.
const siteOpsCandidates = [
  resolve(__dirname, '..', '..', '..', '..', 'site-ops'),
  resolve(__dirname, '..', '..', '..', 'site-ops')
]

const siteOpsRoot = process.env.HERMES_SITE_OPS
  ? resolve(process.env.HERMES_SITE_OPS)
  : siteOpsCandidates.find(root => existsSync(resolve(root, 'scripts', 'site-deep-map.mjs'))) ?? siteOpsCandidates[0]

const workspaceRoot = resolve(siteOpsRoot, '..')
const SITE_OPS_SCRIPTS = resolve(siteOpsRoot, 'scripts')
const SITE_OPS_SITE_OPS = resolve(SITE_OPS_SCRIPTS, 'site-ops')
const DEEP_MAP_SCRIPT = resolve(SITE_OPS_SCRIPTS, 'site-deep-map.mjs')

interface SiteOpsRequest {
  site: string
  operation: string
  args?: string[]
  options?: {
    timeoutMs?: number
    sitePattern?: string
    siteSlug?: string
  }
}

interface SiteOpsResult {
  success: boolean
  data?: unknown
  error?: string
  healTriggered?: boolean
  healSuccess?: boolean
}

const runningProcesses = new Map<string, ChildProcessWithoutNullStreams>()

function generateProcessId(): string {
  return `site-ops-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

function getScriptPath(site: string, operation: string): string {
  if (site === 'whatsapp-web' && ['open-chat', 'send-message', 'get-unread-count'].includes(operation)) {
    return resolve(SITE_OPS_SITE_OPS, 'whatsapp-web.mjs')
  }

  throw new Error(`Unknown site/operation: ${site}/${operation}`)
}

async function runNodeScript(scriptPath: string, args: string[], timeoutMs: number): Promise<{ stdout: string; stderr: string; exitCode: number }> {
  return new Promise((resolve) => {
    const proc = spawn('node', [scriptPath, ...args], {
      cwd: workspaceRoot,
      env: {
        ...process.env,
        HERMES_DESKTOP_CDP_PORT: process.env.HERMES_DESKTOP_CDP_PORT || '9222'
      }
    })

    let stdout = ''
    let stderr = ''

    proc.stdout?.on('data', (data) => { stdout += data.toString() })
    proc.stderr?.on('data', (data) => { stderr += data.toString() })

    const timeout = setTimeout(() => {
      proc.kill('SIGTERM')
      setTimeout(() => proc.kill('SIGKILL'), 1000)
      resolve({ stdout, stderr, exitCode: -1 })
    }, timeoutMs)

    proc.on('close', (exitCode) => {
      clearTimeout(timeout)
      resolve({ stdout, stderr, exitCode: exitCode ?? -1 })
    })

    proc.on('error', (err) => {
      clearTimeout(timeout)
      resolve({ stdout, stderr: err.message, exitCode: -1 })
    })
  })
}

export function registerSiteOpsIpc(): void {
  ipcMain.handle('hermes:site-ops:execute', async (event: IpcMainInvokeEvent, request: SiteOpsRequest): Promise<SiteOpsResult> => {
    const { site, operation, args = [], options = {} } = request
    const timeoutMs = options.timeoutMs ?? 60000
    const sitePattern = options.sitePattern ?? 'web.whatsapp.com'
    const siteSlug = options.siteSlug ?? 'whatsapp-web'

    if (site !== 'whatsapp-web') {
      return { success: false, error: `Unsupported site: ${site}` }
    }

    try {
      const scriptPath = getScriptPath(site, operation)
      const procId = generateProcessId()

      const proc = spawn('node', [scriptPath, operation, ...args], {
        cwd: workspaceRoot,
        env: {
          ...process.env,
          HERMES_DESKTOP_CDP_PORT: process.env.HERMES_DESKTOP_CDP_PORT || '9222'
        }
      })

      runningProcesses.set(procId, proc)

      let stdout = ''
      let stderr = ''

      proc.stdout?.on('data', (data) => { stdout += data.toString() })
      proc.stderr?.on('data', (data) => { stderr += data.toString() })

      const result = await new Promise<SiteOpsResult>((resolve) => {
        const timeout = setTimeout(() => {
          proc.kill('SIGTERM')
          setTimeout(() => proc.kill('SIGKILL'), 1000)
          resolve({ success: false, error: 'Operation timed out' })
        }, timeoutMs)

        proc.on('close', (exitCode) => {
          clearTimeout(timeout)
          runningProcesses.delete(procId)

          try {
            const parsed = stdout.trim() ? JSON.parse(stdout.trim()) : {}

            if (exitCode === 0) {
              resolve({ success: true, data: parsed })
            } else {
              const errorData = stderr.trim() ? JSON.parse(stderr.trim()) : { error: 'Unknown error' }
              resolve({ success: false, error: errorData.error || 'Operation failed', data: parsed })
            }
          } catch {
            resolve({ success: false, error: stderr || 'Invalid JSON output', data: stdout })
          }
        })

        proc.on('error', (err) => {
          clearTimeout(timeout)
          runningProcesses.delete(procId)
          resolve({ success: false, error: err.message })
        })
      })

      return result
    } catch (err) {
      return { success: false, error: err instanceof Error ? err.message : String(err) }
    }
  })

  ipcMain.handle('hermes:site-ops:deep-map', async (_event, command: 'init' | 'scan' | 'status', sitePattern: string): Promise<SiteOpsResult> => {
    try {
      const { stdout, stderr, exitCode } = await runNodeScript(DEEP_MAP_SCRIPT, [command, sitePattern], 120000)

      if (exitCode === 0) {
        try {
          const parsed = JSON.parse(stdout.trim()) as Record<string, unknown>

          const valid = parsed && typeof parsed === 'object' && (
            (command === 'init' && parsed.initialized === true && typeof parsed.slug === 'string') ||
            (command === 'scan' && parsed.scanned === true && typeof parsed.elements === 'number') ||
            (command === 'status' && typeof parsed.slug === 'string' && Array.isArray(parsed.pendingPhases))
          )

          return valid
            ? { success: true, data: parsed }
            : { success: false, error: `Incomplete deep-map ${command} result`, data: parsed }
        } catch {
          return { success: false, error: 'Invalid JSON output from deep-map', data: stdout }
        }
      } else {
        return { success: false, error: stderr || `Deep map ${command} failed` }
      }
    } catch (err) {
      return { success: false, error: err instanceof Error ? err.message : String(err) }
    }
  })

  ipcMain.handle('hermes:site-ops:cancel', async (_event, procId?: string) => {
    if (procId && runningProcesses.has(procId)) {
      const proc = runningProcesses.get(procId)!
      proc.kill('SIGTERM')
      setTimeout(() => proc.kill('SIGKILL'), 1000)
      runningProcesses.delete(procId)

      return { success: true }
    }

    return { success: false, error: 'No such process' }
  })
}

export function disposeSiteOpsIpc(): void {
  ipcMain.removeHandler('hermes:site-ops:execute')
  ipcMain.removeHandler('hermes:site-ops:deep-map')
  ipcMain.removeHandler('hermes:site-ops:cancel')

  for (const proc of runningProcesses.values()) {
    try {
      proc.kill('SIGTERM')
      setTimeout(() => proc.kill('SIGKILL'), 1000)
    } catch {
      // ignore
    }
  }

  runningProcesses.clear()
}