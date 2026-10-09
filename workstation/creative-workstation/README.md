# Hermes Creative Workstation

## ATUALIZAÇÃO CANÔNICA — 2026-10-09 (D-041, HyperFrames-first)

**Esta é a direção atual do produto.** A seção de "superfícies prioritárias" de 2026-10-08 **abaixo é histórica/superada**: HyperFrames Studio auto-hospedado é o **único editor-base padrão** a ser lançado dentro do Chromium/Electron do Hermes Work; OpenReel e Diffusion Studio são **referências**, não editores padrão. Remotion #61 preservado/pausado; Penpot e Three.js opcionais posteriores. Reaproveitar a infraestrutura existente dos PRs draft #58–#60, sem presumir que foram incorporados à main.

**Leia agora** [especificação D-041](HYPERFRAMES_ADOPTION_2026-10-09.md) e [prompt executor P0–P6](HYPERFRAMES_IMPLEMENTER_HANDOFF_2026-10-09.md) em vez da instrução histórica "Execute somente CW-01". Marcos M1a (Studio real no Hermes) e M1b (projeto único editável humano/IA + PNG/MP4 verificados). **Não implementado/qualificado ainda**. Leitura canônica obrigatória, H-079/CI/segurança e ausência de merge automático permanecem. Estudos e documentos CW anteriores são fontes históricas de contratos, não ordens concorrentes.


> **Status (2026-10-08): PROPOSTA DOCUMENTADA / IMPLEMENTAÇÃO NÃO INICIADA.**
> Esta pasta descreve uma iniciativa futura subordinada aos gates canônicos do Hermes Workstation. Sua existência não comprova a instalação, integração, disponibilidade, teste ou certificação de nenhuma engine criativa.

## Tese e objetivo

O Hermes Work deve orquestrar projetos criativos **editáveis, observáveis, versionáveis e reutilizáveis**, sem reproduzir Photoshop, After Effects ou Blender como aplicações monolíticas. O agente controla operações estruturadas via APIs/MCP/código/CLI; a pessoa revisa e edita nos aplicativos web apresentados pelo Chromium integrado; ambos referenciam a mesma fonte de projeto, preservando a autoridade dos proprietários reais de estado.

**Superfícies prioritárias (P0 de produto, não autorização para iniciar código):**
- **Penpot:** layouts, componentes e design systems; MCP oficial e interface web; implantação self-hosted opcional.
- **Remotion:** vídeo e motion por React/TypeScript e CLI, preview via Studio; uso condicionado a uma avaliação de licença antes de qualquer integração de distribuição.
- **Three.js Editor:** cenas 3D e prévia web; código/scene graph e um adaptador tipado próprio, não movimentos arbitrários do mouse.
- **FFmpeg:** codificação e composição de mídia, exposta por operações tipadas e parâmetros validados.

**Engines especializadas posteriores:** Inkscape CLI/SVG, Blender Python/headless, GIMP/Krita; pesquisa opt-in em Graphite; Tone.js/Strudel, PixiJS/p5.js, Godot, CAD/PartMode/replicad somente se casos de uso justificarem.

## Entrada rápida para implementação

**A melhor primeira mensagem é CW-01 (preflight, sem código).** Não envie ao agente o histórico integral como prompt: use o [briefing compacto](EXECUTION_BRIEF.md), o [prompt principal](IMPLEMENTER_PROMPT.md) e, depois, o [prompt da fase autorizada](PHASE_PROMPTS.md). O [plano](IMPLEMENTATION_PLAN.md) define o que produzir; a [matriz](VERIFICATION_MATRIX.md) define como provar. As leituras mandatórias em `AGENTS.md` e `workstation/context/README.md` **continuam obrigatórias**.

O debate original foi preservado em dois documentos de pesquisa sem autoridade normativa: [análise completa](research/2026-10-08-full-analysis.md) e [proposta documental completa](research/2026-10-08-full-documentation-proposal.md). A [síntese curada](research/2026-10-08-original-analysis.md) continua disponível para navegação rápida. A transcrição textual normaliza escapes e omite apenas chips/favicons de UI; o conteúdo técnico, exemplos, tabelas e ressalvas permanecem.

## Onde começar

