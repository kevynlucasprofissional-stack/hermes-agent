# OPC-001 — Hermes Prefabricated Operational Capabilities

**Data:** 2026-10-10 | **Status:** direção aprovada + código de referência externo v0.1/v0.2, **não integrado/qualificado no produto** | **Owner:** Workstation Control Plane / Hermes Agent tool registry / Experience Compiler.

## Objetivo e condição de sucesso

Transformar procedimentos recorrentes observados em sessões reais + snapshots HTML em capacidades determinísticas versionadas, observáveis e verificáveis. Cada capacidade deve ser descoberta por ambos os agentes, selecionada antes do System-2 quando a correspondência for inequívoca, invocada pelo executor canônico, e reaproveitada sem nova inferência de LLM. Chamadas à Laya somente onde a classificação de estados/opções gerar valor mensurável. **Não substituir o agent, Browser, TaskCompiler, Policy, Verifier, ArtifactStore ou OperationalCapabilityRegistry.**

## Fontes locais (não presentes na árvore GitHub main inspecionada)

- Raiz Windows: `C:\Github\hermes-agent`.
- Código v0.1 previamente criado e fornecido: `referências\Hermes-Work-Prefabs-Plug-and-Play-v0.1`. Reaproveitar (não ignorar nem reinstalar cegamente): `Hermes-Prefabs/workstation/prefabs/{catalog,engine,integration,offline,seeding,trello}.py`, `tools/workstation_prefabs.py`, `install.py`, testes e CLI. Localizar realmente o nível da pasta extraída antes de copiar.
- Sessões: `workstation\dogfood\dados\Sessões Hermes`.
- HTML: `workstation\dogfood\dados\Páginas de sites`.
- Sobreposição/opcional de referência desta investigação: arquivo entregue `Hermes-Work-Prefabs-Integracao-v0.2.zip`, com `tools/hermes_prefab_catalog.py`, `workstation/prefabs/harvester.py` e `audit-corpus`. O executor deve localizar seu arquivo local; se indisponível, reconstituir dos requisitos abaixo e registrar a divergência, sem fingir tê-lo lido.
- Esses caminhos *não constaram no GitHub main* no exame de 2026-10-10. O agente implementador com acesso ao Windows deve verificar se existem, se estão ignorados e se contêm informação confidencial. NÃO publicar sessões brutas, HTML de páginas autenticadas ou segredos.

## Evidência empírica limitada e auditável

Na cópia de anexos recebida foram 9 sessões JSON únicas e 8 HTMLs únicos (duplicatas de Trello removidas pelo SHA). Frequência de chamadas de browser por família: Instagram 543, Trello 387, WhatsApp 148, ChatGPT 17, browser genérico 14. Total = 1.109 chamadas de browser e 3.297 chamadas de ferramentas. São *chamadas de ferramentas*, NÃO chamadas faturáveis da LLM. As associações de sessões e HTML pela família/nome não garantem equivalência do estado DOM por timestamp.

HTML Trello registrou 761 cards no snapshot SCRUM e 539 no Editorial, com `data-testid=list-card` e `card-name`; URLs e identificadores de board/card são pistas estáticas, nunca prova do estado atual. Instagram expõe estrutura de interface, mas faltam snapshots individuais de insights de todos os posts. WhatsApp possui DOM de lista/editor/mensagens, com conteúdo privado; ChatGPT possui editor e navegação com drift em relação a seletores antigos. Se a varredura local divergente mostrar números diferentes, registrar hashes e corrigir a matriz com provas.

## Owners e contratos de integração (confirmados em `main` f21e803)

