# WBR-20261019 — Incidente WhatsApp / Browser nativo: recuperação e inventário auditável

Status: DECISÃO + PLANO DE IMPLEMENTAÇÃO; NENHUM PATCH DE RUNTIME APLICADO NESTE REGISTRO.
Branch de execução: feat/d049-browser-80-20-impl-20261018.
Sessão-base: teste-3-20261019.json, 20261019_004838_e48747, 19/10/2026.
Fontes: quatro auditorias independentes entregues em 19/10, sessão JSON e dois HTMLs WhatsApp capturados em 10/10. HTMLs são fixtures históricas, não snapshot do incidente. Não publicar HTML/JSON originais nem dados pessoais neste repositório público.

## Decisão principal e evidências

1. O primeiro snapshot do WhatsApp mostrava 55 conversas não lidas. Após abertura de chats houve queda para 54/53/52; o relatório posterior de 17 conversas / 190 mensagens não demonstra enumeração completa. O DOM capturado contém somente um subconjunto renderizado da lista virtualizada; o aria-rowcount geral não equivale a total de não lidas.
2. Um browser_click para @e22 retornou stale_or_unknown_ref; browser_snapshot continuou funcionando. Onze mutações posteriores foram barradas por prior_operation_requires_reconciliation, bloqueador op_browser_click_3a895fd7e6a4. Não há evidência de queda global do controller.
3. Na implementação examinada em 19/10, pointScript devolve stale_or_unknown_ref para elemento ausente/desconectado ANTES de scroll, focus ou input. A admission persistente antecede clickRef; o ramo de erro não grava terminal não executado nem receipt de efeito. pendingBrowserMutation bloqueia chamadas seguintes.
4. normalizeWorkstationControllerError não inclui literalmente stale_or_unknown_ref em seu mapa STALE_REF/RESNAPSHOT. Somente adicionar o token não resolve admission pendente.
5. A migração a browser_exec foi uma NOVA CHAMADA explícita do agente e não fallback automático do workstation_routed_browser_handler. Ambos os toolsets podem estar expostos. Compactação ocorreu depois da primeira trava e pode agravar a escolha posterior de ferramentas, mas não explica a primeira stale.
6. Banco SQLite operacional: contagem declarada difere de linhas de mensagens efetivas; houve schema.sql usado como .db, erros ON CONFLICT, database is locked, colunas divergentes e chaves sem proveniência. Não concluir corrupção física nem deduplicar apagando conteúdos semelhantes.
7. Divergência entre laudos: um relatório presume commit de incidente ab40cbbb; outro estima fd80408 por reflog; o build SHA do Electron carregado NÃO foi provado. Registre commit local, remote e build antes de qualquer tentativa de atribuição causal. Alguns laudos recomendam deletar admission: REJEITADO como patch plug-and-play inseguro.

Escopo e coexistência: D-049 G0/G1/G2 da mesma branch permanece aberto ou parcialmente implementado; verificar o HEAD atual e os gates existentes ANTES de qualquer patch para não regredir contrato schema_valid, snapshot views, leases, H-079/H-081/H-082, BAV04. Não criar segundo BrowserRuntime/Controller/DB de autoridade ou modificar One Hermes State.

## Política de segurança e ordenação dos trabalhos

P0A — Rejeição pré-efeito, conclusão terminal durável, normalização STALE_REF. Uma prova interna específica, obtida ANTES de scroll/focus/mouseMoved/press/type/navigation, permite persistir NOT_DISPATCHED. NUNCA interpretar qualquer exceção textual, timeout ou erro geral como ausência de efeito. Admissão deve permanecer como histórico imutável com terminal auditável (não deletar, não fabricar receipt nem acknowledged de sucesso). Falha de gravação mantém fence; crash entre admission e terminal mantém uncertain; repetição de mesmo operationId retorna o terminal persistido; nova tentativa usa novo operationId e snapshot fresco. Bloqueio de post-dispatch/efeito incerto permanece.

P0B — Preservar identidade única de navegador. BrowserTask/TaskRun/aba/lease e backend electron-chromium ficam fixados ao escopo da tarefa. Após controller unavailable/reconciliation_required, agente não pode usar browser_exec, subprocesso Chrome, perfil paralelo, CDP arbitrário nem criar um navegador diferente por iniciativa própria. Autorizar recuperação somente pela rota nativa ou handoff humano. Não confundir bloqueio por admission com controller morto; limitar retries com a mesma operação bloqueadora.

