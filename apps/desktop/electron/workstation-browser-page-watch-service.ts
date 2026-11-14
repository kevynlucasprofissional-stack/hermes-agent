/** Page Watch IPC owner. One selected tab, structural metadata only, no external dispatch.
 * No Browser runtime mutations: consumes its existing public owner/WebContents API.
 */
import { spawn } from 'node:child_process'
import crypto from 'node:crypto'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import type { WebContents } from 'electron'
import YAML from 'yaml'

import {
  buildPageWatchDisconnect, buildPageWatchProbe, type PageChangedEvent,
  type PageWatchConfig, PageWatchConfigStore, PageWatchCoordinator,
  type PageWatchStatus
} from './workstation-browser-page-watch'
import { PageWatchOccurrenceLedger } from './workstation-browser-page-watch-ledger'
import { getWorkstationBrowserRuntime } from './workstation-browser-runtime'

export interface PageWatchUiState {
  config: PageWatchConfig | null
  status: PageWatchStatus | null
  gateQualified: boolean
  note: string
}

const LOCAL_ONLY = new Set(['localhost','127.0.0.1','[::1]'])

function profileHome():string {
  return path.resolve(process.env.HERMES_HOME?.trim() ||
    (process.platform === 'win32'
      ? path.join(process.env.LOCALAPPDATA || path.join(os.homedir(),'AppData','Local'),'hermes')
      : path.join(os.homedir(),'.hermes')))
}

function approvedRouteId(origin:string):string | null {
  const location=path.join(profileHome(),'config.yaml')

  if(!fs.existsSync(location)) {return null}
  const raw=YAML.parse(fs.readFileSync(location,'utf8')) as Record<string,unknown>

  if(!raw || typeof raw!=='object') {throw new Error('invalid_business_events_profile')}
  const section=raw.business_events as {routes?:unknown}|undefined
  const rows=section?.routes

  if(rows===undefined){return null}

  if(!Array.isArray(rows) || rows.length>20) {throw new Error('invalid_page_watch_routes')}

  const matching=rows.filter(r=>r && r.enabled===true && r.source==='page_watch'
    && r.origin===origin)

  if(matching.length>1) {throw new Error('ambiguous_page_watch_route')}

  if(matching.length===0) {return null}
  const r=matching[0]

  if(!/^[A-Za-z0-9_-]{1,80}$/.test(r.id) ||
      r.board_id!=='page_watch' || r.delivery!=='local' ||
      !Array.isArray(r.event_types) || r.event_types.length!==1 ||
      r.event_types[0]!=='page_changed' ||
      typeof r.job_id!=='string' || !/^[A-Za-z0-9_:.-]{1,256}$/.test(r.job_id)) {
    throw new Error('invalid_page_watch_authorized_route')
  }

  return r.id
}

function emitAuthorizedP04(event:PageChangedEvent):void {
  // Revalidate the BrowserTask/tab/lease at the irreversible dispatch boundary.
  // The periodic reconciler alone is insufficient during human takeover races.
  const expected = tabConfig(event.tab_id)
  try {
    const current = currentAuthorization(event.tab_id)
    if (!expected || expected.id !== event.watch_id
        || expected.route_id !== event.route_id
        || current.origin !== event.origin
        || current.sessionId.replace(/[^A-Za-z0-9_-]/g,'_').slice(0,80) !== event.session_id
        || safeStatus(event.tab_id)?.status !== 'watching') {
      pageWatchPause(event.tab_id,'session_ended')
      return
    }
  } catch {
    pageWatchPause(event.tab_id,'human_takeover')
    return
  }
  if(event.route_id==='local-only') {return}

  if(approvedRouteId(event.origin)!==event.route_id) {
    pageWatchPause(event.tab_id,'delivery_error')

    return
  }

  // One-shot P04 dispatcher, never a mutation-loop LLM. Local trusted profile only.
  const root=[process.cwd(),path.resolve(process.cwd(),'..','..')]
    .find(candidate=>fs.existsSync(path.join(candidate,'workstation','page_watch_event_bridge.py')))

  if(!root) {
    pageWatchPause(event.tab_id,'delivery_error')
    return
  }

  const child=spawn(process.env.HERMES_PYTHON || 'python',[
    '-m','workstation.page_watch_event_bridge',
    '--profile-home',profileHome(),'--watch-id',event.watch_id,
    '--event-id',event.event_id,'--route-id',event.route_id
  ],{
    cwd:root,windowsHide:true,stdio:'ignore',
    env:{...process.env,HERMES_KANBAN_DB:canonicalKanbanPath()}
  })

  const timeout=setTimeout(()=>{child.kill();pageWatchPause(event.tab_id,'delivery_error')},20000)
  child.on('error',()=>{clearTimeout(timeout);pageWatchPause(event.tab_id,'delivery_error')})
  child.on('exit',code=>{
    clearTimeout(timeout)

    if(code!==0){pageWatchPause(event.tab_id,'delivery_error')}
  })
}

