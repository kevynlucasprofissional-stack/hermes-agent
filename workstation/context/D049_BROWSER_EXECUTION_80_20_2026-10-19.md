# D-049 / R1 — execução 80/20 e prompts autocontidos (19/10/2026)

STATUS: PLANO DOCUMENTAL. Nenhuma implementação, CI ou dogfood é comprovada por este documento. Branch alvo: feat/d049-browser-80-20-impl-20261018. HEAD auditado: fd80408ab29c9cc701dacf1fbe4ceb7899c1a836.

## Diagnóstico adversarial e decisão

Os anexos (183 páginas Fable; duas comparações CHATGPT; auditoria adversarial local) mostram que batch sequencial, DOM refs, snapshot delta, extração sanitizada, cache, BrowserTask, leases, ArtifactStore, ExecutionJournal e TaskCompiler já estão presentes. Não criar mecanismos paralelos. Correção da priorização antiga: B0.1 bridge e B0.2 Learning já tinham patches/testes locais não commitados; a entrega útil agora é G0 checkout íntegro, G1 veredito de extração sem falso sucesso e G2 views baratas acessíveis ao agente. IV recuperação de DOM drift apenas se métricas justificarem.

Evidência da auditoria local: runtime importa workstation-browser-snapshot-views.ts que estava UNTRACKED e ausente do HEAD; teste views 11 PASS, schema 9 PASS; bridge 7 PASS, 1 SKIP (symlink), Learning B0.2 1 PASS, 36 não selecionados. Nenhuma prova de checkout limpo, CI exact-head ou E2E externo. Validar estado atual antes de agir. Não confundir capture success com schema_valid; controller ACK com persisted readback; batch com transação atômica reversível; bytes de snapshot com tokens model-facing.

## Mapa de execução e aceites

| Prompt | Problema | Saída verificável |
| --- | --- | --- |
| 1 G0 | sincronização sem perda; arquivos untracked e patches B0; build | HEAD reproduzível em checkout limpo |
| 2 G1 | schema_requested/schema_valid e WorkItems, inclusive lista vazia | nenhum valid_count ou WorkItem falsamente conforme |
| 3 G2 | exposição tool schema, roteamento e payload; benchmark | views chamáveis pela IA, @eN íntegro e ganho model-facing medido |
| 4 opcional | STALE_REF antes do dispatch | alvo único e 0 re-dispatch de efeito incerto |

As sessões 1–3 devem ser concluídas antes de WebMCP, Lattice scene graph, model router, novos traces SQLite, universal readiness, event bus ou código BrowserOS AGPL. Respeitar H-079/H-081/H-082/BAV04 e gate CI exact-head.

## PROMPT 1 — EXECUTE sincronização + fechamento G0 (grupo de problemas simples)

Você é a IA implementadora do Hermes Work, e deve EFETIVAMENTE editar/testar código. Branch exclusiva: feat/d049-browser-80-20-impl-20261018 em C:\Github\hermes-agent; origem kevynlucasprofissional-stack/hermes-agent. Priorize soluções simples, critique e adapte propostas, sem criar sistemas paralelos.

PASSO ZERO — SINCRONIZAÇÃO. Execute PowerShell:
~~~powershell
Set-Location 'C:\Github\hermes-agent'
git branch --show-current
git rev-parse HEAD
git status --porcelain=v1 -uall
git worktree list --porcelain
git fetch origin feat/d049-browser-80-20-impl-20261018
git log --oneline --left-right HEAD...origin/feat/d049-browser-80-20-impl-20261018
git diff --name-only HEAD..origin/feat/d049-browser-80-20-impl-20261018
~~~
Exija branch correta. Confirme que remote é descendente local e que alterações remotas não colidirão com arquivos locais modificados/não rastreados. SOMENTE nesse caso: git merge --ff-only origin/feat/d049-browser-80-20-impl-20261018. Verifique HEAD e existência local deste documento. Se houver divergência, colisão, worktree concorrente ou dúvida de ownership, PARE e relate; NÃO fazer git pull indiscriminado, reset --hard, clean -fd, stash de terceiros, rebase ou merge forçado. Docs aqui publicados só ficam disponíveis localmente depois de fetch + fast-forward seguro. Preservar optional-skills, dogfood e Obsidian fora do escopo.

