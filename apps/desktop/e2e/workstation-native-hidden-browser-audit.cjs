const {app,BrowserWindow} = require('electron');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const root=fs.mkdtempSync(path.join(os.tmpdir(),'hermes-hidden-native-'));
app.setPath('userData',root);
app.commandLine.appendSwitch('disable-background-timer-throttling');
async function main(){
 const w=new BrowserWindow({show:false,focusable:false,skipTaskbar:true,width:720,height:600,webPreferences:{backgroundThrottling:false,sandbox:true}});
 const wc=w.webContents;
 const html='<html><body style="margin:0"><button id="b" style="width:200px;height:50px">Click</button><input id="i" style="display:block;margin-top:5px;width:300px;height:50px"/><div id="scroll" style="height:140px;overflow:auto"><div style="height:700px">scroll</div></div><script>window.count=0;document.querySelector("#b").onclick=()=>window.count++;document.querySelector("#i").onkeydown=e=>{if(e.key==="Enter")window.enter=true}</script></body></html>';
 await wc.loadURL('data:text/html;charset=utf-8,'+encodeURIComponent(html));
 wc.debugger.attach('1.3');
 async function cmd(name,params){return wc.debugger.sendCommand(name,params)}
 await cmd('Input.dispatchMouseEvent',{type:'mousePressed',x:60,y:25,button:'left',clickCount:1});
 await cmd('Input.dispatchMouseEvent',{type:'mouseReleased',x:60,y:25,button:'left',clickCount:1});
 const clicks=await wc.executeJavaScript('window.count');
 await cmd('Input.dispatchMouseEvent',{type:'mousePressed',x:50,y:80,button:'left',clickCount:1});
 await cmd('Input.dispatchMouseEvent',{type:'mouseReleased',x:50,y:80,button:'left',clickCount:1});
 await cmd('Input.insertText',{text:'hermes-native-proof'});
 await cmd('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
 await cmd('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
 await cmd('Input.dispatchMouseEvent',{type:'mouseWheel',x:60,y:170,deltaX:0,deltaY:250});
 await new Promise(resolve=>setTimeout(resolve,250));
 const state=await wc.executeJavaScript('({clicked:window.count,input:document.querySelector("#i").value,active:document.activeElement.id,enter:!!window.enter,scrolled:document.querySelector("#scroll").scrollTop})');
 const result={native:true,windowVisible:w.isVisible(),focusable:w.isFocusable(),isFocused:w.isFocused(),...state,profileTemp:root.startsWith(os.tmpdir())};
 console.log('HERMES_HIDDEN_NATIVE_AUDIT='+JSON.stringify(result));
 if(result.clicked!==1||result.input!=='hermes-native-proof'||!result.enter||result.scrolled<=0||result.windowVisible){throw Error('NATIVE_HIDDEN_BROWSER_CRITERIA_FAILED')}
 wc.debugger.detach();
 w.destroy();
}
app.whenReady().then(main).then(()=>app.quit()).catch(e=>{console.error('NATIVE_HIDDEN_ERROR='+String(e?.stack||e));process.exitCode=2;app.quit()});
app.on('window-all-closed',()=>{});
app.on('quit',()=>{try{fs.rmSync(root,{recursive:true,force:true,maxRetries:3})}catch{}});