const pollMs = 1200
const configured = new Map<string, PageWatchConfig>()

const coordinator = new PageWatchCoordinator({
  debounceMs: 300,
  onEvent: event => { recordLastEvent(event) },
  reserveEventId: req => ledger().reserve(req).event_id
})

let initialized = false
let occurrenceLedger: PageWatchOccurrenceLedger | null = null
const lastEvents = new Map<string,PageChangedEvent>()
const ownedWebContents = new Map<string,{wc:WebContents;cleanup:()=>void}>()

function canonicalKanbanPath(): string {
  const pin = process.env.HERMES_KANBAN_DB?.trim()

  if (pin) {return path.resolve(pin)}

  const root = process.env.HERMES_KANBAN_HOME?.trim() || (
    process.platform === 'win32'
      ? path.join(process.env.LOCALAPPDATA || path.join(os.homedir(),'AppData','Local'),'hermes')
      : path.join(os.homedir(),'.hermes')
  )

  // Explicit alternate Kanban board must be pinned; never silently write to default.
  if (process.env.HERMES_KANBAN_BOARD?.trim()
      && process.env.HERMES_KANBAN_BOARD !== 'default') {
    throw new Error('page_watch_named_board_requires_canonical_db_pin')
  }

  return path.resolve(root,'kanban.db')
}

function ledger():PageWatchOccurrenceLedger {
  if (!occurrenceLedger) {
    const file=canonicalKanbanPath()

    if (!fs.existsSync(file)) {throw new Error('page_watch_canonical_kanban_db_missing')}
    occurrenceLedger=new PageWatchOccurrenceLedger(file)
  }

  return occurrenceLedger
}

function store():PageWatchConfigStore {
  const profile = getWorkstationBrowserRuntime().state().profilePath

  if (!path.isAbsolute(profile) || !profile) {throw new Error('page_watch_browser_profile_unavailable')}

  return new PageWatchConfigStore(path.join(path.dirname(profile),'page-watch-config.json'))
}

function init():void {
  if (initialized) {return}
  initialized=true

  for (const config of store().load()) {
    configured.set(config.id,config)
    // restore config only; NEVER rearm an observer on process restart.
  }
}

function recordLastEvent(event:PageChangedEvent):void {
  lastEvents.set(event.watch_id,event)
  emitAuthorizedP04(event)
}

function tabConfig(tabId: string):PageWatchConfig | null {
  return [...configured.values()].find(x=>x.tab_id===tabId) ?? null
}

function currentAuthorization(tabId: string):{wc:WebContents;origin:string;sessionId:string} {
  const runtime=getWorkstationBrowserRuntime()
  const state=runtime.state()
  const tab=state.tabs.find(item=>item.id===tabId)
  const wc=runtime.getWebContents(tabId)

  if (!tab || !wc || wc.isDestroyed() || tab.crashed || state.paused
      || state.humanControlLease || state.controlOwner==='human'
      || state.activeTabId!==tabId) {
    throw new Error('page_watch_browser_authority_not_available')
  }

  const url=new URL(wc.getURL())

  if (!LOCAL_ONLY.has(url.hostname) || url.protocol!=='http:') {
    throw new Error('page_watch_fixture_origin_only')
  }

  return {wc,origin:url.origin,sessionId:tab.ownerTaskId || 'browser-local'}
}

function safeStatus(tabId:string):PageWatchStatus | null {
  const config=tabConfig(tabId)

  if (!config) {return null}
  let status:PageWatchStatus

  try {status=coordinator.status(config.id)}
  catch {return {id:config.id,status:'paused',reason:'disabled',
    lastCount:null,lastEvent:lastEvents.get(config.id) ?? null}}

  return status
}

export function pageWatchUiState(tabId: string):PageWatchUiState {
  init()
  const config=tabConfig(tabId)
  let gateQualified=false
  let note='Somente páginas locais de teste; nenhuma ação externa'

  try {
    currentAuthorization(tabId)
    // Status must remain read-only: do not migrate/create tables just to render UI.
    if (!fs.existsSync(canonicalKanbanPath())) {
      throw new Error('page_watch_canonical_kanban_db_missing')
    }
    gateQualified=true
  } catch(e) {
    note=e instanceof Error?e.message:'page_watch_unavailable'

    if (config && safeStatus(tabId)?.status==='watching') {pageWatchPause(tabId,'unavailable')}
  }

  return {config,status:safeStatus(tabId),gateQualified,note}
}

