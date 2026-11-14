# PROMPT 08 — Memória semântica do WhatsApp com evidência e sem duplicar mensagens

**Missão.** Construir projeção semântica por contato a partir do histórico WhatsApp Control autorizado, sem criar outro banco de contatos e sem transformar hipóteses em fatos.

**Preflight.** Depende de WA-M3 qualificado para efeitos externos; para leitura/rascunho pode avançar isoladamente se o owner aprovar, sem alterar o executor M3. Ler schema `contacts/conversations/messages` e `persist_read_messages` em `workstation/integrations/hermes/whatsapp_browser_executor.py`, política de privacidade e de identidade de contatos. Claim exclusivo sobre migrations de memória e novos módulos.

**Alterações.** (1) Criar projeção/versionamento de `contact_memory_fact` na mesma base autorizada, com `contact_id`, `fact_key`, `value` minimizado, `source_message_id`, `confidence`, `status={hypothesis,confirmed,retracted}`, `updated_at` e `expires_at`; `source_message_id` deve referenciar mensagem efetivamente persistida; (2) janela recente das últimas 30 mensagens deve ser **consulta**, nunca duplicação de material bruto; (3) extrator LLM somente para novidades semanticamente relevantes, produzindo candidatos inertes para revisão quando ambíguos; (4) reconciliação por versões/contradições (retract/supersede), retenção privada, classificação por origem autorizada; (5) logs sem conteúdo bruto e sem PII.

**Testes/aceite.** Duas capturas da mesma mensagem não duplicam fatos; conflito entre mensagens preserva evidências e gera revisão; identidade inexistente não une contatos por homônimo; mensagem apagada/retenção expirada invalida projeções conforme política; restore reconstruível. Não enviar nada a terceiros. Registrar testes, migração, política de retenção e posição das novas tabelas no modelo canônico.

---

## Formato de entrega obrigatório para CADA prompt

Entregar ao final: (a) HEAD/branch/dirty inicial e final; (b) caminhos sob claim do agente e integrador dono de commit; (c) contrato/decisões e desvios justificados; (d) diffs por arquivo; (e) evidência RED + GREEN com comandos e exits; (f) validação nativa onde exigida; (g) segurança e riscos residuais; (h) Known Issues que continuam abertos; (i) atualização incremental do `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md` e `workstation/context/engineering-journal/CURRENT.md` somente pelo owner documental, ou handoff de inserts caso esses arquivos estejam claimed. Não chamar `DONE/RELEASE` para teste sintético ou código não integrado.
