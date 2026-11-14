# PROMPT 06 — MVP de monitoramento configurável de uma página sem IA em loop

**Missão.** Adicionar à Workstation o menor monitor de página reutilizável: configurar uma aba/elemento, observar alterações com limites e registrar evento, acionando o adaptador do prompt 04 quando regra autorizada corresponder. Não criar monitor universal de todas as origens no primeiro incremento.

**Preflight.** Exigir prompts 02/04 qualificados e claims Browser/UI. Ler `apps/desktop/electron/workstation-browser-dom-revision.ts`, `workstation-learning-dom.ts`, `workstation-browser-runtime.ts`, gerenciamento de BrowserTask/owner/lease, e UI de abas `apps/desktop/src/app/browser/`. Os `MutationObserver` atuais são para cache e efeitos locais, não monitor durável; não reutilizar listeners com ciclos de vida incompatíveis.

**Alterações.** (1) Contrato `PageWatchConfig{id,session_id,tab_id,origin,selector?,rule,route_id,enabled}` validado e persistido na store canônica de configuração, separadamente de estado de tarefas; (2) um observador por aba/origem, debounce, diff sem dados sensíveis, fingerprint estável, eventos tipados `page_changed` e periodic reconciler restrito; (3) UI `Ativar monitoramento` e painel pequeno com status, último evento, pausa, erro de autenticação; (4) módulo de ligação com outbox do prompt 04, sem invocar LLM para cada mutação; (5) desativação imediata em login/logout/navegação fora da origem, takeover humano e fechamento da aba. Persistir configuração, **não fingir persistência do observador quando aba está fechada**. Background capture é escopo futuro próprio.

**Testes.** RED para repaints, relógio/digitação (ruído), 2 observers concorrentes, DOM virtualizado, reload SPA, logout, mudança de origem, seleção de input sensível, logout+restart, aba fechada, travamento renderer, event duplicate; GREEN unitário + Electron Chromium real. Não capturar conversa/credencial de páginas arbitrárias nem inventar acessos ao WhatsApp.

**DONE.** Usuário ativa/desativa um monitor em página fixture, um evento é emitido com prova de origem e sem conteúdo privado, pausa/reconciliação funcionam, duplicatas suprimidas, sem alteração na autoridade de TaskRun e sem execução pós-logout. Documentar limites e exatamente o que deixa de funcionar com aba fechada.

---

## Formato de entrega obrigatório para CADA prompt

Entregar ao final: (a) HEAD/branch/dirty inicial e final; (b) caminhos sob claim do agente e integrador dono de commit; (c) contrato/decisões e desvios justificados; (d) diffs por arquivo; (e) evidência RED + GREEN com comandos e exits; (f) validação nativa onde exigida; (g) segurança e riscos residuais; (h) Known Issues que continuam abertos; (i) atualização incremental do `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md` e `workstation/context/engineering-journal/CURRENT.md` somente pelo owner documental, ou handoff de inserts caso esses arquivos estejam claimed. Não chamar `DONE/RELEASE` para teste sintético ou código não integrado.
