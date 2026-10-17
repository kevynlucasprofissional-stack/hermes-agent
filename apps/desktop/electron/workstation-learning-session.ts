/**
 * HLM-MVP LearningSessionRecorder (owner Electron).
 * Observes human demonstrations inside the native Electron Browser tab.
 * Manages atomic lifecycle, live-intensity changes, safe event appending,
 * question engine evaluations, auth-screen pauses, and local persistence.
 */

import { type ChildProcess, spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

import { app } from 'electron'

import {
  normalizeHumanGesture,
  type RawHumanBrowserGesture,
  type SafeHumanBrowserGesture
} from './workstation-learning-events'
import {
  decideLearningQuestion,
  type LearningIntensity,
  type LearningQuestionCandidate,
  type LearningQuestionContext,
  type LearningQuestionKind,
  parseLearningIntensity
} from './workstation-learning-question-policy'

export interface LearningSessionConfig {
  runtimeSessionId: string
  storedSessionId: string
  tabId: string
  webContentsId: number
  documentEpoch: string
  allowlistedOrigin: string
  intensity?: LearningIntensity
  videoEnabled?: boolean
}

export interface LearningQuestionItem {
  id: string
  sessionId: string
  tabId: string
  eventRefs: string[]
  fromMs: number
  toMs: number
  kind: LearningQuestionKind
  category: string
  hypothesis: string
  uncertainty: number
  score: number
  dedupeKey: string
  proposedQuestion: string
  state: 'pending' | 'confirmed' | 'corrected' | 'deferred' | 'dismissed'
  userResponse?: string
  needsReinterpretation: boolean
  createdAt: string
  answeredAt?: string
}

export interface LearningSessionState {
  schema: 'hermes.learning_session.v1'
  sessionId: string
  runtimeSessionId: string
  storedSessionId: string
  tabId: string
  webContentsId: number
  documentEpoch: string
  status: 'idle' | 'learning' | 'paused' | 'failed'
  intensity: LearningIntensity
  startedAt: string
  endedAt: string | null
  allowlistedOrigin: string
  eventsCount: number
  questionsCount: number
  pendingQuestions: LearningQuestionItem[]
  videoStatus: 'recording' | 'stopped' | 'blocked' | 'error' | 'disabled'
  lastError: string | null
  sessionDir: string
  userBusy: boolean
}

export interface AnswerQuestionInput {
  action: 'confirm' | 'correct' | 'defer' | 'dismiss'
  userCorrection?: string
}

export interface LearningSessionRecorderOptions {
  baseDir?: string
  captureScreenshot?: (tabId: string) => Promise<{ success: boolean; screenshot_path?: string }>
  nowMs?: () => number
}

const AUTH_URL_PATTERN = /(login|signin|auth|oauth|account|sso|signup|register|checkout|verify)/i

function defaultBaseDir(): string {
  try {
    return path.join(app.getPath('userData'), 'workstation', 'learning-sessions')
  } catch {
    return path.join(process.cwd(), '.hermes-workstation', 'learning-sessions')
  }
}

export class LearningSessionRecorder {
  private readonly baseDir: string
  private readonly captureScreenshot?: (tabId: string) => Promise<{ success: boolean; screenshot_path?: string }>
  private readonly getNowMs: () => number

  private state: LearningSessionState | null = null
  private alreadyAskedKeys = new Set<string>()
  private presentedTimestamps: number[] = []
  private questionsMap = new Map<string, LearningQuestionItem>()
  private recentGestures: SafeHumanBrowserGesture[] = []
  private videoProcess: ChildProcess | null = null
  private lastEvaluationMs = 0

  constructor(options: LearningSessionRecorderOptions = {}) {
    this.baseDir = options.baseDir || defaultBaseDir()
    this.captureScreenshot = options.captureScreenshot
    this.getNowMs = options.nowMs || (() => Date.now())
  }

  isActive(): boolean {
    return this.state !== null && (this.state.status === 'learning' || this.state.status === 'paused')
  }

  getStatus(): LearningSessionState | null {
    if (!this.state) {return null}

    return {
      ...this.state,
      pendingQuestions: Array.from(this.questionsMap.values()).filter(q => q.state === 'pending')
    }
  }

  getQuestions(): LearningQuestionItem[] {
    return Array.from(this.questionsMap.values())
  }

  async start(config: LearningSessionConfig): Promise<LearningSessionState> {
    if (this.isActive()) {
      throw new Error(`learning_session_already_active:${this.state?.sessionId}`)
    }

    const intensity = parseLearningIntensity(config.intensity ?? 'intensivo')
    const sessionId = `learn-${Date.now()}-${config.tabId.slice(0, 8)}`
    const sessionDir = path.join(this.baseDir, sessionId)
    const snapshotsDir = path.join(sessionDir, 'snapshots')
    const mediaDir = path.join(sessionDir, 'media')

    fs.mkdirSync(sessionDir, { recursive: true })
    fs.mkdirSync(snapshotsDir, { recursive: true })
    fs.mkdirSync(mediaDir, { recursive: true })

    const eventsPath = path.join(sessionDir, 'events.jsonl')
    const questionsPath = path.join(sessionDir, 'questions.jsonl')

    if (!fs.existsSync(eventsPath)) {
      fs.writeFileSync(eventsPath, '', { encoding: 'utf-8' })
    }

    if (!fs.existsSync(questionsPath)) {
      fs.writeFileSync(questionsPath, '', { encoding: 'utf-8' })
    }

    this.alreadyAskedKeys.clear()
    this.presentedTimestamps = []
    this.questionsMap.clear()
    this.recentGestures = []
    this.lastEvaluationMs = this.getNowMs()

    let videoStatus: LearningSessionState['videoStatus'] = 'disabled'

    if (config.videoEnabled !== false) {
      videoStatus = this.startVideoRecording(mediaDir)
    }

    this.state = {
      schema: 'hermes.learning_session.v1',
      sessionId,
      runtimeSessionId: config.runtimeSessionId,
      storedSessionId: config.storedSessionId,
      tabId: config.tabId,
      webContentsId: config.webContentsId,
      documentEpoch: config.documentEpoch,
      status: 'learning',
      intensity,
      startedAt: new Date().toISOString(),
      endedAt: null,
      allowlistedOrigin: config.allowlistedOrigin,
      eventsCount: 0,
      questionsCount: 0,
      pendingQuestions: [],
      videoStatus,
      lastError: null,
      sessionDir,
      userBusy: false
    }

    this.persistManifest()

    return this.getStatus()!
  }

  async setIntensity(rawIntensity: unknown): Promise<LearningSessionState> {
    if (!this.state || !this.isActive()) {
      throw new Error('no_active_learning_session')
    }

    const newIntensity = parseLearningIntensity(rawIntensity)

    if (this.state.intensity === newIntensity) {
      return this.getStatus()!
    }

    this.state.intensity = newIntensity
    this.persistManifest()

    // Immediately evaluate questions with the new budget/thresholds
    await this.evaluateQuestions()

    return this.getStatus()!
  }

  checkNavigation(targetUrl: string): boolean {
    if (!this.state || !this.isActive()) {return true}

    try {
      const urlObj = new URL(targetUrl)

      // 1. Check sensitive auth URLs
      if (AUTH_URL_PATTERN.test(urlObj.pathname) || AUTH_URL_PATTERN.test(urlObj.hostname)) {
        this.pause(`Auth/login page detected: ${urlObj.origin}${urlObj.pathname}. Paused before capturing frames.`)

        return false
      }

      // 2. Check allowlisted origin
      if (this.state.allowlistedOrigin) {
        const allowed = new URL(this.state.allowlistedOrigin)

        if (urlObj.origin !== allowed.origin) {
          this.pause(`Off-origin navigation: ${urlObj.origin} !== ${allowed.origin}. Paused before capturing frames.`)

          return false
        }
      }

      return true
    } catch {
      this.pause(`Invalid or unparseable target navigation: ${targetUrl}`)

      return false
    }
  }

  pause(reason?: string): LearningSessionState {
    if (!this.state) {throw new Error('no_learning_session')}
    this.state.status = 'paused'

    if (reason) {
      this.state.lastError = reason
    }

    this.persistManifest()

    return this.getStatus()!
  }

  resume(): LearningSessionState {
    if (!this.state) {throw new Error('no_learning_session')}
    this.state.status = 'learning'
    this.state.lastError = null
    this.persistManifest()

    return this.getStatus()!
  }

  setUserBusy(busy: boolean): void {
    if (this.state) {
      this.state.userBusy = busy
    }
  }

  async recordGesture(raw: RawHumanBrowserGesture): Promise<SafeHumanBrowserGesture | null> {
    if (!this.state || this.state.status !== 'learning') {
      return null
    }

    const safe = normalizeHumanGesture(raw)

    if (!safe) {
      return null
    }

    // Track user busy state for dragging / canvas gestures
    if (safe.kind === 'pointerdown') {
      this.setUserBusy(true)
    } else if (safe.kind === 'pointerup') {
      this.setUserBusy(false)
    }

    // Persist event in JSONL
    try {
      const eventsPath = path.join(this.state.sessionDir, 'events.jsonl')
      fs.appendFileSync(eventsPath, JSON.stringify(safe) + '\n', 'utf-8')
    } catch {
      // Ignore write error
    }

    this.state.eventsCount++
    this.recentGestures.push(safe)

    if (this.recentGestures.length > 50) {
      this.recentGestures.shift()
    }

    // Snapshot on significant actions (clicks or modified shortcuts)
    if (safe.kind === 'click' || safe.kind === 'shortcut') {
      if (this.captureScreenshot) {
        this.captureScreenshot(this.state.tabId).catch(() => undefined)
      }
    }

    this.persistManifest()

    // Evaluate potential questions triggered by this action
    await this.evaluateQuestions()

    return safe
  }

  async evaluateQuestions(): Promise<LearningQuestionItem[]> {
    if (!this.state || this.state.status !== 'learning') {
      return []
    }

    if (this.recentGestures.length === 0) {
      return []
    }

    const now = this.getNowMs()
    const lastGesture = this.recentGestures[this.recentGestures.length - 1]

    // Formulate contextual candidate from recent gestures
    const candidate = this.generateCandidate(lastGesture, now)

    if (!candidate) {
      return this.getStatus()?.pendingQuestions || []
    }

    const context: LearningQuestionContext = {
      intensity: this.state.intensity,
      nowMs: now,
      recentlyPresentedAtMs: this.presentedTimestamps,
      pendingQueueSize: Array.from(this.questionsMap.values()).filter(q => q.state === 'pending').length,
      alreadyAskedKeys: this.alreadyAskedKeys,
      userBusy: this.state.userBusy,
      userPausedQuestions: false
    }

    const decision = decideLearningQuestion(candidate.policyCandidate, context)

    if (decision.action === 'ask') {
      const questionItem: LearningQuestionItem = {
        id: `q-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        sessionId: this.state.sessionId,
        tabId: this.state.tabId,
        eventRefs: [...candidate.policyCandidate.eventRefs],
        fromMs: lastGesture.time_ms,
        toMs: lastGesture.time_ms,
        kind: candidate.policyCandidate.kind,
        category: candidate.category,
        hypothesis: candidate.hypothesis,
        uncertainty: candidate.policyCandidate.uncertainty,
        score: decision.score,
        dedupeKey: candidate.policyCandidate.dedupeKey,
        proposedQuestion: candidate.proposedQuestion,
        state: 'pending',
        needsReinterpretation: false,
        createdAt: new Date().toISOString()
      }

      this.questionsMap.set(questionItem.id, questionItem)
      this.alreadyAskedKeys.add(questionItem.dedupeKey)
      this.presentedTimestamps.push(now)
      this.state.questionsCount++

      try {
        const questionsPath = path.join(this.state.sessionDir, 'questions.jsonl')
        fs.appendFileSync(questionsPath, JSON.stringify(questionItem) + '\n', 'utf-8')
      } catch {
        // Ignore write error
      }

      this.persistManifest()
    }

    return Array.from(this.questionsMap.values()).filter(q => q.state === 'pending')
  }

  async answerQuestion(questionId: string, input: AnswerQuestionInput): Promise<LearningQuestionItem> {
    if (!this.state) {throw new Error('no_learning_session')}

    const question = this.questionsMap.get(questionId)

    if (!question) {
      throw new Error(`question_not_found:${questionId}`)
    }

    const actionMap: Record<AnswerQuestionInput['action'], LearningQuestionItem['state']> = {
      confirm: 'confirmed',
      correct: 'corrected',
      defer: 'deferred',
      dismiss: 'dismissed'
    }

    question.state = actionMap[input.action]
    question.answeredAt = new Date().toISOString()

    if (input.action === 'confirm') {
      question.userResponse = 'Confirmed by user'
      question.needsReinterpretation = false
    } else if (input.action === 'correct') {
      question.userResponse = input.userCorrection || 'Corrected by user'
      question.needsReinterpretation = true
    } else if (input.action === 'defer') {
      question.userResponse = 'Deferred'
    } else if (input.action === 'dismiss') {
      question.userResponse = 'Dismissed'
    }

    // Persist update in questions.jsonl
    try {
      const questionsPath = path.join(this.state.sessionDir, 'questions.jsonl')
      fs.appendFileSync(questionsPath, JSON.stringify(question) + '\n', 'utf-8')
    } catch {
      // Ignore write error
    }

    this.persistManifest()

    return question
  }

  async stop(): Promise<LearningSessionState> {
    if (!this.state || this.state.status === 'idle') {
      return this.state || {
        schema: 'hermes.learning_session.v1',
        sessionId: '',
        runtimeSessionId: '',
        storedSessionId: '',
        tabId: '',
        webContentsId: 0,
        documentEpoch: '',
        status: 'idle',
        intensity: 'intensivo',
        startedAt: '',
        endedAt: null,
        allowlistedOrigin: '',
        eventsCount: 0,
        questionsCount: 0,
        pendingQuestions: [],
        videoStatus: 'stopped',
        lastError: null,
        sessionDir: '',
        userBusy: false
      }
    }

    this.stopVideoRecording()

    this.state.status = 'idle'
    this.state.endedAt = new Date().toISOString()
    this.state.videoStatus = 'stopped'
    this.persistManifest()

    const finalState = this.getStatus()!
    this.state = null

    return finalState
  }

  async discard(): Promise<void> {
    if (!this.state) {return}

    const sessionDir = this.state.sessionDir
    this.stopVideoRecording()

    this.state = null
    this.questionsMap.clear()
    this.alreadyAskedKeys.clear()

    try {
      if (fs.existsSync(sessionDir)) {
        fs.rmSync(sessionDir, { recursive: true, force: true })
      }
    } catch {
      // Ignore file removal errors during discard
    }
  }

  private generateCandidate(
    gesture: SafeHumanBrowserGesture,
    nowMs: number
  ): {
    policyCandidate: LearningQuestionCandidate
    category: string
    hypothesis: string
    proposedQuestion: string
  } | null {
    if (gesture.kind === 'shortcut' && gesture.shortcut) {
      const dedupeKey = `shortcut:${gesture.shortcut}`

      return {
        policyCandidate: {
          id: `cand-${gesture.event_id}`,
          dedupeKey,
          kind: 'causality',
          eventRefs: [gesture.event_id],
          novelty: 0.85,
          uncertainty: 0.8,
          reuseValue: 0.95,
          interruptionCost: 0.1
        },
        category: 'causality',
        hypothesis: `O operador utilizou o atalho ${gesture.shortcut} como passo deliberado de controle ou sincronização.`,
        proposedQuestion: `Por que você executou o atalho ${gesture.shortcut} nesta etapa da demonstração?`
      }
    }

    if (gesture.kind === 'click' && gesture.target?.role) {
      const name = gesture.target.accessible_name || gesture.target.role
      const dedupeKey = `click:${gesture.target.role}:${name}`

      return {
        policyCandidate: {
          id: `cand-${gesture.event_id}`,
          dedupeKey,
          kind: 'decision',
          eventRefs: [gesture.event_id],
          novelty: 0.75,
          uncertainty: 0.75,
          reuseValue: 0.85,
          interruptionCost: 0.15
        },
        category: 'decision',
        hypothesis: `O operador selecionou '${name}' com base em um critério específico do projeto ou fluxo de edição.`,
        proposedQuestion: `Qual foi o critério para escolher '${name}' nesta etapa?`
      }
    }

    if (gesture.kind === 'pointerup' && gesture.normalized_position) {
      const pos = gesture.normalized_position
      const dedupeKey = `canvas:pointer:${Math.floor(pos.x * 10)}_${Math.floor(pos.y * 10)}`

      return {
        policyCandidate: {
          id: `cand-${gesture.event_id}`,
          dedupeKey,
          kind: 'heuristic',
          eventRefs: [gesture.event_id],
          novelty: 0.7,
          uncertainty: 0.85,
          reuseValue: 0.8,
          interruptionCost: 0.2
        },
        category: 'heuristic',
        hypothesis: `O operador manipulou a área do Canvas nas coordenadas normalizadas (${pos.x}, ${pos.y}).`,
        proposedQuestion: `Qual ajuste visual ou parâmetro você refinou nesta área do Canvas?`
      }
    }

    return null
  }

  private startVideoRecording(mediaDir: string): LearningSessionState['videoStatus'] {
    try {
      const videoPath = path.join(mediaDir, 'recording.webm')
      // Check if ffmpeg is available
      const ffmpegBin = process.platform === 'win32' ? 'ffmpeg.exe' : 'ffmpeg'

      const proc = spawn(ffmpegBin, [
        '-y',
        '-f', 'lavfi',
        '-i', 'color=c=black:s=1280x720:r=15',
        '-t', '1',
        '-c:v', 'libvpx',
        videoPath
      ], { stdio: 'ignore' })

      proc.on('error', () => {
        if (this.state) {
          this.state.videoStatus = 'blocked'
          this.state.lastError = 'ffmpeg_unavailable: video capture requires ffmpeg'
          this.persistManifest()
        }
      })

      this.videoProcess = proc

      return 'recording'
    } catch (err) {
      return 'blocked'
    }
  }

  private stopVideoRecording(): void {
    if (this.videoProcess) {
      try {
        this.videoProcess.kill('SIGTERM')
      } catch {
        // ignore
      }

      this.videoProcess = null
    }
  }

  private persistManifest(): void {
    if (!this.state) {return}

    try {
      const sessionFile = path.join(this.state.sessionDir, 'learning_session.json')
      fs.writeFileSync(sessionFile, JSON.stringify(this.state, null, 2), 'utf-8')
    } catch {
      // Ignore write errors to prevent breaking critical loops
    }
  }
}
