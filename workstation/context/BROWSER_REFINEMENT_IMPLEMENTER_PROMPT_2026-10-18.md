# Prompt operacional D-049 — implementação real do Browser 80/20

> **INSTRUÇÃO PARA A IA IMPLEMENTADORA: EXECUTE AS ALTERAÇÕES NO REPOSITÓRIO, NÃO SE LIMITE A PLANEJAR.** Leia os contratos indicados por caminho, tome posição crítica fundamentada e implemente a menor solução que satisfaça os gates. Texto criado em 2026-10-18 a partir de leitura estática do \`main@f436e949\`; arquivos e linhas devem ser revalidados no HEAD atual. O código neste documento é proposta, não permissão para substituir código superior.

## 0. Mandato de execução, autonomia crítica e git hygiene

Repositório: \`kevynlucasprofissional-stack/hermes-agent\`.
Decisão canônica: \`workstation/context/DECISIONS.md\` D-049, plano \`workstation/context/BROWSER_REFINEMENT_2026-10-18.md\`, roadmap/journal/intelligence, e as decisões D-042/D-046/D-047/D-048. O plano foi escrito na branch \`docs/browser-observation-80-20-20261018\`; se ainda não tiver sido mesclada, parta dela ou incorpore explicitamente seus docs. A \`main\` auditada era \`f436e9496344d2c38e6611a88b42f0b7f18ce6df\`.

1. Verifique HEAD, status, remotes, submodules, PRs concorrentes, CI exata e diffs. Nunca sobrescreva working tree suja ou alterações de outras IAs; crie branch/worktree isolada para runtime, preserve arquivos não relacionados. Evite merge automático em main.
2. Antes de modificar cada área, consulte **apenas** o trecho do owner/callsite/contrato/teste indicado abaixo e teste seu entendimento. Faça inspeção adicional cirúrgica se uma premissa estiver desatualizada. Não faça leitura indiscriminada do repositório.
3. Mantenha um mini-registro por tarefa: \`proposta original → evidência encontrada → aceitar/adaptar/rejeitar → patch aplicado → testes → status\`. **Não** aceite sugestões minhas quando houver seam mais simples ou owner já existente; **não** faça engenharia especulativa quando a proposta funcionar e os testes forem suficientes.
4. Priorize 80/20: entregue uma fatia vertical segura, com compatibilidade default, sem criar um segundo Browser, SQLite, SessionDB, owner de lease, event bus, runner, transport/SDK, provider router ou mecanismo paralelo de aprendizado.
5. Se o gate exato de CI ou E2E estiver bloqueado por ambiente, **não pare toda a implementação por formalidade**: faça RED/GREEN focado, aplique patches isolados seguros, documente bloqueio e deixe release **HOLD**. Não marque como verde o que não executou. Preserve \`H-079/H-081/H-082\`.
6. Não copie fonte AGPL do BrowserOS; BrowserTrace, Lattice, Stagehand e abundantbeing Extension são MIT, mas reutilize somente código de licença comprovada, com atribuição se necessário. Prefira padrões e implementação própria estreita.

## 1. Mapa exato: o que NÃO recriar

- \`apps/desktop/electron/workstation-browser-runtime.ts\`: \`snapshotForEntry\`, \`resolvePoint\`, \`clickRef\`, \`typeRef\`, \`extractItemsForEntry\`, \`startLearning\`, \`takeControl\`, \`assertAgentControl\`, \`screenshotForEntry\`.
- \`apps/desktop/electron/workstation-browser-snapshot.ts\`: \`AXInventoryElement\`, \`PageInventoryResult\`, AX/DOM fallback.
- \`apps/desktop/electron/workstation-browser-snapshot-diff.ts\`: \`diffSnapshot\` e \`applySnapshotDelta\`; texto + revisão, não grafo; não substituir.
- \`apps/desktop/electron/workstation-browser-extract-cache.ts\`: \`BoundedExtractCache\`, \`computeQueryDigest\`, \`normalizeExtractedItem\` (filtragem \`schema.properties\`, NÃO validator).
- \`apps/desktop/electron/workstation-browser-batch.ts\` e \`workstation-browser-batch-proof.ts\`: executor sequencial autorizado e receipt local; 20 etapas; não escrever segundo executor.
- \`tools/browser_tool.py\`, \`tools/browser_workstation.py\`: schema de ferramentas, routing, \`_force_redact\`, \`project_model_browser_payload\`; preservar comportamento legado.
- \`workstation/browser_projection.py\`, \`workstation/artifacts.py\`, \`workstation/browser_bridge.py\`: extrações duráveis, referência em ArtifactStore e caminho de escrita.
- \`workstation/browser_readiness.py\`, \`workstation/browser_transaction.py\`, \`workstation/execution_policy.py\`: readiness e evidence strength declarada por owner.
- \`workstation/replay.py\`, \`workstation/journal.py\`, \`workstation/telemetry/browser_observation.py\`, \`workstation/telemetry/privacy.py\`: traces e métricas existentes.
- \`apps/desktop/src/app/browser/task-journal-drawer.tsx\`: interface existente para eventos.
- \`workstation/context/browser-automation-v1/STATE.md\`: BAV04 teste de perda de worker Python, não crash Electron real; PR #85 foi merged 13/10.
- CI auditada: workflow \`workstation-ci.yml\`, run \`39154888493\` = failure em \`f436e949\`; investigar logs e comparar com branch/commit atual.

## 2. P0 — duas correções pequenas + gate de qualificação (FAZER PRIMEIRO)

**P0.1 — Path containment RED→GREEN.**
Arquivo \`workstation/browser_bridge.py\`, função \`_validate_safe_destination\` (perto da linha 25) e \`browser_save_json\` (perto da linha 36). Código candidato para substituir SOMENTE a verificação atual:

\`\`\`python
def _validate_safe_destination(
    dest_path: Path, allowed_roots: Optional[list[Path]] = None
) -> Path:
    resolved = dest_path.resolve()
    if allowed_roots:
        roots = [Path(root).resolve() for root in allowed_roots]
        if not any(resolved == root or resolved.is_relative_to(root) for root in roots):
            raise BridgeSecurityError("Destination is outside permitted workspaces")
    return resolved
\`\`\`

Em \`browser_save_json\`, SUBSTITUA este par:
\`\`\`python
dest = Path(destination_path)
_validate_safe_destination(dest, allowed_roots)
\`\`\`
POR:
\`\`\`python
dest = _validate_safe_destination(Path(destination_path), allowed_roots)
\`\`\`

Esse patch elimina a comparação textual por prefixo e assegura que o destino gravado é o validado, **mas não é proteção completa contra troca concorrente de symlinks**; se esse threat model for relevante, implemente operação baseada em file descriptor/directório já aberto e registre decisão. Teste negativo \`workspace-ok2\` vs \`workspace-ok\`, symlink apontando fora, destino válido interno, arquivo existente e caso sem \`allowed_roots\`; verifique o local realmente gravado. Não oculte erros.

**P0.2 — Learning Mode owner exato.**
No \`startLearning(tabId?,sessionId?,rawIntensity?)\` (~linha 2175), o código encontra \`entry\` pela aba pedida, mas \`takeControl(entry.ownerTaskId ?? undefined,...)\` pode inferir a aba ativa quando não há owner. Escreva teste de Electron com duas abas (A ativa, B escolhida sem owner): o lease nunca deve ir para A; ou adote B com owner real validado, ou recuse B fail-closed com erro tipado. Prefira reutilizar \`taskLifecycle().acquireHumanControl\` e \`unboundHumanControlLease\` do owner existente, sem um segundo lease registry e sem dividir perfil de browser indiscriminadamente. Confirme que \`stopLearning/discardLearning\` encerra escopo correto e não deixa lease órfão; se já estiver corrigido na branch atual, apenas teste e registre.

**P0.3 — prova de efeitos e CI.**
Rode baseline do fluxo \`BrowserTransaction\`, \`browser_batch_actions\` e BAV04; examine \`workstation-browser-batch-proof.ts\` e a distinção \`LOCAL_VERIFIED\` vs \`SEMANTIC_PERSISTED_READBACK\`. Para click \`Save\`, exigir verificador independente do estado externo, não apenas atributo DOM/click receipt. Teste timeout pós-dispatch, lease humano, navegação concorrente, processo worker morto, retomada sem duplicação; não proclame crash do Electron validado se só worker Python morreu. Investigue run #39154888493 e identifique se foi infra ou regressão. Se não der executar E2E real, concluir \`NOT RELEASE QUALIFIED\`, sem desativar gates.

## 3. P1-A — contexto econômico e extração tipada (FAZER APÓS P0)

**P1-A.1 — Projeções de snapshot por tarefa, sem regredir default.**
Criar, se não existir equivalente melhor, \`apps/desktop/electron/workstation-browser-snapshot-views.ts\` + \`.test.ts\`, função pura sobre \`PageInventoryResult\` do módulo snapshot. Conectar apenas quando \`args.view\` for explicitamente um de \`summary | action_map | focus | content\`. Sem \`view\`, \`snapshotForEntry()\` deve conservar contrato/shape default. Não mudar refs \`@eN\` nem reinterpretar seleção como autorização. Código candidato INICIAL para views \`action_map\` e \`focus\` (desenvolva \`summary\` e \`content\` com política de redaction abaixo):

\`\`\`typescript
import type { AXInventoryElement, PageInventoryResult } from './workstation-browser-snapshot'

export type SnapshotViewMode = 'action_map' | 'focus'
export interface SnapshotViewResult {
  snapshot: string
  elements: AXInventoryElement[]
  included: number
  omitted: number
  truncated: boolean
}

export function renderSnapshotView(
  inv: PageInventoryResult,
  options: { mode: SnapshotViewMode; maxChars?: number; focusRef?: string }
): SnapshotViewResult {
  const maxChars = Math.min(12000, Math.max(512, Math.floor(options.maxChars ?? 4000)))
  const elements = options.mode === 'focus'
    ? inv.elements.filter(item => item.ref === options.focusRef)
    : inv.elements
  if (options.mode === 'focus' && elements.length !== 1) {
    throw new Error('browser_focus_ref_missing_or_ambiguous')
  }
  const header = ['URL: ' + inv.url, 'Title: ' + inv.title, 'Interactive elements:']
  const parts = [...header]
  let included = 0
  for (const item of elements) {
    const label = (item.label || '').replace(/[\r\n]+/g, ' ').slice(0, 220)
    const line = '- [' + item.ref + '] ' + item.role + ' "' + label + '"'
    if ([...parts, line].join('\n').length > maxChars) break
    parts.push(line)
    included += 1
  }
  const omitted = elements.length - included
  if (options.mode === 'focus' && omitted) throw new Error('browser_focus_budget_too_small')
  return {
    snapshot: parts.join('\n'),
    elements: elements.slice(0, included),
    included, omitted,
    truncated: omitted > 0 || inv.truncated
  }
}
\`\`\`

**Limitações propositais do candidato:** não sanitiza valores/URL no Electron; não cria \`content/summary\`; não altera defaults, não redige prompt injection, não inclui \`semantic_anchor\`. **Avalie e melhore antes de integrar**: executar sanitização existente antes de qualquer retorno ao modelo, incluir \`truncation_report\`, validar \`view\`, \`focusRef\`, budget extremo e conservar indicação de \`wall_detected\`/handoff. Evitar vazar URL de credenciais quando view chegar a outra fronteira. Não mascarar elementos de interação por heurística de artigos.

\`content\` deve extrair seletivamente \`article, main, [role=main]\` na página quando aplicável, com fallback para texto de inventário; só use em leitura/resumo, jamais como substituto do \`action_map\` em navegação. O texto é não confiável, truncado e redigido; não encaminhar HTML nem secrets ao LLM sem saneamento. \`summary\` usa metadata e contagens verificáveis, não inventa fatos.

**Callsites:** \`snapshotForEntry()\` (~linha 3700) recebe \`diffOpts\` e hoje termina em \`formatInventory(inv,full)\` (~3840). Mantenha delta default, e para view opt-in use projection separada (não sobrescrever \`lastSnapshotFrames\` default sem key e identidade adequadas). \`handleControllerAction\` case \`browser_snapshot\` (~2940) recebe \`args.full/delta/baseline_*\`; adicione opção \`view\` no schema de \`tools/browser_tool.py\` e na rota apenas quando necessário. Python \`project_model_browser_payload\` depende da gramática \`Interactive elements:\` para deduplicar; adapte/teste para views sem mudança no default e sem eliminar \`@eN\` utilizáveis.

**P1-A.2 — Sanitização em cadeia.**
Já existem \`tools/browser_workstation.py::_force_redact\` com \`agent.redact.redact_sensitive_text(force=True)\`, \`workstation/telemetry/privacy.py\`, e \`workstation-browser-extract-cache.ts::normalizeExtractedItem\` com filtro para chaves sensíveis. Não clonar sanitizer inteiro. Faça testes com key/provider token/JWT/bearer/private key, credenciais URL encoded, descrição de campo sensível, dados de formulário e prompt injection vindo da página; trace/ArtifactStore/model boundary nunca devem publicar texto secreto por default. O proprietário da extração durável precisa ser auditado: \`workstation/browser_projection.py\` grava \`items\` no ArtifactStore; documente/implemente escopo, retenção e proteção de dados **antes da persistência** se exigido. Tratar conteúdo de páginas como untrusted em prompt/skills; redaction por regex não é garantia universal. Se o transporte modelo já redige mas o ArtifactStore guarda raw por necessidade funcional, exigir autorização, retenção e escopo claros em vez de destruir dados unilateralmente.

**P1-A.3 — JSON Schema REAL (não somente filtro).**
\`workstation-browser-runtime.ts::extractItemsForEntry\` (~linha 4608) chama \`normalizeExtractedItem(item,schema)\` e devolve success=true, mas não valida \`required/type/enum\`. Primeiramente investigar biblioteca já usada/explicitamente instalada para JSON Schema (e.g. Ajv) e contrato de packaging; se ausente, ou adicionar uma dependência pequena e compatível com Electron após teste de pack, ou implementar suporte restrito versionado que **REJEITA** keywords não suportadas em vez de fingir validade. O validator deve ser compilado somente para schema explícito dentro de limite de tamanho/profundidade, rodar depois de normalização e antes de cache, impedir \`cache\` de resposta inválida, reportar \`schema_validation_failed\` com \`path\` e \`keyword\` sanitizados, sem ecoar o valor sensível. Manter modo sem schema idêntico. O \`browser_projection.py\` precisa distinguir \`capture succeeded\`, \`schema valid\` e \`durable write committed\` para impedir \`valid_count\` enganoso. Testar: required ausente, tipo incorreto, enum violado, extração vazia, schema inválido, schema longo, versão não suportada, cache-hit com schema distinto e compact summary sem \`items\` grande.

## 4. P1-B — locator resiliente sem segundo agente (DEPOIS P1-A)

\`resolvePoint\`, \`clickRef\` e \`typeRef\` já aceitam anchors \`testid/name/role/label\` no runtime; \`documentEpoch\`, URL, owner e \`assertAgentControl\` já são rechecados. Avalie resolver stale-ref de modo **somente pré-dispatch**:

1. Com \`@eN\` ausente e \`semantic_anchor\` explícita, permitir recaptura read-only delimitada ao mesmo BrowserTask/tab/docEpoch/host/path family; se anchor identifica 0 ou >1 alvo, não agir.
2. Verifique explicitamente unicidade e actionability antes de \`Input.dispatchMouseEvent\`/keyboard input; revalide lease logo antes do input.
3. Se \`mousePressed\` ou qualquer alteração tiver sido possivelmente disparada, não chamar click de novo, mesmo com erro/timeout de readback; registrar \`UNCERTAIN\` e exigir reconciliação/verificador.
4. Respeitar DOM/AX discrepante, proteção de página sensível, user takeover, mudança SPA; erros com \`WorkstationBrowserError\` ou fault existente sem nova árvore de classes.
5. Teste duas labels iguais, drift correto de testid único, documento mudou entre lookup e dispatch, human takeover entre lookup e dispatch, erro depois de press, batch com etapa incerta e route bound fail-closed.
6. Não adicionar um \`browser_act(instruction)\` autoexecutor livre; novo intent de linguagem natural, se necessário, deve passar por TaskCompiler/operational resolution/owner/approval atuais e minimizar LLM em tarefas já reconhecidas.

## 5. P2 — comparar runs e visualizar falhas somente opt-in

Em \`workstation/replay.py\`, reaproveite \`PortableTrace\`, \`PortableTraceBuilder\` e \`ReplayEngine\` (o último NÃO executa ferramentas). Acrescente função pura \`compare_portable_traces(left, right)\` com primeiro desvio em \`operation_id/phase/status/reason_code\` e fallback explícito quando não há operação correlacionável. Não copie a ordem-posicional ingênua do BrowserTrace sem explicar o limite. Código candidato INICIAL (estenda alinhamento por operation_id, detecção de duplicados, sanitização, campos reais do journal):

\`\`\`python
def compare_portable_traces(left: PortableTrace, right: PortableTrace) -> dict[str, Any]:
    def compact(event: dict[str, Any]) -> dict[str, str]:
        return {
            key: str(event.get(key, ""))[:256]
            for key in ("operation_id", "phase", "status", "reason_code", "action")
        }

    left_events = [compact(event) for event in left.events]
    right_events = [compact(event) for event in right.events]
    for index in range(max(len(left_events), len(right_events))):
        before = left_events[index] if index < len(left_events) else None
        after = right_events[index] if index < len(right_events) else None
        if before != after:
            return {
                "first_divergence": index, "before": before, "after": after,
                "alignment": "ordinal_fallback",
            }
    return {"first_divergence": None, "alignment": "ordinal_fallback"}
\`\`\`

Esse snippet é apenas *baseline de contrato*, não implementação completa de comparação causal; **prefira alinhamento por operation_id** quando houver identidade e nunca exiba dados privados de \`metadata/evidence\` em diff. Se falta \`operation_id\`, resposta tem de declarar \`ordinal_fallback\`. Teste duas runs com etapa inserida, múltiplos eventos por operation_id, redaction, side-effect-free replay, baseline ausente e resultados idênticos.

Para evidência visual de erro, não crie tracer SQLite adicional. O Electron já possui \`screenshotForEntry\`; use referência task-scoped no ArtifactStore com consentimento explícito por sessão e quota/retention; não capture por default, nem injete imagem/prompt nos eventos de telemetria. UI inicialmente pode ser apenas read-only no \`task-journal-drawer.tsx\`. Diagnóstico por LLM e export HTML avançado ficam HOLD.

## 6. Testes, medição e decisão de integração

**Testes focados sugeridos:** \`python -m pytest workstation/tests/test_browser_extract_items.py workstation/tests/test_browser_model_payload_projection.py workstation/tests/test_browser_supervisor.py workstation/tests/test_memory_replay.py -q\` e novo \`test_browser_bridge_security.py\`; Vitest \`apps/desktop/electron/workstation-browser-{snapshot,snapshot-diff,extract-cache,batch,batch-proof,runtime-recovery}.test.ts\` (ver nomes e comando do package no HEAD). Execute também os testes de Learning ownership, journal/owner e rota nativa. O primeiro teste novo de cada caso deve falhar antes do patch (RED) e passar depois (GREEN). Exija \`npm run typecheck\` no desktop e \`git diff --check\`; CI no HEAD exato, e Electron/Windows quando disponíveis.

**Dogfood mínimo:** (A) abrir site/capturar ação sem schema e comparar output default antes/depois; (B) página longa \`action_map\`/form \`focus\` preservando refs; (C) lista extraída com schema válido e inválido, persistida sem leak; (D) 1 SPA com ref stale corrigido antes do input e 1 ref ambíguo recusado; (E) uma mutação externa com readback persistido e timeout incerto sem segundo clique; (F) falha com trace local/sem screenshot, e ativação com consentimento e referência à imagem; (G) Learning com duas abas/owner e usuário retomando controle.

**Métricas:** reportar baseline e variante com a mesma tarefa e versão: \`model_input_tokens\`, \`model_output_tokens\`, \`cache_tokens\`, \`system2_calls\`, \`browser_tool_calls\`, \`snapshot_bytes\`, \`user_to_verified_ms\`, p50/p95, \`uncertain_effects\`, \`duplicate_effects\`, \`human_conflicts\`, \`verification_strength\` e \`cost_usd\` apenas se observados; nunca prometer 76–99% de redução transferindo a medição Lattice.

## 7. Saída e atualizações obrigatórias (NÃO ENCERRAR COM PROPOSTA)

- Código implementado e testes adicionados; branch e commits, diff/PR de implementação sem merge automático em main.
- Atualizar \`workstation/ROADMAP.md\`, \`workstation/context/engineering-journal/CURRENT.md\`, \`workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md\`, \`DECISIONS.md\`, \`CURRENT_STATE.md\`, \`KNOWN_ISSUES.md\` e este handoff com **status real** por gate/commit.
- Relatar tabela \`Gate | Evidência antes | Patch | Teste com comando/resultado | Qualificação | Pendência\`.
- Informar \`IMPLEMENTED/TESTED/RELEASE QUALIFIED\` separadamente; não confundir PR merged com qualificação de produto; corrigir hipóteses minhas invalidas com prova, sem reproduzir arquitetura por obrigação.
- Ao encontrar solução mais simples: usar sem prolongar deliberação; se opção proposta for adequada, implementar diretamente e seguir. A orientação é execução 80/20, não perfeccionismo nem expandir escopo.

**Resultado desejado:** Hermes observa de forma mais relevante e econômica, age no alvo correto com autoridade preservada, não repete mutações incertas, verifica estado externo persistido, diagnostica falhas com evidências locais e entrega artefatos reutilizáveis ao Experience Compiler. Nenhuma promessa de sucesso de produto sem ensaio real.
