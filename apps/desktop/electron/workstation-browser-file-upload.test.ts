import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { afterEach, test } from 'vitest'

import { browserFileInputExpression, resolveBrowserUploadGrant, validateBrowserUploadFiles, validateBrowserUploadOrigin } from './workstation-browser-file-upload'

const dirs: string[] = []

function setup() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-upload-ts-'))
  dirs.push(dir)
  const ok = path.join(dir, 'allowed'), outside = path.join(dir, 'outside')
  fs.mkdirSync(ok); fs.mkdirSync(outside)
  const file = path.join(ok, 'test.txt')
  fs.writeFileSync(file, 'test')
  const other = path.join(outside, 'secret.txt')
  fs.writeFileSync(other, 'secret')

  return { dir, ok, file, outside, other }
}

afterEach(() => { for (const d of dirs.splice(0)) {fs.rmSync(d, { recursive: true, force: true })} })

test('no upload without matching, unexpired, operator-configured TaskRun grant', () => {
  const x = setup()
  assert.throws(() => resolveBrowserUploadGrant(x.dir, 'task', 'session', 'run'), /upload_scope_required/)
  fs.writeFileSync(path.join(x.dir, 'config.yaml'), [
    'browser:', '  workstation:', '    upload_grants:',
    '      - task_id: task', '        session_id: session', '        run_id: run',
    '        expires_at: 2099-01-01T00:00:00Z',
    '        allowed_origins:', '          - https://example.test', '        allowed_roots:', `          - ${JSON.stringify(x.ok)}`
  ].join('\n'))
  assert.deepEqual(resolveBrowserUploadGrant(x.dir, 'task', 'session', 'run').allowedRoots, [x.ok])
  assert.throws(() => resolveBrowserUploadGrant(x.dir, 'other', 'session', 'run'), /upload_scope_required/)
  assert.throws(() => resolveBrowserUploadGrant(x.dir, 'task', 'other', 'run'), /upload_scope_required/)
  assert.throws(() => resolveBrowserUploadGrant(x.dir, 'task', 'session', 'other'), /upload_scope_required/)
})

test('upload path normalization accepts only small regular files within granted roots', () => {
  const x = setup()
  const entry = validateBrowserUploadFiles([x.file], { allowedRoots: [x.ok], maxBytes: 10 })
  assert.equal(entry.length, 1)
  assert.equal(entry[0].basename, 'test.txt')
  assert.equal(entry[0].absolutePath, fs.realpathSync.native(x.file))
  assert.throws(() => validateBrowserUploadFiles([x.other], { allowedRoots: [x.ok] }), /upload_scope_denied/)
  assert.throws(() => validateBrowserUploadFiles([x.ok], { allowedRoots: [x.dir] }), /upload_regular_file_required/)
  assert.throws(() => validateBrowserUploadFiles([x.file], { allowedRoots: [x.ok], maxBytes: 2 }), /upload_file_too_large/)
  assert.throws(() => validateBrowserUploadFiles(['test.txt'], { allowedRoots: [x.ok] }), /upload_path_invalid/)
  assert.throws(() => validateBrowserUploadFiles([], { allowedRoots: [x.ok] }), /upload_file_count_invalid/)
})

test('realpath rejects symlink or junction paths that escape grant root', () => {
  const x = setup()
  const link = path.join(x.ok, 'linked')

  try { fs.symlinkSync(x.outside, link, process.platform === 'win32' ? 'junction' : 'dir') }
  catch (e) { if ((e as NodeJS.ErrnoException).code === 'EPERM') {return;} throw e }

  assert.throws(() => validateBrowserUploadFiles([path.join(link, 'secret.txt')], { allowedRoots: [x.ok] }), /upload_scope_denied/)
})

test('input resolution only targets exactly one file input, not arbitrary elements or JS', () => {
  const expression = browserFileInputExpression('input[data-test="asset"]')
  assert.match(expression, /querySelectorAll/)
  assert.match(expression, /HTMLInputElement/)
  assert.match(expression, /type === 'file'/)
  assert.doesNotMatch(expression, /\beval\s*\(/)
})

test('upload grant must be bound to the exact current browser origin', () => {
  const x = setup()
  const grant = { allowedRoots: [x.ok], allowedOrigins: ['https://files.example.test'] }
  assert.doesNotThrow(() => validateBrowserUploadOrigin(grant, 'https://files.example.test/upload'))
  assert.throws(() => validateBrowserUploadOrigin(grant, 'https://evil.example.test/upload'), /upload_origin_denied/)
  assert.throws(() => validateBrowserUploadOrigin(grant, 'https://files.example.test.evil.test/'), /upload_origin_denied/)
  assert.throws(() => validateBrowserUploadOrigin(grant, 'file:///C:/private.txt'), /upload_origin_denied/)
  assert.throws(() => validateBrowserUploadOrigin({ allowedRoots: [x.ok] }, 'https://files.example.test'), /upload_origin_denied/)
})
