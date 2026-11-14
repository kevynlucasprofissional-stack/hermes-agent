# Plano de referência — Browser nativo → Kanban Hermes (P1/P2/P3, histórico técnico)

> **Diretriz atual, 13/11/2026:** este plano permanece como evidência e roteiro especializado de Browser/ACK, mas **NÃO é mais o roteiro principal de implementação**. O plano prioritário é [KANBAN_DATABASE_FIRST_IMPLEMENTATION_PLAN_20261113.md](KANBAN_DATABASE_FIRST_IMPLEMENTATION_PLAN_20261113.md). **Database do Workstation é a fonte de verdade dos dados operacionais locais; Kanban Nous organiza somente tarefas/TaskRuns.** Não tornar Kanban autoridade central, não fundir bancos ou reexecutar os prompts antigos por inércia. Integrações Browser/WhatsApp ficam subordinadas à necessidade de seus fluxos específicos; Trello fica fora desta execução.

**Revisão:** 12/11/2026 · Projeto: `C:\Github\hermes-agent` · Branch: `main` · HEAD de referência: `f1d5ab2f03`.

**Objetivo:** o Kanban do Hermes deve funcionar de ponta a ponta: exibir tarefas reais, criar/assumir uma TaskRun, registrar andamento e concluir `DONE` apenas com o resultado efetivo. O Chromium é uma ferramenta do agente, não um produto ou integração a implementar por si só. **Minimizar latência e chamadas, sem confundir ação despachada com alteração persistida.**

**Escopo exclusivo desta sessão (13/11/2026): KANBAN DO HERMES.** Validar interface nativa, backend, banco canônico e fluxo tarefa → execução → conclusão; corrigir somente bloqueios comprovados. **Não executar integração, sincronização, consultas, migração ou testes relacionados ao Trello.** P4/P5 ficam fora da sessão, preservados apenas no histórico e nos prompts futuros.

**Histórico preservado:** [plano original integral, prompts P1–P5 e relatórios de execução](BROWSER_KANBAN_GENERIC_VERIFICATION_PLAN_20261112_HISTORICO.md). **Este arquivo é a versão vigente; o histórico não define mais gates.**

## 1. Situação real — não refazer o que funciona

| Entrega | Estado | Evidência |
| --- | --- | --- |
| P1 — contrato de operação e vínculo causal | **Implementado no código** | `workstation/native_browser_evidence.py` e `workstation/integrations/hermes/tool_observer.py`; owner Electron com `operationAdmissions` |
| P2 — Browser → GET → Kanban `done` | **Aprovado no E2E QA isolado** | Chromium executou `browser_type` + `browser_click`; POST persistiu `revision 0 → 1`; GET novo; `TaskRun done` e `EvidenceRef` verificados em SQLite independente |
| Regressões P1/P2 | **Aprovadas no ensaio realizado** | 104 testes Python combinados, 26 focais posteriores e 27 Electron; conjuntos parcialmente sobrepostos, **não somar como testes únicos** |
| P2 pela entrada real `AIAgent.run_conversation` (processo QA isolado) | **APROVADO** | `%TEMP%\hermes-native-agent-qa-bf608088b7\report.json`: 17,84 s; 4 chamadas ao modelo; Browser Electron 6 ações/leituras; um POST; SQLite independente `done`, `native_browser_external_readback`, 1 EvidenceRef |
| Entrada real do backend já aberto → Trello | **APROVADA para navegação somente leitura** | `%TEMP%\\hermes-p3-gateway-92a0c23753\\report.json`: WS `gateway.ready`, `session.create` + `prompt.submit`, turno terminado em 19,55 s; `browser_navigate` real e aba `trello.com` vinculada à sessão; backend Electron/Python subiu às 17h11 (reinício externo, não executado pela missão) |
| Entrada real do mesmo backend → formulário QA → Kanban DONE | **Não homologada nesse processo** | E2E completo em processo `AIAgent.run_conversation` isolado passou com 1 POST, GET e DONE; backend já aberto não recebeu alteração no escopo de Kanban DB para fixture temporária. Não usar o DB operacional para simular essa prova |
| P3 — ação incerta com efeito ocorrido | **Recuperação de readback implementada/testada em QA; owner pendente** | Ensaio nativo HTTP303 novo: POST=1, ACK confirmado, TaskRun done (defeito intermitente não reproduzido). Teste isolado ACK ausente + GET com ID causal: TaskRun original done sem replay; admissão nativa permanece sem ACK/terminal |
| P4/P5 — integrações externas | **FORA DE ESCOPO** | Não executar nesta sessão; não bloqueiam o Kanban do Hermes |

