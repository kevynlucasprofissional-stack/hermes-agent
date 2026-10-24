/**
 * Dev Chrome DevTools Protocol exposure for the desktop renderer.
 *
 * The renderer is a Chromium page, so `--remote-debugging-port` turns it into
 * something the repo's existing CDP tooling (`scripts/eval.mjs`,
 * `scripts/perf/lib/cdp.mjs`, the `diag-*` / `probe-*` family) can attach to
 * and read the live DOM from. The ordinary launcher and direct dev-server
 * runs now use the separate authenticated native AI Control bridge instead;
 * Chromium CDP is powerful and must require an explicit developer opt-in.
 *
 *  - packaged build              → always closed, whatever the env says.
 *  - no HERMES_DESKTOP_DEV_SERVER → closed (an unpackaged `electron .` against
 *    dist/ is how the packaged app gets smoke tested; it should behave like
 *    the packaged app).
 *  - dev run without explicit opt-in → closed (native AI Control available).
 *  - dev run with HERMES_DESKTOP_CDP_PORT=9222 → open, debug use only.
 *  - HERMES_DESKTOP_CDP_PORT=off / 0 / false → explicitly closed.
 *
 * The port binds to loopback (Chromium's default) and the address is
 * deliberately not configurable: there is no reason to expose a renderer
 * debugger off-host, and offering the knob invites someone to try.
 */

/** Why the port is closed, for a one-line log the developer can act on. */
type ClosedReason = 'packaged' | 'no-dev-server' | 'not-requested' | 'opted-out' | 'invalid-port'

type DevCdpDecision = { port: number; reason: null } | { port: null; reason: ClosedReason }

type DevCdpInput = {
  env: Record<string, string | undefined>
  isPackaged: boolean
  devServer: string | undefined
}

/** What every script under scripts/ already reaches for. */
const DEFAULT_PORT = 9222

// Below 1024 needs privileges on most platforms; 65535 is the ceiling.
const MIN_PORT = 1024
const MAX_PORT = 65535

const OPT_OUT = new Set(['0', 'off', 'false', 'no'])

/**
 * Decide whether this run may expose a renderer debugging port, and on which
 * port. Pure: every input is passed in, so the gate is testable without an
 * Electron app or a real environment.
 */
function resolveDevCdpPort({ env, isPackaged, devServer }: DevCdpInput): DevCdpDecision {
  // Packaged wins over everything. Checked first so no combination of
  // environment variables can talk a shipped build into opening the port.
  if (isPackaged) {
    return { port: null, reason: 'packaged' }
  }

  // A dev server means a source-tree run (`npm run dev` / `hgui`).
  if (!devServer) {
    return { port: null, reason: 'no-dev-server' }
  }

  const requested = (env.HERMES_DESKTOP_CDP_PORT ?? '').trim()

  if (!requested) {
    return { port: null, reason: 'not-requested' }
  }

  if (OPT_OUT.has(requested.toLowerCase())) {
    return { port: null, reason: 'opted-out' }
  }

  const port = Number(requested)

  if (!Number.isInteger(port) || port < MIN_PORT || port > MAX_PORT) {
    return { port: null, reason: 'invalid-port' }
  }

  return { port, reason: null }
}

/** One-line explanation for a closed port, or null when it opened. */
function describeDevCdpDecision(decision: DevCdpDecision): string | null {
  switch (decision.reason) {
    case null:
      return null

    case 'invalid-port':
      return `HERMES_DESKTOP_CDP_PORT is not a valid port (expected an integer ${MIN_PORT}-${MAX_PORT}, or "off"); renderer debugging is disabled.`

    case 'opted-out':
      return 'renderer debugging disabled by HERMES_DESKTOP_CDP_PORT.'

    // Packaged and dist-run builds are closed by design — the common case, not
    // worth a line of startup noise.
    case 'packaged':

    case 'no-dev-server':

    case 'not-requested':
      return null
  }
}

export { DEFAULT_PORT, describeDevCdpDecision, resolveDevCdpPort }
export type { DevCdpDecision }
