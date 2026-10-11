# PROMPT EXECUTOR — Hermes Work Prefabricated Operational Capabilities (OPC-001)

Você é a IA implementadora operando no checkout Windows `C:\Github\hermes-agent`. IMPLEMENTE, TESTE, DOCUMENTE E QUALIFIQUE a iniciativa OPC-001 até o limite dos gates reais; não apenas produza mais um plano. O plano já está definido neste arquivo. Respeite os bloqueios de upstream/CI e jamais declare funcionamento não comprovado.

## Missão inegociável

Converter as operações recorrentes reais das sessões Hermes + HTMLs das páginas em capacidades operacionais pré-fabricadas de custo marginal próximo de zero LLM: descobertas pelo Hermes Agent, anunciadas nos toolsets efetivos, executadas no Hermes Workstation antes do System-2 quando correspondência inequívoca e validadas por resultados reais. Integre à arquitetura existente (`OperationalCapabilityRegistry`, `OperationalKernel`, `TaskCompiler`, `ExperienceCompiler`, Laya/System-1, BrowserTask, Policy, ArtifactStore, ExecutionJournal`) sem duplicar owners. A ferramenta não basta *existir*: prove discovery, routing, selection e execution nos dois ambientes.

## Fontes locais EXATAS — leia somente o necessário e construa inventário por script

ROOT = `C:\Github\hermes-agent`
REFERÊNCIA OBRIGATÓRIA = `C:\Github\hermes-agent\referências\Hermes-Work-Prefabs-Plug-and-Play-v0.1`
SESSÕES = `C:\Github\hermes-agent\workstation\dogfood\dados\Sessões Hermes`
HTML = `C:\Github\hermes-agent\workstation\dogfood\dados\Páginas de sites`
COMPLEMENTO opcional (se copiado ao checkout): `Hermes-Work-Prefabs-Integracao-v0.2.zip` (código adicional de `tools/hermes_prefab_catalog.py`, `workstation/prefabs/harvester.py`, CLI e testes). Se ausente, implemente os mesmos contratos descritos no OPC-001. **Leia, aproveite e adapte o código v0.1** — não o ignore nem copie cegamente em produção. Localize `Hermes-Prefabs` na pasta extraída, normalize UTF-8 e paths Windows. Se a referência ainda não existir, registre blocker e use apenas fontes realmente acessíveis.

### Entradas canônicas já mapeadas (evite pesquisar aleatoriamente o repositório)

- `workstation/AGENTS.md` e `workstation/context/README.md` = instruções mandatórias.
- `workstation/context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md` = H-079; sincronização upstream, pin e qualificação ANTES de alterar runtime.
- `workstation/context/PREFAB_OPERATIONAL_CAPABILITIES_2026-10-10.md` = especificação OPC-001, mapa de owners, matrizes, gates.
- `workstation/context/LAYA_ADAPTIVE_AUTONOMY_AND_DURABLE_LEARNING_2026-10-08.md` = D-039, aprendizado ativo sem autoconcessão de autoridade.
- `workstation/context/ONLINE_COMPILABILITY_POST_IMPLEMENTATION_AUDIT_2026-10-08.md` = riscos e correções D-038.
- `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md`, `workstation/context/engineering-journal/CURRENT.md` = status e histórico.

## Fatos já verificados — use para ir direto ao código

- `main` examinada: `f21e803b3525b70ee6be2305e579c1cc1f930e74` (merge Laya Direct); confirme o HEAD atual antes de agir.
- Discovery: `model_tools.py` importa módulos registráveis `tools/*.py` via `tools/registry.py::discover_builtin_tools()`. `toolsets.py` distingue `browser` (Hermes Agent) e `desktop_ui` (Workstation). Registrar uma ferramenta apenas no desktop NÃO garante que esteja disponível ao Agent CLI.
- Pre-LLM: `workstation/integrations/hermes/turn_admission.py::workstation_turn_admission` e `workstation/integrations/hermes/operational_resolution.py::workstation_operational_resolution` + `agent/operational_resolution.py`. Usar o contexto já autenticado; não inferir autoridade pelo texto da página.
- Dispatcher: `workstation/integrations/hermes/scoped_execution.py::workstation_durable_dispatch`, sob guardrails, interrupção, task e session.
- Execução: `workstation/operational_kernel.py::execute_capability`, `workstation/task_compiler.py::_execute_capability`, `workstation/browser_projection.py`, `tools/browser_workstation.py`.
- Registry: `workstation/operational_capabilities.py::OperationalCapabilityRegistry`, `CapabilityResolver`, `learn_operational_capability`.
- Adoção em-run: `workstation/integrations/hermes/run_local_adoption.py` ainda admite em produção somente `write_file/read_file`, com readback de `write_file`; não basta adicionar `browser_click` a um array. Exigir owner receipt, identity, revision, scope, lease, orçamento e verificador.
- Monitor: `workstation/experience_compiler/compilability_monitor.py` em SHADOW só observa; D-039 propõe OBSERVE_ACTIVE + mineração sem efeitos. O gate `direct_qualification_ref` não vazia não é qualificação real.
- O ZIP v0.1 contém instalador reversível, `catalog.py`, `engine.py`, `integration.py`, `offline.py`, `trello.py`, `seeding.py`, `tools/workstation_prefabs.py`, CLI e testes. Preserve lógica que passa e corrija o restante pela arquitetura atual.
- Evidence baseline recebido: 9 sessões JSON únicas, 8 HTMLs únicos; browser calls: Instagram 543, Trello 387, WhatsApp 148, ChatGPT 17, browser 14. **Não confundir tool calls com preço/tokens LLM**; produzir contagem verificada no checkout local.

## Ordem de execução: não pule fases nem peça para o usuário repetir decisões

### OPC-00 — Pré-condições e estratégia Git

1. Inspecione `git status`, `git branch`, `git log`, os subdiretórios e links de upstream. Preserve arquivos não comitados do usuário. Leia regras de `AGENTS.md`/H-079; classifique H-079/H-081/H-082/CI da versão real.
2. Crie branch de implementação a partir da baseline qualificada, sem tocar `main`, e registre SHA, pin upstream, mudanças pendentes e CI. **Se H-079/CI obrigatório estiver bloqueado, não faça mudanças funcionais:** entregue testes RED isolados, auditoria/catálogo docs e lista exata de bloqueios. Não force merge nem marque gate como verde.
3. Leia o Prefabs v0.1 COMPLETO e compare os arquivos do ZIP/pasta com owners reais; faça `git diff --no-index` contra versões se já instaladas; não reinstale em cima de versão existente. Nenhum arquivo de referência/dogfood vira execução arbitrária ou instalação direta.

### OPC-01 — Inventário inteligente das sessões e HTMLs

4. Enumere todas as sessões recursivamente (`*.json`, dedup SHA-256) e snapshots (`*.html`, dedup SHA-256). Gere `workstation/qualification/prefabs/corpus-inventory.json` sanitizado com: hash, arquivo, data se verificável, operação, sequência de ferramentas, resultado categorizado (VERIFIED/OBSERVED/FAILED/UNCERTAIN), família/site, frequência, potencial de economia e evidências limitadas.
5. Correlacione cada sequência com HTML compatível somente se página/URL/identidade e timestamps permitirem; quando só existir similaridade por site, marque `HYPOTHESIS` e solicite snapshot fresco antes de compilar. Remova material privado, cookies, auth tokens, CSRF, headers de sessão, strings sensíveis e conteúdos de chat. Não comite JSON ou HTML brutos.
6. Priorize Trello, Instagram, WhatsApp e ChatGPT por repetição e capacidade de readback. Cada candidato deve possuir `{id, version, family, intent_patterns, input_schema, effect, scope, preconditions, steps, postconditions, verifier, fallback, source_hashes, promotion_state}`. Rejeite endpoints privados do navegador como execução universal; APIs oficiais suportadas primeiro.

### OPC-02 — Integrar a biblioteca prefabricada ao Hermes Agent E ao Workstation

7. Copie/refatore funções úteis de `referências/Hermes-Work-Prefabs-Plug-and-Play-v0.1/Hermes-Prefabs/workstation/prefabs/*.py` (confirme árvore real) para `workstation/prefabs/*.py`. NÃO substituir `workstation/operational_kernel.py`, `task_compiler.py`, `agent/*`, `tools/browser_workstation.py` nem `tools/registry.py` por versões simplificadas.
8. Copie/refatore `tools/workstation_prefabs.py` para ferramenta `prefab_execute` no `desktop_ui` com schema compacto, ação `catalog`, Trello read-only e status. Acrescente `tools/hermes_prefab_catalog.py` (v0.2) no toolset `browser` para discovery do Agent genérico: `catalog` + `match`; sem mutações, sem browser criado em paralelo. Se o conceito de toolset atual diferir, adapte preservando a mesma prova de visibilidade.
9. Integre Fast Path com **no máximo dois hooks minúsculos**: (a) `workstation_turn_admission` recebe envelope humano e salva apenas intenção exata/allowlisted; (b) `workstation_operational_resolution` chama `maybe_resolve_navigation(context)` antes do System-2. Use `workstation_durable_dispatch` e independent browser snapshot. Nunca terminal EXECUTED por simples acknowledgment.
10. Inclua metadata `when_to_use/do_not_use/risk/verifier` nos schemas e/ou no catálogo versionado; o Agent deve VER ferramenta no conjunto `get_tool_definitions` e identificar quando usá-la. Teste no harness com `browser` habilitado/desabilitado e no Workstation com `desktop_ui` habilitado/desabilitado. Reusar prompts/skills apenas como ajuda, não como garantia de tool routing.
11. Para intenção exata, ponha o resolver determinístico antes de tool search/LLM; toda chamada deve registrar matched/missed/denied/proof. Sem configuração, toolset ou autoridade, falhar fechado, não inventar credenciais e não prometer custo zero.

### OPC-03 — Primeiro vertical real (Trello READ + navegação)

12. Valide `open_trello`, `open_editorial`, `open_scrum`, `board_lists`, `board_cards`, `find_card`, `card` e `prepare_description_diff` no checkout com dados permitidos. O catálogo v0.1 contém as URLs dos quadros; confirme as URLs pelos HTMLs e estado ao vivo, sem hardcode de conta errada.
13. Preferir API oficial Trello GET quando autorizada; não ler HTML gigante a cada operação. Use cache com TTL/context, paginação, IDs estáveis e status de stale. Preserve datas/escopos de membro para consultas corretas. Dados inacessíveis => erro explícito/fallback, não resultado inventado.
14. Forneça um teste de usuário exato sem LLM ('Abra o Calendário Editorial') e outro de GET estruturado sem LLM; confirme URL/GET/fatos por readback independente; prove que Agent e Workstation sabem quando usar ferramentas (testar seleção; não apenas import).

### OPC-04 — Trello mutativo sob política canônica

15. Implemente operações parametrizáveis `create_card`, `set_description`, `assign_member`, `set_due_date`, `move_card` de forma independente; preferir API oficial com token/permissão do owner, e browser apenas com verifier real. Primeiro `dry_run` e canary.
16. NUNCA chamar `TrelloClient.apply_description` do v0.1 a partir de uma ferramenta model-facing sem `TaskRun`, Policy, effect_budget, intention scope e readback. O `--i-approve-external-write` CLI é autorização de operador interativo, NÃO grant do agente.
17. Cada escrita: pré-GET -> comparação/hash/version -> decisão autorizada -> ação UMA VEZ -> GET readback -> recibo canonical. Sem readback -> UNCERTAIN/HOLD, zero replay automático, reconciliação. Suporte batch com `work_execute` se contrato admissível; não introduzir segundo ledger.

### OPC-05 — Compilação, adoção e Laya

18. Mantenha `ExperienceCompiler.mine(task_id, run_id)` escopado. Só materialize `DISCOVERED` de sessões/HTML antigos; promoção exige `ExperiencePromotionPolicy`, validação positiva+negativa, replay real e receipt do owner.
19. Diferencie `OBSERVE_ACTIVE` (captura+mineração segura), `HELD` (efeitos não autorizados), `DIRECT_VERIFIED` (família atestada/owner validado), `QUARANTINED`. Uma `direct_qualification_ref` arbitrária NÃO autoriza. Laya sugere, mas jamais emite `LOCAL_MUTATION`, receipt, grants ou success labels.
20. Extenda browser run-local em `workstation/run_adoption.py` e `integrations/hermes/run_local_adoption.py` somente por família com backend snapshot de verdade, source ref, browser task/tab/revision, lease, scope e supported readback. RED testes contra foreign-run, canceled, superseded, drift, replay fail e effect uncertainty antes do GREEN.
21. Persistir oportunidades com revisão de evidência e restart; limites de memória/filas rígidos, mas 3 tentativas da evidência antiga não bloqueiam novas revisões. Medir latência de foreground, não sobrecarregar navegação com múltiplas inferências Laya por clique.

### OPC-06 — Expandir somente após qualificação do vertical Trello

22. Instagram: API suportada quando possível, posts/insights incremental, checkpoint por mídia, definição de métrica e outliers, sem `browser_console` massivo/requisições internas como premissa de estabilidade. Provar cobertura e frescor.
23. WhatsApp: navegar e extrair apenas escopo de conversa autorizado; sem envio automático por default, sem bypass de auth/criptografia, sem processamento irrestrito. ChatGPT: localizar editor de forma semântica, drift de seletor, preparar sem enviar quando não autorizado.
24. Cada site recebe catálogo, tests/fixtures sintéticos, readback e fallback próprio. Implemente em PRs independentes se o baseline/risco exigir.

### OPC-07 — Qualificação e relatórios de execução

25. Testes: pré-LLM, toolset visibility, canonical scope, profile swap, stale DOM, spoofed host, prompt injection em HTML, negative selection, fake authority/receipt, race/restart, uncertain mutation no-retry, API 401/429, eventual consistency, cache invalidation, kill switch, agent capability discovery. Não comitar dados privados em fixtures.
26. Rodar testes do pacote (`python -m unittest discover -s tests -v`), suites `workstation/tests` selecionadas, regressão total se gate permitir, Electron/Windows real, H-081 live Laya apenas com ambiente compatível, CI exact HEAD. Registrar comandos, duração, falhas e evidências, não declarar CI verde sem prova.
27. Benchmark A/B: mesmos comandos/mesmas permissões/snapshot fresco; métricas `system2_calls_observed`, tokens in/out, wall-time, p50/p95, quantidade de ferramentas, itens verificados, drift, custo real vs desconhecido. Não apresentar economia percentual sem medição.
28. Atualize `workstation/ROADMAP.md`, `workstation/context/engineering-journal/CURRENT.md` + entrada de sessão, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md`, contexto canônico, manuais da ferramenta e testes. Preserve decisões D-038/D-039 e rastreie PR/commits.
29. Faça commits pequenos e PR(s) contra main, **sem auto-merge**, com checklist de baseline e tests, diffs, arquivos, prova de Hermes Agent discovery e Workstation Fast Path, benefício medido, blockers e limitações. Entrega final: o que entrou, o que ainda fica BLOQUEADO, como executar a primeira tarefa, como reverter e qual é a próxima alteração mínima.

## Proibições absolutas

- Não copiar e colar HTML bruto/cookies/session JSON em prompts, GitHub, logs ou tool descriptions.
- Não inventar replay artifacts, user authority, verifiers, receipts ou economia de LLM.
- Não assumir que a pasta de referências foi comitada; verificar caminho local real.
- Não alterar código upstream antes do H-079; não alterar o funcionamento atual de outras famílias por acidente.
- Não abrir outro browser ou API credential channel fora dos owners do produto.
- Não fazer bypass de approval, guardrails, user-controlled lease, route policy, kill switch ou scope.
- Não promover apenas por estatística ou confidence do Laya; nem usar shadow read como autorização de write.
- Não encerrar após diagnóstico: executar os passos admissíveis, registrar bloqueios factuais e produzir código/testes verificáveis.

## Resultado mínimo necessário

PR 1 = descoberta real + Fast Path e Trello READ end-to-end com zero System-2 em matches exatos; PR 2 = Trello mutation certificada e readback; PR 3 = D-039 active learning + browser run-local condicionado a qualificação; PR 4+ = Instagram/WhatsApp/ChatGPT em sequência orientada por risco. Se PR1 estiver bloqueado por H-079/CI, produza docs, auditoria de corpus sanitizada e testes RED, reportando razão específica, sem mesclar alterações de runtime.

INICIE AGORA pelo OPC-00, reporte a baseline e os caminhos encontrados, e execute diretamente cada fase liberada até a entrega real.