**Fontes de implementação:** `tools/browser_workstation.py::_dispatch`; `workstation/native_browser_evidence.py`; `workstation/browser_operation_readback.py`; `workstation/integrations/hermes/tool_observer.py`; `workstation/integrations/hermes/completion_admission.py`; `workstation/kanban.py::{finalize_turn_candidate,complete_task_with_report}`; `workstation/contracts.py::{EvidenceRef,BrowserTaskReport,AcceptanceEvaluator}`. Reusar, não duplicar.

**Evidência E2E:** `%TEMP%\hermes-p2-native-459e6d4132\report.json`; banco Kanban QA e SQLite da fixture no mesmo diretório. A execução confirmou **um único POST**, `tasks.status=done`, `latest_run.status=done`, `verifier=native_browser_external_readback` e o hash do artefato. **Não equivale a homologação de qualquer site externo.**

## 2. Contrato mínimo — somente o que justifica seu custo

Uma operação de edição/salvamento precisa de:

1. **Identidade:** `task_id`, `session_id`, `run_id`, `operation_id` e aba vinculados ao owner real. Conferir vínculo uma vez no ingresso e reutilizar; não fazer preflights manuais repetidos por ferramenta.
2. **Execução única:** `browser_type` prepara o campo; `browser_click` realiza o commit. O retorno do Electron já contém snapshot da ação; **não solicitar snapshot adicional apenas por hábito** se a resposta fresca já for suficiente para a observação de UI.
3. **Uma prova proporcional ao efeito:** para afirmar *persistência externa*, executar uma leitura nova, autenticada e read-only (por exemplo, `GET /api/item`), comparando recurso, campos esperados e revisão. O SQLite independente é verificação **do teste QA**, não etapa obrigatória para todo site.
4. **Conclusão canônica:** `finalize_turn_candidate` fornece `EvidenceRef`/`verifier_results` para uma única avaliação do `AcceptanceEvaluator`, e `complete_task_with_report` registra `done` somente quando o contrato exigido estiver satisfeito.

**Classificação objetiva:**
- `OWNER_ACK`: a ação foi aceita/despachada; **não prova salvamento**.
- `UI_OBSERVED`: o DOM exibe o resultado; pode bastar para uma tarefa cujo objetivo é apenas interagir/visualizar a UI, **não** para garantir persistência.
- `EXTERNALLY_PERSISTED`: readback confiável confirma o estado esperado; pode concluir uma tarefa cujo aceite exige salvamento.
- `UNCERTAIN`: efeito pode ter ocorrido, mas faltou prova; não presumir falha nem reenviar.

**Apenas três proteções são inegociáveis para commits:** destino/TaskRun corretos, correspondência do resultado esperado e ausência de duplicação quando o resultado é incerto. Reaproveitar os verificadores especializados existentes de `write_file`, Trello e WhatsApp. Não acrescentar aprovação humana, etapa de compilação, checkpoint ou serviço só porque é possível implementá-lo.

**Não fazer:** criar outro Browser, outro Kanban, outro `AcceptanceEvaluator`, outro pipeline de receipt, validação dupla do mesmo GET, recálculo de identidade a cada chamada, testes combinatórios sem defeito correspondente ou promover `done` só com screenshot/ACK.

## 3. Próxima entrega — tornar P1/P2 utilizáveis no Hermes

**Meta:** uma TaskRun operacional autorizada alcança o mesmo resultado do E2E QA, sem scripts improvisados nem nova arquitetura. Não alterar serviços externos para provar um fluxo que já foi homologado localmente.

