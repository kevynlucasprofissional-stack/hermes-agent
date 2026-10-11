# PROMPT PARA ANTIGRAVITY — IMPLEMENTAR OTIMIZAÇÕES BROWSER (PLUG-AND-PLAY)

Você é o implementador do Hermes Work no checkout local `C:\Github\hermes-agent`. Recebeu uma auditoria Browser code-to-code e um kit de código no GitHub. **Execute a implementação completa das mudanças aprovadas, fase por fase, sem pedir confirmação entre etapas.** Não substitua os owners canônicos.

## LEITURA OBRIGATÓRIA CURTA (nesta ordem)

1. `workstation/context/BROWSER_CODE_TO_CODE_DECISIONS_2026-10-10.md` — decisões, ressalvas e fatos confrontados com main.
2. `workstation/context/browser-optimization-kit/IMPLEMENTATION_PLAN.md` — ordem e destinos exatos.
3. `workstation/context/browser-optimization-kit/patch-kit/` — código pronto para portar e testes.
4. `workstation/context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md` — gate H-079 (obrigatório antes do runtime).
5. `workstation/context/REFERENCE_CODE_TO_CODE_AUDIT_2026-09-23.md` — evidências.
6. `workstation/ROADMAP.md` e `workstation/context/engineering-journal/CURRENT.md` somente para classificar o estado atual e evitar regressões.

Localize a auditoria detalhada local em `workstation/research/browser-code-to-code-2026-10-10/` e as referências em `referências/02-Browser-Automacao-Web/`, incluindo `BrowserOS-main`, `browserclaw-main`, `openbrowserclaw-master` e Camofox. Se os artefatos locais não estiverem no GitHub, examine-os no disco; não presuma que foram publicados. Verifique licenças/ref do código externo antes de qualquer cópia; **neste plano prefira usar o patch-kit original criado para Hermes**.

## ORDEM INEGOCIÁVEL

**BROW-00: baseline e segurança.** `git status`, branches, `main`, pin upstream, merge-base, CI, H-079/H-080/H-081/H-082. Seguir Stage A upstream-first com pin imutável e testes exigidos. Se o gate bloquear, documente HOLD sem bypass e continue SOMENTE com estudo, testes isolados e tarefas que não alterem runtime. Nunca fazer merges destrutivos ou editar `main` diretamente sem qualificação.

**BROW-01: medição.** Crie fixtures de páginas locais (SPA, editor rico, tabela, formulário, DOM volumoso, shadow DOM, iframe, human takeover). Registre p50/p95 snapshot e ação, CPU/memória, contagem de chamadas, bytes, tokens reais quando disponíveis, sucesso verificado e regressões. Jamais repetir writes contra Trello/Instagram reais para benchmark.

**OPT-01: browser_batch_actions.** Primeiro copiar `patch-kit/batch-contract.ts` para `apps/desktop/electron/workstation-browser-batch.ts`, ajustando somente imports/contratos. Testes `batch-contract.test.ts`. Integrar na função `executeControlRequest()` de `apps/desktop/electron/workstation-browser-runtime.ts`. Utilizar `clickRef/typeRef/pressKey/scrollEntry` existentes. Registrar na ponte `tools/browser_workstation.py`, schema em `tools/browser_tool.py` e owners de admissão/effects/TaskCompiler somente após localizar os símbolos atuais. **Lease + policy + owner recheck antes de CADA step**, receipt real pós-efeito para cada substep, stop ao primeiro `uncertain`; nada de fake success/ACK=VERIFIED, nem código JS arbitrário ou segunda engine. Flag opt-in até E2E.

**OPT-02: snapshot AX.** Criar `apps/desktop/electron/workstation-browser-snapshot.ts` com caminho experimental CDP `Accessibility.getFullAXTree` na main do Electron, lifecycle seguro de debugger e ref/anchor parity. Conectar a `snapshotForEntry()` atrás de flag default-off. Somente substituir `inventoryScript` se todos os E2E funcionarem com referências clicáveis, shadow DOM, iframe, SPA, canvas e post-effects equivalentes. Uma AXTree isolada não prova ref/action; fallback obrigatório.

