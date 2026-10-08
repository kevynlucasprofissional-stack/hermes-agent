# Hermes Creative Workstation — análise e arquitetura recomendada

> **Fonte histórica:** texto longo fornecido pelo usuário na conversa em 2026-10-08, anterior à proposta documental. Este registro reproduz o **corpo textual completo** da análise (títulos, tabelas, afirmações, exemplos e ressalvas), com escapes Markdown normalizados para legibilidade. Elementos de interface da conversa como favicons, chips de fonte, o marcador “+1” e placeholders de imagem não são reproduzidos porque não integram o conteúdo argumentativo. O texto é **fonte de discussão, não constatação de estado atual**; a compatibilidade e as licenças exigem confirmação no ref atual.

A conclusão principal é que o Hermes Work não deveria tentar substituir Photoshop, After Effects, Blender ou Cinema 4D individualmente. Deveria se transformar em uma estação criativa na qual o agente consegue criar, modificar, visualizar e reutilizar projetos em diferentes engines especializadas.

Essa direção aparece repetidamente nos arquivos, especialmente nas discussões sobre Penpot, Remotion, Three.js Editor, Graphite e Blender.

Minha recomendação inicial é construir o sistema em torno de três capacidades principais:

1. Penpot — design visual estruturado

Editor visual no navegador, com MCP oficial e possibilidade de self-hosting. É a melhor opção para um ambiente em que humano e agente editam o mesmo design.

2. Remotion — motion graphics e vídeo

Permite que o Hermes produza animações por código, visualize o resultado no navegador e renderize vídeos. Já existem skills oficiais voltadas a agentes.

Referência citada: `remotion-dev/skills: Agent Skills · GitHub`.

3. Three.js Editor — 3D interativo

É o melhor ponto de partida para criar um estúdio 3D incorporado ao Chromium do Hermes, com uma ponte própria de comandos para agentes.

Essas três ferramentas formariam o núcleo visível do Creative Workstation. Blender, Inkscape, FFmpeg e outras ferramentas entrariam como motores especializados, sem precisar necessariamente ter uma interface própria dentro do Chromium.

Os anexos também trazem uma ideia particularmente importante: criar capacidades criativas instaláveis, em vez de apenas registrar softwares isolados. Essa proposta é mais valiosa do que simplesmente adicionar novos MCPs, porque se conecta ao conceito de reutilização operacional que você está desenvolvendo no Hermes.

## 1. Ranking das tecnologias para integrar ao Hermes

Esta classificação considera principalmente o potencial de automação, a integração com o Chromium, a capacidade de edição humana, o reaproveitamento operacional e o esforço de implementação.

| Tecnologia | Prioridade | Integração recomendada | Decisão |
|---|---|---|---|
| Penpot | P0 | MCP oficial + interface web | Integrar |
| Remotion | P0 | Skills + React/CLI + Studio | Integrar |
| Three.js Editor | P0 | Código + bridge própria + Chromium | Integrar |
| FFmpeg | P0 | CLI + operações tipadas | Integrar como engine |
| Inkscape | P1 | SVG + CLI; MCP opcional | Integrar |
| Blender | P1 | Python/headless + MCP | Integrar |
| Graphite | P2 | Editor web + pesquisa de API de grafos | Laboratório |
| GIMP | P2 | Python/PDB + MCP | Opcional |
| Krita | P2 | API Python + MCP | Opcional |
| Tone.js / Strudel | P2 | JavaScript + navegador | Integrar áudio |
| PartMode / replicad | P3 | MCP / API TypeScript | Módulo CAD opcional |
| Godot | P3 | MCP + CLI/editor | Games e simulações |
| PixiJS / p5.js | P3 | Código + navegador | Creative coding |
| Scribus | P3 | Scripts + geração editorial | Publicação |
| Blockbench / SculptGL | Baixa | Plugin/web | Não priorizar |

Prioridades propostas para o Hermes, não classificações oficiais. P0 = primeira implementação; P1 = extensão de produção; P2 = próxima expansão; P3 = sob demanda.

O ranking é um refinamento das propostas dos anexos. Nele, a conclusão mais relevante é que nem toda ferramenta precisa virar um aplicativo instalado dentro do Hermes. Algumas precisam apenas oferecer operações confiáveis sobre arquivos e gerar artefatos.

## 2. Quais já possuem MCP?

A pesquisa encontrou integrações reais, mas com níveis diferentes de maturidade.

