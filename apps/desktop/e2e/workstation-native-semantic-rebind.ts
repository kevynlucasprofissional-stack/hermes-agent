/** Isolated Electron + Hermes Browser runtime E2E: no production profile, no external effects. */
import fs from 'node:fs'
import http from 'node:http'
import path from 'node:path'
import { app, BrowserWindow } from 'electron'
import { getWorkstationBrowserRuntime, workstationBrowserControlPath } from '../electron/workstation-browser-runtime'

const tempUserData = process.env.HERMES_NATIVE_REBIND_USER_DATA
if (!tempUserData || !tempUserData.includes('hermes-native-semantic-')) {
  throw new Error('ISOLATED_ELECTRON_USER_DATA_REQUIRED')
}
app.setPath('userData', tempUserData)

type Case = 'unique' | 'ambiguous'
type Json = Record<string, any>

const html = (scenario: Case): string => `<!doctype html>
<html><head><meta charset="utf-8"><title>Hermes local selection</title></head><body>
<div id="conversation" data-testid="conversation-42" role="option"
 aria-label="Conversation 42" aria-selected="false" tabindex="0"
 style="display:block; width:350px; height:90px; border:1px solid black; margin:20px">
 Conversation 42
</div>
<script>
  window.clickCount=0;
  document.getElementById('conversation').addEventListener('click',function(){
    window.clickCount++;
    const node=document.createElement('div');
    node.setAttribute('data-testid','conversation-42');
    node.setAttribute('aria-label','Conversation 42');
    node.setAttribute('aria-selected','true');
    node.setAttribute('role','option');
    node.setAttribute('tabindex','0');
    node.style.cssText='display:block;width:350px;height:90px;border:1px solid black;margin:20px';
    node.textContent='Conversation 42';
    this.replaceWith(node);
    if (${JSON.stringify(scenario)} === 'ambiguous') {
      const clone=node.cloneNode(true);
      node.after(clone);
    }
  });
</script></body></html>`

