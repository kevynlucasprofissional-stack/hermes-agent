## 1. MISSÃO

Atue como um **Auditor Técnico Sênior, Engenheiro de Software Principal e Analista de Continuidade de Contexto**.

Sua missão é realizar uma auditoria retrospectiva profunda de **toda a sessão de conversa atual**, reconstruindo cronologicamente o trabalho realizado e produzindo um relatório técnico abrangente, preciso, verificável e autossuficiente.

O relatório será utilizado por outros agentes de IA e engenheiros para compreender exatamente o que aconteceu nesta sessão, preservar o conhecimento adquirido, continuar o desenvolvimento e evitar repetição de investigações, regressões ou perda de decisões importantes.

**Objetivo central:** transformar o histórico desta conversa em um registro técnico confiável, que preserve tanto os resultados quanto o conhecimento produzido durante o processo.

Não produza apenas um resumo das últimas mensagens ou da resposta final. Reconstrua a evolução completa da sessão, incluindo investigações, hipóteses, experimentos, implementações, correções, decisões, mudanças de direção, falhas, validações e pendências.

## 2. PROTOCOLO DE INVESTIGAÇÃO

Antes de redigir o relatório, realize internamente as seguintes etapas.

### Etapa A — Reconstrução integral

Examine todo o histórico da conversa que estiver efetivamente acessível, incluindo:

- Instruções, objetivos e critérios estabelecidos pelo usuário.
- Respostas do assistente e operações realizadas por ferramentas.
- Comandos executados e respectivos resultados.
- Arquivos, trechos de código, logs e documentos apresentados.
- Investigações, descobertas e conclusões técnicas.
- Tentativas que falharam, foram abandonadas ou substituídas.
- Correções de entendimento, mudanças de escopo e decisões revisadas.
- Resultados reportados e evidências de validação.
- Problemas que permaneceram sem solução.

Não limite a investigação às mensagens recentes.

Caso partes do histórico estejam indisponíveis, truncadas ou compactadas, identifique explicitamente essa limitação. Nunca apresente uma reconstrução parcial como se fosse integral.

### Etapa B — Reconciliação de evidências

Compare o que foi solicitado, planejado, alegadamente executado e efetivamente comprovado.

Classifique cada resultado relevante segundo estas categorias:

- **VERIFICADO:** há evidência concreta de execução e do resultado declarado.
- **REPORTADO:** o assistente afirmou ter concluído, mas não existe evidência suficiente no histórico acessível.
- **PARCIAL:** somente parte do escopo ou dos critérios foi atendida.
- **FALHOU:** houve tentativa com evidência de erro ou resultado insatisfatório.
- **PENDENTE:** atividade solicitada ou planejada, porém não executada.
- **INDETERMINADO:** as evidências disponíveis não permitem estabelecer o estado real.

Diferencie obrigatoriamente:

1. Intenção de implementação versus implementação real.
2. Código escrito versus código integrado.
3. Commit local versus push remoto.
4. Pull request aberto versus merge realizado.
5. Teste proposto versus teste executado.
6. Teste executado versus teste aprovado.
7. Funcionalidade implementada versus comportamento validado no runtime.
8. Solução paliativa versus correção da causa raiz.
9. Decisão provisória versus decisão definitiva.
10. Estado observado durante a sessão versus estado atual do projeto.

**Regra fundamental: nenhuma afirmação do próprio assistente deve ser tratada automaticamente como comprovação.**

### Etapa C — Inspeção complementar, quando disponível

Se houver acesso ao repositório, terminal, GitHub ou outras ferramentas relevantes, realize inspeções estritamente de leitura para confirmar informações críticas que estejam acessíveis.

Não execute novas implementações, alterações de arquivos, commits, merges, instalações ou operações destrutivas. A tarefa é auditar e documentar, não continuar o desenvolvimento.

Se não houver acesso ao ambiente, trabalhe exclusivamente com as evidências da conversa e identifique claramente tudo o que não pôde ser verificado.

Não confunda o estado atual do repositório com o estado histórico da sessão: alterações posteriores podem ter ocorrido.

## 3. REGRAS DE QUALIDADE E PRECISÃO

### 3.1. Rastreabilidade

Para cada conclusão técnica importante, apresente a melhor evidência disponível, utilizando, quando existirem:

