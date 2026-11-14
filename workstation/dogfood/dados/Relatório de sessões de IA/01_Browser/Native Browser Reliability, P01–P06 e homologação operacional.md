# Relatório Técnico Integral de Sessão

## Hermes Work — Native Browser Reliability, P01–P06 e homologação operacional

### 0. Identificação e cobertura da sessão

| Campo                             | Identificação                                                                     |
| --------------------------------- | --------------------------------------------------------------------------------- |
| Projeto                           | Hermes Work — Browser nativo persistente                                          |
| Repositório                       | `C:\Github\hermes-agent`                                                          |
| Host                              | `DESKTOP-3NA47UH` — Windows                                                       |
| Branch de trabalho                | `main`                                                                            |
| HEAD de referência                | `f1d5ab2f030e940ed4571371b0de45a21a009c9e`                                        |
| Período reconstruído              | 29/10/2026, aproximadamente 12h até 17h41 BRT, com inspeção complementar às 22h33 |
| Resultado da missão operacional   | MVP homologado para o fluxo efetivamente testado                                  |
| Resultado da homologação integral | Incompleta: AC-01 a AC-24 não foram integralmente satisfeitos                     |

Cobertura e limitações. Foram examinados o histórico de mensagens e operações de ferramentas disponível nesta conversa, os Resume Prompts sucessivos, o relatório canônico `HERMES_NATIVE_BROWSER_RELIABILITY_MASTER.md` e uma inspeção complementar de leitura no Windows. Algumas mensagens intermediárias aparecem compactadas ou omitidas no histórico disponibilizado. O relatório canônico recupera boa parte dessas etapas, mas é documentação produzida durante a própria execução, não evidência independente de cada comando.

Grau de confiança na completude: médio. A sequência principal, as decisões e as entregas estão suficientemente documentadas. Entretanto, não é possível afirmar que todas as tentativas intermediárias, saídas de ferramentas e alterações concorrentes foram recuperadas integralmente.

A inspeção das 22h33 confirmou o mesmo HEAD histórico, 283 entradas dirty, sendo 223 não rastreadas, staging vazio e os principais arquivos de implementação ainda presentes no checkout. O relatório canônico tinha 81.177 bytes e SHA256 `ECD9A8254634D640051A80A3DDC0340F82E18457C0D4623C46B8D39AE3526F1E`.

Critério de evidência utilizado: `VERIFICADO` significa que há uma saída de execução, leitura de código ou artefato concreto que sustenta a conclusão delimitada. Não significa ausência de outros defeitos. `REPORTADO`, `PARCIAL`, `FALHOU`, `PENDENTE` e `INDETERMINADO` seguem as definições solicitadas.

A inspeção complementar foi estritamente de leitura. Não houve implementação, alteração do repositório, commit ou reinicialização do Hermes durante esta auditoria.

### 1. Sumário executivo

1. A missão começou como uma homologação extensa de confiabilidade do Browser nativo, incluindo foco independente, persistência, isolamento entre BrowserTasks, reconciliação segura, crash/restart e integração com TaskRun/Kanban.
    
2. A primeira investigação identificou falhas de segurança e integridade: reconciliação autodeclarada pelo agente, admissões `unbound`, restauração implícita de navegação e recuperação incompleta do cliente.
    
3. As fases P02–P03 implementaram bloqueios e testes de segurança, além de um caminho restrito de revisão humana para navegações sintéticas.
    
4. Em P03 surgiu um defeito crítico: o controlador produzia recibo de clique apesar de o evento não chegar ao DOM. P04 corrigiu o despacho mediante emulação de foco interna ao WebContents e verificação de evento confiável.
    
5. P05 solucionou a operação com a janela humana minimizada usando um host de composição auxiliar; P06 corrigiu perda de host, fechamento de janela e parte da recuperação multiprocesso.
    
6. As regressões chegaram a 136/136 testes Electron e 67 testes Python + 14 subtestes; os typechecks principais passaram. O build de distribuição, porém, falhou com `EPERM`, e o projeto E2E TypeScript ainda apresentava erros.
    
7. A mudança decisiva de estratégia foi priorizar o uso real: após reinício do Hermes, uma BrowserTask do próprio agente executou navegação, clique, digitação, Enter, scroll e snapshots, confirmados por um servidor local independente.
    
8. O Hermes também abriu o WhatsApp Web em modo somente leitura. Isso fundamenta a declaração de MVP operacional homologado no escopo testado, mas não a conclusão de todos os requisitos de engenharia.
    
9. Continuam relevantes os riscos de crash após despacho, batch parcialmente executado, reconciliação de efeitos externos, concorrência humana durante input e qualificação de release.
    
10. Próxima prioridade recomendada: preservar o MVP funcional, obter uma baseline Git recuperável mediante autorização e corrigir apenas falhas reproduzidas que afetem o uso real ou a segurança.
    

### 2. Objetivos, requisitos e evolução do escopo

#### 2.1 Objetivo original

O usuário pretendia que cada sessão Hermes controlasse suas BrowserTasks persistentemente, inclusive com a janela oculta ou minimizada, sem disputar os dispositivos de entrada do Windows.

O fluxo exigido era:

```
Sessão Hermes
  → Hermes Agent
  → Browser Tool
  → Controller HTTP autenticado
  → BrowserTask
  → WebContents / Chromium
  → Readback
  → Receipt e admission
  → TaskRun / Kanban
```

Os requisitos funcionais abrangiam navegação, snapshot, clique, digitação, teclas, scroll, múltiplas sessões e abas, recuperação de controlador e reabertura, ownership determinístico e arbitragem entre humano e agente.

Os requisitos não funcionais incluíam persistência durável, idempotência, ausência de falsos recibos, comportamento fail-closed, isolamento de perfis de teste, preservação do estado produtivo e prevenção de repetição de operações com resultado incerto.

#### 2.2 Restrições obrigatórias

Permaneceram explícitas durante a engenharia:

- Nunca controlar mouse, teclado ou foco global do Windows por automação do sistema operacional.
    
- Usar AI Control autenticado e CDP interno ao WebContents, não CDP externo.
    
- Não enviar mensagens WhatsApp reais durante a homologação.
    
- Não utilizar Windows Agent 01 enquanto indisponível.
    
- Não executar o coordenador multiagente aposentado.
    
- Não apagar, reconciliar, reexecutar ou liberar o incidente histórico protegido.
    
- Não usar `git reset`, `stash`, `clean`, nem criar branches, worktrees, commits ou pushes sem autorização.
    
- Não sobrescrever o trabalho de agentes concorrentes.
    
- Não inferir conclusão de uma tarefa apenas porque uma ferramenta retornou sucesso.
    

O incidente protegido era:

```
Sessão:
20261028_112711_256509

Operação:
op_browser_batch_actions_3d591fa7f8da
```

A dispensa do Stage A foi concedida pelo usuário para as implementações realizadas em 29/10/2026. Não equivalia a uma autorização permanente ou a uma dispensa de testes, CI ou release.

#### 2.3 Evolução da missão

|Etapa|Escopo dominante|Natureza da decisão|
|---|---|---|
|Planejamento inicial|Reliability Master e 24 critérios de aceite|Proposta técnica|
|P02|Reconciliação, identidade, restauração e cliente read-only|Implementação de segurança|
|P03|Revisão humana causal e E2E do executor|Implementação e investigação|
|P04|Entrega correta de clique sem foco global|Correção funcional crítica|
|P05|Browser com janela minimizada|Correção arquitetural|
|P06|Lifecycle, crash multiprocesso e gates de compilação|Robustez e validação|
|P07 original|Crash transacional, leases e release completo|Planejamento não executado|
|Missão 80/20|Ativar e usar o Browser no próprio Hermes|Redirecionamento solicitado pelo usuário|
|Homologação final|Página local, background e WhatsApp read-only|Validação operacional real|

O usuário questionou expressamente o custo-benefício da sequência de testes e exigiu simplicidade, funcionamento prático e foco nos problemas certos. A recomendação do assistente de substituir temporariamente P07 por uma missão de ativação foi aceita e transformada em uma nova instrução.

P07 original foi substituído como prioridade imediata, não concluído. Seus requisitos de confiabilidade e release continuam existindo como trabalho futuro, mas deixaram de ser pré-requisitos para considerar o MVP utilizável.

### 3. Linha do tempo técnica da sessão

As datas e horários abaixo são os registrados nos relatórios e saídas disponíveis, não uma reconstrução de relógio independente para cada operação.

#### Fase 0 — Antecedentes e estabelecimento do Reliability Master

Contexto: havia problemas anteriores no Browser nativo, incluindo foco, restauração, controlador e operações pendentes. O trabalho de 28/10 forneceu um baseline; parte dele pertence a sessões anteriores e não deve ser atribuída automaticamente à execução de 29/10.

Foram elaborados um prompt-mestre de engenharia e sucessivos contratos de continuidade. O arquivo canônico estabelecido foi:

`workstation/context/HERMES_NATIVE_BROWSER_RELIABILITY_MASTER.md`

A matriz AC-01 a AC-24 passou a orientar a comprovação de resultados, diferenciando testes sintéticos, E2E Chromium, dogfooding do Hermes e release.

Resultado: planejamento e rastreabilidade estabelecidos. A origem exata de cada implementação anterior à primeira continuidade de 29/10 não está totalmente visível.

#### Fase 1 — Preflight inicial, Stage A e descoberta dos REDs

Período: início das atividades de 29/10, antes da primeira janela de implementação P02.

O primeiro preflight registrou `main` no HEAD de referência, aproximadamente 230–231 entradas dirty, staging vazio e muitos arquivos de engenharia já modificados.

