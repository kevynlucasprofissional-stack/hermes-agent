import { BrowserWindow, type WebContentsView } from 'electron'

interface HostedView {
  view: WebContentsView
  bounds: Electron.Rectangle
}

interface HostState {
  host: BrowserWindow
  views: HostedView[]
}

interface WindowHooks {
  onMinimize: () => void
  onRestore: () => void
  onResize: () => void
  onClosed: () => void
}

/**
 * Presentation is disposable; the WebContents and BrowserTask are not.
 * Keep the same native WebContentsView composited by a non-focusable,
 * non-minimized host while the human-facing BrowserWindow is minimized.
 * No page reload, TaskRun mutation, input dispatch or Windows focus action.
 */
export class MinimizedBrowserCompositor {
  private readonly windows = new Map<BrowserWindow, WindowHooks>()
  private readonly hosts = new Map<BrowserWindow, HostState>()
  private readonly lastBounds = new WeakMap<WebContentsView, Electron.Rectangle>()
  private readonly humanForView = new WeakMap<WebContentsView, BrowserWindow>()
  private readonly detachedHosts = new Set<BrowserWindow>()
  private readonly detachedForView = new WeakMap<WebContentsView, BrowserWindow>()

  constructor(
    private readonly views: () => WebContentsView[],
    private readonly onOwnerChange: (from: BrowserWindow, to: BrowserWindow | null) => void,
    private readonly onFailure: (error: unknown) => void,
    private readonly isParked: (view: WebContentsView) => boolean = () => false
  ) {}

  register(human: BrowserWindow): void {
    if (this.windows.has(human)) {return}
    const hooks: WindowHooks = {
      onMinimize: () => this.ensureMinimized(human),
      onRestore: () => this.restore(human),
      onResize: () => this.alignParked(human),
      onClosed: () => this.close(human)
    }
    human.on('minimize', hooks.onMinimize)
    human.on('restore', hooks.onRestore)
    human.on('resize', hooks.onResize)
    human.on('closed', hooks.onClosed)
    this.windows.set(human, hooks)
  }

  effectiveWindow(human: BrowserWindow): BrowserWindow {
    return this.hosts.get(human)?.host ?? human
  }

  humanWindow(candidate: BrowserWindow): BrowserWindow {
    for (const [human, state] of this.hosts) {
      if (candidate === state.host) {return human}
    }
    return candidate
  }

  rememberView(human: BrowserWindow, view: WebContentsView, bounds: Electron.Rectangle): void {
    const previousDetached = this.detachedForView.get(view)
    this.detachedForView.delete(view)
    this.humanForView.set(view, human)
    if (previousDetached && !previousDetached.isDestroyed() &&
        !previousDetached.contentView.children.some(child => child === view)) {
      this.reapDetachedHost(previousDetached)
    }
    this.lastBounds.set(view, {...bounds})
    const state = this.hosts.get(human)
    if (!state) {return}
    const prior = state.views.find(item => item.view === view)
    if (prior) {prior.bounds = bounds}
    else {state.views.push({view, bounds})}
  }

  owningHostFor(view: WebContentsView, fallback: BrowserWindow | null): BrowserWindow | null {
    const detached = this.detachedForView.get(view)
    if (detached && !detached.isDestroyed()) {return detached}
    const human = this.humanForView.get(view)
    return human && !human.isDestroyed() ? this.effectiveWindow(human) : fallback
  }

  ensureMinimized(human: BrowserWindow, requested?: Electron.Rectangle, recovered: HostedView[] = []): void {
    if (human.isDestroyed() || !human.isMinimized() || this.hosts.has(human)) {return}
    const children = human.contentView.children
    const moving = this.views()
      .filter(view => children.includes(view))
      .map(view => ({view, bounds:this.lastBounds.get(view) ?? view.getBounds()}))
    for (const item of recovered) {
      if (!item.view.webContents.isDestroyed() && !moving.some(existing => existing.view === item.view)) {
        moving.push(item)
      }
    }
    if (!moving.length && !requested) {return}
    // Preserve the exact renderer viewport dimensions; never fake an input
    // coordinate or reduce the hit-test safety checks to make a test pass.
    const width = Math.max(1400, ...(requested ? [requested.x + requested.width + 80] : []),
      ...moving.map(item => item.bounds.x + item.bounds.width + 2))
    const height = Math.max(900, ...(requested ? [requested.y + requested.height + 100] : []),
      ...moving.map(item => item.bounds.y + item.bounds.height + 2))
    if (width > 8192 || height > 8192) {
      this.onFailure(new Error('minimized_composition_dimensions_unsupported'))
      return
    }
    let host: BrowserWindow | null = null
    const moved: HostedView[] = []
    try {
      host = new BrowserWindow({
        show:false, focusable:false, skipTaskbar:true,
        x:-22000, y:-22000, width, height,
        webPreferences:{backgroundThrottling:false}
      })
      host.showInactive()
      if (host.isFocused() || host.isMinimized() || host.isDestroyed()) {
        throw new Error('minimized_composition_host_not_ready')
      }
      for (const item of moving) {
        if (human.contentView.children.includes(item.view)) {
          human.contentView.removeChildView(item.view)
        }
        host.contentView.addChildView(item.view)
        item.view.setBounds({
          x:item.bounds.x, y:item.bounds.y,
          width:item.bounds.width, height:item.bounds.height
        })
        moved.push(item)
      }
      this.hosts.set(human, {host, views:moving})
      this.onOwnerChange(human, host)
      host.on('closed', () => this.recoverLostHost(human, host!, moving))
    } catch (error) {
      for (const item of moved) {
        try {
          host?.contentView.removeChildView(item.view)
          if (!human.isDestroyed()) {
            human.contentView.addChildView(item.view)
            item.view.setBounds(item.bounds)
          }
        } catch { /* preserve the original error: do not infer success */ }
      }
      if (host && !host.isDestroyed()) {host.destroy()}
      this.onFailure(error)
    }
  }

