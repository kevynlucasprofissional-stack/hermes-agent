import fs from 'node:fs'
import http from 'node:http'

import { app, BrowserWindow } from 'electron'

import { getWorkstationBrowserRuntime, workstationBrowserControlPath } from '../electron/workstation-browser-runtime'

async function run(): Promise<void> {
  await app.whenReady()
  const runtime = getWorkstationBrowserRuntime()
  await runtime.startControlServer()
  const hiddenOwners = new Map(['a','b'].map(id => [id, new BrowserWindow({show:false,focusable:true,skipTaskbar:true,x:-22000,y:-22000,width:1400,height:900})]))
  for (const win of hiddenOwners.values()) {
    win.showInactive()
    if (win.isFocused() || win.getBounds().x > -10000) {throw Error('OFFSCREEN_NO_FOCUS_INVARIANT_FAILED')}
  }
  const server = http.createServer((_req,res) => {
    res.writeHead(200,{'Content-Type':'text/html','Cache-Control':'no-store'})
    res.end('<!doctype html><button id="b" onclick="window.count=(window.count||0)+1">Local action</button><input id="i" aria-label="local input"/>')
  })
  await new Promise<void>(resolve => server.listen(0,'127.0.0.1',resolve))
  try {
    const address = server.address()
    if (!address || typeof address === 'string') {throw Error('LOCAL_TEST_SERVER_NOT_READY')}
    const url = 'http://127.0.0.1:' + address.port
    const control = JSON.parse(fs.readFileSync(workstationBrowserControlPath(),'utf8')) as {url:string;token:string}
    const post = async (action:string, task:string, sid:string, run:string, operation:string, args:Record<string,unknown>) => {
      const response = await fetch(control.url+'/v1/action',{method:'POST',headers:{
        authorization:'Bearer '+control.token,'content-type':'application/json'
      },body:JSON.stringify({action,task_id:task,session_id:sid,run_id:run,operation_id:operation,arguments:args})})
      const data=await response.json() as Record<string,any>
      if (!response.ok || data.success !== true) {throw Error('CONTROL_ACTION_'+action+':'+JSON.stringify({status:response.status,error_code:data.error_code,error:data.error,details:data.details}))}
      return data.result
    }
    let navigationReceiptsMatched = true
    for (const id of ['a','b']) {
      runtime.createTask({taskId:'task-native-'+id,sessionHost:'session-native-'+id,runId:'run-native-'+id})
      runtime.showTask('task-native-'+id,hiddenOwners.get(id)!,{x:0,y:0,width:1280,height:800},'hub')
      await post('browser_navigate','task-native-'+id,'session-native-'+id,'run-native-'+id,'op-nav-native-'+id,{url:url+'/'+id})
      const snap=await post('browser_snapshot','task-native-'+id,'session-native-'+id,'run-native-'+id,'op-snap-native-'+id,{view:'action_map'})
      if (typeof snap.snapshot !== 'string' || !snap.snapshot.includes('@e1') || !snap.snapshot.includes('@e2')) {
        throw Error('NATIVE_SEMANTIC_REFS_MISSING')
      }
      const task=runtime.listTasks().find(t=>t.taskId==='task-native-'+id)
      navigationReceiptsMatched &&= !!task && task.lastReceipt?.action==='browser_navigate' && task.lastReceipt.runId===task.runId
    }
    for (const win of hiddenOwners.values()) {
      win.minimize()
      if (!win.isMinimized() || win.isFocused()) {
        throw Error('P05_HUMAN_WINDOW_NOT_MINIMIZED')
      }
    }
    await new Promise(resolve=>setTimeout(resolve,350))
    const nativeOwnerMapping=(runtime as any).minimizedCompositor.hosts
    console.log('P05_AUTO_MINIMIZE_AUDIT='+JSON.stringify({
      hostCount:nativeOwnerMapping.size,
      mappings:[...nativeOwnerMapping.entries()].map(([human,state]:any)=>({
        originalMinimized:human.isMinimized(),
        hostFocused:state.host.isFocused(),
        hostMinimized:state.host.isMinimized(),
        children:state.host.contentView.children.length
      }))
    }))
    if (nativeOwnerMapping.size!==2) {throw Error('P05_AUTO_HOST_COUNT_MISMATCH')}
    // Keep Task A parked while Task B owns the visible viewport.
    await post('browser_click','task-native-a','session-native-a','run-native-a','op-click-native-a',{ref:'@e1'})
    await post('browser_type','task-native-b','session-native-b','run-native-b','op-type-native-b',{ref:'@e2',text:'native-proof'})
    const taskBeforeRecovery=runtime.listTasks().find(t=>t.taskId==='task-native-a')!
    const tabBeforeRecovery=runtime.state().tabs.find(t=>t.ownerTaskId===taskBeforeRecovery.taskId)!
    const webContentsIdBeforeRecovery=runtime.getWebContents(tabBeforeRecovery.id)!.id
    const stateBeforeRecovery=(runtime as any).sessionStatePersistence().load()
    const countBeforeRecovery=Object.keys(stateBeforeRecovery?.operationAdmissions||{}).length
    await runtime.stopControlServer()
    await runtime.startControlServer()
    const repairedDescriptor=JSON.parse(fs.readFileSync(workstationBrowserControlPath(),'utf8')) as {url:string;token:string}
    const repairedHealth=await fetch(repairedDescriptor.url+'/health',{headers:{authorization:'Bearer '+repairedDescriptor.token}})
    const repairedBody=await repairedHealth.json() as Record<string,any>
    const taskAfterRecovery=runtime.listTasks().find(t=>t.taskId==='task-native-a')!
    const tabAfterRecovery=runtime.state().tabs.find(t=>t.ownerTaskId===taskAfterRecovery.taskId)!
    const wcAfterRecovery=runtime.getWebContents(tabAfterRecovery.id)!
    const stateAfterRecovery=(runtime as any).sessionStatePersistence().load()
    const countAfterRecovery=Object.keys(stateAfterRecovery?.operationAdmissions||{}).length
    const countNativeAfterRecovery=await wcAfterRecovery.executeJavaScript('window.count||0')
    console.log('P05_CONTROLLER_RECOVERY_AUDIT='+JSON.stringify({
      authHealth:repairedHealth.ok,healthSuccess:repairedBody.success,
      sameTab:tabAfterRecovery.id===tabBeforeRecovery.id,
      sameWebContents:wcAfterRecovery.id===webContentsIdBeforeRecovery,
      admissionCountUnchanged:countBeforeRecovery===countAfterRecovery,
      nativeClickCount:countNativeAfterRecovery,
      ownerHostsUnfocused:[...hiddenOwners.values()].every(w=>!w.isFocused())
    }))
    if(!repairedHealth.ok || repairedBody.success!==true ||
       tabAfterRecovery.id!==tabBeforeRecovery.id ||
       wcAfterRecovery.id!==webContentsIdBeforeRecovery ||
       countBeforeRecovery!==countAfterRecovery || countNativeAfterRecovery!==1){
      throw Error('P05_CONTROLLER_RESTART_CHANGED_BROWSER_TASK')
    }
    const tasks=runtime.listTasks()
    const taskA=tasks.find(t=>t.taskId==='task-native-a')!
    const taskB=tasks.find(t=>t.taskId==='task-native-b')!
    const wcA=runtime.getWebContents(taskA.lastReceipt!.tabId)!
    const wcB=runtime.getWebContents(taskB.lastReceipt!.tabId)!
    const clickDiagnostics=await wcA.executeJavaScript('({count:window.count||0,hasHandler:typeof document.querySelector("#b").onclick,viewport:[innerWidth,innerHeight],rect:(()=>{const r=document.querySelector("#b").getBoundingClientRect();return [r.x,r.y,r.width,r.height]})(),hit:document.elementFromPoint(30,10)?.id,focused:document.hasFocus()})')
    console.log('NATIVE_CLICK_DIAGNOSTICS='+JSON.stringify(clickDiagnostics))
    const clickValue=await wcA.executeJavaScript('window.count || 0')
    // No retry of a click with uncertain effect, even in this synthetic harness.
    const typeValue=await wcB.executeJavaScript('document.querySelector("#i").value')
    const state=runtime.state()
    const passed=navigationReceiptsMatched && clickValue===1 && typeValue==='native-proof'
    const output={runtime:state.runtime,controlReady:state.controlReady,backgroundCapable:state.backgroundCapable,
      ownerHostsNotFocused:[...hiddenOwners.values()].every(host=>!host.isFocused()),
      taskCount:tasks.length,boundTasks:tasks.filter(t=>t.taskId.startsWith('task-native-')).length,
      navigationReceiptsMatched,nativeClickVerified:clickValue===1,nativeTypeVerified:typeValue==='native-proof',
      mutationReceipts:tasks.every(t=>t.lastReceipt?.taskId===t.taskId && t.lastReceipt?.runId===t.runId),
      ownedTabs:state.tabs.filter(t=>t.ownerTaskId?.startsWith('task-native-')).length,
      tabCount:state.tabs.length,taskStatuses:tasks.map(t=>t.status),
      receiptWebContentsAlive:tasks.map(t=>{const wc=t.lastReceipt?runtime.getWebContents(t.lastReceipt.tabId):null;return !!wc&&!wc.isDestroyed()})}
    console.log('HERMES_RUNTIME_NATIVE_E2E='+JSON.stringify(output))
    if (!passed || output.ownedTabs!==2 || !output.controlReady || !output.ownerHostsNotFocused) {throw Error('NATIVE_BROWSER_RUNTIME_E2E_FAILED')}
  } finally {
    await runtime.destroy()
    for (const window of hiddenOwners.values()) {window.destroy()}
    await new Promise<void>(resolve=>server.close(()=>resolve()))
  }
}
run().then(()=>app.quit()).catch(error=>{console.error('NATIVE_RUNTIME_ERROR='+String(error?.stack||error));app.exit(2)})
