# Decisoes arquiteturais OL-MVP (16/10/2026)

## D19 — Separar avanço de desenvolvimento e comprovação de produto (17/10/2026)

Dado o relatório P1C local de 17/10/2026: é permitido avançar ao **P2-PREFLIGHT** e interromper hardening indiscriminado, pois testes reportaram 5/5 P1C + 40/40 compiler + 7/7 boundary. Mas a publicação PR #95 não contém as mudanças recentes e o recibo com IDs `"real"` e refs de arquivos de testes não prova `RunLocalAdopter` nativo, qualificação DIRECT, persistência inter-run ou custo líquido. **P2 não deve transformar relatório de fixture em credencial operacional.**

Prioridade: (1) recuperar/preservar/push alterações locais, (2) uma E2E real via Gateway→TaskRun→owner com IDs de operação, recibos e readback, (3) seleção barata determinística antes de System-2 usando Router/registry existentes, (4) medir custo e resultado efetivos. Sem perguntas adicionais ou nova infraestrutura. Stage A e permissões são soberania humana, não autoatribuição. Quatro ImprovementRuns, EmbeddingGemma, BM25, LAYA, versionamento hierárquico, fila econômica continuam DECISÕES ARQUITETURAIS válidas, não provas implementadas nem escopo deste patch.



## D18 — Critério de avanço após P1B implementado (16/10/2026)

`P1B` implementou readback de `browser_extract_items`/aceitação por WorkItem e mineração read-only no PR #94 `27b6376535dc`. Seu teste de 3 WorkItems é integração **sintética**: todos os cards processados por `worker`, não há execução de oferta por `RunLocalAdopter` e não há consumo real de modelo. **Candidato ≠ oferta qualificada ≠ adoção na TaskRun ≠ persistência noutra TaskRun ≠ economia paga.** P1C deve provar essas transições no gateway/Electron real, sob owner e política legítimos.

O vínculo `task_id/run_id/operation_id/raw_result_ref/transition_ref` é uma cadeia causal exata; em produto, falta de prova NÃO permite criar sample/op ID nem escolher a última amostra. `readback` indep. não é atestado DIRECT, e resultados read-only não ampliam permissões. Se Stage A impedir DIRECT, continuar a TaskRun adaptativa, registrar SHADOW e não declarar produto verificado. Após prova real ou dependência externa de qualificação isolada, começar P2 enxuta, preservando D01–D17: seleção híbrida evolutiva, memória hierárquica, 4 especialidades futuras e orçamento global de usuário.



## D17 — Aplicação 80/20 após o primeiro Browser nativo (16/10/2026)

`P1.0 PASS` implica que **não** se deve refazer Browser nativo/boot agora. As provas máximas são observações de runtime real e aceitação canônica, não êxito de fixture. Uma leitura read-only verificada tem **resultado** generalizável, não mutação do DOM; pode alimentar compilação por uma projeção específica após verificador independente do owner. Um `browser_extract_items` com três cartões não são três WorkItems da TaskRun. P1B trata output → accepted sample → compiler → run-local, preservando D01–D16 e Stage A. Código fonte operacional só modificado com autorização explícita, mesmo quando proposta experimental passa testes. PR P1B é pacote de pesquisa/patch experimental, não aprovação do executor.


Estas sao DECISOES DE PRODUTO, nao implementacoes ja comprovadas.

D01 — TaskRun tem dois objetivos simultaneos: concluir solicitacao e observar oportunidades; aprender nao bloqueia indefinidamente tarefa.
D02 — Adocao in-flight: candidato validado do item 1 pode ser testado controladamente no item 2, com fallback LLM apenas para trecho desconhecido e sem repetir efeito incerto.
D03 — Todas as tarefas alimentam memoria operacional leve; compilacao seletiva e progressiva, inclusive antes de recorrencia historica.
D04 — Telemetria independente de memoria, eventos tipados comuns, retencao propria, retorno liquido incluindo custos de aprendizagem.
D05 — Aprendizagem hierarquica: microcapacidades, procedimentos e workflows composicionais; reparar na menor unidade responsavel.
D06 — Promocao global otimista via referencia logica, preservando versoes e rollback contextual; integridade/contrato e permissoes continuam gates.
D07 — Aprendizagem apos TaskRun com fila persistente e ImprovementRun autonoma batelada, sem recursao infinita.
D08 — Quatro especialidades: skills, capacidades operacionais, investigacao do codigo-fonte e selecao de capacidades; um runtime, uma infraestrutura compartilhada.
D09 — SourceResearchRun pode ler repositorio, testar patches em sandbox e recomendar; NAO pode integrar ou editar fonte operacional sem aprovacao expressa.
D10 — Hipoteses: observada, fundamentada, testavel, validada experimentalmente, pronta para revisao, autorizada; ganho experimental nao e ganho em producao.
D11 — Modelos escolhidos por qualificacao, custo e complexidade; abster-se se modelo inadequado; revisao estrutural demanda modelo qualificado.
D12 — Orçamento global do usuario: teto financeiro/tokens/CPU/calls/concorrencia imutavel pelas Runs; quotas por especialidade, exploracao e investimento por retorno realizado, esperado e habilitador.
D13 — Selecao multimétodo: fingerprint/exato, BM25, embeddings (EmbeddingGemma possivel, nao requisito), LAYA System-1 e fallback System-2; Router/Policy comprovam admissibilidade e autoridade.
D14 — SelectionImprovementRun aprende a recuperar, classificar, compor e reconhecer incerteza sem promover mudanca de fonte nao autorizada.
D15 — Priorizar primeiro circuito real item1->item2 na mesma TaskRun, depois persistencia, eficiencia e autonomia pos-TaskRun. Dogfood real e prova maxima; testes isolados nao qualificam produto.
D16 — Promocao global de capacidades nunca concede autorizacao adicional; SHADOW e qualificacao DIRECT permanecem intactos.

Detalhes calibraveis por benchmark nao exigem novos questionarios. Os antigos explicit_seed.py/test_explicit_seed.py nao representam este MVP, manter apenas como historico.
