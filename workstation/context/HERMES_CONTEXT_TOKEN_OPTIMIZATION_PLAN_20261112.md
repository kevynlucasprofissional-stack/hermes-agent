# Hermes Work — Otimização de tokens e compactação (2026-11-12)

**Status: PLANO TÉCNICO PREPARADO — sem implementação ou homologação de código.**
**Repositório:** C:\Github\hermes-agent
**Escopo:** custo de prompt inicial, tool_search, compactação sem progresso e reasoning_content antigo; sem mudanças nas políticas de autoridade do Browser/Kanban/WhatsApp.
**Fonte de evidência:** inspeção real no Windows autorizado em 12/11/2026; código local no HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e e registros do perfil Hermes. PRs upstream são *referências de solução*, não implementações homologadas neste fork.

## 1. Diagnóstico consolidado e limites

- Provedor/modelo: deepseek/deepseek-flash; sessão observada 20261112_150450_a1e413.
- Uso medido pelo provedor: primeira chamada da sessão 34.574 tokens; chamada posterior de 16h51 87.671 tokens (87.424 cache-read; não são 87 mil tokens novos). Contexto frequentemente 80–90 mil.
- Instrumentação: agent/turn_request_assembly.py prepara api_messages e tools_for_api=agent.tools; agent/turn_context.py::build_api_messages monta a cópia de envio; agent/turn_usage.py registra uso do provedor. O medidor agent/context_breakdown.py estima categorias, não é dump exato do payload.
- Configuração ATUAL de %LOCALAPPDATA%\hermes\config.yaml, lida seletivamente sem segredos: compression.enabled=true; threshold=0.4; threshold_tokens=32000; target_ratio=0.15; protect_last_n=8; tail_mode=lean; proactive_prune_tokens=18000; proactive_prune_min_result_chars=4000; proactive_prune_min_reclaim_tokens=3000; tools.tool_search.enabled=auto; model.default=deepseek-flash; model.provider=deepseek.
- tool_search iniciou com 55 ferramentas visíveis, 30 adiadas (log das 15h04); NÃO presumir que ferramentas adiadas estão no payload. prompt-size --platform desktop (7 tools) não representa a sessão CLI/TUI do backend; o prompt-size --platform cli mediu 34 tools em diagnóstico offline, também não é o payload da chamada real.
- Historicamente estimados na chamada de 87.671: raciocínio de assistente 28,4k; argumentos de chamadas 7,5k; respostas de ferramentas 6,3k; conteúdo de usuário/resumos 8,4k; texto do assistente 1,1k; resíduo de aproximadamente 35,9k reúne sistema, esquemas e diferenças do estimador (NÃO atribuição exata independente).
- Na compactação de 16h48: 129->85 mensagens e estimativa ~104.184->79.372; ~37.312 tokens de tail protegida; nova tentativa com failure_class=empty_post_handoff_window. Em uma sessão recém-criada, 34.574 tokens já ultrapassam threshold_tokens=32000: o disparo antecipado é causado pela configuração, não por crescimento da conversa.
- A rota chat_completions do DeepSeek devolve reasoning_content ao modelo: agent/message_sanitization.py::apply_reasoning_content_policy com ReasoningReplayRoute(pad=True, carriers={reasoning_content}). Não remover raciocínio em curso nem desativar echo genericamente.
- Git: main@f1d5ab2f com cerca de 590 entradas de WIP antes deste documento; main atrás de origin/main por 1 commit na inspeção; agent/context_compressor.py e agent/message_sanitization.py estavam limpos, mas model_tools.py e várias integrações estão modificados. worktrees existentes; não trocar main, fazer stash/reset, descartar WIP ou iniciar merge upstream como gate.
- Fluxos Browser/Kanban/WhatsApp têm mudanças em paralelo e homologações parciais: não realizar mutações externas para medir token. Não declarar homologação real a partir de teste isolado.

**Metas condicionais:** <40k tokens na operação simples representativa, >=30% de redução de input em cenários equivalentes sem mais chamadas/falhas/latência material; nenhum loop de compactação sem material elegível. Metas, NÃO resultados já demonstrados.

## 2. Mapa preciso de intervenção