**Execução curta:**
1. Conferir o estado **atual** do checkout compartilhado (`git status` e diff só nos arquivos afetados), o processo Hermes e o código efetivamente carregado. Não presumir que modificações no disco já estão em memória.
2. Exercitar pela entrada real do agente uma TaskRun **QA isolada** já existente ou criada no banco QA; usar o Chromium Electron e o verificador P2 existente. Se houver necessidade real de recarga, relatar a dependência; **não reiniciar sem autorização**.
3. Medir tempo total e **quantidade real de chamadas**. Remover somente chamadas repetidas identificadas, especialmente snapshots extras após respostas nativas que já carregam estado fresco; manter a leitura independente após commit.
4. Encerrar assim que o fluxo real persistir `title/revision`, registrar o verificador e concluir `TaskRun done`. Um desvio de campo/revisão deve impedir `done`.

**Aceite:** uma execução real pelo Hermes (não só executor Python de QA), um salvamento confirmado por GET, um `done` canônico, uma negativa sem `done` e nenhuma repetição de commit. **Não repetir as 104 regressões históricas por padrão**: rodar testes focais dos arquivos modificados e a regressão diretamente afetada. Testes Electron somente se o owner mudar.

**Nota:** o cenário acima é a **próxima validação operacional**. A aprovação anterior de P2 em fixture não deve ser reexecutada por inércia.

## 4. P3 reduzido — recuperar apenas o erro incerto comprovado

**Correção focal 12/11 (QA, sem restart):** `tool_observer.py` reconhece também a mensagem de exceção real convertida pelo executor (`Error executing browser_click: browser_input_delivery_unverified`), antes perdida pela comparação literal. `test_browser_kanban_uncertain_reconciliation.py`: **16 PASS**, incluindo POST HTTP303 real em fixture isolada, ACK perdido injetado, GET causal, `TaskRun DONE` canônico apenas com ID/campos/revision corretos; divergência retorna `uncertain` sem `DONE`, POST=1 e nenhuma segunda chamada `browser_click`. A admissão histórica `op_browser_click_c9d400355d0d` permanece sem ACK, TaskRun original `running` e seu servidor QA anterior não está ativo; **não foi reexecutada nem conciliada**. Reconciliação de falha espontânea no Electron e recarga do backend ativo não homologadas.

**Atualização de implementação 12/11/2026 — PARCIAL, sem release:** `workstation/browser_operation_readback.py` aceita, com `BrowserReadbackContract` confiável, um `browser_click` falho `browser_input_delivery_unverified` apenas quando (a) a admissão original está pendente no owner da mesma task/session/run/tab, (b) o `browser_type` anterior possui observação válida, (c) GET novo traz ID externo de operação previamente fixado pelo host, recurso, campos e revisão exatos. `bind_trusted_browser_expectation` localiza a única admissão pendente; `tool_observer.py` distingue o erro sem inventar ACK. EvidenceRef/verificador canônico pode concluir a TaskRun original. **A admissão do Electron continua pendente, sem confirmação local forjada**: o owner não foi modificado e a liberação de sua fence não está homologada; outros runs permanecem isolados. Sem ID externo confiável, não promover done. Ver testes `workstation/tests/test_browser_kanban_uncertain_reconciliation.py`. O ensaio nativo one-shot `workstation/scripts/browser_kanban_native_p3_once.py` criou QA isolado em `%TEMP%\\hermes-p3-native-0dde25e904` e **não reproduziu** perda de ACK: POST=1, revision 0→1, click acknowledged, task done. Não repetir esse clique.

**Defeito real:** `POST /save` executou e persistiu, mas a troca de documento por HTTP 303 impediu confirmação de entrega do clique. O owner registrou uma tentativa sem ACK; o Kanban QA permaneceu `running`. **Não repetir a ação original.**

