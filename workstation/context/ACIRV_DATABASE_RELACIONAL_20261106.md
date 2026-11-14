# Hermes Workstation — Database relacional ACIRV (06/11/2026)

## Escopo entregue
- Cinco referencias Git clonadas em `referências/15-Kanban`: Grist, NocoDB, Teable, Baserow, TanStack Table; clones rasos, pasta `referências/` ja ignorada pelo Git principal.
- Camada SQLite relacional `workstation/acirv_datasets.py`, independente da store `workstation/board.sqlite`.
- Importacao com SQLite Online Backup e validacao por banco, sem sobrescrever originais, com reimportacao idempotente e copia `.previous.sqlite` para alteracoes futuras.
- API somente-leitura via `plugins/workstation-board/dashboard/plugin_api.py`: catalogo `GET /datasets`, tabela projetada/paginada `GET /datasets/{dataset}/tables/{table}`, detalhe/relacoes `GET /datasets/{dataset}/tables/{table}/rows/{id}`.
- Interface `Bases ACIRV` no Database: visoes Tabela/Kanban dos mesmos registros, selecao de outras tabelas, detalhe e links entre bases; quadros locais existentes permanecem independentes. Definicoes de visao em `views.json`, fora dos dados.
- Sem alteracoes nas bases de origem, sem disparos de WhatsApp, sincronizacao bidirecional, execucao de tarefas ou alteracoes em `kanban.db`.

## Copias internas verificadas
`%LOCALAPPDATA%\Hermes\workstation\datasets\tarefas.sqlite` (7 tabelas; 162 tarefas, 305 eventos, 278 links).
`%LOCALAPPDATA%\Hermes\workstation\datasets\whatsapp.sqlite` (24 tabelas; 181 contatos, 87 conversas, 268 mensagens, 24 pendencias).
Reimportacao das duas fontes sem alteracoes: `unchanged` / `unchanged`.
Relacao real `tasks.id=1` -> WhatsApp contact 12, conversation 1, pendency 1 encontrada.

## Problemas herdados
`tarefas.db` possui **246 violacoes FK** (123 em `task_events`, 123 em `task_links`) de IDs que nao encontram registro pai em `tasks`. Origem e copia mantidas sem eliminar dados. Prioridade: diagnosticar essas 123 referencias antes de qualquer operacao de reconciliacao; nao reconstruir historicos automaticamente.

## Evidencias de teste
`python -m pytest -q workstation/tests/test_acirv_datasets.py tests/workstation/test_kanban_local.py`: 6 passed, 1 warning deprecado de Starlette.
`eslint api.ts board.tsx dataset-explorer.tsx`: exit 0.
Transformacao esbuild dos 3 arquivos: OK.
FastAPI TestClient contra snapshots REAIS: catalogo 200 (2 bases, 5 views), tarefas 200, detalhe da tarefa e 3 relacoes 200, contatos 200.
AI Control: ativo e Hermes aberto em `#/browser?module=database`, a nova aba `Bases ACIRV` apareceu via HMR. **A API nova nao foi homologada no processo Python ja aberto**, que nao foi reiniciado para proteger sessoes e tarefas em andamento; este e o gate para teste visual end-to-end efetivo.

## Para atualizar manualmente
Executar na raiz `C:\Github\hermes-agent`:

```powershell
python workstation/scripts/import_acirv_databases.py --tasks "C:\Github\ACIRV-Notebook\000-Arquivos-originais\Controle tarefas\tarefas.db" --whatsapp "C:\Github\ACIRV-Notebook\000-Arquivos-originais\Controle redes sociais\Whatsapp\Controle WhatsApp\whatsapp_control.db"
```

Nao usar o arquivo `Controle redes sociais\Whatsapp\whatsapp_control.db` da pasta superior: ele tem 0 bytes. Nunca comitar copias privadas das bases, arquivos `-wal` ou PII. Views sao leitura somente ate haver uma decisao explicita de sistema de registro/escrita e reconciliacao.

## Pendente para conclusao de produto
Testar apos recarga segura do backend: abrir Bases ACIRV, selecionar Tarefas, alternar Tabela/Kanban, selecionar T-0001 e abrir relacoes, recarregar UI e verificar consistencia. Nao marcar E2E live como aprovado antes desse teste. Stage A opcional e nao necessario.