P1A — Inventário WhatsApp somente leitura de negócios: primeiro registrar contagem inicial e percorrer filtro não lidas no painel de lista sem abrir conversas; scroll de viewport local é permitido; clicar chat/mark-as-read, enviar/editar/apagar/arquivar ou manipular perfil é proibido nesta fase. Iterar contêiner real de rolagem do #pane-side, coletar apenas rows montadas a cada janela, seguir até terminal verificado e obter cobertura por duas passagens ou critério equivalente. Guardar contagem de origem, total coletado, evidências e divergência. Nunca tratar (55) WhatsApp como 55 mensagens: é indicador de conversas. Nomes de grupo não são IDs únicos; não inventar chatId; chave temporária com proveniência e estado de ambiguidade.
P1B — Persistência operacional WhatsApp em pasta local privada da ACIRV Notebook: SQLite transacional (não banco de autoridade paralelo do Hermes). Salvar observation_run, conversation_observation, message_observation, task_candidate, outbound_intent (NÃO enviar), relation/provenance, evidência e status. Trello só após aprovação ou política explicitamente autorizada; nenhum disparo a terceiros no MVP. Cargas sem IDs reais -> IDs locais de observação, nunca números WhatsApp fictícios.
P2 — Integração/aceite end-to-end offline com DOMs fixture, ref antiga, página rerender, scroll virtualizado, retomada/replay, import idempotente e relatórios verdadeiros. Depois, dogfood manual somente leitura e ambiente real autorizado. Experience Compiler observa resultados verificados depois de infraestrutura confiável; nenhuma skill substitui guards de código.

## Contratos mínimos / proposta de código (CANDIDATOS; conferir tipos no HEAD)

Em apps/desktop/electron/workstation-browser-runtime.ts, dentro de normalizeWorkstationControllerError (ramo de STALE_REF):
~~~typescript
if (token === 'ref_required' || token === 'element_unavailable' ||
    token === 'browser_tab_destroyed' || token === 'stale_or_unknown_ref') {
  return { ...base, error_code: 'STALE_REF', retryable: true,
    state_changed: true, recommended_action: 'RESNAPSHOT' }
}
~~~
A alteração acima melhora o diagnóstico, MAS NÃO permite liberação de admission sozinha.

Em apps/desktop/electron/workstation-browser-session-state.ts, ESTENDER BrowserMutationAdmission e validateAdmission com contrato terminal restrito. Esboço de tipos:
~~~typescript
type AdmissionTerminal = {
  kind: 'NOT_DISPATCHED'
  reason: 'STALE_OR_UNKNOWN_REF' | 'REF_REQUIRED' | 'AMBIGUOUS_ANCHOR'
  evidence: 'TARGET_RESOLUTION_PRE_PAGE_EFFECT'
  recordedAt: string
}
interface BrowserMutationAdmission {
  // manter todos os campos existentes:
  // operationId, taskId, sessionId, runId, tabId, action, argumentsDigest,
  // acknowledged?
  terminal?: AdmissionTerminal
}
~~~
IMPORTANTE: o esboço da interface indica EXTENSÃO, não substituição da interface real; não remover campos. A razão precisa vir de uma classe/resultado tipado criado no próprio resolvePoint/pointScript, não de catch-all por Error.message. A fase 'pre-page-effect' só inclui pontos onde comprovadamente não ocorreram scroll/focus/dispatch; target_not_actionable é admissível APENAS se caminho e ordem forem verificados e testados. Não tratar target_obscured pós-scroll como pré-efeito.

Persistência proposta: novo método de transição com CAS sob withExclusiveAdmissionLock para operação exata (operationId + taskId + sessionId + runId + tabId + action + argumentsDigest) e terminal fixo NOT_DISPATCHED. Sob o lock, recarregar estado de disco, verificar admission igual e não acknowledged, rejeitar receipt conflitante, gravar por save() e fsyncSync; não permitir reversão do terminal em merges posteriores. pendingBrowserMutation ignora apenas terminal NOT_DISPATCHED gravado sob prova, nunca admissions incertas. Replays de mesmo ID não reexecutam; devolvem resultado persistido + recomendação RESNAPSHOT. Nenhum ACK de efeito externo fabricado.

Em runtime: capturar exceção TIPADA de resolução de alvo antes de entrada em scroll/focus/CDP. Se e só se essa exceção garantir pre-page-effect, persistir terminal pela identidade exata; se a persistência falhar, manter a admission bloqueadora. Propagar erro STALE_REF após persistência. Falhas após scroll/focus/mouseMoved/mousePressed/timeout são UNCERTAIN e não podem ser liberadas automaticamente. Não reordenar o gate de admission sem manter persistência antes de todo efeito.