| Ferramenta | Situação do MCP | Implementação encontrada |
|---|---|---|
| Penpot | Oficial | Penpot MCP |
| PartMode | Nativo | PartMode Agent MCP |
| Blender | Comunitário consolidado | MCP for Blender |
| Inkscape | Comunitário | inkscape-mcp |
| GIMP 3 | Comunitário | GIMP Studio MCP |
| Krita | Comunitário | Krita MCP |
| Remotion | Comunitário; não é necessário para o fluxo principal | Remotion MCP Server |
| Godot | Várias implementações comunitárias | Godot MCP |
| Three.js Editor | Sem MCP oficial confirmado | Recomendo bridge própria |
| Graphite | Sem MCP oficial confirmado | Pesquisar API/estrutura de grafos |
| replicad / JSCAD | MCP desnecessário no primeiro momento | APIs JavaScript diretas |
| Tone.js / Strudel | Sem MCP oficial confirmado | APIs JavaScript diretas |

As implementações acima estão publicamente documentadas, mas isso não significa que estejam auditadas ou sejam compatíveis com a sua instalação do Hermes sem ajustes. Particularmente, os MCPs comunitários de GIMP, Krita e Remotion precisam de testes antes de entrar numa distribuição estável.

### Uma descoberta adicional: PartMode

O PartMode merece atenção pelo modo como conecta humanos e agentes ao mesmo documento CAD.

Ele possui operações tipadas, inspeção, pré-visualizações e commits protegidos por revisão. Não depende simplesmente de um agente executando código arbitrário dentro da interface.

Seu MCP documentado é hospedado, com autenticação própria; executar a interface CAD localmente não garante automaticamente uma instância MCP local equivalente. É uma arquitetura que o Hermes deveria estudar mesmo que você nunca venha a utilizar CAD no cotidiano.

### E o n8n?

O n8n também entrou nas discussões, embora não seja open source sob uma licença OSI convencional.

Existe um dado útil: a documentação atual do Hermes Agent já descreve a integração com o MCP oficial do n8n, utilizando a entrada `n8n-official` do catálogo.

Integração documentada:

```
hermes mcp install n8n-official
```

Isso significa que não precisamos introduzir o próprio n8n como subsistema do Creative Workstation. Ele pode permanecer um serviço externo para automações comerciais, webhooks, publicações e integrações.

## 3. Quais já têm skills instaláveis?

Esta foi uma das descobertas mais úteis: algumas ferramentas possuem skills de qualidade suficiente para acelerar a implementação sem desenvolver toda a camada de conhecimento do zero.

### Remotion — skills oficiais

`remotion-dev/skills`

Possui `remotion-best-practices`, `remotion-create`, `remotion-markup`, `remotion-studio`, `remotion-render`, `remotion-captions` e outras.

É o pacote que eu instalaria primeiro.

### Penpot — AI Kit com skills e workflows

`penpot/penpot-ai-kit`

O kit inclui skills para design systems, componentes, telas, auditoria de acessibilidade, tokens e design-to-code.

Também oferece políticas de aprovação, avaliações e workflows. Isso interessa diretamente à arquitetura do Hermes.

### Three.js — skills comunitárias

`noklip-io/agent-skills`

Referências para cenas, materiais, shaders, animação, loaders, WebGPU e React Three Fiber. É uma boa base para a futura bridge do Hermes.

### Blender — skills comunitárias especializadas

Blender Python API Skill.

Orienta automação com `bpy`, modelagem, materiais, render e tratamento de problemas de contexto. É especialmente útil para operações headless.

### Strudel — skill comunitária

`eXodes/skills-workspace`

Skill para padrões musicais, síntese, samples e efeitos no Strudel. Útil para adicionar geração sonora ao Creative Workstation sem instalar uma DAW completa.

### Como essas skills entram no Hermes

A documentação do Hermes Agent confirma a compatibilidade com o padrão `SKILL.md`, instalação pelo Skills Hub e diretórios externos. Portanto, essas skills não precisam ser reescritas integralmente para o Hermes.

Por exemplo, para uma skill comunitária de Three.js:

```
hermes skills install noklip-io/agent-skills/skills/three-js
```

Para pesquisar o que já está no catálogo do Hermes:

```
hermes skills search remotion
hermes skills search penpot
hermes skills search blender
hermes skills search three
```

Para o Penpot AI Kit, eu preservaria a estrutura completa do repositório, porque as skills compartilham arquivos de referências, políticas e workflows. Copiar isoladamente um `SKILL.md` poderia quebrar essas dependências.

Distinção fundamental: uma skill ensina o agente a trabalhar; um MCP oferece ferramentas executáveis; uma capacidade operacional certificada permite ao Hermes repetir um procedimento com contratos, verificações e limites definidos. Nenhuma dessas três camadas substitui automaticamente as demais.

## 4. Arquitetura ideal: Hermes Creative Runtime

Esta seria minha arquitetura de referência, aproveitando a concepção do Chromium interno, do TaskCompiler e do Experience Compiler discutida nos arquivos.

