# Hermes Work — Trello API, etapa P0 (08/11/2026)

## Resultado e status

**API de título no QA: IMPLEMENTADA e VALIDADA EM ISOLAMENTO. E2E real com credenciais Hermes: BLOQUEADO por autenticação não configurada.** Não confundir teste do cliente REST simulado com envio efetivo ao servidor Trello pela API do Hermes.

Continuou-se no checkout compartilhado `C:\Github\hermes-agent`, `main@f1d5ab2f03`, sem worktree, staging, commit, PR ou reinício. Preservadas as alterações locais existentes, os três journals de QA e as fontes institucionais.

### Código entregue

- `workstation/trello_sync_api.py`: operação limitada ao **quadro privado `Hermes Sync QA`**, conferindo o ID de 24 hex `6aefcc8e38ac0595e0035341`, nome da cópia local e ID de quadro retornado pela API. Confere identidade do cartão e se não está fechado.
- `plan_api_title`: usando o `TrelloClient` oficial já existente e `route_for_board`, lê identidade da conta, quadro, permissão `admin` e nome do cartão; compara o campo `name` com a baseline comum. Salva a observação `api_observed` em `trello_sync_reviews`, no **mesmo** `local-edits.sqlite`. Nenhum PUT.
- `push_api_title`: requer revisão `push` de título previamente comprovada por API, administrador autenticado da mesma conta, baseline anterior, ID/shortlink, revisão local `expected_revision`, título remoto inalterado e cartão aberto. Persiste intenção `prepared` antes de toda mutação, revalida a versão local, muda para `dispatching`, tenta **exatamente um** `PUT /1/cards/{id}` com `name` e realiza GET confirmatório. `verified` somente com resposta de PUT e leitura posterior concordantes; falha ambígua resulta em `uncertain` e **não há retry**. Outro envio sobre cartão com intenção incerta é bloqueado.
- Reutiliza `workstation/trello_sync_push.py` (journal de operações, mesma tabela `trello_title_push_intents`) e `workstation.prefabs.trello.TrelloClient`, sem novo armazenamento paralelo ou scheduler.
- Plugin `plugins/workstation_database_agent`: ferramentas `workstation_db_trello_api_plan` e `workstation_db_trello_api_push`, perfil de segredos obrigatório; ausência de chave ou token retorna `transport=hold`, sem revelar segredos. O roteador prévio `workstation_db_trello_route` continua `admin → api`, `normal → browser`, desconhecido → hold.
- Trata **somente título e quadro QA**. Não habilita automaticamente escrita API em ACIRV, calendário editorial ou outros quadros, nem alterações de checklists, anexos, comentários e histórico.

### Evidências

- Regressão conjunta (Cron, Database, Trello inventories, reconciliador, roteador, Browser, push QA e API): **114 passed, 1 StarletteDeprecationWarning**; `pytest` exit 0. `py_compile` dos módulos envolvidos exit 0, `git diff --check` de arquivos rastreados exit 0.
- Testes API incluem resposta perdida após PUT (HOLD sem reenvio), GET indisponível após PUT, conflito por campo, perda da permissão admin, título remoto alterado, revisão local desatualizada e fonte que usa ID de outro quadro. O handler do plugin passou usando transporte REST fictício em ambiente isolado; nenhuma chamada de rede externa.
- Em processo Hermes independente, `model_tools.handle_function_call` para `workstation_db_trello_route`, `workstation_db_trello_api_plan` e `workstation_db_trello_api_push` retornou `HOLD` por ausência de credenciais reais (exit 0), sem tocar dados.
- Houve uma prova adicional do despachante real com transporte inteiramente simulado, baseline `equal` → `push` → `verified` e exatamente um PUT **simulado**. O script confirmou o comportamento, mas a limpeza automática de um SQLite aberto falhou com WinError 32; a pasta exata foi posteriormente removida após encerrar o processo. Não conta como E2E externo.
- Perfil ativo: `C:\Users\Kevyn Lucas\AppData\Local\hermes`. O arquivo `.env` existe, mas `build_profile_secret_scope` informou **`TRELLO_API_KEY=False`** e **`TRELLO_TOKEN=False`**. Nenhum segredo novo foi inventado, copiado ou armazenado.
- `tarefas.sqlite`: **281** tarefas; `trello.sqlite`: **395** cartões; `PRAGMA quick_check=ok` em ambos (consulta somente leitura). Journals QA1 e QA2 `uncertain` (um cada); QA3 `verified` (um); nenhum foi reexecutado.
- Envio **real anterior pelo Browser** permanece comprovado em https://trello.com/c/nzlI4GhN, com duas operações nativas e confirmação independente. **Nenhum PUT Trello API real foi executado nesta intervenção.**

