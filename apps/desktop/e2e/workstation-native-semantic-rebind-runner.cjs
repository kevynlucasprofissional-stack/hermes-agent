const fs=require('node:fs')
const os=require('node:os')
const path=require('node:path')
const {spawn}=require('node:child_process')
const esbuild=require('esbuild')

async function main(){
  const scratch=fs.mkdtempSync(path.join(os.tmpdir(),'hermes-native-semantic-'))
  const executable=path.resolve(__dirname,'../node_modules/electron/dist/electron.exe')
  const entry=path.join(__dirname,'workstation-native-semantic-rebind.ts')
  const output=path.join(scratch,'semantic-rebind-e2e.cjs')
  try {
    await esbuild.build({entryPoints:[entry],outfile:output,bundle:true,platform:'node',
      format:'cjs',target:'node22',external:['electron'],logLevel:'error'})
    const env={...process.env,
      HERMES_HOME:path.join(scratch,'home'),
      HERMES_WORKSTATION_HOME:path.join(scratch,'workstation'),
      HERMES_WORKSTATION_BROWSER_PROFILE:path.join(scratch,'profile'),
      HERMES_WORKSTATION_BROWSER_CONTROL_FILE:path.join(scratch,'control.json'),
      HERMES_WORKSTATION_BROWSER_SESSION_STATE_FILE:path.join(scratch,'browser-session.json'),
      HERMES_NATIVE_REBIND_USER_DATA:path.join(scratch,'electron-userdata')}
    delete env.ELECTRON_RUN_AS_NODE
    fs.mkdirSync(env.HERMES_NATIVE_REBIND_USER_DATA,{recursive:true})
    const result=await new Promise((resolve,reject)=>{
      const child=spawn(executable,[output],{env,windowsHide:true,stdio:['ignore','pipe','pipe']})
      let stdout='',stderr='',timedOut=false
      const timer=setTimeout(()=>{timedOut=true;child.kill()},35000)
      child.stdout.on('data',chunk=>stdout+=chunk)
      child.stderr.on('data',chunk=>stderr+=chunk)
      child.on('error',reject)
      child.on('close',code=>{clearTimeout(timer);resolve({code,stdout,stderr,timedOut})})
    })
    const line=result.stdout.split(/\r?\n/).find(row=>row.startsWith('NATIVE_SEMANTIC_REBIND_E2E='))
    const report=line?JSON.parse(line.slice('NATIVE_SEMANTIC_REBIND_E2E='.length)):null
    console.log('NATIVE_SEMANTIC_REBIND_RESULT='+JSON.stringify({code:result.code,
      timedOut:result.timedOut,report,stderr:result.stderr.slice(-2200),stdout:result.stdout.slice(-2200)}))
    if(result.code!==0||result.timedOut||!report ||
      !report.unique?.acknowledged||!report.unique?.parentReceipt||!report.unique?.nextNavigationAllowed||
      !report.ambiguous?.nextNavigationDenied ||report.ambiguous?.acknowledged){
      process.exitCode=2
    }
  }finally{fs.rmSync(scratch,{recursive:true,force:true,maxRetries:8,retryDelay:140})}
}
main().catch(error=>{console.error('NATIVE_REBIND_RUNNER_ERROR='+String(error?.stack||error));process.exitCode=2})