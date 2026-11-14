# Workstation Kanban — independente do upstream (01/11/2026)

## Decisão
Pedido explícito do mantenedor: o Kanban do Workstation **não** precisa obedecer ao One State Hermes nem derivar estado do Kanban upstream. Esta exceção é específica do novo módulo; preservam-se as regras de permissão, identidade de sessão, execução de agentes e segurança do Hermes.

## MVP implementado no checkout compartilhado
- Backend de domínio: `workstation/kanban_local.py` (SQLite próprio em `<HERMES_HOME>/workstation/board.sqlite`; nenhuma importação de `hermes_cli.kanban_*`).
- REST autenticado via loader oficial: `plugins/workstation-board/dashboard/{manifest.json,plugin_api.py}`, namespace `/api/plugins/workstation-board`.
- Frontend SDK-consumer: `apps/desktop/src/plugins/workstation-board/{plugin.tsx,api.ts,board.tsx}`, rota `/workstation/kanban`, menu `Kanban Workstation`.
- Recursos MVP: quadro com três colunas iniciais, criação de quadros/colunas/cartões, edição de título/descrição, movimentação (drag-and-drop ou seleção), controle de revisão 409, persistência local. Sem dispatcher, estado ou lifecycle do Kanban original.
- Não foi editado nenhum arquivo do plugin upstream para implementar este MVP.

## Evidência real
- `python -m pytest -q tests/workstation/test_kanban_local.py`: 3 passed; um warning de dependência Starlette/httpx.
- ESLint nos três arquivos TS/TSX: 0 erros. Esbuild sintático da entrada do plugin: sucesso. Typecheck integral do app não qualificado (execução anterior terminou com exit 1 sem diagnóstico útil).
- O AI Control visualizou e navegou pela página do novo plugin no Hermes aberto; o backend inicialmente respondeu 404 em função de cache anterior à criação do plugin.
- Cache atualizado sem restart pelo endpoint existente `GET /api/dashboard/plugins/rescan` (5 plugins); leitura autenticada `GET /api/plugins/workstation-board/boards` passou.
- Chamadas pelo próprio `window.hermesDesktop.api`: criou quadro "Workstation" com três colunas, cartão "Migrar personalizações do Kanban para o Workstation", moveu para "Em andamento", editou o texto, leu o resultado; tentativa com revisão antiga rejeitada 409.
- SQLite real separado: 1 quadro, 1 cartão, `PRAGMA integrity_check=ok`. Kanban original ainda 79 tarefas, `PRAGMA integrity_check=ok`.
- Snapshot verificado antes dos trabalhos em `C:\Users\Kevyn Lucas\Documents\Hermes-Workstation-Migracao-20261101\kanban-upstream-snapshot.sqlite` (SHA256 `8280ac1b637b1a4b74a8708a87977760a3938befab5f703c4085c3be456b1761`).
- Com o plugin em estado `loaded`, usei o adaptador nativo `host.navigate('/workstation/kanban')`: interface exibiu quadro e cartão sem alertas; abri o editor, alterei a descrição, cliquei **Salvar**, confirmei a mudança no DOM e pela API (revision 4). A sessão original `#/20261101_152355_b21925` foi restaurada; sem reiniciar o Hermes.

## Estado upstream e funcionalidades pendentes
- O módulo `apps/desktop/src/plugins/kanban/hybrid-board.tsx` (não registrado em rota), as chamadas híbridas em `apps/desktop/src/plugins/kanban/api.ts` e `hermes_cli/hybrid_kanban.py` usam persistência `hybrid_*` no `kanban_db.py` original. Não removê-los até migrar equivalentes e homologar.
- Inspeção de 16 bancos `kanban.db` ativos/históricos sob `AppData/Local/hermes`: nenhum `hybrid_boards` encontrado. O principal tem 79 agent tasks; permaneceram no upstream.
- Paridade ainda pendente: checklists, trilha de atividades, arquivamento, delegação opt-in para agentes, importação de Trello, possíveis operações de movimentação entre quadros, reconciliação de permissões/escopo.
- `plugins/vault` e `apps/desktop/src/plugins/vault` já são módulos independentes; não reconstruir. O nome "Vals" precisa de correspondência real de componente antes de migração.
- Baseline híbrida antiga está vermelha independentemente deste módulo: `tests/plugins/test_kanban_dashboard_plugin.py::test_hybrid_checklist_crud_and_stale_revision` falha por falta de `board` na API `/hybrid/boards`; `tests/hermes_cli/test_hybrid_kanban.py::test_agent_tool_uses_the_same_hybrid_domain` falha porque `tools.kanban_tools._handle_hybrid` não existe. A causa/introdução histórica dessas falhas ainda não foi auditada.
- Não foi feita restauração do Kanban upstream, nem merge, commit, push ou alteração do `main` além dos novos arquivos de trabalho no checkout. `main` contém centenas de alterações de outras missões e deve ser preservado.

## Próxima ação única
Portar o menor conjunto de recursos híbridos que o usuário utiliza ou precisa preservar (priorizar checklists e atividades) para a base própria, testar a integração opcional com agentes sem copiar estado do upstream e provar paridade antes de remover as customizações originais por arquivo/fluxo. Não aplicar reset, stash, clean, reiniciar sessões em curso nem reverter alterações de outros agentes.
