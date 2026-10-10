import type { BrowserWindow, WebContentsView } from 'electron'
import { expect, it } from 'vitest'

import { withCreativeCaptureLayout } from './workstation-creative-frame'

function fixture() {
  const createView = (x: number): WebContentsView => {
    let bounds = { x, y: 20, width: 200, height: 300 }
    return {
      getBounds: () => ({ ...bounds }),
      setBounds: (value: typeof bounds) => { bounds = { ...value } },
      webContents: { isDestroyed: () => false }
    } as unknown as WebContentsView
  }
  const first = createView(100), second = createView(200)
  const main = createView(0)
  const children = [main, first, second]
  const originalOrder = [...children]
  const host = {
    isDestroyed: () => false,
    contentView: {
      children,
      addChildView: (view: WebContentsView, index: number) => {
        const previous = children.indexOf(view)
        if (previous >= 0) children.splice(previous, 1)
        children.splice(index, 0, view)
      }
    }
  } as unknown as BrowserWindow
  return { first, second, host, children, originalOrder }
}

it('overlapping captures in one native host refuse before the second render and restore ordering', async () => {
  const { first, second, host, children, originalOrder } = fixture()
  const bounds = first.getBounds()
  let finish!: (value: string) => void
  let secondRenders = 0
  const pending = withCreativeCaptureLayout(first, host, () => {},
    () => new Promise<string>(resolve => { finish = resolve }))
  await expect(withCreativeCaptureLayout(second, host, () => {}, async () => {
    secondRenders++
  })).rejects.toThrow('creative_capture_host_busy')
  expect(secondRenders).toBe(0)
  finish('captured')
  await expect(pending).resolves.toBe('captured')
  expect(first.getBounds()).toEqual(bounds)
  expect(children).toEqual(originalOrder)
  await expect(withCreativeCaptureLayout(second, host, () => {}, async () => 'next')).resolves.toBe('next')
  expect(children).toEqual(originalOrder)
})

it('a reparented view is refused and never pulled back into the previous host', async () => {
  const { first, second, host, children } = fixture()
  await expect(withCreativeCaptureLayout(first, host, () => {}, async () => {
    children.splice(children.indexOf(first), 1)
    return 'not a completed capture'
  })).rejects.toThrow('creative_capture_host_changed')
  expect(children).not.toContain(first)
  await expect(withCreativeCaptureLayout(second, host, () => {}, async () => 'next')).resolves.toBe('next')
  expect(children).not.toContain(first)
})