Inicialmente, o AI Control estava indisponível e um descritor Browser apontava para um PID morto (`28720`). Também não havia instância Electron identificada para o E2E produtivo. Por isso, a primeira execução limitou-se a diagnóstico e testes isolados.

Foram reproduzidos três defeitos importantes:

1. Restauração P02: um `browser_snapshot` podia carregar a URL anterior apesar de existir batch incerto.
    
2. Reconciliação forjada: `browser_admissions_reconcile` aceitava metadados equivalentes a `OPERATOR_REVIEW` emitidos pelo próprio agente e gravava um terminal `RECONCILED`.
    
3. Identidade insuficiente: uma navegação sem identidade apropriada podia criar admission com `runId=unbound`.
    

Também passaram 20 ciclos sintéticos de recuperação do controlador, divididos entre descritores obsoletos e listeners encerrados. O resultado foi 20/20, com p95 de aproximadamente 1,099 segundo.

Estado final: defeitos reproduzidos, mas inicialmente não corrigidos, por ausência de dispensa Stage A válida para 29/10.

#### Fase 2 — P02: correções de segurança e recuperação

Após a autorização específica do usuário para dispensar Stage A naquele dia, foram aplicadas correções em:

- `workstation-browser-runtime.ts`;
    
- `workstation-browser-runtime-admission.test.ts`;
    
- `workstation-browser-runtime-recovery.test.ts`;
    
- `tools/browser_workstation.py`;
    
- `test_browser_controller_readonly_recovery.py`.
    

As mudanças principais foram:

- Recusa de `browser_admissions_reconcile` originado pelo agente com `agent_reconciliation_forbidden`.
    
- Remoção dessa capacidade do catálogo Python exposto à LLM.
    
- Bloqueio de novas mutações sem identidade mínima.
    
- Ampliação de `shouldDeferRestoredNavigation()` para considerar operações incertas da mesma BrowserTask/aba.
    
- Um retry limitado do cliente para `GET /health` e `GET /resources` após falha de conexão e alteração autenticada do descritor; nenhum retry de POST mutante.
    

A suíte de regressão evoluiu para 115/115 Electron e depois 67 Python + 14 subtestes. O bundle de desenvolvimento foi compilado.

O usuário também abriu o Hermes e ativou AI Control. O controlador voltou a responder, mas o processo aberto ainda não tinha sido reiniciado após a compilação.

Estado final: correções implementadas e regressões direcionadas aprovadas; homologação real ainda pendente.

#### Fase 3 — P03-A: revisão humana restrita

Período registrado: aproximadamente 13h14–13h59.

A investigação demonstrou que o handoff humano já existente apenas registrava revisão e exigia readback. Ele não fornecia uma autorização causal válida para reconciliar operações incertas.

Foi criado `workstation-browser-human-review.ts` e integrado ao runtime, IPC, preload, tipos e painel Browser.

O mecanismo positivo foi limitado a navegações sintéticas locais que possuíssem evidência verificável. Exigia correspondência de task, sessão, run, aba, receipt e WebContents, além de confirmação nativa do Electron.

Não autorizava reconciliação de cliques, batches, envios ou efeitos externos desconhecidos.

Foram executados testes de identificação, aprovação e uso único. Um teste nativo independente de Chromium oculto também passou em clique, digitação, Enter e scroll, mas ainda não exercitava o WorkstationBrowserRuntime completo.

Estado final: revisão humana local restrita implementada; AC-12 geral ainda aberto.

#### Fase 4 — P03-B: segurança transacional e primeiro E2E do runtime

Período registrado: aproximadamente 14h08–14h51.

A revisão humana recebeu proteção adicional contra:

- Lease humana ativa.
    
- Tab com estado de recuperação obsoleto.
    
- Alteração de `taskRevision`.
    
- Concorrência entre dois escritores.
    
- Falhas de `fsync` antes e depois da publicação do terminal.
    

Foi identificado um problema de durabilidade: a implementação podia publicar `RECONCILED` por rename e falhar em `fsync` posteriormente, criando divergência entre resposta e estado persistido. O fluxo foi alterado para sincronizar o arquivo temporário antes da publicação.

Os testes passaram, chegando a 117/117 Electron.

Em seguida surgiu o primeiro problema crítico do executor real. O E2E com duas BrowserTasks e duas sessões comprovou navegação, snapshot e digitação, mas o clique em WebContentsView retornava recibo sem alterar `window.count`.

Resultado RED: `browser_click` aparentemente bem-sucedido, porém `window.count=0`.

Isso demonstrou que ACK do CDP e receipt não bastavam para afirmar entrega de clique ao DOM.

#### Fase 5 — P03-C: hipóteses descartadas e mitigação do recibo falso

Período registrado: aproximadamente 14h54–15h03.

A alternativa `webContents.sendInputEvent()` foi testada e também falhou:

`NATIVE_SENDINPUT_READBACK={"count":0,"focused":false}`

Não havia evidência de que trocar a API de despacho resolveria o problema.

Foi implementado em `clickRef()` um observador temporário que exigia um evento `click` confiável (`isTrusted`) no elemento correto.

Quando a prova faltava, o runtime retornava:

`browser_input_delivery_unverified`

A admission permanecia incerta, sem recibo de sucesso e sem repetição automática.

Essa mudança corrigiu o falso positivo, mas ainda não fez o clique funcionar. O E2E continuava RED corretamente.

#### Fase 6 — P04: correção do clique sem foco

Período registrado: aproximadamente 15h14–15h32.

Uma variante experimental ativou:

`Emulation.setFocusEmulationEnabled`

no debugger interno do próprio WebContents.

O clique passou, com `window.count=1`, enquanto o BrowserWindow hospedeiro permanecia sem foco. A alternativa de apenas habilitar renderização offscreen, sem emulação de foco, continuou RED.

A correção foi integrada em `cdpClick()`:

- Ativar emulação de foco para o WebContents.
    
- Despachar evento de ponteiro.
    
- Confirmar a entrega local.
    
- Desativar a emulação no `finally`.
    
- Falhar fechado se a limpeza da emulação não puder ser confirmada.
    

E2Es nativos passaram para tarefa visível, tarefa `parked`, clique, digitação, Enter e scroll.

Porém, minimizar a janela ainda produzia `target_outside_viewport`.

Estado final: clique em segundo plano corrigido; janela minimizada continuava problemática.

#### Fase 7 — P05: compositor persistente para janelas minimizadas

Período registrado: aproximadamente 15h36–16h16.

O defeito era diferente do P04. Ao minimizar a janela humana, `getContentBounds()` podia chegar a `0×0`, reduzindo a superfície efetiva da WebContentsView a aproximadamente `1×1`.

Foi criado:

`apps/desktop/electron/workstation-browser-minimized-compositor.ts`

O novo compositor transferia a mesma WebContentsView para um BrowserWindow auxiliar não minimizado, não focável e fora da área usual de exibição.

A implementação precisou resolver problemas intermediários de mapeamento entre tarefas, views e hosts, além de impedir que `setBounds()` gravasse novamente geometria inválida.

Os E2Es nativos passaram para minimização inicial, minimização durante a execução, restauração, leases humanas, atualização de bounds e ações de Browser. O watchdog também recuperou um listener HTTP encerrado sem duplicar o clique.

Estado final: BrowserTask operacional em cenário minimizado isolado; crash completo, concorrência e produção ainda pendentes.

#### Fase 8 — P06: lifecycle, reinício multiprocesso e compilação

Período registrado: aproximadamente 16h35–17h05.

Dois defeitos adicionais de lifecycle foram reproduzidos:

- Destruir o host auxiliar deixava o compositor apontando para um host morto.
    
- Fechar uma janela humana enquanto outra permanecia aberta eliminava o host de uma BrowserTask ainda viva.
    

As correções passaram a recuperar o host quando possível e a preservar temporariamente a view em um host independente quando sua janela original fosse fechada.

Os E2Es confirmaram recuperação do host, fechamento, reattach e quatro ciclos adicionais de minimizar/restaurar.

Outro teste utilizou dois processos Electron com o mesmo ledger temporário. O primeiro persistiu uma admission de batch incerta e encerrou abruptamente. O segundo recuperou a identidade e preservou o bloqueio:

`prior_operation_requires_reconciliation`

Não houve replay ou ACK inventado. Entretanto, o teste não simulou uma queda depois de um efeito real ter sido despachado.

Também foram eliminados seis erros de TypeScript, e a regressão alcançou 136/136 Electron.

Dois gates continuaram falhando: o typecheck E2E (`TS6307` e erros de fixtures) e o build de distribuição (`EPERM` em `build/native-deps`).

Estado final: robustez significativamente ampliada, ainda sem release homologado.

#### Fase 9 — Revisão de estratégia: mentalidade 80/20

Após constatar que o trabalho se estendia por muitas horas, o usuário questionou a proporcionalidade entre os testes e o resultado utilizável.

A decisão foi substituir temporariamente o P07 original por quatro objetivos imediatos:

1. Carregar o bundle corrigido no Hermes real.
    
2. Fazer o próprio agente usar uma BrowserTask.
    
3. Confirmar funcionamento em segundo plano/minimizado.
    
4. Abrir WhatsApp Web em modo somente leitura.
    

O usuário deixou claro que precisava usar a solução imediatamente, sem abandonar os mecanismos essenciais de segurança.

Estado final: prioridade redefinida de homologação exaustiva para MVP operacional verificável.

#### Fase 10 — Diagnóstico de bundle desatualizado

Período registrado: aproximadamente 17h17–17h22.

O processo Electron PID `9896` havia sido iniciado às 12h33, enquanto o bundle `dist/electron-main.mjs` tinha sido recompilado às 17h01.

Não havia comprovação de hot reload do processo principal. Logo, os novos testes no código-fonte não garantiam que a instância do operador executasse as correções.

