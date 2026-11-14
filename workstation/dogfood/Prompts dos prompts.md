# MISSÃO — Planejamento Estratégico e Preparação Técnica de Implementações

## 1. Objetivo e princípios gerais

Com base na análise, diagnóstico ou conjunto de problemas apresentados, elabore um **plano de implementação passo a passo**, estruturado em uma sequência de prompts que represente o equilíbrio ideal entre **economia de prompts, profundidade de análise, precisão técnica e qualidade das implementações**.

O objetivo é transformar o conhecimento produzido na análise em um plano de execução concreto, tecnicamente fundamentado e imediatamente utilizável por outra instância de IA responsável pelas implementações.

Organize o trabalho de maneira inteligente:

- **Problemas simples e relacionados** podem ser agrupados em um único prompt, desde que compartilhem contexto, dependências ou componentes e possam ser implementados e verificados conjuntamente.
    
- **Problemas complexos**, que exigem maior capacidade de raciocínio, investigação, decisões arquiteturais ou validações específicas, devem receber prompts individuais ou etapas suficientemente isoladas.
    
- **Alterações interdependentes** devem ser organizadas em uma sequência que respeite seus pré-requisitos técnicos e reduza conflitos, regressões e retrabalho.
    
- **Investigações já concluídas** devem ser aproveitadas, evitando repetir análises que não acrescentem informação relevante.
    

O critério principal não é produzir a menor quantidade possível de prompts, mas encontrar a **divisão de trabalho que maximize a eficiência real de implementação e a confiabilidade dos resultados**.

## 2. Investigação e compreensão do projeto existente

Antes de elaborar os prompts, **acesse e analise diretamente os arquivos, componentes e recursos disponíveis do projeto em questão**, compreendendo sua arquitetura real, organização, tecnologias, implementações existentes e pontos específicos que precisam ser modificados.

Não presuma que o projeto utiliza determinada linguagem, framework, estrutura de diretórios, convenção arquitetural ou sistema de documentação.

Identifique essas características a partir das evidências encontradas no próprio projeto.

A investigação deverá contemplar, conforme a necessidade:

1. **Arquitetura e organização:** estrutura de diretórios, módulos, componentes, camadas, responsabilidades e padrões arquiteturais existentes.
    
2. **Estado atual das implementações:** funcionalidades já desenvolvidas, soluções parciais, recursos reutilizáveis e limitações conhecidas.
    
3. **Dependências e integrações:** bibliotecas, serviços, APIs, interfaces, contratos, persistência de dados e componentes externos envolvidos.
    
4. **Histórico e decisões existentes:** documentação, registros de engenharia, decisões arquiteturais, planos anteriores e resultados de investigações relevantes.
    
5. **Pontos de intervenção:** arquivos, módulos, funções, classes, configurações, fluxos ou componentes que efetivamente precisam ser modificados.
    
6. **Validação disponível:** testes automatizados, ferramentas de diagnóstico, procedimentos de build, ambientes de execução e critérios de qualidade existentes.
    

### Princípio de investigação seletiva

**Não reinvestigue o projeto inteiro indiscriminadamente.**

Aproveite o conhecimento já produzido e concentre a investigação nos pontos necessários para compreender, preparar e validar as alterações propostas.

Priorize a leitura dos arquivos diretamente relacionados às implementações, expandindo a investigação apenas quando dependências, incompatibilidades ou incertezas técnicas justificarem.

Diferencie claramente:

- Informações comprovadas pela inspeção do projeto.
    
- Informações documentadas, mas ainda não verificadas.
    
- Hipóteses técnicas que precisam de confirmação.
    
- Decisões já estabelecidas que devem ser preservadas.
    
- Questões ainda abertas que podem afetar a implementação.
    

Se algum recurso necessário estiver inacessível, registre a limitação e suas consequências. **Não invente caminhos, implementações, contratos ou resultados de verificações.**

## 3. Atualização e preservação da documentação

Identifique e atualize os documentos relevantes do projeto, incorporando as descobertas, decisões arquiteturais, melhorias identificadas e diretrizes estabelecidas na análise.

Isso pode incluir, conforme a estrutura efetivamente encontrada:

- Roadmap e planejamento de desenvolvimento.
    
- Jornal de Engenharia, diário técnico ou histórico de implementação.
    
- Documentação de arquitetura, inteligência técnica ou contexto operacional.
    
- Especificações funcionais e técnicas.
    
- Registros de decisões arquiteturais (ADRs).
    
