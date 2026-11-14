# Hermes Work — Relatório de push Trello QA (07/11/2026)

## Resumo executivo

**Resultado:** fluxo de push de título implementado em modo QA, com intenção durável e proteção contra reenvio, mas **ainda não homologado integralmente** pelo requisito de recibos nativos + releitura após recarregar. A primeira alteração foi persistida no Trello; a segunda não foi persistida. Ambas permanecem com registro de resultado **uncertain**, sem repetição. A terceira tentativa não foi executada porque o AI Control perdeu a conexão.

**Checkout:** `C:\Github\hermes-agent`, branch `main`, último HEAD confirmado `f1d5ab2f03`, staging vazio, sem commit, PR ou restart nesta intervenção. Preservadas as alterações locais anteriores.

## Ambiente QA real

- Quadro privado criado na área pessoal Trello, com `visibility=PRIVATE`, confirmado por listagem filtrada de quadros privados: https://trello.com/b/bnasyDT7/hermes-sync-qa
- Lista: `QA`. Os três cartões abaixo são exclusivos de homologação, sem participação nas bases importadas.
- Cartão QA1: https://trello.com/c/QqzZBITN — título atualizado pelo Browser nativo de `Hermes Sync QA - título inicial` para `Hermes Sync QA - title validated by Hermes`. Consulta independente `trelloReadCard(get)` confirmou persistência no servidor. Lançamento no journal como `uncertain`, ID `3df7088d10e070d9f1b81e8a8c842419`: recibo de preenchimento presente, recibo do passo Enter ausente. **Não repetir operação.**
- Cartão QA2: https://trello.com/c/4GMW1veQ — uma única operação de preenchimento teve recibo válido, porém após recarregar o cartão o título continuou `Hermes Sync QA - second title test`. Verificação independente do Trello confirmou que o servidor não gravou o novo título. Intent `6c7ccbb03d0337f60f6636668ad3d81d` em `uncertain` por `readback_mismatch`. **Não repetir operação.**
- Cartão QA3: https://trello.com/c/nzlI4GhN — criado com título `Hermes Sync QA - two operation test`; Browser nativo confirmou quadro, lista, status aberto e título original. Preparação local por terminal expirou; verificação seguinte mostrou ausência do diretório QA3/manifest. **Nenhum push QA3 executado.**

## Implementação atual

- Novo `workstation/trello_sync_push.py`: push de título **restrito ao quadro QA**. Exige: cartão local com `board_name=Hermes Sync QA`, quadro **remoto** também com esse nome, status aberto, ID/shortlink compatíveis, review com baseline nativa e `push` de nome, revisão local válida e BrowserTask autorizada. Rejeita qualquer cartão institucional.
- Grava `trello_title_push_intents` no **mesmo** `local-edits.sqlite` antes de qualquer efeito. Guarda `intent_id`, `operation_id`, revisão, título anterior e alvo, estado, recibos e readback. Bloqueia reenvio da mesma intenção e novas intenções para cartão com operação não resolvida.
- Referência de título via `browser_snapshot(view=action_map)` e `testid=card-back-title-input`, com âncora estável. Usa `tools.browser_workstation._dispatch`/Browser nativo, não CDP/mouse/teclado global.
- Após QA1 e QA2, o código passou a executar **duas operações nativas distintas**: `browser_batch_actions` de um passo de preenchimento, gravando estado `typed`; depois `browser_press Enter` com outro operation ID e recibo, seguido de `browser_navigate` e leitura de confirmação. Qualquer exceção ou recibo ausente resulta em `uncertain` persistido. **Essa versão ainda não recebeu prova externa.**
- `plugins/workstation_database_agent/__init__.py` e `plugin.yaml` expõem `workstation_db_trello_push` em conjunto com as seis ferramentas prévias. A ferramenta documenta `QA ONLY`.
- `workstation/tests/test_trello_sync_push.py` testa gravação da intenção antes do efeito, recibos, leitura posterior, não repetição, resultado incerto, revisão desatualizada e bloqueio de quadro institucional.

## Evidências e preservação

- Regressão focal ampliada: **86 testes Python aprovados**, 1 aviso preexistente de Starlette/HTTPX; `py_compile` das implementações aprovado.
- Antes dos testes externos: `tarefas.sqlite`: **281 tarefas**, `trello.sqlite`: **395 cartões**, ambos `PRAGMA quick_check=ok`. Os QA foram criados num quadro externo privado e **não foram importados** para esses snapshots.
- Journals QA persistidos sob `%LOCALAPPDATA%\HermesWorkstation\QA\trello-push-20261107` e `trello-push-2-20261107`. Não modificar/reexecutar esses IDs. O ambiente QA3 estava ausente na última verificação.
- O AI Control retornou `aiControl:null` na última inspeção; não houve fallback via automação global, CDP, reinício ou alteração de leases. Bancos WAL existentes não foram convertidos.
- Cron existente com `catch_up_missed=True` continua sem novo job de sincronização. Não alterar antes de provar push com recibo/readback e pull real.

## Próximo gate único

1. Reestabelecer AI Control e verificar BrowserTask/leases/sessões sem reiniciar indiscriminadamente.
2. Confirmar novamente o cartão QA3; preparar um diretório local QA3 **durável e isolado** se ainda inexistente; realizar baseline nativa, editar título no overlay QA, registrar review push.
3. Executar uma única tentativa do `workstation_db_trello_push` no QA3 usando o **código de duas operações independentes**. Exigir recibos válidos dos dois passos, recarga do cartão, título persistido no Browser e confirmação independente de leitura Trello. Se houver efeito incerto, **HOLD, não repetir**.
4. Se qualificado: avaliar migração do modo QA para um executor autorizado por identidade do cartão/board com operação journalizada, provar título nos dois sentidos, conflitos e restauração. Só depois ampliar campos/cartões e cadastrar um único cron diário.

**Status:** entrega de integração ainda parcial; não declarar sincronização bidirecional completa ou cron operacional.
