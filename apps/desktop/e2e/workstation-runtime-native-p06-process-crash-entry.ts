import fs from 'node:fs'
import http from 'node:http'
import crypto from 'node:crypto'
import {app, BrowserWindow} from 'electron'
import {getWorkstationBrowserRuntime, workstationBrowserControlPath} from '../electron/workstation-browser-runtime'

const taskId='task-p06-process'
const sessionId='session-p06-process'
const runId='run-p06-process'
const uncertainOp='op-p06-process-batch-uncertain'
const secondOp='op-p06-process-new-navigation'
async function run():Promise<void>{
 await app.whenReady()
 const runtime=getWorkstationBrowserRuntime()
 await runtime.startControlServer()
 const persistence=(runtime as any).sessionStatePersistence()
 const phase=process.env.P06_PROCESS_PHASE
 if(phase==='seed'){
   const local=http.createServer((_req,res)=>{res.writeHead(200,{'content-type':'text/html'});res.end('<!doctype html><button onclick="window.count=(window.count||0)+1">Synthetic</button>')})
   await new Promise<void>(resolve=>local.listen(0,'127.0.0.1',resolve))
   const address=local.address()!
   if(typeof address==='string'){throw Error('LOCAL_ADDRESS_UNEXPECTED')}
   const owner=new BrowserWindow({show:false,focusable:false,skipTaskbar:true,x:-22000,y:-22000,width:1400,height:900})
   owner.showInactive()
   runtime.createTask({taskId,sessionHost:sessionId,runId})
   runtime.showTask(taskId,owner,{x:0,y:0,width:1280,height:800},'hub')
   const descriptor=JSON.parse(fs.readFileSync(workstationBrowserControlPath(),'utf8'))
   const res=await fetch(descriptor.url+'/v1/action',{method:'POST',headers:{
     authorization:'Bearer '+descriptor.token,'content-type':'application/json'
   },body:JSON.stringify({action:'browser_navigate',task_id:taskId,session_id:sessionId,run_id:runId,
     operation_id:'op-p06-process-navigation-ack',arguments:{url:'http://127.0.0.1:'+address.port+'/synthetic'}})})
   const nav=await res.json()
   if(!res.ok || !nav.success){throw Error('P06_NAV_SEED_FAILED:'+JSON.stringify(nav))}
   const tab=runtime.state().tabs.find(t=>t.ownerTaskId===taskId)
   if(!tab){throw Error('P06_NO_TAB')}
   const admission=persistence.admitBrowserMutation({operationId:uncertainOp,action:'browser_batch_actions',
      argumentsDigest:crypto.createHash('sha256').update('p06-synthetic-batch').digest('hex'),taskId,sessionId,runId,tabId:tab.id})
   const saved=persistence.load()
   console.log('P06_PROCESS_SEED='+JSON.stringify({pid:process.pid,admission,
     pending:!!saved?.operationAdmissions?.[uncertainOp],tabId:tab.id,
     lastReceipt:runtime.listTasks().find(t=>t.taskId===taskId)?.lastReceipt?.action,
     hostFocused:owner.isFocused()}))
   if(admission!=='admitted'||!saved?.operationAdmissions?.[uncertainOp]){throw Error('P06_SEED_NOT_PERSISTED')}
   // Deliberately bypass app shutdown/destroy and teardown hooks (test process only).
   process.exit(73)
   return
 }
 if(phase!=='recover'){throw Error('P06_PHASE_REQUIRED')}
 const snapshot=persistence.load()
 const pendingBefore=snapshot?.operationAdmissions?.[uncertainOp]
 const originalTask=runtime.listTasks().find(t=>t.taskId===taskId)
 const command=(runtime as any).executeControlRequest.bind(runtime)
 const readback=await command({action:'browser_snapshot',task_id:taskId,session_id:sessionId,
     run_id:runId,operation_id:'op-p06-process-snapshot',arguments:{view:'action_map'}})
 const afterSnap=runtime.state().tabs.find(t=>t.ownerTaskId===taskId)
 const wc=afterSnap?runtime.getWebContents(afterSnap.id):null
 const currentURL=wc?.getURL()||null
 const blocked=await command({action:'browser_navigate',task_id:taskId,session_id:sessionId,
    run_id:runId,operation_id:secondOp,arguments:{url:'http://127.0.0.1:9/should-not-load'}})
 const reloaded=persistence.load()
 const pendingAfter=reloaded?.operationAdmissions?.[uncertainOp]
 const newAdmission=!!reloaded?.operationAdmissions?.[secondOp]
 const output={pid:process.pid,pendingBefore:!!pendingBefore,pendingAfter:!!pendingAfter,
    originalTask:!!originalTask,readbackAvailable:typeof readback?.snapshot==='string',
    currentURL,blockedStatus:blocked?.status,blockedReason:blocked?.reason,
    newAdmission,priorAcknowledged:pendingAfter?.acknowledged===true,priorTerminal:!!pendingAfter?.terminal,
    sameTabId:afterSnap?.id===pendingBefore?.tabId}
 console.log('P06_PROCESS_RESTART_AUDIT='+JSON.stringify(output))
 if(!pendingBefore||!pendingAfter||!originalTask||!output.readbackAvailable||
   output.currentURL!=='about:blank'||blocked.status!=='reconciliation_required'||
   blocked.reason!=='prior_operation_requires_reconciliation'||newAdmission||
   output.priorAcknowledged||output.priorTerminal||!output.sameTabId){
   throw Error('P06_PROCESS_CRASH_FENCE_FAILED')
 }
 await runtime.destroy()
}
run().then(()=>app.quit()).catch(e=>{console.error('P06_PROCESS_ERROR='+String(e?.stack||e));app.exit(2)})