- Documentação de APIs, contratos e integrações.
    
- Registros de problemas conhecidos, limitações e pendências.
    
- Planos de testes, critérios de aceitação e procedimentos de validação.
    
- Outros documentos que sejam relevantes para a continuidade do projeto.
    

**Utilize prioritariamente os documentos e convenções já existentes.** Não crie arquivos redundantes nem imponha uma nova estrutura documental sem necessidade.

A documentação deve refletir fielmente:

1. O estado atual comprovado do projeto.
    
2. Os problemas identificados e suas causas conhecidas.
    
3. As soluções propostas e as justificativas técnicas.
    
4. As decisões arquiteturais adotadas e os contratos que devem ser preservados.
    
5. A sequência planejada de implementação.
    
6. Os riscos, dependências, limitações e questões pendentes.
    
7. Os critérios utilizados para verificar o sucesso das alterações.
    

Diferencie explicitamente o que **já foi implementado**, o que **foi apenas preparado**, o que **está planejado** e o que **ainda depende de investigação ou validação**.

Não apresente soluções propostas como funcionalidades concluídas.

## 4. Preparação antecipada das implementações

Quero que você vá além de identificar os problemas e recomendar soluções.

**Sempre que possível, prepare antecipadamente o código, as configurações, os patches e os demais artefatos necessários para executar as implementações e correções.**

O objetivo é reduzir substancialmente a necessidade de interpretação e investigação adicional por parte da IA implementadora.

Para cada alteração, identifique com precisão:

### 4.1. Localização das alterações

- Quais arquivos, diretórios ou recursos deverão ser criados, modificados, removidos ou substituídos.
    
- Em quais funções, classes, módulos, componentes, configurações ou trechos específicos as mudanças deverão ocorrer.
    
- Quais implementações existentes estão diretamente relacionadas ao problema.
    
- Quais elementos deverão ser reutilizados, preservados ou adaptados.
    

Utilize caminhos e identificadores reais sempre que puder verificá-los.

### 4.2. Solução técnica preparada

Sempre que viável, apresente:

- Código completo ou trechos diretamente aplicáveis.
    
- Patches ou diffs com contexto suficiente para identificar os locais de alteração.
    
- Novas interfaces, funções, classes, módulos ou componentes necessários.
    
- Ajustes de configuração, dependências e integração.
    
- Migrações, adaptações de dados ou alterações de contratos, quando aplicáveis.
    
- Instruções explícitas sobre qual código existente deverá ser substituído, preservado ou removido.
    

**Evite pseudocódigo quando for possível preparar uma implementação real.**

Entretanto, não produza código especulativo apenas para preencher lacunas de informação. Quando algum detalhe depender de uma verificação ainda não realizada, identifique essa dependência com clareza.

As soluções devem respeitar as linguagens, convenções, padrões e tecnologias efetivamente utilizados pelo projeto.

### 4.3. Compatibilidade e preservação arquitetural

Identifique:

- Dependências internas e externas.
    
- Contratos públicos e privados.
    
- Interfaces, formatos de dados e mecanismos de persistência.
    
- Fluxos de execução e integrações existentes.
    
- Funcionalidades que não podem sofrer regressões.
    
- Requisitos de segurança, desempenho, estabilidade e compatibilidade.
    

Priorize a reutilização de componentes existentes e a realização de mudanças proporcionais ao problema.

**Não proponha reconstruir uma funcionalidade que já existe e pode ser corrigida, estendida ou reaproveitada adequadamente.**

### 4.4. Verificação das implementações

Para cada alteração, prepare:

- Testes automatizados relevantes.
    
- Testes de integração, quando necessários.
    
- Procedimentos de validação funcional.
    
- Comandos de build, lint, análise estática ou diagnóstico, quando disponíveis.
    
- Critérios objetivos de aceitação.
    
- Casos de borda e cenários de falha.
    
- Procedimentos para identificar regressões.
    
- Evidências que deverão ser produzidas para comprovar o resultado.
    

Quando houver impacto relevante ou risco elevado, inclua estratégias de recuperação, reversão ou rollback.

O objetivo é que a IA implementadora saiba **não apenas o que modificar, mas também como comprovar que a alteração realmente funcionou**.

## 5. Organização estratégica da sequência de prompts

Organize os prompts na ordem ideal de execução, considerando:

1. **Dependências técnicas:** componentes fundamentais deverão estar corretos antes de funcionalidades que dependam deles.
    
2. **Prioridade e impacto:** problemas críticos, bloqueadores ou de maior valor deverão receber a atenção apropriada.
    
