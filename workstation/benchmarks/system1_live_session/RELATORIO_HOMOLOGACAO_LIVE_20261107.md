# Homologação ao vivo — System 1 Browser MVP

**Data:** 2026-11-07 (UTC) · **Sessão:** `20261107_175035_62899b` · **Tarefa canônica:** `t_1863c0f1` (run 77)
**Repositório:** `C:\Github\hermes-agent` · **Nenhum commit, push ou merge realizado.**

## Veredito

| Item | Veredito | Base |
|---|---|---|
| Variante A — caminho atual (System 2) em turno humano real | **MEDIDO** | turno da frase em 2026-11-07T21:00:45Z: 2 chamadas ao System 2, 10,88 s de provedor, ref `@e1` validado |
| Variante B — System 1 fast path **end-to-end** com mensagem humana | **BLOQUEADO** | backend vivo sem a flag e sem Laya; trocar exige reiniciar (proibido) |
| Variante C — System 1 **componente**, com snapshots reais do BrowserTask | **EXECUTADO** | 4 cenários, Laya 0.3.23 real, latências medidas |

O objeto central da homologação — comparar, **no mesmo turno humano real**, o caminho atual com o fast path System 1 — **não pode ser executado** nesta máquina sem violar as salvaguardas impostas. O bloqueio é específico e está detalhado abaixo, com os requisitos exatos de desbloqueio.

## 1. Identidade da sessão e condições reais do backend

| Fato | Valor verificado | Como foi obtido |
|---|---|---|
| Sessão | `20261107_175035_62899b` | `HERMES_SESSION_ID` (env do processo do agente) |
| Tarefa canônica de trabalho | `t_1863c0f1` — nasceu `running` (run 77, `created_by=workstation`, contrato `local-only`); em 21:00:14Z passou a **`blocked` / `needs_input`** (`outcome_not_verified; blocking_pending_items; verification_evidence_missing`), `current_run_id` nulo | `kanban.db` (somente leitura) |
| Backend | PID **40584** — `C:\Github\hermes-agent\.venv\Scripts\python.exe -m hermes_cli.main serve --host 127.0.0.1 --port 0`, filho de **electron.exe PID 37124** | `Win32_Process` |
| Intérprete do backend | `C:\Github\hermes-agent\.venv\Scripts\python.exe` (`HERMES_PYTHON`) | env |
| `HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED` | **ausente** (`unset`) → fast path desligado | env do processo |
| Laya no intérprete do backend | **não importável** (`find_spec('laya') is None`) | sonda com o próprio `.venv` |
| Provedor System 1 registrado no backend | **não** (`registered: false`) | sonda de registro com o `.venv` |
| Eventos `SYSTEM1_COMPLETED` desta sessão | **0** | `telemetry.sqlite` |
| Browser nativo | `electron-chromium`, `aiControl: true`, `controlOwner: agent`, sem lease humano | `check-browser-status.mjs` |
| BrowserTask | `20261107_175035_62899b`, tab `a986a8f6-1b75-49c1-8157-a324fb73464f`, `status: parked`, `revision` 1→5 | ledger do navegador |

Nenhum clique foi executado. Todas as operações foram `browser_navigate` / `browser_snapshot` (somente leitura).

**Mudança de estado observada (não provocada por esta homologação):** o próprio layer de verificação do Workstation bloqueou `t_1863c0f1` (`needs_input`, `outcome_not_verified; verification_evidence_missing`) às 21:00:14Z, encerrando o run 77. Consequência para o teste: mesmo com a flag ligada, a condição "tarefa canônica de trabalho ativa" do gate deixaria de valer a partir daí — o desbloqueio end-to-end precisa reabrir a tarefa, não só religar a flag. Nada foi feito para alterar esse estado.

### Recibos reais das aberturas de página

| Página | operationId | taskId | revision | executedAt |
|---|---|---|---|---|
| `/unique` (1ª abertura) | `op_browser_navigate_b6402cd593f8` | `20261107_175035_62899b` | 1 | 2026-11-07T20:54:30.832Z |
| `/partial` | `op_browser_navigate_c6d7f64b3aa2` | `20261107_175035_62899b` | 2 | 2026-11-07T20:56:11.588Z |
| `/duplicate` | `op_browser_navigate_ee3f6742e631` | `20261107_175035_62899b` | 3 | 2026-11-07T20:56:52.009Z |
| `/missing` | `op_browser_navigate_0a80775b3af7` | `20261107_175035_62899b` | 4 | 2026-11-07T20:56:55.791Z |
| `/unique` (estado final) | `op_browser_navigate_4b70f6ae7dab` | `20261107_175035_62899b` | 5 | 2026-11-07T20:57:01.229Z |

## 2. Ambiente isolado (PM) — disponível