## Homologação de correção do HTTP 404 — 06/11/2026 22h18 (America/Sao_Paulo)
- Diagnóstico: `plugin_api.py` atualizado após inicialização do processo `hermes serve` (19h14 vs. inclusão das rotas às 20h34). A proteção de hot-mount existente não substitui rotas de plugin já montado; o frontend atualizado disparava `GET /api/plugins/workstation-board/datasets` contra servidor antigo e recebia HTTP 404.
- Antes da ação: `state.db.session_turn_leases=0`; `kanban.db.task_runs` sem execução em andamento.
- Correção aplicada pela ponte oficial Hermes AI Control: `window.hermesDesktop.recycleBackend()` retornou `{ok:true}` e novos subprocessos `hermes serve` foram iniciados.
- Prova no backend real via `window.hermesDesktop.api`: resposta com 2 bases e 5 views, sem HTTP 404.
- Prova na interface real `#/browser?module=database`: Tabela de tarefas mostrou 162 linhas; Kanban agrupou por 6 estados; detalhe da tarefa ID 1 apresentou vínculos com WhatsApp; clicar na relação `whatsapp/contacts #12` exibiu o registro de contato e Tabela com 181 contatos; nenhum alerta de erro.
- Verificação posterior: `python -m pytest -q workstation/tests/test_acirv_datasets.py tests/workstation/test_kanban_local.py`: **7 passed** (1 aviso de depreciação preexistente do TestClient); ESLint alvo `exit 0`; SQLite `quick_check=ok` em ambas as cópias.
- Pendências não bloqueantes para leitura: 246 inconsistências de chaves estrangeiras herdadas em tarefas; sincronização bidirecional e edição de registros não implementadas. Nenhuma base original, sessão, run ou cartão existente foi excluído.

## Decisões Trello/Database e inventário em 06/11/2026
Decisões do usuário: (1) recuperar 119 tarefas órfãs pelo Trello, inclusive arquivadas, preservando histórico; (2) sincronização bidirecional entre Trello e Hermes; (3) conflitos por campo exigem decisão humana e preservam ambas as versões; (4) arquivamento sincronizado, exclusões protegidas por confirmação e histórico; (5) incluir comentários, checklists, anexos e histórico disponível; (6) sincronizar continuamente apenas cartões **em aberto** de todos os quadros acessíveis, incluindo nunca importados. Não voltar a fazer perguntas de escopo.

Evidência real Trello connector (06/11/2026):
- Conta: 4 quadros acessíveis, pelo `trelloReadBoard(list)` e `trelloReadBoard(list_by_workspace)`: ACIRV + VCOM: SCRUM, Vontade SMART, +Bela, CRM ACIRV.
- O booleano de conclusão é `dueComplete: true` (e `complete: true`); `due` é a data, NÃO um flag. Filtragem segura: `closed !== true && complete !== true && dueComplete !== true`, e listas explicitamente "Finalizados/Concluídos/Done" removidas da sincronização contínua. Histórico separado não obedece filtro de aberto.
- 1.165 cartões observados; 205 em aberto (66 SCRUM, 44 SMART, 94 +Bela, 1 CRM), 124 arquivados, 834 marcados concluídos e 2 em listas finais sem marcação, total conferido.
- Inventário privado completo **dos 205 ativos** em `%LOCALAPPDATA%\Hermes\workstation\datasets\trello-inventory-20261106.json` (~289 KB). Metadados de comentários/checklists podem estar truncados; NÃO é snapshot integral do histórico/anexos, nem sincronização.
- 119 `task_id` órfãos ligados a 123 `trello_card` URLs distintas no SQLite ACIRV. **Zero** dos 123 shortlinks foram encontrados nos 1.165 cartões dos quatro quadros acessíveis; 4 URLs individuais tentadas pelo conector retornaram inacessível/inexistente. Portanto, **não** recriar as 119 tarefas como se os títulos/estados históricos tivessem sido recuperados. Manter evidência e buscar outra fonte autorizada/backup apenas se existir.

