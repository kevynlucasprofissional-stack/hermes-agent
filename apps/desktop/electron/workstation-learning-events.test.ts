import { describe, expect, it } from 'vitest'

import { normalizeHumanGesture, type RawHumanBrowserGesture } from './workstation-learning-events'

const click: RawHumanBrowserGesture = {
 eventId:'ev1',tabId:'t1',documentEpoch:'ep1',relativeTimeMs:2123.45,
 kind:'click',x:300,y:120,viewportWidth:600,viewportHeight:400,
 role:'button',accessibleName:'Apply Effect',elementTag:'button'
}

describe('HLM-MVP safe event normalization', () => {
 it('keeps stable time/target/normalized coordinates', ()=>{
   expect(normalizeHumanGesture(click)).toMatchObject({schema:'hermes.human_gesture.v1',time_ms:2123,normalized_position:{x:0.5,y:0.3},target:{role:'button',accessible_name:'Apply Effect'}})
 })
 it('does not capture input, passwords, or editable fields', ()=>{
   expect(normalizeHumanGesture({...click, elementTag:'input',inputType:'password'})).toBeNull()
   expect(normalizeHumanGesture({...click,isEditable:true})).toBeNull()
 })
 it('strips sensitive button names', ()=>{
   expect(normalizeHumanGesture({...click,accessibleName:'Copy API key'})?.target).toEqual({role:'button'})
 })
 it('captures only modified shortcut chords, never raw typed letters', ()=>{
   expect(normalizeHumanGesture({...click,kind:'shortcut',key:'a'})).toBeNull()
   expect(normalizeHumanGesture({...click,kind:'shortcut',key:'s',ctrl:true})?.shortcut).toBe('Ctrl+S')
 })
 it('drops malformed events', ()=>expect(normalizeHumanGesture({...click,relativeTimeMs:NaN})).toBeNull())
})
