# Hermes Work — P03 / Trello Relator diário (2026-10-27)

**STATUS:** implementação local em código e Bot/Cron pausado criados. **P03 LOCAL GREEN (72 testes focados); LIVE TRELLO/LLM/BOT CHAT NÃO QUALIFICADOS; RELEASE HOLD.** A continuação extra de P02 é um gate de qualificação de produção, não um prompt que substitui P03. O usuário enviou ambos, e a execução selecionou P03 porque P02 já havia alcançado GREEN sintético.

## Bot e Cron realmente registrados

- Perfil criado pelo **CLI oficial**: `trello-relator`, diretório `C:\Users\Kevyn Lucas\AppData\Local\hermes\profiles\trello-relator`.
- Criação sem alias e sem copiar skills/credenciais; `SOUL.md` incrementado com regras de narração factual e proibição de envio externo.
- Cron job **existente de verdade**: ID `af77883863f8`, nome `[bot:trello-relator] Trello factual diário`, quadro `GDM8ZE3r` (SCRUM da ACIRV), `script=trello_daily_brief.py`.
- Schedule configurado `0 8 * * 1-5` **PAUSADO** (`enabled=false`, `next_run_at=null`). `deliver=local`, `no_agent=false`, `enabled_toolsets=[]`, `job.model=null`, `job.provider=null`: scheduler existente herda `cron.model` e `cron.model_provider` do perfil quando disponíveis; o perfil recém-criado está sem `config.yaml`/modelo e chaves de API. **Não retomar antes de configurar e validar.**
- É um perfil oficial Hermes; a exibição como tile no **Bot Mode Desktop** não foi validada. `deliver=local` salva em Cron/output, **não** é entrega em Bot Chat; primeiro teste de Bot Chat interno depende de qualificação e configuração apropriadas.
- Nenhum agendamento foi ativado, nenhum Trello GET live, nenhuma chamada LLM real e nenhum WhatsApp/Telegram/envio externo.

## Código novo — contrato e ponto de entrada

- `workstation/trello_daily_brief.py`:
  - `collect_brief_facts(conn, board_id, period_start, period_end, max_events=200)`: consulta SELECT-only em `trello_activity_event` no **SQLite canônico delegado ao P02**, ordena por `(event_time,action_id)`, filtra janela UTC [início,fim), conta eventos/tipos, inclui `board_id`, `action_id`, `card_id`, `actor_id` e IDs de listas; não consulta títulos, comentários nem lista `tasks`.
  - `local_day_window(day,timezone_name)` converte meia-noite local em UTC inclusive em dias com horário de verão; a expressão de agendamento segue timezone de configuração própria do Hermes Cron, que deve concordar com a timezone do resumo.
  - `render_brief_text(facts)` gera relatório determinístico; diferencia mudança entre listas com IDs de `listBefore/listAfter`, mas não afirma cartão concluído. `updateCard` sem metadados de listas é alteração de natureza indisponível (não inferir renomeação); `commentCard` registra ocorrência sem conteúdo. Ausência de eventos não é ausência de trabalho.
  - `render_brief_prompt(facts,instructions)` isola evidências em JSON serializado rotulado como dados não confiáveis; só inclui metadados allowlisted. Modelo externo só é chamado em `generate_brief_with_llm(facts, fake_or_real_llm)` por callback **explícito**.
  - `build_daily_brief` acrescenta SHA256 determinístico do conjunto factual.
- `workstation/trello_daily_brief_cron.py`: `main` para script do Cron, `prepare_paused_cron_job` registra via **`cron.jobs.create_job` existente** dentro do perfil especificado, e `register_dry_run` persiste saída via **`cron.jobs.save_job_output` existente**. Sem novo provider, framework, scheduler, banco de dados ou ferramenta núcleo.
- `workstation/tests/test_trello_daily_brief.py`; `workstation/tests/test_trello_daily_brief_cron.py`: testes de observação, fronteiras do período, board isolation, dedupe, privacidade, prompt injection, fake LLM, Cron store isolado, modelo herdado, native `scheduler.run_job` subprocess, saída local e reversão na falha de registro.
- Nada foi editado em `tools/cronjob_tools.py`, `cron/scheduler.py`, `cron/scheduler_delivery.py`, `cron/jobs.py`, `workstation/kanban.py`, `workstation/trello_action_journal.py` ou no executor WA.

## Dry-run persistido no perfil real (somente fixture)

O código testou acesso a uma base SQLite temporária com três **ações fictícias**, nunca dados reais do Trello. O resultado foi salvo com a API de Cron:

