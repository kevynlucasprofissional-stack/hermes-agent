import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import type { RawHumanBrowserGesture } from './workstation-learning-events'
import {
  type LearningSessionConfig,
  LearningSessionRecorder
} from './workstation-learning-session'

describe('HLM-MVP Vertical Integration Slice (Phases S0-S7)', () => {
  let tempDir: string
  let recorder: LearningSessionRecorder
  let capturedScreenshots: string[] = []

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-vertical-slice-'))
    capturedScreenshots = []
    recorder = new LearningSessionRecorder({
      baseDir: tempDir,
      captureScreenshot: async (tabId: string) => {
        const shotPath = path.join(tempDir, `shot-${Date.now()}.png`)
        fs.writeFileSync(shotPath, 'fake-png-data')
        capturedScreenshots.push(shotPath)

        return { success: true, screenshot_path: shotPath }
      },
      nowMs: () => 5_000_000
    })
  })

  afterEach(async () => {
    if (recorder.isActive()) {
      await recorder.discard()
    }

    fs.rmSync(tempDir, { recursive: true, force: true })
  })

  it('executes complete end-to-end demonstration, live intensity, causal QA, and candidate persistence', async () => {
    // 1. Start learning session
    const config: LearningSessionConfig = {
      runtimeSessionId: 'rt-vertical-1',
      storedSessionId: 'st-vertical-1',
      tabId: 'tab-editor-canvas',
      webContentsId: 88,
      documentEpoch: 'epoch-canvas-1',
      allowlistedOrigin: 'https://effectcraft.local',
      intensity: 'intensivo',
      videoEnabled: false // headless test environment
    }

    const state0 = await recorder.start(config)
    expect(state0.status).toBe('learning')
    expect(state0.intensity).toBe('intensivo')
    expect(state0.tabId).toBe('tab-editor-canvas')

    const initialSessionId = state0.sessionId

    // 2. Human performs demonstration with various gestures
    // Gesture A: Click on named tool button
    const clickTool: RawHumanBrowserGesture = {
      eventId: 'evt-tool-1',
      tabId: 'tab-editor-canvas',
      documentEpoch: 'epoch-canvas-1',
      relativeTimeMs: 100,
      kind: 'click',
      x: 120,
      y: 60,
      viewportWidth: 1280,
      viewportHeight: 720,
      role: 'button',
      accessibleName: 'Blur Filter',
      elementTag: 'button'
    }

    const safeTool = await recorder.recordGesture(clickTool)
    expect(safeTool).not.toBeNull()
    expect(safeTool?.target?.accessible_name).toBe('Blur Filter')

    // Gesture B: Attempted sensitive input (must be discarded!)
    const secretInput: RawHumanBrowserGesture = {
      eventId: 'evt-secret-1',
      tabId: 'tab-editor-canvas',
      documentEpoch: 'epoch-canvas-1',
      relativeTimeMs: 150,
      kind: 'click',
      elementTag: 'input',
      inputType: 'password'
    }

    const safeSecret = await recorder.recordGesture(secretInput)
    expect(safeSecret).toBeNull()

    // Gesture C: Canvas gesture (pointerdown -> pointerup)
    const canvasDown: RawHumanBrowserGesture = {
      eventId: 'evt-canvas-down',
      tabId: 'tab-editor-canvas',
      documentEpoch: 'epoch-canvas-1',
      relativeTimeMs: 200,
      kind: 'pointerdown',
      x: 640,
      y: 360,
      viewportWidth: 1280,
      viewportHeight: 720
    }

    await recorder.recordGesture(canvasDown)
    expect(recorder.getStatus()?.userBusy).toBe(true)

    const canvasUp: RawHumanBrowserGesture = {
      eventId: 'evt-canvas-up',
      tabId: 'tab-editor-canvas',
      documentEpoch: 'epoch-canvas-1',
      relativeTimeMs: 400,
      kind: 'pointerup',
      x: 640,
      y: 360,
      viewportWidth: 1280,
      viewportHeight: 720
    }

    await recorder.recordGesture(canvasUp)
    expect(recorder.getStatus()?.userBusy).toBe(false)

    // Gesture D: Deliberate modified shortcut (Ctrl+S)
    const saveShortcut: RawHumanBrowserGesture = {
      eventId: 'evt-save-1',
      tabId: 'tab-editor-canvas',
      documentEpoch: 'epoch-canvas-1',
      relativeTimeMs: 500,
      kind: 'shortcut',
      ctrl: true,
      key: 'S'
    }

    const safeSave = await recorder.recordGesture(saveShortcut)
    expect(safeSave?.shortcut).toBe('Ctrl+S')

    // 3. Live intensity switch during recording
    const stateDiscreto = await recorder.setIntensity('discreto')
    expect(stateDiscreto.sessionId).toBe(initialSessionId)
    expect(stateDiscreto.intensity).toBe('discreto')
    expect(stateDiscreto.status).toBe('learning')
    expect(stateDiscreto.eventsCount).toBe(4) // 4 safe gestures recorded, 1 rejected

    const stateEquilibrado = await recorder.setIntensity('equilibrado')
    expect(stateEquilibrado.sessionId).toBe(initialSessionId)
    expect(stateEquilibrado.intensity).toBe('equilibrado')

    // 4. Verify question generation from demonstration
    const questions = recorder.getQuestions()
    expect(questions.length).toBeGreaterThan(0)

    const causalQuestion = questions.find(q => q.kind === 'causality' || q.kind === 'decision')
    expect(causalQuestion).toBeDefined()
    expect(causalQuestion?.state).toBe('pending')
    expect(causalQuestion?.hypothesis).toBeDefined()

    // 5. Human answers with correction
    const answered = await recorder.answerQuestion(causalQuestion!.id, {
      action: 'correct',
      userCorrection: 'Salvei o projeto como checkpoint de segurança antes de aplicar a máscara de desfoque pesado'
    })

    expect(answered.state).toBe('corrected')
    expect(answered.needsReinterpretation).toBe(true)
    expect(answered.userResponse).toContain('checkpoint de segurança')

    // 6. Navigation security check: navigating to login pauses session
    const navAllowed = recorder.checkNavigation('https://effectcraft.local/login?auth=oauth')
    expect(navAllowed).toBe(false)
    expect(recorder.getStatus()?.status).toBe('paused')
    expect(recorder.getStatus()?.lastError).toContain('Auth/login page detected')

    // Resume session
    recorder.resume()
    expect(recorder.getStatus()?.status).toBe('learning')

    // 7. Stop and finalize session
    const finalState = await recorder.stop()
    expect(finalState.status).toBe('idle')
    expect(finalState.endedAt).not.toBeNull()
    expect(finalState.eventsCount).toBe(4)

    // 8. Verify persistence on disk
    const sessionDir = finalState.sessionDir
    expect(fs.existsSync(path.join(sessionDir, 'learning_session.json'))).toBe(true)
    expect(fs.existsSync(path.join(sessionDir, 'events.jsonl'))).toBe(true)
    expect(fs.existsSync(path.join(sessionDir, 'questions.jsonl'))).toBe(true)

    const eventsContent = fs.readFileSync(path.join(sessionDir, 'events.jsonl'), 'utf-8').trim().split('\n')
    expect(eventsContent).toHaveLength(4)

    // Verify sensitive data was not stored
    const allEventsRaw = fs.readFileSync(path.join(sessionDir, 'events.jsonl'), 'utf-8')
    expect(allEventsRaw).not.toContain('password')
    expect(allEventsRaw).not.toContain('evt-secret-1')

    const questionsContent = fs.readFileSync(path.join(sessionDir, 'questions.jsonl'), 'utf-8').trim().split('\n')
    expect(questionsContent.length).toBeGreaterThanOrEqual(1)
    const lastQuestionRecord = JSON.parse(questionsContent[questionsContent.length - 1])
    expect(lastQuestionRecord.state).toBe('corrected')
    expect(lastQuestionRecord.needsReinterpretation).toBe(true)
  })
})
