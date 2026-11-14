# Hermes Work — P02/Reconciliação: diagnóstico de integração e autoridade (28/10/2026)

**Estado: HOLD de implementação do runtime e de release.** Inspeção e testes isolados executados com Controle Windows; nenhum efeito externo ou alteração do ledger real. Documentação nova independente; nenhum arquivo de terceiros editado.

## Preflight e escopo

- Checkout: `C:\Github\hermes-agent`; `main@f1d5ab2f030e940ed4571371b0de45a21a009c9e`.
- Início: 227 entradas dirty, staging vazio; processos Codex e Electron presentes. Arquivos runtime/session-state já modificados antes desta missão; não sobrescritos.
- `AGENTS.md` e `workstation/AGENTS.md`: coordenador local antigo retirado, coordenação direta de escritores. Gate upstream-first Stage A continua obrigatório para novo patch P02. Existe dispensa específica local registrada para BROW-N2, não uma qualificação técnica/CI nem autorização inequívoca de novo patch P02.
- AI Control autenticado respondeu `aiControl:true` e uma avaliação de metadados do renderer principal; não houve leitura do WebContents WhatsApp nem navegação.

## P0-A: restore inseguro — RED integrado reproduzido

Código corrente `apps/desktop/electron/workstation-browser-runtime.ts::shouldDeferRestoredNavigation` filtra apenas `browser_navigate`. O lote posterior `browser_batch_actions` pendente não participa da decisão de lazy restore.

Reprodutor sintético próprio já preparado em `%TEMP%\hermes-p02-restart-integrated.cjs`, adaptado por cópia para Node 26 em `%TEMP%\hermes-p02-restart-integrated-v2.cjs`. Usa `HERMES_HOME` e `HERMES_WORKSTATION_HOME` temporários, FakeWebContents com contador de `loadURL` e destruição/reconstrução de WorkstationBrowserRuntime, sem abrir URL real. Código do checkout não modificado.

- Fonte original: `RED_EXIT=0`, `P02_INTEGRATED_RED=REPRODUCED`: navegação prévia ACK, lote seguinte pendente, snapshot após restart realiza 1 `loadURL('https://example.test/phase-1')`, e nova mutação é rejeitada por `prior_operation_requires_reconciliation`.
- Modificação de método **somente em memória de teste**: `GREEN_EXIT=0`, `P02_INTEGRATED_GREEN=PASS`: 0 `loadURL(https)`, snapshot `about:blank`, batch permanece pendente, nova mutação permanece bloqueada.
- Fonte derivada com 8 cenários: `SOURCE_DERIVED_CANDIDATE_GREEN=8/8` (somente em memória); conserva isolamento por task/tab/run/session e terminal `NOT_DISPATCHED`. Ainda faltam testes integrados de perfil legado sem runId, concorrência e crash.
- Escopo da prova: Electron sintético com mocks, **não** E2E nativo de Chromium. A função real continua vulnerável no checkout.

## P0-B: bypass de revisão humana — RED integrado reproduzido

O controlador `workstation-browser-runtime.ts::executeControlRequest` recebe `browser_admissions_reconcile` com `operation_id`, `reason`, `evidence`, `evidence_details`, `resolved_by`; valores padrão `OPERATOR_RECONCILED`, `OPERATOR_REVIEW` e `agent`. Esses atributos não autenticam um humano nem provam readback causal.

Reprodutor `%TEMP%\hermes-p02-reconcile-forgery-red.cjs` usa o **mesmo perfil temporário sintético** após admitir um batch incerto; invoca `browser_admissions_reconcile` somente com `{operation_id:'p02-pending-batch'}`.

Saída: `accepted:true`, `terminalKind:'RECONCILED'`, `terminalReason:'OPERATOR_RECONCILED'`, `terminalEvidence:'OPERATOR_REVIEW'`, `resolvedBy:'agent'`. Asserção de segurança desejada `success===false` falha como RED (exit 2 esperado). **Nenhuma admissão real modificada.**

O fluxo de handoff existente (`workstation-browser-pane.tsx` → `hermes_cli/web_server.py` → `plugins/workstation/dashboard/plugin_api.py`) exige token, session e run, implementa single-consume e retorna `readback_required:true, mutation_authorized:false`. Porém a rota de reconciliação do controlador **não** exige uma capacidade de revisão originada deste fluxo. Não equiparar ACK de handoff a terminal de operação.

