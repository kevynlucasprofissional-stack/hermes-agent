import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { LearningControls } from './learning-controls'
import type { LearningSessionState, WorkstationBrowserBridge } from './types'

describe('LearningControls component', () => {
  afterEach(() => {
    cleanup()
  })

  const mockBridge: Partial<WorkstationBrowserBridge> = {
    learningStart: vi.fn().mockResolvedValue({} as any),
    learningStop: vi.fn().mockResolvedValue({} as any),
    learningDiscard: vi.fn().mockResolvedValue(undefined),
    learningSetIntensity: vi.fn().mockResolvedValue({} as any),
    learningAnswerQuestion: vi.fn().mockResolvedValue({} as any)
  }

  it('renders Aprender button when idle and calls onStartLearning on click', () => {
    const onStart = vi.fn()
    render(
      <LearningControls
        activeTabId="tab-1"
        bridge={mockBridge as any}
        learningState={null}
        onStartLearning={onStart}
      />
    )

    const btn = screen.getByRole('button', { name: 'Aprender' })
    expect(btn).toBeDefined()
    fireEvent.click(btn)
    expect(onStart).toHaveBeenCalledOnce()
  })

  it('renders active state with Aprendendo badge, live intensity options and event counts', () => {
    const activeState: LearningSessionState = {
      schema: 'hermes.learning_session.v1',
      sessionId: 'sess-1',
      runtimeSessionId: 'rt-1',
      storedSessionId: 'st-1',
      tabId: 'tab-1',
      webContentsId: 10,
      documentEpoch: 'ep-1',
      status: 'learning',
      intensity: 'intensivo',
      startedAt: new Date().toISOString(),
      endedAt: null,
      allowlistedOrigin: 'https://example.com',
      eventsCount: 7,
      questionsCount: 2,
      pendingQuestions: [],
      videoStatus: 'recording',
      lastError: null,
      sessionDir: '/tmp/learn-1',
      userBusy: false
    }

    render(
      <LearningControls
        activeTabId="tab-1"
        bridge={mockBridge as any}
        learningState={activeState}
      />
    )

    expect(screen.getByText('Aprendendo')).toBeDefined()
    expect(screen.getByText(/Eventos: 7/)).toBeDefined()
    expect(screen.getByRole('button', { name: 'Parar Aprender' })).toBeDefined()

    // Test live intensity change
    const discretoBtn = screen.getByRole('button', { name: 'Discreto' })
    fireEvent.click(discretoBtn)
    expect(mockBridge.learningSetIntensity).toHaveBeenCalledWith('discreto')
  })

  it('renders pending question with hypothesis and handles confirmation', async () => {
    const questionState: LearningSessionState = {
      schema: 'hermes.learning_session.v1',
      sessionId: 'sess-1',
      runtimeSessionId: 'rt-1',
      storedSessionId: 'st-1',
      tabId: 'tab-1',
      webContentsId: 10,
      documentEpoch: 'ep-1',
      status: 'learning',
      intensity: 'intensivo',
      startedAt: new Date().toISOString(),
      endedAt: null,
      allowlistedOrigin: 'https://example.com',
      eventsCount: 3,
      questionsCount: 1,
      pendingQuestions: [
        {
          id: 'q-42',
          sessionId: 'sess-1',
          tabId: 'tab-1',
          eventRefs: ['ev-1'],
          fromMs: 100,
          toMs: 100,
          kind: 'causality',
          category: 'causality',
          hypothesis: 'O operador salvou a versão preliminar.',
          uncertainty: 0.8,
          score: 0.85,
          dedupeKey: 'key-1',
          proposedQuestion: 'Por que você executou o atalho Ctrl+S nesta etapa?',
          state: 'pending',
          needsReinterpretation: false,
          createdAt: new Date().toISOString()
        }
      ],
      videoStatus: 'recording',
      lastError: null,
      sessionDir: '/tmp/learn-1',
      userBusy: false
    }

    render(
      <LearningControls
        activeTabId="tab-1"
        bridge={mockBridge as any}
        learningState={questionState}
      />
    )

    expect(screen.getByText(/O operador salvou a versão preliminar/)).toBeDefined()
    expect(screen.getByText(/Por que você executou o atalho Ctrl\+S/)).toBeDefined()

    const confirmBtn = screen.getByRole('button', { name: 'Confirmar' })
    fireEvent.click(confirmBtn)
    expect(mockBridge.learningAnswerQuestion).toHaveBeenCalledWith('q-42', 'confirm', undefined)
  })

  it('handles user correction with inline input', async () => {
    const questionState: LearningSessionState = {
      schema: 'hermes.learning_session.v1',
      sessionId: 'sess-1',
      runtimeSessionId: 'rt-1',
      storedSessionId: 'st-1',
      tabId: 'tab-1',
      webContentsId: 10,
      documentEpoch: 'ep-1',
      status: 'learning',
      intensity: 'intensivo',
      startedAt: new Date().toISOString(),
      endedAt: null,
      allowlistedOrigin: 'https://example.com',
      eventsCount: 3,
      questionsCount: 1,
      pendingQuestions: [
        {
          id: 'q-43',
          sessionId: 'sess-1',
          tabId: 'tab-1',
          eventRefs: ['ev-1'],
          fromMs: 100,
          toMs: 100,
          kind: 'decision',
          category: 'decision',
          hypothesis: 'Operador selecionou modo rascunho.',
          uncertainty: 0.7,
          score: 0.75,
          dedupeKey: 'key-2',
          proposedQuestion: 'Qual foi o critério para esta seleção?',
          state: 'pending',
          needsReinterpretation: false,
          createdAt: new Date().toISOString()
        }
      ],
      videoStatus: 'recording',
      lastError: null,
      sessionDir: '/tmp/learn-1',
      userBusy: false
    }

    render(
      <LearningControls
        activeTabId="tab-1"
        bridge={mockBridge as any}
        learningState={questionState}
      />
    )

    const correctBtn = screen.getByRole('button', { name: 'Corrigir' })
    fireEvent.click(correctBtn)

    const input = screen.getByPlaceholderText(/Explique o motivo real/)
    fireEvent.change(input, { target: { value: 'Não é modo rascunho, é backup de segurança' } })

    const confirmCorrectionBtn = screen.getByRole('button', { name: 'Confirmar Correção' })
    fireEvent.click(confirmCorrectionBtn)

    expect(mockBridge.learningAnswerQuestion).toHaveBeenCalledWith(
      'q-43',
      'correct',
      'Não é modo rascunho, é backup de segurança'
    )
  })
})