O assistente não reiniciou a aplicação porque a autorização operacional ainda não existia naquele mandato.

Estado final: principal bloqueador operacional identificado, sem alteração do runtime.

#### Fase 11 — Reinício autorizado, atalho e E2E do agente Hermes

Período registrado: aproximadamente 17h30–17h41.

O usuário informou que reiniciou o Hermes por `npm run dev`, ativou AI Control e autorizou novos reinícios no dia 29/10 caso fossem necessários.

A inspeção identificou o novo processo Electron PID `35536` e bundle compilado imediatamente antes de sua inicialização.

Também confirmou o atalho existente:

`C:\Users\Kevyn Lucas\Desktop\Hermes Work.lnk`

Seu destino era PowerShell com `workstation\scripts\fast_reopen.ps1`. O modo de inicialização fria conduzia ao bootstrap e finalmente a `npm run dev`. O atalho já atendia ao requisito de abertura por dois cliques e não foi modificado.

Foi criada uma sessão Hermes intitulada “Teste operacional Browser NATIVO Hermes”.

O agente executou as ações em uma página sintética local:

`http://127.0.0.1:18653/`

O servidor independente confirmou:

|Verificação|Primeira rodada|Rodada em segundo plano|
|---|---|---|
|Carregamentos da página|1|1|
|Cliques acumulados|1|2|
|Valor digitado|`mvp-20261029`|`bg-20261029`|
|Enter acumulados|1|2|
|Scroll acumulado|1|2|
|Posição final de scroll|≈ 533 px|0 px|

O agente manteve a BrowserTask `20261029_173604_b7383a` e a aba `ab6d2ca2-507a-4516-bf07-69a81bff080e`.

Durante parte da segunda rodada, o renderer foi observado como oculto e sem foco. Em outra observação, apareceu novamente focado; a causa dessa mudança não foi determinada.

Por fim, o próprio agente navegou até `https://web.whatsapp.com` e executou snapshot read-only. A página estava carregada e sincronizando uma sessão autenticada. Nenhuma mensagem foi enviada.

O servidor temporário foi encerrado, e o relatório canônico recebeu o registro de homologação.

Estado final: MVP funcional no fluxo testado, com limites explícitos. O trabalho de release e confiabilidade exaustiva não foi encerrado.

### 4. Descobertas técnicas e conhecimento adquirido

#### T-01 — O foco do WebContents não equivale ao foco global do Windows

- Contexto: clique via CDP não chegava ao DOM quando uma WebContentsView estava em segundo plano.
    
- Evidência: E2E P03 com `window.count=0`; probe P04 com `Emulation.setFocusEmulationEnabled` resultando em `window.count=1`, mantendo o host sem foco.
    
- Mecanismo: o despacho de eventos de ponteiro dependia de um estado de foco interno ao alvo Chromium, que podia ser emulado sem atribuir foco ao BrowserWindow do operador.
    
- Consequência: a independência de foco não exigia controle dos periféricos ou foco global.
    
- Aplicabilidade: manter a emulação restrita à operação e ao WebContents, com limpeza no `finally`.
    
- Confiança: confirmado para os cenários nativos ensaiados.
    

#### T-02 — ACK do controlador não comprova entrega ao DOM

- Contexto: o runtime registrava sucesso de clique sem execução de `onclick`.
    
- Evidência: receipt presente e `window.count=0` em E2E nativo.
    
- Mecanismo: a confirmação do despacho pelo CDP era tratada como confirmação de entrega.
    
- Consequência: admissões e recibos podiam representar falsamente uma interação concluída.
    
- Aplicabilidade: separar despacho, entrega de evento e efeito externo. Cada um exige evidência apropriada.
    
- Confiança: confirmado.
    

A prova posterior por evento `click` com `isTrusted` resolve apenas a confirmação de entrega local. Não demonstra, por si só, que um formulário foi processado por um servidor ou que uma mensagem chegou ao destinatário.

#### T-03 — A janela minimizada pode inutilizar a geometria do WebContentsView

- Contexto: P04 passou sem foco, mas falhou minimizado.
    
- Evidência: `target_outside_viewport`, bounds transitórios `0×0` e renderer reduzido a dimensão inadequada.
    
- Mecanismo: o compositor dependia das dimensões da janela humana.
    
- Consequência: manter o renderer ativo não bastava se sua superfície de input fosse inválida.
    
- Aplicabilidade: host de composição não minimizado e geometria independente do estado da janela humana.
    
- Confiança: confirmado no ambiente testado.
    

#### T-04 — Transferir a mesma WebContentsView preserva o contexto Chromium

- Contexto: necessidade de separar executor persistente e apresentação humana.
    
- Evidência: testes de minimização/restauração, host-loss e reattach mantiveram IDs de WebContents e abas.
    
- Mecanismo: a view existente foi reanexada a outro host; não foi criada uma nova sessão de navegador.
    
- Consequência: foi possível manter estado de página e identidade sem duplicar perfil, cookies ou navegação.
    
- Aplicabilidade: qualquer nova mudança de host deve respeitar a propriedade original da view e realizar cleanup.
    
- Confiança: confirmado nos testes isolados.
    

#### T-05 — Ownership da view não pode depender apenas de `ownerWindow` global

- Contexto: uma BrowserTask `parked` foi transferida inadvertidamente para o host de outra tarefa.
    
- Evidência: teste RED de Task A reaparecendo no host B; GREEN após mapeamento de origem por view.
    
- Mecanismo: uma referência global ao host ativo não representava corretamente a propriedade de cada WebContentsView.
    
- Consequência: risco de mistura de interfaces e tarefas entre sessões.
    
- Aplicabilidade: preservar mapeamentos por view (`owningHostFor`, associações WeakMap) e testar isolamento entre tarefas.
    
- Confiança: confirmado no cenário de reparenting.
    

#### T-06 — O ciclo de vida da janela humana não é o ciclo de vida da BrowserTask

- Contexto: destruir um host auxiliar ou fechar uma janela humana eliminava a superfície de uma BrowserTask ainda viva.
    
- Evidência: REDs P06 e testes GREEN após recuperação e reattach.
    
- Mecanismo: o encerramento do host era tratado como encerramento de sua superfície, sem distinguir se o renderer permanecia pertencente ao runtime.
    
- Consequência: BrowserTasks perdiam capacidade de interação sem necessariamente perder estado.
    
- Aplicabilidade: separar destruição de host, troca de apresentação e encerramento definitivo do runtime.
    
- Confiança: confirmado no E2E nativo isolado.
    

#### T-07 — Operação pendente e navegação anterior reconhecida podem coexistir

- Contexto: após restart, snapshot podia carregar uma URL anterior mesmo com um batch posterior incerto.
    
- Evidência: RED em `hermes-p02-restart-integrated-v2.cjs`, seguido de teste integrado GREEN.
    
- Mecanismo: `shouldDeferRestoredNavigation()` considerava inicialmente uma categoria insuficiente de admissões.
    
- Consequência: uma leitura poderia provocar navegação implicitamente, alterando estado antes da reconciliação.
    
- Aplicabilidade: inspeções read-only devem respeitar pendências mutantes da identidade canônica.
    
- Confiança: confirmado.
    

#### T-08 — Recuperação de transporte exige política diferente para GET e POST

- Contexto: falha do controlador fazia consultas read-only retornarem indisponibilidade mesmo quando o descritor havia mudado.
    
- Evidência: testes RED/GREEN de `tools/browser_workstation.py::_request_json()`.
    
- Mecanismo: uma conexão falhada não indica se uma mutação chegou ou não ao destinatário.
    
- Consequência: repetir POST pode duplicar efeitos; repetir GET comprovadamente puro pode ser seguro sob condições definidas.
    
- Aplicabilidade: retry único, autenticado, apenas para `/health` e `/resources` no contrato implementado.
    
- Confiança: confirmado em testes do cliente; integração completa após relisten real ainda pendente.
    

#### T-09 — Metadados de revisão não constituem autorização humana

- Contexto: `OPERATOR_REVIEW` e `resolvedBy=agent` podiam produzir um terminal reconciliado.
    
- Evidência: reprodutor de forja e posterior teste integrado de recusa.
    
- Mecanismo: dados declarados pela ferramenta do agente eram aceitos como se fossem uma decisão autorizada.
    
- Consequência: a LLM podia liberar operações incertas indevidamente.
    
- Aplicabilidade: manter a revisão humana em um canal separado, com identidade, confirmação e persistência controladas.
    
- Confiança: confirmado para a vulnerabilidade inicial e para a recusa implementada.
    

#### T-10 — Persistência reconhecida e persistência durável não são a mesma coisa

- Contexto: o caminho de reconciliação publicava estado antes da confirmação do flush.
    
- Evidência: testes de falha de `fsync` e de dois escritores.
    
- Mecanismo: a ordem entre escrita temporária, sincronização e rename pode produzir discrepâncias entre resultado comunicado e estado observável.
    
- Consequência: um erro reportado ao operador não garantia ausência de terminal publicado.
    
- Aplicabilidade: conservar lock, comparação de estado e sincronização antes da publicação.
    
- Confiança: confirmado nos testes de falha simulada; durabilidade contra perda súbita de energia não comprovada.
    

#### T-11 — O bundle compilado pode ser diferente do código executado

- Contexto: repetidas compilações de desenvolvimento não resolviam o bloqueio operacional.
    
- Evidência: PID `9896` iniciado às 12h33 e bundle atualizado às 17h01.
    
- Mecanismo: o processo principal Electron não havia sido reiniciado para carregar a geração nova.
    
- Consequência: testes no checkout não representavam automaticamente o Hermes aberto.
    
- Aplicabilidade: ao homologar uma mudança no processo principal, comparar versão, processo e bundle efetivamente carregado antes de investigar novamente o código.
    