| Responsabilidade | Dono canônico | Alteração mínima |
|---|---|---|
| Tool discovery do Hermes Agent | `tools/registry.py` / `model_tools.py` / `toolsets.py` | `tools/hermes_prefab_catalog.py` com `registry.register(... toolset='browser')` para descoberta sem side effects; avaliar `prefab_execute` no `desktop_ui` e exposições de Agent com gate explícito |
| Ferramenta Workstation | `tools/workstation_work.py`, `tools/workstation_prefabs.py` | Integrar funções do pacote existente; manter contrato `work_execute` como opção de trabalho durável; nenhuma rota mutativa sem TaskRun |
| Ingresso e intent | `workstation/integrations/hermes/turn_admission.py` | parser fechado para comando humano exato; não usar resultado de DOM/LLM como autorização |
| Resolução pre-LLM | `workstation/integrations/hermes/operational_resolution.py` | chamar resolvedor prefab antes de gastar System-2; falha pré-I/O cai em reasoning; erro pós-I/O fica WAIT/HANDOFF |
| Dispatch, guardrails, profiles | `workstation/integrations/hermes/scoped_execution.py`, `tools/browser_workstation.py` | usar `workstation_durable_dispatch`, sem HTTP/browser paralelo que elida guardrails |
| Execução e verificação | `workstation/operational_kernel.py`, `workstation/task_compiler.py`, `workstation/browser_projection.py`, `workstation/run_adoption.py` | ler estado fresco, owner-receipt e readback por primitive/família; idempotência + drift quarantine |
| Registro e ciclo de vida | `workstation/operational_capabilities.py`, `workstation/experience_compiler/{compiler,lifecycle,promotion}.py` | candidatos `DISCOVERED` até validação empírica + replay; nunca promover por HTML apenas |
| Detecção Laya | `workstation/experience_compiler/compilability_monitor.py`, `workstation/system1/laya_provider.py` | classificar oportunidade sem conceder authority; calibrar pelos labels do verificador |
| Persistência observacional | `workstation/artifacts.py`, `workstation/experience_compiler/corpus.py` | apenas metadados redigidos + refs de provas; não clonar corpora e índices |

**Lacuna real da baseline:** `workstation/integrations/hermes/run_local_adoption.py` expõe `_SUPPORTED=('write_file','read_file')` e `_READBACK=('write_file',)`; no pre-LLM a adoção automática de browser ainda exige `owner` certificado, readback real e testes. `OnlineCompilabilityMonitor` em SHADOW observa mas não minera; D-039 pede separar OBSERVE_ACTIVE de permissão de efeitos. `resolve_policy` aceita `direct_qualification_ref` não vazia como suficiente; uma string qualquer não é atestação.

## Pacotes de capacidades e classes de risco

1. **Browser Navigation:** abrir destino conhecido, reutilizar aba somente após identidade/host/URL/TaskRun, confirmar snapshot owner fresco. Domínio/URL exatos; recusas para variantes ambíguas. Sem LLM em hit exato.
2. **Trello READ:** localizar quadro/lista/card, listar, filtrar por nome, ler campos permitidos. Preferir API pública oficial com credenciais autorizadas e scope correto. Separar leitura de planejamento de escrita. `prepare_description` somente diffs/hashes.
3. **Trello MUTATION:** criar cartão, atualizar descrição, membros, data, mover lista somente via plano canônico + grant do Policy + `effect_budget` + operação idempotente + verificação GET independente. Em erro ou resposta incerta: HALT + reconciliação; nunca retry cego. Desabilitado até gates.
4. **Instagram:** coleta incremental de dados próprios da conta autorizada preferindo API suportada e permissões compatíveis; checkpoints por mídia; redigir PII; metric definitions preservadas; HTML como probe e não endpoint privado autoautorizado.
5. **WhatsApp:** abrir UI/contato autorizado, recuperar informação mínima, redigir mensagem sem enviar; qualquer envio exige intenção, autoridade, escopo e confirmação. Não reconstruir sessões de terceiros nem harvesting irrestrito.
6. **ChatGPT:** localizar editor/conversa e preparar texto; não enviar automaticamente quando não houver autorização por turno; seletores semânticos com fallback e drift detection.
7. **Cross-site:** `get_live_state -> match_known_capability -> validate preconditions -> route/dispatch -> independent readback -> closure receipt -> learning`. Negar qualquer mismatch de perfil, tenant, tab, URL, tarefa, run ou lease.

## Design de descoberta que *garante preferência* sem falsos privilégios

