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
import {
  type DemonstrationPackage,
  type DemonstrationSegment,
  LearningDemonstrationSegmenter
} from './workstation-learning-segmenter'

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
  runtimeSessionId?: string
  storedSessionId?: string
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
  segmentsCount?: number
  pendingQuestions: LearningQuestionItem[]
  videoStatus: 'recording' | 'stopped' | 'blocked' | 'error' | 'disabled'
  lastError: string | null
  sessionDir: string
  userBusy: boolean
  compilationStatus?: 'pending_compilation' | 'compiled' | 'none'
  candidateLessonId?: string
}

export interface AnswerQuestionInput {
  action: 'confirm' | 'correct' | 'defer' | 'dismiss'
  userCorrection?: string
}

export interface CompileCandidateInput {
  learning_session_id: string
  session_dir: string
  skill_name?: string
  intent_description?: string
  proposed_fix_description?: string
}

export interface CompileCandidateResult {
  success: boolean
  candidateLessonId?: string
  idempotentReuse?: boolean
  error?: string
}

export interface CaptureFrameResult {
  success: boolean
  pngBuffer?: Buffer
  timestampMs: number
  error?: string
}

export interface LearningSessionRecorderOptions {
  baseDir?: string
  captureScreenshot?: (tabId: string, targetPath?: string) => Promise<{ success: boolean; screenshot_path?: string }>
  captureFrame?: (tabId: string) => Promise<any>
  nowMs?: () => number
  compileCandidate?: (input: CompileCandidateInput) => Promise<CompileCandidateResult>
  hasProvider?: boolean
  apiBaseUrl?: string
}

const AUTH_URL_PATTERN = /(login|signin|auth|oauth|account|sso|signup|register|checkout|verify)/i

function defaultBaseDir(): string {
  try {
    return path.join(app.getPath('userData'), 'workstation', 'learning-sessions')
  } catch {
    return path.join(process.cwd(), '.hermes-workstation', 'learning-sessions')
  }
}

const DEFAULT_VIDEO_FPS = 3
const FRAME_CAPTURE_INTERVAL_MS = Math.round(1000 / DEFAULT_VIDEO_FPS)

interface FrameIndexEntry {
  frame_number: number
  timestamp_ms: number
  relative_time_ms: number
  png_path: string
  event_refs: string[]
}

export class LearningSessionRecorder {
  private readonly baseDir: string
  private readonly captureScreenshot?: (tabId: string) => Promise<{ success: boolean; screenshot_path?: string }>
  private readonly captureFrame?: (tabId: string) => Promise<CaptureFrameResult>
  private readonly getNowMs: () => number
  private readonly compileCandidate?: (input: CompileCandidateInput) => Promise<CompileCandidateResult>
  private readonly hasProvider: boolean
  private readonly apiBaseUrl: string

  // Monotonic timebase for P0c: hrtime anchor established at construction
  private readonly hrTimeBaseNs: bigint
  private readonly wallClockBaseMs: number

  private state: LearningSessionState | null = null
  private segmenter: LearningDemonstrationSegmenter | null = null
  private latestSnapshotRef: string | null = null
  private alreadyAskedKeys = new Set<string>()
  private presentedTimestamps: number[] = []
  private questionsMap = new Map<string, LearningQuestionItem>()
  private recentGestures: SafeHumanBrowserGesture[] = []
  private videoProcess: ChildProcess | null = null
  private frameCaptureTimer: ReturnType<typeof setInterval> | null = null
  private frameCaptureInFlight = false
  private frameNumber = 0
  private frameIndexEntries: FrameIndexEntry[] = []
  private videoStartedAtMs: number | null = null
  private lastEvaluationMs = 0
  private lastFrameBuffer: Buffer | null = null

  constructor(options: LearningSessionRecorderOptions = {}) {
    this.baseDir = options.baseDir || defaultBaseDir()
    this.captureScreenshot = options.captureScreenshot
    this.captureFrame = options.captureFrame
    this.getNowMs = options.nowMs || (() => Date.now())
    this.compileCandidate = options.compileCandidate
    this.hasProvider = options.hasProvider ?? false
    this.apiBaseUrl = options.apiBaseUrl || 'http://127.0.0.1:8765'
    // P0c: Establish monotonic timebase anchor at construction
    this.hrTimeBaseNs = process.hrtime.bigint()
    this.wallClockBaseMs = Date.now()
  }

