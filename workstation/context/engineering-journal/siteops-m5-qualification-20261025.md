# Site Ops M5 — Qualificação focal e gate pendente (2026-10-25)

## Checkout / ownership

- Checkout: `C:\Github\hermes-agent`; branch `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e`, origin/main local `bafa3c43f4ecf7953e377e29cca6515089e530fe`.
- Worktree compartilhada e suja; nenhum reset, stash, switch, stage, commit, push, envio ou CDP real.
- Preservados os seis arquivos locais da M5 e claims `chatgpt-siteops-contract`, `chatgpt-siteops-sim`, `chatgpt-siteops-docs`, todos READY_FOR_INTEGRATION.
- O agente `chatgpt-whatsapp-m3` possui ownership ativo sobre `tools/browser_workstation.py`, `workstation/integrations/hermes/whatsapp_browser_executor.py` e `workstation/tests/test_whatsapp_browser_executor.py`. `chatgpt-whatsapp-m3-compat` possui `workstation/tests/test_whatsapp_recipient_resolution.py`. NÃO sobrescrever.

## Mudanças nesta continuação (desacopladas do M3)

- `apps/desktop/electron/workstation-browser-runtime-admission.test.ts`: mock Electron recebe `app.getAppPath` e `FakeWebContents.ipc.on`.
- `apps/desktop/electron/workstation-browser-runtime-recovery.test.ts`: mesmas interfaces de mock para o runtime atual.
- `workstation/tests/test_siteops_composer_preflight_contract.py`: caso totalmente sintético `strict xfail` que prova lacuna no pré-dispatch: identidade correta + texto do composer diferente -> executor chama `browser_click`. A proteção ainda não está implementada. Remover xfail só após GREEN legítimo.

## Evidência observada

- Testes Python canônicos (`scripts/run_tests.sh`) sobre cinco arquivos (executor, TaskRun, M5, recipient, metrics): 95 PASS, 1 FAIL. Falha exata: `test_reference_to_wrapper_keeps_private_inputs_internal` em `workstation/tests/test_whatsapp_recipient_resolution.py`: KeyError `db_path` na saída capturada do wrapper. Encaminhar ao owner; não inferir correção sem reconciliar fonte confiável de DB e política do perfil.
- Vitest Browser admission/recovery: 1/6 antes da correção dos mocks; 6/6 depois. Erros anteriores: `app.getAppPath is not a function` e `wc.ipc.on` indefinido.
- Vitest combinado (Site Ops P0 + gates + Browser recovery/admission): 22/22 PASS, 5 arquivos. Simulação Python M5: 3/3 PASS já documentada.
- Pré-dispatch: 1 xfail esperado (`test_wrong_composer_text_cannot_dispatch_even_with_correct_recipient`), NÃO é PASS técnico. O runtime real pode exigir extensão de snapshot/readback autorizado para comprovar conteúdo; não usar CDP por fora.
- Nenhum dado de tokens LLM, latência de WhatsApp real, CI ou native Chrome/WhatsApp: indisponíveis. Sem efeitos externos.

## Único gate prioritário

Sob ownership do M3: validar readback do compositor na superfície Browser autorizada ANTES de `browser_click`; texto precisa ser comparável ao request (normalização explícita, sem falso positivo), com identidade de destinatário já comprovada e vínculo de TaskRun/operation_id persistido. Se ausente ou ambíguo: fail closed como REVIEW_REQUIRED (ou estado equivalente por contrato), zero dispatch; após dispatch incerto, manter UNCERTAIN sem retry. Preservar reserva durável anterior ao primeiro efeito, ACK correlacionado apenas ao novo outbound e isolamento/redaction.

Após coordenação: alterar executor/mock autorizado, transformar o strict xfail em teste normal GREEN, refazer 5 testes Python + Browser admission/recovery e runner nativo; revisar a falha db_path pelo owner compat. Stage A está dispensado somente para desenvolvimento local conforme CURRENT_STATE.md; sem qualificação de release, merge ou CI alegados.