**Correção mínima:**
1. Reusar `operationAdmissions`, o `operation_id` original, `workstation/evidence_recovery.py` e a leitura P2. Verificar primeiro se o caso ainda é recuperável pelo mesmo contrato/autorização.
2. Após timeout/ACK perdido, **somente leitura** do recurso e revisão esperados. Se a fonte comprovar o efeito com vínculo causal suficiente, conciliar o `TaskRun` original pelo gate canônico. Se não comprovar, registrar `UNCERTAIN` com motivo e **parar**.
3. Criar subtarefa de recuperação apenas quando a infraestrutura existente realmente exigir; não introduzir novo daemon, scheduler, máquina de estados paralela nem replay automático.
4. Reproduzir isoladamente a falha de transporte **uma vez** na fixture e confirmar: contador de POST=1, nenhum segundo clique, resultado divergente sem `done`. Concluir o pai somente com evidência adequada; não fabricar ACK retroativo.

**Aceite P3:** uma operação com resposta perdida não vira segundo envio; leitura autorizada resolve o que for verificável; o restante continua `UNCERTAIN`. O erro do HTTP 303 é a prioridade concreta. Casos hipotéticos de recuperação não bloqueiam a utilização do caminho normal P2.

## 5. Fora do escopo desta sessao

P4/P5 e integracoes externas ficam adiados. O historico preserva as propostas, mas nao sao requisitos para o funcionamento do Kanban do Hermes. Nenhuma atividade externa nesta sessao.

## 6. Forma de execução, testes e encerramento

- **Velocidade:** preferir uma chamada bem definida ao Browser, uma verificação proporcional e um registro canônico. Não gastar tempo com relatórios, snapshots, consultas SQL ou gates que repetem o mesmo fato.
- **Checkout compartilhado:** preservar mudanças alheias; sem `reset`, `clean`, `stash`, `commit`, `push`, troca de branch ou restart automático. Conferir diff do arquivo antes de editar; não tocar em bases operacionais durante QA.
- **Evidência suficiente:** testes dos módulos tocados + um teste do fluxo principal proporcional ao risco. `pytest PASS`, build e mock não substituem Chromium real quando a missão é E2E.
- **Custos:** ao identificar lentidão, contar chamadas Electron/tempo por etapa; só então decidir eliminar chamadas, não inventar mecanismos de cache/retry.
- **Encerrar sem burocracia:** reportar em poucas linhas arquivos alterados, o que efetivamente funcionou, testes contados, o que permanece incerto e próxima pendência **bloqueante**. Não abrir uma nova fase se o objetivo já estiver satisfeito.

**Prioridade atual desta sessão:** (1) Kanban visível e funcional na interface nativa, com dados do banco correto; (2) TaskRun real com `DONE` persistido e verificado no backend ativo; (3) recuperação mínima de ACK incerto apenas se bloquear esse fluxo. **Nenhuma atividade com Trello.**

**Resumo decisivo:** não exigir certeza absoluta para toda interação. Exigir a evidência **necessária para a afirmação realizada**: visualização para observação, readback independente para salvamento, não-replay quando uma mutação possivelmente ocorreu.


---

## 7. Prompts prontos para copiar e enviar ao ChatGPT

**Escopo atual:** usar somente os Prompts 1 e 2; os Prompts 3 e 4 ficam arquivados para uma sessao futura.

**Como usar:** copie **somente o bloco de texto** da missão desejada e envie em uma nova mensagem. **Comece pelo Prompt 1.** Os prompts são autossuficientes: nenhum depende de o ChatGPT se lembrar desta conversa. P4 é independente de P3; P5 depende de P4.

### Prompt 1 — Colocar P2 para funcionar no Hermes operacional (PRÓXIMO)

