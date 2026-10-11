# BROW-C2C — Decisões de engenharia para otimização do Browser (2026-10-10)

Status: **AUDITORIA RECEBIDA / CONCILIAÇÃO PARCIAL COM MAIN / IMPLEMENTAÇÃO NÃO AUTORIZADA NESTA BRANCH**.

Origem: relatório executivo do Antigravity de 10/10/2026, fornecido pelo usuário; 25 referências declaradas, 49 sessões de dogfood declaradas; aprofundamentos locais em `workstation/research/browser-code-to-code-2026-10-10/` **não encontrados na main remota** no momento deste registro. Os dados locais devem ser importados e conferidos pelo implementador, não tratados como evidência remota. Baseline de leitura: `main@f21e803b3525b70ee6be2305e579c1cc1f930e74`. O relatório local alegava `codex/creative-d043-engine-neutral@56f5758d9b`; essa branch não foi localizada no GitHub consultado. Não misturar SHAs ou versões.

## Decisão D-BROW-01 — Preserve os proprietários canônicos

O Browser principal continua no Electron/Chromium: `apps/desktop/electron/workstation-browser-runtime.ts`, `workstation-browser-task.ts`, `workstation-browser-session-state.ts`. A ponte Python atual é `tools/browser_workstation.py` e o controller é loopback-only. `TaskRun`, `BrowserTask`, autoridade/lease, `BrowserOwnerReceipt`, `OperationalKernel`, `ExperienceCompiler` e registradores de ferramentas mantêm seus papéis. Não adicionar um navegador, backend, broker, gerenciador de sessões ou corpus paralelo. Compatibilidades com Camofox/CDP/extensão devem ser classificadas antes de consolidação.

## Conciliação FACT / PARTIAL / NV

| ID | Evidência no código main atual | Decisão |
|---|---|---|
| OPT-01 batch Browser | `executeControlRequest()` despacha `browser_click/type/press/scroll` individualmente; `workstation.batch_detection` e `DurableBatchRunner` já existem em outras camadas | **ADAPT**, adicionar lote *dentro* do Browser, sem segundo planejador/admission |
| OPT-02 AXTree | `snapshotForEntry()` utiliza `inventoryScript()`; o script percorre DOM e consulta `getComputedStyle`; não há prova de substituição AX equivalente | **EXPERIMENT** via CDP com fallback e preservação da identidade dos refs |
| OPT-03 extração | `browser_extract_items` **já existe** em `executeControlRequest`, `extractItemsForEntry()` e `_WORKSTATION_SCHEMA_TOOLS` | **EXTEND**, não criar concorrente `browser_extract` sem lacuna demonstrada |
| OPT-04 delta | Operações retornam snapshot após atrasos fixos visíveis em `executeControlRequest()` | **ADAPT** como projeção opcional com baseline/revision/URL; manter full para recuperação |
| OPT-06 crash | `wc.on('render-process-gone')` já atualiza `entry.crashed`, recovery, persistência e estado | **HARDEN/TEST**, não instalar outro watchdog |
| OPT-12 SPA | `snapshotForEntry()` já possui retries e checks para canvas/hidratação | **MEASURE/REFACTOR**, não adicionar outro watchdog de SPA cegamente |
| OPT-05 cookie import | Não auditado no Hermes como requisito nem threat model; envolve credenciais/cookies sensíveis | **DEFER SECURITY REVIEW**: opt-in explícito e consentimento por perfil/origem, nunca migração silenciosa |
| OPT-07 drift | Existing drift/quarantine capability boundaries must be preserved | **DIAGNOSE ONLY** antes de qualquer reparo automático |
| OPT-11 route refactor | Cinco arquivos Python não são automaticamente cinco runtimes concorrentes; há ferramentas de compatibilidade e roteamento | **CLASSIFY FIRST**, evitar unificação por contagem de arquivos |
| OPT-09 navigation race | `did-navigate`, `did-navigate-in-page`, `did-stop-loading` e retries existentes | **TEST FIRST**, revisar corrida real |

O relatório menciona ganhos de 70–85%, AX <50 ms, layout thrashing de 300–1200 ms e 481 chamadas de console em uma sessão. Esses números são **alegações da auditoria local**, não resultados reproduzidos nesta revisão. Não apresentá-los como benefícios verificados ou taxa de sucesso no HEAD atual. O mesmo vale para exclusividade mundial/“estado da arte”. O código demonstra contratos importantes, mas não autoriza comparações absolutas sem benchmark independente.

### Licenças

O relatório caracteriza BrowserOS como AGPL-3.0 e BrowserClaw/browser-use/desktop como MIT. **Rever licenças no SHA exato, em cada arquivo, em dependências e no modo de distribuição antes de portar.** AGPL não é proibição universal de leitura ou reimplementação de ideias, mas copiar código para uma base MIT exige avaliação jurídica e compatibilidade de obrigações; **não copiar código do BrowserOS neste plano**. O código do patch-kit é escrito especificamente para Hermes a partir das necessidades de interface; não é transplantado de fonte de terceiros. Reimplementação de comportamento deverá ser independente, sem tradução linha-a-linha de fontes copyleft.

