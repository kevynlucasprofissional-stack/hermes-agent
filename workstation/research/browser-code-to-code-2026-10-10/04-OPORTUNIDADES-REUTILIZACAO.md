# 04 — Oportunidades de Reutilização de Código: Matriz Decisória

**Data:** 10 de Outubro de 2026  
**Status:** FACT & CODE REUSABILITY CATALOG  

---

## 1. Classificação das Oportunidades por Categoria

Esta seção formaliza o destino de cada mecanismo auditado, aplicando rigorosamente as restrições de licença (MIT vs AGPL-3.0 vs Apache-2.0) e as invariantes arquiteturais do Hermes Work.

---

## 2. Oportunidades de Cópia Direta (`COPY`)

Estas implementações possuem licença permissiva (MIT ou Apache-2.0) e podem ser portadas diretamente para o repositório mediante adaptações mínimas de tipagem.

### Item COPY-1: Motor de Ações em Lote (`BatchAction` e `executeBatch`)
```text
Repositório: browserclaw-main
Commit: N/A (snapshot v0.20.3)
Arquivo: src/actions/batch.ts
Símbolo: export type BatchAction, export async function executeBatch
Licença do arquivo: MIT License (compatível com Hermes MIT)
Dependências: Playwright-core (ou CDP direto)
Local correspondente no Hermes: apps/desktop/electron/workstation-browser-batch.ts
Adaptações mínimas: Adaptar chamadas de página para utilizar o WebContentsView do Electron ou wc.debugger em vez do Playwright Page
Testes necessários: Testar execução sequencial de 5 cliques/inputs, interrupção por stopOnError, e timeout de lote
Riscos: Baixo; o motor roda isolado na thread do Electron
Estimativa de esforço: 1 a 2 dias de engenharia
```

### Item COPY-2: Importador de Sessão e Cookies do Google Chrome Local (`chrome-import`)
```text
Repositório: browser-use--desktop
Commit: f073b7574fcf376a524733355038b30f5ecb8a1c
Arquivo: app/src/main/chrome-import/index.ts (e decodificador DPAPI Windows)
Símbolo: export async function importChromeProfileCookies()
Licença do arquivo: MIT License
Dependências: sqlite3, node-dpapi (ou crypto nativo do Node/Electron)
Local correspondente no Hermes: apps/desktop/electron/chrome-import.ts
Adaptações mínimas: Inserir cookies decodificados na sessão Electron via session.defaultSession.cookies.set()
Testes necessários: Testar leitura de cookies do perfil Default no Windows 11 com descriptografia DPAPI
Riscos: Mudança futura na chave de criptografia do Chrome (v20); requer fallback gracioso caso falhe
Estimativa de esforço: 1 dia de engenharia
```

### Item COPY-3: Calculadora de Custos de Inferência por Execução (`pricing.py`)
```text
Repositório: EricFinland--witness
Commit: 2d3ccdcd6ce6a21356bfb9e1e2333036a1955b25
Arquivo: witness/pricing.py
Símbolo: calculate_cost(model: str, input_tokens: int, output_tokens: int, images: int) -> float
Licença do arquivo: MIT License
Dependências: Nenhuma (Python puro com dicionário de preços)
Local correspondente no Hermes: workstation/operational_telemetry.py e agent/turn_*.py
Adaptações mínimas: Conectar com o contador de tokens do TaskRun do Hermes
Testes necessários: Testar cálculo de custo para modelos OpenAI, Anthropic e DeepSeek
Riscos: Nenhum; puramente métrica analítica
Estimativa de esforço: 3 horas
```

### Item COPY-4: Sentinela de Detecção e Recuperação de Travamento (`CrashWatchdog`)
```text
Repositório: browser-use--browser-use
Commit: c75e8476e2715055b85a36399cebc5ea396a8be4
Arquivo: browser_use/browser/watchdogs/crash_watchdog.py
Símbolo: class CrashWatchdog(BaseWatchdog)
Licença do arquivo: MIT License
Dependências: bubus (barramento de eventos) ou EventEmitter nativo
Local correspondente no Hermes: apps/desktop/electron/workstation-browser-runtime.ts (no evento wc.on('render-process-gone'))
Adaptações mínimas: Converter o listener Python para evento Electron nativo render-process-gone
Testes necessários: Disparar crash intencional via chrome://crash e verificar restauração da aba
Riscos: Muito baixo; melhora a estabilidade
Estimativa de esforço: 4 horas
```