- A existência de código não torna uma ferramenta visível: provar `model_tools.get_tool_definitions()` e `registry` na sessão real para os toolsets `browser` (Hermes Agent) e `desktop_ui` (Workstation). Se desabilitados, respeitar ausência.
- Adicionar metadados de `when_to_use`, `do_not_use`, pré-condições, tipo de efeito, scope, verificador, versão, contrato de inputs, fallback por capacidade. Fornecer ferramenta `prefab_catalog` read-only ao Hermes Agent; `prefab_execute` Workstation somente via runtime habilitado.
- Inserir Fast Path de matching **antes da primeira chamada de System-2** apenas para intenção confiável e fechada; para pedidos vagos, Laya ou LLM resolve intenção, nunca cria autoridade. Emite reasons `PREFAB_MATCH`, `PREFAB_MISS`, `PREFAB_BLOCKED`, `PREFAB_DRIFT`, `PREFAB_VERIFIED`, com contadores reais.
- Verificar *ordem de consulta*: um comando explícito reconhecido não deve disparar `browser_console`/tool search/LLM antes da tentativa segura. Quando pré-condições falham, degradar sem side effects. Registry metadata + skill apenas informam e nunca garantem comportamento isoladamente.

## Fases obrigatórias / dependências

OPC-00: H-079 upstream-first; fixar baseline, gates exatos, H-081/H-082 e `AGENTS.md`; não tocar runtime se baseline bloqueado. Se bloqueado, completar apenas docs, audit fixtures e RED tests isolados; reportar HOLD.
OPC-01: inventário deduplicado com provas SHA de sessão/HTML, tipo de operação, repetição, sucesso/falha/uncertain, seletor e fonte, somente dados sanitizados; separar observação de hipótese.
OPC-02: reusar pacote v0.1 e overlay v0.2; comparar file-by-file, remover duplicações; integrar `prefab_catalog`, `prefab_execute`, Fast Path e acessibilidade por Agent/Workstation em canais reais.
OPC-03: primeiro vertical `open_known_trello` + `board_cards`/`find_card` (read-only): zero chamada System-2 em hit, snapshot/GET independente, toolset disable-denial, no hidden profile fallback.
OPC-04: Trello update de descrição: compare-and-set do SHA, idempotency key, ledger, certificado, readback; lista da Samara e cards do Dia das Crianças como fixtures **sintéticas**, sem publicar dados privados.
OPC-05: browser readback owner e run-local `RunAdoptionOwner` permitido por família, não por wildcard; sem inventar `RunClosureProof` nem receipts.
OPC-06: D-039 OBSERVE_ACTIVE sem mutação; Laya propõe `MINE_CANDIDATE`, ExperienceCompiler trabalha corpus scoped + persistence de HELD, restore/revision retry, validação separada; DIRECT só com atestação real por família.
OPC-07: Instagram, WhatsApp, ChatGPT segundo os respectivos contratos, em PRs separados; não bloquear o primeiro vertical pelo escopo dos demais.
OPC-08: regressão Windows/Electron, E2E Browser real, CI exact head, testes negativos de auth + restart + drift + duplicação, benchmark de custo e latência; handoff e relatório de qualidade, sem merge de PR vermelho.

## Gates de aceitação falsificáveis

- Testes offline de pacote e inventário preservam segredos (nenhum raw HTML ou sessão no repo/telemetria).
- `prefab_catalog` aparece no Hermes Agent com `browser`; `prefab_execute` aparece no Workstation quando `desktop_ui` e runtime estão habilitados; ambos desaparecem quando toolsets/permissões são negados.
- Comando humano exato de navegação não faz chamada System-2 e somente declara EXECUTED após readback owner. Sem browser, antes de qualquer I/O => fallback; depois de efeito incerto => WAIT/HANDOFF sem retry.
- Trello read executa sem LLM e retorna quantidade/links confirmados pela API oficial; leitura falha com credencial ausente sem revelar segredos.
- Mutação escrita não autorizada jamais executa. Após uma tentativa incerta não há segunda PUT. Queda de lease, perfil, identidade, URL, replay/verifier/fingerprint tem denial verificável.
- Laya ABSTAIN/timeout/proposal não promove nem autoriza. GLOBAL PROMOTED segue o ExperiencePromotionPolicy existente.
- Relatório mede chamadas reais de LLM, tokens atribuíveis, latência p50/p95, verificações, erros e economias comparadas a baseline equivalente. Não interpretar `browser_console` count como preço da LLM.

**Arquivos relacionados:** [PROMPT EXECUTOR](PREFAB_IMPLEMENTER_PROMPT_2026-10-10.md), [jornal OPC-001](engineering-journal/prefab-operational-capabilities-2026-10-10.md), [D-039](LAYA_ADAPTIVE_AUTONOMY_AND_DURABLE_LEARNING_2026-10-08.md), [H-079](UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md).