**Correção ainda não aplicada:** retirar autoridade de reconciliação do canal de ferramentas acessível ao agente (falha fechada). Recuperação humana deve ocorrer por caminho separado, autenticado e vinculado a operação, sessão, run, aba e prova de readback; token/capacidade de uso único não mintável por chamada de agente. Manter `browser_admissions_inspect` read-only e ledger canônico. Exigir RED/GREEN para forja e replay antes de reabilitar mutação.

## Verificações de regressão executadas nesta sessão

- Electron Vitest (8 arquivos de batch/proof/admission/recovery/session-state): **71 PASS / 0 FAIL**, exit 0; warning não fatal de mock Electron `session.fromPath is not a function`.
- Python handoff/prefabs: **29 PASS**, 14 subtests PASS, exit 0.
- Browser Pane UI: **3 PASS**, exit 0; warnings de ambiente localStorage/React act.
- Prova source-derived da correção candidata: **8/8 PASS**; não instalada.
- BROW-N2 baseline anterior desta conversa: 35 Python e TypeScript passaram em verificação anterior, sem modificação atual de runtime. Não confundir com CI/E2E nativo.
- Loop sintético H080B: **26 PASS / 0 FAIL**, exit 0, 29,83 s. Testa loop/persistência com fixtures, não navegador Chromium real.

## Ledger real — leitura agregada estritamente passiva

Snapshot `%LOCALAPPDATA%\HermesWorkstation\Runtime\browser-session.json` (28/10/2026, 15:23:28 local): 260 admissions, 234 `runId=unbound`, 21 pendentes. Operação `op_browser_batch_actions_3d591fa7f8da` presente, sem ACK/terminal; BrowserTask `20261028_112711_256509` permanece `parked`. Essas quantidades são voláteis; não demonstram novas órfãs. **Nunca limpar, reconciliar, reexecutar ou alterar esse ledger sem autorização humana causal.**

## P2 — Reprodutor atual de admissão sem identidade

Em `%TEMP%\hermes-p02-unbound-runid-red.cjs`, um perfil sintético chamou `browser_navigate` sem `task_id`, `session_id` ou `run_id`. O controlador criou a admissão `p02-unbound-no-identity` com `runId='unbound'` e `sessionId='unbound'`. A condição de segurança esperada falhou (`UNBOUND_RED_EXIT=2`). Isto confirma que o controlador ainda pode criar novas admissões com essa identidade; a alcançabilidade por chamadores externos e os fluxos legítimos não-Kanban precisam ser investigados antes da correção. Nenhum efeito externo ou alteração do ledger real ocorreu.

## Matrizes e próximos gates

| Área | Status | Próximo gate |
|---|---|---|
| P01 e BROW-N2 | Implementados localmente, 71/71 Electron | Native E2E específico, não repetir patch |
| P02 restauração | RED integrado reproduzido; GREEN apenas candidato em memória | Stage A/waiver explícito P02 e coordenação de escritor, depois RED integrado no repo e patch mínimo |
| Reconcile autodeclarado | P0 vulnerável, RED integrado sintético | Stage A/waiver e fechamento do endpoint agent-accessible, depois autoridade humana separada |
| Handoff UI/API | Testes 29 Python + 3 UI PASS | Auth real end-to-end; chamada de handoff nunca deve liberar admissão por si |
| WhatsApp real | Não inspecionado, sem envio | Readback semântico em aplicação sintética e E2E nativo isolado |
| Kanban/parked | Em parte mock testado | Testes de restart/TaskRun/parked após patch |
| unbound runId | 234 no ledger real; **novo RED sintético reproduzido no controlador** | Verificar alcançabilidade por chamadores e bloquear antes de efeitos quando faltar identidade válida, sem regredir legítimos não-Kanban |
| Release / Stage A | NÃO QUALIFICADO | pin/upstream/CI exact-head e autorização |

## Restrições cumpridas

Nenhum comando de entrada global, mouse, teclado, foco ou CDP externo; nenhuma mensagem real; nenhuma navegação externa efetiva; nenhuma alteração da operação histórica; nenhum commit, push, branch, worktree, reset, stash ou clean. Os testes de mutação são limitados aos respectivos perfis temporários.

## Continuidade

Handoff obrigatório: obter autorização específica para **P02 + fechamento de autoridade do reconciliador** ou qualificação Stage A. Antes de qualquer alteração, reconferir HEAD/dirty/hash, coordenação com escritores reais, regras atuais. Prioridade: (1) P02 fail-closed restore com RED/GREEN integrado, (2) proibir reconciliação agent-only e substituir por aprovação humana autenticada com readback causal, (3) native E2E sintético, (4) regressões/Stage A. Não tratar testes mockados como correção em produção.

---
## Retomada atual — fechamento das investigações isoladas (2026-10-28)

