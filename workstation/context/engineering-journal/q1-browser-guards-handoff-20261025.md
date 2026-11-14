# Q1 — Browser guards: RED, teste focal e HOLD (25/10/2026)

**Estado:** RUNTIME_HOLD / PATCH_PREPARED / NÃO QUALIFICADO. Não foi alterado código de produção, testes existentes, branch nem commits.

## Checkout e ownership

- Repositório: `C:\Github\hermes-agent`, branch `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e` (revalidar).
- A árvore já continha alterações de outros agentes; `tools/browser_workstation.py` está modificado e sob claim ativo `chatgpt-whatsapp-m3`. Os documentos centrais ROADMAP, Intelligence e CURRENT também estão reclamados pelo M3.
- Não há Stage A/H-079 qualificada ou exceção expressa específica para Q1; dispensa histórica de M3 não autoriza esta missão.
- Ler na retomada `AGENTS.md`, `workstation/AGENTS.md`, `tools/AGENTS.md`, `tests/AGENTS.md`, `workstation/context/README.md` e `UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md`. Não fazer reset/stash/switch nem escrever em arquivo de outro owner.

## Constatações verificadas no código

- `tools/browser_workstation.py::_validate_navigation` (L600–629) já protege segredo, cloud metadata e website policy; `_normalize_navigation_target` (L573–592) interpreta textos como pesquisa externa.
- `_dispatch` (L896–1110) já valida TaskRun, envia pelo transporte existente, registra telemetria, redige e projeta payload. `workstation_routed_browser_handler` (L1252–1318) já verifica lease humano e impede fallback depois de selecionar Browser nativo.
- `workstation/browser_guards.py::GuardRegistry.run_all` é async e aparentemente experimental/não ligado ao dispatcher síncrono. `binding_guard` rejeita browser_snapshot sem task/run; `navigate_scheme_guard` rejeita entradas aceitas pelo canônico. Não introduzir esse middleware indiscriminadamente.
- `workstation/browser_error_messages.py::classify_browser_error` não é substituto direto de `WorkstationBrowserError`; sem prova de uso real/RED, não inserir pipeline paralela.

## Probes read-only — sem acesso a site ou envio real

- `_validate_navigation` ACEITOU `about:blank`, `search cats` (normalizou para DuckDuckGo), `localhost:3000/health` (normalizou para HTTP local) e `https://example.org`. `navigate_scheme_guard` REJEITOU os três primeiros com `NAV_DISALLOWED_SCHEME`. Este é um **RED do guard proposto**, não evidência de rejeição indevida já ocorrendo em produção.
- `_validate_navigation` ACEITOU `file:///C:/private.txt` e normalizou para URL de busca externa. O teste da própria `_dispatch`, com `_request_json` substituído em memória, recebeu payload para `https://duckduckgo.com/?q=file%3A%2F%2FC%3A%2Fprivate.txt`. **Nenhuma requisição externa real foi feita.** Isso mostra que uma URI local explícita pode ser encaminhada para pesquisa, risco de exposição de caminho. A intenção de produto para esquemas não web precisa ser confirmada.
- Também se demonstrou que `binding_guard` rejeita `browser_snapshot` sem task/run, enquanto o roteador permite casos read-only legítimos (testes existentes). Não ligá-lo sem escopo.

## Testes pelo runner canônico (Git Bash + HERMES_PYTHON de .venv)

Comando:
`scripts/run_tests.sh workstation/tests/test_browser_workstation_route.py workstation/tests/test_browser_session_run_isolation_p0.py workstation/tests/test_browser_operational_admission.py -j 2 -q`

- `test_browser_workstation_route.py`: **18 PASS**.
- `test_browser_session_run_isolation_p0.py`: **8 PASS, 2 FAIL**:
  1. `test_unrelated_blocked_kanban_task_does_not_bind_browser_session` — `run_id` inesperado no payload de sessão sem vínculo canônico.
  2. `test_session_only_browser_command_does_not_borrow_process_env_run` — mesmo assert (`run_id` presente).
