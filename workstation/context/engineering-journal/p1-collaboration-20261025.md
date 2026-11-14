# Hermes Work — P1: consciência coletiva e handoffs — 2026-10-25

ESTADO: IMPLEMENTADO E VALIDADO LOCALMENTE / SEM GIT INTEGRATION / SEM CI OU RELEASE.

## Checkout e ownership
Checkout C:\Github\hermes-agent. Branch main, HEAD na admissão f1d5ab2f030e940ed4571371b0de45a21a009c9e. 11 claims observados antes desta missão; 12 depois da nova claim. Dirty/untracked existente preservado. Claim deste trabalho: agent chatgpt-p1-awareness-20261025, lane p1-awareness-20261025. Paths exclusivos: workstation/scripts/collab_tasks.py, workstation/tests/test_collab_tasks.py e este journal.

Nao foram editados arquivos da P0-A/P0-B, WhatsApp M3 ou Site Ops, nem roadmap, Intelligence, Decisions ou CURRENT. Nenhum commit, push, merge, branch/worktree, stash, reset ou clean.

## Implementação
- Novo módulo workstation/scripts/collab_tasks.py, sem alterar o CLI multi_agent_coordination.py. Subcommands: tasks, conflicts, resume, register, progress e handoff.
- Reusa coordinator.state_root, read_claims, registry_guard, normalize_path e write_json, e admission.verified_session (P0-B) para mutações autenticadas. Ownership/status seguem EXCLUSIVAMENTE owner.json em .hermes-collab/*.claim.
- Materialização read-only de TODAS as claims legadas como tarefas, mesmo sem sessão P0-B ou metadata. Retorna lane, agente, status, paths, testes, dependências, blockers, next_action e stale_suspected, com campos desconhecidos vazios.
- Metadata persistida como eventos append-only de snapshot completo, dentro de .hermes-collab/task-events/<lane>/<revision>.json, escrita por os.replace atômico sob mesmo registry_guard global. Revisões verificadas desde 00000001. Evento incompleto/corrompido falha fechado em update; leitura conserva a claim real e expõe erro no relatório de conflitos.
- Register exige sessão P0-B válida, task_id=lane, título, branch e HEAD. Progress anota next_action, tests, dependencies, blocked_by. Handoff registra request_id idempotente e path repo-relative, sem transferir ownership. Resume é sempre read-only e retorna ownership_transfer NOT_GRANTED.
- Dependências inexistentes ou cíclicas são recusadas. Tokens/token_digest nunca são gravados como eventos. Notes têm limite e recusam indícios de tokens/senhas, endereços de email e números internacionais; não substitui outras medidas de privacidade.
- Heartbeat velho => STALE_SUSPECTED advisory, nunca atualiza status nem libera claim. Depois do release explícito, task antiga pode ser lida como RELEASED, mas o próximo writer exige nova claim e nova sessão P0-B. Não reciclar lane ID com histórico.
- Comandos de consulta são seguros para usuários legados; comandos de anotação P1 só aceitam sessão tokenizada. Fornecer credenciais por variáveis HERMES_COLLAB_SESSION/HERMES_COLLAB_TOKEN no ambiente do processo, nunca em argumentos, logs ou documentos.

## Demonstração CLI
python workstation/scripts/collab_tasks.py tasks
python workstation/scripts/collab_tasks.py conflicts
python workstation/scripts/collab_tasks.py resume --task-id p0a-coordinator-20261025
Após nova sessão P0-B e token em variáveis locais, não neste documento:
python workstation/scripts/collab_tasks.py register --title "Corrigir integração"
python workstation/scripts/collab_tasks.py progress --tests "18 PASS" --next "Revisar interface"
python workstation/scripts/collab_tasks.py handoff --request-id handoff-001 --next "Retomar após revisão"

## Testes
Focados P1: 19 testes passaram, 3 subtests. Incluem registro e replay em novo processo, tarefas legadas, ownership, token falso, dependências/ciclos, handoff idempotente, proibição de transfer sem release, históricos corrompidos, crash com .tmp órfão, stale heartbeat sem roubo, redaction de notas, concorrência real de 6 subprocessos e CLI legada preservada.

Primeira execução do runner canônico: 61 testes PASS / 1 SKIP após retry, mas arquivo P1 com aviso FLAKY. Causa: token URL-safe aleatório podia começar por '-' e ser interpretado por argparse como opção quando passado por --token VALOR. Correção: testes passaram a fornecer credenciais ao subprocesso só via variáveis de ambiente, melhorando também confidencialidade. Após correção, execução canônica SEM FLAKE:
PowerShell definir HERMES_PYTHON pelo python.exe do Windows, substituir barras conforme P0-B.
Git Bash: scripts/run_tests.sh workstation/tests/test_collab_tasks.py workstation/tests/test_collab_admission.py workstation/tests/test_collab_git.py workstation/tests/test_multi_agent_coordination.py -q --tb=short
Resultado: 4 arquivos, 61 passed, 0 failed, 1 skipped em 12.4s; exit 0.
Ruff: ruff check workstation/scripts/collab_tasks.py workstation/tests/test_collab_tasks.py => PASS.
git diff --check sobre alvos => exit 0; observa-se que novos arquivos untracked não estão incluídos no git diff usual; Ruff confirma estilo Python.

Consulta ao checkout real em modo SOMENTE LEITURA: 12 tasks visíveis, 9 eventos STALE_SUSPECTED e zero claims liberados automaticamente. O comportamento é qualificado em fixtures de repositórios Git temporários, sem real commit no Hermes Work.

## Limitações
- P1 não modifica claims legadas, seus donos devem fazer novo registro sob credencial P0-B se quiserem anotação durável adicional; handoffs legados existentes ainda são mostrados por status/next_action do owner.json.
- A trava global é cooperativa e local. P0-B continua opt-in; shell ou MCP irrestrito podem ignorar limites. P2 precisará integrar clientes externos à superfície gerenciada e executar dois clientes reais.
- Não foram executados testes full repo, CI, Stage A de runtime, release ou E2E ChatGPT/Claude MCP. Nenhum documento canônico reclamado foi atualizado.
- Não declarar que o evento de handoff autoriza escrita ou takeover. Timeout de heartbeat não autoriza roubar a reserva.

## Próxima ação
Marcar p1-awareness-20261025 como READY_FOR_INTEGRATION, revalidar Git/claims; integrador explicitamente designado fará a reconciliação quando autorizado. Próxima missão P2 em workstation/context/multi-agent-collaboration-2026-10-25/IMPLEMENTER_PROMPTS.md, sem reabrir P0-A/P0-B/P1.
