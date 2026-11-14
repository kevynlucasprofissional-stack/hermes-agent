/* Isolated, actual Electron/WebContentsView Browser runtime contract harness.
 * Pattern adapted from Playwright tests/electron/electron-webcontentsview.spec.ts
 * (Apache-2.0), without copying Playwright source or creating a browser owner.
 */
'use strict'
require('tsx/cjs')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const { app, BrowserWindow, WebContentsView } = require('electron')
const temp = process.env.HERMES_C2C_TEST_ROOT || fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-playwright-native-'))
app.setPath('userData', path.join(temp, 'electron'))
Object.assign(process.env, {
  HERMES_TEST_ISOLATION: temp,
  HERMES_WORKSTATION_HOME: path.join(temp, 'workstation'),
  HERMES_WORKSTATION_BROWSER_PROFILE: path.join(temp, 'profile'),
  HERMES_WORKSTATION_BROWSER_CONTROL_FILE: path.join(temp, 'controller.json'),
  HERMES_WORKSTATION_BROWSER_TASK_FILE: path.join(temp, 'tasks.json'),
  HERMES_HOME: path.join(temp, 'hermes')
})
let runtime
let win
async function run() {
  const { WorkstationBrowserRuntime } = require('./workstation-browser-runtime.ts')
  runtime = new WorkstationBrowserRuntime()
  win = new BrowserWindow({ show: false, width: 900, height: 650, webPreferences: { sandbox: true } })
  await win.loadURL('data:text/html,<title>Hermes Test Host</title>')
  const taskId = 'playwright-c2c-offline'
  runtime.createTask({ taskId, sessionHost: 'offline-session', runId: 'offline-run' })
  runtime.showTask(taskId, win, { x: 0, y: 0, width: 800, height: 600 })
  const state = runtime.state()
  const tab = state.tabs.find(t => t.ownerTaskId === taskId)
  assert.ok(tab, 'BrowserTask owns tab')
  const contents = runtime.getWebContents(tab.id)
  assert.ok(contents && !contents.isDestroyed(), 'one native WebContents')
  const matches = win.contentView.children.filter(v => v instanceof WebContentsView && v.webContents === contents)
  assert.equal(matches.length, 1, 'exactly one Hermes-owned WebContentsView attached')
  const html = '<!doctype html><title>Native fixture</title>' +
    '<button id="act" onclick="document.querySelector(\'#status\').textContent=\'clicked\'">Click</button>' +
    '<span id="status">waiting</span>' +
    '<input id="field" placeholder="offline">' +
    '<iframe title="child" srcdoc="<button>Child</button>"></iframe>'
  await contents.loadURL('data:text/html;charset=UTF-8,' + encodeURIComponent(html))
  // WhatsApp puts the send icon inside the actionable footer button. The icon
  // itself is not returned by the interactive-element inventory.
  await contents.executeJavaScript(`document.body.insertAdjacentHTML('beforeend',
    '<footer id="chat-footer"><button id="native-send-button"><span data-icon="send"></span></button></footer><span data-testid="send" id="unrelated-noninteractive-send"></span>')`)
  const before = await runtime.snapshotForEntry(runtime.entries.get(tab.id), true)
  const sendButtons = before.elements.filter(e => e.sendControl === true)
  assert.equal(sendButtons.length, 1, 'nested send icon resolves to one actionable footer control')
  assert.equal(sendButtons[0].tag, 'button')
  assert.equal(sendButtons[0].ref.length > 0, true)
  assert.equal(before.elements.filter(e => e.testid === 'send').length, 0,
    'noninteractive send icons must not be clickable refs')
  await contents.executeJavaScript(`document.getElementById('native-send-button').addEventListener('click',
    e => { e.currentTarget.dataset.clicked = 'yes' })`)
  await runtime.clickRef(runtime.entries.get(tab.id), sendButtons[0].ref)
  assert.equal(await contents.executeJavaScript(`document.getElementById('native-send-button').dataset.clicked`),
    'yes', 'resolved footer button is actually clicked in isolated Chromium')
  assert.equal(before.success, true, 'real Chromium inventory')
  assert.ok(before.__telemetry.renderer_memory_bytes > 0, 'renderer memory is measured independently of MAIN')
  assert.ok(before.__telemetry.renderer_pid > 0, 'renderer operating-system PID is identified')
  const button = before.elements.find(e => e.tag === 'button' && e.label === 'Click')
  assert.ok(button, 'snapshot contains clickable ref')
  await contents.executeJavaScript(`(function(){
    const overlay = document.createElement('div'); overlay.id = 'test-overlay';
    Object.assign(overlay.style, { position: 'fixed', zIndex: '999999', inset: '0', background: 'transparent' });
    document.body.append(overlay);
  })()`)
  await assert.rejects(runtime.clickRef(runtime.entries.get(tab.id), button.ref), /target_obscured|target_not_actionable/)
  assert.equal(await contents.executeJavaScript('document.querySelector("#status").textContent'), 'waiting')
  await contents.executeJavaScript('document.querySelector("#test-overlay").remove()')
  await contents.executeJavaScript('document.querySelector("#act").disabled = true')
  await assert.rejects(runtime.clickRef(runtime.entries.get(tab.id), button.ref), /target_not_actionable/)
  await contents.executeJavaScript('document.querySelector("#act").disabled = false')
  await contents.executeJavaScript(`(function(){
    var scroller=document.createElement('div');
    scroller.id='disabled-scroller';
    Object.assign(scroller.style,{height:'30px',width:'220px',overflow:'auto'});
    scroller.innerHTML='<div style="height:320px"></div><button data-testid="disabled-scrolled" disabled>Disabled below fold</button>';
    document.body.append(scroller);
  })()`)
  const beforeDisabledScroll = await contents.executeJavaScript('document.getElementById("disabled-scroller").scrollTop')
  await assert.rejects(
    runtime.clickRef(runtime.entries.get(tab.id), '@missing-disabled', { type: 'testid', value: 'disabled-scrolled' }),
    /target_not_actionable/
  )
  assert.equal(await contents.executeJavaScript('document.getElementById("disabled-scroller").scrollTop'),
    beforeDisabledScroll, 'disabled target must not trigger DOM scroll before actionability validation')
  await contents.executeJavaScript('document.body.insertAdjacentHTML("beforeend", "<button data-testid=\\"dupe\\">A</button><button data-testid=\\"dupe\\">B</button>")')
  await assert.rejects(runtime.resolvePoint(runtime.entries.get(tab.id), '@missing', false, { type: 'testid', value: 'dupe' }), /ambiguous_anchor/)
  // Simulate a human takeover during async read-only target resolution.
  const originalResolvePoint = runtime.resolvePoint
  runtime.resolvePoint = async function (...args) {
    const point = await originalResolvePoint.apply(this, args)
    this.takeControl(taskId, 'offline-session')
    return point
  }
  await assert.rejects(runtime.clickRef(runtime.entries.get(tab.id), button.ref), /USER_CONTROL_ACTIVE|human.control|under human control/i)
  runtime.resolvePoint = originalResolvePoint
  assert.equal(await contents.executeJavaScript('document.querySelector("#status").textContent'), 'waiting')
  runtime.releaseControl(taskId)
  await runtime.clickRef(runtime.entries.get(tab.id), button.ref)
  const localReadback = await contents.executeJavaScript('document.querySelector("#status").textContent')
  assert.equal(localReadback, 'clicked', 'real renderer proves DOM effect')
  // A short-lived SPA overlay must not permanently abort text entry before
  // any text input has been dispatched. Clicks remain strict above.
  const typeSnapshot = await runtime.snapshotForEntry(runtime.entries.get(tab.id), true)
  const field = typeSnapshot.elements.find(e => e.tag === 'input' && e.label === 'offline')
  assert.ok(field, 'editable input ref exists in the real Chromium DOM')
  await contents.executeJavaScript(`(function () {
    const overlay=document.createElement('div');overlay.id='transient-type-overlay';
    Object.assign(overlay.style,{position:'fixed',inset:'0',zIndex:'99999',background:'transparent'});
    document.body.append(overlay);
    setTimeout(()=>overlay.remove(),350);
  })()`)
  await runtime.typeRef(runtime.entries.get(tab.id), field.ref, 'transient-ready', {clear:true})
  assert.equal(await contents.executeJavaScript('document.querySelector("#field").value'), 'transient-ready')
  await contents.executeJavaScript(`(function () {
    const overlay=document.createElement('div');overlay.id='persistent-type-overlay';
    Object.assign(overlay.style,{position:'fixed',inset:'0',zIndex:'99999',background:'transparent'});
    document.body.append(overlay);
  })()`)
  await assert.rejects(runtime.typeRef(runtime.entries.get(tab.id), field.ref, 'MUST-NOT-ENTER', {clear:true}), /target_obscured/)
  assert.equal(await contents.executeJavaScript('document.querySelector("#field").value'), 'transient-ready', 'persistent obstruction blocks text before effect')
  await contents.executeJavaScript('document.querySelector("#persistent-type-overlay").remove()')
  runtime.takeControl(taskId, 'offline-session')
  assert.throws(() => runtime.assertAgentControl(taskId), /USER_CONTROL_ACTIVE|human|control/i)
  const frameCount = await contents.executeJavaScript('document.querySelectorAll("iframe").length')
  assert.equal(frameCount, 1, 'iframe hosted in same browser view')
  await contents.executeJavaScript('document.querySelector("iframe").remove()')
  const extractArgs = { mode: 'inspect', selector: '#status', attributes: [] }
  const first = await runtime.extractItemsForEntry(runtime.entries.get(tab.id), extractArgs)
  const cached = await runtime.extractItemsForEntry(runtime.entries.get(tab.id), extractArgs)
  assert.equal(first.cached, false)
  assert.equal(cached.cached, true, 'stable DOM can reuse extraction')
  const childCount = await contents.executeJavaScript('document.body.childElementCount')
  await contents.executeJavaScript('document.querySelector("#status").textContent="updated"')
  assert.equal(await contents.executeJavaScript('document.body.childElementCount'), childCount)
  const changed = await runtime.extractItemsForEntry(runtime.entries.get(tab.id), extractArgs)
  assert.equal(changed.cached, false, 'SPA text mutation invalidates old result')
  assert.equal(changed.items[0].text, 'updated')
  process.stdout.write('NATIVE_E2E_PASS pid=' + process.pid + ' tab=' + tab.id + ' viewCount=' + matches.length + '\n')
}
app.whenReady().then(run).then(async () => {
  await runtime?.destroy()
  win?.destroy()
  // Windows keeps Electron's profile files open until the process exits;
  // the external runner owns cleanup after process termination.
  app.quit()
}).catch(async error => {
  process.stderr.write('NATIVE_E2E_FAIL ' + (error?.stack ?? error) + '\n')
  try { await runtime?.destroy() } catch {}
  try { win?.destroy() } catch {}
  app.exit(1)
})
