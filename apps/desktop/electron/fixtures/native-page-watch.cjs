// Native Electron Chromium fixture, localhost-only. Zero external pages or telemetry.
const { app, BrowserWindow } = require('electron')
const http = require('node:http')
const path = require('node:path')
const esbuild = require('esbuild')
const vm = require('node:vm')

async function run() {
  const entry = path.resolve(__dirname, '..', 'workstation-browser-page-watch.ts')
  const built = esbuild.buildSync({
    entryPoints: [entry], bundle: true, platform: 'node', format: 'cjs',
    write: false, target: 'node22'
  })
  const nodeModule = { exports: {} }
  const ctx = { exports: nodeModule.exports, module: nodeModule, require,
    __dirname: path.dirname(entry), process, console, Buffer, URL, setInterval, clearInterval }
  vm.runInNewContext(built.outputFiles[0].text, ctx, { filename: 'page-watch-bundle.cjs' })
  const { PageWatchCoordinator, buildPageWatchProbe, buildPageWatchDisconnect } = nodeModule.exports
  const server = http.createServer((_req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' })
    res.end('<!doctype html><html><body><ul id="items"><li>one</li><li>two</li></ul><span id="clock">18:00</span></body></html>')
  })
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  const origin = 'http://127.0.0.1:' + server.address().port
  const w = new BrowserWindow({ show: false, webPreferences: { nodeIntegration: false, contextIsolation: true } })
  const wc = w.webContents
  const config = { id: 'native-1', session_id: 'fixture-session', tab_id: 'fixture-tab',
    origin, selector: '#items', rule: 'child_count', route_id: 'fixture-route', enabled: true }
  const safe = buildPageWatchProbe(config)
  const events = []
  let now = 1_000
  const coordinator = new PageWatchCoordinator({ now: () => now, debounceMs: 100,
    onEvent: evt => events.push(evt) })
  try {
    await w.loadURL(origin)
    await coordinator.arm(config, () => wc.executeJavaScript(safe),
      () => wc.executeJavaScript(buildPageWatchDisconnect(config)))
    // repaint and clock text update must not create an event.
    await wc.executeJavaScript("document.querySelector('#clock').textContent='18:01'")
    now += 160
    await coordinator.probeOnce(config.id)
    if (events.length) throw new Error('NOISE_FALSE_POSITIVE')
    await wc.executeJavaScript("document.querySelector('#items').appendChild(document.createElement('li'))")
    now += 1; await coordinator.probeOnce(config.id)
    now += 120; await coordinator.probeOnce(config.id)
    if (events.length !== 1 || events[0].current !== 3) throw new Error('NO_CHANGE_EVENT')
    await wc.executeJavaScript("const el=document.createElement('input'); el.type='password'; document.body.appendChild(el)")
    await coordinator.probeOnce(config.id)
    if (coordinator.status(config.id).reason !== 'auth_required') throw new Error('AUTH_NOT_PAUSED')
    if (events.length !== 1) throw new Error('EVENT_AFTER_AUTH')
    // No automatic rearm on reload/logout or renderer crash.
    coordinator.tabLifecycle(config.tab_id, 'tab_closed')
    await new Promise(resolve => setTimeout(resolve, 20))
    const observerPresent = await wc.executeJavaScript('Boolean(window.__hermesPageWatchP06)')
    if (observerPresent) throw new Error('OBSERVER_NOT_DISCONNECTED')
    process.stdout.write(JSON.stringify({
      proof: 'NATIVE_ELECTRON_CHROMIUM_PAGE_WATCH',
      chromium: process.versions.chrome, events: events.length,
      event_id_length: events[0].event_id.length,
      fingerprints_only: !JSON.stringify(events).includes('one') &&
        !JSON.stringify(events).includes('18:01'),
      state: coordinator.status(config.id).status,
      reason: coordinator.status(config.id).reason,
      external_network_calls: 0
    }) + '\n')
  } finally {
    if (!w.isDestroyed()) w.destroy()
    await new Promise(resolve => server.close(resolve))
  }
}
app.whenReady().then(async () => {
  try { await run(); app.exit(0) }
  catch (error) { process.stderr.write('P06_NATIVE_FAIL=' + String(error) + '\n'); app.exit(1) }
}).catch(error => { process.stderr.write(String(error) + '\n'); app.exit(1) })
