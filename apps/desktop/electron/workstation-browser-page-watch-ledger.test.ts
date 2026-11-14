import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { describe, expect, it } from 'vitest'

import { PageWatchOccurrenceLedger } from './workstation-browser-page-watch-ledger'

describe('P06-R canonical SQLite sequence and replay', () => {
  function fixture() {
    const folder=fs.mkdtempSync(path.join(os.tmpdir(),'p06r-ledger-'))
    const name=path.join(folder,'kanban.db')
    return {name,clean:()=>fs.rmSync(folder,{force:true,recursive:true})}
  }
  const request=(activation_key='activation1',observation_key='revision1')=>({
    watch_id:'watch1',activation_key,observation_key,route_id:'local-only',
    origin:'https://fixture.example',previous:1,current:2
  })
  it('replay is idempotent; repeated occurrence after process restart gets new ID',()=>{
    const f=fixture()
    try {
      let db=new PageWatchOccurrenceLedger(f.name)
      const first=db.reserve(request())
      expect(db.reserve(request()).event_id).toBe(first.event_id)
      db.close()
      db=new PageWatchOccurrenceLedger(f.name)
      const second=db.reserve(request('activation2'))
      expect(second.sequence).toBe(2)
      expect(second.event_id).not.toBe(first.event_id)
      expect(db.pending()).toEqual([first.event_id,second.event_id])
      db.close()
    } finally {f.clean()}
  })
  it('two connections cannot mint twice for the same trusted observation key',()=>{
    const f=fixture()
    try {
      const a=new PageWatchOccurrenceLedger(f.name),b=new PageWatchOccurrenceLedger(f.name)
      const one=a.reserve(request()),two=b.reserve(request())
      expect(one.event_id).toBe(two.event_id)
      expect(a.pending()).toHaveLength(1)
      expect(b.reserve(request('activation2')).event_id).not.toBe(one.event_id)
      a.close();b.close()
    }finally {f.clean()}
  })
  it('does not acknowledge independently unverified effect, rejects conflicting replay',()=>{
    const f=fixture()
    try {
      const db=new PageWatchOccurrenceLedger(f.name)
      db.reserve(request())
      expect(()=>db.reserve({...request(),current:3})).toThrow('conflicting_page_watch_replay')
      expect(db.pending()).toHaveLength(1)
      db.close()
    }finally {f.clean()}
  })
})
