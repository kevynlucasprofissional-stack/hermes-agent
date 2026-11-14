# P03 — Handoff de integração e documentação canônica (2026-10-27)

**Estado verdadeiro:** P03 código LOCAL_IMPLEMENTED, dry-run no Cron real com fixture persistido, teste focado 72 PASS; Bot Cron **PAUSED**; LIVE API Trello, LLM real, Bot Chat, CI/Stage A NOT QUALIFIED; RELEASE HOLD.

## Preflight e ownership
- Branch `main`; HEAD inicial `f1d5ab2f030e940ed4571371b0de45a21a009c9e`; sem branch/worktree novo, sem reset/stash/checkout/commit/push.
- Owner código/documentação P03: `chatgpt-trello-daily-brief-p03` (claim exata para quatro novos arquivos de código/testes e duas documentações isoladas).
- `workstation/trello_action_journal.py` já integrado no P02 está claimed por `chatgpt-trello-incremental-p02` READY_FOR_INTEGRATION; foi apenas lido. Banco `WorkstationKanbanBridge` permaneceu intacto.
- `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md`, `workstation/context/engineering-journal/CURRENT.md` e `KNOWN_ISSUES.md` seguem claimed por `chatgpt-whatsapp-m3` ACTIVE, mesmo com agente offline. **Não sobrescrever**: inserts abaixo para o owner/document integrator.

## Inserir no ROADMAP (pelo owner documental)
`HW-IMP-03 LOCAL_IMPLEMENTED / PAUSED_CRON_CREATED / NATIVE_CRON_FIXTURE_GREEN / LIVE_TRELLO_NOT_TESTED / BOT_CHAT_NOT_TESTED / RELEASE_HOLD.`
Produção em `workstation/trello_daily_brief.py` e `workstation/trello_daily_brief_cron.py`: fatos UTC e timezone local, bounds max 200 eventos, sem conteúdo bruto, prompt editorial protegido de prompt injection, rendering determinístico e SHA de proveniência. Bot profile oficial `trello-relator` criado, Cron `af77883863f8` no quadro `GDM8ZE3r` com cron expression `0 8 * * 1-5` mas PAUSED, `deliver=local`, `model/provider` sem pin; saiu relatório fixture persistido, sem comunicação externa. Dependências: qualificação P02 live + modelo/credenciais Cron bot + timezone Cron + Bot Chat, não bloqueiam prosseguir para prompts independentes se gates próprios.

## Inserir em INTELLIGENCE
A narração diária usa somente `trello_activity_event`, não o estado atual dos cartões nem texto de comentários. Uma ação `updateCard` com ID de lista anterior/nova diferente indica movimento entre IDs; sem esses metadados a natureza é desconhecida (não inferir renomeação). Comentário informa ocorrência sem conteúdo. Contagem de eventos não prova contagem de tarefas, conclusão, responsável ou intenção. Toda frase ancorada a `[action_id]`. Fonte = journal P02; sem consulta Trello real. Dados de ações são tratados como evidência não confiável, não instructions. `render_brief_prompt` separa instruções confiáveis de JSON de metadados.

## Inserir no ENGINEERING JOURNAL/CURRENT
- TDD RED: import de módulo P03 ausente; subprocesso real Cron não conseguia importar `workstation` a partir do diretório `scripts`; registro do Cron falho deixava script recém-criado órfão. GREEN corrigiu todos.
- P03 unit/integration: 17/17 PASS, exit 0. Matriz focada P03/P02/Cron `tests/cron/test_atomic_paused_creation.py`, `test_cron_context_from.py` + demais suítes => 72/72 PASS, exit 0.
- `python -m compileall -q` P03 => exit 0; `git diff --check` P03 => exit 0; Ruff no Python 3.13 indisponível (NOT TESTED).
- Suite ampliada somou 102 PASS e 6 FAIL, exit 1. Isoladamente `tests/gateway/test_webhook_cron_trigger.py` teve 2 PASS / 4 FAIL, por falta de plugin `pytest-asyncio` no Python usado; `tests/cron/test_cron_empty_payload.py::test_run_job_does_not_block_a_valid_no_agent_job` falhou isoladamente (Windows/bash/runner legado a investigar). `TestExecuteJobForEvent.test_ambiguous_ref_returns_error` falhou apenas na matriz combinada anterior; precisa investigação de ordem/fixture antes de afirmar causa. Não alterar suites upstream por esta tarefa.
- Perfil real `C:\Users\Kevyn Lucas\AppData\Local\hermes\profiles\trello-relator` criado via `hermes profile create trello-relator --no-alias --no-skills`. Cron real `af77883863f8` criado via `cron.jobs.create_job`, `enabled=false`, `deliver=local`, sem modelo/credencial configurados.
- Dry-run com SQLite temporário e três eventos **SINTÉTICOS**, saída persistida em `...\cron\output\af77883863f8\2026-10-27_01-32-57.md`, SHA `54e5ff2f06edd62a7401f75914884a6aeb63c9172bccd3bb3e66b833f15ca814`, evento count=3. Zero envio externo, zero inferências LLM reais. Perfil criado pelo CLI: Bot Mode tile e chat ainda não comprovados.

## Inserir KNOWN_ISSUES
`HW-TRELLO-DAILY-P03`: report determinístico local qualificado em fixture; LIVE P02 feed/real Cron scheduled Bot Chat/LLM model/CI pending. Bot criado sem `config.yaml`, provider ou API keys; **não resumir Cron** sem configurar model e timezone e verificar consentimento. `deliver=local` só persiste em saída de Cron, não entrega no Bot Chat; execução no Bot Chat é outro gate. Prompt narrativa restringe conteúdo, mas não há verificador automático do texto livre de LLM (não declarar ausência de alucinação por prompt). Falhas legadas no gateway/webhook e shell Windows não resolvidas. Bootstrap histórico P02 > limite permanece separado; WA-M3-01 segue HOLD.

## Reversibilidade e segurança
Bot/profile foi criado sem aliases, sem copiar credenciais/skills, sem configuração de modelo. Cron pausado `af77883863f8` é listável/removível por CLI sob perfil `trello-relator`; script `scripts/trello_daily_brief.py` próprio só deve ser removido após remover/verificar referências de Cron. Não excluir o perfil sem autorização. Não executar jobs reais em background. Não conectar Bots ao WhatsApp.

## Resumo do que precisa antes de promoção
1. Owner documental incorpora inserts, preservando WIP do M3. Definir integrador Git, apenas ele faz commit/push.
2. Qualificar leitura P02 API real, bootstrap e vinculação do SQLite canônico do Bot vs Workstation.
3. Configurar modelo/provider seguro + timezone real no perfil `trello-relator`, testar o `cron_job` em scheduler completo sobre fixture isolada com fake LLM (não somente `cron.scheduler.run_job` no modo `no_agent`) e evidência persistida.
4. Validar target Bot Chat interno se desejado; só então considerar `deliver=bot-chat:trello-relator` mediante consentimento, nunca WhatsApp automático.
5. Investigar falhas pré-existentes e qualificar CI/Stage A/release. Até lá, `PAUSED` e `RELEASE_HOLD`.

## Fonte de continuidade
`workstation/context/TRELLO_DAILY_BRIEF_20261027.md` é o registro operacional completo e determinístico. Este handoff fornece os inserts exatos ao owner dos documentos oficiais; não é necessário voltar ao Prompt 02 para continuar trabalho de desenvolvimento P03.