- Confiança: confirmado como discrepância temporal; a execução byte a byte do bundle não foi atestada criptograficamente.
    

#### T-12 — O atalho existente já executava o fluxo correto

- Contexto: o usuário suspeitava de divergência entre o `.bat` conhecido e o destino do atalho.
    
- Evidência: leitura COM das propriedades de `Hermes Work.lnk`, inspeção dos scripts e execução de `fast_reopen.ps1 -Probe`.
    
- Mecanismo: o atalho chama `fast_reopen.ps1`. Se já existe Electron, sinaliza a instância; se não existe, chama o bootstrap, que chega a `workstation/start.ps1` e `npm run dev`.
    
- Consequência: não era necessário criar um novo atalho para resolver a ativação do Browser.
    
- Confiança: confirmado para a configuração e para o caminho HOT; o caminho COLD foi inspecionado, mas não submetido a uma homologação independente do duplo clique.
    

### 5. Decisões técnicas e arquiteturais

Os identificadores abaixo são exclusivos deste relatório.

|ID|Decisão prevalecente|Justificativa e alternativas documentadas|Estado|
|---|---|---|---|
|D-01|Preservar BrowserTask vinculada à sessão e ao TaskRun|Evitar operações sem identidade e ambiguidade no ledger|Definitiva no desenho atual|
|D-02|Proibir reconciliação pela LLM|A alternativa de confiar em `OPERATOR_REVIEW` foi explorada e demonstrada insegura|Definitiva|
|D-03|Revisão humana positiva somente para navegação sintética comprovada|Não há prova causal suficiente para generalizar a cliques ou efeitos externos|Provisória e restrita|
|D-04|Não repetir mutações com efeito incerto|Retry de POST poderia duplicar operações|Definitiva|
|D-05|Permitir retry limitado para GET puro|Recuperar disponibilidade sem risco conhecido de duplicação mutante|Implementada, ainda parcialmente homologada|
|D-06|Exigir entrega de clique ao DOM antes de receipt|Recibo baseado apenas em dispatch foi falso-positivo|Definitiva para entrega local|
|D-07|Usar emulação de foco no WebContents, não foco do Windows|`sendInputEvent()` e alteração simples de compositor não resolveram o RED|Implementada e validada|
|D-08|Usar host auxiliar para janela minimizada|O viewport humano minimizado produzia geometria inválida|Implementada e validada|
|D-09|Preservar WebContentsView no reparenting|Evita duplicação de sessão/contexto e perda de identidade|Implementada|
|D-10|Distinguir fechamento de janela de encerramento do runtime|Uma BrowserTask pode sobreviver ao host humano|Implementada com limites|
|D-11|Manter o incidente histórico estritamente protegido|Resultado externo desconhecido; reconciliação artificial seria insegura|Definitiva durante a missão|
|D-12|Não executar Stage A em 29/10, com dispensa datada|Autorização explícita do mantenedor para implementar naquele dia|Excepcional e expirada|
|D-13|Não criar commits/branches/pushes automaticamente|Checkout compartilhado, grande WIP e risco de conflitos|Restrição da sessão|
|D-14|Priorizar MVP operacional antes de release exaustivo|O usuário precisava utilizar o produto; o ganho marginal de novos probes havia diminuído|Decisão final de prioridade|
|D-15|Manter o atalho existente|Inspeção demonstrou que já chamava o inicializador apropriado|Definitiva para a configuração observada|

Trade-offs relevantes: D-08 aumenta a complexidade do ciclo de vida de janelas auxiliares; D-03 mantém algumas operações bloqueadas mesmo após revisão humana; D-14 permite uso operacional com débito técnico de release ainda aberto. Esses riscos são conhecidos e não devem ser apagados por uma declaração de MVP.

A opção de usar `webContents.sendInputEvent()` como substituto direto do CDP foi efetivamente investigada e descartada após RED. A alternativa de `element.click()` genérico não foi implementada, pois não demonstraria equivalência com input confiável. A emulação de foco foi a solução escolhida após E2E positivo.

### 6. Inventário de alterações no código, configuração e infraestrutura

A inspeção atual confirma que os arquivos centrais existem. Contudo, o checkout contém WIP anterior e concorrente. Portanto, a presença de uma alteração em Git não prova que toda ela foi introduzida nesta conversa, nem que todas as suas linhas pertencem à missão Browser.

Os grupos abaixo separam as alterações por função.

#### 6.1 Runtime, admissões e execução Chromium

|Arquivo|Operação e comportamento|Validação|
|---|---|---|
|`apps/desktop/electron/workstation-browser-runtime.ts`|Editado. Recusa de reconciliação agent-only, identidade mínima, restauração segura, confirmação de clique, emulação de foco, integração de compositor e correções de nullabilidade|VERIFICADO no checkout; regressões e E2Es aprovados|
|`apps/desktop/electron/workstation-browser-session-state.ts`|Editado. CAS de reconciliação, verificação de revision/lease, proteção transacional e tratamento de durabilidade|VERIFICADO no checkout; testes direcionados aprovados|
|`apps/desktop/electron/workstation-browser-runtime-admission.test.ts`|Testes integrados RED/GREEN para reconciliação, `unbound` e restauração|REPORTADO com evidências registradas|
|`apps/desktop/electron/workstation-browser-runtime-task.test.ts`|Testes de input, foco emulado, recibos e mocks de BrowserWindow|VERIFICADO por resultados de regressão|
|`apps/desktop/electron/workstation-browser-runtime-recovery.test.ts`|Mocks e testes de recuperação do controlador e lifecycle|VERIFICADO por resultados de regressão|
|`apps/desktop/electron/workstation-browser-runtime-batch.test.ts`|Ajustes dos mocks de confirmação de evento e contratos de batch|REPORTADO com regressões aprovadas|

Pontos de integração críticos no runtime, com posições identificadas na inspeção complementar:

```
reviewVerifiedNavigation()             ~1503
relistenClosedControlServer()          ~2751
Recusa agent_reconciliation_forbidden  ~3056
shouldDeferRestoredNavigation()        ~4429
Emulation.setFocusEmulationEnabled     ~4831 / ~4870
browser_input_delivery_unverified      ~4969
```

As posições são referências aproximadas do checkout consultado, não números de linha imutáveis.

#### 6.2 Reconciliação humana e UI

|Arquivos|Alteração|
|---|---|
|`electron/workstation-browser-human-review.ts`|Criado. Elegibilidade e prova local de navegação para revisão|
|`electron/workstation-browser-human-review.test.ts`|Criado. Identidade, lease, stale recovery, revision, CAS, fsync, concorrência|
|`electron/workstation-browser-ipc-human-review.test.ts`|Criado. Autoridade IPC, confirmação, rejeição de owner/frame inválido|
|`electron/workstation-browser-ipc.ts`|Editado. Canais exclusivos de revisão humana|
|`electron/preload.ts`|Editado. Bridge tipada para operações de revisão|
|`src/app/browser/types.ts`|Editado. Contratos de revisão e tipos|
|`src/app/chat/right-rail/workstation-browser-pane.tsx`|Editado. Projeção das revisões locais disponíveis e ação de revisão|

Estado: código e testes presentes/registrados; homologação funcional parcial. O mecanismo não foi validado como autorização geral para efeitos externos.

#### 6.3 Compositor e lifecycle

Arquivo criado:

`apps/desktop/electron/workstation-browser-minimized-compositor.ts`

A classe `MinimizedBrowserCompositor` foi confirmada no checkout atual.

Componentes introduzidos ou alterados incluem:

- Mapeamento de origem da view.
    
- Host auxiliar para janela minimizada.
    
- Reparenting sem recriar WebContents.
    
- Recuperação de host destruído.
    
- Preservação temporária de hosts destacados após fechamento humano.
    
- Reattach e cleanup.
    
- Geometria de tarefas `parked`.
    
- Destruição controlada no encerramento do runtime.
    

Estado: implementado e validado em E2Es isolados; testes adversariais completos de lifecycle ainda pendentes.

#### 6.4 Cliente Python e catálogo de ferramentas

Arquivo:

`tools/browser_workstation.py`

Mudanças implementadas:

- Remoção de `browser_admissions_reconcile` do catálogo disponível à LLM.
    
- Recuperação autenticada e limitada de GETs read-only quando o descritor muda.
    
- Preservação da política de não repetir POST mutante.
    

Teste criado:

`tests/tools/test_browser_controller_readonly_recovery.py`

Estado: código presente e testes direcionados aprovados. A recuperação Python contra uma queda/relisten nativa real ainda não foi homologada de ponta a ponta.

#### 6.5 Gravador de gestos e gates TypeScript

Arquivo editado:

`apps/desktop/electron/workstation-learning-session.ts`

Em `recordGesture`, quatro acessos à propriedade anulável `this.state` passaram a usar `recording`, variável já capturada e validada.

No runtime, dois argumentos `step.ref` passaram a usar `?? null`.

Resultado: os seis erros do typecheck principal do renderer foram eliminados. Os testes Electron passaram de 119 para 136 após inclusão da suíte de learning session.

#### 6.6 Testes E2E nativos criados

Todos os caminhos seguintes estão sob `apps/desktop/e2e/`; a inspeção atual confirma numerosos arquivos como não rastreados pelo Git.

