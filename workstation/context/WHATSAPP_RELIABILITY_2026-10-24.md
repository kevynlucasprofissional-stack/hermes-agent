# Hermes WhatsApp Workstation — contrato arquitetural WA-D1..D6 (2026-10-24)

**Estado:** decisão/documentação; implementação M1–M6 ainda NÃO qualificada. Não publicar dados pessoais, JSONs originais ou dumps de campanhas neste repositório público.

## Evidências que alteram o plano do Antigravity
- JSON de reunião examinado: 12/12 telefones completos. JSON original da oficina de 23/10: 17/17 telefones completos. A saída de `read_file` na mensagem 12 de `abrir-aplicativo-whatsapp-2-20261023.json` mascarou 17/17. Causa reproduzida: `agent/redact.py::_SIGNAL_PHONE_RE/_redact_phone` + `tools/file_tools.py` aplicando `redact_sensitive_text(file_read=True)`. **O arquivo não foi corrompido.**
- `enviar-convites-de-oficina-via-wa.me-20261023.json`: 365 mensagens de sessão, 156 tool calls, 101 `browser_console`. Não há medição equivalente de tokens/latência.
- Na HEAD remota de 24/10, `workstation/integrations/hermes/whatsapp_browser_executor.py` **já implementa** estados `PREPARED/DISPATCHING/OBSERVED/CONFIRMED/UNCERTAIN/FAILED/REVIEW_REQUIRED`, detecção de popup inválido e persistência. Evitar reescrever essas funções.
- Lacunas ainda visíveis nesse executor: fallback `get_default_db_path` hardcoded para ACIRV e outro DB se ausente; tabela `whatsapp_send_logs` armazena números e mensagens integrais; `_extract_delivery_evidence` pode reconhecer bolha anterior; `verify_delivery=False` assume composer vazio; erro pós-clique é marcado FAILED mesmo se o efeito puder ter ocorrido; persistência best-effort após efeito.
- `site-ops/scripts/site-ops/whatsapp-web.mjs` seleciona primeiro resultado de busca e envia sem prova de efeito; não operar como segundo dispatcher CDP independente do Browser autorizado.
- Browser nativo tem admissão/recuperação em `apps/desktop/electron/workstation-browser-runtime.ts` e `workstation-browser-session-state.ts` (`pendingBrowserMutation`, `recordPreEffectTerminal`); relato de 200 entradas `runId=unbound` em 23/10 é evidência histórica a revalidar na HEAD.
- O banco local `ACIRV-Notebook/.../Controle WhatsApp/whatsapp_control.db` já contém `contacts`, `conversations`, `messages`, `campaigns`, `campaign_enrollments`, `campaign_messages`, `campaign_sends`, com UNIQUE (`campaign_id,contact_id,campaign_message_id`) em `campaign_sends`. No exame local: 87 contatos, 70 conversas, 22 inscrições, 107 registros de envio. Não duplicar a base, e UNIQUE por passo não é histórico de tentativas.

## Decisões
**WA-D1 — Separar dado para execução de dado para o modelo.** Preservar redaction upstream global e `security.redact_secrets`. LLM recebe `contact_id`/`enrollment_id`, rótulo seguro e telefone parcialmente oculto. Executor confiável consulta o telefone completo em fonte autorizada após gates de TaskRun, scope, provenance, consentimento e permissão. Número original não volta no tool result, log nem telemetria. Não tentar reconstruir `****`, nem adivinhar DDD.

**WA-D2 — Um único dono do efeito.** Aproveitar a primitiva Python existente e o Browser nativo com leases/admission; `site-ops` vira mapa/selector/adapter, não rota de envio sem controle. Identidade por telefone/ID verificável, nunca primeiro homônimo.

**WA-D3 — Estados causais.** Clique ≠ envio observado ≠ entregue ≠ lido. Prova deve correlacionar um novo ID de mensagem com alvo, direção, conteúdo/digest e snapshot anterior. Sem provas = `UNCERTAIN`; exceção após dispatch não vira `NOT_DISPATCHED`. Não prometer exactly-once na rede.

**WA-D4 — Fonte de verdade por domínio.** Ledger Browser continua owner da admissão; banco relacional existente é owner das campanhas. Tabela auxiliar de tentativas, se necessária, deve ficar no mesmo DB, vinculada por `campaign_send_id` e `operation_id`. Sem `whatsapp_control.db` paralelo e sem fallback silencioso.

**WA-D5 — Segurança e conformidade.** Dry-run default, preview e aprovação vinculados a fingerprint de destinatários/corpos/anexos/etapas; respeitar opt-in e permissões, que check-in não implica. Rate limit é controle operacional, não mecanismo garantido de anti-ban. Para envios comerciais em escala, avaliar API oficial.

**WA-D6 — Alteração mínima upstream-first.** Manter compatibilidade de fork; não editar `agent/redact.py` sem demonstração da necessidade e testes amplos. Respeitar `AGENTS.md`, H-079 Stage A, branch/claims reais e CI exata. Sem envios reais na qualificação automática.

## Sequência de implementação
M1 (P0): resolução privada de contatos e redaction lossless. M2 (P0): identidade TaskRun e reconciliação Browser. M3 (P1): confirmação de envio unitário e persistência causal. M4 (P1): fila, idempotência, aprovação, pausa, retry seguro. M5 (P2): leitura incremental com sync ao DB. M6 (P2): anexos e dogfood/E2E + métricas.

**HOLD:** não aumentar volume até M1–M3 estarem GREEN. [Prompts executáveis](WHATSAPP_IMPLEMENTER_PROMPTS_2026-10-24.md) · [Código de referência](WHATSAPP_REFERENCE_PATCHES_2026-10-24.md) · [Jornal](engineering-journal/whatsapp-privacy-incident-2026-10-24.md).