```text
MISSÃO: Fazer o fluxo Browser nativo → resultado persistido → Kanban DONE funcionar pela entrada real do Hermes Work.

Repositório: C:\Github\hermes-agent
Plano vigente: workstation\context\BROWSER_KANBAN_GENERIC_VERIFICATION_PLAN_20261112.md
Histórico de provas: workstation\context\BROWSER_KANBAN_GENERIC_VERIFICATION_PLAN_20261112_HISTORICO.md
Acesse meu Windows pelo Remote Desktop Commander.

CONTEXTO: P1/P2 já foram implementados e aprovados em E2E QA isolado. O Chromium Electron executou browser_type + browser_click, o POST alterou revision 0→1, o GET confirmou e a TaskRun QA ficou DONE. Evidência histórica em %TEMP%\hermes-p2-native-459e6d4132\report.json. O problema agora é a disponibilidade pela entrada normal do agente, não reconstruir o verificador. O código do disco pode ainda não estar carregado no processo Hermes ativo.

EXECUTE:
1. Inspecione o estado real do checkout compartilhado, do Hermes ativo e do caminho de execução do agente. Reuse browser_operation_readback.py, native_browser_evidence.py, tool_observer.py, completion_admission.py e kanban.py. Não crie outro executor, banco, navegador ou AcceptanceEvaluator.
2. Com o menor patch necessário, conecte o contrato/readback já existente ao fluxo normal de uma TaskRun QA. Não aceite contrato arbitrário do texto do modelo. Se já estiver conectado, não altere nada.
3. Execute UMA tarefa QA isolada pelo fluxo normal do Hermes, usando o Chromium Electron, com edição, salvamento e readback autorizado. Confirme que TaskRun e verificador ficam persistidos no Kanban. Teste um caso negativo em que não pode dar DONE.
4. Conte chamadas ao Electron e tempo do fluxo. Elimine apenas leituras ou snapshots realmente redundantes. Se exigir recarga/restart de processo ativo, NÃO faça sem minha autorização; registre essa dependência objetiva e valide tudo que for possível sem reiniciar.

ACEITE: fluxo real do agente, não só script Python/mocks, produz um commit e readback válido, conclui TaskRun DONE, rejeita resultado divergente e não repete mutação incerta. Testes focais proporcionais aos arquivos tocados.

REGRAS: MVP Quality First; velocidade, precisão, economia. Preserve dados e checkout dirty. Sem reset/clean/stash/commit/push, sem CDP/Playwright externo, sem WhatsApp/Trello reais, sem documentação extensa ou gates novos. Resolva autonomamente o que estiver autorizado e encerre com alterações, prova real, tempo/chamadas e bloqueio restante, se existir.
```

### Prompt 2 — Corrigir P3: salvamento ocorreu, mas o ACK se perdeu

```text
MISSÃO: Corrigir de forma mínima o defeito real de reconciliação no Browser nativo do Hermes.

Repositório: C:\Github\hermes-agent
Leia o plano vigente em workstation\context\BROWSER_KANBAN_GENERIC_VERIFICATION_PLAN_20261112.md e, apenas para evidências históricas, o arquivo correspondente com sufixo _HISTORICO.md. Acesse meu Windows via Remote Desktop Commander.

DEFEITO COMPROVADO: em QA, um browser_click realizou um único POST e persistiu revision=1, mas o HTTP 303 substituiu o documento e o Chromium retornou browser_input_delivery_unverified. O Kanban não concluiu a tarefa; NÃO houve segunda tentativa. O fluxo P2 normal já passou em outro ensaio. Quero recuperar somente o estado incerto com leitura, sem reexecutar a mutação.

EXECUTE:
1. Inspecione a admissão original em operationAdmissions, os recibos e workstation/evidence_recovery.py. Escolha o menor ponto de integração com a verificação/readback P2 já existente.
2. Para um clique com ACK perdido, faça readback autorizado do recurso e do resultado esperado, mantendo operation_id/task/run originais. Conclua pelo AcceptanceEvaluator canônico apenas se o vínculo causal e o valor persistido forem suficientes; caso contrário, marque UNCERTAIN com motivo objetivo.
3. Reproduza a perda de resposta em fixture QA isolada e valide contador de POST=1, zero segundo clique e resultado divergente sem DONE. Não introduza outro scheduler, daemon, pipeline de evidência nem retry de operações mutantes.

ACEITE: efeito já realizado pode ser reconhecido por leitura confiável; nenhuma repetição de POST/click; caso sem evidência fica UNCERTAIN. Registre apenas testes focais e o comportamento observado.

Preserve checkout dirty, bancos operacionais e processos existentes. Sem reset/stash/clean/commit/push/restart automático, sem ações em WhatsApp/Trello real. Não reabra P1/P2 nem amplie o escopo para hipóteses remotas. Execute em vez de criar novos gates.
```

