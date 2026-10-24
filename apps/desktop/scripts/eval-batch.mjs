// Sequential expression evaluation through native AI Control (or explicit
// manually configured CDP). Each result retains the original CLI JSON schema.
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { connectAiControl } from './ai-control-client.mjs'

const args = process.argv.slice(2)
let expressions = []
if (args.includes('--inline')) {
  const idx = args.indexOf('--inline')
  expressions = args.slice(idx + 1).map((expr, i) => ({ label: 'inline-' + i, expr }))
} else if (args.length && !args[0].startsWith('--')) {
  expressions = args.map(file => ({ label: file, expr: readFileSync(resolve(file), 'utf8').trim() }))
} else {
  console.error('Usage: eval-batch.mjs --inline <expr> [expr2] | <file1> [file2]')
  process.exit(1)
}
let client
try { client = await connectAiControl() }
catch (err) { console.error('AI Control: ' + err.message); process.exit(1) }

const results = []
try {
  for (const { label, expr } of expressions) {
    const started = Date.now()
    try {
      results.push({ step: label, result: await client.evaluate(expr), durationMs: Date.now() - started })
    } catch (err) {
      results.push({ step: label, error: err.message, durationMs: Date.now() - started })
    }
  }
  console.log(JSON.stringify(results, null, 2))
} finally {
  client.close()
}
