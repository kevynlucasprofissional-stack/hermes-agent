# WA-OPC-011 — Real canary, fase 1 (somente leitura)

**Situação:** teste preparado em 11/11/2026; **não executado pelo agente Hermes ainda**. O teste não habilita disparos.

## Resultado necessário

Com o Hermes Work Desktop, iniciar uma BrowserTask **nova e da própria sessão**, entrar em `https://web.whatsapp.com/`, abrir exclusivamente a conversa **consigo mesmo** ("Você"/"You"/"Mensagens para você", após identidade inequívoca), e executar a sonda nativa de metadados. Registrar `status`/`reason` do resultado e o número de chamadas ao modelo/ferramentas se observável. **Não abrir conversas de terceiros, não enviar mensagens, não modificar contatos, campanhas, banco ou código.**

## Ambiente preparado e evidência anterior

- Checkout: `C:\Github\hermes-agent`, branch `main`, HEAD inicial `f1d5ab2f030e940ed4571371b0de45a21a009c9e`. Compartilhado e com centenas de alterações preexistentes; não executar `git reset/clean/stash`, commit, push, restart ou troca de branch.
- Runtime: Hermes Desktop com `aiControl=true`, backend `desktop` e Browser Hub `electron-chromium` saudável no preflight. Antes de usar, revalidar `node apps/desktop/scripts/hermes-nav.mjs status`.
- Sonda de produção `workstation/integrations/hermes/whatsapp_native_schema_probe.py`, teste `workstation/tests/test_whatsapp_native_schema_probe.py` (6 casos). CLI de dogfood `workstation/scripts/wa_opc011_canary_readonly.py`, 4 testes em `workstation/tests/test_wa_opc011_canary_cli.py`.
- **Validação já realizada do comando CLI com BrowserTask temporária:** `browser_navigate` retornou `success=true, runtime=electron-chromium`; `python -m workstation.scripts.wa_opc011_canary_readonly --task-id wa-opc011-preflight-20261111 --session-id wa-opc011-preflight-20261111` retornou `{"status":"HOLD","reason":"CANARY_CHAT_NOT_SELECTED","can_send":false,"independently_verified":false,...}`, saída 0. O diagnóstico temporário foi destruído pela ponte; a aba anterior permaneceu ativa. **Nenhum chat estava aberto** nesse preflight, portanto ainda não é prova de atributos de mensagens.
- O CLI executa `probe_native_schema` via `browser_extract_items(mode=inspect)` do controlador autenticado em contexto isolado. Exige **task_id e session_id explícitos**, só retorna estados agregados, nunca uma mensagem, número ou ID de WhatsApp. Sua execução não navega, abre chat, clica, envia ou persiste DB. Valor `CANARY_RECEIPT_NOT_ATTESTED` significa **apenas estrutura encontrada**, nunca confirmação de envio.

## Operação no Hermes (copiar apenas a missão do prompt final)

1. No começo, não carregar as skills locais de WhatsApp: validar capacidade nativa independentemente delas. Ler só este contrato e os dois arquivos `*.py` necessários. Abrir nova BrowserTask com `browser_navigate` e **task_id escolhido explicitamente** (por exemplo `wa-opc011-canary-20261111-01`). Exigir `runtime=electron-chromium`; se QR, `AUTH_REQUIRED` e STOP, sem manipular credenciais.
2. Usar snapshot e UI nativa para encontrar a conversa **consigo mesmo**, e somente ela. Se houver ambiguidade, não clicar; `SELF_CHAT_NOT_IDENTIFIED` e STOP. Ao abrir o próprio chat (se necessário), conferir que a identidade é do usuário e não de outra pessoa. Não clicar em enviar, não digitar mensagens, não anexar arquivos, não enviar mídia. Nenhum `browser_console` mutante, CDP externo, clipboard, teclado global ou automação de foco do Windows.
3. Obter `sessionHost` **da mesma BrowserTask** pela ponte AI Control autenticada, sem inferência por outros jobs: `node apps/desktop/scripts/eval.mjs "(async()=>{const s=await window.hermesDesktop.workstationBrowser.status();return (s.tasks||[]).filter(x=>x.taskId==='wa-opc011-canary-20261111-01').map(x=>({taskId:x.taskId,sessionHost:x.sessionHost,status:x.status,runIdPresent:!!x.runId}))})()"`. O `taskId` da saída deve ser único e corresponder ao BrowserTask aberto; nunca usar `sessionHost` de uma tarefa estacionada de terceiros.
4. A partir da raiz do repositório, executar **uma vez**: `& .\.venv\Scripts\python.exe -m workstation.scripts.wa_opc011_canary_readonly --task-id 'wa-opc011-canary-20261111-01' --session-id '<sessionHost EXATO acima>'`. Se houver conflito de autoridade ou `NATIVE_INSPECT_UNAVAILABLE`, parar. Não usar sessão inventada nem bypass de grant.
5. Registrar **somente** o JSON retornado em `workstation/dogfood/artifacts/wa-opc011-canary-20261111/result.json`, que foi preparado como diretório git-ignored. Não registrar HTML bruto, DOM, conversa, mídia, números ou conteúdo de contatos. Manter o status `can_send=false`.
6. Encerrar com relatório conciso: `NATIVE_SCHEMA_READY` somente se o JSON indicar `SCHEMA_OBSERVED` e houver chat próprio inequivocamente identificado; isso ainda **não é aprovação para envio**. Caso contrário `HOLD` + `reason` real, explicar próximo bloqueio. Informar se houve alguma alteração externa (esperado zero) e chamadas LLM/ferramentas *observadas* (não inventar métricas). Não continuar para envio de teste nesta fase.

## Critérios de aceite desta fase

- Task/session/run **únicos** e corretos; browser interno autenticado; nenhum fallback de browser externo.
- Conversa própria aberta de forma inequívoca ou `HOLD` explícito; sem tocar terceiros.
- CLI retornou resultado estruturado sem PII, gravado uma só vez no diretório próprio.
- Zero mensagens enviadas, zero alterações no controle histórico, nenhuma chamada LLM por espera de 60s (não há envio); preservação das outras sessões do Hermes.

**Fase 2 deliberadamente bloqueada:** emissor de autorização humana confiável; confirmação de mensagem nova e ACK real; envio multietapa incluindo mídia/legenda; dois destinatários reais com intervalo persistido; retomada pós-restart. Não promover a capacidade com este teste de leitura.

**Base técnica:** `WHATSAPP_DETERMINISTIC_CAMPAIGNS_20261111.md`; `workstation/context/engineering-journal/CURRENT.md`.