function detach(id:string):void {
  const bound=ownedWebContents.get(id)

  if (!bound) {return}
  ownedWebContents.delete(id)
  bound.cleanup()
}

export function pageWatchPause(tabId:string, reason:PageWatchStatus['reason']='disabled'):PageWatchUiState {
  const config=tabConfig(tabId)

  if(config) {
    coordinator.pause(config.id,reason || 'disabled')
    detach(config.id)
  }

  return pageWatchUiState(tabId)
}

export async function pageWatchEnable(tabId:string, selector:string):Promise<PageWatchUiState> {
  init()
  const {wc,origin,sessionId}=currentAuthorization(tabId)
  const id='watch-'+crypto.createHash('sha256').update(tabId).digest('hex').slice(0,24)

  const config:PageWatchConfig={
    id,session_id:sessionId.replace(/[^A-Za-z0-9_-]/g,'_').slice(0,80),
    tab_id:tabId, origin,selector,rule:'child_count',route_id:approvedRouteId(origin) || 'local-only',enabled:true
  }

  // Ensure backend validates selector, origin, and all identity fields.
  buildPageWatchProbe(config)
  ledger()

  if (tabConfig(tabId) && safeStatus(tabId)?.status==='watching') {
    throw new Error('page_watch_already_active')
  }

  const active=Array.from(configured.values()).filter(x=>x.tab_id!==tabId)
  store().save([...active,config])
  configured.set(config.id,config)

  const probe=()=>wc.executeJavaScriptInIsolatedWorld(998,[{code:buildPageWatchProbe(config)}]) as
    Promise<{state:'ok'|'origin_mismatch'|'auth_required'|'unsupported'|'unavailable';origin:string;count:number}>

  const stop=()=>{if(!wc.isDestroyed()) {return wc.executeJavaScriptInIsolatedWorld(
    998,[{code:buildPageWatchDisconnect(config)}]).then(()=>undefined).catch(()=>undefined)}}

  const pause=(reason:NonNullable<PageWatchStatus['reason']>)=>{
    coordinator.pause(config.id,reason)
    detach(config.id)
  }

  const onNavigation=(details:{isMainFrame?:boolean;url?:string})=>{
    if (details.isMainFrame) {
      const next=details.url

      // Changing document or navigating to auth is not safe to retain across,
      // even if same origin. Explicit user rearm required.
      if(next) {pause('session_ended')}
    }
  }

  const onGone=()=>pause('renderer_crash')
  const onDestroyed=()=>pause('tab_closed')
  wc.on('did-start-navigation',onNavigation)
  wc.on('render-process-gone',onGone)
  wc.on('destroyed',onDestroyed)
  ownedWebContents.set(id,{wc,cleanup:()=>{
    wc.removeListener('did-start-navigation',onNavigation)
    wc.removeListener('render-process-gone',onGone)
    wc.removeListener('destroyed',onDestroyed)
  }})

  try {
    await coordinator.arm(config,probe,stop)
    // Reconcile every tick with real owner, lease, tab, session, origin.
    coordinator.startPolling(config.id,pollMs)

    if (!interval) {interval=setInterval(checkActive,500); interval.unref?.()}
  } catch(e) {
    pause('unavailable')
    throw e
  }

  return pageWatchUiState(tabId)
}

let interval:ReturnType<typeof setInterval> | null=null

function checkActive():void {
  for(const config of configured.values()) {
    const status=safeStatus(config.tab_id)

    if(status?.status!=='watching') {continue}

    try {
      const auth=currentAuthorization(config.tab_id)

      if(auth.origin!==config.origin || auth.sessionId.replace(/[^A-Za-z0-9_-]/g,'_').slice(0,80)!==config.session_id) {
        pageWatchPause(config.tab_id,'session_ended')
      }
    } catch {pageWatchPause(config.tab_id,'human_takeover')}
  }
}

export function pageWatchDisconnectForTab(tabId:string):void {
  pageWatchPause(tabId,'tab_closed')
}

/** Explicit resource teardown (fixture/application shutdown). Does not erase configuration. */
export function pageWatchShutdown():void {
  for (const config of configured.values()) {
    try {coordinator.pause(config.id,'session_ended')} catch { /* fail closed */ }
    detach(config.id)
  }

  if (interval) {clearInterval(interval);interval=null}

  if (occurrenceLedger) {occurrenceLedger.close(); occurrenceLedger=null}
}
