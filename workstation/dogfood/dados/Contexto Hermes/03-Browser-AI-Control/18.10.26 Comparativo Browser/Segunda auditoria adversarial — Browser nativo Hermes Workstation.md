**Data:** 18–19/10/2026 (horário de Brasília)  
**Fonte principal de implementação:** Desktop Commander, máquina `DESKTOP-3NA47UH`, repositório local `C:\Github\hermes-agent`  
**Branch observada:** `feat/d049-browser-80-20-impl-20261018`  
**HEAD observado e revalidado:** `fd80408ab29c9cc701dacf1fbe4ceb7899c1a836`  
**Outras fontes:** PDF _18.10.26 Análises comparativas do Browser por Fable 5.1(1).pdf_ (183 páginas), plano anterior em `Texto colado(20261019-025128).txt`, documentação D-049 local e relatório da primeira auditoria.  
**Regra:** nenhuma modificação deliberada do código, Git, branches ou documentação local durante a investigação; testes específicos apenas. Resultados descrevem o estado observado, não a produção qualificada.

## 1. Veredito

**A tese arquitetural do plano anterior está correta: preservar o BrowserRuntime Electron, BrowserTask, lease, controller, ExecutionJournal, ArtifactStore, compilador e telemetry como autoridades únicas; ampliar a cadeia existente. Contudo, a _ordem de implementação anterior não maximiza mais o 80/20_.** Ela foi ultrapassada por código recente e não identificou suficientemente dois _gaps de integração entre componentes existentes_:

1. **Observação barata não chega ao agente como uma capability completa.** O Electron aceita views `summary`, `action_map`, `focus`, `content` (`workstation-browser-runtime.ts:~2950, ~3872`), mas o contrato público `browser_snapshot` em `tools/browser_tool.py:495-508` expõe somente `full`; a função de ferramenta Python em `tools/browser_tool.py:930` também não oferece os novos parâmetros. O `project_model_browser_payload` em `tools/browser_workstation.py:966` reconhece a gramática do snapshot canônico, não garante deduplicação de `elements` para as views. Resultado: implementação parcialmente inacessível e economia model-facing não comprovada.
2. **A validade de dados extraídos não chega obrigatoriamente ao domínio durável.** O Electron calcula `schema_valid` (`workstation-browser-runtime.ts:~4654-4682`), mas retorna `success: true` para captura mesmo com schema rejeitado. O domínio `workstation/browser_projection.py:39-~160` persiste itens e declara `valid_count` a partir de sua própria validação genérica (`SemanticValidator(required_fields=['title'])`), sem consumir `schema_valid`. Isso pode gerar um falso sinal de conformidade com o contrato solicitado.

**Terceiro bloqueador imediato:** `workstation-browser-runtime.ts:74` importa `workstation-browser-snapshot-views.ts`, mas o arquivo está **untracked**, ausente do `HEAD` (confirmado por `git cat-file -e HEAD:...` com erro). Um checkout limpo do commit atual não dispõe desse import. O teste também está untracked. Isto deve ser tratado como gate de integração de primeira ordem.

**Reorientação:** _fechar o ciclo já iniciado_ → _corrigir a verdade semântica_ → _medir e otimizar a observação model-facing_ → _então melhorar recuperação de alvo, se as falhas justificarem_. Não recomeçar B0/B1.

## 2. Estado real da árvore e consequências

### O que já avançou em relação ao plano anterior

