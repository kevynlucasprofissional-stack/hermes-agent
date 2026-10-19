# D-049 — Browser Observation & Verified Automation, plano 80/20

## Errata 2026-10-19 — sequência prevalente
A auditoria adversarial substitui a ordem B0–B3 por G0 integração/checkout, G1 verdade schema/WorkItems, G2 views realmente acessíveis e mensuradas; IV drift se houver caso real. O trabalho B0.1/B0.2 já possuía patches/testes locais; preservá-los. Nada de release claim sem CI/readback. [Handoff executável](D049_BROWSER_EXECUTION_80_20_2026-10-19.md).

**Decisão em:** 2026-10-18. **Base estática auditada:** `main@f436e9496344d2c38e6611a88b42f0b7f18ce6df`. **Status:** decisão/handoff documental, sem patch de runtime ou novos testes executados. **Não declarar release** a partir deste documento.

## 1. Intenção, alvo e resultado
Uma única cadeia: `OperationIntent/TaskCompiler/System-1 → BrowserTask + Electron controller → observação sanitizada/escopada → ação autorizada e tipada → readback externo → ExecutionJournal/ArtifactStore → ExperienceCompiler`. Melhorar o contexto oferecido à IA e a resiliência pré-efeito para reduzir reobservação, custo até resultado verificado e depuração manual. Evitar novo navegador, lease owner, event bus, store, executor, roteador de modelos, sistema de traces ou duplicação de competências já existentes.

### Inventário demonstrável na base
| Função | Código atual | Estado |
|---|---|---|
| BrowserTask/controle humano / WebContentsView | `apps/desktop/electron/workstation-browser-runtime.ts`, `workstation-browser-task.ts` | existe; não equivale a E2E transacional certificado |
| Snapshot AX+DOM e refs | `workstation-browser-snapshot.ts`, `workstation-browser-runtime.ts::snapshotForEntry` | AX atrás de flag; fallback DOM; compact 8k chars/120 elementos; full 24k/400 |
| Delta de snapshot | `workstation-browser-snapshot-diff.ts` | delta textual com guardas de identidade, revisão e truncamento; conectado no runtime |
| Cache de extração | `workstation-browser-extract-cache.ts` | 4 segundos/64 entradas; fingerprint, epoch, mutationRevision, digest da query |
| Extração | `workstation-browser-runtime.ts::extractItemsForEntry`, `workstation/browser_projection.py` | `schema.properties` filtra propriedades; **não prova validação completa de JSON Schema** |
| Batch | `workstation-browser-batch.ts`, `workstation-browser-batch-proof.ts`, `tools/browser_tool.py` | max 20 passos; receipt local ≠ persistência externa |
| Privacidade | `tools/browser_workstation.py::_force_redact`, `workstation/telemetry/privacy.py` | sanitize parcial; testar todos os boundaries inclusive ArtifactStore/export |
| Replay / telemetria | `workstation/replay.py`, `workstation/journal.py`, `workstation/telemetry/*` | side-effect-free replay e sink local; não há equivalência full UI BrowserTrace |
| Segurança de escrita | `workstation/browser_bridge.py` | prefixo textual em `_validate_safe_destination` e destino original escrito: corrigir/testar |
| Learning owner | `workstation-browser-runtime.ts::startLearning/takeControl` | suspeita de escopo incorreto em tab não ativa sem task owner; exigir reprodução |

## 2. Sequência com gates independentes
### B0 — P0 Autoridade, segurança, provas reais (primeira sessão, não expandir escopo)
1. Baseline no HEAD da branch implementadora, verificar working tree, upstream stage H-079 e CI exata. Workflow de referência `#39154888493` falhou no HEAD auditado; causa desconhecida. Não presumir verde/erro de produto.
2. TDD `browser_bridge.py`: caminho irmão prefixado, symlink e destino normal dentro da raiz; gravar caminho resolvido validado; se não houver garantia de anti-TOCTOU no modelo atual, documentar e proteger por owner/escopo.
3. TDD Learning em aba não ativa e não associada: lease precisa corresponder exatamente à aba escolhida, ou operação fail-closed; não usar a aba ativa como fallback e não separar perfis indiscriminadamente.
4. Usar fixtures já existentes BAV04 + native Electron para validar `PREPARE→INTERACT→COMMIT→VERIFY` / efeito incerto / no-retry e readback remoto. Anotar evidência limitada; não afirmar real Trello ou crash Electron quando só houver fixture.
**Gate:** 0 re-dispatch em write incerto, nenhum falso receipt persisted, ataques de path rejeitados, lease preservado, testes focados green; CI release apenas no HEAD exato.

