const {app,BrowserWindow}=require('electron')
const esbuild=require('esbuild')
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),http=require('node:http')
const {DatabaseSync}=require('node:sqlite')

async function main(){
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'p06-native-service-'))
 const dbFile=path.join(tmp,'kanban.db')
 const seed=new DatabaseSync(dbFile)
 // Keep the temporary DB empty so Hermes creates its real canonical Kanban schema.
 // A fake tasks(id) schema causes a false migration failure before P04 admission.
 seed.close()
 process.env.HERMES_KANBAN_DB=dbFile
 const server=http.createServer((req,res)=>{
   res.setHeader('content-type','text/html')
   res.end('<!doctype html><html><body><ul id="items"><li>one</li><li>two</li></ul><span id="clock">10:00</span></body></html>')
 })
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve))
 const url='http://127.0.0.1:'+server.address().port
 const authorized=process.env.P06_FIXTURE_AUTHORIZED==='1'
 if(authorized){
   process.env.HERMES_HOME=tmp
   fs.writeFileSync(path.join(tmp,'config.yaml'),
     'business_events:\n  routes:\n    - id: fixture-route\n      enabled: true\n'+
     '      source: page_watch\n      board_id: page_watch\n'+
     '      event_types: [page_changed]\n      job_id: unavailable-fixture-job\n'+
     '      delivery: local\n      origin: '+url+'\n')
 }
 const browser=new BrowserWindow({show:false,webPreferences:{nodeIntegration:false,contextIsolation:true}})
 const wc=browser.webContents
 const state={activeTabId:'tab1',paused:false,controlOwner:'agent',humanControlLease:null,
   profilePath:path.join(tmp,'Browser','User Data'),tabs:[{id:'tab1',crashed:false,ownerTaskId:null}]}
 globalThis.__p06FixtureRuntime={state:()=>state,getWebContents:id=>id==='tab1'?wc:null}
 const script=await esbuild.build({
   entryPoints:[path.resolve(__dirname,'..','workstation-browser-page-watch-service.ts')],
   bundle:true,write:false,platform:'node',format:'cjs',target:'node22',
   plugins:[{name:'fixture-runtime-only',setup(build){
     build.onResolve({filter:/workstation-browser-runtime$/},()=>({path:'fake-runtime',namespace:'p06runtime'}))
     build.onLoad({filter:/.*/,namespace:'p06runtime'},()=>({
       contents:'export const getWorkstationBrowserRuntime=()=>globalThis.__p06FixtureRuntime',
       loader:'js'
     }))
   }}]
 })
 const module={exports:{}}
 const vm=require('node:vm')
 vm.runInNewContext(script.outputFiles[0].text,{
    module,exports:module.exports,require,process,console,Buffer,URL,globalThis,
    __dirname:__dirname, setInterval,clearInterval
 },{filename:'p06-native-service.cjs'})
 const svc=module.exports
 try{
   await browser.loadURL(url)
   let status=svc.pageWatchUiState('tab1')
   if(!status.gateQualified){throw Error('GATE_NOT_READY '+status.note)}
   status=await svc.pageWatchEnable('tab1','#items')
   if(status.status?.status!=='watching'){throw Error('NOT_WATCHING '+JSON.stringify(status))}
   await wc.executeJavaScript("document.querySelector('#clock').textContent='11:00'")
   await new Promise(r=>setTimeout(r,1600))
   if(svc.pageWatchUiState('tab1').status?.lastEvent){throw Error('FALSE_POSITIVE_CLOCK')}
   await wc.executeJavaScript("document.querySelector('#items').appendChild(document.createElement('li'))")
   await new Promise(r=>setTimeout(r,3000))
   status=svc.pageWatchUiState('tab1')
   if(status.status?.lastEvent?.current!==3){throw Error('EVENT_NOT_DETECTED '+JSON.stringify(status))}
   const id=status.status.lastEvent.event_id
   if(authorized){await new Promise(r=>setTimeout(r,7500))}
   const db=new DatabaseSync(dbFile)
   const row=db.prepare('SELECT event_id,sequence,state FROM page_watch_occurrence WHERE event_id=?').get(id)
   if(!row||row.state!=='PENDING'){throw Error('LEDGER_NOT_COMMITTED')}
   let p04State='UNCONFIGURED'
   if(authorized) {
     const p04=db.prepare("SELECT source,state,route_id FROM business_event_outbox WHERE event_id=?").get(id)
     if(!p04 || p04.source!=='page_watch' || p04.route_id!=='fixture-route' ||
        p04.state!=='FAILED_SAFE') {
       throw Error('P04_NOT_FAILSAFE '+JSON.stringify(p04))
     }
     p04State=p04.state
   }
   const configPath=path.join(tmp,'Browser','page-watch-config.json')
   if(!fs.existsSync(configPath)){throw Error('CONFIG_NOT_PERSISTED')}
   // Real WebContents remains usable but host authority is revoked.
   state.humanControlLease={owner:'human'}
   const after=svc.pageWatchUiState('tab1').status
   if(after?.status!=='paused'){throw Error('DID_NOT_REVOKE_ON_HUMAN_LEASE')}
   await wc.executeJavaScript("document.querySelector('#items').appendChild(document.createElement('li'))")
   await new Promise(r=>setTimeout(r,1550))
   const n=db.prepare('SELECT count(*) n FROM page_watch_occurrence').get().n
   if(n!==1){throw Error('EVENT_AFTER_TAKEOVER '+n)}
   state.humanControlLease=null
   // An authorized same-origin navigation also revokes observation (login/logout).
   await svc.pageWatchEnable('tab1','#items')
   if(svc.pageWatchUiState('tab1').status?.status!=='watching'){
     throw Error('REARM_FAILED_AFTER_EXPLICIT_HUMAN_AUTH')
   }
   await browser.loadURL(url+'/logout')
   const navigated=svc.pageWatchUiState('tab1').status
   if(navigated?.status!=='paused'){throw Error('DID_NOT_REVOKE_ON_NAVIGATION')}
   if(db.prepare('SELECT count(*) n FROM page_watch_occurrence').get().n!==1){
     throw Error('EVENT_AFTER_NAVIGATION')
   }
   db.close()
   console.log(JSON.stringify({test:'P06_NATIVE_SERVICE',result:'PASS',chromium:process.versions.chrome,
     events:n,idPrefix:id.slice(0,12),configPersisted:true,paused:true,
     humanTakeoverRevokes:true,navigationRevokes:true,externalCalls:0,p04State}))
 } finally{
   svc.pageWatchShutdown()
   browser.destroy()
   await new Promise(r=>server.close(r))
   await new Promise(r=>setTimeout(r,700))
   try { fs.rmSync(tmp,{recursive:true,force:true,maxRetries:10,retryDelay:250}) }
   catch(e) { console.error('P06_TEMP_CLEANUP_FAIL',String(e)) }
 }
}
app.whenReady().then(()=>main().then(()=>app.exit(0)).catch(e=>{
  console.error('P06_NATIVE_SERVICE_FAIL',String(e));app.exit(1)
}))
