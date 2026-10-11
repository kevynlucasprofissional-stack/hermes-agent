# BROW-C2C — Plano de implementação por unidades pequenas (2026-10-10)

**Escopo:** melhorias do Browser derivadas da auditoria externa. **Estado:** documentação e patch-kit apenas; não há runtime habilitado nesta branch. Ler [decisões canônicas](../BROWSER_CODE_TO_CODE_DECISIONS_2026-10-10.md) antes de qualquer mudança. Um implementador deve considerar o SHA real do checkout como fonte de verdade; a main inspecionada em 10/10 foi `f21e803b3525b70ee6be2305e579c1cc1f930e74`.

| Ordem | ID | Dono/arquivos-alvo | Código de referência | Aceitação mínima |
|---|---|---|---|---|
| 0 | BROW-00 | `workstation/context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md`, CI e core seam | nenhum | baseline upstream-qualified e exact-head audit, ou HOLD formal |
| 1 | BROW-01 | `apps/desktop/electron/workstation-browser-runtime.ts`, testes Electron | fixtures existentes | p50/p95, CPU/memória, snapshots/ações, tokens, false claims classificadas |
| 2 | OPT-01 | `executeControlRequest()` + registro de schemas em `tools/browser_workstation.py` / `tools/browser_tool.py`; TaskCompiler/Policy/Kernel | `patch-kit/batch-contract.ts` | batch serial autorizado/receipt por step; stop no primeiro uncertain; zero novos owners |
| 3 | OPT-02 | `snapshotForEntry()` e `inventoryScript()` no runtime; testes nativos | `webContents.debugger`/CDP; referência Agent Browser | AX fallback/flags, sem perda de refs, acessibilidade/canvas/shadow/iframe; benchmark |
| 4 | OPT-03 | `extractItemsForEntry()`, `extractItemsScript()`, `inspectItemsScript()`; `_WORKSTATION_SCHEMA_TOOLS` | `patch-kit/extract-cache.ts` | estender `browser_extract_items` sem ferramenta concorrente; frescor + schema + isolamento |
| 5 | OPT-04 | projeção de `snapshotForEntry()` e client Python | `patch-kit/snapshot-delta.ts` | base compatível, reconstrução exata, fallback, sem alterações de receipt |
| 6 | OPT-06/09/12 | `wc.on('render-process-gone')`, `did-stop-loading`, retries, controller | testes já existentes | recovery e SPA sem repetição, sem troca indevida de task/tab |
| 7 | UX-01 | `apps/desktop/src/app/browser/` e chat right rail | padrão BrowserOS (sem copiar fonte) | UX derivada de owners existentes; takeover/occlusion E2E |
| 8 | OPT-07/11 | `workstation/operational_kernel.py`, rota Browser Python, registry | Driftlock e mapa atual | diagnósticos sem autopromoção; sem remoção de backends sem prova |
| 9 | OPT-05 | fora do caminho crítico | browser-use/desktop como referência | **HOLD** até threat model, consentimento explícito e isolamento perfil/origem; nunca importação automática |
| 10 | BROW-QUAL | suíte Desktop/Windows/pytest/CI, benchmark de resultados verificados | testes de regressão | exato HEAD qualificado + métrica comparativa + rollback flags |

## Fase de implementação — especificação plug-and-play

### OPT-01: novo batch browser

1. Criar `apps/desktop/electron/workstation-browser-batch.ts` a partir do helper original `patch-kit/batch-contract.ts` e testes `patch-kit/batch-contract.test.ts`.
2. Alterar `executeControlRequest()` em `workstation-browser-runtime.ts` **sem desviar da verificação existente**. Adicionar `browser_batch_actions` ao dispatch tipado e ao conjunto de mutações; sem `console`/JS arbitrário no lote.
3. As ações internas devem usar **as funções nativas existentes** `clickRef`, `typeRef`, `pressKey`, `scrollEntry` com validação de identidade e anchor. Não chamar `executeControlRequest()` recursivamente quando isso recriar tasks, grant ou receipts.
4. Para cada subação, resolver TaskRun/task/tab, revalidar lease e política do mesmo owner, emitir receipt com operationId derivado do plano + índice e persistir no proprietário existente. Verificar pós-condição via readback independente; no mínimo exigir a mesma classe de receipt/evidence do single-step, não inventar `verified:true`.
5. Retornar `completed/verified/uncertain/stoppedAt/substepReceipts`. Falha ou efeito incerto cancela restantes. Operações externas não são revertidas automaticamente.
6. Registrar ferramenta de modo consistente em schema, effect taxonomy, policy, Router, Python bridge, journal, testes de ação e docs. H-079 antes de tocar qualquer um desses arquivos.