- Linha correlata: `tools/browser_workstation.py` L972: `effective_rid = rid or session_id ...`. Há um conflito entre a expectativa histórica do teste e o contrato efetivo de identidade; **não eliminar essa expressão só para produzir GREEN** antes de verificar o Electron `workstation-browser-task.ts::bindRun` e receipts. Pode ser regressão ou teste desatualizado; decidir por evidência.
- `test_browser_operational_admission.py`, execução ampla: **timeout 300s SIGKILL**, arquivo não qualificado. O resumo do runner foi **26 PASS / 2 FAIL / 1 arquivo timeout**, não “todos os testes falharam”.
- Reexecução focada: `scripts/run_tests.sh workstation/tests/test_browser_operational_admission.py -k p0_7 -j 1 -q --file-timeout 180` → **2 PASS, 0 FAIL** (aprox. 10s de subprocess). Cobriu os dois testes P0_7 sobre timeout e retry incerto; não qualifica toda a suíte de admission nem a operação no Browser real.
- Avisos: Laya ausente ao importar em probe isolado; SQLite vinculado 3.50.4 mitigou risco WAL-reset usando DELETE journal no ambiente de teste; nenhum deles foi demonstrado como causa dos asserts.

## Patch independente criado (NÃO aplicado)

Arquivo: `workstation/context/q1-browser-guards-reference-20261025.patch`

- Alvo: `tools/browser_workstation.py::_validate_navigation`. Bloquear esquemas explícitos `file/javascript/data/blob/filesystem` com `WorkstationBrowserError` canônico, antes de criar URL de busca. Preservar `about:blank`, pesquisa livre e localhost.
- Testes novos preparados em `workstation/tests/test_browser_workstation_route.py`: 5 entradas de esquema negadas antes de `_request_json` e 3 entradas válidas preservadas.
- `git apply --check -- workstation/context/q1-browser-guards-reference-20261025.patch` → **exit 0** na fotografia deste checkout. **Nenhum `git apply` foi executado.** No próximo checkout, verificar hunk e intenção de política antes de aplicar.

## Gate objetivo e ordem segura

1. **Owner M3:** fechar/reconciliar os dois testes RED de isolamento no contrato Python↔Electron, com prova de ausência de atribuição de run errado e de preservação dos fences e admissions. Não confundir o `run_id` sintético com autoridade de TaskRun. 
2. **Owner/Stage A:** transferir formalmente claim de `tools/browser_workstation.py` quando M3 acabar; qualificar H-079 Stage A ou obter exceção expressa específica de Q1 registrada pelo owner do estado/jornal canônico.
3. Confirmar política de esquemas não web e somente então aplicar ou aperfeiçoar patch preparado. Antes, demonstrar RED nos casos de URL de risco; depois GREEN no mesmo teste, rota, lease, STALE_RUN, UNCERTAIN, redaction.
4. Se nenhum ganho comprovado vier de `GuardRegistry`, deixá-lo não conectado e documentar **NO_CHANGE nessa parte**. Não usar `asyncio.run` dentro da rota síncrona, nem segundo Browser executor.
5. Reexecutar pelo runner canônico testes seletivos e regressões. A suíte ampla de admission ficou em TIMEOUT e precisa ser isolada, não ignorada.
6. Preservar claims de todos os outros agentes, não enviar mensagem externa, nem efetuar commit/merge sem integrador designado.

## RESUME PROMPT

> Continue Q1 no Hermes em `C:\Github\hermes-agent`, branch `main` (HEAD observado `f1d5ab2f030e940ed4571371b0de45a21a009c9e`; revalidar). Leia primeiro este journal `workstation/context/engineering-journal/q1-browser-guards-handoff-20261025.md` e `workstation/context/q1-browser-guards-reference-20261025.patch`. Não reinvestigue genericamente. Os dois REDs de `test_browser_session_run_isolation_p0.py` são por `run_id` inesperado em chamadas somente com `session_id`; M3 reivindica `tools/browser_workstation.py`. Reconcilie Python `effective_rid` e Electron `bindRun` antes de mudar esse comportamento; preserve o fence. Confirme política de `file:` explícito normalizado indevidamente como pesquisa DuckDuckGo; patch pronto em arquivo isolado, validado por `git apply --check` mas NÃO aplicado. A rota existente já protege TaskRun, lease e redaction; não adote `GuardRegistry` async integralmente. Pré-condições: branch, HEAD, estado sujo, claims, AGENTS e Stage A/exception **desta** missão. Quando ownership e autorização permitirem, reproduza RED→GREEN e implemente a menor correção. Use `scripts/run_tests.sh` via Git Bash, inclusive as suítes de rota/isolamento e `-k p0_7`; suíte completa de admission teve timeout 300s. Não fazer reset, stash, switch, envio externo, blind retry, bypass de lease nem alterar claims alheios. Documente resultados, owners e GO/HOLD. Se parar de novo, entregue outro resume prompt atualizado.
