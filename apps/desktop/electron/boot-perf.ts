// Boot performance milestones: pure utility for [boot-perf] log lines.
// No IPC, no state, no persistence — diagnostic logs only. The aggregated
// startup-latency metric lives in startup-latency-ipc.ts; this module
// records per-phase timings so cold-start bottlenecks are visible in
// desktop.log and the dev console without adding overhead to the hot path.

const BOOT_EPOCH_MS = Date.now()

export type BootPerfPhase =
  | 'electron.ready'
  | 'window.create.begin'
  | 'window.created'
  | 'renderer.load.started'
  | 'renderer.did-finish-load'
  | 'window.revealed'
  | 'backend.connection.resolved'
  | 'backend.connection.failed'
  | 'renderer.hydration.started'
  | 'renderer.hydration.completed'

/** Format a [boot-perf] log line. `electronElapsedMs` is derived from
 *  process.uptime() at the call site so callers don't need to thread it;
 *  `bootstrapElapsedMs` is wall-clock since this module was first imported
 *  (≈ when the main process started evaluating boot-perf.ts). */
export function formatBootMilestone(
  phase: BootPerfPhase,
  electronUptimeSeconds: number = process.uptime(),
): string {
  const electronElapsedMs = Math.round(electronUptimeSeconds * 1000)
  const bootstrapElapsedMs = Date.now() - BOOT_EPOCH_MS

  return `[boot-perf] phase=${phase} electron_elapsed_ms=${electronElapsedMs} bootstrap_elapsed_ms=${bootstrapElapsedMs}`
}

/** Convenience wrapper: formats AND emits via the provided logger.
 *  Callers pass their existing log function (rememberLog, console.log, etc.)
 *  so this module never owns a transport. */
export function recordBootMilestone(
  phase: BootPerfPhase,
  log: (msg: string) => void,
  electronUptimeSeconds: number = process.uptime(),
): void {
  log(formatBootMilestone(phase, electronUptimeSeconds))
}