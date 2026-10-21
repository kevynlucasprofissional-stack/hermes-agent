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

  it('compiles inert CandidateLesson on stop with package and idempotency', async () => {
    let compileCount = 0
    const compilingRecorder = new LearningSessionRecorder({
      baseDir: tempDir,
      captureScreenshot: async () => ({ success: true, screenshot_path: path.join(tempDir, 'shot.png') }),
      nowMs: () => 1_000_000,
      compileCandidate: async input => {
        compileCount++
        expect(input.learning_session_id).toBeDefined()
        expect(input.session_dir).toBeDefined()

        return {
          success: true,
          candidateLessonId: `lesson_hd_${input.learning_session_id}`,
          idempotentReuse: compileCount > 1
        }
      }
    })

    const state = await compilingRecorder.start({
      runtimeSessionId: 'rt-demo',
      storedSessionId: 'st-demo',
      tabId: 'tab-demo',
      webContentsId: 5,
      documentEpoch: 'ep-demo',
      allowlistedOrigin: 'http://127.0.0.1:8767',
      videoEnabled: false
    })

    // Record tool and canvas operations
    await compilingRecorder.recordGesture({
      eventId: 'ev-tool',
      tabId: 'tab-demo',
      documentEpoch: 'ep-demo',
      relativeTimeMs: 100,
      kind: 'click',
      role: 'button',
      accessibleName: 'Ferramenta de Carimbo',
      elementTag: 'button'
    })

    await compilingRecorder.recordGesture({
      eventId: 'ev-canvas',
      tabId: 'tab-demo',
      documentEpoch: 'ep-demo',
      relativeTimeMs: 300,
      kind: 'pointerup',
      x: 300,
      y: 200,
      viewportWidth: 1000,
      viewportHeight: 800
    })

    const stopped = await compilingRecorder.stop()

    expect(stopped.compilationStatus).toBe('compiled')
    expect(stopped.candidateLessonId).toContain('lesson_hd_')
    expect(compileCount).toBe(1)

    // Check demonstration_package.json on disk
    const pkgFile = path.join(state.sessionDir, 'demonstration_package.json')
    expect(fs.existsSync(pkgFile)).toBe(true)
    const pkg = JSON.parse(fs.readFileSync(pkgFile, 'utf-8'))
    expect(pkg.schema).toBe('hermes.demonstration_package.v1')
    expect(pkg.segments.length).toBeGreaterThanOrEqual(1)
    expect(pkg.candidateLessonId).toBe(stopped.candidateLessonId)
    expect(pkg.compilationStatus).toBe('compiled')
    expect(pkg.limitations).toContain('Demonstração humana em observação. Não validada em tempo de execução.')

    // Repeat stop is idempotent and does not create duplicates
    const repeatStop = await compilingRecorder.stop()
    expect(repeatStop.status).toBe('idle')
    expect(compileCount).toBe(1)
  })

  it('persists demonstration package with pending_compilation status when compilation is offline', async () => {
    const offlineRecorder = new LearningSessionRecorder({
      baseDir: tempDir,
      captureScreenshot: async () => ({ success: true }),
      nowMs: () => 1_000_000,
      compileCandidate: async () => {
        throw new Error('gateway_offline')
      }
    })

    const state = await offlineRecorder.start({
      runtimeSessionId: 'rt-off',
      storedSessionId: 'st-off',
      tabId: 'tab-off',
      webContentsId: 2,
      documentEpoch: 'ep-off',
      allowlistedOrigin: 'http://127.0.0.1:8767',
      videoEnabled: false
    })

    await offlineRecorder.recordGesture({
      eventId: 'ev-1',
      tabId: 'tab-off',
      documentEpoch: 'ep-off',
      relativeTimeMs: 50,
      kind: 'click',
      role: 'button',
      accessibleName: 'Novo Projeto',
      elementTag: 'button'
    })

    const stopped = await offlineRecorder.stop()

    expect(stopped.compilationStatus).toBe('pending_compilation')
    expect(stopped.lastError).toContain('pending_compilation:gateway_offline')

    const pkgFile = path.join(state.sessionDir, 'demonstration_package.json')
    expect(fs.existsSync(pkgFile)).toBe(true)
    const pkg = JSON.parse(fs.readFileSync(pkgFile, 'utf-8'))
    expect(pkg.compilationStatus).toBe('pending_compilation')
    expect(pkg.candidateLessonId).toBeUndefined()
  })

  it('reproduces multi-step causal learning flow from dogfood session', async () => {
    let mockTime = 1_000_000
    const causalRecorder = new LearningSessionRecorder({
      baseDir: tempDir,
      captureScreenshot: async () => ({ success: true, screenshot_path: path.join(tempDir, 'shot.png') }),
      nowMs: () => mockTime,
      compileCandidate: async input => ({
        success: true,
        candidateLessonId: 'lesson_hd_real_photocraft_1'
      })
    })

    await causalRecorder.start({
      runtimeSessionId: 'rt-photocraft',
      storedSessionId: 'st-photocraft',
      tabId: 'tab-photo',
      webContentsId: 10,
      documentEpoch: 'ep-photo',
      allowlistedOrigin: 'http://127.0.0.1:8767',
      videoEnabled: false
    })

    // Step 1: Document setup
    await causalRecorder.recordGesture({
      eventId: 'ev-setup',
      tabId: 'tab-photo',
      documentEpoch: 'ep-photo',
      relativeTimeMs: 100,
      kind: 'click',
      role: 'button',
      accessibleName: 'Novo Documento 1080x1440',
      elementTag: 'button'
    })

    // Step 2: Import asset
    mockTime += 1000
    await causalRecorder.recordGesture({
      eventId: 'ev-import',
      tabId: 'tab-photo',
      documentEpoch: 'ep-photo',
      relativeTimeMs: 1100,
      kind: 'click',
      role: 'button',
      accessibleName: 'Importar Imagem',
      elementTag: 'button'
    })

    // Step 3: Tool selection -> Stamp (advance beyond 40s policy cooldown)
    mockTime += 45_000
    await causalRecorder.recordGesture({
      eventId: 'ev-stamp-tool',
      tabId: 'tab-photo',
      documentEpoch: 'ep-photo',
      relativeTimeMs: 46100,
      kind: 'click',
      role: 'button',
      accessibleName: 'Ferramenta de Carimbo',
      elementTag: 'button'
    })

    // Trigger evaluation on tool selection
    const questions = await causalRecorder.evaluateQuestions()
    expect(questions.length).toBeGreaterThan(0)
    const qStamp = questions.find(q => q.proposedQuestion.includes("carimbo"))
    expect(qStamp).toBeDefined()
    expect(qStamp!.proposedQuestion).toContain("ferramenta 'carimbo'")

    // Step 4: Human explanation of causality
    await causalRecorder.answerQuestion(qStamp!.id, {
      action: 'correct',
      userCorrection: 'Tentei remover texto com preenchimento mas falhou, usei carimbo pois o fundo era uniforme'
    })

    // Step 5: Canvas manipulation with stamp
    mockTime += 1000
    await causalRecorder.recordGesture({
      eventId: 'ev-canvas-1',
      tabId: 'tab-photo',
      documentEpoch: 'ep-photo',
      relativeTimeMs: 3100,
      kind: 'pointerup',
      x: 846,
      y: 769,
      viewportWidth: 1000,
      viewportHeight: 1000
    })

    // Step 6: Stop session
    const finalState = await causalRecorder.stop()
    expect(finalState.compilationStatus).toBe('compiled')
    expect(finalState.candidateLessonId).toBe('lesson_hd_real_photocraft_1')
    expect(finalState.segmentsCount).toBeGreaterThanOrEqual(3)

    const finalPkg = JSON.parse(fs.readFileSync(path.join(finalState.sessionDir, 'demonstration_package.json'), 'utf-8'))
    expect(finalPkg.humanCorrections.length).toBe(1)
    expect(finalPkg.humanCorrections[0].userResponse).toContain('fundo era uniforme')
  })

  it('records P05 semantic deltas and breadcrumbs and formulates contextual panel questions', async () => {
    let mockTime = 100_000
    const p05Recorder = new LearningSessionRecorder({
      baseDir: tempDir,
      captureScreenshot: async () => ({ success: true, screenshot_path: path.join(tempDir, 'p05.png') }),
      nowMs: () => mockTime
    })

    await p05Recorder.start({
      runtimeSessionId: 'rt-p05',
      storedSessionId: 'st-p05',
      tabId: 'tab-p05',
      webContentsId: 55,
      documentEpoch: 'ep-p05',
      allowlistedOrigin: 'https://design.local',
      intensity: 'intensivo',
      videoEnabled: false
    })

    // Step 1: Human adjusts slider in panel
    await p05Recorder.recordGesture({
      eventId: 'ev-op',
      tabId: 'tab-p05',
      documentEpoch: 'ep-p05',
      relativeTimeMs: 100,
      kind: 'click',
      role: 'slider',
      accessibleName: 'Opacidade',
      containerBreadcrumb: 'Painel de Camadas',
      currentValue: '35%',
      unit: '%'
    })

    const questions = await p05Recorder.evaluateQuestions()
    expect(questions.length).toBeGreaterThan(0)
    const q = questions.find(item => item.proposedQuestion.includes('opacidade'))
    expect(q).toBeDefined()
    expect(q?.proposedQuestion).toContain('Qual critério visual determinou o ajuste de opacidade para 35% no painel de camadas?')
    expect(q?.hypothesis).toContain("O operador ajustou 'Opacidade' para 35% no Painel de Camadas.")

    await p05Recorder.discard()
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

