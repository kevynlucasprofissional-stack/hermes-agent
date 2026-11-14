# Auditoria crítica do browser

**User:** Anonymous  
**Created:** 10/18/2026 18:43:30  
**Updated:** 10/19/2026 2:46:46  
**Exported:** 10/19/2026 11:15:04  
**Link:** [https://chatgpt.com/c/6ad53d81-afc0-83e8-8683-52e10225a49b](https://chatgpt.com/c/6ad53d81-afc0-83e8-8683-52e10225a49b)  

## Prompt:
18/10/2026, 18:43:24

Análise o abaixo e o anexo, compara com o que está disponível hoje no código do Hermes Work, para isso use o [$github](app://connector_76869538009648d5b282a4bb21c3d157)&#x20;

Segue a análise crítica (Anexo a outra):

Vou localizar os documentos de arquitetura e decisões recentes sobre o browser do Hermes Workstation para fundamentar a análise crítica.

Vou ler os documentos centrais de arquitetura e decisões sobre o browser para fundamentar a análise crítica.

Vou ler as decisões recentes e o estado atual do browser para cruzar com a arquitetura já obtida.

Com base na leitura completa de `workstation/ARCHITECTURE.md` e `workstation/context/DECISIONS.md`, a arquitetura do browser do Hermes Workstation é **sólida em princípios e contratos, mas apresenta uma lacuna crítica entre a visão documentada e a qualificação operacional real**. A análise crítica segue abaixo.

---

## Análise Crítica da Arquitetura do Browser — Hermes Workstation (2026-10-18)

### 1. Visão Original vs. Realidade Atual

A visão que você desenhou está clara e bem preservada nos documentos: o browser do Workstation **não é um segundo aplicativo**, é uma projeção do Chromium que já existe no Electron do Hermes Desktop, com ciclo de vida próprio (`BrowserTask`), perfil isolado, controller loopback-only autenticado e routing fail-closed. Essa visão é correta e diferenciada — evita a armadilha comum de criar um "segundo browser" paralelo.

**O problema:** essa visão está quase inteiramente no plano documental. As decisões mais recentes (CW-047, CW-048B, D-047) mostram que o browser nativo **já executa operações reais** (PhotoCraft/EffectCraft/FilmCraft carregando Wasm/WebGL2 no Chromium interno, Learning Mode capturando eventos na mesma sessão), mas a qualificação end-to-end sob os gates H-079/H-081/exact-head CI permanece aberta ou bloqueada. Ou seja: o browser funciona como runtime criativo, mas ainda não tem prova canônica como mecanismo de automação confiável.

### 2. Pontos Fortes da Arquitetura

- **One Hermes State respeitado:** `BrowserTask` não cria SessionDB/Kanban/Memory paralelos. O binding task↔WebContentsView é process-local e recuperável via metadata atômica. Correto.
- **Fail-closed por design:** Um BrowserTask bound nunca faz failover silencioso para outro lane. Perda de controller → `pause → health/reconnect → rebind → verify → resume`. Isso elimina a classe de bugs onde automação continua em página errada após reconexão.
- **Routing em camadas com semântica clara:** `electron-chromium` (V1 primary) → `agent-browser` (fallback determinístico) → `browser-exec` (adaptive/power) → `lightpanda` (futuro). Cada lane tem contrato explícito; nenhum é "mágico".
- **Safety gates concretos:** Approval gate cobre pagamentos, publish, delete, credentials, money movement, secrets. Não é genérico — é enumerado.
- **D-046 Low-Coupling First:** Motores criativos entram via Browser/painéis existentes sem absorver código-fonte. Cada estágio pode ser o definitivo. Isso protege contra over-engineering prematuro.

### 3. Tensões e Riscos Identificados

#### 3.1 Gap entre "Browser como Runtime Criativo" e "Browser como Mecanismo de Automação"

As decisões CW-047/CW-048B provam que o Chromium interno carrega apps complexas (Wasm, WebGL2, OPFS). Mas `browser-automation-v1/DECISIONS.md` e o estado do P0–P2 mostram que **automação transacional confiável** (Trello write, HyperFrames edit com readback verificado) ainda depende de evidência nativa qualificada que não foi produzida. O browser serve bem como *display surface* para motores externos, mas o contrato de automação durável (`BrowserTransaction` em `ARCHITECTURE.md` §Durable execution routing) carece de prova E2E sob os gates canônicos.

#### 3.2 Controller Loopback-Only vs. LAN/Mobile

A arquitetura declara que o controller descriptor "is never exposed through LAN mode" e que non-loopback bind é fail-closed. Mas a seção LAN/mobile descreve um fluxo V1 (`Desktop toggle → auth verification → dashboard bind → IP detection → QR`) que **necessariamente** envolve comunicação não-loopback. Não há decisão documentada sobre como o controller token sobrevive a esse salto sem violar o invariante loopback-only. Isso é um risco de segurança não resolvido no papel.

#### 3.3 BrowserTask Metadata Recovery Sem Prova de Restauração Fiel

`ARCHITECTURE.md` diz que no restart, metadata é restaurada como parked e a página é recriada lazy sob o mesmo `taskId`. Mas também admite explicitamente: "This is not serialization of the previous renderer, JavaScript heap, or WebContents object." Para motores criativos com estado não-persistido (canvas dirty, timeline não-salva), isso significa perda silenciosa. CW-048B mitiga isso com snapshot prévia e reuso não-destrutivo, mas apenas para os três motores catalogados. Qualquer outro uso do browser perde estado no restart sem aviso ao usuário.

#### 3.4 D-047 Learning Mode Compartilha Sessão do Browser

O Learning Mode usa o "mesmo Browser Chromium e mesma sessão" quando o usuário clica Aprender. Isso viola o isolamento implícito entre tarefas automatizadas e observação humana: se uma automação está rodando em uma aba e o usuário ativa Learning em outra, ambos compartilham cookies/localStorage do mesmo perfil persistente. A captura é opt-in e limitada à aba de origem, mas o **perfil compartilhado** cria um vetor de interferência que não está endereçado na arquitetura atual.

#### 3.5 Quatro Runtimes Declarados, Um Qualificado

A abstração `BrowserRuntime` lista quatro implementações (`electron-chromium`, `agent-browser`, `browser-exec`, `lightpanda`). Na prática, apenas `electron-chromium` tem evidência operacional real (CW-047/CW-048B). Os outros três existem como contratos/documentação. Se o routing falhar para o primário e tentar fallback para um lane não-qualificado, o resultado é indeterminado. A arquitetura deveria declarar explicitamente quais lanes estão qualificados para produção vs. development-only.

### 4. Recomendações

1. **Produzir evidência nativa de BrowserTransaction E2E** sob exact-head CI antes de declarar o mecanismo de automação como qualificado. Os motores criativos provam o runtime; falta provar a transação durável.
2. **Documentar o modelo de ameaça LAN/mobile para o controller.** Ou o token é reemitido pós-auth com escopo restrito, ou o fluxo V1 precisa de um canal seguro separado do loopback descriptor.
3. **Adicionar estado de "non-recoverable" ao BrowserTask lifecycle.** Quando a página tinha estado não-persistido e o restart ocorreu, o usuário deve ser informado explicitamente, não receber uma página vazia sob o mesmo taskId.
4. **Isolar perfis de browser para Learning Mode vs. Automação.** Mesmo Chromium, sessões separadas. O custo é baixo (Electron Session é leve) e elimina o vetor de interferência.
5. **Marcar explicitamente no código e na documentação quais BrowserRuntime lanes são production-qualified.** Hoje isso só existe nas decisões; o router deveria recusar lanes não-qualificados em modo release.

### 5. Conclusão

A arquitetura do browser do Hermes Workstation é **uma das melhores fundações documentadas que vi em projetos de agent-browser**: fail-closed, one-state, low-coupling, safety-enumerated. O desenho está certo. O risco não é arquitetural — é de **qualificação incompleta**. O gap entre "o browser roda PhotoCraft" e "o browser executa transações duráveis com prova canônica" é real e precisa ser fechado antes de qualquer claim de automação confiável. As decisões recentes (D-046, CW-047, CW-048B, D-047) avançaram o runtime criativo corretamente, mas o mecanismo de automação transacional ainda deve seu exame final.

[Attachment: Texto colado(20261018-214144).txt]

## Response:
18/10/2026, 18:43:31 · gpt-6-thinking

Vou confrontar as duas análises com o código atual do `hermes-agent` no GitHub, incluindo a branch, os contratos de execução, o controller, as ferramentas de automação e os testes. Vou separar problemas comprovados, recomendações ainda válidas e propostas que duplicariam recursos existentes, priorizando correções de maior impacto.

A leitura do Electron trouxe um ponto importante: o Hermes já possui executor de ações em lote com verificações por etapa e interrupção em caso de resultado incerto. Isso muda a prioridade da proposta `act()+verify+retry`\: antes de criar outro executor, precisamos avaliar como aproveitar o que existe sem repetir mutações que talvez já tenham sido efetivadas. Também encontrei distinções explícitas entre restauração de metadados e recuperação real da página.

Encontrei um bloqueio verificável no estado atual, não apenas documental: o workflow do Workstation no commit auditado da `main` terminou com **falha**\. Além disso, o PR experimental de Browser Automation (\#85) já foi incorporado à `main`, embora documentos internos ainda o descrevam como não mesclado. Vou examinar os jobs para distinguir falha de qualificação, falha de ambiente e defeito funcional do browser.

> **Lendo texto colado para análise do repositório**
>
>
> **Analisou texto colado sobre o repositório**
>
> 
>
> **Inspecionou repositório, arquitetura, documentação e corrigiu filtros regex inválidos**
>
> 
>
> **Avaliou implementação, segurança, licenciamento, testes e documentação do BrowserOS e Hermes**
>
> 
>
> **Comparando arquiteturas**
>
> Estou distinguindo pseudocódigo de integração real: a execução sem modelo exige etapas estruturadas, enquanto a extração semântica precisa validar o esquema na projeção. Também estou verificando interfaces, eventos existentes e hierarquia de erros estruturados.
>
> **Comparou arquiteturas**
>
> 
>
> **Validando a implementação**
>
> Estou consolidando a auditoria com foco no código existente: cobertura de testes, diferenças entre execução determinística e semântica, validação de esquema, eventos, segurança de caminhos e riscos de duplicação em retentativas.
>
> **Validou a implementação**
>
> 
>
> **Analisou falhas do CI e priorizou testes críticos de segurança**
>
> 
>
> Pensou por 6m 57s

# Auditoria crítica - Browser do Hermes Work (18/10/2026)

**Escopo\:** confronto das duas análises fornecidas com a implementação disponível no repositório [kevynlucasprofissional-stack/hermes-agent](https://github.com/kevynlucasprofissional-stack/hermes-agent?utm_source=chatgpt.com), utilizando o GitHub conectado.

A referência principal desta auditoria é a branch `main`, cujo commit mais recente identificado é `f436e949` \(18/10/2026, 18:24 UTC). Também considero separadamente funcionalidades experimentais e evidências ainda não promovidas para produção.

## 1\. Diagnóstico inicial

As duas análises identificam oportunidades relevantes, mas algumas conclusões precisam ser corrigidas antes de virarem tarefas de implementação.

O primeiro problema é a confusão entre **uma capacidade implementada, uma capacidade integrada e uma capacidade operacionalmente comprovada**\. São três níveis distintos de maturidade.

Já confirmei dois exemplos concretos\:

- O Hermes possui `browser_batch_actions` na superfície de ferramentas do Workstation. Portanto, não precisamos assumir que toda automação exige necessariamente chamadas granulares ao modelo.
- O Hermes já possui `WorkstationBrowserError`, com campos `error_code`, `retryable`, `retry_after_ms` e tratamento estruturado de falhas. Logo, a proposta de criar uma hierarquia de erros do zero parte de uma premissa incorreta.

Esses elementos aparecem em [tools/browser\_workstation.py](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/main/tools/browser_workstation.py?utm_source=chatgpt.com)\.

A análise também precisa diferenciar segurança de atomicidade. O contrato de `browser_transaction.py` exige fases e evidências semânticas, mas isso não significa que uma operação externa em Trello, por exemplo, tenha atomicidade equivalente à de uma transação de banco de dados.

**A questão central não é simplesmente adicionar recursos inspirados no BrowserOS. É descobrir quais contratos já existem, verificar se estão efetivamente conectados ao caminho principal de execução e fechar apenas as lacunas comprovadas.**

## 2\. Estado real da implementação

| Componente | Situação no código | Avaliação |
|--------|--------|--------|
| Chromium nativo com `WebContentsView` | Implementado no Electron | Base funcional |
| BrowserTask com persistência | Implementado | Recuperação parcial |
| Controller autenticado em loopback | Implementado | Contrato de segurança concreto |
| Lease humano e bloqueio de automação | Implementado | Exige E2E adicional |
| `browser_batch_actions` | Implementado com verificações por etapa | Não cobre todas as pós-condições |
| Readiness semântica | Implementada | Integração existente; cobertura a qualificar |
| Extração durável para ArtifactStore | Implementada | Schema genérico ainda é oportunidade |
| Erros estruturados | Implementados | Não requer nova hierarquia |
| Progresso e eventos | Eventos e IPC existentes | Sem SSE nativo equivalente ao BrowserOS no controller inspecionado |
| Learning Mode | Integrado ao browser e ao lease humano | Há riscos específicos a testar |
| Automação transacional real após crash | Evidência parcial e experimental | Não qualificada para release |
| Quatro runtimes intercambiáveis | Contrato abstrato e rotas legadas | Sem prova de quatro implementações equivalentes |

### Evidência de integração já existente

O arquivo [workstation-browser-batch.ts](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/main/apps/desktop/electron/workstation-browser-batch.ts?utm_source=chatgpt.com) implementa `executeAuthorizedBatch()` com até 20 etapas. Ele verifica a autoridade antes de cada ação, executa o efeito, realiza readback e registra checkpoint.

O arquivo [workstation-browser-runtime.ts](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/main/apps/desktop/electron/workstation-browser-runtime.ts?utm_source=chatgpt.com) conecta esse executor à aba real, aos receipts e ao estado persistido do BrowserTask.

Isso demonstra que o executor não é apenas uma interface abstrata. Entretanto, a verificação atual de cliques, no módulo `workstation-browser-batch-proof.ts`, reconhece principalmente mudanças observáveis em controles como `checked`, `aria-pressed` e `aria-expanded`\. Um clique em “Salvar”, que persiste dados remotamente sem alterar esses atributos, não recebe automaticamente uma prova de persistência externa.

**Portanto, existe automação em lote real, mas o verificador genérico não substitui a verificação semântica da transação.**

## 3\. Um problema adicional de qualificação

**A CI do commit auditado não está verde.**

O workflow `workstation-ci.yml`, execução [\#39154888493](https://github.com/kevynlucasprofissional-stack/hermes-agent/actions/runs/39154888493?utm_source=chatgpt.com), apresenta resultado `failure` no commit `f436e949`\.

A consulta retornou o estado geral da execução, mas não disponibilizou os jobs individuais; portanto, ainda não é possível atribuir a falha a um teste específico, ao ambiente ou à infraestrutura.

Há também uma divergência documental comprovada: o [PR \#85 — Browser Automation V1](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/85?utm_source=chatgpt.com) aparece no GitHub como **merged em 13/10/2026**, apesar de seu texto e de `browser-automation-v1/STATE.md` ainda descreverem a entrega como não mesclada.

Isso não significa que a automação tenha sido qualificada para produção. Significa que **código experimental e documentação de qualificação precisam ser tratados separadamente**, mesmo quando já estão na `main`\.

## 4\. Revisão crítica das cinco recomendações arquiteturais

| Recomendação original | Veredito | Decisão recomendada |
|--------|--------|--------|
| 1\. Provar BrowserTransaction E2E | **Procede** | Prioridade máxima |
| 2\. Resolver contradição LAN/loopback | **Diagnóstico incorreto** | Documentar fronteiras de autorização, sem redesenhar controller |
| 3\. Identificar estado não recuperável | **Procede parcialmente** | Ampliar estados e avisos existentes |
| 4\. Separar perfil do Learning Mode | **Solução excessiva** | Corrigir isolamento de autoridade primeiro |
| 5\. Qualificar quatro runtimes | **Procede com ressalvas** | Qualificar rotas executáveis, não exigir quatro implementações completas |

### 4.1. LAN/mobile: não existe a contradição descrita

O Electron realmente mantém o controller escutando em `127.0.0.1` e utiliza um bearer token local. Isso foi confirmado em `workstation-browser-runtime.ts`, linhas 2365-2477.

Já o acesso LAN utiliza a infraestrutura autenticada do Hermes Dashboard, com verificação de autenticação antes de permitir bind não-loopback em `workstation/lan/controller.py`\.

São duas fronteiras diferentes\:

**Cliente remoto - LAN/mobile**

Identidade autenticada e permissões do usuário

**Hermes Dashboard / Backend**

Valida autorização, sessão e intenção

**Controller Electron - 127.0.0.1**

Token privado local; não precisa chegar ao cliente remoto

O problema real a qualificar é se o backend preserva corretamente a identidade e a autorização da operação remota ao invocar o controller. Não há justificativa, no código examinado, para transportar o bearer token até o celular.

### 4.2. Restart: a implementação é mais madura do que a análise sugere

O código já distingue `fresh`, `restored` e `recreated` para BrowserTask, além de `live`, `restored` e `stale` para abas.

Também usa políticas de restauração como `restore-safe-url`, `restore-about-blank` e `browser-task-lazy`\.

Isso demonstra reconhecimento explícito da recuperação incompleta. O problema restante é **comunicar ao usuário se o conteúdo não salvo da página realmente sobreviveu**\.

Eu acrescentaria uma classificação de recuperabilidade da aplicação, quando houver evidência, sem criar outro subsistema de persistência.

### 4.3. Learning Mode: encontrei um risco mais específico

Em `startLearning()`, linhas 2175-2217, o Hermes seleciona uma aba pelo `tabId`, mas chama `takeControl()` utilizando o `ownerTaskId` da aba.

Quando a aba solicitada ainda não possui `ownerTaskId`, `takeControl()` pode resolver a autoridade usando a aba ativa, e não necessariamente a aba solicitada.

Isso sugere uma possível inconsistência quando o Learning Mode é iniciado numa aba diferente da ativa. **É uma hipótese de falha derivada do fluxo do código, ainda não uma exploração reproduzida.**

O teste correto é iniciar Learning em uma aba não ativa, verificar o lease exato e tentar uma operação concorrente nas duas abas. A correção deve preservar a sessão compartilhada quando ela é necessária para observar os logins e o comportamento real do usuário.

Separar automaticamente todos os perfis poderia prejudicar a própria finalidade do Learning Mode.

---

## 5\. Comparação técnica com o BrowserOS-agent

Também conferi diretamente os módulos do [BrowserOS-agent](https://github.com/browseros-ai/BrowserOS-agent?utm_source=chatgpt.com)\.

### O que realmente vale aproveitar

| Recurso | Evidência do BrowserOS | Aplicação no Hermes |
|--------|--------|--------|
| API semântica `nav/act/extract/verify` | Implementada no SDK | Fachada opcional sobre resolvedor, TaskCompiler e executor existentes |
| Verificação automática | `act.ts` possui `verify` e `maxRetries` | Adotar somente retries seguros e condicionados |
| Schema de extração | `extract.ts` envia JSON Schema | Acrescentar validação de dados à projeção existente |
| SSE | `act.ts` consome stream de etapas | Reaproveitar infraestrutura de eventos antes de criar transporte novo |
| Erros tipados | `errors.ts` possui subclasses | Mapear códigos existentes, sem duplicação |

Duas observações mudam a comparação.

**Primeira\:** o `act()` do BrowserOS realmente pode repetir a instrução após falha de verificação. Isso é útil para ações reversíveis, mas pode ser perigoso para uma mutação que já ocorreu remotamente e cujo readback falhou. A implementação do Hermes é mais conservadora ao classificar essa situação como incerta.

**Segunda\:** o `extract.ts` envia um JSON Schema ao servidor, mas o próprio SDK não demonstra uma segunda validação local do resultado retornado. Portanto, não se deve assumir conformidade garantida sem auditar também o serviço servidor.

### Um detalhe essencial de licenciamento

O BrowserOS-agent utiliza **AGPL-3.0**, enquanto o Hermes mantém licença MIT. O próprio `workstation/THIRD_PARTY_NOTICES.md` determina que BrowserOS seja usado como referência, sem incorporar seu código-fonte.

Recomendo implementar os padrões equivalentes de forma independente, preservando essa fronteira de licenciamento. Não copiaria os módulos TypeScript diretamente.

## 6\. Descobertas adicionais

Além das lacunas levantadas nas análises, identifiquei três pontos merecedores de atenção\:

**A. A prova de lote é mais restrita que a semântica das operações.** `hasVerifiedBatchEffect()` comprova mudanças locais específicas. Para ações como clique em Salvar, envio ou publicação, é necessário um readback específico do destino. Isso é particularmente relevante para evitar que o Hermes relate sucesso com base em um ACK local.

**B. A validação de caminhos no bridge merece correção.** Em `workstation/browser_bridge.py`, `_validate_safe_destination()` utiliza comparação textual por prefixo com `startswith`\. Caminhos irmãos com prefixos semelhantes podem passar nessa comparação. Se o helper receber raízes permitidas, a verificação deve utilizar pertencimento real ao diretório, por exemplo `Path.is_relative_to()`, incluindo teste negativo. A utilização desse caminho no fluxo normal ainda precisa ser comprovada antes de classificar a exposição como explorável.

**C. Algumas conclusões documentais ficaram defasadas após merges.** O PR \#85 é um exemplo concreto. Os próximos relatórios precisam identificar separadamente `implementation_status`, `test_evidence`, `release_qualification` e o commit auditado.

---

## 7\. Plano recomendado - priorização 80/20

Não recomendo começar pelos quatro recursos novos sugeridos no anexo. A prioridade deve ser concluir um ciclo real com o que já existe.

## P0

**Qualificação transacional nativa**

Provar `PREPARE → INTERACT → COMMIT → VERIFY` numa aplicação real ou fixture representativa, incluindo perda de resposta, restart, lease revogado, conflito e readback persistido.

Critério: não duplicar mutações; não declarar sucesso sem prova externa; resolver ou documentar a falha da CI exact-head.

---

## P1

**Fachada semântica enxuta**

Aproveitar `OperationIntent`, TaskCompiler e `browser_batch_actions`\. Expor operações de alto nível para tarefas conhecidas sem adicionar outro loop genérico de agente.

Critério: executar uma rotina conhecida com menos coordenação pelo modelo e verificação preservada.

---

## P1

**Extração estruturada**

Adicionar schema opcional à projeção de extrações, mantendo ArtifactStore, referências e os formatos legados.

Critério: dados conformes ou erro explícito, sem carregar extrações extensas no contexto do LLM.

---

## P1

**Correções pontuais de isolamento e recuperação**

Testar a identidade do lease ao iniciar Learning, avisar sobre conteúdo potencialmente perdido e corrigir a validação de caminhos do bridge.

Critério: testes negativos reproduzíveis e regressões verdes.

---

## P2

**Progresso e observabilidade incremental**

Mostrar eventos existentes no frontend, medir durações por etapa e adicionar streaming dedicado apenas se houver um gargalo demonstrado.

Critério: progresso visível e custo/latência mensurados, sem segundo event bus.

### O que eu não faria agora

Eu adiaria a introdução de um executor livre de linguagem natural dentro do controller, a criação de uma nova hierarquia de erros, a reescrita do transporte para SSE e a construção de quatro BrowserRuntime completos.

Também descartaria os percentuais de economia de tokens e latência apresentados no anexo como resultados comprovados. São hipóteses, não benchmarks. A métrica que interessa é o **custo e o tempo até um efeito realmente verificado**, incluindo chamadas ao modelo, readbacks e possíveis reexecuções.

## 8\. Conclusão

A primeira análise acerta ao pedir prova E2E, mas exagera alguns riscos arquiteturais. A segunda encontra padrões úteis no BrowserOS, porém subestima mecanismos que já existem no Hermes e apresenta um `browser_act()` conceitual que não pode ser conectado diretamente a `browser_batch_actions` sem transformar instruções em etapas tipadas e respeitar os contratos de autorização.

Minha prioridade é **consolidar o executor atual, não criar outro**\.

O Hermes já reúne peças importantes: Chromium nativo, identidade de BrowserTask, authority fencing, lotes, receipts, readiness, projeções duráveis e infraestrutura de aprendizado. O próximo ganho substantivo virá de demonstrar que essas peças funcionam juntas, principalmente depois de efeitos externos incertos, e então reutilizar os procedimentos com menos dependência do modelo.

O resultado desejado é simples de definir: o Hermes recebe uma tarefa conhecida, reconhece o procedimento, executa na sessão correta, comprova o resultado e reutiliza essa experiência - sem perder a capacidade de interromper, reconciliar e devolver controle ao usuário quando necessário.

**Esse é o próximo avanço que justifica investimento antes de ampliar a arquitetura do browser.**

## Prompt:
18/10/2026, 18:54:28

Faça o mesmo com essas 4 análises críticas

[Attachment: Texto colado(20261018-215403).txt]

[Attachment: Texto colado (2)(20261018-215411).txt]

[Attachment: Texto colado (3)(3).txt]

[Attachment: Texto colado (4)(2).txt]

## Response:
18/10/2026, 18:54:35 · gpt-6-thinking

Vou auditar as quatro análises contra o código atual do Hermes Work no GitHub e conferir também os projetos de referência: BrowserTrace, Hermes Browser Extension, Lattice e Stagehand. Vou identificar o que já existe, o que foi atribuído incorretamente ao Hermes, quais melhorias realmente agregam valor e como consolidá-las sem criar subsistemas redundantes.

O principal achado até aqui é que duas análises estão substancialmente desatualizadas: o Hermes já usa deltas de snapshot e cache com invalidação por revisão do DOM, e o Stagehand foi comparado com uma versão do Hermes supostamente sem batch. Também confirmei um erro importante na análise da extensão: a configuração somente-leitura se refere ao companion plugin, não necessariamente a toda a extensão, que possui um fluxo próprio de controller.

> **Auditando análises e correção do código-fonte**
>
>
> **Auditou análises e corrigiu o código-fonte**
>
> 
>
> **Auditando prioridades críticas**
>
> Estou verificando o código real para separar riscos confirmados de afirmações exageradas. Vou priorizar isolamento de perfis, privacidade de capturas, cache, comparação de etapas e integração incremental, evitando propor subsistemas novos sem evidências.
>
> **Auditou prioridades críticas**
>
> 
>
> **Auditou repositórios, telemetria, snapshots, extensões, licenças e integração Hermes-Lattice**
>
> 
>
> **Refinando evidências e prioridades**
>
> Estou distinguindo ganhos comprovados de promessas condicionais: cache, roteamento, isolamento e hashing precisam de testes específicos. Vou propor fases enxutas, começando por privacidade, orçamento de contexto, estabilidade das referências e redução de ruído.
>
> **Refinou evidências e prioridades**
>
> 
>
> **Auditou roteamento, arquitetura, interface desktop, automação, custos e problemas conhecidos**
>
> 
>
> **Pesquisou 1 site**
>
> 
>
> **Separando evidências confirmadas**
>
> Minha leitura indica que várias críticas são exageradas: há rastreamento, visão, redaction, cache e isolamento parcial. As prioridades reais são fechar lacunas de privacidade, medir custos e conectar recursos existentes sem duplicar a arquitetura.
>
> **Separou evidências confirmadas**
>
> 
>
> **Consolidando o plano**
>
> Estou concluindo uma auditoria estática: o maior ganho não está em adotar tudo, mas em conectar recursos maduros, corrigir alegações imprecisas e medir privacidade, custo, estabilidade e confiabilidade antes de expandir a arquitetura.
>
> **Inspecionou locadores, privacidade, ferramentas e riscos do BrowserTrace**
>
> 
>
> Pensou por 7m 55s

# Auditoria comparativa - 4 análises críticas do Hermes Work

18 de outubro de 2026 · GitHub conectado · Branch `main` · Commit `f436e949`

As quatro análises abordam componentes complementares do browser: **BrowserTrace** $observabilidade), **Hermes Browser Extension** \(captura e interação), **Lattice** \(representação de interface) e **Stagehand** \(automação orientada por IA).

A leitura dos arquivos e do código atual revela uma diferença importante entre a arquitetura proposta pelas análises e o estágio real de desenvolvimento do Hermes Work.

**Parte significativa das melhorias recomendadas já foi implementada**, especialmente em otimização de snapshots, execução em lote, cache de extrações, classificação de erros e proteção de dados. Algumas análises utilizam informações desatualizadas; outras atribuem ao Hermes recursos que pertencem apenas à extensão externa.

O maior risco seria transformar as quatro análises em quatro projetos de implementação independentes, duplicando mecanismos e aumentando a complexidade do Hermes sem entregar ganhos proporcionais.

## 1\. Diagnóstico consolidado

| Área | O que as análises afirmam faltar | O que encontrei na `main` |
|--------|--------|--------|
| Comparação de snapshots | Sem delta entre observações | `workstation-browser-snapshot-diff.ts` já implementa deltas textuais |
| Cache de extrações | Cada leitura reprocessa tudo | `BoundedExtractCache` já existe, com TTL e escopo |
| Batch de ações | Uma chamada por operação | `browser_batch_actions` já executa sequências |
| Redação de dados sensíveis | Ausente no browser nativo | Há redação no gateway e sanitização parcial no Electron |
| Orçamento de snapshots | Apenas AX/HTML bruto ilimitado | Existem limites de texto, elementos e projeção compacta |
| Schema em extrações | Completamente ausente | Existe filtragem por propriedades, mas não validação integral de JSON Schema |
| Replay visual de falhas | Não disponível como ferramenta equivalente | Lacuna relevante, a confrontar com os mecanismos existentes de evidência e replay |
| Grafo multimodal DOM+AX+layout | Não existe equivalente completo | Oportunidade real, mas não é necessariamente prioritária |
| Self-healing semântico | Sem equivalente genérico | Oportunidade de melhorar resolução de elementos, preservando os controles existentes |
| WebMCP da própria página | Não identificado no controller | Possível extensão futura, dependente de demanda concreta |

As constatações mais importantes aparecem em\:

- [workstation-browser-snapshot-diff.ts](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/main/apps/desktop/electron/workstation-browser-snapshot-diff.ts?utm_source=chatgpt.com)
- [workstation-browser-extract-cache.ts](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/main/apps/desktop/electron/workstation-browser-extract-cache.ts?utm_source=chatgpt.com)
- [workstation-browser-batch.ts](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/main/apps/desktop/electron/workstation-browser-batch.ts?utm_source=chatgpt.com)
- [tools/browser\_workstation.py](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/main/tools/browser_workstation.py?utm_source=chatgpt.com)

A análise correta deve, portanto, priorizar a integração e o aproveitamento dessas implementações, não apenas comparar listas de funcionalidades.

---

## 2\. Auditoria da análise 1 - BrowserTrace

[images: BrowserTrace browser agent debugger UI timeline screenshot tracing aaronlab github]

**BrowserTrace**

[Código-fonte](https://github.com/aaronlab/browsertrace?utm_source=chatgpt.com) · Licença MIT

(Aproveitamento alto)

### O que a análise acerta

BrowserTrace oferece uma experiência de depuração que o Hermes ainda não demonstra de forma equivalente e integrada: uma linha do tempo que reúne ações, resultados, screenshots e decisões do agente.

Também confirmei que `compare_runs()` identifica a primeira divergência entre duas execuções e que existe exportação HTML com opções de remoção de conteúdo privado. \[[GitHub - aaronlab/browsertrace: Local replay debugger for Browser Use failures with screenshots, model I/O, failed-step timelines, and public-safe HTML exports.](https://github.com/aaronlab/browsertrace?utm_source=chatgpt.com)\]

### Onde a análise está incorreta

**O Hermes já possui uma estrutura de traces e replay.**

Em [workstation/replay.py](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/main/workstation/replay.py?utm_source=chatgpt.com) encontrei\:

- `PortableTrace`\: representação portável de eventos de execução.
- `PortableTraceBuilder.from_journal()`\: criação de trace a partir do journal.
- `PortableTrace.fork_at()`\: derivação de uma nova representação a partir de um ponto da execução.
- `ReplayEngine.replay()`\: reprodução de eventos para observadores, sem executar efeitos externos.

Isso não equivale a um replay visual completo, mas invalida a premissa de que precisamos criar a infraestrutura de tracing do zero.

Também existem `browser_vision` e capturas locais por `screenshotForEntry()` no Electron. O que falta é correlacionar esses artefatos automaticamente com a etapa exata de uma falha.

Outra conclusão incorreta é a de que a telemetria do Hermes necessariamente vai para analytics externo. `workstation/telemetry/emit.py` inicia com `NullTelemetrySink`; existe também um sink SQLite local.

### O que eu implementaria

**Uma extensão forense do ExecutionJournal existente**, com captura visual opcional nas falhas relevantes, referenciada pelo ArtifactStore.

Não criaria outro banco de traces.

A comparação de runs deveria utilizar `run_id`, `operation_id`, identidade da operação, fase e evidência, sempre que disponíveis. O `compare_runs()` original compara ações principalmente pela posição na sequência; uma única etapa inserida pode produzir uma divergência pouco informativa.

Eu também adiaria o diagnóstico automático por LLM. Primeiro implementaria uma síntese determinística dos erros existentes. Usar uma LLM para diagnosticar toda falha pode aumentar custo e latência, ao contrário dos percentuais de economia anunciados no anexo.

Prioridade: P1 para comparação de runs e evidência de falha; P2 para diagnóstico por LLM sob demanda.

## 3\. Auditoria da análise 2 - Hermes Browser Extension

[images: Hermes Browser Extension abundantbeing Chrome side panel browser agent interface]

**Hermes Browser Extension**

[Código-fonte](https://github.com/abundantbeing/hermes-browser-extension?utm_source=chatgpt.com) · Licença MIT

(Aproveitamento alto)

### Correção importante: a extensão não é apenas read-only

A análise consultou `companion-plugin/policy.py`, que realmente contém `BROWSER_CONTROL_ENABLED = False`\.

Mas esse arquivo se refere ao companion plugin, não a todas as capacidades da extensão.

A versão 0.3.0 passou a incluir controle de abas autorizado por leases, com ações como cliques, preenchimento de formulários, navegação, snapshots e operações CDP. \[[hermes-browser-extension/CHANGELOG.md at main · abundantbeing/hermes-browser-extension](https://github.com/abundantbeing/hermes-browser-extension/blob/main/CHANGELOG.md?utm_source=chatgpt.com); [hermes-browser-extension/DATA-FLOW.md at main · abundantbeing/hermes-browser-extension](https://github.com/abundantbeing/hermes-browser-extension/blob/main/DATA-FLOW.md?utm_source=chatgpt.com)\]

Portanto, a afirmação de que o Hermes executa ações enquanto a extensão apenas observa está desatualizada.

### O que já existe no browser nativo

A afirmação de ausência completa de redação de secrets também é incorreta.

O código atual possui `redact_sensitive_text()` na fronteira Python do controller, sanitização de chaves sensíveis em `workstation-browser-extract-cache.ts` e filtros de dados privados na telemetria.

Isso não equivale à cobertura integral da extensão. Sua implementação `content-extractor.js` possui tratamento adicional de tokens, assignments sensíveis, múltiplas camadas de URL encoding e heurísticas para remover conteúdo irrelevante.

É aqui que existe uma oportunidade técnica concreta.

### Duas melhorias que fazem sentido

**1\. Melhorar o contexto entregue à IA.** Incorporar uma estratégia de extração de conteúdo principal, removendo navegação, rodapés, publicidade e elementos repetitivos quando a tarefa for de leitura.

Isso deve ser opcional: uma operação sobre menus ou botões não pode perder justamente os elementos interativos que o filtro classificou como ruído.

**2\. Fortalecer a redação nas fronteiras existentes.** Ampliar o conjunto de padrões detectados, testar URL encoding e validar a proteção não somente no texto enviado ao modelo, mas também nos artefatos exportados e nos registros de depuração.

Não começaria criando um `browser_redaction.py` isolado se a implementação puder ser incorporada aos sanitizadores existentes.

### Element picker e indicador visual

Ambos são úteis para UX, mas com prioridades diferentes.

O Hermes já fornece referências `@eN`, semantic anchors e a interface Browser Task Rail, que informa estados de atividade e controle. Um **element picker iniciado pelo usuário** agregaria valor nos casos em que ele precisa apontar um elemento específico para ensinar ou corrigir o agente.

O indicador visual dentro da página também pode ajudar, mas não justifica copiar toda a infraestrutura de overlays da extensão. Uma indicação discreta na interface existente pode atender à maior parte da necessidade.

Prioridade: P1 para qualidade e proteção do contexto; P2 para element picker; indicador in-page somente se o fluxo real demonstrar necessidade.

## 4\. Auditoria da análise 3 - Lattice

**Lattice** · [Código-fonte](https://github.com/apatureai/lattice?utm_source=chatgpt.com) · Licença MIT

Esta é provavelmente a análise com maior potencial de melhoria na percepção e na economia de contexto do Hermes. Também é a que oferece **maior risco de over-engineering**\.

### A premissa de ausência de deltas está errada

O Hermes já possui `diffSnapshot()` e `applySnapshotDelta()` no Electron.

A implementação atual compara snapshots consecutivos por linhas, exige identidade compatível de tarefa/aba/URL, verifica a revisão, recusa baselines inadequadas e somente utiliza o delta quando há economia suficiente.

O fluxo está conectado ao `snapshotForEntry()` no `workstation-browser-runtime.ts`, aproximadamente nas linhas 3840-3888. Não é um módulo isolado sem integração.

O que o Lattice oferece de adicional é um **delta estrutural entre grafos de interface**, com integridade baseada em hashes. Isso é mais sofisticado, mas não significa que o Hermes precise substituir imediatamente seus deltas textuais.

### A economia de 76-99% exige interpretação

O Lattice publicou medições de redução do conteúdo enviado ao modelo. No exemplo do Hacker News, `actionMap` reduziu uma captura estruturada de 745.445 bytes para 53.942 bytes, equivalente a 92,8%. \[[GitHub - apatureai/lattice: Deterministic scene graph for browser agents: fuses DOM, accessibility, style and text capture into one content-addressed snapshot, then renders small budgeted views for a model prompt. When sources disagree, both claims are kept and flagged.](https://github.com/apatureai/lattice?utm_source=chatgpt.com)\]

Porém, a comparação é com a captura bruta e detalhada do próprio Lattice.

O Hermes já utiliza limites de aproximadamente 8.000 caracteres de texto e 120 elementos no snapshot compacto, chegando a 24.000 caracteres e 400 elementos no modo completo.

Portanto, **não é possível aplicar automaticamente o ganho de 92,8% ao Hermes**\. Para demonstrar economia real, precisamos medir os mesmos sites e tarefas nas duas representações, contabilizando os tokens efetivamente enviados ao modelo.

### O que vale incorporar

O Lattice introduz três ideias particularmente relevantes\:

| Recurso | Estado do Hermes | Minha decisão |
|--------|--------|--------|
| Views `actionMap`, `focus` e `summary` | Snapshot compacto e completo, sem equivalentes integrais | **Priorizar** |
| Grafo fundido DOM + AX + layout | Inventário AX/DOM, sem fusão completa com proveniência por fato | Adiar |
| Identidade SHA-256 de snapshots | Revisão, identidade da aba e delta validado; sem sealing equivalente | Adicionar somente se necessário |
| Delta estrutural verificado | Delta textual já implementado | Evoluir, não substituir |
| Stability probe | Readiness e verificações de SPA existentes | Integrar seletivamente |

A oportunidade de maior retorno está em **criar diferentes projeções do mesmo snapshot para finalidades distintas**\.

Por exemplo, numa tarefa que envolve localizar um botão, o Hermes pode enviar apenas elementos interativos, rótulos e referências. Para ler uma notícia, pode priorizar o conteúdo principal. Para editar um formulário, pode apresentar campos, rótulos, valores sanitizados e identificadores.

Tudo isso pode ser desenvolvido inicialmente em cima do inventário existente, sem introduzir um grafo completo.

Há ainda uma ressalva: um hash de conteúdo não substitui o controle de autoridade ou a validação de atualidade da página. Um snapshot idêntico não autoriza executar uma ação numa sessão diferente.

**Veredito\:** aproveitar o modelo de views orientadas à tarefa; não absorver o pipeline integral de grafos na primeira implementação.

## 5\. Auditoria da análise 4 - Stagehand

**Stagehand** · [Código-fonte](https://github.com/browserbase/stagehand?utm_source=chatgpt.com) · Licença MIT

O Stagehand tem duas vantagens reais para o Hermes: uma API semântica bem definida e mecanismos de resolução de elementos mais convenientes para tarefas formuladas em linguagem natural.

Entretanto, a análise exagera algumas deficiências do Hermes.

### Cinco correções importantes

| Afirmação da análise | Resultado da auditoria |
|--------|--------|
| Hermes não possui batch | Incorreto. `browser_batch_actions` já existe |
| Hermes não possui cache | Incorreto. Existe cache de extração com TTL, fingerprint e revisão de DOM |
| Hermes não tem redução de snapshots | Incorreto. Existem limites, projeção compacta e delta |
| Hermes possui BCP v2 nativo com consume-on-read | Atribuição incorreta. Essa implementação foi examinada na extensão e no companion plugin |
| Hermes utiliza necessariamente um único modelo caro para toda ação | Generalização incorreta. O projeto já possui resolução determinística, System-1/LAYA e caminhos de reutilização operacional |

A análise também elogia isolamento explícito de perfis por operação. O Workstation utiliza uma sessão Chromium persistente dedicada (`session.fromPath()`$, separada do perfil padrão do Desktop, mas isso não significa criar um perfil isolado para cada ação.

### O que o Stagehand realmente faz melhor

O método `act()` recebe uma instrução semântica. `observe()` identifica possibilidades de interação e `extract()` aceita schemas Zod. Confirmei que `stagehand.ts` converte o schema para JSON Schema e posteriormente executa `resolvedSchema.parse(response.data)`, realizando validação efetiva do resultado no lado do SDK.

O Hermes possui sanitização e filtragem por propriedades de schema, mas não encontrei equivalência integral dessa validação no transporte nativo examinado.

Outro diferencial é o `Locator`, que encapsula referências a elementos e suporta operações reutilizáveis. O Hermes já resolve referências `@eN` e utiliza semantic anchors; o próximo ganho seria melhorar a capacidade de reencontrar um alvo quando o DOM muda.

### Três recomendações que eu corrigiria

**1\. Não portar o `experimentalBatch()` diretamente.**

O Stagehand serializa callbacks JavaScript para execução remota, uma capacidade flexível, mas que exige um modelo de segurança apropriado.

O Hermes tem um executor de lotes tipados, com autoridade revalidada a cada etapa. Isso é mais compatível com seus contratos atuais. Eu aproveitaria apenas padrões úteis, como deadlines e tratamento explícito de operações cujo resultado permanece incerto.

**2\. Não implementar outro mecanismo autônomo de model routing no controller.**

A seleção de modelos deve continuar integrada ao System-1, ao CapabilityRouter e ao fluxo de execução existente. Uma ação simples e conhecida deve preferencialmente ser determinística, sem gastar sequer uma chamada de modelo.

**3\. Não registrar automaticamente ferramentas WebMCP como autoridades confiáveis.**

A descoberta de ferramentas expostas pelas próprias páginas é interessante, mas essas declarações são conteúdo originado de terceiros. Se adotadas, deverão passar pelo registry, pela política de efeitos, por autorização contextual e pelos mesmos mecanismos de verificação utilizados pelas demais ferramentas.

### Principal oportunidade

Eu aproveitaria o padrão de **self-healing de localizadores**, mas de uma forma restrita\:

**Ação com alvo semântico conhecido**

Ex.: localizar campo por `data-testid` e nome acessível

**Validar identidade e readiness**

BrowserTask, aba, documento, escopo e lease

**Resolver referência atual**

Em caso de DOM drift, reobservar antes da mutação

**Executar, verificar e registrar**

Sem retry cego quando o efeito puder ter ocorrido

O objetivo não é fazer a IA tentar indefinidamente até conseguir. É permitir que o Hermes recupere deterministicamente uma referência obsoleta **antes de produzir um novo efeito**, sempre que houver evidência suficiente de que o alvo permanece o mesmo.

**Veredito\:** aproveitar self-healing restrito, validação de schemas e desenho de locators. Adiar WebMCP e não duplicar o executor de batch.

---

## 6\. Síntese das quatro análises

Minha classificação considera a utilidade incremental para o Hermes atual, não a qualidade absoluta de cada projeto.

| Referência | Maior contribuição | Aproveitamento recomendado |
|--------|--------|--------|
| Hermes Browser Extension | Contexto limpo, sanitização, seleção de elementos | Alto |
| Lattice | Observação orientada à tarefa e compactação | Alto, sem grafo integral |
| Stagehand | Localizadores resilientes e extração tipada | Alto, em escopo restrito |
| BrowserTrace | Diagnóstico visual e comparação de execuções | Médio-alto |

Há uma convergência interessante: a extensão prepara melhor o conteúdo, o Lattice escolhe melhor o que apresentar, o Stagehand facilita a ação e o BrowserTrace ajuda a compreender a falha.

**Essas quatro capacidades devem alimentar um único ciclo de operação do Hermes, não quatro sistemas independentes.**

## 7\. Arquitetura de integração recomendada

**TaskCompiler / OperationIntent / System-1**

Reconhece o objetivo e seleciona capacidades existentes

**BrowserTask + Controller Electron**

Responsável pela identidade, estado, sessão e autoridade

**Observação contextual**

Extension + Lattice

Sanitização, foco, seleção do conteúdo e orçamento

**Resolução de ações**

Stagehand

Localizadores, validação, batch e recuperação de referências

**Verificador / ExecutionJournal / ArtifactStore**

Comprovação do resultado, persistência e tratamento de incerteza

**Diagnóstico + Experience Compiler**

BrowserTrace como inspiração para análise de falhas; experiências comprovadas alimentam a reutilização

O ponto mais importante desse desenho é que observação, resolução de alvos e diagnóstico são **capacidades subordinadas ao executor existente**\. Nenhuma delas ganha permissão para realizar mutações por conta própria.

## 8\. Plano 80/20 de implementação

Eu concentraria o trabalho em três entregas principais, seguidas por uma etapa opcional de expansão.

## P0

**Estabilizar observação e qualificação**

Antes de ampliar a arquitetura, confirmar a segurança do caminho de sanitização, reproduzir os cenários reais de automação e fechar ou diagnosticar a falha de CI do commit auditado.

Componentes: Electron, `browser_workstation.py`, telemetria, testes de autoridade e readback.

---

## P1

**Contexto inteligente e econômico**

Combinar extração de conteúdo principal, views `actionMap`/`focus`, orçamento configurável e validação real de schema no pipeline existente.

Arquivos principais: `workstation-browser-snapshot.ts`, `workstation-browser-runtime.ts`, `workstation-browser-extract-cache.ts`, `browser_projection.py`\.

Resultado esperado: menos conteúdo irrelevante e menos chamadas de interpretação, sem sacrificar elementos necessários à tarefa.

---

## P1

**Localizadores resilientes e extração tipada**

Reaproveitar semantic anchors, implementar reaquisição segura de alvos quando houver DOM drift e manter o executor de ações em lote existente.

Arquivos principais: `workstation-browser-runtime.ts`, `workstation-browser-batch.ts`, `browser_readiness.py`, `browser_transaction.py`\.

Resultado esperado: menor necessidade de intervenção do modelo em alterações simples de páginas, sem repetir efeitos incertos.

---

## P2

**Diagnóstico forense integrado**

Ampliar `PortableTrace` e o journal para comparação de runs e associação opcional de screenshots a falhas, utilizando o ArtifactStore.

Arquivos principais: `workstation/replay.py`, `workstation/journal.py`, `workstation/telemetry/browser_observation.py`, Browser Task Journal Drawer.

Resultado esperado: identificar em qual operação a execução divergiu e apresentar evidência útil para correção humana ou investigação supervisionada.

Deixaria a construção de grafos completos do Lattice, WebMCP, SDK multilíngue, exportador HTML avançado e diagnóstico automático por LLM para um momento posterior. São evoluções defensáveis, mas não são pré-requisitos das três entregas anteriores.

### Como medir o resultado

A qualificação deve comparar baseline e implementação na mesma tarefa, ambiente e nível de segurança.

| Indicador | Critério |
|--------|--------|
| Tokens efetivos por tarefa | Redução medida, não estimativa de caracteres |
| Tempo até resultado verificado | Mediana e p95, incluindo espera e readback |
| Sucesso operacional | Efeito externo comprovado, não somente ACK |
| Recuperação de DOM drift | Referência recuperada corretamente, sem clicar no alvo errado |
| Duplicação de mutações | Zero nos cenários de recuperação ensaiados |
| Privacidade | Nenhuma credencial ou valor sensível conhecido nos artefatos e saídas testadas |
| Regressão | Testes existentes e CI no commit exato da implementação |

## 9\. Conclusão

As quatro análises oferecem referências valiosas, mas não justificam quatro integrações grandes.

O Hermes já possui a maioria dos componentes fundamentais. A maior oportunidade não é adquirir mais ferramentas: é **aumentar a qualidade das observações que chegam ao agente e reduzir o raciocínio necessário para transformar essas observações em ações verificadas**\.

Para o objetivo de automação progressiva do Hermes, a sequência mais eficiente é\:

**Observar melhor → localizar com mais confiabilidade → executar com a infraestrutura existente → verificar → diagnosticar → reutilizar.**

Isso também favorece o Experience Compiler. Uma experiência com alvos semânticos estáveis, observações compactas e pós-condições verificáveis é muito mais reutilizável do que uma sequência de cliques baseada em posições ou seletores frágeis.

A recomendação final é iniciar pela **P1 de contexto inteligente e economia de observação**, preservando a qualificação P0 como condição de segurança, e seguir para localizadores resilientes. Só depois investiria mais profundamente em tracing visual ou grafos multimodais.

Esta auditoria foi baseada na leitura estática dos arquivos disponíveis no GitHub e na conferência dos projetos originais. Não executei testes novos nem alterei o repositório; portanto, as oportunidades identificadas são recomendações de engenharia fundamentadas no código, não resultados de benchmarks ou validação E2E recém-executada.

## Prompt:
18/10/2026, 19:15:53

De acordo com os anexos, faça o seguinte:

Atualize no repositório o roadmap.md, o jornal de engenharia, o hermes work inteligence e qualquer outro documento necessário com essas visões, descobertas e decisões que fizemos aqui. 
Agora cria um prompt para eu mandar para a IA que vai realizar essas implementações/ajustes e ela realizar esses pontos de melhoria que identificamos. Me vê um prompt para eu mandar e a IA resolver tudo isso. Cria um prompt que permita que a IA não precise pensar muito nem ficar lendo nada, que ele saiba de imediato o que ele tem que fazer, quando tem fazer, em que ordem e em que local. Para isso, leia todo o necessário direto no @GitHub  
De preferência, já crie o código que será utilizado nas implementações e correções, e já diga onde esse código será colocado ou qual parte do código esse novo código substitui, faça para que seja o máximo "plug and play" possível para que a IA implementadora pegue o seu código e já coloque nos lugares certos sendo necessário o minimo de adaptações ou ajustes para melhorar a integração.

Mas o prompt deve dar liberdade para a IA implementadora avaliar o código sugerido e melhorar ele ou adaptar conforme a necessidade, pedindo para a IA implementadora uma posição crítica e analítica para com sua sugestões (não tardando em aceitar caso a sua sugestão realmente for a melhor, mas não hesitando em adaptar ou ajustar caso ela encontre uma opção ainda melhor), e também uma posição de implementadora, ou seja, de realmente trabalhar as mudanças no código fonte do Hermes Work / Agent afim de evoluir na direção proposta.

[Attachment: Texto colado(20261018-221150).txt]

[Attachment: Texto colado (2)(20261018-221208).txt]

## Response:
18/10/2026, 19:15:59 · gpt-6-thinking

Vou usar os dois anexos como base de decisão, conferir o HEAD atual e os contratos no GitHub, atualizar a documentação canônica em uma branch de trabalho e entregar um prompt de implementação com caminhos, ordem de execução, testes e código-base. Vou manter separados o que já está implementado, o que ainda depende de qualificação e o que deve ficar fora do escopo 80/20.

A auditoria confirmou o alvo principal: a documentação precisa registrar uma decisão de consolidação, não de substituição do browser. Já criei a branch `docs/browser-observation-80-20-20261018`\. Vou registrar o plano no roadmap, nas decisões, no jornal e na inteligência do Hermes, além de corrigir o status histórico da Browser Automation V1 sem alterar seus resultados experimentais.

O plano canônico já está no repositório, com gates independentes e arquivos-alvo identificados. Agora estou fechando o handoff operacional: instruções para a IA implementadora fazer alterações reais, propostas de patches onde o contrato foi confirmado, testes negativos obrigatórios e liberdade explícita para substituir minhas sugestões quando o código atual oferecer uma solução superior.

> **Inspecionando arquivos anexados para atualizar documentação**
>
>
> **Inspecionou arquivos anexados para atualizar documentação**
>
> 
>
> **Atualizando a documentação**
>
> Vou ajustar os documentos sem reescrever o histórico: registrar o estado atual, corrigir a referência ao pull request já integrado e preparar um guia técnico com interfaces, validações, testes e exemplos de implementação plugável.
>
> **Atualizou a documentação**
>
> 
>
> **Planejando atualizações documentais**
>
> Estou organizando mudanças sequenciais em vários documentos para evitar conflitos. Vou registrar o estado atual com precisão, criar uma decisão estratégica, atualizar pendências e preparar um plano técnico executável para a implementação.
>
> **Planejou atualizações documentais**
>
> 
>
> **Atualizou documentação, decisões e prompts de implementação do HERMES**
>
> 
>
> **Refinando a implementação**
>
> Estou definindo uma orientação para páginas longas, extração segura de conteúdo principal, validação de esquema, proteção de caminhos e comparação determinística de rastros. Vou manter a proposta compatível com o código existente e exigir testes antes da integração.
>
> **Refinou a implementação**
>
> 
>
> **Atualizada documentação, arquitetura, segurança e planos de validação do Browser Ecosystem**
>
> 
>
> **Preparando o prompt final**
>
> Estou consolidando um prompt autocontido para a IA implementadora, com prioridades, arquivos-alvo, contratos, snippets, critérios de aceite e exigência de testes. Também vou deixar claro que a documentação foi atualizada, mas o código ainda não foi alterado.
>
> **Preparou o prompt final**
>
> 
>
> **Preparado prompt completo e PR rascunho para refinamento do Hermes**
>
> 
>
> Pensou por 11m 44s

# Hermes Work - Plano de implementação D-049

(Documentação atualizada no GitHub)

Criei a branch [github.com](https://github.com/kevynlucasprofissional-stack/hermes-agent/tree/docs/browser-observation-80-20-20261018?utm_source=chatgpt.com) e registrei a nova diretriz **D-049 - Browser 80/20: uma cadeia de observação, execução e evidência**\.

As alterações já foram gravadas em sete documentos do repositório, incluindo os três principais solicitados\:

- [github.com](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/docs/browser-observation-80-20-20261018/workstation/ROADMAP.md?utm_source=chatgpt.com)
- [github.com](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/docs/browser-observation-80-20-20261018/workstation/context/engineering-journal/CURRENT.md?utm_source=chatgpt.com)
- [github.com](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/docs/browser-observation-80-20-20261018/workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md?utm_source=chatgpt.com)
- `DECISIONS.md`, `CURRENT_STATE.md`, `KNOWN_ISSUES.md` e `browser-automation-v1/STATE.md`\.

Também corrigi a interpretação documental do PR \#85: ele foi incorporado à `main`, mas suas provas experimentais **não equivalem à qualificação da automação para produção**\.

A decisão arquitetural é preservar os mecanismos existentes e concentrar as melhorias em quatro frentes: qualificação transacional, percepção econômica, resolução segura de elementos e diagnóstico forense.

**As alterações realizadas até aqui são documentais.** Não modifiquei o runtime nem declarei testes que não foram executados.

**[PR \#105 - D-049 Browser 80/20](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/105)** (Draft)

A documentação foi consolidada em um PR com **9 arquivos alterados, 10 commits e nenhuma alteração de runtime**\.

Também criei dois documentos novos que concentram o trabalho\:

**[Plano D-049 — arquitetura, prioridades e critérios de aceitação](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/docs/browser-observation-80-20-20261018/workstation/context/BROWSER_REFINEMENT_2026-10-18.md?utm_source=chatgpt.com)**

Inventário das capacidades existentes, dependências, quatro etapas de implementação e condições de qualificação.

---

**[Handoff completo — 184 linhas](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/docs/browser-observation-80-20-20261018/workstation/context/BROWSER_REFINEMENT_IMPLEMENTER_PROMPT_2026-10-18.md?utm_source=chatgpt.com)**

Prompt detalhado com funções, arquivos de destino, código candidato em Python e TypeScript, testes negativos, metodologia RED/GREEN e critérios de conclusão.

## Prompt para a IA implementadora

A versão abaixo é operacional e pode ser encaminhada diretamente. O handoff completo no GitHub contém os snippets adicionais e as instruções mais granulares de integração.

**document: **

# Implementação D-049 - Hermes Work Browser 80/20

## MISSÃO

Você é a IA engenheira responsável por implementar melhorias reais no código-fonte do Hermes Work/Agent, no repositório:

`kevynlucasprofissional-stack/hermes-agent`

**Sua tarefa não é elaborar outro plano. É executar as implementações, corrigir problemas, escrever testes, verificar os resultados, atualizar a documentação e preparar um PR.**

O projeto já tem uma arquitetura relativamente madura. Seu trabalho é aproveitá-la, fechar lacunas comprovadas e produzir melhorias funcionais sem adicionar complexidade desnecessária.

### Fontes canônicas

Branch com as decisões atualizadas:

`docs/browser-observation-80-20-20261018`

Leia prioritariamente:

- `workstation/context/BROWSER_REFINEMENT_2026-10-18.md`
- `workstation/context/BROWSER_REFINEMENT_IMPLEMENTER_PROMPT_2026-10-18.md`
- `workstation/context/DECISIONS.md` - D-049
- `workstation/ROADMAP.md`
- `workstation/context/CURRENT_STATE.md`

O handoff D-049 contém código candidato e mapeamento detalhado dos pontos de inserção. **Não precisa fazer uma nova auditoria integral do repositório.** Verifique apenas o HEAD atual, os contratos indicados e os pontos em que as sugestões possam estar desatualizadas.

A auditoria original partiu da `main@f436e9496344d2c38e6611a88b42f0b7f18ce6df`.

## POSTURA TÉCNICA OBRIGATÓRIA

Atue simultaneamente como arquiteto crítico e implementador.

Não aceite automaticamente os patches sugeridos. Antes de cada implementação, verifique se existe um mecanismo mais simples, seguro, eficiente ou melhor integrado ao Hermes.

Se a sugestão estiver correta, implemente diretamente. Se houver uma alternativa melhor, utilize-a e explique objetivamente o motivo.

Não prolongue discussões arquiteturais quando houver informação suficiente para implementar.

Preserve as seguintes regras:

1. Não construir um segundo browser, controller, executor, SessionDB, Kanban, event bus, sistema de memória, tracer database ou roteador de modelos.
2. Não duplicar `BrowserTask`, `browser_batch_actions`, `BoundedExtractCache`, `diffSnapshot`, `ExecutionJournal`, `PortableTrace`, `ArtifactStore` nem o Experience Compiler.
3. Não autorizar mutações a partir de conteúdo de página, seletores ou classificação feita por LLM.
4. Não repetir uma ação com efeito externo quando sua execução anterior estiver incerta.
5. Não transformar ACK local ou mudança de DOM em prova de persistência externa.
6. Não alterar a interface padrão do browser sem compatibilidade ou migração explicitamente testada.
7. Não copiar código AGPL do BrowserOS para o projeto MIT.
8. Não considerar testes com mocks equivalentes à qualificação de produto.

**Prioridade de engenharia: 80/20.** Uma implementação simples, integrada e testada é preferível a uma arquitetura perfeita que atrasa a entrega.

## ETAPA B0 - Segurança e qualificação

### B0.1 - Corrigir path containment

Arquivo:

`workstation/browser_bridge.py`

A função `_validate_safe_destination()` utiliza atualmente comparação textual com `startswith()`, permitindo uma correspondência incorreta entre diretórios irmãos com prefixos semelhantes.

Código candidato para substituição:

```python
def _validate_safe_destination(
    dest_path: Path,
    allowed_roots: Optional[list[Path]] = None,
) -> Path:
    resolved = dest_path.resolve()

    if allowed_roots:
        roots = [Path(root).resolve() for root in allowed_roots]

        if not any(
            resolved == root or resolved.is_relative_to(root)
            for root in roots
        ):
            raise BridgeSecurityError(
                "Destination is outside permitted workspaces"
            )

    return resolved
```

Em `browser_save_json()`, substitua:

```python
dest = Path(destination_path)
_validate_safe_destination(dest, allowed_roots)
```

Por:

```python
dest = _validate_safe_destination(
    Path(destination_path),
    allowed_roots,
)
```

Verifique a necessidade de proteção adicional contra troca concorrente de symlinks. O patch acima não elimina por si só toda possibilidade de TOCTOU.

Escreva testes para diretório válido, diretório irmão prefixado, symlink externo, diretório inexistente e destino já existente.

### B0.2 - Corrigir escopo de Learning Mode

Arquivo:

`apps/desktop/electron/workstation-browser-runtime.ts`

Funções relevantes:

- `startLearning()`
- `takeControl()`
- `resolveControlTaskId()`
- `assertAgentControl()`

Existe a hipótese de que `startLearning(tabId)` obtenha um lease referente à aba ativa quando a aba solicitada não possui `ownerTaskId`.

Reproduza com duas abas, sendo A a ativa e B a aba selecionada para aprendizado.

Se a hipótese for confirmada, corrija o vínculo de autoridade para a aba efetivamente escolhida ou recuse a operação de forma fail-closed.

Não crie outro gerenciador de leases nem separe perfis Chromium indiscriminadamente.

### B0.3 - Qualificação transacional

Reutilize:

- `workstation/browser_transaction.py`
- `workstation/browser_readiness.py`
- `apps/desktop/electron/workstation-browser-batch.ts`
- `apps/desktop/electron/workstation-browser-batch-proof.ts`
- `workstation/context/browser-automation-v1/`

Teste a sequência:

`PREPARE → INTERACT → COMMIT → VERIFY`

Inclua interrupção após efeito externo, readback ausente, lease revogado, mudança de documento, conflito humano e retomada sem duplicação.

Investigue a falha do workflow `workstation-ci.yml`, execução `39154888493`, sem presumir que seja regressão do browser.

**Critério:** efeito externo somente é considerado verificado quando existe prova independente adequada ao contrato.

## ETAPA B1 - Percepção contextual econômica

Esta é a principal entrega de ganho funcional.

### B1.1 - Views de snapshot orientadas à tarefa

Arquivos existentes:

- `apps/desktop/electron/workstation-browser-snapshot.ts`
- `apps/desktop/electron/workstation-browser-snapshot-diff.ts`
- `apps/desktop/electron/workstation-browser-runtime.ts`
- `tools/browser_tool.py`
- `tools/browser_workstation.py`

Criar somente se não houver equivalente melhor:

`apps/desktop/electron/workstation-browser-snapshot-views.ts`

Implementar quatro views opcionais:

**`summary`** - resumo compacto de estado, título, contagens e avisos.

**`action_map`** - lista de elementos interativos com referências `@eN`, roles, labels e identificadores úteis.

**`focus`** - contexto restrito ao elemento solicitado, preservando sua referência e identidade.

**`content`** - leitura de conteúdo principal, preferindo `article`, `main` ou `[role=main]`, com fallback e sanitização.

Todas devem aceitar orçamento explícito, reportar truncamento e preservar compatibilidade com o comportamento padrão.

Utilize `PageInventoryResult` e `AXInventoryElement` existentes como base. Não crie um grafo multimodal completo do Lattice nesta etapa.

O handoff D-049 já contém uma implementação candidata de `renderSnapshotView()` em TypeScript para `action_map` e `focus`. Avalie e adapte esse código em vez de começar do zero.

No `workstation-browser-runtime.ts`, integre a projeção somente quando `browser_snapshot` receber um modo de view explícito.

Não altere silenciosamente a gramática de `formatInventory()` nem quebre `project_model_browser_payload()`, que depende da correspondência entre referências e texto.

### B1.2 - Sanitização e economia de contexto

Arquivos relevantes:

- `tools/browser_workstation.py`
- `workstation/telemetry/privacy.py`
- `apps/desktop/electron/workstation-browser-extract-cache.ts`
- `workstation/browser_projection.py`

Aproveite os sanitizadores existentes e amplie a cobertura para credenciais em texto, URL encoding, JWTs, bearer tokens e campos sensíveis.

Use o `content-extractor.js` do repositório `abundantbeing/hermes-browser-extension` como referência de comportamento, sem reproduzir a extensão inteira.

Teste especialmente as fronteiras entre:

`WebContentsView → Controller → Python Tool → Model`

e entre:

`Controller → ArtifactStore / Trace / Export`

Preserve dados que precisam ser armazenados legitimamente para a tarefa, aplicando escopo, autorização, retenção e proteção adequados. Não destrua dados operacionais por uma regra de redação excessivamente ampla.

Conteúdo proveniente de páginas deve permanecer classificado como não confiável.

### B1.3 - Extração validada por schema

Arquivos:

- `workstation-browser-extract-cache.ts`
- `workstation-browser-runtime.ts`, função `extractItemsForEntry()`
- `workstation/browser_projection.py`

A implementação atual possui filtragem por `schema.properties`, mas não valida integralmente `required`, `type`, `enum` e outros requisitos.

Acrescente validação real do schema solicitado.

Primeiro investigue se o repositório já dispõe de uma biblioteca apropriada. Se não, escolha entre uma dependência pequena e compatível ou um subconjunto explícito de JSON Schema que rejeite keywords não suportadas.

A validação deve acontecer antes de cachear ou declarar o resultado válido.

Mantenha separados:

- Captura bem-sucedida.
- Resultado conforme o schema.
- Persistência durável concluída.

Uma extração inválida não pode resultar em `success=True` apenas porque os campos foram filtrados.

Teste schemas válidos, obrigatórios ausentes, tipos errados, enums inválidos, schemas malformados e cache com schemas diferentes.

## ETAPA B2 - Localizadores resilientes

Referências:

- `workstation-browser-runtime.ts::resolvePoint`
- `workstation-browser-runtime.ts::clickRef`
- `workstation-browser-runtime.ts::typeRef`
- `workstation/browser_readiness.py`
- `workstation-browser-batch.ts`

Inspirar-se no Stagehand, mas não portar seu executor.

Objetivo: recuperar elementos cujo ref ficou obsoleto após alterações do DOM, sem reentrar na LLM quando houver uma âncora semântica confiável.

Fluxo exigido:

1. Identificar referência obsoleta antes do efeito.
2. Reobservar a página dentro do mesmo BrowserTask.
3. Reencontrar elemento por `testid`, nome, role ou label, quando houver âncora explícita e singular.
4. Validar identidade de aba, documento, owner, lease e actionability.
5. Executar uma única vez.
6. Verificar o resultado segundo o contrato do efeito.

Se existirem dois candidatos indistinguíveis, não selecionar arbitrariamente.

Se o efeito puder ter ocorrido, não refazer a mutação. Retornar estado incerto e solicitar reconciliação.

Crie testes RED/GREEN para DOM drift, elemento duplicado, takeover humano, navegação durante a resolução e timeout posterior ao despacho.

Não implemente um `browser_act()` autônomo que contorne o TaskCompiler ou a política de execução.

## ETAPA B3 - Diagnóstico forense incremental

Reutilize:

- `workstation/replay.py`
- `workstation/journal.py`
- `workstation/artifacts.py`
- `workstation/telemetry/browser_observation.py`
- `apps/desktop/src/app/browser/task-journal-drawer.tsx`

### B3.1 - Comparação de execuções

Criar `compare_portable_traces()` no sistema de replay existente.

Alinhar prioritariamente eventos por identidade real da operação e fase.

Quando a identidade não existir, utilizar comparação sequencial identificada como fallback, nunca apresentar correspondência ordinal como prova causal.

Retornar um relatório compacto com primeira divergência, tipo de diferença, operação afetada e diagnóstico determinístico.

Não incluir payloads de páginas, tokens ou prompts no relatório padrão.

### B3.2 - Evidência visual opcional

O Electron já dispõe de `screenshotForEntry()`.

Permitir associação de screenshot à etapa de falha quando houver consentimento explícito e escopo de captura apropriado.

Persistir por referência no ArtifactStore, com quota e retenção, evitando criar outro banco.

Não capturar imagens continuamente por padrão.

Não adicionar diagnóstico automático por LLM nesta fase. Primeiro produzir uma linha do tempo confiável e um resumo determinístico.

## FORA DO ESCOPO

Não implementar agora:

- Grafo DOM+AX+layout completo do Lattice.
- Delta estrutural RFC 8785, já que existe delta textual operacional.
- WebMCP de páginas como novo caminho autorizado de execução.
- Outro SDK de browser.
- SSE dedicado, se o canal de eventos atual for suficiente.
- Framework de callbacks JavaScript arbitrários.
- Autopromoção de competências baseada em observação.
- Quatro BrowserRuntime novos apenas para cumprir paridade documental.
- Integração AGPL de BrowserOS.
- Diagnóstico por LLM acionado em todas as falhas.

Esses itens permanecem em HOLD até demonstração de necessidade e benefício líquido.

## TESTES E ACEITAÇÃO

Execute os testes existentes e novos nas áreas modificadas, incluindo:

`workstation/tests/test_browser_extract_items.py`

`workstation/tests/test_browser_model_payload_projection.py`

`workstation/tests/test_browser_supervisor.py`

`workstation/tests/test_memory_replay.py`

E os arquivos de teste do Electron relacionados a snapshot, delta, extração, batch, controller, recovery e Learning Mode.

Verifique os comandos de teste no `apps/desktop/package.json` do HEAD atual.

Faça TDD RED/GREEN para correções verificáveis.

Execute lint, typecheck, regressões focadas e `git diff --check`. Investigue a CI exact-head e execute Electron real/Windows quando o ambiente permitir.

Para medir desempenho, compare baseline e implementação com as mesmas tarefas e os mesmos critérios de verificação.

Registre, quando disponíveis:

- Tokens reais de entrada, saída e cache.
- Número de chamadas System-1 e System-2.
- Chamadas e bytes do browser.
- Tempo até o resultado verificado e p95.
- Erros e reconciliações.
- Efeitos duplicados.
- Conflitos com edições humanas.
- Custo monetário, apenas quando houver dados confiáveis.

Não utilize percentuais do Lattice ou Stagehand como se fossem resultados medidos do Hermes.

## GIT E DOCUMENTAÇÃO

Crie uma branch de implementação isolada baseada na versão atual que já contenha D-049.

Preserve qualquer working tree local com alterações preexistentes.

Atualize, com o resultado real:

- `workstation/ROADMAP.md`
- `workstation/context/DECISIONS.md`
- `workstation/context/engineering-journal/CURRENT.md`
- `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md`
- `workstation/context/CURRENT_STATE.md`
- `workstation/context/KNOWN_ISSUES.md`
- Documentos D-049 e de Browser Automation V1 afetados.

Abra um PR de implementação, sem merge automático.

## FORMATO DO RELATÓRIO FINAL

Apresente:

**1. Estado implementado:** quais arquivos e funções foram modificados, com commits.

**2. Avaliação crítica:** quais sugestões foram aceitas, adaptadas ou rejeitadas e por quê.

**3. Evidências:** comandos, testes RED/GREEN, resultados reais e limitações.

**4. Qualificação:** distinguir IMPLEMENTADO, TESTADO e QUALIFICADO PARA RELEASE.

**5. Performance:** métricas antes/depois quando disponíveis, sem estimativas inventadas.

**6. Pendências:** somente problemas que realmente impedem a próxima etapa.

**7. Próxima ação:** continuar para a próxima melhoria de maior impacto quando o resultado estiver decente e seguro.

Se uma etapa encontrar bloqueio externo, não abandone o restante que puder ser implementado com segurança. Registre o bloqueio, preserve o gate e continue nas partes independentes.

**O resultado esperado não é mais uma arquitetura proposta. É código funcionando, integrado ao Hermes existente, com verificações e documentação correspondentes.**

## Encaminhamento recomendado

O PR [\#105](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/105) está aberto como *draft* para revisão e integração, sem merge automático na `main`\.

Para execução, recomendo entregar à IA implementadora **o prompt acima junto com o acesso ao GitHub**\. A sequência B0 → B1 → B2 → B3 funciona como um único mandato de implementação, mas os gates permitem que ela entregue mudanças independentes sem confundir progresso técnico com liberação para produção.

A prioridade é obter um browser que observe melhor, consuma menos contexto e recupere elementos com segurança - aproveitando o que o Hermes já tem, em vez de iniciar outra rodada de reconstrução arquitetural.

## Prompt:
19/10/2026, 02:37:59

Segue relatório do que foi feito:

O PR [kevynlucasprofissional-stack/hermes-agent#106](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/106) foi aberto, está mergeable com estado limpo e sem auto-merge, contendo a implementação de D-049 B1.2 (redação de secrets em valores) e B1.3 (validador de subconjunto JSON Schema) com testes.

**Resumo do que foi feito nesta sessão:**

1. **Verificação de estado:** Confirmada a branch `feat/d049-browser-80-20-impl-20261018` e os arquivos modificados pendentes de stage.
2. **Staging seletivo:** Adicionados apenas os 6 arquivos pertinentes ao D-049 B1.2/B1.3 (`workstation-browser-extract-cache.ts`, `workstation-browser-extract-cache.test.ts`, `workstation-browser-extract-schema.test.ts`, `workstation-browser-runtime.ts`, `CURRENT_STATE.md`, `engineering-journal/CURRENT.md`), excluindo alterações não relacionadas como `browser_bridge.py` e `.obsidian/workspace.json`.
3. **Correção de lint:** O commit inicial falhou no hook pre-commit (lefthook/eslint) com 4 erros e 23 warnings. Executado `eslint --fix` nos arquivos afetados, corrigindo importação, espaçamento e imports não utilizados.
4. **Commit e push:** Commit realizado com sucesso (`fd80408`) após correções; branch enviada ao remote.
5. **Criação do PR:** PR #106 criado contra `main` com descrição detalhada dos itens B1.2 e B1.3, co-autoria atribuída e sem auto-merge ativado.
6. **Vinculação e verificação:** PR vinculado à sessão; status confirmado como `open`, `MERGEABLE`, `CLEAN`, sem checks falhando e monitoramento desativado conforme solicitado.

Reading the last 300 lines of the engineering journal to locate the P0.2 item-boundary revocation follow-up block.

Searching for the exact "P0.2 item-boundary revocation follow-up (2026-10-10)" block in the engineering journal to apply the pending edit.

Reading the exact P0.2 block and surrounding context to apply the pending edit, then continuing D-049 implementation per the original scope.

Reading the D-049 handoff document and current state to identify the next implementation items after B1.2/B1.3.

Reading the D-049 handoff document to identify the next implementation gate after B1.2/B1.3, then verifying current branch state before proceeding.

Verifying current branch state and reading the D-049 handoff to identify the next gate after B1.2/B1.3 completion.

Reading the modified schema test file to understand what changed since the last commit, then verifying the P0.2 journal block is intact before continuing D-049 G1 implementation.

D-049 B1.2 (value-level secret redaction) and B1.3 (schema subset validation including the empty-items unsupported-keyword bug fix) are fully implemented, tested, committed as fd80408 on branch `feat/d049-browser-80-20-impl-20261018`, and PR [kevynlucasprofissional-stack/hermes-agent#106](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/106) is open and mergeable with auto-merge disabled; the P0.2 journal block at line 5920 of `workstation/context/engineering-journal/CURRENT.md` was inspected and requires no pending edit, and the next gates per the D-049 handoff are G1 (Python-side `schema_status` propagation through `browser_projection.py` and WorkItems) and G2 (tool schema `view` parameter exposure with benchmark).

Gerando relatório detalhado da sessão D-049 B1.2/B1.3 com evidências verificadas dos arquivos, testes e PR.

Reunindo evidências adicionais (commits G0, diff completo B1.2/B1.3, testes Python bridge e status do PR) para compor o relatório profundo solicitado.

# Relatório Detalhado — D-049 Browser Refinement 80/20 (B1.2 + B1.3 + G0)

## Resumo Executivo

A sessão implementou, testou e entregou via PR os itens **B1.2** (redação de secrets em valores) e **B1.3** (validador de subconjunto JSON Schema) do plano D-049, além de fechar o gate **G0** (sincronização e integração de arquivos untracked). Tudo está na branch `feat/d049-browser-80-20-impl-20261018` com PR [kevynlucasprofissional-stack/hermes-agent#106](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/106) aberto, mergeable e sem auto-merge.

---

## Cadeia de Commits (14 commits acima de main)

| SHA                         | Tipo | Descrição                                                                                        |
| --------------------------- | ---- | ------------------------------------------------------------------------------------------------ |
| `b7086c1834`                | fix  | Preflight schema keywords antes da iteração de items em `validateExtractedItems`                 |
| `267aebda31`                | feat | Fecha G0 — track snapshot-views, bridge security e ownership tests                               |
| `ab40cbbb33`                | docs | Handoff adversarial D-049 80/20 com sync seguro e prompts implementadores                        |
| `fd80408ab2`                | feat | Implementa B1.2 value-level secret redaction e B1.3 schema validation                            |
| `cd8e1e0db2`                | docs | Corrige formatação markdown no handoff D-049                                                     |
| `e34a59390b`                | docs | Adiciona prompt implementador executável com paths e gates                                       |
| `b4bb27a132`                | docs | Plano D-049 browser refinement com gates e file map                                              |
| `6dff5a0d19` – `f31e110952` | docs | Registros em STATE, KNOWN_ISSUES, CURRENT_STATE, HERMES_WORKSTATION, CURRENT, DECISIONS, ROADMAP |

---

## B1.2 — Value-Level Secret Redaction

### Problema

A redação anterior operava apenas por nome de chave (`SENSITIVE_KEY_PATTERN`). Secrets embutidos em valores de campos benignos como `text`, `content`, `url` ou `response_body` passavam sem filtro.

### Implementação (`workstation-browser-extract-cache.ts`)

Quatro padrões regex adicionais aplicados **após** o check de key-name, evitando dupla redação:

| Padrão                       | Cobre                                        | Exemplo de match                                      |
| ---------------------------- | -------------------------------------------- | ----------------------------------------------------- |
| `JWT_PATTERN`                | Tokens JWT completos (3 segmentos base64url) | `eyJhbGciOi...`                                       |
| `BEARER_VALUE_PATTERN`       | Header Bearer com token                      | `Bearer eyJ...` → `Bearer [REDACTED]`                 |
| `PREFIXED_KEY_PATTERN`       | Chaves prefixadas de provedores reais        | `sk-...`, `ghp_...`, `xoxb-...`, `AKIA...`, `AIza...` |
| `URL_ENCODED_SECRET_PATTERN` | Secrets URL-encoded em query strings         | `%22password%22:%22secret123%22`                      |

Strings bare (top-level array items, primitivos) também recebem `redactSecretValues()` antes do truncamento a 20.000 chars. A constante foi renomeada de `SENSITIVE_PATTERN` para `SENSITIVE_KEY_PATTERN` para clareza semântica.

### Testes (8 PASS, 227ms)

Cobrem: key-name redaction, value-level JWT/Bearer/prefix/URL-encoded, nested objects, bare strings, e prioridade correta (key-name short-circuit antes de value-level).

---

## B1.3 — Lightweight JSON Schema Subset Validator

### Problema

Extrações com schema retornavam `success=true` mesmo quando o schema era incompatível ou a validação nunca ocorreu. Não havia distinção entre "captura funcionou" e "resultado conforma ao schema".

### Implementação

Validador dependency-free suportando o subconjunto seguro: `type`, `required`, `enum`, `properties` (recursivo até profundidade 8), `description`, `title`.

**Rejeição explícita de keywords não suportadas:** `$ref`, `allOf`, `anyOf`, `oneOf`, `patternProperties`, etc. retornam `valid: false` com `unsupportedKeywords` populado. Isso previne aceitação silenciosa de dados que nunca foram realmente validados.

**Bug fix adicional (commit `b7086c1834`):** O preflight de unsupported keywords agora roda **antes** da iteração de items. Com `items=[]`, schemas incompatíveis eram anteriormente aceitos como válidos porque o loop nunca executava. Agora a verificação é independente da quantidade de itens.

### Integração no Runtime (`workstation-browser-runtime.ts`)

`extractItemsForEntry` retorna três novos campos no payload:

- `schema_valid`: boolean do owner Electron
- `schema_errors`: array bounded de erros
- `schema_unsupported_keywords`: lista de keywords rejeitadas

### Testes (12 PASS incluindo empty-items fix, 259ms)

Cobrem: valid/invalid type/required/enum, nested recursion, unsupported keywords ($ref/allOf/anyOf/oneOf/patternProperties), empty items com schema válido e inválido, multi-item error indexing.

---

## G0 — Sincronização e Integração

### Escopo Fechado (commit `267aebda31`, 500 inserções)

- **`workstation-browser-snapshot-views.ts`** (228 linhas): módulo anteriormente untracked, agora rastreado e importado corretamente pelo runtime
- **`workstation-browser-snapshot-views.test.ts`** (108 linhas): 11 testes cobrindo todas as view projections
- **`workstation-browser-runtime-task.test.ts`** (+41 linhas): teste B0.2 ownership/lease
- **`browser_bridge.py`** (+26/-9): patch B0.1 Path.resolve/is_relative_to + gravação de destino validado
- **`test_browser_bridge_security.py`** (+106 linhas): 7 PASS, 1 SKIP (symlink)

---

## Evidências Verificadas

| Dimensão               | Resultado                            | Comando/Evidência                                                        |
| ---------------------- | ------------------------------------ | ------------------------------------------------------------------------ |
| Vitest B1.2+B1.3       | **20/20 PASS** (518ms)               | `vitest run electron/workstation-browser-extract-{cache,schema}.test.ts` |
| Python bridge security | **7 PASS, 1 SKIP** (0.99s)           | `pytest -q workstation/tests/test_browser_bridge_security.py`            |
| Lint desktop app       | **0 errors, 0 warnings**             | `eslint --fix` aplicado antes do commit final                            |
| TypeCheck              | **0 errors**                         | Confirmado no journal entry                                              |
| PR #106 state          | OPEN, MERGEABLE, CLEAN               | `gh pr view 106 --json state,mergeable,mergeStateStatus`                 |
| Auto-merge             | **Desativado**                       | Monitor: `auto_merge: false`                                             |
| P0.2 journal block     | Inspeccionado na linha 5920, íntegro | Leitura direta de CURRENT.md                                             |

---

## Gates Próximos (não iniciados)

| Gate   | Descrição                                                                                                                                                                        | Dependência                              |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| **G1** | Propagação Python `schema_status` (valid/invalid/unknown/not_requested) através de `browser_projection.py` → WorkItems; `valid_count` só conta quando `schema_status == "valid"` | B1.3 ✅                                   |
| **G2** | Exposição do parâmetro `view` (summary/action_map/focus/content) no tool schema do agente + benchmark pareado medindo bytes model-facing                                         | G0 ✅                                     |
| **IV** | Recuperação semântica STALE_REF/DOM_DRIFT antes do CDP dispatch                                                                                                                  | Condicional: só se G2 provar necessidade |

Todos os gates respeitam H-079/H-081/H-082/BAV04 e exigem CI exact-head antes de promoção.

## Response:
19/10/2026, 02:38:11 · gpt-6-thinking

Vou conferir o PR \#106 e os commits diretamente no GitHub, separando o que foi realmente implementado do que o relatório apenas declara como concluído. Depois identifico o próximo passo 80/20 e preparo um prompt para a IA continuar sem refazer trabalho nem ampliar o escopo desnecessariamente.

A revisão do código encontrou um problema que o relatório não menciona: o commit de redação substituiu testes antigos do cache, eliminando cobertura de isolamento entre perfil, tarefa, aba, documento e schema. Também confirmei que o veredito `schema_valid` ainda não chega ao WorkPlan/WorkItems; portanto, a extração pode ser considerada válida pelo Python mesmo após reprovação no Electron. Vou conferir mais dois pontos do contrato antes de definir a próxima implementação.

> **Revisando vulnerabilidades**
>
> Estou identificando regressões em cache, validação de esquemas e sanitização. Há riscos de vazamento por mensagens de erro, palavras-chave ilimitadas, dados não sanitizados e sobrescrita de metadados seguros por campos brutos. Também noto inconsistências no tratamento de esquemas inválidos e resultados vazios.
>
> **Revisou vulnerabilidades**
>
> 
>
> **Auditando PRs e investigando regressões críticas em validação e cache**
>
> 
>
> **Aprofundando a revisão**
>
> Estou verificando se as checagens atuais realmente cobrem os riscos encontrados, sem alterar nada sem solicitação explícita. Os principais bloqueios continuam sendo vazamentos em erros de validação, campos brutos não sanitizados e sobrescrita de metadados.
>
> **Aprofundou a revisão**
>
> 
>
> **Definindo próximos passos**
>
> Estou separando a correção em etapas: primeiro, restaurar a cobertura de regressão e endurecer a validação do esquema, incluindo o fluxo G1. Depois, revisarei a visualização de snapshots e os testes de desempenho antes de qualquer alteração adicional.
>
> **Refinando o plano**
>
> Estou priorizando um primeiro ciclo com testes de regressão, pré-validação recursiva e limites para erros de esquema. Em seguida, separarei a revisão das projeções de visualização, evitando misturar correções de semântica, privacidade e desempenho na mesma mudança.
>
> **Refinou o plano e definiu os próximos passos**
>
> 
>
> **Avaliou segurança, validação e testes de projeção do navegador**
>
> 
>
> Pensou por 4m 25s

# Revisão do relatório D-049 - PR \#106

Conferi o [PR \#106](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/106?utm_source=chatgpt.com) e o código da branch `feat/d049-browser-80-20-impl-20261018` diretamente no GitHub.

**Minha avaliação: a implementação está avançando na direção correta, mas ainda não está pronta para integração sem uma correção de regressão e um fechamento do contrato de validação.** Não recomendo reescrever o que já foi feito.

Estado confirmado no GitHub (PR aberto, mergeable)

HEAD do PR

**`b7086c18`**

Arquivos no PR

**19 arquivos**

### O que foi realmente implementado

| Entrega | Avaliação |
|--------|--------|
| B0.1 - Proteção de diretórios | Implementada no código, com testes relatados; qualificação final pendente |
| B0.2 - Teste de ownership do Learning | Adicionado; ainda exige verificação em browser real |
| B1.1 - Quatro views de snapshot | Código integrado ao Electron, mas não totalmente acessível à IA |
| B1.2 - Redação de secrets em valores | Implementada com cobertura direcionada |
| B1.3 - Validação de subconjunto JSON Schema | Implementada, mas possui lacunas de validação |
| G1 - Propagação ao WorkPlan | Não implementada |
| G2 - Exposição e medição das views | Não concluída |

Encontrei três questões que mudam a ordem do próximo trabalho.

**1\. Regressão nos testes do cache.** O arquivo `workstation-browser-extract-cache.test.ts` foi substituído por testes de redação, removendo testes preexistentes de invalidação, isolamento entre perfil/aba/documento e diferenciação de schemas. O código do cache continua presente, mas sua cobertura de regressão foi perdida.

**2\. Um schema inválido pode continuar produzindo WorkItems concluídos.** O Electron retorna `schema_valid: false`, porém `workstation/browser_projection.py` não utiliza esse veredito para calcular `valid_count` ou decidir quais WorkItems concluir.

**3\. O validador ainda pode aceitar schemas malformados.** `validateSchemaSubset()` verifica `type` somente quando é string, `required` somente quando é array e `enum` somente quando é array. Um valor de formato incorreto para essas keywords pode ser ignorado. Além disso, em extrações vazias, o preflight só inspeciona as keywords da raiz; keywords inválidas em schemas aninhados podem passar sem serem examinadas.

São problemas localizados. Nenhum deles justifica substituir todo o mecanismo de extração.

### Outro ponto: PR mergeable não significa CI aprovada

Consultei os checks do HEAD `b7086c18`\. O GitHub retornou **zero check runs** e nenhum status associado ao commit, além de nenhuma execução de workflow localizada pela consulta de PRs.

Portanto, o relatório local de testes é uma evidência útil, mas o PR **não possui comprovação de CI verde no commit exato**\.

Também há dois ajustes pontuais de qualidade que merecem entrar na próxima sessão\:

- A mensagem de erro de `enum` inclui os valores completos permitidos pelo schema, o que pode revelar valores sensíveis e gerar mensagens grandes. O diagnóstico deve informar a violação sem reproduzir esses valores.
- O código das quatro views já existe, mas `browser_snapshot` ainda expõe somente `full` no schema de ferramentas. Além disso, `action_map` e `focus` não utilizam a gramática que o compactador Python reconhece, de modo que os elementos estruturados podem continuar sendo enviados integralmente junto com o texto.

**Decisão 80/20\:** primeiro corrigir a regressão de testes e concluir a validação até os WorkItems (**G1**\). Depois expor as views ao agente e medir o benefício real (**G2**\). A recuperação de localizadores (**IV**\) permanece condicional.

## Próximo prompt - G1 com revisão corretiva

Este é o prompt que eu enviaria agora à IA implementadora. Ele concentra problemas que fazem sentido resolver juntos e evita iniciar uma fase complexa de automação antes de corrigir a cadeia de validação.

**document: **

# Hermes Work D-049 - Continuação G1 e correção de regressões

## Objetivo

Continue a implementação na branch:

`feat/d049-browser-80-20-impl-20261018`

Repositório: `kevynlucasprofissional-stack/hermes-agent`

PR atual: #106

HEAD de referência auditado: `b7086c1834c150b558182b841743d295be176af2`.

Sua tarefa é **corrigir os problemas remanescentes de B1.3 e concluir G1 até o WorkPlan/WorkItems**, preservando todas as implementações já entregues.

Não produza apenas um relatório. Modifique o código, acrescente os testes necessários, execute-os, atualize a documentação e publique os commits na branch existente.

## 0. Sincronização obrigatória

Antes de editar:

1. Execute `git fetch origin`.
2. Confirme branch, HEAD, `git status --porcelain=v1 -uall` e worktrees.
3. Compare o HEAD local com o remoto.
4. Faça fast-forward somente se não houver conflitos nem perda de alterações locais.
5. Nunca execute `reset --hard`, `clean -fd`, stash indiscriminado ou rebase forçado.
6. Preserve arquivos de outros agentes.

Leia somente os contratos relevantes nos arquivos abaixo.

## 1. P0 - Restaurar testes removidos do cache

Arquivo:

`apps/desktop/electron/workstation-browser-extract-cache.test.ts`

A auditoria do PR #106 constatou que o commit de B1.2 substituiu a suíte antiga do cache por testes de redação.

Os testes anteriores cobriam:

- Invalidação após alteração de `mutationRevision` ou `documentFingerprint`.
- Isolamento por perfil, tarefa, aba, documento, URL e query.
- Distinção entre schemas no `computeQueryDigest`.
- Rejeição de fingerprints inválidos.
- Limpeza e sanitização.

**Restaure esses testes preservando os novos testes de B1.2.**

Utilize o arquivo na `main` anterior ao PR como referência e combine as duas suítes. Não sobrescreva o arquivo atual com a versão antiga.

Critério: a suíte final deve conter a cobertura anterior e os novos cenários de redaction, todos aprovados.

## 2. P0 - Corrigir validação de schemas malformados

Arquivo:

`apps/desktop/electron/workstation-browser-extract-cache.ts`

Funções:

- `validateSchemaSubset()`
- `validateExtractedItems()`

O commit `b7086c18` já corrigiu a detecção de keywords desconhecidas **na raiz** de schemas quando `items=[]`.

Não refaça essa correção.

Os problemas restantes são:

1. Keywords com valores malformados podem ser ignoradas, por exemplo `type: 123`, `required: "id"` ou `enum: "active"`.
2. Keywords não suportadas em schemas aninhados podem passar quando a lista de itens está vazia ou quando a propriedade não está presente.
3. `enum` pode expor todos os valores permitidos na mensagem de erro.
4. Não existe um limite suficientemente claro para volume e tamanho das mensagens de validação.
5. A semântica de `integer`, arrays e enums estruturados precisa estar explicitamente definida no subconjunto suportado.
6. A checagem de campos obrigatórios deve considerar propriedades próprias do objeto, sem confiar em atributos herdados.

### Implementação

Crie uma validação estrutural do próprio schema, executada antes de iterar sobre os itens.

Essa validação deve percorrer recursivamente as definições em `properties`, respeitar limites de profundidade e tamanho, rejeitar tipos/keywords não suportados e emitir erros estruturados sem reproduzir valores sensíveis.

Depois, execute a validação dos dados.

Não adicione uma dependência nova se o subconjunto explícito atual for suficiente. Se identificar que uma biblioteca já instalada resolve o problema com menor complexidade, poderá utilizá-la, justificando a escolha.

**Importante:** lista vazia com schema estruturalmente válido não é, por si só, erro de schema. Entretanto, o resultado deve distinguir claramente `0 itens encontrados` de `itens efetivamente validados`.

Escreva testes RED/GREEN antes da correção.

## 3. G1 - Propagar o veredito até os WorkItems

Arquivos principais:

`apps/desktop/electron/workstation-browser-runtime.ts`

`workstation/browser_projection.py`

`workstation/integrations/hermes/browser_controller.py`

`workstation/tests/test_browser_extract_items.py`

`workstation/tests/test_browser_controller_domain_processing.py`

### Problema confirmado

O Electron devolve `schema_valid`, mas `process_extracted_items_durably()` não consulta esse campo.

Atualmente, um item com `title` válido pode ser marcado como concluído mesmo que o schema solicitado pelo usuário tenha sido rejeitado.

### Contrato esperado

Preservar explicitamente quatro estados:

- `valid`: o schema foi solicitado e o owner comprovou conformidade.
- `invalid`: o schema foi solicitado e o owner rejeitou os dados ou o próprio schema.
- `unknown`: o schema foi solicitado, mas não chegou um veredito confiável.
- `not_requested`: a operação não solicitou schema.

A classificação deve ser feita no owner adequado e propagada até o resumo e a persistência durável.

Quando o schema foi solicitado:

- `invalid` e `unknown` nunca autorizam concluir WorkItems como conformes ao schema.
- Não inventar validade individual a partir de um booleano agregado.
- Preservar dados capturados de maneira sanitizada para investigação e correção.
- Não confundir erro de captura, erro de schema e falha de persistência.
- Não apresentar `valid_count` positivo como conformidade do schema se o veredito global é inválido ou desconhecido.

Quando o schema não foi solicitado, preserve o comportamento legado da validação semântica, salvo defeito comprovado.

A regra histórica de `SemanticValidator(required_fields=["title"])` não deve ser aplicada cegamente como exigência universal de todo schema. Separe a validação semântica do produto da validação do schema solicitado.

### Persistência

Reutilize o `DurableTaskStore`, `WorkPlan`, `WorkItem` e `ArtifactStore` atuais.

Persistir status, referência de evidência e erros limitados/sanitizados na estrutura existente, sem criar outra tabela ou outro banco.

Se houver falha na persistência, não declarar durabilidade ou conclusão comprovada.

## 4. Matriz mínima de testes

Testar obrigatoriamente:

- Schema válido com itens conformes.
- Schema inválido com itens aparentemente corretos.
- Schema solicitado, mas `schema_valid` ausente.
- Schema inválido com `items=[]`.
- Keyword desconhecida em schema aninhado, inclusive com itens vazios.
- Keyword suportada com formato inválido.
- `enum` com valor sensível, comprovando que o erro não revela esse valor.
- Campo `title` ausente quando o schema solicitado não o exige.
- Nenhum schema solicitado, preservando resultado legado.
- Falha de ArtifactStore, impedindo falso `durable=true`.
- Fluxo controller → projeção Python → resumo.
- Todos os testes antigos e novos do cache.

Execute Vitest, Pytest, typecheck, lint e `git diff --check`, além das regressões adjacentes relevantes.

Não afirme CI verde sem um check concluído no SHA exato.

## 5. Critérios de aceite

A entrega é considerada funcional quando:

1. A suíte de cache anterior foi recuperada sem perder a cobertura nova.
2. Nenhum schema malformado é aceito silenciosamente.
3. Nenhum erro de schema publica secrets ou estruturas ilimitadas.
4. `schema_status` atravessa corretamente o controller até o domínio Python.
5. Um veredito `invalid` ou `unknown` impede falsa conclusão de WorkItems como conformes.
6. O comportamento sem schema permanece compatível.
7. Os testes relevantes são executados e seus resultados registrados.

## 6. Encerramento

Atualize ROADMAP, jornal de engenharia, Hermes Work Intelligence, Current State e Known Issues apenas com evidências reais.

Faça commit e push na branch de implementação, mantendo o PR #106 atualizado.

Relate de forma sucinta:

- SHA inicial e final.
- Arquivos alterados.
- Problemas corrigidos.
- Testes executados e resultados.
- Estado da CI.
- Pendências que realmente impedem o próximo passo.

Se uma sugestão minha não se ajustar ao código atual, adapte. Não replique arquiteturas desnecessárias. Use o menor patch que satisfaça os contratos.

**Após G1, o próximo trabalho é G2: disponibilizar `summary`, `action_map`, `focus` e `content` na ferramenta real `browser_snapshot` e comparar o custo model-facing com a implementação anterior. Não comece G2 antes de registrar claramente o resultado deste gate.**

## E depois de G1?

O próximo trabalho é **G2 - economia real de contexto**\. O módulo de views já contém 228 linhas de código e tem testes direcionados; portanto, o investimento principal será conectar os parâmetros `view`, `focus_ref`, `focus_neighbors` e `max_chars` à ferramenta do agente, eliminar duplicação no payload model-facing e medir o ganho.

Eu **não iniciaria a recuperação semântica IV nem o tracing visual agora**\. Primeiro terminaria G1, depois G2. Se as medições indicarem que o browser já funciona adequadamente sem um resolvedor mais complexo, podemos encerrar a D-049 no ponto 80/20.

Por fim, observe que o PR \#106 contém os commits documentais que já estavam no PR \#105. Como ambos estão abertos contra a `main`, convém evitar integrá-los separadamente sem conferir a sobreposição. O \#106 pode servir como PR consolidado, desde que o histórico e os testes finais estejam corretos.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)