| Fato | Valor |
|---|---|
| Projeto PM isolado | `%LOCALAPPDATA%\HermesWorkstation\qualification\system1-laya-project` (gen `79019aa16c2f405ba254edbba3c575d7`) |
| Python | 3.14.7 no venv do gen isolado |
| Laya | **0.3.23**, `source_bytes_verified: true`, sha `4aa6761b`, `is_vendored: true`, model `multilingual`, device `cpu`, calibração `calib-v1-20261002` |
| Router | carrega em ~10,8 ms (lazy) |
| Imports | `run_agent`, `hermes_cli`, `workstation.system1.browser_read_fastpath` OK no venv isolado |
| Flag nesse ambiente | também **não definida** (a flag não foi ligada em lugar algum; só foi lida) |

O venv isolado **é capaz** de hospedar o provedor Laya; o backend vivo **não é**.

## 3. Variante C — componente com snapshots reais (resultados medidos)

Entrada: snapshots nativos reais capturados nesta sessão (`live_snapshots_20261107.json`), intenção `("button", "Relatórios")` — exatamente o alvo dos cenários. Duas passagens por cenário (pass 1 = carga fria do modelo, pass 2 = decisão quente).

| Cenário | Pass | Status | Ref | Motivo | Provedor | Total | Chamadas System 1 |
|---|---|---|---|---|---|---|---|
| `/unique` | 1 / 2 | `verified` | `@e1` | `exact_match` | deterministic | 0,12 ms / 0,07 ms | **0** |
| `/partial` | 1 | `verified` | `@e1` | `system1_proposal` | **laya** | **19.386,9 ms** (carga fria) | 1 |
| `/partial` | 2 | `verified` | `@e1` | `system1_proposal` | **laya** | **217,8 ms** (quente) | 1 |
| `/duplicate` | 1 / 2 | `fallback` | — | `ambiguous_label` | — | 0,03 ms | **0** |
| `/missing` | 1 | `fallback` | — | `model_target_unsubstantiated` | — | 205,8 ms | 1 |
| `/missing` | 2 | `fallback` | — | `model_target_unsubstantiated` | — | 210,3 ms | 1 |

Leitura honesta desses números:

1. **Sem falso positivo nos três cenários negativos.** Duplicidade foi barrada antes de qualquer modelo (`ambiguous_label`). No cenário sem alvo, o Laya **propôs um controle errado** e a guarda de substanciação (`model_target_unsubstantiated`) recusou — o invariante "confiança do modelo não estabelece alvo" funcionou com o modelo real, não só em teste sintético.
2. **Custo do Laya é relevante e não trivial:** ~206–218 ms por decisão quente, e **~19,4 s na primeira inferência** (download/carga do modelo). Numa sessão recém-iniciada, o "fast path" seria mais lento que o caminho atual na primeira chamada.
3. **O caminho determinístico é ~0,1 ms** e resolve o caso exato sem invocar modelo algum — é o único ganho já comprovado nesta máquina.
4. Em `/partial`, a confirmação de `"Abrir relatórios"` para o alvo `"Relatórios"` depende de contenção de substring na guarda. É o comportamento desenhado para leitura somente, mas fica registrado como observação de risco de aceitação semântica ampla.

## 4. Bloqueio específico do System 1 end-to-end

O gate real (`workstation/system1/browser_read_fastpath.py:200-247`) exige, no mesmo turno: flag `=1`, `origin=human`, `intent_authority ∈ {create_work, update_work}`, mensagem idêntica ao envelope, intenção que casa o regex de localização, `browser_snapshot` no toolset, `agent._canonical_work_task_id` e `session_id` preenchidos, e então um dispatch durável de `browser_snapshot` amarrado ao BrowserTask.

Nesta máquina, o **único backend que recebe mensagens humanas** é o PID 40584 (Electron → `.venv`), que tem:
- flag **ausente** → `return None` na primeira linha do gate;
- **Laya não importável** → nenhum provedor System 1 pode ser registrado, mesmo com a flag ligada.

Ligar a flag exige reiniciar esse backend; **reiniciar o Hermes existente é proibido** pela instrução. Um runtime separado também não fecha a malha: o controlador de navegador pertence a uma única instância Electron (bridge `%APPDATA%\Hermes\ai-control-bridge.json`, pid 37124), então um backend "independente" não teria browser próprio sem duplicar esse dono, e a evidência de browser deixaria de ser independente.

### Requisitos exatos para desbloquear

1. Backend iniciado com `HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED=1` **e** um intérprete que importe `laya` (o venv isolado `gen-79019aa…` já satisfaz: 0.3.23, proveniência verificada).
2. `HERMES_HOME` e armazenamento de workstation próprios (sessões, leases, ledger, telemetria) para esse backend.
3. Uma UI que o humano possa digitar, ligada **a esse** backend — sem ela, `origin=human` + `create_work` não acontecem e o gate nunca abre.
4. Dono de navegador próprio para essa sessão (ou autorização explícita para compartilhar o browser do Electron), senão o BrowserTask e os recibos deixam de ser evidência isolada.

## 5. Instrumentação — disponível e confiável

`telemetry.sqlite` grava, por evento e por sessão: `provider_calls`, `tool_calls`, `input_tokens`, `output_tokens`, `duration_ms`, além de `BROWSER_OPERATION_OBSERVED` e `SYSTEM1_COMPLETED`. Portanto a medição de "chamadas reais ao System 2" existe e não precisa ser estimada.

