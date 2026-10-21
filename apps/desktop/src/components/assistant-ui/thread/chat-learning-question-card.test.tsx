import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { LearningQuestionItem } from '@/app/browser/types'
import { ChatLearningQuestionCard } from './chat-learning-question-card'

vi.mock('@assistant-ui/react', () => ({
  MessagePrimitive: {
    Root: ({ children, className, ...props }: any) => (
      <div className={className} data-testid="chat-question-root" {...props}>
        {children}
      </div>
    )
  }
}))

describe('ChatLearningQuestionCard', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  const sampleQuestion: LearningQuestionItem = {
    id: 'lq-101',
    sessionId: 'learn-sess-1',
    runtimeSessionId: 'rt-1',
    storedSessionId: 'st-1',
    tabId: 'tab-1',
    eventRefs: ['ev-1', 'ev-2'],
    fromMs: 1200,
    toMs: 1500,
    kind: 'intent',
    category: 'intent',
    hypothesis: 'Operador recortou a imagem para destacar o produto.',
    uncertainty: 0.65,
    score: 0.8,
    dedupeKey: 'key-101',
    proposedQuestion: 'Por que você recortou a camada do produto nesta etapa?',
    state: 'pending',
    needsReinterpretation: false,
    createdAt: new Date().toISOString()
  }

  it('renders question details with hypothesis, uncertainty, and proposed question', () => {
    render(<ChatLearningQuestionCard question={sampleQuestion} />)

    expect(screen.getByText('Modo Aprender')).toBeDefined()
    expect(screen.getByText('intent')).toBeDefined()
    expect(screen.getByText(/Incerteza: 65%/)).toBeDefined()
    expect(screen.getByText(/Operador recortou a imagem para destacar o produto/)).toBeDefined()
    expect(screen.getByText('Por que você recortou a camada do produto nesta etapa?')).toBeDefined()

    expect(screen.getByRole('button', { name: 'Confirmar' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Corrigir' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Adiar' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Dispensar' })).toBeDefined()
  })

  it('handles confirmation via onAnswer callback', async () => {
    const onAnswer = vi.fn()
    render(<ChatLearningQuestionCard onAnswer={onAnswer} question={sampleQuestion} />)

    const confirmBtn = screen.getByRole('button', { name: 'Confirmar' })
    fireEvent.click(confirmBtn)

    expect(onAnswer).toHaveBeenCalledWith('lq-101', 'confirm', undefined)
    expect(screen.getByText('Confirmado pelo usuário')).toBeDefined()
  })

  it('handles inline correction with explanation text', async () => {
    const onAnswer = vi.fn()
    render(<ChatLearningQuestionCard onAnswer={onAnswer} question={sampleQuestion} />)

    const correctBtn = screen.getByRole('button', { name: 'Corrigir' })
    fireEvent.click(correctBtn)

    const input = screen.getByPlaceholderText(/Explique o motivo real ou ajuste correto/)
    expect(input).toBeDefined()

    fireEvent.change(input, { target: { value: 'Removi o fundo para adicionar sombra' } })

    const confirmCorrectionBtn = screen.getByRole('button', { name: 'Confirmar Correção' })
    fireEvent.click(confirmCorrectionBtn)

    expect(onAnswer).toHaveBeenCalledWith('lq-101', 'correct', 'Removi o fundo para adicionar sombra')
    expect(screen.getByText('Corrigido: Removi o fundo para adicionar sombra')).toBeDefined()
  })

  it('handles defer action', async () => {
    const onAnswer = vi.fn()
    render(<ChatLearningQuestionCard onAnswer={onAnswer} question={sampleQuestion} />)

    const deferBtn = screen.getByRole('button', { name: 'Adiar' })
    fireEvent.click(deferBtn)

    expect(onAnswer).toHaveBeenCalledWith('lq-101', 'defer', undefined)
    expect(screen.getByText('Adiado')).toBeDefined()
  })

  it('handles dismiss action', async () => {
    const onAnswer = vi.fn()
    render(<ChatLearningQuestionCard onAnswer={onAnswer} question={sampleQuestion} />)

    const dismissBtn = screen.getByRole('button', { name: 'Dispensar' })
    fireEvent.click(dismissBtn)

    expect(onAnswer).toHaveBeenCalledWith('lq-101', 'dismiss', undefined)
    expect(screen.getByText('Dispensado')).toBeDefined()
  })

  it('renders pre-answered question state cleanly without action buttons', () => {
    const answeredQuestion: LearningQuestionItem = {
      ...sampleQuestion,
      state: 'confirmed',
      userResponse: 'Confirmado pelo usuário'
    }

    render(<ChatLearningQuestionCard question={answeredQuestion} />)

    expect(screen.getByText('Confirmado pelo usuário')).toBeDefined()
    expect(screen.queryByRole('button', { name: 'Confirmar' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Corrigir' })).toBeNull()
  })
})