|Família|Arquivos principais|Finalidade|
|---|---|---|
|Chromium independente|`workstation-native-hidden-browser-audit.cjs` e `-runner.cjs`|Controle positivo do Chromium oculto|
|Runtime real isolado|`workstation-runtime-native-isolated-entry.ts` e `-runner.cjs`|Duas BrowserTasks, input e recibos|
|Investigação de foco|`workstation-runtime-native-send-input-probe.ts`, `workstation-runtime-native-focus-emulation-probe.ts` e runners|Comparação de APIs e foco|
|P04|`workstation-runtime-native-parked-probe-runner.cjs`, `workstation-runtime-native-actions-probe-runner.cjs`|Clique parked, type, Enter e scroll|
|P05|Runners `minimized-probe`, `minimize-transition`, `restore-transition`, `minimized-lease`, `minimized-bounds`, `minimized-actions`|Minimização, restauração e leases|
|Recuperação HTTP|`workstation-runtime-native-controller-restart-runner.cjs`, `workstation-runtime-native-watchdog-relisten-runner.cjs`|Recuperação de controlador/listener|
|P06 lifecycle|`workstation-runtime-native-p06-host-loss-runner.cjs`, `-human-close-runner.cjs`, `-reattach-runner.cjs`, `-cycles-runner.cjs`|Falhas de host e janelas|
|P06 multiprocesso|`workstation-runtime-native-p06-process-crash-entry.ts` e `-runner.cjs`|Admissão pendente persistida e recuperação entre processos|

Os runners normalmente compilam a entrada TypeScript com esbuild, iniciam Electron separado e usam diretórios temporários para perfis e ledgers.

Dependência importante: o fato de passarem individualmente em Electron não implica que sejam compiláveis como parte do projeto `tsconfig.e2e.json`. Esse projeto apresentava falhas.

#### 6.7 Infraestrutura de execução e inicialização

Recursos relevantes:

```
apps/desktop/dist/electron-main.mjs
apps/desktop/scripts/bundle-electron-main.mjs
apps/desktop/scripts/hermes-nav.mjs
apps/desktop/scripts/eval.mjs
apps/desktop/scripts/ai-control-client.mjs
workstation/scripts/fast_reopen.ps1
START-HERMES-WORKSTATION.bat
workstation/scripts/oneclick_bootstrap.ps1
workstation/start.ps1
```

O bundle de desenvolvimento foi compilado repetidas vezes. O atalho e o fluxo de inicialização foram inspecionados, não modificados na missão MVP.

A página sintética final foi servida por um arquivo temporário Node denominado `hermes_mvp_local_page_20261029.cjs`, na pasta temporária do Windows, usando a porta `18653` em loopback. O processo do servidor foi encerrado ao final do teste. A existência posterior do arquivo temporário não foi verificada.

#### 6.8 Documentação produzida

Principal artefato:

`workstation/context/HERMES_NATIVE_BROWSER_RELIABILITY_MASTER.md`

O documento passou de um relatório inicial de bloqueio para um registro cronológico das fases, com matrices AC, RED/GREEN, hashes, testes, limitações e homologação operacional final.

Validação: arquivo existente, 81.177 bytes, SHA256 atual confirmado na seção 0.

### 7. Problemas, bugs e análise de causa raiz

|ID|Sintoma e causa identificada|Correção e evidência|Estado|
|---|---|---|---|
|B-01|Descritor do controlador apontava para processo morto|Watchdog, republicação e relisten; 20 ciclos sintéticos e relisten nativo|PARCIAL: recuperação após morte integral do app não homologada|
|B-02|Snapshot restaurava URL apesar de batch incerto|`shouldDeferRestoredNavigation()` ampliado; RED/GREEN e reinício multiprocesso sem auto-load|VERIFICADO para cenário testado|
|B-03|LLM conseguia declarar `OPERATOR_REVIEW`|`agent_reconciliation_forbidden`, remoção de catálogo|VERIFICADO em testes|
|B-04|Mutação gerava `runId=unbound`|Validação de identidade pré-dispatch|VERIFICADO em regressão; históricos mantidos|
|B-05|Cliente Python não se recuperava em GET|Redescoberta autenticada + retry único|PARCIAL: unitário passou, E2E real pendente|
|B-06|`browser_click` recebia ACK sem evento DOM|Observador de `click` confiável antes do receipt|VERIFICADO como mitigação do falso positivo|
|B-07|Clique não chegava à WebContentsView sem foco|`Emulation.setFocusEmulationEnabled` restrita ao WebContents|VERIFICADO em E2E e MVP|
|B-08|Janela minimizada reduzia viewport a 1×1|Compositor auxiliar não minimizado e geometria preservada|VERIFICADO nos cenários executados|
|B-09|Task A `parked` podia migrar para host B|Ownership por view e `owningHostFor()`|VERIFICADO no E2E|
|B-10|Host auxiliar destruído continuava referenciado|Recuperação por evento `closed` e reparenting|VERIFICADO no E2E P06|
|B-11|Fechamento da janela humana eliminava host de task viva|Host detached e reattach posterior|VERIFICADO no E2E P06|
|B-12|`fsync` podia falhar após publicação de `RECONCILED`|Sincronização anterior à publicação e remoção de flush redundante|PARCIAL: testes de injeção passaram; power-loss não provado|
|B-13|Seis erros de TypeScript no renderer|`step.ref ?? null` e variável `recording` validada|VERIFICADO|
|B-14|E2E TypeScript apresentava `TS6307` e erros em fixtures|Nenhuma correção definitiva registrada|FALHOU / PENDENTE|
|B-15|Build de distribuição falhava com `EPERM` em `native-deps`|Não houve correção nem remoção forçada|FALHOU / PENDENTE|
|B-16|Processo Hermes executava bundle anterior|Reinício normal pelo usuário e nova compilação|VERIFICADO operacionalmente|
|B-17|Origem de uma mudança de foco durante o teste não foi identificada|Nenhuma causa raiz demonstrada|INDETERMINADO|

#### Análises que não devem ser distorcidas

B-07: o experimento sustenta uma dependência de foco interno do renderer para o cenário testado. Não demonstra uma regra universal de todos os componentes Chromium, versões Electron ou topologias de composição.

B-08: a emulação de foco e o host auxiliar resolvem problemas diferentes. Remover qualquer um deles sem regressão correspondente pode reintroduzir o defeito.

B-12: o uso de lock e `fsync` não demonstra automaticamente atomicidade contra perda de energia em todas as variantes do filesystem Windows.

B-15: o erro `EPERM` indica uma falha de operação de arquivo. A hipótese de um processo mantendo o diretório bloqueado é plausível, mas o processo proprietário não foi identificado. Não se deve registrá-la como causa raiz comprovada.

B-17: o histórico registrou `document.hidden=true` e `document.hasFocus()=false` durante operações; depois apareceu `hidden=false` e `focus=true`. Não há evidência suficiente para atribuir a restauração ao agente, ao operador ou ao comportamento da própria aplicação.

### 8. Testes, verificações e evidências de funcionamento

#### 8.1 Distinção entre os níveis de validação

Foram utilizados quatro níveis de prova, com capacidades diferentes:

|Nível|O que comprova|O que não comprova automaticamente|
|---|---|---|
|Teste unitário / Vitest|Contrato e comportamento de componentes instrumentados|Funcionamento real do Chromium|
|E2E Chromium isolado|Electron, WebContents, input e readback reais em perfil de teste|Integração do agente produtivo|
|Dogfooding do Hermes|Agente real operando BrowserTask no aplicativo|Resistência a qualquer crash ou concorrência|
|Build/release/CI|Integridade da geração distribuível e gates pertinentes|Ausência universal de falhas operacionais|

O principal erro de interpretação evitado durante a sessão foi considerar sucesso em um desses níveis como prova de todos os demais.

#### 8.2 Evolução das regressões

|Fase|Electron|Python|UI|Observação|
|---|---|---|---|---|
|Preflight inicial|94/94|35 + 29, além de 14 subtestes|3/3|Baseline inicial|
|P02|115/115|Evolução de 66 para 67 + 14 subtestes|3/3|Correções de admissões e cliente|
|P03 revisão humana|112/112 e depois 117/117|67 + 14 subtestes|3/3|Mudança de conjunto de suítes e testes|
|P04|119/119|67 + 14 subtestes|3/3|Foco emulado e clique confiável|
|P05|119/119|67 + 14 subtestes|3/3|Compositor minimizado|
|P06|136/136|67 + 14 subtestes|3/3|Inclui testes de learning session|

Esses números representam execuções e conjuntos selecionados, não a cobertura integral do repositório. Não devem ser somados para produzir um total de testes independentes.

Os resultados históricos estão registrados no relatório canônico; vários resultados posteriores também aparecem diretamente nas respostas das ferramentas nesta conversa.

#### 8.3 Comandos principais e resultados

Electron:

```
cd C:\Github\hermes-agent\apps\desktop

..\..\node_modules\.bin\vitest.cmd run `
  --project electron `
  electron/workstation-learning-session.test.ts `
  electron/workstation-browser-human-review.test.ts `
  electron/workstation-browser-ipc-human-review.test.ts `
  electron/workstation-browser-ipc-learning-owner.test.ts `
  electron/workstation-browser-runtime-admission.test.ts `
  electron/workstation-browser-runtime-recovery.test.ts `
  electron/workstation-browser-session-state.test.ts `
  electron/workstation-browser-runtime-task.test.ts `
  electron/workstation-browser-runtime-batch.test.ts `
  electron/workstation-browser-batch.test.ts `
  electron/workstation-browser-batch-proof.test.ts `
  --reporter=dot
```

Resultado registrado em P06: 136/136 PASS, 11 arquivos.

Python:

```
cd C:\Github\hermes-agent

.\.venv\Scripts\python.exe -m pytest `
  tests/tools/test_browser_controller_readonly_recovery.py `
  tests/tools/test_browser_batch_semantic_contract.py `
  tests/tools/test_whatsapp_browser_tools.py `
  workstation/tests/test_p0_native_handoff_review_api.py `
  workstation/tests/prefabs/test_prefabs.py -q
```

Resultado: 67 PASS + 14 subtestes, conforme os registros da execução.

