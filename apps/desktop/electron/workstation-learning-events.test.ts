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
 it('extracts container breadcrumb and slider values while retaining privacy', () => {
   const sliderClick: RawHumanBrowserGesture = {
     ...click,
     role: 'slider',
     elementTag: 'input',
     inputType: 'range',
     accessibleName: 'Opacidade',
     containerBreadcrumb: 'Painel de Camadas',
     currentValue: '35%',
     unit: '%'
   }
   const norm = normalizeHumanGesture(sliderClick)
   expect(norm).not.toBeNull()
   expect(norm?.target?.role).toBe('slider')
   expect(norm?.target?.accessible_name).toBe('Opacidade')
   expect(norm?.target?.containerBreadcrumb).toBe('Painel de Camadas')
   expect(norm?.target?.container_breadcrumb).toBe('Painel de Camadas')
   expect(norm?.target?.currentValue).toBe('35%')
   expect(norm?.target?.unit).toBe('%')
 })
 it('strictly rejects text inputs, emails, tel, search, and textarea', () => {
   expect(normalizeHumanGesture({ ...click, elementTag: 'input', inputType: 'text' })).toBeNull()
   expect(normalizeHumanGesture({ ...click, elementTag: 'input', inputType: 'email' })).toBeNull()
   expect(normalizeHumanGesture({ ...click, elementTag: 'input', inputType: 'tel' })).toBeNull()
   expect(normalizeHumanGesture({ ...click, elementTag: 'textarea' })).toBeNull()
   expect(normalizeHumanGesture({ ...click, elementTag: 'input' })).toBeNull()
 })
 it('normalizes DOM mutation delta correctly', () => {
   const modalClick: RawHumanBrowserGesture = {
     ...click,
     domDelta: { effectKind: 'modal_opened', summary: 'Diálogo aberto' }
   }
   const norm = normalizeHumanGesture(modalClick)
   expect(norm?.domDelta).toEqual({ effectKind: 'modal_opened', summary: 'Diálogo aberto' })
   expect(norm?.dom_delta).toEqual({ effectKind: 'modal_opened', summary: 'Diálogo aberto' })
 })
 it('strips sensitive container breadcrumbs and delta summaries', () => {
   const sensitiveBreadcrumb: RawHumanBrowserGesture = {
     ...click,
     containerBreadcrumb: 'Painel de Password Recovery',
     domDelta: { effectKind: 'modal_opened', summary: 'Reveal secret api key' }
   }
   const norm = normalizeHumanGesture(sensitiveBreadcrumb)
   expect(norm?.target?.containerBreadcrumb).toBeUndefined()
   expect(norm?.domDelta?.summary).toBeUndefined()
 })
 it('drops malformed events', ()=>expect(normalizeHumanGesture({...click,relativeTimeMs:NaN})).toBeNull())
})
