import { describe, expect, it } from 'vitest'
import { decideLearningQuestion, learningQuestionScore, parseLearningIntensity, type LearningQuestionCandidate, type LearningQuestionContext } from './workstation-learning-question-policy'

const candidate: LearningQuestionCandidate = {
  id: 'c1', dedupeKey: 'effectcraft:duplicate-blur:why', kind: 'causality',
  eventRefs: ['evt-1', 'evt-2'], novelty: 0.9, uncertainty: 0.9,
  reuseValue: 1, interruptionCost: 0.1
}
const context: LearningQuestionContext = {
  intensity: 'intensivo', nowMs: 600_000, recentlyPresentedAtMs: [],
  pendingQueueSize: 0, alreadyAskedKeys: new Set(), userBusy: false, userPausedQuestions: false
}
describe('Hermes Learning Mode question policy (inert)', () => {
  it('never asks without linked evidence', () => {
    expect(decideLearningQuestion({...candidate, eventRefs: []}, context).action).toBe('observe')
  })
  it('clamps malformed confidence inputs', () => {
    expect(learningQuestionScore({...candidate, novelty: Number.NaN})).toBeGreaterThanOrEqual(0)
    expect(learningQuestionScore({...candidate, reuseValue: 100})).toBeLessThanOrEqual(1)
  })
  it('asks on a high-value non-interrupting opportunity', () => {
    expect(decideLearningQuestion(candidate, context).action).toBe('ask')
  })
  it('queues during a drag and does not interrupt editing', () => {
    expect(decideLearningQuestion(candidate, {...context, userBusy: true})).toMatchObject({action: 'queue', reason: 'busy'})
  })
  it('honors deduplication and explicit pause', () => {
    expect(decideLearningQuestion(candidate, {...context, alreadyAskedKeys: new Set([candidate.dedupeKey])}).action).toBe('observe')
    expect(decideLearningQuestion(candidate, {...context, userPausedQuestions: true}).action).toBe('observe')
  })
  it('changes question budget immediately with intensity (same session)', () => {
    const previous = [570_000, 575_000]
    expect(decideLearningQuestion(candidate, {...context, intensity: 'equilibrado', recentlyPresentedAtMs: previous}).action).toBe('queue')
    expect(decideLearningQuestion(candidate, {...context, intensity: 'intensivo', recentlyPresentedAtMs: previous}).action).toBe('ask')
  })
  it('rejects unsupported intensity without silently changing the active session', () => {
    expect(parseLearningIntensity('intensivo')).toBe('intensivo')
    expect(() => parseLearningIntensity('always')).toThrow('unsupported_learning_intensity')
  })
  it('enforces queue bounds and suppresses trivial questions', () => {
    expect(decideLearningQuestion(candidate, {...context, pendingQueueSize: 5})).toMatchObject({action:'observe', reason:'queue_full'})
    expect(decideLearningQuestion({...candidate, novelty:0, uncertainty:0, reuseValue:0}, context)).toMatchObject({action:'observe', reason:'low_information_gain'})
  })
})