Entregue agora:
- `workstation/acirv_datasets.py`: terceiro dataset `trello` com URL resolvida apenas a SQLite privado (não altera tarefas/WhatsApp).
- `workstation/trello_inventory.py`: `import_inventory(snapshot,home)`, verificação fail-closed de 205 cartões abertos/deduplicados, snapshot SQLite atômico; também gera tabela de 119 `orphan_refs` com contagem de eventos/vínculos, sem inventar títulos nem modificar o original. Acrescenta duas views sem sobrescrever as cinco existentes.
- `workstation/tests/test_trello_inventory.py`: valida leitura e integridade, preservação de origem, idempotência, rejeição de cartões concluídos/arquivados.
- API existente após recarga nativa de backend confirmou 3 datasets / 7 views. Navegação UI real `#/browser?module=database` confirmou 205 linhas na view `Trello · Em aberto`, 119 linhas na view `Trello · Referências órfãs`, sem alerta de erro.
- Testes: `python -m pytest -q workstation/tests/test_trello_inventory.py workstation/tests/test_acirv_datasets.py tests/workstation/test_kanban_local.py` => **13 passed**, 1 warning Starlette TestClient. SQLite `trello.sqlite` `PRAGMA quick_check=ok`. `tarefas.sqlite` ainda tem 246 FK violations herdadas, intactas.
- Nenhum cartão foi criado/alterado no Trello; `board.sqlite`, fonte ACIRV e repositórios originais intactos. Sem commit, push ou PR; working tree compartilhado tem muitos outros itens alterados.

Não implementado (BLOQUEANTE para alegar sincronização bidirecional): conexão contínua do Hermes ao Trello com identidade de conta/perfil e escopo, mapeamento estável card<->task com deduplicação, envio ao Trello, change tracking por campo, resolução de conflitos com versões guardadas, checkpoint/replay idempotente, arquivamento sincronizado com deleção protegida, leitura completa paginada de comentários/checklists/anexos/atividades, e reconstrução comprovada das 119 tarefas inacessíveis. Trello connector funciona nesta conversa, mas o ambiente local não possui TRELLO_API_KEY/TRELLO_TOKEN em variáveis nem no .env do Hermes; não expor ou inventar chaves. O Trello connector desta conversa não está implicitamente injetado no processo do Hermes.

RESUME PROMPT (uso direto): Continue em C:\Github\hermes-agent na branch main HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e, working tree compartilhado dirty/untracked sem commit, worktree separado não criado, PR não criado. Preserve todas as mudanças do usuário e dos agentes; sem reset/stash/clean/push. O objetivo aprovado é sincronização bidirecional segura entre todos os quadros Trello acessíveis e o Database Hermes apenas para cartões ativos, preservando histórico dos 119 órfãos separadamente. Parta dos arquivos workstation/trello_inventory.py, workstation/acirv_datasets.py, workstation/tests/test_trello_inventory.py, plugins/workstation-board/dashboard/plugin_api.py e do inventário %LOCALAPPDATA%\Hermes\workstation\datasets\trello-inventory-20261106.json. Estado validado: 205 cartões, 119 orphans, 13 testes verdes, views acessíveis na UI. Primeira pendência crítica: integrar acesso Trello autenticado por perfil de forma segura ao runtime Hermes e implementar pull incremental com mapeamento card<->task e conflitos por campo, sem publicar alterações remotas até provar autorização, identidade, dry-run e escrita idempotente E2E. Antes de concluir, testar de ponta a ponta pull, edição Hermes->Trello, Trello->Hermes, conflito bilateral, exclusão protegida, reinício/retry, e não quebrar a base original nem sessões de outros agentes. Não fabricar a recuperação das 119 tarefas: 123 URLs não aparecem nos quadros atualmente acessíveis, quatro retornam inacessíveis. Gere novo handoff objetivo se precisar interromper.

## Recuperação histórica ACIRV — 07/11/2026 (três exports de quadros Trello enviados pelo usuário)
Arquivos analisados (originalmente anexados na conversa; são fontes estáticas, não permissões de API):
- `06.11.26 - calendario-editorial.json`: Calendário Editorial, 4.577 cartões; 3.913 arquivados, 508 concluídos não arquivados, 156 em aberto.
- `07.11.26 - leads-de-associados.json`: LEADS DE ASSOCIADOS, 34 cartões em aberto.
- `06,11,26 - acirv-vcom-scrum.json`: ACIRV + VCOM: SCRUM, 947 cartões; 95 arquivados, 784 concluídos, 2 em lista de finalização sem marca de conclusão, 66 em aberto (já presentes no inventário anterior).