3. **Complexidade cognitiva:** tarefas que demandam raciocínio arquitetural profundo não deverão ser sobrecarregadas com problemas independentes.
    
4. **Riscos de regressão:** alterações sensíveis deverão ser acompanhadas de verificações proporcionais ao risco.
    
5. **Afinidade entre alterações:** mudanças relacionadas poderão ser agrupadas para reduzir repetição de contexto e operações redundantes.
    
6. **Reutilização de conhecimento:** resultados e componentes produzidos em uma etapa deverão ser aproveitados nas etapas seguintes.
    
7. **Verificabilidade:** cada etapa deverá produzir resultados suficientemente claros para permitir determinar se pode ser considerada concluída.
    

### Critérios para agrupar tarefas

Agrupe alterações quando:

- Compartilharem os mesmos arquivos, módulos ou componentes.
    
- Resolverem partes relacionadas de um mesmo problema.
    
- Dependerem do mesmo contexto técnico.
    
- Puderem ser testadas conjuntamente sem comprometer a clareza dos resultados.
    
- O agrupamento reduzir significativamente o esforço sem aumentar excessivamente os riscos.
    

Separe alterações quando:

- Exigirem decisões arquiteturais independentes ou complexas.
    
- Envolverem riscos elevados ou mudanças estruturais sensíveis.
    
- Dependerem de resultados ainda não conhecidos.
    
- Demandarem investigação especializada.
    
- O agrupamento dificultar o diagnóstico de falhas ou a validação individual.
    

**Não divida excessivamente tarefas simples, mas também não concentre problemas complexos demais em um único prompt.**

A economia de prompts deve resultar de uma organização tecnicamente inteligente, e não de compactação artificial.

## 6. Requisitos obrigatórios de cada prompt

Cada prompt deverá ser **autossuficiente, objetivo, operacional e suficientemente detalhado** para que a IA implementadora consiga iniciar o trabalho imediatamente.

Cada prompt deverá conter, conforme sua aplicabilidade:

### 6.1. Objetivo e justificativa

Explique:

- O que precisa ser implementado, corrigido ou aprimorado.
    
- Por que a alteração é necessária.
    
- Qual problema deverá ser resolvido.
    
- Qual resultado concreto é esperado.
    

### 6.2. Contexto técnico

Forneça as informações necessárias para a execução, incluindo:

- Arquitetura e componentes envolvidos.
    
- Arquivos e caminhos relevantes.
    
- Comportamento atual identificado.
    
- Comportamento desejado.
    
- Dependências e decisões arquiteturais já estabelecidas.
    

Inclua o contexto suficiente para tornar o prompt independente das explicações desta etapa de planejamento.

### 6.3. Instruções de implementação

Descreva:

- Quais arquivos e componentes deverão ser modificados.
    
- Quais alterações deverão ser realizadas.
    
- Qual código previamente preparado poderá ser utilizado.
    
- Como integrar as mudanças aos recursos existentes.
    
- Quais contratos, interfaces e comportamentos deverão ser preservados.
    

Sempre que possível, incorpore o código preparado diretamente ao prompt ou indique sua localização exata em um artefato acessível à IA implementadora.

### 6.4. Liberdade crítica e arquitetural

Instrua a IA implementadora a verificar a adequação da solução proposta ao código real.

Ela deverá identificar eventuais incompatibilidades, riscos ou oportunidades de melhoria, podendo adotar uma alternativa superior quando houver justificativa técnica consistente.

### 6.5. Testes e validação

Defina:

- Quais verificações deverão ser executadas.
    
- Quais testes existentes deverão continuar passando.
    
- Quais testes adicionais deverão ser criados.
    
- Como reproduzir e confirmar a correção.
    
- Quais evidências deverão comprovar a implementação.
    

### 6.6. Critérios objetivos de conclusão

Estabeleça condições claras para considerar a tarefa concluída.

A conclusão deverá depender de resultados observáveis e verificáveis, não apenas da aplicação de alterações ou da ausência aparente de erros.

### 6.7. Registro e documentação final

Indique:

- Quais documentos deverão ser atualizados.
    
- Quais decisões técnicas deverão ser registradas.
    
- Quais alterações realizadas deverão ser descritas.
    
- Quais testes, resultados e evidências deverão ser preservados.
    
- Quais limitações ou pendências deverão ser comunicadas.
    

### 6.8. Relatório de execução

Ao finalizar cada prompt, a IA implementadora deverá apresentar um relatório objetivo contendo:

