import fs from 'node:fs';
import {connectAiControl} from '../../apps/desktop/scripts/ai-control-client.mjs';
const [title, file]=process.argv.slice(2);
if(!title||!file)throw Error('title_and_prompt_file_required');
const prompt=fs.readFileSync(file,'utf8');
const bridge=await connectAiControl();
const info=await bridge.evaluate('window.hermesDesktop.getGatewayWsUrl()');
if(!info?.ok||!info.wsUrl?.startsWith('ws://127.0.0.1:'))throw Error('no_authorized_loopback_gateway');
const ws=new WebSocket(info.wsUrl),pending=new Map();
let serial=0,sessionId=null,done=false;
const connected=new Promise((resolve,reject)=>{
 ws.addEventListener('open',resolve,{once:true});
 ws.addEventListener('error',reject,{once:true});
});
await Promise.race([connected,new Promise((_,reject)=>setTimeout(()=>reject(Error('ws_timeout')),9000))]);
ws.addEventListener('message',e=>{
 let m;try{m=JSON.parse(e.data)}catch{return}
 if(m.id&&pending.has(m.id)){const h=pending.get(m.id);pending.delete(m.id);h(m);return}
 if(m.method==='event'){
  const x=m.params||{};
  if(x.session_id===sessionId && x.type==='message.complete'){
   done=true;
   const summary=String(x.payload?.text||'').slice(0,2400);
   console.log(JSON.stringify({event:'message.complete',sessionId,summary}));
  }
 }
});
function rpc(method,params,timeoutMs=25000){
 const id=++serial;
 const res=new Promise((resolve,reject)=>{
  const t=setTimeout(()=>{pending.delete(id);reject(Error(method+'_timeout'))},timeoutMs);
  pending.set(id,x=>{clearTimeout(t);x.error?reject(Error(x.error.message)):resolve(x.result)});
 });
 ws.send(JSON.stringify({jsonrpc:'2.0',id,method,params}));return res;
}
try{
 const c=await rpc('session.create',{title,source:'desktop',cwd:'C:\\Github\\hermes-agent',close_on_disconnect:false,idempotency_key:'wa-hyb-c8-'+title});
 sessionId=c.session_id;console.log(JSON.stringify({phase:'create',sessionId,title}));
 const ack=await rpc('prompt.submit',{session_id:sessionId,text:prompt});
 console.log(JSON.stringify({phase:'submit',status:ack.status,sessionId}));
 for(let i=0;i<75 && !done;i++){await new Promise(resolve=>setTimeout(resolve,4000));if(i%5===0)console.log(JSON.stringify({phase:'poll',index:i,sessionId,done}));}
 const h=await rpc('session.history',{session_id:sessionId},16000);
 const last=(h?.messages||[]).filter(m=>m.role==='assistant'&&typeof m.content==='string'&&m.content.trim()).slice(-1);
 console.log(JSON.stringify({phase:'finish',sessionId,done,total:h?.count,last:last.map(m=>m.content.slice(0,3800))}));
}catch(e){console.log(JSON.stringify({phase:'error',sessionId,error:String(e.message)}));process.exitCode=1}
finally{ws.close();bridge.close()}
