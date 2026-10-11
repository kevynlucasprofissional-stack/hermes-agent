# Relatório de Auditoria Code-to-Code: Stagehand

**Projeto:** Stagehand (`browserbase/stagehand`)  
**Commit SHA:** `f261c38b4d83e16441bf105fc1f1fae92976eb69`  
**Branch:** `main`  
**Caminho Local:** `referências/02-Browser-Automacao-Web/browserbase--stagehand`  
**Licença:** **Apache-2.0** (`LICENSE`)  
**Stack:** TypeScript / Node.js (monorepo Turbo/pnpm), Python (`packages/sdk-python`)  
**Tamanho Auditado:** 1.133 arquivos TS, 82 arquivos Python, 469 arquivos de teste  
**Classificação de Reuso:** **ADAPT / COPY** (Apache-2.0 é compatível com MIT mediante inclusão de copyright notice)  

---

## 1. Identidade e Arquitetura

O Stagehand, desenvolvido pela Browserbase, é um framework de automação focado em três primitivos modulares de alta confiança:
1. `act(instruction)`: Executa ações autônomas orientadas por intenção na página.
2. `extract(instruction, schema)`: Extração de dados estruturados com validação por Pydantic/Zod e cache determinístico.
3. `observe(instruction)`: Percepção de elementos e ações possíveis para planejamento.

A arquitetura desacopla o protocolo de comandos (`packages/protocol`) do cliente de execução local e remoto (`packages/sdk-ts` e `packages/sdk-python`).

---

## 2. Mecanismos Relevantes Inspecionados

### 2.1. Execução em Lote (`experimentalBatch`)
- **Arquivo:** `packages/sdk-ts/src/batch.ts` (linhas 1–76)
- **Símbolo:** `experimentalBatch(callback, options): Promise<Result>`
- **Mecanismo:** Executa um conjunto de operações (`act`, `observe`, `extract`) sob um único prazo de execução no lado do navegador (`CALLBACK_BATCH_CLIENT_GRACE_MS = 15_000`). O cliente aguarda uma única resposta consolidada em vez de fazer viagens de ida e volta (roundtrips) a cada clique.
- **Superioridade sobre Hermes Work:** No Hermes Work, cada ação elementar requer uma requisição HTTP isolada com 160–220 ms de delay forçado e geração de snapshot completo. O Stagehand permite agrupamento com medição única de métricas (`metrics()`).

### 2.2. Extração Estruturada com Cache Determinístico
- **Arquivo:** `packages/sdk-python/examples/caching.py` e `packages/sdk-ts/src/clientSchemas.ts`
- **Mecanismo:** A função `extract()` recebe um schema Zod/Pydantic e uma flag `cache=True`. A biblioteca calcula um hash combinando a URL, a estrutura da página e a instrução. Em visitas subsequentes, se a página não sofreu drift estrutural, os dados são retornados instantaneamente da memória sem gastar chamadas de LLM.
- **Evidência nas sessões reais do Hermes:** Em `continuar-coleta-instagram-acirv-setembro-2026-20261002.json` e `sincronizar-descri-es-lote-piloto-acirv-no-trell-20260919.json`, o agente teve que emitir centenas de comandos `browser_console` com loops de scraping em JavaScript porque o Hermes não possuía uma ferramenta `browser_extract` com cache.

### 2.3. Resolução de Seletores e Locators Semânticos
- **Arquivo:** `packages/sdk-ts/src/locator.ts` e `packages/sdk-python/src/stagehand/locator.py`
- **Mecanismo:** O Stagehand encapsula seletores resilientes que cruzam atributos semânticos, texto visível e acessibilidade para encontrar elementos mesmo após pequenas alterações de classe CSS no front-end.

---

## 3. Mapa de Correspondência com o Hermes Work

| Mecanismo | Stagehand | Hermes Work | Veredito |
|---|---|---|---|
| Extração de Dados | `extract(instruction, schema)` nativo com schema tipado | Não possui primitivo; agente improvisa via `browser_console` | **Stagehand muito superior** |
| Execução em Lote | `experimentalBatch` agrupando ações | Ações estritamente atômicas com delay obrigatório por ação | **Stagehand superior** |
| Cache de Procedimentos | Cache baseado em hash de instrução + DOM | `OperationalKernel` e `ExperienceCompiler` (com ciclo de vida formal, verificação e quarentena) | **Hermes superior em autoridade e segurança** |
| Hospedagem de Navegador | Requer Browserbase na nuvem ou Playwright local | Chromium embutido nativo do Electron com `WebContentsView` | **Hermes superior** (Zero dependência externa) |

---

## 4. Análise de Licença e Requisitos de Portabilidade

- **Licença do Stagehand:** **Apache License 2.0**.
- **Licença do Hermes Agent:** **MIT**.
- **Compatibilidade:** Totalmente compatível. Código sob Apache 2.0 pode ser adaptado para o Hermes, desde que o arquivo de destino inclua o cabeçalho original de copyright da Browserbase Inc. e a menção no arquivo `THIRD_PARTY_NOTICES.md` do repositório.

---

## 5. Recomendações Objetivas para o Hermes Work

1. **Criar a ferramenta `browser_extract` adaptada do Stagehand (`ADAPT`):**
   Adicionar ao `tools/browser_workstation.py` e ao runtime do Electron um comando `browser_extract` que receba instrução e schema JSON para extrair coleções estruturadas da página em uma única chamada.
2. **Introduzir o conceito de Batch Execution no Controller:**
   Adaptar o padrão `experimentalBatch` para permitir ao agente enviar uma lista de 5 a 10 ações atômicas consecutivas no `browser_click` / `browser_type`.
3. **Preservar o OperationalKernel para quarentena:**
   O cache do Stagehand é otimista; o Hermes deve continuar usando seu `OperationalKernel` com contratos de verificação de pré/pós-condições para evitar execuções cegas.