Testes RED/GREEN indispensáveis:
- stale @eN sem envio de Input.dispatchMouseEvent + terminal durável + segundo clique novo ID admitido;
- erro após scroll/focus e mousePressed -> preserva fence, mesmo após restart;
- fail de fsync/save do terminal -> bloqueio e sem replay;
- operação_id duplicado/collision -> nenhum segundo dispatch;
- dupla janela/duas tasks -> exclusão por escopo e CAS;
- restart/crash antes/depois do terminal, receipt legítimo e replay;
- sem mutações externas na etapa inventário; cobertura parcial não vira complete.

## Estratégia de inventário e privacidade

Adaptador pequeno e desacoplado para WhatsApp Web sobre o Browser nativo. Validar seletor por prioridade: #pane-side, [role=grid] e [role=row], data-testid=cell-frame-container/cell-frame-title/icon-unread-count (somente hints, não garantias de estabilidade). Confirmar contêiner rolável em runtime; HTML estático serve apenas para parsing/fixtures, não prova comportamento JS ao vivo.
Enquadrar cada janela em {taskId, tabId, url, scanRunId, scrollPosition, collectedAt, rowIndex?, displayedName, unreadCount?, evidence}. Deduplicar preferindo identidade autorizada estável provada; caso indisponível, fingerprint local composto + collision flag, SEM declarar identidade remota.
Saída: reported_unread_conversations, observed_unique_conversations, counted_unread_messages, unread_count_unknown, windows_scanned, coverage=('complete'|'partial'|'unstable'), difference, changed_while_scanning, opened_conversations=0, provenance e confidence. Um contador mutável durante varredura requer reconciliar ou marcar unstable. Não inferir 'complete' só porque scroll estacionou uma vez. Evitar transporte de HTML completo, nomes ou conteúdo sensível ao modelo: produzir sumário redigido + referências locais protegidas.
Após inventário e autorização explícita, segunda fase de leitura de chats pode alterar estado lido no WhatsApp; registrar baseline antes de fazê-lo. 'read-only' do usuário significa nenhum envio E nenhuma abertura até snapshot persistido.
Nunca publicar mensagens, HTML, números, tokens, contatos reais nem banco na branch pública. Dados locais sob ACIRV-Notebook, com .gitignore e acesso mínimo conforme autorização do usuário.

## Série ótima: CINCO prompts, entrega independente por etapa

**Prompt 1 / P0A — sincronizar + corrigir deadlock**. A primeira instrução deve rodar no Windows em C:\Github\hermes-agent: verificar branch/status/remotes/worktrees, fetch da branch remota, comparar HEAD e origin, e fazer fast-forward somente se seguro; jamais reset/clean/stash/rebase automático. O objetivo técnico exclusivo é admission terminal pré-efeito + STALE_REF + testes/crash. Corrigir e registrar no mesmo branch, push escopado.

**Prompt 2 / P0B — seleção de ferramentas e recuperação**. Consertar gating de toolsets e afinidade da sessão, contrato ControllerUnavailable vs ReconciliationRequired, sem fallback explícito disfarçado, instruções de agente com budget de retry e testes cross-session/context compaction. Não criar browser adicional.

**Prompt 3 / P1A — inventário DOM**. Construir adaptador incremental read-only de lista virtualizada, extração compacta, cobertura verificável, sem abrir chats. Testar HTML fixture e SPA simulada. Separar 'current unread' de baseline e usar IDs locais.

**Prompt 4 / P1B — SQLite local, proveniência e continuidade**. Reparar projeto ACIRV Notebook por migração forward-only, backup e WAL/busy_timeout, sem editar/commitar dados sensíveis ao repositório público; SQLite não é fonte de verdade de TaskRun. Não integrar envio real; outbound intent é rascunho.

**Prompt 5 / P2 — integração e qualificação**. Validar TaskRun longa, crash/restart, reincidência de stale, cobertura >= número inicial quando estável e sem novas mensagens, reruns idempotentes, nenhum switch de navegador, zero mensagens enviadas, sem read antes da conclusão do inventário. Registrar QUALIFIED somente se testes realmente rodarem. Não dar 'DONE' por teste unit isolado.

## Orientação aos implementadores

Em cada prompt: atualizar HEAD remoto primeiro, ler ESTE arquivo + código dono e testes citados (não ler centenas de documentos), escrever teste RED, patch mínimo, teste GREEN, typecheck/build focado e diff --check; não fazer merge de main, força, limpeza de worktrees ou commit de arquivos não relacionados. Revisar criticamente snippets, adaptar se houver solução melhor preservando invariantes. Publicar somente commits de autoria, registrar antes/depois SHA e comandos/resultados reais e atualizar journal/known issues/roadmap/intelligence com status distinto PLAN, IMPLEMENTED, UNIT_TESTED, CI_QUALIFIED, EXTERNAL_E2E. Divergência ou worktree suja não são autorização para sobrescrever.