| Área | Código real | Ação recomendada |
| --- | --- | --- |
| Request ao provedor | agent/turn_request_assembly.py; agent/turn_context.py::build_api_messages; agent/turn_usage.py | Extrair contagens temporárias por categoria somente em ambiente controlado, sem logar conteúdo/PII |
| Detalhe estimado | agent/context_breakdown.py::compute_session_context_breakdown; hermes_cli/prompt_size.py | Reusar estimadores, sinalizar derivação/limites; evitar contador paralelo |
| Tools | tools/tool_search.py::assemble_tool_defs; agent/agent_init.py::_load_tools; model_tools.py; hermes_cli/config_defaults.py | Medir tools_for_api efetivo, evitar descrições/esquemas desnecessários, preservar descoberta |
| Config de disparo/poda | %LOCALAPPDATA%\hermes\config.yaml; agent/agent_init.py; agent/context_compressor.py | Experimentar limiar sem exceder custo fixo e verificar por que poda já ativa não recupera |
| Poda sem janela | agent/context_compressor.py::compress, _finalize_compressed; agent/conversation_compression.py::_commit_compaction; agent/conversation_compression_archive.py | Corrigir descarte do candidato podado e persistência de linhas carregadas; PR #137513 |
| Evitar sumarização inútil | agent/context_compressor.py::compress e _feasibility_skip | Apenas se persistir custo evitável; PR #138563 |
| Reasoning histórico | agent/context_compressor.py::_finalize_compressed; agent/message_sanitization.py::apply_reasoning_content_policy | Reduzir somente histórico não corrente em fronteira segura; PR #132020 |
| Fluxos externos | workstation/browser_operation_readback.py; workstation/integrations/hermes; tools/browser_workstation.py | Reutilizar regressões/QA existentes sem enviar WhatsApp ou alterar Trello |

**Conjuntos focais existentes:** tests/hermes_cli/test_prompt_size.py; tests/agent/test_context_breakdown.py; tests/tools/test_tool_search.py; tests/agent/test_proactive_prune_config.py; tests/agent/test_proactive_prune_loop_wiring.py; tests/agent/test_proactive_prune_rearm_threshold.py; tests/agent/test_proactive_prune_restart_safety.py; tests/agent/test_context_compressor_structural_backoff.py; tests/agent/test_compression_feasibility.py; tests/agent/test_compression_persistence.py; tests/agent/test_deepseek_reasoning_content_echo.py; tests/agent/test_reasoning_replay_routes.py. Confirmar nomenclaturas antes da execução.

## 3. Soluções e patches candidatos (PREPARADOS, NÃO APLICADOS)

**C1 — configuração existente, teste controlado:** threshold_tokens=32000 é menor que o prompt inicial medido de 34574. Em perfil de teste isolado, comparar valor atual com um *candidato experimental* de 48000 tokens (não é valor final escolhido), mantendo threshold=0.4 e demais parâmetros. Medir se o disparo desaparece na sessão nova; medir cache/latência em sessão com histórico. Não editar a configuração operacional sem ter baseline comparável e rollback. proactive_prune_tokens já é 18000: investigar reason no-op (tail_only/nothing_eligible/reclaim_below_minimum/rearm mark) antes de alterar; não "habilitar" algo já habilitado.

**C2 — poda em retorno no-op:** no ramo if compress_start >= compress_end e no ramo if not turns_to_summarize de agent/context_compressor.py::compress, a implementação atual retorna canonical_messages após _prune_old_tool_results, descartando a economia preliminar. O PR upstream #137513 fornece um caminho concreto: quando pruned_count>0 e o candidato realmente encolheu, devolver a finalização do candidato com as mesmas verificações e marcação de persistência, preservando linhas inalteradas via agent/conversation_compression_archive.py. NÃO copiar somente a alteração do return: o PR também muda ownership/coverage/commit, sob risco de duplicar linhas ou perder histórico. Preferir extrair/adaptar o conjunto mínimo dos hunks do PR, mantendo interfaces do fork; incluir teste RED com handoff-only, tool output elegível, SQLite QA e relançamento da sessão. Se não houver poda elegível, retornar o original e preservar backoff sem fazer chamada de sumarização.

**C3 — baixa recuperação:** se após C2 continuar ocorrendo resumo caro com head/tail protegidos e middle incapaz de cobrir o déficit, adaptar guard de expected savings do PR #138563 para não chamar LLM na primeira tentativa inútil; não bloquear compressões forçadas nem recuperação perto do limite rígido. Provar pela telemetria antes de adicionar esse guard.

