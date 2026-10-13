import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { CreativeWorkspacePage } from './CreativeWorkspacePage'

describe('Creative Workspace first usable editor', () => {
  it('mounts its own provider and opens an editable project from the empty state', () => {
    render(<CreativeWorkspacePage />)
    expect(screen.getByText('Creative Workspace')).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: 'New project' }))
    expect(screen.getByRole('toolbar', { name: 'Creative toolbar' })).toBeDefined()
    expect(screen.getByRole('button', { name: /Save/ })).toBeDefined()
  })
  it('creates and edits shapes, and undo restores the previous project', () => {
    render(<CreativeWorkspacePage />)
    fireEvent.click(screen.getByRole('button', { name: 'New project' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add rectangle' }))
    expect(screen.getByText('Layer: Rectangle')).toBeDefined()
    expect(screen.getByLabelText('width')).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: 'Undo' }))
    expect(screen.getByText('Select a clip, track, layer, or keyframe to inspect')).toBeDefined()
  })
  it('changes workspace modes and allows adding a text layer', () => {
    render(<CreativeWorkspacePage />)
    fireEvent.click(screen.getByRole('button', { name: 'New project' }))
    fireEvent.change(screen.getByRole('combobox', { name: 'Workspace mode' }), { target: { value: 'motion' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add text' }))
    expect(screen.getByDisplayValue('Your text')).toBeDefined()
    fireEvent.change(screen.getByLabelText('Text'), { target: { value: 'Edited manually' } })
    expect(screen.getByDisplayValue('Edited manually')).toBeDefined()
  })
})
