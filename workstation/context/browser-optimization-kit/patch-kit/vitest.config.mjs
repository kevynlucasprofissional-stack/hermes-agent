import path from 'node:path'
import { fileURLToPath } from 'node:url'

const packageRoot = process.env.VITEST_PACKAGE_ROOT
if (!packageRoot) {
  throw new Error('Set VITEST_PACKAGE_ROOT to the existing Vitest package directory.')
}

export default {
  root: path.dirname(fileURLToPath(import.meta.url)),
  resolve: {
    alias: {
      vitest: path.join(packageRoot, 'dist', 'index.js')
    }
  },
  test: {
    include: ['*.test.ts'],
    environment: 'node',
    pool: 'threads',
    maxWorkers: 1
  }
}