TypeScript:

```
cd C:\Github\hermes-agent\apps\desktop

..\..\node_modules\.bin\tsc.cmd -p tsconfig.electron.json --noEmit
..\..\node_modules\.bin\tsc.cmd -p tsconfig.json --noEmit
```

Ambos passaram após P06.

UI:

```
..\..\node_modules\.bin\vitest.cmd run `
  --project ui `
  src/app/chat/right-rail/workstation-browser-pane.test.tsx `
  --reporter=dot
```

Resultado: 3/3 PASS, com avisos não fatais de React `act` e localStorage.

E2E TypeScript:

```
..\..\node_modules\.bin\tsc.cmd -p tsconfig.e2e.json --noEmit
```

Resultado: FALHOU. Foram registrados `TS6307` e erros de tipagem nos probes/fixtures.

Build:

```
node scripts/bundle-electron-main.mjs --dev
node scripts/build.mjs
```

O bundle de desenvolvimento passou. O build completo falhou com `EPERM` na etapa de publicação de dependências nativas.

#### 8.4 Testes RED importantes

|Cenário|Resultado antes da correção|Significado|
|---|---|---|
|Forja de reconciliação|`RECONCILED` aceito com `resolvedBy=agent`|Vulnerabilidade de autoridade|
|Mutação sem identidade|Admission `runId=unbound`|Identidade insuficiente|
|Restart P02|URL anterior carregada apesar de batch incerto|Violação da semântica read-only|
|Clique em WebContentsView|Receipt com `window.count=0`|Falso positivo de efeito|
|Alternativa `sendInputEvent`|`count=0`, `focused=false`|Alternativa descartada|
|Janela minimizada|`target_outside_viewport`|Superfície inválida|
|Host auxiliar destruído|WebContents vivo, host não recuperado|Falha de lifecycle|
|Fechamento humano|View viva sem host apropriado|Falha de ownership/lifecycle|
|Fsync após publicação|Terminal visível apesar de erro|Problema transacional|
|Renderer TypeScript|Seis erros de nulabilidade|Bloqueio de compilação|
|Release build|`EPERM` em `native-deps`|Bloqueio não resolvido|

Esses REDs são importantes porque comprovam por que as soluções posteriores foram necessárias.

#### 8.5 Homologação operacional real

O teste final diferenciou-se dos anteriores por utilizar o próprio Hermes Agent.

A página local forneceu um registro independente dos efeitos:

```
http://127.0.0.1:18653/

loads   = 1
clicks  = 2
typed   = bg-20261029
enters  = 2
scrolls = 2
lastY   = 0
```

Esses valores foram observados após duas rodadas intencionais de operação.

O agente reportou operation IDs individualizados, incluindo:

```
op_browser_navigate_734a86cd646a
op_browser_click_beb99d9da1e0
op_browser_type_8ed6a9f86eed
op_browser_press_d529eb570c24
op_browser_scroll_ef9bb28e0b72
```

Na segunda rodada, também reportou:

```
op_browser_click_2cfae1a9d24e
op_browser_type_6e2104a92bdd
op_browser_press_362fc4de6621
op_browser_scroll_6b691a00248a
```

Evidência mais forte: os efeitos foram observados por um servidor HTTP local separado da declaração do agente. Isso sustenta o resultado funcional de clique, texto, Enter e rolagem.

A inspeção do controlador mostrou `controlOwner=agent`, uma aba pertencente à BrowserTask correta e `lastError=null`.

#### 8.6 WhatsApp Web

A navegação ocorreu pelo próprio agente, utilizando a BrowserTask de teste.

Resultado observado:

- Domínio: `web.whatsapp.com`.
    
- Título: WhatsApp.
    
- Interface em estado de sincronização.
    
- Snapshot estrutural executado.
    
- Nenhum envio ou seleção de destinatário registrado.
    
- Nenhum erro informado pelo controlador.
    

Classificação: VERIFICADO para navegação e snapshot no escopo observado; PARCIAL para operação geral do WhatsApp.

O retorno HTTP 200 foi informado pelo agente. O controlador confirmou URL e título, mas não houve captura independente de uma transação HTTP que permita extrapolar para disponibilidade completa de todas as funções do WhatsApp.

#### 8.7 Lacunas de validação

Não foram concluídos:

1. Crash entre `mousePressed`, `mouseReleased`, readback e ACK durável.
    
2. Recuperação de batch com etapa efetivamente executada antes da queda.
    
3. Lease humana adquirida no meio de uma mutação em andamento.
    
4. Concorrência real entre apresentação humana e input do agente em todas as transições.
    
5. Recuperação Python GET contra queda/relisten real do controlador.
    
6. Fluxo completo de evidências de TaskRun/Kanban.
    
7. Múltiplos monitores físicos e topologias excepcionais.
    
8. Build de distribuição e CI completo.
    
9. Prova de durabilidade contra falha de energia.
    
10. Auditoria contínua de ausência de mudanças indevidas de foco durante todo o ciclo operacional.
    

Essas lacunas não anulam os testes aprovados. Limitam o alcance das conclusões.

### 9. Estado final dos artefatos e do repositório

#### 9.1 Estado Git

A inspeção complementar de 29/10/2026 às 22h33 confirmou:

|Atributo|Estado|
|---|---|
|Repositório|`C:\Github\hermes-agent`|
|Branch|`main`|
|HEAD|`f1d5ab2f030e940ed4571371b0de45a21a009c9e`|
|Entradas dirty|283|
|Arquivos não rastreados|223|
|Staging|0|
|Alterações rastreadas|60 arquivos com diferenças|
|Resumo das diferenças rastreadas|11.637 inserções e 876 exclusões|

Cuidado: esses totais abrangem o checkout compartilhado. Não constituem um diff exclusivamente produzido pela missão Browser.

Não foram observados commits, branches, worktrees ou pushes criados pelas operações desta conversa. O HEAD permaneceu inalterado. A existência de commits em outras máquinas, PRs remotos ou merges externos não foi verificada.

A referência `upstream/main` registrada no primeiro preflight estava em `571a5911ae6aaa05ef3df53bf0f6720c4556c24a`, com `merge-base` `3b63f7b0a4c7beb9eadbce2f15b9da75d01f5065`. A divergência reportada foi de 6.574 commits atrás e 1.349 à frente. Como não houve `git fetch` naquele diagnóstico, esses números não devem ser tratados como estado atual do remoto.

#### 9.2 Hashes importantes confirmados na inspeção complementar

|Arquivo|SHA256|
|---|---|
|`workstation-browser-runtime.ts`|`7C187664C28B8C19C38D99E9261EC392E64F378E7A7B890B19EB1EC0392EAA9F`|
|`workstation-browser-minimized-compositor.ts`|`31D6D3B378C4FD48CEBBECF71D8DBBC87B4180754A4C7D179905EE131AB51E58`|
|`workstation-browser-human-review.ts`|`B086E995345929B6DFAE9BD3E7450C99A02C33C66878229BCD8E76F91739F85C`|
|`workstation-browser-session-state.ts`|`38836171EC88971E4305E9CDC351DDAD4F0DF5BEDF99F8A526554D44DBA9193A`|
|`workstation-learning-session.ts`|`9CE4642C5FBDFC14EAD7803CDA0DD64A942C2414E202EF425EC1BACBB4C13F6D`|
|`tools/browser_workstation.py`|`DC1A1885FC657FF018DEACFF78D41D4FDDC5EA3414CF2C34F69372852588001F`|

Esses hashes identificam os bytes existentes às 22h33, e não um commit de release.

#### 9.3 Estado da aplicação

Às aproximadamente 17h41, a missão operacional deixou o Electron PID `35536` em execução, com AI Control e controlador autenticados.

Na inspeção complementar das 22h33, nenhum processo `electron.exe` apareceu no inventário do Windows.

Portanto, o resultado correto é:

- O Hermes funcionou durante a homologação.
    
- O processo `35536` estava vivo no postflight daquela missão.
    
- A existência de uma instância ativa às 22h33 não foi confirmada.
    
- Não há evidência suficiente para concluir por que a instância deixou de aparecer.
    

O sucesso operacional histórico não deve ser confundido com o estado instantâneo do aplicativo no momento da auditoria.

#### 9.4 Ledger produtivo

A inspeção das 22h33 encontrou:

```
%LOCALAPPDATA%\HermesWorkstation\Runtime\browser-session.json