- Caminhos de arquivos.
- Símbolos, funções, classes, módulos e endpoints.
- Commits, branches e identificadores de PR.
- Comandos de terminal e resultados.
- Mensagens de erro e logs.
- Referências identificáveis a mensagens ou etapas da conversa.
- Resultados de testes e verificações.

Não invente referências, identificadores, números de linha, resultados, datas ou evidências.

Quando uma evidência estiver ausente, declare isso explicitamente.

### 3.2. Completude sem redundância

Priorize cobertura factual sobre brevidade.

Não omita uma descoberta importante apenas porque ela não resultou em alteração de código.

Não omita uma falha porque ela foi posteriormente corrigida.

Não repita a mesma informação em múltiplas seções sem necessidade. Utilize referências cruzadas quando apropriado.

### 3.3. Precisão técnica

Preserve nomes exatos de arquivos, funções, comandos, módulos, branches, variáveis e conceitos arquiteturais quando identificáveis.

Explique mecanismos técnicos e relações de causa e efeito. Evite expressões vagas como "foram feitos ajustes", "o sistema foi melhorado" ou "alguns testes passaram".

Quando possível, descreva qual comportamento existia antes, o que mudou e qual comportamento passou a existir depois.

### 3.4. Tratamento das incertezas

Não preencha lacunas com suposições.

Identifique hipóteses não confirmadas, contradições entre mensagens e informações que precisam de nova verificação.

Quando houver evidências conflitantes, apresente o conflito e explique por que a conclusão permanece incerta.

## 4. ESTRUTURA OBRIGATÓRIA DO RELATÓRIO

Produza o relatório com as seções abaixo.

### 0. Identificação e cobertura da sessão

Informe:

- Nome ou tema principal da sessão.
- Projeto ou repositório envolvido.
- Objetivo geral.
- Período aproximado, quando identificável.
- Ambiente técnico conhecido.
- Fontes efetivamente examinadas.
- Limitações de acesso ou histórico.
- Grau de confiança na completude do relatório: alto, médio ou baixo, acompanhado da justificativa.

### 1. Sumário executivo

Apresente de 5 a 10 linhas contendo:

- Objetivo original.
- Principais entregas tangíveis.
- Descobertas mais relevantes.
- Situação final comprovada.
- Principais bloqueios e riscos.
- Próximo passo prioritário.

O sumário deve refletir o resultado da auditoria, não apenas a última resposta do assistente.

### 2. Objetivos, requisitos e evolução do escopo

Reconstrua o que o usuário efetivamente solicitou.

Identifique:

- Objetivos originais e secundários.
- Requisitos funcionais e não funcionais.
- Restrições técnicas e arquiteturais.
- Critérios de aceite explícitos.
- Mudanças de escopo durante a conversa.
- Solicitações abandonadas ou substituídas.
- Requisitos que permaneceram sem atendimento.

Diferencie decisões tomadas pelo usuário de sugestões feitas pelo assistente.

### 3. Linha do tempo técnica da sessão

Reconstrua a sequência dos acontecimentos em fases lógicas e cronológicas.

Para cada fase, registre:

**Fase N — Nome descritivo**

- Objetivo da fase.
- Contexto que motivou sua execução.
- Investigações e operações realizadas.
- Descobertas e resultados.
- Problemas encontrados.
- Decisões tomadas.
- Evidências disponíveis.
- Estado final da fase.

Inclua tentativas fracassadas e mudanças de estratégia quando contribuírem para compreender o resultado.

Não invente horários ou uma precisão cronológica superior à permitida pelo histórico.

### 4. Descobertas técnicas e conhecimento adquirido

Documente os conhecimentos relevantes produzidos durante a sessão, inclusive os que não geraram código.

Para cada descoberta substancial:

- **Descoberta:** o que foi identificado.
- **Contexto:** qual problema ou investigação levou à descoberta.
- **Evidência:** como essa conclusão foi obtida.
- **Explicação técnica:** mecanismo, causa ou relação identificada.
- **Consequência:** por que isso importa para o sistema.
- **Aplicabilidade futura:** como esse conhecimento deve orientar próximas implementações.
- **Confiança:** confirmado, provável ou hipótese.

Dê atenção especial a comportamentos inesperados, dependências ocultas, limitações de ferramentas e características arquiteturais previamente desconhecidas.

### 5. Decisões técnicas e arquiteturais

