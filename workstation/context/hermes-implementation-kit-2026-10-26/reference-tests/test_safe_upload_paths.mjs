import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { validateUploadFiles } from '../reference-code/safe_upload_paths.mjs';

function fixture(t) {
  const parent = fs.mkdtempSync(path.join(os.tmpdir(), 'hw-upload-'));
  t.after(() => fs.rmSync(parent, { recursive: true, force: true }));
  fs.mkdirSync(path.join(parent, 'allow'));
  fs.mkdirSync(path.join(parent, 'other'));
  const allowed = path.join(parent, 'allow', 'sample.png');
  const outside = path.join(parent, 'other', 'forbidden.png');
  fs.writeFileSync(allowed, 'png');
  fs.writeFileSync(outside, 'outside');
  return { parent, allowed, outside, root: path.join(parent, 'allow') };
}

test('valid regular file in authorized scope', t => {
  const x = fixture(t);
  assert.equal(validateUploadFiles([x.allowed], { allowedRoots: [x.root] })[0].basename, 'sample.png');
});

test('fails closed when roots missing', t => {
  const x = fixture(t);
  assert.throws(() => validateUploadFiles([x.allowed], {}), /upload_scope_required/);
});

test('rejects path outside root and same-prefix sibling', t => {
  const x = fixture(t);
  assert.throws(() => validateUploadFiles([x.outside], { allowedRoots: [x.root] }), /upload_scope_denied/);
});

test('rejects directory, oversized, and relative paths', t => {
  const x = fixture(t);
  assert.throws(() => validateUploadFiles([x.root], { allowedRoots: [x.parent] }), /upload_regular_file_required/);
  assert.throws(() => validateUploadFiles([x.allowed], { allowedRoots: [x.root], maxBytes: 2 }), /upload_file_too_large/);
  assert.throws(() => validateUploadFiles(['sample.png'], { allowedRoots: [x.root] }), /upload_path_invalid/);
});

test('symlink escaping root is rejected', t => {
  const x = fixture(t);
  const link = path.join(x.root, 'escape.png');
  fs.symlinkSync(x.outside, link);
  assert.throws(() => validateUploadFiles([link], { allowedRoots: [x.root] }), /upload_scope_denied/);
});
