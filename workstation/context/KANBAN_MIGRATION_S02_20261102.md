# S02 — Migração Kanban upstream → Database (02/11/2026)

## Estado e restrições
Etapa 1 concluída no S01; etapa 2 ainda **incompleta**. Nenhum arquivo oficial Kanban foi restaurado, nenhum reset/stash/clean/commit/push/restart. Checkout compartilhado `C:\Github\hermes-agent`, branch `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e` observado no início e no final das operações. Referência upstream local `571a5911ae6aaa05ef3df53bf0f6720c4556c24a`, merge-base `3b63f7b0a4c7beb9eadbce2f15b9da75d01f5065`.
Baseline/checksums: `C:\Users\Kevyn Lucas\Documents\Hermes-Workstation-Migracao-20261101\baseline-20261101-v2\baseline.json`. Não repetir inventário se estado permanecer compatível.

## Trabalho S02
- `workstation/kanban_local.py`: migração SQL **aditiva** de `boards`/`columns`/`cards` para campos `archived`, `revision` em board/column; `INSERT` explícito para compatibilidade com colunas novas. APIs de arquivo/restore com revisão (CAS), sem deletar objetos, auditoria `unknown` quando identidade não existe; `get_board` e `list_boards` aceitam `include_archived`. Reordenação de colunas e cartões por `before_id`, inclusive movimento entre colunas, renumeração densa em transação SQLite. Nenhuma dependência de `hermes_cli.kanban_db`.
- `plugins/workstation-board/dashboard/plugin_api.py`: GET de bases com `include_archived`, PATCH `/archive/{entity}/{id}`, POST `/columns/{id}/reorder` e `/cards/{id}/reorder`, além das rotas S01.
- `apps/desktop/src/plugins/workstation-board/api.ts`: clientes tipados de archive/reorder + campos de revisão; preservadas as mesmas fontes de registros para Kanban/Tabela.
- `apps/desktop/src/plugins/workstation-board/board.tsx`: checkbox de arquivados, arquivar/restaurar base, coluna e cartão, controles de subida/descida na visualização Kanban. **Compatibilidade da instância ativa:** novos controles ficam desabilitados enquanto resposta `board.archived` não existir; painel novo `CardDetailsPanel` não monta nesse caso. Isto impede UI de usar API antiga. Restam testes no Desktop reiniciado.
- `tests/workstation/test_archive_migration.py` e `test_reorder_migration.py` criados. Matriz atualizada `workstation/context/KANBAN_MIGRATION_MATRIX_20261101.md`.

## Evidências
- `.venv\Scripts\python.exe -m pytest -q tests/workstation/test_kanban_local.py tests/workstation/test_checklist_migration.py tests/workstation/test_archive_migration.py tests/workstation/test_reorder_migration.py` → **9 passed**, aviso Starlette/httpx não bloqueante.
- ESLint nos três arquivos TS/TSX Database: **0 erros**. Esbuild parsing dos três: sucesso.
- Sobre cópia temporária do `AppData\Local\hermes\workstation\board.sqlite`, migração aditiva preservou 1 cartão, adicionou `archived` e `PRAGMA integrity_check=ok`. Banco real não alterado nesta verificação.
- Leitura SQLite em modo readonly: `kanban.db` 79 tasks, integridade OK; `workstation/board.sqlite` 1 card, integridade OK.
- Consulta real via AI Control: `/api/plugins/workstation-board/boards/<id>` responde sem `archived` e `/api/plugins/workstation-board/cards/<id>` retorna **404**. Não homologar UI nova como funcional antes de atualizar o processo backend.
- Diagnóstico fonte `hermes_cli/web_server_dashboard.py`: `_plugin_api_mounted` impede remontagem de plugin já montado; `rescan` não reimporta as rotas Python alteradas. Um reinício controlado do dashboard/backend é necessário, salvo outro mecanismo comprovado seguro. Não realizar sem proteger sessões concorrentes.
- HEAD e status verificados: nenhuma alteração no working tree dos caminhos oficiais `apps/desktop/src/plugins/kanban`, `plugins/kanban`, `hermes_cli/kanban_db.py`, `hermes_cli/hybrid_kanban.py`, `tools/kanban_tools.py`; continuam divergentes da referência upstream por alterações já no HEAD.

## Pendências e ação seguinte
1. Ao retomar, validar estado/HEAD e 9 testes. Verificar mecanismo/condições de reinício coordenado **apenas do backend** sem interromper operações; depois provar checklists, arquivo e reordenação na interface real por API autenticada, em dados temporários, removendo somente criados na prova. Se não viável, manter blocker explícito.
2. Implementar paridade **comprovada** de checklist reordenação, metadados, autoria autenticada (não inventar actor), deleção/recuperação e delegação opt-in com reconciliação segura. Verificar a existência real de importação Trello antes de incluí-la.
3. Revisar todos os 10 caminhos do diff para separar customização híbrida de segurança oficial: `ToolEffect` em `tools/kanban_tools.py` e admissão em `hermes_cli/kanban_db.py` exigem cuidado. Só depois de paridade comprovada restaurar upstream arquivo por arquivo.
4. Homologar `/kanban` (79 tasks), `/browser?module=database` Kanban/Tabela, backups e integridade; não executar push/merge remoto sem autorização.
5. Se incompleto, entregar novo Resume Prompt autossuficiente.