```text
HERMES WORK
Agente · planejamento · intenção · contexto
          |
Creative Capability Router
Escolhe a engine, a operação e o fluxo de execução
          |
          +-- Penpot -- MCP + Web
          +-- Remotion -- React + CLI
          +-- Three.js -- Bridge + Web
          |
Creative Engines
Blender · Inkscape · GIMP · FFmpeg · Tone.js
Operações especializadas e renderização
          |
Chromium
Preview e edição humana
          |
Experience Compiler
Captura, validação e reutilização
          |
Artefatos finais e projetos editáveis
SVG · TSX · JSON · GLB · BLEND · PNG · MP4
```

Diagrama conceitual proposto, não uma representação de componentes já implementados e verificados na branch atual.

### Uma decisão importante: o projeto, não a imagem, é a fonte da verdade

Pense no Hermes criando um convite para um evento.

Em vez de simplesmente salvar um PNG, ele salva uma representação estruturada contendo texto, componentes, cores, posições, assets, movimentos e parâmetros.

Assim, o mesmo projeto pode produzir:

| Saída | Mecanismo |
|---|---|
| Post estático 1080 × 1350 | React/SVG + render |
| Story vertical | Mesmo projeto com layout adaptado |
| Vídeo para Reels | Composição Remotion |
| Logo 3D animada | Three.js |
| Variações de texto | Parâmetros de template |
| Revisão manual | Penpot ou editor apropriado |

Isso não significa que Penpot, React e Three.js compartilhem automaticamente o mesmo formato interno. A conversão precisa ser planejada: exportar SVG do Penpot não preserva, por si só, toda a semântica de componentes, restrições de layout ou animações.

Eu criaria um Creative Project Manifest, contendo referências aos projetos nativos e uma especificação intermediária de elementos, parâmetros e assets.

Essa separação permite que o Hermes adapte um projeto para novas mídias sem reconstruí-lo integralmente.

## 5. O que fazer com Graphite?

Graphite Editor.

Pesquisa estratégica — não produção principal.

Nos anexos, Graphite aparece como possível motor gráfico 2D do Hermes porque combina vetores, raster e edição procedural baseada em grafos.

Considero a ideia válida. O código do Graphite tem licença MIT/Apache-2.0, o que favorece uma eventual integração profunda ou fork.

Mas existe uma diferença entre possuir uma arquitetura baseada em grafos e já oferecer uma API estável para agentes manipularem esses grafos.

Eu não substituiria o Penpot pelo Graphite neste momento. Implementaria um experimento separado para verificar acesso ao documento, edição de nós, execução headless, exportação e estabilidade da API.

Se esse experimento funcionar, Graphite poderá oferecer ao Hermes uma capacidade que Penpot e Inkscape não priorizam: composições gráficas procedurais que o agente modifica reconfigurando um grafo de operações.

É uma possibilidade particularmente interessante para efeitos, texturas, padrões, identidade visual generativa e futura composição avançada.

## 6. A integração que eu construiria de outra forma: Three.js

Eu não perderia tempo procurando um MCP genérico de Three.js como primeira solução.

O próprio Three.js já é uma API JavaScript. O Hermes pode escrever cenas diretamente e verificar os resultados no Chromium.

A inovação real seria criar um Hermes Three Bridge, um adaptador controlado pelo Workstation:

```
Hermes Three Bridge
├── inspectScene
├── createObject
├── modifyGeometry
├── setMaterial
├── addAnimation
├── configureLights
├── configureCamera
├── importGLB
├── exportScene
├── capturePreview
└── undoTransaction
```

O editor oficial do Three.js já oferece a base visual para objetos, câmeras, materiais, scripts e cenas. A bridge precisaria controlar essa estrutura de forma estável, sem depender de movimentos de mouse.

Eu usaria um fork fino, mantendo alterações específicas do Hermes isoladas, com versão fixa do upstream e testes de compatibilidade.

Existe ainda uma alternativa que vale investigar para animações 3D com keyframes: Theatre.js. Ele oferece um editor temporal para aplicações web e integração com React Three Fiber. O projeto está menos ativo e seu Studio utiliza AGPL, portanto seria um experimento opcional, não uma dependência central.

## 7. Como o Experience Compiler muda tudo

Esta é, para mim, a ideia com maior valor arquitetural.

O Hermes Creative Workstation não deveria precisar perguntar a uma LLM como executar todas as etapas de uma tarefa que já foi resolvida satisfatoriamente antes.

Imagine o seguinte:

**Primeira solicitação**

“Crie uma animação de logo 3D de oito segundos, em formato vertical, com entrada de câmera e iluminação dramática.”

