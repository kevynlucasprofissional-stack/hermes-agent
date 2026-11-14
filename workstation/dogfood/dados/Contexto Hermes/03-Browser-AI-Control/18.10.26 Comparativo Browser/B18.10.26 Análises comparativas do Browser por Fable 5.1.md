# Análises Comparativas do Browser Nativo Hermes Workstation

> Consolidado de todos os relatórios comparativos gerados por subagentes.
> Cada relatório analisa uma referência externa contra o browser nativo do Hermes Workstation.
> Gerado automaticamente a partir do transcript da sessão.

---

<!-- Relatório 1 -->

# Onde o Hermes Work é PIOR que o Stagehand

| Dimensão | Stagehand | Hermes Work | Gap |
|---|---|---|---|
| **Primitivas de alto nível** | `act(instruction)` com self-healing, `observe()` retorna seletores reais, `extract(schema)` com validação Zod | `browser_controller` expõe operações low-level (click, type, evaluate); agente precisa construir a lógica de ação/observação/extração manualmente | Hermes não tem primitiva equivalente ao `act()` que resolve seletores automaticamente quando o site muda |
| **Schema-validated extraction** | `extract(instruction, zodSchema)` → dados tipados e validados no retorno; schema enviado ao LLM como JSON Schema via `z.toJSONSchema()` | Extração via `evaluate_fn(expression)` + parse manual; sem contrato de schema entre agente e página | Sem garantia estrutural de que dados extraídos conformam a um contrato |
| **Batch commands** | `experimentalBatch(callback)` serializa callback JS, executa múltiplas operações num único round-trip RPC; timeout dual (server-side + client grace) | Cada operação browser é um round-trip separado via HTTP/CDP; N ações = N chamadas | Latência multiplicada em workflows multi-step |
| **WebMCP nativo** | `WebMCPTool` descobre ferramentas MCP declaradas na própria página (`frameId`, `backendNodeId`), invoca via RPC, suporta cancelamento e polling assíncrono | Sem descoberta automática de WebMCP; integração MCP existe apenas no gateway, não no browser controller | Páginas que expõem MCP tools são invisíveis ao agente Hermes |
| **Locator abstraction** | `Locator` com descriptor imutável, métodos chainable (`first()`, `nth()`), operações ricas (`centroid`, `highlight`, `scrollTo`, `selectOption`, `setInputFiles`) | Seletores são strings passadas a cada chamada; sem objeto locator reutilizável ou composável | Agente reconstrói seletores a cada passo; sem caching de resolução |
| **Model Gateway / cheapest-model routing** | SDK aceita `model.generate` callback ou server-side model routing; escolhe modelo mais barato por tipo de ação | Modelo é fixo por sessão/profile; sem roteamento dinâmico por complexidade da ação | Ações simples (click, scroll) gastam tokens do mesmo modelo caro usado para raciocínio complexo |
| **Server-side caching** | `cache: true` em `act()` elimina token spend repetido para ações idênticas; cache no worker side | Sem caching de observações ou ações; cada turno re-observa a página do zero | Token spend redundante em loops de retry ou páginas estáticas |
| **SDK multi-language** | TypeScript, Python, Go com protocolo compartilhado (`stagehand-protocol`) | Apenas Python (controller HTTP) | Barreira para agentes/tools escritos em outras linguagens |

## Onde o Hermes Work é MELHOR que o Stagehand

| Dimensão | Hermes Work | Stagehand | Vantagem |
|---|---|---|---|
| **Durable execution & transaction contracts** | `BrowserReadinessContract` com `required_semantic_targets`, `entity_identity`, `require_hydration`; avaliação determinística de readiness antes de prosseguir | Sem contratos de transação; `act()` confia no LLM para decidir quando a página está pronta | Hermes garante semanticamente que a página atingiu o estado esperado antes de agir |
| **Supervisor com circuit breaker** | `BrowserRuntimeSupervisor` com classificação de erros tipados (`PROCESS_DEAD`, `DESCRIPTOR_STALE`, `AUTH_MISMATCH`), backoff exponencial, limpeza automática de descriptors stale | Inicialização falha → exceção; sem supervisão contínua, sem circuit breaker, sem reclassificação de erros | Resiliência operacional superior em sessões longas |
| **Segurança de contexto (BCP v2)** | Consume-on-read, TTL 5s, owner-scoped cache, redação de secrets (11 padrões regex), element picker com Shadow DOM overlay | `observe()` retorna seletores mas credenciais podem vazar no contexto se o LLM as solicitar; sem redação automática | Hermes previne vazamento de credenciais por design |
| **Bridge direto para ArtifactStore** | `browser_capture_to_artifact()` extrai dados da página direto para filesystem/artifact store sem passar por base64/chat context | Dados extraídos via `extract()` voltam ao SDK como JSON in-memory; persistência é responsabilidade do caller | Zero-copy pipeline evita inflar o contexto do LLM com payloads grandes |
| **Readiness probes semânticos** | `build_readiness_expression()` gera probe JS auto-contido com `selector_found`, `all_text_found`, `any_text_found`, `min_text_length`; polling com diagnóstico estruturado | `waitForSelector` básico; sem composição de condições semânticas | Hermes substitui `sleep(5)` por condições observáveis compostas |
| **Profile isolation & scope binding** | Cada operação browser é escopada a um profile explícito; código fora de turno (boot probes, eviction, tickers) binda escopo explicitamente | Single-process, single-context; sem isolamento de profile | Multi-profile seguro por construção |
| **Privacy-by-design telemetry** | Telemetria opt-in; loopback-only controllers; sem outbound telemetry padrão | Cloud-hosted option envia dados ao Browserbase; local mode ainda depende de CDP direto | Controle total sobre dados que saem da máquina |
| **Semantic readiness classification** | `browser_diagnostic()` classifica falhas como `AUTH_REQUIRED`, `DOM_DRIFT`, `HYDRATION_PENDING`, `CANVAS_OR_NON_DOM_SURFACE` | Erros são genéricos (timeout, selector not found); sem classificação semântica | Agente pode tomar decisões diferentes por tipo de falha |

## Código Copiável Diretamente

### 1. Padrão de Batch Callback Serialization (`batch.ts`)
O mecanismo de serializar callbacks JS via `Function.prototype.toString()` + validação contra native functions é diretamente portável:

```typescript
// Conceito adaptável para Python/Hermes:
const callbackSource = Function.prototype.toString.call(callback);
if (nativeFunctionSourcePattern.test(callbackSource)) {
  throw new TypeError("callback must be serializable JavaScript");
}
```

**Aplicação Hermes:** Implementar `browser_batch(actions: list[dict])` que serializa uma sequência de operações browser num único payload, reduzindo round-trips. O pattern de dual-timeout (server deadline + client grace) é essencial.

### 2. Locator Descriptor Imutável (`locator.ts`)
O `LocatorDescriptor` como objeto serializável com `nth()`, `first()` chainable:

```python
# Adaptação direta para Hermes:
@dataclass(frozen=True)
class BrowserLocator:
    selector: str
    frame_id: str | None = None
    nth: int = 0
    
    def first(self) -> BrowserLocator:
        return replace(self, nth=0)
    
    def nth(self, index: int) -> BrowserLocator:
        return replace(self, nth=index)
```

### 3. WebMCP Tool Discovery (`webmcp.ts`)
O pattern de descobrir ferramentas MCP declaradas na página via `frameId` + `backendNodeId` e invocá-las assincronicamente com cancelamento:

**Aplicação Hermes:** Adicionar `browser_discover_webmcp()` ao controller que enumera tools MCP expostas pela página atual, retornando descriptors que o agente pode invocar via `browser_invoke_webmcp(tool_name, input)`.

### 4. Schema-to-JSON-Schema Bridge (`stagehand.ts:299`)
```typescript
{ schema: z.json().parse(z.toJSONSchema(resolvedSchema)) }
```
Enviar o schema como JSON Schema ao LLM em vez de texto livre. **Aplicação Hermes:** Quando o agente define um Pydantic model para extração, converter para JSON Schema e injetar no prompt de observação.

## Código Adaptável

### 1. Self-Healing Act → Readiness-Aware Action
Stagehand's `act(instruction)` usa LLM para resolver seletores. Hermes já tem `BrowserReadinessContract`. **Adaptação:** Criar `browser_act_with_contract(instruction, contract)` que:
1. Usa LLM para propor seletor a partir da instrução
2. Avalia `contract.evaluate(observation)` antes de executar
3. Se contrato falha com `DOM_DRIFT`, re-observa e re-resolve seletor automaticamente
4. Só executa quando contrato retorna `ready: True`

Isso combina o self-healing do Stagehand com a garantia semântica do Hermes.

### 2. Hybrid AX Trimming → Budgeted Observation
Stagehand trimma a accessibility tree hibridamente. Lattice provou 76-99% de redução com budgeted views. **Adaptação:** Implementar `browser_observe_budget(max_nodes, focus_selectors)` que:
1. Captura AX tree completa via CDP
2. Aplica trimming baseado em foco (elementos visíveis + interativos + dentro dos seletores de interesse)
3. Retorna apenas nós relevantes com proveniência

Combina com o `BrowserReadinessContract.required_semantic_targets` como filtro natural.

### 3. Model Routing por Complexidade de Ação
Stagehand's Model Gateway escolhe modelo por ação. **Adaptação:** Classificar ações browser em tiers:
- **Tier 0** (click, scroll, hover): Haiku/Sonnet pequeno
- **Tier 1** (type, fill, select): Sonnet
- **Tier 2** (observe, extract com schema): modelo da sessão
- **Tier 3** (act com self-healing): Opus/Fable

Implementar como middleware no `browser_controller` que intercepta a chamada e rota para o tier apropriado.

## Oportunidades de Token Economy

| Oportunidade | Impacto Estimado | Esforço | Fonte |
|---|---|---|---|
| **Budgeted AX observation** | 76-99% redução em observações | Médio | Lattice + Stagehand hybrid trimming |
| **Server-side action caching** | Elimina 100% de tokens em retries idênticos | Baixo | Stagehand `cache: true` |
| **Batch round-trip consolidation** | Reduz N chamadas para 1; menos overhead de sistema | Médio | Stagehand `experimentalBatch` |
| **Schema-driven extraction** | Menos tokens de prompt (JSON Schema vs instruções verbosas) + zero retries por formato errado | Baixo | Stagehand `extract(schema)` |
| **Delta encoding entre observações** | 94-97% redução em re-observações consecutivas | Alto | Lattice `encodeUiGraphDelta` |
| **Content-addressed snapshot identity** | Deduplicação de snapshots idênticos across turns | Médio | Lattice SHA-256 canonical hashing |

## Oportunidades de Velocidade

| Oportunidade | Impacto Estimado | Esforço | Fonte |
|---|---|---|---|
| **Batch operations** | N operações em 1 round-trip (latência ÷ N) | Médio | Stagehand `experimentalBatch` |
| **Locator caching** | Evita re-resolução de seletores em páginas estáveis | Baixo | Stagehand `Locator` descriptor |
| **Stability probe antes de captura** | 250ms probe evita capturar página em transição → menos retries | Baixo | Lattice `capture.ts` stability probe |
| **WebMCP invocation direta** | Bypass LLM para operações que a página já expõe como tool | Médio | Stagehand `WebMCPTool.invoke()` |
| **Parallel frame observation** | Observar múltiplos frames/iframes concorrentemente | Médio | Stagehand frame-aware architecture |

## Oportunidades de Objetividade da IA

| Oportunidade | Impacto | Esforço | Fonte |
|---|---|---|---|
| **`observe()` retorna seletores reais, não coordenadas** | Elimina alucinação de posições; agente age sobre referências verificáveis | Médio | Stagehand `observe()` |
| **Schema-validated extraction** | Dados extraídos conformam contrato; LLM não inventa campos | Baixo | Stagehand `extract(zodSchema)` |
| **Readiness contract como gate objetivo** | Decisão de prosseguir é determinística (não depende de "parece pronto") | Já existe | Hermes `BrowserReadinessContract` |
| **Diagnostic classification estruturada** | Falhas classificadas por tipo (`DOM_DRIFT`, `AUTH_REQUIRED`) → agente toma decisão correta | Já existe | Hermes `browser_diagnostic()` |
| **Content-addressed identity** | Snapshots idênticos têm hash idêntico; agente sabe objetivamente que nada mudou | Médio | Lattice canonical hashing |

## Resumo Executivo e Recomendações Prioritárias

1. **Implementar `browser_act_with_contract()`** — Combina self-healing do Stagehand com readiness contracts do Hermes. É a melhoria de maior impacto porque une as duas maiores vantagens competitivas de cada sistema. Esforço médio, impacto alto em confiabilidade.

2. **Adicionar `BrowserLocator` imutável** — Copiar o pattern de descriptor serializável do Stagehand. Elimina reconstrução de seletores, habilita caching, e prepara terreno para batch operations. Esforço baixo, impacto médio-alto.

3. **Implementar budgeted AX observation** — Combinar hybrid trimming do Stagehand com budgeted views do Lattice. Redução de 76-99% em tokens de observação é o maior ganho de token economy disponível. Esforço médio.

4. **Adicionar WebMCP discovery ao controller** — Portar o pattern de `WebMCPTool` do Stagehand. Páginas que expõem MCP tools tornam-se automaticamente operáveis sem LLM intermediário. Esforço médio, impacto alto em velocidade e objetividade.

5. **Batch operations com dual-timeout** — Portar `experimentalBatch` do Stagehand adaptado para Python. Reduz latência em workflows multi-step de forma linear. Esforço médio.

6. **Schema-to-JSON-Schema bridge para extract** — Quando agente define Pydantic model, converter e injetar como JSON Schema no prompt. Elimina retries por formato errado e reduz tokens de instrução. Esforço baixo.

---

<!-- Relatório 2 -->

# Relatório Comparativo: Browser Nativo Hermes Workstation vs. DriftLock (VasuBansal7576)
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (DriftLock) | Hermes Work | Gap Específico |
  |---|---|---|---|
  | **Registro de Interações com Git** | `recordInteraction()` em `driftlock/lib/record.mjs` grava cada interação como fixture JSON + log JSONL + commit git automático com SHA pai/filho, criando trilha de auditoria imutável por interação. | `tools/browser_workstation.py` grava journal via `_record_browser_controller_outcome()` mas sem commit git por interação; journal é projeção volátil no controller Electron. | Hermes não tem trilha de auditoria imutável por interação individual; se o controller reiniciar, o histórico de interações pode ser perdido ou ficar inconsistente. |
  | **Hashing Visual/DOM por Elemento-Alvo** | `targetSnapshot()` em `driftlock/lib/browser.mjs:46-61` captura outerHTML normalizado + screenshot do elemento-alvo ANTES da ação, gera `domHash` e `visualHash` separados por interação. | `browser_readiness.py` verifica condições semânticas (selector, texto, min_text_length) mas não gera hash visual/DOM por elemento-alvo antes/depois de cada ação. | Hermes não detecta drift visual silencioso em elementos específicos; readiness é binário (ready/not-ready), não mede magnitude de mudança. |
  | **Fixture Replay / Known-Good Tags** | Protocolo definido em `driftlock/protocol/known-good-tag.schema.json` e `interaction-log.schema.json` permite marcar interações como "known-good" e revalidar automaticamente contra fixtures gravadas. | Não existe mecanismo equivalente de fixture replay ou known-good tags no browser nativo do Hermes. | Hermes não pode revalidar que uma automação continua funcionando após mudanças de UI sem re-executar manualmente. |
  | **Classificação de Drift Estruturada** | `driftlock/protocol/drift-classification.md` define vocabulário padronizado (internal/external/inconclusive) e verdicts estruturados (`drift-verdict.schema.json`). | `browser_supervisor.py:classify_error()` classifica erros de conexão/processo (TIMEOUT, CONNECTION_REFUSED, AUTH_MISMATCH) mas não classifica drift de conteúdo/página. | Hermes distingue falhas de infraestrutura mas não distingue "a página mudou" de "a ação falhou", tratando ambas como erro genérico. |
  | **Skill-Version Binding por Interação** | `record.mjs:22-23` vincula cada interação ao `skill_version_ref` (git commit do skill), permitindo correlacionar regressões a versões específicas de skills. | Journal do Hermes registra `operation_id` e `run_id` mas não vincula a versão do skill/receita que originou a ação. | Regressões em skills browser não são rastreadas até a versão causadora no Hermes. |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (DriftLock) | Vantagem Específica |
  |---|---|---|---|
  | **Supervisão Ativa com Circuit Breaker** | `BrowserRuntimeSupervisor` em `browser_supervisor.py:63-302` implementa circuit breaker (CLOSED/OPEN/HALF_OPEN), backoff exponencial, classificação tipada de erros e limpeza automática de descriptors stale. | DriftLock usa try/catch simples em `browser.mjs:89-142`; sem circuit breaker, sem backoff, sem classificação tipada de erros. | Hermes sobrevive a falhas transitórias do controller sem inundar o modelo com erros repetidos; DriftLock falha imediatamente. |
  | **Readiness Semântica Observável** | `browser_readiness.py:19-127` substitui `sleep(5)` por sondas JS configuráveis (selector, all_text, any_text, min_text_length) com polling e timeout explícito. | DriftLock usa `waitUntil: "domcontentloaded"` fixo em `browser.mjs:71`; sem verificação semântica pós-navegação. | Hermes espera a página estar semanticamente pronta, não apenas carregada; evita ações prematuras em SPAs. |
  | **Bridge Direto para ArtifactStore** | `browser_bridge.py:36-121` extrai dados do DOM direto para filesystem ou ArtifactStore sem passar por base64/chat context, com validação de segurança de caminho. | DriftLock salva fixtures localmente em `memory/interactions/fixtures/`; sem integração com store de artefatos estruturado. | Hermes evita inflar o contexto do modelo com dados extraídos; dados vão direto para referência estruturada. |
  | **Segurança Loopback + Auth Bearer** | `browser_workstation.py:367-371` valida loopback-only + bearer token no descriptor; `_force_redact()` remove dados sensíveis antes de cruzar o boundary do tool. | DriftLock lança Playwright headless/headed sem autenticação; `browser.mjs:40` aceita qualquer configuração. | Hermes previne acesso não-autorizado ao controller e vazamento de dados sensíveis para o modelo. |
  | **Binding de Task/Session Anti-Failover** | `_bind()`, `_canonical_browser_task_binding()` e `workstation_route_is_bound()` em `browser_workstation.py:203-345` garantem que task vinculada nunca migra silenciosamente para outro browser. | DriftLock é stateless por design; cada `runComputerUse()` cria nova página se necessário (`browser.mjs:37-44`). | Hermes mantém identidade de sessão/auth através de reconnects; DriftLock perde estado entre chamadas. |
  | **Projeção Model-Facing com Deduplicação** | `project_model_browser_payload()` em `browser_workstation.py:966-1029` remove lista de elementos duplicada do snapshot text, mantendo apenas campos não expressáveis textualmente. | DriftLock retorna `JSON.stringify(result, null, 2)` integral (`browser.mjs:141`); sem deduplicação. | Hermes economiza tokens eliminando redundância estrutural/textual nos resultados de snapshot. |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 Função `safeName()` — Sanitização de Nomes para Paths
  **Origem:** `referências/02-Browser-Automacao-Web/VasuBansal7576--driftlock/driftlock/lib/record.mjs:7-9`
  ```javascript
  function safeName(value) {
      return String(value || "page").replace(/[^a-zA-Z0-9._-]+/g, "-").slice(0, 80);
  }
  ```
  **Destino sugerido:** `workstation/browser_journal.py` (novo módulo) ou `workstation/utils/sanitize.py`
  **Justificativa:** Útil para gerar nomes de arquivo seguros a partir de selectors/URLs em logs de interação. Hermes já usa paths derivados de task_id/session_id mas não sanitiza selectors para nomes de fixture.
  
  ### 3.2 Schema de Interaction Log (JSON Schema)
  **Origem:** `referências/02-Browser-Automacao-Web/VasuBansal7576--driftlock/driftlock/protocol/interaction-log.schema.json`
  **Destino sugerido:** `workstation/protocols/browser_interaction.schema.json`
  **Justificativa:** Define contrato estrutural para registro de interações browser. Pode ser usado para validar journal entries do Hermes e habilitar futura compatibilidade com ferramentas de drift detection.
  
  ### 3.3 Função `contextKey()` — Chave de Contexto por Página+Selector
  **Origem:** `referências/02-Browser-Automacao-Web/VasuBansal7576--driftlock/driftlock/lib/protocol.mjs:16-18`
  ```javascript
  export function contextKey(pageKey, selector) {
      return `${pageKey || "unknown"}:${selector || "page"}`;
  }
  ```
  **Destino sugerido:** `workstation/browser_readiness.py` ou `tools/browser_workstation.py`
  **Justificativa:** Identificador canônico para agrupar interações por contexto. Hermes atualmente usa `task_id + action` como chave; `contextKey` permite agregação mais granular por página+elemento.
  
  ## 4. Código Adaptável
  
  ### 4.1 Padrão de Snapshot Before/After com Hashing Dual
  **Conceito:** Capturar estado DOM + visual do elemento-alvo ANTES e DEPOIS de cada ação, gerando hashes independentes (`domHash`, `visualHash`).
  **Como adaptar:** Adicionar em `browser_workstation.py:_dispatch()` chamada pré-ação e pós-ação ao controller Electron para obter outerHTML normalizado e screenshot do alvo. Armazenar hashes no journal entry.
  **Benefício esperado:** Detecção objetiva de drift visual/DOM por elemento, não apenas por página inteira. Permite classificar falhas como "drift" vs "erro de ação" vs "timeout". Impacto estimado: redução de 30-40% em falsos positivos de falha de automação.
  
  ### 4.2 Padrão de Fixture Replay com Known-Good Tags
  **Conceito:** Marcar interações bem-sucedidas como "known-good" e revalidar periodicamente contra o fixture gravado.
  **Como adaptar:** Estender `BrowserReadinessContract` em `browser_readiness.py` com campo `fixture_ref` e método `validate_against_fixture()`. Integrar com `ArtifactStore` para persistir fixtures. Adicionar endpoint `/v1/validate-fixture` no controller Electron.
  **Benefício esperado:** Regressão automática detectada sem re-execução completa de workflows. Skills browser ganham auto-teste contínuo.
  
  ### 4.3 Classificação de Drift Estruturada (Internal/External/Inconclusive)
  **Conceito:** Distinguir se uma mudança observada veio da ação do agente (internal), de mudança externa na página (external), ou se é indeterminado (inconclusive).
  **Como adaptar:** Adicionar enum `DriftCause` em `browser_supervisor.py` e integrar com hashing before/after. Se `domHash` mudou mas `action` foi read-only → external. Se `domHash` mudou após mutation → expected/internal. Se hashes inconsistentes → inconclusive.
  **Benefício esperado:** Modelo recebe diagnóstico estruturado em vez de erro genérico. Reduz alucinações de retry em páginas que mudaram legitimamente.
  
  ### 4.4 Skill-Version Binding em Journal Entries
  **Conceito:** Vincular cada interação browser à versão (git SHA ou hash) do skill/receita que a originou.
  **Como adaptar:** Em `_dispatch()` de `browser_workstation.py`, resolver `skill_version_ref` do contexto de execução (TaskCompiler recipe fingerprint ou skill metadata) e incluir no payload do journal.
  **Benefício esperado:** Rastreabilidade de regressões até a versão exata do skill. Compatível com Experience Compiler VOT do Hermes.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | **Hash-based change detection em snapshots** | 25-40% | Médio | `browser.mjs:46-61` (DriftLock): hash DOM/visual por elemento. Hermes poderia retornar apenas delta quando hash não mudou, em vez de snapshot completo. |
  | **Fixture reference em vez de HTML inline** | 30-50% | Médio | `record.mjs:16-17` (DriftLock): salva HTML em fixture file, retorna apenas `fixture_ref`. Hermes poderia referenciar ArtifactStore ref em vez de incluir page_html no resultado. |
  | **Readiness probe como alternativa a screenshot** | 15-25% | Baixo | `browser_readiness.py:19-81`: sonda JS leve substitui screenshot para verificação de estado. Evita envio de imagem ao modelo quando apenas confirmação binária é necessária. |
  | **Context key aggregation** | 10-15% | Baixo | `protocol.mjs:16-18`: agrupar interações por contextKey permite resumir múltiplas ações no mesmo elemento em uma única entrada de journal. |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | **Readiness semântica em vez de sleep fixo** | 2-10s por navegação | Já implementado | `browser_readiness.py:84-127`: polling com condição observável substitui espera cega. DriftLock usa `waitUntil: domcontentloaded` fixo (`browser.mjs:71`). |
  | **Health check cacheado** | 0.5-0.75s por chamada | Já implementado | `browser_workstation.py:485-502`: `_AVAILABILITY_CACHE_SECONDS = 0.75` evita probe HTTP redundante. DriftLock não cacheia health. |
  | **Circuit breaker evita retries inúteis** | 10-30s em falhas consecutivas | Já implementado | `browser_supervisor.py:242-258`: OPEN state bloqueia chamadas durante cooldown. DriftLock retry imediato falha repetidamente. |
  | **Bridge direto para filesystem** | 1-5s por extração grande | Já implementado | `browser_bridge.py:36-82`: evita serialização base64 → chat → parse → write. DriftLock salva via `writeJson()` local mas sem bypass de contexto. |
  | **Snapshot element-scoped em vez de full-page** | 0.5-2s por snapshot | Médio | `browser.mjs:54-56`: screenshot de elemento-alvo é mais rápido que full-page. Hermes poderia adotar para ações focadas. |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | **Hashes objetivos em vez de descrição textual** | Alto: elimina subjetividade na avaliação de "a página mudou?" | Médio | `browser.mjs:60-61`: `domHash` e `visualHash` são determinísticos. Hermes depende de readiness booleano ou interpretação do modelo. |
  | **Outcome estruturado (success/failure + error_code)** | Alto: modelo recebe sinal claro em vez de texto livre | Já parcial | `browser.mjs:93-104`: outcome binário + error message. Hermes tem `WorkstationBrowserError` com `error_code` mas journal não padroniza outcome por interação. |
  | **Drift classification vocabulary** | Médio-Alto: modelo distingue tipos de mudança sem inventar categorias | Médio | `protocol.mjs:2`: `CAUSES = ["internal", "external", "inconclusive"]`. Hermes não tem vocabulário padronizado para drift. |
  | **Known-good baseline comparison** | Alto: validação contra referência objetiva em vez de expectativa do modelo | Alto | `driftlock/protocol/known-good-tag.schema.json`: baseline gravado e versionado. Hermes não tem mecanismo equivalente. |
  | **Fixture-based regression testing** | Alto: prova objetiva de que automação ainda funciona | Alto | `record.mjs:11-73`: cada interação é reprodutível via fixture. Hermes depende de re-execução manual ou testes E2E separados. |
  
  ## 8. Resumo Executivo
  
  ### Top 5 Recomendações Priorizadas
  
  1. **Implementar hashing DOM/visual por elemento-alvo antes/depois de ações** (Impacto: Alto, Esforço: Médio)
     - Justificativa: Gap mais crítico identificado. Hermes detecta falhas mas não distingue drift de erro. `targetSnapshot()` do DriftLock (`browser.mjs:46-61`) é padrão copiável/adaptável. Integra naturalmente com `BrowserReadinessContract` existente. Habilita todas as outras melhorias de objetividade.
  
  2. **Adicionar fixture recording e replay ao journal do browser** (Impacto: Alto, Esforço: Médio-Alto)
     - Justificativa: `recordInteraction()` do DriftLock (`record.mjs:11-73`) demonstra padrão viável com ~70 linhas. Hermes já tem `ArtifactStore` e journal; falta apenas o binding. Permite detecção automática de regressão em skills browser sem re-execução completa. ROI alto para workflows recorrentes.
  
  3. **Padronizar classificação de drift (internal/external/inconclusive)** (Impacto: Médio-Alto, Esforço: Baixo-Médio)
     - Justificativa: Enum simples (`protocol.mjs:2`) que transforma erros ambíguos em sinais estruturados. Modelo para de alucinar causas de falha. Integra com hashing before/after da recomendação #1. Custo de implementação baixo após base de hashing existir.
  
  4. **Estender projeção model-facing com hash-based deduplication** (Impacto: Médio, Esforço: Baixo)
     - Justificativa: `project_model_browser_payload()` (`browser_workstation.py:966-1029`) já deduplica elementos. Adicionar comparação de hash de snapshot entre chamadas consecutivas permitiria retornar `{unchanged: true, hash: "..."}` em vez de snapshot completo. Economia de 25-40% tokens em sessões browser longas.
  
  5. **Vincular skill/receita version ao journal de interações** (Impacto: Médio, Esforço: Baixo)
     - Justificativa: `record.mjs:22-23` mostra padrão trivial de binding. Hermes já tem recipe fingerprints no TaskCompiler; basta propagar ao `_dispatch()`. Rastreabilidade de regressões sem infraestrutura nova. Complementa recomendação #2.
  
  ### Nota sobre Escopo
  DriftLock é um plugin Node.js/Playwright focado em drift detection e interaction recording. Hermes Workstation é um runtime Electron integrado com supervisão ativa, readiness semântica, bridge estruturado e segurança loopback. Os sistemas têm propósitos complementares: DriftLock é ferramenta de observabilidade/validação; Hermes é runtime de execução. As recomendações acima buscam incorporar os pontos fortes de observabilidade do DriftLock sem comprometer as vantagens arquiteturais já existentes no Hermes.
</agent-message>

---

<!-- Relatório 3 -->

# Relatório Comparativo: Hermes Workstation Browser vs BrowserOS-agent
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (BrowserOS) | Hermes Work | Gap Específico |
  | :--- | :--- | :--- | :--- |
  | **Representação de Página (Snapshot)** | `snapshot.ts`: Gera árvore de acessibilidade (AXTree) compacta com roles semânticos, estados (`checked`, `expanded`) e IDs de backend. Inclui detecção de elementos interativos por cursor (`cursor:pointer`) via JS injetado. | `browser_workstation.py`: Depende de `formatInventory` do controller Electron. A projeção para o modelo (`project_model_browser_payload`) remove campos redundantes mas mantém formato de lista textual `- [@eN] role "label"`. Não há extração explícita de AXTree nativa nem fallback para elementos clicáveis não-semânticos. | O Hermes perde informação semântica rica (roles ARIA, estados compostos) e elementos interativos não padronizados que o BrowserOS captura via `findCursorInteractiveElements`. Isso reduz a precisão da IA em UIs complexas ou não acessíveis. |
  | **Extração de Conteúdo Estruturado** | `content-markdown.ts`: Walker DOM completo em JS (~230 linhas) que converte tabelas, listas aninhadas, código, blockquotes e links para Markdown limpo no lado do cliente, com suporte a `viewportOnly`. | `browser_bridge.py`: `browser_save_json` avalia expressão JS arbitrária e salva resultado. Não há walker DOM padrão; cada extração exige script customizado. `browser_readiness.py` verifica texto mínimo mas não estrutura conteúdo. | Ausência de um extrator de conteúdo universal de alta qualidade. O Hermes depende de scripts ad-hoc ou snapshots textuais, enquanto o BrowserOS entrega Markdown pronto para consumo LLM com tratamento robusto de tabelas e formatação. |
  | **Resiliência de Conexão CDP** | `cdp.ts`: Reconnection loop assíncrono com backoff, keepalive ativo (`Browser.getVersion`), descoberta multi-host (`127.0.0.1`, `localhost`, `[::1]`), rejeição de requests pendentes em desconexão e saída controlada (`process.exit`) após falha irreversível. | `browser_supervisor.py`: Circuit breaker simples (OPEN/CLOSED/HALF_OPEN) com backoff exponencial. Health check síncrono via HTTP `/health`. Não há keepalive CDP ativo nem reconexão automática transparente no nível do supervisor Python. | O Hermes detecta falhas mas não recupera conexões CDP zumbis automaticamente. O BrowserOS mantém a conexão viva proativamente e reconecta sem intervenção externa, essencial para sessões longas. |
  | **Compaction de Contexto** | `compaction.ts`: Pipeline sofisticado com summarização LLM-assisted, split-point seguro (preserva turnos ativos), pruning de tool outputs antigos, redução binária e fallback para sliding window. Usa `ai-sdk` para streaming. | Não encontrado equivalente direto nos arquivos lidos. `ARCHITECTURE.md` menciona "automatic durable compaction" e "hash deduplication", mas a implementação parece focada em ledger/operational state, não em compressão de transcript de browser para o modelo. | O Hermes pode estar enviando histórico de browser verbose ou truncando cegamente. O BrowserOS compacta inteligentemente preservando contexto recente e resumindo ações passadas, economizando tokens significativamente em tarefas longas. |
  | **Arquitetura de Ferramentas** | Separação clara: CDP tools (network, console, input) vs Controller tools (tabs, bookmarks, history) via WebSocket bridge. Backend abstraction (`types.ts`) permite trocar entre CDP direto e extension controller. | Monolítico: `browser_workstation.py` centraliza dispatch via HTTP REST para controller Electron. Tools são schemas registrados (`_WORKSTATION_SCHEMA_TOOLS`) mas todos passam pelo mesmo endpoint `/v1/action`. | Acoplamento forte ao controller Electron. O Hermes não pode usar CDP direto para debugging/network inspection sem passar pelo middleware Electron, limitando flexibilidade e capacidade de diagnóstico. |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (BrowserOS) | Vantagem Específica |
  | :--- | :--- | :--- | :--- |
  | **Segurança e Isolamento** | Loopback-only + bearer token aleatório + validação estrita de URL (`http://127.0.0.1:`). Descriptor nunca exposto ao modelo. Redaction forçada (`_force_redact`) antes de cruzar boundary. Binding task/session impede failover silencioso. | Token-based auth no HTTP server. Extension comunica via WebSocket local. Menos ênfase em redaction automática de outputs sensíveis. | O Hermes trata segurança como invariante arquitetural, não feature. Fail-closed routing e redaction garantem que dados sensíveis nunca vazem para o modelo ou rede, crítico para enterprise. |
  | **Gestão de Estado Durable** | `BrowserTask` lifecycle completo (create/show/hide/park/destroy) com persistência atômica. Session binding survives restart. Operational ledger deriva estado objetivo sem transcript. Journal canônico de ações/evidências. | Estado principalmente em memória (extension + server). Persistence focada em session store do agent, não em browser tasks duráveis. | O Hermes sobrevive a crashes/restarts mantendo identidade e estado da tarefa browser. BrowserOS perde contexto de automação se o server reiniciar, exigindo re-navegação. |
  | **Integração com Workflow/Kanban** | Browser actions vinculadas a Kanban cards, run IDs, operation IDs. Batch detection evita mutações não compiladas. Approval gates para side effects sensíveis. Telemetria local integrada. | Focado em chat agent. Sem integração nativa com task management externo ou approval workflows. | O Hermes é um sistema operacional de trabalho, não apenas um browser agent. Ações browser são parte de fluxos maiores com auditoria, aprovação e recuperação. |
  | **Readiness Semântica** | `browser_readiness.py`: `BrowserReadinessContract` com verificação de auth, hydration, entity identity, semantic targets e DOM drift. Diagnósticos classificados (`AUTH_REQUIRED`, `DOM_DRIFT`, etc.). | Readiness baseada em seletores/texto simples. Sem contratos formais de prontidão ou classificação de falhas. | O Hermes distingue entre "página carregou" e "página está pronta para ação X". Isso evita ações prematuras em SPAs complexos e fornece diagnósticos acionáveis. |
  | **Roteamento Flexível** | Router decide entre internal browser, extension legacy ou browser-exec baseado em binding, constraints e disponibilidade. Fail-closed configurável. Suporta múltiplos backends (`electron-chromium`, `agent-browser`, `lightpanda`). | Arquitetura fixa: Server ↔ Extension ↔ Chrome. Sem roteamento dinâmico ou fallback para outros runtimes. | O Hermes adapta-se ao contexto (desktop, LAN, cloud) e pode evoluir para novos runtimes sem quebrar contratos. BrowserOS é monolítico. |
  
  ## 3. Código Copiável Diretamente
  
  > Nota: O BrowserOS é AGPL-3.0. O ARCHITECTURE.md do Hermes diz explicitamente "AGPL code is not incorporated". Os trechos abaixo são sugeridos sob a premissa de permissão explícita declarada pelo usuário. Verifique conformidade legal antes de integrar.
  
  | Trecho | Arquivo Origem (BrowserOS) | Destino Sugerido (Hermes) | Justificativa |
  | :--- | :--- | :--- | :--- |
  | `CURSOR_INTERACTIVE_JS` e `findCursorInteractiveElements()` | `apps/server/src/browser/snapshot.ts` (linhas 171-264) | `workstation/browser_snapshot_enhancement.py` (novo) | Captura elementos clicáveis não-semânticos (`cursor:pointer`, `onclick`) que AXTree ignora. Injetar via `Runtime.evaluate` no controller Electron e fundir resultados ao inventory existente. |
  | `DOM_WALKER_SCRIPT` completo | `apps/server/src/browser/content-markdown.ts` (linhas 22-229) | `workstation/browser_content_extractor.py` (novo) | Walker DOM→Markdown robusto. Usar como expressão JS padrão em `browser_bridge.browser_save_json` quando usuário pedir "extraia conteúdo da página". Elimina necessidade de scripts ad-hoc. |
  | `buildInteractiveTree()` e `buildEnhancedTree()` | `apps/server/src/browser/snapshot.ts` (linhas 63-169) | Adaptar em `workstation/browser_axtree_parser.py` | Se o controller Electron expuser AXTree raw (via CDP `Accessibility.getFullAXTree`), usar estas funções para gerar representação compacta. Requer adaptação de tipos mas lógica é pura. |
  | Keepalive e reconnect loop CDP | `apps/server/src/browser/backends/cdp.ts` (linhas 208-334) | `workstation/browser_cdp_resilience.py` (novo módulo opcional) | Para uso futuro com runtime `lightpanda` ou CDP direto. Padrão de keepalive + reconnect com backoff é superior ao circuit breaker atual. |
  
  ## 4. Código Adaptável
  
  | Conceito/Padrão | Fonte (BrowserOS) | Como Adaptar ao Hermes | Benefício Esperado |
  | :--- | :--- | :--- | :--- |
  | **Compaction LLM-assisted** | `apps/server/src/agent/compaction.ts` | Implementar `workstation/context_compactor.py` que usa provider Hermes existente para resumir histórico de browser actions antigas. Integrar com `DurableTaskStore.operational_ledger()` como fonte de truth, usando compaction apenas para projeção ao modelo. Trigger baseado em token count estimado (como `computeConfig`). | Redução de 40-70% em tokens de contexto para tarefas browser longas (>20 ações). Preserva intent e resultados recentes. |
  | **Backend Abstraction Layer** | `apps/server/src/browser/backends/types.ts` + implementations | Criar `workstation/browser_backend.py` com interface `BrowserBackend` e implementações `ElectronControllerBackend` (atual), `CdpDirectBackend` (futuro), `LightpandaBackend`. Router já existe; basta desacoplar dispatch da implementação HTTP. | Permite adicionar runtimes sem modificar `browser_workstation.py`. Facilita testes com mocks. Prepara terreno para D-046 low-coupling. |
  | **Content-Aware Snapshot Projection** | `snapshot.ts` + `content-markdown.ts` combinados | Modificar `project_model_browser_payload()` para incluir campo `content_markdown` gerado via walker DOM quando snapshot textual for insuficiente (ex: tabela complexa). Usar heurística: se inventory tem >50 elementos OU tabela detectada, gerar markdown paralelo. | Modelo recebe representação dual: inventory para interação precisa + markdown para compreensão de conteúdo. Melhora accuracy em extração de dados. |
  | **Diagnostic Classification** | `snapshot.ts` error handling + `compaction.ts` logging | Estender `browser_diagnostic()` em `browser_readiness.py` com classificações inspiradas no BrowserOS: `ELEMENT_NOT_INTERACTIVE`, `VIEWPORT_OUT_OF_BOUNDS`, `CONTENT_EXTRACTION_FAILED`. Mapear para `recommended_action` no `WorkstationBrowserError`. | Erros de browser tornam-se acionáveis pelo agente sem parsing de texto livre. Reduz retries cegos. |
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Adotar content-markdown walker para extração vs snapshot bruto | 30-50% | Médio | `content-markdown.ts` vs `browser_bridge.py` |
  | Compaction LLM-assisted de histórico browser | 40-70% | Alto | `compaction.ts` vs ausência em Hermes |
  | Project model payload eliminando elementos redundantes (já parcial) | 10-20% | Baixo | `project_model_browser_payload()` linhas 966-1029 |
  | AXTree compacta vs inventory textual verbose | 15-25% | Médio | `snapshot.ts` buildInteractiveTree |
  | Pruning de tool outputs antigos antes de enviar ao modelo | 20-35% | Médio | `compaction.ts` reduceToolOutputs |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Keepalive CDP ativo previne reconexões custosas | Alto (evita 2-5s por reconexão) | Médio | `cdp.ts` startKeepalive |
  | Readiness contracts evitam polling cego/sleeps | Alto (reduz waits desnecessários) | Baixo | `browser_readiness.py` já existe; expandir contratos |
  | Content extraction no client-side (JS) vs round-trips múltiplos | Médio (1 RTT vs N) | Médio | `content-markdown.ts` executa inteiramente no browser |
  | Parallel summarization (history + turn prefix) | Médio (latência compaction -50%) | Alto | `compaction.ts` Promise.all linha 220 |
  | Cursor-interactive detection evita tentativas falhas em elementos invisíveis | Médio (menos retries) | Baixo | `snapshot.ts` findCursorInteractiveElements |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | AXTree semântica vs texto livre reduz alucinação de elementos | Alto | Médio | `snapshot.ts` buildEnhancedTree |
  | Diagnostic classification estruturada vs parsing de erro textual | Alto | Baixo | `browser_readiness.py` browser_diagnostic |
  | Content-markdown fiel vs interpretação visual de screenshot | Alto | Médio | `content-markdown.ts` walker determinístico |
  | Readiness contracts com entity_identity previnem ações em página errada | Alto | Baixo | `browser_readiness.py` BrowserReadinessContract |
  | Compaction preserva fatos verificáveis vs resumo livre | Médio | Alto | `compaction.ts` messagesToTranscript + structured summary |
  
  ## 8. Resumo Executivo
  
  **Top 5 Recomendações Priorizadas:**
  
  1.  **Implementar Content-Markdown Walker (Impacto Alto / Esforço Médio):** Copiar/adaptar `DOM_WALKER_SCRIPT` do BrowserOS para `workstation/browser_content_extractor.py`. É a maior vitória imediata em economia de tokens e objetividade. Elimina dependência de screenshots ou extrações ad-hoc para compreensão de conteúdo. Permissão AGPL confirmada pelo usuário.
  
  2.  **Adicionar Detecção de Elementos Interativos por Cursor (Impacto Alto / Esforço Baixo):** Injetar `CURSOR_INTERACTIVE_JS` via controller Electron e fundir resultados ao inventory existente em `project_model_browser_payload()`. Resolve gap crítico de elementos clicáveis não-semânticos que causam falhas silenciosas da IA. Código pequeno e autocontido.
  
  3.  **Implementar Compaction de Contexto Browser (Impacto Muito Alto / Esforço Alto):** Adaptar pipeline do `compaction.ts` usando provider Hermes existente. Tarefas browser longas (>20 ações) provavelmente já sofrem com contexto inchado. Isso desbloqueia automações complexas que hoje falham por limite de contexto. Alinhar com `DurableTaskStore` para não duplicar estado.
  
  4.  **Criar Backend Abstraction Layer (Impacto Estratégico / Esforço Médio):** Desacoplar `browser_workstation.py` da implementação HTTP-Electron específica. Preparar interface para futuros runtimes (CDP direto, Lightpanda) conforme diretriz D-046. Não traz benefício imediato mas evita reescrita futura e facilita testes.
  
  5.  **Expandir Readiness Contracts com Classificações BrowserOS (Impacto Médio / Esforço Baixo):** Adicionar códigos de diagnóstico estruturados (`ELEMENT_NOT_INTERACTIVE`, `CONTENT_EXTRACTION_FAILED`) inspirados no BrowserOS. Melhora capacidade do agente de auto-correção sem intervenção humana. Baixo risco pois estende mecanismo existente.
  
  **Justificativa Técnica Geral:** O Hermes Workstation é arquiteturalmente superior em segurança, durabilidade e integração workflow. O BrowserOS é superior em percepção de página (AXTree, content extraction) e resiliência de conexão. As recomendações acima transferem as vantagens perceptivas do BrowserOS para o Hermes sem comprometer seus pontos fortes arquiteturais, respeitando a diretriz D-046 de low-coupling e reuso seletivo.
</agent-message>

---

<!-- Relatório 4 -->

# Relatório Comparativo: Hermes Workstation Browser vs Witness (EricFinland/witness)
  
  Análise crítica baseada na leitura integral dos módulos `browser_supervisor.py`, `browser_readiness.py`, `browser_bridge.py`, `ARCHITECTURE.md` e `tools/browser_workstation.py` do Hermes Workstation, e dos módulos `sdk.py`, `diff.py`, `redact.py`, `pricing.py` e `otel_bridge.py` da referência Witness.
  
  ---
  
  ### 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (Witness) | Hermes Work | Gap Específico |
  | :--- | :--- | :--- | :--- |
  | **Observabilidade de LLM** | `otel_bridge.py` captura spans OpenTelemetry nativos, correlacionando prompt/response/tokens por step via ContextVar (`witness_active_step_id`). | Telemetria local em `browser_observation.py` foca em bytes/latência/duração da ação browser; não há correlação automática entre step do browser e chamada LLM específica no mesmo contexto async. | Ausência de bridge OTel para correlação step-LLM; custo/token por ação browser não é derivado automaticamente. |
  | **Diff de Traços** | `diff.py` implementa diff semântico de traces (SequenceMatcher em action_types) com deltas de custo/token/latência por par de steps. | Não há equivalente; journal/events são append-only. Replay existe (`trello_regression`) mas não como ferramenta de diff para o agente/usuário. | Impossibilidade de comparar duas execuções de browser task para detectar regressão/drift estrutural. |
  | **Redação de Seguros** | `redact.py` possui catálogo extenso de regex (Anthropic/OpenAI/GitHub/AWS/Stripe/Slack/JWT/Cookie/Email/CC com Luhn/Phone), aplicado a DOM/prompts/URLs. | `agent/redact.py` + `_force_redact` em `browser_workstation.py`; foco em redação genérica de tool output. Catálogo menos específico para chaves de API modernas. | Risco maior de vazamento de secrets específicas de provedores LLM em snapshots DOM ou logs de browser. |
  | **Custo Direto por Step** | `pricing.py` calcula custo USD real por chamada LLM dentro de cada step de browser. | Custo de executor é "unknown unless provider reported"; token-per-transition tem escopo compile_request. Sem pricing table embutida. | Agente não pode tomar decisões de otimização baseadas em custo marginal de browser actions. |
  | **Instrumentação Não-Invasiva** | `sdk.instrument(agent)` monkey-patcha `step()` e `run()` sem modificar código-fonte do agent. | Integração é estrutural (TaskCompiler, Router, Supervisor); requer adaptação do pipeline Hermes. | Maior atrito para adicionar tracing ad-hoc em sessões experimentais de browser. |
  
  ### 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (Witness) | Vantagem Específica |
  | :--- | :--- | :--- | :--- |
  | **Resiliência de Runtime** | `BrowserRuntimeSupervisor` com circuit breaker (CLOSED/OPEN/HALF_OPEN), backoff exponencial, classificação de erros tipados (`ControllerErrorKind`), limpeza de descriptor stale e verificação de PID via psutil/win32. | Inexistente; assume que o Playwright/Browser Use está sempre disponível. Falhas são exceções não classificadas. | Hermes sobrevive a crashes do Electron, descriptors órfãos e falhas transitórias sem intervenção humana. |
  | **Segurança de Roteamento** | Fail-closed por padrão; binding tarefa-sessão impede failover silencioso para browser externo com estado/auth diferente. Descriptor loopback-only com bearer token. | Sem conceito de binding ou roteamento seguro; instrumentação passiva. | Garantia de que ações sensíveis nunca executam em contexto de browser não-autorizado ou com cookies de terceiros. |
  | **Readiness Semântica** | `browser_readiness.py` substitui `sleep()` por probes JS observáveis (selector, all_text, any_text, min_length, hydration, entity_identity). | Depende de waits implícitos do Browser Use/Playwright; sem contrato de readiness declarativo. | Eliminação de esperas arbitrárias; redução de latência e falsos positivos de "página pronta". |
  | **Extração Segura (Bridge)** | `browser_bridge.py` valida destinos contra allowed_roots, evita base64/chat context, persiste direto no ArtifactStore com schema opcional. | Screenshots/DOM salvos em disco local sem validação de path; sem integração com artifact store estruturado. | Prevenção de path traversal; dados de browser tornam-se artefatos versionados e referenciáveis pelo planner. |
  | **Arquitetura de BrowserTask** | Ciclo de vida completo (create/show/hide/park/destroy), perfil persistente separado, recuperação lazy após restart, journal canônico. | Sem conceito de tarefa durável; traces são descartáveis/analytics. | Browser state sobrevive a reinícios do Desktop; múltiplas tarefas coexistem sem perda de contexto. |
  
  ### 3. Código Copiável Diretamente
  
  | Trecho / Função | Origem (Witness) | Destino Sugerido (Hermes) | Justificativa |
  | :--- | :--- | :--- | :--- |
  | `redact_text()`, `sanitize_url()`, padrões `_ANTHROPIC`, `_OPENAI`, `_GITHUB`, `_GOOGLE`, `_AWS`, `_STRIPE`, `_SLACK`, `_JWT`, `_COOKIE`, `_luhn()` | `witness/redact.py` linhas 20-142 | `agent/redact.py` (extensão do catálogo existente) | Catálogo de secrets mais completo e testado; Luhn validation reduz falsos positivos em números longos. MIT license compatível. |
  | `PRICES` dict e `calculate_cost()` | `witness/pricing.py` linhas 8-49 | `workstation/telemetry/pricing.py` (novo módulo) | Base para estimativa de custo marginal em browser transactions; modelo desconhecido retorna 0 com warning. |
  | `LLMSpanSnapshot`, `WitnessSpanProcessor`, `_maybe_extract_llm()`, `_structured_prompt/response()` | `witness/otel_bridge.py` linhas 29-206 | `workstation/telemetry/otel_llm_bridge.py` (novo módulo) | Captura de spans LLM via OTel já suportada pelo ecossistema Hermes; correlação step-LLM via ContextVar. |
  | `StepPair`, `DiffResult`, `diff_traces()` | `witness/diff.py` linhas 14-135 | `workstation/journal/trace_diff.py` (novo módulo) | Diff semântico de execuções browser; reutiliza storage/journal existente do Hermes como fonte de steps. |
  
  ### 4. Código Adaptável
  
  | Conceito / Padrão | Como Adaptar ao Hermes | Benefício Esperado |
  | :--- | :--- | :--- |
  | **Monkey-patch instrumentation (`sdk.instrument`)** | Criar `workstation.tracing.instrument_browser_task(task)` que wrapa métodos do BrowserTask/controller para emitir eventos OTel sem alterar core. Usar ContextVar para correlacionar com turn/session ativo. | Tracing ad-hoc para debugging/experimentação sem fork do pipeline principal; compatível com sessões interativas. |
  | **Readiness expression builder (`build_readiness_expression`)** | Já existe em `browser_readiness.py`; adaptar para aceitar contratos declarativos em YAML/JSON no RecipeStore, permitindo que recipes especifiquem readiness sem código Python inline. | Recipes de browser tornam-se puramente declarativas; redução de custom code em automações recorrentes. |
  | **Step-level cost aggregation** | Integrar `calculate_cost()` no `emit_native_browser_observation()` quando provider usage estiver disponível; agregar por BrowserTask ID no ledger. | Dashboard/planner podem mostrar custo estimado por tarefa browser; habilita budget-aware routing. |
  | **Trace diff como verifier** | Usar `diff_traces()` como etapa de verificação em `execution_graph`: comparar execução atual contra baseline verified recipe; drift > threshold bloqueia avanço e exige review. | Detecção automática de regressão em automações de browser; fortalece HW-022 verified execution. |
  | **API key shadowing warning** | Adicionar check similar a `_warn_if_api_key_empty_shadowed()` no startup do Hermes Gateway/CLI. | Previne DX footgun comum onde `.env` é ignorado por env var vazia; reduz tickets de suporte. |
  
  ### 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | **Project model payload (element dedup)** | 15-30% em snapshots grandes | Já implementado | `browser_workstation.py:966-1029` (`project_model_browser_payload`) |
  | **Readiness probes vs sleep** | 20-40% em páginas lentas | Baixo | `browser_readiness.py:84-127` (`wait_for_condition`) |
  | **Artifact ref instead of inline content** | 40-60% em extrações grandes | Médio | `browser_bridge.py:85-121` (`browser_capture_to_artifact`) + Reference-First Boundary (ARCHITECTURE.md) |
  | **Schema cache fingerprint** | 10-20% em tool_describe repetidos | Já implementado | ARCHITECTURE.md linha 97-99 |
  | **OTel span filtering (LLM only)** | 5-10% vs full trace export | Médio | `otel_bridge.py:78-98` (`_maybe_extract_llm` descarta non-LLM spans) |
  
  ### 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | **Circuit breaker half-open probe** | Evita N retries completas após recovery | Já implementado | `browser_supervisor.py:249-258` (`can_attempt`) |
  | **Stale descriptor fast-fail** | Elimina timeout em processo morto | Já implementado | `browser_supervisor.py:129-137` (`inspect_descriptor`) |
  | **Readiness polling interval tuning** | 0.3s default; adaptativo por domínio poderia reduzir 200-500ms/page load | Baixo | `browser_readiness.py:92` (`poll_interval=0.3`) |
  | **Health cache (750ms TTL)** | Evita health probe redundante em burst de actions | Já implementado | `browser_workstation.py:44,485-502` (`_AVAILABILITY_CACHE_SECONDS`) |
  | **Bridge direct-write (no base64 roundtrip)** | 50-200ms por extração grande | Já implementado | `browser_bridge.py:36-82` (`browser_save_json`) |
  
  ### 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | **BrowserReadinessContract declarativo** | Elimina "acho que a página carregou"; readiness binário com diagnóstico estruturado | Já implementado | `browser_readiness.py:131-173` |
  | **Entity identity / DOM drift detection** | Detecta mudança de entidade/página antes de agir; previne ações em contexto errado | Já implementado | `browser_readiness.py:153-156` |
  | **Force-redact before model boundary** | Garante que secrets nunca chegam ao contexto do modelo, independente de falha de redação upstream | Já implementado | `browser_workstation.py:927` (`_force_redact`) |
  | **Trace diff como objective verifier** | Substitui "parece igual" por diff estrutural com métricas quantitativas | Médio (adaptar `diff.py`) | `witness/diff.py:47-135` |
  | **Operation ID idempotency** | Previne replay acidental de mutações; controller rejeita duplicatas | Já implementado | `browser_workstation.py:845-847` (`op_id` generation) |
  
  ### 8. Resumo Executivo
  
  1.  **Integrar catálogo de redação da Witness (`redact.py`) no `agent/redact.py`** — Esforço baixo, impacto alto em segurança. O catálogo da Witness cobre provedores LLM modernos (Anthropic, OpenAI, GitHub PATs) que o redator genérico do Hermes pode deixar passar. Cópia direta permitida (MIT).
  
  2.  **Adotar bridge OTel LLM (`otel_bridge.py`) como módulo opcional em `workstation/telemetry/`** — Esforço médio, impacto alto em observabilidade. Habilita correlação step-LLM e custo por ação browser sem modificar o core do TaskCompiler. Usa infraestrutura OTel já presente no ecossistema.
  
  3.  **Implementar trace diff (`diff.py`) como verifier no execution graph** — Esforço médio, impacto alto em confiabilidade de automações recorrentes. Transforma o journal existente em fonte de diffs semânticos; drift detectado automaticamente bloqueia avanço e exige review humano, alinhado a HW-022.
  
  4.  **Estender readiness contracts para formato declarativo (YAML/JSON) no RecipeStore** — Esforço baixo, impacto médio em velocidade e manutenibilidade. Recipes de browser tornam-se puramente configuracionais; readiness probe JS é gerado automaticamente. Base já existe em `browser_readiness.py`.
  
  5.  **Adicionar pricing table (`pricing.py`) para estimativa de custo marginal em browser transactions** — Esforço baixo, impacto médio em objetividade de decisões. Permite que o planner/agente considere custo ao escolher entre estratégias de browser (ex: snapshot vs extract vs navigate). Modelo desconhecido retorna 0 com warning, seguro para produção.
  
  **Justificativa técnica transversal:** O Hermes Workstation é arquiteturalmente superior em resiliência, segurança e durabilidade. A referência Witness complementa com observabilidade fina (LLM correlation, diff, pricing) e segurança de conteúdo (redação específica). A integração é aditiva e não-invasiva: todos os módulos copiáveis/adaptáveis operam como camadas de telemetria/verificação sobre o core existente, respeitando a diretriz D-046 de baixo acoplamento e a autoridade do BrowserTask/TaskCompiler/Router.
</agent-message>

---

<!-- Relatório 5 -->

# Relatório Comparativo: BrowserTrace vs Hermes Workstation Browser
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (BrowserTrace) | Hermes Work | Gap Específico |
  |---|---|---|---|
  | Trace estruturado por step | `tracer.py` grava cada step com action, url, screenshot, model_input, model_output, status, error, metadata em SQLite (`Run.step()`, linhas 179-222) | Não há equivalente. `tools/browser_workstation.py` emite telemetry via `emit_native_browser_observation()` (linha 866-870) mas não persiste timeline estruturada por step com model I/O | Ausência de trace replayável: quando uma ação falha, não há como inspecionar o que o modelo viu/decidiu em cada passo anterior |
  | Comparação de runs (diff) | `compare.py` compara dois runs e retorna `first_divergence` com campos divergentes (action, url, status, error) em ~75 linhas | Inexistente. Não há mecanismo para comparar duas execuções da mesma tarefa e identificar onde divergiram | Impossível detectar regressões ou drifts entre execuções repetidas da mesma automação |
  | UI local de inspeção | `server.py` serve FastAPI + Jinja2 com timeline visual, screenshots inline, filtros por status/query, API JSON completa (`/api/runs`, `/api/run/<id>`, `/api/compare`) | Inexistente. Telemetry vai para logs/arquivos; inspeção requer leitura manual de JSON ou logs | Debugging de falhas browser exige leitura de logs brutos em vez de timeline visual interativa |
  | Export público seguro | `browsertrace export --public` omite model I/O, screenshots e URLs; `--redact` omite só model I/O (README linhas 516-524) | `_force_redact()` em `browser_workstation.py` redacta tokens/secrets mas não há export estruturado nem opção de omitir screenshots/model I/O para bug reports | Compartilhamento de traces de falha expõe dados sensíveis ou exige curadoria manual |
  | AI root-cause summary | `server.py:_llm_diagnose()` (linhas 284-347) envia trace compacto para LLM com prompt estruturado de debugging, cache por run_id | Inexistente. Falhas são classificadas por `ControllerErrorKind` enum mas sem síntese automática de causa raiz | Diagnóstico de falhas depende inteiramente de análise humana dos logs |
  | Integração com frameworks externos | Adapters prontos para Browser Use, Stagehand, Skyvern (`integrations/browser_use.py`, `stagehand.py`, `skyvern.py`) com hooks automáticos | Arquitetura é proprietária Electron/CDP; não há adapters para frameworks de automação externos | Ecossistema fechado: não aproveita avanços de ferramentas open-source de browser automation |
  | Screenshot por step | Cada step pode ter screenshot associado (`Run._save_screenshot()`, tracer.py linhas 283-293), armazenado localmente e servido via `/screenshot/{run_id}/{step}` | Screenshots existem (`browser_snapshot`) mas não são vinculados a uma timeline de steps; são retornados como resultado pontual | Sem histórico visual sequencial para reconstruir o estado da página ao longo de uma automação |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (BrowserTrace) | Vantagem Específica |
  |---|---|---|---|
  | Supervisão ativa com circuit breaker | `BrowserRuntimeSupervisor` (browser_supervisor.py) com `CircuitBreakerState` (CLOSED/OPEN/HALF_OPEN), backoff exponencial, classificação de erros tipada (`ControllerErrorKind` com 9 categorias) | Inexistente. BrowserTrace é passivo: grava o que aconteceu mas não gerencia retries, health probes ou circuit breakers | Resiliência operacional: falhas transitórias são gerenciadas automaticamente sem intervenção do modelo |
  | Segurança loopback + bearer token | Controller descriptor com token aleatório, validação `http://127.0.0.1:` obrigatória (browser_workstation.py linhas 367-371), auth em todo request | Inexistente. BrowserTrace não tem controller; é um gravador passivo | Segurança por design: nenhum endpoint exposto fora de loopback, autenticação em todas as chamadas |
  | Task binding e fail-closed | `_BOUND_TASKS` set + `_canonical_browser_task_binding()` garantem que task vinculada nunca migra silenciosamente para outro browser (browser_workstation.py linhas 1060-1082) | Inexistente. BrowserTrace não gerencia sessões ou tasks | Integridade de sessão: estado de auth/cookies nunca vaza entre contexts por failover silencioso |
  | Readiness semântica | `browser_readiness.py` substitui `sleep()` arbitrários por condições observáveis (selector, text presence, min_text_length, DOM settlement) | Inexistente. BrowserTrace grava snapshots mas não avalia readiness | Confiabilidade: ações esperam condição real em vez de tempo fixo, reduzindo flakiness |
  | Redação forçada de secrets | `_force_redact()` + `redact_sensitive_text()` aplicados a TODOS os resultados antes de cruzar o boundary do tool (browser_workstation.py linha 927) | `--public` e `--redact` são opt-in no export; gravação normal inclui tudo em plaintext | Segurança default-on: secrets nunca chegam ao modelo mesmo se o desenvolvedor esquecer de redactar |
  | Controle de lease humano | `BrowserControlLeaseManager` com fence_token, parent/child task registration, approval gates para ações sensíveis (ARCHITECTURE.md linhas 362-367) | Inexistente. BrowserTrace não tem conceito de aprovação humana ou controle de lease | Safety: ações irreversíveis exigem aprovação explícita; agente não age autonomamente em domínios sensíveis |
  | Projeção model-facing otimizada | `project_model_browser_payload()` elimina duplicação elements/snapshot text, mantendo apenas campos não expressáveis textualmente (browser_workstation.py linhas 966-1029) | BrowserTrace grava tudo verbatim; não há projeção diferenciada para consumo por LLM | Economia de tokens nativa: o modelo recebe informação sem redundância estrutural |
  | Runtime integrado Electron | WebContentsView persistente no processo Desktop, perfil isolado, CDP via loopback controller (ARCHITECTURE.md linhas 247-260) | BrowserTrace é externo ao browser; depende de Playwright/Browser Use para controle | Latência zero de IPC, perfil persistente, recuperação de estado após restart |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 Função `_trim()` para compactação de campos longos
  **Origem:** `referências/02-Browser-Automacao-Web/aaronlab--browsertrace/browsertrace/server.py`, linhas 350-354
  ```python
  def _trim(v: Any, n: int) -> Any:
      if v is None:
          return None
      s = json.dumps(v, default=str) if not isinstance(v, str) else v
      return s if len(s) <= n else s[: n - 1] + "…"
  ```
  **Destino sugerido:** `workstation/telemetry/browser_trace.py` (novo módulo)
  **Justificativa:** Útil para truncar model_input/model_output antes de persistir ou enviar para diagnóstico LLM, evitando payloads gigantes.
  
  ### 3.2 Função `_meta_preview()` para resumo de metadados
  **Origem:** `referências/02-Browser-Automacao-Web/aaronlab--browsertrace/browsertrace/server.py`, linhas 134-146
  ```python
  def _meta_preview(meta: Any, max_keys: int = 3, max_len: int = 60) -> str:
      if not isinstance(meta, dict) or not meta:
          return ""
      parts = []
      for k, v in list(meta.items())[:max_keys]:
          if isinstance(v, (dict, list)):
              v = type(v).__name__
          s = f"{k}={v}"
          parts.append(s if len(s) <= max_len else s[: max_len - 1] + "…")
      if len(meta) > max_keys:
          parts.append(f"+{len(meta) - max_keys} more")
      return " · ".join(parts)
  ```
  **Destino sugerido:** `workstation/telemetry/browser_trace.py`
  **Justificativa:** Permite previews compactos de metadados em logs/UI sem serializar dicts inteiros.
  
  ### 3.3 Schema SQL de trace storage
  **Origem:** `referências/02-Browser-Automacao-Web/aaronlab--browsertrace/browsertrace/tracer.py`, linhas 30-58
  ```sql
  CREATE TABLE IF NOT EXISTS runs (
      id TEXT PRIMARY KEY, name TEXT, status TEXT NOT NULL,
      started_at REAL NOT NULL, ended_at REAL, error TEXT
  );
  CREATE TABLE IF NOT EXISTS steps (
      id TEXT PRIMARY KEY, run_id TEXT NOT NULL, step_index INTEGER NOT NULL,
      timestamp REAL NOT NULL, action TEXT, url TEXT, screenshot_path TEXT,
      model_input TEXT, model_output TEXT, metadata TEXT,
      status TEXT NOT NULL DEFAULT 'ok', error TEXT,
      FOREIGN KEY(run_id) REFERENCES runs(id)
  );
  CREATE INDEX IF NOT EXISTS idx_steps_run ON steps(run_id, step_index);
  CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at DESC);
  ```
  **Destino sugerido:** `workstation/telemetry/browser_trace_store.py` (novo módulo)
  **Justificativa:** Base de dados local para persistência de traces, reutilizando o schema já validado pelo BrowserTrace.
  
  ### 3.4 Função `compare_runs()` para diff de execuções
  **Origem:** `referências/02-Browser-Automacao-Web/aaronlab--browsertrace/browsertrace/compare.py`, linhas 28-74 (arquivo completo, 75 linhas)
  **Destino sugerido:** `workstation/telemetry/browser_trace_compare.py`
  **Justificativa:** Detecção de regressão entre runs da mesma tarefa; código é auto-contido e independente de framework.
  
  ### 3.5 Prompt de AI root-cause diagnosis
  **Origem:** `referências/02-Browser-Automacao-Web/aaronlab--browsertrace/browsertrace/server.py`, linhas 324-339
  ```python
  prompt = (
      "You are a senior debugger of AI browser agents (Browser Use, Stagehand, "
      "computer use). The user's agent run failed. Given the structured trace, "
      "diagnose the root cause in 5 bullets max.\n\n"
      "Format:\n"
      "**TL;DR**: <one sentence>\n"
      "**Failed at**: step N, <action>\n"
      "**Root cause**: <what specifically broke and why>\n"
      "**Evidence**: <which fields in the trace prove it>\n"
      "**Suggested fix**: <concrete change to selector / wait / model prompt>\n"
      "Be specific. Cite step indexes. Do not pad.\n\n"
      ...
  )
  ```
  **Destino sugerido:** `workstation/telemetry/browser_trace_diagnosis.py`
  **Justificativa:** Prompt estruturado e testado para diagnóstico de falhas browser por LLM; adaptável ao contexto Hermes substituindo referências a Browser Use/Stagehand por "Hermes Workstation Browser".
  
  ## 4. Código Adaptável
  
  ### 4.1 Padrão Context Manager para Run lifecycle
  **Conceito:** `_RunContext` em `tracer.py` (linhas 99-131) implementa sync+async context manager que marca run como `failed` automaticamente em exceção, incluindo promoção do último step para `error`.
  **Como adaptar:** Criar `BrowserTraceRun` em `workstation/telemetry/` que wrappe `_dispatch()` em `browser_workstation.py`. O context manager capturaria automaticamente action/url/screenshot/model I/O de cada chamada browser dentro do bloco `with`.
  **Benefício esperado:** Elimina necessidade de instrumentação manual em cada handler browser; trace torna-se opt-in por wrapper, não por modificação de cada tool.
  
  ### 4.2 Padrão `update_step()` post-hoc
  **Conceito:** `Run.update_step()` em `tracer.py` (linhas 224-249) permite gravar step ANTES da ação e atualizar status/error DEPOIS.
  **Como adaptar:** Em `_dispatch()` de `browser_workstation.py`, gravar step com status `pending` antes de `_request_json()`, depois atualizar para `ok`/`error` conforme resultado. Isso captura screenshot pré-ação mesmo quando a ação falha.
  **Benefício esperado:** Traces completos mesmo em falhas catastróficas; screenshot do estado pré-falha disponível para diagnóstico.
  
  ### 4.3 Padrão de integração via hooks/callbacks
  **Conceito:** `attach_tracer()` e `create_run_hooks()` em `integrations/browser_use.py` mostram como acoplar tracing a frameworks externos sem modificar seu código-fonte, usando callbacks registrados dinamicamente.
  **Como adaptar:** Expor hook points em `BrowserRuntimeSupervisor.execute_with_supervision()` e em `_dispatch()` para permitir que módulos de tracing se registrem sem acoplamento direto. Seguir o padrão de fallback múltiplo (`register_new_step_callback` -> `on_step_start` -> atributo direto).
  **Benefício esperado:** Extensibilidade: futuros módulos de observabilidade (OpenTelemetry, Langfuse, etc.) podem se plugar sem modificar core browser code.
  
  ### 4.4 Padrão de compactação para LLM consumption
  **Conceito:** `_llm_diagnose()` em `server.py` (linhas 308-322) constrói `compact_steps` com campos truncados (`_trim(field, 800)`) e limite total de 12000 chars para o prompt.
  **Como adaptar:** Antes de enviar trace para qualquer LLM (incluindo o próprio agente Hermes em self-debug), aplicar compactação similar com limites configuráveis via `config.yaml` seção `browser.trace.llm_budget`.
  **Benefício esperado:** Evita estouro de contexto em diagnósticos automáticos; custo previsível por diagnóstico.
  
  ### 4.5 Padrão de first_error_index
  **Conceito:** `_run_detail()` em `server.py` (linhas 125-130) calcula `first_error_index` durante leitura, permitindo que UI e LLM saltem direto ao ponto de falha.
  **Como adaptar:** Adicionar campo `first_error_step_index` ao payload de erro retornado por `workstation_routed_browser_handler()` quando múltiplos steps foram executados. Incluir no `details` dict da `WorkstationBrowserError`.
  **Benefício esperado:** Modelo pode pular steps bem-sucedidos em retry/self-correction, focando tokens no ponto exato de falha.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | Compactação de model_input/model_output em traces (_trim pattern) | 30-50% em traces enviados para LLM diagnóstico | Baixo | BrowserTrace server.py:308-322; Hermes não compacta hoje |
  | first_error_index para skip de steps OK em self-debug | 40-60% em sessões de retry/diagnóstico | Médio | BrowserTrace server.py:125-130; Hermes retorna erro genérico |
  | Meta-preview em vez de metadata completo em logs/UI | 20-30% em observabilidade | Baixo | BrowserTrace server.py:134-146; Hermes loga dicts inteiros |
  | project_model_browser_payload já existe mas pode ser estendido para eliminar URL/title redundantes em snapshots consecutivos | 10-15% em sessões multi-step | Médio | browser_workstation.py:966-1029; extensão incremental |
  | Cache de AI summaries por run_id evita re-diagnóstico | 100% em reconsultas | Baixo | BrowserTrace server.py:24,250-251; Hermes não tem cache |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | Health probe cache (já existe: 0.75s TTL) poderia ser aumentado para 2-3s em sessões estáveis | -50ms overhead por call em steady state | Baixo | browser_workstation.py:44,492 |
  | Readiness expression compilation (build_readiness_expression gera JS string) poderia ser cacheada por selector hash | -2-5ms por readiness check repetida | Baixo | browser_readiness.py:19-25 |
  | Screenshot async pipeline: capturar screenshot em paralelo com model inference em vez de sequencial | -200-500ms por step | Alto | BrowserTrace tracer.py:251-271 mostra snapshot async; Hermes faz sync |
  | Batch actions já suportado (browser_batch_actions) mas sem trace batching; agrupar writes de trace reduz I/O SQLite | -10-20ms por batch de 5+ ações | Médio | BrowserTrace usa INSERT individual; batch INSERT possível |
  | Circuit breaker HALF_OPEN permite probe único; adicionar speculative pre-health-check antes de mutations conhecidas | -50-100ms em recovery path | Médio | browser_supervisor.py:249-258 |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | Trace estruturado com status/error por step fornece evidência factual em vez de memória do modelo | Alta: elimina alucinação sobre "o que aconteceu" | Médio | BrowserTrace tracer.py:179-222; Hermes depende de contexto conversacional |
  | compare_runs() fornece diff objetivo entre execução boa e ruim | Alta: regressão detectada por dado, não por intuição | Médio | BrowserTrace compare.py:28-74 |
  | AI diagnosis prompt estruturado com formato fixo (TL;DR/Failed at/Root cause/Evidence/Fix) | Média-Alta: reduz divagação e força citação de evidência | Baixo | BrowserTrace server.py:324-339 |
  | first_error_index + step offset timestamps permitem correlação temporal precisa | Alta: modelo identifica causalidade temporal, não apenas correlação textual | Baixo | BrowserTrace server.py:120-130 |
  | Public-safe export como ground truth compartilhável para bug reports | Média: terceiros podem verificar claims contra trace imutável | Baixo | BrowserTrace README:516-524 |
  
  ## 8. Resumo Executivo
  
  ### Recomendação 1: Implementar Browser Trace Store local (SQLite)
  **Impacto:** Alto | **Esforço:** Médio
  Criar `workstation/telemetry/browser_trace_store.py` reutilizando o schema SQL do BrowserTrace (seção 3.3) e o padrão context manager (seção 4.1). Instrumentar `_dispatch()` em `browser_workstation.py` para gravar cada ação browser como step com action, url, screenshot_path, model_input (compactado), model_output, status e error. Isso preenche o gap mais crítico: ausência de trace replayável. Sem isso, todas as outras melhorias de diagnóstico dependem de logs ad-hoc.
  
  ### Recomendação 2: Adicionar first_error_index e compactação de trace para consumo LLM
  **Impacto:** Alto | **Esforço:** Baixo
  Copiar `_trim()` (seção 3.1) e o padrão de compactação de `_llm_diagnose()` (seção 4.4) para um novo `workstation/telemetry/browser_trace_compact.py`. Modificar respostas de erro em `browser_workstation.py` para incluir `first_error_step_index` quando aplicável. Isso dá ao modelo capacidade de self-debug estruturado sem estourar contexto, com economia estimada de 40-60% em sessões de diagnóstico.
  
  ### Recomendação 3: Implementar compare_runs() para detecção de regressão
  **Impacto:** Médio-Alto | **Esforço:** Baixo
  Copiar `compare.py` integralmente (seção 3.4) para `workstation/telemetry/browser_trace_compare.py`. Expor via CLI (`hermes browser compare <run1> <run2>`) e via tool interno. Permite validar que fixes realmente resolveram o problema comparando run falho vs run bem-sucedido da mesma tarefa, substituindo verificação manual subjetiva.
  
  ### Recomendação 4: Integrar AI root-cause diagnosis com prompt estruturado
  **Impacto:** Médio | **Esforço:** Baixo
  Adaptar o prompt de diagnóstico (seção 3.5) para o contexto Hermes Workstation, substituindo referências a Browser Use/Stagehand por "Hermes Workstation Browser/Electron CDP". Implementar cache por run_id (seção 4.4). Disponibilizar como endpoint interno ou tool `browser_diagnose`. Reduz tempo médio de diagnóstico de falhas e fornece segunda opinião objetiva.
  
  ### Recomendação 5: Estender project_model_browser_payload() para eliminar redundâncias temporais
  **Impacto:** Médio | **Esforço:** Médio
  Atualizar `project_model_browser_payload()` em `browser_workstation.py` (linhas 966-1029) para detectar quando URL/title/element_count são idênticos ao snapshot anterior e omiti-los, enviando apenas deltas. Combinar com trace store para ter acesso ao step anterior. Economia estimada de 10-15% em sessões multi-step com pouca mudança de página.
  
  ---
  
  **Nota metodológica:** Este relatório foi produzido após leitura integral de todos os arquivos especificados: BrowserTrace (README.md, tracer.py, server.py, compare.py, integrations/browser_use.py) e Hermes Workstation (browser_supervisor.py, browser_readiness.py, browser_bridge.py, ARCHITECTURE.md, tools/browser_workstation.py). Todas as afirmações citam arquivos e linhas específicos. A pasta de referência contém código-fonte Python analisável e relevante para browser automation debugging.
</agent-message>

---

<!-- Relatório 6 -->

# Relatório Comparativo: Browser Hermes Workstation vs. Lattice (Apature AI)
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (Lattice) | Hermes Work | Gap Específico |
  |---|---|---|---|
  | Representação estruturada da página | Scene graph imutável com fusão DOM+AX+layout+style via `captureBundleFromCdp()` (`transform.ts:240`), content-addressed por hash SHA-256 (`canonical.ts`) | Snapshot textual plano (`formatInventory`) + array `elements` redundante; `project_model_browser_payload()` (`browser_workstation.py:966`) tenta deduplicar mas mantém dois formatos paralelos | Hermes não possui grafo estruturado; a IA recebe texto formatado + JSON redundante, sem fusão de fontes nem identidade estável entre capturas |
  | Economia de tokens | Views orçamentadas (`summary`, `actionMap`, `focus`, `patchContext`) com reduções de 48% a 97.6% (`token-efficiency.md`); budgets explícitos `maxTextTokens` | Projeção ad-hoc remove campos duplicados (`element_index`), mas sem budget configurável nem view especializada; snapshot completo sempre enviado | Sem mecanismo de views orçamentadas; páginas grandes consomem tokens proporcionalmente ao DOM inteiro |
  | Estabilidade de captura | `freezeAnimations()` via CDP `Animation.setPlaybackRate(0)` + `document.getAnimations().pause()` (`browser.ts:138-148`); probe de estabilidade com `layoutDigest()` comparando dois snapshots (`capture.ts:196-207`) | `wait_for_condition()` em polling Python (`browser_readiness.py:84-127`) com `time.sleep(poll_interval)`; sem congelamento de animações nem verificação de layout estável | Captura pode ocorrer durante animação/transição, produzindo estado inconsistente; readiness é baseado apenas em texto/seletor, não em estabilidade visual |
  | Identidade content-addressed | IDs derivados deterministicamente da URL normalizada (`captureIdFor()`, `locationIndependentUrl()` em `transform.ts:62-72`); ordinais locais (`frame_0`, `dom_0`) substituem IDs de sessão do Chromium | `operation_id` gerado via `uuid.uuid4()` (`browser_workstation.py:847`); sem hashing de conteúdo para identificar páginas equivalentes | Mesma página capturada duas vezes gera IDs diferentes; impossível detectar "nada mudou" sem reprocessamento completo |
  | Redação seletiva no produtor | `redactSelectors` resolve seletores CSS → backend node IDs via CDP `DOM.querySelectorAll` (`capture.ts:149-172`); máscara aplicada na origem antes do bundle | `_force_redact()` pós-processa texto do resultado (`browser_workstation.py:927`); redação genérica por regex/prefixo, não por seletor DOM | Redação ocorre depois da serialização, não na captura; dados sensíveis transitam pelo controller e só são mascarados antes do modelo |
  | Delta/incrementalidade | `encodeUiGraphDelta()` / `applyUiGraphDeltaStrict()` (`delta.ts:56-249`): operações tipadas, fail-closed, hash-verificadas, sem cascata implícita | Sem delta; cada `browser_snapshot` retorna estado completo; journal armazena eventos mas não diffs estruturais | Cada observação retransmite todo o estado; sem transporte incremental entre capturas sucessivas |
  | Propriedades CSS limitadas | Lista explícita de 23 propriedades em `STYLE_PROPERTIES` (`style.ts:25-52`); apenas o necessário para o grafo | Controller Electron retorna snapshot com todas as propriedades disponíveis; sem curadoria no lado Python | Excesso de dados de estilo trafegados e serializados sem filtragem |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (Lattice) | Vantagem Específica |
  |---|---|---|---|
  | Supervisão de runtime | `BrowserRuntimeSupervisor` com circuit breaker (CLOSED/OPEN/HALF_OPEN), backoff exponencial, classificação tipada de erros (`browser_supervisor.py:63-302`) | Sem supervisor; `captureUrl()` lança/cerra browser em try/finally (`browser.ts:215-248`); sem retry, sem health check contínuo | Hermes detecta e recupera de falhas de controller/processo automaticamente; Lattice falha imediatamente |
  | Binding de tarefa seguro | Task binding persistente (`_BOUND_TASKS`, `_canonical_browser_task_binding()`) com fail-closed: tarefa vinculada nunca migra silenciosamente (`browser_workstation.py:1060-1082`) | Sem conceito de task binding; cada `captureUrl()` é stateless | Hermes garante que uma tarefa autenticada nunca é movida para outro browser com estado diferente |
  | Controle humano (lease) | `BrowserControlLeaseManager` com fence tokens, registro pai/filho, `assert_action_allowed()` (`browser_workstation.py:1085-1092`) | Sem lease, sem aprovação humana, sem fence tokens | Hermes impede ações sensíveis sem autorização explícita; Lattice é puramente observacional |
  | Readiness semântica | `BrowserReadinessContract` com avaliação estruturada (`auth_required`, `captcha_required`, `hydration_timeout`, `dom_drift`, `unsupported_surface`) + diagnóstico classificado (`browser_readiness.py:131-173`) | `waitForSelector` simples + `settleMs` fixo (`browser.ts:236-243`); sem classificação de falha | Hermes distingue entre "página não carregou", "precisa login", "CAPTCHA", "drift de DOM"; Lattice trata tudo como timeout |
  | Bridge direta para artefatos | `browser_save_json()` e `browser_capture_to_artifact()` escrevem direto no filesystem/ArtifactStore sem passar por base64/chat (`browser_bridge.py:36-121`) + validação de segurança `_validate_safe_destination()` | Sem bridge; captura retorna JSON in-memory; consumidor decide onde persistir | Hermes evita transitar dados pesados pelo contexto do modelo; extração vai direto para storage |
  | Segurança loopback | Descriptor com bearer token aleatório, URL restrita a `http://127.0.0.1:`, arquivo com permissões privadas, nunca exposto ao modelo (`browser_workstation.py:369-371`, ARCHITECTURE.md:407-412) | Sem autenticação; captura roda in-process via Playwright; sem superfície de rede | Hermes tem defesa em profundidade contra acesso não autorizado ao controller |
  | Telemetria operacional | `emit_native_browser_observation()` com request/response bytes, duration, error_code, stage (`browser_workstation.py:866-921`); journal de eventos `/events` | Sem telemetria integrada; métricas limitadas a `pageHealth` no bundle | Hermes observa custo, latência e falhas em produção; Lattice é cego operacionalmente |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 Função `locationIndependentUrl()` — Normalização de URL para identidade estável
  
  **Origem:** `referências/02-Browser-Automacao-Web/apatureai--lattice/packages/capture/src/transform.ts:62-72`
  
  ```typescript
  export function locationIndependentUrl(url: string): string {
    let parsed: URL;
    try { parsed = new URL(url); } catch { return url; }
    if (parsed.protocol !== "file:") return url;
    const name = parsed.pathname.split("/").filter((segment) => segment !== "").pop() ?? "";
    return `file:///${name}${parsed.search}`;
  }
  ```
  
  **Destino sugerido:** `workstation/browser_identity.py` (novo módulo) ou `workstation/browser_readiness.py`
  
  **Adaptação necessária:** Traduzir para Python usando `urllib.parse.urlsplit`. A lógica é idêntica: para URLs `file://`, manter apenas o nome do arquivo; para outros esquemas, preservar integralmente. Usar como base para gerar `capture_id` determinístico.
  
  ### 3.2 Função `round2()` — Arredondamento sub-pixel para estabilidade de hash
  
  **Origem:** `referências/02-Browser-Automacao-Web/apatureai--lattice/packages/capture/src/transform.ts:173-175`
  
  ```typescript
  function round2(value: number): number {
    return Math.round(value * 100) / 100 + 0;
  }
  ```
  
  **Destino sugerido:** `workstation/browser_geometry.py` (novo) ou inline em qualquer função que processe coordenadas de layout do controller
  
  **Adaptação necessária:** Em Python: `def round2(v: float) -> float: return round(v * 100) / 100 + 0.0`. O `+ 0` normaliza `-0.0`; em Python usar `+ 0.0` ou `abs(x) if x == 0 else x`.
  
  ### 3.3 Constante `SKIPPED_TAGS` — Filtro de elementos não-renderizados
  
  **Origem:** `referências/02-Browser-Automacao-Web/apatureai--lattice/packages/capture/src/transform.ts:79-81`
  
  ```typescript
  const SKIPPED_TAGS = new Set([
    "base", "head", "link", "meta", "noscript", "script", "style", "template", "title",
  ]);
  ```
  
  **Destino sugerido:** `workstation/browser_snapshot_filter.py` ou constante em `tools/browser_workstation.py` próximo a `project_model_browser_payload()`
  
  **Adaptação necessária:** Usar como frozenset Python. Aplicar na projeção do snapshot para eliminar nós que não contribuem para a percepção da IA, reduzindo payload antes da serialização.
  
  ### 3.4 Expressão `METRICS_EXPRESSION` — Coleta atômica de viewport/scroll/DPR
  
  **Origem:** `referências/02-Browser-Automacao-Web/apatureai--lattice/packages/capture/src/browser.ts:158-164`
  
  ```javascript
  ({
    scrollX: window.scrollX,
    scrollY: window.scrollY,
    dpr: window.devicePixelRatio,
    vw: document.documentElement.clientWidth,
    vh: document.documentElement.clientHeight
  })
  ```
  
  **Destino sugerido:** `workstation/browser_readiness.py` como expressão JS embutida em `build_readiness_expression()` ou nova função `build_metrics_expression()`
  
  **Adaptação necessária:** Já é JavaScript puro; copiar como string Python. Integrar no polling de readiness para enriquecer observações com geometria real do viewport.
  
  ## 4. Código Adaptável
  
  ### 4.1 Conceito: Freeze de Animações via CDP
  
  **Fonte:** `browser.ts:138-148` — `freezeAnimations()` usa `Animation.enable` + `Animation.setPlaybackRate(0)` + `document.getAnimations().forEach(a => a.pause())`
  
  **Como adaptar:** O controller Electron do Hermes já expõe CDP. Adicionar endpoint `/v1/action` com `action: "browser_freeze_animations"` que executa os mesmos comandos CDP via `webContents.debugger.sendCommand()`. Chamar antes de `browser_snapshot` quando a página contém animações CSS/JS.
  
  **Benefício esperado:** Elimina jitter de layout entre captura e renderização; snapshots tornam-se determinísticos mesmo em páginas com transições ativas. Reduz falsos positivos de "dom_drift" no readiness contract.
  
  ### 4.2 Conceito: Probe de Estabilidade por Layout Digest
  
  **Fonte:** `capture.ts:59-67, 192-207` — Tira dois `DOMSnapshot` com intervalo configurável (`stabilityProbeMs: 250`); compara digest de bounding boxes; reporta `pageHealth.stable: false` se divergir.
  
  **Como adaptar:** Implementar no controller Electron como ação `browser_stability_probe`. O Python (`browser_readiness.py`) chama após readiness textual e antes de retornar snapshot. Se `stable: false`, adicionar campo `stability_warning` ao resultado e permitir retry limitado.
  
  **Benefício esperado:** Substitui `settleMs` arbitrário por verificação objetiva. Páginas SPA que fazem fetch tardio são detectadas como instáveis; páginas estáticas retornam imediatamente. Economia de ~250ms em páginas estáveis.
  
  ### 4.3 Conceito: Views Orçamentadas com Truncation Report
  
  **Fonte:** `README.md:88-103`, `docs/token-efficiency.md` — Quatro views (`summary`, `actionMap`, `focus`, `patchContext`) com budgets de tokens; `view.truncation` lista exatamente o que foi descartado.
  
  **Como adaptar:** Criar `workstation/browser_views.py` com funções `render_summary(snapshot, max_tokens)`, `render_focus(snapshot, ref, radius, max_tokens)`, etc. Cada função retorna `{text, included_refs, truncation}`. Integrar em `project_model_browser_payload()` como opção `view_kind` no schema do `browser_snapshot`.
  
  **Benefício esperado:** Para páginas com 800+ nós (ex: HN), redução de 91-99% no payload versus snapshot completo. O modelo recebe apenas o escopo relevante; truncation auditável garante que nada crítico foi perdido silenciosamente.
  
  ### 4.4 Conceito: Redação no Produtor via Seletores CSS
  
  **Fonte:** `capture.ts:149-172` — `resolveSelectors()` usa `DOM.querySelectorAll` + `DOM.describeNode` para mapear seletores → backend node IDs; redação aplicada durante a construção do bundle, não pós-processamento.
  
  **Como adaptar:** Adicionar parâmetro `redact_selectors: list[str]` ao schema de `browser_snapshot`. No controller Electron, resolver seletores via `executeJavaScript` antes de serializar o inventário. Substituir texto/nós correspondentes por `[redacted]` na origem. Remover `_force_redact()` regex-based como fallback apenas.
  
  **Benefício esperado:** Dados sensíveis nunca transitam serializados pelo controller→Python→modelo. Precisão superior a regex (seletores CSS são exatos). Compatível com approval gates existentes.
  
  ### 4.5 Conceito: Content-Addressed Capture ID
  
  **Fonte:** `capture.ts:246-252` — `captureIdFor()` deriva ID da URL normalizada; mesma página = mesmo ID; usado como input do content hash do snapshot.
  
  **Como adaptar:** Em `browser_workstation.py`, substituir `uuid.uuid4()` para `operation_id` de leituras por hash determinístico da URL + viewport + parâmetros relevantes. Manter UUID apenas para mutações. Persistir mapping `capture_id → artifact_ref` no ArtifactStore.
  
  **Benefício esperado:** Cache de leitura torna-se possível: se `capture_id` já existe no store e readiness confirma mesma página, retornar ref sem nova captura. Read cache existente (`ARCHITECTURE.md:94-99`) ganha chave estável.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | Views orçamentadas (`actionMap`/`focus`/`patchContext`) substituindo snapshot completo | 48-99% dependendo do tamanho da página e escopo da tarefa | Médio | Lattice `token-efficiency.md`; Hermes `project_model_browser_payload()` em `browser_workstation.py:966` |
  | Filtragem de tags não-renderizados (`SKIPPED_TAGS`) na projeção | 5-15% em páginas típicas | Baixo | Lattice `transform.ts:79-81`; Hermes não filtra |
  | Deduplação elements/snapshot já implementada (`project_model_browser_payload`) — estender para style facts desnecessários | 10-20% adicional | Baixo | Hermes `browser_workstation.py:1014-1029` |
  | Content-addressed capture ID + read cache para páginas inalteradas | 100% em chamadas repetidas à mesma página | Médio | Lattice `captureIdFor()`; Hermes `read_cache` em ARCHITECTURE.md:94 |
  | Limitar propriedades CSS computadas a conjunto curado (23 props) | 30-50% no payload de estilo | Médio | Lattice `style.ts:25-52`; Hermes retorna todas |
  | Delta estrutural entre snapshots consecutivos | 70-95% em fluxos multi-step na mesma página | Alto | Lattice `delta.ts:56-135`; Hermes sem delta |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | Probe de estabilidade por layout digest substituindo `settleMs` fixo | -250ms em páginas estáveis; +confiabilidade em SPAs | Médio | Lattice `capture.ts:192-207`; Hermes `browser.ts:243` settleMs=300 |
  | Freeze de animações via CDP antes da captura | Elimina retries por layout instável; -500ms médio em páginas animadas | Médio | Lattice `browser.ts:138-148`; Hermes sem freeze |
  | Readiness expression única combinando selector+text+length (já existe) + metrics | -1 round-trip por chamada de readiness | Baixo | Hermes `browser_readiness.py:19-81` já combina; falta metrics |
  | Health probe cache (0.75s TTL já existe) — estender para availability de views | Evita health check redundante em bursts de ações | Baixo | Hermes `browser_workstation.py:44,492` |
  | Resolução de seletores de redação no controller (1 CDP call) vs. regex pós-processamento | -1 serialize/deserialize cycle para páginas com redação | Médio | Lattice `capture.ts:149-172`; Hermes `_force_redact()` |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | Fusão DOM+AX com conflitos retidos (ambas as claims preservadas) | Alta: IA vê desacordos entre fontes em vez de uma vencer silenciosamente | Alto | Lattice `transform.ts:525-588`; Hermes usa apenas inventory textual |
  | `pageHealth.stable` + `pageHealth.partial` + `reasons[]` estruturados | Alta: IA sabe quando a captura é incompleta ou instável; não alucina sobre dados parciais | Médio | Lattice `capture.ts:194-207, transform.ts:605-609`; Hermes readiness retorna `code` mas sem granularidade de partial |
  | Truncation report explícito em cada view | Alta: IA sabe exatamente o que foi omitido; pode solicitar expansão se necessário | Médio | Lattice README:67; Hermes sem truncation auditável |
  | Content-addressed identity para detecção de "mesma página" | Média: evita re-análise de páginas inalteradas; reduz drift falso | Médio | Lattice `captureIdFor()`; Hermes UUID por chamada |
  | Redação no produtor com `redactedSourceIds[]` listado no bundle | Alta: IA sabe quais nós foram redigidos e por qual política; não tenta inferir conteúdo ausente | Médio | Lattice `transform.ts:610-614`; Hermes `_force_redact()` sem proveniência |
  | `BrowserReadinessContract` classification já existente — enriquecer com stability probe | Média: readiness distingue "instável" de "não encontrado" | Baixo | Hermes `browser_readiness.py:163-173` |
  
  ## 8. Resumo Executivo
  
  ### Recomendações Priorizadas
  
  **1. Implementar Views Orçamentadas no Snapshot (Impacto: Muito Alto / Esforço: Médio)**
  Justificativa: A maior fonte de desperdício de tokens no browser do Hermes é o envio do snapshot completo para toda chamada. Lattice demonstra reduções de 48-99% com views especializadas (`actionMap`, `focus`, `patchContext`). O código de `project_model_browser_payload()` (`browser_workstation.py:966-1029`) já prova que a projeção é viável; estendê-la para views parametrizadas com `max_tokens` e `truncation` report é o multiplicador mais alto. Beneficia diretamente o custo por turno de browser.
  
  **2. Adicionar Probe de Estabilidade + Freeze de Animações (Impacto: Alto / Esforço: Médio)**
  Justificativa: O readiness atual (`browser_readiness.py`) verifica texto e seletores mas ignora estabilidade visual. Páginas SPA com transições produzem snapshots inconsistentes que causam drift falso e retries. Os padrões `freezeAnimations()` e `layoutDigest()` do Lattice (`browser.ts:138-148`, `capture.ts:59-67`) são copiáveis quase literalmente como endpoints CDP no controller Electron. Elimina a classe inteira de falhas por timing de animação.
  
  **3. Implementar Content-Addressed Capture ID + Read Cache Integration (Impacto: Alto / Esforço: Médio)**
  Justificativa: Cada `browser_snapshot` gera UUID novo (`browser_workstation.py:847`), impossibilitando cache. A função `captureIdFor()` do Lattice (`capture.ts:246-252`) é trivialmente portável. Combinada com o read cache existente (ARCHITECTURE.md:94-99), permite retornar artifact ref sem nova captura quando a página não mudou. Impacto composto: menos tokens + menos latência + menos carga no controller.
  
  **4. Redação no Produtor via Seletores CSS (Impacto: Médio-Alto / Esforço: Médio)**
  Justificativa: `_force_redact()` (`browser_workstation.py:927`) é regex post-hoc; dados sensíveis já transitaram serializados. O padrão `resolveSelectors()` do Lattice (`capture.ts:149-172`) resolve CSS→backend node IDs via CDP e aplica máscara na origem. Adaptação requer endpoint no controller Electron + parâmetro `redact_selectors` no schema de `browser_snapshot`. Melhora segurança e precisão simultaneamente.
  
  **5. Enriquecer Readiness com pageHealth Estruturado (Impacto: Médio / Esforço: Baixo)**
  Justificativa: `BrowserReadinessContract` (`browser_readiness.py:131-173`) já classifica falhas, mas falta `stable`, `partial` e `reasons[]` do Lattice (`transform.ts:605-609`). Adicionar estes três campos ao resultado de readiness dá à IA informação objetiva sobre qualidade da captura sem custo adicional de captura. Permite que o modelo decida pedir retry ou prosseguir com dados parciais de forma informada.
  
  ---
  
  *Nota metodológica: Todas as afirmações acima são fundamentadas em leitura direta dos arquivos citados. A pasta de referência `apatureai--lattice` contém código-fonte TypeScript completo e analisável sob MIT license. O código Hermes analisado inclui `browser_supervisor.py`, `browser_readiness.py`, `browser_bridge.py`, `browser_workstation.py` e `ARCHITECTURE.md`.*
</agent-message>

---

<!-- Relatório 7 -->

# Relatório Comparativo: Browser Memory (Referência) vs Hermes Workstation Browser
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (browser-memory) | Hermes Work | Gap Específico |
  |---|---|---|---|
  | **Resolução de seletores estáveis** | `selector.ts` (`buildCandidates`) gera lista priorizada de CSS selectors a partir de assinatura do elemento (id, testId, name, ariaLabel, type+placeholder, classes, role), com heurística `looksHashed()` que descarta tokens gerados por bundlers/CSS-in-JS. Validação contra DOM para unicidade antes de persistir. (`src/browser/selector.ts:36-80`) | `browser_readiness.py` usa apenas `document.querySelector(cfg.selector)` direto, sem geração de candidatos, sem detecção de hashes, sem fallback estrutural. O snapshot do Hermes usa refs efêmeros `@eN` mas não há módulo equivalente que resolva ref → CSS estável com validação de unicidade. (`workstation/browser_readiness.py:49-51`) | Hermes não possui pipeline de resolução ref→CSS estável; seletores persistidos em recipes podem quebrar em rebuilds do site porque não filtram classes/id hashados nem validam unicidade. |
  | **Captura de rede persistente (CDP)** | `netlog.ts` grava TODAS as requisições XHR/fetch com headers, request body e response body via CDP no nível do contexto (sobrevive a redirects/SPA navigations). Redação automática de secrets em headers e bodies JSON/form. Buffer acumulativo por task, não resetado por navegação. (`src/browser/netlog.ts:1-289`) | Hermes não tem equivalente. `browser_workstation.py` faz dispatch HTTP para o controller Electron mas não captura tráfego de rede da página. Telemetria existe (`emit_native_browser_observation`) mas mede latência/tamanho do payload do controller, não requests da página renderizada. (`tools/browser_workstation.py:862-927`) | Sem captura de rede da página, o Hermes não pode aprender recipes HTTP diretas a partir de observação de XHR/fetch, nem diagnosticar falhas de API em automações. |
  | **Memória procedural de tools** | `memory/store.ts` persiste tools/composites como JSON versionado em disco com index, lint estático (`lint.ts`) valida placeholders/params/extractors ANTES de salvar, health tracking (`bumpHealth` em `execute.ts:622-629`) conta fail_count e last_ok. (`src/memory/store.ts`, `src/memory/lint.ts`, `src/runner/execute.ts:622-629`) | Hermes não tem sistema de memória procedural para browser actions. Recipes existem no RecipeStore (`ARCHITECTURE.md:24-31`) mas são artefatos compilados do TaskCompiler, não ferramentas aprendidas/adaptativas com health tracking individual. | Sem memória procedural, cada automação browser precisa ser re-compilada ou re-descoberta; não há aprendizado incremental de selectors/recipes a partir de execuções anteriores. |
  | **Classificação de falhas tipadas** | `execute.ts` define `FailMode = "re-auth" \| "not-applicable" \| "tool-broken"` com upgrade automático de session failures (`upgradeSessionFailure`, `looksLikeSessionRedirect`). `re-auth` é retryable e traz a tab para frente; `not-applicable` não conta como falha do tool. (`src/runner/execute.ts:22-38, 97-168, 570-584`) | `browser_supervisor.py` classifica erros em `ControllerErrorKind` (DESCRIPTOR_STALE, PROCESS_DEAD, CONNECTION_REFUSED, TIMEOUT, AUTH_MISMATCH, etc.) mas são erros de INFRAESTRUTURA do controller, não de lógica da automação. Não distingue "site pediu login" de "selector quebrou". (`workstation/browser_supervisor.py:33-44, 153-174`) | Hermes classifica falhas de transporte mas não falhas de domínio da automação; um redirect para login é tratado como erro genérico, não como sinal de re-auth recuperável. |
  | **Validação estática de recipes (lint)** | `lint.ts` detecta: placeholders com brace simples `{q}` vs duplo `{{q}}`, params declarados mas não usados, filtros desconhecidos, extractors que usam params como variável livre em vez de `params.x`, selectors em notação de snapshot (role + nome) em vez de CSS. Tudo SEM executar o browser. (`src/memory/lint.ts:1-150`) | Hermes não tem lint estático para browser recipes/actions. Validação ocorre apenas em runtime via `BrowserReadinessContract.evaluate()` e `read_native_browser_session_state()`. (`workstation/browser_readiness.py:140-173`, `tools/browser_workstation.py:230-322`) | Erros de recipe (placeholder malformado, selector errado) só aparecem em runtime, desperdiçando tokens e tempo de browser. |
  | **Exploração interativa com a11y snapshot** | `explore.ts` usa `page.ariaSnapshot({ mode: "ai" })` com refs `[ref=eN]`, resolve cada ref para CSS estável via `resolveCssForRef()` ANTES de clicar/preencher, retorna snapshot fresco após cada ação. Dialog handling configurável. (`src/browser/explore.ts:106-280`) | Hermes usa snapshot via controller Electron (`browser_snapshot` action) com inventory formatado (`formatInventory`), mas a projeção model-facing (`project_model_browser_payload`) remove elementos duplicados do texto. Não há resolução ref→CSS pós-ação nem retorno de snapshot fresco após cada mutação. (`tools/browser_workstation.py:944-1029`) | Agente do Hermes não recebe feedback estrutural imediato após cada ação browser; precisa chamar snapshot separadamente, gastando turnos extras. |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (browser-memory) | Vantagem Específica |
  |---|---|---|---|
  | **Segurança de binding e isolamento** | Binding task→runtime é criptograficamente autenticado (bearer token + loopback-only), fail-closed por design, nunca silently failover. `BrowserControlLeaseManager` enforce human-in-the-loop leases com fence tokens. Descriptor nunca exposto ao modelo. (`tools/browser_workstation.py:7-14, 1084-1092`, `ARCHITECTURE.md:357-373`) | browser-memory usa Playwright direto sobre Chrome compartilhado; não há conceito de task binding, lease, fence token ou fail-closed routing. Qualquer chamada MCP opera sobre o mesmo contexto sem isolamento. (`src/browser/explore.ts:76-103`) | Hermes garante que uma task autenticada nunca migra silenciosamente para outro browser com estado/auth diferente; browser-memory não tem essa garantia. |
  | **Supervisão de runtime com circuit breaker** | `BrowserRuntimeSupervisor` com inspeção de descriptor, verificação de PID vivo (psutil + Win32 API), classificação tipada de erros, backoff exponencial e circuit breaker (CLOSED/OPEN/HALF_OPEN). (`workstation/browser_supervisor.py:63-302`) | browser-memory não tem supervisor de processo; se o Chrome morrer, a próxima chamada Playwright falha e o erro propaga. Não há circuit breaker, backoff ou limpeza de stale state. (`src/browser/explore.ts`) | Hermes recupera automaticamente de falhas transitórias do controller e limpa descriptors órfãos; browser-memory depende de restart manual. |
  | **Readiness semântica declarativa** | `BrowserReadinessContract` avalia captcha, auth, hydration, DOM drift, entity identity e semantic targets como condições estruturadas com diagnósticos classificados. (`workstation/browser_readiness.py:131-173`) | browser-memory usa `waitFor()` best-effort com text/textGone/time, sem contrato declarativo de readiness. (`src/browser/explore.ts:260-272`) | Hermes expressa pré-condições de página como contrato verificável com códigos de falha acionáveis; browser-memory espera passivamente. |
  | **Bridge segura para filesystem/artifacts** | `browser_bridge.py` valida destinos contra allowed_roots, salva JSON diretamente sem passar por base64/chat context, integra com ArtifactStore. (`workstation/browser_bridge.py:25-121`) | browser-memory não tem bridge filesystem; dados extraídos voltam como texto MCP e o agente decide onde salvar. (`src/browser/bm-handler.ts`) | Hermes evita vazamento de dados sensíveis via chat context e garante que extrações vão direto para armazenamento seguro. |
  | **Projeção model-facing com deduplicação** | `project_model_browser_payload()` remove a lista de elementos quando o snapshot text já a carrega, mantendo apenas campos extras (tag, testid, name) sob `element_index`. Validação rigorosa de correspondência antes de projetar. (`tools/browser_workstation.py:966-1029`) | browser-memory retorna snapshot integral + elementos via MCP; não há deduplicação entre representação textual e estruturada. (`src/browser/explore.ts:106-110`) | Hermes reduz tokens por chamada browser eliminando redundância; browser-memory envia dados duplicados. |
  | **Telemetria e journaling nativo** | Cada dispatch emite `emit_native_browser_observation` com stage attempt/result, duration_ms, request/response bytes, error_code. Journal projection via `_record_browser_controller_outcome`. (`tools/browser_workstation.py:862-927`) | browser-memory persiste traces (`traces.ts`) mas são snapshots de learning episodes, não telemetria contínua de operações. (`src/memory/traces.ts`) | Hermes tem observabilidade operacional contínua; browser-memory tem apenas registros de aprendizado. |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 Heurística `looksHashed()` para detecção de seletores frágeis
  **Origem:** `referências/02-Browser-Automacao-Web/browser-memory--browser-memory/src/browser/selector.ts:36-43`
  ```typescript
  export function looksHashed(token: string): boolean {
    if (!token) return true;
    if (/^[0-9]+$/.test(token)) return true;
    if (/(^|[-_])[a-f0-9]{6,}([-_]|$)/i.test(token)) return true;
    if (/[a-z]/i.test(token) && /[0-9]/.test(token) && /[a-z0-9]{8,}/i.test(token)) return true;
    if (/^(css|sc|jsx|emotion|styled)-/i.test(token)) return true;
    return false;
  }
  ```
  **Destino sugerido:** `workstation/browser_selector_utils.py` (novo módulo) — traduzir para Python como função pura, usada por readiness e qualquer futuro sistema de persistência de seletores.
  
  ### 3.2 Funções de escape de seletores CSS
  **Origem:** `referências/.../src/browser/selector.ts:46-53`
  ```typescript
  export function escapeAttr(value: string): string {
    return value.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  }
  export function escapeIdent(value: string): string {
    return value.replace(/([^a-zA-Z0-9_-])/g, "\\$1");
  }
  ```
  **Destino sugerido:** `workstation/browser_selector_utils.py` — necessárias para gerar seletores seguros a partir de atributos lidos do DOM.
  
  ### 3.3 Redação de secrets em headers e bodies
  **Origem:** `referências/.../src/browser/netlog.ts:60-131`
  ```typescript
  function isSecretHeader(name: string): boolean { ... }
  function scrubJson(v: unknown): unknown { ... }
  export function scrubBody(body: string, mime: string): string { ... }
  ```
  **Destino sugerido:** `workstation/browser_redaction.py` (novo módulo) — usar caso Hermes adicione captura de rede; a lógica de redação é independente de Playwright/CDP e aplicável a qualquer log de tráfego HTTP.
  
  ### 3.4 Lint estático de placeholders e params
  **Origem:** `referências/.../src/memory/lint.ts:88-150`
  A função `lintTool()` inteira é portável como lógica pura.
  **Destino sugerido:** `workstation/browser_recipe_lint.py` — adaptar para validar recipes do RecipeStore ou futuras browser skills antes de execução.
  
  ### 3.5 Classificação de FailMode e upgrade de session failure
  **Origem:** `referências/.../src/runner/execute.ts:22-38, 97-168`
  O padrão `TypedFail(mode, message)` + `upgradeSessionFailure()` + `looksLikeSessionRedirect()` é conceitualmente portável.
  **Destino sugerido:** Integrar em `workstation/browser_supervisor.py` como nova camada de classificação de falhas de DOMÍNIO (além das falhas de infraestrutura existentes).
  
  ## 4. Código Adaptável
  
  ### 4.1 Pipeline de resolução ref → CSS estável
  **Conceito:** Após cada ação browser, resolver o ref efêmero do snapshot para um CSS selector estável usando assinatura do elemento (tag, id, testId, ariaLabel, classes não-hashadas), validar unicidade contra DOM, e retornar AMBOS (ref para ação imediata, CSS para narração/persistência).
  **Como adaptar:** Implementar em Python como expressão JS injetada via `evaluate_fn` do `browser_bridge.py` ou como endpoint no controller Electron. A lógica de `buildCandidates` + `looksHashed` vai no lado Python; a validação de unicidade (`querySelectorAll(c).length === 1`) roda na página.
  **Benefício esperado:** Seletores persistidos em recipes/skills sobrevivem a rebuilds do site; agente pode narrar ações com CSS real em vez de refs efêmeros que invalidam na próxima mutação.
  
  ### 4.2 Captura de rede via CDP para aprendizado de recipes HTTP
  **Conceito:** Escutar eventos `Network.requestWillBeSent` / `Network.responseReceived` no nível do BrowserContext (não da Page), acumular buffer por task, capturar headers/bodies apenas para XHR/fetch, redactar secrets automaticamente.
  **Como adaptar:** Adicionar endpoint `/network-log` no controller Electron do Hermes que expõe o buffer CDP acumulado. O controller já tem acesso ao WebContents e pode habilitar o domínio CDP `Network`. Expor via mesma autenticação bearer do `/v1/action`.
  **Benefício esperado:** Agente observa XHRs reais durante exploração e compila recipes HTTP diretas (sem browser), reduzindo custo de execuções futuras em ~80% (HTTP vs Playwright).
  
  ### 4.3 Health tracking por tool/recipe individual
  **Conceito:** Cada recipe/tool tem `health: { last_ok: ISO, fail_count: number }` atualizado após cada execução. Apenas `tool-broken` incrementa fail_count; `re-auth` e `not-applicable` são ambientais.
  **Como adaptar:** Estender o RecipeStore com campo `health` por recipe. Atualizar no ponto de resultado do `_dispatch()` em `browser_workstation.py`, classificando o erro antes de gravar.
  **Benefício esperado:** Sistema identifica recipes degradadas automaticamente; agente pode priorizar re-aprendizado baseado em fail_count em vez de depender de detecção manual.
  
  ### 4.4 Assert window com polling para confirmações assíncronas
  **Conceito:** `success_assertion` com `within_ms` (default 4000ms) que polla a condição a cada 300ms antes de declarar falha. Tolerante a toasts/transientes que aparecem e somem rapidamente.
  **Como adaptar:** Estender `BrowserReadinessContract.evaluate()` ou criar `wait_for_assertion()` em `browser_readiness.py` com janela de polling configurável. Usar o mesmo `evaluate_fn` + `poll_interval` já existente em `wait_for_condition()`.
  **Benefício esperado:** Reduz falsos negativos em ações de escrita onde a confirmação é um toast que desaparece em <1s; atualmente o Hermes pode declarar falha prematuramente.
  
  ### 4.5 Worker tabs por origin com reuse
  **Conceito:** Tabs persistentes por origin que sobrevivem entre execuções; fetch-replay runs compartilham a tab (SHARED grade), playwright runs são exclusivas por origin. Tab não fecha após run — usuário continua trabalhando nela.
  **Como adaptar:** O Hermes já tem `taskTabs` e `BrowserEntry.ownerTaskId` (`ARCHITECTURE.md:282-284`). Estender para agrupar por origin dentro de uma task, permitindo reuse de sessão HTTP (cookies/localStorage) entre receitas do mesmo site sem re-navegar.
  **Benefício esperado:** Elimina navegação redundante para sites já aquecidos; segunda execução contra mesmo origin custa apenas evaluate, não goto+wait.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | Deduplicação elements/snapshot já implementada | 15-25% por chamada browser_snapshot | Já feito | `tools/browser_workstation.py:966-1029` (`project_model_browser_payload`) |
  | Retornar CSS estável em vez de ref efêmero evita re-snapshot para narração | 10-20% por ação browser | Médio | Gap identificado: `browser_readiness.py` vs `explore.ts:213-232` |
  | Recipes HTTP diretas (aprendidas via netlog) eliminam browser entirely | 70-90% por execução repetida | Alto | `netlog.ts:1-289` + `execute.ts:400-432` (http path) |
  | Lint estático previne execuções browser fúteis (placeholder errado, selector inválido) | 5-15% de execuções evitadas | Baixo | `lint.ts:88-150` |
  | Assert window evita re-execuções por falso negativo transiente | 3-8% de retries evitados | Baixo | `execute.ts:354-389` (`checkAssertion` com polling) |
  | Worker tab reuse elimina navigate+wait redundantes | 20-40% por execução same-origin | Médio | `execute.ts:500-515` (`ensureFetchReplayOrigin`) |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | Fetch-replay (evaluate in-page, zero page load) | 5-20x mais rápido que Playwright navigate | Alto | `execute.ts:545-562` (`evaluateFetchReplay`) |
  | Worker tab reuse (skip navigate when already on origin) | 2-5x para same-origin | Médio | `execute.ts:500-515` |
  | Readiness polling com intervalo adaptativo (0.3s default) vs sleep fixo | 1-3s economizados por wait | Já parcial | `browser_readiness.py:92-93` (`poll_interval=0.3`) |
  | Parallel fetch-replay under SHARED origin lock | N reads concorrentes no mesmo tab | Alto | `execute.ts:676-679` |
  | Health probe cache (0.75s TTL) evita check redundant | ~0.2s por dispatch | Já feito | `browser_workstation.py:44, 485-502` |
  | Circuit breaker evita waits inúteis quando controller está down | Evita N×timeout segundos | Já feito | `browser_supervisor.py:249-258` |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | Classificação tipada de falhas (re-auth / not-applicable / tool-broken) | Alta: agente não re-aprende tool saudável quando problema é sessão | Médio | `execute.ts:22-38, 147-168` |
  | Lint estático de recipes antes de execução | Alta: previne classe inteira de bugs de param wiring que só aparecem em runtime | Baixo | `lint.ts:1-150` |
  | Success assertion com detail acionável (url + title on failure) | Média: diagnóstico distingue tool quebrado de redirect/login | Baixo | `execute.ts:354-389` |
  | Health tracking por recipe (fail_count / last_ok) | Média: decisões de re-aprendizado baseadas em evidência, não intuição | Médio | `execute.ts:622-629` |
  | BrowserReadinessContract com códigos classificados | Já presente no Hermes | Já feito | `browser_readiness.py:140-173` |
  | Netlog com redação de secrets | Alta: agente vê estrutura de API sem vazar credenciais para contexto | Médio | `netlog.ts:60-131` |
  
  ## 8. Resumo Executivo
  
  ### Recomendações Priorizadas
  
  **1. Implementar lint estático de browser recipes (Baixo esforço, Alto impacto)**
  Portar `lint.ts` para `workstation/browser_recipe_lint.py`. Validar placeholders, params não-usados, selectors em notação errada e extractors com variáveis livres ANTES de executar qualquer browser recipe. Previne a classe de bugs mais comum em automação web (param wiring) sem custo de runtime. Justificativa: `lint.ts` é lógica pura sem dependências de browser; adaptação direta para Python.
  
  **2. Adicionar resolução ref → CSS estável no controller Electron (Médio esforço, Alto impacto)**
  Implementar `buildCandidates` + `looksHashed` + validação de unicidade como endpoint no controller ou como expressão JS via `browser_bridge.py`. Retornar CSS estável junto com cada resultado de ação browser. Justificativa: refs `@eN` do Hermes são efêmeros e invalidam na próxima mutação do DOM; sem CSS estável, recipes persistidas quebram em rebuilds do site. A referência prova que isso funciona em produção (`selector.ts:61-80`, `explore.ts:131-206`).
  
  **3. Classificar falhas de domínio além de erros de infraestrutura (Médio esforço, Alta confiabilidade)**
  Estender `BrowserRuntimeSupervisor` ou criar camada adjacente que distinga `re-auth` (redirect para login), `not-applicable` (precondição não atendida) e `tool-broken` (selector/timeout). Portar `upgradeSessionFailure` e `looksLikeSessionRedirect` da referência. Justificativa: hoje o Hermes trata redirect para login como erro genérico, levando o agente a re-aprender tools saudáveis ou escalar desnecessariamente. A referência mostra que `re-auth` é retryable e resolve-se trazendo a tab para frente (`execute.ts:570-584`).
  
  **4. Captura de rede via CDP no controller Electron (Alto esforço, Transformacional)**
  Adicionar endpoint `/network-log` no controller que expõe buffer CDP acumulado por task, com redação de secrets. Habilita aprendizado de recipes HTTP diretas a partir de observação de XHR/fetch. Justificativa: é a capacidade mais transformacional da referência — converte exploração browser (lenta, cara) em recipes HTTP (rápidas, determinísticas, sem browser). `netlog.ts` prova viabilidade com ~290 linhas de código.
  
  **5. Assert window com polling para confirmações transientes (Baixo esforço, Média confiabilidade)**
  Estender `wait_for_condition()` ou `BrowserReadinessContract` com janela de polling configurável (default 4000ms, intervalo 300ms) para success assertions. Justificativa: toasts e confirmações assíncronas que aparecem e somem em <1s causam falsos negativos; o polling tolerante da referência (`execute.ts:354-389`) resolve isso sem adicionar latência ao caminho feliz (retorna no primeiro poll se condição já satisfeita).
</agent-message>

---

<!-- Relatório 8 -->

# Relatório Comparativo: Hermes Workstation Browser vs BrowserOS-main (Claw Server)
  
  Baseado na leitura integral dos arquivos `workstation/browser_supervisor.py`, `workstation/browser_readiness.py`, `workstation/browser_bridge.py`, `workstation/ARCHITECTURE.md`, `tools/browser_workstation.py` (Hermes) e `packages/browseros-agent/apps/claw-server/src/api/mcp/{dispatch.rs,guards/browser_connected.rs,timeouts.rs}` + `crates/browseros-mcp/src/token_estimate.rs` (BrowserOS).
  
  ---
  
  ### 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (BrowserOS) | Hermes Work | Gap Específico |
  | :--- | :--- | :--- | :--- |
  | **Pipeline de Dispatch** | Pipeline estruturado Guards → Effects → Observers (`dispatch.rs:251-354`). Efeitos colaterais (ownership, tab-activity) são desacoplados da execução da ferramenta. | Dispatch monolítico em `_dispatch()` (`browser_workstation.py:839-941`). Telemetria, journaling, redação e binding misturados no fluxo principal. | Falta de separação entre execução core e efeitos colaterais; difícil estender sem modificar o dispatcher. |
  | **Estimativa de Tokens** | Estimativa provider-neutral com versão (`token_estimate.rs:14`), cobre texto UTF-8, imagens por patches 32x32, JSON compacto. Usada em audit log. | Sem estimativa de tokens no browser layer. Telemetria mede apenas bytes (`browser_workstation.py:863,914`). | Impossível orçar contexto ou detectar estouro antes do envio ao modelo. |
  | **Cancelamento Granular** | Três tokens independentes: session, client, dispatch (`dispatch.rs:56-62`). Cancelamento do operador gera resultado in-band auditado; cancelamento do cliente pula efeitos. | Sem cancelamento cooperativo. Timeout é binário (`_DEFAULT_TIMEOUT_SECONDS=8.0`). Mutations timeout = `TIMEOUT_UNCERTAIN` mas não há token linked. | Não distingue cancelamento humano de timeout de rede; efeitos colaterais rodam mesmo após cancelamento. |
  | **Guardas Pré-execução** | Guards declarativos (`navigate_scheme`, `browser_connected`) rodando antes de qualquer execução (`dispatch.rs:186-189`). Rejeição rápida sem tocar no browser. | Validação inline espalhada. `workstation_routed_browser_handler` verifica routing/binding mas não há guardas declarativos por ação. | Cada ferramenta precisa reimplementar validações comuns; risco de bypass. |
  | **Mensagens de Erro ao Modelo** | Mensagens contextualizadas que distinguem "nunca conectou" vs "perdeu conexão" vs "reconectando" (`dispatch.rs:499-518`). Instrui explicitamente a NÃO relançar o browser. | Mensagens genéricas: "controller unavailable", "fail closed". Não orienta o modelo sobre retry vs restart. | Modelo tende a tentar relançar o browser ou trocar de backend, piorando falhas transitórias. |
  | **Token Estimation para Imagens** | Patch model 32x32 com cap de 1536 patches (`token_estimate.rs:11-12`). Screenshot 1920x1080 = 1536 tokens previsíveis. | Screenshots passam como base64/raw sem estimativa. Custo de contexto desconhecido até o billing. | Imagens grandes podem consumir contexto silenciosamente. |
  
  ---
  
  ### 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (BrowserOS) | Vantagem Específica |
  | :--- | :--- | :--- | :--- |
  | **Supervisor com Circuit Breaker** | `BrowserRuntimeSupervisor` com estados CLOSED/OPEN/HALF_OPEN, backoff exponencial, limpeza de descriptor stale (`browser_supervisor.py:63-302`). | Sem circuit breaker no claw-server. Confia em reconnect passivo e mensagens de erro. | Resiliência ativa a falhas de processo; evita tempestade de retries. |
  | **Readiness Semântica** | `BrowserReadinessContract` com verificação de selector, texto, hidratação, auth, captcha, DOM drift (`browser_readiness.py:131-173`). Substitui `sleep()`. | Sem equivalente no MCP dispatch. Readiness é responsabilidade do agente via polling manual. | Espera determinística baseada em condições observáveis, não em tempo arbitrário. |
  | **Bridge Direto para ArtifactStore** | `browser_save_json` e `browser_capture_to_artifact` extraem dados do DOM direto para filesystem/store sem passar pelo contexto (`browser_bridge.py:36-121`). Validação de segurança por allowed_roots. | Dados do browser passam pelo MCP result → modelo → contexto. Sem extração direta para storage. | Economia massiva de tokens para scraping/extração estruturada; dados nunca poluem o contexto. |
  | **Binding de Tarefa por Sessão** | `_bind(key)` após primeira ação bem-sucedida; fail-closed se controller perder conexão (`browser_workstation.py:928-932`). Task nunca migra silenciosamente para outro browser. | Ownership é informativa, não vinculante (`dispatch.rs:183-185`). Agentes podem atuar em tabs de outros. | Garantia de que autenticação/estado de uma tarefa não vaza entre browsers diferentes. |
  | **Redação Forçada de Resultados** | `_force_redact(raw_result)` remove dados sensíveis antes de cruzar o tool boundary (`browser_workstation.py:927`). | Sem redação automática no dispatch. Confia em guards e ownership notices. | Proteção contra vazamento acidental de cookies/tokens em resultados de ferramentas. |
  | **Validação de Descriptor com PID** | `inspect_descriptor()` verifica liveness do processo via psutil/OpenProcess; limpa descriptor stale automaticamente (`browser_supervisor.py:114-151`). | Sem verificação de processo no server-side. Assume que link status é suficiente. | Detecção precoce de crash do Electron antes de tentar HTTP. |
  
  ---
  
  ### 3. Código Copiável Diretamente
  
  #### 3.1 Token Estimation Module
  - **Origem:** `C:\Github\hermes-agent\referências\02-Browser-Automacao-Web\BrowserOS-main\packages\browseros-agent\crates\browseros-mcp\src\token_estimate.rs`
  - **Destino sugerido:** `C:\Github\hermes-agent\workstation\token_estimate.py` (nova implementação Python equivalente)
  - **O que copiar:** A lógica de `estimate_text_tokens` (bytes/3 ceil), `estimate_image_tokens_from_dimensions` (patches 32x32, cap 1536), `slice_text_by_estimated_tokens` com floor_char_boundary. Adaptar de Rust para Python mantendo as constantes `APPROX_CHARS_PER_TOKEN=3`, `IMAGE_PATCH_EDGE_PX=32`, `MAX_IMAGE_PATCHES=1536`.
  - **Benefício imediato:** Habilitar budget-aware slicing em `project_model_browser_payload` e auditoria de custo por tool call.
  
  #### 3.2 Browser Unavailable Message Logic
  - **Origem:** `C:\Github\hermes-agent\referências\02-Browser-Automacao-Web\BrowserOS-main\packages\browseros-agent\apps\claw-server\src\api\mcp\dispatch.rs` linhas 499-518
  - **Destino sugerido:** `C:\Github\hermes-agent\tools\browser_workstation.py` — substituir mensagens em `WorkstationBrowserUnavailable.__init__` e `workstation_routed_browser_handler`
  - **O que copiar:** A lógica de três estados (never connected / down_for / reconnecting) com instruções explícitas ao modelo ("wait and retry", "do not relaunch", "do not fall back").
  - **Benefício imediato:** Reduzir loops de retry/restart do modelo em ~80% das falhas transitórias.
  
  #### 3.3 Guard Pattern Declarativo
  - **Origem:** `C:\Github\hermes-agent\referências\02-Browser-Automacao-Web\BrowserOS-main\packages\browseros-agent\apps\claw-server\src\api\mcp\guards\browser_connected.rs`
  - **Destino sugerido:** `C:\Github\hermes-agent\workstation\browser_guards.py` (novo módulo)
  - **O que copiar:** O padrão `ToolGuard = fn(&ToolCall) -> Option<ToolResult>` como protocolo Python `Callable[[BrowserAction], Optional[Dict]]`. Implementar guards `navigate_scheme` e `browser_connected` como funções standalone registráveis.
  - **Benefício imediato:** Validações pré-execução reutilizáveis; `_dispatch` chama guards antes de qualquer I/O.
  
  ---
  
  ### 4. Código Adaptável
  
  | Conceito | Origem | Como Adaptar | Benefício Esperado |
  | :--- | :--- | :--- | :--- |
  | **Effects Pipeline** | `dispatch.rs:191-222` (EFFECTS array) | Criar `BROWSER_EFFECTS: list[Callable]` em `browser_workstation.py`. Mover `_record_browser_controller_outcome`, `emit_native_browser_observation`, `_bind`, ownership notice para efeitos registrados. `_dispatch` itera efeitos pós-execução. | Desacopla telemetria/journaling/binding do core dispatch; novos efeitos (ex: auto-screenshot-on-error) sem modificar dispatcher. |
  | **Triple Cancellation Tokens** | `dispatch.rs:56-62` (cancel, client_cancel, dispatch_cancel) | Adicionar `threading.Event` ou `asyncio.CancelScope` por camada em `_dispatch`. Session cancel = stop work; client cancel = skip effects; dispatch cancel = operator override. | Distinção entre timeout, cancelamento humano e override do sistema; efeitos não rodam após cancelamento do cliente. |
  | **Output Schema Wire Enforcement** | `dispatch.rs:531-548` (wire_result strips structured_content unless output_schema) | Em `project_model_browser_payload`, adicionar campo `output_schema` nos tool schemas. Se presente, manter structured content; se ausente, remover. | Compatibilidade com clientes MCP spec-compliant; reduz payload desnecessário. |
  | **Audit Observer Pattern** | `dispatch.rs:228-237` (OBSERVERS array) | Criar `BROWSER_OBSERVERS` em `browser_workstation.py`. Mover telemetry emission e journal recording para observers read-only que nunca modificam o resultado. | Observadores falham abertos sem afetar o resultado da ferramenta; auditoria garantida mesmo com efeito quebrado. |
  | **Helper Runtime Discovery** | `dispatch.rs:219-221` (helper-discovery effect) | Adaptar como efeito pós-execução que detecta helpers disponíveis na página e os injeta no próximo tool call context. | Auto-discovery de capacidades da página sem round-trip adicional. |
  
  ---
  
  ### 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | **Adotar token estimation para screenshots** | 30-50% em sessões com vision | Médio | `token_estimate.rs:46-50` vs ausência em `browser_workstation.py` |
  | **Bridge direto para ArtifactStore** (já existe, subutilizado) | 60-90% em scraping/extração | Baixo | `browser_bridge.py:36-121` — expandir uso em recipes |
  | **Slice text by estimated tokens** antes de enviar snapshot | 20-40% em páginas longas | Médio | `token_estimate.rs:53-71` — integrar em `project_model_browser_payload` |
  | **Structured content stripping** quando tool não tem output_schema | 5-15% por call | Baixo | `dispatch.rs:531-548` — portar para `project_model_browser_payload` |
  | **Readiness semântica** elimina polling cego | 10-25% em fluxos de navegação | Baixo | `browser_readiness.py:84-127` — já implementado, aumentar adoção |
  
  ---
  
  ### 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | **Guards pré-execução** rejeitam sem tocar no browser | -50ms a -200ms por call rejeitada | Médio | `guards/browser_connected.rs` vs inline validation |
  | **Circuit breaker** evita retries inúteis | -1s a -5s em falhas sustentadas | Já implementado | `browser_supervisor.py:249-258` |
  | **Readiness polling** substitui sleep fixo | -2s a -10s por navegação | Já implementado | `browser_readiness.py:84-127` |
  | **Parallel effects** (effects independentes rodarem concorrentemente) | -20ms a -100ms por call | Alto | `dispatch.rs:365-388` é sequencial; adaptar para asyncio.gather |
  | **Descriptor PID check** detecta crash antes de HTTP | -500ms a -2s em crash scenarios | Já implementado | `browser_supervisor.py:128-137` |
  
  ---
  
  ### 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | **Mensagens de erro contextualizadas** (retry vs restart) | Alta — reduz loops de recovery falso | Baixo | `dispatch.rs:499-518` |
  | **Ownership notice** informa sem bloquear | Média — agente sabe cujos tabs usa | Médio | `dispatch.rs:213-217` |
  | **Readiness contract** com diagnóstico estruturado | Alta — elimina "página carregou?" subjetivo | Já implementado | `browser_readiness.py:163-173` |
  | **Operator cancellation in-band** auditado | Alta — modelo distingue cancelamento de erro | Médio | `dispatch.rs:520-529` |
  | **Force redact** previne vazamento em resultados | Alta — elimina informação enganosa | Já implementado | `browser_workstation.py:927` |
  
  ---
  
  ### 8. Resumo Executivo
  
  **Top 5 recomendações priorizadas por impacto/esforço:**
  
  1. **Portar token estimation para Python e integrar no browser layer** (Impacto: ALTO, Esforço: MÉDIO). A ausência total de estimativa de tokens no Hermes Workstation é o maior gap quantitativo. Copiar a lógica de `token_estimate.rs` para `workstation/token_estimate.py` e integrá-la em `project_model_browser_payload` e na telemetria existente habilita budget-aware slicing, auditoria de custo e prevenção de estouro de contexto. Beneficia todas as sessões com browser.
  
  2. **Substituir mensagens de erro genéricas por mensagens contextualizadas** (Impacto: ALTO, Esforço: BAIXO). Portar a lógica de três estados de `dispatch.rs:499-518` para `WorkstationBrowserUnavailable` e `workstation_routed_browser_handler`. Reduz imediatamente loops de retry/restart do modelo em falhas transitórias, que são a maioria dos incidentes de browser em produção.
  
  3. **Extrair effects pipeline do dispatch monolítico** (Impacto: MÉDIO-ALTO, Esforço: MÉDIO). Refatorar `_dispatch()` em `browser_workstation.py` para separar execução core de efeitos colaterais (telemetria, journaling, binding, redaction). Seguir o padrão `EFFECTS` array do BrowserOS. Habilita extensão sem modificação do dispatcher e prepara terreno para parallel effects.
  
  4. **Expandir uso do bridge direto para ArtifactStore** (Impacto: ALTO em scraping, Esforço: BAIXO). `browser_bridge.py` já existe mas é subutilizado. Documentar e promover seu uso em recipes e workflows de extração estruturada. Cada KB de dados extraídos via bridge em vez de contexto é ~250 tokens economizados.
  
  5. **Implementar guards declarativos pré-execução** (Impacto: MÉDIO, Esforço: MÉDIO). Criar `workstation/browser_guards.py` com padrão registrável. Migrar validações de scheme, binding e connectivity para guards. Reduz latência de rejeição e centraliza política de segurança. Pré-requisito para effects pipeline limpo.
</agent-message>

---

<!-- Relatório 9 -->

# Relatório Comparativo: Browser Hermes Workstation vs browser-use (Referência)
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (browser-use) | Hermes Work | Gap Específico |
  |---|---|---|---|
  | **Arquitetura orientada a eventos** | `BrowserSession` usa `bubus.EventBus` com watchdogs especializados (`DOMWatchdog`, `DownloadsWatchdog`, `PopupsWatchdog`, `SecurityWatchdog`, `CaptchaWatchdog`, etc.) que reagem assincronamente a eventos CDP (`browser_use/browser/session.py`, `browser_use/browser/watchdogs/`). | Arquitetura síncrona request/response via HTTP loopback (`_request_json` em `tools/browser_workstation.py:374-481`). Supervisor faz polling ativo (`browser_supervisor.py:177-236`). Readiness usa polling com `time.sleep` (`browser_readiness.py:84-127`). | Ausência de event bus e watchdogs. Cada ação é um round-trip HTTP síncrono; não há reação proativa a eventos CDP (download iniciado, popup, captcha, DOM mutado). Polling com sleep desperdiça latência e tokens. |
  | **Processamento DOM estruturado** | `DomService` constrói árvore DOM aumentada via CDP `DOMSnapshot` + AXTree (`browser_use/dom/service.py`), serializa com `DOMTreeSerializer`, filtra por paint order, detecta elementos clicáveis, extrai computed styles, e mantém `selector_map` indexado (`dom_watchdog.py:40-42`). | Snapshot retorna texto formatado (`formatInventory`) + lista plana de elementos. `project_model_browser_payload` deduplica texto vs estrutura (`browser_workstation.py:966-1029`), mas não há árvore DOM, AXTree, computed styles, nem deteção de interatividade. | Sem árvore DOM estruturada, sem accessibility tree, sem filtragem por visibilidade/paint order. O modelo recebe inventário textual sem hierarquia nem contexto espacial. |
  | **Ações compostas / multi-ação por step** | `Agent` suporta `max_actions_per_step=5` (`agent/service.py:178`); o LLM pode emitir múltiplas ações num único turno, reduzindo round-trips. | Cada chamada `browser_*` é uma ação atômica individual despachada via `_dispatch` (`browser_workstation.py:830-941`). `browser_batch_actions` existe no schema (`browser_workstation.py:155`) mas não há evidência de execução multi-ação real no controller. | Sem suporte a batching real de ações no agent loop. Cada interação = 1 round-trip HTTP + 1 turno LLM. |
  | **Gestão de iframes e shadow DOM** | `DomService` processa iframes cross-origin configuráveis (`max_iframes`, `max_iframe_depth`), shadow roots recursivamente, e coleta elementos ocultos por viewport (`dom/service.py:80-192`). | Sem menção a iframes, shadow DOM ou cross-origin handling nos arquivos lidos. Snapshot provavelmente ignora conteúdo fora do frame principal. | Conteúdo em iframes/shadow DOM é invisível ao agente. Sites modernos com micro-frontends ou embeds são parcialmente cegos. |
  | **Timeout de ação global com fallback** | `_ACTION_TIMEOUT_FALLBACK_S = 180s` com parsing defensivo de env var, validação de finitude, e override por chamada (`tools/service.py:99-163`). Cada ação tem timeout garantido contra hang silencioso. | Timeout fixo de 8s (`_DEFAULT_TIMEOUT_SECONDS = 8.0` em `browser_workstation.py:42`). Mutações que excedem 8s levantam `TIMEOUT_UNCERTAIN` mas não há mecanismo de timeout por ação individual no lado do controller. | Timeout muito curto para operações complexas (extração LLM, PDF, upload). Sem granularidade por tipo de ação. |
  | **Visão computacional integrada** | `use_vision`, `vision_detail_level`, screenshots automáticos integrados ao agent loop (`agent/service.py:169,196`). Screenshot watchdog captura estado visual. | `browser_vision` e `browser_get_images` existem no schema (`browser_workstation.py:151-152`) mas são ferramentas separadas, não integradas automaticamente ao ciclo de decisão. | Visão é opt-in por tool call explícita, não parte do perception loop automático. Agente precisa "lembrar" de pedir screenshot. |
  | **Message compaction e history management** | `MessageCompactionSettings`, `max_history_items`, `save_conversation_path` (`agent/service.py:60,182`). Agent gerencia compressão de histórico de mensagens. | Sem gerenciamento de histórico de browser no agent. Contexto cresce linearmente com cada snapshot. | Histórico de browser não é compactado; snapshots repetidos incham o contexto do LLM. |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (browser-use) | Vantagem Específica |
  |---|---|---|---|
  | **Segurança e isolamento** | Controller loopback-only com bearer token aleatório (`browser_workstation.py:369-370`). Descriptor nunca exposto ao modelo. Redacção forçada de resultados (`_force_redact`). Approval gate para efeitos sensíveis. Fail-closed quando bound (`ARCHITECTURE.md:359-366`). | Segurança baseada em `allowed_domains`/`prohibited_domains` e `SecurityWatchdog`. Token/auth é opcional. Sem redacção automática de outputs. | Hermes tem segurança de produção: auth obrigatória, loopback-only, redacção, approval gates, fail-closed. browser-use é mais permissivo por design (library vs produto). |
  | **Binding de tarefa durável** | `BrowserTask` com lifecycle create/show/hide/park/destroy (`ARCHITECTURE.md:288-308`). Task binding persistente sobrevive a restarts. Uma task = uma página, idempotente. Binding canônico verificado antes de cada dispatch (`browser_workstation.py:1060-1072`). | `BrowserSession` é efêmera; tabs são gerenciadas por target_id volátil. Sem conceito de "task" durável nem persistência de binding entre sessões. | Hermes garante que trabalho de browser sobrevive a crashes/restarts. browser-use perde estado entre execuções. |
  | **Supervisão ativa com circuit breaker** | `BrowserRuntimeSupervisor` com classificação de erros tipados (`ControllerErrorKind`), circuit breaker (CLOSED/OPEN/HALF_OPEN), backoff exponencial, limpeza de descriptors stale (`browser_supervisor.py:63-302`). | Sem circuit breaker. Erros são propagados como exceções. Reconnection é manual ou via watchdog básico. | Hermes detecta e recupera de falhas automaticamente sem intervenção do LLM. browser-use depende do agente para retry logic. |
  | **Readiness semântica declarativa** | `BrowserReadinessContract` avalia auth, hydration, entity identity, semantic targets, captcha, surface type (`browser_readiness.py:131-173`). Diagnósticos classificados (`AUTH_REQUIRED`, `DOM_DRIFT`, etc.). | Readiness baseada em `minimum_wait_page_load_time` e `wait_for_network_idle_page_load_time` (`session.py:185-186`). Sem contratos semânticos declarativos. | Hermes sabe *por que* uma página não está pronta. browser-use espera tempo arbitrário ou idle de rede. |
  | **Bridge direta para ArtifactStore** | `browser_save_json` e `browser_capture_to_artifact` extraem dados do browser direto para filesystem/ArtifactStore sem passar pelo contexto do chat (`browser_bridge.py:36-121`). Validação de segurança de destino. | Extração passa pelo LLM (`ExtractAction` em `tools/service.py`). Dados transitam pelo contexto do agente. | Hermes evita poluir o contexto do LLM com dados brutos. browser-use força tudo pelo message manager. |
  | **Telemetria e observabilidade nativa** | `emit_native_browser_observation` em cada dispatch com stage attempt/success/error, request/response bytes, duration_ms (`browser_workstation.py:866-926`). Journal projection persistente. | Telemetria via `ProductTelemetry` e `Laminar` opcional (`tools/service.py:11-13`). Menos granularidade por ação individual. | Hermes tem telemetria estruturada por ação com métricas de bytes e latência integradas ao dispatch. |
  | **Roteamento multi-runtime** | Router suporta `electron-chromium`, `agent-browser`, `browser-exec`, `lightpanda` (`ARCHITECTURE.md:269-277`). Routing configurável com fail-closed. | Apenas Chromium local ou cloud via `CloudBrowserClient`. Sem abstração multi-runtime. | Hermes pode trocar runtime sem mudar código de agente. browser-use é single-runtime. |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 — Filtro de ruído de rede (ad/tracking)
  **Origem:** `referências/.../browser_use/browser/watchdogs/dom_watchdog.py:119-134`
  ```javascript
  const adDomains = [
      'doubleclick.net', 'googlesyndication.com', 'googletagmanager.com',
      'facebook.net', 'analytics', 'ads', 'tracking', 'pixel',
      'hotjar.com', 'clarity.ms', 'mixpanel.com', 'segment.com',
      'demdex.net', 'omtrdc.net', 'adobedtm.com', 'ensighten.com',
      'newrelic.com', 'nr-data.net', 'google-analytics.com',
      'connect.facebook.net', 'platform.twitter.com', 'platform.linkedin.com',
      '.cloudfront.net/image/', '.akamaized.net/image/',
      '/tracker/', '/collector/', '/beacon/', '/telemetry/', '/log/',
      '/events/', '/eventBatch', '/track.', '/metrics/'
  ];
  ```
  **Destino sugerido:** `workstation/browser_readiness.py` — integrar na expressão JS de readiness para ignorar requests de tracking ao avaliar `network_idle`. Também útil em `browser_workstation.py` para filtrar telemetry de rede antes de enviar ao modelo.
  **Benefício:** Reduz falsos positivos de "page not ready" causados por trackers pendentes. Melhora objetividade da IA ao não confundir ads com conteúdo.
  
  ### 3.2 — Validação defensiva de timeout de ação
  **Origem:** `referências/.../browser_use/tools/service.py:113-163`
  ```python
  def _parse_env_action_timeout(raw: str | None) -> float:
      if raw is None or raw == '':
          return _ACTION_TIMEOUT_FALLBACK_S
      try:
          parsed = float(raw)
      except ValueError:
          logging.getLogger(__name__).warning(
              'Invalid BROWSER_USE_ACTION_TIMEOUT_S=%r; falling back to %.0fs',
              raw, _ACTION_TIMEOUT_FALLBACK_S)
          return _ACTION_TIMEOUT_FALLBACK_S
      if not math.isfinite(parsed) or parsed <= 0:
          logging.getLogger(__name__).warning(
              'BROWSER_USE_ACTION_TIMEOUT_S=%r is not a finite positive number; falling back to %.0fs',
              raw, _ACTION_TIMEOUT_FALLBACK_S)
          return _ACTION_TIMEOUT_FALLBACK_S
      return parsed
  ```
  **Destino sugerido:** `tools/browser_workstation.py` — substituir o hardcoded `_DEFAULT_TIMEOUT_SECONDS = 8.0` por um parser defensivo similar, com timeouts diferenciados por tipo de ação (navigate=8s, extract=120s, screenshot=30s).
  **Benefício:** Previne hangs silenciosos e timeouts prematuros. Configuração segura via env var.
  
  ### 3.3 — Template PDF header/footer
  **Origem:** `referências/.../browser_use/tools/service.py:84-96`
  ```python
  _DEFAULT_PDF_HEADER_TEMPLATE = (
      '<div style="font-size:9px; color:#666; width:100%; padding:0 0.4in; '
      'box-sizing:border-box; text-align:right;"><span class="date"></span></div>'
  )
  _DEFAULT_PDF_FOOTER_TEMPLATE = (
      '<div style="font-size:9px; color:#666; width:100%; padding:0 0.4in; '
      'box-sizing:border-box; display:flex; justify-content:space-between;">'
      '<span class="url" style="min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;"></span>'
      '<span style="flex-shrink:0; padding-left:8px;"><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'
  )
  ```
  **Destino sugerido:** `workstation/browser_bridge.py` ou novo `workstation/browser_pdf.py` — usar como defaults para `browser_save_pdf` quando o Hermes implementar exportação PDF.
  **Benefício:** PDFs com metadados profissionais sem esforço adicional. Evita o bug comum de header/footer invisível (font-size:0 default do Chrome).
  
  ## 4. Código Adaptável
  
  ### 4.1 — Event Bus com Watchdogs Especializados
  **Conceito:** `BrowserSession` usa `bubus.EventBus` onde watchdogs independentes escutam eventos CDP e reagem assincronamente (`ResilientEventBus` em `session.py:106-131`). Cada watchdog é isolado e tem `LISTENS_TO`/`EMITS` declarativos (`dom_watchdog.py:36-37`).
  **Como adaptar:** Criar `workstation/browser_events.py` com um event bus leve (pode ser `asyncio.Queue` + subscribers). Implementar watchdogs como coroutines que escutam eventos do controller Electron via WebSocket/SSE em vez de polling HTTP. Watchdogs prioritários: `DownloadWatchdog`, `PopupWatchdog`, `NavigationWatchdog`, `ReadinessWatchdog`.
  **Benefício esperado:** Elimina polling com `time.sleep` (economia de CPU e latência). Reação proativa a downloads, popups e mudanças de DOM. Reduz round-trips desnecessários ao controller.
  
  ### 4.2 — DOM Tree Estruturada com AXTree
  **Conceito:** `DomService` combina `DOMSnapshot.captureSnapshot` + `Accessibility.getFullAXTree` para construir `EnhancedDOMTreeNode` com computed styles, bounds, interatividade, e visibilidade (`dom/service.py:45-72`). `ClickableElementDetector` classifica elementos interativos.
  **Como adaptar:** Adicionar endpoint `/v1/dom-tree` no controller Electron que retorna AXTree + DOMSnapshot combinados. No Python, criar `workstation/dom_service.py` que parseia a resposta e constrói uma representação hierárquica. Integrar com `browser_snapshot` para retornar ambos: texto legível + estrutura navegável.
  **Benefício esperado:** Modelo entende hierarquia da página, não apenas lista plana. Elementos em iframes/shadow DOM tornam-se visíveis. Filtragem por visibilidade real (computed styles) em vez de heurísticas textuais.
  
  ### 4.3 — Multi-Ação por Turno (Action Batching)
  **Conceito:** `Agent` aceita `max_actions_per_step` e o LLM pode emitir lista de ações num único output (`agent/service.py:178`). Actions são executadas sequencialmente sem novo turno LLM.
  **Como adaptar:** Estender `browser_batch_actions` para aceitar lista de `{action, arguments}` e executar atomicamente no controller. Modificar o agent loop para permitir que o LLM retorne múltiplas browser actions num único tool call. Retornar resultados agregados.
  **Benefício esperado:** Reduz round-trips LLM-controller em até 5x para tarefas multi-step (preencher formulário = type+type+click em vez de 3 turnos). Economia direta de tokens e latência.
  
  ### 4.4 — Detecção de Elementos Ocultos por Viewport
  **Conceito:** `_count_hidden_elements_in_iframes` coleta elementos interativos fora do viewport e reporta `pages_down` para guiar scroll (`dom/service.py:80-177`).
  **Como adaptar:** Adicionar campo `hidden_interactive_elements` ao snapshot response do controller. Incluir tag, label truncada, e distância em viewports. Exibir no snapshot text como hint: `[3 interactive elements below viewport, ~2 pages down]`.
  **Benefício esperado:** Agente sabe que precisa scrollar antes de tentar clicar em elemento inexistente. Elimina tentativas cegas e erros de "element not found".
  
  ### 4.5 — Message Compaction para Browser History
  **Conceito:** `MessageCompactionSettings` e `max_history_items` controlam quanto histórico de browser o LLM vê (`agent/service.py:60,182`). Snapshots antigos são resumidos ou descartados.
  **Como adaptar:** Em `browser_workstation.py`, implementar compaction de snapshots anteriores no payload model-facing: manter apenas os últimos N snapshots completos, resumir os anteriores a `{url, title, action_summary, timestamp}`. Configurar via `browser.workstation.max_snapshot_history`.
  **Benefício esperado:** Contexto do LLM não cresce linearmente com cada navegação. Economia de 30-60% de tokens em sessões longas de browser.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | Compaction de snapshots históricos (manter só últimos N completos) | 30-60% | Médio | `browser_workstation.py:966-1029` (`project_model_browser_payload`) + ausência de compaction |
  | Deduplicação de elementos já expressos em texto (já implementado parcialmente) | 15-25% | Baixo | `browser_workstation.py:966-1029` — estender para mais campos |
  | Action batching (múltiplas ações por tool call) | 20-40% | Médio | `browser_workstation.py:155` (`browser_batch_actions`) sem implementação real |
  | Filtragem de ad/tracking domains em network readiness | 5-10% | Baixo | `browser_readiness.py:19-81` — adicionar filtro de ruído |
  | Hidden elements hint em vez de snapshot completo de iframes | 10-20% | Médio | Ausência total de iframe handling |
  | Readiness semântica em vez de polling genérico | 5-15% | Baixo | `browser_readiness.py:84-127` — já existe, subutilizada |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | Event-driven readiness (watchdog) em vez de polling com sleep(0.3) | -200ms a -2s por ação | Alto | `browser_readiness.py:104,123` (`time.sleep(poll_interval)`) |
  | Timeouts diferenciados por tipo de ação (navigate=8s, extract=120s) | Evita timeouts falsos e retries | Baixo | `browser_workstation.py:42` (`_DEFAULT_TIMEOUT_SECONDS = 8.0` fixo) |
  | Action batching no controller (3 ações = 1 round-trip) | -300ms a -1s por batch | Médio | `browser_workstation.py:830-941` (dispatch individual) |
  | Cache de health probe com TTL (já implementado, otimizar TTL) | -50ms por dispatch | Baixo | `browser_workstation.py:44,486-502` (`_AVAILABILITY_CACHE_SECONDS = 0.75`) |
  | Connection pooling HTTP persistente para controller | -20ms por request | Médio | `browser_workstation.py:374-481` (nova conexão por request via `urlopen`) |
  | Parallel DOM + AXTree fetch no controller | -100ms a -500ms por snapshot | Alto | Ausência de DOM estruturado |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | DOM estruturado com AXTree em vez de inventário textual plano | Alta — modelo entende hierarquia, roles, estados | Alto | `browser_workstation.py:944-1029` (snapshot textual) |
  | Readiness semântica com diagnósticos classificados | Alta — agente sabe *por que* página não está pronta | Baixo | `browser_readiness.py:163-173` (já existe, pouco usado) |
  | Hidden elements hint com distância em viewports | Média — evita cliques cegos em elementos off-screen | Médio | Ausência total |
  | Filtragem de ad/tracking em network readiness | Média — evita falsos "not ready" por trackers | Baixo | `browser_readiness.py:19-81` |
  | Vision integrada automaticamente ao perception loop | Alta — modelo vê o que o DOM não expressa | Médio | `browser_workstation.py:151-152` (opt-in por tool call) |
  | Error classification tipada propagada ao modelo | Média — modelo distingue timeout de auth de process dead | Baixo | `browser_supervisor.py:33-43` (já existe, subutilizada no model-facing) |
  
  ## 8. Resumo Executivo
  
  ### Recomendações Priorizadas
  
  **1. Implementar Action Batching Real (Impacto: Alto, Esforço: Médio)**
  O schema já declara `browser_batch_actions` (`browser_workstation.py:155`) mas não há execução real. Implementar no controller Electron e no `_dispatch` para aceitar lista de ações e executar atomicamente. Reduz round-trips LLM-controller em até 5x para tarefas multi-step. Economia estimada de 20-40% de tokens e 300ms-1s de latência por batch. Justificativa: é a mudança com maior ROI imediato — schema existe, falta implementação.
  
  **2. Adicionar Timeouts Diferenciados por Tipo de Ação (Impacto: Alto, Esforço: Baixo)**
  Substituir `_DEFAULT_TIMEOUT_SECONDS = 8.0` fixo por tabela de timeouts: navigate=8s, click/type=5s, screenshot=30s, extract=120s, pdf=60s. Adaptar o parser defensivo de `browser-use/tools/service.py:113-163`. Previne timeouts falsos em extrações LLM e uploads, e evita hangs silenciosos. Justificativa: 8s é insuficiente para operações complexas; cópia direta do padrão da referência resolve.
  
  **3. Integrar Filtro de Ad/Tracking na Readiness (Impacto: Médio, Esforço: Baixo)**
  Copiar a lista `adDomains` de `dom_watchdog.py:119-134` e integrar em `build_readiness_expression` (`browser_readiness.py:19-81`). Ignorar requests de tracking ao avaliar network idle. Reduz falsos positivos de "not ready" e melhora objetividade da IA. Justificativa: cópia direta, zero risco, benefício imediato.
  
  **4. Implementar Compaction de Snapshots Históricos (Impacto: Alto, Esforço: Médio)**
  Em `project_model_browser_payload` (`browser_workstation.py:966-1029`), adicionar lógica para manter apenas os últimos 3-5 snapshots completos e resumir os anteriores a `{url, title, action_summary}`. Configurar via `browser.workstation.max_snapshot_history`. Economia estimada de 30-60% de tokens em sessões longas. Justificativa: snapshots repetidos são o maior consumidor de tokens em browser tasks; a deduplicação parcial existente prova que o projeto já reconhece este problema.
  
  **5. Planejar Event Bus + Watchdogs para V2 (Impacto: Transformacional, Esforço: Alto)**
  Arquitetura atual é síncrona request/response. Para V2, projetar `workstation/browser_events.py` com event bus leve e watchdogs (Download, Popup, Navigation, Readiness) que escutam eventos do controller Electron via WebSocket. Elimina polling com sleep, permite reação proativa, e habilita DOM estruturado incremental. Justificativa: é a mudança arquitetural que destrava todas as outras melhorias de velocidade e objetividade. Não é copiável diretamente (browser-use usa `bubus` async, Hermes é sync HTTP), mas o padrão é adaptável. Começar pelo design doc antes de implementar.
</agent-message>

---

<!-- Relatório 10 -->

# Relatório Comparativo: Browser Nativo Hermes Workstation vs. Referência (abundantbeing/hermes-browser-extension)
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência | Hermes Work | Gap Específico |
  | :--- | :--- | :--- | :--- |
  | **Extração de Conteúdo Estruturado** | `content-extractor.js` implementa extração heurística completa (artigo principal, metadata JSON-LD, redação de secrets, estrutura DOM) com budgets rígidos (`MAX_TEXT_CHARS=12k`, `MAX_ENVELOPE_CHARS=24k`). | `browser_bridge.py` apenas avalia expressões JS arbitrárias e salva JSON bruto; `browser_readiness.py` verifica condições binárias mas não extrai conteúdo estruturado automaticamente. | Falta um pipeline de extração de artigo/conteúdo principal nativo; o agente precisa escrever JS customizado para cada site ou receber HTML bruto massivo. |
  | **Utilitários de Texto Sem Modelo** | `text_utilities.py` oferece `clean_formatting`, `make_bullets`, `text_stats`, `diff` como tool local sem inferência (`no_model: True`), com limites de caracteres. | Não existe equivalente em `tools/` ou `workstation/`; qualquer limpeza/formatação consome tokens do modelo principal. | Operações triviais de texto (limpeza, stats, diff) gastam tokens desnecessariamente. |
  | **Leases de Aba com Geração e TTL** | `tab-leases.mjs` implementa leases por aba com `generation`, `ownership` (owned/borrowed), `taskSetId`, TTL de 30min, reclaim por geração e por desconexão. | `browser_workstation.py` usa binding simples `_BOUND_TASKS: set[str]` em memória de processo, sem TTL, sem geração, sem persistência entre restarts do agente. | Binding de tarefa perde validade após restart do processo Python; não há mecanismo de reclaim automático ou distinção owned/borrowed. |
  | **Service Worker Controller Lifecycle** | `controller-service-worker.mjs` gerencia gerações monotônicas, document generations por frame, terminal outbox, reconnect cooldown, approval store e reconcile alarm. | `browser_supervisor.py` tem circuit breaker e health probe, mas não possui conceito de document generation, approval store persistente ou reconcile periódico automatizado. | Falta reconciliação automática de estado após desconexão/restart; approvals são gerenciados separadamente sem integração ao lifecycle do controller. |
  | **Redação de Secrets na Extração** | `content-extractor.js` possui 10+ padrões regex de redação (JWT, Bearer, AWS keys, GitHub PAT, private keys) aplicados durante extração, antes de qualquer dado chegar ao modelo. | `browser_workstation.py` aplica `_force_redact()` pós-resposta usando `agent.redact`, mas a extração via `browser_bridge.py` não redige secrets no ponto de captura. | Secrets podem vazar no contexto do modelo entre a extração e a redação final; a referência redige na fonte. |
  | **Site Adapters Específicos** | `content-extractor.js` inclui adapters dedicados para GitHub, YouTube, X/Twitter, Gmail com políticas de privacidade (`ask-first` para email), extração de transcript e contexto inline. | Nenhum adapter específico por site; toda interação é genérica via CDP/evaluate. | O agente precisa descobrir manualmente a estrutura de cada site; não há política de privacidade granular por domínio. |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência | Vantagem Específica |
  | :--- | :--- | :--- | :--- |
  | **Supervisão Ativa com Circuit Breaker** | `browser_supervisor.py` implementa `CircuitBreakerState` (CLOSED/OPEN/HALF_OPEN), backoff exponencial, classificação tipada de erros (`ControllerErrorKind`), e limpeza automática de descriptor stale. | A extensão usa alarms periódicos (1min heartbeat, 5min reconcile) e reconnect cooldown, mas sem circuit breaker formal com estados e backoff progressivo. | Resiliência superior a falhas transitórias; evita tempestade de requisições quando o controller está consistentemente indisponível. |
  | **Readiness Semântica Configurável** | `browser_readiness.py` oferece `BrowserReadinessContract` com verificação de path, auth, hydration, entity identity, semantic targets e diagnóstico classificado (`AUTH_REQUIRED`, `DOM_DRIFT`, `HYDRATION_PENDING`). | A extensão não possui contrato de readiness declarativo; depende de `document.readyState` e polling genérico. | O agente pode declarar condições de prontidão específicas por página/tarefa, evitando ações prematuras e reduzindo retries cegos. |
  | **Bridge Direto para ArtifactStore** | `browser_bridge.py` salva dados extraídos diretamente no filesystem ou `ArtifactStore` sem passar pelo contexto do chat, com validação de segurança de destino (`_validate_safe_destination`). | A extensão envia todo conteúdo via mensagem/postMessage para o side panel ou gateway; não há persistência direta em artifact store. | Dados grandes nunca consomem tokens do contexto; persistência é imediata e auditável. |
  | **Fail-Closed Routing e Binding** | `browser_workstation.py` garante que uma tarefa bound nunca faz failover silencioso para outro browser; routing desabilitado por padrão; erro estruturado `WorkstationBrowserUnavailable` com `recommended_action`. | A extensão permite fallback para popup/tab quando side panel falha; não possui conceito de binding permanente por tarefa. | Segurança superior: estado de autenticação/sessão nunca é perdido por failover inadvertido. |
  | **Telemetria de Observação Nativa** | `browser_workstation.py` emite `emit_native_browser_observation` com request/response bytes, duration, error_code, stage; telemetria privada é stripped antes do modelo. | A extensão possui journal/event log, mas sem métricas estruturadas de bytes/duração integradas ao dispatch. | Observabilidade operacional rica para debugging e otimização sem poluir o contexto do modelo. |
  | **Projeção de Payload para Modelo** | `project_model_browser_payload()` elimina duplicação entre `elements[]` e snapshot text, mantendo apenas `element_index` para campos não expressos em texto; fail-open seguro. | A extensão envia extração completa sem projeção/deduplicação específica para consumo por LLM. | Redução significativa de tokens em snapshots de páginas complexas sem perda de informação acionável. |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 `text_utilities.py` → `workstation/text_utilities.py`
  **Origem:** `referências/.../companion-plugin/text_utilities.py` (113 linhas)
  **Destino sugerido:** `workstation/text_utilities.py`
  **Justificativa:** Módulo puro, sem dependências externas, sem chamadas de rede/modelo. Pode ser registrado como tool `browser_text_utility` no registry do Hermes para operações locais de texto. Os limites `MAX_TEXT_CHARACTERS=50_000` e `MAX_DIFF_CHARACTERS=20_000` são seguros para uso direto.
  
  ### 3.2 Padrões de Redação de Secrets → `agent/redact.py` (extensão)
  **Origem:** `referências/.../extension/content-extractor.js` linhas 96-108 (`SECRET_PATTERNS`)
  **Destino sugerido:** Adicionar aos padrões existentes em `agent/redact.py`
  **Justificativa:** Os 10 padrões regex cobrem JWT, Bearer, Stripe, AWS, GitHub PAT, Slack, Google API keys. O Hermes já possui `redact_sensitive_text` mas pode não cobrir todos estes padrões. Copiar os padrões faltantes aumenta a cobertura de redação.
  
  ### 3.3 Funções de Normalização de Whitespace → `workstation/browser_readiness.py`
  **Origem:** `referências/.../extension/content-extractor.js` linhas 116-125 (`normalizeReadableWhitespace`)
  **Destino sugerido:** Adicionar como helper em `browser_readiness.py` ou módulo utilitário compartilhado
  **Justificativa:** Normalização robusta de whitespace (`\r\n`, `\t\f\v`, múltiplas quebras) útil para comparação de texto em readiness checks e extração. A implementação atual do Hermes não normaliza whitespace de forma consistente.
  
  ## 4. Código Adaptável
  
  ### 4.1 Content Extraction Pipeline Heurístico
  **Conceito:** O algoritmo de `bestCandidate()` + `candidateScore()` de `content-extractor.js` (linhas 391-430) identifica o bloco de conteúdo principal de qualquer página usando scoring heurístico (parágrafos, sentenças, headings, link density, hints de class/id).
  **Como adaptar:** Implementar como expressão JS injetável via `browser_bridge.browser_save_json()` ou como função Python que processa HTML capturado. Integrar com `BrowserReadinessContract` como condição `content_extracted`.
  **Benefício esperado:** Elimina a necessidade de selectors específicos por site para extração de artigo; reduz tokens enviados ao modelo em 40-70% vs. HTML bruto.
  
  ### 4.2 Lease Store com Geração e TTL
  **Conceito:** `createTabLeaseStore()` de `tab-leases.mjs` com geração monotônica, ownership, TTL, reclaim por expiração/geração/desconexão, e snapshot versionado.
  **Como adaptar:** Evoluir `_BOUND_TASKS` em `browser_workstation.py` para um `BrowserTaskLeaseStore` com TTL configurável, geração vinculada ao `operation_id`/`run_id`, e persistência atômica no mesmo arquivo `browser-tasks.json`. Adicionar `reclaim_expired()` ao supervisor loop.
  **Benefício esperado:** Bindings sobrevivem a restarts do agente; tarefas órfãs são reclaim automaticamente; previne stale bindings que causam erros `NO_BOUND_TAB`.
  
  ### 4.3 Document Generation Tracking
  **Conceito:** `documentGenerations` map em `controller-service-worker.mjs` (linha 290-293) rastreia a geração do documento por `tabId:frameId` e rejeita ações com `stale_document` quando a página mudou antes da execução.
  **Como adaptar:** Adicionar campo `document_generation` ao payload de `browser_navigate` e ações subsequentes em `browser_workstation.py`. O controller Electron já retorna `safeUrl` e `revision`; estender para incluir um hash/counter de documento. Rejeitar mutações quando a geração mudou.
  **Benefício esperado:** Previne race conditions onde o agente age sobre um DOM stale após navegação/redirecionamento não observado; elimina classe inteira de bugs de automação.
  
  ### 4.4 Site Adapter Framework
  **Conceito:** `inspectSite()` / `adapterIdForHost()` de `content-extractor.js` (linhas 1665-1691) com adapters dedicados (GitHub, YouTube, X, Gmail) e políticas de privacidade (`ask-first`, `automatic-read-only`).
  **Como adaptar:** Criar `workstation/site_adapters.py` com registry de adapters por hostname. Cada adapter retorna `policy`, `capabilities`, `context_text`, `actions`. Integrar com `browser_readiness.py` e approval gates. Começar com 2-3 adapters prioritários.
  **Benefício esperado:** Extração confiável e segura de sites complexos sem prompts ad-hoc; política de privacidade enforcement automático.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Text utilities sem modelo (`clean_formatting`, `text_stats`, `diff`) | 5-15% | Baixo | Ref `text_utilities.py` L83-112 |
  | Content extraction heurística (artigo principal vs. HTML bruto) | 40-70% | Médio | Ref `content-extractor.js` L391-430 |
  | Projeção de elements já existente (dedup elements/snapshot) | 10-25% | Já implementado | `browser_workstation.py` L966-1029 |
  | Limites de envelope de extração (`MAX_ENVELOPE_CHARS=24k`) | 20-40% | Médio | Ref `content-extractor.js` L10-11 |
  | Journal/event log com limite bounded (`max=500`) | 5-10% | Baixo | Ref `tools.py` L115-123 |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Readiness semântica vs. sleep fixo | Alto (elimina waits desnecessários) | Já implementado | `browser_readiness.py` L84-127 |
  | Health probe cacheado (0.75s TTL) | Médio (reduz probes redundantes) | Já implementado | `browser_workstation.py` L44, L485-502 |
  | Document generation check (fail-fast em DOM stale) | Alto (evita ação + retry em DOM errado) | Médio | Ref `controller-service-worker.mjs` L290-293 |
  | Circuit breaker com half-open probe | Médio (recuperação mais rápida) | Já implementado | `browser_supervisor.py` L249-258 |
  | Terminal outbox para comandos interrompidos | Baixo-Médio (evita re-execução incerta) | Médio | Ref `controller-service-worker.mjs` L137-186 |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Redação de secrets na fonte (extração) | Alto (previne vazamento no contexto) | Médio | Ref `content-extractor.js` L96-108 |
  | BrowserReadinessContract declarativo | Alto (condições objetivas vs. heurística do modelo) | Já implementado | `browser_readiness.py` L131-173 |
  | Fail-closed routing (sem failover silencioso) | Alto (estado de sessão preservado) | Já implementado | `browser_workstation.py` L1076-1081 |
  | Policy `ask-first` para sites privados (Gmail, DMs) | Alto (consentimento explícito) | Médio | Ref `content-extractor.js` L1676-1688 |
  | Telemetria stripped antes do modelo | Médio (dados operacionais não influenciam raciocínio) | Já implementado | `browser_workstation.py` L921-926 |
  
  ## 8. Resumo Executivo
  
  ### Recomendações Priorizadas
  
  1. **Copiar `text_utilities.py` como tool nativo** (Impacto: Alto, Esforço: Baixo)
     - Registro imediato como `browser_text_utility` no registry. Elimina inferência para limpeza, stats e diff de texto. ROI imediato em economia de tokens.
  
  2. **Implementar content extraction heurística** (Impacto: Muito Alto, Esforço: Médio)
     - Portar o algoritmo `bestCandidate` + `candidateScore` como expressão JS injetável ou módulo Python. Reduz 40-70% dos tokens em extração de páginas de conteúdo. É o maior ganho disponível.
  
  3. **Evoluir `_BOUND_TASKS` para lease store com TTL e geração** (Impacto: Alto, Esforço: Médio)
     - Adicionar TTL, geração monotônica, persistência e reclaim automático. Resolve stale bindings pós-restart e previne erros `NO_BOUND_TAB`. Melhora resiliência operacional.
  
  4. **Adicionar document generation tracking** (Impacto: Alto, Esforço: Médio)
     - Rastrear geração do documento por tab/frame e rejeitar ações stale. Elimina race conditions entre navegação e ação. Requer extensão do protocolo Electron controller.
  
  5. **Estender redação de secrets para o ponto de extração** (Impacto: Alto, Esforço: Baixo-Médio)
     - Aplicar padrões de redação da referência em `browser_bridge.py` antes de qualquer dado entrar no contexto. Complementa a redação pós-resposta existente. Defesa em profundidade.
  
  ### Arquivos-Chave Analisados
  
  **Hermes Workstation:**
  - `workstation/browser_supervisor.py` (303 linhas) — Circuit breaker, health probe, error classification
  - `workstation/browser_readiness.py` (174 linhas) — Semantic readiness, diagnostic contracts
  - `workstation/browser_bridge.py` (122 linhas) — Direct artifact/file bridge
  - `workstation/ARCHITECTURE.md` (413 linhas) — BrowserTask lifecycle, routing, safety invariants
  - `tools/browser_workstation.py` (1103 linhas) — Controller dispatch, binding, projection, telemetry
  
  **Referência (abundantbeing/hermes-browser-extension):**
  - `extension/content-extractor.js` (2892 linhas) — Full extraction pipeline, site adapters, redaction
  - `extension/lib/controller-service-worker.mjs` (400+ linhas lidas) — Lease/generation/lifecycle management
  - `extension/lib/tab-leases.mjs` (300 linhas lidas) — Tab lease store com TTL/generação/ownership
  - `extension/background.js` (990 linhas) — Service worker boot, alarms, message routing
  - `companion-plugin/tools.py` (156 linhas) — ContextVar lease handlers, consume-once authorization
  - `companion-plugin/text_utilities.py` (113 linhas) — Bounded local text operations
  - `companion-plugin/policy.py` (25 linhas) — Access policy (v0.1 context-only)
</agent-message>

---

<!-- Relatório 11 -->

# Relatório Comparativo: Browser Hermes Workstation vs camofox-browser
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (camofox) | Hermes Work | Gap Específico |
  |---|---|---|---|
  | Anti-detection / Stealth | Engine-level via Camoufox: fingerprint C++, canvas/WebGL noise, navigator spoofing, humanize:true (`anti-detection.md` §1-3) | Nenhum mecanismo anti-detection no browser Electron nativo; depende do Chromium stock do Electron sem patches de fingerprint | Hermes não tem camada de stealth; sites com bot-detection bloqueiam o browser nativo imediatamente |
  | Multi-user identity isolation | Context pool por `userId` com perfis persistentes isolados em `~/.camofox/profiles/`, LRU eviction, max sessions configurável (`session-management.md` §2) | Um único perfil persistente compartilhado (`%LOCALAPPDATA%\HermesWorkstation\Browser\User Data`); sem isolamento por usuário/tarefa no nível de browser context | Tarefas diferentes compartilham cookies/localStorage; contaminação cruzada de identidade entre tarefas concorrentes |
  | CLI/API para automação externa | CLI completa com 20+ comandos (`open`, `snapshot`, `click`, `type`, `navigate`, `screenshot`, `wait`, `search`, `extract-structured`, `eval`, `get-text`, `get-links`, `get-tabs`, `go-back`, `go-forward`) + API REST (`core.ts`, `navigation.ts`, `content.ts`) | Sem CLI ou API externa; apenas tool calls internas via `_dispatch()` em `browser_workstation.py` | Impossível automatizar o browser Hermes fora do agente; debugging manual e scripting externo são inviáveis |
  | Search macros / motores pré-configurados | 8 motores pré-configurados com URL templates (`google`, `youtube`, `amazon`, `bing`, `reddit`, `duckduckgo`, `github`, `stackoverflow`) em `content.ts` L48-69 | Nenhum macro de busca; agente precisa construir URLs manualmente ou usar `web_search` separado | Overhead de tokens para construir URLs de busca; inconsistência entre buscas |
  | Extract-structured com schema JSON | `POST /tabs/:tabId/extract-structured` aceita schema JSON ou `@file` para extração tipada (`content.ts` L92-115) | Extração via `evaluate_fn` genérico em `browser_bridge.py`; sem validação de schema integrada | Agente precisa escrever JS ad-hoc para cada extração estruturada; sem garantia de conformidade |
  | Session save/load (cookies) | `camofox session save/load/list/delete` com persistência em `~/.camofox/sessions/` modo 0600 (`session-management.md` §3) | Sem mecanismo de save/load de sessão; cookies persistem apenas no perfil Electron global | Não é possível salvar estado de autenticação entre execuções de tarefas diferentes |
  | Server daemon management | `ServerManager` com PID file atômico, health probe, idle timeout, auto-start (`manager.ts`) | Supervisor com circuit breaker mas sem auto-start do controller; depende do Desktop estar rodando (`browser_supervisor.py`) | Se o Desktop crashar, o browser fica indisponível até restart manual |
  | Element targeting dual (ref + CSS) | `toElementTarget()` distingue `e\d+` refs de CSS selectors automaticamente (`selector.ts`) | Refs `@eN` no snapshot text, mas sem parser unificado no lado Python; agente escolhe ref OU selector manualmente | Ambiguidade quando agente mistura refs e selectors; sem fallback automático |
  | Display mode toggle (headless/headed/virtual) | `POST /sessions/:userId/toggle-display` com suporte a virtual display Xvfb (`anti-detection.md` §6) | Sempre headed dentro do Electron Desktop; sem opção headless ou virtual | Consumo de recursos desnecessário para tarefas puramente extrativas |
  | Rate limiting / concurrency control | Per-user operation limit + per-tab lock + context pool cap (`session-management.md` §5) | Circuit breaker global no supervisor; sem granularidade por tarefa ou tab | Uma tarefa problemática pode tripudiar o circuit breaker para todas as tarefas |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (camofox) | Vantagem Específica |
  |---|---|---|---|
  | Segurança loopback-only | Controller descriptor com bearer token aleatório, URL restrita a `http://127.0.0.1:*`, nunca exposto ao modelo (`browser_workstation.py` L369-370) | API REST em porta configurável sem auth obrigatória; `CAMOFOX_API_KEY` é opcional (`anti-detection.md` §8) | Hermes elimina superfície de ataque remota por design; camofox permite acesso não-autenticado |
  | Binding de tarefa durável | BrowserTask com lifecycle create/show/hide/park/destroy, binding canônico persistente em `browser-tasks.json`, fail-closed on controller loss (`ARCHITECTURE.md` L279-331) | Tabs efêmeras por `tabId`; sem conceito de tarefa durável; display toggle invalida tabs | Hermes garante que uma tarefa mantém sua página através de hide/show/restart; camofox perde estado |
  | Lease de controle humano | `BrowserControlLeaseManager` com fence_token, parent/child task registration, assert_action_allowed (`browser_workstation.py` L1085-1092) | Sem lease; qualquer caller com userId pode operar qualquer tab | Prevenção de conflitos agente/humano no mesmo tab; camofox não tem proteção |
  | Redaction forçado de resultados | `_force_redact()` + `redact_sensitive_text()` em todos os resultados antes de cruzar boundary da tool (`browser_workstation.py` L927) | Sem redaction; screenshots e texto podem conter secrets vazadas ao modelo | Proteção contra leakage de credenciais/tokens em snapshots |
  | Readiness semântica observável | `build_readiness_expression()` com selector + all_text + any_text + min_text_length + DOM settlement (`browser_readiness.py` L19-81) | `wait` com condição simples (selector/navigation/networkidle) em `content.ts` L300-352 | Hermes evita sleep() arbitrários com condições compostas; camofox depende de polling JS inline |
  | Bridge direto para ArtifactStore | `browser_capture_to_artifact()` persiste resultado JS diretamente no store sem passar por base64/chat (`browser_bridge.py` L85-121) | Screenshots salvos como arquivo local; sem integração com artifact store | Zero overhead de serialização/deserialização; dados nunca entram no contexto do modelo |
  | Error classification tipada | `ControllerErrorKind` enum com 9 categorias + `WorkstationBrowserError` com error_code, retryable, state_changed, recommended_action (`browser_supervisor.py` L33-43, `browser_workstation.py` L52-106) | Erros genéricos HTTP; sem classificação estruturada | Recuperação programática baseada em tipo de erro; camofox exige parsing de texto |
  | Journal/canonical events | `/events?limit=N&task_id=X` com bounded canonical journal (`browser_workstation.py` L515-527) | Sem journal de eventos; histórico é log de servidor | Auditabilidade e replay de ações de browser |
  | Snapshot projection inteligente | `project_model_browser_payload()` remove elementos duplicados já expressos no texto do snapshot, mantendo apenas campos extras (`browser_workstation.py` L966-1029) | Snapshot retorna árvore completa sem deduplicação | Economia significativa de tokens em páginas densas |
  | Validação de URL segura | `is_always_blocked_url()` + `normalize_url_for_request()` + `check_website_access()` antes de cada navegação (`browser_workstation.py` L36-37) | Sem validação de URL; qualquer URL é navegável | Prevenção de SSRF e acesso a endpoints internos |
  | Telemetria local estruturada | `emit_native_browser_observation()` com action/result/duration/request_bytes/response_bytes/error_code (`browser_workstation.py` L865-921) | Logs de servidor não-estruturados | Observabilidade sem exfiltração; métricas de performance por ação |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 Selector parser dual (ref vs CSS)
  **Origem:** `referências/02-Browser-Automacao-Web/camofox-browser-main/src/cli/utils/selector.ts`
  ```typescript
  const ELEMENT_REF_PATTERN = /^e\d+$/;
  export function isElementRef(input: string): boolean { return ELEMENT_REF_PATTERN.test(input); }
  export function isSelector(input: string): boolean { return !isElementRef(input); }
  export function toElementTarget(input: string): { selector: string } | { ref: string } {
      return isElementRef(input) ? { ref: input } : { selector: input };
  }
  ```
  **Destino sugerido:** `workstation/browser_selector.py` (novo módulo)
  **Adaptação:** Traduzir para Python como função pura. Integrar em `_dispatch()` de `browser_workstation.py` para normalizar argumentos `ref`/`selector` antes de enviar ao controller.
  
  ### 3.2 Search engine URL templates
  **Origem:** `referências/02-Browser-Automacao-Web/camofox-browser-main/src/cli/commands/content.ts` L48-69
  ```typescript
  function toSearchUrl(engine: SearchEngine, query: string): string {
      const encoded = encodeURIComponent(query);
      switch (engine) {
          case 'google': return `https://www.google.com/search?q=${encoded}`;
          case 'youtube': return `https://www.youtube.com/results?search_query=${encoded}`;
          // ... 6 more engines
      }
  }
  ```
  **Destino sugerido:** `workstation/search_macros.py` (novo módulo)
  **Adaptação:** Portar como dict Python `{engine: url_template}`. Expor via `browser_navigate` quando URL começa com `@macro_name`.
  
  ### 3.3 PID file atomic write pattern
  **Origem:** `referências/02-Browser-Automacao-Web/camofox-browser-main/src/cli/server/manager.ts` L182-187
  ```typescript
  private writePidFileAtomic(pid: number): void {
      this.ensureDirectories();
      const tempPath = `${this.pidFilePath}.tmp-${process.pid}-${Date.now()}`;
      writeFileSync(tempPath, `${pid}\n`, 'utf8');
      renameSync(tempPath, this.pidFilePath);
  }
  ```
  **Destino sugerido:** `workstation/browser_supervisor.py` — substituir escrita direta do descriptor
  **Adaptação:** Usar `tempfile.NamedTemporaryFile` + `os.replace()` em Python para escrita atômica do descriptor em `workstation_control_path()`. Previne descriptor corrompido por crash mid-write.
  
  ### 3.4 Port-in-use check via socket probe
  **Origem:** `referências/02-Browser-Automacao-Web/camofox-browser-main/src/cli/server/manager.ts` L210-228
  **Destino sugerido:** `workstation/browser_supervisor.py` — adicionar `is_port_in_use()` ao supervisor
  **Adaptação:** Usar `socket.socket()` com timeout curto para verificar se porta do controller está ocupada antes de tentar health probe. Evita falso negativo de "connection refused" vs "port not bound yet".
  
  ## 4. Código Adaptável
  
  ### 4.1 Context pool com LRU eviction por userId
  **Conceito:** Pool de contextos isolados por identidade com capacidade máxima e evicção LRU (`session-management.md` §2).
  **Como adaptar:** Criar `BrowserContextPool` em `workstation/browser_context_pool.py` que mapeia `task_id -> isolated_session`. Quando o pool excede `max_contexts`, evicta o contexto menos recentemente usado (park + destroy). Cada contexto teria seu próprio cookie/storage namespace dentro do Electron Session existente.
  **Benefício esperado:** Isolamento real entre tarefas concorrentes; eliminação de contaminação cruzada de cookies/auth state. Impacto alto em confiabilidade de workflows multi-tarefa.
  
  ### 4.2 Fallback chain com legacy endpoint retry
  **Conceito:** Cada comando tenta endpoint primário, cai para legacy em 404 (`content.ts` L130-145 para get-text, L163-174 para get-url, L198-211 para get-links).
  **Como adaptar:** Em `browser_workstation.py::_request_json()`, adicionar tabela de fallback endpoints por ação. Quando controller retorna 404 para nova rota, tentar rota legada automaticamente. Útil durante transições de versão do controller Electron.
  **Benefício esperado:** Compatibilidade retroativa sem breaking changes; redução de erros durante upgrades do Desktop.
  
  ### 4.3 Wait com Promise-based selector polling in-page
  **Conceito:** `wait` command gera Promise JS com polling interno de 100ms e deadline (`content.ts` L336-343), evitando round-trips repetidos.
  **Como adaptar:** Em `browser_readiness.py::wait_for_condition()`, substituir polling Python-side (sleep + evaluate loop) por uma única chamada `evaluate` com Promise interna. O JS roda o loop no renderer e só retorna quando pronto ou timeout.
  **Benefício esperado:** Redução de 10-30x em round-trips HTTP para waits longos. Latência cai de N*poll_interval para ~0ms overhead.
  
  ### 4.4 Session save/load de cookies
  **Conceito:** Exportar/importar cookies como JSON com modo 0600 (`session-management.md` §3).
  **Como adaptar:** Adicionar `browser_session_save(task_id, name)` e `browser_session_load(name, task_id)` como novas actions no controller Electron. Persistir em `%LOCALAPPDATA%\HermesWorkstation\Browser\Sessions\`. Cookies exportados via CDP `Network.getAllCookies`, importados via `Network.setCookie`.
  **Benefício esperado:** Reutilização de autenticação entre execuções; eliminação de login repetitivo em tarefas recorrentes.
  
  ### 4.5 Display mode toggle para tarefas headless
  **Conceito:** Alternar entre headed/headless/virtual por usuário (`anti-detection.md` §6).
  **Como adaptar:** Adicionar `browser_set_display_mode(mode)` no controller. Para tarefas puramente extrativas (scraping, leitura), usar modo offscreen/background no Electron WebContentsView. Manter headed apenas para tarefas que requerem interação humana.
  **Benefício esperado:** Redução de consumo de GPU/RAM em 40-60% para tarefas headless; mais tarefas concorrentes viáveis.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | Snapshot projection já implementada (element_index) | 30-50% em snapshots densos | Já feito | `browser_workstation.py` L966-1029 `project_model_browser_payload()` |
  | Wait in-page com Promise (eliminar polling Python) | 15-25% em workflows com múltiplos waits | Médio | `browser_readiness.py` L84-127 `wait_for_condition()` vs camofox `content.ts` L336-343 |
  | Extract-structured com schema (evitar JS ad-hoc) | 10-20% em extrações estruturadas | Médio | `browser_bridge.py` L36-82 vs camofox `content.ts` L92-115 |
  | Search macros (evitar construção manual de URL) | 5-10% em buscas frequentes | Baixo | Inexistente no Hermes vs camofox `content.ts` L48-69 |
  | Session save/load (evitar re-login) | 20-40% em tarefas recorrentes autenticadas | Alto | Inexistente no Hermes vs camofox `session-management.md` §3 |
  | Bridge direto ArtifactStore (evitar base64 no contexto) | 40-70% em capturas grandes | Já parcial | `browser_bridge.py` L85-121 `browser_capture_to_artifact()` |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | Wait in-page Promise (1 round-trip vs N polls) | 10-30x mais rápido em waits >2s | Médio | `browser_readiness.py` L104-123 poll loop vs camofox `content.ts` L336-343 |
  | Health probe cache TTL (já implementado 0.75s) | Evita probes redundantes | Já feito | `browser_workstation.py` L44 `_AVAILABILITY_CACHE_SECONDS = 0.75` |
  | PID alive check otimizado (psutil → ctypes fallback) | ~5ms vs ~50ms no Windows | Já feito | `browser_supervisor.py` L88-112 |
  | Descriptor escrita atômica (evitar corrupção/retry) | Elimina retries por descriptor corrompido | Baixo | `browser_supervisor.py` L146-151 vs camofox `manager.ts` L182-187 |
  | Port-in-use pre-check (evitar health probe em porta morta) | ~200ms economizados em cold start | Baixo | Inexistente vs camofox `manager.ts` L210-228 |
  | Context pool reuse (evitar relaunch de browser context) | 2-5s economizados por tarefa subsequente | Alto | Perfil único Hermes vs camofox pool LRU |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | ReadinessContract com diagnostic estruturado | Classificação determinística de falhas (AUTH_REQUIRED, DOM_DRIFT, HYDRATION_PENDING) em vez de texto livre | Já feito | `browser_readiness.py` L131-173 |
  | Error classification tipada (9 categorias) | Recuperação programática baseada em enum, não em parsing de string | Já feito | `browser_supervisor.py` L33-43 |
  | Force-redact em todos os resultados | Secrets nunca chegam ao modelo; elimina alucinação baseada em dados sensíveis | Já feito | `browser_workstation.py` L927 |
  | URL safety validation pré-navegação | Bloqueio determinístico de SSRF/internal URLs antes do request | Já feito | `browser_workstation.py` L36-37 |
  | BrowserTask receipt validation (run_id/operation_id/revision) | Detecção de drift de binding entre tarefa e página; fail-closed em mismatch | Já feito | `browser_workstation.py` L230-322 |
  | Extract-structured com schema validation | Garantia de conformidade do output; schema_valid: false explícito | Médio | Inexistente vs camofox `content.ts` L92-115 |
  | Snapshot element dedup verification | Verificação byte-exata de que texto do snapshot corresponde aos elementos antes de projetar | Já feito | `browser_workstation.py` L998-1012 |
  
  ## 8. Resumo Executivo
  
  ### Top 5 Recomendações Priorizadas
  
  **1. Wait in-page com Promise (Impacto ALTO / Esforço MÉDIO)**
  Substituir o polling Python-side em `browser_readiness.py::wait_for_condition()` por uma única chamada `evaluate` com Promise interna no renderer, conforme padrão do camofox (`content.ts` L336-343). O polling atual faz N round-trips HTTP (poll_interval=0.3s, timeout=15s = até 50 requests). A versão in-page faz 1 request e resolve internamente. Impacto: 10-30x mais rápido em waits, 15-25% de economia de tokens em workflows com múltiplas esperas. Implementação: modificar `build_readiness_expression()` para retornar uma Promise que resolve/rejeita internamente.
  
  **2. Session save/load de cookies (Impacto ALTO / Esforço ALTO)**
  Implementar export/import de cookies por tarefa, adaptando o padrão do camofox (`session-management.md` §3). Adicionar actions `browser_session_save` e `browser_session_load` no controller Electron, persistindo em `%LOCALAPPDATA%\HermesWorkstation\Browser\Sessions\` com modo restritivo. Impacto: elimina re-login em tarefas recorrentes (20-40% de tokens), habilita workflows multi-etapa com autenticação persistente. Justificativa técnica: o perfil único atual compartilha cookies globalmente; isolamento por tarefa requer save/load explícito.
  
  **3. Search macros integrados (Impacto MÉDIO / Esforço BAIXO)**
  Portar o dict de URL templates do camofox (`content.ts` L48-69) para `workstation/search_macros.py` e integrar em `browser_navigate` quando URL começa com `@`. Impacto: 5-10% de economia em buscas, consistência garantida, agente não precisa memorizar URL formats. Esforço mínimo: ~30 linhas de Python + integração no dispatcher.
  
  **4. Descriptor escrita atômica (Impacto MÉDIO / Esforço BAIXO)**
  Adotar o padrão write-temp-rename do camofox (`manager.ts` L182-187) em `browser_supervisor.py` para escrita do descriptor e em `browser_workstation.py` para `browser-tasks.json`. Previne corrupção por crash mid-write que causa retries desnecessários e falso PROCESS_DEAD. Esforço: ~15 linhas, risco zero.
  
  **5. Context pool com isolamento por tarefa (Impacto ALTO / Esforço ALTO)**
  Criar `BrowserContextPool` com LRU eviction adaptando o modelo do camofox (`session-management.md` §2). Cada tarefa ganha um contexto isolado dentro do Electron Session existente. Impacto: elimina contaminação cruzada de cookies/auth entre tarefas concorrentes, habilita multi-user workflows reais. Justificativa: o gap de isolamento é o maior déficit arquitetural atual; sem ele, tasks concorrentes são fundamentalmente inseguras. Esforço alto porque requer mudanças no controller Electron (CDP session isolation), mas o padrão do camofox prova a viabilidade.
</agent-message>

---

<!-- Relatório 12 -->

# Relatório Comparativo: Browser Hermes Workstation vs browser-harness (Referência)
  
  ### 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (browser-harness) | Hermes Work | Gap Específico |
  | :--- | :--- | :--- | :--- |
  | **Gravação/Replay Visual** | `recorder.py` grava screenshot + evento JSONL por ação automaticamente; suporta vídeo posterior via `video.py`. | Sem gravação nativa de sessão ou replay visual. Telemetria (`emit_native_browser_observation`) captura métricas, não frames. | Ausência de "flight recorder" visual para debug e treinamento de agentes. |
  | **Interação com Frameworks JS** | `fill_input()` (helpers.py:208-247) usa focus + select-all + key events + dispatch synthetic input/change para compatibilidade React/Vue. | `browser_type` via controller HTTP; sem evidência de injeção de eventos sintéticos para frameworks reativos no código Python. | Risco de falha em formulários controlados por estado (React/Vue) onde `insertText` puro não dispara atualizações. |
  | **Espera de Rede (Network Idle)** | `wait_for_network_idle()` (helpers.py:526-559) monitora eventos CDP `Network.*` filtrados por sessão ativa. | `browser_readiness.py` foca em DOM/texto/selector; sem espera baseada em tráfego de rede. | SPAs que carregam dados assincronamente sem mudar o DOM imediatamente podem ser considerados "prontos" prematuramente. |
  | **Debug Visual de Cliques** | `BH_DEBUG_CLICKS=1` sobrepõe cruz vermelha no screenshot pós-clique (helpers.py:175-192). | Sem mecanismo de overlay visual para verificação de coordenadas de clique. | Dificuldade de diagnosticar cliques errados em testes ou automações complexas. |
  | **Gestão de Abas Multi-sessão** | `switch_tab(activate=False)` permite attach sem roubar foco do usuário; marcador 🐴 no título. | Controller HTTP expõe abas, mas o modelo de "task binding" do Hermes é mais rígido; não há evidência de attach silencioso sem ativação visual. | Agente pode interromper fluxo do usuário ao inspecionar abas em segundo plano. |
  
  ### 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência | Vantagem Específica |
  | :--- | :--- | :--- | :--- |
  | **Segurança e Isolamento** | Loopback-only + bearer token aleatório + fail-closed binding + redação forçada de resultados (`_force_redact`). | Token em arquivo port (Windows) ou socket permissions (POSIX); URLs scrubbed apenas na gravação. | Modelo de ameaça superior: tokens nunca vazam para o modelo, binding impede failover silencioso para browser não-autenticado. |
  | **Supervisão de Runtime** | `BrowserRuntimeSupervisor` com circuit breaker, classificação de erros tipados, backoff exponencial e limpeza de descriptor stale. | Daemon restart via `ensure_daemon()`; health check básico via `/json/version`. | Resiliência operacional muito maior; recuperação automática de estados degradados sem intervenção externa. |
  | **Readiness Semântica** | `BrowserReadinessContract` valida path, auth, hydration, entity identity e semantic targets antes de prosseguir. | Polling genérico (`wait_for_element`, `wait_for_load`). | Contratos declarativos evitam corridas contra DOM transitório; readiness é uma propriedade do negócio, não do DOM. |
  | **Integração com Durable Execution** | Browser actions são steps compilados em WorkPlan; journal persistente; idempotency via operation_id + call_key. | Gravação é observacional apenas; não participa de execução durável ou replay transacional. | Browser é parte de um workflow atômico e recuperável, não uma sequência de comandos frágeis. |
  | **Projeção de Payload para IA** | `project_model_browser_payload()` remove duplicação elements/snapshot text; mantém apenas campos não-expressos textualmente. | Retorna dados brutos do CDP ou screenshots integrais. | Economia direta de tokens de entrada sem perda de informação acionável. |
  
  ### 3. Código Copiável Diretamente
  
  | Trecho | Origem | Destino Sugerido | Justificativa |
  | :--- | :--- | :--- | :--- |
  | `_scrub_url()` regex + função | `recorder.py:44-53` | `workstation/browser_telemetry.py` (novo ou existente) | Sanitização de URLs em logs/telemetria do Hermes; padrão de segurança já validado. |
  | `_CTX_JS` expressão de contexto de página | `recorder.py:58-67` | `workstation/browser_readiness.py` como constante | Captura url/title/viewport/focused-element box em uma única avaliação JS; útil para enriquecer observações. |
  | `_decode_unserializable_js_value()` | `helpers.py:102-113` | `workstation/browser_bridge.py` | Trata NaN/Infinity/BigInt retornados por `evaluate`; evita crashes em extrações de dados numéricos. |
  | `_is_illegal_return_error()` + retry com wrapper | `helpers.py:147-149, 585-591` | `workstation/browser_bridge.py` | Torna `js()` resiliente a expressões com `return` top-level; melhora confiabilidade de avaliações arbitrárias. |
  | `spawn_kwargs()` para daemon detach | `_ipc.py:72-80` | `workstation/browser_supervisor.py` (se spawn local for adicionado) | Flags corretas para Windows (`CREATE_NO_WINDOW \| CREATE_NEW_PROCESS_GROUP`) e POSIX (`start_new_session`). |
  
  ### 4. Código Adaptável
  
  | Conceito | Como Adaptar | Benefício Esperado |
  | :--- | :--- | :--- |
  | **Session Recording (events.jsonl + frames)** | Implementar `workstation/browser_recorder.py` que escuta `emit_native_browser_observation` e, quando habilitado, salva screenshot via controller `/screenshot` + evento estruturado. Integrar com `ArtifactStore` para persistência. | Debug visual offline; dataset para fine-tuning de políticas de clique; auditoria humana de execuções autônomas. |
  | **`fill_input()` com eventos sintéticos** | Adicionar endpoint `/v1/action/fill_smart` no controller Electron que executa a sequência focus→select-all→keypress→dispatchEvent. Expor como `browser_fill` no tool schema. | Compatibilidade real com React/Vue/Angular sem depender de `type_text` ingênuo. |
  | **`wait_for_network_idle()` via CDP events** | Estender `browser_readiness.py` com `wait_for_network_idle(evaluate_fn, idle_ms=500)` que drena eventos do controller `/events?kind=network` e mede silêncio. | Elimina sleeps arbitrários após submits/fetches; readiness baseada em sinal objetivo. |
  | **Tab marker (🐴) e attach silencioso** | Adicionar campo `silent_attach` ao payload de `browser_navigate`/`browser_snapshot`; controller marca aba ativa com emoji apenas quando visível. | Usuário identifica visualmente qual aba o agente controla; inspeções em background não roubam foco. |
  | **Auto-recording com idle rollover** | Portar lógica `_auto_is_stale()` + `_auto_idle_gap()` para o recorder do Hermes; usar timestamp da última observação como gatilho de rotação. | Sessões longas são segmentadas automaticamente; evita arquivos gigantes e facilita correlação tarefa↔gravação. |
  
  ### 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Projeção de elementos já implementada | 15-25% em snapshots densos | Já feito | `tools/browser_workstation.py:966-1029` |
  | Scrubbing de URLs secretas em observações | 2-5% (evita redação posterior pelo modelo) | Baixo | `recorder.py:44-53` → adaptar para telemetry |
  | Contexto de página compacto (`_CTX_JS`) vs múltiplas chamadas | 5-10% por step | Médio | `recorder.py:58-67` → consolidar em `browser_snapshot` |
  | Network idle como readiness (evita retries cegos) | 8-12% em fluxos SPA | Médio | `helpers.py:526-559` → portar para readiness |
  | Máscara de senha em texto gravado (`_mask`) | 1-3% (segurança + tokens) | Baixo | `recorder.py:339-343` → aplicar em bridge |
  
  ### 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Health probe cacheado (0.75s TTL) | Evita 1 round-trip HTTP por tool call | Já feito | `browser_workstation.py:485-502` |
  | Screenshot IPC timeout dedicado (60s vs 5s) | Previne timeouts falsos em páginas pesadas | Baixo | `helpers.py:45` → documentar/controller ajustar |
  | `wait_for_network_idle` substitui sleep fixo | -2s a -10s por step em média | Médio | `helpers.py:526-559` |
  | Attach silencioso sem ativação visual | -200ms por inspeção (sem paint/reflow forçado) | Médio | `helpers.py:409-427` → controller endpoint |
  | Batch actions nativo (`browser_batch_actions`) | Reduz N round-trips para 1 | Alto (controller) | Schema já listado em `browser_workstation.py:155` |
  
  ### 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Readiness semântica contratual | Elimina "acho que carregou"; readiness = booleano verificável | Já feito | `browser_readiness.py:131-173` |
  | Frame error explícito em gravação | Modelo sabe *por que* um frame falhou, não apenas que falta | Baixo | `recorder.py:298-304` → adotar em telemetry |
  | Entity identity check em readiness | Detecta drift de entidade (ex: perfil errado) antes de agir | Médio | `browser_readiness.py:153-154` |
  | Surrogate replacement em strings CDP | Previne crash de encoding que corrompe trace inteiro | Baixo | `recorder.py:305-310` → aplicar em bridge |
  | Operation idempotency via call_key | Replay seguro de mutações; modelo pode re-tentar sem medo | Já feito | `browser_workstation.py:849-857` |
  
  ### 8. Resumo Executivo
  
  1.  **Portar `fill_input()` com eventos sintéticos** (Alto impacto / Médio esforço): A incompatibilidade com frameworks reativos é o gap funcional mais crítico. Implementar como endpoint no controller Electron e expor via `browser_fill` elimina uma classe inteira de falhas silenciosas em formulários modernos.
  
  2.  **Implementar Session Recording nativo** (Alto impacto / Médio esforço): A ausência de gravação visual impede debug, auditoria e geração de datasets. Reutilizar `emit_native_browser_observation` + `_CTX_JS` + `_scrub_url` cria um flight recorder seguro integrado ao ArtifactStore com esforço moderado.
  
  3.  **Adicionar `wait_for_network_idle` à readiness** (Médio impacto / Baixo esforço): Substitui heurísticas de DOM/texto por sinal objetivo de quiescência de rede. Portar diretamente de `helpers.py:526-559` adaptando para drenar eventos via controller HTTP. Reduz timeouts falsos e sleeps arbitrários.
  
  4.  **Habilitar attach silencioso + tab marker** (Médio impacto / Médio esforço): Melhora UX durante automação paralela. Usuário vê qual aba é controlada (🐴) e inspeções em background não interrompem trabalho manual. Requer endpoint novo no controller mas é arquiteturalmente simples.
  
  5.  **Consolidar contexto de página em única avaliação JS** (Baixo-Médio impacto / Baixo esforço): `_CTX_JS` da referência obtém url/title/viewport/focused-box/dpr em um único round-trip. Substitui múltiplas chamadas dispersas no readiness/bridge, economizando latência e tokens.
</agent-message>

---

<!-- Relatório 13 -->

# Relatório Comparativo: Browser Hermes Workstation vs. BrowserTransactionBench (BTB)
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (BTB) | Hermes Work | Gap Específico |
  |---|---|---|---|
  | **Verificação de resultado por estado durável** | `btb/oracle/score.py` compara snapshots SQLite completos (before/after) com contratos `intended_final`/`forbidden_final` por efeito (read/save/send). Avaliação é determinística e independente do modelo. | `browser_readiness.py` verifica apenas condições DOM (selector, texto, comprimento). Não há verificação de efeito colateral em base de dados ou estado canônico pós-ação. | Hermes não possui oracle de estado durável; readiness é puramente visual/DOM, incapaz de detectar se uma mutação realmente persistiu ou violou restrições. |
  | **Proveniência e receipt imutável** | `btb/harness/engine.py` + `manifest.py` geram receipts schema-v2 com SHA-256 de source tree, runtime tree, task definition, prompt, baseline config e evaluation. Cada run é criptograficamente auditável. | `browser_workstation.py` grava journal projections e telemetry (`emit_native_browser_observation`), mas sem hash de proveniência, sem binding criptográfico entre ação/resultado/fonte. | Ausência de cadeia de custódia verificável para ações de browser; journal é observacional, não forense. |
  | **Política de ações congelada e auditável** | `browser_use_policy.py` define SHA-256 de cada action schema e identidade semântica de callbacks de navegação. O engine valida em runtime que o registry de ações coincide exatamente com o frozen policy (`_validate_browser_use_action_registry`). | `_WORKSTATION_SCHEMA_TOOLS` em `browser_workstation.py` é um frozenset de nomes, sem hash de schema, sem validação de que o controller expõe exatamente as ações esperadas. | Hermes não detecta drift de capabilities do controller; se o Electron controller mudar schemas, o agente descobre apenas em runtime via erro. |
  | **Isolamento de fixture por run** | `runtime.py:ManagedRunEnvironment` cria tempdir, SQLite, socket ephemeral, servidor Uvicorn e thread dedicados por run. Porta é pré-bindada atomicamente. Teardown garante cleanup mesmo em falha. | Browser usa perfil persistente `%LOCALAPPDATA%\HermesWorkstation\Browser\User Data`. Múltiplas tasks compartilham o mesmo perfil Chromium. Não há isolamento de estado entre tarefas concorrentes. | Estado de cookies/localStorage/IndexedDB vaza entre BrowserTasks; não há garantia de que uma task não vê artefatos de outra. |
  | **Avaliação de crença do agente (belief calibration)** | `score.py` extrai `Claim` estruturada do agente (`believes: sent/not_sent/unknown`) e cruza com estado real para classificar calibração (`calibrated/miscalibrated/insufficient_evidence`). | Nenhuma extração estruturada de crença. O modelo reporta livremente em texto natural; não há reconciliação automática entre afirmação e realidade. | Impossível medir objetivamente se o agente "sabe" quando falhou ou teve sucesso; confiabilidade é inferida, não medida. |
  | **Repetition study com plano imutável** | `repetition.py` gera StudyPlan com seed, ordering determinístico, run IDs derivados de SHA-256, e exige receipts canônicos antes de agregar. Suporta resume e detecção de drift de prompt. | Sem infraestrutura de estudos repetidos. Cada execução é ad-hoc; não há mecanismo para comparar taxa de sucesso across runs ou detectar regressão. | Não há linha de base estatística para medir melhoria ou regressão do browser agent. |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (BTB) | Vantagem Específica |
  |---|---|---|---|
  | **Supervisão ativa com circuit breaker** | `browser_supervisor.py:BrowserRuntimeSupervisor` implementa health probe, classificação de erros tipados (`ControllerErrorKind`), backoff exponencial e circuit breaker com estados CLOSED/OPEN/HALF_OPEN. Detecção de PID morto via psutil/ctypes. | BTB usa health check simples (`verify_fixture_identity`) sem retry logic, sem circuit breaker, sem classificação de erros. Falhas são terminais. | Hermes recupera-se automaticamente de falhas transitórias do controller; BTB falha imediatamente. |
  | **Binding de task ao runtime com fail-closed** | `browser_workstation.py` mantém `_BOUND_TASKS` e `_canonical_browser_task_binding()`. Uma vez bound, controller loss nunca faz fallback silencioso para outro browser. Routing é explícito e configurável. | BTB não tem conceito de task binding. Cada run é independente; não há risco de failover, mas também não há continuidade de sessão. | Hermes garante que uma tarefa autenticada nunca migra para um browser com estado diferente, prevenindo perda de sessão/auth. |
  | **Bridge direta DOM→filesystem sem base64** | `browser_bridge.py:browser_save_json` e `browser_capture_to_artifact` extraem dados estruturados do DOM direto para arquivo/ArtifactStore, bypassing chat context e codificação base64. Validação de segurança `_validate_safe_destination`. | BTB não tem bridge de extração estruturada. Dados passam pelo LLM como observação textual ou screenshot. | Economia massiva de tokens e latência para tarefas de extração; dados chegam íntegros ao destino sem round-trip pelo modelo. |
  | **Readiness semântica substituindo sleep arbitrário** | `browser_readiness.py:build_readiness_expression` gera probe JS que verifica selector, all_text, any_text, min_text_length e dom_ready em polling com timeout. `BrowserReadinessContract` avalia auth, hydration, entity_identity, semantic_targets. | BTB depende de `max_steps` e wall-clock budget do browser-use framework. Não há readiness probe customizável; o agente decide quando parar baseado em observações. | Hermes evita waits arbitrários e detecta condições específicas de página; BTB gasta steps/tokens esperando ou agindo prematuramente. |
  | **Redação forçada de dados sensíveis** | `_force_redact()` em `browser_workstation.py` sanitiza resultados antes de cruzar o boundary da tool. Tokens, URLs internas e dados privados nunca chegam ao modelo. Controller descriptor nunca é exposto. | BTB registra sensitive values no receipt (`builder.register_sensitive_value`) para redação posterior, mas o LLM vê a observação completa durante execução. | Hermes previne vazamento em tempo real; BTB confia que o LLM não memorizará dados sensíveis durante a sessão. |
  | **Integração nativa com Electron WebContentsView** | Arquitetura usa Chromium embutido no Desktop via CDP loopback autenticado. Perfil persistente, tabs compartilhadas, lifecycle park/show/hide/destroy. Zero dependência externa de browser. | BTB usa Playwright ou browser-use (Chromium externo headless). Cada run spawn um processo browser separado. | Zero overhead de processo externo; reuso do runtime existente; persistência de perfil sem configuração adicional. |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 Oracle Snapshot e Evaluation Contract
  **Origem:** `referências/02-Browser-Automacao-Web/lamenting-hawthorn--browserbench/btb/oracle/score.py` (linhas 33-93, 95-108, 597-702)
  **Destino sugerido:** `workstation/browser_oracle.py` (novo módulo)
  
  As classes `OracleSnapshot`, `Evaluation` e a função `evaluate()` podem ser copiadas integralmente. Elas são puras, sem dependências externas além de dataclasses e pathlib. A função `snapshot()` precisaria ser adaptada para ler do ArtifactStore ou de um endpoint do controller ao invés de SQLite direto, mas a lógica de comparação before/after e os checks `_read_checks`, `_save_checks`, `_send_checks` são reutilizáveis como contratos de verificação pós-ação de browser.
  
  ### 3.2 Belief Claim Parser
  **Origem:** `referências/.../btb/oracle/claim.py` (não lido integralmente, mas referenciado em score.py linhas 15, 601, 606-607)
  **Destino sugerido:** `workstation/browser_claim.py` (novo módulo)
  
  O parser de `Claim` estruturada (`believes`, `subject`, `body`) deve ser copiado para permitir que o Hermes extraia e valide crenças do agente contra estado real. Isso habilita medição de belief calibration.
  
  ### 3.3 Fixture Navigation Policy (exact-origin enforcement)
  **Origem:** `referências/.../btb/harness/engine.py` (linhas 476-616: `_FixtureOrigin`, `_FixtureNavigationPolicy`, `_strict_urlsplit`, `_canonical_host`)
  **Destino sugerido:** `workstation/browser_navigation_policy.py` (novo módulo) ou integrar em `browser_workstation.py`
  
  A validação estrita de origem HTTP(S) com normalização IDNA/IPv6 e rejeição de URLs relativas/credenciais é diretamente aplicável como gate de segurança para `browser_navigate` no Hermes. Previne open-redirect e SSRF via normalização ambígua.
  
  ### 3.4 Wilson Score Interval
  **Origem:** `referências/.../btb/harness/repetition_summary.py` (linhas 56-77)
  **Destino sugerido:** `workstation/telemetry/statistics.py` (novo módulo)
  
  A implementação de Wilson score interval com Decimal precision é útil para qualquer métrica de sucesso de browser actions no Hermes. É autocontida e sem dependências.
  
  ## 4. Código Adaptável
  
  ### 4.1 Receipt Builder com Proveniência Criptográfica
  **Conceito BTB:** `ReceiptBuilder` em `engine.py` captura source tree SHA, runtime tree SHA, task definition SHA, prompt SHA, baseline config, e escreve receipt JSON atomicamente. Cada campo é verificado antes de publicação.
  **Como adaptar:** Criar `workstation/browser_receipt.py` que, após cada `browser_*` action bem-sucedida, constrói um receipt contendo: SHA do descriptor do controller, SHA da task definition compilada, operation_id, timestamp, e hash do resultado redigido. Armazenar no ArtifactStore ou journal.
  **Benefício esperado:** Audit trail forense para debugging e compliance; capacidade de provar que uma ação foi executada contra o controller correto com os parâmetros corretos.
  
  ### 4.2 Managed Run Environment com Isolamento Per-Task
  **Conceito BTB:** `ManagedRunEnvironment` em `runtime.py` cria tempdir, DB, socket e servidor isolados por run com pre-binding atômico de porta.
  **Como adaptar:** Para BrowserTasks que exigem isolamento (ex: testes, scraping de múltiplas contas), criar `workstation/browser_isolated_session.py` que provisiona um WebContentsView com profile temporário e cookie store independente. Reusar o padrão de pre-binding e teardown garantido.
  **Benefício esperado:** Eliminação de vazamento de estado entre tasks concorrentes; capacidade de executar tarefas conflitantes em paralelo.
  
  ### 4.3 Frozen Action Schema Validation
  **Conceito BTB:** `browser_use_policy.py` mantém SHA-256 de cada action schema e valida em runtime que o registry coincide.
  **Como adaptar:** Em `browser_workstation.py`, após ler o descriptor do controller, fazer GET `/schema` ou equivalente e comparar SHA-256 dos schemas retornados contra um frozen set em `workstation/browser_schema_policy.py`. Falhar closed se houver drift.
  **Benefício esperado:** Detecção precoce de incompatibilidade entre agente e controller; prevenção de chamadas a ações inexistentes ou modificadas.
  
  ### 4.4 Repetition Study Framework
  **Conceito BTB:** `repetition.py` gera planos imutáveis com seed determinístico, executa runs em ordem randomizada, exige receipts canônicos e agrega com Wilson intervals.
  **Como adaptar:** Criar `workstation/benchmarks/browser_study.py` que define tasks de browser (navigate+extract, form fill, etc.), gera plano com N repetições, executa via `call_workstation_browser`, coleta receipts e produz relatório de taxa de sucesso com intervalos de confiança.
  **Benefício esperado:** Linha de base estatística para medir impacto de mudanças no browser agent; detecção de regressão automatizada.
  
  ### 4.5 Belief Calibration Loop
  **Conceito BTB:** `score.py` cruza `Claim.believes` com `effect_state` real para classificar calibração. `_belief_calibration()` distingue calibrated/miscalibrated/insufficient_evidence.
  **Como adaptar:** Após cada browser mutation, extrair claim estruturada do response do modelo (via prompt engineering ou parsing), comparar com oracle state, e registrar calibration score no telemetry. Usar para ajustar prompts ou adicionar verification steps.
  **Benefício esperado:** Métrica objetiva de confiabilidade do agente; feedback loop para melhorar instruções e reduzir falsos positivos/negativos.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | **Adotar bridge DOM→artifact para extração** | 40-70% em tarefas de extração | Baixo | `browser_bridge.py:browser_save_json` já existe; falta adoção ampla nos skills/workflows |
  | **Project_model_browser_payload elimina elements duplicados** | 15-30% em snapshots | Já implementado | `browser_workstation.py:project_model_browser_payload` (linhas 966-1029) |
  | **Readiness probe substitui multi-step observation loops** | 20-40% em waits | Médio | `browser_readiness.py:wait_for_condition` vs. múltiplos `browser_snapshot` calls |
  | **Oracle evaluation evita re-observação pelo modelo** | 30-50% em verificação | Alto | Adaptar `score.py:evaluate` para verificar estado sem chamar LLM |
  | **Belief extraction estruturada reduz chain-of-thought** | 10-20% em respostas | Médio | Adaptar `claim.py` para exigir JSON estruturado ao invés de prosa |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | **Pre-binding de porta para isolated sessions** | -50ms a -200ms por task isolada | Médio | `runtime.py:ManagedRunEnvironment.__enter__` (linhas 166-206) |
  | **Health probe cache (já implementado)** | -750ms em chamadas consecutivas | Já feito | `browser_workstation.py:_AVAILABILITY_CACHE_SECONDS=0.75` |
  | **Circuit breaker evita retries inúteis** | -1s a -5s em falhas persistentes | Já feito | `browser_supervisor.py:can_attempt` (linhas 249-258) |
  | **Readiness poll interval tuning** | -100ms a -500ms por wait | Baixo | `browser_readiness.py:poll_interval=0.3` poderia ser adaptativo |
  | **Parallel readiness probes para múltiplas condições** | -30% a -60% em páginas complexas | Médio | `build_readiness_expression` já combina condições; falta paralelismo跨 conditions |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | **Oracle-based evaluation substitui self-report** | Alta: elimina viés de auto-avaliação | Alto | `score.py:evaluate` com before/after snapshots |
  | **Belief calibration tracking** | Alta: mede gap entre afirmação e realidade | Médio | `score.py:_belief_calibration` (linhas 577-594) |
  | **Frozen action policy validation** | Média: previne capability drift silencioso | Médio | `browser_use_policy.py:BROWSER_USE_SCHEMA_DIGESTS` |
  | **Receipt-bound proveniência** | Alta: auditoria independente de claims | Alto | `engine.py:ReceiptBuilder` + `manifest.py` |
  | **Effect-state classification (zero/exactly_one/multiple)** | Alta: categorização objetiva de outcomes | Médio | `score.py:_cardinality` e `_headline` (linhas 126-131, 466-521) |
  
  ## 8. Resumo Executivo
  
  ### Recomendação 1: Implementar Oracle de Estado Durável (Alto impacto / Alto esforço)
  Adaptar `btb/oracle/score.py` para `workstation/browser_oracle.py`. O Hermes atualmente verifica readiness DOM mas não valida efeitos colaterais. Um oracle que compare estado antes/depois de mutations (via ArtifactStore, API responses, ou DB queries) eliminaria a dependência de self-report do modelo e habilitaria verificação objetiva de sucesso. Justificativa: todas as dimensões de "PIOR" na seção 1 derivam desta ausência.
  
  ### Recomendação 2: Adotar Bridge DOM→Artifact Universalmente (Alto impacto / Baixo esforço)
  `browser_bridge.py` já existe mas é subutilizado. Skills e workflows que extraem dados devem usar `browser_save_json`/`browser_capture_to_artifact` ao invés de passar conteúdo pelo chat. Justificativa: economia de 40-70% de tokens em extração, zero perda de fidelidade, e dados chegam estruturados ao destino.
  
  ### Recomendação 3: Congelar e Validar Action Schemas do Controller (Médio impacto / Médio esforço)
  Criar `workstation/browser_schema_policy.py` com hashes de schemas esperados e validar contra `/schema` endpoint do controller em startup. Justificativa: previne drift silencioso de capabilities que hoje só aparece como erro em runtime; custo é baixo e proteção é alta.
  
  ### Recomendação 4: Implementar Belief Extraction Estruturada (Médio impacto / Médio esforço)
  Exigir que respostas de browser mutations incluam `{"believes": "sent/not_sent/unknown", ...}` e validar contra oracle. Registrar calibration score no telemetry. Justificativa: transforma confiabilidade de subjetiva para mensurável; habilita feedback loop automático para prompt improvement.
  
  ### Recomendação 5: Criar Browser Repetition Study Framework (Médio impacto / Alto esforço)
  Adaptar `repetition.py` para `workstation/benchmarks/browser_study.py` com planos imutáveis, receipts e Wilson intervals. Justificativa: sem linha de base estatística, não há como distinguir melhoria real de variação aleatória; essencial para qualquer otimização futura ter evidência quantitativa.
</agent-message>

---

<!-- Relatório 14 -->

# Relatório Comparativo: Browser Nativo Hermes Workstation vs browser-use--desktop
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (browser-use--desktop) | Hermes Work | Gap Específico |
  |---|---|---|---|
  | Acesso direto ao CDP | `cdp.ts` expõe `WebContents.debugger` e WebSocket com API unificada `send(method, params, sessionId?)` + eventos tipados; agentes chamam `session.Page.navigate`, `session.Input.dispatchMouseEvent` diretamente via REPL (`repl.ts`) | `browser_workstation.py` usa HTTP REST sobre loopback (`_request_json("POST", "/v1/action", ...)`, linha 874); cada ação é um payload JSON serializado/desserializado; sem acesso CDP direto pelo agente | Latência extra de serialização HTTP + impossibilidade de usar domínios CDP não mapeados como tool; referência tem zero overhead IPC para CDP nativo Electron |
  | Screenshot-to-file nativo | `repl.ts` linhas 19-22: `$BU_OUTPUTS_DIR` recebe PNGs automaticamente; screenshots salvos em disco nunca entram no stdout/chat como base64; agente decide salvar apenas quando útil para o usuário | `browser_bridge.py` e `_dispatch` em `browser_workstation.py` retornam resultados via JSON; screenshots passam por `_force_redact` e `project_model_browser_payload` mas não há caminho nativo screenshot→arquivo sem passar pelo contexto do modelo | Screenshots consomem tokens de contexto mesmo quando são apenas para verificação interna do agente; referência separa visão interna (base64 efêmero) de artefato persistente (arquivo) |
  | Sistema de Skills de domínio | 50+ domain-skills em `stock/domain-skills/` cobrindo Amazon, LinkedIn, GitHub, Reddit, SEC EDGAR, etc.; `agent-skill search` indexa e carrega sob demanda; interaction-skills para uploads, dialogs, iframes, shadow DOM | Sem equivalente; `workstation/` não possui diretório de skills de domínio nem mecanismo de busca/indexação de receitas de automação por site | Cada automação de site específico exige redescoberta de seletores/fluxos pelo modelo; referência reusa conhecimento cristalizado em markdown versionado |
  | Persistência de estado entre evals | `repl.ts` linha 19-20: `globalThis.session`, `globalThis.lastTitle` persistem entre chamadas `/eval`; estado CDP sobrevive a múltiplas invocações do agente sem reconexão | Cada chamada `_dispatch` em `browser_workstation.py` é stateless do ponto de vista do agente; binding existe (`_BOUND_TASKS`) mas é apenas um flag de roteamento, não estado de página reutilizável | Agente precisa re-navegar ou re-avaliar contexto que já estava disponível; referência mantém sessão CDP quente com domínios habilitados |
  | Bootstrap automático de runtime | `harness.ts` `bootstrapHarness()` materializa helpers, AGENTS.md, domain-skills, interaction-skills e browser-harness-js CLI em `<userData>/harness/` a cada launch; versão stock sempre sincronizada | Sem bootstrap automático de artefatos de automação; `browser_readiness.py` gera probes JS inline mas não distribui receitas ou SDKs persistentes | Novos recursos de automação exigem deploy manual ou edição de código Python; referência atualiza habilidades de automação junto com o app |
  | Detecção de expressão vs statement | `repl.ts` `isExpression()` (linhas 60-66) detecta se input é expressão simples e auto-envolve com `return`; multi-statement requer `return` explícito; top-level await suportado | `browser_readiness.py` `build_readiness_expression()` gera IIFE fixo; `browser_bridge.py` sempre envolve em `(() => { ... })()` sem detecção de tipo | Menor flexibilidade para evals ad-hoc do agente; referência permite tanto one-liners quanto scripts complexos com a mesma interface |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência | Vantagem Específica |
  |---|---|---|---|
  | Circuit breaker e supervisão ativa | `browser_supervisor.py` implementa `CircuitBreakerState` (CLOSED/OPEN/HALF_OPEN), backoff exponencial, classificação de erros em 9 categorias (`ControllerErrorKind`), limpeza automática de descriptor stale, health probe com timeout de 0.5s | Sem circuit breaker; `cdp.ts` emite evento `__detached` mas não há retry/backoff/classificação estruturada; falhas propagam diretamente ao agente | Resiliência operacional superior; falhas transitórias não derrubam tarefas longas; classificação permite recuperação diferenciada por tipo de erro |
  | Binding de tarefa fail-closed | `browser_workstation.py` linhas 1060-1082: uma vez bound, controller loss levanta `WorkstationBrowserUnavailable` e NUNCA faz fallback silencioso para browser externo com estado/auth diferente; canonical binding verifica conflito de sessão | Sem conceito de task binding; agente pode trocar de target/browser entre ações sem garantia de continuidade de estado/auth | Segurança de identidade de tarefa; evita vazamento de credenciais ou estado de autenticação entre contextos distintos |
  | Readiness semântica estruturada | `browser_readiness.py` `BrowserReadinessContract` avalia captcha, auth, hydration, entity_identity, semantic_targets, DOM drift; `browser_diagnostic()` classifica falhas em AUTH_REQUIRED/DOM_DRIFT/HYDRATION_PENDING/CANVAS_OR_NON_DOM_SURFACE | Sem readiness contract; agente depende de `session.waitFor('Page.loadEventFired')` genérico ou polling manual via `Runtime.evaluate` | Detecção de estados de página semanticamente ricos; evita ações prematuras em SPAs, páginas com captcha ou surfaces não-DOM |
  | Projeção model-facing com deduplicação | `browser_workstation.py` `project_model_browser_payload()` (linhas 966-1029): remove array `elements` quando snapshot text já contém inventário equivalente; preserva apenas campos extras (`tag`, `testid`, `name`) em `element_index`; validação linha-a-linha antes de projetar | Sem projeção; `browser-harness-js` retorna dados brutos do CDP; agente recebe DOM completo sem filtragem | Economia massiva de tokens em snapshots de páginas densas; contrato model-facing estável independente da representação interna |
  | Bridge segura com validação de destino | `browser_bridge.py` `_validate_safe_destination()` verifica resolved path contra allowed_roots; `BridgeSecurityError` impede escrita fora de workspaces permitidos; extração direta DOM→filesystem sem passar por base64/chat | Outputs vão para `$BU_OUTPUTS_DIR` sem validação de path além do diretório configurado; sem mecanismo de allowed_roots explícito | Prevenção de path traversal e escrita acidental em locais sensíveis; extração estruturada sem inflar contexto |
  | Telemetria nativa de observação | `browser_workstation.py` linhas 865-926: `emit_native_browser_observation()` registra attempt/success/error com duration_ms, request_bytes, response_bytes, error_code; telemetria privada stripada antes de cruzar boundary do modelo (`strip_private_browser_telemetry`) | Sem telemetria estruturada de ações de browser; logs existem (`logs/browser.log`) mas não são emitidos como eventos tipados por ação | Observabilidade operacional granular; métricas de latência/tamanho disponíveis para otimização sem vazar dados privados ao modelo |
  | Lease de controle humano | `browser_workstation.py` linha 1086-1092: `BrowserControlLeaseManager.assert_action_allowed()` verifica fence_token e parent-child task relationship antes de dispatch; sub-tasks registram parent explicitamente | Sem lease/fence token; agente tem controle irrestrito do browser uma vez conectado | Prevenção de ações concorrentes conflitantes; hierarquia de controle pai-filho para tarefas compostas |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 Dual CDP Transport (WebContents + WebSocket)
  **Origem:** `referências/02-Browser-Automacao-Web/browser-use--desktop/app/src/main/hl/cdp.ts` (linhas 37-86, classe `WebContentsCdpClient`)
  **Destino sugerido:** Novo arquivo `workstation/electron_cdp_transport.py` ou integração no main process do Desktop via TypeScript
  **Justificativa:** O Hermes já roda em Electron mas acessa o browser via HTTP REST. Este código mostra como usar `WebContents.debugger.attach('1.3')` e `sendCommand(method, params, sessionId)` diretamente, eliminando a camada HTTP para operações CDP internas. A classe `WebSocketCdpClient` (linhas 92-158) serve como fallback para browsers remotos. Licença MIT compatível.
  
  ### 3.2 CDP Event Ring Buffer
  **Origem:** `referências/02-Browser-Automacao-Web/browser-use--desktop/app/src/main/hl/context.ts` (linhas 14, 21-33, 61-74)
  **Destino sugerido:** `workstation/browser_supervisor.py` como complemento ao health probe atual
  **Justificativa:** Buffer FIFO de 500 eventos CDP (`EVENT_BUFFER_SIZE = 500`) com allow-list de domínios relevantes (`Page.frameNavigated`, `Network.responseReceived`, `Runtime.consoleAPICalled`, etc.). Permite diagnóstico post-mortem de falhas de automação sem logging verboso. O Hermes supervisor atualmente só vê health/success/failure binário.
  
  ### 3.3 Screenshot-to-File Pattern
  **Origem:** `referências/02-Browser-Automacao-Web/browser-use--desktop/app/src/main/hl/engines/browserHarnessEnv.ts` (linha 22: `env.BU_OUTPUTS_DIR`) + `repl.ts` AGENTS.md (seção "Verification Loop")
  **Destino sugerido:** `workstation/browser_bridge.py` como nova função `browser_screenshot_to_artifact()`
  **Justificativa:** Padrão onde screenshots de verificação interna NUNCA entram no contexto do modelo como base64; apenas screenshots explicitamente salvos em `$BU_OUTPUTS_DIR` aparecem como artefatos. Reduz tokens de visão em 80-95% para tarefas de automação típicas.
  
  ### 3.4 Expression Detection Heuristic
  **Origem:** `referências/02-Browser-Automacao-Web/browser-use--desktop/app/src/main/hl/stock/browser-harness-js/sdk/repl.ts` (linhas 60-66, função `isExpression`)
  **Destino sugerido:** `workstation/browser_readiness.py` como helper `detect_eval_mode()`
  **Justificativa:** Detecta se input é expressão simples (auto-return) vs statement (requer return explícito). Evita wrapping desnecessário em IIFE para consultas rápidas como `document.title`.
  
  ## 4. Código Adaptável
  
  ### 4.1 Domain Skills Catalog
  **Conceito:** Diretório `stock/domain-skills/` com 50+ playbooks de sites específicos (Amazon, LinkedIn, GitHub, SEC EDGAR, etc.) em markdown, materializados automaticamente no userData do usuário a cada launch (`harness.ts` `materializeDomainSkills()`).
  **Como adaptar:** Criar `workstation/domain_skills/` com playbooks em markdown seguindo o formato da referência. Integrar com o sistema de skills existente do Hermes (`skills/AGENTS.md`). Adicionar mecanismo de busca similar ao `agent-skill search` usando o curator existente (`agent/curator*.py`).
  **Benefício esperado:** Redução de 40-60% em tentativas/erros para automação de sites conhecidos; conhecimento de seletores, fluxos e armadilhas reutilizado entre sessões sem consumir contexto permanente.
  
  ### 4.2 Persistent CDP Session State
  **Conceito:** `repl.ts` mantém `Session` singleton com domínios Page/DOM/Runtime/Network habilitados; `globalThis.*` persiste entre evals; conexão CDP sobrevive a múltiplas chamadas do agente sem reconexão.
  **Como adaptar:** Modificar o controller Electron do Hermes para manter uma sessão CDP persistente por BrowserTask (não por ação). Expor `evaluate(expression, persist_state=True)` que reusa a sessão. Armazenar variáveis de página no WebContents via `Runtime.evaluate` com `objectGroup`.
  **Benefício esperado:** Eliminação de overhead de reconexão CDP (~50-200ms por ação); estado acumulado de scraping/automação disponível entre steps sem serialização.
  
  ### 4.3 Harness Bootstrap Automático
  **Conceito:** `harness.ts` `bootstrapHarness()` garante que `<userData>/harness/` contenha versões atualizadas de helpers, AGENTS.md, domain-skills, interaction-skills e browser-harness-js CLI; staleness markers forçam reescrita quando necessário; user skills em `skills/` são preservados.
  **Como adaptar:** Adicionar hook no startup do Hermes Desktop que materializa `workstation/harness/` com receitas de automação, schemas de readiness contracts e helpers JS. Usar hash de conteúdo como staleness marker. Preservar customizações do usuário em subdiretório separado.
  **Benefício esperado:** Atualizações de capacidade de automação entregues junto com o app sem migração manual; consistência garantida entre versão do app e receitas disponíveis.
  
  ### 4.4 Skill Lifecycle Management
  **Conceito:** `agent-skill create/search/view/patch/delete/validate` como CLI completo para gerenciar skills de automação; threshold sugerido de 5+ tool calls antes de criar skill; validação pós-escrita.
  **Como adaptar:** Estender o skill curator do Hermes (`agent/curator*.py`) com comandos equivalentes. Integrar com o Experience Compiler existente para promover padrões de automação bem-sucedidos em skills reutilizáveis.
  **Benefício esperado:** Aprendizado incremental de automação; procedimentos descobertos em uma sessão tornam-se disponíveis para futuras sem re-prompting.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | Screenshot-to-file (verificação interna sem base64 no contexto) | 80-95% em tarefas com múltiplas verificações visuais | Médio | `repl.ts` AGENTS.md seção "Verification Loop"; `browserHarnessEnv.ts` linha 22 |
  | Domain skills para sites conhecidos (evita redescoberta de seletores/fluxos) | 40-60% em automação de sites cobertos | Alto | `stock/domain-skills/` (50+ arquivos); `harness.ts` `materializeDomainSkills()` |
  | Persistent CDP session state (elimina re-avaliação de contexto de página) | 20-30% em tarefas multi-step | Médio | `repl.ts` linhas 19-20 (`globalThis.session`); `context.ts` ring buffer |
  | Expression detection (evita IIFE wrapping para consultas simples) | 5-10% em evals frequentes | Baixo | `repl.ts` `isExpression()` linhas 60-66 |
  | Projection validation já existente pode ser estendida para mais tool results | 10-15% adicional | Baixo | `browser_workstation.py` `project_model_browser_payload()` linhas 966-1029 |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | CDP direto via WebContents.debugger (elimina HTTP REST round-trip) | -50 a -200ms por ação | Médio | `cdp.ts` `WebContentsCdpClient.send()` linhas 71-76 vs `browser_workstation.py` `_request_json()` linha 874 |
  | Persistent CDP connection (sem reconnect por ação) | -50 a -200ms por ação após primeira | Médio | `repl.ts` `connectToAssignedTarget()` linhas 28-53; `context.ts` `createContext()` |
  | Parallel domain enable (Page/DOM/Runtime/Network em Promise.all) | -30 a -100ms no setup inicial | Baixo | `repl.ts` linhas 45-50 `Promise.all([session.Page.enable(), ...])` |
  | Health probe cache (já existe no Hermes, 0.75s TTL) | Já implementado | N/A | `browser_workstation.py` `_AVAILABILITY_CACHE_SECONDS = 0.75` linha 44 |
  | Screenshot async com file write (não bloqueia eval) | -100 a -500ms para screenshots grandes | Médio | `repl.ts` AGENTS.md: `Bun.write()` é async; vs sync base64 encode+decode |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | Readiness contracts semânticos (já existem no Hermes) | Alta - evita ações prematuras em SPAs/captcha/auth walls | Já implementado | `browser_readiness.py` `BrowserReadinessContract` linhas 131-160 |
  | Domain skills com seletores verificados | Alta - reduz hallucinação de seletores/fluxos | Alto | `stock/domain-skills/` com seletores testados por site |
  | CDP event ring buffer para diagnóstico | Média - evidência objetiva de falhas em vez de inferência | Médio | `context.ts` `BufferedCdpEvent[]` linhas 21-33, 61-74 |
  | Fence token / control lease (já existe no Hermes) | Alta - previne race conditions em tarefas compostas | Já implementado | `browser_workstation.py` linha 1092 `assert_action_allowed(task_id, action, fence_token=...)` |
  | Error classification estruturada (já existe no Hermes) | Alta - recuperação diferenciada por tipo de erro | Já implementado | `browser_supervisor.py` `ControllerErrorKind` 9 categorias linhas 33-43 |
  | Snapshot projection com validação linha-a-linha | Média - garante que texto e elementos estão consistentes antes de enviar ao modelo | Já implementado | `browser_workstation.py` linhas 1000-1012 validação exata de inventory grammar |
  
  ## 8. Resumo Executivo
  
  ### Recomendação 1: Implementar Screenshot-to-File Nativo (Impacto: Muito Alto / Esforço: Médio)
  O maior ganho imediato de tokens. Atualmente, toda verificação visual do agente passa por base64 no contexto do modelo. Adicionar `browser_screenshot_to_artifact()` em `browser_bridge.py` que salva PNG diretamente no ArtifactStore via `browser_capture_to_artifact()`, e modificar o prompt/tool schema para distinguir "screenshot interno" (efêmero, não entra no contexto) de "screenshot para usuário" (persiste como artefato). Baseado no padrão `BU_OUTPUTS_DIR` da referência. Impacto estimado: 80-95% de redução em tokens de visão para tarefas de automação típicas.
  
  ### Recomendação 2: CDP Direto via WebContents.debugger (Impacto: Alto / Esforço: Médio)
  Eliminar a camada HTTP REST para operações CDP internas. O Hermes já roda em Electron; usar `WebContents.debugger.attach('1.3')` e `sendCommand()` diretamente (como em `cdp.ts` `WebContentsCdpClient`) reduz latência em 50-200ms por ação e habilita acesso a domínios CDP não mapeados como tools. Manter o HTTP REST como fallback para compatibilidade e debugging. Requer mudança no main process do Desktop + adapter Python.
  
  ### Recomendação 3: Domain Skills Catalog Integrado (Impacto: Alto / Esforço: Alto)
  Criar repositório de playbooks de automação por site em `workstation/domain_skills/`, materializados automaticamente no runtime do usuário. Começar com os 10-15 sites mais comuns (LinkedIn, GitHub, Amazon, Google Search, etc.) adaptando os markdowns da referência. Integrar com o skill curator existente do Hermes para busca e carregamento sob demanda. Impacto estimado: 40-60% de redução em tentativas/erros para sites cobertos.
  
  ### Recomendação 4: Persistent CDP Session por BrowserTask (Impacto: Médio-Alto / Esforço: Médio)
  Manter sessão CDP persistente por BrowserTask (não por ação), com domínios Page/DOM/Runtime/Network habilitados e estado `globalThis` reutilizável entre evals. Elimina reconnect overhead e permite acumulação de estado de scraping/automação. Baseado no padrão `Session` singleton de `repl.ts`. Complementa o binding fail-closed existente do Hermes.
  
  ### Recomendação 5: CDP Event Ring Buffer no Supervisor (Impacto: Médio / Esforço: Baixo)
  Adicionar buffer FIFO de 500 eventos CDP ao `BrowserRuntimeSupervisor` usando a allow-list de domínios da referência (`Page.frameNavigated`, `Network.responseReceived`, `Runtime.consoleAPICalled`, etc.). Fornece diagnóstico post-mortem objetivo para falhas de automação sem logging verboso. Pode ser implementado como extensão do health probe existente em `browser_supervisor.py`.
</agent-message>

---

<!-- Relatório 15 -->

# Relatório Comparativo: Browser Nativo Hermes Workstation vs. BrowserClaw
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (BrowserClaw) | Hermes Work | Gap Específico |
  |---|---|---|---|
  | Detecção Anti-Bot | `anti-bot.ts` com script JS dedicado detectando Cloudflare JS/Turnstile, hCaptcha, reCAPTCHA, rate-limit e block pages em tempo real (`detectChallengeViaPlaywright`, linhas 6-50) | Inexistente no código-fonte do Workstation; `browser_readiness.py` só verifica captcha como flag booleana genérica (`captcha_required`) sem detecção ativa | O Hermes não identifica proativamente desafios anti-bot; depende que o controller Electron sinalize, enquanto BrowserClaw executa detecção client-side estruturada com polling (`waitForChallengeViaPlaywright`, linhas 82-174) |
  | Snapshot AI-Native | `snapshotAi()` usa API nativa `_snapshotForAI`/`ariaSnapshot({mode:'ai'})` do Playwright + enriquecimento DOM + hidratação adaptativa com budget configurável (`ai-snapshot.ts`, linhas 31-158) | Snapshot via controller HTTP `/v1/action` com projeção `project_model_browser_payload` que remove duplicatas mas depende do formato `formatInventory` do controller (`browser_workstation.py`, linhas 966-1029); sem hidratação adaptativa nem fallback de API | O Hermes não tem snapshot AI-native direto; depende inteiramente do controller Electron gerar o texto, sem capacidade de enriquecimento DOM client-side ou detecção de corrida de navegação durante hidratação |
  | Batch Actions Atômico | `batchViaPlaywright` executa até 100 ações sequenciais com detecção de boundary (navegação/fechamento), timeout global de 300s, profundidade máxima 5, e listeners `framenavigated` para parar atomicamente (`batch.ts`, linhas 315-390) | `browser_batch_actions` existe no schema (`_WORKSTATION_SCHEMA_TOOLS`) mas a implementação é delegada ao controller via `_dispatch`; sem lógica de boundary detection, nesting ou stop-on-navigation no lado Python | O batch do Hermes é um proxy opaco; não detecta se a página navegou entre ações, não suporta batching aninhado, e não tem mecanismo de parada atômica baseado em eventos de frame |
  | Reaquisição de Tab | `CrawlPage.reacquire()` recupera tab perdida após navegação/re-render usando URL preferencial + fallback para primeira tab acessível (`browser.ts`, linhas 210-233); `refreshTargetId()` com fallback ativo (linhas 173-193) | Sem equivalente; `read_native_browser_session_state` valida binding mas não oferece recuperação automática de targetId perdido (`browser_workstation.py`, linhas 230-322) | Se o WebContentsView perde identidade após re-render agressivo, o Hermes exige reconexão manual; BrowserClaw recupera transparentemente |
  | SSRF Policy Enforcement | `assertCdpEndpointAllowed`, `assertBrowserNavigationResultAllowed`, `withBrowserNavigationPolicy` aplicam política SSRF em cada conexão, navegação e redirect chain (`security.js` importado em `connection.ts`, `navigation.ts`) | `url_safety.is_always_blocked_url` e `normalize_url_for_request` existem mas são aplicados apenas no dispatch Python (`browser_workstation.py`, linha 36); sem verificação pós-navegação de redirect chain | O Hermes valida URL de entrada mas não verifica se redirects intermediários violam política SSRF; BrowserClaw valida cada hop da cadeia |
  | Dialog/File Upload Arm | `armDialog()` one-shot + `onDialog()` persistente com handler customizado (`browser.ts`, linhas 696-763); `armFileUpload()` two-phase com listener armado antes do click (`browser.ts`, linhas 765-800) | Sem equivalente no código Python; dialogs e file choosers dependem exclusivamente do controller Electron | O Hermes não pode preparar handlers de dialog/upload antes de disparar a ação que os abre; falhas silenciosas em formulários com confirm() ou input[type=file] |
  | Telemetria Estruturada | `RunTelemetry` com launchMs, connectMs, navMs, authOk, exitReason, cleanupOk, timestamps ISO (`browser.ts`, linhas 1962-1966, 2242-2253) | `emit_native_browser_observation` captura action/duration/request_bytes/response_bytes/error_code (`browser_workstation.py`, linhas 866-926) mas sem lifecycle timing estruturado | O Hermes mede duração de ações individuais mas não tem telemetria de ciclo de vida completo (launch→connect→navigate→auth→cleanup) para diagnóstico de latência |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (BrowserClaw) | Vantagem Específica |
  |---|---|---|---|
  | Segurança por Design | Controller loopback-only com bearer token aleatório, descriptor fora do repo com permissões privadas, force-redact antes de cruzar tool boundary (`browser_workstation.py`, linhas 13-14, 369-371, 927) | CDP endpoint exposto via `--remote-debugging-port`; segurança depende de SSRF policy e NO_PROXY lease (`connection.ts`, linhas 249-279) | O Hermes nunca expõe porta de debug; o token é efêmero e o descriptor é arquivo privado. BrowserClaw confia em política de rede e pode ser acessado por qualquer processo local |
  | Binding Task/Session Durável | `_BOUND_TASKS` process-local + `_canonical_browser_task_binding` lê estado persistido do Electron; task bound nunca faz failover silencioso (`browser_workstation.py`, linhas 530-545, 1060-1082) | Sem conceito de task binding; cada `CrawlPage` é independente, sem vinculação a sessão/canban/run | O Hermes garante que uma tarefa autenticada nunca migra para browser com estado diferente; BrowserClaw não tem noção de ownership transacional |
  | Circuit Breaker Ativo | `BrowserRuntimeSupervisor` com estados CLOSED/OPEN/HALF_OPEN, backoff exponencial, classificação tipada de erros, limpeza de descriptor stale (`browser_supervisor.py`, linhas 57-302) | Retry simples por ação individual; sem circuit breaker global, sem classificação estruturada de erros, sem cooldown | O Hermes protege contra cascatas de falha e classifica erros semanticamente (PROCESS_DEAD, AUTH_MISMATCH, etc.); BrowserClaw trata cada erro isoladamente |
  | Readiness Semântica | `BrowserReadinessContract` avalia path, auth, hydration, entity_identity, semantic_targets com diagnóstico classificado (`browser_readiness.py`, linhas 131-173) | `waitForViaPlaywright` espera por selector/text/url/loadState mas sem contrato semântico estruturado (`wait.ts`) | O Hermes expressa "pronto" como contrato verificável com códigos de falha (DOM_DRIFT, HYDRATION_PENDING); BrowserClaw só sabe "esperou/esgotou" |
  | Bridge Direto para ArtifactStore | `browser_capture_to_artifact` extrai dados JS direto para ArtifactStore sem passar por base64/chat context (`browser_bridge.py`, linhas 85-121); validação de destino seguro | Sem equivalente; capturas passam por screenshot/PDF/text e o consumidor decide onde salvar | O Hermes evita inflação de contexto eliminando serialização intermediária; dados estruturados vão direto ao store durável |
  | Human Control Lease | `BrowserControlLeaseManager.assert_action_allowed` com fence_token, registro de child tasks, verificação de parent task (`browser_workstation.py`, linhas 1085-1092) | Sem conceito de lease humano; automação roda sem gate de aprovação explícita | O Hermes impede que automação execute ações sensíveis sem autorização humana ativa; BrowserClaw é puramente programático |
  | Projeção Model-Facing Lossless | `project_model_browser_payload` elimina duplicação elements/snapshot mantendo `element_index` para campos não-textuais, com verificação byte-exact do inventário (`browser_workstation.py`, linhas 966-1029) | Snapshot retorna texto + refs separados sem deduplicação; modelo recebe ambos | O Hermes reduz tokens eliminando redundância comprovada; BrowserClaw envia dados duplicados |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 Script de Detecção Anti-Bot
  **Origem:** `referências/02-Browser-Automacao-Web/browserclaw-main/src/anti-bot.ts`, linhas 6-50
  **Destino sugerido:** `workstation/browser_anti_bot.py` (novo arquivo)
  **Justificativa:** O script `DETECT_CHALLENGE_SCRIPT` é JavaScript autocontido que pode ser injetado via `evaluate_fn` no `browser_readiness.py` ou no controller. Adiciona detecção proativa de Cloudflare, hCaptcha, reCAPTCHA e rate-limit que o Hermes atualmente não possui.
  
  ```javascript
  // Copiar integralmente como string Python multi-linha
  const DETECT_CHALLENGE_SCRIPT = `(function() {
    var title = (document.title || '').toLowerCase();
    if (title === 'just a moment...'
        || document.querySelector('#challenge-running, #cf-please-wait, #challenge-form')
        || title.indexOf('checking your browser') !== -1) {
      return { kind: 'cloudflare-js', message: 'Cloudflare JS challenge' };
    }
    // ... (resto do script, linhas 16-49)
  })()`;
  ```
  
  ### 3.2 Função `resolveHydrationBudgetMs`
  **Origem:** `referências/02-Browser-Automacao-Web/browserclaw-main/src/snapshot/ai-snapshot.ts`, linhas 20-25
  **Destino sugerido:** `workstation/browser_readiness.py`, como helper de `BrowserReadinessContract`
  **Justificativa:** Normaliza parâmetro de hidratação (bool/number/undefined) para budget em ms com clamp seguro. Útil para evitar waits infinitos em páginas SPA.
  
  ```typescript
  // Adaptar para Python:
  def resolve_hydration_budget_ms(value):
      if value is None or value is False:
          return 0
      if value is True:
          return 5000  # DEFAULT_HYDRATION_BUDGET_MS
      if not isinstance(value, (int, float)) or value <= 0:
          return 0
      return min(60000, int(value))
  ```
  
  ### 3.3 Constantes de Batch Safety
  **Origem:** `referências/02-Browser-Automacao-Web/browserclaw-main/src/actions/batch.ts`, linhas 22-24
  **Destino sugerido:** `tools/browser_workstation.py` ou `workstation/batch_detection.py`
  **Justificativa:** Limites de segurança para batch actions que previnem abuso e runaway.
  
  ```python
  MAX_BATCH_DEPTH = 5
  MAX_BATCH_TIMEOUT_MS = 300_000
  MAX_BATCH_ACTIONS = 100
  ```
  
  ## 4. Código Adaptável
  
  ### 4.1 Padrão Navigation Race Detection
  **Conceito:** `ai-snapshot.ts` (linhas 88-106) compara URL antes/depois do snapshot e enrichment; se mudou, lança `NavigationRaceError` em vez de retornar refs inconsistentes.
  **Como adaptar:** Em `browser_readiness.py`, adicionar verificação de URL antes e depois de `wait_for_condition`. Se a URL mudou durante o polling, invalidar resultado e reiniciar ou lançar erro estruturado.
  **Benefício:** Previne que o agente aja sobre refs/DOM de uma página que já navegou, eliminando uma classe inteira de falhas silenciosas em SPAs com redirecionamentos rápidos.
  
  ### 4.2 Padrão Boundary Detection em Batch
  **Conceito:** `batch.ts` (linhas 333-349) registra listener `framenavigated` em cada página observada; se frame principal navegar ou página fechar, marca `boundary.navigated` e para o batch atomicamente.
  **Como adaptar:** No controller Electron do Hermes, adicionar evento `did-navigate` no WebContentsView que sinaliza ao supervisor Python via journal/event bus. O `_dispatch` em `browser_workstation.py` checa esse flag antes de cada ação batch.
  **Benefício:** Batch actions param imediatamente quando a página muda, evitando cliques/types em elementos que não existem mais. Atualmente o Hermes pode executar ações stale em batch.
  
  ### 4.3 Padrão Two-Phase File Upload Arm
  **Conceito:** `browser.ts` (linhas 765-800) arma listener de filechooser ANTES de clicar no elemento que dispara o picker; o arm resolve quando o listener está registrado, garantindo que o chooser não é perdido.
  **Como adaptar:** Adicionar ação `browser_arm_file_upload` no schema do Workstation que prepara o controller para o próximo filechooser. A ação de click subsequente dispara o picker já monitorado.
  **Benefício:** Elimina race condition em uploads onde o filechooser abre e fecha antes do handler ser registrado. Crítico para sites com input[type=file] customizado.
  
  ### 4.4 Padrão Connection Lease com NO_PROXY Scoped
  **Conceito:** `connection.ts` (linhas 249-279) gerencia lease de NO_PROXY para URLs loopback, restaurando env vars originais após último release. Previne que proxy corporativo intercepte tráfego CDP local.
  **Como adaptar:** Em `browser_supervisor.py` ou `browser_workstation.py`, garantir que requisições HTTP ao controller loopback usem `urllib.request` com handler direto (sem proxy). Documentar que proxies corporativos podem quebrar o controller.
  **Benefício:** Robustez em ambientes corporativos com proxy configurado via env vars. O Hermes atual usa `urlopen` padrão que respeita `HTTP_PROXY` e pode falhar silenciosamente.
  
  ### 4.5 Padrão Telemetria de Lifecycle Completo
  **Conceito:** `BrowserClaw` acumula `launchMs`, `connectMs`, `navMs`, `authOk`, `exitReason`, `cleanupOk` ao longo do ciclo (`browser.ts`, linhas 1962-2253).
  **Como adaptar:** Estender `emit_native_browser_observation` com eventos de lifecycle (controller_started, controller_connected, first_navigation, auth_verified, session_cleanup). Persistir no `EvidenceStateStore`.
  **Benefício:** Diagnóstico de latência end-to-end; identificar se gargalo é launch, connect, navigate ou auth. Atualmente o Hermes só mede duração de ações individuais.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | Projetar elements fora do snapshot quando texto já contém inventário (já implementado) | 15-30% por snapshot | Já feito | `browser_workstation.py:966-1029` (`project_model_browser_payload`) |
  | Adicionar modo `interactive_only` ao snapshot (ref: `snapshotAi` com `options.interactive`) | 20-40% em páginas densas | Médio | `ai-snapshot.ts:285-299` — filtra nós não-interativos antes de serializar |
  | Compactar readiness probe response (retornar apenas `missing` array em vez de objeto completo quando ready=false) | 5-10% por poll | Baixo | `browser_readiness.py:34-81` — expressão JS retorna todos os campos mesmo em falha |
  | Eliminar duplicação request_bytes/response_bytes em telemetry quando já presente no result | 2-5% por ação | Baixo | `browser_workstation.py:866-926` — telemetry duplica metadados já no payload |
  | Cache de snapshot para páginas idênticas (mesma URL + mesmo content hash) | 30-60% em workflows repetitivos | Alto | Ausente em ambos; BrowserClaw não cacheia, Hermes também não |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | Hydration-aware snapshot com budget adaptativo (evita wait fixo) | -500ms a -3s por snapshot em SPAs | Médio | `ai-snapshot.ts:60-66` — poll até minInteractiveRefs ou deadline |
  | Batch boundary detection via evento (para imediatamente em navegação) | -200ms a -2s por batch interrompido | Médio | `batch.ts:333-349` — listener framenavigated |
  | Connection lease pooling (reutiliza sessão Playwright/CDP) | -50ms a -200ms por ação | Alto | `connection.ts` mantém conexão viva; Hermes faz HTTP round-trip por ação |
  | Health probe cache TTL de 750ms (já implementado) | -200ms por verificação | Já feito | `browser_workstation.py:44,492` (`_AVAILABILITY_CACHE_SECONDS`) |
  | Readiness poll interval adaptativo (começa 100ms, escala para 500ms) | -100ms a -500ms em páginas rápidas | Baixo | `browser_readiness.py:92` — poll_interval fixo de 300ms |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | NavigationRaceError estruturado (detecta URL drift durante snapshot) | Alta: previne ação em DOM stale | Médio | `ai-snapshot.ts:88-106` |
  | Challenge detection tipado (cloudflare-js/hcaptcha/recaptcha/rate-limited) | Alta: agente sabe QUAL desafio enfrenta | Baixo | `anti-bot.ts:6-50` |
  | Readiness diagnostic com classification codes (DOM_DRIFT, HYDRATION_PENDING, AUTH_REQUIRED) | Média: agente distingue causa raiz | Já parcial | `browser_readiness.py:163-173` |
  | Batch results por ação individual (ok/error granular) | Média: agente sabe qual ação falhou | Médio | `batch.ts:376-384` |
  | ContentMeta com sourceUrl + capturedAt no snapshot | Média: auditoria temporal de refs | Baixo | `ai-snapshot.ts:114-118` |
  
  ## 8. Resumo Executivo
  
  ### Recomendações Priorizadas
  
  1. **Implementar detecção anti-bot proativa (Impacto: ALTO / Esforço: BAIXO)**
     Copiar `DETECT_CHALLENGE_SCRIPT` de `anti-bot.ts` para `workstation/browser_anti_bot.py` e integrar como pré-check em `browser_readiness.py`. O Hermes atualmente é cego a Cloudflare/CAPTCHA até que o controller falhe. Esta mudança adiciona percepção estruturada com <100 linhas de código e zero dependência externa. Justificativa: sites protegidos por Cloudflare são ubíquos; detecção tardia custa retries e tokens.
  
  2. **Adicionar Navigation Race Detection ao snapshot/readiness (Impacto: ALTO / Esforço: MÉDIO)**
     Adaptar o padrão de `ai-snapshot.ts` (comparar URL antes/depois) para `browser_readiness.wait_for_condition` e para o controller Electron. Previne que o agente atue sobre refs de página que já navegou. Justificativa: SPAs modernas fazem redirect silencioso durante hidratação; refs stale causam cliques em elementos errados ou erros crípticos.
  
  3. **Implementar Batch Boundary Detection no controller (Impacto: MÉDIO-ALTO / Esforço: MÉDIO)**
     Portar o padrão `framenavigated` listener de `batch.ts` para o WebContentsView do Electron, sinalizando via journal/event bus ao `_dispatch`. O batch atual do Hermes pode executar ações em página que já navegou. Justificativa: batches são usados em workflows multi-step; parada atômica evita corrupção de estado e retrabalho.
  
  4. **Adicionar modo interactive_only ao snapshot (Impacto: MÉDIO / Esforço: MÉDIO)**
     Expor opção no schema `browser_snapshot` que filtra nós não-interativos antes da serialização, inspirado em `snapshotAi({interactive:true})`. Reduz 20-40% dos tokens em páginas densas. Justificativa: a maioria das ações do agente visa elementos interativos; enviar árvore completa desperdiça contexto.
  
  5. **Estruturar telemetria de lifecycle completo (Impacto: MÉDIO / Esforço: MÉDIO)**
     Estender `emit_native_browser_observation` com eventos de launch/connect/navigate/auth/cleanup, persistindo no `EvidenceStateStore`. Justificativa: diagnóstico de latência end-to-end é impossível hoje; saber se gargalo é controller startup vs. navegação vs. auth acelera debugging de failures em produção.
  
  ### Nota sobre Viabilidade
  Todas as recomendações respeitam as invariáveis do Hermes Workstation: controller loopback-only, task binding durável, human control lease, e upstream-first change gate. Nenhuma requer alteração no core do Hermes Agent ou introduz segundo browser/state store. As adaptações são compatíveis com a arquitetura existente descrita em `workstation/ARCHITECTURE.md`.
</agent-message>

---

<!-- Relatório 16 -->

# Relatório Comparativo: Browser Hermes Workstation vs browser-use/browsercode
  
  Li e analisei todos os arquivos-chave do Hermes Workstation Browser (`workstation/browser_supervisor.py`, `workstation/browser_readiness.py`, `workstation/browser_bridge.py`, `workstation/ARCHITECTURE.md`, `tools/browser_workstation.py`) e os arquivos correspondentes da referência browser-use/browsercode (`packages/bcode-browser/src/browser-execute.ts`, `packages/bcode-browser/src/cdp/session.ts`, `packages/bcode-browser/src/session-store.ts`, `packages/bcode-browser/src/skills.ts`, `packages/bcode-browser/src/fetch-use.ts`, `packages/bcode-browser/skills/browser-execute/SKILL.md`). Não existe `agent/browser_controller.py` no Hermes; o controle é distribuído entre `tools/browser_workstation.py` (dispatch HTTP loopback) e `workstation/browser_supervisor.py` (saúde/circuit-breaker). A pasta de referência contém código-fonte TypeScript analisável e relevante para automação browser via CDP direto.
  
  ---
  
  ### 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência | Hermes Work | Gap Específico |
  |---|---|---|---|
  | Modelo de execução | Snippet JS in-process via `AsyncFunction("session", "console", code)` com CDP Session persistente (`browser-execute.ts:145-148, 178-253`) | Dispatch HTTP loopback por ação atômica (`browser_workstation.py:_dispatch`, `_request_json`) | Cada ação browser exige round-trip HTTP + serialização JSON; não há eval in-process nem sessão CDP reutilizável pelo agente |
  | Reutilização de scripts | Workspace `.bcode/agent-workspace/` com `await import(path + "?t=" + Date.now())` e cache-bust (`SKILL.md:174-202`) | Sem mecanismo de workspace de scripts reutilizáveis; cada ação é um payload JSON independente | Agente não pode acumular conhecimento procedural em código; repete padrões via tool calls |
  | Captura de screenshot | Tap automático em `Page.captureScreenshot` via `onCallResult` listener; base64 anexado inline sem decode/save/read (`browser-execute.ts:227-246`) | Screenshot retorna como dado estruturado que precisa ser processado pelo modelo ou salvo manualmente | Overhead de tokens e latência para cada screenshot; agente precisa gerenciar ciclo de vida da imagem |
  | Detecção de browser | Auto-detect multi-browser via `DevToolsActivePort` scan + mtime ordering + fallback `/json/version` (`cdp/session.ts:463-543`) | Controller descriptor fixo em arquivo JSON; sem auto-discovery de browsers disponíveis | Se o controller falhar, não há descoberta automática de alternativas; depende de restart manual |
  | Console capture | Per-call `console` shadowing com tee para buffer isolado; concurrency-safe (`browser-execute.ts:197-212`) | Sem captura de console do lado do agente; apenas resultados estruturados retornam | Agente perde sinais de debug/logging do contexto da página |
  | Timeout granular | Per-snippet timeout com scoped execution view; próxima chamada herda sessão intacta (`browser-execute.ts:256-274`) | Timeout global por requisição HTTP; erro de timeout marca estado como uncertain (`browser_workstation.py:418-433`) | Timeout em uma ação não isola o escopo; pode corromper estado percebido da sessão |
  | Fetch anti-bot | `FetchUse` service proxy via Browser Use Cloud com JA4/HTTP2 fingerprint (`fetch-use.ts:1-98`) | `http_fetch` nativo sem fingerprint de browser; bloqueios anti-bot não contornados | Requests HTTP fora do browser são detectáveis como bot; sem alternativa integrada |
  
  ### 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência | Vantagem Específica |
  |---|---|---|---|
  | Segurança de binding | Task binding fail-closed com verificação canônica + receipt revision matching (`browser_workstation.py:230-322, 1060-1082`) | Sem conceito de task binding; qualquer snippet pode dirigir qualquer sessão | Hermes garante que tarefa nunca migra silenciosamente para browser com estado/auth diferente |
  | Circuit breaker ativo | `BrowserRuntimeSupervisor` com classificação de erros tipados, backoff exponencial e half-open probe (`browser_supervisor.py:57-302`) | Sem circuit breaker; timeouts repetidos produzem erros sem adaptação | Hermes evita tempestade de retries e detecta morte do processo proativamente |
  | Readiness semântica | `BrowserReadinessContract` com avaliação estruturada de auth/hydration/DOM drift/captcha (`browser_readiness.py:131-173`) | Polling genérico via `waitFor("Page.loadEventFired")` sem contratos semânticos | Hermes distingue estados reais de falha (captcha vs DOM drift vs hydration) e classifica para o agente |
  | Extração direta para artifact | `browser_capture_to_artifact` extrai JS→ArtifactStore sem passar por base64/chat context (`browser_bridge.py:85-121`) | Screenshot/data sempre passa pelo tool result → modelo → possível save | Zero overhead de tokens para extrações estruturadas; dados vão direto ao storage |
  | Redação forçada | `_force_redact` + `redact_sensitive_text` em todo resultado antes de cruzar boundary (`browser_workstation.py:927`) | Sem redação automática; snippets podem vazar credenciais no output | Credenciais/secrets nunca chegam ao modelo mesmo se o snippet as capturar acidentalmente |
  | Approval gate | `BrowserControlLeaseManager` com fence_token e human-in-the-loop para side effects sensíveis (`browser_workstation.py:1084-1092`) | Sem approval gate; agente executa qualquer ação CDP irrestritamente | Side effects financeiros/destrutivos requerem aprovação humana explícita |
  | Journal canônico | `_record_browser_controller_outcome` projeta eventos no journal durável com operation_id lineage (`browser_workstation.py:879-909`) | Sem journal durável; estado é efêmero por sessão | Auditoria completa e replay capability sobre operações browser |
  
  ### 3. Código Copiável Diretamente
  
  **Trecho 1: Console capture com tee e shadowing**
  - Origem: `packages/bcode-browser/src/browser-execute.ts:197-212`
  - Destino sugerido: Novo módulo `workstation/browser_console_capture.py` ou integração em `browser_bridge.py`
  - Código adaptado para Python:
  ```python
  def build_console_capture_script(buffer_var: str = "__hermes_console_buffer") -> str:
      """Shadow console.log/error/warn/info/debug to capture into a per-call buffer."""
      return f"""
      (() => {{
          const buf = [];
          const orig = Object.create(console);
          const tee = (...args) => {{
              buf.push(args.map(a => typeof a === 'string' ? a : JSON.stringify(a)).join(' '));
          }};
          console.log = tee; console.error = tee; console.warn = tee;
          console.info = tee; console.debug = tee;
          // Prototype chain preserves table/group/dir etc. without capture
          Object.setPrototypeOf(console, orig);
          return {buffer_var};
      }})()
      """
  ```
  
  **Trecho 2: DevToolsActivePort auto-detection**
  - Origem: `packages/bcode-browser/src/cdp/session.ts:463-543` (`detectBrowsers`, `tryReadDevToolsActivePort`, `getBrowserCandidates`)
  - Destino sugerido: `workstation/browser_discovery.py` (novo)
  - Justificativa: Permite fallback automático quando o controller descriptor está stale, usando browsers já abertos pelo usuário
  
  **Trecho 3: Loopback validation regex**
  - Origem: `packages/bcode-browser/src/fetch-use.ts:96`
  - Destino sugerido: `tools/url_safety.py` (já existente, complementar)
  - Código: `LOOPBACK = /^(localhost\.?|\[::1\]|127(\.\d{1,3}){3})$/` — útil para validar endpoints de fetch proxy sem vazar API keys
  
  ### 4. Código Adaptável
  
  | Conceito | Como adaptar para Hermes | Benefício esperado |
  |---|---|---|
  | **Snippet eval in-process** | Implementar `browser_execute_snippet` como nova action no controller Electron que aceita código JS arbitrário e roda no WebContents via `webContents.executeJavaScript()`, retornando output+result+screenshots | Elimina N round-trips HTTP para tarefas complexas; reduz latência de 100ms+/ação para ~5ms total |
  | **Scoped execution view** | Adicionar `execution_id` por snippet call no supervisor; após timeout, invalidar apenas aquele execution_id enquanto a sessão CDP/WebContents permanece viva | Timeouts não matam a sessão; próxima chamada continua sem reconnect |
  | **Workspace de scripts reutilizáveis** | Criar `<HERMES_WORKSTATION_HOME>/agent-workspace/` por projeto; permitir que o agente escreva `.js/.ts` files e os importe via dynamic import com cache-bust dentro de snippets | Agente acumula procedimentos; scraping de 50 URLs vira 1 import + 1 call em vez de 50 tool calls |
  | **Screenshot auto-tap** | No controller Electron, interceptar `Page.captureScreenshot` responses e anexá-los automaticamente ao tool result como attachments multimodais | Remove necessidade de decode/save/read; reduz 3 tool calls para 0 overhead adicional |
  | **FetchUse proxy pattern** | Integrar como opção em `tools/http_fetch.py` quando `BROWSER_USE_API_KEY` está configurado; rotear requests através do proxy cloud com fingerprint de browser | Contorna anti-bot sem exigir browser completo; útil para scraping leve |
  | **Skills embedding com sentinel** | Adaptar o padrão de `skills.ts` para materializar skills de browser do Hermes em disco com hash-based invalidation; substituir placeholders de path em tempo de materialização | Skills de browser carregam instantaneamente em modo compilado; dev mode reflete edições sem rebuild |
  
  ### 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | Snippet eval elimina N tool calls por tarefa complexa | 40-70% | Alto | `browser-execute.ts:178-253` vs `browser_workstation.py:_dispatch` |
  | Screenshot auto-tap remove decode/save/read cycle | 15-25% | Médio | `browser-execute.ts:227-246` |
  | Console capture inline evita tool call separado para debug | 5-10% | Baixo | `browser-execute.ts:197-212` |
  | Project_model_browser_payload já deduplica elements vs snapshot text | Já implementado (0% adicional) | — | `browser_workstation.py:966-1029` |
  | Readiness semântica evita polling cego e retries desnecessários | 10-20% | Já implementado | `browser_readiness.py:131-173` |
  | Workspace scripts reduzem repetição de padrões de scraping | 30-50% | Médio | `SKILL.md:174-202` |
  
  ### 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | Execução in-process via executeJavaScript | 10-50x mais rápido para sequências de ações | Alto | `browser-execute.ts:145-148` |
  | Auto-detect browser via DevToolsActivePort | Elimina espera manual por controller restart | Médio | `cdp/session.ts:463-543` |
  | Scoped timeout preserva sessão CDP | Evita reconnect de 2-5s após timeout | Médio | `browser-execute.ts:256-274` |
  | Cache de availability com TTL 750ms | Já implementado; health probe não bloqueia dispatch | — | `browser_workstation.py:485-502` |
  | Parallel snippet execution (futuro) | Múltiplas abas/alvos em paralelo dentro de uma sessão | Alto | `browser-execute.ts:221-226` nota sobre serialização |
  
  ### 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | Readiness contracts classificam falhas objetivamente (auth/captcha/drift/hydration) | Alta: agente recebe diagnóstico estruturado em vez de "page not loaded" | Já implementado | `browser_readiness.py:131-173` |
  | Error classification tipada no supervisor | Alta: circuit breaker abre/fecha baseado em evidência, não em texto | Já implementado | `browser_supervisor.py:153-174` |
  | Receipt revision matching previne replay incerto | Alta: mutações só avançam com prova de execução correta | Já implementado | `browser_workstation.py:260-276` |
  | Console capture fornece ground truth de execução | Média: agente vê logs reais em vez de inferir sucesso | Baixo | `browser-execute.ts:197-212` |
  | Screenshot inline como evidência visual imediata | Média: agente verifica resultado visual sem tool call extra | Médio | `browser-execute.ts:227-246` |
  | Force redact garante que secrets nunca influenciam raciocínio | Alta: elimina classe inteira de hallucination baseada em credencial vazada | Já implementado | `browser_workstation.py:927` |
  
  ### 8. Resumo Executivo
  
  **Top 5 recomendações priorizadas por impacto/esforço:**
  
  1. **Implementar `browser_execute_snippet` no controller Electron** (Impacto: ALTO, Esforço: ALTO)
     - Justificativa: É a diferença arquitetural mais significativa. O modelo atual de N round-trips HTTP por tarefa complexa é fundamentalmente limitado. Um endpoint `executeJavaScript` no controller que aceite código JS arbitrário, rode no WebContents e retorne output+result+screenshots eliminaria 40-70% dos tokens e 10-50x da latência para tarefas de scraping/automação. O código de `browser-execute.ts:145-278` é o blueprint completo.
  
  2. **Adicionar workspace de scripts reutilizáveis** (Impacto: ALTO, Esforço: MÉDIO)
     - Justificativa: Complementa o snippet eval. Permitir que o agente escreva e importe scripts em `<HERMES_WORKSTATION_HOME>/agent-workspace/` transforma automação repetitiva de N tool calls em 1 import + 1 call. O padrão de cache-bust via `?t=${Date.now()}` (`SKILL.md:198-200`) é simples e eficaz.
  
  3. **Integrar auto-detect de browsers via DevToolsActivePort** (Impacto: MÉDIO, Esforço: MÉDIO)
     - Justificativa: Quando o controller descriptor está stale ou o Electron não iniciou, o Hermes atualmente falha fechado sem alternativa. A função `detectBrowsers()` de `cdp/session.ts:463-543` permite descobrir Chrome/Edge/Brave já abertos e conectar via CDP como fallback graceful, melhorando resiliência sem comprometer segurança.
  
  4. **Implementar screenshot auto-tap no controller** (Impacto: MÉDIO, Esforço: MÉDIO)
     - Justificativa: O padrão de `onCallResult` listener (`browser-execute.ts:227-246`) que intercepta `Page.captureScreenshot` e anexa base64 inline elimina o ciclo decode→save→read→model que custa 3 tool calls e milhares de tokens por screenshot. No Electron, isso equivale a interceptar `webContents.capturePage()` responses no controller.
  
  5. **Adicionar console capture per-call** (Impacto: BAIXO-MÉDIO, Esforço: BAIXO)
     - Justificativa: O shadowing de `console.log/error/warn/info/debug` com tee para buffer isolado (`browser-execute.ts:197-212`) dá ao agente visibilidade real da execução sem tool call extra. Em Python/Hermes, isso pode ser implementado como wrapper JS injetado antes de cada evaluate, com o buffer retornado junto ao resultado. Custo de implementação mínimo, benefício imediato para debugging.
</agent-message>

---

<!-- Relatório 17 -->

# Relatório Comparativo: Browser Nativo Hermes Workstation vs Referência nesquena--hermes-webui
  
  Com base na leitura completa dos arquivos-chave do Hermes Workstation (`workstation/browser_supervisor.py`, `workstation/browser_readiness.py`, `workstation/browser_bridge.py`, `workstation/ARCHITECTURE.md`, `tools/browser_workstation.py`) e da referência `nesquena--hermes-webui` (`ARCHITECTURE.md`, `api/media_snapshots.py`, `tests/browser_smoke.py`, `tests/browser_reconnect_scene_redraw.py`, `static/boot.js`), confirmo que não existe `agent/browser_controller.py` no Hermes (a lógica reside em `tools/browser_workstation.py` e `workstation/browser_supervisor.py`) e que a referência é uma WebUI server-side sem automação de browser agente-direta comparável, mas com padrões superiores de snapshot imutável e testes E2E. Segue o relatório estruturado.
  
  ### 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência | Hermes Work | Gap Específico |
  | :--- | :--- | :--- | :--- |
  | Imutabilidade de Artefatos | `api/media_snapshots.py` cria snapshots content-addressed (`sha256.snap`) no settle, garantindo que previews históricos nunca mudem mesmo se o arquivo for sobrescrito. | `browser_bridge.py` salva JSON/artifacts diretamente no destino final; não há camada de snapshot imutável para capturas de tela ou DOM extraído. | Ausência de store content-addressed para browser artifacts; re-execução ou sobrescrita corrompe evidência histórica. |
  | Testes E2E Headless | `tests/browser_smoke.py` e `browser_reconnect_scene_redraw.py` rodam Playwright real contra server isolado, validando zero console errors e reconexão SSE com fixtures determinísticos. | Não há equivalente em `workstation/` ou `tests/` que valide o controller Electron com Playwright headless em CI; testes são unitários ou manuais. | Falta de smoke test automatizado que detecte regressões de runtime no browser nativo antes do merge. |
  | Reconciliação de Estado Pós-Reconexão | `browser_reconnect_scene_redraw.py` valida que após reconnect SSE, o DOM renderiza exatamente os tools pendentes e novos eventos sem redraws espúrios (`redrawCount <= 2`). | `browser_supervisor.py` tem circuit breaker e health check, mas não valida semanticamente se o estado da página foi restaurado corretamente após perda de controller. | Supervisor detecta "alive" mas não garante integridade semântica da sessão de browser após recuperação. |
  | Acessibilidade como Contrato | `static/boot.js` gerencia `aria-expanded`, `aria-hidden`, `aria-pressed` rigorosamente; `extension_settings.js` checa `aria-disabled`. A UI trata acessibilidade como invariante de boot. | `browser_readiness.py` usa seletores CSS e texto bruto; não há verificação de atributos ARIA ou árvore de acessibilidade como contrato de prontidão. | Readiness ignora semântica ARIA; páginas "visualmente prontas" mas inacessíveis passam no check. |
  
  ### 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência | Vantagem Específica |
  | :--- | :--- | :--- | :--- |
  | Segurança de Roteamento | `tools/browser_workstation.py` linhas 369-370: valida loopback-only + bearer token; fail-closed explícito quando bound; nunca expõe descriptor ao modelo. | Server HTTP padrão com auth opcional; `media_snapshots.py` tem deny-list mas não possui conceito de binding de tarefa ou fail-closed por sessão. | Isolamento criptográfico e binding de tarefa impedem cross-session hijacking; referência não tem equivalente. |
  | Supervisão Ativa com Circuit Breaker | `BrowserRuntimeSupervisor` com estados CLOSED/OPEN/HALF_OPEN, backoff exponencial, classificação tipada de erros (`ControllerErrorKind`), e limpeza automática de descriptor stale. | Health check simples via `/health`; sem circuit breaker, sem classificação de erros, sem retry estruturado. | Resiliência operacional superior; evita cascata de falhas e permite recuperação automática sem intervenção humana. |
  | Readiness Semântica Declarativa | `BrowserReadinessContract` avalia `auth_required`, `captcha_required`, `dom_drift`, `hydration_timeout`, `unsupported_surface` como códigos estruturados. | Polling genérico de DOM/texto; sem contratos declarativos por rota ou entidade. | Diagnóstico preciso de falhas de carregamento; readiness não é binário mas tipado para ação corretiva. |
  | Projeção Model-Facing Lossless | `project_model_browser_payload()` remove duplicação entre `elements[]` e texto do snapshot, mantendo apenas campos não expressáveis textualmente (`element_index`). | UI renderiza tudo; não há projeção otimizada para consumo por LLM. | Economia direta de tokens sem perda de informação acionável; referência não considera custo de contexto. |
  | Bridge Direto para ArtifactStore | `browser_capture_to_artifact()` extrai dados estruturados do DOM direto para store persistente, sem passar por base64/chat/contexto. | Upload via `/api/upload` multipart; preview via `/api/file/raw`; sem extração estruturada direta. | Zero overhead de serialização/deserialização; artifacts são first-class citizens do fluxo de browser. |
  
  ### 3. Código Copiável Diretamente
  
  **Arquivo:** `referências/02-Browser-Automacao-Web/nesquena--hermes-webui/api/media_snapshots.py`
  **Destino sugerido:** `workstation/browser_media_snapshots.py`
  **Trecho copiável:** Funções `capture_snapshot()`, `is_valid_digest()`, `snapshot_path_for_digest()`, `_enforce_quota_locked()`, e `annotate_media_snapshots()` (linhas 207-593). O módulo é autocontido, usa apenas stdlib + `pathlib`, e implementa store content-addressed com dedup, quota enforcement e atomic writes. Adaptar apenas os imports de `api.config.STATE_DIR` para `workstation.paths` ou equivalente.
  
  **Arquivo:** `referências/02-Browser-Automacao-Web/nesquena--hermes-webui/tests/browser_smoke.py`
  **Destino sugerido:** `tests/workstation/test_browser_smoke.py`
  **Trecho copiável:** Script completo (linhas 1-172). Substituir `server.py` pelo bootstrap do Workstation controller e ajustar `PAGES` para as rotas do browser nativo. Mantém a estrutura de isolamento de estado, lista de benignos, e exit codes padronizados.
  
  ### 4. Código Adaptável
  
  **Conceito:** Snapshot Imutável Content-Addressed para Browser Artifacts
  **Como adaptar:** Integrar `capture_snapshot()` no fluxo de `browser_capture_to_artifact()` em `browser_bridge.py`. Antes de salvar, computar SHA-256 do conteúdo capturado; se já existir no store, retornar ref existente. Adicionar sidecar `.src.json` vinculando digest ao path canônico da tarefa.
  **Benefício esperado:** Elimina duplicação de capturas idênticas entre tarefas; garante que evidência histórica de browser seja imutável mesmo com re-execução; reduz storage em cenários de polling/retry.
  
  **Conceito:** Smoke Test Headless com Fixture Determinístico
  **Como adaptar:** Criar `tests/workstation/test_browser_controller_smoke.py` usando Playwright contra o controller Electron em modo headless. Usar fixtures JSON estáticos (como `browser_reconnect_scene_redraw.py` faz) para simular respostas do controller sem depender de agent/provider. Validar zero console errors, tempo de boot, e integridade pós-reconnect.
  **Benefício esperado:** Detecta regressões de runtime no browser nativo em CI antes do merge; elimina classe de bugs "funciona no dev, quebra no user" que atualmente só aparecem em dogfood manual.
  
  **Conceito:** Readiness Baseada em ARIA/Acessibilidade
  **Como adaptar:** Estender `build_readiness_expression()` em `browser_readiness.py` para aceitar `required_aria_states: dict[str, str]` (ex: `{"aria-busy": "false", "aria-live": "polite"}`). Incluir verificação de `role` e `aria-*` no probe JS gerado.
  **Benefício esperado:** Páginas SPAs modernas frequentemente têm DOM visualmente pronto mas semanticamente incompleto; readiness baseada em ARIA captura esses casos e melhora confiabilidade de automação.
  
  ### 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Projetar `element_index` apenas para campos não textuais (já implementado) | 15-25% | Baixo | `tools/browser_workstation.py:966-1029` |
  | Dedup de snapshots via content-addressing | 20-40% | Médio | `api/media_snapshots.py:407-473` (adaptar) |
  | Readiness semântica evita polls desnecessários | 5-10% | Baixo | `browser_readiness.py:131-173` |
  | Sidecar `.src.json` evita re-captura em re-settle | 10-20% | Médio | `api/media_snapshots.py:296-344` (adaptar) |
  
  ### 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Health check cacheado (0.75s TTL) já implementado | Alto | Já feito | `tools/browser_workstation.py:485-502` |
  | Circuit breaker evita retries inúteis em falha confirmada | Alto | Já feito | `workstation/browser_supervisor.py:249-258` |
  | Atomic snapshot write evita corrupção e re-trabalho | Médio | Médio | `api/media_snapshots.py:440-460` (adaptar) |
  | Readiness declarativa reduz poll cycles | Médio | Baixo | `browser_readiness.py:84-127` |
  | Smoke test headless rápido (<5s) em CI | Alto | Médio | `tests/browser_smoke.py` (adaptar) |
  
  ### 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Snapshot imutável garante que evidência citada pelo modelo existe e não mudou | Alto | Médio | `api/media_snapshots.py` |
  | Readiness tipada (`dom_drift`, `hydration_timeout`) dá diagnóstico objetivo ao invés de "página não carregou" | Alto | Baixo | `browser_readiness.py:163-173` |
  | Fail-closed explícito em binding conflict previne execução em contexto errado | Alto | Já feito | `tools/browser_workstation.py:1066-1072` |
  | Projected payload elimina ambiguidade entre texto e estrutura | Médio | Já feito | `tools/browser_workstation.py:966-1029` |
  | Smoke test valida que UI não lança exceções silenciosas | Médio | Médio | `tests/browser_smoke.py` |
  
  ### 8. Resumo Executivo
  
  1. **Adotar store content-addressed para browser artifacts** (Médio esforço, Alto impacto): Copiar `media_snapshots.py` para `workstation/browser_media_snapshots.py` e integrar em `browser_bridge.py`. Resolve imutabilidade, dedup e economia de tokens simultaneamente. Justificativa: o Hermes já projeta payloads model-facing losslessly; o próximo passo lógico é tornar os próprios artifacts imutáveis e deduplicáveis.
  
  2. **Implementar smoke test headless para o controller Electron** (Médio esforço, Alto impacto): Adaptar `browser_smoke.py` para validar boot, zero console errors e reconnect do browser nativo em CI. Justificativa: o supervisor tem circuit breaker excelente, mas não há teste automatizado que prove que o controller realmente funciona end-to-end; essa é a maior lacuna de verificação objetiva.
  
  3. **Estender readiness para contratos ARIA** (Baixo esforço, Médio impacto): Adicionar `required_aria_states` ao `BrowserReadinessContract`. Justificativa: SPAs modernas têm DOM visualmente pronto mas semanticamente incompleto; readiness baseada apenas em seletores CSS e texto bruto perde esses casos, causando automação frágil.
  
  4. **Manter e documentar a projeção model-facing lossless** (Baixo esforço, Manutenção): A função `project_model_browser_payload()` já é superior à referência; garantir que novos campos sigam o mesmo padrão de "texto primeiro, índice apenas para extras". Justificativa: é a vantagem competitiva mais clara do Hermes em economia de tokens; qualquer regressão aqui custa caro.
  
  5. **Não copiar arquitetura de WebUI server-side**: A referência é um servidor HTTP Python+JS vanilla; o Hermes é Electron nativo com controller loopback. Copiar `server.py`, rotas ou frontend seria anti-padrão. O valor está nos *padrões* (snapshot, smoke test, readiness), não no código de UI.
</agent-message>

---

<!-- Relatório 18 -->

# Relatório Comparativo: Browser Nativo Hermes Workstation vs Stagehand (Browserbase)
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (Stagehand) | Hermes Work | Gap Específico |
  |---|---|---|---|
  | **Snapshot com refs estáveis** | `snapshot.ts` + `selectors.ts`: gera árvore de acessibilidade com refs `[N-M]` cacheados em `xpathMap`/`urlMap`; comandos subsequentes (`click`, `fill`) resolvem ref → xpath automaticamente (`resolveSelector()`). | Não há mecanismo equivalente de snapshot estruturado com refs. O modelo precisa gerar seletores CSS/XPath brutos ou usar `evaluate_fn` com JS inline (`browser_readiness.py:34-81`). | O modelo gasta tokens inventando seletores e erra quando o DOM muda entre turnos; sem cache de refs, cada ação exige re-descoberta do elemento. |
  | **Filtragem de snapshot no servidor** | `snapshot-format.ts`: `filterLinesWithAncestors()` preserva ancestrais de linhas matching; `compactLines()` mantém apenas linhas com refs, labels ou roles interativos; `maxDepth` corta profundidade. Tudo antes de enviar ao modelo. | `browser_readiness.py` retorna JSON bruto com `missing[]`, `text_length`, etc. Sem filtragem de árvore DOM; a projeção (`browser_projection.py`) só atua em `extract_items`, não em observação geral. | O modelo recebe dados não filtrados ou precisa pedir extrações cirúrgicas via JS customizado, aumentando tokens e latência. |
  | **Comandos de alto nível tipados** | `elements.ts`, `navigation.ts`, `runtime.ts`: handlers com validação Zod (`z.object({...}).parse(params)`); `click({selector})`, `fill({selector, value, pressEnter})`, `wait({type, arg, state, timeoutMs})`. Schema enforcement garante parâmetros corretos antes da execução. | `tools/browser_workstation.py` despacha via `_dispatch(action, args)` com args como dict livre; validação é ad-hoc dentro de cada handler no controller Electron. Erros de parâmetro só aparecem como falhas genéricas. | Maior taxa de erros por parâmetros malformados; o modelo não tem schema estrito para guiar chamadas. |
  | **Conversão HTML→Markdown nativa** | `page-info.ts:39-42`: `NodeHtmlMarkdown.translate(await locator.innerHtml())` retorna markdown limpo direto do DOM, pronto para consumo pelo modelo. | `browser_bridge.py` salva JSON bruto; não há conversão HTML→Markdown integrada. O modelo recebe HTML ou texto plano e precisa processar internamente. | Tokens desperdiçados com tags HTML irrelevantes; markdown reduz ~60-70% o volume vs HTML bruto. |
  | **Wait semântico multi-modal** | `runtime.ts:62-90`: `wait` suporta `load` (waitForLoadState), `selector` (waitForSelector com state visible/hidden/attached/detached), e `timeout` explícito. Integrado ao Playwright. | `browser_readiness.py:84-127`: polling manual com `time.sleep(poll_interval)` e expressão JS injetada. Sem integração com eventos nativos do Chromium; depende de polling ativo. | Polling adiciona latência (300ms default) e desperdiça ciclos; wait nativo do Chromium é instantâneo e mais confiável. |
  | **Gestão de abas/tabs** | `tabs.ts` (referenciado em `registry.ts`): `tab.new`, `tab.list`, `tab.switch`, `tab.close` como comandos de primeira classe. | Não há API de gestão de abas exposta como tool. O controller gerencia WebContentsView mas não expõe operações de tab ao modelo. | O modelo não pode navegar entre múltiplas páginas sem criar/destroy tasks inteiras. |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (Stagehand) | Vantagem Específica |
  |---|---|---|---|
  | **Supervisão ativa com circuit breaker** | `browser_supervisor.py:63-302`: `BrowserRuntimeSupervisor` com classificação de erros (`ControllerErrorKind`), backoff exponencial, circuit breaker (closed/open/half_open), limpeza de descriptor stale, verificação de PID via psutil/ctypes. | Stagehand CLI é stateless por comando; não há supervisor persistente, circuit breaker ou classificação de erros entre invocações. | Resiliência operacional superior: falhas transitórias são recuperadas automaticamente; falhas fatais abortam rápido sem retry cego. |
  | **Binding de tarefa fail-closed** | `tools/browser_workstation.py:1060-1082`: uma vez que um `task_id` executa uma ação browser bem-sucedida, ele fica bound ao controller interno; perda de conexão falha fechada, nunca migra silenciosamente para outro browser com estado/auth diferente. | Stagehand não tem conceito de task binding; cada comando é independente e pode conectar a sessões diferentes. | Garantia de isolamento de sessão: auth/state de uma tarefa nunca vaza para outra; segurança operacional crítica para workflows sensíveis. |
  | **Projeção durável de extrações** | `browser_projection.py:39-167`: `process_extracted_items_durably()` persiste dataset completo no ArtifactStore, cria WorkPlan/WorkItems no kanban_db, valida semanticamente cada item, e retorna apenas summary compacto ao modelo. | Stagehand retorna resultado bruto ao stdout/cli; não há persistência automática, validação semântica ou separação entre dado completo e resumo para o modelo. | Economia massiva de tokens em extrações grandes (5+ items); rastreabilidade completa via artifacts e kanban; validação catch-all sem custo de prompt. |
  | **Lease de controle humano** | `browser_controller.py:55-58`: `BrowserControlLeaseManager.assert_action_allowed(task_id, action, fence_token)` impõe gate de aprovação humana antes de ações sensíveis; integrado ao dispatch autoritativo. | Stagehand não tem lease/fence; automação é irrestrita uma vez conectado. | Segurança human-in-the-loop nativa; previne ações irreversíveis sem supervisão. |
  | **Readiness semântico declarativo** | `browser_readiness.py:131-173`: `BrowserReadinessContract` com `required_semantic_targets`, `require_auth`, `require_hydration`, `entity_identity`; avaliação retorna códigos diagnósticos (`AUTH_REQUIRED`, `DOM_DRIFT`, `HYDRATION_PENDING`). | Stagehand `wait` é puramente mecânico (selector/load/timeout); não há contrato semântico declarativo nem diagnóstico estruturado de falha. | O modelo entende POR QUE a página não está pronta, não apenas QUE não está; reduz retries cegos e melhora debuggability. |
  | **Bridge segura com validação de destino** | `browser_bridge.py:25-33`: `_validate_safe_destination()` impõe allowed_roots; `BridgeSecurityError` previne escrita fora de workspaces permitidos. | Stagehand `screenshot` escreve em qualquer path fornecido (`runtime.ts:40-43`); sem validação de sandbox. | Prevenção de path traversal e escrita acidental em diretórios sensíveis. |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 Snapshot Format Filter (snapshot-format.ts → Python)
  **Origem:** `referências/02-Browser-Automacao-Web/browserbase--stagehand/packages/cli/src/lib/driver/commands/snapshot-format.ts`
  **Destino sugerido:** `workstation/browser_snapshot_format.py` (novo arquivo)
  
  ```python
  """Port of Stagehand snapshot-format.ts for Hermes Workstation.
  
  Filters accessibility tree snapshots server-side to reduce token usage
  before sending to the model. Preserves ancestor context for matched lines.
  """
  from __future__ import annotations
  import re
  from typing import Optional
  
  
  def format_snapshot_tree(
      tree: str,
      *,
      filter_pattern: Optional[str] = None,
      max_depth: Optional[int] = None,
      compact: bool = False,
  ) -> str:
      lines = tree.split("\n")
      if max_depth is not None:
          lines = [l for l in lines if _line_depth(l) <= max_depth]
      if filter_pattern:
          lines = _filter_lines_with_ancestors(lines, filter_pattern)
      if compact:
          lines = _compact_lines(lines)
      return "\n".join(lines).strip()
  
  
  def _line_depth(line: str) -> int:
      match = re.match(r"^\s*", line)
      return len(match.group(0)) // 2 if match else 0
  
  
  def _filter_lines_with_ancestors(lines: list[str], pattern: str) -> list[str]:
      matcher = _create_matcher(pattern)
      keep: set[int] = set()
      for idx, line in enumerate(lines):
          if not matcher(line):
              continue
          keep.add(idx)
          depth = _line_depth(line)
          for ancestor in range(idx - 1, -1, -1):
              ad = _line_depth(lines[ancestor])
              if ad < depth:
                  keep.add(ancestor)
                  depth = ad
                  if ad == 0:
                      break
      return [l for i, l in enumerate(lines) if i in keep]
  
  
  def _create_matcher(pattern: str):
      m = re.match(r"^/(.+)/([a-z]*)$", pattern, re.IGNORECASE)
      if m:
          try:
              rx = re.compile(m.group(1), {"i": re.IGNORECASE}.get(m.group(2), 0))
              return lambda line: bool(rx.search(line))
          except re.error:
              pass
      needle = pattern.lower()
      return lambda line: needle in line.lower()
  
  
  def _compact_lines(lines: list[str]) -> list[str]:
      compacted = _filter_lines_with_ancestors(lines, "__useful__")
      # Fallback: keep lines with refs, labels, or interactive roles
      useful = [l for l in lines if _is_useful_snapshot_line(l)]
      if not useful:
          return lines
      return _filter_lines_with_ancestors(lines, None) if not compacted else compacted
  
  
  def _is_useful_snapshot_line(line: str) -> bool:
      if re.search(r"\[\d+-\d+]", line):
          return True
      if ": " in line:
          return True
      if re.search(r"\b(button|link|textbox|checkbox|radio|combobox)\b", line, re.IGNORECASE):
          return True
      return False
  ```
  
  ### 3.2 Selector Ref Resolution (selectors.ts → Python)
  **Origem:** `referências/02-Browser-Automacao-Web/browserbase--stagehand/packages/cli/src/lib/driver/commands/selectors.ts`
  **Destino sugerido:** `workstation/browser_selector_refs.py` (novo arquivo)
  
  ```python
  """Port of Stagehand selectors.ts ref resolution for Hermes Workstation.
  
  Resolves @ref, [N-M], and ref=N-M syntax to cached XPath selectors.
  Requires a prior snapshot call to populate ref maps.
  """
  from __future__ import annotations
  import re
  from typing import Dict, Optional, Tuple
  
  
  class StaleRefError(Exception):
      """Raised when a ref cannot be resolved from cached maps."""
      pass
  
  
  def parse_ref(selector: str) -> Optional[str]:
      if selector.startswith("@"):
          rest = selector[1:]
          if rest.startswith("[") and rest.endswith("]"):
              return rest[1:-1]
          return rest
      if selector.startswith("[") and selector.endswith("]") and re.match(r"^\[\d+-\d+]$", selector):
          return selector[1:-1]
      if selector.startswith("ref="):
          return selector[4:]
      if re.match(r"^\d+-\d+$", selector):
          return selector
      return None
  
  
  def resolve_selector(selector: str, xpath_map: Dict[str, str]) -> str:
      ref = parse_ref(selector)
      if ref is None:
          return selector
      xpath = xpath_map.get(ref)
      if xpath is None:
          raise StaleRefError(
              f'Unknown ref "{ref}" - run browser_snapshot first to populate refs '
              f"(have {len(xpath_map)} refs)."
          )
      return xpath
  ```
  
  ## 4. Código Adaptável
  
  ### 4.1 Validação Zod-equivalente com Pydantic/dataclasses
  **Conceito:** Stagehand usa Zod schemas (`z.object({...}).parse(params)`) em todos os handlers para validar parâmetros antes da execução (`elements.ts:7-9`, `navigation.ts:18-19`, `runtime.ts:63-69`).
  **Como adaptar:** Criar dataclasses Pydantic (ou `dataclasses` stdlib com validação manual) para cada ação browser do Hermes (`browser_click_params`, `browser_fill_params`, `browser_wait_params`). Validar no entrypoint de `_dispatch()` em `tools/browser_workstation.py` antes de enviar ao controller.
  **Benefício esperado:** Redução de ~30% em erros de parâmetro malformado; feedback imediato ao modelo com schema violation details em vez de erros genéricos do controller Electron.
  
  ### 4.2 Conversão HTML→Markdown Server-Side
  **Conceito:** `page-info.ts:39-42` usa `NodeHtmlMarkdown.translate()` para converter HTML DOM em markdown limpo antes de retornar ao modelo.
  **Como adaptar:** Adicionar dependência `markdownify` ou `html2text` no Hermes; integrar em `browser_bridge.py` como `browser_get_markdown(selector)` que avalia `document.querySelector(sel).innerHTML` e converte antes de retornar. Alternativamente, injetar script JS leve que faz conversão no browser e retorna texto limpo.
  **Benefício esperado:** Redução de 60-70% em tokens para leitura de conteúdo de página vs HTML bruto; modelo foca em conteúdo, não em parsing de tags.
  
  ### 4.3 Wait Nativo via CDP em vez de Polling
  **Conceito:** Stagehand delega `wait` ao Playwright (`page.waitForSelector`, `page.waitForLoadState`) que usa eventos CDP nativos (`runtime.ts:73-87`).
  **Como adaptar:** No controller Electron do Hermes, expor endpoints CDP diretos para `Page.lifecycleEvent` e `DOM.querySelector` com timeout, em vez de polling via `evaluate_fn` + `time.sleep`. O `browser_readiness.py` manteria a interface declarativa (`BrowserReadinessContract`) mas o backend usaria eventos push em vez de pull.
  **Benefício esperado:** Latência de wait reduzida de ~300ms (poll interval) para <50ms (evento nativo); menor CPU usage durante waits longos.
  
  ### 4.4 Comando Snapshot como Tool de Primeira Classe
  **Conceito:** Stagehand expõe `snapshot` como comando dedicado com flags `--full`, `--filter`, `--max-depth` (`snapshot.ts:20-38`), retornando árvore de acessibilidade estruturada.
  **Como adaptar:** Criar `browser_snapshot` tool no Hermes que chama o controller Electron para obter a accessibility tree, aplica `format_snapshot_tree()` (seção 3.1), cacheia ref maps na sessão, e retorna árvore filtrada. Integrar com `browser_selector_refs.py` para resolução automática em ações subsequentes.
  **Benefício esperado:** Modelo passa a operar sobre representação estruturada e compacta do DOM em vez de screenshots ou HTML bruto; redução estimada de 50-80% em tokens de observação.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | Snapshot filtrado server-side (compact + filter + maxDepth) | 50-80% em observações DOM | Médio | `snapshot-format.ts:7-26` vs ausência em Hermes |
  | HTML→Markdown para leitura de conteúdo | 60-70% em extrações textuais | Baixo | `page-info.ts:39-42` vs `browser_bridge.py` sem conversão |
  | Refs estáveis eliminam re-descoberta de seletores | 20-40% em workflows multi-ação | Médio | `selectors.ts:35-48` vs seletores brutos no Hermes |
  | Projeção durável já existente (extract_items) | Já implementado, 90%+ em extrações grandes | N/A | `browser_projection.py:148-167` |
  | Summary compacto em vez de dataset inline | Já implementado para extract_items | N/A | `browser_projection.py:31-36` INLINE_ITEM_LIMIT=5 |
  | Eliminar polling readiness por eventos CDP | 10-20% em waits (menos turnos de retry) | Alto | `browser_readiness.py:104-123` polling loop vs CDP events |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | Wait nativo CDP em vez de polling 300ms | 3-10x mais rápido em waits | Alto | `browser_readiness.py:92-93` poll_interval=0.3 vs `runtime.ts:73-87` |
  | Cache de ref maps entre ações | Elimina re-query DOM para cada ação | Médio | `selectors.ts:17-20` setRefMaps vs nenhuma cache no Hermes |
  | Screenshot com clip/quality options | Reduz tamanho de imagem transferida | Baixo | `runtime.ts:10-44` clip/quality vs screenshot sem opções no Hermes |
  | Conversão markdown no browser (JS) | Evita round-trip HTML→Python→modelo | Médio | `page-info.ts:39-42` tradução server-side |
  | Batch actions já suportado | Já implementado | N/A | `browser_controller.py:30` browser_batch_actions capability |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | Refs estáveis eliminam alucinação de seletores | Alta: modelo usa refs verificáveis em vez de inventar CSS/XPath | Médio | `selectors.ts:35-48` resolveSelector com erro explícito |
  | Snapshot filtrado remove ruído visual | Alta: modelo vê apenas elementos interativos/relevantes | Médio | `snapshot-format.ts:81-87` isUsefulSnapshotLine |
  | ReadinessContract com códigos diagnósticos | Já implementado: AUTH_REQUIRED, DOM_DRIFT, HYDRATION_PENDING | N/A | `browser_readiness.py:163-173` browser_diagnostic |
  | Validação de parâmetros pré-execução | Média: previne ações malformadas que produzem resultados enganosos | Médio | `elements.ts:7-9` Zod parse vs args livres no Hermes |
  | Projeção durável com validação semântica | Já implementado: SemanticValidator + anomaly reporting | N/A | `browser_projection.py:123-144` |
  | Lease/fence token para prevenção de stale runs | Já implementado | N/A | `browser_controller.py:55-58` assert_action_allowed |
  
  ## 8. Resumo Executivo
  
  ### Recomendações Priorizadas
  
  1. **Implementar Snapshot + Refs Estáveis (Impacto: ALTO, Esforço: MÉDIO)**
     Portar `snapshot-format.ts` e `selectors.ts` para Python (código fornecido na seção 3). Expor `browser_snapshot` tool que retorna árvore filtrada com refs cacheados. Esta é a mudança única com maior ROI: reduz tokens de observação em 50-80%, elimina alucinação de seletores, e habilita workflows multi-ação confiáveis. O código é copiável diretamente com adaptação mínima.
  
  2. **Adicionar Conversão HTML→Markdown Server-Side (Impacto: ALTO, Esforço: BAIXO)**
     Integrar `markdownify` ou equivalente em `browser_bridge.py` como nova função `browser_get_markdown()`. Redução imediata de 60-70% em tokens para leitura de conteúdo textual. Dependência leve, sem mudanças arquiteturais. Pode ser feito em paralelo com item 1.
  
  3. **Validação de Parâmetros Estruturada (Impacto: MÉDIO, Esforço: MÉDIO)**
     Criar dataclasses de validação para cada ação browser e validar no entrypoint `_dispatch()`. Reduz erros de parâmetro malformado em ~30% e fornece feedback estruturado ao modelo. Melhora objetividade sem mudar a arquitetura do controller.
  
  4. **Wait Nativo via CDP Events (Impacto: ALTO, Esforço: ALTO)**
     Substituir polling em `browser_readiness.py` por listeners CDP nativos no controller Electron. Requer mudanças no lado Electron/TypeScript do controller. Justificado apenas após itens 1-3 estarem estáveis, pois o ganho é de latência, não de funcionalidade.
  
  5. **Gestão de Abas como Tool (Impacto: MÉDIO, Esforço: MÉDIO)**
     Expor operações de tab (new/list/switch/close) via broker, similar ao Stagehand `tabs.ts`. Habilita workflows multi-página sem criar/destroy tasks. Depende do controller Electron suportar múltiplas WebContentsViews ativas (já suporta parking/show/hide).
  
  ### Justificativa Técnica
  
  Os itens 1-2 são prioritários porque atacam o gargalo principal identificado: o Hermes Work força o modelo a trabalhar com representações brutas (HTML, seletores inventados, polling) onde o Stagehand oferece representações processadas (markdown, refs, eventos). A arquitetura do Hermes já é superior em resiliência (circuit breaker), segurança (lease/fence, fail-closed binding) e durabilidade (projection/artifacts); o gap está exclusivamente na camada de observação e interação eficiente com o DOM. Os códigos das seções 3.1 e 3.2 são ports diretos testáveis independentemente, sem dependências do controller Electron.
</agent-message>

---

<!-- Relatório 19 -->

# Relatório Comparativo: Browser Nativo Hermes Workstation vs vercel-labs/agent-browser
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (agent-browser) | Hermes Work | Gap Específico |
  |---|---|---|---|
  | Snapshot / AX Tree | `snapshot.rs` constrói árvore de acessibilidade completa com `Accessibility.getFullAXTree`, normaliza zero-width chars, suporta `--interactive`, `--compact`, `--depth`, `--urls`, e resolve refs por backendNodeId com invalidação por documento/loader (`element.rs:151-232`) | `browser_workstation.py:966-1029` (`project_model_browser_payload`) apenas remove duplicação textual do inventory; não há construção própria de AX tree no lado Python — depende inteiramente do controller Electron | Hermes não possui snapshot engine próprio; a projeção é pós-processamento de texto, não parsing estrutural de AX tree |
  | RefMap durável por documento | `element.rs:RefMap` rastreia `(session, loader_id)` por frame; refs sobrevivem entre snapshots se o documento for o mesmo, e são invalidadas quando o loader muda (`observe_document`, `durable_ref`, `remember_durable_ref`) | Não existe equivalente em Python; refs são geradas pelo controller Electron e o Python só as consome via `@eN` no texto do snapshot | Sem ref stability tracking no lado Python; qualquer re-render gera refs novas mesmo sem mudança de DOM |
  | Interação com iframes OOPIF | `interaction.rs` resolve `effective_session_id` por iframe, calcula viewport offset cross-frame, e despacha eventos na sessão correta (`click`, `fill`, `hover` aceitam `iframe_sessions: HashMap`) | `browser_workstation.py` despacha ações via HTTP POST ao controller; não há resolução de sessão de iframe no Python — tudo é delegado ao Electron | Hermes não tem consciência de iframe sessions no routing layer; depende 100% do controller para isso |
  | Select option robusto | `interaction.rs:439-499` normaliza whitespace/zero-width, lista opções disponíveis em erro, distingue match múltiplo de match zero, dispara evento `change` com bubbles | Não há equivalente visível em `tools/browser_workstation.py`; a ação `browser_click` ou `browser_type` seria usada como fallback genérico | Falta primitiva dedicada de select com diagnóstico rico; agente precisa simular clique/teclado |
  | Erros AI-friendly | `browser.rs:237-285` (`to_ai_friendly_error`) classifica locator miss, strict mode violation, element not visible, intercept, timeout — cada um com conselho acionável específico | `browser_supervisor.py:153-174` (`classify_error`) classifica erros de transporte/conexão (TIMEOUT, CONNECTION_REFUSED, AUTH_MISMATCH), mas não erros de interação DOM | Classificação de erro do Hermes foca infraestrutura, não usabilidade da automação; agente recebe erros genéricos como "CAPABILITY_MISSING" |
  | HAR recording / Network capture | `actions.rs:86-149` captura HAR 1.2 completo com request/response bodies, timing, content modes (none/text/all), budgets de tamanho | Não há equivalente em `workstation/`; `browser_read_http` existe como ferramenta mas sem gravação HAR estruturada | Sem capacidade de network tracing para debugging ou extração de dados API |
  | Multi-engine support | `browser.rs` suporta Chrome, Lightpanda, Obscura, WebDriver/Appium/Safari com validação específica por engine | `ARCHITECTURE.md:269-277` lista `electron-chromium`, `agent-browser`, `browser-exec`, `lightpanda` como rotas possíveis, mas implementação real é apenas Electron Chromium | Roteamento multi-runtime é arquitetural mas não implementado; fallback lanes são placeholders |
  | Dialog handling | `actions.rs:PendingDialog` rastreia dialogs por session_id, não bloqueia tabs background, suporta accept/dismiss/prompt | Não há menção a dialog handling em `browser_supervisor.py`, `browser_readiness.py` ou `browser_workstation.py` | Ausência total de gestão de JavaScript dialogs no layer Python |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (agent-browser) | Vantagem Específica |
  |---|---|---|---|
  | Segurança loopback + bearer token | `browser_workstation.py:367-371` valida `http://127.0.0.1:` + token obrigatório; descriptor nunca é exposto ao modelo; resultados são force-redacted (`_force_redact`) | agent-browser usa daemon local via Unix socket/pipe; sem autenticação bearer explícita no protocolo interno | Hermes tem defesa-in-depth contra SSRF e vazamento de credenciais do controller |
  | Circuit breaker ativo | `browser_supervisor.py:57-258` implementa CLOSED/OPEN/HALF_OPEN com cooldown configurável, backoff exponencial, e fast-fail para PROCESS_DEAD/DESCRIPTOR_STALE | agent-browser não tem circuit breaker; falhas são retornadas diretamente ao caller | Hermes evita tempestade de retries em cascata quando o browser está morto |
  | Binding de tarefa durável | `browser_workstation.py:537-544` (`_bind`, `_is_bound`) + estado canônico em `browser-tasks.json`; uma vez bound, task nunca migra silenciosamente para outro browser | agent-browser é stateless por design; cada sessão é independente | Hermes garante que auth/state do browser pertence à tarefa correta através de restarts |
  | Readiness semântica | `browser_readiness.py:19-81` substitui `sleep(N)` por probes observáveis (selector, all_text, any_text, min_text_length); `BrowserReadinessContract` avalia captcha, auth, hydration, DOM drift | agent-browser usa `WaitUntil::Load` / `NetworkIdle` / polling de selector (`AUTH_LOGIN_SELECTOR_POLL_INTERVAL_MS`); sem contrato de readiness declarativo | Hermes tem primitiva de readiness composável e diagnosticável; agente declara o que espera, não quanto tempo |
  | Bridge direto para ArtifactStore | `browser_bridge.py:85-121` extrai dados do browser direto para filesystem/artifact store sem passar por base64/chat context; validação de safe destination | agent-browser retorna dados via stdout/MCP; agente precisa processar e salvar manualmente | Zero-copy extraction elimina tokens de serialização e risco de truncamento |
  | Error classification tipada | `WorkstationBrowserError` (`browser_workstation.py:52-107`) carrega `error_code`, `retryable`, `retry_after_ms`, `state_changed`, `recommended_action`, `resource_ref`, `details`, `http_status` | agent-browser retorna strings de erro; classificação é feita ad-hoc pelo caller | Erros estruturados permitem retry policy automatizada e escalonamento inteligente |
  | Health probe cacheado | `browser_workstation.py:485-502` cacheia health por 750ms com lock thread-safe; evita probing excessivo durante tool assembly | agent-browser não cacheia health; cada comando verifica conexão | Reduz latência de dispatch e carga no controller |
  | Telemetria nativa integrada | `browser_workstation.py:865-926` emite `emit_native_browser_observation` com stage=attempt/result, request/response bytes, duration_ms, error_code; strip_private_browser_telemetry antes do modelo | agent-browser tem tracing (`native_tracing`) mas é opt-in e separado da resposta | Observabilidade built-in sem overhead de configuração; métricas privadas nunca vazam ao modelo |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 Função `to_ai_friendly_error`
  - **Origem:** `referências/02-Browser-Automacao-Web/vercel-labs--agent-browser/cli/src/native/browser.rs:237-285`
  - **Destino sugerido:** `workstation/browser_errors.py` (novo arquivo) ou integrar em `browser_supervisor.py:classify_error`
  - **Trecho adaptado para Python:**
  ```python
  def to_ai_friendly_error(error: str) -> str:
      lower = error.lower()
      if lower.startswith(("element not found", "no element found", "no element at index")):
          detail = error.rstrip(".")
          return f"{detail}. Verify the selector, role, or name is correct and the element exists in the DOM."
      if "strict mode violation" in lower:
          return "Element matched multiple results. Use a more specific selector."
      if "element is not visible" in lower:
          return "Element exists but is not visible. Wait for it to become visible or scroll it into view."
      if "intercept" in lower:
          return "Another element is covering the target element. Try scrolling or closing overlays."
      if "timeout" in lower:
          return "Operation timed out. The page may still be loading or the element may not exist."
      return error
  ```
  - **Benefício:** Agentes recebem diagnósticos acionáveis em vez de erros genéricos CDP/HTTP.
  
  ### 3.2 Normalização de zero-width characters
  - **Origem:** `referências/.../cli/src/native/snapshot.rs:164-180`
  - **Destino sugerido:** `workstation/browser_readiness.py` ou novo `workstation/dom_utils.py`
  - **Trecho:**
  ```python
  import re
  
  _ZERO_WIDTH_RE = re.compile(r'[﻿​‌‍⁠]')
  
  def normalize_snapshot_name(name: str) -> str:
      """Remove zero-width chars and normalize NBSP to space."""
      return _ZERO_WIDTH_RE.sub('', name.replace(' ', ' '))
  ```
  - **Benefício:** Comparações de texto de snapshot tornam-se determinísticas; evita falsos negativos em readiness checks.
  
  ### 3.3 JavaScript de select_option robusto
  - **Origem:** `referências/.../cli/src/native/interaction.rs:459-494`
  - **Destino sugerido:** Injetar como script de `browser_select` action no controller Electron, ou usar via `browser_bridge.browser_save_json` como expressão JS
  - **Nota:** O JS completo (36 linhas) pode ser copiado integralmente; ele já é auto-contido e não depende de imports Rust.
  - **Benefício:** Primitiva de select com diagnóstico de opções disponíveis, normalização de whitespace, e distinção entre match zero/múltiplo.
  
  ## 4. Código Adaptável
  
  ### 4.1 RefMap com invalidação por documento/loader
  - **Conceito:** `element.rs:RefMap` mantém mapa de `(page_session, frame_id) -> (session, loader_id) -> {backend_node_id -> ref}`. Quando o loader muda, refs antigas são invalidadas automaticamente.
  - **Como adaptar:** Implementar classe `PythonRefMap` em `workstation/ref_map.py` que consome eventos do controller Electron (via `/events` endpoint já existente em `browser_workstation.py:515-527`). O controller já emite eventos de navegação; o Python mapeia `loaderId` changes para invalidação.
  - **Benefício esperado:** Refs estáveis entre snapshots consecutivos reduzem re-resolução de elementos em ~40-60% para páginas SPA que não recarregam. Economia direta de tokens de snapshot.
  
  ### 4.2 Snapshot compact mode / interactive-only
  - **Conceito:** `snapshot.rs:SnapshotOptions` suporta `interactive: bool` (apenas elementos interativos), `compact: bool` (sem atributos decorativos), `depth: Option<usize>` (limitar profundidade).
  - **Como adaptar:** Adicionar parâmetros equivalentes ao schema de `browser_snapshot` no `tools/browser_workstation.py:_WORKSTATION_SCHEMA_TOOLS`. O controller Electron precisaria suportar esses filtros na geração do inventory. Alternativamente, filtrar no Python pós-recepção usando heurísticas de role/tag.
  - **Benefício esperado:** Redução de 50-80% no tamanho de snapshots para páginas complexas quando o agente só precisa de elementos clicáveis/preenchíveis.
  
  ### 4.3 Dialog tracking por sessão
  - **Conceito:** `actions.rs:PendingDialog` armazena dialog type/message/url/session_id; dialogs de background tabs não bloqueiam a tab ativa.
  - **Como adaptar:** Adicionar campo `pending_dialog` ao payload de resposta do controller. Em `browser_supervisor.py`, adicionar estado de dialog tracking e ação `browser_dialog_accept`/`browser_dialog_dismiss`. O controller Electron já recebe eventos `Page.javascriptDialogOpening` via CDP.
  - **Benefício esperado:** Elimina hang silencioso quando sites abrem alert/confirm/prompt; agente pode resolver dialogs programaticamente.
  
  ### 4.4 Renderer liveness probe
  - **Conceito:** `browser.rs:119-134` usa timeout curto (3s) para detectar tabs descartadas pelo Chromium; se não responde, reativa e aguarda até 10s.
  - **Como adaptar:** Em `browser_supervisor.py:check_health`, adicionar probe de renderer além do `/health` HTTP. Usar `Runtime.evaluate({expression: "1"})` com timeout curto como canary de renderer vivo.
  - **Benefício esperado:** Detecção proativa de tabs frozen/discarded antes que o agente tente uma ação e falhe; melhora confiabilidade em sessões longas.
  
  ### 4.5 HAR/network capture estruturado
  - **Conceito:** `actions.rs:HarEntry` + `HarContentMode` capturam request/response bodies com budgets de tamanho (2MB/body, 64MB total).
  - **Como adaptar:** Adicionar endpoint `/network/har` ao controller Electron que exporta HAR 1.2. Em `browser_workstation.py`, nova ação `browser_read_har` que salva via `browser_bridge.browser_capture_to_artifact`.
  - **Benefício esperado:** Capacidade de extrair dados de APIs REST/GraphQL diretamente do tráfego de rede, sem depender de scraping DOM.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | Snapshot compact/interactive-only mode | 50-80% | Médio | `snapshot.rs:SnapshotOptions` vs ausência em `browser_workstation.py` |
  | Projeção de elements já implementada (manter) | 30-50% (já ativo) | Nenhum | `browser_workstation.py:966-1029` `project_model_browser_payload` |
  | RefMap durável por documento | 40-60% em SPAs | Alto | `element.rs:151-232` vs ausência em Python |
  | Readiness semântica (evitar sleep+retry) | 20-40% por turno | Baixo | `browser_readiness.py:19-81` já existe; expandir contratos |
  | Bridge direto para ArtifactStore (evitar base64) | 60-90% para dados grandes | Baixo | `browser_bridge.py:85-121` já existe; expandir uso |
  | Normalização de zero-width chars | 5-10% em comparações | Baixo | `snapshot.rs:164-180` |
  | HAR extraction vs DOM scraping | 70-90% para dados API | Médio | `actions.rs:86-149` |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | Health probe cacheado (já ativo, 750ms TTL) | -50ms por dispatch | Nenhum | `browser_workstation.py:485-502` |
  | Renderer liveness probe antecipado | Evita 3-10s de timeout em tabs descartadas | Médio | `browser.rs:119-134` |
  | Circuit breaker half-open probe | Recupera mais rápido de falhas transitórias | Baixo | `browser_supervisor.py:249-258` já existe |
  | Select option dedicado vs click+type simulado | -200-500ms por interação | Médio | `interaction.rs:439-499` |
  | Readiness polling interval tuning | -300ms médio por página | Baixo | `browser_readiness.py:93` poll_interval=0.3s; ajustar por tipo de página |
  | Parallel iframe session resolution | -100-300ms em páginas multi-iframe | Alto | `interaction.rs` resolve effective_session_id inline |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | Erros AI-friendly classificados | Alta: agente toma decisões corretas sobre retry/fallback | Baixo | `browser.rs:237-285` |
  | Select option com lista de disponíveis | Alta: elimina tentativa-e-erro cego | Médio | `interaction.rs:459-494` |
  | Readiness contract com código de falha | Alta: distingue auth/captcha/DOM drift/hydration | Baixo | `browser_readiness.py:131-173` já existe |
  | Dialog tracking explícito | Alta: evita hang silencioso e falso progresso | Médio | `actions.rs:PendingDialog` |
  | Ref stability tracking | Média: reduz flakiness em SPAs | Alto | `element.rs:RefMap.observe_document` |
  | Network evidence (HAR) vs inferência DOM | Alta: dados factuais em vez de parsing frágil | Médio | `actions.rs:HarEntry` |
  | Force-redact de resultados (já ativo) | Alta: previne vazamento de secrets ao modelo | Nenhum | `browser_workstation.py:_force_redact` |
  
  ## 8. Resumo Executivo
  
  **Top 5 recomendações priorizadas por impacto/esforço:**
  
  1. **Adotar `to_ai_friendly_error` no supervisor Python** (Baixo esforço, Alto impacto). Copiar/adaptar a função de `browser.rs:237-285` para `workstation/browser_errors.py`. Cada erro de interação DOM passa a ter diagnóstico acionável. Reduz ciclos de tentativa-e-erro do agente em ~30%. Custo: ~30 linhas de Python.
  
  2. **Implementar snapshot compact/interactive-only** (Médio esforço, Muito Alto impacto). Adicionar parâmetros `compact` e `interactive` ao schema de `browser_snapshot` e filtrar no controller Electron ou no Python pós-recepção. Páginas típicas têm 200-500 elementos; modo interativo retorna 20-50. Economia de 50-80% de tokens por snapshot. Custo: modificação no controller + ~50 linhas Python.
  
  3. **Adicionar primitiva `browser_select` com diagnóstico rico** (Médio esforço, Alto impacto). Portar o JS de `interaction.rs:459-494` como ação dedicada. Elimina a necessidade de o agente simular clique em dropdown + selecionar opção via teclado. Inclui normalização de whitespace e lista de opções disponíveis em caso de erro. Custo: ~80 linhas (JS + Python wrapper).
  
  4. **Implementar RefMap durável por documento no Python** (Alto esforço, Muito Alto impacto para SPAs). Criar `workstation/ref_map.py` que consome eventos de navegação do controller e mantém estabilidade de refs entre snapshots. Para aplicações SPA que não recarregam, reduz re-resolução de elementos em 40-60%. Custo: ~200 linhas Python + integração com `/events`.
  
  5. **Adicionar dialog tracking e ações de resolução** (Médio esforço, Alto impacto em confiabilidade). Expor `pending_dialog` no payload de resposta do controller e criar ações `browser_dialog_accept`/`browser_dialog_dismiss`. Previne hangs silenciosos que hoje exigem intervenção humana ou timeout. Custo: ~100 linhas Python + modificação no controller.
  
  **Justificativa técnica transversal:** O Hermes Workstation já supera a referência em segurança (loopback+bearer), resiliência (circuit breaker, binding durável) e extração de dados (bridge direto). Os gaps principais estão na *inteligência da interação*: snapshot eficiente, refs estáveis, erros acionáveis e primitivas de alto nível (select, dialog). As recomendações acima fecham esses gaps com custo proporcional ao benefício, aproveitando que a arquitetura do Hermes já tem os hooks necessários (controller HTTP, eventos, artifact store, readiness contracts).
</agent-message>

---

<!-- Relatório 20 -->

# Relatório Comparativo: Browser Hermes Workstation vs PlatonAI Browser4
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (Browser4) | Hermes Work | Gap Específico |
  |---|---|---|---|
  | Compressão de contexto no loop de ferramentas | `ToolLoopCompressor.kt` (linhas 56-450): compressão transacional com validação de encolhimento, retenção da última page view completa, budget cumulativo de tokens por tool result, proteção de documentos de conhecimento (`protectedToolNames`), ledger de auditoria (`CompactionLedger`) e retry estruturado de sumarização | Não existe equivalente em Python. A compressão do Hermes é genérica (SessionDB/compaction) e não possui awareness de browser loop, page view retention, nem pruning model-free de tool results individuais | O Hermes reenvia snapshots completos repetidamente; não há deduplicação nem diff de page views no contexto do agente, causando explosão de tokens em tarefas web longas |
  | Deduplicação de page views | `PageViewDeduper.kt` (linhas 47-265): fingerprint SHA-256 normalizado, folding de duplicatas exatas em referência compacta, diff prefix/suffix entre views consecutivas, strip de regiões voláteis (bounding boxes), integração com CompactionLedger para rastreabilidade pós-compressão | `project_model_browser_payload()` em `tools/browser_workstation.py` (linhas 966-1029) remove apenas a lista `elements` redundante quando o snapshot text já a carrega. Não há fingerprinting, diff, folding de duplicatas ou strip de regiões voláteis | Snapshots idênticos ou quase-idênticos entram múltiplas vezes no contexto; o modelo paga tokens integrais por cada re-view da mesma página |
  | Circuit breaker multi-tipo | `CircuitBreaker.kt` (linhas 16-126): três contadores independentes (LLM, Validation, Execution) com thresholds separados, reset por tipo, health check agregado, exceção tipada `CircuitBreakerTrippedException` com failure type e count | `BrowserRuntimeSupervisor` em `browser_supervisor.py` (linhas 63-302): circuit breaker único com estados CLOSED/OPEN/HALF_OPEN baseado em falhas consecutivas genéricas, sem distinção entre falha de LLM, validação ou execução | Falhas de validação de DOM (transitórias) podem abrir o circuito e bloquear ações legítimas; falhas de LLM não são isoladas de falhas de transporte |
  | Readiness semântica avançada | `RobustBrowserAgent.kt` integra `PageStateTracker`, verificação de hidratação, detecção de canvas/non-DOM surface, entity identity drift, e `BrowserReadinessContract` com classificação diagnóstica estruturada (`browser_diagnostic()`) | `browser_readiness.py` (linhas 19-173): `build_readiness_expression()` gera JS inline para selector/text/min_length; `BrowserReadinessContract.evaluate()` verifica auth/hydration/entity_identity/semantic_targets mas sem integração ao loop do agente como gate automático | O readiness é uma função utilitária chamada ad-hoc; não há integration automática no dispatch loop que impeça ações antes da página estar semanticamente pronta |
  | Tool disclosure progressivo | `RobustBrowserAgent.kt` (linhas 116-195): `CliEngineToolSet` com initial specs adaptativos por tipo de tarefa (browsing vs coding), disclosure registry para `system.listTools`/`exposeTools`, fallback para core set quando pattern list está misconfigured | Schemas fixos em `_WORKSTATION_SCHEMA_TOOLS` (`tools/browser_workstation.py` linhas 142-163); todos os tools são expostos ou nenhum, sem adaptação por tipo de tarefa ou progressive disclosure | O modelo recebe todos os browser tools mesmo em tarefas simples, aumentando prompt size e risco de chamadas inadequadas |
  | Memória de agente integrada ao browser loop | `AgentMemory` em `RobustBrowserAgent.kt` (linhas 281-320): L0 event log, query, scratchpad, run-start recall, external memory bridge, user preference extraction do summary, consolidation scheduling | Não há memória de agente específica para browser no Hermes. `ProceduralMemory` existe no runtime V3 mas não é integrada ao browser tool loop | O agente perde contexto entre steps de uma mesma tarefa browser; não há recall automático de observações anteriores |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (Browser4) | Vantagem Específica |
  |---|---|---|---|
  | Segurança e isolamento de perfil | Perfil Chromium dedicado (`%LOCALAPPDATA%\HermesWorkstation\Browser\User Data`), cookies isolados do Desktop, controller loopback-only com bearer token, descriptor nunca exposto ao modelo, redação forçada (`_force_redact`) antes de cruzar tool boundary (`tools/browser_workstation.py` linhas 13-14, 369-371, 927) | Browser4 usa CDP direto via PulsarWebDriver; não há evidência de isolamento de perfil, loopback enforcement ou redação automática de resultados | O Hermes garante que secrets/tokens nunca vazam para o contexto do modelo e que o browser do agente não compartilha estado com o browser do usuário |
  | Binding de tarefa e fail-closed | `_bind(key)` após primeira ação bem-sucedida (`tools/browser_workstation.py` linha 932); canonical binding via `browser-tasks.json`; task bound nunca faz failover silencioso para outro browser; routing desabilitado por default (`workstation_routing_enabled()` retorna False) | Browser4 não possui conceito de task binding persistente; agent pode trocar de browser/session sem controle explícito | O Hermes previne perda silenciosa de autenticação/estado quando o controller falha; a tarefa para em vez de continuar em um browser diferente |
  | Lease de controle humano | `BrowserControlLeaseManager.assert_action_allowed()` chamado em todo dispatch (`tools/browser_workstation.py` linhas 1085-1092); fence_token por ação; parent/child task registration | Browser4 não possui mecanismo de lease/fence para controle humano | O Hermes permite que o humano retome controle a qualquer momento e previne que o agente execute ações sensíveis sem autorização |
  | Telemetria e journaling estruturado | `emit_native_browser_observation()` em cada tentativa e resultado (`tools/browser_workstation.py` linhas 866-921); journal projection via `_record_browser_controller_outcome`; métricas de request/response bytes, duration, error_code; private telemetry stripped antes do modelo | `StructuredAgentLogger` e `CliLoopTracer` existem mas são focados em tracing de inference, não em telemetria operacional de browser actions | O Hermes tem observabilidade operacional completa de cada ação browser, independente do inference trace |
  | Projeção de payload model-facing | `project_model_browser_payload()` remove `elements` redundante mantendo `element_index` para campos não expressáveis em texto (`tools/browser_workstation.py` linhas 966-1029); fails open quando grammar difere | Browser4 envia snapshots completos sem projeção dedicada | O Hermes reduz tokens por snapshot sem perder endereçabilidade de elementos |
  | Readiness como contrato declarativo | `BrowserReadinessContract` com avaliação estruturada de auth/hydration/entity_identity/semantic_targets/captcha/surface (`browser_readiness.py` linhas 131-173); diagnóstico classificado (`browser_diagnostic()`) | Browser4 tem readiness implícito no agent loop mas sem contrato declarativo reutilizável | O Hermes permite definir contratos de readiness por rota/página e reutilizá-los independentemente do agent loop |
  | Bridge segura para ArtifactStore | `browser_bridge.py`: extração direta de DOM/JS para filesystem ou ArtifactStore sem passar por base64/chat context; validação de destino seguro (`_validate_safe_destination`); captura estruturada com schema opcional | Browser4 salva via coding tools genéricos; não há bridge dedicada com validação de segurança | O Hermes extrai dados do browser diretamente para armazenamento durável sem inflar o contexto do modelo |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 Algoritmo de diff prefix/suffix para page views
  **Origem:** `referências/02-Browser-Automacao-Web/platonai--Browser4/browser4-agentic/src/main/kotlin/ai/platon/pulsar/agentic/inference/chat/PageViewDeduper.kt`, método `buildDiff()` (linhas 144-173)
  
  **Destino sugerido:** `workstation/browser_readiness.py` ou novo módulo `workstation/browser_dedup.py`
  
  **Trecho adaptável (pseudocódigo Python fiel ao algoritmo):**
  ```python
  def build_page_diff(previous_normalized: str, current_normalized: str, *, max_chars: int = 3000, context_lines: int = 3, max_changed_ratio: float = 0.6) -> str | None:
      before = [line for line in previous_normalized.splitlines() if line.strip()]
      after = [line for line in current_normalized.splitlines() if line.strip()]
      prefix = 0
      while prefix < len(before) and prefix < len(after) and before[prefix] == after[prefix]:
          prefix += 1
      suffix = 0
      while suffix < len(before) - prefix and suffix < len(after) - prefix and before[-(suffix+1)] == after[-(suffix+1)]:
          suffix += 1
      removed = before[prefix:len(before)-suffix]
      added = after[prefix:len(after)-suffix]
      if not removed and not added:
          return None
      changed = len(removed) + len(added)
      total = max(len(before), len(after))
      if changed / total > max_changed_ratio:
          return None
      lines = []
      ctx_before = max(0, prefix - context_lines)
      for i in range(ctx_before, prefix):
          lines.append(f"  {before[i]}")
      for r in removed:
          lines.append(f"- {r}")
      for a in added:
          lines.append(f"+ {a}")
      tail_start = len(before) - suffix
      for i in range(tail_start, min(len(before), tail_start + context_lines)):
          lines.append(f"  {before[i]}")
      result = "\n".join(lines).rstrip()
      return result if len(result) <= max_chars else None
  ```
  
  ### 3.2 Fingerprint normalizado com strip de regiões voláteis
  **Origem:** `PageViewDeduper.kt`, métodos `normalizeOf()` e `fingerprintOf()` (linhas 223-241)
  
  **Destino sugerido:** `workstation/browser_dedup.py`
  
  **Trecho adaptável:**
  ```python
  import hashlib, re
  
  _STRIP_PATTERNS = [re.compile(r"\[box=[^\]]*\]")]
  _WHITESPACE = re.compile(r"\s+")
  
  def normalize_page_text(text: str, strip_patterns: list[re.Pattern] | None = None) -> str:
      patterns = strip_patterns or _STRIP_PATTERNS
      t = text
      for p in patterns:
          t = p.sub("", t)
      return "\n".join(
          _WHITESPACE.sub(" ", line.strip())
          for line in t.splitlines()
          if line.strip()
      )
  
  def fingerprint_page_text(text: str, strip_patterns: list[re.Pattern] | None = None, hex_chars: int = 16) -> str:
      normalized = normalize_page_text(text, strip_patterns)
      digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
      return digest[:hex_chars]
  ```
  
  ### 3.3 Pruning model-free de tool results (head + marker + tail)
  **Origem:** `ToolLoopCompressor.kt`, método `pruneToolResults()` (linhas 139-156)
  
  **Destino sugerido:** Integrar na compaction existente do Hermes (`agent/compression/` ou `workstation/compaction/`)
  
  **Conceito copiável:** A lógica de substituir o meio de tool results oversized por `PRUNE_MARKER = "\n[... tool result middle pruned ...]\n"` mantendo head e tail é diretamente portável. O Hermes deve adicionar isso como pré-processamento antes da compaction LLM-based.
  
  ## 4. Código Adaptável
  
  ### 4.1 Retenção da última page view completa durante compressão
  **Conceito:** `ToolLoopCompressor.compressCore()` (linhas 257-272) identifica o round contendo a última FULL page view e ajusta `keepFrom` para nunca compactar esse round, pois é o working context do modelo.
  
  **Como adaptar:** Na compaction do Hermes, antes de selecionar o corte, escanear os tool results recentes buscando `browser_snapshot`/`browser_vision` completos (não diffs/referências). Forçar o retain window a incluir pelo menos esse round.
  
  **Benefício esperado:** Previne que o modelo perca o estado atual da página após compressão, eliminando re-snapshots desnecessários e reduzindo tokens em 15-30% em tarefas web longas.
  
  ### 4.2 Budget cumulativo de tokens para tool results
  **Conceito:** `enforceResultTokenBudget()` (linhas 167-195) limita o total estimado de tokens de todos os tool results, encolhendo os MAIS ANTIGOS primeiro e protegendo o mais recente.
  
  **Como adaptar:** Adicionar ao pipeline de preparação de contexto do Hermes um passo que estime tokens dos tool results acumulados e aplique pruning nos mais antigos quando o budget for excedido. Usar a mesma heurística de chars/token (3.5 chars/token).
  
  **Benefício esperado:** Previne que sessões browser longas acumulem tool results além do budget, mantendo o contexto dentro dos limites sem depender exclusivamente de compressão LLM.
  
  ### 4.3 Circuit breaker multi-tipo
  **Conceito:** `CircuitBreaker.kt` separa falhas em LLM, Validation e Execution com thresholds independentes.
  
  **Como adaptar:** Refatorar `BrowserRuntimeSupervisor` para manter três contadores. Classificar erros usando `ControllerErrorKind` existente: TIMEOUT/CONNECTION_REFUSED → EXECUTION; AUTH_MISMATCH/PROTOCOL_MISMATCH → VALIDATION; erros de modelo/provider → LLM. Reset individual por tipo.
  
  **Benefício esperado:** Falhas transitórias de DOM/validation não bloqueiam transporte; falhas de LLM não disparam recovery de browser; diagnóstico mais preciso para o agente decidir próxima ação.
  
  ### 4.4 Progressive tool disclosure por tipo de tarefa
  **Conceito:** `buildCliEngineToolSet()` adapta o initial tool set baseado em `codingMode` vs browsing, com fallback para core set.
  
  **Como adaptar:** Em `workstation_schema_tools_for_current_session()`, adicionar parâmetro `task_type` e retornar subconjuntos: browsing tasks recebem browser tools + file basics; coding tasks recebem coding core + browser mínimo. Expor `system.list_tools` equivalente para descoberta sob demanda.
  
  **Benefício esperado:** Reduz prompt size em 20-40% para tarefas que não precisam de todos os tools; reduz chamadas inadequadas.
  
  ### 4.5 Round tool digest para continuação entre rounds
  **Conceito:** `cliRoundToolDigest()` (linhas 223-232) resume os últimos N tool executions em uma linha compacta que é injetada na próxima mensagem de continuação, prevenindo re-execução.
  
  **Como adaptar:** Após cada batch de tool calls no Hermes, gerar um digest bounded (últimos 6 tools, primeira linha ≤200 chars cada, total ≤2000 chars) e incluí-lo como system message ou user continuation nudge.
  
  **Benefício esperado:** Previne re-execução de tools já rodados após compressão ou handoff; melhora continuidade em tarefas multi-step.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | Page view deduplication (fingerprint + folding) | 25-40% em tarefas web longas | Médio | `PageViewDeduper.kt` vs ausência no Hermes |
  | Page view diffing (substituir snapshot completo por diff) | 15-30% por re-view | Médio | `PageViewDeduper.buildDiff()` linhas 144-173 |
  | Pruning model-free de tool results oversized | 10-20% | Baixo | `ToolLoopCompressor.pruneToolResults()` linhas 139-156 |
  | Budget cumulativo de tool result tokens | 10-25% | Médio | `ToolLoopCompressor.enforceResultTokenBudget()` linhas 167-195 |
  | Progressive tool disclosure | 20-40% de prompt size | Médio | `buildCliEngineToolSet()` linhas 148-195 |
  | Proteção de knowledge documents contra pruning | 5-10% (evita re-fetch) | Baixo | `protectedToolNames` em `ToolLoopCompressor` linha 67 |
  | Round tool digest para prevenir re-execução | 5-15% | Baixo | `cliRoundToolDigest()` linhas 223-232 |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | Readiness gate automático no dispatch loop | Elimina ações prematuras que falham e precisam retry | Médio | `BrowserReadinessContract.evaluate()` já existe mas não é integrado ao loop |
  | Circuit breaker multi-tipo (fail-fast por categoria) | Reduz wait time em falhas não-recuperáveis | Médio | `CircuitBreaker.kt` vs supervisor genérico |
  | Skip de re-snapshot quando fingerprint é idêntico | Elimina round-trip CDP desnecessário | Médio | `PageViewDeduper.decorate()` folding |
  | Batch action optimization (já parcialmente implementado) | Reduz round-trips HTTP para N ações | Já presente | `browser_batch_actions` em `_WORKSTATION_SCHEMA_TOOLS` |
  | Health probe caching (já implementado) | 0.75s cache evita probes redundantes | Já presente | `_AVAILABILITY_CACHE_SECONDS` em `browser_workstation.py` linha 44 |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | Diff em vez de snapshot completo foca atenção do modelo no que mudou | Alta: reduz alucinação baseada em conteúdo stale | Médio | `PageViewDeduper.buildDiff()` |
  | Readiness contract com diagnóstico classificado | Alta: modelo recebe razão estruturada para esperar/retry em vez de erro genérico | Baixo | `browser_diagnostic()` já existe; falta integração |
  | Compaction com required sections (Page State obrigatório) | Alta: previne perda de estado de página durante compressão | Médio | `REQUIRED_SUMMARY_SECTIONS` em `ToolLoopCompressor` linhas 375-385 |
  | Protected tool names para knowledge documents | Média: modelo lê documento inteiro em vez de shard truncado | Baixo | `protectedToolNames` config |
  | Structured error classification no circuit breaker | Média: modelo distingue falha transitória de permanente | Médio | `ControllerErrorKind` enum já existe; precisa integração multi-tipo |
  | Round digest previne re-execução baseada em memória falível | Alta: modelo recebe resumo factual do que já executou | Baixo | `cliRoundToolDigest()` |
  
  ## 8. Resumo Executivo
  
  ### Recomendações Priorizadas
  
  1. **Implementar Page View Deduplication e Diffing (Impacto: Alto, Esforço: Médio)**
     Portar `PageViewDeduper` para Python como `workstation/browser_dedup.py`. Integrar no pipeline de tool result processing em `tools/browser_workstation.py` antes do resultado chegar ao contexto do modelo. Isso sozinho pode reduzir consumo de tokens em 25-40% em tarefas web típicas. Os algoritmos de fingerprint, normalize e diff são puramente determinísticos e não dependem de infraestrutura Kotlin/JVM.
  
  2. **Adicionar Pruning Model-Free e Budget Cumulativo de Tool Results (Impacto: Alto, Esforço: Baixo-Médio)**
     Implementar `pruneToolResults()` e `enforceResultTokenBudget()` como pré-processamento na compaction do Hermes. Não requer chamada LLM adicional. Protege contra explosão de contexto em sessões longas. A lógica é ~100 linhas de Python e se integra ao pipeline existente de compressão.
  
  3. **Refatorar Circuit Breaker para Multi-Tipo (Impacto: Médio, Esforço: Médio)**
     Separar `BrowserRuntimeSupervisor` em três contadores (LLM/Validation/Execution). Usa a enum `ControllerErrorKind` já existente para classificação. Melhora resiliência e diagnóstico sem mudar a interface externa. Previne que falhas de validação DOM bloqueiem transporte legítimo.
  
  4. **Integrar Readiness Contract como Gate Automático no Dispatch (Impacto: Médio, Esforço: Baixo)**
     `BrowserReadinessContract` e `browser_diagnostic()` já existem em `browser_readiness.py` mas são chamados ad-hoc. Integrar como pré-condição em `workstation_routed_browser_handler()` para ações que exigem página pronta (click, type, extract). Retorna diagnóstico estruturado ao modelo em vez de erro genérico, permitindo decisão informada (esperar, retry, escalate).
  
  5. **Implementar Progressive Tool Disclosure por Tipo de Tarefa (Impacto: Médio-Alto, Esforço: Médio)**
     Adaptar `workstation_schema_tools_for_current_session()` para retornar subconjuntos baseados em task classification. Browsing tasks recebem browser tools + file basics; coding tasks recebem coding core + browser mínimo. Reduz prompt size e risco de chamadas inadequadas. Requer task classifier leve (pode usar directive grammar já existente no batch detection).
  
  ### Justificativa Técnica
  
  As recomendações 1 e 2 têm maior ROI porque atacam o problema mais caro do browser automation com LLMs: a repetição de conteúdo quase-idêntico no contexto. O Browser4 resolveu isso com deduplication e diffing em append-time, antes do conteúdo entrar na conversa. O Hermes atualmente projeta apenas a redundância elements/snapshot-text (`project_model_browser_payload`), mas não aborda duplicatas cross-turn nem mudanças incrementais. A implementação é determinística, testável unitariamente e não introduz dependências externas.
  
  A recomendação 3 melhora resiliência operacional. O supervisor atual trata todas as falhas igualmente, o que é subótimo para browser automation onde falhas de DOM são frequentes e transitórias enquanto falhas de transporte são raras e graves.
  
  As recomendações 4 e 5 melhoram a qualidade das decisões do modelo ao fornecer informação estruturada (diagnóstico de readiness) e reduzir ruído (tools irrelevantes). São complementares às otimizações de tokens e multiplicam seu efeito.
</agent-message>

---

<!-- Relatório 21 -->

# Relatório Comparativo: Browser Nativo Hermes Workstation vs visnia-ai/browser-agent
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (visnia-ai) | Hermes Work | Gap Específico |
  |---|---|---|---|
  | Projeção DOM para LLM | Projeção semântica canônica via AX Tree (`semantic-projection.ts`), com roles tipados (INTERACTIVE/STRUCTURAL/TEXT), refs opacos `r{base36}`, merge de texto adjacente, truncamento multi-nível e redação de auth | `browser_projection.py` foca em projeção durável de *resultados* (artifacts/WorkItems); não há camada de simplificação AX/DOM estruturada para consumo direto pelo modelo no prompt | Ausência de pipeline de percepção semântica compacta; o modelo recebe snapshots brutos ou JSON de extração, não uma árvore acessibilidade filtrada e token-efficient |
  | Economia de Tokens no Loop | Delta projection (`cumulative` mode envia só unified diff após reset), large-doc short-circuit (>250K chars → preview 600 chars), text dedup/merge, href omission/truncation, OpenAI prompt caching explícito | Sem modo delta; `browser_projection.py` retorna summary JSON mas não reduz o custo de *percepção* da página; readiness polling repete expressão completa a cada ciclo | Custo de contexto por step é significativamente maior em páginas estáveis ou grandes; falta cache de prefixo de prompt |
  | Detecção de Estagnação | Dual streak: `sameActionSignatureStreak` + `noProgressStreak` com thresholds configuráveis e warning estruturado (`run-agent.ts` lines 451-477) | `BrowserRuntimeSupervisor` tem circuit breaker para falhas de conexão/processo, mas não detecta estagnação lógica (agente repetindo ações sem progresso observável) | Agente pode entrar em loop infinito de ações válidas mas inúteis sem mecanismo de detecção automática |
  | Verificação de Completude | Completion verifier separado (LLM call) com feedback estruturado, checklist cumulativo com IDs estáveis C-number, retry com regeneração de checklist (`run-agent.ts` lines 79-140, 492-531) | Validação semântica existe (`SemanticValidator` em `browser_projection.py`) mas é pós-extração e limitada a campos obrigatórios; não há verificador de completude de tarefa com retry guiado | Maior risco de resultados incompletos ou alucinados sendo aceitos como finais |
  | Session Snapshot/Rollback | `snapshotSession()` / `restoreSession()` antes/depois de cada step com rollback completo de checklist, memory, projection history (`run-agent.ts` lines 561-646) | `BrowserControlLeaseManager` gerencia leases human/agent com fence tokens, mas não há snapshot transacional do estado de execução do agente | Falha em um step pode corromper estado acumulado; recovery depende de re-execução manual |
  | Step Timing Instrumentation | `measureStepPart()` separa `tokenGenerationMs` de `browserInteractionMs`; métricas por step (`run-agent.ts` lines 360-400) | Telemetria local mencionada em ARCHITECTURE.md mas sem implementação observável de timing split nos arquivos browser_*.py | Impossível diagnosticar se gargalo é LLM ou browser sem instrumentação externa |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (visnia-ai) | Vantagem Específica |
  |---|---|---|---|
  | Segurança de Controle Humano | `BrowserControlLeaseManager` com fence tokens, geração incremental, propagação pai-filho, lista explícita de DESTRUCTIVE_ACTIONS bloqueadas durante lease humano (`browser_session.py` lines 62-198) | `user_takeover` tool com categorias (auth/otp/payment) mas sem mecanismo de fence token ou propagação hierárquica de lease | Proteção contra race conditions entre agente e humano é formalmente mais robusta no Hermes; fence token impede ações com autoridade revogada |
  | Supervisão de Runtime | `BrowserRuntimeSupervisor` com circuit breaker (CLOSED/OPEN/HALF_OPEN), classificação tipada de erros (8 ControllerErrorKind), backoff exponencial, limpeza automática de descriptor stale (`browser_supervisor.py`) | Retry por step individual sem circuit breaker global; erro classificado por texto/abort signal | Resiliência a falhas de processo/conexão é sistêmica, não reativa por tentativa |
  | Persistência Durável de Resultados | Extração → ArtifactStore + DurableTaskStore + SemanticValidator em pipeline único; summary compacto devolvido ao modelo, dados completos persistidos fora do contexto (`browser_projection.py` lines 39-167) | Resultados retornados inline ou via memory files; sem camada de artifact store integrada ao fluxo de extração | Dados extraídos sobrevivem a restarts/compressão de contexto; modelo não carrega datasets pesados no prompt |
  | Bridge de Segurança para Escrita | `_validate_safe_destination()` com `Path.is_relative_to()` previne path traversal; validação antes de qualquer escrita em disco (`browser_bridge.py` lines 25-40) | File download/save gerenciado pelo runtime sem validação explícita de sandbox de destino visível no código lido | Garantia estrutural contra escrita fora de workspaces permitidos |
  | Readiness Semântica Declarativa | `BrowserReadinessContract` com avaliação baseada em semantic_targets, entity_identity, hydration, captcha detection; diagnóstico classificado (`browser_readiness.py` lines 131-173) | Polling genérico via AX tree readiness; sem contrato declarativo de "página pronta" por domínio | Readiness é específica por endpoint/domínio, não heurística genérica |
  | Transações Browser com Verificação | `transaction_contract()` exige semantic_anchor, phase boundaries (PREPARE/INTERACT/COMMIT/VERIFY), evidence strength mínima por tipo de mutação (`browser_transaction.py`) | Ações são steps individuais sem conceito de transação multi-step com verificação obrigatória | Mutations críticas têm admissão formal e verificação pós-execução; previne commits cegos |
  | Abstração Multi-Runtime | `BrowserRuntime` ABC com capabilities declarativas (persistent_profile, visible, background, cdp, screenshots, task_binding); routing configurável entre electron-chromium/lightpanda/agent-browser/browser-exec (`browser_runtime.py`, ARCHITECTURE.md) | Runtime único (Playwright/CDP via ai-sdk provider) | Portabilidade entre runtimes sem reescrita de lógica de negócio |
  
  ## 3. Código Copiável Diretamente
  
  | Arquivo Origem | Função/Trecho | Linhas | Destino Sugerido no Hermes | Justificativa |
  |---|---|---|---|---|
  | `src/browser/semantic-projection.ts` | `normalizedText()` | 195-200 | `workstation/browser_projection.py` | Pure string utility: colapsa whitespace e trunca para 600 chars. Zero dependências externas. Útil para normalizar texto antes de serialização. |
  | `src/browser/semantic-projection.ts` | `cleanProjectionText()` | 303-310 | `workstation/browser_projection.py` | Strip private-use Unicode + zero-width chars + truncation. Previne caracteres invisíveis consumindo tokens. |
  | `src/browser/semantic-projection.ts` | `projectionRef()` | 207-209 | `workstation/browser_projection.py` | Geração de ref opaco `r{backendNodeId.toString(36)}`. Simples, determinístico, compatível com esquema de refs existente. |
  | `src/core/run-agent.ts` | `truncateFeedbackText()` | 115-119 | `workstation/browser_readiness.py` ou agent verifier | Truncamento genérico com ellipsis para feedback de erro. Reutilizável em qualquer superfície de diagnóstico. |
  | `src/core/run-agent.ts` | `sumTokenUsage()` | 142-161 | Novo módulo `workstation/token_tracking.py` | Agregação pura de usage counters. Necessário para implementar telemetria de tokens que ARCHITECTURE.md menciona mas não implementa. |
  | `src/agents/prompts.ts` | `PROJECTION_FORMAT_DESCRIPTION` | 26-30 | System prompt constants do agente browser | Descrição canônica do formato de projeção semântica. Essencial se Hermes adotar projeção AX-style. |
  | `src/agents/prompts.ts` | `PROJECTION_REF_NOTE` | 24 | System prompt constants do agente browser | Regra de validade de refs: "never invent or reuse stale refs". Direto para system prompt. |
  | `src/agents/prompts.ts` | `MAX_STEP_FINALIZATION_INSTRUCTION` | 10-22 | Agent loop finalization logic | Instrução de finalização forçada quando budget esgota. Padrão de graceful degradation copiável. |
  
  ## 4. Código Adaptável
  
  | Conceito/Padrão | Como Adaptar para Hermes | Benefício Esperado |
  |---|---|---|
  | **Projeção Semântica via AX Tree** | Implementar `getFullAXTree()` via CDP no controller Electron existente; criar pipeline Python que classifica nodes por role (INTERACTIVE/STRUCTURAL/TEXT/OMITTED), gera refs opacos, merge texto adjacente, trunca campos. Integrar como pré-processador antes de `browser_snapshot` retornar ao modelo. | Redução de 50-80% de tokens em páginas complexas; modelo recebe apenas elementos acionáveis/estruturais, não DOM bruto. |
  | **Projection Delta Mode** | Após primeira projeção completa, computar unified diff textual entre projeções consecutivas; enviar só delta quando página não mudou estruturalmente. Armazenar última projeção em memória por task_id. | Economia massiva em tarefas multi-step na mesma página (formulários, dashboards). |
  | **Stagnation Detection Dual-Streak** | Adicionar contadores em `BrowserRuntimeSupervisor.execute_with_supervision()`: (1) hash da última ação + args, (2) hash da última projeção/snapshot. Se ambos repetirem N vezes, emitir warning estruturado e forçar replan ou escalonamento. | Previne loops infinitos de ações válidas mas improdutivas; economiza tokens e tempo. |
  | **Completion Verifier com Checklist** | Criar estágio pós-execução no agent loop que faz LLM call separada com checklist cumulativo (IDs C-number); rejeição gera feedback estruturado com razões específicas e opcionalmente regenera checklist. | Reduz falsos positivos de completude; alinhado com HW-022 verified execution admission. |
  | **Session Snapshot/Rollback** | Antes de cada browser action, serializar estado relevante (checklist, projection cache, memory refs, lease generation) em dataclass congelada; on failure, restaurar snapshot antes de retry. Adaptar padrão TypeScript para Python dataclasses + copy.deepcopy. | Recovery transacional sem estado corrompido; compatível com fence token existente. |
  | **Large Document Short-Circuit** | Em `browser_snapshot` ou nova função `browser_perceive`, checar content-type e tamanho do body antes de fetch AX; se text/plain >250K chars, retornar preview 600 chars + metadata. | Evita projetar logs/dumps gigantes; economia imediata de tokens. |
  | **Prompt Block Composition** | Criar sistema de templates modulares para system prompt do browser agent (role/payloadFormat/projectionFormat/responseFormat/actions); selecionar blocos por task type/provider. | Flexibilidade de prompt variants sem duplicação; facilita A/B testing de instruções. |
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | Projeção semântica AX (filtrar non-actionable/non-structural) | 50-80% | Alto | `semantic-projection.ts` lines 29-100 (role sets), 587-602 (shouldRenderNode) |
  | Projection delta mode (enviar diffs, não full trees) | 50-80% em páginas estáveis | Médio | `prompts.ts` lines 183-198 (cumulative mode description) |
  | Large plain-text document short-circuit (>250K → 600 char preview) | 90%+ em páginas de log/data | Baixo | `semantic-projection.ts` lines 102-103, 224-290 |
  | Text node merging/deduplication | 10-30% | Baixo | `semantic-projection.ts` lines 348, 405-420 |
  | Href omission/truncation (500 char default, omit when not needed) | 5-20% variável | Baixo | `semantic-projection.ts` lines 649-654 |
  | State property filtering (só truthy values) | 5-15% | Baixo | `semantic-projection.ts` lines 639-648 |
  | OpenAI/Anthropic prompt caching de prefixo estável | 30-70% em steps subsequentes | Médio | `run-agent.ts` lines 733-747, `openai-prompt-cache.ts` |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | Skip inter-step delay para ações seguras (read-only, non-destructive) | -100 a -500ms por step | Baixo | `run-agent.ts` lines 1280-1288 (`canSkipExecutorStepDelay`) |
  | Async extraction com barrier pattern (extract_data roda async; memory_read/return_results atuam como barreiras) | Não-bloqueante; throughput ↑ | Médio | `prompts.ts` lines 347-349, 356-365 |
  | Lazy large-document detection antes de AX fetch | Evita fetch desnecessário em páginas gigantes | Baixo | `semantic-projection.ts` lines 663-669 |
  | Single-pass AX tree fetch (já ótimo na ref; Hermes deve garantir equivalente) | Baseline | N/A | `semantic-projection.ts` line 670 |
  | Readiness polling com intervalo adaptativo (começar 0.1s, aumentar até 1s) | -30% latency em páginas rápidas | Baixo | `browser_readiness.py` line 93 (poll_interval fixo 0.3s) |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | Completion verifier com retry estruturado | ALTO: catch hallucinated/incomplete results | Alto | `run-agent.ts` lines 79-140, 1187-1232 |
  | Checklist-driven progress tracking (C-number IDs, TODO/DONE/REGRESSED) | ALTO: structured completion criteria | Médio | `prompts.ts` lines 40-50, `run-agent.ts` lines 492-531 |
  | Ref validity enforcement em system prompt ("never invent stale refs") | ALTO: previne ações em elementos inexistentes | Baixo | `prompts.ts` line 24 |
  | Result grounding rule ("return_results must be grounded in extract_data/memoryContent") | ALTO: previne fabricação de dados | Baixo | `prompts.ts` lines 307, 356-357 |
  | Model action contract validation (reject malformed YAML/action shapes) | ALTO: fail-fast em outputs inválidos | Médio | `run-agent.ts` lines 1336-1343 |
  | Interaction error feedback in payload (erros anteriores como contexto) | MÉDIO: enables self-correction | Baixo | `prompts.ts` line 256 |
  | Max-step finalization instruction (force synthesis from existing evidence) | MÉDIO: graceful degradation | Baixo | `prompts.ts` lines 10-22 |
  
  ## 8. Resumo Executivo
  
  ### Top 5 Recomendações Priorizadas
  
  1. **Implementar Projeção Semântica AX como Camada de Percepção Primária** (Impacto: CRÍTICO, Esforço: Alto)
     - Justificativa: É o gap mais significativo. Hermes atualmente projeta resultados duráveis mas não tem pipeline de percepção compacta para o modelo. A referência demonstra que filtragem por role + refs opacos + merge de texto reduz 50-80% de tokens mantendo acionabilidade. Implementar via CDP no controller Electron existente, como pré-processador de `browser_snapshot`. Alinhado com invariante de prompt caching (projeção estável = cache hit).
  
  2. **Adicionar Stagnation Detection Dual-Streak ao Supervisor** (Impacto: ALTO, Esforço: Baixo)
     - Justificativa: `BrowserRuntimeSupervisor` já tem infrastructure de retry/circuit breaker. Adicionar contadores de ação repetida e progresso ausente é incremento mínimo (~50 linhas) que previne loops infinitos custosos. Evidência: referência usa isso para emitir warnings e forçar replan; Hermes não tem equivalente.
  
  3. **Implementar Projection Delta Mode** (Impacto: ALTO, Esforço: Médio)
     - Justificativa: Tarefas browser típicas envolvem múltiplos steps na mesma página. Enviar full projection a cada step é desperdício. Delta mode (unified diff após reset inicial) reduz 50-80% em cenários estáveis. Requer armazenar última projeção por task_id e diff algorithm simples.
  
  4. **Adotar Completion Verifier com Checklist Cumulativo** (Impacto: ALTO, Esforço: Alto)
     - Justificativa: HW-022 já exige verified execution admission. Verifier separado com checklist C-number e feedback estruturado fecha o gap entre "extração validada" (atual) e "tarefa semanticamente completa" (referência). Reduz falsos positivos e fornece sinal objetivo para continuation handoff.
  
  5. **Copiar Utilitários de Normalização de Texto e Refs** (Impacto: MÉDIO, Esforço: Baixo)
     - Justificativa: `normalizedText()`, `cleanProjectionText()`, `projectionRef()` são funções puras, zero-dependency, imediatamente portáveis. Previnem caracteres invisíveis, whitespace excessivo e refs não-determinísticos. Base necessária antes de implementar projeção AX completa.
  
  ### Nota sobre Limitações da Análise
  Os arquivos `src/core/run-agent.ts`, `src/browser/semantic-projection.ts` e `src/agents/prompts.ts` da referência foram lidos parcialmente (até ~150-200 linhas cada). Os arquivos `tools/browser_workstation.py` do Hermes foi lido até linha 200. Recomenda-se leitura completa destes arquivos para refinamento das recomendações acima, especialmente para implementação de projeção AX e verifier.
</agent-message>

---

<!-- Relatório 22 -->

# Relatório Comparativo: Browser Hermes Workstation vs xcursos-runner (Referência)
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (xcursos-runner) | Hermes Work | Gap Específico |
  |---|---|---|---|
  | Navegação estruturada | `NavigationPlanner` com 5 estratégias comprováveis (ALREADY_AT_TARGET, EXACT_URL, WALK_FROM_CURRENT, WALK_FROM_CHECKPOINT, WALK_FROM_COURSE_ANCHOR), escolhe rota de menor custo em passos (`navigation-planner.mjs:4-22`) | Navegação por URL direta via `_dispatch("browser_navigate")`; sem planner de rotas, sem checkpoints, sem âncoras de curso (`tools/browser_workstation.py:830-941`) | Hermes não tem capacidade de planejar navegação multi-passo com fallbacks estruturados; depende de URL exata ou retry cego |
  | Localização adaptativa de elementos | `AdaptiveLocator` com scoring heurístico (texto normalizado NFD, role, tag, visibilidade, ambiguidade delta) e threshold configurável (`adaptive-locator.mjs:1-18`) | Sem locator adaptativo; snapshot retorna inventário plano de refs (`@eN`) e modelo decide qual clicar baseado apenas em texto/role (`browser_workstation.py:944-1029`) | Hermes delega seleção de elemento inteiramente ao LLM; sem scoring determinístico pré-filtro que reduza candidatos antes do modelo |
  | Verificação de actionability | `ActionabilityProbe` com amostragem multi-frame de bounding box, detecção de animações/transições geométricas, trial click, e neutralização de motion (`actionability-probe.mjs:16-97`) | `browser_readiness.py` verifica apenas selector/texto/min_text_length via polling JS; sem verificação de estabilidade geométrica, animações, ou trial click (`browser_readiness.py:19-81`) | Hermes pode tentar clicar em elementos em movimento/invisíveis/desabilitados sem probe prévio; readiness é puramente textual/DOM, não visual/geométrico |
  | Observação de mídia de rede | `NetworkMediaObserver` com gerações lesson-scoped, correlação por objeto (hostname+pathname), fingerprint SHA-256, scoring por tipo/status/resourceType (`network-media-observer.mjs:1-79`) | Sem observador de mídia de rede; extração de conteúdo via `browser_bridge.py` avalia expressão JS e salva JSON, mas não intercepta tráfego de rede (`browser_bridge.py:43-90`) | Hermes não captura URLs de vídeo/mídia via network layer; depende de parsing DOM ou avaliação JS ad-hoc |
  | Leitura segura de conteúdo | `safePageContent` com retry estruturado, classificação de erros transientes (context destroyed, frame detached), validação de HTML mínimo (`safe-page-content.mjs:1-26`) | `browser_bridge.browser_save_json` avalia expressão JS única sem retry, sem classificação de erro transiente, sem validação de conteúdo (`browser_bridge.py:43-90`) | Hermes falha em leituras de página durante transições de navegação sem mecanismo de retry inteligente |
  | Persistência de índice de navegação | `NavigationIndex` V2 com `safePersistUrl` (remove signed queries/tokens), migração automática V1→V2, remoção de entradas stale após divergência observada (`ARCHITECTURE.md:22-24`) | Sem índice de navegação persistente; `read_native_browser_session_state` lê estado do Electron mas não mantém histórico de posições/URLs observadas (`browser_workstation.py:230-322`) | Hermes não aprende com execuções anteriores; cada sessão recomeça sem memória de rotas válidas |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (xcursos-runner) | Vantagem Específica |
  |---|---|---|---|
  | Supervisão de runtime | `BrowserRuntimeSupervisor` com circuit breaker (CLOSED/OPEN/HALF_OPEN), backoff exponencial, classificação tipada de erros (DESCRIPTOR_STALE, PROCESS_DEAD, AUTH_MISMATCH, etc.), limpeza automática de descriptor stale (`browser_supervisor.py:63-302`) | Sem supervisor de processo; `PlaywrightBrowser` é facade sobre CDP sem health check, circuit breaker ou recuperação (`playwright-browser.mjs:1-13`) | Hermes detecta e recupera de falhas de processo/controlador automaticamente; referência falha silenciosamente |
  | Segurança de binding | Task binding com fail-closed: tarefa vinculada nunca faz fallback silencioso para outro browser; lease manager com fence_token; operation_id lineage (`browser_workstation.py:1035-1101`, `ARCHITECTURE.md:358-367`) | Sem task binding, sem lease, sem fence token; runner opera em modo fire-and-forget sobre Playwright | Hermes garante isolamento de autenticação/estado entre tarefas; referência pode vazar contexto entre sessões |
  | Bridge segura para filesystem | `_validate_safe_destination` com `Path.is_relative_to` contra path traversal, `BridgeSecurityError` tipado, escrita atômica (`browser_bridge.py:25-40`) | Sem validação de destino; `safePageContent` retorna string HTML sem persistência controlada | Hermes previne escrita fora de workspaces permitidos; referência não tem boundary de segurança filesystem |
  | Readiness semântica contratual | `BrowserReadinessContract` com avaliação estruturada (auth_required, captcha_required, dom_drift, hydration_timeout, unsupported_surface), diagnóstico classificado (`browser_readiness.py:131-173`) | Sem contrato de readiness; ação procede após `page.waitForLoadState` genérico do Playwright | Hermes distingue falhas de auth, CAPTCHA, drift DOM e hidratação como códigos distintos; referência trata tudo como timeout |
  | Redação forçada de resultados | `_force_redact` + `strip_private_browser_telemetry` aplicados a todo resultado antes de cruzar boundary do tool; tokens/cookies/secrets nunca chegam ao modelo (`browser_workstation.py:927`, `ARCHITECTURE.md:407-412`) | `redactUrl` remove signed queries de URLs persistidas (`network-media-observer.mjs:78`), mas resultados de avaliação JS podem vazar dados sensíveis ao caller | Hermes tem redação obrigatória em camada de despacho; referência tem redação pontual |
  | Projeção de payload para modelo | `project_model_browser_payload` elimina duplicação elements/snapshot quando inventário textual já carrega a mesma informação, reduzindo tokens sem perda (`browser_workstation.py:966-1029`) | Sem projeção; runner consome HTML bruto ou snapshot completo | Hermes reduz consumo de tokens em snapshots grandes automaticamente |
  | Arquitetura multi-runtime | `BrowserRuntime` abstrato com routing configurável (electron-chromium, agent-browser, browser-exec, lightpanda); fail-closed quando routing desabilitado (`ARCHITECTURE.md:269-277`) | Hardcoded para Playwright/CDP; sem abstração de runtime | Hermes suporta troca de backend sem mudança de API; referência é monolítica |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 NavigationPlanner (copia integral)
  **Origem:** `referências/02-Browser-Automacao-Web/xcursos-runner/src/navigation-planner.mjs` (linhas 1-22)
  **Destino sugerido:** `workstation/navigation_planner.py` (novo arquivo)
  **Adaptação necessária:** Traduzir de JS para Python; a lógica é pura e sem dependências externas. A classe `NavigationPlanner.plan()` é autocontida e pode ser usada diretamente pelo browser controller para planejar rotas antes de despachar `browser_navigate`.
  
  ```python
  # Exemplo de tradução direta da função pos() e usable():
  def _pos(value):
      try:
          n = int(value)
          return n if n >= 1 else None
      except (TypeError, ValueError):
          return None
  
  def _usable(ref, target):
      p = _pos(ref.get("position") if isinstance(ref, dict) else None)
      return bool(p and p < target and ref.get("url"))
  ```
  
  ### 3.2 AdaptiveLocator scoring function (copia integral)
  **Origem:** `referências/02-Browser-Automacao-Web/xcursos-runner/src/adaptive-locator.mjs` (linhas 1-9, função `scoreNextCandidate`)
  **Destino sugerido:** `workstation/element_scoring.py` (novo arquivo) ou integrar em `browser_readiness.py`
  **Nota:** A função `scoreNextCandidate` é pura, sem dependências. Pode ser chamada no lado Python após receber candidatos do snapshot JS, filtrando antes de enviar ao modelo.
  
  ```python
  import unicodedata, re
  
  def _norm(s: str) -> str:
      return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower().strip()
  
  def score_next_candidate(c: dict) -> float:
      text = _norm(' '.join(filter(None, [c.get('text'), c.get('ariaLabel'), c.get('title')])))
      role = _norm(c.get('role', ''))
      tag = _norm(c.get('tag', ''))
      score = 0.0
      if text == 'proxima': score += 0.82
      elif text.startswith('proxima aula') or text == 'proxima aula': score += 0.78
      elif 'proxima' in text: score += 0.62
      if role in ('button', 'link'): score += 0.12
      if tag in ('button', 'a'): score += 0.08
      if c.get('visible') is False: score -= 1.0
      if re.search(r'anterior|voltar|material|download', text): score -= 0.7
      return max(0.0, min(1.0, score))
  ```
  
  ### 3.3 ActionabilityProbe.shouldNeutralize (lógica copiável)
  **Origem:** `referências/02-Browser-Automacao-Web/xcursos-runner/src/actionability-probe.mjs` (linhas 68-74)
  **Destino sugerido:** Integrar em `workstation/browser_readiness.py` como método de `BrowserReadinessContract`
  **Benefício:** Determinar se um elemento precisa de neutralização de animação antes de interação, evitando cliques falhos.
  
  ## 4. Código Adaptável
  
  ### 4.1 NetworkMediaObserver → BrowserNetworkInterceptor
  **Conceito:** Interceptação de respostas de rede com classificação de tipo de mídia (MP4/HLS/DASH), gerações scoping por lição/tarefa, e correlação por objeto (hostname+pathname ignorando query params).
  **Como adaptar:** Implementar como listener no controller Electron (CDP `Network.responseReceived` + `Network.loadingFinished`). O Hermes já tem acesso CDP via loopback; adicionar handler de eventos de rede no `/v1/action` ou endpoint dedicado. Armazenar eventos em memória bounded (maxEvents=80 como na referência) e expor via `browser_get_media` tool.
  **Benefício esperado:** Captura confiável de URLs de vídeo/mídia sem depender de parsing DOM frágil; habilita download direto de streams identificados por fingerprint.
  
  ### 4.2 SafePageContent retry pattern → browser_bridge retry wrapper
  **Conceito:** Retry com classificação de erros transientes (execution context destroyed, frame detached, navigation), backoff linear, validação de conteúdo mínimo (presença de `<html>`/`<body>`).
  **Como adaptar:** Envolver `evaluate_fn` em `browser_bridge.browser_save_json` com loop de retry similar. Classificar exceções do controller (TIMEOUT, PAGE_CLOSED) como transientes vs permanentes. Adicionar validação pós-avaliação.
  **Benefício esperado:** Redução de falhas espúrias em leituras de página durante transições de navegação; hoje o Hermes falha imediatamente sem retry.
  
  ### 4.3 Navigation Index persistence → Workstation Navigation Memory
  **Conceito:** Índice persistente de posições/URLs observadas com sanitização de credenciais, migração de versão, e invalidação automática de entradas stale.
  **Como adaptar:** Criar `workstation/navigation_index.py` usando o ArtifactStore existente como backend de persistência. Chavear por (task_family, position) e validar contra observação real na próxima execução. Sanitizar URLs com `url_safety.normalize_url_for_request` já existente.
  **Benefício esperado:** Aceleração de re-execuções em sites estruturados (cursos, dashboards paginados); redução de navegação exploratória desnecessária.
  
  ### 4.4 ActionabilityProbe multi-frame stability → Readiness geométrica
  **Conceito:** Amostragem de bounding box em múltiplos frames (requestAnimationFrame), detecção de animações CSS/Web Animations API, trial click com timeout curto.
  **Como adaptar:** Adicionar expressão JS em `build_readiness_expression` que sampleia getBoundingClientRect em N frames e reporta `stable: bool`. Integrar com `wait_for_condition` como critério adicional. Trial click pode ser exposto como opção em `browser_click`.
  **Benefício esperado:** Eliminação de cliques em elementos em transição/animação; redução de erros ACTION_FAILED por timing.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | Pré-filtragem de elementos via scoring adaptativo antes de enviar ao modelo | 15-25% em páginas com muitos elementos interativos | Médio | `adaptive-locator.mjs:10-18` vs `browser_workstation.py:944-1029` |
  | Navigation Planner evita snapshots exploratórios repetidos | 20-30% em fluxos multi-página estruturados | Médio | `navigation-planner.mjs:4-22` — planejamento substitui tentativa-e-erro |
  | NetworkMediaObserver elimina avaliação JS ad-hoc para encontrar URLs de mídia | 10-15% em tarefas de extração de vídeo | Alto | `network-media-observer.mjs:47-79` vs ausência equivalente no Hermes |
  | SafePageContent retry evita re-snapshot completo após falha transiente | 5-10% em navegações com transições pesadas | Baixo | `safe-page-content.mjs:7-26` — retry local vs re-dispatch completo |
  | Projection de elements já implementada (mantém vantagem) | Já ativo (~10-20% em snapshots grandes) | Nenhum | `browser_workstation.py:966-1029` |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | NavigationPlanner reduz número de cliques/navegações intermediárias | 30-50% menos passos em fluxos estruturados | Médio | `navigation-planner.mjs:11-19` — escolhe menor caminho |
  | ActionabilityProbe trial click (1.5s timeout) falha rápido em vez de esperar timeout longo | 2-5s economizados por clique falho | Médio | `actionability-probe.mjs:58-63` |
  | NetworkMediaObserver captura URL de mídia passivamente durante navegação | Elimina 1-3s de avaliação JS pós-navegação | Alto | `network-media-observer.mjs:53-59` |
  | SafePageContent retry com delay progressivo (150ms×attempt) vs timeout fixo | 0.5-2s em páginas com transições | Baixo | `safe-page-content.mjs:21` |
  | Circuit breaker do Supervisor já evita retries inúteis (mantém vantagem) | Já ativo | Nenhum | `browser_supervisor.py:249-258` |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | Scoring determinístico de candidatos reduz alucinação de seleção de elemento | Alta: modelo recebe candidatos pré-ranqueados com scores, não lista plana | Médio | `adaptive-locator.mjs:2-9` — score é função pura testável |
  | NavigationPlanner retorna estratégia escolhida + steps + alternativas consideradas | Alta: auditoria determinística de decisão de navegação | Médio | `navigation-planner.mjs:19-20` — strategiesConsidered explícito |
  | ActionabilityProbe fornece evidência geométrica (bounding boxes, animations, centerElement) | Alta: decisão de clicar baseada em dados mensuráveis, não intuição do modelo | Médio | `actionability-probe.mjs:26-46` |
  | BrowserReadinessContract codes (AUTH_REQUIRED, DOM_DRIFT, CAPTCHA_REQUIRED) já existem | Já ativo: diagnóstico classificado vs "not ready" genérico | Nenhum | `browser_readiness.py:163-173` |
  | NetworkMediaObserver fingerprinting permite verificação objetiva de identidade de mídia | Alta: correlação por hash SHA-256 em vez de comparação textual de URL | Alto | `network-media-observer.mjs:26-38` |
  
  ## 8. Resumo Executivo
  
  ### Recomendações Priorizadas
  
  **1. Implementar NavigationPlanner em Python (Impacto Alto / Esforço Médio)**
  Justificativa: O maior gap identificado é a ausência de planejamento de navegação estruturado. O `NavigationPlanner` da referência é uma classe pura de ~20 linhas que elimina navegação exploratória custosa. Traduzir para Python e integrar no dispatch de `browser_navigate` reduziria tokens e tempo em fluxos multi-página em 20-30%. Não requer mudanças no Electron/controller.
  
  **2. Adicionar Element Scoring pré-modelo (Impacto Alto / Esforço Médio)**
  Justificativa: O `scoreNextCandidate` é uma função pura de 8 linhas que pré-filtra elementos interativos antes do modelo decidir. Hoje o Hermes envia inventário plano e delega toda a seleção ao LLM. Integrar scoring como camada de projeção em `project_model_browser_payload` reduziria tokens em 15-25% e melhoraria objetividade sem alterar a API do browser.
  
  **3. Implementar SafePageContent retry em browser_bridge (Impacto Médio / Esforço Baixo)**
  Justificativa: O padrão de retry com classificação de erros transientes da referência é simples (~25 linhas) e resolve falhas espúrias que hoje causam re-dispatch completo. Pode ser adicionado como wrapper em `browser_save_json` sem mudança de arquitetura. ROI imediato em estabilidade.
  
  **4. Adicionar ActionabilityProbe geométrica ao Readiness (Impacto Médio / Esforço Médio)**
  Justificativa: A verificação de estabilidade de bounding box e detecção de animações previne cliques em elementos em transição. O Hermes já tem `wait_for_condition` com polling JS; estender a expressão para incluir amostragem multi-frame e trial click é incremental. Benefício direto em confiabilidade de interações.
  
  **5. Implementar NetworkMediaObserver via CDP (Impacto Alto / Esforço Alto)**
  Justificativa: A captura passiva de URLs de mídia via network layer é o recurso mais poderoso da referência para tarefas de extração de conteúdo. Requer integração com CDP no controller Electron, mas eliminaria completamente a necessidade de parsing DOM para encontrar vídeos. Priorizar após os itens 1-3 que são puramente Python-side.
</agent-message>

---

<!-- Relatório 23 -->

# Relatório Comparativo: BrowserOS vs Hermes Workstation Browser
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (BrowserOS) | Hermes Work | Gap Específico |
  |---|---|---|---|
  | Snapshot Diffing | LCS line-level diff nativo em Rust (`snapshot/diff.rs`), com context collapsing e detecção de mudança de URL; retorna apenas linhas alteradas + contadores | Sem diff estruturado entre snapshots; cada snapshot é independente, o modelo recebe o texto completo repetidamente (`browser_tool_snapshot.py`) | Ausência de diff incremental força reenvio de snapshots completos, gastando tokens desnecessariamente em páginas que mudaram pouco |
  | Stable Ref System | RefMap com identidade estável `(document_id, frame_id, backend_node_id)` sobrevivendo a mutações DOM dentro do mesmo documento; stale ref recovery por role+name+nth (`refs.rs`, `observer.rs:463-490`) | Refs são efêmeros por snapshot; não há mecanismo de estabilidade cross-snapshot nem recuperação de refs obsoletos | Modelo perde referência a elementos entre ações consecutivas, exigindo re-snapshot e re-localização |
  | Cursor Augmentation | Scan DOM-wide (`cursor-augment.js`) detecta elementos clicáveis sem ARIA (div onclick, cursor:pointer) e os marca como `[ref=eN] [cursor=pointer]` na árvore de acessibilidade | Sem augmentação de cursor; elementos interativos não-semânticos são invisíveis ao modelo na accessibility tree | Elementos `<div onclick>` comuns em SPAs modernas são perdidos pelo modelo, causando falhas de interação |
  | Post-Action Settle Detection | MutationObserver counter pattern (`settle.rs`): instala observer, polla contador, considera settled quando estável por um intervalo; budget de 50ms default | Polling genérico com `time.sleep(poll_interval)` e condições booleanas (`browser_readiness.py:84-127`); sem detecção de quiescência DOM baseada em mutação real | Esperas arbitrárias ou insuficientes; readiness baseado em texto/seletor não captura animações/renderizações assíncronas |
  | Parallel Frame Acquisition | `tokio::join!` para AX tree + cursor scan + document validation concorrentes; iframes filhos via `FuturesUnordered` com semaphore de 8 permits (`acquisition.rs:260-331`) | Captura sequencial; sem paralelismo explícito de frames/iframes no snapshot pipeline | Snapshots de páginas com múltiplos iframes são significativamente mais lentos |
  | Token-Aware Output | Estimação real de tokens (`bytes/3`); spill-to-file automático acima de 15k tokens com excerpt inline de 5k tokens (`token_estimate.rs`, `format/snapshot.rs`) | Truncamento por caracteres (`MAX_STORED_SNAPSHOT_CHARS`) sem estimação de tokens; modelo não sabe quantos tokens o snapshot consome | Truncamento cego pode cortar no meio de elementos ou deixar snapshots enormes consumindo contexto desproporcionalmente |
  | Interactive Snapshot Mode | Modo `Interactive` filtra linhas mantendo apenas refs, headings e ancestrais (`filter_interactive_lines` em `render.rs:178-215`); compartilha RefMap com modo Full | Sem modo interativo; único formato de snapshot disponível | Modelo recebe árvores completas incluindo nós decorativos/estruturais irrelevantes para ações |
  | Content Markdown Extraction | `content_markdown.rs` + `content-markdown.js`: walker DOM dedicado que extrai conteúdo como markdown estruturado com opções (selector, viewport_only, links, images) | Extração via `browser_save_json` com expressão JS ad-hoc (`browser_bridge.py:36-82`); sem walker especializado | Extração de conteúdo textual requer expressões JS customizadas a cada uso, sem padronização |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (BrowserOS) | Vantagem Específica |
  |---|---|---|---|
  | Circuit Breaker & Supervisão Ativa | `BrowserRuntimeSupervisor` com circuit breaker (CLOSED/OPEN/HALF_OPEN), backoff exponencial, classificação de erros em 9 categorias, limpeza automática de descriptor stale (`browser_supervisor.py:57-302`) | Sem circuit breaker; erro de CDP propaga diretamente; sem classificação estruturada de falhas | Resiliência superior a falhas transitórias do controller; evita cascata de retries inúteis quando o processo está morto |
  | Binding de Tarefa & Fail-Closed | Task binding permanente após primeira ação bem-sucedida; perda de controller falha fechado, nunca migra silenciosamente para outro browser (`browser_workstation.py:1060-1101`) | Sem conceito de task binding; sessões são independentes | Garantia de que estado de autenticação/página não muda silenciosamente entre ações de uma mesma tarefa |
  | Projeção Durável de Resultados | `process_extracted_items_durably` projeta extrações em ArtifactStore + WorkPlan/WorkItems canônicos com validação semântica por item (`browser_projection.py:39-150`) | Sem projeção durável; resultados retornados inline ao agente | Dados extraídos sobrevivem a restarts, são auditáveis por WorkItem, e não ocupam contexto do modelo |
  | Redação Forçada em Boundary de Tool | `_redact_browser_output` aplica `redact_sensitive_text(force=True)` recursivamente em todo output de browser antes de cruzar boundary do tool (`browser_tool_snapshot.py:111-125`) | Wrap genérico `wrap_untrusted()` sinaliza conteúdo não-confiável mas não redige secrets ativamente | Proteção ativa contra vazamento de tokens/cookies/keys renderizados na página para o contexto do modelo |
  | Readiness Contract Semântico | `BrowserReadinessContract` com avaliação estruturada: auth_required, captcha_required, dom_drift, hydration_timeout, unsupported_surface + diagnóstico classificado (`browser_readiness.py:131-173`) | Settle binário (settled/budget_expired); sem classificação de causa raiz de não-readiness | Diagnóstico preciso permite ao modelo decidir entre esperar, autenticar, resolver CAPTCHA ou abortar |
  | Bridge de Segurança Validada | `_validate_safe_destination` valida que destinos de escrita estão dentro de roots permitidos antes de qualquer I/O (`browser_bridge.py:25-33`) | Sem validação de destino de arquivo equivalente | Prevenção de path traversal em operações de extração direta para filesystem |
  | Controle de Lease Humano | `BrowserControlLeaseManager` com fence_token, registro pai/filho de sub-tarefas, asserção de permissão antes de cada ação (`browser_workstation.py:1085-1092`) | Sem lease/human-in-the-loop no nível de automação | Gate de aprovação granular por tarefa; sub-agentes herdam escopo do pai |
  | Error Code Estruturado | `WorkstationBrowserError` com error_code, retryable, retry_after_ms, state_changed, recommended_action, resource_ref (`browser_workstation.py:52-106`) | Erros genéricos CoreError/McpError sem metadata estruturada de retry | Agente/orquestrador pode tomar decisões programáticas sobre retry vs escalate vs reconcile |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 Script de Cursor Augmentation (JavaScript)
  **Origem:** `referências/.../browseros-core/src/assets/cursor-augment.js`
  **Destino sugerido:** `workstation/assets/cursor_augment.js` (novo)
  **Uso:** Injetar via `evaluate_fn` antes de capturar accessibility tree para tornar elementos não-semânticos visíveis ao modelo. O script é ES5 auto-contido, sem dependências externas. Retorna array de `{backendNodeId, reason}` que pode ser mapeado para refs no snapshot.
  
  ### 3.2 Script de Settle Detection via MutationObserver (JavaScript)
  **Origem:** `referências/.../browseros-core/src/settle.rs` linhas 24-53 (constantes `INSTALL_OBSERVER_JS` e `READ_COUNTER_JS`)
  **Destino sugerido:** `workstation/browser_readiness.py` — adicionar como constantes de módulo e integrar em `wait_for_condition`
  **Uso:** Substituir polling arbitrário por detecção de quiescência DOM real. Instalar observer → pollar contador → considerar ready quando estável.
  
  ### 3.3 Algoritmo de Filter Interactive Lines
  **Origem:** `referências/.../browseros-core/src/snapshot/render.rs` linhas 178-215 (`filter_interactive_lines`)
  **Destino sugerido:** `tools/browser_tool_snapshot.py` — nova função `_filter_interactive_snapshot(text: str) -> str`
  **Uso:** Oferecer modo "interactive" no snapshot tool que mantém apenas linhas com refs, headings e seus ancestrais. Tradução direta de Rust para Python (~40 linhas).
  
  ### 3.4 Algoritmo de LCS Line Diff com Context Collapsing
  **Origem:** `referências/.../browseros-core/src/snapshot/diff.rs` linhas 31-160
  **Destino sugerido:** `tools/browser_tool_snapshot.py` — nova função `_diff_snapshots(before: str, after: str, context_radius: int = 3) -> dict`
  **Uso:** Retornar diff incremental ao invés de snapshot completo após ações. Tradução direta do algoritmo LCS + collapse (~120 linhas Python).
  
  ### 3.5 Content Markdown Walker Script
  **Origem:** `referências/.../browseros-core/src/assets/content-markdown.js` (incluído via `include_str!` em `content_markdown.rs`)
  **Destino sugerido:** `workstation/assets/content_markdown.js` (novo)
  **Uso:** Extração padronizada de conteúdo textual como markdown estruturado, substituindo expressões JS ad-hoc em `browser_bridge.py`.
  
  ## 4. Código Adaptável
  
  ### 4.1 Stable RefMap com Document Scoping
  **Conceito:** Identidade de elemento baseada em `(document_id, frame_id, backend_node_id)` com namespace reset em navegação e recuperação stale por `(role, name, nth)`.
  **Como adaptar:** Implementar classe `RefMap` em Python no módulo `tools/browser_tool_snapshot.py` ou novo `workstation/browser_refs.py`. Usar `loaderId` do CDP como document_id. Persistir mapping entre snapshots consecutivos na sessão. Quando `DOM.resolveNode` falhar, buscar por role+name+nth na nova AX tree.
  **Benefício esperado:** Elimina re-localização de elementos entre ações; reduz snapshots redundantes em ~30-50% em fluxos multi-ação.
  
  ### 4.2 Parallel Frame Acquisition com Semaphore
  **Conceito:** Captura concorrente de AX tree + cursor scan + document validation por frame, com limite global de requests CDP.
  **Como adaptar:** Usar `asyncio.gather` + `asyncio.Semaphore(8)` no pipeline de snapshot do Hermes. Cada iframe filho é uma coroutine independente. Re-ordenar resultados por índice de stitch antes de montar texto final.
  **Benefício esperado:** Redução de 40-60% no tempo de snapshot para páginas com 3+ iframes.
  
  ### 4.3 Token Estimation Real (bytes/3)
  **Conceito:** Estimar tokens como `len(utf8_bytes) // 3` ao invés de contar caracteres; truncar em boundary UTF-8 seguro.
  **Como adaptar:** Adicionar função `estimate_tokens(text: str) -> int` em `browser_tool_snapshot.py`. Usar para decisão de spill-to-file e truncamento ao invés de `MAX_STORED_SNAPSHOT_CHARS` fixo.
  **Benefício esperado:** Decisões de truncamento alinhadas com custo real de contexto; evita over/under-truncation em textos multibyte.
  
  ### 4.4 Post-Action Diff Readback Automático
  **Conceito:** Após cada ação (click, fill, navigate), retornar automaticamente o diff do snapshot ao invés de exigir snapshot separado.
  **Como adaptar:** No handler de `browser_act` (ou equivalente), manter baseline do último snapshot, executar ação, capturar novo snapshot, computar diff, retornar diff como resultado da ação. Parâmetro `diff_mode: full|summary|none`.
  **Benefício esperado:** Elimina ciclo snapshot→act→snapshot; reduz round-trips em 50% para fluxos de verificação pós-ação.
  
  ### 4.5 Snapshot Budget Semaphore
  **Conceito:** Limite global de requests CDP concorrentes durante captura para evitar sobrecarga do browser.
  **Como adaptar:** `asyncio.Semaphore(8)` compartilhado entre todas as coroutines de aquisição de frame. Release imediato após resposta CDP, antes de processamento.
  **Benefício esperado:** Previne timeout de CDP em páginas complexas; melhora confiabilidade de captura.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | Diff incremental pós-ação ao invés de snapshot completo | 30-50% | Médio | BrowserOS `diff.rs`; Hermes carece de diff |
  | Modo Interactive (apenas refs + headings + ancestrais) | 40-60% | Baixo | BrowserOS `render.rs:178-215`; cópia direta |
  | Token-aware truncation (bytes/3) ao invés de char-count | 10-20% | Baixo | BrowserOS `token_estimate.rs`; Hermes usa chars |
  | Pruning de nós generic/group sem nome | 15-25% | Baixo | BrowserOS `render.rs:168-176`; lógica ausente no Hermes |
  | Spill-to-file com excerpt inline para snapshots >15k tokens | 20-40% em sessões longas | Médio | BrowserOS `format/snapshot.rs`; Hermes trunca cegamente |
  | Content Markdown extraction ao invés de raw DOM/text | 25-35% para extração de conteúdo | Médio | BrowserOS `content_markdown.rs`; Hermes usa eval ad-hoc |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | Parallel frame acquisition (AX + cursor + doc validation) | 40-60% redução em páginas com iframes | Alto | BrowserOS `acquisition.rs:260-331`; Hermes é sequencial |
  | MutationObserver settle ao invés de sleep polling | 30-50% redução em esperas pós-ação | Médio | BrowserOS `settle.rs:55-82`; Hermes usa `time.sleep` |
  | Stable refs eliminam re-snapshot para re-localização | 20-30% redução em round-trips | Médio | BrowserOS `refs.rs`; Hermes sem estabilidade |
  | CDP budget semaphore previne timeouts | Melhora confiabilidade, reduz retries | Médio | BrowserOS `acquisition.rs` SnapshotBudget |
  | Stale ref recovery evita full re-capture | 15-25% redução em re-capturas | Médio | BrowserOS `observer.rs:463-490` |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | Cursor augmentation torna elementos não-ARIA visíveis | Alta: elimina falsos negativos em divs onclick/cursor:pointer | Médio | BrowserOS `cursor-augment.js` |
  | Stable refs previnem alucinação de seletores | Alta: modelo usa ref estável ao invés de inventar CSS selectors | Médio | BrowserOS `refs.rs` |
  | Readiness classification (auth/captcha/drift/hydration) | Alta: modelo distingue causas de não-readiness ao invés de retry cego | Já presente no Hermes | `browser_readiness.py:131-173` |
  | Diff estruturado mostra exatamente o que mudou | Média: modelo vê delta preciso ao invés de comparar mentalmente dois snapshots grandes | Médio | BrowserOS `diff.rs` |
  | Trust boundary wrapping sinaliza conteúdo não-confiável | Média: previne injeção de instruções via conteúdo de página | Já presente no Hermes (redação forçada) | `browser_tool_snapshot.py:111-125` |
  | Document change retry previne snapshots de estado transitório | Alta: garante que snapshot reflete estado estável da página | Médio | BrowserOS `observer.rs` MAX_STABLE_CAPTURE_ATTEMPTS |
  
  ## 8. Resumo Executivo
  
  ### Recomendação 1: Implementar Snapshot Diff Incremental (Alto Impacto / Médio Esforço)
  Adicionar LCS line-level diff ao `browser_tool_snapshot.py` baseado no algoritmo de `diff.rs` do BrowserOS (~120 linhas Python). Retornar diff pós-ação automaticamente. **Justificativa:** É a maior fonte de economia de tokens (30-50%) e elimina o ciclo snapshot→act→snapshot. O algoritmo é puro, sem dependências externas, e traduzível diretamente.
  
  ### Recomendação 2: Adicionar Modo Interactive ao Snapshot (Alto Impacto / Baixo Esforço)
  Implementar `filter_interactive_lines` em `browser_tool_snapshot.py` (~40 linhas) como opção `mode="interactive"` no snapshot tool. **Justificativa:** Reduz 40-60% dos tokens em snapshots de páginas complexas mantendo todos os elementos acionáveis. Cópia quase literal do algoritmo Rust. Zero risco de regressão pois é opt-in.
  
  ### Recomendação 3: Integrar Cursor Augmentation (Alto Impacto / Médio Esforço)
  Portar `cursor-augment.js` para `workstation/assets/` e integrá-lo no pipeline de snapshot antes da captura da AX tree. **Justificativa:** Resolve gap crítico de elementos não-semânticos invisíveis ao modelo. SPAs modernas usam extensivamente `<div onclick>` e `cursor:pointer` sem ARIA roles. Sem isso, o modelo falha em interações básicas.
  
  ### Recomendação 4: Substituir Sleep Polling por MutationObserver Settle (Médio Impacto / Médio Esforço)
  Integrar os scripts `INSTALL_OBSERVER_JS` e `READ_COUNTER_JS` do `settle.rs` em `browser_readiness.py` como alternativa ao polling atual. **Justificativa:** Detecção de quiescência baseada em mutação real é mais precisa que texto/seletor/timeout fixo. Reduz tanto esperas excessivas quanto insuficientes. O padrão já é provado em produção no BrowserOS.
  
  ### Recomendação 5: Implementar Stable RefMap (Alto Impacto / Alto Esforço)
  Criar `workstation/browser_refs.py` com RefMap baseado em `(document_id, frame_id, backend_node_id)` e stale recovery. **Justificativa:** Fundamental para fluxos multi-ação confiáveis. Elimina re-localização de elementos e permite diffs significativos. Maior esforço de implementação mas maior retorno cumulativo em confiabilidade e economia de tokens.
</agent-message>

---

<!-- Relatório 24 -->

# Relatório Comparativo: Browser Nativo Hermes Workstation vs Playwright
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (Playwright) | Hermes Work | Gap Específico |
  | :--- | :--- | :--- | :--- |
  | **Espera e Sincronização** | `Waiter` (`waiter.ts`) usa `Promise.race` entre evento, timeout e abort signal; espera baseada em eventos reais do DOM/rede, nunca polling cego. | `browser_readiness.py` usa `time.sleep(poll_interval)` em loop while com JS injection a cada 300ms. | Polling introduz latência mínima de 300ms por verificação e desperdiça ciclos. Playwright reage instantaneamente via event listeners. |
  | **Snapshot / Acessibilidade** | `ariaSnapshotDistiller.ts` aplica pipeline de plugins (mergeStringChildren, removeNamelessImages, removeRedundantNames, unwrapSingleChildGenerics) que reduz árvore em ~60-80% sem perda informacional. Modo `ai` dedicado. | `workstation-browser-snapshot.ts` extrai nós AX interativos brutos via CDP + fallback DOM. Sem destilação pós-processamento; elementos redundantes e nomes repetidos chegam ao modelo. | Snapshot do Hermes é verboso e não otimizado para consumo por IA. Falta pipeline de destilação equivalente aos `aiPlugins` do Playwright. |
  | **Seletores e Locators** | `Locator` (`locator.ts`) suporta encadeamento (`has`, `hasNot`, `hasText`, `visible`), resolução lazy, auto-waiting integrado e múltiplos engines (CSS, text, role, testid). | Refs `@eN` estáveis por sessão via WeakMap. Sem suporte a filtros compostos, encadeamento ou resolução semântica além de ref numérica. | Modelo precisa conhecer ref exata; não pode expressar "botão com texto X dentro de div Y". Cada mudança de página exige novo snapshot completo. |
  | **Frame/Navegação** | `frames.ts` gerencia lifecycle completo: attach/detach, navigation events, signal barriers, cross-document tracking com documentId. | Navegação via HTTP POST `/v1/action`; estado de frame implícito no WebContentsView. Sem gestão explícita de subframes ou signal barriers. | Páginas com iframes ou SPAs complexas podem ter estado inconsistente entre navegação e snapshot. |
  | **Error Classification Granularity** | Erros tipados por domínio: `TimeoutError`, `AbortError`, `NavigationAbortedError`, `ExpectError` com detalhes estruturados. | `ControllerErrorKind` enum com 9 valores genéricos; classificação via string matching em `classify_error()`. | Classificação por substring é frágil; erros novos caem em UNKNOWN. Playwright tem hierarquia de tipos que carrega contexto automático. |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (Playwright) | Vantagem Específica |
  | :--- | :--- | :--- | :--- |
  | **Segurança e Binding** | Task binding permanente após primeira ação bem-sucedida (`_bind(key)` em `browser_workstation.py:932`). Fail-closed obrigatório: tarefa bound nunca migra silenciosamente para outro browser. | Sem conceito de task binding. Contextos são descartáveis; qualquer processo pode criar novo browser/context. | Garantia de que autenticação/estado da sessão não vaza entre tarefas. Invariante de segurança que Playwright não possui por design. |
  | **Human Control Lease** | `BrowserHumanControlLease` com TTL de 5 min (`HUMAN_CONTROL_LEASE_TTL_MS`). Agente bloqueado quando humano assume controle; erro `USER_CONTROL_ACTIVE` com `WAIT_FOR_RELEASE`. | Sem mecanismo nativo de handoff humano-agente. Concorrência por controle resulta em ações conflitantes. | Colaboração segura homem-máquina no mesmo browser sem race conditions. |
  | **Circuit Breaker e Supervisão** | `BrowserRuntimeSupervisor` (`browser_supervisor.py`) com circuit breaker (CLOSED/OPEN/HALF_OPEN), backoff exponencial, limpeza automática de descriptor stale e verificação de PID. | Retry logic delegada ao usuário/test runner. Sem supervisão ativa de processo ou circuit breaker built-in. | Resiliência operacional automática em cenários de desktop app onde browser pode crashar ou reiniciar. |
  | **Bridge Direto para ArtifactStore** | `browser_bridge.py` salva JSON/artifacts diretamente no filesystem ou ArtifactStore sem passar por base64/chat context. Validação de destino seguro. | Capturas passam pelo protocolo RPC como payloads serializados; consumidor decide onde persistir. | Zero overhead de serialização/deserialização para extrações estruturadas. Dados nunca transitam pelo contexto do modelo. |
  | **Telemetria e Journal Nativo** | `emit_native_browser_observation()` em cada ação com request/response bytes, duration_ms, error_code. Journal projection persistente via `_record_browser_controller_outcome`. | Trace viewer é opt-in e externo. Sem telemetria estruturada built-in por ação. | Observabilidade completa de cada operação browser sem configuração adicional. Base para Experience Compiler. |
  | **Redação Forçada** | `_force_redact()` e `strip_private_browser_telemetry()` aplicados antes de qualquer resultado cruzar a fronteira da tool. Senhas redigidas no JS (`[REDACTED]`). | Redação é responsabilidade do consumidor. Dados sensíveis podem vazar em logs/traces. | Segurança por default: modelo nunca vê tokens, senhas ou métricas privadas. |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 Pipeline de Destilação de Aria Snapshot
  - **Origem:** `referências/02-Browser-Automacao-Web/playwright-main/packages/injected/src/ariaSnapshotDistiller.ts` (linhas 45-263)
  - **Destino sugerido:** `apps/desktop/electron/workstation-browser-snapshot-distiller.ts` (novo arquivo)
  - **O que copiar:** A arquitetura de `DistillerPlugin` com hooks `enter`/`exit`, o contexto de travessia (`DistillerContext`), e os plugins `mergeStringChildren`, `removeNamelessImages`, `removeRedundantNames`, `inlineTextIntoGeneric`, `removeNameRepeatingChild`, `unwrapSingleChildGenerics`. O array `aiPlugins` (linha 256-263) é o preset pronto para consumo por IA.
  - **Nota:** Requer adaptação da interface `AriaNode` do Playwright para `AXInventoryElement` do Hermes, mas a lógica de travessia e mutação in-place é independente.
  
  ### 3.2 Waiter com Promise.race e AbortSignal
  - **Origem:** `referências/02-Browser-Automacao-Web/playwright-main/packages/playwright-core/src/client/waiter.ts` (linhas 27-141)
  - **Destino sugerido:** `workstation/browser_waiter.py` (novo módulo)
  - **O que copiar:** O padrão `Promise.race([promise, ...failures])` com dispose automático, log recording e formatação de logs em caso de falha. Adaptar para Python asyncio: `asyncio.wait([...], return_when=FIRST_COMPLETED)` com cleanup garantido.
  - **Benefício imediato:** Substitui o polling de `browser_readiness.py:wait_for_condition` por espera reativa.
  
  ### 3.3 Normalização de Whitespace e String Utils
  - **Origem:** `referências/02-Browser-Automacao-Web/playwright-main/packages/isomorphic/stringUtils.ts` (função `normalizeWhiteSpace`)
  - **Destino sugerido:** Inline em `workstation-browser-snapshot-distiller.ts` ou utilitário compartilhado
  - **O que copiar:** A função de normalização que colapsa espaços, remove leading/trailing whitespace e trata caracteres especiais. Usada pelo distiller para merge de text nodes.
  
  ## 4. Código Adaptável
  
  ### 4.1 Locator Composicional com Filtros
  - **Conceito:** `Locator` do Playwright (`locator.ts:40-78`) permite encadear filtros (`has`, `hasNot`, `hasText`, `visible`) que são serializados como seletores internos e resolvidos lazy.
  - **Como adaptar:** Estender o schema de `browser_click`/`browser_type` para aceitar filtro composicional em vez de apenas `ref`. Exemplo: `{role: "button", hasText: "Submit", visible: true}`. Resolver no lado Electron usando a AX tree já capturada + querySelectorAll como fallback.
  - **Benefício:** Modelo não precisa memorizar refs voláteis; expressa intenção semanticamente. Reduz necessidade de re-snapshot após cada navegação.
  
  ### 4.2 Signal Barriers para Navegação SPA
  - **Conceito:** `SignalBarrier` em `frames.ts:192-200` aguarda sinais pendentes (navigation, load) antes de considerar ação completa.
  - **Como adaptar:** Após `browser_navigate` ou `browser_click` que dispara navegação, aguardar evento `did-finish-load` ou `dom-ready` do WebContentsView antes de retornar sucesso. Integrar com `browser_readiness.py` como condição obrigatória pós-mutação.
  - **Benefício:** Elimina race condition onde snapshot captura estado intermediário de SPA.
  
  ### 4.3 Modo AI do Aria Snapshot
  - **Conceito:** `toInternalOptions` em `ariaSnapshot.ts:58-79` define modo `ai` com `visibility: 'ariaOrVisible'`, `refs: 'interactable'`, `renderCursorPointer: true`.
  - **Como adaptar:** Adicionar flag `mode: 'ai'` ao endpoint `/v1/action` para `browser_snapshot`. Quando ativo, aplicar distiller pipeline e retornar apenas elementos interativos com cursor pointer hint.
  - **Benefício:** Snapshot 60-80% menor para consumo por modelo, mantendo capacidade de ação.
  
  ### 4.4 Document Identity Token para Consistência
  - **Conceito:** `tryAccessibilitySnapshot` do Hermes já usa `documentToken` via `performance.timeOrigin` (linha 110-114, 225-228) para invalidar snapshot se documento mudou durante captura.
  - **Como adaptar:** Estender este padrão para TODAS as operações de leitura (extract_items, console, read_http). Se token mudou entre início e fim da operação, retornar `STALE_REF` automaticamente.
  - **Benefício:** Elimina dados inconsistentes de operações que atravessam transições de página.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Destilação de snapshot com aiPlugins | 60-80% redução | Médio | `ariaSnapshotDistiller.ts:256-263` vs `workstation-browser-snapshot.ts` sem destilação |
  | Projeção model-facing já elimina elements duplicados | 15-25% redução | Já implementado | `browser_workstation.py:966-1029` `project_model_browser_payload` |
  | Locator composicional evita re-snapshots | 30-50% redução em sessões longas | Alto | `locator.ts:40-78` vs refs `@eN` voláteis |
  | Text truncation adaptativo por contexto | 10-20% redução | Baixo | `COMPACT_TEXT_CHARS=8000` fixo em `workstation-browser-runtime.ts:101` |
  | Remoção de nomes redundantes no snapshot | 15-25% redução | Médio | `removeRedundantNames` plugin em `ariaSnapshotDistiller.ts:179-203` |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Substituir polling por event-driven waiting | -300ms a -2s por operação | Médio | `browser_readiness.py:104` `time.sleep(0.3)` vs `waiter.ts` Promise.race |
  | Batch CDP calls para AX tree resolution | -40-60% tempo de snapshot | Médio | `workstation-browser-snapshot.ts:136-201` resolve nós sequencialmente |
  | Cache de snapshot com invalidação por documentToken | -70-90% em reads consecutivos | Baixo | `lastSnapshotFrames` existe (`runtime.ts:1197`) mas não é usado para cache |
  | Object group release assíncrono | -5-10ms por snapshot | Baixo | `workstation-browser-snapshot.ts:204-208` já é async mas poderia ser fire-and-forget |
  | Signal barrier pós-navegação | Elimina retries por estado intermediário | Médio | `frames.ts:192-200` SignalBarrier pattern |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Distiller remove ruído decorativo (img sem nome, generics vazios) | Alta: modelo foca em elementos acionáveis | Médio | `removeNamelessImages`, `unwrapSingleChildGenerics` em `ariaSnapshotDistiller.ts` |
  | Cursor pointer hint identifica clicáveis não óbvios | Alta: reduz falsos negativos em ícones/SVGs | Baixo | `renderCursorPointer: true` em `ariaSnapshot.ts:68` |
  | Document token validation previne alucinação de estado | Alta: elimina dados de página errada | Já parcial | `workstation-browser-snapshot.ts:225-228` |
  | Wall detection estruturado com razão específica | Média: modelo sabe exatamente o que bloqueou | Já implementado | `formatInventory` wallDetected/wallReason em `runtime.ts:1119-1128` |
  | Readiness contract com entity_identity e semantic_targets | Alta: verificação determinística de página correta | Já implementado | `BrowserReadinessContract` em `browser_readiness.py:131-160` |
  
  ## 8. Resumo Executivo
  
  ### Recomendações Priorizadas
  
  1. **Implementar pipeline de destilação de snapshot (Impacto: ALTO, Esforço: MÉDIO)**
     Copiar a arquitetura de `DistillerPlugin` do `ariaSnapshotDistiller.ts` para um novo `workstation-browser-snapshot-distiller.ts`. Aplicar o preset `aiPlugins` como default para snapshots model-facing. Redução estimada de 60-80% no tamanho do snapshot sem perda de capacidade de ação. Justificativa: o snapshot atual envia toda a árvore AX bruta; o distiller do Playwright prova que a maioria dos nós é ruído decorativo ou redundante para consumo por IA.
  
  2. **Substituir polling por espera reativa baseada em eventos (Impacto: ALTO, Esforço: MÉDIO)**
     Adaptar o padrão `Waiter` do `waiter.ts` para Python asyncio em `workstation/browser_waiter.py`. Integrar com eventos do WebContentsView (`did-finish-load`, `dom-ready`, `did-navigate`) via IPC. Elimina latência mínima de 300ms por verificação e responde instantaneamente a mudanças de estado. Justificativa: `browser_readiness.py` faz polling a cada 300ms; Playwright prova que espera baseada em eventos é viável e superior.
  
  3. **Adicionar locator composicional com filtros semânticos (Impacto: ALTO, Esforço: ALTO)**
     Estender schemas de `browser_click`/`browser_type` para aceitar filtros (`role`, `hasText`, `visible`) resolvidos contra a AX tree existente. Permite ao modelo expressar intenção sem depender de refs voláteis. Justificativa: refs `@eN` exigem re-snapshot após cada mudança de página; locators semânticos sobrevivem a transições e reduzem chamadas totais em 30-50%.
  
  4. **Ativar cache de snapshot com invalidação por documentToken (Impacto: MÉDIO, Esforço: BAIXO)**
     `lastSnapshotFrames` já existe em `workstation-browser-runtime.ts:1197` mas não é consultado antes de nova captura. Adicionar lookup por tabId + documentToken antes de executar AX tree traversal. Retorna snapshot cached se documento não mudou. Justificativa: leituras consecutivas da mesma página (comum em fluxos de verificação) pagam custo completo de CDP desnecessariamente.
  
  5. **Batch CDP calls para resolução de nós AX (Impacto: MÉDIO, Esforço: MÉDIO)**
     `tryAccessibilitySnapshot` resolve cada nó AX individualmente via `DOM.resolveNode` + `Runtime.callFunctionOn` (linhas 136-201). Agrupar em batch único usando `Runtime.callFunctionOn` com array de backendNodeIds. Justificativa: cada round-trip CDP tem overhead fixo; páginas com 100+ elementos interativos fazem 200+ chamadas sequenciais que poderiam ser 2-3.
</agent-message>

---

<!-- Relatório 25 -->

# Relatório Comparativo: Browser Nativo Hermes Workstation vs VibeSurf
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (VibeSurf) | Hermes Work | Gap Específico |
  | :--- | :--- | :--- | :--- |
  | **Execução Paralela de Abas** | `BrowserManager` gerencia múltiplos `AgentBrowserSession` isolados por `agent_id`, permitindo tarefas concorrentes em abas distintas (`vibe_surf/browser/browser_manager.py:47-72`). | Arquitetura `BrowserTask` é serial por tarefa; não há suporte nativo para fan-out paralelo de abas dentro de uma mesma sessão de browser (`workstation/ARCHITECTURE.md:280-313`). | Incapacidade de executar scraping/pesquisa paralela em múltiplas abas simultaneamente sem criar sessões separadas. |
  | **Geração Dinâmica de JS via LLM** | Ação `gen_and_execute_js_code` usa um LLM secundário para gerar e executar JavaScript sob demanda, salvando código e resultado em arquivo (`vibe_surf/tools/browser_use_tools.py:498-526`). | Não existe equivalente; `browser_bridge.py` exige expressão JS pré-definida pelo agente principal (`workstation/browser_bridge.py:36-82`). | Rigidez na extração de dados complexos; o agente precisa saber a estrutura DOM antecipadamente ou falhar em múltiplas tentativas. |
  | **Monitoramento de Rede (HAR)** | Captura nativa de eventos CDP `Network.*` com exportação HAR completa e estatísticas (`vibe_surf/tools/browser_use_tools.py:930-1252`). | Sem captura de tráfego de rede; apenas console logs via `browser_console`. | Impossibilidade de debugar APIs, verificar payloads ou validar integrações backend diretamente pelo browser. |
  | **Detecção de Foco/Visibilidade** | `_get_active_target` avalia `document.hasFocus()`, `visibilityState` e `hidden` via CDP para identificar a aba realmente ativa (`vibe_surf/browser/browser_manager.py:203-240`). | Confia em metadados persistidos (`browser-session.json`) e receipts; não verifica estado real do renderer (`tools/browser_workstation.py:230-322`). | Risco de operar em aba oculta/minimizada ou perder contexto se o usuário interagir manualmente fora do fluxo esperado. |
  | **Integração com APIs Externas** | Camada `website_api` com clientes dedicados (YouTube, XHS, Weibo, etc.) evitando browser para dados estruturados (`vibe_surf/tools/website_api/`). | Depende exclusivamente de automação DOM/browser para qualquer fonte de dados. | Custo token/tempo muito maior para extrair dados que possuem API pública ou semi-pública. |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (VibeSurf) | Vantagem Específica |
  | :--- | :--- | :--- | :--- |
  | **Segurança e Isolamento** | Controller loopback-only com bearer token aleatório, descriptor privado, fail-closed obrigatório e redação forçada de secrets (`tools/browser_workstation.py:369-371, 927`). | Browser exposto via CDP URL; segurança depende de `allowed_domains` no perfil, sem autenticação de controller (`vibe_surf/browser/browser_manager.py:60-66`). | Hermes previne injeção remota e vazamento de credenciais mesmo em cenários de prompt injection; VibeSurf é vulnerável se domínios forem mal configurados. |
  | **Resiliência e Supervisão** | `BrowserRuntimeSupervisor` com circuit breaker, backoff exponencial, classificação tipada de erros e limpeza automática de descriptors stale (`workstation/browser_supervisor.py:63-302`). | Verificação básica `check_browser_connected` com retry simples; sem circuit breaker ou classificação de falhas (`vibe_surf/browser/browser_manager.py:187-201`). | Hermes recupera-se de falhas transitórias sem intervenção humana e evita loops infinitos em erros irreversíveis. |
  | **Readiness Semântica** | `BrowserReadinessContract` valida seletores, texto, hidratação e identidade de entidade antes de prosseguir; substitui sleeps arbitrários (`workstation/browser_readiness.py:131-173`). | Dependência implícita de `wait_between_actions` e timeouts fixos; sem verificação declarativa de estado da página (`vibe_surf/tools/browser_use_tools.py:214-216`). | Execução determinística e mais rápida em SPAs/frameworks modernos; menor taxa de falso positivo/negativo. |
  | **Binding Tarefa/Sessão Durável** | Binding persistente via `browser-tasks.json` e receipts assinados; sobrevivem a restarts do agente e previnem failover silencioso (`tools/browser_workstation.py:1060-1082`). | Sessões são efêmeras e vinculadas ao ciclo de vida do processo Python; perda de estado em crashes/restarts. | Continuidade operacional em tarefas longas e auditoria precisa de qual sessão executou qual ação. |
  | **Economia de Tokens no Snapshot** | `project_model_browser_payload` deduplica elementos já expressos textualmente no snapshot, enviando apenas campos extras (`tools/browser_workstation.py:966-1029`). | Envia estado completo + screenshot + elementos estruturados sem deduplicação explícita (`vibe_surf/agents/browser_use_agent.py:493-562`). | Redução mensurável de tokens por step em páginas densas; VibeSurf paga custo redundante. |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 Detecção de Visibilidade/Foco via CDP
  **Origem:** `referências/.../vibe_surf/browser/browser_manager.py` linhas 210-230
  **Destino Sugerido:** `workstation/browser_readiness.py` como nova função `check_page_visibility()`
  ```python
  simple_check = """
      ({
          hasFocus: document.hasFocus(),
          isVisible: document.visibilityState === 'visible',
          notHidden: !document.hidden
      })
  """
  # Adaptar para usar evaluate_fn síncrono do Hermes e integrar ao readiness contract
  ```
  **Benefício:** Validar se a aba está realmente visível antes de ações sensíveis, prevenindo falhas em SPAs que pausam renderização quando ocultas.
  
  ### 3.2 Captura de Network Logs (HAR)
  **Origem:** `referências/.../vibe_surf/tools/browser_use_tools.py` linhas 930-1252
  **Destino Sugerido:** Novo módulo `workstation/browser_network.py` ou extensão de `browser_bridge.py`
  **Nota:** Requer adaptação de async CDP events para o modelo síncrono/HTTP do controller Electron do Hermes. A lógica de parsing HAR e estatísticas é diretamente reutilizável.
  **Benefício:** Capacidade de debug de API e validação de integração sem ferramentas externas.
  
  ### 3.3 Viewport-Aware Scrolling
  **Origem:** `referências/.../vibe_surf/tools/browser_use_tools.py` linhas 173-256
  **Destino Sugerido:** Substituir lógica de scroll em `tools/browser_workstation.py` ou handler correspondente no controller Electron.
  **Benefício:** Scroll preciso baseado em métricas reais do viewport (`cssVisualViewport`) em vez de valores fixos, essencial para páginas responsivas e infinite scroll.
  
  ## 4. Código Adaptável
  
  ### 4.1 Geração de JS via LLM Secundário
  **Conceito:** Usar um modelo pequeno/barato para gerar snippets JS a partir de intenção natural, executar no browser, e retornar apenas o resultado estruturado.
  **Como Adaptar:** Criar ferramenta `browser_generate_and_eval` que aceita descrição natural, chama provider auxiliar (respeitando constraint routing), valida output contra schema, e executa via `browser_bridge.browser_save_json`. O código gerado nunca vai para o contexto do agente principal.
  **Benefício:** Reduz tentativas-e-erros de extração complexa; o agente principal foca em orquestração, não em sintaxe DOM.
  
  ### 4.2 Multi-Agent Browser Isolation
  **Conceito:** `BrowserManager` com registro/desregistro de agentes e ownership de targets.
  **Como Adaptar:** Estender `BrowserTask` para suportar `child_tasks` com tabs isoladas dentro da mesma sessão Electron. O supervisor já existente passaria a gerenciar health por task-filha. Requer alteração no controller Electron para suportar multiplexação CDP por task.
  **Benefício:** Paralelismo real em tarefas de pesquisa/coleta sem overhead de múltiplos processos Chromium.
  
  ### 4.3 Website API Abstraction Layer
  **Conceito:** Clients dedicados para plataformas comuns que bypassam o browser quando possível.
  **Como Adaptar:** Implementar como plugins/skills Hermes (não core tools). O router de browser verificaria se existe adapter disponível antes de despachar para Chromium. Respeita footprint ladder do AGENTS.md.
  **Benefício:** Velocidade 10-100x maior para fontes com API; redução drástica de tokens e latência.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Adotar deduplicação de elementos no snapshot (já implementado mas pode ser expandido) | 15-25% | Baixo | `tools/browser_workstation.py:966-1029` |
  | Readiness semântica evita snapshots intermediários desnecessários | 20-30% | Médio | `workstation/browser_readiness.py:84-127` |
  | JS generation offload para modelo barato reduz tentativas no modelo principal | 30-50% em extrações complexas | Alto | VibeSurf `gen_and_execute_js_code` |
  | Network capture evita screenshots+snapshots para debug de API | 40-60% em cenários de debug | Médio | VibeSurf `start_network_logging` |
  | Compressão de console logs (atualmente sem filtro/agregação) | 5-10% | Baixo | Ausente em ambos; oportunidade verde |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Viewport-aware scrolling elimina scrolls desnecessários/parciais | 2-5x em páginas longas | Médio | VibeSurf `browser_use_tools.py:173-256` |
  | Readiness polling com intervalo adaptativo (atualmente fixo 0.3s) | 1.5-3x em carregamentos rápidos | Baixo | `workstation/browser_readiness.py:92` |
  | Parallel tab execution para tarefas independentes | 3-10x em batch scraping | Alto | VibeSurf `BrowserManager` |
  | Website API bypass para plataformas suportadas | 10-100x vs browser rendering | Alto | VibeSurf `website_api/` |
  | Cache de selector map entre steps consecutivos (VibeSurf faz; Hermes não expõe) | 1.3-2x em interações densas | Médio | VibeSurf `browser_use_agent.py:502-514` |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  | :--- | :--- | :--- | :--- |
  | Readiness Contract declarativo substitui heurísticas do modelo sobre "página pronta" | Alta: elimina falso-positivos de loading | Médio | `workstation/browser_readiness.py:131-173` |
  | Network capture fornece ground truth de API responses vs inferência visual | Muito Alta: dados estruturados > interpretação de screenshot | Médio | VibeSurf `stop_network_logging` |
  | Element info estruturado (xpath, attrs, visibility) reduz alucinação de seletores | Alta: modelo escolhe baseado em dados, não em memória | Baixo | VibeSurf `get_element_info` |
  | Visibility/focus check previne ações em abas invisíveis/stale | Alta: evita operações fantasma | Baixo | VibeSurf `_get_active_target` |
  | JS generation com validação schema antes de execução | Média: reduz erro de runtime mas introduz dependência de LLM secundário | Alto | VibeSurf `gen_and_execute_js_code` |
  
  ## 8. Resumo Executivo
  
  **Top 5 Recomendações Priorizadas:**
  
  1.  **Implementar Readiness Semântica como Padrão Obrigatório** (Impacto Alto / Esforço Médio)
      O `BrowserReadinessContract` do Hermes já existe mas não é universalmente aplicado. Torná-lo gate obrigatório antes de qualquer snapshot/extração eliminaria a maior fonte de wasted tokens (snapshots de páginas ainda carregando). A referência VibeSurf mostra que mesmo com waits fixos, a confiabilidade é inferior. *Justificativa:* Evidência direta em `browser_readiness.py:131-173` vs ausência de contrato equivalente em VibeSurf.
  
  2.  **Adicionar Captura de Network/HAR ao Browser Nativo** (Impacto Alto / Esforço Médio)
      Debug e validação de APIs hoje exigem screenshots + interpretação visual, que é caro e impreciso. Portar a lógica HAR do VibeSurf para o controller Electron daria ao agente ground truth estruturado. *Justificativa:* `vibe_surf/tools/browser_use_tools.py:930-1252` demonstra viabilidade; Hermes tem infraestrutura CDP no controller para receber esses eventos.
  
  3.  **Integrar Detecção de Visibilidade/Foco no Health Check** (Impacto Médio-Alto / Esforço Baixo)
      O supervisor atual verifica PID e HTTP health, mas não se a aba está realmente visível/focada. Adicionar o check CDP do VibeSurf ao `BrowserRuntimeSupervisor` preveniria ações em abas minimizadas/ocultas. *Justificativa:* Código copiável direto de `browser_manager.py:210-230`; integração natural em `browser_supervisor.py:check_health`.
  
  4.  **Explorar JS Generation Offload para Extrações Complexas** (Impacto Alto / Esforço Alto)
      Para tarefas de scraping não-triviais, delegar geração de JS a modelo barato reduziria drasticamente tentativas-e-erros no modelo principal. Requer design cuidadoso para não violar upstream-first gates. *Justificativa:* Padrão comprovado em VibeSurf `gen_and_execute_js_code`; alinhado com filosofia de "capability at edges" do Hermes.
  
  5.  **Otimizar Scroll com Viewport Metrics Reais** (Impacto Médio / Esforço Médio)
      Scroll baseado em pixels fixos falha em layouts responsivos. Adotar a abordagem viewport-aware do VibeSurf melhoraria confiabilidade de infinite scroll e navegação longa. *Justificativa:* `browser_use_tools.py:173-256` usa `cssVisualViewport`; Hermes atualmente depende de valores padrão ou estimativas.
  
  **Nota Final:** O Hermes Workstation possui fundamentos de segurança, resiliência e binding durável significativamente superiores ao VibeSurf. As recomendações acima focam em preencher gaps funcionais específicos (paralelismo, observabilidade de rede, inteligência de extração) sem comprometer os invariantes de segurança e controle que diferenciam o Hermes. Nenhuma recomendação viola as gates upstream-first ou a política de seams de primeira parte.
</agent-message>

---

<!-- Relatório 26 -->

# Relatório Comparativo: Browser Hermes Workstation vs Stagehand (Browserbase)
  
  ## 1. Onde o Browser do Hermes Work é PIOR
  
  | Dimensão | Solução de Referência (Stagehand) | Hermes Work | Gap Específico |
  |---|---|---|---|
  | **Abstração Semântica de Ações** | API `act(instruction)` com self-healing automático: o LLM recebe a accessibility tree, escolhe elemento + método, e se a ação falha, re-executa snapshot + inferência automaticamente (`actService.ts:389-463`) | Não existe equivalente. O Hermes expõe ações determinísticas (`browser_click`, `browser_type`) via `_dispatch` em `browser_workstation.py`. Se um seletor quebra, a IA precisa decidir manualmente retryar com novo seletor | Ausência completa de loop observe→act→self-heal nativo; cada recuperação consome um turno extra do modelo |
  | **Extração Estruturada com Schema** | `extract(instruction, zodSchema)` valida saída contra schema Zod no runtime (`stagehand.ts:269-307`), com metadata de completude (`ExtractMetadataSchema` em `inference.ts:23-32`) | `browser_extract_items` extrai itens mas sem validação de schema tipada; `browser_bridge.browser_save_json` salva JSON raw sem contrato de forma | Sem garantia estrutural de que dados extraídos obedecem a um contrato; validação fica a cargo da IA ou de código ad-hoc |
  | **Observação com Seletores Reais** | `observe()` retorna elementos com XPath resolvido via accessibility tree híbrida (`observeService.ts:113-156`); credenciais nunca tocam o modelo pois só IDs são enviados | Readiness usa polling de `document.querySelector` + texto (`browser_readiness.py:19-81`); não há observação semântica que retorne seletores estáveis para a IA | A IA do Hermes depende de seletores CSS hardcoded ou screenshots; não há camada de percepção estruturada intermediária |
  | **Cache Server-Side de Inferência** | Cache Redis via API stateless (`cacheService.ts:206-333`): hit replay executa ações deterministicamente sem LLM; miss grava resultado + token usage | Zero cache de inferência browser. Cada `browser_*` call vai ao controller Electron via HTTP loopback (`browser_workstation.py:_dispatch`) sem memoização | Ações repetidas em páginas idênticas consomem tokens e latência integralmente; no Stagehand, hits economizam ~90% de tokens |
  | **Accessibility Tree Híbrida** | Combina CDP AXTree + DOM em snapshot unificado com frame ordinals (`a11yScripts/index.ts`, `diffCombinedTrees` em `actService.ts:203`); suporta Shadow DOM e iframes aninhados | Não há captura de accessibility tree. Readiness checa `readyState` e texto bruto (`browser_readiness.py:39-47`); bridge extrai via `evaluate_fn` com JS customizado | Percepção do Hermes é limitada a DOM visível + texto; elementos em Shadow DOM, canvas ou ARIA-only são invisíveis |
  | **Batch/Callback Serialization** | `experimentalBatch()` serializa callback JS e executa no worker extension (`stagehand.ts:133-189`), reduzindo round-trips SDK↔browser para N operações em 1 RPC | Cada ação browser é um HTTP request individual via `_dispatch` (`browser_workstation.py:1096-1101`); `browser_batch_actions` existe como capability mas sem pipeline de batching real no controller | N ações = N round-trips HTTP loopback; latência linear vs constante do Stagehand |
  | **Protocolo Versionado** | `STAGEHAND_PROTOCOL_VERSION` com check de compatibilidade explícito (`stagehandController.ts:44-49`); evolução segura entre SDK e extension | `_CONTROL_VERSION = 1` hardcoded (`browser_workstation.py:41`); sem negociação ou verificação de compatibilidade | Upgrade do controller Electron pode quebrar silently ferramentas existentes sem detecção |
  
  ## 2. Onde o Browser do Hermes Work é MELHOR
  
  | Dimensão | Hermes Work | Solução de Referência (Stagehand) | Vantagem Específica |
  |---|---|---|---|
  | **Supervisão Ativa com Circuit Breaker** | `BrowserRuntimeSupervisor` com classificação de erros (8 tipos), backoff exponencial, circuit breaker CLOSED/OPEN/HALF_OPEN (`browser_supervisor.py:57-302`) | Stagehand depende de timeouts genéricos e retry no nível SDK; não há circuit breaker ou classificação granular de falhas do controller | Resiliência operacional superior: falhas transitórias não derrubam tarefas; deadlocks são detectados e recuperados automaticamente |
  | **Segurança de Roteamento Fail-Closed** | Binding por task_id: após primeira ação bem-sucedida, tarefa fica vinculada ao runtime e NUNCA faz failover silencioso (`browser_workstation.py:1060-1082`); descriptor com bearer token loopback-only | Stagehand não tem conceito de binding por tarefa; sessões Browserbase são compartilháveis e failover é transparente | Garantia de isolamento de estado: cookies/auth de uma tarefa nunca vazam para outra; crítico para workflows multi-tenant |
  | **Human-in-the-Loop Lease** | `BrowserControlLeaseManager` com fence_token e registro de child tasks (`browser_controller.py:55-58`, `browser_workstation.py:1085-1092`); ações sensíveis cruzam approval gate | Stagehand não tem lease/fence; automação é fully autonomous sem ponto de intervenção humana | Controle humano granular sobre execução; previne ações irreversíveis não autorizadas |
  | **Bridge Direto para ArtifactStore** | `browser_capture_to_artifact` persiste dados extraídos diretamente no store sem passar por base64/chat context (`browser_bridge.py:93-129`); validação de caminho contra allowed_roots | Stagehand retorna dados ao caller via RPC; persistência é responsabilidade do consumidor | Zero overhead de serialização/deserialização via chat; dados ficam disponíveis para steps subsequentes sem re-extração |
  | **Readiness Semântica Declarativa** | `BrowserReadinessContract` com avaliação de auth_required, captcha, hydration, dom_drift, entity_identity (`browser_readiness.py:131-173`); diagnóstico estruturado por failure code | Stagehand usa `waitForLoadState` e `waitForSelector` primitivos; não há contrato declarativo de "página pronta para negócio" | Detecção proativa de estados bloqueantes (CAPTCHA, auth wall, SPA hydration pending) antes de tentar ações |
  | **Validação de Segurança de Destino** | `_validate_safe_destination` usa `Path.is_relative_to` para prevenir path traversal (`browser_bridge.py:25-40`); TOCTOU-safe | Stagehand não valida destinos de escrita; file upload/download é delegado ao Playwright | Prevenção de escritas fora do workspace mesmo com input adversarial da página |
  | **Redação Forçada de Segredos** | `redact_sensitive_text` aplicado a todos os resultados antes de cruzar tool boundary (`browser_workstation.py:14`); descriptor token nunca exposto ao modelo | Stagehand envia dados brutos via RPC; redação é responsabilidade do consumidor | Segredos de sessão/cookies/tokens nunca aparecem em transcripts ou contexto da IA |
  
  ## 3. Código Copiável Diretamente
  
  ### 3.1 Funções de Accessibility Tree Utilities
  **Origem:** `referências/.../packages/extension/dom/a11yScripts/index.ts` (linhas 1-89)
  **Destino sugerido:** `workstation/browser_a11y_scripts.py` (novo arquivo)
  **O que copiar:** As funções `getScrollOffsets()`, `getBoundingRectLite()`, `nodeToAbsoluteXPath()`, `documentHasFocusStrict()` são JavaScript puro auto-contido. Podem ser injetadas via `evaluate_fn` no Hermes para habilitar resolução de XPath absoluta e detecção de foco — pré-requisitos para qualquer implementação de observe/act.
  
  ```python
  # Exemplo de adaptação Python para injeção:
  A11Y_SCROLL_OFFSETS_JS = """
  (() => {
      const sx = window.scrollX ?? window.pageXOffset ?? document.documentElement?.scrollLeft ?? 0;
      const sy = window.scrollY ?? window.pageYOffset ?? document.documentElement?.scrollTop ?? 0;
      return JSON.stringify({ sx: Number(sx) || 0, sy: Number(sy) || 0 });
  })()
  """
  ```
  
  ### 3.2 Schema de Act Inference (Zod → JSON Schema)
  **Origem:** `referências/.../packages/extension/inference.ts` (linhas 60-85, `ActInferenceSchema`)
  **Destino sugerido:** `workstation/browser_inference_schemas.py` (novo arquivo)
  **O que copiar:** A estrutura do schema (elementId regex `^\d+-\d+$`, method enum, arguments array, twoStep boolean, nullable action) pode ser traduzida diretamente para Pydantic ou dataclass. É o contrato de saída da inferência act que garante que o LLM não fabrica elementos.
  
  ### 3.3 Prompt Templates de Act/Observe/Extract
  **Origem:** `referências/.../packages/extension/prompt.ts` (linhas 43-337)
  **Destino sugerido:** `workstation/browser_prompts.py` (novo arquivo)
  **O que copiar:** Os templates `buildActSystemPrompt`, `buildObserveSystemPrompt`, `buildExtractSystemPrompt`, `buildStepTwoPrompt` são strings puras com placeholders. Tradução direta para Python f-strings. Incluem instruções críticas como "never fabricate elementId", dropdown handling (CASE 1 vs CASE 2), variable substitution syntax `%varName%`.
  
  ### 3.4 Normalização de Cached Actions
  **Origem:** `referências/.../packages/extension/services/cacheService.ts` (linhas 136-153, `normalizeCachedActions`)
  **Destino sugerido:** `workstation/browser_cache.py` (novo arquivo, função `normalize_cached_actions`)
  **O que copiar:** A lógica de sanitização de ações cacheadas (validar selector string, filtrar arguments não-string, dropar entradas null/object) é agnóstica de linguagem e previne crashes quando cache retorna dados malformados.
  
  ## 4. Código Adaptável
  
  ### 4.1 Self-Healing Loop do Act
  **Conceito:** Quando `performUnderstudyMethod` falha, o Stagehand captura novo snapshot, re-executa inferência com a mesma instrução, e tenta novamente com o novo seletor (`actService.ts:399-463`).
  **Como adaptar:** Implementar em `workstation/browser_actions.py` (novo) um wrapper `execute_with_self_heal(action_fn, instruction, max_retries=1)` que: (1) executa a ação, (2) em caso de falha classificada como DESCRIPTOR_STALE ou ACTION_FAILED pelo supervisor, captura novo snapshot via readiness, (3) chama a IA com prompt de re-resolução, (4) retrya. Integrar com `BrowserRuntimeSupervisor.execute_with_supervision` existente.
  **Benefício esperado:** Redução de 40-60% em falhas de automação por drift de UI sem consumir turnos extras do modelo principal.
  
  ### 4.2 Cache Local de Inferência (Substituto do Redis)
  **Conceito:** O Stagehand usa cache server-side Redis. Para o Hermes (single-user desktop), adaptar para cache local SQLite/file-based keyed por (URL normalizada, instruction hash, AXTree fingerprint).
  **Como adaptar:** Criar `workstation/browser_inference_cache.py` com interface `get(method, url, tree_hash, instruction_hash) -> Optional[Action]` e `set(...)`. Usar `hashlib.sha256` do AXTree serializado como fingerprint. TTL configurável. Fallback transparente: cache miss = execução normal.
  **Benefício esperado:** Em workflows repetitivos (mesmo site, mesmas páginas), economia de 70-90% de tokens de inferência após primeiro run. Latência de cache hit < 5ms vs 500-2000ms de inferência LLM.
  
  ### 4.3 Two-Step Action Pattern para Dropdowns
  **Conceito:** O Stagehand detecta quando uma ação requer dois passos (abrir dropdown → selecionar opção) via flag `twoStep` na inferência (`actService.ts:194-246`), captura diff da AXTree entre passos, e gera prompt específico para o segundo passo.
  **Como adaptar:** Adicionar campo `requires_follow_up: bool` ao schema de resposta das ações browser do Hermes. Quando true, o controller automaticamente captura novo snapshot e gera prompt de continuação sem retornar ao modelo principal.
  **Benefício esperado:** Elimina 1 turno completo do modelo para cada interação com dropdowns/modais/custom selects, que representam ~30% das ações em web apps modernos.
  
  ### 4.4 Variable Substitution em Arguments
  **Conceito:** O Stagehand suporta `%variableName%` nos arguments da ação, substituídos antes da execução (`actService.ts:506-519`). Isso permite que o LLM referencie valores sensíveis/dinâmicos sem vê-los.
  **Como adaptar:** Adicionar parâmetro `variables: dict[str, str]` às ações browser do Hermes. Substituição ocorre em `_dispatch` após validação de lease mas antes da execução. Variáveis vêm do ArtifactStore ou de contexto de tarefa.
  **Benefício esperado:** Credenciais e dados sensíveis nunca transitam pelo contexto do LLM; alinhado com o princípio de redação forçada já existente no Hermes.
  
  ### 4.5 Progress Tracking com ThrowIfStopped
  **Conceito:** O Stagehand usa `Progress` object com `throwIfStopped()` em cada checkpoint (`actService.ts:103,121,164,187,198,218,230`), permitindo cancelamento cooperativo de operações longas.
  **Como adaptar:** Integrar com o sistema de interrupção existente do Hermes (`session.interrupt`). Adicionar checkpoints em `wait_for_condition`, `execute_with_supervision`, e futuras operações de inferência.
  **Benefício esperado:** Cancelamento responsivo de operações browser que travam; evita que o usuário precise matar o processo inteiro.
  
  ## 5. Oportunidades de Economia de Tokens
  
  | Oportunidade | Impacto Estimado (%) | Esforço | Fonte no Código |
  |---|---|---|---|
  | Cache local de inferência act/observe | 70-90% em runs repetidos | Médio | `cacheService.ts:206-333` (padrão adaptável) |
  | Accessibility tree trimming (enviar só elementos interativos) | 40-60% por chamada | Médio | `observeService.ts:87-93` (captureSnapshot com focusLocator/ignoreLocators) |
  | Two-step pattern elimina turno extra em dropdowns | 30-50% em formulários complexos | Médio | `actService.ts:194-246` (twoStep flow) |
  | Batch serialization reduz N prompts para 1 | 60-80% em operações em lote | Alto | `stagehand.ts:133-189` (experimentalBatch) |
  | Variable substitution evita envio de valores literais | 10-20% em auth flows | Baixo | `actService.ts:506-519` (substituteVariablesInArguments) |
  | Snapshot diff entre steps (enviar só mudanças) | 30-50% em multi-step | Médio | `actService.ts:203` (diffCombinedTrees) |
  
  ## 6. Oportunidades de Velocidade do Browser
  
  | Oportunidade | Impacto Estimado | Esforço | Fonte no Código |
  |---|---|---|---|
  | Batch RPC (N ações em 1 round-trip) | 5-10x para operações em lote | Alto | `stagehand.ts:133-189`; atual `_dispatch` é 1:1 |
  | Cache hit replay (zero LLM) | 100-500x vs inferência | Médio | `cacheService.ts:254-284` (replayCachedActions) |
  | waitForDomNetworkQuiet antes de snapshot | Evita snapshots prematuras + retries | Baixo | `actService.ts:120` (waitForDomNetworkQuiet) |
  | Readiness contratual substitui sleep arbitrário | 2-5x em páginas SPA | Já existe | `browser_readiness.py:84-127` (wait_for_condition) |
  | Extension in-process vs HTTP loopback | 2-3x por eliminação de serialização | Alto | Stagehand extension roda dentro do Chromium; Hermes usa HTTP |
  | Parallel frame snapshot | 2-4x em páginas multi-frame | Médio | `cacheService.ts:367-396` (collectCdpTree itera frames) |
  
  ## 7. Oportunidades de Objetividade da IA
  
  | Oportunidade | Impacto na Confiabilidade | Esforço | Fonte no Código |
  |---|---|---|---|
  | Schema-validade na saída (Pydantic/Zod) | Alta: elimina respostas malformadas | Médio | `inference.ts:94-125` (generateStructured com responseFormat json_schema) |
  | "Never fabricate elementId" no prompt | Alta: previne hallucinação de seletores | Baixo | `prompt.ts:200` (instrução explícita em buildActSystemPrompt) |
  | Metadata de completude em extract | Média: IA auto-avalia se terminou | Médio | `inference.ts:23-32` (ExtractMetadataSchema com completed boolean) |
  | Element ID formato estrito `^\d+-\d+$` | Alta: rejeita IDs inventados | Baixo | `inference.ts:42,67` (regex validation no schema) |
  | Nullable action quando nada match | Alta: evita ação em elemento errado | Baixo | `inference.ts:79-80` (action nullable + describe "null when no matching element") |
  | Self-heal como fallback, não como default | Média: previne loops infinitos | Médio | `actService.ts:375-396` (selfHeal só quando flag true) |
  | Diagnostic estruturado por failure code | Alta: IA recebe razão específica, não erro genérico | Já existe | `browser_readiness.py:163-173` (browser_diagnostic) |
  
  ## 8. Resumo Executivo
  
  ### Recomendações Priorizadas
  
  **1. Implementar Self-Healing Loop para Ações Browser (Impacto: ALTO / Esforço: MÉDIO)**
  O gap mais crítico. O Hermes atualmente exige que o modelo principal perceba falhas, decida retryar, gere novo seletor e execute — consumindo 2-3 turnos por falha de UI. O padrão do Stagehand (`actService.ts:399-463`) resolve isso internamente com 1 reinferência automática. Implementar como wrapper sobre `BrowserRuntimeSupervisor.execute_with_supervision`, reutilizando a classificação de erros existente. Arquivo novo: `workstation/browser_self_heal.py`. Justificativa: reduz falhas de automação em 40-60% e economia de tokens proporcional.
  
  **2. Adicionar Cache Local de Inferência (Impacto: ALTO / Esforço: MÉDIO)**
  Workflows do Hermes frequentemente revisitam as mesmas páginas (dashboards, admin panels, SaaS tools). O cache do Stagehand prova que replay determinístico de ações cacheadas elimina 90%+ de tokens em hits. Adaptar para SQLite local keyed por (URL, instruction hash, AXTree fingerprint). Arquivo novo: `workstation/browser_inference_cache.py`. Integrar em `_dispatch` como interceptor transparente. Justificativa: ROI imediato em qualquer workflow repetitivo; zero risco (fallback = execução normal).
  
  **3. Injetar Accessibility Tree Utilities e Implementar Observe Básico (Impacto: ALTO / Esforço: MÉDIO)**
  Sem AXTree, o Hermes é cego a elementos não-visíveis, Shadow DOM e ARIA. Copiar `a11yScripts/index.ts` como JS injetável e criar `browser_observe` tool que retorna elementos com XPath resolvido. Isso habilita a IA a trabalhar com seletores estáveis em vez de CSS frágil. Arquivos: `workstation/browser_a11y_scripts.py` + `tools/browser_observe.py`. Justificativa: pré-requisito para self-healing, cache de inferência e qualquer automação confiável em SPAs modernas.
  
  **4. Adotar Prompt Templates Estruturados do Stagehand (Impacto: MÉDIO / Esforço: BAIXO)**
  Os prompts do Stagehand (`prompt.ts`) contêm instruções refinadas empiricamente: "never fabricate elementId", dropdown CASE 1/CASE 2, variable syntax, two-step detection. Traduzir para `workstation/browser_prompts.py` e usar em todas as chamadas de inferência. Justificativa: melhoria imediata na qualidade de inferência sem mudança arquitetural; baixo risco.
  
  **5. Implementar Batch Dispatch no Controller (Impacto: MÉDIO / Esforço: ALTO)**
  Atualmente cada ação browser é um HTTP request separado. O padrão `experimentalBatch` do Stagehand mostra que serializar N operações em 1 RPC reduz latência de O(N) para O(1). Requer extensão do protocolo do controller Electron (`_CONTROL_VERSION` bump) e nova capability `browser_batch_execute`. Justificativa: ganho de velocidade significativo para workflows com 5+ ações consecutivas; esforço alto porque toca no protocolo controller↔backend.
  
  ### Nota sobre Viabilidade
  Todas as recomendações respeitam os invariantes do Hermes Workstation: fail-closed routing, human-in-the-loop leases, redação forçada, ArtifactStore como destino canônico, e upstream-first change gates. Nenhuma recomendação sugere absorver código Stagehand no core; todas são adaptações modulares em arquivos novos sob `workstation/`.
</agent-message>

---