  private recoverLostHost(human: BrowserWindow, lostHost: BrowserWindow, retained: HostedView[]): void {
    if (this.hosts.get(human)?.host !== lostHost) {return}
    this.hosts.delete(human)
    if (human.isDestroyed()) {
      this.onOwnerChange(lostHost, null)
      this.onFailure(new Error('minimized_compositor_human_window_closed'))
      return
    }
    // A native host may be destroyed while a task input is in flight.
    // Reparent the *existing* renderer; never replay a dispatched input.
    const live = retained.filter(item => !item.view.webContents.isDestroyed())
    if (human.isMinimized() && live.length) {
      this.ensureMinimized(human, live[0].bounds, live)
      const replacement = this.hosts.get(human)?.host ?? null
      this.onOwnerChange(lostHost, replacement)
      if (!replacement) {this.onFailure(new Error('minimized_compositor_recovery_failed'))}
      return
    }
    this.onOwnerChange(lostHost, null)
    if (live.length) {this.onFailure(new Error('minimized_compositor_no_safe_replacement'))}
  }

  private alignParked(human: BrowserWindow): void {
    if (human.isDestroyed() || human.isMinimized() || this.hosts.has(human)) {return}
    const content = human.getContentBounds()
    if (content.width < 2 || content.height < 2) {return}
    for (const view of this.views()) {
      if (this.humanForView.get(view) !== human || !this.isParked(view) ||
          !human.contentView.children.includes(view)) {continue}
      const bounds = view.getBounds()
      view.setBounds({
        x:Math.max(0,content.width-1), y:Math.max(0,content.height-1),
        width:bounds.width, height:bounds.height
      })
    }
  }

  restore(human: BrowserWindow): void {
    const state = this.hosts.get(human)
    if (!state) {return}
    if (human.isDestroyed() || human.isMinimized()) {return}
    try {
      const children = state.host.isDestroyed() ? [] : state.host.contentView.children
      const tracked = this.views()
      for (const view of children) {
        const owned = tracked.find(candidate => candidate === view)
        if (!owned || state.views.some(item => item.view === owned)) {continue}
        state.views.push({view:owned, bounds:owned.getBounds()})
      }
      for (const item of state.views) {
        if (!children.includes(item.view)) {continue}
        state.host.contentView.removeChildView(item.view)
        human.contentView.addChildView(item.view)
        if (this.isParked(item.view)) {
          const content = human.getContentBounds()
          item.view.setBounds({
            x:Math.max(0,content.width-1), y:Math.max(0,content.height-1),
            width:item.bounds.width, height:item.bounds.height
          })
        } else {
          item.view.setBounds(item.bounds)
        }
      }
      this.onOwnerChange(state.host, human)
      this.hosts.delete(human)
      if (!state.host.isDestroyed()) {state.host.destroy()}
      // Restore and resize events can observe different intermediate content
      // dimensions; re-park after layout settles without touching OS focus.
      setImmediate(() => this.alignParked(human))
    } catch (error) {
      this.onFailure(error)
      // Do not destroy a host still owning a live WebContentsView.
    }
  }

  private reapDetachedHost(host: BrowserWindow): void {
    if (!this.detachedHosts.has(host) || host.isDestroyed()) {return}
    if (host.contentView.children.some(view => this.views().includes(view as WebContentsView))) {return}
    this.detachedHosts.delete(host)
    this.onOwnerChange(host, null)
    host.destroy()
  }

  private close(human: BrowserWindow): void {
    const state = this.hosts.get(human)
    if (state) {
      this.hosts.delete(human)
      const otherHuman = [...this.windows.keys()].some(win => win !== human && !win.isDestroyed())
      const live = state.views.filter(item => !item.view.webContents.isDestroyed() &&
        !state.host.isDestroyed() && state.host.contentView.children.includes(item.view))
      if (otherHuman && live.length) {
        this.detachedHosts.add(state.host)
        for (const item of live) {this.detachedForView.set(item.view, state.host)}
      } else {
        this.onOwnerChange(state.host, null)
        if (!state.host.isDestroyed()) {state.host.destroy()}
      }
    }
    const hooks = this.windows.get(human)
    if (hooks) {
      human.off('minimize', hooks.onMinimize)
      human.off('restore', hooks.onRestore)
      human.off('resize', hooks.onResize)
      human.off('closed', hooks.onClosed)
      this.windows.delete(human)
    }
  }

  dispose(): void {
    for (const human of [...this.windows.keys()]) {this.close(human)}
    for (const host of this.detachedHosts) {
      this.onOwnerChange(host, null)
      if (!host.isDestroyed()) {host.destroy()}
    }
    this.detachedHosts.clear()
  }
}