- Alterações efetivamente realizadas.
    
- Arquivos criados ou modificados.
    
- Decisões técnicas relevantes e eventuais desvios da solução proposta.
    
- Testes executados e respectivos resultados.
    
- Evidências de funcionamento.
    
- Problemas encontrados e como foram resolvidos.
    
- Pendências, limitações ou bloqueios restantes.
    

**Cada prompt deverá resultar, sempre que houver condições técnicas e operacionais, em alterações reais, integradas, testadas e verificadas no projeto.**

## 7. Autonomia e postura da IA implementadora

Embora os prompts devam oferecer soluções praticamente prontas, não quero transformar a IA implementadora em uma executora mecânica, limitada a copiar e colar código.

Ela deverá assumir simultaneamente duas responsabilidades complementares.

### 7.1. Analista crítica e arquitetural

A IA deverá:

- Avaliar criticamente as soluções propostas.
    
- Confrontá-las com a arquitetura e o código realmente existentes.
    
- Identificar incompatibilidades, riscos e consequências não previstas.
    
- Verificar a preservação dos contratos e comportamentos existentes.
    
- Reconhecer oportunidades concretas de simplificação, reutilização ou melhoria.
    
- Questionar recomendações tecnicamente inadequadas, mesmo quando apresentadas de maneira detalhada.
    

**Uma solução não deverá ser aceita apenas porque foi previamente proposta.**

Se encontrar uma alternativa comprovadamente superior, a IA terá liberdade para adotá-la, desde que preserve os objetivos, requisitos, contratos e decisões arquiteturais estabelecidos.

Qualquer desvio relevante deverá ser justificado e documentado.

### 7.2. Engenheira implementadora

A IA deverá:

- Realizar efetivamente as alterações necessárias.
    
- Integrar as soluções à arquitetura existente.
    
- Executar os testes e verificações apropriados.
    
- Investigar e corrigir problemas identificados durante a implementação.
    
- Confirmar os resultados em condições representativas do funcionamento real.
    
- Atualizar a documentação relevante.
    
- Apresentar evidências concretas do trabalho executado.
    

**A tarefa não deverá terminar em uma nova análise ou recomendação quando houver condições de implementar.**

Se a solução inicialmente preparada apresentar problemas, a responsabilidade da IA será aprimorá-la e concluir a implementação, e não simplesmente devolver o problema ao usuário.

### 7.3. Limites da autonomia

A liberdade técnica não deverá servir como justificativa para:

- Repetir investigações já suficientemente concluídas.
    
- Ampliar o escopo sem necessidade.
    
- Refatorar componentes não relacionados.
    
- Substituir arquiteturas existentes sem justificativa.
    
- Reconstruir funcionalidades já disponíveis.
    
- Introduzir dependências desnecessárias.
    
- Ignorar decisões arquiteturais estabelecidas.
    
- Modificar contratos externos sem avaliar suas consequências.
    
- Comprometer alterações preexistentes ou trabalho realizado por outros agentes.
    
- Declarar como concluídas implementações que não foram verificadas.
    

Em caso de divergência entre a proposta preparada e o estado real do projeto, a IA deverá priorizar as evidências técnicas atuais, respeitando os objetivos e as restrições estabelecidas.

As soluções antecipadamente preparadas deverão funcionar como uma **base técnica de alta qualidade, não como uma imposição inflexível**.

## 8. Continuidade, preservação do trabalho e prevenção de regressões

Considere que o projeto pode conter alterações em andamento, trabalho não consolidado, arquivos modificados por outros agentes e decisões anteriores que precisam ser preservadas.

Antes de executar modificações relevantes, a IA implementadora deverá verificar, conforme as ferramentas disponíveis:

- O estado atual dos arquivos envolvidos.
    
- A existência de alterações não consolidadas.
    
- Possíveis conflitos com trabalho paralelo.
    
- As convenções existentes de versionamento e integração.
    
- Os mecanismos de recuperação disponíveis.
    

Não presuma que é seguro sobrescrever arquivos, descartar alterações, trocar branches, executar comandos destrutivos ou restaurar versões anteriores.

**Preserve o trabalho existente e evite operações potencialmente destrutivas sem necessidade e sem as salvaguardas apropriadas.**

Sempre que possível, cada etapa deverá manter o projeto em um estado funcional e verificável, permitindo continuidade segura para a etapa seguinte.

Os prompts também deverão evitar que implementações posteriores desfaçam decisões ou correções realizadas anteriormente.