Estado desta sessão no momento do pré-voo: 51 `PROVIDER_CALLED`, 70 `TOOL_COMPLETED`, 18 `BROWSER_OPERATION_OBSERVED`, **0 `SYSTEM1_COMPLETED`**.

## 6. Turno da frase exata — caminho atual medido (2026-11-07T21:00:45Z)

Frase humana real recebida: `Localize o botão Relatórios na página atual`. Página ativa: `/unique` (BrowserTask `20261107_175035_62899b`, aba `a986a8f6…`, `revision` 0 estável). Nenhum clique.

Telemetria real do turno (`telemetry.sqlite`, `session_id=20261107_175035_62899b`, janela a partir de `TURN_STARTED 21:00:45.357Z`):

| # | Evento | Horário (UTC) | Detalhe |
|---|---|---|---|
| 1 | `TURN_STARTED` | 21:00:45.357 | admissão do turno no backend |
| 2 | `ROUTING_DECIDED` | 21:00:45.669 | `CONTINUE_REASONING` em 0,06 ms — o hook do fast path devolveu `None` (flag desligada) |
| 3 | `PROVIDER_CALLED` | 21:00:52.501 | **System 2, chamada 1** — 6.806 ms, 95.747 tokens de entrada, 654 de saída |
| 4 | `BROWSER_OPERATION_OBSERVED` | 21:00:52.640 | `op_browser_snapshot_2a39ffb4f819`, `OBSERVED`, 33,2 ms |
| 5 | `TOOL_COMPLETED` | 21:00:52.779 | `tool.browser_snapshot` 106,6 ms |
| 6 | `PROVIDER_CALLED` | 21:00:56.972 | **System 2, chamada 2** — 4.069 ms, 97.032 tokens de entrada, 486 de saída |
| 7 | `BROWSER_OPERATION_OBSERVED` | 21:00:57.276 | `op_browser_snapshot_8272e48c9cef`, `OBSERVED`, 117,0 ms |
| 8 | `TOOL_COMPLETED` | 21:00:57.420 | `tool.browser_snapshot` 196,8 ms |

**Validação do ref:** duas leituras nativas independentes, ambas com `@e1 button "Relatórios"`, `readiness: stable`, `truncated: false`, `wall_detected: false`, mesma aba e `revision`. Referência confirmada sem ambiguidade (4 elementos: `@e1` Relatórios, `@e2` Configurações, `@e3` tab Painel, `@e4` Ajuda) — exatamente o caso `exact_match` do componente.

**Provedor usado:** provedor de chat do Hermes (System 2). `SYSTEM1_COMPLETED` nesta sessão: **0**.

### Comparação direta no mesmo alvo

| Métrica | Caminho atual (medido) | System 1 determinístico (componente) | System 1 com Laya (componente) |
|---|---|---|---|
| Chamadas de modelo | **2** | **0** | 1 |
| Tempo de modelo | **10.876 ms** | 0 ms | ~218 ms quente (19.386 ms frio) |
| Tokens de entrada | **192.779** | 0 | ~poucos milhares (estado mínimo) |
| Leitura de browser | 2 snapshots (33 ms + 117 ms) | 2 snapshots (before + readback) | 2 snapshots (before + readback) |
| Tempo total do turno até a resposta | ~12,1 s (admissão → 2ª chamada concluída) | ~0,1 ms de seleção + 2 snapshots | ~0,2 s de seleção + 2 snapshots |

Observação de honestidade: nesta frase, o alvo tem correspondência **exata**, então o ganho maior não vem do Laya e sim do caminho determinístico — 0 chamadas de modelo contra 2. O Laya só entraria em cena em correspondência parcial, e ali custa ~218 ms por decisão quente.

## 7. O que falta para fechar a comparação end-to-end

O que resta é **somente** a metade System 1 do mesmo turno. O baseline está medido e o componente está validado com snapshots reais, mas nenhum turno humano desta sessão executou o fast path, porque o gate nunca pôde abrir aqui. Para fechar o comparativo faltam, na ordem:

1. Runtime com `HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED=1` e Laya importável (o venv isolado `gen-79019aa…` já atende) mais `HERMES_HOME` próprio.
2. UI ligada a esse runtime para que `origin=human` e `create_work` ocorram de verdade.
3. Browser próprio dessa sessão, para que o recibo e o `revision` sejam evidência independente e não compartilhada com este backend.

Com isso, o turno equivalente deve produzir `SYSTEM1_COMPLETED` com `provider_calls=0` para o caso exato, ou 1 chamada Laya para correspondência parcial — e a comparação fica completa.

Artefatos desta rodada (todos no diretório `workstation/benchmarks/system1_live_session/`):

- `live_snapshots_20261107.json` — snapshots nativos verbatim dos 4 cenários (before/after) + recibos.
- `run_component_bench_20261107.py` — bench componente (executável no venv isolado).
- `component_bench_20261107.json` — resultados medidos acima.
- `collect_turn_evidence_20261107.py` — coletor de evidência de turno/telemetria (somente leitura).
- `evidence_preflight_20261107.json` — evidência de pré-voo desta sessão.
