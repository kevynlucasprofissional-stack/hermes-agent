# Relatório de Auditoria Code-to-Code: Browser-Memory

**Projeto:** Browser Memory (`browser-memory/browser-memory`)  
**Commit SHA:** `138d05d515a77ccde1865261d76395dc04cc51bc`  
**Branch:** `main`  
**Caminho Local:** `referências/02-Browser-Automacao-Web/browser-memory--browser-memory`  
**Licença:** **MIT** (`LICENSE`)  
**Stack:** TypeScript / Node.js  
**Tamanho Auditado:** 67 arquivos TS, 22 arquivos de teste  
**Classificação de Reuso:** **ADAPT** (Convergência natural com o Experience Compiler do Hermes)  

---

## 1. Identidade e Arquitetura

O `browser-memory` foi desenhado para resolver o problema clássico de repetição em agentes: em vez de fazer o agente navegar e raciocinar sobre a mesma interface web repetidas vezes, o sistema **observa os rastros de navegação bem-sucedidos (*traces*), destila procedimentos reutilizáveis e os armazena em uma memória de procedimentos operacionais**.

Sua arquitetura é dividida em:
1. `src/browser`: Instrumentação do navegador e captura de logs de rede/DOM (`bm-handler.ts`, `origin-lock.ts`).
2. `src/learn`: Destilação de sinais e síntese de procedimentos (`signal.ts`).
3. `src/memory`: Armazenamento indexado de procedimentos com linting de segurança (`store.ts`, `lint.ts`).
4. `src/runner`: Motor de execução de procedimentos compostos (`compose.ts`, `execute.ts`).

---

## 2. Mecanismos Relevantes Inspecionados

### 2.1. Destilação de Procedimentos a Partir de Rastros
- **Arquivo:** `src/learn/signal.ts` e `src/learn/distill-prompt.md`
- **Mecanismo:** Analisa a sequência de eventos de um rastro bruto (cliques, inputs, navegações), descarta passos intermediários de exploração falha ou tentativas e extrai a cadeia causal mínima necessária para atingir o objetivo.
- **Parametrização:** Identifica valores que devem ser transformados em variáveis (ex: termos de busca, credenciais, URLs de destino) versus valores que são invariantes estruturais da interface.

### 2.2. Trava de Origem e Segurança de Execução
- **Arquivo:** `src/browser/origin-lock.ts`
- **Mecanismo:** Garante que um procedimento compilado para um domínio específico (ex: `https://trello.com`) nunca possa vazar para outro domínio ou carregar scripts de origens não autorizadas durante a execução automática.

---

## 3. Comparação com o Hermes Work

O Hermes Work já possui o `ExperienceCompiler` e o `OperationalCapabilityRegistry`. No entanto, a extração de procedimentos no Hermes é altamente rigorosa e frequentemente exige confirmação de replay ou rejeita candidatos que não atingem fechamento operacional completo (`BOA-013`).

O `browser-memory` oferece um pipeline de destilação mais ágil e focado na web:
- Seu parser de sinais de rastro (`signal.ts`) pode ser adotado dentro do `ExperienceCorpus` do Hermes para pré-filtrar rastros da web antes de passá-los ao `ExperienceCompiler`.

---

## 4. Recomendações Objetivas

- **ADAPT:** Incorporar as regras de saneamento de rastro web de `signal.ts` e `origin-lock.ts` nos adaptadores de captura do Hermes Work (`workstation/experience_compiler/`), aumentando a taxa de sucesso de compilação de rotinas web recorrentes (como Trello e Instagram).
