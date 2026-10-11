# Hermes Creative Workstation — investigação tecnológica e arquitetural

**Data de corte:** 9 de outubro de 2026  
**Escopo:** pesquisa de tecnologia, leitura estática de repositórios e comparação arquitetural. Nenhum código, documento ou branch do repositório Hermes foi alterado.

## Sumário executivo

Não encontrei um editor open source que já ofereça, em um só documento e com maturidade comprovada, design vetorial/raster avançado, NLE de vídeo, motion graphics, composição 3D, operação por agente e edição humana sem perda.

A recomendação depende do horizonte:

- **Resultados hoje, fora do Hermes:** Penpot para design de produto e Blender para composição 3D, animação e vídeo. Blender mantém cenas, keyframes, compositor e sequências de vídeo/áudio no mesmo arquivo editável. A concessão é uma ferramenta externa e GPL; para trabalho editorial de vídeo sem 3D, Kdenlive ou Shotcut são opções maduras externas.
- **Base de código mais promissora para uma superfície web de edição no Hermes:** OpenReel, condicionado a uma prova de conceito. Seu projeto TypeScript combina timeline de vídeo, clipes de texto/formas/SVG, composições de motion, cenas 3D limitadas e ferramentas de agente. É MIT na raiz, mas está em alpha e mantém subsistemas com esquemas diferentes sob um objeto Project comum.
- **Arquitetura recomendada a longo prazo:** híbrida e progressiva. Hermes conserva identidade do projeto, permissões, execuções, artefatos, evidência e aprendizagem; motores especializados editam subdocumentos nativos. O projeto Hermes deve ser um pacote/manifesto versionado com fontes preservadas, não uma tentativa de reduzir todo motor a um esquema universal de nós.
- **Não recomendo como base:** transformar profundamente o Penpot; adotar a reescrita atual do OpenCut; tratar a branch Girafic do Penpot como pronta; embutir Remotion antes do gate de licença; ou construir um editor amplo com Konva/Fabric/Canvas do zero.
- **Forks investigados:** a branch Girafic do Penpot contém implementação substancial de animação, mas está 378 commits atrás do Penpot atual, mexe em 262 arquivos e não tem PR upstream identificado. FableMint acrescenta interface de agente interessante ao FableCut, mas está seis commits à frente e 206 atrás do pai. Nenhum fork é vencedor de produção demonstrado.
- **Estado real do Hermes:** Creative Workstation consta na main como iniciativa planejada/documentada. CW-01 está bloqueada; não há runtime criativo, motores instalados ou E2E do produto. Main é o ponto correto para futuras análises: workstation/laya-direct-system1 está no ancestral da main, que tem 21 commits posteriores.

A classificação numérica adiante é triagem baseada em código, documentação primária, releases e contratos visíveis. Não é benchmark. **Os seis cenários de validação do pedido não foram executados.** Este ambiente permitiu leitura dos repositórios, mas não forneceu checkout local nem os runtimes para compilar e rodar as provas.

## Método, data e limites

Foram consultados repositórios e arquivos oficiais no GitHub, documentação, metadados de licença, branches, comparação de commits, releases e issues. A auditoria direta concentrou-se em OpenReel, OpenCut, Penpot/Girafic, Hermes, FableMint, Excalimate e Babylon.js Editor.

Uso três estados para as conclusões:

- **Implementado em código:** existem tipos, handlers, UI, testes ou APIs no repositório.
- **Prometido:** aparece em README, roadmap ou issue como futuro, não como recurso entregue.
- **Validado em execução por esta pesquisa:** somente quando rodei o produto. Nenhum candidato teve execução local aqui.

Uma classe, endpoint ou teste no repositório não prova que o fluxo completo funcione no Windows, que o preview corresponda ao export, ou que o projeto sobreviva a fechar/reabrir. Não afirmo que qualquer teste 1–6 passou.

Snapshot Hermes:

- **main:** f21e803b3525b70ee6be2305e579c1cc1f930e74, commit de 8 de outubro de 2026.
- **workstation/laya-direct-system1:** 04e158f3d4320ffde4ff23d600c3f6d1e9248b4c.
- Comparação GitHub: main é descendente da branch e tem 21 commits posteriores.
- Documentos do Workstation na main dizem explicitamente **PLANNED / DOCS ONLY / NOT IMPLEMENTED**; CW-01 continua bloqueada e CW-02 não está admitida pelo gate registrado.

---

# Parte I — mapa tecnológico

## A. Design 2D, ilustração e vetores

