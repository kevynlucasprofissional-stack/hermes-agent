const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const { spawn } = require('node:child_process')
const esbuild = require('esbuild')

async function run() {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'hermes-runtime-native-'))
  const exe=path.resolve(__dirname,'../node_modules/electron/dist/electron.exe')
  const entry=path.join(__dirname,'workstation-runtime-native-p06-human-close.ts')
  const out=path.join(root,'browser-native-runtime.cjs')
  try {
    await esbuild.build({entryPoints:[entry],outfile:out,bundle:true,platform:'node',
      format:'cjs',target:'node22',external:['electron'],logLevel:'error'})
    const env={...process.env,HERMES_HOME:path.join(root,'home'),
      HERMES_WORKSTATION_HOME:path.join(root,'workstation'),
      HERMES_WORKSTATION_BROWSER_PROFILE:path.join(root,'profile'),
      HERMES_WORKSTATION_BROWSER_CONTROL_FILE:path.join(root,'control.json'),
      HERMES_WORKSTATION_BROWSER_SESSION_STATE_FILE:path.join(root,'browser-session.json')}
    delete env.ELECTRON_RUN_AS_NODE
    const result=await new Promise((resolve,reject)=>{
      const child=spawn(exe,[out],{env,windowsHide:true,stdio:['ignore','pipe','pipe']})
      let stdout='',stderr='',timedOut=false
      const timer=setTimeout(()=>{timedOut=true;child.kill()},25000)
      child.stdout.on('data',chunk=>stdout+=chunk)
      child.stderr.on('data',chunk=>stderr+=chunk)
      child.on('error',reject)
      child.on('close',code=>{clearTimeout(timer);resolve({code,stdout,stderr,timedOut})})
    })
    const line=result.stdout.split(/\r?\n/).find(s=>s.startsWith('HERMES_RUNTIME_NATIVE_E2E='))
    const audit=line?JSON.parse(line.slice('HERMES_RUNTIME_NATIVE_E2E='.length)):null
    console.log('RUNTIME_NATIVE_RESULT='+JSON.stringify({code:result.code,timedOut:result.timedOut,
      audit,stderr:result.stderr.slice(-600),stdout:result.stdout.slice(-2200)}))
    if(result.code!==0||result.timedOut||!audit||!audit.navigationReceiptsMatched||
      !audit.nativeClickVerified || !audit.nativeTypeVerified || !audit.mutationReceipts ||
      audit.ownedTabs!==2){process.exitCode=2}
  } finally {fs.rmSync(root,{recursive:true,force:true,maxRetries:8,retryDelay:120})}
}
run().catch(e=>{console.error('RUNTIME_NATIVE_RUNNER_ERROR='+String(e?.stack||e));process.exitCode=2})
