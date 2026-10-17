import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import type { RawHumanBrowserGesture } from './workstation-learning-events'
import {
  type LearningSessionConfig,
  LearningSessionRecorder
} from './workstation-learning-session'

describe('HLM-MVP LearningSessionRecorder (owner Electron)', () => {
  let tempDir: string
  let recorder: LearningSessionRecorder

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-learning-test-'))
    recorder = new LearningSessionRecorder({
      baseDir: tempDir,
      captureScreenshot: async () => ({ success: true, screenshot_path: path.join(tempDir, 'shot.png') }),
      nowMs: () => 1_000_000
    })
  })

  afterEach(async () => {
    if (recorder.isActive()) {
      await recorder.discard()
    }

    fs.rmSync(tempDir, { recursive: true, force: true })
  })

  it('starts learning session with default intensivo intensity and persists manifest', async () => {
    const config: LearningSessionConfig = {
      runtimeSessionId: 'sess-rt-1',
      storedSessionId: 'sess-st-1',
      tabId: 'tab-101',
      webContentsId: 42,
      documentEpoch: 'epoch-1',
      allowlistedOrigin: 'https://app.example.com',
      videoEnabled: false
    }

    const state = await recorder.start(config)

    expect(state.status).toBe('learning')
    expect(state.intensity).toBe('intensivo')
    expect(state.tabId).toBe('tab-101')
    expect(state.runtimeSessionId).toBe('sess-rt-1')
    expect(state.storedSessionId).toBe('sess-st-1')
    expect(state.eventsCount).toBe(0)
    expect(state.questionsCount).toBe(0)

    const sessionFile = path.join(state.sessionDir, 'learning_session.json')
    expect(fs.existsSync(sessionFile)).toBe(true)
    const saved = JSON.parse(fs.readFileSync(sessionFile, 'utf-8'))
    expect(saved.schema).toBe('hermes.learning_session.v1')
    expect(saved.intensity).toBe('intensivo')
  })

  it('changes intensity LIVE without restarting recording or losing events', async () => {
    const state0 = await recorder.start({
      runtimeSessionId: 'rt-1',
      storedSessionId: 'st-1',
      tabId: 'tab-1',
      webContentsId: 1,
      documentEpoch: 'ep-1',
      allowlistedOrigin: 'https://example.com',
      videoEnabled: false
    })

    const sessionId = state0.sessionId

    // Record an event
    const gesture: RawHumanBrowserGesture = {
      eventId: 'evt-1',
      tabId: 'tab-1',
      documentEpoch: 'ep-1',
      relativeTimeMs: 100,
      kind: 'click',
      x: 100,
      y: 100,
      viewportWidth: 1000,
      viewportHeight: 800,
      role: 'button',
      accessibleName: 'Save Project',
      elementTag: 'button'
    }

    await recorder.recordGesture(gesture)

    // Change intensity live to 'discreto'
    const state1 = await recorder.setIntensity('discreto')
    expect(state1.sessionId).toBe(sessionId)
    expect(state1.intensity).toBe('discreto')
    expect(state1.status).toBe('learning')
    expect(state1.eventsCount).toBe(1)

    // Change intensity live to 'equilibrado'
    const state2 = await recorder.setIntensity('equilibrado')
    expect(state2.sessionId).toBe(sessionId)
    expect(state2.intensity).toBe('equilibrado')
    expect(state2.eventsCount).toBe(1)

    // Verify events.jsonl contains the event
    const eventsFile = path.join(state2.sessionDir, 'events.jsonl')
    expect(fs.existsSync(eventsFile)).toBe(true)
    const lines = fs.readFileSync(eventsFile, 'utf-8').trim().split('\n')
    expect(lines).toHaveLength(1)
    const ev = JSON.parse(lines[0])
    expect(ev.event_id).toBe('evt-1')
    expect(ev.target?.accessible_name).toBe('Save Project')
  })

  it('rejects unsupported intensity string without altering session state', async () => {
    await recorder.start({
      runtimeSessionId: 'rt-1',
      storedSessionId: 'st-1',
      tabId: 'tab-1',
      webContentsId: 1,
      documentEpoch: 'ep-1',
      allowlistedOrigin: 'https://example.com',
      videoEnabled: false
    })

    await expect(recorder.setIntensity('turbo' as any)).rejects.toThrow('unsupported_learning_intensity')
    expect(recorder.getStatus()?.intensity).toBe('intensivo')
  })

  it('refuses to start two concurrent learning sessions (fail-closed)', async () => {
    await recorder.start({
      runtimeSessionId: 'rt-1',
      storedSessionId: 'st-1',
      tabId: 'tab-1',
      webContentsId: 1,
      documentEpoch: 'ep-1',
      allowlistedOrigin: 'https://example.com',
      videoEnabled: false
    })

    await expect(recorder.start({
      runtimeSessionId: 'rt-2',
      storedSessionId: 'st-2',
      tabId: 'tab-2',
      webContentsId: 2,
      documentEpoch: 'ep-2',
      allowlistedOrigin: 'https://other.com',
      videoEnabled: false
    })).rejects.toThrow(/already_active/)
  })

  it('sanitizes gestures and discards sensitive/editable inputs from recording', async () => {
    await recorder.start({
      runtimeSessionId: 'rt-1',
      storedSessionId: 'st-1',
      tabId: 'tab-1',
      webContentsId: 1,
      documentEpoch: 'ep-1',
      allowlistedOrigin: 'https://example.com',
      videoEnabled: false
    })

    // Password field interaction
    const passwordInput: RawHumanBrowserGesture = {
      eventId: 'evt-bad-1',
      tabId: 'tab-1',
      documentEpoch: 'ep-1',
      relativeTimeMs: 200,
      kind: 'click',
      elementTag: 'input',
      inputType: 'password'
    }

    const recordedBad = await recorder.recordGesture(passwordInput)
    expect(recordedBad).toBeNull()

    // Regular button click
    const goodClick: RawHumanBrowserGesture = {
      eventId: 'evt-good-1',
      tabId: 'tab-1',
      documentEpoch: 'ep-1',
      relativeTimeMs: 300,
      kind: 'click',
      x: 200,
      y: 150,
      viewportWidth: 800,
      viewportHeight: 600,
      role: 'button',
      accessibleName: 'Render Frame',
      elementTag: 'button'
    }

    const recordedGood = await recorder.recordGesture(goodClick)
    expect(recordedGood).not.toBeNull()
    expect(recorder.getStatus()?.eventsCount).toBe(1)
  })

  it('pauses immediately on navigation to sensitive auth URL or different origin', async () => {
    await recorder.start({
      runtimeSessionId: 'rt-1',
      storedSessionId: 'st-1',
      tabId: 'tab-1',
      webContentsId: 1,
      documentEpoch: 'ep-1',
      allowlistedOrigin: 'https://app.example.com',
      videoEnabled: false
    })

    // Navigation within allowlist
    const allowed = recorder.checkNavigation('https://app.example.com/editor/canvas')
    expect(allowed).toBe(true)
    expect(recorder.getStatus()?.status).toBe('learning')

    // Navigation to auth/login
    const authNav = recorder.checkNavigation('https://app.example.com/login?redirect=1')
    expect(authNav).toBe(false)
    expect(recorder.getStatus()?.status).toBe('paused')
    expect(recorder.getStatus()?.lastError).toContain('Auth/login page detected')

    // Navigation off-origin
    recorder.resume()
    const offOrigin = recorder.checkNavigation('https://evil.com/phishing')
    expect(offOrigin).toBe(false)
    expect(recorder.getStatus()?.status).toBe('paused')
    expect(recorder.getStatus()?.lastError).toContain('Off-origin navigation')
  })

  it('evaluates and answers questions with confirmation or correction', async () => {
    let mockTime = 1_000_000

    const timeRecorder = new LearningSessionRecorder({
      baseDir: tempDir,
      captureScreenshot: async () => ({ success: true, screenshot_path: path.join(tempDir, 'shot.png') }),
      nowMs: () => mockTime
    })

    await timeRecorder.start({
      runtimeSessionId: 'rt-1',
      storedSessionId: 'st-1',
      tabId: 'tab-1',
      webContentsId: 1,
      documentEpoch: 'ep-1',
      allowlistedOrigin: 'https://app.example.com',
      videoEnabled: false,
      intensity: 'intensivo'
    })

    // Record high value causal shortcut
    const shortcut: RawHumanBrowserGesture = {
      eventId: 'evt-cut-1',
      tabId: 'tab-1',
      documentEpoch: 'ep-1',
      relativeTimeMs: 100,
      kind: 'shortcut',
      ctrl: true,
      key: 'S'
    }

    await timeRecorder.recordGesture(shortcut)

    // Trigger evaluation
    const questions = await timeRecorder.evaluateQuestions()
    expect(questions.length).toBeGreaterThan(0)
    const q = questions[0]
    expect(q.kind).toBeDefined()
    expect(q.proposedQuestion).toBeDefined()
    expect(q.state).toBe('pending')

    // Answering with correction
    const answered = await timeRecorder.answerQuestion(q.id, {
      action: 'correct',
      userCorrection: 'Eu salvei uma versão preliminar para evitar perda de dados antes de aplicar desfoque pesado'
    })

    expect(answered.state).toBe('corrected')
    expect(answered.userResponse).toContain('preliminar')
    expect(answered.needsReinterpretation).toBe(true)

    // Verify questions.jsonl was appended
    const qFile = path.join(timeRecorder.getStatus()!.sessionDir, 'questions.jsonl')
    expect(fs.existsSync(qFile)).toBe(true)
    const qLines = fs.readFileSync(qFile, 'utf-8').trim().split('\n')
    expect(qLines.length).toBeGreaterThanOrEqual(1)
  })

  it('stops and finalizes session cleanly without data duplication', async () => {
    await recorder.start({
      runtimeSessionId: 'rt-1',
      storedSessionId: 'st-1',
      tabId: 'tab-1',
      webContentsId: 1,
      documentEpoch: 'ep-1',
      allowlistedOrigin: 'https://example.com',
      videoEnabled: false
    })

    const finalState = await recorder.stop()
    expect(finalState.status).toBe('idle')
    expect(finalState.endedAt).not.toBeNull()
    expect(recorder.isActive()).toBe(false)

    // Stop again is idempotent
    const secondStop = await recorder.stop()
    expect(secondStop.status).toBe('idle')
  })

  it('discards session completely removing files and resetting state', async () => {
    const state = await recorder.start({
      runtimeSessionId: 'rt-1',
      storedSessionId: 'st-1',
      tabId: 'tab-1',
      webContentsId: 1,
      documentEpoch: 'ep-1',
      allowlistedOrigin: 'https://example.com',
      videoEnabled: false
    })

    const sessionDir = state.sessionDir
    expect(fs.existsSync(sessionDir)).toBe(true)

    await recorder.discard()
    expect(recorder.isActive()).toBe(false)
    expect(fs.existsSync(sessionDir)).toBe(false)
  })
})