Status: HOLD de patch do runtime. Mantida a dispensa Stage A anterior restrita à BROW-N2 local; sem qualificação ou nova dispensa expressa P02. Checkout main no HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e, 228 dirty no início, stage vazio. Escritores Codex ativos; não houve coordenação explícita para sobrepor WIP.

O código real continua com as três falhas registradas: restauração de aba após batch incerto, reconciliação por argumentos autodeclarados e novas mutações sem identidade canônica. Não foram editados arquivos de implementação, testes do repo, ledger, credenciais ou interface.

Candidatos de patch avaliados SÓ EM MEMÓRIA em perfis sintéticos temporários:
- P02 restore: %TEMP%\hermes-p02-restart-integrated-v2.cjs — investigação anterior reproduziu carregamento HTTPS implícito após batch pendente; injeção em memória resultou 0 loads externos, about:blank e fence mantido.
- P02 reconciliação: %TEMP%\hermes-p02-reconcile-deny-green.cjs — foi inserida apenas no loader de teste uma rejeição fail-closed de browser_admissions_reconcile no controlador do agente. Resultado atual: denied=true, terminalPresent=false, inspectPending=1, exit 0. NÃO demonstra autorização humana, apenas mitigação da via.
- P02 identidade: %TEMP%\hermes-p02-unbound-deny-green.cjs — guard de preflight mutante injetado apenas na memória. Resultado atual: rejected=true, error=browser_owner_identity_required, admissionExists=false; cenário legítimo legado com task_id explícito permaneceu disponível; P02_ID_GREEN=PASS, exit 0.

Autorização humana: tools/browser_workstation.py expõe browser_admissions_reconcile no catálogo da LLM. O controlador aceita metadata de revisão por parâmetro e a persistência trata enum de evidência como valor, não como autoridade criptográfica. O handoff UI/API autentica sessão/run e informa readback_required=true, mutation_authorized=false; não concede por si capacidade de reconciliação. A correção efetiva exige retirar essa ação do canal LLM e introduzir canal humano distinto, vinculado à operação e prova causal independente, com nonce/consumo único não mintável pelo agente.

Identidade: tools/browser_workstation.py devolve task key default sem task/session; o controlador converte a identidade de admissão para unbound. Candidate guard recusa apenas mutação sem identidade, preservando task_id legado, mas ainda faltam ensaios de todos os chamadores autorizados.

Verificações fresh desta retomada:
- Electron Vitest: 71/71 PASS em 8 arquivos, exit 0 (stderr de mock session.fromPath).
- Python pytest: 64/64 PASS + 14 subtestes em handoffs, prefabs, Browser e WhatsApp sintético, exit 0.
- Renderer UI browser-pane: 3/3 PASS, exit 0 (avisos React act e Node localStorage).
- Electron tsc --noEmit: exit 0.
Essas validações são sobre o checkout corrente, NÃO sobre patches candidatos e NÃO constituem E2E nativo ou release.

Restam: autorização específica P02 ou Stage A qualificado; ownership explícito com escritores; RED tests no framework do repo; aplicação dos patches; autenticidade humana e readback independente; gates nativos/CI; homologação WhatsApp não-mutante; investigação completa de chamadores unbound; build de release. A operação real op_browser_batch_actions_3d591fa7f8da não foi modificada, reconciliada ou reexecutada. Nenhuma mensagem enviada, mouse ou teclado usado, CDP exposto, branches/commits/pushes criados.


### Repetição final dos seis testes sintéticos na retomada

Execução final conjunta, isolada em diretórios temporários, sem escrita no runtime real:
- RESTORE_RED: carregamento HTTPS implícito reproduzido; exit 0 (RED identificado por saída P02_INTEGRATED_RED=REPRODUCED).
- RESTORE_GREEN: nenhum carregamento HTTPS, about:blank, fence preservado; exit 0.
- RECONCILE_RED: falha da asserção esperada por aceitação de OPERATOR_REVIEW fabricado; exit 2.
- RECONCILE_GREEN: acesso de agente negado, terminal inexistente, inspeção permanece disponível; exit 0.
- UNBOUND_RED: falha da asserção esperada por admissão unbound criada; exit 2.
- UNBOUND_GREEN: mutação sem identidade negada, sem admissão; chamada legada com task_id aceita; exit 0.

Vetor de saídas esperado e observado: 0,0,2,0,2,0. Os exits 2 pertencem especificamente aos testes NEGATIVOS que devem falhar antes do patch, não a falhas inesperadas das regressões. O loader foi modificado somente nos scripts temporários. Não converter GREEN de candidato em conclusão de patch instalado.