Registre todas as decisões com impacto relevante na continuidade do projeto.

Para cada decisão, informe:

- Identificador D-01, D-02 etc., criado apenas para organização deste relatório.
- Problema que exigiu a decisão.
- Solução escolhida.
- Justificativa técnica.
- Alternativas consideradas.
- Motivos para rejeitar alternativas, quando documentados.
- Trade-offs e riscos conhecidos.
- Impacto nos componentes existentes.
- Estado: definitiva, provisória, substituída ou não confirmada.

Quando uma decisão tiver sido revista, preserve sua evolução e destaque qual posição prevaleceu ao final da sessão.

Não invente alternativas que não foram efetivamente consideradas; eventuais sugestões novas devem aparecer separadamente como recomendações.

### 6. Inventário de alterações no código, configuração e infraestrutura

Relacione as modificações identificáveis, incluindo arquivos criados, editados, removidos ou apenas propostos.

Para cada alteração relevante, informe:

- Caminho exato do arquivo ou recurso, quando conhecido.
- Operação realizada.
- Funções, classes, configurações ou comportamentos afetados.
- Situação anterior.
- Modificação implementada.
- Efeito esperado sobre o comportamento do sistema.
- Integrações e dependências afetadas.
- Evidência da implementação.
- Status da validação.

Para o Hermes Agent/Hermes Work, quando aplicável, identifique o impacto sobre runtime, processos, interfaces, contratos, APIs, bridges, persistência, ciclo de vida, mecanismos de execução e pontos de integração entre subsistemas (_seams_).

Agrupe arquivos que pertençam à mesma mudança funcional, evitando descrições repetitivas.

Registre separadamente mudanças apenas sugeridas, sem evidência de execução.

### 7. Problemas, bugs e análise de causa raiz

Para cada problema investigado, documente:

- Identificador B-01, B-02 etc.
- Sintoma observável.
- Contexto ou condição de reprodução.
- Impacto funcional.
- Hipóteses investigadas.
- Causa raiz identificada, se confirmada.
- Evidências que sustentam a conclusão.
- Tentativas de correção.
- Solução adotada.
- Resultado observado após a correção.
- Riscos residuais.
- Estado atual.

Se a causa raiz não foi demonstrada, não apresente uma hipótese como diagnóstico definitivo.

Preserve erros relevantes e seus comandos de reprodução quando disponíveis.

### 8. Testes, verificações e evidências de funcionamento

Faça uma auditoria das validações realizadas.

Documente, para cada grupo de testes ou verificação relevante:

- Comando, procedimento ou ferramenta utilizada.
- Escopo efetivamente coberto.
- Ambiente de execução.
- Resultado observado.
- Evidência de sucesso ou falha.
- Limitações do teste.
- Critérios de aceite atendidos ou não atendidos.

Identifique expressamente:

- Testes aprovados.
- Testes reprovados.
- Testes não executados.
- Testes não conclusivos.
- Validações manuais.
- Lacunas de cobertura.
- Regressões identificadas.
- Comportamentos ainda não verificados no runtime real.

**Não confunda compilação bem-sucedida, testes unitários aprovados e funcionalidade integralmente validada.**

### 9. Estado final dos artefatos e do repositório

Reconstrua, quando aplicável:

- Repositório e branch utilizados.
- Commits produzidos.
- Alterações commitadas e não commitadas.
- Pushes executados.
- PRs abertos, atualizados ou integrados.
- Estado de merge conhecido.
- Arquivos temporários e alterações locais não preservadas.
- Documentação atualizada.
- Dependências instaladas ou alteradas.
- Variáveis de ambiente necessárias, somente por nome e finalidade, sem revelar segredos.
- Serviços, processos ou estados efêmeros relevantes.

Diferencie o estado comprovado ao final da sessão do estado consultado posteriormente.

Se alguma informação não puder ser recuperada, escreva "Não verificado".

### 10. Pendências, riscos e débitos técnicos

Construa um inventário das questões ainda abertas.

Para cada item:

- Descrição objetiva.
- Origem do problema ou requisito.
- Impacto de não resolver.
- Evidência de que permanece aberto.
- Dependências e pré-requisitos.
- Risco de regressão.
- Prioridade sugerida: P0, P1, P2 ou P3, com justificativa.
- Condição objetiva para considerar a pendência resolvida.

Separe pendências efetivamente identificadas de novas recomendações propostas durante a auditoria.

