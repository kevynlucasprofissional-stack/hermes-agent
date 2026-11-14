# Kanban upstream -> Workstation Database — S04 (02/11/2026)

## Estado e provas
- **Etapa 2:** migracao em progresso; **Etapas 3-4:** nao iniciadas. Nao restaurar upstream antes de paridade e homologacao real.
- Repositorio `C:\Github\hermes-agent`, branch `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e` na abertura.
- Referencia upstream **local** fixada: `571a5911ae6aaa05ef3df53bf0f6720c4556c24a`; baseline e backups no S01.
- Backup dos dois bancos/patch + checksums: `C:\Users\Kevyn Lucas\Documents\Hermes-Workstation-Migracao-20261101\baseline-20261101-v2\baseline.json`.
- Artefatos checkpoint: `KANBAN_MIGRATION_S03_20261102.md` e `KANBAN_MIGRATION_MATRIX_20261101.md`.
- Registro de testes na Biblioteca: `/Hermes-Workstation/KANBAN_TESTES_PENDENTES_S02.md`.

## S04 implementado (somente Database independente)
- `workstation/kanban_local.py`: migracao aditiva de `cards.metadata_json`; escrita JSON validada (ate 16 KiB), CAS por `revision`, atividade com autor `unknown` na falta de autenticacao. Adicionadas `card_delegations` e operacoes de intent, vinculo idempotente, falha recuperavel, reconciliação de estado oficial e historico local.
- `workstation/task_adapter.py` novo: cria e consulta somente tarefas oficiais do Hermes por `kanban_db`/ `kanban_db_connect` **apos** acao explicita, sem misturar tabelas de cartoes com o banco upstream. Chave de idempotencia estavel e busca inclusive tarefa arquivada antes de criar. Nenhuma criacao real executada nesta sessao.
- `plugins/workstation-board/dashboard/plugin_api.py`: `PATCH /cards/{id}/metadata`, `POST /cards/{id}/delegate` (confirmed=true), `POST /cards/{id}/delegation/sync`. Respostas de erro 409/400/503, intent persistido no caso de falha de gateway.
- `apps/desktop/src/plugins/workstation-board/api.ts`: cliente/tipos REST para metadados e delegacao.
- `apps/desktop/src/plugins/workstation-board/card-details.tsx`: editor JSON de metadados e painel de delegacao.
- `apps/desktop/src/plugins/workstation-board/delegation-panel.tsx` novo: checkbox de consentimento e advertencia de que a tarefa oficial pode iniciar execucao; nenhuma delegacao automatica; sincronizacao sob comando.
- Novos testes `tests/workstation/test_s03_metadata.py`, `tests/workstation/test_s04_delegation.py`. Mock de gateway em testes evita qualquer despacho/gravacao no Kanban real.

## Validacao
- Suite de sete arquivos `tests/workstation/test_{kanban_local,checklist_migration,archive_migration,reorder_migration,s02_regression,s03_metadata,s04_delegation}.py`: **18 passed, 1 aviso deprecation Starlette/httpx**, exit 0. Teste dirigido do adapter confirma mesma tarefa para mesma chave e um unico create oficial (em SQLite temporario com monkeypatch).
- ESLint do frontend Database foi corrigido; validacao final pendente do retorno completo da execucao mais recente, se necessario repetir apenas esse escopo.
- Nenhuma tarefa oficial real criada; sem reset/clean/stash, commit/push/merge, restart do Hermes ou alteracao no codigo upstream.
- Hermes real continuava com `GET /api/plugins/workstation-board/cards/{id}` 404 no checkpoint S03 (backend Python montado antigo). Nao houve tentativa de reinicio nesta sessao.

## Classificacao parcial de 10 diferencas upstream/main
- Frontend `apps/desktop/src/plugins/kanban/{api.ts,board.tsx,i18n.ts,plugin.tsx,types.ts}`, inclusao `hybrid-board.tsx`, exclusao `card-badges.test.tsx`: examinar e restaurar apenas apos paridade. `board.tsx` tem mudancas em badges originais, nao somente novo Kanban.
- `hermes_cli/hybrid_kanban.py`: novo modulo 1029 linhas; remover apos paridade e ausencia de referencias.
- `hermes_cli/kanban_db.py`: alem das tabelas `hybrid_*`, existe `task_acceptance_contracts`, alteracoes de claim/complete/task context. Nao restaurar cegamente; classificar seguranca/execucao independente.
- `tools/kanban_tools.py`: adicionou `ToolEffect.PURE_READ` vs `MUTATION`, guarda de efeitos. Preservar ate classificar como controle de seguranca independente. O objetivo de upstream limpo nao autoriza perder protecoes de execucao.

## Pendencias e proxima acao
1. Corrigir qualquer lint/erro de parse residual; suite completa Python 18/18 ja validada.
2. Inspecionar se exclusao fisica e importacao sao recursos personalizados com paridade obrigatoria. Nao excluir dados reais.
3. Autoria autenticada: o namespace atual nao expoe identificador verificavel de usuario; nao aceitar actor_id arbitrario enviado pelo cliente nem falsificar autoria. Registrar `unknown` ate haver seam confiavel.
4. Homologar criacao de tarefa oficial e sincronizacao sem acoplar bancos, inicialmente em ambiente isolado com controle de permissao/autoridade; nao despachar agente real sem autorizacao especifica.
5. Backend ativo retorna 404 de API nova; avaliar janela de recarga segura com preservacao das outras sessoes antes de testar UI real.
6. Comparacao final dos dez caminhos, restauracao cirurgica do upstream **so apos paridade**; provar `/kanban`, 79 tarefas, APIs e Database em coexistencia.
7. Em caso de sessao inconclusa, produzir Resume Prompt atualizado, sem novos requisitos.
