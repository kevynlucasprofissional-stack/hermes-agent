// Evaluate in the authorized Hermes renderer. No CDP port required.
import { connectAiControl } from './ai-control-client.mjs'

let client
try {
  client = await connectAiControl()
  const result = await client.evaluate(process.argv[2] || '1+1')
  console.log(JSON.stringify(result === undefined ? null : result, null, 2))
} catch (err) {
  console.error('AI Control: ' + err.message)
  process.exitCode = 1
} finally {
  client?.close()
}
