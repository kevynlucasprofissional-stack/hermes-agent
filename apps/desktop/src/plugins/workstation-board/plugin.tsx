import type { HermesPlugin, RouteContribution } from '@hermes/plugin-sdk'
import { ROUTES_AREA } from '@hermes/plugin-sdk'
import { Navigate } from 'react-router'

import { bindBoardApi } from './api'

/** Database is inside Workstation; retain only a redirect for old links. */
const plugin: HermesPlugin = {
  id: 'workstation-board',
  name: 'Workstation Database',
  description: 'Bases próprias do Workstation, com visualizações Kanban e tabela.',
  defaultEnabled: true,
  register(ctx) {
    ctx.onDispose(bindBoardApi(ctx))
    ctx.register({
      id: 'legacy-kanban-link',
      area: ROUTES_AREA,
      data: { path: '/workstation/kanban' } satisfies RouteContribution,
      render: () => <Navigate replace to="/browser?module=database" />
    })
  }
}

export default plugin