## Como liberar a API, sem expor tokens nesta conversa

1. No Trello, entrar em https://trello.com/apps/admin, criar/selecionar um Power-Up, abrir **Trello Auth**, gerar uma **API Key** e autorizar um token de usuário com permissões `read` e `write`. Consultar a documentação oficial da Atlassian para o fluxo atual.
2. Inserir as variáveis `TRELLO_API_KEY` e `TRELLO_TOKEN` **diretamente** em `C:\Users\Kevyn Lucas\AppData\Local\hermes\.env`, preservando as entradas existentes. Não colocar o token no repositório, no ChatGPT ou em logs.
3. Usar o mecanismo normal de recarga do perfil Hermes para que o escopo de segredos atualize; não reiniciar processos com sessões/leases ativos. Com o perfil carregado, consultar `workstation_db_trello_route` com board_id QA `6aefcc8e38ac0595e0035341` e confirmar `transport=api` a partir do próprio Hermes.
4. Criar **novo** cartão QA, importar somente esse cartão para **cópia local de teste**, criar baseline API igual, editar seu título no overlay local, planejar push API e executar **uma** operação com `workstation_db_trello_api_push`. Verificar intenção, PUT, GET e leitura independente do servidor. Se incerto, manter HOLD.

**Risco residual:** Trello REST PUT não fornece um CAS remoto atômico neste contrato. A conferência GET imediatamente antes do PUT reduz o risco de sobrescrever edição simultânea, mas não o elimina totalmente. Para produção, qualificar conflitos e respeitar alterações humanas; não ampliar o escopo automaticamente.

## Pendências e próximo gate

- **Bloqueante:** credenciais próprias no perfil Hermes e teste E2E **real** de API com novo cartão privado QA. A conexão Trello do ChatGPT não fornece credenciais de API ao processo Hermes.
- Transporte Browser para quadro com papel `normal`: leitura nativa em `LEADS DE ASSOCIADOS` comprovada anteriormente, porém falta prova de papel via mesma identidade autenticada e teste de escrita autorizado em cartão isolado (sem alterar cartões institucionais).
- Inventário incremental de todos os cartões abertos, comentários, checklists, anexos, atividades, prazos, arquivamento e histórico; conflitos por campo com decisão humana.
- **Cron:** não há job de sincronização ativado; scheduler existente com `catch_up_missed=True` deve ser reaproveitado **somente após E2E dos dois transportes e checkpoint seguro**.

**Conclusão:** a primeira fatia correta da API foi entregue e testada com controle de efeitos; a autenticação real é o próximo bloqueio externo. Não há sincronização bidirecional completa nem cron operacional.

## Prova final limpa do despacho real (simulado)

Processo Hermes independente com registro real de ferramentas model_tools.handle_function_call, escopo de perfil ficticio e transporte REST inteiramente simulado: equal -> push -> verified; exatamente 1 PUT simulado, nenhum HTTP real, sem replay, fonte importada intacta. A execucao terminou com FAKE_RUNTIME_EXIT=0; a pasta temporaria especifica foi removida em processo separado. Esta prova e de integracao de codigo, NAO homologacao da API externa do Trello.

## 2026-11-08 - retomada: credencial ainda ausente

- Checkout main@f1d5ab2f03, staging zero; AI Control ativo, sem reinicio/commit/PR.
- Inspecao do perfil ativo C:\Users\Kevyn Lucas\AppData\Local\hermes: arquivo .env existe, mas TRELLO_API_KEY e TRELLO_TOKEN continuam ausentes do build_profile_secret_scope.
- Sem novo cartao QA ou GET/PUT da API do Hermes nesta rodada. Nenhum segredo copiado, exportado ou registrado.
- Dados originais intactos: 281 tarefas, 395 cartoes, PRAGMA quick_check ok; QA1/QA2 uncertain, QA3 verified. Nao repetir operacoes.
- Codigo nao alterado; os 114 testes pertencem a rodada anterior e nao foram refeitos.
- Proximo gate: inserir credenciais proprias diretamente no .env do perfil Hermes; validar recarga segura sem reiniciar sessoes ativas; provar route=api no QA; criar novo cartao QA e efetuar UMA tentativa PUT com intencao duravel, GET e confirmacao independente. Cron continua nao ativado.