## Prioridade e dependências

**Gate 0 (obrigatório)**: H-079 upstream-first e snapshot exato de main/feature/upstream; H-080A/B, H-081, H-082, Windows/browser CI e status de autorização. Não iniciar runtime patch enquanto baseline não for qualificada ou exceção documentada conforme política.

**Gate 1 (baseline)**: congelar cenários sintéticos/fixtures e 3 sessões reais redigidas; medir latência p50/p95 por snapshot/ação, chamadas, bytes/tokens observáveis, drift, memory footprint, CPU, corretude e receipts. O número de 49 sessões só será adotado após encontrar e validar a fonte local.

**Gate 2 (OPT-01)**: `browser_batch_actions` tipado, serial, até limite explícito, admitido pelo mesmo owner, lease reavaliado ANTES de cada step, receipts individuais pós-efeito, checkpoint e parada em efeito incerto. Não executar JavaScript arbitrário nem continuar após erro. Sem sucesso sintético de plano.

**Gate 3 (OPT-02)**: experimento de snapshots AX via `webContents.debugger`/CDP ou API qualificada, com teste real de identity/action target; se a AXTree não fornecer refs utilizáveis, manter inventário atual ou estratégia híbrida. A leitura AX pode reduzir reflows, mas não garante <50ms.

**Gate 4 (OPT-03)**: melhorar `browser_extract_items` com seleção estruturada/normalização, resultados limitados, esquema tipado, `origin`/BrowserTask/time-box e cache somente após fingerprint DOM/epoch comprovado. Testar mudanças assíncronas e dados sensíveis. Não reutilizar cache stale depois de mutação, navegação, mudança de perfil/tab, challenge/auth wall ou drift.

**Gate 5 (OPT-04)**: delta de snapshot via helper original em `patch-kit/snapshot-delta.ts`; exigir compatibilidade task/tab/url/revision e fornecer modo full por padrão; fallback full ao perder base, ficar truncado ou economizar pouco. Deltas são projeções, não receipt ou verificador.

**Gate 6 (OPT-06/09/12)**: reaproveitar eventos crash/recovery e readiness SPA; testes de crash, troca de abas, delayed hydration, navigation races e human takeover. Trocar delays fixos por waits dirigidos a eventos apenas quando replay e medição comprovarem equivalência.

**Gate 7 (UX BrowserOS)**: indicador visual de alvo e rail/drawer compacto como projeções de TaskRun/BrowserTask sem autoridade; não compilar Chromium customizado nem migrar cérebro para extensão.

**Gate 8 (drift, cost, backends)**: diagnóstico cosmético vs estrutural com quarentena fail-closed; custo com preço versionado e denominador real; revisar backends um a um sem remover fallbacks necessários.

**Gate 9**: benchmark comparativo, exact-head CI, Windows native E2E, segurança/privacidade/licenças, PR pequeno por unidade, rollback simples. Sem merge no main sem qualificação.

## Critérios de aceitação compartilhados

- Não piorar sucesso verificado nem violar `409 USER_CONTROL_ACTIVE`.
- Nenhum `ACK` transforma-se automaticamente em `VERIFIED`; falta de readback é `UNCERTAIN`.
- Identidade `operationId/taskId/runId/BrowserTask/tabId/revision/action/safeUrl` segue os owners e receipts atuais.
- O primeiro erro ou efeito incerto em batch interrompe as operações subsequentes; batch parcial nunca vira sucesso total.
- Browser nativo ligado não muda silenciosamente para backend com outro perfil.
- Eventos de navegação, mutação assíncrona ou perda de baseline invalidam diff/cache.
- Segredos de cookies, tokens e dados pessoais não entram em traces, relatórios ou caches persistidos.
- Benchmarks reportam medido/estimado/NV, p50/p95 e custo por resultado *verificado*, com denominadores.
- Upstream-first antes de qualquer código runtime, e rollback por feature flag.
- Todo resultado é rastreável a arquivo, SHA, teste e execução; listas de “10 melhorias” não são preenchidas artificialmente.

## Artefatos de execução

- [Plano de implementação integrado](browser-optimization-kit/IMPLEMENTATION_PLAN.md).
- [Prompt de execução](browser-optimization-kit/IMPLEMENTER_PROMPT.md).
- `browser-optimization-kit/patch-kit/`: helpers TypeScript originais e testes unitários de referência. **Não estão conectados ao runtime**, portanto não alegar ganho funcional até integração, testes e qualificação.
- Original local do Antigravity: `workstation/research/browser-code-to-code-2026-10-10/` (não disponível remotamente na revisão). Importar como artefatos de auditoria após revisão de segredos e proveniência, sem dar status FACT às hipóteses quantitativas.

As decisões não substituem H-079/H-080 e documentos preexistentes; esta nota é o ponteiro operacional para a próxima fase Browser.