|Assunto|Evidência local|Qualificação|
|---|---|---|
|Sanitização em valores de extração (B1.2)|`workstation-browser-extract-cache.ts`, função `redactSecretValues`; commit `fd80408`|Implementação presente; testes unitários de esquema, sem prova de cobertura universal|
|Validação estrutural de extrações (B1.3)|`validateExtractedItems` em `workstation-browser-extract-cache.ts:320`; uso em `workstation-browser-runtime.ts:~4667`|Implementada parcialmente, integração durável incompleta|
|Views compactas (B1.1)|`workstation-browser-snapshot-views.ts` (novo não rastreado), `renderSnapshotView` utilizado no runtime, testes|Funciona em testes unitários; arquivo ausente em checkout limpo; agente não tem schema de tool adequado|
|Segurança do bridge (B0.1)|`workstation/browser_bridge.py` modificado; `test_browser_bridge_security.py` novo|7 testes passaram, 1 pulado. Patch ainda não commitado|
|Escopo correto do Modo Aprender (B0.2)|`startLearning` rejeita `ownerTaskId` ausente; teste modificado em `workstation-browser-runtime-task.test.ts`|1 teste B0.2 passou; não substitui E2E UX|
|Batch|`workstation-browser-batch.ts`, callsite do runtime; esquema do agente|Já implementado; receipts locais não equivalem a prova externa|
|Snapshot delta|`workstation-browser-snapshot-diff.ts`, `snapshotForEntry`|Implementado; resposta tradicional ainda inclui snapshot completo; economia não comprovada|
|Readiness semântica|`BrowserReadinessContract` e preflight `task_compiler.py:652`|Presente como preflight opcional; não universal|

### Risco de sobrescrita por IAs concorrentes

No momento da auditoria havia alterações rastreadas não commitadas em `workstation/browser_bridge.py`, `apps/desktop/electron/workstation-browser-runtime-task.test.ts` e arquivo de workspace Obsidian, além de muitos diretórios e arquivos novos não rastreados. O repositório utiliza vários worktrees e branches auxiliares. **Não executar `git reset --hard`, `git clean -fd`, merges automáticos nem checkout forçado.** Antes de uma execução implementadora, conferir se o conteúdo foi alterado desde este diagnóstico.

## 3. Verificação executada no computador

|Procedimento|Resultado|O que comprova / não comprova|
|---|---|---|
|`python -B -m pytest -q -p no:cacheprovider workstation/tests/test_browser_bridge_security.py` com bytecode desativado|**7 passed, 1 skipped**|Comprova os contratos executados de caminho; symlink não foi validado naquele ambiente; não prova ausência de TOCTOU sob adversário concorrente|
|Vitest `workstation-browser-snapshot-views.test.ts` no projeto Desktop|**11 passed**|Projeções puras, orçamento e foco em fixtures; não mede uso do agente nem tokens|
|Vitest `workstation-browser-extract-schema.test.ts`|**9 passed**|Subconjunto de schema nas amostras existentes; não cobre todos os invariantes em inputs vazios e integração de WorkPlan|
|Vitest `workstation-browser-runtime-task.test.ts -t B0.2`|**1 passed, 36 skipped**|Comprova o gate exercitado de Learning; não é dogfood real com usuário/Chromium|
|`git grep` + `git cat-file` sobre `HEAD`|Falha da existência de `workstation-browser-snapshot-views.ts` no commit|Prova direta de que import presente no commit aponta para arquivo ainda não rastreado|
|Inspeção do `browser_snapshot` schema/função Python|`full` apenas|Demonstra ausência dos parâmetros de view na API model-facing apresentada nesse schema|
|Revisão de `workstation/browser_projection.py`|Não utiliza `schema_valid`|Demonstra descontinuidade entre validação Electron e critério de sucesso durável|

Os testes executados preservaram os arquivos rastreados não commitados observados antes da auditoria. **Não foram executados:** build/CI completo, Chromium E2E de fluxo externo, benchmarks de tokens/faturas, sessão longa e adversarial de efeitos remotos.

## 4. Julgamento adversarial das recomendações do PDF

Referências documentais agrupadas: Stagehand (p. 1–8; 117–125; 175–183), Lattice (p. 34–43), BrowserTrace (p. 25–34), DriftLock (p. 8–14), browser-use (p. 58–66), BrowserTransactionBench (p. 85–91), VibeSurf (p. 170–175) e BrowserOS (p. 14–20; 52–58; 156–163). O PDF reúne 26 comparações e contém propostas conflitantes: diversas analisam um Hermes anterior ao código de batch/delta/cache e chamam inexistente o que está implementado.