async function main(): Promise<void> {
  await app.whenReady()
  const runtime = getWorkstationBrowserRuntime()
  const windows: BrowserWindow[] = []
  const site = http.createServer((request, response) => {
    response.writeHead(200, { 'Content-Type':'text/html; charset=utf-8', 'Cache-Control':'no-store' })
    response.end(html(request.url?.startsWith('/ambiguous') ? 'ambiguous' : 'unique'))
  })
  await new Promise<void>(resolve => site.listen(0,'127.0.0.1',resolve))
  try {
    await runtime.startControlServer()
    const address=site.address()
    if (!address || typeof address === 'string') throw Error('LOCAL_SERVER_NOT_READY')
    const base='http://127.0.0.1:'+address.port
    const control=JSON.parse(fs.readFileSync(workstationBrowserControlPath(),'utf8')) as {url:string;token:string}
    const request = async (action:string, ids:{task_id:string;session_id:string;run_id:string}, op:string, args:Json):Promise<Json> => {
      const reply=await fetch(control.url+'/v1/action',{method:'POST',headers:{
        authorization:'Bearer '+control.token,'content-type':'application/json'
      },body:JSON.stringify({...ids,action,operation_id:op,arguments:args})})
      const payload=await reply.json() as Json
      return {httpStatus:reply.status,...payload}
    }
    const invoke = async (action:string, ids:{task_id:string;session_id:string;run_id:string}, op:string, args:Json) => {
      const payload=await request(action,ids,op,args)
      if (payload.httpStatus >= 400 || payload.success !== true) {
        throw Error('ACTION_FAILED:'+action+':'+JSON.stringify({status:payload.httpStatus,error:payload.error,error_code:payload.error_code,reason:payload.result?.reason}))
      }
      return payload.result as Json
    }
    const output:Json={}
    for(const scenario of ['unique','ambiguous'] as const){
      const ids={task_id:'native-rebind-'+scenario,session_id:'session-rebind-'+scenario,run_id:'run-rebind-'+scenario}
      const window=new BrowserWindow({show:false,focusable:true,skipTaskbar:true,x:-22000,y:-22000,width:1280,height:850})
      windows.push(window)
      window.showInactive()
      if(window.isFocused() || window.getBounds().x > -10000) throw Error('HOST_NOT_ISOLATED')
      runtime.createTask({taskId:ids.task_id,sessionHost:ids.session_id,runId:ids.run_id})
      runtime.showTask(ids.task_id,window,{x:0,y:0,width:1100,height:750},'hub')
      await invoke('browser_navigate',ids,'nav-rebind-'+scenario,{url:base+'/'+scenario})
      const snap=await invoke('browser_snapshot',ids,'snap-rebind-'+scenario,{view:'action_map'})
      if(typeof snap.snapshot!=='string') throw Error('MISSING_NATIVE_ACTION_MAP_'+scenario)
      const match=snap.snapshot.match(/@e\d+/)
      if(!match) throw Error('NO_NATIVE_ELEMENT_REF_'+scenario+':'+snap.snapshot.slice(0,300))
      const step={kind:'click',ref:match[0],anchor:{type:'testid',value:'conversation-42'},postcondition:{kind:'selected'}}
      const batch=await invoke('browser_batch_actions',ids,'batch-rebind-'+scenario,{steps:[step]})
      const task=runtime.listTasks().find(row=>row.taskId===ids.task_id)
      const tab=runtime.state().tabs.find(row=>row.ownerTaskId===ids.task_id)
      const wc=tab && runtime.getWebContents(tab.id)
      if(!wc || wc.isDestroyed()) throw Error('NATIVE_TAB_NOT_AVAILABLE_'+scenario)
      const dom=await wc.executeJavaScript('({clicks:window.clickCount||0,matches:document.querySelectorAll(\'[data-testid="conversation-42"]\').length,selected:Array.from(document.querySelectorAll(\'[data-testid="conversation-42"]\')).map(el=>el.getAttribute("aria-selected"))})',true) as Json
      const filePath=process.env.HERMES_WORKSTATION_BROWSER_SESSION_STATE_FILE!
      const saved=JSON.parse(fs.readFileSync(filePath,'utf8')) as Json
      const admission=saved.operationAdmissions?.['batch-rebind-'+scenario]
      const receipt=saved.receipts?.[ids.task_id]
      output[scenario]={status:batch.status,reason:batch.batch_result?.reason ?? batch.reason,verifiedSteps:batch.verified_steps,
        completedSteps:batch.completed_steps,clickCount:dom.clicks,domCandidates:dom.matches,selected:dom.selected,
        acknowledged:admission?.acknowledged === true,parentReceipt:receipt?.operationId === 'batch-rebind-'+scenario &&
        receipt?.action === 'browser_batch_actions', uncertaintyReason:admission?.uncertainty?.reason,
        ownerRunMatches:task?.runId===ids.run_id,ownerTaskMatches:receipt?.taskId===ids.task_id,
        hostFocus:window.isFocused()}
      if(scenario==='unique'){
        if(batch.status!=='verified' || batch.verified_steps!==1 || dom.clicks!==1 ||
          dom.matches!==1 || !output.unique.acknowledged || !output.unique.parentReceipt ||
          !output.unique.ownerRunMatches || !output.unique.ownerTaskMatches) {
          throw Error('UNIQUE_REBIND_FAILED:'+JSON.stringify(output.unique))
        }
        // Confirm same owner can execute a distinct mutation once parent ACK was durably stored.
        const next=await invoke('browser_navigate',ids,'next-rebind-unique',{url:base+'/next'})
        output.unique.nextNavigationAllowed=Boolean(next)
        if(!output.unique.nextNavigationAllowed) throw Error('NEXT_NAVIGATION_NOT_ALLOWED')
      }else{
        if(batch.status!=='uncertain' || dom.clicks!==1 || dom.matches!==2 ||
          output.ambiguous.acknowledged || output.ambiguous.parentReceipt ||
          output.ambiguous.uncertaintyReason!=='stale_or_replaced_target') {
          throw Error('AMBIGUOUS_REBIND_FALSE_ACK:'+JSON.stringify(output.ambiguous))
        }
        const blocked=await request('browser_navigate',ids,'next-rebind-ambiguous',{url:base+'/blocked'})
        output.ambiguous.nextNavigationDenied=blocked.httpStatus>=400 ||
          blocked.result?.status==='reconciliation_required' ||
          blocked.result?.reason==='prior_operation_requires_reconciliation'
        if(!output.ambiguous.nextNavigationDenied) {
          throw Error('AMBIGUOUS_FENCE_NOT_ENFORCED:'+JSON.stringify(blocked).slice(0,500))
        }
      }
    }
    console.log('NATIVE_SEMANTIC_REBIND_E2E='+JSON.stringify(output))
  }finally{
    await runtime.destroy()
    for(const window of windows){if(!window.isDestroyed())window.destroy()}
    await new Promise<void>(resolve=>site.close(()=>resolve()))
  }
}
main().then(()=>app.quit()).catch(error=>{console.error('NATIVE_SEMANTIC_REBIND_ERROR='+String(error?.stack||error));app.exit(2)})
