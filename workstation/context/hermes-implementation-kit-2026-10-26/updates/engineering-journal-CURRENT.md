## 2026-10-26 — Planejamento 80/20 fundamentado em código local (PREPARED / NOT APPLIED)

**Missão:** transformar 15 oportunidades de Hermes Work em sequência de prompts independentes, com instruções técnicas e código de referência, mantendo autonomia crítica do implementador. Leitura direta via canal Windows existente, sem modificação do projeto. `Windows - Agent 01` confirmou agent_id `988402ea-d991-4f89-958f-82fc21882c43` e **somente** projeto autorizado `p0-mcp-isolation-20261026-3e1a4935`, logo os docs locais do Hermes não foram modificados por esse agente.

**Baseline observado:** `C:\Github\hermes-agent` branch `main`, HEAD `f1d5ab2f03`, remoto à frente `bafa3c43f4`; extensas alterações dirty/untracked no checkout Windows, particularmente Browser, Site Ops, WhatsApp e documentação. Claims de agentes devem ser verificados novamente antes de cada implementação.

**Evidência de código:** `workstation-browser-runtime.ts` contém `browser_file_upload` por `DOM.setFileInputFiles`; ausência dessa ação no Set `mutating` visto em trecho próximo exige gate de autoridade; `tools/browser_workstation.py` expõe a ferramenta; `tools/cronjob_tools.py::execute_job_for_event` existe; `workstation/events.py` possui pipeline in-memory, não journal de evento de negócio durável; `workstation/prefabs/trello.py` possui cliente REST e métodos de leitura; esquema `contacts/conversations/messages` em WhatsApp e `WA-M3-01` em HOLD; ASR/TTS e learning recorder já contam com módulos dedicados.

**Código preparado fora do repo:** `reference-code/trello_action_journal.py` + `reference-tests/test_trello_action_journal.py` (pytest 5/5 PASS em sandbox) e `reference-code/safe_upload_paths.mjs` + `reference-tests/test_safe_upload_paths.mjs` (node:test 5/5 PASS em sandbox). Tais testes só validam helpers isolados, **não** integração, segurança do Electron, Trello live ou qualificação do checkout.

**Decisão:** priorizar upload seguro → Trello action journal → Bot narrativo → adapter event/Cron → ASR/TTS → monitor MVP → gates WA-M3 e memória/demandas → replay supervisionado; Moli/EmbeddingGemma apenas por benchmark. Não abrir novo scheduler/banco de tarefas, não enviar mensagens, não criar branch, não tomar claims alheios, não assumir sucesso com provas sintéticas.

**Status:** `PLAN_PREPARED_EXTERNAL` / `NOT_APPLIED_TO_REPO` / `NOT_RELEASE_QUALIFIED`. Handoff: `PLANO_IMPLEMENTACAO.md` e `PROMPTS_IMPLEMENTADOR.md`; integração documental requer agente explicitamente autorizado ao projeto Hermes e claim do owner.
