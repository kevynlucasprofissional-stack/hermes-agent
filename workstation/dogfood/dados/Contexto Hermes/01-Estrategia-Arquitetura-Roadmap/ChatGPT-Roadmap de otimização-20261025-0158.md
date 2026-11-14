# Roadmap de otimização

**User:** Anonymous  
**Created:** 10/24/2026 16:36:06  
**Updated:** 10/25/2026 1:55:58  
**Exported:** 10/25/2026 1:58:56  
**Link:** [https://chatgpt.com/c/6add08a6-092c-83e9-b982-ea58699188ad](https://chatgpt.com/c/6add08a6-092c-83e9-b982-ea58699188ad)  

## Prompt:
24/10/2026, 16:36:07

Faz o seguinte, lê essas mensagens são as últimas mensagens as últimas sessões que eu que eu troquei com a ferramenta que eu estou criando que eu vou dizer abaixo e procura nela pontos de melhoria pontos de desperdício de tokens pontos onde skills utilizadas deveriam se tornar scripts determinísticos ou deveriam se tornar skills permanentes do Hermes colocado em site ops ou deveriam se tornar capacidades operacionais de acordo com o que a gente está construindo lá no Experience Compiler é procura lugares onde tinha uma alta taxa de incerteza e por isso precisou ser feita muitos muitas tentativas procura lugares onde a gente poderia focar um esforço para aumentar a velocidade do que está sendo entregue e de como está sendo feito procure os lugares de maior desperdício operacional ou de maior desperdício de tokens de maior desperdício de velocidade maior desperdício de tempo levanta hipóteses de como corrigir esses desperdícios se seria por exemplo a gente fazer alguma modificação no código da ferramenta seria criar um skill global para ficar diretamente no código fonte da ferramenta ou seria criar uma capacidade operacional vamos investigar isso em tudo e vamos fazer isso parte por parte então cria aí uma um roadmap né de prompts em fluxo de prompts pra eu te enviar e a gente investigar isso passo a passo só que você precisa encontrar o ponto ótimo entre economia de quantidade de prompts e profundidade necessária para a gente conseguir realmente investigar o tanto certo para a gente entender o que realmente precisa ser feito vamos focar aí na na menor quantidade de esforço para o maior impacto e também os prompts eles podem fazer pedidos de investigação nos aquilocais da minha máquina através do remote desktop Commander.

[Attachment: abrir-whatsapp-web-2-20261022.json]

[Attachment: criar-banco-de-dados-para-controle-do-whatsapp-20261022.json]

[Attachment: abrir-aplicativo-whatsapp-2-20261023.json]

[Attachment: enviar-convites-de-oficina-via-wa.me-20261023.json]

[Attachment: abre-o-whatsapp-20261024.json]

[Attachment: abrir-photocraft-2-20261019.json]

[Attachment: sauda-o-amig-vel-20261023.json]

[Attachment: automatizar-envio-de-mensagem-no-whatsapp-web-20261021(1).json]

[Attachment: enviar-mensagem-de-agradecimento-pelo-whatsapp-20261021(1).json]

[Attachment: enviar-mensagem-teste-para-kevyn-acirv-no-whatsa-20261021(1).json]

[Attachment: abrir-o-google-20261019.json]

[Attachment: automatizar-envio-de-mensagem-no-whatsapp-web-20261021(2).json]

[Attachment: enviar-9-e-mails-p-s-evento-acirv-20261021(1).json]

[Attachment: enviar-email-de-agradecimento-aos-participantes--20261021(1).json]

## Response:
24/10/2026, 16:36:12 · gpt-6-thinking

Vou analisar as 14 exportações como um conjunto de evidências: identificar padrões recorrentes, medir o desperdício observável e separar problemas de orquestração, ferramentas, skills e capacidades operacionais. Depois organizarei a investigação em poucos prompts sequenciais, cada um com critérios objetivos e possibilidade de consultar o código local pelo Remote Desktop Commander.

> **Analisando sessões e falhas de ferramentas**
>
>
> **Analisando expansão de contexto e compactions**
>
>
> **Analisando padrões de ferramentas e falhas**
>
>
> **Estruturando prompts sequenciais**
>
> Estou organizando um fluxo enxuto de três etapas: validar evidências no repositório correto, priorizar causas e soluções, depois implementar e verificar. Vou incluir caminhos como modelos, sem presumir a localização da cópia local.
>
> **Refinando o roadmap**
>
> Estou ajustando o fluxo para investigar antes de implementar: primeiro mapeio evidências e causas, depois comparo soluções, e só então executo mudanças com testes. Também vou manter uma etapa opcional de avaliação após os resultados.
>
> **Refinou o roadmap e estruturou prompts sequenciais**
>
> 
>
> **Analisando falhas e padrões das sessões**
>
>
> **Projetando prompts investigativos**
>
> Estou consolidando prompts orientados por evidências, com métricas, critérios de decisão e limites claros: investigar sem alterar, desenhar alternativas comparáveis, implementar somente após aprovação e medir resultados sem confundir correlação com causa.
>
> **Projetou prompts investigativos**
>
> 
>
> **Encontrando evidências para prompts de arquitetura**
>
>
> **Consolidando evidências**
>
> Estou fechando três prompts autossuficientes: auditoria quantitativa, diagnóstico arquitetural e implementação controlada. Cada etapa exige artefatos verificáveis, preserva o estado atual e evita modificar o código antes de haver decisão explícita.
>
> **Consolidou evidências**
>
> 
>
> **Analisou sessões, ferramentas, falhas e evidências para arquitetura**
>
> 
>
> **Buscou mais informações nos arquivos**
>
> 
>
> Pensou por 5m 16s

# Auditoria do Hermes Work - Roadmap de investigação e otimização

A investigação deve responder a uma questão central\:

**Quais partes do trabalho o Hermes continua resolvendo com raciocínio de IA, tentativas e chamadas de ferramentas, quando poderia executá-las por mecanismos reutilizáveis, mais rápidos, baratos e confiáveis?**

O objetivo não é simplesmente diminuir tokens. É **reduzir o custo operacional por tarefa concluída corretamente**, mantendo flexibilidade para situações novas.

## 1\. Diagnóstico preliminar das sessões

Já identifiquei alguns sinais importantes nos arquivos enviados.

Sessões distintas

# 13

14 arquivos; 1 duplicado

Mensagens registradas

# 4.093

Incluindo chamadas e respostas

Texto retornado por ferramentas

# 6,9 mi

Caracteres, não tokens

A sessão **“Criar banco de dados para controle do WhatsApp”** concentra 2.406 mensagens, com centenas de execuções de terminal, consultas ao navegador e operações de arquivos. É a primeira candidata a uma análise aprofundada.

Outro padrão aparece nas operações de envio pelo WhatsApp: o agente frequentemente precisa observar a página, localizar elementos, decidir uma ação, executá-la e observar novamente. Parte desse ciclo é necessária, mas sua repetição sugere oportunidades para macros determinísticas, operações em lote e capacidades de navegador com contratos explícitos.

Também encontrei problemas de infraestrutura, como rejeições do controlador do navegador e bloqueios de aprovação no Gmail. Esses problemas não se resolvem simplesmente escrevendo melhores skills.

**Limitação importante\:** os campos `token_count` das exportações estão vazios. Podemos medir chamadas, volume de texto, repetições e falhas observadas, mas o consumo real de tokens e o tempo efetivo de execução exigirão correlação com a telemetria local.

## 2\. Onde concentraria a investigação primeiro

**P0 - Ciclos repetitivos de execução**

Foram registradas 612 respostas de `browser_console` e 723 de `terminal`\. Há oportunidades de agrupar ações e retirar o modelo do caminho de execução de operações previsíveis. Esses números são indicadores de volume, não de desperdício líquido.

---

**P0 - Falhas e incerteza do controlador**

Encontrei ocorrências de `ControllerRejected`, `timed out after dispatch`, `uncertain_mutation_requires_review` e avisos de repetição de falhas idênticas. Aqui, melhorar o runtime e sua recuperação de erros pode trazer mais resultado que criar novas skills.

---

**P0 - Automatizações existentes subaproveitadas**

Os registros mencionam `whatsapp-email-campaign-control`, `campaign_control.py`, `wa_cdp_batch.py` e `whatsapp_control.db`\. Precisamos descobrir por que ainda há tantos comandos manuais, apesar desses mecanismos. Não devemos criar substitutos sem verificar o que já existe.

---

**P1 - Custo da memória e redescoberta**

Identifiquei 60 mensagens de compactação de contexto, somando aproximadamente 1,58 milhão de caracteres. Também há leituras repetidas de skills extensas. É necessário investigar a diferença entre contexto indispensável e informação que deveria estar disponível por recuperação seletiva.

---

**P1 - Automação de interfaces sem garantias suficientes**

Uma das sessões registra cliques que abriram inesperadamente o download do WhatsApp para Windows. Isso aponta para a necessidade de validar identidade, visibilidade e geometria dos elementos, além de confirmar o efeito de cada mutação importante.

Essas prioridades são **hipóteses de investigação, não decisões de implementação**\. O código atual pode já ter corrigido parte dos problemas presentes nas sessões de 19 a 24 de outubro.

## 3\. Como decidir o que cada melhoria deve virar

O Experience Compiler precisa distinguir cinco destinos possíveis\:

| Destino | Quando utilizar |
|--------|--------|
| **Script determinístico** | Procedimento estável, parametrizável, testável, com entradas e saídas previsíveis |
| **Skill global em `site_ops`** | Conhecimento específico de um site, incluindo sua navegação, particularidades e estratégia operacional |
| **Capacidade operacional** | Primitiva reutilizável por várias skills e tarefas, com interface, estado, validação e tratamento de erros |
| **Correção no núcleo do Hermes** | Defeito estrutural de runtime, integração, permissões, browser, execução ou persistência |
| **Experience Compiler** | Seleção, aprendizagem, composição, promoção, versionamento e aperfeiçoamento dessas soluções |

Esses destinos não são mutuamente exclusivos. Uma automação robusta pode usar uma capacidade operacional que executa um script determinístico, orientado por uma skill específica do site.

Exemplo: a skill sabe *como o WhatsApp funciona*; a capacidade sabe *executar e verificar ações no navegador*; o script sabe *processar uma fila de destinatários sem duplicações*; o Experience Compiler sabe *quando reutilizar ou melhorar cada componente*\.

### O fluxo recomendado

**Prompt 1 - Auditoria causal e inventário local**

O que está sendo desperdiçado e por quê?

**Prompt 2 - Investigação profunda das 3 maiores oportunidades**

Qual é a causa no código e qual solução realmente funciona?

**Prompt 3 - Decisão arquitetural e plano 80/20**

O que corrigir, reutilizar, transformar ou descartar?

**Prompt 4 - Implementação e benchmark**

Opcional: executar depois de escolhidas as correções

São **três prompts de investigação e decisão**, mais um de execução. Cada etapa reaproveita o resultado da anterior, evitando repetir a auditoria inteira.

## 4\. Os prompts prontos para uso

ETAPA 1 DE 4

### Prompt 1 - Auditoria causal e inventário do Hermes

**document: **

# MISSÃO 1 - Auditoria de desperdícios operacionais do Hermes Work

Analise as 14 exportações JSON das sessões do Hermes Work anexadas nesta conversa, considerando 13 sessões distintas (uma exportação está duplicada).

**Objetivo:** descobrir onde o Hermes desperdiça mais tokens, chamadas de ferramentas, tempo, tentativas e raciocínio, e identificar as três oportunidades de maior retorno.

## Procedimento

1. Utilize os logs para reconstruir os principais fluxos de execução, agrupando operações repetidas e falhas relacionadas.
2. Identifique loops, polling desnecessário, consultas redundantes, skills relidas, redescoberta de procedimentos, excesso de contexto, falhas de seleção de ferramentas e operações que poderiam ser determinísticas.
3. Investigue especialmente os ciclos de `browser_console`, `terminal`, `browser_snapshot`, compactações, falhas do controlador, envios em lote e estados de execução incertos.
4. Diferencie desperdício verdadeiro de complexidade necessária e de custos provocados por falhas de infraestrutura.
5. Use o **Remote Desktop Commander** para inspecionar, somente em leitura, o repositório local `C:\Github\hermes-agent`, se este for o caminho atual, além das skills e scripts operacionais existentes. Localize o código do Experience Compiler, navegador, seleção de ferramentas, capacidades, `site_ops` (ou equivalente) e telemetria.
6. Verifique se problemas observados nos logs antigos já foram corrigidos no código atual. Não proponha construir novamente algo que já existe.

## Medições

Quantifique, quando possível: chamadas por tarefa, ciclos repetidos, erros, tentativas, volume de payload, compactações, latência observável e proporção de trabalho concluído.

Não invente consumo de tokens quando faltar telemetria. Use proxies explicitamente identificados.

## Entregáveis

- Ranking dos **8 maiores desperdícios**, com evidências concretas das sessões.
- Para cada problema: causa provável, impacto, recorrência, confiança e status no código atual.
- Inventário dos mecanismos reutilizáveis já existentes.
- Classificação preliminar: script, skill global, capacidade operacional, núcleo do Hermes ou Experience Compiler.
- **As 3 oportunidades prioritárias** para investigação profunda, considerando impacto esperado × recorrência × confiança ÷ esforço.

Não modifique arquivos. Não execute envios ou ações externas. Termine indicando exatamente o que investigar na etapa seguinte, sem repetir toda a auditoria.

O resultado desta etapa será um mapa de desperdícios com prioridades baseadas em evidências, não apenas impressões.

ETAPA 2 DE 4

### Prompt 2 - Investigação técnica das três maiores oportunidades

**document: **

# MISSÃO 2 - Diagnóstico de causa-raiz e experimentos

Continue a auditoria do Hermes Work realizada anteriormente, utilizando suas conclusões e as sessões JSON já fornecidas.

**Objetivo:** investigar profundamente as três maiores oportunidades identificadas, até descobrir quais mudanças realmente eliminariam suas causas.

## Método

Para cada oportunidade:

1. Reconstrua um caso representativo: intenção do usuário → decisões do agente → chamadas de ferramentas → resultados → tentativas adicionais → desfecho.
2. Use o Remote Desktop Commander para examinar as implementações correspondentes no repositório local e nas skills instaladas.
3. Investigue se o custo vem de raciocínio desnecessário, seleção incorreta, ausência de primitiva operacional, falha de runtime, persistência inadequada, conhecimento insuficiente ou integração defeituosa.
4. Localize funções, classes, módulos e arquivos relevantes. Verifique a implementação real, não apenas a documentação.
5. Formule no máximo três hipóteses de correção por problema e escolha a mais promissora.
6. Quando possível, valide as hipóteses com inspeções, testes existentes, simulações ou experimentos isolados, sem modificar o repositório.

Considere soluções híbridas, como skill global de site que invoca uma capacidade operacional implementada com script determinístico.

**Atenção:** distinga falhas que exigem correção na infraestrutura de problemas que podem ser resolvidos por automações. Não tente contornar CSP, permissões, aprovações ou mecanismos de reconciliação por manipulação manual de estado.

## Entregáveis

Para cada uma das três oportunidades, apresente:

- Evidência observada e causa-raiz confirmada ou hipótese ainda não comprovada.
- Local exato no código e implementação existente que pode ser reutilizada.
- Comparação de alternativas, com trade-offs de tokens, velocidade, confiabilidade e manutenção.
- Solução recomendada, esforço estimado, dependências, riscos e estratégia de validação.
- Critério objetivo que demonstrará que o desperdício foi eliminado ou reduzido.

Diferencie claramente **fatos verificados, inferências e questões pendentes**.

Não implemente ainda. Ao final, determine quais correções devem entrar primeiro e quais não justificam investimento.

Esta é a etapa de maior profundidade técnica. Ela evita transformar um sintoma em uma skill quando a verdadeira causa está no controlador ou no código-base.

ETAPA 3 DE 4

### Prompt 3 - Arquitetura final e plano 80/20

**document: **

# MISSÃO 3 - Decisões arquiteturais para otimização do Hermes Work

Com base na auditoria das sessões e na investigação técnica das três maiores oportunidades, produza um plano de correções priorizado pelo maior resultado com o menor esforço.

**Objetivo:** decidir precisamente o que será implementado, em qual camada do Hermes e em qual ordem.

## Critérios arquiteturais

Considere cinco alternativas:

1. **Script determinístico:** procedimentos parametrizáveis, repetitivos, testáveis e com efeitos controláveis.
2. **Skill global (`site_ops` ou equivalente):** playbook específico de site, com conhecimento e estratégias reutilizáveis.
3. **Capacidade operacional:** primitiva universal, reutilizável por diversas skills, com interface tipada e contrato verificável.
4. **Correção do núcleo:** mudanças necessárias no runtime, navegador, ferramentas, permissões, persistência ou execução.
5. **Experience Compiler:** aprendizagem, seleção hierárquica, composição, versionamento, promoção, autocorreção e acompanhamento de desempenho.

Permita arquiteturas híbridas, mas evite camadas e abstrações que não tragam benefício mensurável.

Considere o modelo de aprendizagem progressiva do Hermes: o agente executa a tarefa e melhora sua execução futura, com preferência por seleção barata e determinística/System-1 e escalada ao System-2 somente quando necessário.

## Entregáveis

Produza um plano contendo:

- As **3 primeiras mudanças recomendadas**, com justificativa de impacto, esforço, recorrência, risco e confiança.
- O que reutilizar, alterar, criar ou eliminar, indicando arquivos e módulos.
- A relação entre skills permanentes, scripts, capacidades e o Experience Compiler.
- Contratos de entrada/saída, critérios de sucesso, prevenção de duplicações, recuperação de falhas e mecanismos de rollback.
- Benchmarks de antes/depois: latência, chamadas, tokens reais quando disponíveis, taxa de sucesso e intervenção humana.
- Ordem exata de implementação, dependências e testes de aceite.

Classifique cada melhoria como **quick win**, melhoria estrutural ou investimento de longo prazo.

Priorize obter ganho mensurável rapidamente. Não proponha uma refatoração geral quando uma correção localizada resolver o problema.

Não faça alterações ainda. Termine com a recomendação de **uma única implementação inicial**, suficientemente delimitada para ser executada e testada na próxima etapa.

Após esse prompt teremos uma especificação executável, com decisões tomadas e sem a necessidade de reabrir todas as discussões.

ETAPA 4 DE 4 · OPCIONAL

### Prompt 4 - Implementação supervisionada e benchmark

**document: **

# MISSÃO 4 - Implementar e validar a otimização prioritária do Hermes Work

Execute a primeira melhoria aprovada no plano 80/20 produzido na investigação anterior.

**Objetivo:** entregar uma correção funcional, testada e mensuravelmente melhor que o comportamento anterior.

Use o Remote Desktop Commander para trabalhar no repositório local do Hermes. Antes de editar, verifique branch, estado do Git, alterações existentes, testes e contratos das ferramentas afetadas.

## Regras de execução

- Respeite o fluxo de branch compartilhada existente; não crie worktrees ou branches desnecessárias.
- Reutilize capacidades e scripts existentes antes de criar novos componentes.
- Faça a menor alteração capaz de resolver a causa-raiz.
- Preserve permissões, isolamento, aprovações humanas e mecanismos de reconciliação.
- Para ações externas, como mensagens ou e-mails, utilize mocks ou dry-run por padrão. Não faça envios reais sem autorização explícita.
- Acrescente testes de regressão, falha, retry, idempotência e recuperação de estado conforme o componente.
- Instrumente o comportamento para tornar o ganho mensurável.
- Não altere outras áreas fora do escopo.

## Validação

Compare o comportamento anterior e posterior usando o mesmo cenário e condições equivalentes.

Meça chamadas de ferramentas, tempo de execução, tokens quando disponíveis, erros, repetições, sucesso e confiabilidade.

Se alguma métrica não puder ser medida, diga por quê e quais instrumentos seriam necessários.

## Entrega final

Apresente:

1. O que foi alterado e em quais arquivos.
2. Os testes realizados, resultados e limitações.
3. Comparação antes/depois com evidências.
4. Problemas remanescentes ou regressões.
5. Como o Experience Compiler deve reconhecer, recuperar e reutilizar a melhoria.
6. Qual seria a próxima melhoria de maior retorno, agora que esta foi concluída.

Não declare sucesso sem evidência de funcionamento. Não faça merge ou push sem autorização específica.

---

## 5\. Um ponto crítico que não deixaria de investigar

Além dos padrões gerais, encontrei um episódio especialmente relevante na sessão mais extensa: uma operação de navegador ficou bloqueada por `prior_operation_requires_reconciliation`\. Posteriormente, o agente registrou uma intervenção direta em `browser-session.json`, alterando uma confirmação de operação pendente.

Isso merece prioridade porque não representa apenas um problema de velocidade. Pode indicar uma lacuna no protocolo de reconciliação de ações: **o agente precisa conseguir distinguir uma operação confirmada, não executada ou de resultado desconhecido sem adulterar o estado de controle**\.

Outro achado é o carregamento de skills extensas, incluindo uma com aproximadamente 25,8 mil caracteres, posteriormente removida da janela de contexto por compactação. Isso sugere uma oportunidade para recuperação seletiva de instruções, scripts e referências, em vez de injetar playbooks completos.

Esses dois casos ilustram bem a distinção entre corrigir **o mecanismo de execução** e otimizar **a seleção de conhecimento**\.

## 6\. Quando encerrar a investigação

Eu aplicaria uma regra simples: investigar até haver evidência suficiente para tomar uma decisão implementável, não até eliminar toda incerteza.

A cada etapa, podemos encerrar a investigação de determinado problema quando tivermos identificado\:

- A causa-raiz com confiança adequada.
- O componente existente que precisa mudar.
- Uma solução de baixo acoplamento.
- Um teste capaz de confirmar o ganho.
- Um retorno esperado que justifique o esforço.

Se já houver evidência suficiente ao final do Prompt 1 para implementar uma correção pequena, não será obrigatório atravessar todas as etapas para aquela correção.

**Minha recomendação\:** comece pelo **Prompt 1**, aproveitando a análise inicial que já fizemos. A prioridade é confirmar no código atual os maiores pontos de desperdício, sobretudo os loops do navegador, as falhas de reconciliação e a subutilização das automações existentes. O ganho mais relevante provavelmente virá de tornar a execução repetitiva determinística e confiável, reservando a IA para decisões que realmente exigem inteligência.

## Prompt:
24/10/2026, 16:42:57

# MISSÃO 1 — Auditoria de desperdícios operacionais do Hermes Work

Analise as 14 exportações JSON das sessões do Hermes Work anexadas nesta conversa, considerando 13 sessões distintas (uma exportação está duplicada).

**Objetivo:** descobrir onde o Hermes desperdiça mais tokens, chamadas de ferramentas, tempo, tentativas e raciocínio, e identificar as três oportunidades de maior retorno.

## Procedimento

1. Utilize os logs para reconstruir os principais fluxos de execução, agrupando operações repetidas e falhas relacionadas.
2. Identifique loops, polling desnecessário, consultas redundantes, skills relidas, redescoberta de procedimentos, excesso de contexto, falhas de seleção de ferramentas e operações que poderiam ser determinísticas.
3. Investigue especialmente os ciclos de `browser_console`, `terminal`, `browser_snapshot`, compactações, falhas do controlador, envios em lote e estados de execução incertos.
4. Diferencie desperdício verdadeiro de complexidade necessária e de custos provocados por falhas de infraestrutura.
5. Use o **Remote Desktop Commander** para inspecionar, somente em leitura, o repositório local `C:\Github\hermes-agent`, se este for o caminho atual, além das skills e scripts operacionais existentes. Localize o código do Experience Compiler, navegador, seleção de ferramentas, capacidades, `site_ops` (ou equivalente) e telemetria.
6. Verifique se problemas observados nos logs antigos já foram corrigidos no código atual. Não proponha construir novamente algo que já existe.

## Medições

Quantifique, quando possível: chamadas por tarefa, ciclos repetidos, erros, tentativas, volume de payload, compactações, latência observável e proporção de trabalho concluído.

Não invente consumo de tokens quando faltar telemetria. Use proxies explicitamente identificados.

## Entregáveis

- Ranking dos **8 maiores desperdícios**, com evidências concretas das sessões.
- Para cada problema: causa provável, impacto, recorrência, confiança e status no código atual.
- Inventário dos mecanismos reutilizáveis já existentes.
- Classificação preliminar: script, skill global, capacidade operacional, núcleo do Hermes ou Experience Compiler.
- **As 3 oportunidades prioritárias** para investigação profunda, considerando impacto esperado × recorrência × confiança ÷ esforço.

Não modifique arquivos. Não execute envios ou ações externas. Termine indicando exatamente o que investigar na etapa seguinte, sem repetir toda a auditoria.

## Response:
24/10/2026, 16:43:04 · gpt-6-thinking

Vou fazer a auditoria em duas camadas: primeiro, análise quantitativa das 13 sessões distintas e reconstrução dos ciclos de falha; depois, comparação com o código e as skills atuais pelo Remote Desktop Commander. Vou manter a inspeção em modo somente leitura e separar evidências confirmadas de hipóteses.

A comparação com o repositório já revelou algo decisivo: o Hermes **já tem um `site-ops` global para WhatsApp**, com mapa de elementos, script determinístico, cliente CDP, auto-healing e integração IPC. Portanto, a recomendação não será criar outro sistema. Estou verificando agora se essas peças são realmente confiáveis, acessíveis ao agente e capazes de confirmar o resultado das operações.

> **Verificando rapidamente o esquema dos arquivos JSON**
>
>
> **Verificado rapidamente o esquema dos arquivos JSON**
>
> 
>
> **Listou dispositivos disponíveis do Remote Desktop Commander**
>
> 
>
> **Calculando métricas robustas das sessões**
>
>
> **Calculou métricas robustas e converteu conteúdo C para JSON**
>
> 
>
> **Inspecionado rapidamente o caminho remoto**
>
> 
>
> **Analisando compactações de conversas JSON**
>
>
> **Analisou compactações de conversas em JSON**
>
> 
>
> **Calculou métricas precisas de compactação**
>
> 
>
> **Analisando referências de contexto nas sessões**
>
>
> **Analisou referências de contexto e mensagens longas do assistente**
>
> 
>
> **Buscou arquivos remotos e analisou arquitetura de inteligência do site_ops**
>
> 
>
> **Verificando estrutura de métricas computacionais**
>
>
> **Verificou a estrutura de métricas computacionais**
>
> 
>
> **Leu documentação e inspecionou integrações WhatsApp, SiteOps e CDP**
>
> 
>
> **Inspecionando status, erros e tamanhos de ferramentas**
>
>
> **Inspecionou status, erros e tamanhos das ferramentas**
>
> 
>
> **Avaliou riscos, bugs, integrações e telemetria do SiteOps**
>
> 
>
> **Used container tool**
>
> 
>
> **Inspecionou ferramentas, prontidão e contratos do WFR no WhatsApp**
>
> 
>
> **Analisando chamadas repetidas de ferramentas**
>
>
> **Avaliando lacunas técnicas**
>
> Estou identificando três prioridades: corrigir a recuperação quando o navegador falha, validar o fluxo de operações do site ponta a ponta e melhorar o uso de contexto, memória e habilidades. Também estou comparando a documentação com o código atual e testes realmente executados.
>
> **Avaliou lacunas técnicas**
>
> 
>
> **Analisou chamadas repetidas de ferramentas**
>
> 
>
> **Avaliou a confiabilidade de automação e operações**
>
> 
>
> **Computando métricas de contexto e ferramentas**
>
>
> **Priorizando correções**
>
> Estou consolidando 65 registros, distinguindo conteúdo compactado de visões de habilidades. Os maiores riscos atuais são recuperação sem limites, seletores dependentes de idioma e confirmação de envio sem validação real. Vou priorizar confiabilidade operacional, testes ponta a ponta e rastreabilidade dos resultados.
>
> **Classificando oportunidades**
>
> Estou separando oito padrões por impacto, recorrência, confiança e maturidade da correção. As prioridades concentram-se em recuperação do navegador, operações do WhatsApp, verificação de resultados, seleção de contexto, qualidade de dados e observabilidade ainda incompleta.
>
> **Definindo próximos passos**
>
> Estou priorizando três frentes para a etapa seguinte: reconciliar estados do navegador, tornar as operações do WhatsApp determinísticas e reduzir contexto desnecessário. Vou investigar evidências, caminhos de execução e validações observáveis, sem repetir a auditoria completa.
>
> **Priorizou correções, classificou oportunidades e definiu próximos passos**
>
> 
>
> **Calculou métricas de contexto e ferramentas**
>
> 
>
> Pensou por 8m 4s

# Auditoria operacional do Hermes Work

Missão 1 - Análise das sessões de 19 a 24 de outubro de 2026, com inspeção do repositório local

## 1\. Resumo executivo

**O principal problema identificado não é apenas o consumo de tokens. É o custo de coordenação necessário para transformar uma intenção em uma ação concluída e verificável.**

Os logs mostram situações em que o Hermes precisa repetir ciclos de observação, raciocínio, execução e verificação para tarefas relativamente previsíveis. Em outros casos, esse ciclo se agrava porque uma ferramenta falha, o estado fica incerto ou o agente não consegue acessar um mecanismo que já existe.

Há uma oportunidade importante de redução de custos, mas ela exige separar três situações\:

- **Desperdício de execução\:** a IA realiza repetidamente operações que poderiam ser automatizadas com procedimentos determinísticos.
- **Desperdício de recuperação\:** o agente precisa redescobrir instruções, ferramentas, estado ou procedimentos anteriormente conhecidos.
- **Falha de infraestrutura\:** o Hermes tenta executar corretamente, mas é prejudicado pelo navegador, controlador, permissões ou inconsistência de estado.

A última categoria merece atenção especial: nenhum aperfeiçoamento de prompt ou skill corrige, sozinho, uma ferramenta estruturalmente defeituosa.

## 2\. Medições das 13 sessões

Analisei programaticamente as 14 exportações JSON, desconsiderando a duplicação da sessão *Automatizar envio de mensagem no WhatsApp Web*\.

Mensagens registradas

# 4.093

Respostas de ferramentas

# 2.243

Conteúdo de respostas de ferramentas

# 6,92 mi

Caracteres serializados, incluindo imagens

Raciocínio registrado

# 1,69 mi

Caracteres, não tokens faturados

### Distribuição das ferramentas mais utilizadas

`terminal` e `browser_console` representam juntos **1.335 chamadas, ou 59,5% das respostas de ferramentas registradas**\.

Isso não significa que 59,5% do trabalho seja desperdício. Significa que o maior volume de operações está concentrado em dois canais que merecem uma auditoria de granularidade, retornos, repetições e utilização de scripts.

### Concentração em sessões

| Sessão | Mensagens | Respostas de ferramentas |
|--------|--------|--------|
| Criar banco de dados para controle do WhatsApp | 2.406 | 1.334 |
| Enviar convites de oficina via wa.me | 365 | 194 |
| Enviar agradecimentos pelo WhatsApp | 328 | 175 |
| Abrir PhotoCraft \#2 | 282 | 155 |
| Enviar 9 e-mails pós-evento | 204 | 124 |
| Demais oito sessões | 508 | 261 |
| **Total** | **4.093** | **2.243** |

A sessão de criação do banco representa **59,5% das respostas de ferramentas** do conjunto. Ela também abrange múltiplas subtarefas e retomadas; portanto, não deve ser interpretada como uma única operação homogênea.

**Limitações das medições\:** os campos `token_count` estão sem valores úteis; os intervalos entre o primeiro e o último timestamp incluem interrupções e retomadas; e aproximadamente 2,86 milhões de caracteres serializados vêm de apenas três respostas `computer_use` com conteúdo visual. Não seria correto converter diretamente esse volume em tokens faturados ou em tempo produtivo perdido.

## 3\. O que já existe no código atual

A inspeção foi realizada no dispositivo `DESKTOP-3NA47UH`, no repositório\:

`C:\Github\hermes-agent`

**Estado identificado** (Alterações locais)

Branch `main`

Commit HEAD `e9fe6b38a0`

Há arquivos modificados e não rastreados, incluindo `apps/desktop/electron/ipc/site-ops.ts`\. As alterações já existiam antes da auditoria. Não as modifiquei.

### Inventário de mecanismos reutilizáveis

| Mecanismo | Implementação localizada | Situação |
|--------|--------|--------|
| **Experience Compiler** | `workstation/experience_compiler/` | Implementação existente de captura, compilação, generalização, promoção e composição hierárquica |
| **Site Operations** | `site-ops/` | Framework, mapa, skill global e script WhatsApp já presentes |
| **Browser batch** | `workstation-browser-batch.ts` e `workstation-browser-runtime.ts` | Operações em lote implementadas |
| **Readiness adaptativo** | `tools/browser_workstation.py` | `browser_wait_for_ready` e `whatsapp_wait_for_ready` já definidos |
| **Operações WhatsApp** | `tools/browser_workstation.py` | `whatsapp_search_contact` e `whatsapp_send_message` já definidos |
| **Estado e reconciliação** | `workstation-browser-session-state.ts` | Controle persistente e proteção contra efeitos incertos existentes |
| **Telemetria operacional** | `workstation/telemetry/` | Eventos tipados, observações e persistência SQLite |
| **Telemetria de compactação** | `agent/conversation_compression_telemetry.py` | Registro de tentativas e efeitos de compressão |
| **Motor de campanhas** | `campaign_control.py`, `whatsapp_control.db`, `wa_cdp_batch.py` | Existência registrada nas sessões; versão local atual não auditada diretamente |

**Conclusão importante\:** a arquitetura fundamental para aproveitar as oportunidades já existe. Não é necessário iniciar um novo sistema de automação, outra camada de memória ou outro Experience Compiler.

O principal trabalho deverá ser verificar a confiabilidade dos mecanismos existentes e garantir que o agente os selecione automaticamente.

### Quatro problemas concretos encontrados no `site-ops`

A leitura do código revelou riscos mais específicos que a documentação não deixa evidentes.

**1\. Sucesso declarado sem confirmação do efeito.**

Em `site-ops/scripts/site-ops/whatsapp-web.mjs`, a operação `sendMessage` altera `textContent`, dispara um `KeyboardEvent` sintético e retorna `success: true`\.

Não há confirmação posterior de que a mensagem realmente foi enviada, muito menos entregue. O retorno demonstra apenas que o código chegou ao fim sem uma exceção detectada.

**2\. Seletores e digitação potencialmente incompatíveis com a interface.**

`openChat` procura rótulos em inglês e altera diretamente o `.value` do campo de busca. Já os logs documentam problemas com a digitação programática do WhatsApp e interfaces em português. Além disso, o código clica no primeiro resultado sem uma verificação forte da identidade do destinatário.

**3\. Auto-healing com inconsistências de caminhos e garantias.**

`site-ops/framework/auto-heal.mjs` tenta acessar o script de remapeamento por um caminho que, resolvido a partir do próprio arquivo, não corresponde ao local atual de `site-deep-map.mjs`\.

A documentação também promete cooldown e limite de tentativas por sessão; esses controles não estão implementados no módulo inspecionado. A recuperação automática ainda precisa ser validada.

**4\. Integração IPC aparentemente incompleta.**

Em `apps/desktop/electron/ipc/site-ops.ts`, o handler de `deep-map` passa `'node'` como caminho do script para uma função que já executa o processo Node. Isso produz argumentos de processo incompatíveis com a intenção declarada.

A resolução dos caminhos de `workspaceRoot` também necessita validação no ambiente empacotado. O teste E2E encontrado usa predominantemente invocação direta dos scripts, não uma verificação integral pelo renderer real.

Esses achados são do **código-fonte inspecionado**, não provas de falha reproduzida ao vivo. Não executei as operações, pois isso poderia modificar o estado do aplicativo ou enviar mensagens.

## 4\. Ranking dos oito maiores desperdícios

A classificação combina volume observado, recorrência, gravidade, potencial de reutilização e esforço estimado de correção.

## 01

**Execução fragmentada de operações no navegador**

Impacto muito alto · Recorrência alta · Confiança alta

**Evidência\:** 612 chamadas de `browser_console` nas sessões; 117 apenas em *Enviar convites via wa.me*, 97 em *Enviar agradecimentos* e 271 na sessão de criação do banco.

O agente precisa conduzir manualmente ciclos de navegação, inspeção, decisão e execução. Parte dessas operações já poderia ser absorvida pelos mecanismos nativos do navegador e pelo `site-ops`\.

**Causa provável\:** granularidade excessiva e seleção inconsistente das capacidades disponíveis.

**Código atual\:** mecanismos de batch e readiness existentes; uso automático não demonstrado.

Destino: capacidade operacional + script determinístico + seleção pelo Experience Compiler.

---

## 02

**Bloqueios e reconciliação de operações com efeito incerto**

Impacto muito alto · Recorrência alta · Confiança alta na ocorrência

**Evidência\:** 41 respostas de ferramenta contendo `ControllerRejected`, em 11 sessões; 41 contendo `reconciliation_required`, em sete sessões; e 22 respostas com `timed out after dispatch`, em oito sessões. Essas contagens podem se sobrepor.

A sessão extensa registra inclusive uma intervenção direta em `browser-session.json` para reconhecer uma operação pendente. Isso indica que o caminho de recuperação não era satisfatório naquela execução.

**Causa provável\:** operações sem desfecho inequivocamente reconhecido, combinadas com dificuldade de reconciliação controlada.

**Código atual\:** proteção por admissão, persistência e testes de resiliência existentes. A proteção em si é necessária; o problema é a frequência com que o estado permanece inconclusivo.

Destino: núcleo do Hermes e protocolo de recuperação do Browser.

---

## 03

**Automação nativa existente, mas ainda não demonstrada como confiável**

Impacto alto · Recorrência potencial alta · Confiança alta na inspeção estática

**Evidência\:** os logs registram repetidas tentativas de localizar contatos, digitar mensagens, carregar conversas e confirmar envios. No código atual, o `site-ops` implementa parte desse trabalho, mas apresenta os problemas identificados na seção anterior.

**Causa provável\:** distância entre possuir um script funcional em determinadas condições e possuir uma capacidade operacional validada, descoberta e reutilizada automaticamente.

**Código atual\:** estrutura global presente, mas com lacunas de verificação, caminhos e testes.

Destino: corrigir `site-ops`, preservar sua skill global e integrar ao catálogo de capacidades.

---

## 04

**Releitura de skills e reconstrução de contexto**

Impacto alto · Recorrência alta · Confiança alta no volume

**Evidência\:** 65 registros identificáveis de compactação/handoff, com aproximadamente 1,65 milhão de caracteres. As 45 respostas de `skill_view` somaram aproximadamente 396 mil caracteres. Foram encontrados ainda 31 registros de skills podadas no contexto de handoff.

Esses volumes não equivalem a tokens desperdiçados, mas demonstram circulação expressiva de contexto e recuperação posterior de conhecimento.

**Causa provável\:** carregamento integral de playbooks, seleção tardia e contexto operacional pouco granular.

**Código atual\:** compressor e telemetria existentes. Não há evidência suficiente de recuperação seletiva eficaz para as skills envolvidas.

Destino: seleção de skills, carregamento progressivo e memória operacional do Experience Compiler.

---

## 05

**Campanhas e operações em lote conduzidas com supervisão excessivamente granular**

Impacto alto · Recorrência média/alta · Confiança média/alta

**Evidência\:** há fluxos com múltiplos destinatários e mensagens. O Hermes alterna consultas ao SQLite, comandos de terminal, verificações no DOM, navegação e atualização de status. Na sessão mais extensa aparecem 618 respostas de `terminal`, embora parte corresponda a desenvolvimento legítimo do sistema.

**Causa provável\:** fluxo de execução e controle de campanhas insuficientemente encapsulado ou pouco utilizado.

**Código atual\:** `campaign_control.py`, banco SQLite e `wa_cdp_batch.py` aparecem nos logs. Não foi possível verificar diretamente a versão atual desses componentes fora do repositório principal.

Destino: script determinístico com checkpoints, idempotência e evidência por destinatário; skill para política da campanha.

---

## 06

**Retrabalho provocado por dados de entrada e identidade de contatos**

Impacto alto · Recorrência média · Confiança alta

**Evidência\:** nas sessões de agradecimento e convites, o agente trabalhou com números mascarados ou incompletos enquanto o usuário indicava a existência de dados completos. Houve também uma personalização incorreta em uma mensagem, seguida de necessidade de correção.

**Causa provável\:** validação insuficiente da origem dos dados, resolução de identidade e personalização antes da execução.

**Código atual\:** existem verificações de números e placeholders em `whatsapp_send_message`, mas sua aplicação consistente aos diferentes fluxos não foi demonstrada.

Destino: capacidade operacional de pré-validação e resolução de identidade, integrada ao controle das campanhas.

---

## 07

**Falhas de integração entre navegador, autenticação e aprovação humana**

Impacto alto · Recorrência localizada · Confiança alta no histórico

**Evidência\:** 12 respostas de ferramentas contêm `uncertain_mutation_requires_review`, distribuídas por três sessões. Na primeira tentativa de envio dos e-mails, o agente não conseguiu operar de forma consistente o Gmail autenticado no painel do Desktop e o fluxo precisou ser retomado.

**Causa provável\:** separação entre contextos de autenticação, autorização e controle da interface, associada a problemas de entrega das aprovações.

**Código atual\:** a existência de uma correção definitiva não foi estabelecida nesta inspeção.

Destino: núcleo do Hermes, roteamento de integrações e UX de autorização - não contornar aprovações por scripts.

---

## 08

**Evidência de resultados e economia ainda insuficiente**

Impacto estrutural alto · Recorrência geral · Confiança alta

**Evidência\:** as exportações não fornecem consumo real de tokens. Três respostas visuais `computer_use` representam aproximadamente 2,86 milhões de caracteres serializados. No código do Experience Compiler, `llm_calls_per_verified_outcome` permanece sem valor calculado no trecho inspecionado.

**Causa provável\:** observabilidade distribuída e ausência de uma medição de custo líquido por resultado verificado.

**Código atual\:** o Hermes já dispõe de telemetria tipada e métricas de otimização do navegador; o agregador específico `browser_optimization_metrics.py` vem desativado por padrão e usa estimativas de caracteres por token.

Destino: integrar os dados existentes em benchmarks de tarefa, sem criar um segundo sistema de telemetria.

## 5\. Desperdício versus complexidade necessária

A classificação precisa evitar otimizações que pioram o resultado.

| Comportamento observado | Avaliação |
|--------|--------|
| Conferir o destinatário antes de uma mensagem | Necessário |
| Reabrir o mesmo contato após cada mensagem, sem mudança de contexto | Candidato a desperdício |
| Confirmar o efeito real de um envio | Necessário |
| Repetir dezenas de inspeções sem novos dados | Candidato a desperdício |
| Bloquear uma mutação de resultado desconhecido | Proteção necessária |
| Não oferecer reconciliação e recuperação confiáveis | Deficiência operacional |
| Ler uma skill para conhecer um procedimento novo | Necessário |
| Reler um playbook inteiro após compactações sucessivas | Candidato a desperdício |
| Fazer várias tentativas de autenticação por canais incompatíveis | Falha de integração, não problema de raciocínio |

Quanto aos resultados concretos, os logs documentam, entre outros desfechos, **9 de 9 e-mails enviados e conferidos**, **8 de 9 agradecimentos por WhatsApp concluídos** em uma campanha e **16 envios confirmados** em outra etapa. Esses números não devem ser agregados como uma taxa global de sucesso, pois as sessões incluem várias subtarefas, testes e retomadas com denominadores distintos.

---

## 6\. As três oportunidades de maior retorno

Minha priorização pondera impacto, recorrência, confiança e esforço, sem atribuir uma precisão numérica artificial a custos ainda não medidos.

PRIORIDADE 1 · GANHO MAIS IMEDIATO

**Tornar o `site-ops` confiável e automaticamente reutilizável**

Aproveitar o framework já criado para transformar a operação fragmentada do navegador em chamadas de capacidades com precondições, execução e verificação.

Corrigir os problemas estáticos identificados, evitar sucesso falso e investigar por que o agente não escolhe consistentemente as operações existentes.

**Potencial\:** redução do número de turnos de IA e de chamadas para tarefas comuns. Retorno elevado se a integração funcionar sem introduzir regressões.

---

PRIORIDADE 2 · CONFIABILIDADE E RECUPERAÇÃO

**Resolver a recorrência de operações incertas e reconciliações bloqueantes**

Investigar timeout, admissão, receipts, vinculação de TaskRun, estado persistente e mecanismos formais de reconciliação.

O objetivo é permitir recuperação segura, sem simplesmente repetir mutações cujo resultado seja desconhecido.

**Potencial\:** evitar grandes cadeias de tentativas frustradas e tarefas interrompidas, inclusive fora do WhatsApp.

---

PRIORIDADE 3 · EFICIÊNCIA COGNITIVA

**Seleção antecipada de skills, capacidades e contexto mínimo**

Investigar a recuperação seletiva de playbooks, os casos de compactação e os critérios que levam o agente a procurar ferramentas ou repetir descoberta operacional.

Aproveitar o compressor, corpus, registry e estruturas de seleção existentes, sem antecipar toda a arquitetura futura de ImprovementRuns.

**Potencial\:** reduzir contexto, latência e custo de raciocínio em diferentes classes de tarefa.

### O que não recomendo construir agora

Não recomendo criar outro framework `site-ops`, duplicar o banco de campanhas, desenvolver um novo Browser, acrescentar uma segunda memória operacional ou implementar antecipadamente as quatro especialidades completas de ImprovementRun.

O código já contém infraestrutura suficiente para realizar uma primeira otimização com impacto mensurável. A prioridade deve ser **fechar o caminho entre uma capacidade existente, sua seleção e um resultado realmente comprovado**\.

## 7\. Próxima etapa - Missão 2

A investigação aprofundada deve ficar restrita a três trilhas, sem reabrir o inventário inteiro.

| Trilha | Arquivos prioritários | Questão que precisa ser resolvida |
|--------|--------|--------|
| **A - Site Ops** | `site-ops/framework/`, `site-ops/scripts/site-ops/whatsapp-web.mjs`, `ipc/site-ops.ts`, `tools/browser_workstation.py` | Por que os mecanismos existentes ainda não oferecem uma operação única, segura, verificável e selecionada automaticamente? |
| **B - Browser Runtime** | `workstation-browser-runtime.ts`, `workstation-browser-session-state.ts` e testes de resiliência | O que provoca operações inconclusivas e qual protocolo de reconciliação pode recuperar o fluxo com segurança? |
| **C - Contexto e seleção** | `agent/skill_utils.py`, `agent/conversation_compression_telemetry.py`, `workstation/experience_compiler/` | Por que o agente precisa reler, redescobrir e raciocinar sobre procedimentos que já possuem representação reutilizável? |

Em cada trilha, a Missão 2 deverá verificar a causa-raiz, encontrar os testes existentes, comparar soluções de menor esforço e propor um benchmark antes/depois. O trabalho com scripts de campanha entra inicialmente na trilha A, para evitar investigar em paralelo duas implementações da mesma operação.

**Resultado da Missão 1\:** temos oito problemas classificados, três frentes prioritárias e uma constatação arquitetural relevante: o Hermes já possui boa parte das soluções necessárias, mas ainda precisamos demonstrar sua integração, confiabilidade e reutilização efetiva.

Não foram alterados arquivos, executados envios ou realizadas mutações no Hermes.

## Prompt:
24/10/2026, 16:54:49

# MISSÃO 2 — Diagnóstico de causa-raiz e experimentos

Continue a auditoria do Hermes Work realizada anteriormente, utilizando suas conclusões e as sessões JSON já fornecidas.

**Objetivo:** investigar profundamente as três maiores oportunidades identificadas, até descobrir quais mudanças realmente eliminariam suas causas.

## Método

Para cada oportunidade:

1. Reconstrua um caso representativo: intenção do usuário → decisões do agente → chamadas de ferramentas → resultados → tentativas adicionais → desfecho.
2. Use o Remote Desktop Commander para examinar as implementações correspondentes no repositório local e nas skills instaladas.
3. Investigue se o custo vem de raciocínio desnecessário, seleção incorreta, ausência de primitiva operacional, falha de runtime, persistência inadequada, conhecimento insuficiente ou integração defeituosa.
4. Localize funções, classes, módulos e arquivos relevantes. Verifique a implementação real, não apenas a documentação.
5. Formule no máximo três hipóteses de correção por problema e escolha a mais promissora.
6. Quando possível, valide as hipóteses com inspeções, testes existentes, simulações ou experimentos isolados, sem modificar o repositório.

Considere soluções híbridas, como skill global de site que invoca uma capacidade operacional implementada com script determinístico.

**Atenção:** distinga falhas que exigem correção na infraestrutura de problemas que podem ser resolvidos por automações. Não tente contornar CSP, permissões, aprovações ou mecanismos de reconciliação por manipulação manual de estado.

## Entregáveis

Para cada uma das três oportunidades, apresente:

- Evidência observada e causa-raiz confirmada ou hipótese ainda não comprovada.
- Local exato no código e implementação existente que pode ser reutilizada.
- Comparação de alternativas, com trade-offs de tokens, velocidade, confiabilidade e manutenção.
- Solução recomendada, esforço estimado, dependências, riscos e estratégia de validação.
- Critério objetivo que demonstrará que o desperdício foi eliminado ou reduzido.

Diferencie claramente **fatos verificados, inferências e questões pendentes**.

Não implemente ainda. Ao final, determine quais correções devem entrar primeiro e quais não justificam investimento.

## Response:
24/10/2026, 16:55:02 · gpt-6-thinking

Vou aprofundar as três frentes já priorizadas: `site-ops` e automação determinística, reconciliação do Browser Runtime, e seleção de skills/contexto. Vou confrontar episódios reais dos JSONs com as funções atuais do Hermes, usando inspeções somente de leitura e testes isolados quando forem seguros. Ao final, separarei causas confirmadas, hipóteses pendentes e correções com maior retorno.

A investigação do Browser Runtime mostrou uma distinção relevante: o bloqueio de operações incertas é uma proteção deliberada, não simplesmente um bug a remover. O código já reconhece alguns casos comprovadamente não executados e possui persistência de admissões e recibos. O ponto a resolver é onde a classificação ou a reconciliação falha — sem permitir que uma ação possivelmente executada seja repetida por engano.

> **Planejando a análise**
>
> Vou ler os arquivos montados e verificar manualmente os dados e estatísticas anteriores, sem alterar o repositório. Também vou reconstruir eventos, chamadas e erros para confirmar se as conclusões estão corretas.
>
> **Planejou a análise**
>
> 
>
> **Listando arquivos montados e verificando sessões**
>
>
> **Listou arquivos montados e verificou sessões**
>
> 
>
> **Verificou remotamente o dispositivo agora**
>
> 
>
> **Analisando sessões e padrões de chamadas**
>
>
> **Analisou sessões, padrões de chamadas e cronologias representativas**
>
> 
>
> **Analisados dados remotos, arquivos compactados e caminhos de autoajuste**
>
> 
>
> **Analisando falhas e recuperação do runtime**
>
>
> **Analisou falhas e recuperação do runtime**
>
> 
>
> **Verificou caminhos do renderer, ACKs e seleção remota**
>
> 
>
> **Analisando reconciliação e seleção de habilidades**
>
>
> **Revisando o diagnóstico técnico**
>
> Estou identificando possíveis falhas no código: seletores frágeis, injeção em scripts, caminhos de diretório possivelmente incorretos, execução de comandos malformada, autocorreção ineficaz e incompatibilidade entre nomes de artefatos.
>
> **Revisado o diagnóstico técnico**
>
> 
>
> **Analisou reconciliação e seleção de habilidades**
>
> 
>
> **Validando hipóteses**
>
> Vou confirmar essas suspeitas com verificações estáticas e testes isolados de leitura: seletores reais, caminhos resolvidos, descoberta de habilidades e coerência dos artefatos, sem executar ações externas ou modificar arquivos.
>
> **Validou hipóteses**
>
> 
>
> **Consolidando evidências**
>
> As verificações devem separar métricas por tarefa, não por sessão inteira. Também estou tratando testes que enviam mensagens como inadequados para CI e distinguindo defeitos confirmados de riscos ainda não demonstrados.
>
> **Consolidou evidências**
>
> 
>
> **Avaliou automação, governança, testes, habilidades e roteamento**
>
> 
>
> Pensou por 8m 51s

# MISSÃO 2 — Diagnóstico de causa-raiz do Hermes Work

Análise das 13 sessões distintas, com inspeção somente de leitura do repositório `C:\Github\hermes-agent`, branch `main`, commit `e9fe6b38a0` e alterações locais preexistentes.

## 1\. Diagnóstico executivo

A investigação já permite estabelecer uma distinção importante: **o Hermes não sofre principalmente por falta de scripts, skills ou capacidades operacionais. Sofre porque parte desses mecanismos está incompleta, não está suficientemente integrada ao fluxo de decisão do agente ou não oferece garantias adequadas sobre o resultado.**

Encontrei três causas centrais, com graus diferentes de comprovação\:

| Frente | Diagnóstico principal | Confiança |
|--------|--------|--------|
| **A — Site Ops** | A automação determinística existe, mas tem lacunas no contrato de execução, verificação e integração com o agente | Alta |
| **B — Browser Runtime** | Falhas e timeouts podem produzir efeitos incertos; o sistema protege contra repetição, mas a recuperação ainda merece investigação | Alta na ocorrência, média na causa completa |
| **C — Skills e contexto** | O agente carrega conhecimento extenso e repetitivo, enquanto a recuperação e a seleção de capacidades ainda não exploram plenamente os mecanismos existentes | Alta no desperdício observado, média na atribuição causal |

Não houve envio de mensagens, modificações no repositório ou tentativas de contornar permissões e reconciliação.

## 2\. Frente A — Site Ops: capacidades existentes, mas execução ainda frágil

### Caso reconstruído: envio dos convites via `wa.me`, 23 de outubro

1. **Intenção\:** retomar o envio de três mensagens para 15 contatos pendentes, sem salvá-los, confirmando cada envio.
2. **Preparação\:** o Hermes leu o status da campanha e carregou a skill `whatsapp-email-campaign-control`, a referência do DOM e o script `wa_cdp_batch.py`\.
3. **Execução\:** tentou abrir conversas por links diretos, localizar o composer e utilizar CDP. Alternou navegação, inspeção do DOM, snapshots e terminal.
4. **Falhas\:** composer indisponível em certas tentativas, endpoint CDP sem resposta JSON válida e operações posteriores bloqueadas por reconciliação pendente.
5. **Resultado\:** o histórico registra uma etapa interrompida sem completar os 15 destinatários previstos.

A sessão contém **117 respostas de `browser_console` e 21 de `browser_navigate`**\. Essas chamadas não são todas desperdício, mas mostram o volume de interação necessário para executar e diagnosticar uma operação recorrente.

### Causa-raiz confirmada no código

O repositório possui o framework `site-ops` com mapa do WhatsApp, script determinístico, cliente CDP e IPC do Desktop. Entretanto, a inspeção revelou\:

**1\. A operação `send-message` declara sucesso sem confirmar envio.**

Arquivo: `site-ops/scripts/site-ops/whatsapp-web.mjs`

A função `sendMessage()` altera o conteúdo do composer, dispara um evento sintético de teclado e retorna `success: true`\.

O código não comprova que o WhatsApp aceitou a mensagem, que a conversa correta estava ativa ou que ocorreu a transição esperada no histórico.

**2\. A busca pelo contato não garante identidade.**

No mesmo arquivo, `openChat()` seleciona o primeiro resultado encontrado. A correspondência nominal não é confirmada antes de abrir a conversa.

Isso representa risco de envio ao destinatário errado, sobretudo com nomes semelhantes.

**3\. O caminho de auto-healing apresenta inconsistências.**

Arquivo: `site-ops/framework/auto-heal.mjs`

O caminho utilizado para localizar o script de remapeamento não corresponde à localização real do script. Também há divergências entre os nomes de artefatos gerados por domínio e os procurados pelo mecanismo de recuperação.

Uma alteração local preexistente acrescentou cooldown de 30 segundos, mas isso não corrige, por si só, as inconsistências de caminhos.

**4\. A integração IPC ainda contém uma falha identificável.**

Arquivo: `apps/desktop/electron/ipc/site-ops.ts`

O handler `deep-map` utiliza incorretamente a rotina de execução de processos, passando `'node'` como se fosse o arquivo de script.

Esse caminho precisa ser corrigido e validado por um teste que exercite o IPC real, em vez de testar somente o CLI.

**5\. A disponibilidade para o agente não está demonstrada.**

O playbook global `whatsapp-web-ops` está em `site-ops/skills/`, mas a resolução normal de skills usa outros diretórios. A integração pelo preload expõe uma API ao renderer; isso não significa automaticamente que o modelo tenha acesso a ela como ferramenta selecionável.

Esse é um candidato forte à causa do agente continuar escolhendo sequências manuais.

**Conclusão da frente A\:** o problema não justifica construir um novo `site-ops`\. Justifica corrigir o existente, estabelecer contratos verificáveis e integrar sua descoberta e execução ao Hermes.

### Validação isolada da frente A

Executei verificações **somente de leitura**, sem acessar uma conversa ou enviar mensagens.

| Verificação | Resultado |
|--------|--------|
| Elementos de busca com rótulo em inglês aceitos por `openChat()` | 0 |
| Elementos de busca com rótulo `Pesquisar` no mapa principal | 1 |
| Elementos com `data-testid="contact-item"` no mapa principal | 0 |
| Caminho real do script `site-deep-map.mjs` | Existe |
| Caminho utilizado por `auto-heal.mjs` | Não existe |
| Artefato `site-map-web-whatsapp-com.json` | Existe |
| Artefato `site-map-whatsapp-web.json`, procurado pelo auto-healing | Não existe |

Esses resultados confirmam **incompatibilidades concretas entre o script, o mapa e a recuperação**, independentemente de qualquer hipótese sobre desempenho do modelo.

A ausência de `contact-item` no mapa não prova que o seletor jamais apareça em outro estado da interface, mas demonstra que seu uso não está validado pelo mapa inspecionado.

### Alternativas para a frente A

| Alternativa | Custo de IA | Confiabilidade | Avaliação |
|--------|--------|--------|--------|
| Melhorar somente a skill existente | Baixo esforço inicial, mas mantém múltiplas decisões do modelo | Limitada pelas falhas de execução | Insuficiente |
| Corrigir apenas o script CDP | Poucas chamadas de IA | Melhora operações isoladas, mas não resolve autorização e seleção | Solução parcial |
| **Reaproveitar `site-ops` como capacidade governada pelo runtime** | Maior economia potencial por tarefa repetida | Permite contratos, verificação e recuperação | **Recomendada** |

A terceira opção deve aproveitar `workstation/control_plane/router.py`, o registry de capacidades e a política de execução existentes. Não recomendo disponibilizar ao agente um caminho CDP direto que contorne controle humano, permissões, identidade da TaskRun ou mecanismos de reconciliação.

**Esforço estimado\:** baixo a médio para corrigir os defeitos localizados; médio para consolidar a integração segura como capacidade reutilizável.

**Critérios de aceite propostos\:** selecionar a operação nativa sem redescoberta manual, resolver corretamente o contato, realizar uma execução controlada em ambiente de teste, confirmar a pós-condição por evidência independente e jamais retornar `success` para um efeito não comprovado.

---

## 3\. Frente B — Browser Runtime: onde a recuperação se torna um gargalo

### Caso reconstruído: agradecimentos pelo WhatsApp, 21 de outubro

O agente tentava enviar mensagens personalizadas aos participantes de um evento. Durante a operação\:

1. Um `browser_click` retornou `target_obscured`\.
2. A operação ficou associada a uma admissão persistente sem confirmação conclusiva.
3. Cliques subsequentes receberam `prior_operation_requires_reconciliation`\.
4. O agente precisou continuar investigando o estado, em vez de prosseguir normalmente pelo fluxo de envios.
5. A sessão sofreu também timeout posterior em `browser_console`\.

No conjunto das 13 sessões, aparecem **33 respostas contendo `prior_operation_requires_reconciliation` e 22 contendo `timed out after dispatch`**\. Essas categorias podem se sobrepor e representam ocorrências textuais, não 55 falhas independentes.

### O que o código comprova

Examinei\:

- `apps/desktop/electron/workstation-browser-runtime.ts`
- `apps/desktop/electron/workstation-browser-session-state.ts`
- Os caminhos de admissão, recibos e terminais `NOT_DISPATCHED`\.

O runtime possui um mecanismo de **admissão durável anterior à mutação**, que registra identidade, ação e digest dos argumentos. Antes de permitir uma nova mutação, ele verifica se existe outra operação da mesma execução com resultado pendente.

Esse comportamento é correto como princípio: executar uma mutação novamente quando o resultado anterior é desconhecido pode causar envios duplicados ou outras alterações indevidas.

Também confirmei que já há um caminho de recuperação para certos erros comprovadamente anteriores ao efeito, incluindo referências obsoletas, ausentes ou ambíguas. Nesses casos, o runtime pode registrar um terminal `NOT_DISPATCHED`\.

Além disso, o código associa recibos persistidos às admissões para marcar reconhecimento. **Portanto, a hipótese de que o Hermes simplesmente nunca reconhece operações concluídas foi descartada.**

O que permanece problemático é a capacidade de distinguir e recuperar os estados intermediários, especialmente quando a ação foi parcialmente despachada ou o controlador perdeu a resposta.

### Três hipóteses

**H1 — Classificação incompleta das falhas pré-efeito.** Alguns erros podem permanecer inconclusivos mesmo quando uma observação confiável permitiria provar que nenhuma mutação ocorreu. A hipótese é plausível, mas requer análise da ordem exata de resolução, foco, scroll, clique e dispatch.

**H2 — Reconciliação insuficientemente acessível à execução.** O controle de estado existe, mas as sessões demonstram que o agente frequentemente não conseguiu transformá-lo em uma decisão segura de recuperação. Esta é a hipótese mais promissora.

**H3 — Timeouts em diferentes camadas produzem perda de causalidade.** A resposta pode se perder depois de o Chromium já ter executado a ação. Nesse caso, aumentar timeouts pode reduzir ocorrências, mas não resolve a necessidade de evidência e reconciliação.

### Solução recomendada

Reforçar o **protocolo de reconciliação por resultado comprovado**, não retirar a trava.

O caminho deverá distinguir explicitamente\:

**Efeito verificado** — concluir e liberar a próxima ação.

---

**Não executado, com prova** — registrar terminal e permitir nova operação.

---

**Efeito desconhecido** — bloquear repetição e oferecer reconciliação ou revisão humana.

Para operações externas, um ACK local deve continuar sendo tratado como recibo de execução, não como prova do resultado remoto.

**Esforço estimado\:** médio. A persistência e a política já existem; o esforço principal está nas transições de estado, evidências, UX de recuperação e testes de crash/timeout.

**Critério de aceite\:** uma falha comprovadamente pré-efeito não bloqueia permanentemente a TaskRun; uma mutação de resultado desconhecido nunca é repetida automaticamente; e qualquer desbloqueio apresenta evidência auditável.

### Por que não recomendo simplesmente aumentar os timeouts?

Um timeout pode ocorrer antes ou depois de o navegador ter produzido um efeito.

Se o Hermes apenas esperar mais tempo, algumas falhas podem desaparecer, mas outras continuarão inconclusivas. Se repetir automaticamente a operação, pode duplicar um envio.

A investigação também confirmou que já existem testes de recuperação e resiliência. A próxima etapa deve acrescentar cobertura para os casos observados nas sessões, em vez de reescrever a persistência.

| Alternativa | Vantagem | Limitação |
|--------|--------|--------|
| Aumentar timeout e retries | Implementação simples | Não resolve resultados desconhecidos |
| Tratar mais erros como `NOT_DISPATCHED` | Recuperação rápida | Perigoso sem prova de ausência de efeito |
| **Reconciliação tipada com verificador específico por operação** | Recuperação segura e reutilizável | Exige integração com verificadores e testes |

**Dependências\:** `workstation-browser-runtime.ts`, `workstation-browser-session-state.ts`, contratos de verificação e ferramentas de apresentação de estado ao agente.

**Risco prioritário\:** um erro de classificação criar falsos negativos e permitir a duplicação de ações externas.

A correção deve ser testada com falhas injetadas em pontos diferentes: antes da resolução do elemento, depois de adquirir foco, antes do dispatch, depois do dispatch e durante a persistência do recibo.

---

## 4\. Frente C — Skills, seleção e reconstrução de contexto

### Caso reconstruído: retomada de campanhas do WhatsApp

Na sessão *Enviar convites de oficina via wa.me*, o agente consultou a skill `whatsapp-email-campaign-control` e seus arquivos complementares.

Entre os materiais carregados estavam\:

- Playbook principal: aproximadamente 25,8 mil caracteres.
- Referência do DOM: aproximadamente 6,5 mil caracteres.
- Script `wa_cdp_batch.py`\: aproximadamente 11 mil caracteres.

Após a compactação, esses conteúdos apareceram como `SKILL_PRUNED`\. Posteriormente, o agente voltou a consultar a skill principal.

Na sessão de criação do banco, o padrão também se repetiu com skills de WhatsApp, e-mail e Google Workspace.

### Medição do problema

Respostas de `skill_view`

# 45

Conteúdo serializado

# 396 mil

Caracteres retornados

Identifiquei 20 respostas de ferramentas com marcadores explícitos `SKILL_PRUNED`\. Não é correto considerar todo esse conteúdo desperdício: parte corresponde a contexto útil e parte a marcadores compactos. A medição de economia líquida ainda depende da telemetria do provedor.

### Causa confirmada: política de recarregamento

No arquivo `agent/prompt_builder.py`, a regra `SKILLS_GUIDANCE` instrui explicitamente o agente a recarregar uma skill cujo conteúdo foi perdido na compactação.

Isso explica parte da repetição: **o comportamento observado não é necessariamente uma falha de obediência do modelo; ele está seguindo uma política do próprio Hermes.**

Essa política tem uma justificativa — não permitir que o agente execute um procedimento baseado em instruções que já não estão acessíveis.

O desperdício potencial está em precisar recuperar um documento inteiro quando o agente talvez necessite apenas de uma operação, uma referência ou uma regra.

### Outra descoberta: o roteador já possui seleção determinística e System-1

Inspecionei `workstation/control_plane/router.py`, especialmente `CapabilityRouter.route()`\.

O fluxo existente já contempla\:

1. Verificação de mutações incertas pendentes.
2. Verificação de objetivo já satisfeito.
3. Busca de capacidades promovidas.
4. Ranqueamento de candidatas via System-1 quando aplicável.
5. Requisitos de política, autoridade e execução verificável.

Também existe `tools/tool_search.py`, com catálogo e recuperação lexical de ferramentas.

Logo, **não é necessário construir outro roteador de capacidades ou introduzir imediatamente BM25, embeddings e LAYA para resolver este problema**\.

A questão central é se os mecanismos de automação desejados estão devidamente registrados, descritos e acessíveis ao roteador, e se o agente os recupera antes de recorrer a sequências de ferramentas de baixo nível.

### Três hipóteses de melhoria

| Hipótese | Fundamentação | Prioridade |
|--------|--------|--------|
| **H1 — Recuperação granular de skills** | Playbooks extensos precisam ser relidos após compactações | Alta |
| **H2 — Registro incompleto das capacidades de `site-ops`** | A skill existe no código-fonte, mas sua disponibilização automática pelo catálogo normal não foi demonstrada | Alta |
| **H3 — Seleção multimétodo insuficiente** | O roteador já oferece seleção exata e System-1, mas pode não recuperar bons candidatos em certas formulações | Média, ainda não comprovada |

### Solução recomendada

Implementar a menor integração capaz de permitir que o Hermes descubra e reutilize a operação correta, com três responsabilidades separadas\:

**Catálogo resumido** Quando usar

Metadados compactos de skills e capacidades, incluindo operações disponíveis, requisitos e custos conhecidos.

---

**Recuperação seletiva** O que carregar

Trazer somente o procedimento, contrato ou referência necessários para a execução atual.

---

**Capability Router** O que executar

Selecionar uma capacidade promovida e verificar autoridade, estado, precondições e resultado.

Não recomendo remover a regra `SKILL_PRUNED` para economizar tokens. A otimização é preservar acesso seguro ao conhecimento necessário com menor volume de contexto, e não deixar o agente agir com instruções ausentes.

### Comparação das alternativas

| Abordagem | Custo/latência | Confiabilidade | Manutenção |
|--------|--------|--------|--------|
| Aumentar limite de contexto | Pode reduzir algumas compactações, mas aumentar custo | Não corrige seleção | Simples inicialmente |
| Resumir manualmente todas as skills | Pode reduzir tokens | Risco de perder regras operacionais | Alto ao longo do tempo |
| **Catálogo compacto + recuperação sob demanda + roteador existente** | Menor custo recorrente potencial | Preserva contratos completos quando necessários | Boa, se usar o índice existente |
| Implementar já toda a seleção multimétodo | Custo inicial alto | Ganho ainda não demonstrado | Complexa |

**Esforço estimado\:** baixo a médio para integrar descoberta e carregamento seletivo; alto para um sistema novo e abrangente de seleção multimétodo.

**Critérios de aceite\:** a mesma tarefa deve encontrar a capacidade correta sem consultas exploratórias desnecessárias, manter acesso às regras obrigatórias e reduzir o volume de contexto carregado. A diminuição de chamadas LLM deverá ser medida, não presumida.

---

## 5\. Um risco adicional: automação determinística não significa execução autorizada

O `site-ops` atual utiliza CDP diretamente para operar páginas. Isso pode reduzir a latência, mas existe uma diferença arquitetural entre executar um script e executar uma **capacidade operacional governada pelo Hermes**\.

No handler IPC inspecionado, não identifiquei uma verificação explícita equivalente ao conjunto de garantias do `CapabilityRouter`\: autoridade da TaskRun, autorização humana, ausência de mutações incertas e verificação de pós-condições.

Isso não prova a ausência de controles em todas as camadas do aplicativo. Significa que essa integração ainda não foi demonstrada no caminho inspecionado.

A correção deve impedir que otimizar o navegador crie uma via paralela, com menos garantias que as ferramentas nativas.

Outro problema está em `withAutoHealing()`\: a implementação intercepta qualquer erro de execução, não apenas falhas demonstradas de seletor. Assim, um problema de CDP, permissão ou controlador pode provocar uma tentativa de remapeamento que não resolverá sua causa.

**Recomendação\:** o mecanismo deve classificar o erro antes de decidir entre recuperar seletor, reconectar, reconciliar, solicitar intervenção humana ou simplesmente interromper a operação.

## 6\. Plano de validação das três hipóteses principais

Não executei testes E2E que enviam mensagens ou modificam o aplicativo. A validação realizada até aqui é estática e baseada em inspeção de código, dados das sessões e verificações inertes dos arquivos locais.

Os próximos testes devem produzir evidência mensurável.

| Frente | Experimento controlado | Critério de sucesso |
|--------|--------|--------|
| **A — Site Ops** | Simular abrir contato → compor → enviar → verificar em uma interface controlada | Identidade correta, pós-condição comprovada, nenhuma declaração falsa de sucesso |
| **B — Reconciliação** | Injetar falhas antes e depois do dispatch, inclusive durante a persistência | Nenhuma repetição insegura; liberação quando comprovado `NOT_DISPATCHED` |
| **C — Seleção** | Reproduzir tarefas reais com catálogo atual versus recuperação seletiva | Mesma correção operacional, menos consultas e menor custo de contexto |

### Metas experimentais sugeridas

São critérios de avaliação propostos, não ganhos observados.

Chamadas de ferramentas por tarefa repetitiva

# −50%

Meta inicial para a frente A

Falsos sucessos e envios duplicados

# 0

Exigência de segurança

Redução de contexto operacional

# −40%

Meta para a frente C, mantendo as regras necessárias

Resultados desconhecidos repetidos automaticamente

# 0

Exigência de segurança

Um cuidado de mensuração: não se deve comparar uma chamada simples de `site-ops` contra dezenas de ferramentas se a primeira tiver deixado de verificar o resultado. O benchmark precisa comparar **tarefas concluídas com o mesmo nível de evidência e segurança**\.

## 7\. Decisões de prioridade

Depois da investigação técnica, minha ordem recomendada ficou mais específica\:

| Ordem | Correção | Esforço preliminar | Retorno esperado |
|--------|--------|--------|--------|
| 1 | Corrigir seletores, caminhos, classificação de auto-healing e testes isolados do `site-ops` | Baixo | Alto, habilita o restante |
| 2 | Fortalecer reconciliação e contratos de verificação para mutações | Médio | Muito alto em confiabilidade |
| 3 | Integrar `site-ops` ao caminho governado de capacidades e selecionar automaticamente | Médio | Muito alto em reutilização |
| 4 | Tornar o carregamento de skills mais granular e econômico | Baixo–médio | Alto e transversal |
| 5 | Expandir seleção multimétodo, embeddings e ImprovementRuns | Alto | Ainda não demonstrado |

Essas estimativas são qualitativas, pois não foram executados benchmarks do código corrigido.

### O que deve ser reaproveitado

**`site-ops` existente\:** corrigir, não substituir.

**`CapabilityRouter` e `OperationalCapabilityRegistry`\:** registrar e selecionar capacidades usando os contratos já implementados.

**`browser_batch_actions` e ferramentas de readiness\:** aproveitar antes de construir novas primitivas.

**`whatsapp_control.db`, `campaign_control.py` e `wa_cdp_batch.py`\:** manter o controle de campanhas separado das capacidades genéricas de navegador, evitando duplicação de estado.

**Telemetria existente\:** instrumentar custo por resultado verificado, em vez de criar outro pipeline de eventos.

### O que não justifica investimento agora

Não recomendo um framework novo de automação de sites, uma reestruturação geral do Experience Compiler, uma nova memória de skills nem uma expansão antecipada de todos os ImprovementRuns.

Também não recomendo remover as barreiras de reconciliação, utilizar CDP para contornar a política do Browser ou diminuir os requisitos de verificação para demonstrar economia artificial.

---

## 8\. Pendências que permanecem abertas

Apesar dos diagnósticos, ainda existem quatro questões que devem ser resolvidas antes de considerar a arquitetura definitivamente validada\:

1. **Disponibilidade real do `site-ops` ao modelo\:** confirmar o percurso completo do catálogo até o dispatcher, inclusive na instalação empacotada.
2. **Origem dos timeouts\:** correlacionar eventos do controlador, Electron, TaskRun e recibos para determinar onde a resposta se perde.
3. **Cobertura de testes\:** os testes E2E encontrados incluem operações potencialmente mutantes e verificações de sucesso pouco rigorosas. Precisam de mocks e asserts de pós-condições.
4. **Ganho econômico real\:** correlacionar logs com contagens de tokens do provedor, duração efetiva e resultados verificados.

Essas são pendências de comprovação, não motivos para redesenhar o sistema do zero.

## 9\. Recomendação para a Missão 3

A etapa seguinte não precisa investigar tudo novamente. Ela deve converter os diagnósticos em um plano de implementação de baixo acoplamento.

**Minha escolha para a primeira implementação seria corrigir e testar a cadeia `site-ops` em modo isolado, sem permitir envios reais**, com o seguinte escopo: resolução de seletores, caminhos de auto-healing, classificação de falhas, contrato de resultados e testes de integração IPC.

Depois disso, a integração com o fluxo de execução governado dependerá da validação dos mecanismos de reconciliação da frente B. A melhoria de seleção e carregamento de skills poderá então reutilizar uma capacidade cuja confiabilidade já tenha sido demonstrada.

**Conclusão da Missão 2\:** identificamos defeitos reproduzíveis por inspeção na automação nativa, confirmamos que o bloqueio de operações incertas é um mecanismo de proteção legítimo e encontramos uma política explícita que explica parte da releitura de skills. O maior retorno está em consolidar a infraestrutura já existente: **executar com menos intermediação de IA, mas com identidade, autorização e resultado verificáveis**\.

O repositório permanece sem alterações realizadas por esta auditoria.

## Prompt:
24/10/2026, 17:05:04

# MISSÃO 3 — Decisões arquiteturais para otimização do Hermes Work

Com base na auditoria das sessões e na investigação técnica das três maiores oportunidades, produza um plano de correções priorizado pelo maior resultado com o menor esforço.

**Objetivo:** decidir precisamente o que será implementado, em qual camada do Hermes e em qual ordem.

## Critérios arquiteturais

Considere cinco alternativas:

1. **Script determinístico:** procedimentos parametrizáveis, repetitivos, testáveis e com efeitos controláveis.
2. **Skill global (`site_ops` ou equivalente):** playbook específico de site, com conhecimento e estratégias reutilizáveis.
3. **Capacidade operacional:** primitiva universal, reutilizável por diversas skills, com interface tipada e contrato verificável.
4. **Correção do núcleo:** mudanças necessárias no runtime, navegador, ferramentas, permissões, persistência ou execução.
5. **Experience Compiler:** aprendizagem, seleção hierárquica, composição, versionamento, promoção, autocorreção e acompanhamento de desempenho.

Permita arquiteturas híbridas, mas evite camadas e abstrações que não tragam benefício mensurável.

Considere o modelo de aprendizagem progressiva do Hermes: o agente executa a tarefa e melhora sua execução futura, com preferência por seleção barata e determinística/System-1 e escalada ao System-2 somente quando necessário.

## Entregáveis

Produza um plano contendo:

- As **3 primeiras mudanças recomendadas**, com justificativa de impacto, esforço, recorrência, risco e confiança.
- O que reutilizar, alterar, criar ou eliminar, indicando arquivos e módulos.
- A relação entre skills permanentes, scripts, capacidades e o Experience Compiler.
- Contratos de entrada/saída, critérios de sucesso, prevenção de duplicações, recuperação de falhas e mecanismos de rollback.
- Benchmarks de antes/depois: latência, chamadas, tokens reais quando disponíveis, taxa de sucesso e intervenção humana.
- Ordem exata de implementação, dependências e testes de aceite.

Classifique cada melhoria como **quick win**, melhoria estrutural ou investimento de longo prazo.

Priorize obter ganho mensurável rapidamente. Não proponha uma refatoração geral quando uma correção localizada resolver o problema.

Não faça alterações ainda. Termine com a recomendação de **uma única implementação inicial**, suficientemente delimitada para ser executada e testada na próxima etapa.

## Response:
24/10/2026, 17:05:28 · gpt-6-thinking

> **Estruturando o plano**
>
> Estou preparando um plano independente, não necessariamente um documento formal. Vou separar fatos comprovados de hipóteses, preservar mudanças existentes e tratar operações externas com contratos tipados, políticas e resultados verificáveis.
>
> **Priorizando mudanças**
>
> Estou escolhendo uma primeira implementação pequena: corrigir o caminho determinístico de leitura e o artefato do site, adicionar testes offline e manter mutações bloqueadas até haver verificação explícita. Depois, considero reconciliação, descoberta e integração com habilidades nativas.
>
> **Definindo a implementação**
>
> Estou separando a execução em três fases: estabilizar leituras e caminhos, criar um portão seguro para mutações com reconciliação e, por fim, integrar descoberta de capacidades e recuperação progressiva, medindo impacto antes de ampliar o escopo.
>
> **Estimando execução**
>
> Estou mantendo estimativas relativas: primeira correção, cerca de meio a um dia; reconciliação de mutações, dois a cinco dias; integração de descoberta, um a três dias. Rollback usa commits isolados, ativação gradual e preserva estados existentes.
>
> **Estruturou o plano, priorizou mudanças e estimou a implementação**
>
> 
>
> Pensou por 1m 35s

# MISSÃO 3 — Plano arquitetural de otimização do Hermes Work

Decisão técnica baseada nas Missões 1 e 2 · Repositório analisado: `C:\Github\hermes-agent` · Referência: `main` / `e9fe6b38a0`

## 1\. Decisão executiva

**Recomendo otimizar o Hermes em três intervenções incrementais, aproveitando a infraestrutura já existente, sem criar um novo sistema de automação ou aprendizagem.**

A principal mudança arquitetural será transformar as automações disponíveis em **capacidades selecionáveis, governadas pelo runtime e verificáveis**, para que o modelo deixe de executar manualmente operações repetitivas.

MUDANÇA 1 · QUICK WIN

**Estabilizar o `site-ops` existente**

Corrigir incompatibilidades entre scripts, mapas, caminhos, tratamento de erros e contratos de resultado. Começar por operações somente de leitura.

---

MUDANÇA 2 · ESTRUTURAL

**Unificar execução, verificação e reconciliação**

Garantir que operações determinísticas respeitem os mecanismos de autorização, persistência, identidade e recuperação do Browser Runtime.

---

MUDANÇA 3 · EFICIÊNCIA COGNITIVA

**Integrar capacidades e skills à seleção econômica**

Fazer o agente descobrir e reutilizar primeiro o procedimento mais barato e confiável, carregando somente o conhecimento necessário.

A sequência é intencional: **primeiro tornar a operação correta, depois torná-la segura e finalmente torná-la automaticamente selecionável**\.

## 2\. Priorização por impacto e esforço

Estimativas qualitativas de engenharia, não benefícios já comprovados.

| Critério | 1\. Site Ops | 2\. Runtime | 3\. Seleção |
|--------|--------|--------|--------|
| Impacto esperado | Alto | Muito alto | Muito alto |
| Recorrência | Alta | Alta | Alta |
| Esforço | Baixo–médio | Médio–alto | Médio |
| Risco técnico | Baixo–médio | Alto | Médio |
| Confiança no diagnóstico | Alta | Média–alta | Média–alta |
| Reutilização | Sites automatizados | Qualquer mutação no Browser | Várias classes de tarefas |
| Estimativa inicial | 1–2 dias | 2–5 dias | 1–3 dias |

As estimativas pressupõem reaproveitamento das implementações atuais e não incluem grandes regressões descobertas durante testes.

**A maior economia potencial vem da combinação das mudanças 2 e 3**, mas a primeira intervenção oferece uma oportunidade mais barata de verificar se o caminho operacional funciona.

---

## 3\. Arquitetura de referência

O modelo recomendado é híbrido, com responsabilidades bem delimitadas.

**Intenção do usuário**

Objetivo, restrições e autorização

**Seleção de procedimento**

Catálogo → contrato/exato → System-1 → System-2 quando necessário

**Capability Router + política**

Identidade, precondições, autorização, estado e prevenção de duplicações

**Execução determinística**

Capacidade operacional → `site-ops` → Browser Runtime

**Verificação e reconciliação**

Efeito comprovado, não executado ou desconhecido

**Telemetria + Experience Compiler**

Capturar evidências, reconhecer oportunidades e melhorar a próxima execução

### Responsabilidade de cada camada

| Camada | Responsabilidade | Exemplo |
|--------|--------|--------|
| Script determinístico | Realizar operações parametrizadas | Localizar um campo e preencher um valor |
| Skill global | Ensinar procedimentos e particularidades do site | Como identificar conversas no WhatsApp |
| Capacidade operacional | Expor uma operação com contrato, estado e verificador | Abrir conversa do contato correto |
| Núcleo do Hermes | Garantir autorização, execução, receipts e recuperação | Não repetir mutação incerta |
| Experience Compiler | Aprender o que reutilizar, compor e aperfeiçoar | Reconhecer uma sequência recorrente e propor uma capacidade |

A skill **não deve implementar um executor paralelo**, e o Experience Compiler **não deve substituir o runtime ou a política de autorização**\.

---

# 4\. Mudança 1 — Estabilização do Site Ops

(Quick win)

### O que implementar

Consolidar o `site-ops` como implementação determinística confiável, eliminando primeiro os defeitos confirmados na Missão 2.

| Ação | Arquivo/módulo |
|--------|--------|
| Corrigir localização do script de remapeamento | `site-ops/framework/auto-heal.mjs` |
| Uniformizar identificação de slug e artefatos | `site-ops/scripts/site-deep-map.mjs` e `auto-heal.mjs` |
| Evitar auto-healing para erros não relacionados a seletores | `site-ops/framework/auto-heal.mjs` |
| Corrigir invocação do `deep-map` no IPC | `apps/desktop/electron/ipc/site-ops.ts` |
| Corrigir seleção dos elementos e validação de alvo | `site-ops/scripts/site-ops/whatsapp-web.mjs` |
| Eliminar retornos de sucesso sem evidência | `whatsapp-web.mjs` e seus testes |
| Adicionar testes isolados de contratos e recuperação | Testes novos ou existentes do `site-ops` |

### Decisões específicas

**A. Separar erros de seletor de erros de infraestrutura.**

O auto-healing deve ser ativado somente quando houver evidência de um seletor ausente ou incompatível. Erros como controlador indisponível, timeout, permissão negada e resultado incerto precisam de tratamentos próprios.

**B. Substituir esperas fixas por condições observáveis.**

Usar os mecanismos de readiness já disponíveis no Hermes. Não criar outro sistema de polling.

**C. Não validar identidade por posição.**

`openChat()` não deve presumir que o primeiro resultado corresponde ao contato pretendido. A identidade deve ser confirmada antes de qualquer operação mutante.

**D. Não confundir execução com conclusão.**

Uma chamada que executa um `KeyboardEvent` não prova que o WhatsApp aceitou o envio. O script deve retornar um estado inconclusivo quando não existir evidência suficiente.

### Critérios de aceite

- 100% dos testes de resolução de caminhos e mapas passando.
- Auto-healing acionado apenas para erros elegíveis.
- Nenhum script declarando sucesso sem satisfazer sua pós-condição.
- Integração IPC testada de maneira isolada, inclusive falhas e timeout.
- Nenhum envio real utilizado nos testes automatizados.
- Nenhuma nova duplicação de executor ou registry.

**Resultado esperado\:** uma base operacional utilizável e testável. Esta mudança, isoladamente, não garante que o agente selecionará automaticamente o `site-ops`\.

---

# 5\. Mudança 2 — Execução governada e reconciliação

MELHORIA ESTRUTURAL

### O que implementar

O script determinístico não pode ter menos garantias que uma operação nativa do Browser.

A execução das operações mutantes do `site-ops` deve passar pelos controles existentes de identidade, autorização, admissão persistente e verificação.

Arquivos centrais\:

- `apps/desktop/electron/workstation-browser-runtime.ts`
- `apps/desktop/electron/workstation-browser-session-state.ts`
- `apps/desktop/electron/ipc/site-ops.ts`
- `workstation/control_plane/router.py`
- `workstation/control_plane/verification.py` e contratos associados

É necessário adaptar as interfaces existentes, não criar uma segunda autoridade de estado.

## Contrato de execução proposto

Contrato conceitual; o esquema definitivo deve reutilizar os tipos já existentes.

**Entrada**

Identidade da operação

`site`, `operation`, parâmetros tipados, `task_id`, `session_id`, `run_id` e `operation_id`\.

Precondições obrigatórias

Alvo resolvido, sessão correta, estado atualizado, autoridade suficiente e nenhuma mutação incerta conflitante.

---

**Saída**

| `VERIFIED` | Pós-condição satisfeita com evidência suficiente |
|--------|--------|
| `NOT_DISPATCHED` | Comprovadamente não produziu efeito na página |
| `UNCERTAIN` | Efeito não pode ser confirmado nem descartado |
| `REJECTED` | Operação recusada pela política ou precondições |

Um recibo de execução local pode acompanhar o resultado, mas não é equivalente à verificação do efeito externo.

Para o WhatsApp, é importante distinguir mensagem submetida na interface de mensagem efetivamente entregue ao destinatário. O verificador deve declarar exatamente o que a evidência permite afirmar.

### Idempotência e prevenção de duplicações

A regra será: **repetir uma chamada nunca pode significar automaticamente repetir seu efeito externo**\.

O `operation_id` deverá ser preservado em tentativas de recuperação. Se o runtime identificar execução anterior com efeito incerto, a nova tentativa deverá retornar essa condição sem reenviar a ação.

A identidade e a autorização confiáveis devem ser obtidas ou verificadas pelo runtime, não aceitas como autoridade simplesmente porque foram fornecidas pelo modelo.

### Recuperação e rollback

A recuperação deve preservar os registros existentes e utilizar somente recibos e verificadores autorizados. Nunca editar diretamente `browser-session.json` para forçar um reconhecimento.

Caso uma melhoria introduza regressão, o rollback deve reverter apenas os arquivos e capacidades modificados, mantendo o histórico de admissões e resultados. Não se deve limpar o estado pendente para fazer o navegador funcionar.

### Critérios de aceite

- Nenhuma repetição automática de operação externa inconclusiva.
- Falhas comprovadamente pré-efeito liberam a execução sem intervenção desnecessária.
- Crash e timeout preservam a identidade operacional.
- Ações não autorizadas continuam bloqueadas.
- Os verificadores distinguem ACK, estado local e efeito externo.
- Testes de recuperação cobrem os pontos antes e depois do dispatch.

**Resultado esperado\:** eliminar retrabalho causado por operações inconclusivas recuperáveis, sem enfraquecer as garantias de segurança.

---

# 6\. Mudança 3 — Seleção econômica e aprendizagem progressiva

EFICIÊNCIA COGNITIVA · MELHORIA ESTRUTURAL

### O que implementar

Integrar as capacidades estáveis ao catálogo e ao roteador existentes, permitindo que a seleção favoreça procedimentos reutilizáveis antes de recorrer à execução manual com IA.

Os componentes principais são\:

| Componente | Ação |
|--------|--------|
| `agent/skill_utils.py` | Garantir descoberta consistente da skill global do `site-ops` |
| `agent/prompt_builder.py` | Reduzir necessidade de carregar playbooks completos, preservando a política de segurança |
| `tools/tool_search.py` | Melhorar descoberta das operações existentes usando o catálogo atual |
| `workstation/control_plane/router.py` | Reutilizar seleção de capacidades e contratos |
| `workstation/experience_compiler/` | Registrar experiências verificadas e reutilização |
| `workstation/telemetry/` | Medir custo, latência e resultados sem duplicar instrumentação |

### Política de seleção

**Nível 1 — Correspondência exata** Capacidade promovida, compatível, saudável e autorizada.

---

**Nível 2 — Recuperação lexical** Busca local por operações e skills relacionadas à intenção.

---

**Nível 3 — System-1** Desambiguação e ranqueamento econômico quando necessário.

---

**Nível 4 — System-2** Novidade, incompatibilidade, raciocínio complexo ou incerteza não resolvida.

Esse fluxo não implica implementar quatro novos módulos: corresponde à política de uso dos mecanismos disponíveis.

### Carregamento progressivo de skills

A skill global precisa conter conhecimento específico, mas não deve obrigar o modelo a ler todas as referências e scripts a cada operação.

A estratégia recomendada é carregar inicialmente um catálogo compacto com nome, finalidade, operações disponíveis, requisitos e apontadores para os contratos completos. As regras necessárias à ação escolhida são carregadas antes da execução.

A regra `SKILL_PRUNED` deve permanecer: caso um conteúdo obrigatório tenha sido removido na compactação, o sistema precisa recuperá-lo.

O objetivo é tornar essa recuperação granular.

### Papel do Experience Compiler

O Experience Compiler poderá observar quais procedimentos foram reutilizados, seus custos, falhas e verificações. Com evidência suficiente, poderá identificar oportunidades de composição ou melhoria.

Entretanto, não deverá promover automaticamente uma sequência apenas por ser recorrente. A promoção precisa continuar condicionada aos contratos de segurança, utilidade e comprovação existentes.

O mecanismo também deve saber quando **não compilar**\: situações ambíguas ou com efeitos externos insuficientemente verificados devem permanecer para raciocínio ou supervisão.

### Critérios de aceite

- Capacidades relevantes aparecem no catálogo e podem ser selecionadas.
- Procedimentos reutilizáveis não exigem nova investigação a cada tarefa.
- As regras obrigatórias continuam acessíveis.
- A seleção correta é demonstrada com casos de teste positivos, negativos e ambíguos.
- A economia de contexto e chamadas é medida em condições comparáveis.

---

## 7\. Benchmark antes/depois

A métrica principal deverá ser **custo por resultado corretamente verificado**, e não quantidade bruta de mensagens ou chamadas.

### Indicadores obrigatórios

| Métrica | Como medir | Objetivo |
|--------|--------|--------|
| Latência | Tempo entre início e resultado final | Reduzir |
| Chamadas de ferramentas | Contagem por tarefa | Reduzir sem perder verificação |
| Chamadas LLM | Requisições ao provedor por tarefa | Reduzir |
| Tokens reais | Usage reportado pelo provedor | Reduzir |
| Taxa de sucesso | Resultados verificados / tentativas elegíveis | Manter ou aumentar |
| Estado incerto | Operações sem desfecho comprovado | Reduzir |
| Intervenção humana | Ações humanas necessárias por tarefa | Reduzir quando seguro |
| Repetição indevida | Efeitos externos duplicados | Zero |
| Reutilização | Tarefas atendidas por capacidade existente | Aumentar |

Para cada experimento, utilizar o mesmo objetivo, dados, ambiente e critérios de aceite. O modo anterior e o novo devem produzir evidência equivalente.

**Metas iniciais de avaliação\:** investigar se é possível reduzir pelo menos 50% das chamadas de ferramentas em fluxos repetitivos e 40% do contexto operacional carregado, sem diminuir a taxa de sucesso. Esses percentuais são metas experimentais, não resultados demonstrados.

Não converter caracteres em tokens faturados. Quando o provedor não retornar contagens reais, registrar o valor como indisponível e apresentar os proxies separadamente.

---

## 8\. Ordem exata de implementação

1. **Estabelecer baseline e preservar o estado atual**
   
   Registrar branch, HEAD e diff existente. Como o repositório já tinha alterações locais em `site-ops`, IPC e outros arquivos, preservar essas alterações antes de qualquer patch. Capturar métricas e fixtures para os três cenários principais.
2. **Aplicar a correção localizada do `site-ops`**
   
   Reparar caminhos, contratos e tratamento de erros. Validar primeiro funções puras e operações somente de leitura com mocks. Não ativar envio de mensagens.
3. **Conectar operações mutantes ao caminho de controle do Browser Runtime**
   
   Integrar identidade, autorização, admissão persistente e verificadores. Exercitar falhas simuladas, replay e reconciliação.
4. **Disponibilizar capacidades confiáveis ao agente**
   
   Registrar operações no catálogo existente, ajustar descoberta e testar a seleção automática em modo de observação ou execução simulada antes de habilitar mutações.
5. **Otimizar o carregamento de skills**
   
   Introduzir recuperação granular apenas onde os benchmarks confirmarem releituras custosas. Preservar as regras obrigatórias.
6. **Comparar resultados e promover gradualmente**
   
   Medir antes/depois, testar regressões e ativar somente capacidades validadas. Registrar evidências de reutilização no Experience Compiler.

### Condições para avançar entre etapas

A etapa 2 depende de testes isolados satisfatórios da etapa 1. A seleção automática de operações mutantes depende de garantias de execução e verificação comprovadas. A promoção de capacidades depende de evidências positivas e da ausência de regressões de autoridade.

Não será necessário aguardar a implementação completa das camadas de aprendizagem para obter os primeiros ganhos: o Hermes poderá reutilizar capacidades estáveis mesmo antes das melhorias mais avançadas do Experience Compiler.

---

## 9\. Investimentos que ficam fora do escopo

| Proposta | Decisão | Motivo |
|--------|--------|--------|
| Criar novo framework de automação | Descartar | `site-ops` já existe |
| Criar outro banco para campanhas | Descartar | Controle SQLite existente |
| Reescrever o Browser Runtime | Descartar | Correções localizadas são preferíveis |
| Implementar quatro ImprovementRuns agora | Adiar | Não há benchmark econômico que justifique |
| Implantar embeddings e LAYA como requisito inicial | Adiar | Seleção exata, lexical e System-1 já oferecem uma base |
| Resolver timeouts somente aumentando esperas | Não priorizar | Não trata efeitos desconhecidos |
| Contornar reconciliação via script/CDP | Rejeitar | Compromete garantias de execução |

A modernização mais ampla do Experience Compiler pode continuar como investimento de longo prazo, mas não deve bloquear a entrega das melhorias concretas.

---

## 10\. Implementação inicial escolhida

**P0 — Corrigir o caminho determinístico de remapeamento do Site Ops** (Primeira entrega)

**Escopo estrito\:** corrigir a localização do `site-deep-map.mjs`, a identificação do artefato gerado e a invocação IPC do `deep-map`\. Adicionar testes isolados que verifiquem caminhos, argumentos do processo, propagação de erros e compatibilidade com o mapa existente.

Arquivos principais

`site-ops/framework/auto-heal.mjs``apps/desktop/electron/ipc/site-ops.ts`Testes associados, reaproveitando os existentes.

---

**Critérios de conclusão**

- O remapeamento localiza o script correto.
- O artefato produzido é localizado pelo auto-healing.
- O IPC constrói corretamente o comando Node e seus argumentos.
- As falhas são propagadas sem retornos falsos de sucesso.
- Todos os testes passam sem abrir conversas, enviar mensagens ou modificar dados de usuários.
- O diff final permanece restrito ao escopo, preservando alterações preexistentes.

Essa é a primeira implementação que recomendo autorizar na Missão 4.

Ela não resolve sozinha todos os desperdícios, mas elimina incompatibilidades já demonstradas e oferece um teste de engenharia de baixo risco. Uma vez validada, teremos uma base concreta para avançar aos contratos de execução e à seleção automática.

**Decisão arquitetural final\:** preservar o núcleo atual do Hermes e construir eficiência pela integração das camadas existentes. A IA deve decidir *o que fazer e quando*, enquanto scripts e capacidades executam o trabalho previsível sob autorização, verificação e reconciliação confiáveis.

## Prompt:
24/10/2026, 18:03:22

# MISSÃO 4 — Implementar e validar a otimização prioritária do Hermes Work

Execute a primeira melhoria aprovada no plano 80/20 produzido na investigação anterior.

**Objetivo:** entregar uma correção funcional, testada e mensuravelmente melhor que o comportamento anterior.

Use o Remote Desktop Commander para trabalhar no repositório local do Hermes. Antes de editar, verifique branch, estado do Git, alterações existentes, testes e contratos das ferramentas afetadas.

## Regras de execução

- Respeite o fluxo de branch compartilhada existente; não crie worktrees ou branches desnecessárias.
- Reutilize capacidades e scripts existentes antes de criar novos componentes.
- Faça a menor alteração capaz de resolver a causa-raiz.
- Preserve permissões, isolamento, aprovações humanas e mecanismos de reconciliação.
- Para ações externas, como mensagens ou e-mails, utilize mocks ou dry-run por padrão. Não faça envios reais sem autorização explícita.
- Acrescente testes de regressão, falha, retry, idempotência e recuperação de estado conforme o componente.
- Instrumente o comportamento para tornar o ganho mensurável.
- Não altere outras áreas fora do escopo.

## Validação

Compare o comportamento anterior e posterior usando o mesmo cenário e condições equivalentes.

Meça chamadas de ferramentas, tempo de execução, tokens quando disponíveis, erros, repetições, sucesso e confiabilidade.

Se alguma métrica não puder ser medida, diga por quê e quais instrumentos seriam necessários.

## Entrega final

Apresente:

1. O que foi alterado e em quais arquivos.
2. Os testes realizados, resultados e limitações.
3. Comparação antes/depois com evidências.
4. Problemas remanescentes ou regressões.
5. Como o Experience Compiler deve reconhecer, recuperar e reutilizar a melhoria.
6. Qual seria a próxima melhoria de maior retorno, agora que esta foi concluída.

Não declare sucesso sem evidência de funcionamento. Não faça merge ou push sem autorização específica.

## Response:
24/10/2026, 18:03:29 · gpt-6-thinking

Vou implementar apenas o P0 aprovado: corrigir a resolução de caminhos e artefatos do `site-ops`, além da chamada IPC de remapeamento. Primeiro verificarei o Git e o diff atual para preservar edições já em andamento; depois aplicarei o menor patch possível, acrescentarei testes isolados e compararei o comportamento anterior e posterior sem acessar o WhatsApp nem executar envios.

Confirmei que o `site-deep-map.mjs` já devolve o `slug` real na etapa `init`; vou usá-lo para localizar o artefato, em vez de reconstruir o nome por tentativa. Também identifiquei que o carregador de mapas já define o caminho correto do override local. A correção poderá reutilizar ambos, mantendo um único mapa e uma única tentativa de recuperação por falha elegível.

O baseline com testes isolados confirmou o problema: **5 falhas e 2 aprovações em 7 casos**\. As falhas incluem o script de remapeamento inexistente no caminho calculado, a construção incorreta do comando IPC e a aceitação de saída inválida como sucesso. Também encontrei um detalhe adicional: a resolução do diretório-raiz precisa funcionar tanto no código-fonte quanto no Desktop empacotado. Vou corrigir isso sem mexer nas outras frentes do repositório.

> **Revisando a implementação**
>
> Estou avaliando uma alteração pequena e segura: corrigir a resolução de caminhos usando o carregador existente, validar o padrão do site e manter falhas de mutação separadas da recuperação. Também estou planejando testes antes de modificar arquivos.
>
> **Refinando a recuperação**
>
> Estou restringindo a recuperação automática a erros explicitamente relacionados a seletores, evitando mascarar falhas de contato. Também vou preservar a causa original, usar execução segura e permitir testes isolados sem depender de processos externos.
>
> **Revisou a implementação e refinou a recuperação**
>
> 
>
> **Estruturando testes isolados**
>
> Estou separando a lógica de caminhos, classificação e execução para testar cada comportamento sem abrir conexões reais. A recuperação continuará limitada a erros elegíveis, com métricas simples e preservação clara da falha original.
>
> **Finalizando a estratégia**
>
> Estou consolidando a implementação com validação do artefato recém-gerado, classificação explícita de erros, limite de uma tentativa e testes para sucesso, falhas não elegíveis, recuperação incompleta e execução segura.
>
> **Estruturou testes isolados e finalizou a estratégia**
>
> 
>
> **Inspecionou dispositivos, iniciou processos e analisou ferramentas e configurações**
>
> 
>
> **Implementados testes automatizados de auto-recuperação e operações IPC**
>
> 
>
> **Corrigiu auto-recuperação, resolução IPC, testes, typecheck e lint**
>
> 
>
> **Verificou processo, testes de falhas, auto-recuperação, cooldown, TypeScript e ESLint**
>
> 
>
> **Corrigidos tipos TypeScript, lint e validação de rollback em três arquivos**
>
> 
>
> **Validou status IPC, testou append e monitorou métricas do processo**
>
> 
>
> Pensou por 9m

## Estado inicial verificado

O repositório está acessível em `C:\Github\hermes-agent`, na branch compartilhada `main`\. O HEAD atual é `246f58291a`, diferente daquele observado na Missão 3.

Há diversas alterações locais de outras frentes de trabalho, principalmente em AI Control e componentes do Desktop. **Os dois arquivos de produção selecionados para o P0 estavam sem alterações locais no momento da inspeção**\:

- `site-ops/framework/auto-heal.mjs`
- `apps/desktop/electron/ipc/site-ops.ts`

Confirmei três defeitos no código atual: o auto-healing procura o script em um caminho incorreto, procura um artefato com identificador diferente do gerado e o IPC acrescenta indevidamente `node` aos argumentos da execução.

Vou manter os demais arquivos e alterações intactos, usando testes com processos e arquivos simulados.

## Primeiro resultado de validação

A bateria inicial passou de **2/7 testes aprovados antes da correção para 7/7 depois dela**\. Os testes usam processos, respostas e filesystem simulados; não acessam o WhatsApp.

Os cenários aprovados cobrem a chamada correta do remapeador, sua saída JSON, propagação de falhas, retry limitado, recusa de remapeamento para erro de infraestrutura e uso do override correto.

Isso comprova a correção dos defeitos reproduzidos nessa bateria, mas **ainda não demonstra uma redução real de tokens ou latência em tarefas completas do Hermes**\. Essas métricas exigem um benchmark posterior do agente e do Browser com o mesmo nível de verificação.

## 1\. Resultado final da implementação

(P0 validado em testes isolados)

A correção foi aplicada diretamente ao repositório local. O escopo ficou restrito a **dois arquivos de produção e dois arquivos novos de teste**\.

| Arquivo | Alteração |
|--------|--------|
| `site-ops/framework/auto-heal.mjs` | Correção dos caminhos, identificação do artefato, classificação de falhas e retry controlado |
| `apps/desktop/electron/ipc/site-ops.ts` | Correção da localização do `site-ops`, execução do script e validação das respostas IPC |
| `apps/desktop/electron/ipc/site-ops-auto-heal.test.ts` | Testes de recuperação, falhas, cooldown e retry |
| `apps/desktop/electron/ipc/site-ops.test.ts` | Testes do IPC com processos simulados e validação de resultados |

### Principais mudanças funcionais

O auto-healing agora obtém o `slug` informado pelo próprio remapeador, localiza o artefato correspondente e usa o caminho de override definido pelo carregador existente. Deixa também de iniciar um remapeamento para erros genéricos de infraestrutura.

A execução dos comandos `init` e `scan` passou a utilizar argumentos de processo separados, sem interpolação em shell. O retry permanece limitado a uma tentativa.

No IPC, a execução aponta diretamente para `site-deep-map.mjs`\. Além disso, resultados vazios, JSON inválido ou respostas que não confirmem o comando solicitado deixam de ser classificados como sucesso.

## 2\. Evidências de validação

Testes antes do patch

# 2/7

Aprovados no baseline

Testes finais

# 11/11

Aprovados após correção e ampliação da cobertura

| Validação final | Resultado |
|--------|--------|
| Vitest — dois arquivos de regressão | 11 aprovados |
| ESLint nos arquivos TypeScript alterados | Sem erros |
| TypeScript — `tsconfig.electron.json` | Aprovado |
| `node --check` do auto-healing | Aprovado |
| `git diff --check` | Aprovado |
| Envio de mensagens ou e-mails | Nenhum |

A cobertura inclui falha durante o remapeamento, ausência de retry indevido, cooldown, rejeição de slug inválido, erro de processo filho e rejeição de respostas IPC falsas ou incompletas.

## 3\. Comparação antes/depois

| Indicador | Antes | Depois |
|--------|--------|--------|
| Caminho do remapeador | Incorreto | Resolvido corretamente nos testes |
| Identificação do artefato | Incompatível | Baseada no `slug` retornado |
| Comando IPC | Argumentos incorretos | Comando correto |
| Saída vazia/JSON inválido | Podia ser aceita | Rejeitada |
| Erro de infraestrutura | Podia disparar remapeamento | Não dispara |
| Retry após remapeamento | Não alcançava a etapa corretamente | Exatamente uma tentativa |
| Testes de regressão | 2/7 | 11/11 |

**Latência\:** a execução final da bateria Vitest levou aproximadamente 267 ms, mas esse valor representa testes com mocks. Não é uma medição do tempo de operação real do Hermes. Os tempos de baseline e pós-correção não são diretamente comparáveis como benchmark de desempenho porque a versão antiga falhava antes de completar o fluxo.

**Chamadas\:** o caminho corrigido prevê duas execuções determinísticas para `init` e `scan`, seguidas de no máximo uma nova tentativa da operação original. Não há evidência de redução de chamadas LLM nesta etapa.

**Tokens\:** indisponíveis. Os testes não invocaram modelos de IA e os logs históricos não oferecem telemetria suficiente para calcular economia faturada.

Portanto, o ganho comprovado é **funcional e de confiabilidade local**, não ainda uma economia quantitativa de tokens.

## 4\. Limitações e problemas remanescentes

Esta entrega não comprova ainda o funcionamento completo em um Desktop empacotado ou em uma sessão real de navegador.

Também permanecem fora do P0\:

- `send-message` ainda precisa de pós-condições confiáveis para impedir sucesso falso.
- O caminho CDP direto ainda precisa ser confrontado com os contratos de autorização e reconciliação do Browser Runtime.
- A descoberta automática do `site-ops` pelo agente ainda não foi demonstrada.
- O cooldown continua sendo um controle em memória do processo, não uma política durável entre execuções.

O teste E2E existente do WhatsApp inclui operações potencialmente mutantes; não o executei para respeitar a exigência de nenhum envio real.

## 5\. Como o Experience Compiler deve reutilizar a melhoria

O Experience Compiler não deve tratar essa correção de código como uma experiência de navegador promovida automaticamente.

O aproveitamento correto é registrar a operação `site_ops.remap` como um procedimento candidato, com identidade do site, pré-condições, motivo da falha, versão do mapa, resultado do remapeamento e evidência de que o seletor voltou a ser utilizável.

Somente após validações independentes deverá considerar reutilização e promoção. Falhas de controlador, autorização ou efeito desconhecido não devem ser convertidas em aprendizado de retry.

A telemetria adicionada ao caminho bem-sucedido já emite `status=remapped`, quantidade de comandos, retry e duração. O passo seguinte é correlacionar esses eventos com `task_id`, `run_id` e `operation_id` no sistema de telemetria existente, sem criar outro coletor.

## 6\. Git e preservação do trabalho

O HEAD ao final permaneceu em `246f58291a`, na branch `main`\.

As alterações preexistentes de outras frentes foram preservadas. **Não fiz commit, merge, push nem criei outra branch ou worktree.**

Os quatro arquivos desta implementação permanecem como alterações locais e arquivos de teste não rastreados, prontos para revisão e eventual commit autorizado.

## 7\. Próxima melhoria de maior retorno

Recomendo avançar para **contratos de execução e verificação das operações mutantes do `site-ops`**\.

O primeiro caso de teste deverá ser uma operação simulada de composição e envio no WhatsApp que confirme identidade do destinatário, ausência de duplicações e pós-condições reais, respeitando autorização e reconciliação.

Isso é mais valioso, neste momento, do que expandir o Experience Compiler: elimina a possibilidade de o Hermes considerar concluída uma operação que apenas disparou um evento de interface.

**Conclusão\:** o P0 foi implementado e passou nos testes isolados, corrigindo os defeitos específicos aprovados. O ganho de confiabilidade está comprovado nesse escopo; o ganho operacional do agente ainda depende de um benchmark integrado, sem o qual não seria correto declarar redução de tokens ou latência.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)