**OPT-03: extração estruturada.** NÃO criar outro `browser_extract`: já existe `browser_extract_items` em `extractItemsForEntry()`, `inspectItemsScript()` e `_WORKSTATION_SCHEMA_TOOLS`. Estender esquema com projection/normalização/cache condicionados a fingerprint confiável e validação. Adaptar `patch-kit/extract-cache.ts`; nenhum cache persistente de segredo e invalidar ao menor indício de mudança.

**OPT-04: delta.** Copiar `patch-kit/snapshot-delta.ts` para `apps/desktop/electron/workstation-browser-snapshot-diff.ts`, adaptar o contrato de snapshots e ligar como projeção opt-in. Ações continuam gerando receipts canônicos. Delta exige task/tab/url/revision compatíveis; perda de baseline/truncamento => full. O cliente reconstrói e compara sem disparar ação novamente.

**OPT-06/09/12: estabilidade.** Melhore a rotina `wc.on('render-process-gone')`, readiness/hydration e race control que já existem; antes escreva testes RED demonstrando falha real. Eventos de recuperação não podem executar efeitos duplicados.

**UX BrowserOS:** Implementar indicadores discretos de alvo e progresso no Browser Hub e right rail, projetados de BrowserTask/TaskRun. Não copiar código AGPL, não compilar Chromium próprio nem deslocar lógica decisória para extensões. E2E de host fencing, takeover e foreground.

**P2/P3:** Diagnóstico de drift conservador, contabilidade de custo com denominadores observados e classificação dos backends Python. Não auto-repare seletor ou remova fallback sem replay/verificador. Importação de cookies Chrome/DPAPI fica HOLD até aprovação explícita de privacy/security review; sem execução por padrão.

## MODIFICAÇÕES OBRIGATÓRIAS POR ETAPA

Para cada OPT: 1) listar arquivo/símbolo atual; 2) pequeno teste RED; 3) portar código do patch-kit para destino acima; 4) integrar aos owners existentes; 5) testes GREEN/E2E; 6) medir p50/p95 e corretude; 7) atualizar status/receipts no jornal e no roadmap; 8) commit/PR próprio por unidade. Se teste ou baseline falhar, manter implementação isolada/flag off e registrar bloqueio; não afirmar concluído.

## ARQUIVOS IMPORTANTES

- `apps/desktop/electron/workstation-browser-runtime.ts`: `inventoryScript`, `snapshotForEntry`, `executeControlRequest`, `extractItemsForEntry`, `wc.on('render-process-gone')`.
- `apps/desktop/electron/workstation-browser-task.ts`: `BrowserHumanControlLease`, `BrowserOwnerReceipt`, revisão canônica.
- `apps/desktop/electron/workstation-browser-session-state.ts`: persistência e recuperação.
- `tools/browser_workstation.py`: `_WORKSTATION_SCHEMA_TOOLS` e `_dispatch`.
- `tools/browser_tool.py` e demais registry/effects: localizar schemas e semantic routes na branch atual.
- `workstation/operational_kernel.py`, `workstation/experience_compiler/`: manter aprendizagem e verificação, não criar novos owners.
- `apps/desktop/electron/*browser*.test.ts`, `workstation/tests/`: testes focalizados e Windows CI.

## ACEITAÇÃO / RELATÓRIO FINAL

Entregar PRs independentes com código, testes, benchmarking e rollback, sem merge automático. Relatar para cada item: SHA inicial/final, arquivo alterado, contrato, red/green, E2E, p50/p95, custo real, risco residual, licença e status `DONE/PARTIAL/BLOCKED`. Não vender porcentagens do relatório externo como medições. Não concluir com “done” se H-079 ou exact-head CI estiver vermelho. A qualidade e a segurança valem mais do que uma lista longa de funcionalidades nominalmente implementadas.

Comece por BROW-00 agora e continue pelas fases sem novas perguntas.
