import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { CreativeWorkspacePage } from './CreativeWorkspacePage'

describe('Creative Workstation first use', () => {
  it('opens an editable blank project without requiring a JSON file', async () => {
    render(<CreativeWorkspacePage />)
    expect(await screen.findByRole('button', { name: 'Add rectangle' })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Importar assets/i })).toBeTruthy()
    expect(screen.queryByText(/open a previously saved JSON project/i)).toBeNull()
  })

  it('lets the user import local images into the asset shelf without opening a JSON project', async () => {
    const createObjectURL = vi.fn().mockReturnValue('blob:preview-test')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL, revokeObjectURL }))
    render(<CreativeWorkspacePage />)
    const picker = await screen.findByLabelText('Selecionar assets')
    const file = new File(['fake-png'], 'foto.png', { type: 'image/png' })
    fireEvent.change(picker, { target: { files: [file] } })
    expect(await screen.findByText('foto.png')).toBeTruthy()
    expect(screen.getByText(/somente nesta sessão|ainda não.*projeto/i)).toBeTruthy()
    vi.unstubAllGlobals()
  })
})
