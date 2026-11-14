# Kanban upstream → Workstation Database — S01 (01/11/2026)

## Decisões e gates
Etapa 1 concluída; Etapa 2 **em andamento**. Não restaurar o Kanban upstream antes da paridade e homologação. Checkout compartilhado com muitas mudanças simultâneas: nenhuma alteração em arquivos oficiais do Kanban; sem reset/stash/clean/commit/push/restart.

## Baseline
- Branch `main` HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e`, referência `upstream/main` local `571a5911ae6aaa05ef3df53bf0f6720c4556c24a`, merge-base `3b63f7b0a4c7beb9eadbce2f15b9da75d01f5065`.
- 10 arquivos de Kanban divergentes de upstream (ver matriz). Modificação de `tools/kanban_tools.py` sobre `ToolEffect` é controle de segurança e deve ser classificada antes de revertê-la. `hermes_cli/kanban_db.py` possui mecanismos de admissão além das personalizações `hybrid_*`.
- Bancos: `C:\Users\Kevyn Lucas\AppData\Local\hermes\kanban.db` = 79 tasks, sete tabelas híbridas vazias, integrity ok; `...\workstation\board.sqlite` = 1 board, 3 columns, 1 card, integrity ok.
- Backups online SQLite em `C:\Users\Kevyn Lucas\Documents\Hermes-Workstation-Migracao-20261101\baseline-20261101-v2\`, arquivos `kanban.db` e `workstation__board.sqlite`, ambos checksum SHA-256 em `baseline.json`. Patch `kanban-vs-upstream.patch` inclui diferenças dos arquivos oficiais, além de `git-status-porcelain.txt`.
- Matriz: `workstation/context/KANBAN_MIGRATION_MATRIX_20261101.md`. Não repetir inspeção sem mudança material.

## Trabalho S01 implementado apenas em arquivos da Database
- `workstation/kanban_local.py`: sem import de Kanban upstream, adicionadas tabelas independentes `card_checklists`, `checklist_items`, `board_activity`; endpoints internos de leitura de detalhes/checklists/atividades, CRUD checklists e itens, completar, revisão otimista, exclusão com auditoria. Eventos agora acompanham criar/editar/mover cartões e operações de checklist. Ator não autenticado fica marcado `unknown` (não inventar identidade).
- `plugins/workstation-board/dashboard/plugin_api.py`: REST GET detalhe do cartão, POST checklists/itens, PATCH item com revisão, POST exclusão condicionada à revisão.
- `apps/desktop/src/plugins/workstation-board/api.ts`: tipos e funções REST de checklists/atividades.
- `apps/desktop/src/plugins/workstation-board/card-details.tsx`: novo painel no editor existente (criar/excluir listas/itens, checkbox, histórico).
- `apps/desktop/src/plugins/workstation-board/board.tsx`: painel incorporado ao editor de cartões, tanto Kanban quanto Tabela.
- `tests/workstation/test_checklist_migration.py`: testes armazenamento/API em banco temporário.
- `workstation/context/KANBAN_MIGRATION_MATRIX_20261101.md`: matriz atualizada para status parcial.
- Não tocou no `apps/desktop/src/app/browser/index.tsx` e outras alterações de agentes.

## Validação e limitações
- `.venv\\Scripts\\python.exe -m pytest -q tests/workstation/test_kanban_local.py tests/workstation/test_checklist_migration.py`: 5 passing (1 warning não-bloqueante Starlette). Falha temporária por asserção de 5 eventos foi corrigida para 6 após adição legítima de `card_created`.
- ESLint nos arquivos TS/TSX relacionados: 0 erros (após `--fix` apenas no novo componente); esbuild transformou API e TSX sem erro.
- Backend HTTP isolado via TestClient: criar/completar/excluir checklists, erro 404 em cartão ausente, conflito 409 em revisão obsoleta, histórico/persistência.
- **Ainda não homologado no Hermes real**: em Electron, `GET /api/plugins/workstation-board/cards/<id>` respondeu HTTP 404 após `GET /api/dashboard/plugins/rescan`. O servidor em execução mantém a versão anterior do plugin Python. Não reiniciar com outras sessões ativas sem verificar segurança/impacto; continuar a homologação numa janela segura.
- GUI de checklists está escrita, não afirmar operabilidade real até backend atualizado/validado.
- Schema migra de forma aditiva: nenhuma exclusão de registro original. Nenhum dado híbrido a migrar nesta base ativa (0 registros).
- Nenhuma restauração upstream efetuada. Os arquivos oficiais ainda divergem em dez caminhos.

## Continuação obrigatória
1. Rechecar git status, em especial `workstation/kanban_local.py`, `plugins/workstation-board/`, `apps/desktop/src/plugins/workstation-board/` antes de editar (checkout concorrente).
2. Executar pytest/lint final, e planejar reload seguro de plugin sem perturbar outros agentes; testar UI real com checklist de prova em base temporária e limpar (atividade não some após exclusão). Se houver bloqueio, não afirmar êxito.
3. Concluir equivalência: arquivar/restaurar bases/colunas/cartões, reordenações, metadados/autoria autenticada, delegação opt-in e sincronização; somente recursos realmente presentes em `hermes_cli/hybrid_kanban.py`, sem acoplamento ao SQLite upstream.
4. Confirmar dados híbridos (baseline 0) antes de qualquer remoção; comparar todos os 10 arquivos com referência fixada, separar proteção de segurança `ToolEffect` e admissão de agente. Restaurar upstream somente depois de paridade, arquivo por arquivo.
5. Provar `/kanban` original, API, 79 tarefas; provar Database Kanban/Tabela, checklists, trilha, delegação; integridade bancos; fechar plano.
6. Caso sessão termine antes disso, produzir novamente Resume Prompt autossuficiente, sem novos requisitos.
