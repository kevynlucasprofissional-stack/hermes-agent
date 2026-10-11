const root = document.querySelector('#fixture-root')
const title = document.querySelector('#fixture-title')
const status = document.querySelector('#fixture-status')
const scenario = location.pathname.split('/').filter(Boolean).at(-1) || 'index'
const params = new URLSearchParams(location.search)
const runId = params.get('run_id') || 'missing-run-id'

const setStatus = value => {
  status.textContent = value
  status.dataset.state = value
}

const postState = async (name, value) => {
  const response = await fetch(`/api/state/${encodeURIComponent(name)}?run_id=${encodeURIComponent(runId)}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(value)
  })

  if (!response.ok) {
    throw new Error(`state write failed: ${response.status}`)
  }

  return response.json()
}

function renderIndex() {
  const list = document.createElement('ul')

  for (const name of window.__BROW01_FIXTURE__.scenarios) {
    const item = document.createElement('li')
    const link = document.createElement('a')
    link.href = `/scenario/${name}?run_id=${encodeURIComponent(runId)}`
    link.textContent = name
    item.append(link)
    list.append(item)
  }

  root.append(list)
  setStatus('ready')
}

function renderForms() {
  root.innerHTML = `
    <form data-testid="profile-form">
      <label>Name <input data-testid="form-name" name="name" autocomplete="off" /></label>
      <label>Email <input data-testid="form-email" name="email" type="email" autocomplete="off" /></label>
      <label>Priority
        <select data-testid="form-priority" name="priority">
          <option value="normal">Normal</option><option value="high">High</option>
        </select>
      </label>
      <label><input data-testid="form-confirm" name="confirmed" type="checkbox" /> Confirm</label>
      <button data-testid="form-submit" type="submit">Save form</button>
    </form>`
  root.querySelector('form').addEventListener('submit', async event => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    await postState('forms', {
      name: data.get('name'),
      email: data.get('email'),
      priority: data.get('priority'),
      confirmed: data.get('confirmed') === 'on'
    })
    setStatus('form-saved')
  })
  setStatus('ready')
}

function renderDelayedHydration() {
  const delayMs = Math.min(5_000, Math.max(0, Number(params.get('delay_ms') || 350)))
  root.innerHTML = '<p data-testid="hydration-placeholder">Waiting for hydration</p>'
  setStatus('waiting')
  setTimeout(() => {
    root.innerHTML = '<button data-testid="hydration-action">Hydrated action</button>'
    root.querySelector('button').addEventListener('click', async () => {
      await postState('delayed-hydration', { activated: true, delay_ms: delayMs })
      setStatus('hydrated-action-fired')
    })
    setStatus('hydrated')
  }, delayMs)
}

function renderListsTables() {
  const rowCount = Math.min(2_000, Math.max(10, Number(params.get('rows') || 500)))
  const rows = Array.from({ length: rowCount }, (_, index) => {
    const id = index + 1
    return `<tr data-testid="row-${id}"><td>${id}</td><td>Item ${String(id).padStart(4, '0')}</td><td>${id % 2 ? 'ready' : 'queued'}</td></tr>`
  }).join('')
  root.innerHTML = `
    <table data-testid="items-table">
      <caption>BROW-01 deterministic items</caption>
      <thead><tr><th>ID</th><th>Name</th><th>Status</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`
  setStatus(`rows-${rowCount}`)
}

function renderRichEditor() {
  root.innerHTML = `
    <div data-testid="rich-editor" contenteditable="true" role="textbox" aria-label="Rich text"></div>
    <button data-testid="rich-save">Save rich text</button>`
  root.querySelector('button').addEventListener('click', async () => {
    await postState('rich-editor', { text: root.querySelector('[contenteditable]').innerText })
    setStatus('rich-saved')
  })
  setStatus('ready')
}

function renderNavigation() {
  const target = location.pathname.endsWith('/navigation-target')

  if (target) {
    root.innerHTML = '<h2 data-testid="navigation-target">Navigation target</h2><a data-testid="navigation-back" href="/scenario/navigation">Back</a>'
    document.title = 'BROW-01 navigation target'
    setStatus('navigation-target')
    return
  }

  root.innerHTML = '<a data-testid="navigation-next" href="/scenario/navigation-target">Open target</a>'
  setStatus('ready')
}

async function renderRecovery() {
  const key = `brow01-recovery:${runId}`
  const localCount = Number(localStorage.getItem(key) || 0) + 1
  localStorage.setItem(key, String(localCount))
  const state = await postState('tab-recovery', { local_count: localCount })
  root.innerHTML = `<p data-testid="recovery-marker">Recovery visit ${state.write_count}; local ${localCount}</p>`
  setStatus('recovery-ready')
}

function renderHumanTakeover() {
  root.innerHTML = `
    <p>The button below is only a fixture cue. Acquire the real Hermes human-control lease in the Desktop UI.</p>
    <button data-testid="takeover-cue">Mark local cue</button>`
  root.querySelector('button').addEventListener('click', () => {
    document.body.classList.add('takeover-active')
    window.dispatchEvent(new CustomEvent('brow01:takeover-cue'))
    setStatus('takeover-cue-active')
  })
  setStatus('ready')
}

window.__BROW01_FIXTURE__ = Object.freeze({
  classification: 'FIXTURE_SMOKE',
  run_id: runId,
  scenario,
  scenarios: Object.freeze([
    'forms',
    'delayed-hydration',
    'lists-tables',
    'rich-editor',
    'navigation',
    'tab-recovery',
    'human-takeover'
  ])
})

title.textContent = `BROW-01 · ${scenario}`
document.title = `BROW-01 ${scenario}`

const renderers = {
  forms: renderForms,
  'delayed-hydration': renderDelayedHydration,
  'lists-tables': renderListsTables,
  'rich-editor': renderRichEditor,
  navigation: renderNavigation,
  'navigation-target': renderNavigation,
  'tab-recovery': renderRecovery,
  'human-takeover': renderHumanTakeover
}

await (renderers[scenario] ?? renderIndex)()
