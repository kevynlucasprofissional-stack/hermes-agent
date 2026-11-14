import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { validateUploadFiles } from '../reference-code/safe_upload_paths.mjs';

test('Windows: directory junction cannot escape explicitly granted upload root', t => {
  if (process.platform !== 'win32') return t.skip('Windows junction regression');
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-junction-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const allow = path.join(root, 'allowed');
  const outside = path.join(root, 'outside');
  fs.mkdirSync(allow);
  fs.mkdirSync(outside);
  fs.writeFileSync(path.join(outside, 'private.txt'), 'no-escape');
  const junction = path.join(allow, 'linked');
  try {
    fs.symlinkSync(outside, junction, 'junction');
  } catch (error) {
    if (error?.code === 'EPERM') return t.skip('Windows policy prohibits junction creation');
    throw error;
  }
  assert.throws(
    () => validateUploadFiles([path.join(junction, 'private.txt')], { allowedRoots: [allow] }),
    /upload_scope_denied/
  );
});
