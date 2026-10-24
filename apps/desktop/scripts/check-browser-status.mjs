import { connectAiControl } from './ai-control-client.mjs'

async function checkBrowserStatus() {
  const client = await connectAiControl()
  try {
    const res = await client.evaluate(`(async () => {
      if (window.hermesDesktop?.workstationBrowser?.status) {
        return await window.hermesDesktop.workstationBrowser.status();
      }
      if (window.electron?.ipcRenderer?.invoke) {
        return await window.electron.ipcRenderer.invoke('hermes:workstation-browser:status');
      }
      // Inspect window.hermesDesktop keys
      return {
        hasHermesDesktop: !!window.hermesDesktop,
        keys: window.hermesDesktop ? Object.keys(window.hermesDesktop) : [],
        electronKeys: window.electron ? Object.keys(window.electron) : []
      };
    })()`)
    console.log(JSON.stringify(res, null, 2))
  } finally {
    client.close()
  }
}

checkBrowserStatus().catch(err => {
  console.error(err)
  process.exit(1)
})
