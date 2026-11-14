import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

import { test } from 'vitest'

const legacyScript = fileURLToPath(new URL('../../../../site-ops/scripts/site-ops/whatsapp-web.mjs', import.meta.url))

test.each(['send-message', 'open-chat'])('standalone CLI rejects legacy %s before CDP target discovery', operation => {
  const result = spawnSync(process.execPath, [legacyScript, operation, 'TEST_FIXTURE_ONLY'], {
    encoding: 'utf8',
    timeout: 5000,
    env: { ...process.env, HERMES_DESKTOP_CDP_PORT: '1' }
  })
  assert.equal(result.status, 1)
  assert.match(result.stderr, /NATIVE_WHATSAPP_EXECUTOR_REQUIRED/)
  assert.doesNotMatch(result.stderr, /ECONNREFUSED|fetch failed|WebSocket/)
})
