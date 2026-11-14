/** Reference-only pure host-side validation. Not wired into Electron. */
import fs from 'node:fs';
import path from 'node:path';

/**
 * Validate named local files against explicitly granted roots.
 * Returns resolved paths for internal CDP only; NEVER serialize `absolutePath`
 * into model-facing output. TaskRun authority must be independently checked.
 */
export function validateUploadFiles(rawFiles, { allowedRoots, maxBytes = 50 * 1024 * 1024, maxFiles = 10 } = {}) {
  if (!Array.isArray(allowedRoots) || allowedRoots.length === 0) throw new Error('upload_scope_required');
  if (!Array.isArray(rawFiles) || rawFiles.length === 0 || rawFiles.length > maxFiles) throw new Error('upload_file_count_invalid');
  if (!Number.isSafeInteger(maxBytes) || maxBytes <= 0) throw new Error('upload_size_limit_invalid');
  const roots = allowedRoots.map(root => {
    if (typeof root !== 'string' || !path.isAbsolute(root)) throw new Error('upload_scope_invalid');
    return fs.realpathSync.native(root);
  });
  return rawFiles.map(raw => {
    if (typeof raw !== 'string' || !path.isAbsolute(raw) || raw.includes('\0')) throw new Error('upload_path_invalid');
    const absolutePath = fs.realpathSync.native(raw);
    const st = fs.statSync(absolutePath);
    if (!st.isFile()) throw new Error('upload_regular_file_required');
    if (st.size > maxBytes) throw new Error('upload_file_too_large');
    const inside = roots.some(root => {
      const relative = path.relative(root, absolutePath);
      return relative !== '' && relative !== '..' && !relative.startsWith('..' + path.sep) && !path.isAbsolute(relative);
    });
    if (!inside) throw new Error('upload_scope_denied');
    return { absolutePath, basename: path.basename(absolutePath), bytes: st.size };
  });
}
