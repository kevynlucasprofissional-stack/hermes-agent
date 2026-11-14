import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { WorkstationHub } from './index'

vi.mock('../browser', () => ({ BrowserView: () => <div data-testid="existing-browser">Ferramentas de navegador</div> }))
vi.mock('@/plugins/workstation-board/board', () => ({
  WorkstationBoardPage: () => <div data-testid="database-module">Database module</div>
}))
vi.mock('@/plugins/vault/vault-page', () => ({
  VaultPage: () => <div data-testid="vault-module">Vault module</div>
}))
vi.mock('../creative-workspace', () => ({
  CreativeWorkspacePage: () => <div data-testid="creative-module">Creative editor</div>
}))

function mount(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<WorkstationHub />} path="/browser" />
      </Routes>
    </MemoryRouter>
  )
}

afterEach(cleanup)

describe('Workstation as the single central dashboard', () => {
  it('opens a dashboard with internal Database and browser tools', async () => {
    mount('/browser')
    expect(screen.getByRole('heading', { name: 'Hermes Workstation' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Seu ambiente de trabalho' })).toBeTruthy()
    expect(screen.queryByTestId('existing-browser')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /Database Bases de tarefas/ }))
    expect(await screen.findByTestId('database-module')).toBeTruthy()
    expect(screen.queryByTestId('existing-browser')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Início' }))
    expect(screen.getByRole('heading', { name: 'Seu ambiente de trabalho' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Navegador Guias/ }))
    expect(await screen.findByTestId('existing-browser')).toBeTruthy()
  })

  it('opens existing browser directly for creative and popout links', async () => {
    mount('/browser?creative=1')
    expect(await screen.findByTestId('existing-browser')).toBeTruthy()
    expect(screen.queryByTestId('database-module')).toBeNull()
  })

  it('supports a direct Database link without adding a second sidebar page', async () => {
    mount('/browser?module=database')
    expect(await screen.findByTestId('database-module')).toBeTruthy()
  })

  it('opens Vault from the dashboard without a separate page', async () => {
    mount('/browser')
    fireEvent.click(screen.getByRole('button', { name: /Vault Notas Markdown/ }))
    expect(await screen.findByTestId('vault-module')).toBeTruthy()
    expect(screen.queryByTestId('existing-browser')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Início' }))
    expect(screen.getByRole('heading', { name: 'Seu ambiente de trabalho' })).toBeTruthy()
  })

  it('supports a direct Vault module link', async () => {
    mount('/browser?module=vault')
    expect(await screen.findByTestId('vault-module')).toBeTruthy()
  })

  it('opens Creative Workstation inside the dashboard without a separate sidebar entry', async () => {
    mount('/browser')
    fireEvent.click(screen.getByRole('button', { name: /Creative Workstation Editor audiovisual/ }))
    expect(await screen.findByTestId('creative-module')).toBeTruthy()
    expect(screen.queryByTestId('existing-browser')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Início' }))
    expect(screen.getByRole('heading', { name: 'Seu ambiente de trabalho' })).toBeTruthy()
  })

  it('opens Creative Workstation via direct Workstation module URL', async () => {
    mount('/browser?module=creative')
    expect(await screen.findByTestId('creative-module')).toBeTruthy()
  })
})
