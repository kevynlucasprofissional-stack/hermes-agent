# Auditoria do Hermes Work

**User:** Anonymous  
**Created:** 10/18/2026 23:15:11  
**Updated:** 10/19/2026 2:49:07  
**Exported:** 10/19/2026 11:33:06  
**Link:** [https://chatgpt.com/c/6ad57d2f-8238-83e9-8e44-dcf5de45c41a](https://chatgpt.com/c/6ad57d2f-8238-83e9-8e44-dcf5de45c41a)  

## Prompt:
18/10/2026, 23:15:42

[$github](app://connector_76869538009648d5b282a4bb21c3d157)&#x20;

Faça de acordo com o texto colado em relação ao pdf anexado e ao repositório do Hermes Work

[Attachment: 18.10.26 Análises comparativas do Browser por Fable 5.1(1).pdf]

[Attachment: Texto colado(20261019-021515).txt]

## Response:
18/10/2026, 23:15:43 · gpt-6-thinking

Vou seguir o roteiro do texto colado: inventariar as recomendações das 183 páginas, conferir o estado atual da `main` e das PRs pelo GitHub, e confrontar cada capacidade com o código real. Depois entregarei o diagnóstico, a priorização 80/20, o plano de implementação e os critérios de validação.

A auditoria será somente de leitura. Vou distinguir recursos existentes, recursos efetivamente integrados e funcionalidades ainda não comprovadas em execução.

Já encontrei uma discrepância relevante: o relatório trata batch, snapshot diferencial e cache de extração como lacunas, mas há implementações correspondentes na `main`\.

O batch não é apenas uma função isolada: aparece ligado ao dispatch do runtime Electron. A questão passa a ser quanto ele economiza no fluxo completo e quais ações consegue verificar com segurança. Vou conferir essas limitações antes de classificar as melhorias.

A segunda passagem confirmou outro ponto importante: o problema não é só implementar capacidades, mas fazer com que elas economizem trabalho **sem enfraquecer a verificação**\.

Por exemplo, o Hermes já diferencia o ACK do controller de uma confirmação externa persistida. Também possui testes para efeitos incertos, mas alguns usam servidores e cenários controlados, não serviços reais. Estou incorporando essa distinção ao ranking para não propor otimizações que aumentem a taxa de erros silenciosos.

> **Lendo instruções de PDF e listando arquivos**
>
>
> **Lido PDF e listados arquivos**
>
> 
>
> **Automatizei análise, indexação e estruturação de PDFs detalhados**
>
> 
>
> **Extraindo texto e cabeçalhos do PDF**
>
>
> **Extraído texto e cabeçalhos do PDF**
>
> 
>
> **Explorou a estrutura e os arquivos essenciais do repositório Hermes Agent**
>
> 
>
> **Identificando seções e limites dos relatórios**
>
>
> **Encontrando títulos no topo das páginas**
>
>
> **Localizando inícios de relatórios comparativos**
>
>
> **Identificou títulos e limites dos relatórios comparativos**
>
> 
>
> **Analisou execução em lote, cache de snapshots e roteamento de runtime**
>
> 
>
> **Analisando seções prioritárias do relatório**
>
>
> **Analisou as seções prioritárias do relatório**
>
> 
>
> **Auditou código, PRs, CI, licenças, segurança, testes e documentação**
>
> 
>
> **Pesquisou 4 sites**
>
> 
>
> **Revisou segurança, caminhos e validação de snapshots incrementais**
>
> 
>
> **Extraindo resumos executivos dos documentos**
>
>
> **Organizando o inventário**
>
> Estou estruturando um inventário auditável a partir dos relatórios, preservando recomendações distintas, referências de origem e agrupamentos por tema. Também estou priorizando uma saída prática, já que o volume pode ser grande.
>
> **Organizou o inventário**
>
> 
>
> **Extraindo recomendações dos relatórios PDF**
>
>
> **Lendo segunda metade restante**
>
>
> **Extraídos resumos e recomendações dos documentos PDF restantes**
>
> 
>
> **Refinando prioridades técnicas**
>
> Estou consolidando os achados em recomendações rastreáveis. Além dos riscos já identificados, estou destacando limitações de delta, verificação de resultados, mutações assíncronas, cache, acessibilidade, sanitização e controle de sessões.
>
> **Refinou prioridades técnicas**
>
> 
>
> **Pesquisou 1 site**
>
> 
>
> **Consolidando recomendações**
>
> Estou reunindo os achados em um inventário rastreável, distinguindo recomendações independentes, evidências, prioridades, lacunas de validação e um plano de execução gradual. Também estou separando segurança, confiabilidade, observabilidade e experiência de uso.
>
> **Preparando o relatório**
>
> Estou fechando um relatório auditável com inventário técnico, evidências, prioridades e lacunas de validação. Vou separar recomendações por categoria, registrar o grau de confiança e destacar os próximos testes mais importantes.
>
> **Consolidei recomendações e preparei o relatório**
>
> 
>
> **Simplifiquei regexes e documentei auditoria completa do navegador**
>
> 
>
> **Criando índice e relatório técnico dos achados**
>
>
> **Planejando auditoria profunda do Browser Workstation**
>
>
> **Verificando qualidade dos artefatos gerados**
>
>
> **Inspecionando arquivos e script presentes**
>
>
> **Verificando regex e cabeçalhos extraídos**
>
>
> **Corrigindo limites e extração executiva**
>
>
> **Gerando inventário PDF de comparações**
>
>
> **Revisando seções finais do relatório**
>
>
> **Concluí auditoria do Browser Workstation e gerei relatório técnico PDF**
>
> 
>
> Pensou por 19m 17s

# Auditoria técnica — Browser Nativo Hermes Workstation

Base da auditoria: PDF comparativo de 183 páginas, código-fonte GitHub e estado do repositório em 18/10/2026.

## 1\. Estado confirmado do repositório

A primeira verificação pelo conector GitHub confirmou\:

| Item | Estado |
|--------|--------|
| Repositório | `kevynlucasprofissional-stack/hermes-agent` |
| Branch padrão | `main` |
| HEAD da `main` | `f436e9496344d2c38e6611a88b42f0b7f18ce6df` |
| PR \#105 | Aberta, draft, não integrada |
| Natureza da PR \#105 | Documentação e planejamento D-049 |
| Implementação de runtime na PR \#105 | Nenhuma, conforme escopo declarado |

A [github.com](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/105?utm_source=chatgpt.com) registra explicitamente que ainda faltam qualificação de CI no commit exato e validação operacional BAV04. Portanto, seu plano B0–B3 não deve ser tratado como funcionalidade já implementada.

Essa distinção é importante: **a auditoria precisa separar a capacidade que existe no código, a capacidade acessível ao agente e a capacidade cuja execução real já foi demonstrada.**

## 2\. Descobertas críticas no confronto PDF × código

### O Browser já possui mais capacidades do que várias análises reconhecem

| Capacidade | Verificação no código | Classificação |
|--------|--------|--------|
| Batch de ações | `executeAuthorizedBatch`, até 20 etapas, integrado ao runtime | Implementado; validação operacional limitada |
| Snapshot diferencial | `diffSnapshot` e `applySnapshotDelta`, usados em `snapshotForEntry` | Implementado; economia ponta a ponta não comprovada |
| Cache de extração | `BoundedExtractCache`, TTL de 4 segundos, até 64 entradas | Implementado |
| Referências de elementos `@eN` | Mapeamento de elementos no DOM e resolução para coordenadas | Implementado, com limitações |
| Accessibility Tree | `Accessibility.getFullAXTree`, com fallback para DOM | Parcial; ativação depende de flag |
| Extração com schema | Normaliza resultados e filtra campos conforme `schema.properties` | Parcial; não equivale a validação completa |
| Readiness semântica | `BrowserReadinessContract`, `wait_for_condition` | Implementado, mas aplicação universal não demonstrada |
| Controle humano e isolamento | `BrowserTaskLifecycle`, leases e admissão de operações | Implementado; qualificação E2E ainda necessária |
| Traces e journal | `PortableTrace`, `ExecutionJournal` e telemetria nativa | Implementado parcialmente para diagnóstico comparativo |

Evidências: [github.com](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/f436e9496344d2c38e6611a88b42f0b7f18ce6df/apps/desktop/electron/workstation-browser-runtime.ts?utm_source=chatgpt.com), [github.com](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/f436e9496344d2c38e6611a88b42f0b7f18ce6df/apps/desktop/electron/workstation-browser-batch.ts?utm_source=chatgpt.com), [github.com](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/f436e9496344d2c38e6611a88b42f0b7f18ce6df/apps/desktop/electron/workstation-browser-snapshot-diff.ts?utm_source=chatgpt.com), [github.com](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/f436e9496344d2c38e6611a88b42f0b7f18ce6df/apps/desktop/electron/workstation-browser-extract-cache.ts?utm_source=chatgpt.com)\.

### Três questões técnicas merecem especial atenção

**1\. O delta existe, mas pode não gerar a economia esperada.** O runtime calcula `snapshot_delta`, porém continua retornando o campo `snapshot` completo. Isso significa que disponibilizar um diff não garante uma redução de tokens consumidos pela IA. É necessário testar uma projeção compacta que efetivamente substitua, quando seguro, a representação integral.

**2\. O batch executa ações, mas não comprova necessariamente o resultado no serviço externo.** A verificação atual utiliza sinais locais, como alteração do valor de um input, mudança de toggle ou deslocamento de scroll. O código deliberadamente trata cliques sem pós-condição observável como incertos. É uma proteção correta, mas limita o uso de batches longos em tarefas com efeitos externos.

**3\. Há um problema concreto de validação de caminhos no bridge.** Em `workstation/browser_bridge.py`, a função `_validate_safe_destination` usa comparação textual de prefixos, e `browser_save_json` não utiliza o caminho resolvido retornado pela validação. Isso permite identificar um defeito lógico de contenção; ainda seria necessário reproduzir a exploração no fluxo real para estabelecer sua gravidade operacional.

A correção desse último ponto exige esforço pequeno e merece precedência sobre novas funcionalidades.

## 3\. Inventário e priorização 80/20

O documento de 183 páginas contém **26 blocos comparativos**\. Organizei as propostas em **59 capacidades técnicas canônicas**, reunindo recomendações equivalentes e preservando suas referências.

A conclusão central é que **o Hermes precisa mais de integração, comprovação e refinamento de componentes existentes do que de novos subsistemas**\.

### Ranking das melhorias

| Prioridade | Melhoria | Benefício esperado | Esforço |
|--------|--------|--------|--------|
| P0 | Corrigir validação de caminhos no Browser Bridge | Segurança de arquivos | Baixo |
| P0 | Testar e corrigir escopo do controle humano no Modo Aprender | Evitar controle da aba errada | Baixo–médio |
| P0 | Qualificar CI e efeitos externos incertos | Confiabilidade demonstrável | Médio |
| P1 | Observações compactas `action_map` e `focus` | Menos contexto e seleção mais objetiva | Médio |
| P1 | Fazer o delta substituir efetivamente o snapshot completo quando seguro | Economia de tokens | Médio |
| P1 | Validar extrações contra schemas reais | Reduzir dados incorretos | Médio |
| P1 | Reaquisição semântica de elementos antes de executar ações | Resistência a mudanças no DOM | Médio–alto |
| P2 | Comparação causal de execuções e diagnóstico de divergências | Depuração e aprendizagem | Médio |

As prioridades são julgamentos de engenharia, não resultados de benchmarks. A estimativa de redução de tokens precisa ser medida em tarefas completas.

### O que eu não implementaria agora

Não recomendo recriar o executor batch, o mecanismo de snapshot diferencial, o cache de extração ou o journal. Também adiaria WebMCP nativo, roteamento adicional de modelos e um sistema próprio de armazenamento de traces.

Em particular, **self-healing não pode significar repetir automaticamente um clique cujo efeito seja incerto**\. O sistema deve recuperar seletores antes da mutação, mas exigir reconciliação quando houver possibilidade de o efeito já ter ocorrido.

## 4\. Sequência de implementação recomendada

**Sessão 1 — Segurança e baseline**

Corrigir contenção de caminhos, reproduzir o possível erro de lease no Modo Aprender, investigar a CI e estabelecer testes de controle e efeitos incertos.

---

**Sessão 2 — Observação econômica**

Adicionar views compactas opt-in, preservar os elementos `@eN` e aproveitar o delta existente sem retornar desnecessariamente o conteúdo completo.

---

**Sessão 3 — Extração objetiva**

Adicionar validação estrutural de schema e reforçar sanitização antes de armazenar dados, sem modificar o comportamento legado sem schema.

---

**Sessão 4 — Recuperação segura**

Reutilizar os resolvers existentes para reencontrar um alvo único antes da ação, testar alterações dinâmicas do DOM e impedir qualquer reenvio de mutações incertas.

Uma quinta sessão, dedicada à comparação forense de execuções, só se justifica após reunir falhas operacionais reais suficientes.

## 5\. Relatórios completos

**[Baixar auditoria técnica completa — PDF × GitHub](sandbox:/mnt/data/Auditoria_Hermes_Browser_PDF_vs_GitHub_2026-10-18.md)**

Relatório em Markdown com diagnóstico, matriz das 59 capacidades, evidências de código, análise crítica, ranking ponderado, roadmap, critérios de aceite, testes, riscos e respostas estratégicas.

---

**[Baixar inventário das 183 páginas](sandbox:/mnt/data/Inventario_fontes_PDF_Hermes_Browser_183p.md)**

Índice dos 26 relatórios externos, páginas correspondentes e recomendações executivas identificadas. As páginas de transição entre relatórios foram contabilizadas.

O relatório principal inclui referências ao código vinculadas ao commit auditado, para que outra IA possa verificar as conclusões sem repetir toda a investigação.

## 6\. Conclusão estratégica

A maior vantagem identificada no Hermes é a **estrutura de autoridade, rastreabilidade e proteção contra efeitos duplicados**\. Sua maior oportunidade é tornar a interação com páginas mais barata e robusta aproveitando essa estrutura.

Minha escolha para o próximo incremento é começar pelas correções P0 e, em seguida, entregar **observação compacta + delta efetivamente econômico + seleção de elementos verificável**\.

A PR \#105 já contém uma proposta de evolução compatível com parte desses objetivos. Recomendo aproveitá-la como base documental, revisando suas premissas, em vez de criar um roadmap concorrente.

**Limite da auditoria\:** foram examinados o PDF e os componentes relevantes disponíveis pelo GitHub, mas não executei o Electron, testes locais ou benchmarks. As 59 capacidades representam um inventário agrupado, não a transcrição de cada recomendação secundária. A investigação também não valida todas as licenças externas individualmente. Essas limitações estão registradas nos arquivos.

Nenhuma alteração foi realizada no repositório.

## Prompt:
18/10/2026, 23:53:16

Usa o desktop commander para fazer mais uma sessão de investigação, planejamento e verificação comparativa do pdf anexado anteriormente e suas hipóteses com o código real do hermes que estou construindo, mas agora use o [$remote-desktop-commander](app://asdk_app_6a057d268ebc81919918d37eec718425) para investigar direto o meu repositório local em C:\Github\hermes-agent

Anexei o plano que fez agora, quero que seja crítico com ele afim de verificar se essa realmente é a direção certa de maior impacto e maior qualidad pelo menor esforço (80/20)

[Attachment: Texto colado(20261019-025128).txt]

## Response:
18/10/2026, 23:53:17 · gpt-6-thinking

Vou refazer a avaliação a partir do repositório local, sem presumir que o plano anterior está correto. Primeiro verificarei o HEAD, as alterações não publicadas e os caminhos reais de execução; depois confrontarei as hipóteses do PDF com os pontos de integração, testes e possíveis gargalos. A conclusão será uma revisão crítica do ranking 80/20, inclusive descartando etapas que não justifiquem seu custo.

Farei a investigação em modo somente leitura, sem alterar arquivos, branches ou estado do Git.

A investigação já permite mudar a ordem das prioridades. A antiga primeira prioridade — corrigir o Browser Bridge — é uma correção de segurança válida, mas encontrei apenas testes e referências documentais chamando `browser_save_json`, não um uso comprovado no fluxo principal. Seu impacto operacional imediato foi superestimado.

Por outro lado, a passagem de `schema_valid` até os WorkItems e a exposição das views ao agente têm efeitos diretos na confiabilidade e no custo das tarefas. Vou fechar a avaliação distinguindo **bloqueadores de integração**, **melhorias de alto retorno** e **pesquisas que podem esperar**\.

> **Lendo instruções e arquivos anexados**
>
>
> **Leu instruções e arquivos anexados**
>
> 
>
> **Planejando a verificação**
>
> Estou priorizando a avaliação do impacto real das mudanças já presentes, separando commits de alterações não integradas. Vou conferir usos efetivos no código, diferenças relevantes e executar testes locais sem modificar arquivos rastreados.
>
> **Planejou a verificação**
>
> 
>
> **Mapeando bloqueios críticos**
>
> Estou verificando o roteamento e a integração entre arquivos. Já apareceu um possível bloqueio grave: uma importação depende de um arquivo não versionado, o que pode quebrar uma cópia limpa. Também vou confirmar o problema de lease e a validação do esquema.
>
> **Mapeou bloqueios críticos**
>
> 
>
> **Inspecionou dispositivos, auditorias e schemas de snapshots, investigando falhas de validação**
>
> 
>
> **Auditou roteamento do navegador e bloqueios de integração**
>
> 
>
> **Consolidando evidências**
>
> Estou priorizando bloqueios que impedem uma cópia limpa e falhas que contradizem o comportamento esperado. Depois, vou separar correções imediatas de melhorias posteriores, indicando limites da verificação executada.
>
> **Priorizando correções**
>
> Estou tratando a dependência não versionada e a validação silenciosamente permissiva como bloqueios principais. O roteamento também precisa distinguir adoção explícita de controle automático; só depois vale otimizar deltas, lotes e projeções.
>
> **Consolidou evidências e priorizou correções**
>
> 
>
> **Concluída validação de segurança, extrações, testes e integrações remotas**
>
> 
>
> **Verificando fontes e páginas do PDF**
>
>
> **Verificou fontes e páginas do PDF**
>
> 
>
> **Elaborou relatório auditável com ranking e evidências**
>
> 
>
> **Criando relatório de segunda auditoria adversarial**
>
>
> **Criou relatório da segunda auditoria adversarial**
>
> 
>
> Pensou por 14m 21s

# Segunda auditoria — Hermes Workstation Browser

Verificação direta no computador Windows, confrontando o PDF de 183 páginas, o plano anterior e o código local.

## 1\. Primeira descoberta: o plano anterior já está desatualizado

Consegui acessar `C:\Github\hermes-agent` pelo Desktop Commander. O repositório local está em um estado significativamente diferente daquele examinado pelo GitHub na auditoria anterior.

| Informação | Estado local encontrado |
|--------|--------|
| Branch | `feat/d049-browser-80-20-impl-20261018` |
| HEAD | `fd80408ab29c9cc701dacf1fbe4ceb7899c1a836` |
| Último commit | D-049 B1.2: sanitização de segredos e B1.3: validação de schema |
| Working tree | Contém alterações não commitadas e numerosos arquivos novos |

Também encontrei novos arquivos relacionados à observação compacta e a testes de segurança. Isso significa que **não seria correto simplesmente entregar os quatro prompts de implementação que sugeri anteriormente**\: parte das mudanças já avançou, e é necessário verificar sua integração antes de pedir mais código.

A árvore de trabalho contém alterações que podem pertencer a outras sessões ou agentes. Não vou modificá-las.

## 2\. Duas correções relevantes na avaliação anterior

### A correção de caminhos já está em andamento

A alteração não commitada em `workstation/browser_bridge.py` substitui a comparação textual insegura por `Path.is_relative_to()` e utiliza o caminho resolvido na gravação. Há também uma suíte nova, `test_browser_bridge_security.py`, cobrindo diretórios irmãos, symlinks e destinos legítimos.

Portanto, esse item não deve continuar no roadmap como uma implementação inteiramente nova. **A tarefa restante é validar os testes, revisar os limites de segurança e consolidar a alteração existente.**

Há uma ressalva técnica: utilizar o caminho resolvido elimina a divergência entre o caminho inicialmente validado e aquele utilizado para gravação, mas não elimina uma troca concorrente de symlink entre a validação e a abertura do arquivo. Esse risco precisa ser descrito corretamente, sem exigir uma arquitetura mais complexa antes de demonstrar que ela é necessária.

### As observações compactas também já estão implementadas parcialmente

Encontrei `workstation-browser-snapshot-views.ts`, com quatro projeções: `summary`, `action_map`, `focus` e `content`\.

A lógica já está conectada à operação `browser_snapshot` no runtime Electron, preservando internamente o snapshot canônico. Os novos testes, entretanto, ainda não comprovam uso efetivo pelo agente nem redução de tokens em tarefas completas.

Isso altera a recomendação de prioridade: **antes de criar outra camada de otimização, é preciso garantir que a IA consiga solicitar e receber essas projeções de forma econômica pelo contrato real de ferramentas.**

## 3\. Achado mais importante: duas otimizações ainda não fecham o ciclo com a IA

Encontrei um problema de integração que considero mais relevante para o ganho imediato do que adicionar novas técnicas de observação.

**A. As views compactas não aparecem no contrato atual de `browser_snapshot` exposto ao agente.** O runtime aceita `view`, `focus_ref`, `focus_neighbors` e `max_chars`, mas o schema em `tools/browser_tool.py` apresenta somente `full`\. Além disso, a projeção Python que elimina elementos duplicados foi construída para o formato de snapshot tradicional; não está demonstrado que ela reduza corretamente a resposta das novas views.

Consequência: o código pode gerar observações econômicas sem que o agente consiga escolhê-las normalmente ou receba todo o benefício da compactação.

**B. A validação de schema não é uma garantia ponta a ponta.** O Electron agora retorna `schema_valid`, mas mantém `success: true` mesmo para itens não conformes. No fluxo durável, `workstation/browser_projection.py` continua usando uma validação própria, baseada em `title`, e seu resumo não incorpora explicitamente o novo `schema_valid`\.

Isso abre a possibilidade de uma extração rejeitada pelo schema solicitado ser registrada e apresentada como válida por outra camada. É um problema de integração e semântica do resultado, não uma razão para criar um segundo validador.

Também confirmei que `BrowserReadinessContract` é acionado em preflights declarados do `TaskCompiler`, mas não funciona como gate universal do navegador. Torná-lo obrigatório em toda leitura, como propõem algumas análises do PDF, não seria necessariamente uma melhoria: poderia introduzir novas esperas e falsos bloqueios.

## 4\. Verificação com testes locais

Executei testes focados no computador, utilizando as dependências já instaladas, sem instalar pacotes nem editar o código.

| Verificação | Resultado |
|--------|--------|
| Segurança de caminhos — Python | 7 passaram, 1 pulado |
| Views compactas — Vitest | 11 passaram |
| Validação de schema — Vitest | 9 passaram |
| Escopo de Learning B0.2 — Vitest | 1 passou, 36 testes não selecionados |

**O defeito B0.2 também já recebeu uma correção no runtime local.** `startLearning` agora rejeita uma aba sem `ownerTaskId` antes de tentar assumir controle. O teste focado passou. Isso não equivale a um teste com toda a interface Electron e usuário real, mas comprova o comportamento exercitado pelo contrato de teste.

Encontrei ainda um bloqueador de integração objetivo: o commit atual importa `workstation-browser-snapshot-views.ts`, mas esse arquivo existe somente como não rastreado no Git. Confirmei consultando o conteúdo do próprio HEAD, não apenas o diretório local.

**Consequência\:** um checkout limpo desse commit não contém um módulo necessário ao runtime. Consolidar esse arquivo e suas provas deve vir antes de desenvolver outra funcionalidade.

## 5\. Novo ranking 80/20

Minha recomendação mudou após a investigação local. A prioridade agora deve ser **concluir e integrar corretamente o que já foi desenvolvido**, antes de ampliar a arquitetura.

| Ordem | Trabalho recomendado | Esforço residual | Decisão |
|--------|--------|--------|--------|
| 1 | Consolidar arquivos e garantir build a partir de checkout limpo | Baixo | Fazer agora |
| 2 | Propagar corretamente a validação de schema até os resultados duráveis | Baixo–médio | Fazer agora |
| 3 | Expor views compactas no contrato de ferramentas da IA e eliminar redundância | Baixo–médio | Fazer agora |
| 4 | Otimizar snapshot delta mediante benchmark real | Médio | Medir primeiro |
| 5 | Recuperação semântica de elementos antes de ações | Médio–alto | Fazer se DOM drift for frequente |
| 6 | Comparação forense, WebMCP e mecanismos mais avançados | Variável | Adiar |

O pacote de maior retorno provável é **integridade dos resultados + observações realmente econômicas + integração completa com o agente**\.

Isso é diferente de implementar simplesmente mais recursos. O código existente precisa produzir benefícios verificáveis no percurso inteiro\:

**Agente / TaskRun**

**Schema da ferramenta**

**Controller Electron / Chromium**

**Observação ou ação autorizada**

**Validação e resultado durável**

**Resposta compacta e confiável à IA**

Cadeia proposta sem duplicar responsabilidades existentes.

## 6\. Plano de execução corrigido

Recomendo **três sessões de implementação**, com uma quarta apenas se os benchmarks ou os logs justificarem\:

1. **Fechamento da implementação atual\:** consolidar módulos não rastreados, revisar os patches de segurança e Learning e garantir checkout reproduzível.
2. **Integridade das extrações\:** corrigir a passagem do resultado de schema para WorkItems e resumos, com testes negativos e prevenção de falsos sucessos.
3. **Economia efetiva de contexto\:** permitir que o agente solicite `action_map` e `focus`, corrigir a duplicação de campos e medir tokens e tempo até conclusão.

A sessão condicional seria dedicada à reaquisição semântica de alvos em páginas dinâmicas, mantendo proteção contra ações duplicadas.

## 7\. Relatório completo da segunda investigação

**[Baixar segunda auditoria local e roadmap revisado](sandbox:/mnt/data/Hermes_Browser_Segunda_Auditoria_Local_80_20_2026-10-19.md)**

Documento técnico com evidências e caminhos locais, matriz comparativa do PDF, classificação das hipóteses, resultados dos testes, critérios de aceite, ordem de implementação e instruções para a próxima IA.

**Conclusão\:** mantenho a arquitetura central proposta anteriormente, mas **rejeito a antiga ordem de implementação como a mais econômica para o estado atual do código**\. Ela desperdiçaria esforço repetindo trabalho parcialmente concluído. O melhor próximo passo é resolver os pontos em que capacidades existentes ainda não se traduzem em resultados corretos, acessíveis e baratos para a IA.

A auditoria não executou um fluxo E2E autenticado com comprovação de efeito externo. Portanto, ainda não há fundamento para afirmar uma porcentagem real de ganho de desempenho ou aumento da taxa de conclusão. Nenhum arquivo ou branch do repositório local foi alterado deliberadamente nesta investigação.

## Prompt:
19/10/2026, 00:53:18

De acordo com os anexos, faça o seguinte na branch feat/d049-browser-80-20-impl-20261018 , coloque instruções no primeiro prompt para sincronizar com a branch remota para as instruções que você vai fazer no repositório remoto usando o [$github](app://connector_76869538009648d5b282a4bb21c3d157) sejam acessíveis nas minhas pastas locais, no meu computador, e também me entregue me entregue um passo a passo, uma série de prompts que é o ponto ótimo entre economia de tokens e profundidade de qualidade de implementação, fazendo com que um prompt possa focar em um grupo de problemas simples que fazem sentido serem resolvidos juntos ou focar em um único problema complexo que requer atenção máxima da IA implementadora.

Atualize no repositório o roadmap.md, o jornal de engenharia, o hermes work inteligence e qualquer outro documento necessário com essas visões, descobertas e decisões que fizemos aqui.\
&#x20;Agora cria um prompt para eu mandar para a IA que vai realizar essas implementações/ajustes e ela realizar esses pontos de melhoria que identificamos. Me vê um prompt para eu mandar e a IA resolver tudo isso. Cria um prompt que permita que a IA não precise pensar muito nem ficar lendo nada, que ele saiba de imediato o que ele tem que fazer, quando tem fazer, em que ordem e em que local. Para isso, leia todo o necessário direto no @GitHub\
&#x20;De preferência, já crie o código que será utilizado nas implementações e correções, e já diga onde esse código será colocado ou qual parte do código esse novo código substitui, faça para que seja o máximo "plug and play" possível para que a IA implementadora pegue o seu código e já coloque nos lugares certos sendo necessário o minimo de adaptações ou ajustes para melhorar a integração.
Mas o prompt deve dar liberdade para a IA implementadora avaliar o código sugerido e melhorar ele ou adaptar conforme a necessidade, pedindo para a IA implementadora uma posição crítica e analítica para com sua sugestões (não tardando em aceitar caso a sua sugestão realmente for a melhor, mas não hesitando em adaptar ou ajustar caso ela encontre uma opção ainda melhor), e também uma posição de implementadora, ou seja, de realmente trabalhar as mudanças no código fonte do Hermes Work / Agent afim de evoluir na direção proposta.

[Attachment: Segunda auditoria adversarial — Browser nativo Hermes Workstation.pdf]

[Attachment: 18.10.26 Comparativo Browser - CHATGPT 2.pdf]

[Attachment: 18.10.26 Comparativo Browser - CHATGPT 1.pdf]

[Attachment: 18.10.26 Análises comparativas do Browser por Fable 5.1(2).pdf]

## Response:
19/10/2026, 00:53:20 · gpt-6-thinking

Vou comparar os quatro anexos com o estado mais recente da branch no GitHub e transformar o resultado em um roteiro executável, dividido por complexidade e dependências. Também vou atualizar a documentação canônica na branch solicitada, sem alterar a `main` nem sobrescrever trabalho local.

O primeiro prompt terá um procedimento de sincronização seguro: como a auditoria anterior encontrou arquivos não commitados e não rastreados no computador, ele não poderá começar com `git pull` indiscriminado.

A documentação remota será um único commit na branch, com um guia novo contendo os prompts completos e atualizações curtas no roadmap, jornal, inteligência, decisões e estado. Estou mantendo o histórico antigo como registro, mas marcando explicitamente as prioridades superadas, para que a próxima IA não execute o plano D-049 antigo por engano.

O procedimento de sincronização do Prompt 1 será condicionado à ausência de conflitos com os arquivos locais. Assim, as instruções publicadas no GitHub poderão chegar ao computador sem apagar as modificações que outras sessões deixaram na working tree.

> **Lendo instruções PDF e inspecionando arquivos**
>
>
> **Lidas instruções do PDF e inspecionados arquivos**
>
> 
>
> **Avaliados PDFs com metadados e texto extraído**
>
> 
>
> **Comparando PDFs e extraindo pontos decisivos**
>
>
> **Comparou PDFs e preparou documentação de auditoria adversarial**
>
> 
>
> **Ajustando validação**
>
> Estou garantindo que a rota diferencie claramente o modo nativo do fallback: parâmetros não suportados precisam gerar erro explícito. Também estou separando conformidade do esquema de validações semânticas, preservando resultados parciais e evitando marcar itens como concluídos quando houver falhas.
>
> **Ajustou validação**
>
> 
>
> **Planejando documentação**
>
> Estou preparando documentos autocontidos: um guia de execução, um arquivo separado com trechos de implementação e prompts prontos para copiar. Também vou preservar atualizações concorrentes usando commits atômicos e validação do estado atual antes de publicar.
>
> **Organizando a execução**
>
> Estou estruturando o material em documentos práticos, com instruções autocontidas, trechos de implementação, critérios de aceite e três prompts reutilizáveis. Também estou mantendo a publicação segura diante de alterações concorrentes e evitando misturar arquivos de outras tarefas.
>
> **Planejou a documentação e organizou a execução**
>
> 
>
> **Atualizada documentação e revisada implementação remota do navegador**
>
> 
>
> **Reavaliou branch, atualizou documentação e verificou commit remoto seguro**
>
> 
>
> Pensou por 10m 25s

## Direção de implementação consolidada

A comparação dos anexos com a branch remota confirma que o caminho de melhor retorno é **terminar a integração de três capacidades existentes**, e não recriar o Browser.

A branch `feat/d049-browser-80-20-impl-20261018` existe no GitHub e, na verificação inicial, estava no commit `fd80408ab29c9cc701dacf1fbe4ceb7899c1a836`\. O trabalho anterior deixou o runtime Electron com views compactas e validação parcial de schema, mas ainda há lacunas entre a ferramenta exposta à IA, o controller e o resultado durável.

Vou organizar a execução em **três prompts principais e um quarto condicional**\:

| Prompt | Escopo | Resultado exigido |
|--------|--------|--------|
| 1 | Sincronização segura, recuperação dos arquivos não rastreados, build e correções B0 | Checkout reproduzível |
| 2 | Validação de extração até ArtifactStore e WorkItems | Nenhum falso sucesso de schema |
| 3 | Views compactas acessíveis ao agente, projeção sem duplicação e benchmark | Economia efetiva demonstrada |
| 4, condicional | Recuperação semântica pré-dispatch | Menos falhas por DOM drift, sem duplicar efeitos |

Duas regras são especialmente importantes: **um ACK de clique não prova persistência no servidor**, e **um resultado `success: true` de captura não prova conformidade com o schema solicitado**\. A implementação deve preservar essas distinções.

# D-049 - Roadmap atualizado e prompts de implementação

**Atualização realizada no GitHub**

As instruções e decisões foram publicadas na branch solicitada, sem alterar a `main`\.

COMMIT DOCUMENTAL CONFIRMADO

`ab40cbbb33b65fe9b844565c3924ba2f0c9ba734`

8 arquivos publicados · 1 guia novo · 7 documentos atualizados

---

[Abrir guia completo de execução D-049](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/ab40cbbb33b65fe9b844565c3924ba2f0c9ba734/workstation/context/D049_BROWSER_EXECUTION_80_20_2026-10-19.md)

[Inspecionar as alterações do commit](https://github.com/kevynlucasprofissional-stack/hermes-agent/commit/ab40cbbb33b65fe9b844565c3924ba2f0c9ba734?utm_source=chatgpt.com)

Foram atualizados `workstation/ROADMAP.md`, `engineering-journal/CURRENT.md`, `HERMES_WORKSTATION_INTELLIGENCE.md`, `DECISIONS.md`, `CURRENT_STATE.md`, `KNOWN_ISSUES.md` e `BROWSER_REFINEMENT_2026-10-18.md`\. Também foi criado `D049_BROWSER_EXECUTION_80_20_2026-10-19.md` com os quatro prompts, trechos de código candidatos, arquivos de destino e critérios de aceite.

O commit foi verificado no GitHub. **Ele é exclusivamente documental**\: não afirma que as implementações estejam concluídas.

## Como executar

Branch única: `feat/d049-browser-80-20-impl-20261018`

Diretório local: `C:\Github\hermes-agent`

Envie os prompts sequencialmente à IA implementadora. O primeiro começa sincronizando as instruções remotas com o repositório local, antes de editar qualquer código.

## Prompt 1 - Sincronização e fechamento G0

Complexidade baixa-média. Agrupa sincronização, recuperação das views, segurança do Bridge, Learning e build reproduzível.

**document: **

# EXECUTAR D-049 / SESSÃO 1 - Sincronização e fechamento G0

Trabalhe como engenheiro implementador do Hermes Workstation. Sua responsabilidade é modificar código, testar e entregar resultados, não apenas planejar.

**Repositório:** `C:\Github\hermes-agent`  
**Branch obrigatória:** `feat/d049-browser-80-20-impl-20261018`  
**Commit documental a sincronizar:** `ab40cbbb33b65fe9b844565c3924ba2f0c9ba734`

## 1. Sincronize antes de qualquer modificação

Execute:

```powershell
Set-Location 'C:\Github\hermes-agent'
git branch --show-current
git rev-parse HEAD
git status --porcelain=v1 -uall
git worktree list --porcelain

git fetch origin feat/d049-browser-80-20-impl-20261018

git log --oneline --left-right HEAD...origin/feat/d049-browser-80-20-impl-20261018
git diff --name-only HEAD..origin/feat/d049-browser-80-20-impl-20261018
```

Confirme que está na branch correta, que o remoto é descendente da versão local e que a atualização não sobrescreverá arquivos modificados ou não rastreados.

Se essas condições forem satisfeitas, execute:

```powershell
git merge --ff-only origin/feat/d049-browser-80-20-impl-20261018
git rev-parse HEAD
```

**Não execute** reset --hard, clean, stash automático, rebase forçado ou merge que sobrescreva trabalho de outras IAs. Em caso de divergência ou colisão, interrompa e apresente um diagnóstico preciso.

Confirme que o guia abaixo apareceu no repositório local:

`workstation/context/D049_BROWSER_EXECUTION_80_20_2026-10-19.md`

## 2. Feche os problemas G0

Trabalhe exclusivamente nos arquivos relevantes:

- `apps/desktop/electron/workstation-browser-runtime.ts`
- `apps/desktop/electron/workstation-browser-snapshot-views.ts`
- `apps/desktop/electron/workstation-browser-snapshot-views.test.ts`
- `apps/desktop/electron/workstation-browser-runtime-task.test.ts`
- `workstation/browser_bridge.py`
- `workstation/tests/test_browser_bridge_security.py`

A auditoria confirmou que o runtime importa `workstation-browser-snapshot-views.ts`, mas esse arquivo ainda não estava rastreado no Git. Aproveite a implementação local existente, valide-a e inclua o módulo e seus testes no commit de implementação.

Revise os patches de segurança do Browser Bridge e de ownership do Modo Aprender. Se já estiverem corretos, não reimplemente; consolide-os. O Learning nunca deve assumir controle de outra aba por fallback implícito.

## 3. Verifique

Execute os testes Python e Vitest focados, typecheck/build do Desktop, `git diff --check` e uma verificação isolada de checkout limpo.

Critérios obrigatórios:

- O commit pode ser compilado a partir de checkout limpo.
- Nenhum arquivo de terceiros é sobrescrito.
- As views e os testes estão rastreados.
- O controle humano mantém o owner correto.
- Os testes existentes continuam passando.

Comite exclusivamente o escopo autorizado e faça push fast-forward após conferir novamente o remoto.

Ao terminar, informe o HEAD inicial/final, arquivos alterados, testes PASS/FAIL/SKIP e pendências. **Não inicie a próxima sessão se G0 estiver bloqueado.**

Você tem liberdade para adaptar minhas sugestões quando encontrar uma solução tecnicamente melhor, desde que preserve os contratos e comprove a melhoria.

## Prompt 2 - Integridade da extração estruturada

Complexidade média-alta. Uma única responsabilidade: impedir que dados rejeitados pelo schema sejam declarados válidos no resultado durável.

**document: **

# EXECUTAR D-049 / SESSÃO 2 - Schema verdadeiro de ponta a ponta

Implemente uma correção completa e testada no pipeline de extração do Hermes Workstation, na branch `feat/d049-browser-80-20-impl-20261018`.

Confirme HEAD e working tree. Leia somente os componentes necessários:

- `apps/desktop/electron/workstation-browser-extract-cache.ts`
- `apps/desktop/electron/workstation-browser-runtime.ts`, função de extração
- `workstation/browser_projection.py`
- `workstation/integrations/hermes/browser_controller.py`
- `workstation/tests/test_browser_extract_items.py`
- `workstation/tests/test_browser_controller_domain_processing.py`
- `workstation-browser-extract-schema.test.ts`

## Problema 1: schema inválido com array vazio

`validateExtractedItems` atualmente verifica keywords não suportadas durante a iteração dos itens.

Um array vazio pode, portanto, passar pela função sem que keywords incompatíveis sejam detectadas.

Implemente validação de admissibilidade do schema independentemente de haver itens.

Utilize TDD: teste RED → correção → GREEN.

## Problema 2: falso sucesso durável

O Electron retorna `schema_valid`, mas `workstation/browser_projection.py` utiliza uma validação genérica baseada em `title` para preencher `valid_count` e finalizar WorkItems.

Corrija a propagação do veredito entre:

**Electron → Controller → ArtifactStore/WorkPlan → WorkItems → Resumo entregue ao agente.**

Diferencie explicitamente:

- Sucesso da captura.
- Conformidade com o schema solicitado.
- Validação semântica adicional.
- Persistência do resultado.

Contrato obrigatório:

Se o usuário solicitou schema e `schema_valid=false`, nenhum WorkItem poderá ser considerado conforme a esse schema. Se o owner omitir o veredito, o estado é desconhecido, não aprovado.

Se existir apenas um veredito agregado do lote, não invente validade individual dos itens. Preserve dados capturados para investigação, mas nunca transforme resultado inválido em sucesso verificado.

### Trecho orientador

```python
schema_requested = isinstance(args.get("schema"), dict)
owner_verdict = data.get("schema_valid")

if not schema_requested:
    schema_status = "not_requested"
elif owner_verdict is True:
    schema_status = "valid"
elif owner_verdict is False:
    schema_status = "invalid"
else:
    schema_status = "unknown"
```

Adapte aos contratos reais. Não aplique o trecho literalmente se ele introduzir inconsistências.

## Testes obrigatórios

Cubra array vazio com schema incompatível, required/type/enum, `schema_valid=false` com title presente, veredito ausente, schema válido sem title obrigatório, erros sanitizados, falha de persistência e compatibilidade com extrações sem schema.

Execute os testes focados e regressões. Preserve TaskRun, ArtifactStore e autoridade existentes. Não crie outro banco ou validador independente.

Entregue código implementado, provas RED/GREEN, commit e push na mesma branch. Registre claramente quais contratos foram testados e quais dependem de E2E externo.

## Prompt 3 - Economia de tokens e observações acessíveis

Complexidade média-alta. Foco exclusivo no caminho entre a ferramenta da IA, o runtime, a projeção e o custo realmente observado.

**document: **

# EXECUTAR D-049 / SESSÃO 3 - Observação econômica model-facing

Implemente a exposição das views compactas do Browser Electron ao agente Hermes, com compatibilidade legada, segurança e benchmark.

Branch: `feat/d049-browser-80-20-impl-20261018`.

Confirme HEAD/status e examine:

- `tools/browser_tool.py`: BROWSER_TOOL_SCHEMAS, browser_snapshot, _BROWSER_TOOL_TABLE, _routed_handler
- `tools/browser_workstation.py`: _dispatch e project_model_browser_payload
- `apps/desktop/electron/workstation-browser-runtime.ts`: snapshotForEntry
- `apps/desktop/electron/workstation-browser-snapshot-views.ts`
- Testes de registry, projeção, snapshot e telemetria.

## Implementação

**1. Exponha as views no schema real de browser_snapshot.**

Adicione os parâmetros `view`, `focus_ref`, `focus_neighbors` e `max_chars`, respeitando limites e validação de tipos.

Código candidato para o objeto `properties` existente:

```python
"view": {
    "type": "string",
    "enum": ["summary", "action_map", "focus", "content"]
},
"focus_ref": {
    "type": "string",
    "description": "Current @eN ref of the same tab"
},
"focus_neighbors": {
    "type": "integer", "minimum": 0, "maximum": 10
},
"max_chars": {
    "type": "integer", "minimum": 200, "maximum": 12000
}
```

Não basta adicionar campos ao schema: faça-os percorrer o roteamento autorizado até o Electron. Backends sem suporte não podem ignorar silenciosamente uma view solicitada.

**2. Reduza o payload entregue à IA.**

O runtime já suporta views, mas ainda pode devolver a lista completa `elements`, duplicando informações do snapshot.

Corrija a projeção para evitar redundância, preservando referências `@eN`, identidade, estado de truncamento e metadados necessários.

Preserve o resultado legado quando nenhuma view for solicitada.

**3. Avalie o snapshot delta existente.**

Não recrie o mecanismo. Verifique se é possível evitar a combinação redundante de snapshot integral e delta no contexto do modelo, somente quando o baseline for confiável e pertencer à mesma tarefa, aba e documento.

Na dúvida, use fallback seguro.

**4. Execute benchmark.**

Compare cenários equivalentes, com pelo menos dez ciclos por cenário viável. Inclua navegação simples, SPA, formulário, extração e controle humano.

Meça, quando disponível:

- Bytes efetivamente entregues ao modelo.
- Tokens de entrada/saída.
- Chamadas de ferramentas e do modelo.
- Latência até conclusão verificada.
- p50/p95.
- Taxa de conclusão e efeitos incertos.

Não use as estimativas do PDF como resultados do Hermes.

## Aceite

O agente consegue solicitar `action_map` e `focus` pela ferramenta registrada, o browser mantém referências válidas e isolamento, e a economia é medida no retorno real ao modelo.

Implemente, teste RED/GREEN, atualize o jornal com resultados, comite e faça push fast-forward. Se não houver ganho mensurável ou houver regressão, mantenha a otimização opt-in e registre o resultado.

Sua responsabilidade é tanto implementar quanto contestar ou melhorar minhas sugestões quando houver evidência técnica.

## Prompt 4 - Somente se necessário

Reservado para quando as métricas da sessão 3 comprovarem falhas relevantes por DOM drift.

**document: **

# EXECUTAR D-049 / SESSÃO 4 CONDICIONAL - Recuperação semântica

Antes de implementar, verifique se os resultados da Sessão 3 demonstram que STALE_REF ou DOM_DRIFT é causa relevante de tarefas fracassadas. Se não houver evidência, NÃO implemente; registre HOLD.

Se houver evidência, trabalhe na branch `feat/d049-browser-80-20-impl-20261018` e reutilize `resolvePoint`, `clickRef`, `typeRef`, semantic anchors, documentEpoch, mutationRevision e os contratos de lease existentes.

Implemente reaquisição somente ANTES de qualquer evento CDP com efeito, usando atributos semânticos existentes como testid, role, name e aria-label.

Exija correspondência única na mesma task, aba, origem e revisão compatível. Alvos ambíguos devem provocar abstenção ou handoff.

Nunca repita automaticamente uma mutação depois de mousePressed, timeout com efeito potencial ou qualquer resultado UNCERTAIN.

Valide com testes de SPA re-renderizada, referências ambíguas, troca de aba, takeover humano, timeout antes/depois do input e contador de efeitos externos garantindo ausência de duplicações.

Entregue código, testes, métricas de melhoria e registro da decisão. Não crie um novo Stagehand, browser controller ou mecanismo de lease.

---

## Recomendação de execução

O ponto ótimo é **três sessões obrigatórias**, não uma única sessão gigante. Cada uma encerra um contrato verificável, reduzindo o risco de a IA trabalhar em muitas frentes e declarar conclusões sem provas.

A primeira deve ser executada antes das demais porque resolve um problema de integridade do checkout. A segunda protege a veracidade dos resultados. A terceira busca economia real de contexto. A quarta só será necessária se a medição justificar o investimento.

Os prompts completos e o roteiro também estão [persistidos na branch remota](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/ab40cbbb33b65fe9b844565c3924ba2f0c9ba734/workstation/context/D049_BROWSER_EXECUTION_80_20_2026-10-19.md), permitindo continuar a implementação diretamente pelo repositório local após a sincronização.

**Próxima ação\:** enviar o Prompt 1 à IA implementadora. Não é necessário recriar a branch ou repetir a auditoria anterior.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)