**Diagnóstico fechado:** os 123 `task_links.ref` antigos (`trello:<shortLink>`) das 119 tarefas órfãs IDs 268..386 correspondem exatamente a 123 cartões de `Calendário Editorial`; todos constam como `dueComplete=true`, `closed=false`. IDs 283, 290, 367, 377 possuem dois cartões cada, preservados como evidência separada. 0/123 estavam nos quatro quadros retornados pela conta do conector de Trello; a fonte correta era o export de um quinto quadro, não acessível naquele escopo.

**Correção aplicada à cópia interna, sem escrita no Trello ou na fonte original:**
- Payload fundamentado no export, com títulos, descrições, datas, metadados de anexos/etiquetas e 123 IDs originais em `%LOCALAPPDATA%\Hermes\workstation\datasets\trello-calendario-resgate-20261107.json` (522 KB).
- `workstation/trello_recovery.py::recover`: refaz 119 registros `tasks` com IDs originais e status `concluida`, preserva 305 `task_events`, 278 `task_links` e 123 metadados da fonte em `trello_recovery_evidence`. Backup em `%LOCALAPPDATA%\Hermes\workstation\datasets\tarefas.before-recovery.sqlite`; a substituição da cópia é atômica e recusa mudanças concorrentes. Rodar novamente retorna `unchanged`.
- Resultado na cópia: **281 tasks; 0 violações de FK; 305 eventos; 278 links; 123 evidências**. Original `C:\Github\ACIRV-Notebook\000-Arquivos-originais\Controle tarefas\tarefas.db` **intocado** (162 tasks e 246 violações históricas).
- A visualização `Trello · Histórico recuperado` mantém as 119 referências com status `recuperada` (cópia `trello.sqlite` atualizada com backup). O Desktop backend real respondeu 281 tarefas e detalhe da tarefa 268 com nome/status corretos; nenhuma rota 404.
- Proteção contra regressão em `workstation/acirv_datasets.py::import_sources`: reimportar o original por cima da cópia recuperada retorna erro explícito antes de sobrescrever dados restaurados. Uma futura atualização das fontes exige reconciliação explícita.
- Evidência: `python -m pytest -q workstation/tests/test_trello_recovery.py workstation/tests/test_trello_inventory.py workstation/tests/test_acirv_datasets.py tests/workstation/test_kanban_local.py` => **16 passed**, um aviso de depreciação Starlette TestClient; `py_compile` OK. Recuperação real isolada validada antes da operação em produção, incluindo repetição idempotente.

**Limites importantes:** os outros exports não foram incorporados como novos cartões ativos; o atual inventário de 205 ativos do conector continua como estava. O export contém apenas as últimas 1.000 ações do quadro e metadados de anexos, não garante todos os comentários/atividades nem arquivos binários. Isto resolve a integridade da cópia histórica, **não** conclui a sincronização bidirecional. O conector Trello ligado ao ChatGPT não fornece automaticamente credenciais ao Hermes local; faltam conexão contínua por perfil, track de mudanças por campo, conflitos, escrita com verificação e sincronização dos quadros fora do acesso da conta conectada. Não afirmar sincronização ativa. Sem commit/push; preservar árvore compartilhada dirty/untracked.

**Continuação objetiva:** se a tarefa for finalizar a sincronização Trello↔Hermes, continuar em `C:\Github\hermes-agent` main HEAD anterior `f1d5ab2f030e940ed4571371b0de45a21a009c9e` (rever HEAD real), sem worktree separado ou PR registrado. Manter mudanças concorrentes intocáveis, sem reset/stash/clean. A primeira falha bloqueante é o Hermes não possuir acesso autenticado ao Trello nesses quadros. Integrar credenciais por perfil com aprovação e escopo, realizar pull incremental com dados originais e deduplicação, depois conflitos por campo e push idempotente com prova E2E. Não usar export offline como prova de sincronização ao vivo. Reexecutar teste de regressão `test_import_refuses_silent_loss_of_recovered_trello_tasks` antes de qualquer alteração na importação das fontes. Não modificar originais nem reativar tarefas concluídas.