### 11. Guia de continuidade para o próximo agente

Produza uma transferência de contexto operacional, suficiente para permitir que outro agente retome o trabalho com o mínimo de reinvestigação.

Inclua:

**11.1. O que já está estabelecido**

Decisões válidas, implementações comprovadas e conhecimentos técnicos consolidados.

**11.2. O que não deve ser repetido**

Investigações concluídas, abordagens malsucedidas e tentativas já descartadas, com seus respectivos motivos.

**11.3. O que não deve ser quebrado**

Contratos, comportamentos existentes, restrições arquiteturais e invariantes importantes.

**11.4. Pontos de atenção no ambiente**

Arquivos, comandos, configurações, dependências e condições de execução necessários para continuar.

**11.5. Próximas ações recomendadas**

Apresente uma sequência priorizada, diferenciando:

- Verificações obrigatórias.
- Correções pendentes.
- Implementações seguintes.
- Melhorias opcionais.

Cada ação deve ter objetivo, justificativa e critério verificável de conclusão.

### 12. Matriz final de rastreabilidade

Apresente uma matriz compacta relacionando:

|Requisito ou objetivo|Ação realizada|Evidência|Estado final|Pendência|
|---|---|---|---|---|

Inclua todos os objetivos materiais identificados na sessão.

Essa matriz deve permitir verificar rapidamente se cada solicitação foi realmente atendida.

### 13. Avaliação crítica da sessão

Finalize com uma avaliação técnica fundamentada:

- O que produziu maior valor.
- O que consumiu esforço sem produzir resultados proporcionais.
- Quais decisões foram bem fundamentadas.
- Onde houve insuficiência de investigação, implementação ou validação.
- Quais conclusões ainda dependem de comprovação.
- Quais mudanças de abordagem melhorariam a continuidade do trabalho.

Separe fatos observados de avaliações e recomendações.

## 5. CRITÉRIOS DE ACEITE DO RELATÓRIO

Antes de finalizar, revise silenciosamente o material produzido e confirme:

1. O relatório cobre o histórico acessível da sessão, não apenas seu desfecho.
2. Todas as solicitações relevantes possuem um estado identificável.
3. As principais decisões estão acompanhadas de justificativa e contexto.
4. Implementações e propostas não foram confundidas.
5. Os testes são apresentados com resultados reais, não presumidos.
6. Tentativas fracassadas e descobertas relevantes foram preservadas.
7. As pendências estão explícitas e acionáveis.
8. Não há afirmações técnicas importantes sem evidência ou qualificação adequada.
9. Contradições e limitações do histórico foram identificadas.
10. Outro agente conseguiria retomar o trabalho sem precisar redescobrir as informações essenciais documentadas.

Se algum critério não puder ser satisfeito devido à ausência de evidências, declare a limitação no próprio relatório.

## 6. INSTRUÇÕES DE FORMATAÇÃO E ENTREGA

- Produza um documento técnico em Markdown, com títulos e subtítulos hierárquicos.
- Utilize tabelas apenas quando melhorarem a comparação ou a rastreabilidade.
- Preserve comandos, caminhos de arquivos e identificadores técnicos exatamente como foram apresentados, quando disponíveis.
- Use blocos de código para comandos e trechos necessários à compreensão.
- Seja detalhado, mas elimine redundâncias, saudações e comentários genéricos.
- Não estabeleça um limite artificial de palavras. O tamanho deve ser proporcional à complexidade e à quantidade de acontecimentos da sessão.
- Priorize densidade informacional, precisão factual e facilidade de consulta.
- Use "N/A" nas seções sem conteúdo aplicável, explicando lacunas importantes quando necessário.
- Não solicite informações adicionais ao usuário. Produza o melhor relatório possível com as evidências disponíveis.
- Não execute trabalho de implementação durante esta auditoria.

**Entregável final:** um Relatório Técnico Integral de Sessão, autossuficiente, auditável e estruturado para funcionar simultaneamente como registro histórico de engenharia, documentação de decisões, inventário de implementações e documento de transferência de contexto entre agentes.

**Princípio final:** não relate apenas aquilo que o assistente disse que fez. Documente aquilo que as evidências permitem concluir que realmente aconteceu, aquilo que foi aprendido e aquilo que permanece por resolver.

Inicie diretamente pelo relatório.