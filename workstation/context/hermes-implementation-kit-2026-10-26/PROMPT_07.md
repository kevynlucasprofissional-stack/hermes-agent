# PROMPT 07 — Fechar o bloqueio WA-M3 de evidência nativa (não habilitar envios)

**Missão.** Concluir a qualificação da prova de identidade da conversa/destinatário e ACK no WhatsApp Browser nativo, SEM envio de mensagens reais nem relaxamento dos controles.

**Preflight.** Confirmar expressamente ownership de caminhos WA-M3 e liberar claims anteriores por owner — não roubar claim. Ler `workstation/context/WHATSAPP_RELIABILITY_2026-10-24.md`, `WHATSAPP_IMPLEMENTER_PROMPTS_2026-10-24.md`, `KNOWN_ISSUES.md` `WA-M3-01`, `workstation/integrations/hermes/whatsapp_browser_executor.py`, `site-ops/scripts/site-ops/whatsapp-web.mjs`, `apps/desktop/electron/workstation-browser-runtime.ts` e `tests/tools/test_whatsapp_browser_tools.py`. M1/M2 locais devem ser preservados.

**Correção proposta.** (1) TDD RED: snapshot nativo não apresenta `data-chat-id`, `data-recipient-id`, `data-direction`, `data-ack` comprováveis; casos homônimo, bolha antiga, `msg-meta` avulso, composer vazio, click sem receipt e recibo com `run_id` incompatível devem bloquear prova; (2) projetar metadados mínimos DOM autorizados, tipados e somente leitura no runtime nativo ou adaptar verificadores a evidência genuinamente disponível — não inventar atributos no JavaScript; (3) garantir base de saída antes do click, nova mensagem após click, identidade exata, digest de conteúdo e ACK da mesma mensagem; (4) estado pós-dispatch ambíguo → `UNCERTAIN`, sem segundo clique/retry automático; (5) verificar snapshot real **sem enviar** e testes negativos comparando identidades/sessões.

**DONE.** E2E readback real do Browser demonstra origem e atributos válidos (ou registra HOLD sem inventar sucesso); testes nativos admission/recovery + Python WA focados verdes, preservação PII e políticas auditadas. M4–M6 permanecem HOLD até gate completo, mesmo que sintéticos passem. O integrador, não o agente, decide enviar teste real a número explicitamente autorizado.

---

## Formato de entrega obrigatório para CADA prompt

Entregar ao final: (a) HEAD/branch/dirty inicial e final; (b) caminhos sob claim do agente e integrador dono de commit; (c) contrato/decisões e desvios justificados; (d) diffs por arquivo; (e) evidência RED + GREEN com comandos e exits; (f) validação nativa onde exigida; (g) segurança e riscos residuais; (h) Known Issues que continuam abertos; (i) atualização incremental do `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md` e `workstation/context/engineering-journal/CURRENT.md` somente pelo owner documental, ou handoff de inserts caso esses arquivos estejam claimed. Não chamar `DONE/RELEASE` para teste sintético ou código não integrado.