## Continuação 07/11/2026 — consolidação dos exports não vinculados (somente leitura)
- Em paralelo a esta sessão, `workstation/trello_recovery.py` recuperou os 119 tasks/123 links do export Calendário Editorial na cópia interna: a auditoria independente confirmou 281 tasks, 305 task_events preservados byte-a-byte por valores, 278 task_links preservados, 123 trello_recovery_evidence, zero foreign_key_check. A fonte `C:\Github\ACIRV-Notebook\000-Arquivos-originais\Controle tarefas\tarefas.db` mantém 162 tasks e 246 FK violations. Backup: `%LOCALAPPDATA%\Hermes\workstation\datasets\tarefas.before-recovery.sqlite`. Não executar outra recuperação sobre esses registros.
- Detectados 190 cartões adicionais ativos nos exports que não constavam do dataset: 156 de `06.11.26 - calendario-editorial.json`, 34 de `07.11.26 - leads-de-associados.json`; export `06,11,26 - acirv-vcom-scrum.json` possui 66 ativos, já presentes. Todos os 3 arquivos estavam também em `C:\Github\ACIRV-Notebook\000-Arquivos-originais\`, sem necessidade de copiar upload via rede.
- `workstation/trello_offline_exports.py::import_exports` (novo) valida origem/listas/cartões não arquivados e `dueComplete!=true`, preserva todos os 205 cards existentes e insere 190 novos em `%LOCALAPPDATA%\Hermes\workstation\datasets\trello.sqlite`. Guarda card JSON integral disponível, ações e checklists disponíveis (histórico incompleto pela limitação do export) em `trello_export_evidence`; não baixa anexos binários nem grava no Trello. Backup `trello.before-export-merge.sqlite`. Atualmente 395 cards, 190 evidências de export, 119 orphan_refs com status recuperada, `PRAGMA quick_check=ok`, 0 foreign_key_check.
- Validação isolada com dados reais: primeiro merge 156+34+0, 395 registros, dados dos 205 anteriores preservados, rerun unchanged, exports originais byte idênticos. Backend local autenticado respondeu dataset Trello 395 e tarefas 281. Interface nativa `#/browser?module=database`, view `Trello · Em aberto`, tabela **395 linhas**, sem alerta de erro; voltou à view anterior `Tarefas ACIRV` / Kanban.
- Proteção anti-perda adicional em `workstation/trello_inventory.py::import_inventory`: uma futura importação manual dos 4 quadros do conector que apagaria os dados adicionais ou a recuperação histórica agora **falha fechada** com pedido de reconciliação. Teste isolado forçou reimportação sobre base de 395 e confirmou exceção e preservação byte-a-byte da cópia; nenhuma sobrescrita. Uma verdadeira atualização automática deverá fazer merge/reconciliação e não substituir o SQLite com um snapshot parcial.
- Testes: `python -m pytest -q workstation/tests/test_trello_recovery.py workstation/tests/test_trello_inventory.py workstation/tests/test_acirv_datasets.py tests/workstation/test_kanban_local.py` => **16 passed**, 1 aviso de depreciação do Starlette TestClient. `python -m py_compile workstation/trello_offline_exports.py workstation/trello_inventory.py workstation/trello_recovery.py workstation/acirv_datasets.py` exit 0.
- Branch compartilhada `main`, HEAD `f1d5ab2f03`, muitas alterações concorrentes/untracked; sem commit/stash/reset/push, sem PR e sem worktree isolado neste ciclo. Protótipo redundante criado pela sessão removido; preservar scripts existentes da outra sessão.
- **Não está pronto:** sincronização bidirecional em tempo real, credenciais Trello por perfil no Hermes, controles de conflito e exclusão, push idempotente, comentários e anexos integrais, import incremental dos seis quadros (dois apenas offline). Não classificar o catálogo de 395 como espelho em tempo real. Priorização seguinte: integrar autenticação por perfil e pull incremental seguro com merge que não apague 190 exports nem 119 históricos; só depois push por campo e conflitos, com testes E2E de escrita remota.