Operação protegida: presente
ACK: false
Terminal: ausente
```

O timestamp de modificação do ledger era 17h49min30s, posterior à homologação inicial.

Isso não demonstra adulteração ou reconciliação do incidente protegido: a operação continuava pendente. Contudo, significa que não é correto afirmar que o arquivo inteiro permaneceu sem alterações até as 22h33.

Há uma diferença entre preservar a operação histórica e impedir toda gravação normal no ledger produtivo. O primeiro foi confirmado; o segundo não ocorreu, nem era necessariamente um requisito da execução cotidiana.

#### 9.5 Dependências e variáveis relevantes

Os testes nativos utilizaram, conforme cada harness:

```
HERMES_HOME
HERMES_WORKSTATION_HOME
HERMES_WORKSTATION_BROWSER_PROFILE
HERMES_WORKSTATION_BROWSER_CONTROL_FILE
HERMES_WORKSTATION_BROWSER_SESSION_STATE_FILE
```

Finalidade: isolar home, perfil Chromium, descritor de controle e persistência de sessão.

A configuração de desenvolvimento também utilizava `HERMES_DESKTOP_CDP_PORT=off` para não expor CDP externo. A ponte AI Control utilizava seu mecanismo autenticado de descoberta.

Tokens, cookies e segredos não são necessários para esta transferência e não foram reproduzidos.

#### 9.6 Documentação e recursos efêmeros

- Relatório canônico: atualizado com P02–P06 e MVP, ainda presente.
    
- Resume Prompts: produzidos em várias fases, sem representar implementação por si mesmos.
    
- Runners E2E: numerosos arquivos novos ainda não rastreados.
    
- Build dev: gerado localmente, sem prova de publicação ou release.
    
- Build completo: falhou.
    
- Página MVP temporária: servidor encerrado depois da homologação.
    
- Atalho Hermes Work: validado, sem modificação.
    
- Instalações de dependências novas: não foi verificada uma instalação específica como parte da missão MVP.
    
- PRs, merge e push remoto: não verificados.
    

### 10. Pendências, riscos e débitos técnicos

As prioridades abaixo são recomendações desta auditoria, não uma reabertura automática da missão de engenharia encerrada pelo usuário.

|ID|Pendência comprovada|Impacto|Prioridade|Condição objetiva de conclusão|
|---|---|---|---|---|
|P-01|WIP grande e não commitado|Perda de trabalho, conflitos, baseline ambígua|P0|Snapshot recuperável e revisão de escopo/ownership, com autorização Git específica|
|P-02|Crash após efeito real, antes do ACK|Duplicação ou reconciliação indevida|P0|E2E multiprocesso com efeito real, fence preservado e nenhum replay|
|P-03|Batch parcialmente executado|Resultado externo incerto|P0|Teste com etapa comprovadamente executada, reinício e estado causal seguro|
|P-04|Reconciliação de efeitos externos ainda restrita|Operações incertas podem permanecer bloqueadas|P1|Canal humano autenticado com evidência suficiente para a classe de efeito correspondente|
|P-05|Lease humana durante input|Possível disputa de autoridade|P1|Teste de mudança de lease antes/durante/depois do dispatch|
|P-06|Foco e lifecycle em cenários excepcionais|Interferência ou perda de superfície|P1|Testes com janelas/monitores/host loss e observabilidade de foco apropriada|
|P-07|Typecheck E2E falhando|Testes nativos fora do gate integral|P1|Projeto E2E compilável sem ocultar testes ou erros|
|P-08|Build completo `EPERM`|Ausência de pacote de release|P1|Identificar causa, executar build em ambiente controlado, exit 0|
|P-09|Cliente Python pós-relisten real|Recuperação incompleta de consultas|P2|Integração real GET read-only, sem retry de POST|
|P-10|TaskRun/Kanban final|Tarefas podem permanecer sem aceite verificável|P2|Evidência end-to-end de operação, readback, receipt, ACK e avaliação de aceite|
|P-11|CI exact-head e qualificação final|Incerteza para distribuição|P2|Gates pertinentes verdes em baseline identificada|
|P-12|Flakiness no teste de reattach|Resultado intermitente|P2|Reprodutor estável e causa da intermitência qualificada|
|P-13|Estado atual de execução do Hermes|Não comprova disponibilidade instantânea|P2|Verificação da instância quando houver demanda de uso|
|P-14|Logs e diagnósticos distribuídos em múltiplos prompts|Custo de continuidade e duplicação|P3|Uma baseline canônica concisa, sem descartar evidências históricas|

Separação importante: P-02 e P-03 são riscos de segurança transacional; P-07 e P-08 são gates de engenharia/release; P-14 é principalmente organização documental. Não devem receber o mesmo tratamento ou urgência.

#### Recomendações novas, não executadas

Esta auditoria recomenda duas melhorias de processo que não fazem parte das implementações comprovadas:

1. Manter um registro curto de versão operacional, incluindo HEAD, hashes do runtime, bundle, data de carga e última prova MVP.
    
2. Definir três gates distintos: MVP utilizável, release qualificável e resiliência avançada. Uma falha no terceiro não deve automaticamente reabrir todas as etapas do primeiro.
    

Nenhuma dessas recomendações foi implementada nesta auditoria.

### 11. Guia de continuidade para o próximo agente

#### 11.1 O que já está estabelecido

O próximo agente deve assumir como baseline, sujeito à verificação do checkout:

- O fluxo normal do Hermes pode controlar seu Browser nativo sem recorrer a mouse ou teclado global.
    
- O runtime usa `electron-chromium` e o controlador HTTP autenticado.
    
- A aplicação possui correções para clique confiável em segundo plano e compositor de tarefas minimizadas.
    
- A BrowserTask pode manter sua identidade ao mudar de host.
    
- O agente não deve poder reconciliar pendências por autodeclaração.
    
- A operação histórica protegida permanece pendente.
    
- O atalho atual já aponta para o fluxo de inicialização correto.
    
- O MVP foi homologado no cenário documentado, mas não como release integral.
    

#### 11.2 O que não deve ser repetido sem evidência nova

|Investigação|Motivo|
|---|---|
|Trocar CDP por `webContents.sendInputEvent()` como solução direta|RED comprovado em P03|
|Tratar ACK do CDP como entrega de clique|Falso positivo reproduzido|
|Usar `element.click()` como fallback genérico|Não demonstra equivalência causal|
|Corrigir clique minimizado apenas com emulação de foco|A causa geométrica exige solução distinta|
|Criar nova WebContents ao minimizar|O modelo aprovado preserva a mesma view|
|Reescrever o compositor apenas por preferência arquitetural|Há E2Es nativos e dogfooding aprovado|
|Repetir os 20 ciclos sintéticos sem alteração de código|Resultado já registrado|
|Criar outro atalho sem verificar o existente|O atalho atual foi inspecionado e validado|
|Recomeçar o P07 inteiro antes de usar o Hermes|A decisão 80/20 substituiu essa prioridade|

#### 11.3 O que não deve ser quebrado

Invariantes fundamentais:

```
Uma mutação pertence a uma identidade canônica.

Uma operação incerta não é repetida automaticamente.

Um ACK de transporte não comprova efeito externo.

Um receipt de clique local exige prova de entrega ao DOM.

Uma confirmação humana não substitui readback causal.

Uma BrowserTask não deve migrar para a sessão errada.

Uma janela humana minimizada não deve inutilizar o executor.

Nenhuma operação de Browser deve controlar mouse ou teclado global.

A operação histórica protegida não pode ser reconciliada por teste.
```

Também devem permanecer os bloqueios agent-only de reconciliação, a validação pré-dispatch e a distinção entre evidência local, admissão e aceite TaskRun/Kanban.

#### 11.4 Pontos de atenção no ambiente

Leituras iniciais:

```
C:\Github\hermes-agent\AGENTS.md
C:\Github\hermes-agent\workstation\AGENTS.md
C:\Github\hermes-agent\apps\desktop\AGENTS.md

C:\Github\hermes-agent\workstation\context\
HERMES_NATIVE_BROWSER_RELIABILITY_MASTER.md
```

Comandos de inspeção sem alteração:

```
Set-Location C:\Github\hermes-agent

git status --short
git rev-parse HEAD
git diff --stat

node apps/desktop/scripts/hermes-nav.mjs status
```

Testes direcionados:

```
Set-Location C:\Github\hermes-agent\apps\desktop

node e2e/workstation-runtime-native-isolated-runner.cjs

node e2e/workstation-runtime-native-minimized-probe-runner.cjs

