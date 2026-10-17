/**
 * HLM-MVP policy core. Intentionally deterministic and side-effect-free.
 * NO page access, provider calls, dispatch, promotion, credentials, or scheduling here.
 * Wire through the single Electron-main LearningSession owner; do not call this in a renderer
 * as a source of authority. Decisions describe opportunities, not proven knowledge.
 */
export type LearningIntensity = 'discreto' | 'equilibrado' | 'intensivo'
export type LearningQuestionKind =
  | 'intent' | 'causality' | 'decision' | 'heuristic'
  | 'generalization' | 'alternative' | 'validation'

export interface LearningQuestionCandidate {
  id: string
  dedupeKey: string // canonical app+operation+uncertainty fingerprint, not raw page text
  kind: LearningQuestionKind
  eventRefs: readonly string[]
  novelty: number       // normalized [0,1], supplied by a trusted local assessor
  uncertainty: number   // normalized [0,1]
  reuseValue: number    // normalized [0,1]
  interruptionCost: number // normalized [0,1]
}

export interface LearningQuestionContext {
  intensity: LearningIntensity
  nowMs: number // monotonic ms from same Electron process/session
  recentlyPresentedAtMs: readonly number[]
  pendingQueueSize: number
  alreadyAskedKeys: ReadonlySet<string>
  userBusy: boolean  // dragging, drawing, mask editing, active manipulation
  userPausedQuestions: boolean
}

export type LearningQuestionDecision =
  | { action: 'ask'; score: number; reason: 'opportunity' }
  | { action: 'queue'; score: number; reason: 'busy' | 'cooldown' | 'window_budget' }
  | { action: 'observe'; score: number; reason: 'low_information_gain' | 'duplicate' | 'no_evidence' | 'paused' | 'queue_full' }

export const LEARNING_QUESTION_PRESETS: Readonly<Record<LearningIntensity, Readonly<{
  minScore: number
  maxQuestionsPerFiveMinutes: number
  maxPending: number
  cooldownMs: number
}>>> = {
  discreto:   { minScore: 0.82, maxQuestionsPerFiveMinutes: 1, maxPending: 2, cooldownMs: 240_000 },
  equilibrado:{ minScore: 0.69, maxQuestionsPerFiveMinutes: 2, maxPending: 3, cooldownMs: 105_000 },
  intensivo:  { minScore: 0.55, maxQuestionsPerFiveMinutes: 4, maxPending: 5, cooldownMs: 40_000 }
}

const clamp01 = (n: number): number => Number.isFinite(n) ? Math.min(1, Math.max(0, n)) : 0

export function learningQuestionScore(candidate: LearningQuestionCandidate): number {
  // A heuristic to calibrate via genuine operator feedback; NOT an information-theoretic proof.
  return Math.round(1000 * clamp01(
    0.23 * clamp01(candidate.novelty) +
    0.25 * clamp01(candidate.uncertainty) +
    0.52 * clamp01(candidate.reuseValue) -
    0.22 * clamp01(candidate.interruptionCost)
  )) / 1000
}

export function decideLearningQuestion(
  candidate: LearningQuestionCandidate,
  context: LearningQuestionContext
): LearningQuestionDecision {
  const score = learningQuestionScore(candidate)
  if (!candidate.id || !candidate.dedupeKey || !candidate.eventRefs.length) {
    return { action: 'observe', score, reason: 'no_evidence' }
  }
  if (context.userPausedQuestions) {
    return { action: 'observe', score, reason: 'paused' }
  }
  if (context.alreadyAskedKeys.has(candidate.dedupeKey)) {
    return { action: 'observe', score, reason: 'duplicate' }
  }
  const policy = LEARNING_QUESTION_PRESETS[context.intensity]
  if (score < policy.minScore) {
    return { action: 'observe', score, reason: 'low_information_gain' }
  }
  if (context.pendingQueueSize >= policy.maxPending) {
    return { action: 'observe', score, reason: 'queue_full' }
  }
  const recent = context.recentlyPresentedAtMs.filter(
    t => Number.isFinite(t) && t <= context.nowMs && context.nowMs - t < 300_000
  )
  if (context.userBusy) {
    return { action: 'queue', score, reason: 'busy' }
  }
  if (recent.length >= policy.maxQuestionsPerFiveMinutes) {
    return { action: 'queue', score, reason: 'window_budget' }
  }
  const last = recent.length ? Math.max(...recent) : -Infinity
  if (context.nowMs - last < policy.cooldownMs) {
    return { action: 'queue', score, reason: 'cooldown' }
  }
  return { action: 'ask', score, reason: 'opportunity' }
}

/** Intensity is live policy, NEVER a recording restart or a capability authority switch. */
export function parseLearningIntensity(raw: unknown): LearningIntensity {
  if (raw === 'discreto' || raw === 'equilibrado' || raw === 'intensivo') return raw
  throw new Error('unsupported_learning_intensity')
}
