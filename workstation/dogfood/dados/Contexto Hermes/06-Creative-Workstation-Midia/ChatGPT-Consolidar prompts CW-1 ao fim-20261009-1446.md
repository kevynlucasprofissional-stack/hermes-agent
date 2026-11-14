# Consolidar prompts CW-1 ao fim

**User:** Anonymous  
**Created:** 10/8/2026 15:19:08  
**Updated:** 10/8/2026 17:30:07  
**Exported:** 10/9/2026 14:46:58  
**Link:** [https://chatgpt.com/c/6ac7de9b-d900-83e9-b3c7-e8d69022d200](https://chatgpt.com/c/6ac7de9b-d900-83e9-b3c7-e8d69022d200)  

## Prompt:
08/10/2026, 15:19:10

Cria um prompt consolidado para eu mandar para a IA e ela realizar tudo, o prompt abaixo na verdade são 2, quero manter a profundidade do primeiro e os detalhes extras do segundo, o segundo pede para começar pela CW-1 ou algo assim, mas o prompt final deve falar para começar pela CW-1 e ir até o final. Segue em anexo.

[Attachment: Markdown colado(1).md]

## Response:
08/10/2026, 15:19:17 · gpt-6-thinking

> **Consolidando o prompt**
>
> Estou organizando o material em um único artefato, preservando as fases CW-01 a CW-07, os gates, as condições de bloqueio, a progressão entre PRs e a regra de não fazer merge automático.
>
> **Consolidando a execução**
>
> Estou estruturando um prompt único para conduzir o trabalho de CW-01 a CW-07, com branches empilhadas, gates verificáveis, PRs sem merge automático, bloqueios localizados e continuidade somente quando houver base validada.
>
> **Consolidou o prompt e a execução**
>
> 
>
> Pensou por 23s

Consolidei os dois prompts em uma única instrução de implementação. Mantive a profundidade arquitetural e técnica do primeiro, incorporei os documentos, gates e critérios adicionais do segundo e corrigi a principal limitação: **a IA deverá começar pela CW-01 e avançar sequencialmente até a CW-07**, sem encerrar o trabalho após a auditoria inicial.

O prompt também diferencia bloqueios reais de pendências não impeditivas, permite trabalhar com PRs dependentes sem fazer merge automático e exige evidências concretas em cada fase.

<WritingBlock id="58321" variant="document"># PROMPT MESTRE - IMPLEMENTAÇÃO INTEGRAL DO HERMES CREATIVE WORKSTATION

## 0. MISSÃO E AUTORIZAÇÃO DE EXECUÇÃO

Você é o agente engenheiro responsável pela implementação integral do **Hermes Creative Workstation**, uma extensão do Hermes Workstation existente.

**Repositório:**
`kevynlucasprofissional-stack/hermes-agent`

**Diretório da iniciativa:**
`workstation/creative-workstation/`

**Plano inicial:** PR #50  
https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/50

**Branch de documentação:**
`docs/creative-workstation-foundation-20261008`

### Objetivo

Transformar o Hermes Work em uma estação criativa integrada na qual o agente possa criar, modificar, visualizar, renderizar, verificar, preservar e reutilizar projetos produzidos por diferentes engines especializadas.

O usuário e o agente deverão poder trabalhar nos mesmos projetos editáveis, preservando revisões, arquivos nativos, assets, operações e evidências.

O Hermes deverá aproveitar sua arquitetura operacional existente, incluindo Control Plane, TaskCompiler, OperationalCapabilityRegistry, Experience Compiler, ArtifactStore, ExecutionJournal, Chromium/Electron, plugins, skills e MCP.

### Ordem de execução obrigatória

**EXECUTE A INICIATIVA COMPLETA, COMEÇANDO PELA CW-01 E AVANÇANDO ATÉ A CW-07.**

A CW-01 não é a tarefa final. É a primeira fase de uma execução sequencial.

Ordem:

1. CW-01 - Auditoria, baseline, owners, segurança e liberação.
2. CW-02 - Creative Runtime, descoberta, lifecycle e health.
3. CW-03A - React/SVG, Chromium real, PNG e persistência.
4. CW-03B - FFmpeg/ffprobe e processamento audiovisual.
5. CW-03C - Remotion, condicionado à aprovação de licenciamento e segurança.
6. CW-04 - Penpot, MCP e edição colaborativa.
7. CW-05 - Three.js Editor, bridge tipada e edição de cenas 3D.
8. CW-06 - Engines especializadas, Creative Project Manifest e consolidação.
9. CW-07 - Integração criativa ao Experience Compiler e reutilização operacional.

As subdivisões CW-03A/B/C fazem parte da CW-03.

**Não pare voluntariamente após CW-01, CW-02 ou qualquer outra fase.**

Ao concluir e qualificar uma fase, registre seu resultado, crie o PR correspondente quando aplicável e avance para a próxima fase elegível, sem exigir que o usuário envie um novo prompt.

Não confunda autonomia de execução com autorização irrestrita. Nenhuma instrução deste prompt substitui os gates canônicos, as permissões exigidas ou as decisões humanas reservadas.

Se encontrar um bloqueio real:

- Identifique sua causa e seu impacto exato.
- Execute as correções que estejam dentro da autoridade e do escopo permitido.
- Reexecute os testes necessários.
- Continue se o bloqueio tiver sido comprovadamente resolvido.
- Se não puder resolvê-lo com segurança, interrompa apenas o trabalho dependente desse bloqueio.
- Prossiga com atividades independentes e permitidas.
- Não declare etapas bloqueadas como concluídas.
- Não use pendências cosméticas ou questões já resolvidas pela documentação como pretexto para interromper toda a execução.

**Não faça merge automaticamente no `main`.**

---

## 1. PRINCÍPIOS DE EXECUÇÃO

Esta iniciativa já possui visão, prioridades e arquitetura documentadas.

Portanto:

**Não reinicie a discussão arquitetural. Não substitua o plano existente por uma proposta nova. Implemente a solução documentada.**

Adaptações só são permitidas quando a inspeção do código atual, os contratos existentes, as limitações comprovadas ou os testes demonstrarem que são necessárias.

Adote os seguintes princípios:

- **Upstream-first:** preservar compatibilidade com o Hermes Agent e seguir os procedimentos de sincronização estabelecidos.
- **First-party seams:** integrar tecnologias externas pelos pontos de extensão legítimos do Hermes.
- **Menor mudança suficiente:** evitar refatorações e abstrações desnecessárias.
- **Sem autoridades paralelas:** não duplicar registries, approvals, journals, sessões ou mecanismos de execução.
- **Projetos editáveis:** preservar os fontes e não apenas outputs renderizados.
- **Evidência empírica:** demonstrar funcionamento real, não apenas compilação ou testes simulados.
- **Segurança por padrão:** autorização explícita para ações privilegiadas e efeitos externos.
- **Reutilização operacional:** aproveitar capacidades existentes antes de introduzir novas.
- **Mudanças reversíveis:** suporte a rollback, cancelamento, retomada e diagnóstico.
- **Documentação sincronizada:** registrar decisões e estado efetivo conforme a implementação progride.

Não faça mudanças amplas por conveniência. Não introduza dependências apenas porque elas poderão ser úteis futuramente.

---

## 2. DOCUMENTAÇÃO E CONTEXTO - LEITURA OTIMIZADA

### 2.1. Fonte inicial

A especificação inicial encontra-se no PR #50, especialmente em:

- `workstation/creative-workstation/README.md`
- `workstation/creative-workstation/ARCHITECTURE.md`
- `workstation/creative-workstation/IMPLEMENTATION_PLAN.md`
- `workstation/creative-workstation/INTEGRATIONS.md`
- `workstation/creative-workstation/AGENTS.md`
- `workstation/creative-workstation/IMPLEMENTER_PROMPT.md`

O plano adicional introduz os documentos operacionais:

- `workstation/creative-workstation/EXECUTION_BRIEF.md`
- `workstation/creative-workstation/VERIFICATION_MATRIX.md`
- `workstation/creative-workstation/PHASE_PROMPTS.md`

Confirme a presença e o conteúdo desses arquivos na branch correta.

Se o PR #50 ainda não estiver integrado, consulte-o diretamente pela branch de documentação. **Não faça merge apenas para acessar a especificação.**

### 2.2. Leitura canônica obrigatória

Antes de modificar qualquer código, leia, na ordem aplicável:

1. `AGENTS.md`
2. `workstation/AGENTS.md`
3. `workstation/context/README.md`
4. Todos os documentos e gates adicionais exigidos por esses arquivos.

Consulte também os documentos canônicos pertinentes:

- `workstation/ROADMAP.md`
- `workstation/SOURCE_MATRIX.md`
- `workstation/ARCHITECTURE.md`
- `workstation/context/CURRENT_STATE.md`
- `workstation/context/DECISIONS.md`
- `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md`
- `workstation/context/EXPERIENCE_COMPILER.md`
- `workstation/context/engineering-journal/CURRENT.md`

Verifique os caminhos reais e as instruções de precedência dos documentos antes de usá-los.

### 2.3. Estratégia para economizar contexto e processamento

A leitura deve ser seletiva, mas nunca omitir uma obrigação canônica.

Depois das leituras obrigatórias:

1. Consulte `EXECUTION_BRIEF.md` para recuperar o contexto executivo consolidado.
2. Consulte somente a seção da fase atual em `IMPLEMENTATION_PLAN.md`.
3. Consulte os critérios correspondentes em `VERIFICATION_MATRIX.md`.
4. Consulte o prompt específico dessa fase em `PHASE_PROMPTS.md`.
5. Investigue os owners e os símbolos de código afetados.
6. Carregue documentação adicional somente quando necessária.

Não examine milhares de arquivos sem justificativa. Use buscas por símbolos, caminhos, dependências e contratos.

Não reconstrua decisões já registradas sem evidência de incompatibilidade.

### 2.4. Precedência em caso de conflito

Respeite primeiro as instruções e políticas canônicas aplicáveis, os gates de segurança e os contratos executáveis vigentes.

Use a documentação da iniciativa como especificação funcional.

Considere o código como evidência do comportamento atual, não como justificativa automática para descartar requisitos.

Se houver conflito material:

- Identifique as fontes conflitantes.
- Registre o requisito e o comportamento real.
- Avalie a menor solução compatível.
- Resolva dentro da autoridade disponível.
- Registre uma decisão arquitetural explícita quando necessária.
- Não silencie requisitos importantes por conveniência.

---

## 3. CW-01 - AUDITORIA, BASELINE E LIBERAÇÃO

**Objetivo:** determinar precisamente o estado do Hermes, localizar os pontos corretos de integração e estabelecer um baseline qualificado.

Esta é a primeira etapa de execução.

### 3.1. Auditoria do repositório

Identifique:

- HEAD atual do `main`.
- Estado e base do PR #50.
- HEAD da branch de documentação.
- Upstream remoto e SHA fixado.
- Merge-base relevante.
- Alterações pendentes.
- Branches de trabalho relacionadas.
- Checks obrigatórios e situação do CI.
- Políticas vigentes de branch e merge.

Execute o procedimento **H-079 upstream-first** conforme sua definição canônica.

Verifique H-080A, H-080B, KI-024 e os demais bloqueios críticos vigentes.

Não pressuponha que um bloqueio histórico continua aberto. Confirme seu estado atual com evidências.

Não faça implementação funcional sobre um baseline considerado bloqueado pela política canônica.

### 3.2. Auditoria dos subsistemas

Identifique os owners, seams, símbolos e contratos atuais dos seguintes subsistemas:

| Subsistema | Responsabilidade investigada |
|---|---|
| Control Plane | Autoridade, políticas, verificações |
| Capability Router | Seleção e encaminhamento de capacidades |
| TaskCompiler | Compilação e execução operacional |
| OperationalCapabilityRegistry | Descoberta e reutilização de capacidades |
| Experience Compiler | Extração, certificação e promoção |
| ArtifactStore | Persistência e referência de artefatos |
| ExecutionJournal | Evidências e histórico de execução |
| Session / TaskRun / Kanban | Estado e ciclo de tarefas |
| BrowserTask / Chromium Electron | Visualização e automação |
| Plugins / Skills / MCP | Integrações externas |
| Lifecycle / Health | Processos, recursos e dependências |

Investigue inicialmente, quando existentes e pertinentes:

- `workstation/capabilities.py`
- `workstation/control_plane/`
- `workstation/operational_capabilities.py`
- `workstation/host.py`
- `workstation/health.py`
- `apps/desktop/electron/`
- `workstation/components.lock.json`

Esses caminhos são referências de investigação, não autorização para modificá-los indiscriminadamente.

### 3.3. Matriz de reutilização

Produza a matriz:

`owner → arquivo::símbolo → contrato/comportamento atual → capacidade reutilizável → lacuna concreta → menor alteração necessária`

Cubra obrigatoriamente:

- Descoberta e lifecycle de engines.
- MCP e skills.
- Chromium e Electron.
- Execução controlada.
- Persistência e revisões.
- Verificação de artefatos.
- Experience Compiler.
- Permissões, cancelamento e rollback.

**Não crie uma nova infraestrutura quando a existente já atender ao contrato.**

### 3.4. Auditoria das tecnologias externas

Verifique fontes oficiais, commits/versões, dependências, riscos e condições de licenciamento para:

- Penpot MCP.
- Penpot AI Kit.
- Three.js Editor.
- FFmpeg e ffprobe.
- Remotion.

Registre compatibilidade com as plataformas-alvo, principalmente Windows e Hermes Desktop/Electron.

Audite também os limites de isolamento, credenciais, filesystem e execução arbitrária.

Não instale as tecnologias durante CW-01.

### 3.5. Entregas e conclusão da CW-01

Registre os resultados no jornal de engenharia e nos documentos pertinentes.

Forneça:

- SHAs reais.
- Gates e CI verificados.
- Owners e contratos.
- Bloqueios comprovados.
- Falsificadores das principais hipóteses.
- Riscos de integração.
- Lista mínima de arquivos e símbolos a modificar na CW-02.
- Classificação de liberação: `GO` ou `BLOCKED`.

Se `GO`, **inicie CW-02 imediatamente**.

Se `BLOCKED`, resolva os bloqueios reparáveis dentro da autoridade disponível. Se permanecer bloqueado, não altere runtime dependente.

---

## 4. CW-02 - CREATIVE RUNTIME

**Objetivo:** disponibilizar engines criativas ao Hermes pelo mecanismo operacional existente.

Implemente a menor extensão suficiente para:

1. Descobrir ferramentas instaladas.
2. Detectar versões e dependências.
3. Classificar compatibilidade.
4. Solicitar autorização para instalações opcionais.
5. Inicializar e encerrar processos controlados.
6. Executar health checks.
7. Gerenciar portas locais e conflitos.
8. Isolar processos e recursos.
9. Persistir os projetos e referências necessários.
10. Recuperar estado depois de reinicialização.
11. Reportar erros estruturados.
12. Desativar ou remover integrações de forma segura.

### Regras de arquitetura

Não crie outro lifecycle manager se o Hermes já tiver um equivalente.

Não crie um registry paralelo ao `OperationalCapabilityRegistry`.

Não crie um novo sistema de sessão ou um novo modelo de autorização.

Utilize Control Plane, Policy, Verifier, ArtifactStore e ExecutionJournal existentes.

Prefira operações tipadas e contratos verificáveis.

### Critérios de aceitação

Demonstre descoberta de dependência presente e ausente, versão incompatível, health positivo e negativo, cancelamento, término de processo, porta ocupada, recuperação e impossibilidade de executar ação não autorizada.

Certifique-se de que engines opcionais não sejam instaladas ou iniciadas silenciosamente.

Após testes e qualificações aplicáveis, documente os resultados, abra o PR específico e avance para CW-03A.

---

## 5. CW-03A - PRIMEIRA VERTICAL CRIATIVA

**Objetivo:** provar uma experiência criativa completa antes de adicionar editores complexos.

### Fluxo obrigatório

`Solicitação → execução React/SVG → preview Chromium → renderização PNG → verificação → persistência → reabertura`

O agente deverá:

1. Receber uma solicitação de criação visual.
2. Criar um projeto editável React/SVG.
3. Registrar os fontes e assets.
4. Abrir uma prévia no Chromium real do Hermes Desktop.
5. Gerar um PNG correspondente ao projeto.
6. Verificar dimensões, formato, integridade e hashes.
7. Registrar evidências no ArtifactStore/ExecutionJournal.
8. Preservar o projeto editável.
9. Reabrir o mesmo projeto após reinicialização.

### Requisitos adicionais

Separe fontes editáveis dos outputs gerados.

Preserve referências estáveis entre projeto, task, evidências e artefatos.

Não dependa exclusivamente de screenshots ou coordenadas para identificar objetos.

Não substitua um projeto real por um mock que apenas simule o resultado final.

### Teste obrigatório

Executar o fluxo completo com o **Chromium real do Hermes Desktop/Electron**, incluindo exportação e reabertura.

Testes unitários não substituem esse E2E.

Se o ambiente atual não permitir Electron real, execute as verificações disponíveis, marque o E2E `NOT_RUN` e não declare `QUALIFIED`.

Após qualificação, avance para CW-03B.

---

## 6. CW-03B - FFMPEG E FFPROBE

**Objetivo:** incorporar processamento audiovisual verificável.

Integre FFmpeg/ffprobe usando operações controladas e contratos tipados.

Capacidades iniciais:

- Inspecionar arquivos de mídia.
- Ler metadados técnicos.
- Identificar codecs, resolução, duração e streams.
- Converter formatos suportados.
- Produzir vídeo a partir de frames.
- Processar áudio quando solicitado.
- Validar arquivos gerados.
- Tratar erros, cancelamentos e processos interrompidos.

### Segurança

Não exponha comandos arbitrários sem validação.

Valide caminhos, parâmetros, arquivos de entrada, destinos e escopo de escrita.

Previna writes fora do workspace autorizado.

Evite sobrescritas destrutivas e execuções duplicadas.

### Qualificação

Teste arquivos válidos e inválidos, parâmetros incompatíveis, cancelamento, recuperação, outputs e inspeção com ffprobe.

Verifique integridade, dimensões, streams, duração quando aplicável e hashes.

Depois da qualificação, prossiga para CW-03C.

---

## 7. CW-03C - REMOTION

**Objetivo:** permitir motion graphics programáticos e renderização de vídeos editáveis.

Esta integração é **condicionada ao licenciamento e à compatibilidade operacional**.

### Primeiro: licenciamento

Verifique:

- Licença oficial vigente.
- Direitos para uso comercial.
- Condições de redistribuição.
- Impacto do modelo de distribuição do Hermes.
- Dependências e custos aplicáveis.
- Permissões e restrições relevantes.

Não presuma que Remotion é MIT ou que sua licença permite qualquer integração.

Se a licença não permitir a integração proposta, registre `BLOCKED` para CW-03C e não incorpore a tecnologia indevidamente.

Esse impedimento não deve bloquear automaticamente Penpot, Three.js ou as outras engines independentes.

### Implementação autorizada

Se os requisitos forem atendidos:

1. Criar projetos editáveis de animação React/Remotion.
2. Parametrizar cenas e composições.
3. Visualizar animações no Chromium.
4. Renderizar frames e vídeos.
5. Verificar outputs com os mecanismos existentes.
6. Preservar código, assets, composição e dependências.
7. Permitir alterações posteriores.
8. Registrar evidências e metadados da renderização.

### Testes

Demonstre renderização real, reabertura, alteração de parâmetros, cancelamento, erros e verificação do vídeo.

Registre limitações técnicas ou de licença.

Após a qualificação possível dessa etapa, avance para CW-04.

---

## 8. CW-04 - PENPOT

**Objetivo:** integrar uma superfície de design visual estruturado, editável tanto pelo usuário quanto pelo agente.

### Fontes iniciais

MCP oficial:
https://github.com/penpot/penpot/tree/develop/mcp

AI Kit:
https://github.com/penpot/penpot-ai-kit

Confirme contratos, versões e requisitos atuais diretamente nas fontes oficiais.

### Capacidades

Implemente, conforme suporte real das interfaces disponíveis:

- Conexão MCP autorizada.
- Descoberta de projetos e arquivos.
- Leitura de layouts.
- Inspeção de componentes.
- Modificação de elementos.
- Manipulação de tokens e estilos.
- Exportação de assets.
- Abertura no Chromium integrado.
- Identificação de versões e revisões.
- Detecção de conflitos de edição.
- Persistência de referências do projeto.

Não presuma que o MCP oferece todas as operações desejadas. Se uma capacidade não existir, identifique a lacuna e implemente somente uma extensão segura e justificada.

### Teste obrigatório de colaboração humano/agente

Execute este cenário:

1. O agente cria um layout.
2. O projeto abre no Penpot.
3. O usuário modifica manualmente um elemento.
4. O agente recebe uma nova instrução.
5. O agente detecta o estado atualizado.
6. O agente modifica outra parte do projeto.
7. A alteração humana permanece preservada.

Quando ocorrer conflito de revisão, não sobrescreva silenciosamente as alterações do usuário.

### Restrições

O Penpot não deve se tornar uma autoridade paralela para tarefas e políticas do Hermes.

Não instale nem inicialize MCPs automaticamente sem a autorização exigida.

Respeite os limites de credenciais e rede.

Qualifique o fluxo real e avance para CW-05.

---

## 9. CW-05 - THREE.JS EDITOR

**Objetivo:** transformar o editor Three.js em uma superfície 3D editável, controlável por operações tipadas do Hermes.

Fonte oficial:
https://github.com/mrdoob/three.js

### Estratégia arquitetural

Priorize uma bridge fina entre o Hermes e o editor oficial.

Evite fazer fork quando uma extensão ou adaptador resolver o problema.

Caso seja necessário modificar o editor, documente a incompatibilidade, a justificativa e os testes de compatibilidade upstream.

### Contratos desejados

Implemente os métodos aplicáveis:

- `inspectScene`
- `createObject`
- `modifyGeometry`
- `setMaterial`
- `configureLights`
- `configureCamera`
- `addAnimation`
- `importGLB`
- `exportScene`
- `capturePreview`
- `undoTransaction`

Use IDs semânticos estáveis para objetos e controle de revisões.

### Experiência esperada

O agente deverá conseguir:

1. Criar uma cena 3D.
2. Adicionar objetos.
3. Modificar geometria e materiais.
4. Configurar luz e câmera.
5. Adicionar animação.
6. Abrir a cena no editor real.
7. Preservar alterações feitas pelo usuário.
8. Salvar o projeto.
9. Reabrir a cena posteriormente.
10. Exportar formatos compatíveis.
11. Capturar e verificar uma prévia.

### Segurança

Não exponha execução irrestrita de JavaScript em contexto Electron privilegiado.

Valide mensagens entre contextos, parâmetros e escopos.

Controle mutações de cena, erros parciais e transações.

Não execute retries cegos quando o resultado de uma mutação for incerto.

### Teste obrigatório

Criação, edição, preview, exportação, reabertura e recuperação de cena real.

Inclua testes de conflito, objeto inexistente, operação inválida e undo.

Após qualificação, avance para CW-06.

---

## 10. CW-06 - ENGINES ESPECIALIZADAS E MANIFESTO DE PROJETOS

**Objetivo:** consolidar o ecossistema criativo e estabelecer a interoperabilidade possível sem introduzir complexidade desnecessária.

### 10.1. Engines especializadas

Avalie progressivamente:

- Inkscape CLI, para processamento SVG.
- Blender Python/headless, para modelagem e renderização.
- GIMP/Krita, apenas mediante necessidade concreta.
- FFmpeg/ffprobe, como infraestrutura audiovisual já integrada anteriormente.

Cada engine efetivamente incorporada deverá possuir:

- Contratos tipados.
- Discovery e health.
- Versão e dependências.
- Escopo de filesystem.
- Autorizações.
- Isolamento.
- Cancelamento.
- Verificação dos outputs.
- Recuperação de falhas.
- Rollback e desativação.

Não instale todas as ferramentas antecipadamente.

Se uma engine opcional não for necessária, registre a decisão de adiamento em vez de inventar uma implementação sem caso de uso.

### 10.2. Tecnologias que permanecem opcionais

Graphite, Tone.js, Strudel, Godot, PartMode, replicad e tecnologias semelhantes permanecem no backlog até existir justificativa técnica e funcional.

Não amplie o escopo apenas porque uma ferramenta parece interessante.

### 10.3. Creative Project Manifest

Defina e integre um formato de referência versionado que preserve:

- Identificador do projeto.
- Referência do workspace.
- Engine principal e engines auxiliares.
- Fontes editáveis nativas.
- Assets e dependências.
- Parâmetros de criação e render.
- Versões e requisitos.
- Revisões e hashes.
- Outputs produzidos.
- Histórico ou referências de transformações.
- Evidências de execução.
- Referências aos registros existentes do Hermes.

O manifesto deverá suportar projetos com diferentes engines sem exigir uma representação universal destrutiva.

Ele não substitui `TaskRun`, `ArtifactStore`, `ExecutionJournal` nem o registry operacional.

### 10.4. Interoperabilidade

Quando tecnicamente suportado, permita importação, exportação e transformações controladas entre formatos.

Não prometa conversão perfeita entre:

- Penpot.
- React.
- SVG.
- Three.js.
- Blender.
- Formatos de vídeo e imagem.

Quando uma transformação perder editabilidade, informação ou semântica, registre explicitamente a limitação.

### 10.5. Qualificação

Teste persistência e recuperação de projetos, resolução de dependências, versões incompatíveis, referência quebrada, outputs e operações suportadas.

Ao concluir, avance para CW-07.

---

## 11. CW-07 - EXPERIENCE COMPILER E REUTILIZAÇÃO OPERACIONAL

**Objetivo:** permitir que o Hermes aprenda a reutilizar procedimentos criativos efetivamente comprovados.

A integração deve usar o **Experience Compiler já existente**, sem criar outro.

### Pré-condição

Pelo menos uma vertical criativa precisa estar realmente funcional e possuir evidências verificáveis.

Não transforme uma sequência hipotética em capability certificada.

### Pipeline obrigatório

1. **Observação:** registrar operações executadas durante tarefas criativas.
2. **Efeitos:** identificar resultados observáveis e verificáveis.
3. **Mineração:** reconhecer sequências candidatas à reutilização.
4. **Parametrização:** distinguir dados variáveis de operações estáveis.
5. **Candidatura:** gerar candidatos operacionais compatíveis com os contratos existentes.
6. **Validação positiva:** demonstrar resultados esperados.
7. **Validação negativa:** executar controles negativos seguros.
8. **Replay:** reproduzir operações em contexto controlado.
9. **Certificação:** utilizar a política de promoção existente.
10. **Reutilização:** disponibilizar capabilities aprovadas para execuções futuras.

### Exemplos de candidatos

- Criar um SVG a partir de parâmetros.
- Exportar layouts com dimensões específicas.
- Aplicar uma configuração parametrizada de iluminação.
- Produzir previews 3D.
- Renderizar uma composição audiovisual.
- Gerar variantes de design sem reconstruir o projeto.

Esses são exemplos, não autorização para certificar operações sem evidência.

### Regras de promoção

Uma execução bem-sucedida isolada não basta para promoção automática.

A certificação exige os oráculos e políticas aplicáveis, com replay positivo e controles negativos seguros.

Skills em Markdown podem orientar a execução, mas não substituem capacidades executáveis certificadas.

APIs, MCPs, CLIs e bridges realizam operações; a camada operacional do Hermes determina autoridade e reutilização.

### Invalidação

Uma capability deverá ser revalidada quando mudar algum requisito relevante:

- Versão da engine.
- Schema ou contrato.
- Escopo de autorização.
- Dependência necessária.
- Estrutura do projeto.
- Recurso externo.
- Comportamento do verificador.

Não reutilize cegamente uma capability certificada sob condições incompatíveis.

### Eficiência

A meta é reduzir chamadas desnecessárias a LLMs, preservando confiabilidade, qualidade e autoridade.

Não substitua o planejamento inteligente por replay indiscriminado.

Demonstre que um procedimento criativo aprovado pode ser reutilizado em uma tarefa posterior, com validação de seu resultado e registro da execução.

---

## 12. INVARIANTES ARQUITETURAIS

Estas restrições se aplicam a **todas as fases**.

### Componentes que não podem ser duplicados

Não introduza sistemas paralelos de:

- Session.
- TaskRun.
- Kanban.
- BrowserTask.
- Control Plane.
- Approvals e Policy.
- Verifier.
- ExecutionJournal.
- ArtifactStore.
- OperationalCapabilityRegistry.
- Experience Compiler.

Exceções exigem demonstração documentada de insuficiência do contrato atual e uma decisão arquitetural explícita.

### Ordem de preferência para execução

Use, nesta ordem, conforme adequação:

1. APIs e operações tipadas.
2. Código, filesystem e CLI controlados.
3. MCPs autorizados.
4. Browser automation, quando interfaces estruturadas não atenderem à necessidade.

O Chromium deve funcionar prioritariamente como superfície de interação e visualização humana, e não como substituto indiscriminado de APIs.

### Semântica operacional

Preserve a separação entre:

- Instrução.
- Seleção de capacidade.
- Autorização.
- Execução.
- Verificação.
- Persistência.
- Certificação.
- Reutilização.

Não misture essas responsabilidades para simplificar a implementação.

---

## 13. SEGURANÇA, DEPENDÊNCIAS E LICENCIAMENTO

Antes de incorporar cada integração, registre:

- Repositório oficial.
- Commit ou versão fixada.
- Licença e obrigações.
- Condições de uso comercial e redistribuição.
- Dependências diretas e transitivas relevantes.
- Permissões.
- Superfícies de execução.
- Acesso a filesystem, rede e credenciais.
- Possibilidades de execução arbitrária.
- Estratégia de isolamento.
- Estratégia de desativação e rollback.
- Evidências de validação.

Atenção especial à licença própria do Remotion, às condições GPL/AGPL e às licenças independentes de assets ou marcas.

MCPs comunitários e skills externas devem ser auditados.

Não forneça acesso irrestrito à máquina, às credenciais ou ao workspace a componentes externos sem justificativa e autorização.

### Proibições operacionais

- Instalações silenciosas.
- Execução privilegiada arbitrária.
- Escrita fora do escopo autorizado.
- Exposição de segredos em logs.
- Sobrescrita silenciosa de alterações humanas.
- Retry cego de operações mutáveis.
- Operações destrutivas sem autorização exigida.
- Atribuição fictícia de resultados a ferramentas.
- Promoção de capabilities sem validação empírica.

---

## 14. VERIFICAÇÃO E QUALIFICAÇÃO

**`VERIFICATION_MATRIX.md` é a referência operacional dos oráculos, testes negativos, E2E, rollback e gates da iniciativa, subordinada às políticas canônicas aplicáveis.**

Execute para cada fase, conforme o subsistema alterado:

- Testes unitários.
- Testes de integração.
- Testes negativos de autorização.
- Testes de isolamento.
- Testes de cancelamento.
- Testes de recuperação.
- Testes de idempotência e operações duplicadas.
- Testes de persistência.
- Testes de revisões e conflitos.
- Verificação de outputs.
- Regressões dos owners afetados.
- Electron E2E quando houver interface.
- Auditoria de first-party seams.
- CI no HEAD exato.
- Verificação final do upstream e baseline.

Não invente comandos. Descubra os comandos reais nas instruções do projeto e nos respectivos workflows.

Não invente `PASS`, CI verde, logs, hashes, screenshots, receipts ou aprovação de licença.

Use `NOT_RUN` quando um teste não foi executado.

Use `BLOCKED` quando o gate impede a continuidade.

Use `PARTIAL` quando uma entrega estiver incompleta.

### Distinção entre implementação e qualificação

`IMPLEMENTED` não significa `QUALIFIED`.

Uma fase pode ter código implementado e ainda depender de E2E, testes ou CI.

Não declare conclusão integral quando existirem lacunas obrigatórias sem evidência.

Cada fase deve ter critérios explícitos de entrada, saída e aceite.

---

## 15. DISCIPLINA DE GIT E EXECUÇÃO CONTÍNUA

### Branches e PRs

Trabalhe em branches específicas por fase ou subfase.

Não reúna toda a iniciativa em um único PR.

Não misture, sem necessidade, sincronização upstream, runtime, integração de editores e Experience Compiler.

Mantenha commits pequenos e descritivos.

Abra PRs revisáveis com descrição de escopo, evidências e dependências.

### Continuidade sem merge automático

Como o `main` não pode ser modificado automaticamente, preserve a continuidade usando o mecanismo permitido pelo workflow canônico.

Quando uma fase depender de alterações de um PR ainda não integrado, avalie branches e PRs dependentes (*stacked PRs*), preservando bases e SHAs identificáveis.

Use essa estratégia somente quando compatível com as políticas do repositório.

Não finja que o `main` já contém alterações pendentes.

Não qualifique etapas sobre uma base não verificada.

Se o processo exigir aprovação humana ou merge para permitir com segurança a fase seguinte, registre essa dependência e execute apenas as atividades independentes permitidas.

**A ausência de autorização para merge não é autorização para ignorar os gates nem motivo para encerrar prematuramente trabalhos independentes.**

### Documentação

Depois de cada alteração efetiva, atualize os documentos pertinentes:

- Roadmap.
- Current State.
- Decisions, quando houver decisão nova.
- Engineering Journal.
- Hermes Workstation Intelligence.
- Source Matrix, quando houver mudança de fontes, contratos ou owners.
- Documentação da iniciativa.
- Matrizes de verificação e integração, quando aplicável.

Não marque entregas como concluídas antecipadamente.

Evite duplicação documental. Preserve o papel canônico de cada arquivo.

---

## 16. RELATÓRIO OBRIGATÓRIO DE CADA FASE

Ao finalizar cada fase, produza o seguinte registro:

**FASE / STATUS**  
CW-xx - `GO | BLOCKED | PARTIAL | IMPLEMENTED | E2E_PASS | QUALIFIED`, conforme aplicável.

**BASELINE**  
HEAD, upstream pinado, merge-base, gates e situação do CI no commit exato.

**OWNERS**  
`arquivo::símbolo → comportamento reutilizado → alteração realizada`.

**IMPLEMENTAÇÃO**  
Arquivos modificados, contratos novos, componentes reutilizados e comportamento entregue.

**EXTERNAL**  
Engines e integrações, versões, licença, riscos e situação real.

**TESTS**  
Comandos efetivamente executados, resultados, negativos e `NOT_RUN`.

**EVIDENCE**  
Receipts, hashes, revisões, previews, outputs, logs e referências verificáveis.

**BLOCKERS**  
Motivo, impacto, menor correção segura e rollback.

**GITHUB**  
Branch, commits, PR, checks, HEAD e situação de merge.

**NEXT**  
Próxima fase elegível e suas dependências.

### Regra de continuidade

Depois de gerar esse registro:

1. Determine se o gate de saída da fase foi atendido.
2. Se foi atendido, inicie automaticamente a fase seguinte.
3. Se não foi atendido, tente resolver as falhas permitidas.
4. Se persistir bloqueio, identifique os trabalhos independentes autorizados.
5. Não represente como concluída uma fase dependente de uma etapa não qualificada.
6. Não peça novas instruções apenas para continuar o plano já autorizado.

Os relatórios intermediários são checkpoints, não encerramentos da missão.

---

## 17. CENÁRIOS FINAIS DE ACEITAÇÃO

A implementação consolidada deverá buscar demonstrar os seguintes cenários integrados.

### Cenário A - Design editável

O usuário solicita um material visual.

O Hermes produz o projeto, abre o editor compatível no Chromium, permite alterações humanas, preserva revisões e exporta um arquivo verificado.

### Cenário B - Animação e vídeo

O usuário solicita uma animação.

O Hermes utiliza capacidades de composição e renderização autorizadas, gera o vídeo, verifica suas propriedades e preserva o projeto original.

### Cenário C - Criação 3D

O usuário solicita:

"Crie uma logo 3D, anime sua entrada, adicione iluminação, produza um vídeo de oito segundos e preserve o projeto editável."

O Hermes deverá usar as engines compatíveis e efetivamente disponíveis para executar as operações, abrir a cena ou projeto no Chromium, preservar seus fontes e produzir outputs verificáveis.

Se a cadeia completa depender de uma integração não qualificada, reporte a limitação em vez de simular sucesso.

### Cenário D - Reutilização operacional

Depois de executar e certificar adequadamente um procedimento criativo, uma nova solicitação compatível deverá poder reutilizar essa capability pelo mecanismo operacional existente.

Demonstre:

- Seleção da capability.
- Verificação de suas condições de validade.
- Execução controlada.
- Resultado verificável.
- Evidências persistidas.
- Comportamento seguro diante de incompatibilidade.

---

## 18. RELATÓRIO FINAL DA INICIATIVA

Depois de executar todas as fases elegíveis, produza uma consolidação contendo:

1. Status individual de CW-01 a CW-07, incluindo CW-03A/B/C.
2. Matriz de funcionalidades planejadas, implementadas e qualificadas.
3. Componentes existentes reaproveitados.
4. Contratos e componentes novos.
5. Engines integradas e versões efetivamente testadas.
6. PRs, branches, commits e situação dos merges.
7. CI e regressões do HEAD correspondente.
8. Evidências de E2E real.
9. Limitações técnicas e de licenciamento.
10. Bloqueios externos pendentes.
11. Compatibilidade upstream.
12. Situação real do Creative Project Manifest.
13. Situação real da integração ao Experience Compiler.
14. Demonstração dos cenários de aceitação disponíveis.
15. Próximas ações mínimas para alcançar a qualificação integral.

Não declare a iniciativa `QUALIFIED` se alguma integração obrigatória permanecer sem a qualificação exigida.

Diferencie claramente escopo opcional adiado de requisito obrigatório não atendido.

---

## 19. INSTRUÇÃO FINAL - EXECUTAR, NÃO REPLANEJAR

A visão do produto, a ordem das fases e as restrições arquiteturais já estão definidas.

Sua responsabilidade é **transformar essa especificação em implementação real, testada, documentada e inspecionável**.

Não desperdice contexto produzindo uma nova arquitetura especulativa.

Não carregue documentação extensa sem necessidade.

Não instale toda a suíte antecipadamente.

Não crie componentes paralelos.

Não substitua testes reais por mocks.

Não declare resultados inexistentes.

Não faça merge no `main` automaticamente.

Não encerre a execução depois da primeira fase aprovada.

**COMECE AGORA POR CW-01.**

Execute a auditoria H-079, confirme o baseline, libere os gates e identifique os owners e os menores gaps de integração.

Na sequência, implemente CW-02, CW-03A, CW-03B, CW-03C, CW-04, CW-05, CW-06 e CW-07, respeitando a qualificação e as dependências de cada etapa.

**A conclusão esperada não é um novo planejamento. É a máxima implementação efetiva e comprovável de toda a iniciativa, até CW-07, dentro das autorizações e dos gates vigentes.**
</WritingBlock>

**Principal ajuste em relação aos originais:** o primeiro prompt tinha profundidade técnica, mas não organizava toda a execução nos identificadores CW; o segundo tinha essa organização, mas limitava expressamente a execução à CW-01. Esta versão conserva ambos os elementos e estabelece uma continuidade operacional com checkpoints de qualificação, sem transformar cada checkpoint em um ponto de parada obrigatório.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)