|Referência/proposta|Juízo atualizado|Fundamentação|
|---|---|---|
|Stagehand: novo `act` com self-healing|**Adiar**|Há refs, anchors, `resolvePoint` e gates antes de CDP; novo roteador/LLM de seleção pode ampliar custo e duplicar efeitos. Primeiro medir casos de `STALE_REF`|
|Stagehand: locator imutável universal|**Adiar**|`@eN`, anchor, identity já atendem parte do objetivo; comprovar necessidade de locators persistentes antes de abstratizar|
|Stagehand: `extract(schema)`|**Corrigir integração existente**|Validator subset agora existe, mas `schema_valid` pode desaparecer no resumo durável|
|Stagehand: batch|**Não recriar**|Presente; semântica real é sequencial com checkpoints, _não_ transação atômica reversível|
|Lattice: views budgeted|**Fechar exposição ao agente**|Projeção existe; precisa schema, deduplicação segura e benchmark|
|Lattice: grandes reduções 76–99%|**Não extrapolar**|Valores da referência não equivalem a economia real no Hermes|
|Lattice: graph multimodal/delta estrutural|**Pesquisa/P3**|Incremento complexo e potencial redundância com snapshot existente|
|BrowserTrace: novo trace store SQLite|**Descartar agora**|Hermes dispõe de ExecutionJournal, PortableTrace, ArtifactStore; evitar segunda autoridade|
|DriftLock: known-good replay/hash por elemento em todo clique|**Adiar e amostrar**|Pode inflar CPU, armazenamento, sensibilidade e latência; adotar diagnóstico opt-in|
|BrowserTransactionBench: prova externa|**Preservar como gate central**|ACK do browser e estado local não são persistência remota; importante nos casos de escrita incerta|
|browser-use: batch inexistente|**Obsoleto**|Já conectado no runtime|
|browser-use: timeout por ação|**Investigar somente se logs indicarem**|Não foi comprovada taxa relevante de timeout devido ao padrão atual|
|VibeSurf: readiness universal|**Não implementar indiscriminadamente**|Preflight existe; toda leitura com polling obrigatório pode aumentar latência e bloquear SPAs legítimas|
|BrowserOS: content-markdown walker|**P2 condicional**|Útil se as tarefas de extração de conteúdo dominarem o workload; menos útil que integração de views para automação de formulários|
|WebMCP no browser|**P3**|Dependência de suporte real das páginas, superfície de segurança e maturidade de protocolo|
|Novo backend, SDK multilíngue, bus de eventos, router LLM|**Descartar do 80/20**|Desnecessários para resolver lacunas observadas, risco de arquiteturas paralelas|
|Bridge direto como "zero-copy"|**Corrigir linguagem**|Evitar passagem pelo contexto do LLM não significa ausência de serialização/transporte; `evaluate_fn` e `ArtifactStore` ainda movimentam dados|

## 5. Achados técnicos mais críticos

### A1. Build reproduzível em checkout limpo — bloqueador G0

- **Origem:** import em `apps/desktop/electron/workstation-browser-runtime.ts:74`, módulo untracked em `apps/desktop/electron/workstation-browser-snapshot-views.ts`.
- **Verificação:** `git cat-file -e HEAD:apps/desktop/electron/workstation-browser-snapshot-views.ts` resultou em erro de objeto ausente.
- **Ação mínima:** adicionar apenas os dois arquivos de views ao commit apropriado após revisão e confirmar que o import, tests e packaging passam em checkout limpo.
- **Aceite:** checkout reproduzível sem arquivos externos ao Git; TypeScript/Vitest no HEAD exato e sem geração ad hoc.

### A2. Views economizam caracteres, mas não necessariamente tokens model-facing — P1 mais alto