| Documento | Responsabilidade |
| --- | --- |
| [EXECUTION_BRIEF.md](EXECUTION_BRIEF.md) | Resumo operacional de entrada, com dependências e status, sem reler todo o histórico |
| [VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md) | Evidência, testes negativos, segurança, rollout e promoção |
| [PHASE_PROMPTS.md](PHASE_PROMPTS.md) | Instruções enxutas por etapa, a usar após os gates |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Limites, proprietários de estado, fluxo de execução e modelo de projeto |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Ordem executável, responsáveis por subsistema, testes, gates e critérios de aceite |
| [INTEGRATIONS.md](INTEGRATIONS.md) | Candidatos, integração, licenças, MCPs, skills, links e nível de evidência |
| [IMPLEMENTER_PROMPT.md](IMPLEMENTER_PROMPT.md) | Briefing curto, autocontido e sequencial para uma IA implementadora |
| [research/2026-10-08-original-analysis.md](research/2026-10-08-original-analysis.md) | Síntese curada da análise anterior |
| [research/2026-10-08-full-analysis.md](research/2026-10-08-full-analysis.md) | Texto-base completo da análise (sem itens temporários de UI) |
| [research/2026-10-08-full-documentation-proposal.md](research/2026-10-08-full-documentation-proposal.md) | Texto-base completo da proposta de documentação |
| [../ROADMAP.md](../ROADMAP.md) | **Única fonte de verdade para prioridade e liberação da iniciativa** |
| [../SOURCE_MATRIX.md](../SOURCE_MATRIX.md) | **Único registro canônico de referências externas** |

## Princípios de implementação

1. **Upstream-first.** Antes de tocar código, executar [H-079](../context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md) e qualificar o baseline exato. Sem contornar H-080A/H-080B ou os bloqueios P0 em [CURRENT_STATE](../context/CURRENT_STATE.md).
2. **Sem autoridades paralelas.** Não criar outro SessionDB, Kanban, Memory, BrowserSessionState, Approval, ExecutionJournal, ArtifactStore ou OperationalCapabilityRegistry.
3. **Chromium é superfície visual, não motor primário da automação.** Preferir operações tipadas, APIs/MCP, filesystem e CLI. Browser automation é fallback quando essencial.
4. **Instalação opt-in.** Detectar capacidades e verificar requisitos sem baixar, executar serviços, vazar credenciais ou instalar terceiros automaticamente.
5. **A imagem final não é o projeto.** Preservar a fonte editável (Penpot file, TSX, scene JSON, GLB, .blend conforme aplicável) e um manifesto com referências e proveniência, sem reivindicar conversão lossless entre formatos.
6. **Verificação antes da aprendizagem.** Skill instrui; MCP fornece operações; capability certificada exige provas externas, versão/scope e política de promoção canônica do Experience Compiler.
7. **Licenças e segurança explícitas.** Código aberto não implica MIT. Remotion tem licença própria. MCPs que executam código e apps servidos localmente exigem isolamento, autoridade e auditoria.
8. **Escopo incremental:** documentar -> investigar contratos existentes -> provar vertical mínima -> estender editores -> integrar aprendizado. Nenhuma P0 criativa prevalece sobre P0 de confiabilidade.

## Caso de uso demonstrativo

> Crie uma logo 3D vertical de oito segundos com luz dramática e entregue um MP4 mais o projeto editável.

Fluxo desejado, **não implementado**:
`OperationIntent -> Router/Policy -> TaskCompiler -> Three.js scene -> preview Chromium -> Remotion/FFmpeg -> verificação de render/artefato -> accepted outcome -> Experience Compiler candidate -> validação/replay/promoção -> eventual reuso`.

Um único fluxo não prova interoperabilidade geral. Cada transição tem contrato, capacidade efetiva e verificador explícito.

## Estado, prova e governança

- **FACT**: arquivo/função/teste inspecionado ou documentação oficial referenciada com link e ref.
- **PARTIAL**: interface conhecida, mas compatibilidade no Hermes ainda não verificada.
- **NV**: não verificado; nunca converter NV em AUSENTE.
- **PROPOSED**: decisão de produto para experimentação, não arquitetura qualificada.
- **IMPLEMENTED / VERIFIED / QUALIFIED**: somente com commit, testes, recibos e gates reais.

O código do Hermes e seus documentos canônicos permanecem autoridade. Para começar uma tarefa, leia [AGENTS.md](AGENTS.md), depois [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).
