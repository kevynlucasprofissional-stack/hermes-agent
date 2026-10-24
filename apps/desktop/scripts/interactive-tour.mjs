// Interactive Tour of Hermes Work Desktop
import { connectAiControl } from './ai-control-client.mjs'

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function runInteractiveTour() {
  const client = await connectAiControl()
  const report = {
    startedAt: new Date().toISOString(),
    modules: {},
    panes: {},
    chatComposer: {},
  }

  try {
    // Step 0: Verify AI Control
    const aiActive = await client.evaluate('window.__hermesAiControlActive')
    if (!aiActive) {
      throw new Error('AI Control is not active. Press Ctrl+Shift+A in the Hermes window.')
    }

    // Step 1: Tour Left Sidebar Modules
    const moduleNames = [
      { id: 'workstation', label: 'Workstation' },
      { id: 'capabilities', label: 'Capabilities' },
      { id: 'messaging', label: 'Messaging' },
      { id: 'artifacts', label: 'Artifacts' },
      { id: 'scheduled', label: 'Scheduled jobs' },
      { id: 'vault', label: 'Vault' },
      { id: 'kanban', label: 'Kanban' },
    ]

    console.log('--- Iniciando Tour pelos Módulos Principais ---')
    for (const mod of moduleNames) {
      console.log(`Visitando módulo: ${mod.label}...`)
      const clickExpr = `(() => {
        const btns = Array.from(document.querySelectorAll('button[data-sidebar="menu-button"]'));
        const btn = btns.find(b => (b.textContent || '').trim() === '${mod.label}');
        if (btn) { btn.click(); return true; }
        return false;
      })()`

      const clicked = await client.evaluate(clickExpr)
      await sleep(1200) // Pause for visual observation and render

      const detailsExpr = `(() => {
        const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4')).map(h => (h.textContent || '').trim()).filter(Boolean);
        const buttons = Array.from(document.querySelectorAll('button')).map(b => (b.textContent || '').trim() || b.getAttribute('aria-label')).filter(Boolean).slice(0, 15);
        const activeTab = document.querySelector('[role="tab"][aria-selected="true"]')?.textContent?.trim() || null;
        return { headings, buttons, activeTab };
      })()`

      const details = await client.evaluate(detailsExpr)
      report.modules[mod.id] = { label: mod.label, clicked, ...details }
    }

    // Step 2: Tour Right Sidebar Panes
    const rightTabs = ['Sessions', 'Bots', 'Files', 'Terminal', 'Browser']
    console.log('--- Iniciando Tour pelas Abas do Painel Lateral Direito ---')
    for (const tabName of rightTabs) {
      console.log(`Abrindo painel: ${tabName}...`)
      const clickTabExpr = `(() => {
        const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
        const tab = tabs.find(t => (t.textContent || '').trim() === '${tabName}');
        if (tab) { tab.click(); return true; }
        return false;
      })()`

      const clicked = await client.evaluate(clickTabExpr)
      await sleep(1200) // Pause for visual observation

      const paneDetailsExpr = `(() => {
        const activeTab = document.querySelector('[role="tab"][aria-selected="true"]')?.textContent?.trim();
        const textSnippets = Array.from(document.querySelectorAll('div, section, span, button'))
          .filter(el => el.children.length === 0 && (el.textContent || '').trim().length > 3)
          .map(el => el.textContent.trim())
          .filter(t => !['Sessions', 'Bots', 'Files', 'Terminal', 'Browser'].includes(t))
          .slice(0, 8);
        return { activeTab, textSnippets };
      })()`

      const paneDetails = await client.evaluate(paneDetailsExpr)
      report.panes[tabName] = { clicked, ...paneDetails }
    }

    // Return right sidebar to Sessions
    await client.evaluate(`(() => {
      const tab = Array.from(document.querySelectorAll('[role="tab"]')).find(t => (t.textContent || '').trim() === 'Sessions');
      tab?.click();
    })()`)

    // Step 3: Inspect Chat Composer & Settings
    console.log('--- Inspecionando Barra de Chat e Composer ---')
    const composerExpr = `(() => {
      const input = document.querySelector('div[role="textbox"][aria-label="Message"]');
      const modelBtn = document.querySelector('button[aria-label^="Model ·"]') || document.querySelector('button[aria-label="Open model picker"]');
      const effortBtn = document.querySelector('button[aria-label^="Effort:"]');
      const voiceBtn = document.querySelector('button[aria-label="Voice dictation"]');
      const contextBtn = document.querySelector('button[aria-label="Add context"]');
      return {
        hasMessageInput: !!input,
        currentModel: modelBtn?.textContent?.trim() || modelBtn?.getAttribute('aria-label') || 'Padrão',
        effortLevel: effortBtn?.textContent?.trim() || effortBtn?.getAttribute('aria-label') || 'N/A',
        hasVoiceDictation: !!voiceBtn,
        hasContextAttachment: !!contextBtn
      };
    })()`

    report.chatComposer = await client.evaluate(composerExpr)
    report.completedAt = new Date().toISOString()
    console.log('--- Tour Concluído com Sucesso! ---')
    console.log(JSON.stringify(report, null, 2))
  } finally {
    client.close()
  }
}

runInteractiveTour().catch(err => {
  console.error('Erro no tour:', err)
  process.exit(1)
})