- **Origem:** `tools/browser_tool.py:495-508`, `:930`; `apps/desktop/electron/workstation-browser-runtime.ts:2950`, `:~3872-3990`; `tools/browser_workstation.py:966+`.
- **Causa:** o contrato do agente não oferece `view`/`focus_ref`; a função Python assume `full`/legado; a deduplicação de `elements` exige inventário textual canônico e pode falhar diante das novas gramáticas; `snapshot_delta` ainda é enviado ao lado de `snapshot` completo.
- **Correção mínima:** adicionar parâmetros estritamente validados e documentados ao schema nativo; passá-los até o controller; separar `snapshot_view` da gramática canônica; projetar `elements` para modelo sem perder as refs selecionáveis. No caso de delta, exigir compatibilidade de baseline/identidade e omitir FULL apenas quando comprovadamente aplicável; fallback FULL quando necessário.
- **Aceite:** modelo consegue pedir `action_map` e `focus`; `@eN` mantém endereçabilidade; nenhuma observação usa alvo de aba/sessão/revisão diversa; medir bytes e tokens realmente vistos pelo LLM, não somente `snapshot_chars` interno.

### A3. Schema validado localmente mas resumo durável pode sinalizar validade indevida — P0 dado incorreto

- **Origem:** `workstation-browser-extract-cache.ts:~320`, `workstation-browser-runtime.ts:~4667`, `workstation/browser_projection.py:39-~160`.
- **Causa:** `schema_valid=false` não alimenta `valid_count` nem a validação de WorkItem; fallback para `required_fields=['title']` não garante o contrato solicitado.
- **Observação adicional:** `validateExtractedItems` itera sobre itens e só verifica keywords no interior dessa iteração; para lista vazia, um schema com keyword não suportada pode retornar `valid: true` (inferência direta do fluxo, não teste executado).
- **Correção mínima:** diferenciar sucesso da captura, conformidade ao schema e persistência; propagar verdict do owner com proveniência até o WorkPlan e resumo; impedir `valid_count` de ser apresentado como validado pelo schema quando não está; validar o schema _antes_ de percorrer o array de itens; testes negativos para vazio e schemas recusados.
- **Aceite:** `schema_valid=false` aparece em resumo model-facing e não produz WorkItems concluídos como conformes ao schema; a política mantém acesso aos dados capturados e ao erro para depuração, sem silenciar falha.

### A4. B0 security está quase pronto, mas sua prioridade operacional foi exagerada

- **Origem:** `workstation/browser_bridge.py` patch local; `workstation/tests/test_browser_bridge_security.py`.
- **Observação:** busca de `browser_save_json` em `workstation`, `tools`, `tests`, `apps` encontrou uso direto de produção não demonstrado; ocorrências encontradas estavam em definição, testes e documentação. Isso não prova ausência de consumidores dinâmicos, mas reduz a confiança no impacto imediato sobre tarefas frequentes.
- **Ação:** aceitar correção estreita, complementar documentação sobre riscos de troca concorrente de symlink; não interromper melhoria funcional para desenvolver operação baseada em file descriptor sem threat model.
- **Aceite:** suite focada, paths irmãos rejeitados, preservação de caminho resolvido e ausência de alteração da working tree de terceiros.

### A5. Learning B0.2 já foi corrigido e testado

- **Origem:** `workstation-browser-runtime.ts:~2195-2210`, `workstation-browser-runtime-task.test.ts:~1510+`.
- **Verificação:** teste B0.2 passou (1/1 escolhido). Não reimplementar.
- **Limitação de UX:** o modo Aprender em aba manual não vinculada agora recusa operação; é mais seguro que arrendar a aba errada, mas deve oferecer caminho claro de adoção/vinculação ao BrowserTask existente (por exemplo, `adoptTab`) se o fluxo do produto o exigir.

### A6. O PDF superestima benefícios de batch e readiness como mudanças isoladas

