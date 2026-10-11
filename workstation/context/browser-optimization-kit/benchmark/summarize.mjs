import { writeFile } from 'node:fs/promises'

import { readMeasurements, summarizeMeasurements } from './measurements.mjs'

function parseArgs(argv) {
  const args = {}

  for (let index = 0; index < argv.length; index++) {
    const token = argv[index]
    if (token === '--input' || token === '--output') {
      args[token.slice(2)] = argv[++index]
    } else {
      throw new Error(`unknown argument: ${token}`)
    }
  }

  if (!args.input) throw new Error('--input is required')
  return args
}

const args = parseArgs(process.argv.slice(2))
const summary = summarizeMeasurements(await readMeasurements(args.input))
const rendered = `${JSON.stringify(summary, null, 2)}\n`

if (args.output) {
  await writeFile(args.output, rendered, 'utf8')
}

process.stdout.write(rendered)
