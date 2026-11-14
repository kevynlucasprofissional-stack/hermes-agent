# Migração Kanban upstream → Workstation Database — S03 (02/11/2026)

**Estado:** Etapa 2 em andamento. Não restaurar upstream antes da paridade e homologação.

## Referências
- Repositório `C:\Github\hermes-agent`; `main` HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e`.
- Upstream local fixado `571a5911ae6aaa05ef3df53bf0f6720c4556c24a`. Dez arquivos diferem no baseline S01; segurança e contratos de admissão devem ser preservados.
- Backup `C:\Users\Kevyn Lucas\Documents\Hermes-Workstation-Migracao-20261101\baseline-20261101-v2\baseline.json`.
- Registro de testes: Biblioteca ChatGPT `/Hermes-Workstation/KANBAN_TESTES_PENDENTES_S02.md`.
- Bancos reais, leitura final: `kanban.db` 79 tarefas; `workstation/board.sqlite` 1 cartão; ambos `PRAGMA integrity_check=ok`.
- Escopo Git: somente `workstation/kanban_local.py`, `plugins/workstation-board/`, `apps/desktop/src/plugins/workstation-board/`, `tests/workstation/` e este handoff. Tudo ainda untracked; nenhum arquivo oficial do Kanban alterado no worktree por esta sessão.

## S02 executado
- Inspeção mostrou controles ↑/↓ de colunas e cartões já presentes no checkout; não duplicados.
- `tests/workstation/test_s02_regression.py` criado: migração aditiva da Database anterior, posições e fronteiras entre bases, reordenação de checklist/itens, conflitos de revisão e contrato HTTP.
- `workstation/kanban_local.py`: operações de reordenação de checklist e de itens com revisão otimista, transações, auditoria e autor `unknown` quando identidade indisponível.
- `plugins/workstation-board/dashboard/plugin_api.py`: POST `/checklists/{id}/reorder`, `/checklist-items/{id}/reorder`.
- `apps/desktop/src/plugins/workstation-board/api.ts`: cliente REST das operações.
- `apps/desktop/src/plugins/workstation-board/card-details.tsx`: controles ↑/↓ nas listas e itens; erro informativo se backend não fornecer detalhes.

## Evidências
- Suite completa `pytest -q tests/workstation/test_kanban_local.py tests/workstation/test_checklist_migration.py tests/workstation/test_archive_migration.py tests/workstation/test_reorder_migration.py tests/workstation/test_s02_regression.py`: **13 passed**, 1 aviso Starlette/httpx, exit 0.
- ESLint do frontend Database: exit 0. Sintaxe esbuild dos componentes: exit 0 em checagem anterior; última edição do fallback só foi verificada pelo ESLint.
- Hermes real somente leitura via AI Control: `GET /boards` → 1 base, `GET /boards/{id}` → 1 cartão, **GET /cards/{id} → 404**. Recarregamento de Python do plugin ainda não homologado.
- Sem reset/clean/stash/commit/push, reinicializações, mudanças de dados reais ou despacho de agentes.

## Pendências
1. Metadados, autoria autenticada e delegação opt-in/reconciliação, apenas conforme implementações híbridas comprovadas.
2. Homologar UI real após recarga segura da API Python, somente com impacto avaliado e janela autorizada; não reiniciar sessões concorrentes sem autorização.
3. Classificar 10 arquivos divergentes de upstream, inclusive `ToolEffect` e contratos de admissão.
4. Restaurar upstream cirurgicamente **após paridade**, provar `/kanban`, 79 tarefas, API e Database independentes.

No encerramento de sessão ainda incompleta: gerar novo Resume Prompt completo preservando escopo e pendências.
