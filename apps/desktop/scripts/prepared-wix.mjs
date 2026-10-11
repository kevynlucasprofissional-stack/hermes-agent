import path from 'node:path'
import { consumePreparedWix, preparationRequired } from './prepared-packaging.mjs'

/** @param {unknown} options */
export async function downloadBuilderToolset(options) {
  const manifest = process.env.HERMES_PREPARED_PACKAGING
  if (!manifest) throw preparationRequired('Missing prepared WiX manifest')
  return consumePreparedWix(options, manifest, path.resolve(import.meta.dirname, '../../..'), process.env.HERMES_PREPARED_TARGET)
}
