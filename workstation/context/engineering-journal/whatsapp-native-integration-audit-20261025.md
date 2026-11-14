# Hermes WhatsApp — checkpoint de integração nativa, 2026-10-25

**HOLD: somente auditoria/RED; NÃO qualificado. Sem runtime editado, sem envio real, sem acesso de escrita ao DB de produção.**

## Checkout
- `C:\Github\hermes-agent`, `main@f1d5ab2f030e940ed4571371b0de45a21a009c9e`.
- `origin/main@bafa3c43f4` (checkout 1 commit atrás).
- `upstream/main` observado via `git ls-remote`: `4ea8d23cc9f527332ccb1d55359b27741b6ea51b`.
- Baseline upstream/Stage A/CI exact-head não qualificado aqui; sem exceção explícita para este trabalho. Não foi feito fetch/merge/pull/reset/stash/commit.
- Alterações locais substanciais anteriores em `tools/browser_workstation.py`, `tools/browser_tool.py`, `whatsapp_browser_executor.py`, `model_tools.py`, Electron e testes. Claim independente `site-ops-migration`: não editar `apps/desktop/scripts/site-ops`.

## Achados reproduzidos
1. O catálogo registra `whatsapp_send_message`, mas `registry.get_toolset_for_tool` retorna `None` para `whatsapp_read_messages` e `whatsapp_batch_preview`; wrappers sozinhos não expõem capacidades ao agente.
2. `whatsapp_batch_preview` devolve números completos e registros integrais; não ligar à LLM diretamente sem sanitização/refs seguras.
3. `whatsapp_batch_approve` emite token ativo com parâmetro de texto `approved_by`; sem comprovação humana nessa função. Não disponibilizar autoaprovação à LLM.
4. `workstation-browser-task.ts::bindRun` recusa nova run para BrowserTask já vinculado. `tools/browser_workstation.py::_dispatch` gera `effective_rid=rid or session_id` para sessão: causa plausível do mismatch cross-turn; não remover fence para contornar.
5. Prova de envio M3 aceita bolha antiga, alvo/corpo/direção inválidos e ACK genérico; pós-clique incerto marcado FAILED em vez de UNCERTAIN.

## Testes e próximos gates
- GREEN: `python -m pytest workstation/tests/test_whatsapp_taskrun_binding.py workstation/tests/test_whatsapp_recipient_resolution.py tests/tools/test_whatsapp_browser_tools.py -q -p no:cacheprovider` → **64 passed**.
- RED existentes: `python -m pytest workstation/tests/test_whatsapp_batch_executor.py workstation/tests/test_whatsapp_metrics.py workstation/tests/test_whatsapp_browser_executor.py -q -p no:cacheprovider` → **8 failures M3** (bolha antiga/errada/dupla, pós-clique incerto, compositor presumido vazio, persistência antes do clique).
- RED confirmado: `python -m pytest tests/tools/test_whatsapp_native_catalog_regression.py -q -p no:cacheprovider --tb=line` → **3 failed em 42.67s**: `test_native_read_and_preview_are_registered_in_agent_catalog`, `test_batch_preview_never_exposes_raw_phone_to_model`, `test_batch_token_cannot_be_minted_by_unverified_operator_string`. Todos com fixtures sintéticos e DB temporário; testes isolados deliberadamente RED.
- E2E agent-driven real pelo chat Hermes **NÃO EXECUTADO**. Sem certificados.

**Próxima ação única:** fechar Stage A ou registrar autorização explícita, depois implementar interfaces seguras de descoberta `whatsapp_read_messages`/`whatsapp_batch_preview` (refs e egress sanitizado) e tornar RED->GREEN; corrigir M3 e continuidade cross-turn antes de testes pelo chat nativo. Sem CDP externo, sem alterar controles nem usar dados reais como fixture.