## 9. Resultado esperado da etapa de planejamento

Ao concluir a análise e preparação, quero receber os seguintes entregáveis.

### 9.1. Diagnóstico técnico consolidado

Uma síntese dos problemas que serão tratados, das evidências relevantes, das causas conhecidas, das dependências e dos riscos.

Não repita desnecessariamente toda a análise anterior. Concentre-se no conhecimento necessário para fundamentar as implementações.

### 9.2. Documentação atualizada

Os documentos pertinentes do projeto deverão estar atualizados com as descobertas, decisões e diretrizes estabelecidas.

Se a atualização direta não for possível, forneça o conteúdo ou patch preparado, indicando o destino correto e a limitação encontrada.

### 9.3. Soluções técnicas preparadas

Apresente, sempre que viável:

- Código pronto para utilização.
    
- Patches ou diffs aplicáveis.
    
- Alterações de configuração e integração.
    
- Caminhos exatos dos arquivos envolvidos.
    
- Dependências que precisarão ser respeitadas.
    
- Testes e critérios de aceitação correspondentes.
    

### 9.4. Sequência otimizada de prompts

Entregue a sequência completa de prompts, na ordem recomendada de execução.

Cada prompt deverá estar pronto para ser copiado e enviado à IA implementadora, sem depender de explicações externas, informações implícitas ou referências indisponíveis.

Quando necessário, inclua explicitamente os pré-requisitos de execução e os resultados esperados das etapas anteriores.

### 9.5. Mapa de dependências e critérios de avanço

Deixe claro:

- Quais etapas são independentes.
    
- Quais dependem de implementações anteriores.
    
- Quais validações precisam ser concluídas antes de avançar.
    
- Quais riscos exigem atenção especial.
    
- Quais resultados permitem considerar uma etapa efetivamente encerrada.
    

### 9.6. Transparência sobre o que foi realizado

Diferencie claramente:

- Análises e verificações efetivamente realizadas.
    
- Documentos efetivamente modificados.
    
- Soluções preparadas, mas ainda não aplicadas.
    
- Código efetivamente implementado, caso alguma implementação tenha sido realizada.
    
- Testes realmente executados.
    
- Verificações ainda pendentes ou impossibilitadas.
    

Não apresente resultados esperados como resultados comprovados.

## 10. Diretriz central de execução

O princípio central é:

**Concentrar o esforço de raciocínio, investigação e planejamento nesta etapa para reduzir ao máximo o trabalho interpretativo da IA implementadora, sem comprometer sua capacidade crítica, autonomia técnica e responsabilidade pelos resultados.**

Quero que a IA implementadora gaste menos tempo tentando descobrir o que fazer e mais tempo efetivamente:

- Implementando soluções.
    
- Integrando alterações.
    
- Executando testes.
    
- Corrigindo falhas.
    
- Verificando resultados.
    
- Aprimorando a qualidade do projeto.
    

O planejamento deverá eliminar ambiguidades sempre que possível, antecipar dificuldades previsíveis e oferecer soluções concretas, mas sem impedir adaptações tecnicamente justificadas durante a execução.

**Não transforme a preparação em uma investigação interminável.** Quando as evidências disponíveis forem suficientes para definir uma solução segura, avance para sua preparação.

Da mesma forma, não sacrifique correção arquitetural ou segurança apenas para produzir rapidamente uma sequência de prompts.

## 11. Critério definitivo de sucesso

O objetivo final não é produzir mais planejamento, documentação ou recomendações por si só.

É **acelerar a evolução concreta do projeto, com precisão técnica, qualidade arquitetural, preservação do trabalho existente e o mínimo possível de retrabalho**.

A qualidade deste planejamento deverá ser avaliada principalmente por sua capacidade de permitir que a IA implementadora:

1. Compreenda imediatamente o problema e o resultado desejado.
    
2. Localize os componentes relevantes sem investigação redundante.
    
3. Utilize soluções previamente preparadas e tecnicamente fundamentadas.
    
4. Exerça julgamento crítico quando necessário.
    
5. Execute alterações reais e integradas.
    
6. Comprove os resultados por meio de testes e evidências.
    
7. Preserve a integridade e a continuidade do projeto.
    
8. Conclua cada etapa com o menor desperdício possível de contexto, tempo e esforço.
    

**O melhor plano não é o mais extenso nem o que contém menos prompts: é aquele que transforma conhecimento técnico em implementações corretas, verificáveis e sustentáveis com a maior eficiência possível.**