  /**
   * P0c: Returns monotonic milliseconds elapsed since recorder construction.
   * Uses hrtime delta to guarantee monotonicity regardless of wall-clock adjustments.
   * Falls back to injected nowMs when it differs from Date.now() (test mock support).
   * Public to allow WorkstationBrowserRuntime to synchronize event timestamps.
   */
  getMonotonicMs(): number {
    const injected = this.getNowMs()

    if (injected !== Date.now()) {
      return injected
    }

    const deltaNs = process.hrtime.bigint() - this.hrTimeBaseNs

    return Number(deltaNs / BigInt(1_000_000))
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
    this.lastEvaluationMs = this.getMonotonicMs()
    this.segmenter = new LearningDemonstrationSegmenter(sessionId, config.tabId)
    this.latestSnapshotRef = null

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
      segmentsCount: 0,
      pendingQuestions: [],
      videoStatus,
      lastError: null,
      sessionDir,
      userBusy: false,
      compilationStatus: 'none'
    }

    this.persistManifest()

    return this.getStatus()!
  }

  getSegments(): DemonstrationSegment[] {
    return this.segmenter ? this.segmenter.getSegments() : []
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

    // Suspend frame capture while paused — do NOT stop the encoder process,
    // just stop feeding frames so the video pauses at the last captured state.
    this.stopFrameCaptureLoop()
    this.persistManifest()

    return this.getStatus()!
  }

  resume(): LearningSessionState {
    if (!this.state) {throw new Error('no_learning_session')}
    this.state.status = 'learning'
    this.state.lastError = null

    // Resume frame capture if video recording is active
    if (this.videoProcess && !this.frameCaptureTimer) {
      this.startFrameCaptureLoop()
    }

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
      const snapFilename = `snap_${safe.event_id}_${safe.time_ms}.png`
      const snapRelPath = path.join('snapshots', snapFilename).replace(/\\/g, '/')
      const snapAbsPath = path.join(this.state.sessionDir, 'snapshots', snapFilename)

      if (this.lastFrameBuffer) {
        try {
          fs.mkdirSync(path.dirname(snapAbsPath), { recursive: true })
          fs.writeFileSync(snapAbsPath, this.lastFrameBuffer)
          safe.snapshot_ref = snapRelPath
          this.latestSnapshotRef = snapRelPath
        } catch {
          // ignore
        }
      } else if (this.captureScreenshot) {
        try {
          const res = await this.captureScreenshot(this.state.tabId)

          if (res?.success && res.screenshot_path) {
            safe.snapshot_ref = res.screenshot_path
            this.latestSnapshotRef = res.screenshot_path
          }
        } catch {
          // ignore
        }
      }
    }

    if (this.segmenter) {
      this.segmenter.addGesture(safe, this.latestSnapshotRef ?? undefined)
      this.state.segmentsCount = this.segmenter.getSegments().length
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

    const now = this.getMonotonicMs()
    const lastGesture = this.recentGestures[this.recentGestures.length - 1]

    // Formulate contextual candidate from segmenter or fallback
    const candidate = this.segmenter
      ? this.segmenter.generateQuestionCandidate(now, this.hasProvider)
      : this.generateCandidate(lastGesture, now)

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
        id: `q-${this.getMonotonicMs()}-${Math.random().toString(36).slice(2, 6)}`,
        sessionId: this.state.sessionId,
        runtimeSessionId: this.state.runtimeSessionId,
        storedSessionId: this.state.storedSessionId,
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

    // Update segmenter with human answer and causal explanation
    if (this.segmenter) {
      this.segmenter.recordHumanAnswer(
        questionId,
        question.proposedQuestion,
        question.userResponse || '',
        question.needsReinterpretation
      )
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
        segmentsCount: 0,
        pendingQuestions: [],
        videoStatus: 'stopped',
        lastError: null,
        sessionDir: '',
        userBusy: false,
        compilationStatus: 'none'
      }
    }

    // Await encoder shutdown and frame index flush before finalizing state
    await this.stopVideoRecording()

    this.state.status = 'idle'
    this.state.endedAt = new Date().toISOString()
    this.state.videoStatus = 'stopped'

    // Build demonstration package with structured segments and evidence refs
    let pkg: DemonstrationPackage | null = null

    if (this.segmenter) {
      pkg = this.segmenter.buildDemonstrationPackage(
        this.state.allowlistedOrigin,
        this.state.startedAt,
        this.state.endedAt,
        this.state.eventsCount,
        this.state.questionsCount,
        this.state.sessionDir
      )

      try {
        const pkgPath = path.join(this.state.sessionDir, 'demonstration_package.json')
        fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2), 'utf-8')
      } catch {
        // ignore write error
      }
    }

    // Attempt compilation bridge to Python runtime
    await this.compileDemonstrationCandidate(pkg)

    // P1b: Ingest inert candidate so the experience compiler can index it later
    try {
      const ingestEndpoint = `${this.apiBaseUrl}/api/workstation/learning/ingest-candidate`

      const ingestPayload = {
        learning_session_id: this.state.sessionId,
        session_dir: this.state.sessionDir,
        skill_name: this.state.allowlistedOrigin || 'workstation_learning'
      }

      const ingestRes = await fetch(ingestEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ingestPayload),
        signal: AbortSignal.timeout(3000)
      })

      if (!ingestRes.ok && !this.state.lastError) {
        this.state.lastError = `ingest_candidate_failed: status ${ingestRes.status}`
      }
    } catch (err: any) {
      if (!this.state.lastError) {
        this.state.lastError = `ingest_candidate_unreachable: ${err?.message || 'timeout'}`
      }
    }

    this.persistManifest()

    const finalState = this.getStatus()!
    this.state = null

    return finalState
  }

  private async compileDemonstrationCandidate(pkg: DemonstrationPackage | null): Promise<void> {
    if (!this.state) {return}

    const payload: CompileCandidateInput = {
      learning_session_id: this.state.sessionId,
      session_dir: this.state.sessionDir,
      skill_name: this.state.allowlistedOrigin || 'workstation_learning'
    }

    if (this.compileCandidate) {
      try {
        const result = await this.compileCandidate(payload)

        if (result.success && result.candidateLessonId) {
          this.state.compilationStatus = 'compiled'
          this.state.candidateLessonId = result.candidateLessonId
        } else {
          this.state.compilationStatus = 'pending_compilation'
          this.state.lastError = result.error || 'compilation_hook_failed'
        }
      } catch (err: any) {
        this.state.compilationStatus = 'pending_compilation'
        this.state.lastError = `pending_compilation:${err?.message || 'error'}`
      }
    } else {
      // Default: invoke authorized local gateway HTTP endpoint
      try {
        const endpoint = `${this.apiBaseUrl}/api/workstation/experience/learning-sessions/compile-candidate`

        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          signal: AbortSignal.timeout(3000)
        })

        if (res.ok) {
          const data: any = await res.json()
          this.state.compilationStatus = 'compiled'
          this.state.candidateLessonId = data.lesson?.lesson_id
        } else {
          this.state.compilationStatus = 'pending_compilation'
          this.state.lastError = `pending_compilation: endpoint status ${res.status}`
        }
      } catch (err: any) {
        this.state.compilationStatus = 'pending_compilation'
        this.state.lastError = `pending_compilation: backend unreachable (${err?.message || 'timeout'})`
      }
    }

    // Update demonstration_package.json with final candidateLessonId and compilationStatus
    if (pkg && this.state.sessionDir) {
      pkg.compilationStatus = this.state.compilationStatus || 'pending_compilation'
      pkg.candidateLessonId = this.state.candidateLessonId

      try {
        const pkgPath = path.join(this.state.sessionDir, 'demonstration_package.json')
        fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2), 'utf-8')
      } catch {
        // ignore
      }
    }
  }

  async discard(): Promise<void> {
    if (!this.state) {return}

    const sessionDir = this.state.sessionDir
    await this.stopVideoRecording()

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
    if (!this.captureFrame) {
      return 'disabled'
    }

    try {
      const videoPath = path.join(mediaDir, 'recording.webm')
      const ffmpegBin = process.platform === 'win32' ? 'ffmpeg.exe' : 'ffmpeg'

      const proc = spawn(ffmpegBin, [
        '-y',
        '-f', 'image2pipe',
        '-framerate', String(DEFAULT_VIDEO_FPS),
        '-vcodec', 'png',
        '-i', 'pipe:0',
        '-an',
        '-c:v', 'libvpx-vp9',
        '-deadline', 'realtime',
        '-cpu-used', '5',
        '-pix_fmt', 'yuv420p',
        videoPath
      ], { stdio: ['pipe', 'ignore', 'pipe'] })

      let encoderFailed = false

      proc.on('error', () => {
        encoderFailed = true

        if (this.state) {
          this.state.videoStatus = 'blocked'
          this.state.lastError = 'ffmpeg_unavailable: video capture requires ffmpeg'
          this.persistManifest()
        }

        this.stopFrameCaptureLoop()
      })

      proc.stderr?.on('data', (chunk: Buffer) => {
        const msg = chunk.toString().toLowerCase()

        if (msg.includes('error') || msg.includes('invalid')) {
          encoderFailed = true
        }
      })

      proc.on('exit', (code) => {
        if (code !== 0 && code !== null && !encoderFailed) {
          encoderFailed = true

          if (this.state && this.state.videoStatus === 'recording') {
            this.state.videoStatus = 'blocked'
            this.state.lastError = `ffmpeg_exited_with_code_${code}`
            this.persistManifest()
          }
        }
      })

      this.videoProcess = proc
      this.frameNumber = 0
      this.frameIndexEntries = []
      this.videoStartedAtMs = this.getMonotonicMs()
      this.frameCaptureInFlight = false

      this.startFrameCaptureLoop()

      return 'recording'
    } catch {
      return 'blocked'
    }
  }

  private startFrameCaptureLoop(): void {
    if (this.frameCaptureTimer) {
      clearInterval(this.frameCaptureTimer)
    }

    this.frameCaptureTimer = setInterval(() => {
      this.captureNextFrame().catch(() => undefined)
    }, FRAME_CAPTURE_INTERVAL_MS)
  }

  private stopFrameCaptureLoop(): void {
    if (this.frameCaptureTimer) {
      clearInterval(this.frameCaptureTimer)
      this.frameCaptureTimer = null
    }
  }

  private async captureNextFrame(): Promise<void> {
    if (!this.state || !this.captureFrame || this.frameCaptureInFlight) {return}

    if (this.state.status !== 'learning') {return}

    if (!this.videoProcess || !this.videoProcess.stdin || this.videoProcess.stdin.destroyed) {return}

    this.frameCaptureInFlight = true

    try {
      const nowMs = this.getMonotonicMs()
      const rawRes = await this.captureFrame(this.state.tabId)

      if (!rawRes) {
        return
      }

      const pngBuf = Buffer.isBuffer(rawRes)
        ? rawRes
        : (rawRes as any).pngBuffer || (rawRes as any).buffer || null

      if (!pngBuf) {
        return
      }

      this.lastFrameBuffer = pngBuf

      const relativeTimeMs = this.videoStartedAtMs ? nowMs - this.videoStartedAtMs : 0
      this.frameNumber++

      // Write PNG to FFmpeg stdin with backpressure handling
      const canWrite = this.videoProcess.stdin.write(pngBuf)

      if (!canWrite) {
        await new Promise<void>(resolve => {
          this.videoProcess?.stdin?.once('drain', resolve)
        })
      }

      // Persist snapshot for significant frames (every 10th or on event proximity)
      const snapshotPath = path.join(this.state.sessionDir, 'snapshots', `frame_${String(this.frameNumber).padStart(6, '0')}.png`)

      try {
        fs.writeFileSync(snapshotPath, pngBuf)
      } catch {
        // Non-fatal: snapshot persistence failure does not stop recording
      }

      // Collect recent event refs for frame association
      const eventRefs = this.recentGestures
        .filter(g => Math.abs(g.time_ms - nowMs) < 500)
        .map(g => g.event_id)

      this.frameIndexEntries.push({
        frame_number: this.frameNumber,
        timestamp_ms: nowMs,
        relative_time_ms: relativeTimeMs,
        png_path: snapshotPath,
        event_refs: eventRefs
      })
    } finally {
      this.frameCaptureInFlight = false
    }
  }

  private async stopVideoRecording(): Promise<void> {
    this.stopFrameCaptureLoop()

    // Flush frame index to disk
    if (this.state && this.frameIndexEntries.length > 0) {
      try {
        const indexPath = path.join(this.state.sessionDir, 'media', 'frame_index.jsonl')
        const lines = this.frameIndexEntries.map(e => JSON.stringify(e)).join('\n') + '\n'
        fs.writeFileSync(indexPath, lines, 'utf-8')
      } catch {
        // Non-fatal
      }
    }

    if (!this.videoProcess) {
      this.frameIndexEntries = []
      this.videoStartedAtMs = null

      return
    }

    const proc = this.videoProcess
    this.videoProcess = null

    // Close stdin to signal EOF to FFmpeg, then wait for clean exit
    try {
      if (proc.stdin && !proc.stdin.destroyed) {
        proc.stdin.end()
      }
    } catch {
      // ignore
    }

    // Wait up to 5 seconds for graceful exit
    await new Promise<void>(resolve => {
      const timeout = setTimeout(() => {
        try { proc.kill('SIGKILL') } catch { /* ignore */ }
        resolve()
      }, 5000)

      proc.once('exit', () => {
        clearTimeout(timeout)
        resolve()
      })
    })

    // Validate output: file must exist and be non-trivial (> 4KB rules out synthetic stubs)
    if (this.state) {
      try {
        const videoPath = path.join(this.state.sessionDir, 'media', 'recording.webm')

        if (fs.existsSync(videoPath)) {
          const stat = fs.statSync(videoPath)

          if (stat.size < 4096) {
            this.state.videoStatus = 'blocked'
            this.state.lastError = 'video_output_too_small: encoder may have failed'
          }
        } else {
          this.state.videoStatus = 'blocked'
          this.state.lastError = 'video_output_missing'
        }
      } catch {
        // Non-fatal validation failure
      }
    }

    this.frameIndexEntries = []
    this.videoStartedAtMs = null
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
