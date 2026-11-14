# AC-V1 — Patches de integração preparados (REFERÊNCIA; não integrados)

## 1. apps/desktop/electron/ai-control-bridge.ts

Na interface AiControlBridgeOptions, acrescentar:
~~~ts
performOperation?: (request: unknown) => Promise<unknown>
~~~

Reusar o listener HTTP já existente em createAiControlBridge e as verificações de Host, Origin, bearer, token ativo e body máximo. No mesmo handler, permitir POST /operation e validar o JSON ANTES de chamar o código nativo. Substituir apenas a seleção de rota, preservando /evaluate legado até migração AC-3:
~~~ts
const isTyped = req.method === 'POST' && req.url === '/operation'
const isLegacy = req.method === 'POST' && req.url === '/evaluate'
if (!isTyped && !isLegacy) { json(res, 404, {error: 'not_found'}); return }
if (isTyped && !options.performOperation) {
  json(res, 501, {error: 'typed_operations_not_installed'}); return
}
// Dentro do try, após JSON.parse(await readBody(req)):
if (isTyped) {
  const command = validateAiControlOperation(body)
  const result = await options.performOperation!(command)
  if (!active() || token !== newToken) {
    json(res, 403, {error: 'ai_control_disabled'}); return
  }
  json(res, 200, {result}); return
}
~~~

Código TS para validador: adaptar ai-control-operations.mjs (mesma pasta) e testes. Somente validação de shape: NÃO confirma autorização. O P0 final só fecha em AC-3 quando /evaluate arbitrário for removido/desabilitado por padrão. Erros recomendados: 400 schema, 401 auth, 403 revogado, 409 documento/grant stale, 413 tamanho, 503 renderer.

## 2. apps/desktop/electron/main.ts

Na configuração createAiControlBridge (~1964 no snapshot), injetar performOperation que usa APENAS mainWindow.webContents e um serviço trusted de operações. Base para adaptação, desde que variáveis estejam inicializadas:
~~~ts
performOperation: async raw => {
  const command = validateAiControlOperation(raw)
  const wc = mainWindow && !mainWindow.isDestroyed() ? mainWindow.webContents : null
  if (!wc || wc.isDestroyed()) throw new Error('primary_renderer_unavailable')
  if (!aiControlBridge.active()) throw new Error('ai_control_disabled')
  return desktopOperations.execute(wc, command)
},
~~~

desktopOperations deve gerar grantId e documentId no Electron, invalidar em did-navigate/destroyed/toggle off e VERIFICAR token/grant/epoch no limite do efeito. IDs fornecidos pelo cliente não são permissão. Preservar callbacks em app ready, avoiding TDZ e vazamentos. Não entregar guest WebContentsView a esta ponte.

## 3. apps/desktop/electron/ai-control-desktop-actions.ts

Screenshot nativa pode reaproveitar a mesma API capturePage já usada no Browser:
~~~ts
async function captureBoundedPng(wc: Electron.WebContents) {
  if (wc.isDestroyed()) throw new Error('renderer_gone')
  const img = await wc.capturePage()
  const bytes = img.toPNG()
  if (bytes.byteLength > 2 * 1024 * 1024) throw new Error('screenshot_too_large')
  return {mimeType: 'image/png', base64: bytes.toString('base64')}
}
~~~
Limitar e redigir dados sensíveis ANTES de expor imagem; não logar base64. O cursor de um clique deve ser resolvido a partir de locator único e visível, confirmado por elementFromPoint e documento atual, não construído com JS de origem cliente:
~~~ts
wc.sendInputEvent({type: 'mouseMove', x, y})
wc.sendInputEvent({type: 'mouseDown', x, y, button: 'left', clickCount: 1})
wc.sendInputEvent({type: 'mouseUp', x, y, button: 'left', clickCount: 1})
~~~
Consultar tipos Electron reais para coordenadas e foco, aplicar readback; recusar campo password/sensível; nenhuma interação externa irreversível como teste. WaitFor limitada, abortável por revogação/reload. Não alegar que KeyboardEvent sintético ou element.click provam input real.

## 4. apps/desktop/scripts/ai-control-client.mjs

Reusar a função request autenticada já existente:
~~~js
async operation(payload) {
  return (await request('/operation', payload)).result
}
~~~
Criar client.status()/snapshot()/locator(...)/waitFor()/screenshot() sobre ela. Não fabricar documentId/grantId: obtê-los do main e renovar após navegação. Alterar clientes existentes para operações tipadas antes de desligar /evaluate. Preservar CDP manual explícito e sem fallback oculto.

## 5. Testes

AC-1 vitest negative auth/grant/reload/timeout; AC-2 fixture Electron sandbox com click nativo reversível e screenshot; AC-3 Node CLI tests e impedir /evaluate default; AC-4 MCP stdio com cliente real, stdout JSON-RPC apenas, modo off/on/off. Sempre RED->GREEN; node --test no validador de referência 3/3 não valida integração Electron.
