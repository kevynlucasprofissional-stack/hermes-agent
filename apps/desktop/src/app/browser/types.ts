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

export type BrowserTaskStatus = 'visible' | 'hidden' | 'parked'
export type BrowserTaskRecoveryState = 'fresh' | 'restored' | 'recreated' | null

export interface BrowserTask {
  taskId: string
  createdAt: string
  updatedAt: string
  panelHost: string | null
  controlHost: string | null
  sessionHost: string | null
  kanbanCardId: string | null
  runId: string | null
  localConnection: string | null
  status: BrowserTaskStatus
  leaseState: string | null
  parked: boolean
  recoveryState: BrowserTaskRecoveryState
}

export interface WorkstationDownloadItem {
  id: string
  filename: string
  savePath: string
  totalBytes: number
  receivedBytes: number
  state: 'progressing' | 'completed' | 'cancelled' | 'interrupted'
  url: string
}

export interface WorkstationBrowserState {
  runtime: 'electron-chromium'
  ready: boolean
  attached: boolean
  viewportHost: 'hub' | 'chat' | string | null
  backgroundCapable: true
  paused: boolean
  controlOwner: WorkstationBrowserControlOwner
  controlReady: boolean
  profilePath: string
  cacheBytes: number | null
  activeTabId: string | null
  tabs: WorkstationBrowserTabState[]
  tasks: BrowserTask[]
  downloads: WorkstationDownloadItem[]
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
  attach: (bounds: WorkstationBrowserBounds, host?: string) => Promise<WorkstationBrowserState>
  setBounds: (bounds: WorkstationBrowserBounds) => Promise<WorkstationBrowserState>
  detach: () => Promise<WorkstationBrowserState>
  transferViewport: (targetHost: string, bounds: WorkstationBrowserBounds) => Promise<WorkstationBrowserState>
  listTasks: () => Promise<BrowserTask[]>
  showTask: (taskId: string, bounds: WorkstationBrowserBounds, host?: string) => Promise<BrowserTask>
  hideTask: (taskId: string) => Promise<BrowserTask>
  parkTask: (taskId: string) => Promise<BrowserTask>
  pause: () => Promise<WorkstationBrowserState>
  resume: () => Promise<WorkstationBrowserState>
  takeControl: () => Promise<WorkstationBrowserState>
  releaseControl: () => Promise<WorkstationBrowserState>
  cleanupCache: (force?: boolean) => Promise<WorkstationBrowserState>
  onState: (callback: (state: WorkstationBrowserState) => void) => () => void
}
