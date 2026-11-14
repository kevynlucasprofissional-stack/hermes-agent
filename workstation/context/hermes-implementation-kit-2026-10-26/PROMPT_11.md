# PROMPT 11 (OPCIONAL, NÃO PRIORITÁRIO) — Benchmark isolado do Moli

**Missão.** Responder experimentalmente se o navegador Moli merece ser backend **auxiliar**, sem substituir Chromium ou alterar Browser Workstation principal. Ler `tools/browser_lightpanda.py`, `tools/browser_tool_lightpanda_fallback.py`, `agent/browser_provider.py` e contratos de Browser nativo. Inspecionar licença/versionamento e instalar somente em sandbox reversível, com autorização, não globalmente.

**Etapas.** Criar benchmark idêntico em Chromium e Moli: páginas públicas/fixture e fluxo de DOM, HTML dinâmico, autenticação falsa local, upload falso, compatibilidade CDP, consumo CPU/RSS, latência, erros, falsas confirmações e cleanup. Proibir credenciais reais. Medir ganho total considerando falhas/retries. Emitir decisão `GO_EXPERIMENTAL` ou `NO_GO` documentada; integração de produção é tarefa posterior independente.

---

## Formato de entrega obrigatório para CADA prompt

Entregar ao final: (a) HEAD/branch/dirty inicial e final; (b) caminhos sob claim do agente e integrador dono de commit; (c) contrato/decisões e desvios justificados; (d) diffs por arquivo; (e) evidência RED + GREEN com comandos e exits; (f) validação nativa onde exigida; (g) segurança e riscos residuais; (h) Known Issues que continuam abertos; (i) atualização incremental do `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md` e `workstation/context/engineering-journal/CURRENT.md` somente pelo owner documental, ou handoff de inserts caso esses arquivos estejam claimed. Não chamar `DONE/RELEASE` para teste sintético ou código não integrado.
