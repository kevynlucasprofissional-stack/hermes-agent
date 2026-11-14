// Offline Chromium/CDP smoke proof. Does not submit forms or connect to any external origin.
const { app, BrowserWindow } = require('electron')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')

app.whenReady().then(async () => {
  const sample = path.join(os.tmpdir(), `hermes-upload-fixture-${process.pid}.txt`)
  let window
  try {
    fs.writeFileSync(sample, 'Hermes offline CDP selection proof\n')
    window = new BrowserWindow({ show: false, webPreferences: { nodeIntegration: false, contextIsolation: true } })
    const document = '<!doctype html><title>offline-upload-proof</title><input type="file" id="asset"><script>window.uploadChanges=0;document.getElementById("asset").addEventListener("change",()=>{window.uploadChanges++});</script>'
    await window.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(document))
    const wc = window.webContents
    wc.debugger.attach('1.3')
    await wc.debugger.sendCommand('DOM.enable')
    const selector = 'input#asset'
    const expression = `(() => { const nodes = document.querySelectorAll(${JSON.stringify(selector)}); if (nodes.length !== 1) return null; const el = nodes[0]; return el instanceof HTMLInputElement && el.type === 'file' ? el : null })()`
    const target = await wc.debugger.sendCommand('Runtime.evaluate', { expression, returnByValue: false })
    if (!target?.result?.objectId) throw new Error('NO_FILE_INPUT')
    await wc.debugger.sendCommand('DOM.setFileInputFiles', { files: [sample], objectId: target.result.objectId })
    const observed = await wc.executeJavaScript('({count:document.getElementById("asset").files.length, name:document.getElementById("asset").files[0]?.name, changes:window.uploadChanges})')
    const ok = observed.count === 1 && observed.name === path.basename(sample) && observed.changes > 0
    process.stdout.write(JSON.stringify({ kind: 'ELECTRON_OFFLINE_CDP', chromium: process.versions.chrome, ...observed, ok }) + '\n')
    app.exit(ok ? 0 : 2)
  } catch (error) {
    process.stderr.write('NATIVE_PROOF_ERROR=' + String(error) + '\n')
    app.exit(1)
  } finally {
    if (window && !window.isDestroyed()) window.destroy()
    fs.rmSync(sample, { force: true })
  }
}).catch(err => { process.stderr.write(String(err) + '\n'); app.exit(1) })
