import crypto from 'node:crypto'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import type { WebContentsView } from 'electron'
import { expect, it, vi } from 'vitest'

import { renderCreativeFrame } from './workstation-creative-frame'

function fixture() {
  const initialBounds = { x: 90, y: 50, width: 900, height: 500 }
  const state = { bounds: { ...initialBounds }, zoom: 1.25, url: '' }
  const view = {
    getBounds: () => ({ ...state.bounds }),
    setBounds: (bounds: typeof initialBounds) => { state.bounds = { ...bounds } },
    webContents: {
      getZoomFactor: () => state.zoom,
      setZoomFactor: (zoom: number) => { state.zoom = zoom },
      loadURL: async (url: string) => { state.url = url },
      executeJavaScript: async () => ({ width: 32, height: 32 }),
      getURL: () => state.url,
      isDestroyed: () => false
    }
  } as unknown as WebContentsView
  const source = JSON.stringify({ schemaVersion: 1, width: 32, height: 32, background: '#112233', elements: [] })
  const args = { source_json: source, source_sha256: crypto.createHash('sha256').update(source).digest('hex') }
  return { initialBounds, state, view, args }
}

it('lost owner after asynchronous capture restores geometry and publishes no output', async () => {
  const { initialBounds, state, view, args } = fixture()
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-creative-owner-'))
  let owned = true
  try {
    await expect(renderCreativeFrame(view, args, directory, () => {
      if (!owned) throw new Error('owner revoked')
    }, async () => { owned = false; return Buffer.alloc(0) })).rejects.toThrow('owner revoked')
    expect(state.bounds).toEqual(initialBounds)
    expect(state.zoom).toBe(1.25)
    expect(fs.readdirSync(directory)).toEqual([])
  } finally {
    fs.rmSync(directory, { recursive: true })
  }
})

it('capture timeout restores geometry and a late completion cannot publish output', async () => {
  const { initialBounds, state, view, args } = fixture()
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-creative-timeout-'))
  vi.useFakeTimers()
  let complete!: (png: Buffer) => void
  try {
    const pending = renderCreativeFrame(view, args, directory, () => {},
      () => new Promise<Buffer>(resolve => { complete = resolve }))
    const rejected = expect(pending).rejects.toThrow('creative_capture_timeout')
    await vi.advanceTimersByTimeAsync(8000)
    await rejected
    complete(Buffer.alloc(0))
    await Promise.resolve()
    expect(state.bounds).toEqual(initialBounds)
    expect(state.zoom).toBe(1.25)
    expect(fs.readdirSync(directory)).toEqual([])
  } finally {
    vi.useRealTimers()
    fs.rmSync(directory, { recursive: true })
  }
})