- **Batch:** no runtime existe sequência com `checkBefore`, `perform`, `verifyAfter`, `checkpoint`. Alguns efeitos locais como click exigem toggle; clique com navegação/commit externo permanece incerto. Não tornar todos os cliques 'sucesso' só para elevar throughput.
- **Readiness:** o contrato é aplicado nos preflights declarados do TaskCompiler, não em toda operação. Tornar obrigatório pode ser contraproducente; preferir `wait` sob sinais de hidratação, DOM drift ou intenção declarada, verificando custo total.
- **Autoridade:** não criar segundo BrowserRuntime, router LLM, SQLite paralelo ou journaling autoritativo.

## 6. Novo ranking de decisão: bloquear vs gerar valor

**Gates de integração (antes de liberar; não são o ranking de valor ao usuário):**

|Ordem|Gate|Situação|Trabalho residual|
|---|---|---|---|
|G0|Checkout limpo compilável + arquivos rastreados|**Bloqueado**: import aponta para arquivo não rastreado|Consolidar arquivos e executar teste/build no commit reproduzível|
|G1|Integridade de dados sob schema|**Gap identificado**|Carregar verdict até projeção durável; casos de schema vazio/inválido|
|G2|Ownership Learning e bridge path|**Ajustes locais com testes**|Revisão do diff, commit seletivo e eventual E2E UX; não reescrever|
|G3|Evidência de efeito externo real|**Sem comprovação nesta auditoria**|Executar uma tarefa controlada com readback independente e ausência de duplicidade|

**Ranking por retorno provável após gates:**

|Rank|Melhoria|Impacto esperado|Esforço incremental|Confiança|Decisão|
|---|---|---|---|---|---|
|1|Expor views e compactação ao agente sem duplicações|Alto em tarefas observacionais|Baixo–médio|Alta no gap; ganho quantitativo ainda hipótese|**Fazer agora**|
|2|Propagar `schema_valid` corretamente no WorkPlan/resultado|Alto em correção de extrações estruturadas|Baixo–médio|Alta|**Fazer agora**|
|3|Calibrar snapshot FULL vs delta (sem duplicar payload)|Potencialmente alto em tarefas repetidas|Médio|Média|**Benchmark e implementar se vencer**|
|4|Recuperação semântica estrita de alvo antes de CDP|Alto em sites que mudam DOM|Médio|Média|**Depois de medir falhas relevantes**|
|5|Diagnóstico causal leve no journal atual|Médio em investigação de falhas|Baixo–médio|Média|**Condicional**|
|6|Content-markdown universal|Médio em leitura longa, baixo em controles|Médio|Baixa sem workload|**Adiar**|
|7|WebMCP, multimodal graph, nova infraestrutura, model-router browser|Incerto|Alto|Baixa|**Pesquisar/descartar do 80/20**|

Não atribuir uma falsa pontuação decimal. O ganho depende de número de chamadas, orçamento de tokens, comportamento real de páginas e custo de erros; precisa ser aferido por cenários comparáveis.

## 7. Roadmap corrigido e número de sessões

### Sessão I — FECHAMENTO DO QUE JÁ EXISTE (uma sessão curta, G0 + G2)

**Objetivo:** transformar trabalho atual em HEAD reproduzível, sem expandir arquitetura.

- Proteger alterações não commitadas; identificar owners e conciliar diffs, preservando tudo que não é do Browser.
- Verificar/revisar `workstation-browser-snapshot-views.ts` + `.test.ts`, o import no runtime e o contrato de retorno; incluí-los em commit apropriado.
- Revisar patch `browser_bridge.py` e testes, registrar o limite TOCTOU honestamente.
- Validar teste B0.2 e caminho de UX para abas sem owner.
- Rodar Vitest focado, pytest focado, TS check/build no HEAD verificável; não confundir suite local com CI release.

**Gate:** clean checkout não perde o módulo, testes focados verdes, zero alteração não autorizada da working tree, zero falso sucesso de Learning. **Complexidade:** baixa–média.

### Sessão II — VERDADE CONTRATUAL DAS EXTRAÇÕES (uma sessão focada, G1)

**Objetivo:** um único veredito de conformidade do pedido até o WorkItem/Artifact.