Inspecione estritamente: apps/desktop/electron/workstation-browser-runtime.ts, workstation-browser-snapshot-views.ts e .test.ts, workstation-browser-runtime-task.test.ts, workstation/browser_bridge.py e workstation/tests/test_browser_bridge_security.py. O módulo snapshot-views era untracked; integre os dois arquivos existentes (não substitua código melhor) de modo que o import do runtime esteja válido no HEAD commitado. Revisar e concluir somente patches locais B0.1 (Path.resolve/is_relative_to + gravar destino validado) e B0.2 (startLearning exige ownerTaskId da aba solicitada, jamais lease da aba ativa errada). Tratar aba manual não vinculada por adoção/handoff explícitos existentes, não por concessão silenciosa. A correção de paths não elimina necessariamente corrida adversarial de symlink; documentar limite.

Executar testes reais: python -B -m pytest -q -p no:cacheprovider workstation/tests/test_browser_bridge_security.py com PYTHONDONTWRITEBYTECODE=1; dentro de apps/desktop executar ..\..\node_modules\.bin\vitest.cmd run electron/workstation-browser-snapshot-views.test.ts electron/workstation-browser-extract-schema.test.ts --config vitest.config.ts --no-file-parallelism e teste B0.2 em workstation-browser-runtime-task.test.ts; executar typecheck/build correto do package e git diff --check. Comprovar checkout limpo isolado e teste de import; não apagar worktree atual. Comitar apenas caminhos de sua autoria, push fast-forward após fetch/check. Reportar SHA anterior/final, arquivos, comandos, PASS/FAIL/SKIP e limitações. Sem merge main.

## PROMPT 2 — EXECUTE contrato de schema do owner até WorkItems (um problema complexo)

Confirme branch/HEAD/status, leia este handoff e estes owners: apps/desktop/electron/workstation-browser-extract-cache.ts, workstation-browser-runtime.ts extractItemsForEntry, workstation/browser_projection.py, workstation/integrations/hermes/browser_controller.py, workstation/tests/test_browser_extract_items.py, workstation/tests/test_browser_controller_domain_processing.py e testes TS schema. Não reler arquitetura inteira.

Escreva primeiro testes RED. Bug verificável na leitura: validateExtractedItems só examina keyword unsupported dentro do loop de items; com items=[] pode aceitar schema incompatível. Faça preflight das keywords independentemente da quantidade de itens e mantenha limites de profundidade; não adicionar biblioteca JSON Schema só por entusiasmo.

Bug de fronteira: Electron devolve success=true para captura mesmo com schema_valid=false; browser_projection.py valida campos title por SemanticValidator e computa valid_count sem consumir schema_valid. Corrija a cadeia Electron -> controller -> ArtifactStore/WorkPlan -> WorkItems -> resumo. Separar capture_success, schema_status(valid/invalid/unknown/not_requested), semantic_validation e durability. Se foi pedido schema e não veio verdict boolean do owner, UNKNOWN e nunca conformidade; se verdict global false sem erro indexado confiável, não complete NENHUM WorkItem como conforme ao schema, mas preserve payload bruto sanitizado + errors bounded para investigação. Não inventar validade por item a partir de um boolean agregado; não exigir title quando schema de usuário válido não o exige, exceto outra regra semântica identificada separadamente. valid_count precisa ter significado explícito; schema_errors redacted.

Código candidato Python (adapte ao estado real, não copie cegamente):
~~~python
schema_requested = isinstance(args.get("schema"), dict)
owner_verdict = data.get("schema_valid")
if not schema_requested:
    schema_status = "not_requested"
elif owner_verdict is True:
    schema_status = "valid"
elif owner_verdict is False:
    schema_status = "invalid"
else:
    schema_status = "unknown"
# Persistir schema_status e schema_errors limitados no WorkPlan/Artifact/resumo.
# Nunca completar WorkItem como schema-conforme se schema_status != "valid".
~~~
Teste itens 0 com schema unsupported; required/type/enum inválidos; schema_valid=false com title presente; owner verdict ausente; schema true com title ausente e schema que permite; payload sensível; persistência falha; compatibilidade sem schema; controller efetivamente chama projeção Workstation. RED/GREEN e pytest/Vitest focados, git diff --check, commit/push escopado. Distinguir unit PASS de E2E externo, não alterar política canônica de incerteza.

