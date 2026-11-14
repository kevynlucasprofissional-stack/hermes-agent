const fs=require('node:fs'),os=require('node:os'),path=require('node:path')
const {spawn}=require('node:child_process'),esbuild=require('esbuild')
async function phase(exe,out,env,phase){
  return await new Promise((resolve,reject)=>{
    const child=spawn(exe,[out],{windowsHide:true,env:{...env,P06_PROCESS_PHASE:phase},stdio:['ignore','pipe','pipe']})
    let stdout='',stderr='',timedOut=false
    const timer=setTimeout(()=>{timedOut=true;child.kill()},18000)
    child.stdout.on('data',chunk=>stdout+=chunk)
    child.stderr.on('data',chunk=>stderr+=chunk)
    child.on('error',reject)
    child.on('close',code=>{clearTimeout(timer);resolve({phase,code,stdout,stderr,timedOut})})
  })
}
async function run(){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'hermes-p06-process-crash-'))
 try{
  const entry=path.join(__dirname,'workstation-runtime-native-p06-process-crash-entry.ts')
  const out=path.join(root,'p06-runtime.cjs')
  await esbuild.build({entryPoints:[entry],outfile:out,bundle:true,platform:'node',
    format:'cjs',target:'node22',external:['electron'],logLevel:'error'})
  const exe=path.resolve(__dirname,'../node_modules/electron/dist/electron.exe')
  const env={...process.env,HERMES_HOME:path.join(root,'home'),
    HERMES_WORKSTATION_HOME:path.join(root,'workstation'),
    HERMES_WORKSTATION_BROWSER_PROFILE:path.join(root,'profile'),
    HERMES_WORKSTATION_BROWSER_CONTROL_FILE:path.join(root,'control.json'),
    HERMES_WORKSTATION_BROWSER_SESSION_STATE_FILE:path.join(root,'session.json')}
  delete env.ELECTRON_RUN_AS_NODE
  const seed=await phase(exe,out,env,'seed')
  const recover=seed.code===73 && !seed.timedOut ? await phase(exe,out,env,'recover') : null
  const raw=seed.stdout+'\n'+(recover?.stdout||'')
  const one=raw.split(/\r?\n/).find(line=>line.startsWith('P06_PROCESS_SEED='))
  const two=raw.split(/\r?\n/).find(line=>line.startsWith('P06_PROCESS_RESTART_AUDIT='))
  const audit={seed:one?JSON.parse(one.substring('P06_PROCESS_SEED='.length)):null,
    recovery:two?JSON.parse(two.substring('P06_PROCESS_RESTART_AUDIT='.length)):null}
  const result={seedExit:seed.code,recoveryExit:recover?.code,
    seedPid:audit.seed?.pid,recoveryPid:audit.recovery?.pid,
    differentProcesses:audit.seed?.pid!==audit.recovery?.pid,
    recovery:audit.recovery,
    seedErrors:seed.stderr.slice(-550),recoveryErrors:recover?.stderr.slice(-650),
    seedTimedOut:seed.timedOut,recoveryTimedOut:recover?.timedOut}
  console.log('P06_MULTIPROCESS_RESULT='+JSON.stringify(result))
  if(seed.code!==73||recover?.code!==0||seed.timedOut||recover.timedOut||
    !audit.seed||!audit.recovery||result.differentProcesses!==true){process.exitCode=2}
 }finally{fs.rmSync(root,{recursive:true,force:true,maxRetries:7,retryDelay:140})}
}
run().catch(e=>{console.error('P06_RUNNER_ERROR='+String(e?.stack||e));process.exitCode=2})