### OPT-02: AXTree com compatibilidade

1. Criar `apps/desktop/electron/workstation-browser-snapshot.ts`; experimentar leitura de CDP `Accessibility.getFullAXTree` num BrowserTask local seguro.
2. Fazer mapeamento de alvo comprovado: AX node/DOM backend node ↔ `@e` / âncora semântica existente. O ref temporal não pode ser reutilizado após troca de documento. Sem mapeamento verificável, usar caminho anterior ou snapshot híbrido.
3. Controlar `webContents.debugger` por lifecycle e cleanup; evitar sessões concorrentes de debugger e qualquer exposição de CDP ao renderer.
4. Canary/feature flag default-off até resultados. Casos: shadow DOM, iframe, canvas/WebGL, SPA, reader mode, auth wall, redaction e editáveis ricos.
5. Não desabilitar `inventoryScript` antes de equivalência funcional medida.

### OPT-03: ampliar extração já existente

1. Usar `extractItemsForEntry()` e `browser_extract_items` como owners: extensões opcionais de schema/atributos/normalização.
2. Cache via `patch-kit/extract-cache.ts` APENAS quando o chamador oferece fingerprint de documento **revalidado** (URL, profile, task/tab, documentEpoch, contentDigest, mutationRevision e schema/selector). TTL sozinho não prova frescor em SPA.
3. Guardar no máximo uma quantidade limitada de entradas e nunca armazenar payload secreto em disco. Invalidar cache on navigation, mutation, task/control transfer, user actions, auth wall, unexpected content changes.
4. Validar que o resultado atende schema; não inventar sucesso em extração vazia ou parcialmente carregada.

### OPT-04: projeção delta reversível

1. Copiar **código original do patch-kit** `snapshot-delta.ts` para `apps/desktop/electron/workstation-browser-snapshot-diff.ts`; conectar pós-`snapshotForEntry()` sem alterar recibos.
2. Cliente faz opt-in com baseline/versão; em qualquer incompatibilidade de task/tab/url/revision ou truncamento, enviar snapshot completo.
3. Um delta só é enviado se `applySnapshotDelta(previous, delta)` reconstruir exatamente o texto; custo/bytes medidos.
4. Em falha de reconstrução, retry full sem executar novamente a ação externa.

### Resiliência / UX / segurança

- Não adicionar watchdog de crash duplicado: melhorar a resposta aos eventos de renderer já existentes.
- Não adicionar readiness polling paralelo sem antes medir os retries já presentes.
- `BrowserOS` é referência UX, **não fornecedor de código para cópia** nesta fase.
- Importador DPAPI/cookies é **opcional e adiado**; consentimento e threat model explícitos.
- Consolidação de arquivos Python exige mapa de proprietários e semânticas de fallback, jamais mera remoção por nome.

## Gatilhos de regressão P0

1. humano assume durante segunda ação: terceira nunca executa;
2. first step executa efeito mas readback falha: batch UNCERTAIN e stop;
3. navegação em meio ao lote: refs inválidos, abort sem atuar em aba diversa;
4. controller crash após mutação: não duplica side effect durante retry;
5. auth wall, URL insegura ou cross-origin: guardrails existentes;
6. extract cache inválido após modificação SPA sem URL nova;
7. snapshot delta base não existe, versão muda, tab troca, conteúdo truncado;
8. cold boot e restart state; perfil Chromium persistido, sem browser externo silencioso;
9. coabitação de Browser e Laya/CW branches não muda owners;
10. Windows CI / suite de navegador executada no HEAD exato.

## Estratégia de entrega

Unidades separadas por PR e gates, após qualificações. Começar pelo contrato/medição, e implementar OPT-01 → OPT-02 → OPT-03 → OPT-04 com provas e rollbacks. Em nenhum ponto compartilhar tokens/cookies em logs. Não publicar métricas hipotéticas como resultados.