### [ARQUIVADO / FORA DE ESCOPO] Prompt 3 — P4: sincronização mínima Trello ↔ Kanban (INDEPENDENTE)

```text
MISSÃO: Implementar o menor MVP de sincronização bidirecional de TÍTULO entre um cartão Trello QA autorizado e um registro correspondente do Kanban canônico do Hermes.

Repositório: C:\Github\hermes-agent
Plano vigente: workstation\context\BROWSER_KANBAN_GENERIC_VERIFICATION_PLAN_20261112.md
Acesse Windows via Remote Desktop Commander e use o conector Trello existente se necessário.

EXECUTE:
1. Inspecione o schema real de hermes_cli/kanban_db.py, hermes_cli/hybrid_kanban.py e os consumers; escolha AgentTask ou hybrid_card como entidade mapeada, sem confundir com workstation-board ou Database visual.
2. Reuse workstation/trello_sync_reconcile.py, trello_sync_push.py, trello_sync_api.py, external_readback.py e o mapeamento que já existir. Não reimporte cartões históricos nem crie segundo sincronizador.
3. Com UM cartão QA explicitamente autorizado e um registro Hermes isolado, vincule IDs estáveis e sincronize o título uma vez em cada direção. Preserve o último valor comum; quando ambos mudarem de forma divergente, registre conflito sem sobrescrever.
4. Teste reprocessamento sem duplicação, conflito bilateral e os dois sentidos reais. Se não existir cartão QA autorizado/acesso funcional, implemente só a parte local verificável, relate exatamente o bloqueio e NÃO altere quadros produtivos.

ACEITE: um vínculo estável, duas atualizações confirmadas por leitura, um conflito preservado e zero duplicações. Sem comentários, anexos, checklists, arquivamento ou cron nesta missão.

Priorize código mínimo e testes focais; preserve checkout e dados existentes. Sem reset/stash/clean/commit/push/restart. Não transforme este trabalho em gate do Browser→Kanban, que já tem E2E QA aprovado.
```

### [ARQUIVADO / FORA DE ESCOPO] Prompt 4 — P5: ampliar uma família de campos Trello (OPCIONAL)

```text
MISSÃO: Expandir de forma incremental a sincronização Trello ↔ Kanban do Hermes, mas SOMENTE se o MVP bidirecional de título (P4) já estiver funcionando.

Repositório: C:\Github\hermes-agent
Plano vigente: workstation\context\BROWSER_KANBAN_GENERIC_VERIFICATION_PLAN_20261112.md
Acesse meu Windows pelo Remote Desktop Commander e consulte o Trello conectado quando necessário.

EXECUTE:
1. Primeiro confirme se P4 está funcional de verdade. Se não estiver, não implemente P5; reporte a pendência objetiva.
2. Escolha a PRIMEIRA família de campos mais útil e viável, começando por descrição, status ou prazo. Reuse o vínculo estável, baseline, CAS/conflitos e adaptadores Trello já existentes. Não implemente todas as famílias.
3. Prove uma atualização em cada sentido no QA autorizado e um conflito sem perda de valor; mantenha idempotência. Não trate histórico, comentários, anexos, exclusões ou arquivamento como entregues sem operação real.
4. Encerre ao concluir a família escolhida. Nenhuma migração ampla, reimportação de cartões, cron ou refatoração especulativa.

ACEITE: apenas a família escolhida sincronizada nos dois sentidos, conflito preservado e nenhum registro duplicado. Testes focais proporcionais ao risco; informe exatamente o que foi feito, comprovado e adiado.

Preserve checkout dirty, dados produtivos e processos existentes. Sem reset/stash/clean/commit/push/restart automático ou operações destrutivas.
```
