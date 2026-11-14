# PROMPT 10 — Homologar replay supervisionado do Modo Aprender sem autopromoção

**Missão.** Fechar somente o gate de execução supervisionada de candidatas do Modo Aprender. Reaproveitar observadores DOM, gravador, question engine e Experience Compiler existentes.

**Preflight.** Ler `workstation/context/CURRENT_STATE.md` P02/P03/P04/P05, `KNOWN_ISSUES.md` HLM-KI-06, `apps/desktop/electron/workstation-learning-session.ts`, `workstation-learning-segmenter.ts`, `workstation/skill_learning.py`, lifecycle TaskRun e testes já existentes. Claims separados dos owners do runtime Browser/WhatsApp; se chocarem, estacionar o trabalho.

**Implementação.** TDD RED da promoção indevida: CandidateLesson de demonstração sem `VERIFIED_SUCCESS` nunca passa a capacidade ativa. Implementar percurso supervisionado explícito: seleciona candidato → autorização humana contextual → TaskRun com session/tab/owner → execução em fixture → readback independente e receipt → qualificar somente se critérios verificáveis forem atingidos. Falha, mudança de origem ou tomada humana resultam em HOLD e trilha de evidências, sem forjar etapas do chat.

**DONE.** Replay em Electron Chromium com artefato real e verificação independente; testes de fracasso/restart/duplicidade; nenhuma aprendizagem promovida por mera observação. Documentar captura e gate do recorder FFmpeg separadamente da validação de replay.

---

## Formato de entrega obrigatório para CADA prompt

Entregar ao final: (a) HEAD/branch/dirty inicial e final; (b) caminhos sob claim do agente e integrador dono de commit; (c) contrato/decisões e desvios justificados; (d) diffs por arquivo; (e) evidência RED + GREEN com comandos e exits; (f) validação nativa onde exigida; (g) segurança e riscos residuais; (h) Known Issues que continuam abertos; (i) atualização incremental do `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md` e `workstation/context/engineering-journal/CURRENT.md` somente pelo owner documental, ou handoff de inserts caso esses arquivos estejam claimed. Não chamar `DONE/RELEASE` para teste sintético ou código não integrado.