## PROMPT 3 — EXECUTE economia model-facing via tool real + medição (um problema complexo)

Revalidar branch/HEAD/status, ler somente: tools/browser_tool.py nas zonas BROWSER_TOOL_SCHEMAS browser_snapshot (~495), browser_snapshot (~930), _BROWSER_TOOL_TABLE e _routed_handler (~1550); tools/browser_workstation.py _dispatch (~774) e project_model_browser_payload (~966); apps/desktop/electron/workstation-browser-runtime.ts snapshotForEntry (~2950, ~3870); workstation-browser-snapshot-views.ts/.test.ts, testes registry/projection e telemetry.

Electron já recebe view=summary|action_map|focus|content; o schema exposto ao agente aceita apenas full. Adicionar no properties da tool e validar: view enum; focus_ref @eN somente com view=focus; focus_neighbors inteiro 0..10; max_chars inteiro 200..12000. Propagar args pela mesma rota autorizada. Não adicionar parâmetro inerte só ao fallback Python. Se rota legada não suporta view, retornar unsupported explícito ou degradar apenas com equivalência semântica comprovada, nunca fingir que view foi aplicada. Modo sem view mantém byte/semântica legados.

Snippet candidato (inserir no objeto properties atual, adaptando):
~~~python
"view": {"type": "string", "enum": ["summary", "action_map", "focus", "content"]},
"focus_ref": {"type": "string", "description": "Current @eN of same tab and revision"},
"focus_neighbors": {"type": "integer", "minimum": 0, "maximum": 10},
"max_chars": {"type": "integer", "minimum": 200, "maximum": 12000},
~~~
Corrigir model-facing: não devolver elements completos duplicados para action_map/focus; manter refs utilizáveis, metadados únicos, tab/owner/revision, truncation e redaction de label/value/URL; projetar subset sem alegar lossless global. Delta não deve somar full+delta no contexto do modelo; só substituir full se há baseline compatível da mesma task/tab/url/epoch e reconstrução comprovada; senão full. Não ativar default sem teste.

Benchmark pareado pelo menos 10 ciclos por cenário viável (navegação simples, SPA, formulário, lista de 20 itens, takeover). Medir bytes retornados ao MODELO, tokens reais onde observáveis, calls, user_to_verified_ms, p50/p95 e sucesso externo. Se faltam serviço externo ou tokens faturados, apresentar métricas disponíveis e marcar outras NOT MEASURED, jamais inventar 76–99% ou 5x do PDF. Exigir snapshot legado, focus missing, ref stale, duas abas, baseline inválido, dados sensíveis e testes da rota registrada. Testes RED/GREEN, commit/push escopado, journal com números e denominadores. Se benefício não se provar, feature permanece opt-in.

## PROMPT 4 — CONDICIONAL: recuperação semântica antes do CDP

NÃO EXECUTAR sem evidência concreta de que STALE_REF/DOM_DRIFT é causa material no benchmark G2. Se confirmado, reusar resolvePoint, clickRef, typeRef, semantic_anchor, documentEpoch, mutationRevision e lease; tentar reaquisição somente antes do input com testid/name/aria-label/role e correspondência única mesma task/tab/origem. Ambiguidade -> abstenção/handoff, nunca alvo adivinhado. Não repetir click/type após possível dispatch parcial, timeout ou mousePressed; reconciliar por readback independente. Testes SPA rerender, alvos duplicados, takeover, troca de aba, timeout antes/depois do press e contador servidor com 0 duplicações. Não construir Stagehand paralelo.

## Contrato de saída para cada IA implementadora

Tabela: HEAD inicial/final | alterações exatas | comandos e PASS/FAIL/SKIP | métricas medidas | gate IMPLEMENTED/UNIT TESTED/CI QUALIFIED/EXTERNAL E2E | pendências. Atualizar ROADMAP, journal, intelligence e state com fatos pós-commit, sem reclassificar intenção em sucesso. Preservar política H-079/H-081/H-082, BAV04, 0 replay de efeito incerto.