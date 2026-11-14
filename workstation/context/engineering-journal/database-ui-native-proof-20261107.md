# Hermes Database — homologação real da edição nativa (07/11/2026)

## Escopo e estado
- Repo `C:\Github\hermes-agent` em `main@f1d5ab2f03`; checkout compartilhado com alterações anteriores, staging vazio; nenhum commit, PR ou restart.
- Entrada: `node apps/desktop/scripts/hermes-nav.mjs status` → `aiControl:true`, backend `v0.21.7+1590 (+1)`. Ponte autenticada local, sem CDP e sem mouse/teclado global.
- Fluxo real pela interface Electron: Workstation → Database → Bases ACIRV → tabela `tarefas/people`.
- Para não tocar tarefas reais ou cartões Trello, criada UMA linha sintética `people.id=-20261107001`, `name=Hermes UI QA temporary 2026-11-07`, `role=qa-original` em cópia interna `tarefas.sqlite`. Antes: `people=0`, `tasks=281`, FK check=0; tabela não tem chaves estrangeiras, trigger só em UPDATE. Seed com `.venv\Scripts\python.exe` (SQLite 3.53.4), em `BEGIN IMMEDIATE`, nunca nos originais externos.
- Na UI nativa, abertura da linha exibiu `Editar registro`; editor JSON foi alterado exclusivamente em `role: qa-ui-verified`; clique `Salvar` mostrou `role=qa-ui-verified`, `revisão 1`, `Alteração local pendente de sincronização`, 0 alerts.
- Saída da visualização para Quadros locais e retorno a Bases ACIRV, seleção da mesma linha → persistiram valor e revisão (novo fetch real de painel). 
- Despachante real do agente `model_tools.handle_function_call('workstation_db_query', dataset='tarefas',table='people',record_id='-20261107001')` viu o mesmo `role=qa-ui-verified` e `local_revision=1`; ferramentas `workstation_db_query` e `workstation_db_update` expostas.
- `local-edits.sqlite` apresentou `actor=human`, 1 `edit_events`, `changes_json={role:qa-ui-verified}`. **O banco ficou em WAL** no processo live, apesar de a fonte atual remover a ativação de WAL — evidência de módulo pré-carregado no backend.

## Limpeza efetivamente executada
- Antes da limpeza, saiu da tabela relacional para Quadros locais, evitando alteração em tela aberta.
- Um script SQL com verificações rígidas removeu SOMENTE `tarefas/people/-20261107001` do `local-edits.sqlite`, 1 evento QA e 1 linha seed `people` da cópia `tarefas.sqlite`, com validação de conteúdo e revisão antes de cada DELETE.
- Resultados: `QA_OVERLAY_REMOVED 1`, `QA_EVENTS_REMOVED 1`, `QA_SOURCE_REMOVED 1`, `TASKS_PRESERVED 281`, `QA_CLEANUP_VERIFIED`, `people=0`, FK check=0, nenhuma linha QA remanescente. `trello/cards` (395) não foi tocado.
- Navegação original da UI restaurada ao chat `#/20261107_175035_62899b`.

## Qualificação e pendências
- PASS: fluxo UI real selecionar → editar → salvar → readback; navegação para outra view e retorno com persistência; leitura da mesma alteração pela ferramenta real do agente; histórico e CAS; limpeza isolada; originais intactos.
- HOLD: restart completo do Desktop/backend para provar recarga entre processos. Existe sessão alheia em andamento no mesmo Hermes; o chat de homologação System 1 passou a `Task blocked — needs your input` com `outcome_not_verified`, `blocking_pending_items` e `verification_evidence_missing`. Nenhuma reinicialização autorizada; não interferir no ledger, leases ou BrowserTask.
- Risco: backend do host tem processos Python com SQLite 3.53.4 e 3.50.4; esta última versão tem aviso de risco de WAL-reset no próprio Hermes. `local-edits.sqlite` e `agent-generated.sqlite` existentes estão em WAL. Não converter WAL com conexões abertas nem afirmar mitigação em processo antigo; agendar parada controlada e atualizar o interpretador servido pelo Desktop.
- E2 cron: `catch_up_missed=True` efetivo; teste dirigido para 06/11 09h → 07/11 17h recuperou exatamente um claim e reancorou 08/11 09h. Suíte focal 44 passed em Python normal e na venv.
- E3 Browser Trello: Navegador nativo foi aberto **somente para inspeção**; Task Rail mostrava WORKING=1 ligado a System1 e tab ativa `Hermes System 1 — Alvo único`, `http://127.0.0.1:18791`. Nenhuma URL/tab Trello foi aberta, nenhuma navegação da página externa, nenhum controle tomado, nenhuma mutação remota. Após restauro do chat, tarefa System1 estava `Task blocked — needs your input` com verificação pendente. Estado do Browser não qualificado como livre; Trello E3 HOLD.
- E4 sync bidirecional e E5 job diário: NÃO implementados/ativados. Nenhum cron Trello foi cadastrado; atual `list_jobs()` retornou `[]` no perfil inspecionado.
- Próximo gate: resolver operação/lease do Browser ativo sem repetir efeito incerto; confirmar sessão Trello autenticada no Browser nativo disponível e realizar leitura real repetível de um cartão em aberto. Depois desenvolver pull/diff seguro por campo, push verificado e cron único. Não reiniciar para contornar bloqueio; não usar sessão Chrome externa ou conector Trello ChatGPT como evidência de Browser nativo.