- `workstation-browser-extract-cache.ts`: validar o schema (inclusive unsupported keywords) independentemente de ter itens.
- `workstation-browser-runtime.ts`: conservar a distinção entre captura, sanitização e validação.
- `workstation/browser_projection.py`: nunca transformar `schema_valid=false` em `valid_count` conforme, preservando os dados e a falha de forma explícita.
- Testes negativos de `required`, `type`, `enum`, keyword não suportada sem itens, objeto vazio, `valid_count`/`anomalies_count`, conteúdo sensível no erro e política de degradação.

**Gate:** schema inválido não pode aparecer como conformidade aprovada no resumo ou memória compilável; os casos legados sem schema continuam compatíveis. **Complexidade:** média.

### Sessão III — CONTEXTO ECONÔMICO MODEL-FACING (uma sessão focada, G2 de performance)

**Objetivo:** a IA usar a projeção mais barata que ainda permite agir corretamente.

- Expor `view`, `focus_ref`, `max_chars` (e `focus_neighbors` com limites) no schema de `browser_snapshot` e encaminhar pela mesma rota autoritativa existente, com suporte apenas em Desktop/Workstation quando pertinente.
- Manter `@eN`, identidade e truncamento; não projetar objetos duplicados para `action_map`/`focus`.
- Garantir fallback FULL seguro e evitar delta sem baseline confirmado. Não criar protocolo paralelo.
- Comparar 10–30 ciclos reproduzíveis (páginas estática, SPA, formulário e read-only) com mesmo modelo/preço e mesmas tarefas. Medir `bytes_model_facing`, tokens reais, p50/p95, número de tool calls, taxa de conclusão verificável e custo por sucesso.

**Gate:** ganho model-facing positivo e sem queda observada de taxa de conclusão no corpus controlado; se não houver benefício, conservar feature opt-in e não ampliar. **Complexidade:** média.

### Sessão IV — SOMENTE SE BASELINE MOSTRAR RELEVÂNCIA: RECUPERAÇÃO DE DOM DRIFT

- Reusar `resolvePoint`, `clickRef`, `typeRef`, `documentEpoch`, `mutationRevision` e contrato de lease.
- Apenas antes de CDP Input, tentar reaquisição por `testid/name/aria-label/role`, exigindo alvo singular e mesmo task/tab/origem; ambiguidade resulta em abstenção/handoff.
- Nunca repetir efeito possivelmente despachado; fazer readback externo independente e registrar incerteza.
- Prova: SPA com seletor alterado, alvo duplicado, mudança de aba, takeover humano, timeout antes/depois do `mousePressed`.

**Gate:** melhora de conclusão em casos de DOM drift sem duplicação/erro de alvo. **Complexidade:** média-alta. Não iniciar por entusiasmo com Stagehand, mas por evidência de falhas no workload.

**Quantidade ótima agora:** **3 sessões objetivas** para consolidar, corrigir veracidade e tornar a observação útil; **1 sessão condicional** de reaquisição. A ordem anterior de quatro sessões abrangentes era menos econômica porque tratava itens já implementados como novos.

## 8. Protocolo de benchmark proposto

**Baseline por cenário:**

- S1 navegação e leitura simples: já recebe snapshot de `navigate` — evitar snapshot redundante.
- S2 SPA que re-renderiza botões: `@eN`, DOM revision, stale/ref, readiness.
- S3 formulário de 4 etapas com submissão em servidor controlado: validação e readback externo.
- S4 lista com 20 itens extraídos: schema válido, inválido, vazio e artifact.
- S5 controle humano/Modo Aprender em aba ativa, inativa, vinculada e não vinculada.

**Métricas:** `user_to_verified_ms`, tokens de entrada e saída, bytes model-facing por observação, chamadas LLM e tools, p50/p95, proporção de execução verificada, `uncertain`, retries, ações em aba errada, duplicações, custo total até sucesso. A política de segurança/autoridade é um gate, não uma pontuação compensável. Medir na rota real do agente, não só em pure functions.