**Execução inicial assistida por LLM**

Three.js constrói a cena, Remotion compõe a sequência, FFmpeg finaliza o arquivo. O agente inspeciona previews e corrige problemas.

**Captura e certificação**

O Experience Compiler registra um procedimento parametrizável, dependências, versões, entradas, saídas, validações e condições de falha.

**Solicitações futuras**

O Hermes reutiliza o procedimento certificado, trocando a logo, cores e parâmetros. A LLM só participa das etapas que realmente exigem decisões novas.

Aqui está a diferença entre uma skill e uma capacidade operacional.

Uma skill pode ensinar como criar uma animação. Uma capacidade operacional certificada pode executar uma receita específica repetidamente, verificar o resultado e identificar quando precisa recorrer novamente ao agente.

O cuidado essencial é não confundir uma sequência observada com um procedimento confiável. Antes de reutilizar, o Hermes deve ter contratos de entrada e saída, testes, limites de permissões, versões de dependências e condições de invalidação.

Isso preserva a filosofia do Experience Compiler, sem transformar toda atividade criativa em uma automação rígida.

## 8. Licenciamento e segurança

Há uma correção importante em relação a algumas classificações dos arquivos: Remotion não deve ser tratado como um componente open source irrestrito para distribuição comercial.

Sua licença atual permite uso gratuito por indivíduos e determinadas organizações pequenas ou sem fins lucrativos, mas prevê licenças comerciais para outros contextos. Também há regras específicas para produtos de automação e renderização. Portanto, integrar Remotion como dependência de um produto distribuído exige revisão da licença aplicável.

Outras diferenças relevantes:

| Ferramenta | Implicação |
|---|---|
| Penpot — MPL 2.0 | Open source, com obrigações relacionadas aos arquivos modificados abrangidos pela licença |
| Three.js — MIT | Favorável a fork e integração profunda |
| Graphite — MIT/Apache-2.0 | Favorável à integração futura |
| Blender/GIMP/Inkscape — GPL | Boas engines externas; alterações e redistribuição exigem atenção à GPL |
| PartMode — AGPL-3.0 | Atenção especial à distribuição e disponibilização de versões modificadas via rede |
| Remotion — licença própria | Conferir termos antes de comercializar uma solução integrada |

A instalação de MCPs comunitários também exige limites claros. Alguns oferecem execução arbitrária de Python ou scripts, o que é poderoso, mas arriscado.

Para o Hermes, recomendaria processos isolados, diretórios permitidos, controle de rede, confirmação para operações destrutivas, versões fixadas e validação visual dos resultados. Não instalaria servidores MCP desconhecidos automaticamente só porque o usuário pediu uma capacidade criativa.

## 9. Ordem de implementação

Não recomendo tentar integrar toda a suíte de uma vez. Eu seguiria quatro fases:

| Fase | Entrega | Critério para avançar |
|---|---|---|
| 1. Creative Runtime | Manifesto de aplicativos, instalador controlado, health checks, lifecycle e workspaces persistentes | Iniciar, usar, parar e recuperar um app com sucesso |
| 2. Núcleo criativo | Penpot + Remotion + Three.js Editor, com previews e edição humana | Produzir artefatos reais e editáveis nos três ambientes |
| 3. Engines e automação | FFmpeg, Inkscape e Blender; operações tipadas e renderizações | Fluxos repetíveis com artefatos validados |
| 4. Aprendizado operacional | Recipes certificadas e integração com Experience Compiler | Reexecutar fluxos conhecidos com menor custo, sem regressões |

Depois disso, Graphite, áudio procedural, CAD e ferramentas de games entram como módulos adicionais, conforme os casos de uso demonstrarem necessidade.

Uma consideração para a implementação: consegui verificar a documentação pública do Hermes Agent e as ferramentas dos ecossistemas, mas não consegui confirmar o conteúdo do roadmap e o estado dos módulos específicos do Workstation no seu fork por meio dos caminhos tentados no GitHub. Assim, a sequência acima é uma proposta de arquitetura, não uma afirmação de que determinados componentes já estejam prontos.

## Decisão final

**Stack que eu adotaria para a primeira versão operacional**

Design: Penpot + SVG.

Motion: Remotion + FFmpeg.

3D: Three.js Editor.

Render avançado: Blender.

Automação: MCP + APIs + CLI.

Reutilização: Experience Compiler.

A maior oportunidade não está em reunir um grande catálogo de softwares. Está em permitir que o usuário e o Hermes trabalhem sobre o mesmo projeto, cada um com sua forma de controle, e que o sistema aprenda a reproduzir aquilo que já demonstrou funcionar.

Esse é o diferencial que eu procuraria construir antes de adicionar ferramentas mais exóticas.