**C4 — reduzir raciocínio antigo, somente se necessário:** o PR #132020 concentra a alteração na finalização de compactação. Reaproveitar uma seleção baseada no último turno user acionável; antigos assistant rows podem perder reasoning/reasoning_content só quando já absorvidos na síntese e sem tool round pendente; as mensagens do turno atual continuam intactas. Em DeepSeek, o sanitizador ainda deve prover " " em assistant histórico sem reasoning, com carrier obrigatório. Aplicar só a fronteiras de compactação (mudança de cache já ocorre), não em cada chamada do modelo; medir trade-off em cache. Criar teste incluindo mensagens compaction handoff e tool_call continuado.

**Referências GitHub verificadas em 12/11:** #153254 e #152474 mesclados (redução de esquemas); #137513, #138563 e #132020 ainda abertos. A referência do PR não autoriza cherry-pick indiscriminado; comparar com código local e aplicar por partes.

## 4. Prompts executáveis, por dependência

### PROMPT 1 — Medição efetiva e otimização do custo fixo (P0)

MISSÃO: no Windows autorizado, repo C:\Github\hermes-agent, reduzir o custo inicial do prompt do Hermes Work sem alterar contratos operacionais. Atue com autonomia, MVP Quality First; leia workstation/context/HERMES_CONTEXT_TOKEN_OPTIMIZATION_PLAN_20261112.md, root AGENTS.md e workstation/context/README.md. Estado conhecido: main@f1d5ab2f, ~590 alterações prévias; %LOCALAPPDATA%\hermes\config.yaml já contém threshold_tokens=32000, protect_last_n=8, proactive_prune_tokens=18000, tool_search=auto. Primeira chamada real deepseek-flash=34.574 tokens; 55 ferramentas visíveis/30 adiadas no log, sem atribuição exata em wire. Não recompute investigações históricas: confirme apenas configuração efetiva e baseline de uma operação simples reproduzível.

1. Preserve checkout/serviço ativo/segredos e WIP. Para alterações use worktree+branch isolados com base explicitamente identificada; verifique se diferenças locais relevantes do runtime precisam ser reproduzidas. Não mudar branch do checkout compartilhado.
2. Inspecione agent/turn_request_assembly.py (tools_for_api), agent/turn_context.py::build_api_messages, agent/context_breakdown.py, hermes_cli/prompt_size.py, tools/tool_search.py e model_tools.py. Reuse mecanismos de medição já existentes; adicione só se indispensável uma instrumentação temporária e restrita, com totais de caracteres/tokens por categoria, quantidade e nomes das tools, sem conteúdos privados. Registre uso exato retornado pelo provedor e taxa cache-read.
3. Compare os esquemas realmente enviados com a lista de ferramentas frequentemente usadas (terminal, execute_code, Browser, WhatsApp, Kanban) e procure schemas redundantes. Identifique se PRs upstream #153254/#152474 já foram incorporados; adapte somente diferenças úteis. Preserve descoberta das ferramentas adiadas e evite reduzir ferramentas necessárias.
4. O threshold de 32k menor que 34,6k é explicitamente configurado. Experimente 48k em perfil QA isolado contra 32k, apenas para eliminar a compactação na primeira chamada; confirme se 48k permanece adequado a workload real. NÃO reajustar indiscriminadamente a configuração operacional. Identifique também por que a poda habilitada em 18k não recupera tokens: examine no-op/rearm/persistência/candidato sem material elegível.
5. Teste a montagem da requisição, descoberta de uma ferramenta adiada e um fluxo simples de ferramenta, com comparação de input/cache/latência antes/depois. Use testes focais tests/tools/test_tool_search.py, tests/agent/test_context_breakdown.py, tests/hermes_cli/test_prompt_size.py e test_proactive_prune_config.py, conforme necessidade.

ACEITE: custo fixo atribuível a system/tools/histórico separado sem confundir estimativa com usage real; reduzir apenas o que foi demonstrado; nenhuma ferramenta indispensável perdida; nenhuma alteração da configuração ativa sem baseline e reversão. Entrega: arquivos alterados, números antes/depois com fonte, testes e resultado operacional; atualizar este plano e o jornal existente. Se o prompt inicial já estiver suficientemente otimizado, encerrar sem refatorações.

### PROMPT 2 — Recuperar poda e impedir compactação sem progresso (P0)

MISSÃO: resolver o defeito concreto do Hermes ContextCompressor no Windows, no repo C:\Github\hermes-agent. Leia workstation/context/HERMES_CONTEXT_TOKEN_OPTIMIZATION_PLAN_20261112.md e as regras AGENTS. Baseline: deepseek-flash com threshold_tokens=32000, proactive_prune_tokens=18000 já ativado, protect_last_n=8; logs de 12/11 registram 104.184->79.372 tokens após compactação e falha empty_post_handoff_window; a função agent/context_compressor.py::compress poda resultados antigos, mas retorna canonical_messages nos ramos no_compressible_window / empty_post_handoff_window. Preserve WIP, bases e prompt caching; não sincronize upstream integralmente.