node e2e/workstation-runtime-native-p06-process-crash-runner.cjs
```

Os comandos E2E são testes com efeitos em processos e perfis isolados, não meras leituras; devem ser executados apenas quando necessários e após revalidar a configuração de isolamento.

Abertura operacional:

`C:\Users\Kevyn Lucas\Desktop\Hermes Work.lnk`

Não é necessário recriar o atalho. Abertura, encerramento ou reinício da aplicação devem respeitar a autorização vigente no momento da execução.

A autorização especial de 29/10 não deve ser interpretada como permanente em sessões ou datas posteriores.

#### 11.5 Próximas ações recomendadas

1. Revalidar o estado de leitura do repositório e dos processos. Confirmar HEAD, alterações concorrentes, presença dos arquivos e instância ativa. Conclusão: inventário consistente, sem modificar nada.
    
2. Preservar a baseline atual antes de novas correções. Propor um procedimento de versionamento ou snapshot recuperável e obter autorização. Conclusão: alterações de P02–P06 não dependem exclusivamente de arquivos soltos no checkout.
    
3. Investigar falhas reais de uso, caso apareçam. Executar apenas o reprodutor relacionado ao sintoma, corrigir e repetir o fluxo operacional correspondente. Conclusão: efeito verificável e nenhuma regressão nos invariantes.
    
4. Priorizar crash pós-dispatch e batch parcial quando houver necessidade de maior autonomia. Conclusão: teste multiprocesso com efeito efetivo, sem replay nem recibo falso.
    
5. Qualificar o release em uma etapa separada. Resolver os gates `TS6307`, `EPERM` e CI sem interromper desnecessariamente o uso diário. Conclusão: build reproduzível associado a uma baseline identificada.
    

### 12. Matriz final de rastreabilidade

A matriz preserva os 24 critérios originais e acrescenta as solicitações operacionais posteriores.

|Requisito ou objetivo|Ação realizada|Melhor evidência|Estado final|Pendência|
|---|---|---|---|---|
|AC-01 Controller autenticado|Health e descoberta|GET `/health` no Hermes real|VERIFICADO historicamente|Estado instantâneo futuro|
|AC-02 Recuperação de descritor|Watchdog|10 ciclos específicos|VERIFICADO, sintético|Prova adicional somente se houver regressão|
|AC-03 Relisten|Watchdog nativo|E2E listener encerrado|VERIFICADO, isolado|Crash completo é outro critério|
|AC-04 Isolamento dos testes|Perfis e ledgers TEMP|Testes isolados, descritor preservado|VERIFICADO no escopo|Auditoria integral de isolamento não feita|
|AC-05 Persistência de sessões/viewports|Reparent, restore e restart|E2Es P05/P06|PARCIAL|Lifecycle integral|
|AC-06 Clique sem foco|Focus emulation + proof|E2E e servidor MVP|VERIFICADO no escopo|Não equivaler a ausência universal de falhas|
|AC-07 Digitação sem foco|Input no WebContents|E2E e MVP|VERIFICADO no escopo|Demais cenários de concorrência|
|AC-08 Press/scroll/snapshot|Operações nativas|E2E e MVP|VERIFICADO no escopo|Matriz completa de janelas|
|AC-09 Não interferência global|Sem APIs globais nas rotinas|Código/procedimento e estados ocultos|PARCIAL|Mudança de foco sem causa identificada|
|AC-10 Arbitragem humano/agente|Lease e HTTP 409|E2E P05|PARCIAL|Lease durante dispatch|
|AC-11 Idempotência após crash|Reinício de dois processos|Admission pendente conservada|PARCIAL|Crash após efeito real|
|AC-12 Revisão humana completa|IPC e CAS para navegação local|Testes P03|PARCIAL|Efeitos externos|
|AC-13 Impedir forja|Bloqueio agent-only|RED/GREEN integrado|VERIFICADO nos caminhos testados|Auditoria de superfícies adicionais, se surgirem|
|AC-14 Batch parcial|Requisitos e testes parciais|Sem E2E de efeito parcial|PENDENTE|Crash após etapa executada|
|AC-15 Isolamento BrowserTasks|Duas tarefas e hosts distintos|E2Es P04–P06|PARCIAL|Interleavings completos|
|AC-16 TaskRun/Kanban|Contratos e UI existentes|Testes dirigidos|PARCIAL|Aceite end-to-end|
|AC-17 Cliente read-only|Retry autenticado GET|Testes Python|PARCIAL|Integração após relisten real|
|AC-18 Fences após crash|Restart multiprocesso|`prior_operation_requires_reconciliation`|PARCIAL|Efeito despachado antes do crash|
|AC-19 Vinte ciclos|Harness isolado|20/20 PASS|VERIFICADO sintético|N/A para critério sintético|
|AC-20 Hermes real → Chromium|Sessão de teste do agente|Servidor independente e receipts|VERIFICADO, MVP|Cenários adicionais de produção|
|AC-21 Regressões-alvo|Electron/Python/UI/TS|136, 67+14, 3, typechecks|VERIFICADO|Não equivale à suíte integral|
|AC-22 Build/release/CI|Tentativas de build|`EPERM`, `TS6307`|FALHOU / PENDENTE|Qualificação integral|
|AC-23 Consistência final|Código, relatório e MVP|Testes, hashes e runtime|PARCIAL|Gates e resiliência avançada|
|AC-24 Preservação de incidente|Não reconciliar/repetir|Ledger de 22h33|VERIFICADO|Preservar até resolução legítima|
|Atalho por dois cliques|Inspeção de `.lnk` e scripts|Destino, argumentos, probe HOT|VERIFICADO na configuração|COLD não ensaiado independentemente|
|Novo bundle carregado|Reinício normal do usuário|PID novo e horários|VERIFICADO operacionalmente|Atestação criptográfica não realizada|
|Página sintética local|Agente Hermes|`loads=1`, DOM e receipts|VERIFICADO|N/A para MVP|
|Operação minimizada|AI Control + agente|Renderer oculto, efeitos locais|VERIFICADO no cenário|Foco posterior indeterminado|
|WhatsApp read-only|Navegação e snapshot|URL, título e estado estrutural|VERIFICADO no escopo|Demais funções não ensaiadas|
|Não enviar WhatsApp|Apenas navegação/snapshot|Operações exibidas|VERIFICADO para o teste|Auditoria de todos os fluxos externos não realizada|
|Não criar commit/push|Preservação WIP|HEAD e staging inalterados|VERIFICADO nas operações observadas|Estado remoto não verificado|
|MVP utilizável|Homologação operacional|Efeitos independentes e controlador|VERIFICADO no escopo|Não equivale a release completo|

Síntese da matriz: o critério AC-20, que permaneceu bloqueado durante quase toda a engenharia, recebeu finalmente evidência real. Em contrapartida, os critérios de durabilidade avançada, segurança transacional completa e release não foram concluídos. Essas duas conclusões são compatíveis e não devem ser fundidas em um único status de aprovação ou reprovação.

### 13. Avaliação crítica da sessão

#### 13.1 O que produziu maior valor

Fatos observados: os maiores avanços técnicos foram a descoberta do receipt falso-positivo, a correção do foco interno ao Chromium, a separação entre janela humana e host de execução e a homologação real no Hermes Agent.

Esses trabalhos removeram bloqueadores que impediam o comportamento desejado. Em particular, a combinação de `Emulation.setFocusEmulationEnabled` com prova de `click` confiável resolveu um defeito que não era identificável apenas pelos testes unitários.

O compositor minimizado corrigiu um segundo defeito, independente do primeiro: geometria inválida em janela humana minimizada.

Por fim, o teste operacional com servidor local independente trouxe a melhor evidência de uso real de toda a sessão.

#### 13.2 O que consumiu esforço desproporcional

Avaliação: a sequência de Resume Prompts e critérios AC-01 a AC-24 foi útil para preservar segurança e contexto, mas tornou-se o mecanismo dominante de trabalho.

Houve tendência a ampliar a matriz de homologação antes de verificar se o aplicativo produtivo já tinha carregado o código desenvolvido.

O fato de o processo PID `9896` estar rodando um bundle anterior foi identificado tardiamente em relação ao volume de testes já executados. Depois que isso foi resolvido por reinício normal, o fluxo operacional apresentou resultados positivos rapidamente.

Isso não torna os testes anteriores inúteis: vários encontraram defeitos reais de segurança e integridade. Significa que a ordem de execução poderia ter produzido valor prático mais cedo.

#### 13.3 Decisões bem fundamentadas

Foram particularmente adequadas:

- Impedir reconciliação por autodeclaração da LLM.
    
- Preservar operações incertas, em vez de reexecutá-las.
    
- Exigir readback de entrega do clique.
    
- Não controlar periféricos globais.
    
- Não modificar o ledger histórico para facilitar testes.
    
- Manter perfis isolados para experimentos de crash.
    
- Distinguir compilação, E2E isolado, runtime produtivo e release.
    
- Respeitar a ausência de autorização inicial para reiniciar o Hermes.
    
- Conservar o atalho existente após demonstrar que seu fluxo já era adequado.
    

#### 13.4 Onde faltou investigação ou validação

Fatos:

1. Não há prova de recuperação após crash no meio de um efeito realmente executado.
    
2. O build de distribuição não passou.
    
3. O typecheck E2E não passou.
    
4. O fluxo causal completo de TaskRun/Kanban não foi homologado.
    
5. O fluxo de revisão humana não foi generalizado de maneira segura para efeitos externos.
    
6. A origem da restauração de foco durante o MVP não foi identificada.
    
7. Não houve uma baseline Git consolidada dos arquivos produzidos nesta sequência.
    
8. O estado posterior do aplicativo mudou: o processo observado na homologação não apareceu na inspeção das 22h33.
    

Essas limitações devem permanecer documentadas.

#### 13.5 Avaliação da engenharia de confiabilidade

O sistema terminou a missão operacional em situação substancialmente melhor que no começo.

No início, havia um controlador indisponível, falhas de autoridade, restauração insegura e um executor que podia confirmar cliques não entregues.

No final, havia evidência real de uma sessão Hermes executando a sequência essencial do Browser e abrindo WhatsApp Web sem envio.

A conclusão tecnicamente defensável é: o MVP funciona no cenário homologado; a confiabilidade universal e a distribuição ainda não foram certificadas.

Não seria correto declarar que o Browser está completamente livre de erros. Também não seria correto desconsiderar o resultado funcional apenas porque nem todos os 24 critérios estão fechados.

#### 13.6 Mudança de abordagem recomendada

A continuidade deveria ser organizada em três níveis de prioridade:

|Nível|Objetivo|Quando executar|
|---|---|---|
|Operação cotidiana|Usar o Hermes nos fluxos já homologados, preservar segurança e observar falhas concretas|Imediatamente, quando o aplicativo estiver disponível|
|Correção de bloqueadores|Resolver regressões reais, crash com efeito incerto e falhas que interrompam o uso|Quando reproduzidas ou necessárias à autonomia|
|Qualificação de release|CI, build, compatibilidade E2E e certificação ampliada|Como projeto separado de estabilização/publicação|

A próxima sessão de engenharia não deveria começar automaticamente por outro conjunto de dezenas de cenários. Deveria começar pela pergunta verificável: qual falha concreta ainda impede o uso ou cria risco inaceitável?

Se não houver bloqueador operacional, o melhor próximo investimento é preservar uma baseline recuperável e continuar usando a solução. Se houver, reproduzir exclusivamente essa falha, aplicar a menor correção segura e validá-la no runtime correspondente.

## Conclusão da auditoria

MVP operacional: comprovado no fluxo real de 29/10.

Implementações centrais: presentes no checkout consultado.

Incidente histórico: ainda pendente e protegido na última leitura.

Release e resiliência integral: não homologados.

Baseline Git: grande volume de WIP ainda sem consolidação.

Veredito: a sessão produziu correções reais, conhecimento técnico relevante e uma homologação operacional válida. O principal problema de processo foi prolongar a investigação abrangente antes de comprovar o funcionamento na instância efetivamente utilizada. A mudança para a estratégia 80/20 corrigiu essa prioridade.

O registro histórico está preservado no relatório canônico e nesta reconstrução, com as limitações de evidência explicitadas. Nenhuma nova implementação foi realizada durante a auditoria.