`C:\Users\Kevyn Lucas\AppData\Local\hermes\profiles\trello-relator\cron\output\af77883863f8\2026-10-27_01-32-57.md`

`event_count=3`, `evidence_sha256=54e5ff2f06edd62a7401f75914884a6aeb63c9172bccd3bb3e66b833f15ca814`. O relatório abre com **DRY-RUN DE FIXTURE SINTÉTICA — NÃO É HISTÓRICO REAL**; inclui três IDs de ação sintéticos e desconhece os títulos/descrições. O arquivo de teste do SQLite era temporário e não foi ligado à conta Trello.

## Testes executados e resultados

- P02 pré-condição: `python -m pytest -q workstation/tests/test_trello_action_journal.py workstation/tests/test_trello_board_actions.py` -> **29 PASS**, exit 0.
- P03 TDD RED: `test_trello_daily_brief.py` falhou inicialmente por módulo ausente; `test_trello_daily_brief_cron.py` falhou inicialmente por módulo ausente e depois reproduziu erro de import no subprocesso; ambos corrigidos. Outro RED comprovou script órfão após falha de registro; correção preserva script usado em job existente.
- GREEN P03: `python -m pytest -q workstation/tests/test_trello_daily_brief.py workstation/tests/test_trello_daily_brief_cron.py` -> **17 PASS**, exit 0.
- GREEN conjunto focado com Trello e Cron: `python -m pytest -q workstation/tests/test_trello_daily_brief.py workstation/tests/test_trello_daily_brief_cron.py workstation/tests/test_trello_action_journal.py workstation/tests/test_trello_board_actions.py workstation/tests/test_trello_concurrent_edit_protection.py tests/cron/test_atomic_paused_creation.py tests/cron/test_cron_context_from.py` -> **72 PASS**, exit 0.
- Matriz ampliada também incluiu `tests/cron/test_cron_empty_payload.py` e `tests/gateway/test_webhook_cron_trigger.py`: **102 PASS, 6 FAIL**, exit 1. Na reexecução isolada, a suíte webhook terminou 2 PASS/4 FAIL por ausência de plugin pytest-asyncio (funções `async def` não suportadas pelo runner); `tests/cron/test_cron_empty_payload.py::test_run_job_does_not_block_a_valid_no_agent_job` segue FAIL isolada (script .sh e ambiente Windows precisam de análise), e `test_ambiguous_ref_returns_error` falhou somente na matriz conjunta anterior (interferência/ordem não comprovada). Não mudar esses testes sem investigação e gate próprio.
- `python -m compileall -q` P03: exit 0. `git diff --check --` arquivos P03: exit 0. Ruff não instalado neste Python, portanto **LINT UNKNOWN**.
- Sem CI/Stage A pleno; autorização anterior de pular H-079 foi considerada exclusivamente local, não release.

## Modelos, custos e ativação

O dry-run determinístico e o Cron `no_agent` fake usaram **0 chamadas de LLM**, custo de inferência observado R$ 0. O prompt para LLM foi testado com callback fake apenas; volume de tokens/custo em operação real dependem de `cron.model`, `cron.model_provider`, tamanho do journal do dia e preço do provider (não medidos). O profile `trello-relator` não possui `config.yaml`/modelo nem credenciais; selecionar model/provider antes de qualquer tentativa agent-backed real.

Para uso ativo, revisar os gates: (1) P02 leitura API Trello live, bootstrap e autorização do banco; (2) identidade/autorização do board e periodização; (3) Cron timezone correto, modelo e credenciais do Bot; (4) decisão de destino interno `local` ou `bot-chat:<profile>` após validado — nunca auto WhatsApp; (5) execução manual com readback e confirmação de persistência; (6) só então autorizar `resume_job`. Até lá, job permanece PAUSED.

## Reversão segura

Job criado em `trello-relator`: pausar é estado atual; `hermes -p trello-relator cron list` exibe o estado. Remover apenas por ID confirmado `af77883863f8` usando comandos oficiais Cron depois de autorização; remover script próprio `scripts/trello_daily_brief.py` apenas após verificar que não é referenciado; remoção do perfil é ação destrutiva SEPARADA e **não executada**.

O sample `2026-10-27_01-32-57.md` é arquivo local derivado de fixture; não o tratar como atividade ACIRV. Código e documentação de P02 preservados. Os documentos oficiais estão com claim de `chatgpt-whatsapp-m3` e receberão apenas handoff em `HANDOFF_PROMPT_03_20261027.md`.