---

## 3. Oportunidades de Adaptação (`ADAPT`)

### Item ADAPT-1: Extração Estruturada com Cache (`extract`) do Stagehand
- **Referência:** `browserbase--stagehand` (`packages/sdk-ts/src/clientSchemas.ts` e `caching.py`).
- **O que adaptar:** Adicionar o método `browser_extract(instruction, schema, cache=True)` no `tools/browser_workstation.py`. Quando chamado, o runtime avalia a página, extrai os campos no formato JSON solicitado e grava o resultado indexado por `hash(url + dom_digest + instruction)`.
- **Benefício:** Elimina centenas de chamadas erráticas ao `browser_console` observadas nas sessões reais.

### Item ADAPT-2: Detecção e Classificação de UI Drift do Driftlock
- **Referência:** `VasuBansal7576--driftlock` (`driftlock/lib/diagnose.mjs`).
- **O que adaptar:** Integrar o algoritmo de diagnóstico em `workstation/operational_kernel.py`. Ao encontrar um `CapabilityDriftError`, classificar se o drift é `COSMETIC`, `LAYOUT_SHIFT` ou `STRUCTURAL_BREAK` e tentar auto-reparo do seletor antes da quarentena.

---

## 4. Reimplementação de Padrões (`REIMPLEMENT PATTERN`)

### Item REIMPL-1: Diff de Snapshots em Nível de Linhas do BrowserOS
- **Referência:** `browseros-ai--BrowserOS` (`packages/browser-core/src/core/snapshot/diff.ts`).
- **Motivo de não copiar diretamente:** O BrowserOS é **AGPL-3.0**. Copiar o arquivo contaminaria a base MIT do Hermes.
- **O que reimplementar:** Reimplementar em TypeScript limpo no Hermes Desktop o algoritmo de Longest Common Subsequence (LCS) com janela de contexto deslizante (`contextRadius = 3`). O runtime retornará deltas formatados (`+ linha`, `- linha`) em vez de snapshots inteiros pós-clique.

### Item REIMPL-2: Snapshot Nativo via CDP AXTree (Inspirado no Agent Browser e BrowserOS)
- **Referência:** `vercel-labs/agent-browser` (`snapshot.rs`) e `browseros-ai/BrowserOS` (`render.ts`).
- **O que reimplementar:** Trocar a injeção do `inventoryScript` no DOM por uma chamada ao domínio de acessibilidade do Chromium via `Accessibility.getFullAXTree`. Formatar a saída em texto indentado com referências numéricas curtas (`@1`, `@2`), reduzindo a latência de 800 ms para menos de 50 ms.

---

## 5. Integração Externa (`INTEGRATE EXTERNAL`)

### Item EXT-1: Camofox como Backend de Evasão Avançada
- **Referência:** `camofox-browser-main`.
- **Decisão:** Manter como serviço autônomo via Docker / processo separado. O Hermes Agent aciona o Camofox via `tools/browser_camofox.py` somente para alvos com Cloudflare rigoroso ou proteções antibot de alto nível.

---

## 6. O que Manter no Hermes Work (`KEEP HERMES`)

1. **`WebContentsView` dentro do Electron com Throttling para 6 fps em Background:** Superior a qualquer solução externa em isolamento e economia de energia.
2. **`BrowserSessionStateFilePersistence` com Restauração Lazy:** Sistema de recuperação de abas pós-restart comprovadamente seguro e com zero vazamento de memória.
3. **`OperationalKernel` e `ExperienceCompiler`:** Vantagem competitiva absoluta do Hermes Work. Nenhum outro projeto tem compilação de procedimentos operacionais com verificação em dois níveis.
4. **Contratos de Autoridade e Leases (`BrowserHumanControlLease`):** Proteção formal contra concorrência entre humano e agente.

---

## 7. O que Rejeitar (`REJECT`)

1. **Compilação de Chromium Customizado do BrowserOS:** Custo de compilação e manutenção incompatível com desenvolvimento ágil.
2. **Dependência da JVM do Browser4:** Incompatível com o ecossistema Python/TypeScript do Hermes.
3. **VibeSurf:** Licença com cláusulas comerciais restritivas e código redundante.
4. **Hermes WebUI como substituto do Desktop:** Não oferece abas nativas aceleradas por GPU.
