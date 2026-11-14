import type { HermesPlugin, PluginContext, RouteContribution } from '@hermes/plugin-sdk'
import { ROUTES_AREA } from '@hermes/plugin-sdk'
import { Navigate } from 'react-router'

import { bindApi } from './api'

/** Keep existing Vault storage/API intact; surface its UI inside Workstation. */
const plugin: HermesPlugin = {
  id: 'vault',
  name: 'Hermes Vault',
  description: 'Local-first Markdown knowledge base (Obsidian-compatible) with bidirectional links and graph view',
  defaultEnabled: true,
  register(ctx: PluginContext) {
    bindApi(ctx)
    ctx.register({
      id: 'legacy-vault-route',
      area: ROUTES_AREA,
      data: { path: '/vault' } satisfies RouteContribution,
      render: () => <Navigate replace to="/browser?module=vault" />
    })
  }
}

export default plugin
