import assert from 'node:assert/strict'
import test from 'node:test'
import {validateAiControlOperation as validate,isMutation} from './ai-control-operations.mjs'
const click = {op:'click',surface:'desktop',target:{kind:'role',value:'button'},
  expected:{documentId:'doc-1',grantId:'grant-1'}}

test('accepts bounded typed operations, reports mutation class',()=>{
 assert.equal(validate({op:'snapshot',surface:'desktop'}).op,'snapshot')
 assert.equal(validate(click).target.kind,'role')
 assert.equal(isMutation('click'),true)
 assert.equal(isMutation('snapshot'),false)
})
test('rejects guest, arbitrary evaluate, unknown properties',()=>{
 for(const x of [
   {op:'evaluate',surface:'desktop',code:'1+1'},
   {op:'snapshot',surface:'browser'},
   {op:'snapshot',surface:'desktop',code:'1+1'},
   {...click,target:{kind:'css',value:'a',script:'bad'}}
 ]) assert.throws(()=>validate(x))
})
test('mutations require a bounded target and an explicit binding',()=>{
 for(const x of [
   {...click,expected:undefined},
   {...click,expected:{documentId:'doc-1',grantId:''}},
   {...click,target:{kind:'css',value:''}},
   {...click,op:'fill',text:'x'.repeat(4097)},
   {...click,op:'press',key:'Meta+R'}
 ]) assert.throws(()=>validate(x))
})