1. Inspecione apenas agent/context_compressor.py::compress/_finalize_compressed, agent/conversation_compression.py::_commit_compaction, agent/conversation_compression_archive.py e tests/agent/test_context_compressor_structural_backoff.py, test_compression_persistence.py, test_compression_feasibility.py. Compare com o PR upstream #137513 (aberto): sua solução precisa reter a poda útil mesmo quando inexiste middle para resumir, sem inserir resumo falso e sem duplicar registros em SQLite. Considere o mecanismo de carried rows/coverage/commit do PR: NÃO implementar apenas um return pruned_msgs.
2. Construa regressão RED com transcript realista que contenha handoff compactado, resultado de ferramenta antiga passível de poda, histórico novo protegido e SessionDB QA temporário. Demonstre antes da correção que o retorno perde a poda; depois prove que a candidata compactada persiste, que as linhas não mudadas não duplicam e que o histórico original é recuperável/arquivado.
3. Implemente o menor patch compatível, preservando pending tool rounds, compaction ownership/watermark, invariantes de cache e estados de falha/retentativa. Sem migrações nem novo sistema de estado. Considere o guard do PR #138563 somente se a telemetria provar custo real de compressões com recuperação irrisória, além do no-op já evitado pelo mecanismo existente.
4. Execute os testes RED/GREEN e regressões focais de persistência, concorrência, backoff e DeepSeek. Rode uma compactação real em QA isolado e confirme tokens recuperados; não aplique compactação destrutiva sobre sessões de produção.

ACEITE: sumário/resultado de ferramenta preservado funcionalmente; poda útil sobrevivendo a empty_post_handoff_window; 0 chamada de sumarização quando não há janela elegível; 0 duplicação/perda de linhas no armazenamento; sem novo loop no-op. Entrega: diff, testes e logs QA, economia real observada, quaisquer limitações; registrar no plano e no journal. Se a causa específica já tiver sido corrigida no runtime atual, provar e encerrar sem patch redundante.

### PROMPT 3 — Redução segura de raciocínio histórico DeepSeek (P1; CONDICIONAL)

MISSÃO: após PROMPT 2 e só se a medição residual justificar, diminuir reasoning_content obsoleto em contextos longos do DeepSeek. Repo C:\Github\hermes-agent. Leia workstation/context/HERMES_CONTEXT_TOKEN_OPTIMIZATION_PLAN_20261112.md e aceite dos prompts anteriores. Medição histórica antes de mudanças: ~28,4k tokens atribuíveis a raciocínio em sessão ~87,7k; DeepSeek chat_completions exige reasoning_content de assistant em turns com chamadas de ferramentas e o sanitizador usa pad não vazio. Não alterar o envio WhatsApp/Browser/Kanban, nem apagar reasoning do banco operacional.

1. Verifique no código e logs se após P1/P2 o reasoning antigo continua sendo custo relevante. Inspecione agent/context_compressor.py::_finalize_compressed e agent/message_sanitization.py::_replayable_reasoning_text / apply_reasoning_content_policy. Compare com PR upstream #132020, ainda aberto. Teste a hipótese de que reasoning de turns anteriores pode ser descartado somente na fronteira de compactação, sem perder o reasoning do turno atual ou ferramenta pendente.
2. Crie teste RED que tenha dois turns antigos com reasoning, um turno atual com múltiplos assistant/tool_calls, resumo/handoff e mensagens protegidas. Prove no payload DeepSeek que o raciocínio atual é retransmitido integralmente, que antigos recebem pad válido quando exigido e que tools e argumentos não mudam. Inclua teste de fallback para rota strict que não aceita reasoning_content.
3. Introduza o menor helper na finalização de compactação, não no hot path por chamada; mantenha integridade de transcrição e cache (não invalidar prefixo no meio do turno). Se houver risco de 400 ou perda funcional, não forçar a alteração: preservar comportamento original e reportar causa técnica.
4. Execute testes focais tests/agent/test_deepseek_reasoning_content_echo.py, tests/agent/test_reasoning_replay_routes.py, testes de compactação relevantes e uma sequência de ferramentas real em perfil QA. Compare input tokens efetivos e cache com o baseline.

