import { beforeEach, expect, it, vi } from 'vitest'

const TABS_KEY = 'hermes.desktop.previewTabs.v2'

beforeEach(() => {
  window.localStorage.clear()
  vi.resetModules()
})

it('hydrates persisted default-scope tabs on a cold renderer import', async () => {
  window.localStorage.setItem(
    TABS_KEY,
    JSON.stringify({
      default: [
        {
          id: 'url:workstation-browser',
          target: {
            kind: 'url',
            label: 'Workstation Browser',
            source: 'workstation-browser',
            url: 'workstation:browser'
          }
        }
      ]
    })
  )

  const { $previewTabs, setPreviewScope } = await import('./preview')

  // This is the startup sequence that previously returned early and left the
  // atom empty even though the bucket had already been read from localStorage.
  setPreviewScope('default')

  expect($previewTabs.get().map(tab => tab.target.source)).toEqual(['workstation-browser'])
})
