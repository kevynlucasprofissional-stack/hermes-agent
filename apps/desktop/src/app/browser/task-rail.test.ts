import { describe, expect, it } from 'vitest'

import { getTaskExecutionActivity } from './task-rail'
import type { BrowserTask } from './types'

describe('TaskRail Activity Projection', () => {
  const baseTask: BrowserTask = {
    taskId: 'task-1',
    createdAt: '2026-09-18T00:00:00Z',
    updatedAt: '2026-09-18T00:00:00Z',
    panelHost: null,
    controlHost: null,
    sessionHost: 'session-1',
    kanbanCardId: null,
    runId: null,
    localConnection: null,
    status: 'parked',
    leaseState: null,
    parked: true,
    recoveryState: null
  }

  it('projects working activity when session is actively working in $sessionDotStateById even if task is parked', () => {
    const dotStates = { 'session-1': 'working' }
    const sessions = [{ id: 'session-1' }]

    const activity = getTaskExecutionActivity(baseTask, dotStates, sessions)
    expect(activity).toBe('working')
  })

  it('projects working activity when session lineage alias is working in $sessionDotStateById', () => {
    const dotStates = { 'session-alias-live': 'working' }
    const sessions = [{ id: 'session-alias-live', parent_session_id: 'session-1' }]

    const activity = getTaskExecutionActivity(baseTask, dotStates, sessions)
    expect(activity).toBe('working')
  })

  it('projects waiting activity when task is waiting for human or leaseState is waiting', () => {
    const waitingTask: BrowserTask = {
      ...baseTask,
      leaseState: 'waiting'
    }

    const activity = getTaskExecutionActivity(waitingTask, {}, [])
    expect(activity).toBe('waiting')
  })

  it('projects human_control when humanControlLease is active', () => {
    const humanTask: BrowserTask = {
      ...baseTask,
      humanControlLease: {
        owner: 'human',
        taskId: 'task-1',
        sessionId: 'session-1',
        tabId: 'tab-1',
        pageId: 1,
        profileScope: null,
        acquiredAt: '2026-09-18T00:00:00Z',
        expiresAt: '2026-09-18T00:10:00Z',
        renewedAt: null
      }
    }

    const activity = getTaskExecutionActivity(humanTask, {}, [])
    expect(activity).toBe('human_control')
  })

  it('projects idle activity when session is idle and no waiting/human lease exists', () => {
    const dotStates = { 'session-1': 'idle' }
    const sessions = [{ id: 'session-1' }]

    const activity = getTaskExecutionActivity(baseTask, dotStates, sessions)
    expect(activity).toBe('idle')
  })
})
