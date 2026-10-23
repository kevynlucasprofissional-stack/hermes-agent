// Batch eval helper — runs multiple expressions over a single CDP connection.
//
// Usage:
//   node scripts/eval-batch.mjs step1.js step2.js step3.js
//   node scripts/eval-batch.mjs --inline "document.title" "location.href"
//
// Each step file should export a default string (the expression) or be a plain
// text file containing one JS expression. Results are printed as a JSON array
// to stdout, one entry per step: { step, result, error?, durationMs }.
//
// This eliminates the ~200-400ms spawn+connect overhead per step that makes
// sequential eval.mjs calls slow for multi-step navigation tours.

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const port = Number(process.env.HERMES_DESKTOP_CDP_PORT || 9222)

// Parse args
const args = process.argv.slice(2)
let expressions = []

if (args.includes('--inline')) {
  const idx = args.indexOf('--inline')
  expressions = args.slice(idx + 1).map((e, i) => ({ label: `inline-${i}`, expr: e }))
} else if (args.length > 0 && !args[0].startsWith('--')) {
  // File mode: each arg is a path to a file containing an expression
  expressions = args.map((f, i) => {
    const content = readFileSync(resolve(f), 'utf-8').trim()
    return { label: f, expr: content }
  })
} else {
  console.error('Usage: eval-batch.mjs [--inline] <expr1> [expr2] ... | <file1> [file2] ...')
  process.exit(1)
}

// Connect once
let targets
try {
  targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
} catch {
  console.error(
    `no renderer debugging port on 127.0.0.1:${port}. ` +
      'Check the app is running with CDP enabled.'
  )
  process.exit(1)
}

const t = targets.find((t) => t.url.includes('5174')) ?? targets.find((t) => t.type === 'page')
if (!t) {
  console.error(`no page target on 127.0.0.1:${port}`)
  process.exit(1)
}

const ws = new WebSocket(t.webSocketDebuggerUrl)
let id = 0
const pending = new Map()

ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data)
  if (pending.has(m.id)) {
    pending.get(m.id)(m)
    pending.delete(m.id)
  }
})

await new Promise((r) => ws.addEventListener('open', r))

const send = (method, params) =>
  new Promise((res) => {
    const i = ++id
    pending.set(i, res)
    ws.send(JSON.stringify({ id: i, method, params }))
  })

// Execute all steps sequentially over the same connection
const results = []

for (const { label, expr } of expressions) {
  const start = Date.now()
  try {
    const r = await send('Runtime.evaluate', {
      expression: expr,
      returnByValue: true,
      awaitPromise: true,
    })

    if (r.result.exceptionDetails) {
      results.push({
        step: label,
        error: r.result.exceptionDetails.exception?.description || 'unknown exception',
        durationMs: Date.now() - start,
      })
    } else {
      results.push({
        step: label,
        result: r.result.result.value,
        durationMs: Date.now() - start,
      })
    }
  } catch (err) {
    results.push({
      step: label,
      error: err.message,
      durationMs: Date.now() - start,
    })
  }
}

ws.close()
console.log(JSON.stringify(results, null, 2))