**Valores do PDF são hipóteses até benchmark:** 76–99% de economia do Lattice, 5× para batches, 30–60% em compaction histórica e outros números não devem ser declarados resultados do Hermes. Ganhos sobrepostos não devem ser somados.

## 9. Não fazer

- Não criar outro executor batch, browser controller, estado de TaskRun, lease manager, banco de journal, router de modelos ou nova engine de aprendizagem.
- Não tornar `schema_valid` opcional silencioso para WorkItems declarados conformes ao schema.
- Não capturar screenshot de toda ação nem serializar DOM inteiro em cada turno por padrão.
- Não atualizar todos os arquivos de roadmap antes de fechar e testar trabalho já iniciado.
- Não copiar BrowserOS AGPL para um produto MIT; adotar conceitos originais e checar licenças antes de reutilizar código.
- Não exigir readiness universal como condição para toda snapshot se essa mudança só adiciona esperas.
- Não chamar batch de _transação atômica_ no contrato do agente; a execução é sequencial e pode terminar com efeitos parciais.

## 10. Incertezas e próximos testes de falsificação

- **Ausência de dogfood real:** a segunda auditoria não ligou o Electron para navegar em aplicação de terceiros nem executou um TaskRun com persistência externa controlada.
- **Schema vazio e keyword não suportada:** caso derivado da leitura da função; falta adicionar teste dedicado e confirmar RED→GREEN no projeto atual.
- **Oportunidade de tokens:** nenhuma comparação end-to-end foi medida nesta sessão. Views em fixtures não constituem prova de economia.
- **Bridge reachability:** busca encontrou definição, testes e documentação de `browser_save_json`, não um callsite de produção direto no universo pesquisado. Consumidores dinâmicos não foram excluídos.
- **Atenção ao snapshot views módulo untracked:** o estado local pode mudar entre leitura e execução de outra IA; revalidar `git status`, `HEAD`, imports e testes antes do handoff.
- **Suite Python:** o teste de symlink foi pulado no host; não interpretar como segurança integral.
- **Contratos de governança:** não foram revalidados H-079/H-081/H-082 nem a CI exact-head remota; manter HOLD de release até qualificação.

## 11. Instrução objetiva para o próximo agente implementador

> Trabalhe em `C:\Github\hermes-agent`. Antes de editar, capture HEAD, branch, `git status`, diferenciais dos arquivos do Browser e owners de worktrees; nunca destrua alterações de outras IAs. Você NÃO está autorizado a recriar capacidades existentes. Priorize concluir o que já foi iniciado: (I) faça HEAD compilar a partir de checkout limpo, incluindo views e testes existentes que ainda não estão rastreados, revisando B0 bridge e Learning; (II) una o veredito de `schema_valid` da extração Electron com a projeção durável `workstation/browser_projection.py`, evitando falso `valid_count`; adicione RED/GREEN para schema inválido com lista vazia; (III) exponha as views de snapshot à tool real `browser_snapshot` e reduza a duplicação de payload sem perder @eN, executando baseline antes/depois. Execute testes focados e documente o que NÃO foi medido em E2E. Somente depois, se houver falhas concretas de DOM drift, proponha reaquisição semântica pré-CDP mantendo fail-closed e readback externo. Não faça merge automático nem afirme release verde sem CI e dogfood reais.

## 12. Conclusão final

**A direção correta é _integração que elimina trabalho e falsos sucessos_, não complexidade adicional.** O erro de priorização anterior foi usar como P0 operacional uma função possivelmente periférica (`browser_save_json`) e considerar como trabalho novo capacidades já parcialmente construídas, enquanto o percurso modelo → schema da tool → controller → verificação → artefato ainda tinha lacunas importantes. O melhor pacote 80/20 atual é: **checkout reproduzível + veredito de schema verdadeiro + views compactas acessíveis com resultado menor no prompt**. A otimização por delta e o self-healing ficam condicionados à medição e aos erros reais.