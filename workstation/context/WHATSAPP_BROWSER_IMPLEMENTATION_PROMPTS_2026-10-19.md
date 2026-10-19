# WBR — 5 prompts executáveis (19/10/2026)
Status: PLANO; nenhum destes patches foi aplicado por este documento.
Leia o contexto técnico em WHATSAPP_BROWSER_DOGFOOD_RECOVERY_2026-10-19.md. Execute somente na branch feat/d049-browser-80-20-impl-20261018. Não criar outro branch/DB de autoridade/browser, não sobrescrever worktree de terceiros, não publicar dados do WhatsApp.

## PROMPT 1 — sincronização local obrigatória + deadlock do Browser (P0A)

Você é IA implementadora, não apenas auditora. Repo kevynlucasprofissional-stack/hermes-agent. Desktop Windows em C:\Github\hermes-agent. Comece SINCRONIZANDO alterações que o ChatGPT publicou via GitHub nesta branch, antes de qualquer código.

Execute PowerShell:
~~~powershell
Set-Location 'C:\Github\hermes-agent'
git remote -v
git branch --show-current
git rev-parse HEAD
git status --porcelain=v1 -uall
git worktree list --porcelain
git fetch origin feat/d049-browser-80-20-impl-20261018
git log --oneline --left-right HEAD...origin/feat/d049-browser-80-20-impl-20261018
git diff --name-status HEAD..origin/feat/d049-browser-80-20-impl-20261018
~~~
Se e somente se branch correta, fast-forward possível, arquivos locais preservados e ausência de colisões, execute:
~~~powershell
git merge --ff-only origin/feat/d049-browser-80-20-impl-20261018
git rev-parse HEAD
git status --porcelain=v1 -uall
~~~
Confirme presença local de workstation/context/WHATSAPP_BROWSER_DOGFOOD_RECOVERY_2026-10-19.md. Se houver conflito, NÃO reset --hard, clean, rebase, force, stash ou overwrite automático. Use checkout isolado somente se seguro; documente bloqueios. Nunca apagar arquivo não rastreado ou trabalho de outra IA.

Implemente P0A com testes RED antes do patch. Leia SOMENTE apps/desktop/electron/workstation-browser-runtime.ts (pointScript, resolvePoint, clickRef, executeControlRequest, normalizeWorkstationControllerError), workstation-browser-session-state.ts (BrowserMutationAdmission, admitBrowserMutation, pendingBrowserMutation, save), e testes admission/recovery/persistence. Bug observado: ref @e22 -> stale_or_unknown_ref, admission sem receipt, onze mutações travadas por reconciliation_required apesar de snapshots funcionarem. Mapear token literal stale_or_unknown_ref para STALE_REF/RESNAPSHOT, mas isso NÃO resolve a admission. Implementar terminal durável NOT_DISPATCHED em BrowserMutationAdmission quando e SOMENTE quando uma exceção TIPADA de resolução de ref antes de scroll/focus/input prove ausência de efeito. CAS por identidade completa sob lock, gravação e fsync, não apagar registro nem fabricar acknowledged/receipt; falha de persistência mantém fence. pending ignora somente terminal comprovado; reexecução do mesmo opId retorna terminal sem clicar; novo opId com ref atualizada pode avançar. Pós-scroll/focus/CDP/timeout continua incerto e bloqueado. Não confiar só em Error.message. Reavaliar criticamente snippets do WBR e adaptar se solução melhor.

Testes obrigatórios: stale pre-page-effect libera próxima nova operação, 0 dispatch; erro pós mousePressed permanece blocked; crash antes/depois de terminal; fsync fail-closed; opId collision; multi-task/tab; legacy admission; replay sem duplicação. Rodar testes focados Electron, typecheck/build viável e git diff --check; commit/push sem force apenas caminhos próprios. Registrar SHA inicial/final, resultados PASS/FAIL/SKIP e STATUS (unit tested não significa external E2E). Não fazer merge main.

## PROMPT 2 — impedir fuga de navegador (P0B)

Na MESMA branch, fetch/status e ff-only seguro antes da tarefa; não limpar/rebasear/modificar arquivos alheios. Ler WBR e somente model_tools.py, toolsets.py, tools/browser_use_cli.py, tools/browser_workstation.py, tools/browser_tool.py nos trechos de roteamento e testes relevantes. Problema: browser_exec foi ESCOLHIDO explicitamente depois de falha em browser_* electron-chromium; não foi fallback automático do router. Implementar policy determinística e guard tanto no tool schema quanto no dispatch: sessão/TaskRun/BrowserTask vinculada ao Electron jamais pode acionar browser_exec, Chrome subprocess, perfil ou CDP paralelo como tentativa de recuperação, inclusive após compactação/troca de modelo/restart; outras sessões não vinculadas mantêm compatibilidade. Controller unavailable: fail-closed. Admission incerta: bloquear sem retry mutador, devolver causa, operationId e procedimento humano. STALE_REF realmente pré-efeito: resnapshot e no máximo uma nova tentativa com ref nova dentro da mesma aba/lease; jamais repetir opId incerto. Evitar loops.