### B1 — P1 Projeções por tarefa, redaction e schema (segunda sessão)
1. Adicionar views **opt-in**, geradas do mesmo `PageInventory`: `summary`, `action_map`, `focus`, `content`; default `browser_snapshot` fica byte/shape-compatible. Não alterar `@eN` nem eliminar `elements` úteis à ação.
2. `action_map`: ref/role/label/testid com orçamento; `focus`: subset por ref/anchor e vizinhança limitada, fail-closed quando target não está presente; `content`: heurística opt-in `article/main/[role=main]`, sem remover menu útil no modo de interação; `summary`: título/host, counts e truncation report, sanitizados.
3. Expandir sanitização centralizada antes do modelo e export, incluindo secrets embutidos em strings/URL decoded, sob limites explícitos; evitar armazenar segredo bruto em novos traces.
4. `extract` com schema opcional: validar de fato **após** normalização, rejeitar required/type/enum/array/unknown schema inadequado; distinguir `schema_validation_failed` da falha de captura; não declarar `valid_count` nem `success=True` por filtragem. Se biblioteca JSON Schema ausente, implementar subconjunto identificado e rejeitar keywords não suportadas; evitar dependência pesada no Electron sem necessidade.
**Gate:** snapshot default não regressa; views compactas referenciam alvos existentes; privacidade RED/GREEN; schema falso/ausente rejeitado; latência/tokens reais baseline vs variante, nunca importar % de benchmarks Lattice.

### B2 — P1 Reaquisição semântica estrita antes da mutação (terceira sessão, sequenciar após B1)
1. Reaproveitar `resolvePoint`, `clickRef`, `typeRef`, `BrowserReadinessContract`, `browser_batch_actions`, `documentEpoch`, `mutationRevision`, `assertAgentControl`.
2. Se `@eN` falhou **antes do envio de CDP Input**, resolver somente `testid/name/aria-label/role` e exigir alvo singular, mesmo docEpoch/tab/task, mesma host/path family, lease validada, nova verificação imediatamente pré-despacho. Ambiguidade = handoff/abstenção.
3. Após qualquer possibilidade de efeito emitido: `UNCERTAIN/RECONCILIATION_REQUIRED` e readback independente. Nenhum `retry(act)` cego e nenhuma autopromoção de capability.
**Gate:** DOM drift (target com identidade estável) recuperado; target duplicado e mudança de tab/owner recusados; falha pós-dispatch não clica duas vezes.

### B3 — P2 Forense causal sem novo banco (quarta sessão opcional)
1. Estender `PortableTrace`/`ExecutionJournal` com `compare_runs` determinístico por operation_id+fase+scope quando disponível, fallback de sequência **explicitamente identificado**, primeira divergência e resumo compacto redigido.
2. Reutilizar `screenshotForEntry` somente ao solicitar diagnóstico ou aceitar consentimento explícito por sessão; salvar referência task-scoped no ArtifactStore, com quota/retention e sem anexar bytes/prompt ao transcript ou telemetria.
3. Mostrar primeira divergência em `apps/desktop/src/app/browser/task-journal-drawer.tsx` somente se tiver dados válidos. Não criar banco, servidor, LLM diagnoser automático ou export público contendo PII.
**Gate:** side-effect-free replay, nenhuma captura padrão, nenhum vazamento de token; trace de exemplo aponta etapa divergente com receipt verdadeiro quando existente.

## 3. Adiamentos e economia real
- HOLD: grafo multimodal Lattice integral + sealing RFC8785 + delta estrutural, WebMCP de páginas, SDK multilíngue, SSE dedicado, rota concorrente de providers, auto-healing pós-dispatch, engine BrowserOS/AGPL incorporado, extração/screenshot em toda etapa.
- `76–99%` redução de Lattice usa baseline do **próprio** Lattice; não transferir ao Hermes. Métricas: tokens reais (input/output/cache), chamadas de sistema, tempo `user_to_verified_ms`, p95, bytes de observação, conflitos humanos, `uncertain`, verificações persistidas e custo quando houver rate confiável.
- Segurança: não ignorar D-042 dogfood, D-046 low coupling, D-047 Learning M3 HOLD, D-048 recovery; não sincronizar artifacts privados nem reverter alterações humanas.

## 4. Referências auditadas
- BrowserTrace MIT: https://github.com/aaronlab/browsertrace (tracer/compare; referência forense, não banco paralelo).
- Hermes Browser Extension MIT: https://github.com/abundantbeing/hermes-browser-extension (`content-extractor.js`; companion read-only não descreve controller da extensão v0.3).
- Lattice MIT: https://github.com/apatureai/lattice (`summary/actionMap/focus/patchContext`; benchmark não é do Hermes).
- Stagehand MIT: https://github.com/browserbase/stagehand (`observe/act/extract`, schema Zod, locator; não importar callback batch irrestrito).
- BrowserOS-agent AGPL-3.0: https://github.com/browseros-ai/BrowserOS-agent (somente referência de padrões).
- [Implementer handoff autossuficiente](BROWSER_REFINEMENT_IMPLEMENTER_PROMPT_2026-10-18.md).