ACEITE: queda mensurada de tokens atribuíveis ao reasoning já absorvido, sem 400, perda de tool_call/receipt ou aumento compensatório de chamadas. Registrar patch, testes, números e decisão. Se P1/P2 já atingiram metas, ABSTER-SE de implementar esta etapa.

### PROMPT 4 — Homologação operacional e encerramento (P0 final)

MISSÃO: homologar o MVP de contexto do Hermes Work a partir dos patches aprovados de PROMPTS 1–3. Repo C:\Github\hermes-agent; preserve serviço ativo, WIP e bancos operacionais. Leia workstation/context/HERMES_CONTEXT_TOKEN_OPTIMIZATION_PLAN_20261112.md e relatórios dos prompts anteriores. Nunca confunda build/mocks com funcionamento real.

1. Registre baseline e resultados finais em cenários equivalentes: (a) sessão nova e uma operação de ferramenta simples; (b) conversa operacional com chamadas de ferramentas suficiente para acionar crescimento e compactação; (c) chamada de ferramenta adiada via tool_search; (d) navegação Browser e readback QA para Kanban sem mutações externas não autorizadas. Para WhatsApp, valide seleção de destinatário e caminho de admissão sem clique de envio; somente envio real com destinatário e autorização específicos, se já existirem.
2. Observe no backend carregado os logs de prompt_tokens, cache_read, custo/latência, número de requisições e resultados. Garanta que a versão editada foi realmente carregada (não inferir do código em disco); se houver reload/restart, faça apenas de forma compatível com sessões e alterações paralelas.
3. Comprove no armazenamento QA que a compactação não duplicou ou perdeu linhas e que o fluxo Browser->Kanban existente não regrediu. Reaproveite testes já disponíveis; não desenvolva outra infraestrutura de homologação.
4. Compare os indicadores por *operação concluída* e não apenas por requisição. As metas são <40k tokens em tarefa simples e >=30% menos input médio em cenários comparáveis, com taxa de sucesso, cache-hit e latência sem piora material; se uma meta for inviável sem risco desproporcional, registrar o motivo e conservar o melhor resultado.
5. Faça rollback pontual apenas de regressões comprovadas, sem reset/stash/force. Atualize plano, journal e entrada README conforme status final. Descreva o que foi alterado, executado, verificado, não verificado e adiado.

ACEITE: execução no runtime real com resultados observáveis, sem loops estruturais inúteis e sem regressões materiais; métricas antes/depois registradas; encerramento ao alcançar resultado suficiente, sem novas etapas especulativas.

## 5. Dependências, gates e limites

- P1 antes de P2: atribuição e configuração correta evitam patch desnecessário; P2 pode usar fixtures independente da instrumentação, mas exige baseline e diagnóstico de persistência.
- P2 antes de P3: normalizar fronteira e persistência de compactação antes de alterar reasoning; P3 só executa se as metas não forem alcançadas.
- P4 após o último patch útil. Não executar WhatsApp real sem autorização/destinatário; não reinterpretar "sucesso" com Browser/SQLite fake como aceitação do mesmo backend operacional.
- Proteções essenciais: DeepSeek must-echo, integridade da SessionDB, tool-call pairing, idempotência das mutações Browser/WhatsApp, cache prefix estável, TaskRun/Kanban e worktrees/WIP.
- Não introduzir novo motor de contexto, schema paralelo, outro banco, código de segurança extra sem evidência, ou refatoração de módulos não envolvidos.
- Não acionar ações irreversíveis na branch shared main. Se branch isolada não reproduzir o backend com WIP, registrar explicitamente a divergência, transportar apenas diff relevante e manter a qualificação operacional pendente.

## 6. Estado final DESTA PREPARAÇÃO

- **Verificado:** arquivos/funções no HEAD, configuração efetiva e logs anteriores, tool_search real, pontos de no-op e política DeepSeek; PRs e disponibilidade de testes.
- **Documentado:** este plano e os quatro prompts executáveis; os patches candidatos foram mapeados para códigos/PRs e contratos reais.
- **Não implementado:** nenhum ajuste de runtime/threshold/toolsets/razão de replay; sem cherry-pick; sem commits/push, restart ou mutação externa.
- **Não validado ainda:** redução de 30%, contexto <40k, eficácia de novas mudanças de compactação e E2E pós-patch no backend.
- **Próxima ação:** PROMPT 1, no worktree isolado apropriado, preservando o checkout compartilhado.
