// Operator-authorized upload scope for an explicit Hermes campaign TaskRun.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {parseDocument} from 'yaml';

const [mode, task, session, run, root] = process.argv.slice(2);
if (!['add','remove'].includes(mode) || ![task,session,run,root].every(s=>typeof s==='string'&&s.length>0))
  throw Error('campaign_upload_scope_invalid');
if (task.length>128||session.length>128||run.length>128)
  throw Error('campaign_upload_identity_invalid');
const home = process.env.HERMES_HOME || path.join(process.env.LOCALAPPDATA||'', 'hermes');
const cfg=path.join(home,'config.yaml');
const st=fs.statSync(cfg);
if (!st.isFile()||st.size>65536) throw Error('campaign_upload_config_invalid');
const before=fs.readFileSync(cfg,'utf8');
const doc=parseDocument(before,{keepSourceTokens:true});
if(doc.errors.length)throw Error('campaign_upload_config_syntax');
const previous=doc.toJS()?.browser?.workstation?.upload_grants||[];
const grants=Array.isArray(previous)?previous:[];
const filtered=grants.filter(x=>!(x?.task_id===task && x?.session_id===session && x?.run_id===run));
if(mode==='add'){
  const real=fs.realpathSync.native(root);
  // Windows may resolve an 8.3 TEMP alias to its canonical long path.
  // Containment is checked against the canonical base immediately below.
  if(!fs.statSync(real).isDirectory()) throw Error('campaign_upload_root_invalid');
  const base=path.join(home,'campaign-media');
  const relative=path.relative(fs.realpathSync.native(base),real);
  if(!relative||relative==='..'||relative.startsWith('..'+path.sep)||path.isAbsolute(relative))
    throw Error('campaign_upload_root_untrusted');
  filtered.push({
    task_id:task,session_id:session,run_id:run,
    expires_at:new Date(Date.now()+25*60*1000).toISOString(),
    allowed_roots:[real],allowed_origins:['https://web.whatsapp.com'],
    max_bytes:20000000,max_files:1
  });
}
doc.setIn(['browser','workstation','upload_grants'],filtered);
const after=String(doc);
if(fs.statSync(cfg).mtimeMs!==st.mtimeMs) throw Error('campaign_upload_concurrent_config_change');
const tmp=cfg+'.campaign-grant-'+process.pid;
try{
  fs.writeFileSync(tmp,after,{flag:'wx',mode:st.mode});
  fs.renameSync(tmp,cfg);
}catch(e){try{fs.unlinkSync(tmp)}catch{}throw e}
console.log(JSON.stringify({ok:true,mode,scopes:filtered.length}));
