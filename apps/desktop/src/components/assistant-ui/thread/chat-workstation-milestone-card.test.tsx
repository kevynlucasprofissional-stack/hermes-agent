import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { WorkstationMilestone } from '@/app/browser/types'
import { ChatWorkstationMilestoneCard } from './chat-workstation-milestone-card'

vi.mock('@assistant-ui/react', () => ({
  MessagePrimitive: {
    Root: ({ children, className, ...props }: any) => (
      <div className={className} data-testid="chat-milestone-root" {...props}>
        {children}
      </div>
    )
  }
}))

describe('ChatWorkstationMilestoneCard', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('renders candidate milestone with proper badge, capability, and reason', () => {
    const milestone: WorkstationMilestone = {
      eventId: 'ev-1',
      sessionId: 'sess-1',
      stage: 'candidate',
      occurredAt: '2026-10-18T10:00:00Z',
      capabilityId: 'photocraft.layer_crop',
      reasonCode: 'demonstration_segmented',
      evidenceRefs: ['lesson:lesson_hd_1234', 'events:events.jsonl']
    }

    render(<ChatWorkstationMilestoneCard milestone={milestone} />)

    expect(screen.getByText('Candidata identificada')).toBeDefined()
    expect(screen.getByText('photocraft.layer_crop')).toBeDefined()
    expect(screen.getByText('demonstration_segmented')).toBeDefined()
    expect(screen.getByText('Evidências (2)')).toBeDefined()

    // By default evidence details are collapsed
    expect(screen.queryByText('lesson:lesson_hd_1234')).toBeNull()

    // Click toggle to reveal evidence
    fireEvent.click(screen.getByText('Evidências (2)'))
    expect(screen.getByText('lesson:lesson_hd_1234')).toBeDefined()
    expect(screen.getByText('events:events.jsonl')).toBeDefined()
  })

  it('renders validation_failed milestone with refusal style', () => {
    const milestone: WorkstationMilestone = {
      eventId: 'ev-2',
      sessionId: 'sess-1',
      stage: 'validation_failed',
      occurredAt: '2026-10-18T10:05:00Z',
      capabilityId: 'photocraft.layer_crop',
      reasonCode: 'negative_control_failed',
      evidenceRefs: ['evidence:canary_failure.json']
    }

    render(<ChatWorkstationMilestoneCard milestone={milestone} />)

    expect(screen.getByText('Validação recusada')).toBeDefined()
    expect(screen.getByText('negative_control_failed')).toBeDefined()
  })

  it('renders executed milestone with verified readback', () => {
    const milestone: WorkstationMilestone = {
      eventId: 'ev-3',
      sessionId: 'sess-1',
      stage: 'executed',
      occurredAt: '2026-10-18T10:10:00Z',
      capabilityId: 'browser.navigate',
      taskRunId: 'tr-99',
      reasonCode: 'readback_verified',
      evidenceRefs: ['evidence:readback_url_match.json']
    }

    render(<ChatWorkstationMilestoneCard milestone={milestone} />)

    expect(screen.getByText('Capacidade executada')).toBeDefined()
    expect(screen.getByText('tr-99')).toBeDefined()
    expect(screen.getByText('readback_verified')).toBeDefined()
  })

  it('renders capability_selected and compilation_started milestones accurately', () => {
    const selectedMilestone: WorkstationMilestone = {
      eventId: 'ev-4',
      sessionId: 'sess-1',
      stage: 'capability_selected',
      occurredAt: '2026-10-18T10:12:00Z',
      capabilityId: 'layer_manager',
      evidenceRefs: []
    }

    const { rerender } = render(<ChatWorkstationMilestoneCard milestone={selectedMilestone} />)
    expect(screen.getByText('Capacidade selecionada')).toBeDefined()

    const startedMilestone: WorkstationMilestone = {
      eventId: 'ev-5',
      sessionId: 'sess-1',
      stage: 'compilation_started',
      occurredAt: '2026-10-18T10:14:00Z',
      capabilityId: 'layer_manager',
      evidenceRefs: []
    }

    rerender(<ChatWorkstationMilestoneCard milestone={startedMilestone} />)
    expect(screen.getByText('Compilação iniciada')).toBeDefined()
  })
})
