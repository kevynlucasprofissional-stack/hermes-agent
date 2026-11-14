import { beforeEach, describe, expect, it, vi } from 'vitest'

import { bindApi, configureVaultRoot, fetchVaultStatus, saveVaultNote, searchVault, updateVaultNoteSource } from './api'

describe('Vault plugin API', () => {
  const rest = vi.fn()

  beforeEach(() => {
    rest.mockReset()
    bindApi({ rest })
  })

  it('reads status through the plugin RPC boundary', async () => {
    rest.mockResolvedValue({ status: 'ok', root: 'C:\\Knowledge', notes_count: 3 })
    await expect(fetchVaultStatus()).resolves.toEqual({
      status: 'ok',
      root: 'C:\\Knowledge',
      notes_count: 3
    })
    expect(rest).toHaveBeenCalledWith('/status', undefined)
  })

  it('uses the canonical full-text search endpoint', async () => {
    rest.mockResolvedValue({ results: [{ rel_path: 'Projects/N.md' }], count: 1 })
    await searchVault('linked notes')
    expect(rest).toHaveBeenCalledWith('/search?q=linked%20notes', undefined)
  })

  it('updates an existing file with its revision, not a new root-level note', async () => {
    rest.mockResolvedValue({ status: 'ok' })
    await updateVaultNoteSource('Projects/N.md', '# Changed', 'a'.repeat(64))
    expect(rest).toHaveBeenCalledWith('/notes/Projects%2FN.md', {
      method: 'PUT',
      body: { content: '# Changed', expected_revision: 'a'.repeat(64) }
    })
  })

  it('marks new-note writes as create-only to protect existing files', async () => {
    rest.mockResolvedValue({ status: 'ok' })
    await saveVaultNote({ title: 'New', content: '# New', create_only: true })
    expect(rest).toHaveBeenCalledWith('/notes', {
      method: 'POST',
      body: { title: 'New', content: '# New', create_only: true }
    })
  })
  it('persists custom roots through the backend owner', async () => {
    rest.mockResolvedValue({ status: 'ok', root: 'D:\\Obsidian', notes_count: 42 })
    await configureVaultRoot('D:\\Obsidian')
    expect(rest).toHaveBeenCalledWith('/root', {
      method: 'PUT',
      body: { root: 'D:\\Obsidian' }
    })
  })
})
