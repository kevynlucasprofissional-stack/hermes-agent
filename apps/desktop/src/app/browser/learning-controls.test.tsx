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

  it('renders non-intrusive notice when active question exists and no chat session is connected', () => {
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
        sessionId={null}
      />
    )

    expect(screen.getByTestId('learning-no-chat-notice')).toBeDefined()
    expect(screen.getByText(/Por que você executou o atalho Ctrl\+S/)).toBeDefined()

    const confirmBtn = screen.getByRole('button', { name: 'Confirmar' })
    fireEvent.click(confirmBtn)
    expect(mockBridge.learningAnswerQuestion).toHaveBeenCalledWith('q-42', 'confirm', undefined)
  })

  it('does NOT render questions in browser host when chat session is connected', () => {
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
        sessionId="chat-session-123"
      />
    )

    // Should only have Parar Aprender and Descartar, no question card in the browser host
    expect(screen.queryByTestId('learning-no-chat-notice')).toBeNull()
    expect(screen.queryByText(/Por que você executou o atalho Ctrl\+S/)).toBeNull()
  })
})
