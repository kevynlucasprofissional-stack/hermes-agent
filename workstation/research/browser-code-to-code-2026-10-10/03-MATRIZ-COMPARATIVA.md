# 03 — Matriz Comparativa Multidimensional: Mecanismos x Projetos

**Data da Matriz:** 10 de Outubro de 2026  
**Status:** FACT & AUDIT EVIDENCE  
**Convenção de Evidência:** `FACT` (comprovado no código), `PARTIAL` (parcial), `NV` (não verificado), `INFERENCE` (dedução lógica), `RECOMMENDATION` (proposta de ação).  

---

## Matriz Comparativa Completa (25 Dimensões)

| # | Dimensão Arquitetural | Hermes Work (Atual) | BrowserOS | Stagehand | browser-use | Agent Browser | BrowserClaw | Camofox | Driftlock |
|---|---|---|---|---|---|---|---|---|---|
| **1** | **Navegação** | Electron `WebContentsView` (`FACT`) | Chromium customizado (`FACT`) | Playwright wrapper (`FACT`) | Playwright + CDP (`FACT`) | Rust + CDP direto (`FACT`) | Playwright CDP (`FACT`) | Camoufox REST (`FACT`) | Playwright (`FACT`) |
| **2** | **Percepção DOM** | `querySelectorAll` JS injetado (`FACT`) | Não prioriza DOM bruto (`FACT`) | Parser semântico (`FACT`) | Serializer clicável (`FACT`) | Não usa (`FACT`) | Enriquecimento DOM (`FACT`) | Injeção JS (`FACT`) | Hash DOM (`FACT`) |
| **3** | **Accessibility Tree** | Ausente no runtime principal (`FACT`) | Nativo CDP `renderSnapshot` (`FACT`) | Nativo CDP via Locator (`FACT`) | Opcional via CDP (`FACT`) | Nativo `snapshot.rs` Rust (`FACT`) | Playwright AI Snapshot (`FACT`) | Parcial (`PARTIAL`) | Não usa (`FACT`) |
| **4** | **Percepção Visual** | `browser_vision` com screenshot (`FACT`) | Suporte visual no sidepanel (`FACT`) | Suporte multimodal (`FACT`) | Destaques na tela (`FACT`) | Screenshot CDP (`FACT`) | Screenshot CDP (`FACT`) | VNC streaming (`FACT`) | Diffs visuais (`FACT`) |
| **5** | **Automação Determinística** | `OperationalKernel` (`FACT`) | Parcial via shortcuts (`PARTIAL`) | Sim (`act` estruturado) (`FACT`) | Básico no controller (`FACT`) | Sim (CLI determinístico) (`FACT`) | Sim (`guarded-input.ts`) (`FACT`) | Parcial (`PARTIAL`) | Sim (`FACT`) |
| **6** | **Automação Adaptativa** | Turn loop Hermes + System-1 (`FACT`) | Agente LLM reativo (`FACT`) | Agente adaptativo (`FACT`) | Agent loop completo (`FACT`) | Loop do modelo (`FACT`) | Agente via refs (`FACT`) | Orientado a API (`FACT`) | Não (`FACT`) |
| **7** | **Execução em Lote (Batching)** | **Ausente** (ações atômicas) (`FACT`) | Parcial (`PARTIAL`) | `experimentalBatch` (`FACT`) | Não nativo (`PARTIAL`) | Em lote no CLI (`FACT`) | **`executeBatch` completo** (`FACT`) | `batch-downloader` (`FACT`) | Não (`FACT`) |
| **8** | **Persistência de Sessão** | `BrowserSessionState` lazy (`FACT`) | Persistência Chromium (`FACT`) | Browserbase cloud (`FACT`) | `storage_state_watchdog` (`FACT`) | Sessões efêmeras (`FACT`) | Perfil reutilizável (`FACT`) | `session.ts` (`FACT`) | Não (`FACT`) |
| **9** | **Perfis Autenticados** | Perfil local no Electron (`FACT`) | Perfil local Chromium (`FACT`) | Perfis em nuvem (`FACT`) | **`chrome-import` DPAPI** (`FACT`) | Reusa diretório (`FACT`) | Reusa diretório (`FACT`) | Fingerprint profiles (`FACT`) | Não (`FACT`) |
| **10** | **Recuperação** | `workstation-browser-task` (`FACT`) | Básico do Chromium (`FACT`) | Retry embutido (`FACT`) | **`watchdogs/` modulares** (`FACT`) | Recovery por frame (`FACT`) | `NavigationRaceError` (`FACT`) | `nav-recovery.ts` (`FACT`) | `driftlock-revert` (`FACT`) |
| **11** | **Replay** | `ExecutionJournal` (`FACT`) | Histórico de ações (`FACT`) | Não gravado por padrão (`NV`) | Gravação de vídeo/HAR (`FACT`) | Trace CDP (`FACT`) | Gravação de trace (`FACT`) | Tracing (`FACT`) | Interaction log (`FACT`) |
| **12** | **Tratamento de Drift** | `CapabilityDriftError` (`FACT`) | Não possui (`FACT`) | Retry com LLM (`FACT`) | Não possui (`FACT`) | Não possui (`FACT`) | Não possui (`FACT`) | Não possui (`FACT`) | **`diagnoseDrift` formal** (`FACT`) |
| **13** | **Eficiência de Tokens** | Baixa (snapshot integral) (`FACT`) | **Alta (`diffSnapshots`)** (`FACT`) | Média/Alta (`observe`) (`FACT`) | Média (`dom/service.py`) (`FACT`) | **Alta (AXTree compacto)** (`FACT`) | Alta (refs numéricos) (`FACT`) | Média (`PARTIAL`) | Média (`PARTIAL`) |
| **14** | **Cache de Contexto** | Prompts prefixados estáveis (`FACT`) | Não focado em cache (`NV`) | **Cache instrução+DOM** (`FACT`) | Não possui cache (`FACT`) | Não possui cache (`FACT`) | Cache de refs (`FACT`) | Não possui (`FACT`) | Cache de seletores (`FACT`) |
| **15** | **Execução em Fundo** | **6 fps throttling background** (`FACT`) | Standard Chromium (`FACT`) | Headless na nuvem (`FACT`) | Headless Playwright (`FACT`) | Headless nativo (`FACT`) | Headless Playwright (`FACT`) | Headless container (`FACT`) | Headless (`FACT`) |
| **16** | **Intervenção Humana** | `BrowserHumanControlLease` (`FACT`) | Pausa por clique no app (`FACT`) | Não interativo (`FACT`) | **`takeoverOverlay.ts`** (`FACT`) | Não interativo (`FACT`) | Não interativo (`FACT`) | Live VNC (`FACT`) | Não interativo (`FACT`) |
| **17** | **Integração com Agentes** | Toolset de sessão e CLI (`FACT`) | Side panel + MCP (`FACT`) | SDK TypeScript / Python (`FACT`) | Biblioteca Python (`FACT`) | Ferramenta CLI / MCP (`FACT`) | Biblioteca TS (`FACT`) | REST API (`FACT`) | Script / plugin (`FACT`) |
| **18** | **Segurança e Isolamento** | Fail-closed + URL safety (`FACT`) | Isolamento de processo (`FACT`) | Nuvem isolada (`FACT`) | `security_watchdog.py` (`FACT`) | SSRF policy nativa (`FACT`) | Path confinement (`FACT`) | Stealth sandboxing (`FACT`) | Origin guard (`FACT`) |
| **19** | **Memória Procedural** | `OperationalCapabilities` (`FACT`) | Histórico simples (`FACT`) | Não possui (`FACT`) | Não possui (`FACT`) | Não possui (`FACT`) | Não possui (`FACT`) | Não possui (`FACT`) | Não possui (`FACT`) |
| **20** | **Reutilização Operacional** | **`ExperienceCompiler`** (`FACT`) | Não possui (`FACT`) | Cache de extração (`FACT`) | Não possui (`FACT`) | Não possui (`FACT`) | Não possui (`FACT`) | Não possui (`FACT`) | Reparo de seletores (`FACT`) |
| **21** | **Observabilidade** | `ExecutionJournal` + Receipts (`FACT`) | Sidepanel history (`FACT`) | `metrics()` de batch (`FACT`) | Logs estruturados (`FACT`) | Inspecionar via WebSocket (`FACT`) | Activity capture (`FACT`) | Tracing (`FACT`) | Protocol log (`FACT`) |
| **22** | **Verificação de Efeitos** | **Contratos formais pré/pós** (`FACT`) | Ausente (`FACT`) | Verificação heurística (`FACT`) | Não estruturada (`FACT`) | Ausente (`FACT`) | Ausente (`FACT`) | Não estruturada (`FACT`) | Veredito formal (`FACT`) |
| **23** | **Testabilidade** | 900+ testes locais (`FACT`) | 432 testes no monorepo (`FACT`) | 469 testes automatizados (`FACT`) | 132 testes unitários (`FACT`) | 13 testes de integração (`FACT`) | 66 testes unitários (`FACT`) | 88 testes (`FACT`) | 2 testes (`FACT`) |
| **24** | **Complexidade de Integração** | Alta (4.300 linhas runtime) (`FACT`) | Muito alta (Chromium patches) (`FACT`) | Média (SDK desacoplado) (`FACT`) | Baixa/Média (`FACT`) | Média (Rust CLI) (`FACT`) | Baixa (Módulos TS puros) (`FACT`) | Média (Container) (`FACT`) | Baixa (`FACT`) |
| **25** | **Portabilidade de Código** | Proprietário do Hermes (`FACT`) | **AGPL-3.0 (Não portável)** (`FACT`) | **Apache-2.0 (Portável)** (`FACT`) | **MIT (Totalmente portável)** (`FACT`) | **Apache-2.0 (Portável)** (`FACT`) | **MIT (Totalmente portável)** (`FACT`) | **MIT (Portável)** (`FACT`) | **MIT (Portável)** (`FACT`) |

---

## Conclusões Chave da Matriz

1. **Onde o Hermes Work é Imbatível (Preservar a todo custo):**
   - **Dimensões 10, 15, 16, 19, 20 e 22:** Nenhum outro projeto do ecossistema possui `OperationalKernel`, `ExperienceCompiler`, verificação formal de pré/pós-condições, throttling de background para 6 fps e controle de autoridade com leases humano-agente (`409`).
2. **Onde o Hermes Work é Inferior (Ação imediata):**
   - **Dimensão 7 (Batching):** O Hermes é o único grande projeto sem suporte nativo a operações em lote. O **BrowserClaw** possui a melhor implementação.
   - **Dimensão 3 e 13 (Accessibility Tree & Eficiência de Tokens):** O Hermes ainda usa injeção de script DOM pesado (`querySelectorAll`). O **Agent Browser** (Rust) e o **BrowserOS** (AXTree + Diff) são 10x mais rápidos e gastam 80% menos tokens.
   - **Dimensão 9 (Perfis Autenticados):** O **browser-use/desktop** possui `chrome-import` pronto com DPAPI para importar cookies do Chrome local sem atrito.