| Projeto | O que é de fato | Licença / estado | Valor e limite para Hermes |
|---|---|---|---|
| [Penpot](https://github.com/penpot/penpot) | Aplicação completa de design UI/vetor com arquivos, páginas, componentes, colaboração, API, plugins e MCP oficial. Frontend ClojureScript, backend Clojure, serviços e renderização próprios. | MPL-2.0; produto maduro, self-hostável; stack e operação consideráveis. | Melhor aplicação pronta para design de produto e vetores. Não é NLE nem editor 3D; adicionar timeline de NLE muda documento, render, backend e persistência. Integrar como editor/subprojeto ou usar API/MCP, não como núcleo universal. |
| [Fabric.js](https://github.com/fabricjs/fabric.js) | Modelo de objetos sobre Canvas 2D, controles, seleção, serialização e conversão SVG/Canvas. | MIT; biblioteca ativa. | Boa base se houver necessidade de criar canvas próprio com objetos arrastáveis e exportação. Não fornece Photoshop/Figma completo, ferramentas de nós, design system ou gestão de projeto. |
| [Konva](https://github.com/konvajs/konva) / [React-Konva](https://github.com/konvajs/react-konva) | Cena em Canvas com layers, eventos, hit-testing, transformações e integração React. | MIT; biblioteca, com exemplos de editor. | Boa camada de interação para canvas e preview. Não fornece modelo completo de design, paths profissionais ou documento editável por conta própria. |
| [Paper.js](https://github.com/paperjs/paper.js) | Framework vetorial com paths, segmentos Bézier, operações geométricas e scripting. | MIT; ferramenta técnica, não editor. | Útil para paths, snapping e geometria; não substitui interface de design nem documento completo. |
| [SVG.js](https://github.com/svgdotjs/svg.js) | Manipulação e animação do DOM SVG. | MIT. | Boa para construir e animar SVG existente; não é editor completo de paths nem armazenamento. |
| [PixiJS](https://github.com/pixijs/pixijs) | Renderizador 2D de alto desempenho sobre WebGL/WebGPU, sprites, texturas e filtros. | MIT; engine/renderizador. | Útil para preview/raster e cenas com muitos elementos. Não fornece edição vetorial semântica ou editor pronto. |
| [Excalidraw](https://github.com/excalidraw/excalidraw) | Editor completo de whiteboard/diagramas com JSON editável e exportação PNG/SVG. | MIT. | Excelente para diagramas, rascunhos e explicadores com estética desenhada. Não oferece o conjunto de paths, texto, layout e edição de ferramenta de design profissional. |
| [tldraw](https://github.com/tldraw/tldraw) | SDK e editor completo de canvas infinito, API de runtime e schema persistido. | O SDK principal tem licença comercial/hobby com chave para produção; alguns pacotes auxiliares são MIT. Não classificar o SDK como MIT. | Tecnicamente bom para canvas colaborativo e custom shapes; a licença conflita com preferência por distribuição aberta e precisa de aprovação comercial. |
| [Graphite](https://github.com/GraphiteEditor/Graphite) | Aplicação/engine 2D vetorial e raster, não destrutiva, baseada em grafo de nós; código Rust e frontend web/WASM. | Apache-2.0; alpha. O projeto marca motion design, VFX e publicação como roadmap. | Melhor observatório de arquitetura de grafo procedural e edição 2D aberta. A maturidade atual não sustenta a promessa de suíte universal. |
| [Inkscape](https://inkscape.org/) / [GIMP](https://www.gimp.org/) / [Krita](https://krita.org/) | Aplicações desktop completas para vetor, raster e pintura/ilustração, respectivamente. | GPL; maduras, com plugins e scripting variáveis. | Alternativas externas para produção real; não são bibliotecas incorporáveis. Inkscape também oferece CLI para conversão/export. Nenhuma é timeline universal. |
| [OpenToonz](https://github.com/opentoonz/opentoonz) / [Synfig](https://github.com/synfig/synfig) | Aplicações de animação 2D quadro a quadro ou vetorial. | GPL; ferramentas especializadas. | Úteis para animação tradicional; não resolvem NLE, editor 3D e design colaborativo numa superfície única. |

**Implicação técnica:** Canvas é alvo de desenho, não documento. Se a UI usar Fabric, Konva ou Pixi, Hermes ainda terá que definir ids, hierarquia, paths, constraints, texto, história, undo, versões e serialização. SVG preserva semântica vetorial melhor que bitmap, mas a importação/exportação de SVG arbitrário perde alguns filtros, fontes, máscaras e extensões. Escolher renderizador não elimina o custo do modelo editável.

## B. Motion graphics e animação

| Tecnologia | Categoria real | Licença / risco | Uso recomendado |
|---|---|---|---|
| [Motion Canvas](https://github.com/motion-canvas/motion-canvas) | Projeto/engine de animação TypeScript, com preview e timeline para inspeção e export de frames. | MIT. | Rápida para vídeos gráficos determinísticos programados. Não é timeline genérica multifaixa com editor visual de qualquer media. |
| [Revideo](https://github.com/redotvideo/revideo) | Engine TypeScript que renderiza cenas declarativas/código; API headless de vídeo e player React. | MIT; telemetria de render pode ser desligada conforme docs. | Alternativa aberta a Remotion para renderização dirigida por código. É renderizador, não NLE de usuário final. Boa candidata para serviço de render após teste de paridade. |
| [Remotion](https://github.com/remotion-dev/remotion) | Renderização React por frame, player e pipeline de vídeo com ecossistema amplo. | Licença comercial própria. A página atual cobra para “build video creation tools” por render, com mínimo mensal; Editor Starter é pago. | Bom para protótipos e automação React. Hermes Work é editor/ferramenta de criação, então licença deve ser aprovada antes de incorporar ou vender a função. |
| [Theatre.js](https://github.com/theatre-js/theatre) | Biblioteca de animação + Studio visual para editar cenas web e propriedades. | @theatre/core Apache-2.0; @theatre/studio AGPL-3.0. | Bom editor técnico de motion web. Workstation incluiria o Studio como UI de criação; essa licença importa mesmo que bundle final use core. |
| [GSAP](https://gsap.com/) | Biblioteca de animação de propriedades; não editor. | Termos próprios gratuitos para muitos usos comerciais, mas não é licença OSS padronizada. Confirmar limites ao vender editor/SDK que expõe GSAP. | Boa interpolação e timeline programática; não fornece documento, interface de timeline ou export de vídeo. |
| [Anime.js](https://animejs.com/) / [Motion](https://motion.dev/) | Bibliotecas de animação DOM/SVG/JS. | MIT nos cores pertinentes. | Componentes para UI e animação web; não substituem sequenciador/exportador. |
| [Lottie](https://github.com/airbnb/lottie-web) | Formato/runtime de animações serializadas, com players e exporters de ecossistema. | Runtime principal MIT; authoring não equivale a editor OSS completo. | Asset de motion leve importável/renderizável; não modelo mestre universal. |

**Forks e pequenos editores:** [Excalimate](https://github.com/excalimate/excalimate) combina Excalidraw, timeline, câmera, export de vídeo/Lottie e MCP; [MotionEditor](https://github.com/tomaslachmann/motion-editor) oferece canvas, layers, keyframes, graph, assets de vídeo/áudio e export Remotion; [Nemo](https://github.com/mysteropodes/nemo) tenta reunir animação e desenho quadro a quadro num documento; [AnimateMo](https://github.com/zainadeel/animatemo) anima SVG e exporta GSAP; [Rivo](https://github.com/zin-ix/rivo) faz rigging/animação SVG. São verticais, alpha ou sem licença explícita detectada, não base universal comprovada.

## C. 3D

| Tecnologia/produto | O que fornece | Licença / maturidade | Limite de integração |
|---|---|---|---|
| [Three.js](https://github.com/mrdoob/three.js) | Engine JS 3D WebGL/WebGPU, glTF, cameras, materials, scene graph, animation clips; inclui [Editor web](https://threejs.org/editor/). | MIT; engine madura e ativa. | Editor simples, orientado a montagem/inspeção de cena, não modeler/rigging de nível Blender. Engine é ótima para camada 3D embutida; Hermes ainda teria que manter cena, UI, keyframes e export. |
| [React Three Fiber](https://github.com/pmndrs/react-three-fiber) | Renderizador declarativo React para Three.js. | MIT. | Integra Three à UI React; não fornece editor. Não converter React scene tree automaticamente em formato universal sem camada própria. |
| [Babylon.js](https://github.com/BabylonJS/Babylon.js) + [Babylon.js Editor](https://github.com/BabylonJS/Editor) | Engine e editor desktop Electron de cenas. O editor tem cena/asset browser, CLI e MCP; repo atual é TypeScript, Apache-2.0, Windows/macOS/Linux, testes Vitest. | Editor 5.5.2 indicado no README consultado; repo ativo em outubro de 2026. | Melhor candidato de app especializado local para 3D com controle por agente. É editor externo de cenas de engine, não timeline de vídeo. MCP e scripts constroem objetos editáveis; validar ponte/export antes de adotá-lo. |
| [PlayCanvas Engine/Editor](https://github.com/playcanvas/editor) | Engine e editor visual WebGL/WebGPU/WebXR com MCP para sessão aberta. | Editor MIT; frontend fonte ativo. | Editor depende da experiência hospedada em playcanvas.com e dados de projeto na plataforma; menos adequado a editor offline local autônomo. Demonstra como um editor pode expor MCP com mutação ao vivo. |
| [Blender](https://www.blender.org/) | Aplicação completa 3D, animação, graph editor, compositor, VSE, Python API, headless e glTF. | GPL-3.0-or-later. | Único candidato examinado que cobre 3D, animação, composição e vídeo num documento maduro. É aplicação externa/subprocesso, não UI incorporável leve; não tem UX de Penpot/Illustrator. |
| Godot | Engine/editor de jogos com 2D, 3D, animação e scripting. | MIT. | Pode fornecer edição visual e runtime, mas é game engine. NLE e export vídeo exigem módulos externos; não é recomendação de workstation criativo. |
| glTF/GLB | Formato/intercâmbio de cena, malhas, materiais, rigs e animação. | Especificação aberta; direitos do asset à parte. | Bom formato de interchange 3D. Não guarda todas as operações não destrutivas nem substitui projeto-fonte Blender/Babylon. |

## D. Vídeo e áudio

| Projeto/API | Papel real | Licença / observação |
|---|---|---|
| [FFmpeg](https://ffmpeg.org/) | Ferramentas e bibliotecas de decode/encode, filtros, mux/demux e transcode; não editor. Pode rodar como worker local. | Default LGPL 2.1+ em configurações compatíveis; opções GPL e dependências mudam o regime. Binários, codecs e patentes devem ser auditados por build/plataforma. |
| [MLT](https://github.com/mltframework/mlt) | Framework multimídia orientado a edição, usado por Shotcut/Kdenlive. | Core LGPL-2.1; módulos/plugins têm licenças próprias. Não é UI. |
| [GStreamer](https://gstreamer.freedesktop.org/) | Framework de mídia por elementos e plugins. | LGPL para core, módulos variáveis. Pipeline, não NLE. |
| [WebCodecs](https://developer.mozilla.org/en-US/docs/Web/API/WebCodecs_API) | API do navegador para decode/encode por frame com acesso a hardware em workers. | API do browser, não encoder independente. Codecs variam por browser, OS e hardware; exige fallback e teste no Electron/Windows. |
| [MediaBunny](https://github.com/Vanilagy/mediabunny) | Toolkit TypeScript browser para ler, escrever e converter containers/áudio/vídeo. | MPL-2.0; usa capabilities de codec do browser ou backend server. Não é FFmpeg nem editor. |
| [OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO) | API/formato de interchange para ordem, duração de cortes e referências a media. | Apache-2.0; não é container de media, renderizador ou documento gráfico universal. Bom para troca de montagem NLE. |
| [Editly](https://github.com/mifi/editly) | CLI Node baseada em JSON/FFmpeg para gerar montagem. | MIT; render programático/template, sem editor visual geral. |
| [Shotcut](https://github.com/mltframework/shotcut) / [Kdenlive](https://github.com/KDE/kdenlive) | Aplicações NLE desktop completas baseadas em MLT. | GPL-3.0; boas para entrega externa, não bibliotecas React. |
| [Olive](https://github.com/olive-editor/olive) | Projeto NLE com interface completa e pipeline próprio. | GPL; README marca alpha e altamente instável. |
| [LosslessCut](https://github.com/mifi/lossless-cut) | Corte lossless de streams com UI desktop. | GPL; bom para trim/copy rápido, não timeline de efeitos/motion. |
| [OpenShot](https://github.com/OpenShot/openshot-qt) | Editor NLE desktop e engine libopenshot. | GPL na aplicação; dependências próprias. Investigar apenas se o requisito for reaproveitar editor externo. |

**Não confundir:** WebCodecs/MediaBunny/FFmpeg são blocos de mídia; MLT/GStreamer são frameworks; OTIO troca informação editorial; Shotcut/Kdenlive são produtos. Uma timeline JSON/OTIO não inclui compositor nem garante render igual ao preview.

## E. IA visual executável localmente

| Tarefa | Opções de pesquisa | Avaliação/licença |
|---|---|---|
| Segmentação/rotoscopia de imagem/vídeo | [SAM 2](https://github.com/facebookresearch/sam2) | Código, demo, treino e checkpoints informados como Apache-2.0. API de vídeo propaga máscaras; não promete alpha de cabelo perfeito. Boa primeira prova local com worker Python e GPU. |
| Remoção de fundo de imagem | [rembg](https://github.com/danielgatis/rembg) | Código MIT, mas docs dizem que pesos/modelos têm licenças próprias. Não aprovar modelo pelo LICENSE do wrapper. |
| Matte de vídeo | [Robust Video Matting](https://github.com/PeterL1n/RobustVideoMatting) | Pipeline PyTorch/ONNX/TensorFlow.js/CoreML; repo GPL-3.0. Útil tecnicamente, com custo de licença ao incluí-lo/distribuí-lo. |
| Tracking/pose | SAM 2 para propagação de máscara; OpenCV para optical flow/tracking. | [OpenPose](https://github.com/CMU-Perceptual-Computing-Lab/openpose) usa licença de pesquisa não comercial; não é candidato a produto sem outra licença. |
| Transcrição/legendas | [Whisper](https://github.com/openai/whisper), faster-whisper | Whisper informa código e pesos MIT; executar em background e devolver segmentos/timings como clips editáveis. |
| Separação de stems | [Demucs](https://github.com/facebookresearch/demucs) | Código MIT, mas upstream diz que não é mais mantido. Verificar direitos de weights/datasets e não assumir que MIT do código cobre todos os pesos. |
| Interpolação de frames | [RIFE](https://github.com/hzwer/ECCV2022-RIFE) | Código RIFE MIT; validar qualidade, ghosting e modelos na GPU alvo. |
| Geração de assets/imagens | [ComfyUI](https://github.com/Comfy-Org/ComfyUI), Hugging Face Diffusers | ComfyUI é app de nós GPL-3 para execução local. Integrar como sidecar/API ou usar modelos por serviço autorizado. Cada modelo, checkpoint, LoRA e node tem licença própria; “open weights” não significa uso comercial irrestrito. |
| Geração 3D/vídeo | Workflows de pesquisa via ComfyUI e modelos específicos | Não escolher ainda. Modelos mudam; direitos, datasets, VRAM e tempo por frame precisam de gate. Criar interface de job/proveniência, não acoplar um modelo ao Project. |

**Estratégia recomendada:** operações de IA como jobs assíncronos que produzem dados revisáveis (máscara, track, transcript, keyframes, asset) e operações aplicáveis ao projeto. Resultado continua editável no modelo nativo. Não embutir modelo na UI nem tratar imagem final como substituto do original.

---

# Parte II — repositórios, forks e estado observado

## OpenReel — candidato a editor web de vídeo/motion

- Repositório: [Augani/openreel-video](https://github.com/Augani/openreel-video), commit auditado c9340465e5d37e684cc25bdbe746c4ccd45e165c, de 3 de outubro de 2026; MIT na raiz; TypeScript; release v1.0.0-alpha.17.
- Arquitetura divide app web/desktop e pacotes core/agent/creation. Existem testes para timeline, export, agente e cena 3D; a suite não foi executada.
- **Documento:** packages/core/src/types/project.ts tem Project serializável com timeline, mediaLibrary, textClips, shapeClips, svgClips, masks, adjustment layers, nested clips, motionCompositions, motionInstances e shaders.
- **Vídeo:** packages/core/src/types/timeline.ts define tracks/clips, transforms, keyframes, effects, áudio, velocidade e transições.
- **Motion:** packages/core/src/motion/types.ts define composições/layers de texto, shapes, imagens, vídeo, grupos, partículas, adjustment e scene3d. motion-engine.ts converte uma instância em clip reconhecido pela timeline principal. Portanto motion não está só numa aba sem relação com NLE: há ligação de instância/clip dentro do documento raiz.
- **3D:** motion-scene3d.ts declara primitives, room, text3D e modelo; material, iluminação, câmera e keyframes fazem parte de uma layer de cena. Não equivale a editor de hierarquia, rigging e modelagem 3D. A cena é modelada para motion/composição.
- **Agente:** packages/agent/src/host.ts define Project como fonte autoritativa serializável, ações, transações undoable, jobs e export. docs/AGENT-GUIDE.md descreve superfícies web/desktop/headless com ferramentas comuns; README relata 228 ferramentas + chamadas de escape. beginTransaction/commitTransaction dá rollback de turno. Isso é mais seguro que editar diretamente objetos da UI.
- **Risco preview/engine:** comentários e código indicam que stores e renderizadores precisam permanecer sincronizados; ações que mudem arrays shape/text fora do host/engine podem deixar preview desatualizado. O bridge tipado é central.
- **Export:** exportMotionScene é capability opcional no host; render queue/motion export pode não existir em todos hosts. Engine de export é extensa, mas não foi comparada em execução com preview. Headless, desktop e browser não são equivalentes sem teste.
- **Persistência:** há Project JSON/IndexedDB e autosave; media é armazenada/recuperada em estrutura separada e metadados ajudam relink. Não há prova nesta pesquisa de pacote único autossuficiente com projeto+todo media para transferir entre máquinas.
- **Licença/dependências:** MIT na raiz é favorável; MediaBunny é MPL-2.0 e desktop/FFmpeg/codec builds pedem auditoria própria.
- **Resultado:** melhor candidato encontrado para base code-first de vídeo/motion com operações IA; não atende design profissional 2D nem edição 3D completa. Tratar alpha como risco de churn e rodar bateria 1–6 antes de fork.

Links de código: [Project](https://github.com/Augani/openreel-video/blob/c9340465e5d37e684cc25bdbe746c4ccd45e165c/packages/core/src/types/project.ts), [timeline](https://github.com/Augani/openreel-video/blob/c9340465e5d37e684cc25bdbe746c4ccd45e165c/packages/core/src/types/timeline.ts), [motion types](https://github.com/Augani/openreel-video/blob/c9340465e5d37e684cc25bdbe746c4ccd45e165c/packages/core/src/motion/types.ts), [3D layer](https://github.com/Augani/openreel-video/blob/c9340465e5d37e684cc25bdbe746c4ccd45e165c/packages/core/src/motion/motion-scene3d.ts), [EditingHost](https://github.com/Augani/openreel-video/blob/c9340465e5d37e684cc25bdbe746c4ccd45e165c/packages/agent/src/host.ts), [StorageEngine](https://github.com/Augani/openreel-video/blob/c9340465e5d37e684cc25bdbe746c4ccd45e165c/packages/core/src/storage/storage-engine.ts), [AI guide](https://github.com/Augani/openreel-video/blob/c9340465e5d37e684cc25bdbe746c4ccd45e165c/docs/AGENT-GUIDE.md).

## Penpot e a branch Girafic

### Penpot upstream

- Repositório [penpot/penpot](https://github.com/penpot/penpot), MPL-2.0. Produto web de design colaborativo, self-hostável, com API/plugins e servidor MCP oficial no monorepo.
- Arquitetura usa frontend ClojureScript, backend Clojure, serviços e modelo gráfico próprio. Alterar núcleo requer compreender migrations, RPC commands, frontend, renderer e testes.
- Produto e código dão suporte a 2D/vetores/design systems. Não encontrei NLE multifaixa de vídeo ou objeto Three.js nativamente editável.
- Penpot pode ser editor 2D vinculado ao projeto Hermes; rasterizar cena 3D/MP4 nele não mantém os objetos originais editáveis.

### girafic/penpot — girafic-penpot-timeline-animation

- Branch existente, com código substantivo. Comparação com upstream atual em 9 de outubro: **99 commits à frente, 378 atrás**, merge base fab8e0e35d2773ae543f263b9c499ff3d66b082a. Diff: **262 arquivos, +25.894/−322 linhas**: frontend 184, common 37, backend 22, render-wasm 13, além de MCP/plugins.
- Não encontrei PR upstream da branch. Thread do autor a descreve como experimental e com feature flag. Ausência de PR e drift são fatos separados da qualidade do código.
- A branch adiciona timeline por board, tracks/keyframes para propriedades de shapes, easing, loop/ping-pong, áudio e caminhos de export MP4/WebM/GIF/AVIF/SVG/Lottie/dotLottie, além de renderer, persistência, plugins/MCP e testes.
- É mais que demo, mas continua animação de design por board. Não é timeline NLE com vários clips nem engine 3D. Mudanças incluem migrations e grande carga de merge.
- **Conclusão:** auditoria interessante; não usar diretamente sem rodar suite, editar/exportar/reabrir, inspecionar migrations e medir atualização para os 378 commits upstream.

Links: [branch](https://github.com/girafic/penpot/tree/girafic-penpot-timeline-animation), [comparação no upstream atual](https://github.com/penpot/penpot/compare/develop...girafic:girafic-penpot-timeline-animation), [timeline UI](https://github.com/girafic/penpot/blob/girafic-penpot-timeline-animation/frontend/src/app/main/ui/workspace/timeline.cljs), [modelo comum](https://github.com/girafic/penpot/blob/girafic-penpot-timeline-animation/common/src/app/common/types/animation.cljc), [plugin motion API](https://github.com/girafic/penpot/blob/girafic-penpot-timeline-animation/frontend/src/app/plugins/motion.cljs).

## OpenCut atual e OpenCut Classic

- [OpenCut-app/OpenCut](https://github.com/OpenCut-app/OpenCut) está sendo reescrito do zero. A arquitetura nova anuncia Editor API, plugins, desktop/mobile/web com Rust core, MCP, headless e scripting como recursos futuros.
- Issue de tracking deixa esses itens desmarcados. README não prova que core/API/MCP estão prontos.
- Rust core e app web/desktop são direção, não compatibilidade já demonstrada com Hermes. MIT é favorável, mas não compensa ausência de editor/API testada.
- README aponta o editor anterior como versão utilizável. [OpenCut Classic](https://github.com/OpenCut-app/opencut-classic) foi arquivado em 17 de maio de 2026. Seu README descreve refatoração de timeline, renderer e export e pede para evitar mudanças em preview/export. É NLE web real, mas congelado enquanto partes críticas mudavam.
- **Conclusão:** não iniciar integração estratégica no rewrite atual. Classic serve para explorar UI/workflows de editor pequeno, não como motor confiável de render/export a longo prazo.

## Outros candidatos pequenos e forks

| Projeto | Achado e estado | Decisão |
|---|---|---|
| [Excalimate](https://github.com/excalimate/excalimate) | MIT; versão 0.5.1 observada; Excalidraw + timeline por elemento/câmera, presets, MP4/WebM/GIF/SVG/Lottie, 35 tools MCP e live preview HTTP/SSE. MCP age sobre schema browser-neutral e não hospeda modelo. README alerta que parte relevante foi feita com IA e ainda está sendo limpa. | Excelente prova vertical de diagramas animados; não NLE universal nem 3D. |
| [FableMint](https://github.com/Pheem49/FableMint) / [pai FableCut](https://github.com/ronak-create/FableCut) | MIT; Node local sem dependências de pacote, UI web e timeline JSON; 3 faixas de vídeo, áudio, split/trim/transitions, SVG/text overlays, MCP/REST, checkpoints e atualização ao vivo. MCP escreve project.json usado pelo editor e verifica revisão concorrente. | Padrão simples de “documento como API”; limitado a vídeo/overlays, não design vetorial/3D. |
| Fork FableMint vs pai | Compare: seis commits à frente e 206 atrás. Diff inclui app.js, mcp-server.js e checkpoints; não substitui arquitetura do pai. package.json não mostra script de teste; nenhum teste foi executado aqui. | Não declarar fork superior: portar recursos pontuais ao pai é mais defensável que adotar fork divergente. |
| [MotionEditor](https://github.com/tomaslachmann/motion-editor) | React/Vite e backend Node local para JSON, assets, biblioteca, ações IA e export Remotion; canvas SVG/texto/formas, vídeo/áudio, keyframes e graph. Não foi detectado SPDX license no repo. | Boa referência funcional, não usar antes de resolver direitos. Remotion exige gate para produto que cria vídeos. |
| [Nemo](https://github.com/mysteropodes/nemo) | GPL-3.0, 0.7.0-alpha.1, WebGPU, desenho quadro a quadro e motion design no mesmo documento. README assume alpha cedo, bugs e mudanças de formato. | Observar; sem NLE e sem estabilidade de produção. |
| [Graphite](https://github.com/GraphiteEditor/Graphite) | Rust, Apache-2.0, alpha ativo. Motion/VFX aparecem principalmente em roadmap. | Potencial de engine procedural 2D, não atalho de produto maduro. |
| [AnimateMo](https://github.com/zainadeel/animatemo) e [Rivo](https://github.com/zin-ix/rivo) | SVG/keyframes em escopo estreito; não foi detectada licença declarada nos metadados consultados. | Inspiração técnica, não candidatos de distribuição até resolver licença. |

---

# Parte III — comparação arquitetural

| Estratégia | O que reutiliza | Vantagem | Custo/risco | Parecer |
|---|---|---|---|---|
| **A. Adaptar profundamente Penpot** | Produto/documento 2D maduro; forks demonstram animação de board. | Excelente design vetorial, APIs e plugins. | Núcleo amplo; NLE, 3D e render de vídeo mexem em frontend, backend, schema, migrations e renderer. Fork tem alto drift. | Não como base universal. Manter Penpot como módulo 2D e usar API/MCP. |
| **A2. Adaptar OpenReel profundamente** | Timeline web, Project, motion, clip 3D simplificado, agente e export. | Mais próximo de vídeo+motion+design elementar em um Project; MIT e TS encaixam no Electron/React. | Alpha; schemas separados; persistência de media e paridade ainda sem PoC; não tem design vetorial de produto nem Blender completo. | Melhor código para avaliar em vídeo/motion, não solução final. |
| **B. Construir UI e engine próprias sobre libs** | React/TS, SVG/Canvas, timeline, FFmpeg/WebCodecs. | Controle de UX, schema e integração Hermes. | Canvas não traz ferramentas, histórico, modelo, undo, texto, mask, constraints, timeline nem render. Reimplementar produtos maduros é trabalho duplicado. | Construir shell e workflows Hermes, não editor inteiro. |
| **C. Híbrida com documento/manifesto Hermes** | Penpot, OpenReel, Blender/Babylon/Three, FFmpeg e capacidades Hermes. | Entrega incremental; cada motor mantém formato forte; IA usa adapters; peças substituíveis. | Sincroniza assets/tempo, lifecycle de subdocs e render preview; editabilidade bidirecional precisa ser declarada e provada. | Melhor arquitetura longa, com ownership de subdocs e round-trip explícito. |
| **D. Aplicativos externos sob shell unificado** | Penpot, Blender, Kdenlive/Shotcut. | Mais rápido para produzir arte/vídeo sem desenvolver editor. | Não cria UI integrada nem timeline/documento comum; cópias/exports têm bordas; licenças e automação externa. | Melhor curto prazo operacional; shell não é documento único. |
| **E. Um documento universal sem subdocs** | Um schema de shapes, timeline, 3D, áudio e vídeo. | Aspira a uma fonte única e coerente. | Engines discordam em coordenadas, tempo, efeitos, rig, composição e render. Schema pequeno perde conteúdo; grande vira engine gigante. | Evitar. Criar envelope comum com subdocs nativos. |

## Modelo de projeto recomendado

Um arquivo Hermes Creative Project, por exemplo .hcw, poderia conter:

- manifest.json versionado, id do projeto, timebase racional, render profile, engine IDs, assets e proveniência.
- assets/ com media, hash, metadados, licença e proxies.
- subprojects/ com arquivo-fonte nativo de cada domínio: Penpot/design, OpenReel/motion-video, Blender/Babylon/glTF.
- composition.json com referências a subprojects, ranges, transformação de layer, versão do adapter, operação de import e fallback render.
- renders/ como cache/export, nunca fonte de verdade.
- vínculo de cada layer visual ao documento proprietário e teste de ida/volta para cada transformação anunciada como editável.

Para um objeto externo, distinguir: **editável nativamente**, **editável no aplicativo proprietário via ponte**, ou **apenas renderizado/flattened**. Não dizer que PNG de cena 3D é objeto 3D editável.

Use OpenTimelineIO para interchange de montagem; SVG/Lottie/glTF para assets; manifesto Hermes para referências/proveniência. Nenhum substitui documentos-fonte.

---

# Parte IV — Hermes Work real e integração

## Branches e documentação

Caminhos reais na main consultada:

- [workstation/ROADMAP.md](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/f21e803b3525b70ee6be2305e579c1cc1f930e74/workstation/ROADMAP.md)
- [workstation/ARCHITECTURE.md](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/f21e803b3525b70ee6be2305e579c1cc1f930e74/workstation/ARCHITECTURE.md)
- [workstation/SOURCE_MATRIX.md](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/f21e803b3525b70ee6be2305e579c1cc1f930e74/workstation/SOURCE_MATRIX.md)
- [workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/f21e803b3525b70ee6be2305e579c1cc1f930e74/workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md)
- [CW-01 audit](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/f21e803b3525b70ee6be2305e579c1cc1f930e74/workstation/creative-workstation/CW01_AUDIT_2026-10-08.md)
- [Creative Workstation architecture](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/f21e803b3525b70ee6be2305e579c1cc1f930e74/workstation/creative-workstation/ARCHITECTURE.md)

Documentos na main registram proposta, referências e gates, não aplicativo. Roadmap indica React/SVG→Electron preview→PNG, FFmpeg, estudo Remotion após gate, Penpot, Three.js Editor e adapters Blender/Inkscape. É planejamento documental.

## O que já existe e deve ser reutilizado

- **workstation/task_compiler.py:** caminho canônico de execução estruturada; não chama modelo para resolver escrita nem adivinha mutações.
- **workstation/operational_capabilities.py:** registro/ciclo de vida de capacidades promovidas após verificação.
- **workstation/experience_compiler/compiler.py** e módulos de promoção/contrato: aprendizagem de outcomes verificados em capability formal; não aprende de mera intenção.
- **workstation/system1/laya_provider.py** e schemas/contracts: provider System-1 para decisões de conjunto fechado; não deve ganhar autoridade para editar projeto por escolher uma ação.
- **workstation/artifacts.py:** armazenamento durável por referência e evidência.
- **workstation/integrations/hermes/adapter.py**, resolução operacional e runners locais: lugar para construir ponte segundo contratos existentes.
- **apps/desktop/src/:** UI React/API/componentes do Desktop.
- **apps/desktop/electron/workstation-browser-runtime.ts:** runtime Electron com WebContentsView para Browser controlado, com IPC e controle autenticado local. É runtime Browser, não editor criativo existente.

Integração deve preservar Session/TaskRun, políticas/control plane, autorização/verificação, ArtifactStore/Journal e Experience Compiler. Não criar banco, agent runtime, compilador de workflow ou caminho oculto de escrita paralelo.

---

# Parte V — capacidades, pesos e scores

## Matriz de capacidades

| Candidato | Design 2D | Motion/keyframes | NLE vídeo | 3D integrado | Agente/API | Papel indicado |
|---|---|---|---|---|---|---|
| Penpot upstream | Forte | Baixo | Não | Não | MCP/plugins fortes para design | Editor 2D externo/ponte |
| Penpot Girafic | Forte | Médio para board animation | Não é NLE | Não | MCP/plugins alterados | Fork experimental |
| OpenReel | Médio para shapes/text/SVG; não substitui Penpot | Forte para seu escopo | Forte por escopo | Cena 3D/motion limitada | MCP/headless/host tipado | Melhor base web de vídeo/motion a provar |
| Blender | Básico/3D-centric | Forte | Forte | Forte | Python/headless; MCP externo pede validação | Produção externa e bridge |
| Excalimate | Diagramas/whiteboard | Forte em explainers | Export vídeo, não NLE geral | Não | MCP local, live schema | Módulo de diagramas animados |
| FableMint | Overlay texto/SVG | Keyframes de clips | Editor NLE pequeno | Não | MCP + REST sobre project.json | Benchmark de vídeo simples |
| Babylon Editor | Não | Animação cena 3D | Não | Forte dentro Babylon | MCP + script API | Editor externo de cenas |
| OpenCut rewrite | Não validado | Prometido | Não qualificado | Não | API/MCP/headless prometidos | Reavaliar quando funcional |
| Graphite | Vetor/raster alpha | Motion em roadmap | Não | Grafo 2D | API precisa de avaliação | Observar evolução |
| Hermes Hybrid | Nenhuma função criativa implementada | Nenhuma | Nenhuma | Nenhuma | Runtime Hermes existe; CW adapter não | Arquitetura futura, não software pronto |

## Matriz ponderada — candidatos existentes como base

Fórmula: score = soma de nota 0–10 × peso / 100. Pesos iguais aos solicitados. Notas refletem código/releases, não execução própria. “Implementado e comprovado” recebe nota menor quando maturidade/evidência é fraca; nenhuma linha recebe 10 sem validar fluxos 1–6.

| Candidato | Funções 25 | IA 15 | Unificação/editabilidade 20 | Velocidade 15 | Extensão 10 | Estabilidade 10 | Licença 5 | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| OpenReel | 7 | 8 | 7 | 8 | 8 | 5 | 8 | **7,25** |
| Blender | 8 | 4 | 7 | 6 | 8 | 9 | 3 | **6,75** |
| FableMint | 6 | 8 | 4 | 8 | 6 | 4 | 9 | **6,15** |
| Excalimate | 5 | 9 | 4 | 8 | 6 | 4 | 9 | **6,05** |
| Penpot + Girafic | 6 | 8 | 6 | 4 | 7 | 3 | 7 | **5,85** |
| Penpot upstream | 5 | 8 | 2 | 5 | 8 | 8 | 7 | **5,55** |
| MotionEditor | 6 | 5 | 5 | 6 | 6 | 3 | 0 | **5,05** |
| OpenCut Classic | 5 | 3 | 2 | 6 | 5 | 2 | 9 | **4,15** |
| Graphite | 4 | 2 | 4 | 3 | 8 | 3 | 9 | **4,10** |
| Nemo | 4 | 2 | 4 | 3 | 7 | 2 | 4 | **3,65** |
| OpenCut rewrite | 2 | 2 | 2 | 2 | 7 | 2 | 9 | **2,85** |

### Justificativas dos scores

- **OpenReel (7,25):** melhor cobertura de vídeo/motion e tool API num Project; reduz código redundante. Cai por alpha, export/preview sem prova, media persistido em estrutura separada e falta de design/3D profissional.
- **Blender (6,75):** mais funções de produção hoje e estável; cai em UI Hermes nativa, distribuição GPL, ergonomia de design e integração agent pronta.
- **FableMint (6,15):** operações legíveis pelo modelo e human-in-the-loop são simples; cai em arquitetura pequena, fork com drift e ausência de 3D/design.
- **Excalimate (6,05):** agent UX explícita para explainers, MCP e documento de desenho; não é NLE/3D e reconhece cleanup em andamento.
- **Penpot+Girafic (5,85):** adiciona timeline em design existente; cai por drift e ausência de NLE/3D. Nota 6 de funções não prova runtime.
- **Penpot upstream (5,55):** editor 2D robusto e MCP; baixa unificação porque não resolve vídeo/3D.
- **MotionEditor (5,05):** experiência boa no README e integração local; licença não encontrada e Remotion adiciona custo.
- **OpenCut Classic (4,15):** app existente, mas arquivo foi arquivado e README marca export/preview em refatoração.
- **Graphite/Nemo:** potencial 2D/motion, mas alpha e lacunas fora do recorte principal.
- **OpenCut rewrite:** API/MCP/headless são futuros, não pontuados como recursos existentes.

## Sensibilidade

**Velocidade:** pesos alternativos 35/10/10/30/5/5/5 para funções/IA/unificação/velocidade/extensão/estabilidade/licença deixam OpenReel primeiro entre códigos candidatos (7,40); Blender 6,70, FableMint 6,65, Excalimate 6,40. Para usuário final que só precisa terminar vídeo 3D hoje, Blender pode ser mais rápido que integrar editor web; a tabela mede base técnica para Workstation.

**Arquitetura e escala:** pesos 15/20/30/5/15/10/5 mantêm OpenReel como base existente mais equilibrada (7,25), com Penpot+Girafic em 6,20. Uma arquitetura híbrida Hermes, depois de implementada, tem potencial estimado 7,50 usando notas 5/9/8/5/9/6/7; isso é **avaliação potencial**, não score de capacidade atual. Hoje o Hermes Creative Workstation tem zero função criativa implementada. A escolha por horizonte muda de “testar OpenReel para vídeo” para “construir envelope Hermes + módulos especializados”; não muda para “fork do Penpot”.

---

# Parte VI — recomendação final

1. **Projeto mais vantajoso como base:** OpenReel é o candidato de código mais vantajoso para subsistema web vídeo/motion. Não basta para todo Workstation. Blender é base mais completa para arquivo único de 3D+animação+composição+vídeo fora do Hermes.
2. **Existe fork superior ao original?** Nenhum demonstrado para produção. Girafic adiciona timeline no código, mas diverge do Penpot atual. FableMint mostra padrão MCP/JSON de vídeo, mas está desatualizado em relação ao pai. Excalimate é integração estreita de Excalidraw.
3. **Bibliotecas necessárias:** não fixar conjunto antes do PoC. Mínimo provável: editor existente 2D (Penpot), vídeo/motion engine escolhido após teste (OpenReel líder), editor/engine 3D (Babylon/Blender/Three conforme embed), FFmpeg em worker com build/licença controlados, IA especializada isolada em Python. OpenTimelineIO ajuda a trocar montagem NLE; não é documento mestre.
4. **Melhor estratégia de IA:** tools tipadas por domínio/contrato, não tool genérica que altera arrays sem validação. Agente lê estado, propõe diff, executa batch transacional undoable, guarda checkpoint, espera preview/export, coleta evidência e confirma. Adapters Hermes chamam API/MCP local. IA de segmentação/STT/geração produz dados revisáveis e registra modelo/versão/licença/fonte.
5. **Preservar mesmo arquivo:** container .hcw com manifesto comum, media/asset IDs, timebase e subdocumentos nativos, cada um com engine/version/bridge e vínculo de layer. Um pacote único editável é realizável; um modelo universal bidirecional Penpot+NLE+Blender não foi demonstrado.
6. **O que já existe:** design 2D (Penpot/Inkscape/GIMP/Krita), NLE (Kdenlive/Shotcut/Blender/OpenReel), composição 3D (Blender/Babylon/Three), media processing (FFmpeg/MLT/GStreamer), timelines (OpenReel/Motion Canvas/Remotion/Theatre) e IA (SAM2/Whisper/RIFE etc.). Hermes não precisa reimplementar paths, codecs, editor 3D ou STT.
7. **Menos trabalho para resultados utilizáveis:** hoje Penpot + Blender, com Kdenlive/Shotcut para NLE tradicional. Para trazer edição web ao Hermes com menos código repetido, testar OpenReel primeiro; aceitar módulos separados temporariamente.
8. **Melhor potencial longo:** arquitetura híbrida, envelope Hermes e adapters verificáveis. OpenReel é motor candidato, não autoridade de todo projeto; Penpot/Babylon/Blender podem manter formatos nativos.
9. **Não desenvolver do zero:** renderer Bézier sem requisito, timeline NLE básica, codecs, editor 3D, transcrição, segmentation, export PNG/SVG/MP4. Desenvolver envelope, referências, mapping temporal, provenance, policy, review e verificação.
10. **Hipóteses a comprovar:** export determinístico/paridade OpenReel; save/reopen media/relink/offline; MCP que altera e desfaz no mesmo UI state; scene3D com GLB/camera/material/vídeo; build FFmpeg/codec no Windows; integração WebContentsView sem contornar control-plane; migrations Girafic; GPU local SAM2/RIFE/Whisper; licença de cada binário/peso/plugin.

---

# Parte VII — planos de implementação

Planos para execução futura; nada foi executado aqui. Prioridade oficial existente manda resolver primeiro gates upstream/safety/reliability. Roadmap atual descreve CW-03A React/SVG→Electron preview→PNG, CW-03B FFmpeg e CW-03C Remotion após licença; prova OpenReel e licença Remotion devem anteceder fixação de tecnologia.

## Plano de resultado imediato — produzir artes e vídeos

| Etapa | Repositórios/subsistemas | Trabalho | Teste/critério de conclusão |
|---|---|---|---|
| 1. Liberar execução CW no Hermes | Hermes main, gates H-079/H-080/KI e CI vigente | Reconciliar gate no commit exato; não iniciar runtime se baseline continua bloqueada. | CI/segurança no HEAD exato aceitos pelos gates existentes. |
| 2. Design editável | Penpot upstream; Inkscape se SVG/print local bastar | Arte com texto, imagem, formas/grupos; salvar/reabrir; export PNG/SVG. | Teste 1 manual no Windows; texto/grupos/paths editáveis após reload. |
| 3. Composição vídeo/3D | Blender; Kdenlive/Shotcut se NLE sem 3D bastar | Importar vídeo/áudio; cena 3D, títulos; montar composição; render MP4 e manter .blend. | Testes 2–4 e 6; registrar versão, codec e amostra; comparar preview/render. |
| 4. Comparar editor web agente | OpenReel alpha e FableMint; Excalimate para explainers | Executar testes 1–6 em projeto pequeno isolado; coletar projeto, output, diff e logs. | Registrar PASS/FAIL por fluxo, Windows, tempo, relink e divergências. README não conta como aprovação. |
| 5. Adotar vertical | OpenReel se vídeo/motion passar; Excalimate se primeira necessidade for diagrama animado | Usar local/sidecar, sem integrar ainda ao Hermes core. | Usuário cria, agente modifica, humano retoca, exporta e reabre o mesmo projeto. |

**Dependências:** apps e dependências locais, build FFmpeg com licença fixada, projeto de teste e hardware alvo. OpenCut Classic não é dependência recomendada; está arquivado.

## Plano de evolução — Workstation unificado e agentic

| Fase | Dependências/repos | Subsistemas Hermes afetados | Testes/critério de término |
|---|---|---|---|
| 0. Baseline/gates | Hermes main | release, segurança, CI, policies | CW-01 fecha só com audit/hygiene no HEAD; gates atuais passam. |
| 1. Contrato de projeto | RFC .hcw; OpenReel, Penpot, OTIO, glTF, Blender | registry de projetos, ArtifactStore, journal, versioning | Round-trip manifest, hashes, refs, relink, timebase racional, upgrade/downgrade, asset recovery. Sem schema que achate dados. |
| 2. Capability vertical | OpenReel core ou CW-03A/SVG, conforme bateria | operational capability registry, Task Compiler, TaskRun, preview | Testes 1–3 e 5; operação tipada gera diff, artefato e preview/render de verificação. |
| 3. Pipeline de mídia | FFmpeg, WebCodecs/MediaBunny opcional, licença/codec matrix | job worker, UI progress/cancel, ArtifactStore | Testes 3/6 em codecs/resolução Windows; tolerância preview/frame definida; cancel/resume. |
| 4. 3D como subdocumento | Babylon MCP ou Blender Python/headless; Three.js para preview | adapter + child process/MCP + asset bridge | Teste 4 abre mesma cena humana/IA; materiais/câmera/keyframes sobrevivem e render entram como layer. Declarar editável vs render-only. |
| 5. Design 2D como subdocumento | Penpot MCP/plugins; testar embed/route e versioning | Electron surface, file refs, operation adapter | Teste 1; envelope guarda fonte/asset/ids; SVG/PNG pode ser reimportado sem apagar fonte. |
| 6. IA em operações/jobs | Hermes Agent, MCP adapters, SAM2/Whisper/RIFE/modelos aprovados | Task Compiler, policy, capability registry, Experience Compiler | Teste 5 com diff/review/undo/idempotência/proveniência e aprovação para ação destrutiva/serviço externo. |
| 7. Consolidação | CI e benchmarks | Experience Compiler, release, telemetry/docs | Promover capability só após sucesso repetido e validado; testes 1–6 em regressão e comparação de frames. |

**Critério arquitetural:** cada editor continua dono do subdocumento em que tem representação nativa. Hermes é dono de orquestração, vínculos, proveniência, aprovação e verificação. A camada comum representa tempo/assets/composição externa; adapter declara propriedades editáveis após transformação.

---

## Resultado dos seis cenários

Nenhum cenário foi executado. “Há código/feature declarada” não significa “passou a prova”.

| Teste solicitado | OpenReel | Penpot upstream/Girafic | Blender | OpenCut atual |
|---|---|---|---|---|
| 1. Design com texto/imagem/formas/grupos salvar/reabrir PNG | Parcial em código para formas/text/SVG; sem runtime | Upstream completo para design 2D; Girafic altera timeline. Não executado. | Possível em 3D/texto, UX não é design; não executado. | Rewrite não provado; Classic era app, hoje arquivado. |
| 2. Animar design, keyframes, MP4 e projeto editável | Motion composition/clip/export APIs em código; export não comparado | Girafic tem keyframes/export no código; integração real não provada | Keyframes e render existem; não executado | Sem API estável demonstrada |
| 3. Import/corte/texto/áudio/export | Escopo central e handlers em código; não executado | Não | VSE atende em produto; não executado | Rewrite não provado; Classic arquivado/refatoração |
| 4. 3D/material/câmera/keyframe na composição | Scene3D de motion e objetos em código; testar GLB/rig/export | Não | Cena 3D + compositor/VSE; não executado | Não |
| 5. Agente altera projeto e humano continua editando | Host/MCP/actions/transactions documentados; não rodou aqui | MCP/plugins; branch altera ambos; sem prova | Python API permite script; MCP é outra camada | MCP é roadmap na rewrite |
| 6. Reabrir propriedades e preview == export | Storage/autosave e JSON; não comparado | Tests no código do fork; sem execução | .blend mantém cena, roundtrip não executado | Sem garantia demonstrada |

---

# Licenças: interpretação operacional

- **MIT/BSD/Apache-2.0:** geralmente permitem modificar/distribuir preservando copyright/licença; Apache inclui termos de patente/notices. Ainda auditar dependências, fonts, sample media e modelos.
- **MPL-2.0:** copyleft por arquivo coberto; modificar/distribuir Penpot ou MediaBunny exige fornecer fonte das partes cobertas sob termos MPL. Combina melhor com arquivos independentes que GPL, mas não é licença sem obrigações.
- **LGPL:** linking dinâmico e possibilidade de substituir biblioteca importam em distribuição; analisar FFmpeg/MLT/GStreamer modules e build.
- **GPL-3.0/AGPL-3.0:** integrar/distribuir bibliotecas ou aplicações pode exigir fonte correspondente sob os termos; AGPL também trata uso em rede. Blender, Kdenlive, Shotcut, RVM e @theatre/studio precisam de análise antes de integrar. Rodar processo externo não apaga automaticamente obrigações de redistribuição.
- **Licença comercial/SDK:** Remotion e tldraw requerem termos pagos/condições de produto; não chamar de OSS só porque há código no GitHub.
- **Código, binário, codec, modelo e pesos são objetos distintos:** FFmpeg muda de regime por configuração; SAM2 declara checkpoints Apache; rembg documenta licenças próprias dos modelos; OpenPose é não comercial; Demucs tem código MIT, mas não é mantido e weights/datasets precisam de análise separada.

---

# Fontes principais

## Hermes Work

- [Main commit f21e803](https://github.com/kevynlucasprofissional-stack/hermes-agent/commit/f21e803b3525b70ee6be2305e579c1cc1f930e74)
- [Workstation roadmap](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/f21e803b3525b70ee6be2305e579c1cc1f930e74/workstation/ROADMAP.md)
- [Workstation architecture](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/f21e803b3525b70ee6be2305e579c1cc1f930e74/workstation/ARCHITECTURE.md)
- [Source matrix](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/f21e803b3525b70ee6be2305e579c1cc1f930e74/workstation/SOURCE_MATRIX.md)
- [Central workstation intelligence](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/f21e803b3525b70ee6be2305e579c1cc1f930e74/workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md)
- [Creative Workstation CW-01 audit](https://github.com/kevynlucasprofissional-stack/hermes-agent/blob/f21e803b3525b70ee6be2305e579c1cc1f930e74/workstation/creative-workstation/CW01_AUDIT_2026-10-08.md)

## Web editors, repos e forks

- [OpenReel](https://github.com/Augani/openreel-video) · [release alpha.17](https://github.com/Augani/openreel-video/releases/tag/v1.0.0-alpha.17)
- [Penpot](https://github.com/penpot/penpot) · [plugin API](https://help.penpot.app/plugins/) · [Girafic timeline branch](https://github.com/girafic/penpot/tree/girafic-penpot-timeline-animation) · [comparação upstream](https://github.com/penpot/penpot/compare/develop...girafic:girafic-penpot-timeline-animation)
- [OpenCut rewrite](https://github.com/OpenCut-app/OpenCut) · [rewrite tracking issue](https://github.com/OpenCut-app/OpenCut/issues/811) · [OpenCut Classic archive](https://github.com/OpenCut-app/opencut-classic)
- [Excalimate](https://github.com/excalimate/excalimate) · [FableMint](https://github.com/Pheem49/FableMint) · [FableCut pai](https://github.com/ronak-create/FableCut) · [Nemo](https://github.com/mysteropodes/nemo) · [MotionEditor](https://github.com/tomaslachmann/motion-editor)

## 2D, animation e 3D

- [Fabric.js](https://github.com/fabricjs/fabric.js) · [Konva](https://github.com/konvajs/konva) · [Paper.js](https://github.com/paperjs/paper.js) · [SVG.js](https://github.com/svgdotjs/svg.js) · [PixiJS](https://github.com/pixijs/pixijs) · [Excalidraw](https://github.com/excalidraw/excalidraw) · [tldraw license](https://github.com/tldraw/tldraw/blob/main/LICENSE.md) · [Graphite](https://github.com/GraphiteEditor/Graphite)
- [Motion Canvas](https://github.com/motion-canvas/motion-canvas) · [Revideo](https://github.com/redotvideo/revideo) · [Remotion license/pricing](https://www.remotion.dev/docs/license/pricing) · [Theatre.js license](https://github.com/theatre-js/theatre)
- [Three.js Editor](https://threejs.org/editor/) · [Babylon.js Editor](https://github.com/BabylonJS/Editor) · [Babylon MCP contract](https://github.com/BabylonJS/Editor/blob/master/mcp/mcp-tools-contract.md) · [PlayCanvas Editor](https://github.com/playcanvas/editor) · [PlayCanvas MCP](https://github.com/playcanvas/editor-mcp-server)
- [Blender Video Sequencer](https://docs.blender.org/manual/en/latest/editors/video_sequencer/introduction.html) · [OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO)

## Vídeo e IA

- [FFmpeg legal](https://ffmpeg.org/legal.html) · [MLT](https://github.com/mltframework/mlt) · [Kdenlive](https://github.com/KDE/kdenlive) · [Shotcut](https://github.com/mltframework/shotcut) · [WebCodecs](https://developer.mozilla.org/en-US/docs/Web/API/WebCodecs_API) · [MediaBunny](https://github.com/Vanilagy/mediabunny)
- [SAM 2](https://github.com/facebookresearch/sam2) · [Whisper](https://github.com/openai/whisper) · [RIFE](https://github.com/hzwer/ECCV2022-RIFE) · [Robust Video Matting](https://github.com/PeterL1n/RobustVideoMatting) · [rembg](https://github.com/danielgatis/rembg) · [Demucs](https://github.com/facebookresearch/demucs) · [OpenPose license](https://github.com/CMU-Perceptual-Computing-Lab/openpose/blob/master/LICENSE) · [ComfyUI](https://github.com/Comfy-Org/ComfyUI)

**Conclusão de engenharia:** reaproveitar software pronto hoje e preservar liberdade de evolução exige limites honestos de editabilidade. Reutilizar editores especializados e integrar operações verificáveis é mais barato e menos frágil que forçar Penpot, OpenReel ou schema próprio a ser uma engine que nenhum deles já é.