RED/GREEN: sessão bound invocando browser_exec rejeitada; unbound preservado; duas sessões; compaction; restart; controller down; stale vs uncertain; nenhum novo Chrome iniciado. Rodar testes Python e Electron focados, diff --check, commit/push sem force e atualização factual no journal. Não criar outro BrowserRuntime.

## PROMPT 3 — inventário completo SEM abrir chats (P1A)

Na mesma branch, fetch/status/ff-only seguro. Leia WBR; somente runtime browser_extract_items, browser_snapshot, scroll, snapshot views/cache/batch e adapters existentes. Implementar adaptador mínimo de INVENTÁRIO de WhatsApp Web que não abre conversas, não clica linhas, não marca lida, não usa APIs privadas, não envia, não altera dados externos. Filtro Não lidas mostra número de CONVERSAS, não de mensagens. Guardar baseline antes de abertura de chat; percorrer container scrollável real sob #pane-side e role=grid/row, incluindo rows virtualizadas, janelas sobrepostas e estado de rolagem; data-testid cell-frame-container, cell-frame-title, icon-unread-count são pistas sujeitas a drift. Não considerar DOM parcial como cobertura total. Validar topo/fim, janelas, estabilidade e contagem; se mudança concorrente ou identidade ambígua, resultado partial/unstable. Nomes não são chatIDs; usar chave local de observação + collision flag. Não transmitir conteúdo privado ao modelo; retornar metadados resumidos e provenance.

Saída: scan_run_id, initial_unread_conversations, observed_conversations, unread_messages_observed, count_unknown, opened_chats=0, windows_scanned, coverage complete|partial|unstable, mismatches e timestamps. Fixtures: HTMLs de 10/10 somente como referência estrutural; testes de SPA sintética com 55+ chats/23 rows visíveis, homônimos, rerender, scroll, badge mutante, interrupção/retomada, bytes/tokens medidos. Dados reais jamais entram no GitHub público. RED/GREEN, commit/push escopados, evidências e limites.

## PROMPT 4 — persistência operacional ACIRV (P1B)

Na mesma branch, fetch/status/ff-only seguro. Leia WBR e diretrizes One Hermes State. Inspecione com cuidado a pasta local privada C:\Github\ACIRV-Notebook\000-Arquivos-originais\Controle redes sociais\Whatsapp\Controle WhatsApp. Inicialmente somente leitura. O SQLite é registro operacional de comunicações, NÃO segundo authority store de TaskRun. Não copiar HTML, JSON, bancos, contatos ou mensagens para repo GitHub público. Sem acesso à pasta, implemente apenas schema/migração com fixtures sintéticas, marque migração real NOT RUN.

Corrigir schema.sql vs .db, constraints UNIQUE válidas para ON CONFLICT, FK, índices, busy_timeout, transações curtas, WAL quando apropriado, versionamento, backups e migrações forward-only. Modelar observation_run, conversation_observation, message_observation, task_candidate, outbound_intent com default pending_authorization, source/provenance/confidence/timestamp e link Trello apenas se autorizado. Se não existir chatId real permitido, use observation_key local e marque ambiguidade; não inventar IDs ou duplicar/destruir linhas semelhantes. Nunca interpretar delivered/read por ausência de confirmação. Testar import repetido, schema inválido, lock, rollback, migração, identidade homônima, mensagem de mesmo texto e concorrência. Backup antes de alterar banco real; sem envios WhatsApp e sem Trello externo não autorizado. Commit/push somente código genérico e documentação, não dados pessoais.

## PROMPT 5 — integração e qualificação fim-a-fim (P2)

Mesma branch, fetch/status/ff-only seguro. Leia WBR e diffs dos commits de 1–4. Executar bateria de integração: Electron nativo + TaskRun vinculada + inventário fixture 55 chats virtualizados antes de qualquer chat aberto; stale @eN gera terminal NOT_DISPATCHED seguro e recupera mesma aba, erro após mousePressed mantém fence, restart preserva operações e checkpoints, tentativa browser_exec é barrada, import SQLite idempotente; 0 duplicação, 0 mensagem enviada, 0 troca silenciosa de backend. Simular alteração do badge, chat homônimo, suspensão e retomada. Testar typecheck, build, testes unitários e integração; E2E do WhatsApp real somente com autorização explícita; nunca simular prova real. Medir bytes/tokens model-facing e latência p50/p95 apenas se instrumentação existir; não inventar ganho.

Atualize ROADMAP, engenharia CURRENT, inteligência, known issues, decisions e state com fatos pós-commit, gate separando PLANNED, IMPLEMENTED, UNIT_TESTED, CI_QUALIFIED, EXTERNAL_E2E. Reporte SHAs antes/depois, commits/push, caminhos, comandos e PASS/FAIL/SKIP, aceites satisfeitos e pendências. Proponha correções de divergência somente se reproduzíveis; não reabrir arquitetura inteira, não fazer merge main, sem release se gates não foram alcançados.

## Contrato em todas as etapas

A IA deve agir como implementadora crítica: julgar nossas sugestões, aceitá-las se adequadas e modificá-las se comprovar opção superior, sem perder os invariantes. As cinco etapas são finitas, não gerar prompts intermináveis. Se faltam testes/infra, entregue código parcial honesto e próximos bloqueadores. Repita cada etapa somente se seu gate obrigatório falhar, e não reescreva trabalho já qualificado.
