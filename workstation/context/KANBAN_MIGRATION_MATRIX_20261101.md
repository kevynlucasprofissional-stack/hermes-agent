# Kanban upstream → Workstation Database — matriz de migração (baseline 01/11/2026)

## Referências comprovadas
- Checkout compartilhado: `main` @ `f1d5ab2f030e940ed4571371b0de45a21a009c9e`.
- Referência upstream *local* fixada: `upstream/main` @ `571a5911ae6aaa05ef3df53bf0f6720c4556c24a`; merge-base `3b63f7b0a4c7beb9eadbce2f15b9da75d01f5065`. Não foi feito fetch nem atualização remota.
- Backups SQLite consistentes + patch binário + estado Git + checksums: `C:\Users\Kevyn Lucas\Documents\Hermes-Workstation-Migracao-20261101\baseline-20261101-v2\baseline.json`.
- Banco atual: `kanban.db` 79 tasks; sete tabelas `hybrid_*` com **zero** registros. `workstation/board.sqlite` 1 board, 3 columns, 1 card. Ambos `integrity_check=ok`.
- Não há migração de registros híbridos atuais a executar; backup protege histórico e dados extra-checkout.

## Matriz de funcionalidades
| Recurso | Origem híbrida | Destino próprio | Prova para aceite |
|---|---|---|---|
| Bases/colunas/cartões CRUD, mover, editar, revisão | `hybrid_kanban.py` | `workstation/kanban_local.py`, plugin REST, Database | Já existe: testes 3/3; smoke UI anterior |
| Visualizações Kanban/Tabela | `hybrid-board.tsx` + cliente | `apps/desktop/src/plugins/workstation-board/board.tsx` | Já existe, compartilhando `fetchBoard` |
| Checklists / itens CRUD, completar, revisão, ordenação | `hybrid_kanban.py` e `hybrid_checklists*` | **Parcial:** criar/listar/concluir/excluir/controle revisão em SQLite + REST + editor; reordenação pendente | 5 testes Python passando; UI real aguarda recarga do módulo backend |
| Histórico de atividades e atribuição de ator | `hybrid_activity` | **Parcial:** eventos de cartão e checklists, histórico por cartão; autoria externa/board/coluna pendentes | REST e SQLite testados; UI real aguarda recarga do backend |
| Arquivar/restaurar bases, colunas e cartões | `archive_*/restore_*` | **Implementado em código**: flag de arquivo em SQLite por migração aditiva, REST com CAS, UI arquivar/restaurar e filtro | 2 testes específicos + compatibilidade de migração em cópia do banco; runtime pendente |
| Mover/ordenar colunas e cartões com adjacência | `move_column/move_card` | **Implementado em código**: reordenação por âncora, cross-column, REST, setas Kanban | Domínio + REST testados; UI em runtime pendente |
| Metadados e autoria `human/agent/system` | `hybrid_cards.metadata`, `_activity` | Pendente | Origem/autoria sem falsificação, revisão e auditoria |
| Delegação opcional + reconciliação | `hybrid_card_delegations`, `hybrid_kanban.py` | Pendente; adaptador próprio de tarefas oficiais | Recibo de autorização, tarefa criada somente após opt-in, sync verificável |
| Exclusão, recuperação, importação | `delete_*; Trello` | Inspecionar sem expandir escopo | Provar comportamento existente antes de classificar como obrigatório |
| Dashboard `/browser?module=database` | `/workstation/kanban` antigo | Já implementado com redirecionamento | UI real |

## Diferenças do upstream a classificar antes de restaurar
- 10 caminhos no diff de `upstream/main`: `api.ts`, `board.tsx`, `card-badges.test.tsx` (ausente), `hybrid-board.tsx` (novo), `i18n.ts`, `plugin.tsx`, `types.ts`, `hermes_cli/hybrid_kanban.py` (novo), `hermes_cli/kanban_db.py`, `tools/kanban_tools.py`.
- Atenção: `tools/kanban_tools.py` inclui classificação de efeitos `ToolEffect` (proteção de execução); pode ser outra melhoria e **não** é seguro reverter sem classificar origem e dependências. `kanban_db.py` contém `task_acceptance_contracts` e código de admissão que não podem ser classificados automaticamente como personalização Kanban.
- Os arquivos oficiais citados estão **limpos no working tree atual** (diferenças já no HEAD); há centenas de arquivos modificados não relacionados em checkout compartilhado, protegidos.
- `hybrid-board.tsx` não está registrado; `/hybrid` REST ausente; baseline legado possui testes falhos de checklist/dispatch. Não considerar o legado funcional.
- Critério de restauração é equivalência seletiva com **versão oficial fixada e comportamento correto**; não sobrescrever segurança/integrações independentes.

## Gates
1. Domínio Database com CRUD/revisão/auditoria e principais operações testadas.
2. REST e UI real + persistência; backup confirmado.
3. Delegação e migração de dados se aplicáveis, sem acoplamento aos bancos.
4. Só então restaurar caminhos upstream, verificar `git diff` de cada arquivo, `/kanban` e 79 tarefas; não usar reset/clean/stash.
