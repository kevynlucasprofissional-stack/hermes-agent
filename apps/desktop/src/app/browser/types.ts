export type WorkstationBrowserControlOwner = 'agent' | 'human'

export interface WorkstationBrowserBounds {
  x: number
  y: number
  width: number
  height: number
}

export interface WorkstationBrowserTabState {
  id: string
  title: string
  url: string
  active: boolean
  loading: boolean
  canGoBack: boolean
  canGoForward: boolean
  crashed: boolean
  ownerTaskId: string | null
}

export interface WorkstationBrowserState {
  runtime: 'electron-chromium'
  ready: boolean
  attached: boolean
  backgroundCapable: true
  paused: boolean
  controlOwner: WorkstationBrowserControlOwner
  controlReady: boolean
  profilePath: string
  cacheBytes: number | null
  activeTabId: string | null
  tabs: WorkstationBrowserTabState[]
  lastError: string | null
}

export interface WorkstationBrowserBridge {
  status: () => Promise<WorkstationBrowserState>
  ensure: () => Promise<WorkstationBrowserState>
  newTab: (target?: string) => Promise<WorkstationBrowserState>
  activateTab: (tabId: string) => Promise<WorkstationBrowserState>
  closeTab: (tabId: string) => Promise<WorkstationBrowserState>
  navigate: (target: string) => Promise<WorkstationBrowserState>
  back: () => Promise<WorkstationBrowserState>
  forward: () => Promise<WorkstationBrowserState>
  reload: () => Promise<WorkstationBrowserState>
  stop: () => Promise<WorkstationBrowserState>
  focus: () => Promise<WorkstationBrowserState>
  attach: (bounds: WorkstationBrowserBounds) => Promise<WorkstationBrowserState>
  setBounds: (bounds: WorkstationBrowserBounds) => Promise<WorkstationBrowserState>
  detach: () => Promise<WorkstationBrowserState>
  pause: () => Promise<WorkstationBrowserState>
  resume: () => Promise<WorkstationBrowserState>
  takeControl: () => Promise<WorkstationBrowserState>
  releaseControl: () => Promise<WorkstationBrowserState>
  cleanupCache: (force?: boolean) => Promise<WorkstationBrowserState>
  onState: (callback: (state: WorkstationBrowserState) => void) => () => void
}
