# Relatório de Auditoria Code-to-Code: Upstream Baseline (NousResearch/hermes-agent)

**Projeto:** Hermes Agent Upstream Baseline (`NousResearch/hermes-agent`)  
**Commit SHA:** `6a2662a4aaad68e1b75f6e7ac789409aa653abf7`  
**Branch:** `main`  
**Caminho Local:** `referências/02-Browser-Automacao-Web/NousResearch--hermes-agent`  
**Licença:** **MIT** (`LICENSE`)  
**Papel no Estudo:** **BASELINE UPSTREAM CANÔNICA** para isolar o que é núcleo oficial do que é delta do Hermes Workstation.  

---

## 1. O que o Upstream Oficial Fornece

No upstream oficial do `hermes-agent` (`main@6a2662a4aa`), o subsistema Browser compreende:
1. `tools/browser_tool.py` (1.538 linhas):
   - Motor baseado em **Playwright externo**.
   - Conexão com instâncias locais do Chromium ou endpoints remotos CDP na nuvem (Browserbase, Steel, Browserless).
   - Suporte a modo stealth via Camofox (`tools/browser_camofox.py`).
   - Ferramentas elementares: `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_press`, `browser_scroll`, `browser_back`, `browser_console`, `browser_vision`, `browser_get_images`.
2. `tools/browser_tool_cdp.py` e `tools/browser_cdp_tool.py`:
   - Conexão WebSocket direta para inspecionar e manipular instâncias remotas via CDP.
3. `gateway/browser_control_broker.py` e `tools/browser_extension_router.py`:
   - Broker agnóstico para conectar o agente a instâncias externas (como extensões Chrome).

---

## 2. O Delta do Hermes Workstation (Downstream)

O Hermes Work downstream não descartou o upstream; ele construiu uma camada de produto de primeira classe sobre ele:
1. **Chromium Embutido no Electron:** Em vez de depender do Playwright iniciando um processo filho de Chrome no sistema operacional, o Workstation hospeda abas em `WebContentsView` dentro da janela do Desktop.
2. **Ciclo de Vida de Tarefa e Abas:** `BrowserTask` vincula abas a tarefas específicas de agentes e Kanban, garantindo que o agente navegue em segundo plano sem tomar a tela do usuário.
3. **Throttling de Fundo:** Redução de taxa de quadros para 6 fps em abas não-visíveis, economizando CPU/GPU.
4. **Recuperação e Persistência:** Recuperação do estado de abas e tarefas após restart do app em modo parked/lazy.
5. **Lease de Controle Humano:** Proteção contra mutações do agente quando o humano assume a navegação (Take Control / `409 USER_CONTROL_ACTIVE`).
6. **Controle Operacional Verificado:** O `OperationalKernel` e o `ExperienceCompiler` fecham o ciclo de execução determinística e aprendizagem procedural.

---

## 3. Conclusão da Comparação com o Upstream

O upstream oficial fornece os contratos e as abstrações de ferramentas genéricas. A Workstation fornece o runtime nativo de alta performance para Desktop e o plano de controle operacional.

A integridade do portão upstream-first (H-079) exige que novas capacidades de browser desenvolvidas na Workstation (como `browser_batch_actions` e `browser_extract`) sejam projetadas como extensões compatíveis com o broker genérico do upstream, evitando acoplamento desnecessário no core do Hermes.
