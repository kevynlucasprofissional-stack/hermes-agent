# Registro da análise original — Hermes Creative Workstation (2026-10-08)

**Origem:** análise e recomendações apresentadas na conversa do usuário em 2026-10-08, incluindo os sete arquivos Markdown discutidos. **Natureza:** registro curado, com elementos de interface/citações temporárias removidos; preserva a substância, as propostas, classificações e ressalvas, mas não substitui o texto integral da conversa como transcrição literal. Para decisões normativas consulte os arquivos superiores e documentos canônicos.

## Tese

Hermes Work não deve replicar monoliticamente Photoshop, After Effects, Blender ou Cinema 4D: deve tornar-se um workstation criativo em que o agente cria, modifica, visualiza e reutiliza projetos sobre engines especializadas.

Três superfícies centrais:
1. **Penpot** — design estruturado, layout, design system, MCP oficial e self-host.
2. **Remotion** — motion graphics/vídeo via React/TSX/CLI com interface Studio. Skills oficiais.
3. **Three.js Editor** — 3D, cenas interativas, editor incorporável e bridge própria.

Blender, Inkscape, GIMP e FFmpeg são motores complementares, não exigem superfície Electron própria. "Capabilities criativas instaláveis" são mais valiosas que apenas registrar softwares.

## Ranking debatido

| Ferramenta | Prioridade | Integração debatida | Avaliação |
| --- | --- | --- | --- |
| Penpot | P0 | MCP oficial + interface web | integrar |
| Remotion | P0 | Skills + React/CLI + Studio | integrar condicionado à licença |
| Three.js Editor | P0 | código + bridge + Chromium | integrar |
| FFmpeg | P0 | CLI + operações tipadas | engine |
| Inkscape | P1 | SVG/CLI; MCP opcional | integrar |
| Blender | P1 | Python/headless + MCP | integrar |
| Graphite | P2 | editor web + pesquisa de API node graph | laboratório |
| GIMP | P2 | Python/PDB + MCP | opcional |
| Krita | P2 | Python + MCP | opcional |
| Tone.js/Strudel | P2 | JS/browser | áudio futuro |
| PartMode/replicad | P3 | MCP / TS API | CAD futuro |
| Godot | P3 | MCP + CLI/editor | games futuro |
| PixiJS/p5.js | P3 | código/browser | creative coding |
| Scribus | P3 | scripts/CLI | publishing |
| Blockbench/SculptGL | baixa | web/plugin | não priorizar |

Prioridade é recomendação estratégica, não gate de merge nem maturidade técnica. Nem tudo deve ser um aplicativo instalado; operações determinísticas via filesystem, APIs e CLI frequentemente são melhores.

## MCPs discutidos

**Oficial:** Penpot; **nativo/documentado:** PartMode (com cautela sobre serviço hospedado/autenticação). **Comunitários:** Blender, Inkscape, GIMP, Krita, Remotion, Godot. **Sem MCP oficial confirmado:** Three.js Editor, Graphite, Tone.js/Strudel. Em replicad/JSCAD a API JavaScript direta é preferível ao MCP. Não presumir segurança, suporte, licença ou compatibilidade apenas porque existe repositório MCP.

O n8n foi citado como serviço de automação externo, com entrada MCP opcional documentada no Hermes; não deve virar novo motor interno nem substituir o Experience Compiler.

## Skills discutidas

- `remotion-dev/skills` oficial: guidelines, create, studio, render, captions, animação.
- `penpot/penpot-ai-kit` oficial: workflows, tokens, componentes, design systems, auditorias e referências compartilhadas.
- `noklip-io/agent-skills` comunitário: Three.js/React Three Fiber/shaders.
- `libevm/agent-skills` comunitário: Blender Python API.
- `eXodes/skills-workspace` comunitário: Strudel/música procedural.

Skill é instrução versionável, MCP é interface de ferramentas, OperationalCapability é competência executável certificada. Uma não substitui a outra.

## Arquitectura candidata

```text
HERMES WORK (Agent + TaskCompiler + Control Plane)
          |
    Creative Capability Router (extensão aos owners existentes)
          |            |              |
       Penpot        Remotion      Three Editor
      MCP/web       React/CLI       bridge/web
          |            |              |
          +--- specialized engines ---+
              FFmpeg, Inkscape, Blender,
              GIMP, Tone.js
          |                         |
   Browser Chromium           Verified effects
   visual / human edit        ArtifactStore / Journal
          \                         /
           +--- Experience Compiler
                     |
                 verified reusable capability
```

A interface Chromium deve mostrar o mesmo projeto editável que o agente modifica. Controle determinístico via API/MCP/CLI é preferível a cliques. Documento fonte é mais importante que um PNG; Creative Project Manifest registra referências, parâmetros, assets, versões e outputs sem prometer conversão lossless.

Exemplo de mesmo projeto: post 1080x1350, story vertical, Reels Remotion, logo Three.js, variações de copy, revisão Penpot. Transformações Penpot -> SVG -> React/Remotion têm limites semânticos reais.

## Graphite

Graphite é interessante para gráficos procedurais 2D por node graph, vetores/raster, Rust e licença MIT/Apache-2.0. Não é substituto de produção para Penpot antes de provar API de grafos, alteração programática, render, export e estabilidade. A proteção separada de branding e assets também importa.

## Three.js de outra forma

Não construir um MCP genérico primeiro. Usar Three.js e o editor oficial com uma bridge tipada com inspeção, criação/remoção, transformações, materiais, luz/câmera, import/export, animação e undo. Manter fork fino com revisão pinada e testes para internals; objetos com IDs semânticos. Theatre.js foi citado como hipótese opcional para keyframes, não core.

## Experience Compiler

Primeira requisição de logo 3D de oito segundos: LLM constrói cena, compõe vídeo, testa/inspeciona render. Em seguida o Hermes registra a execução, candidato parametrizável, dependências e verificadores. Só depois de teste empírico, negativos, replay e promoção canônica passa a reexecutar a operação sem refazer toda a descoberta por LLM. Drift de versão, schema ou scope impede reuse inseguro.

Evitar confundir trace observado e procedimento confiável: qualidade de saída visual precisa de oráculo apropriado e eventualmente revisão humana.

## Licença, segurança e estratégia

Remotion **não** é uma dependência open source irrestrita: licenciamento especial por tipo de organização e uso/distribuição. Penpot MPL, Three.js MIT, Graphite MIT/Apache, Blender/GIMP/Inkscape GPL, PartMode AGPL; conferir builds, plugins, codecs e assets. MCPs comunitários com execução arbitrária de scripts têm blast radius elevado. Isolamento/escopo, pin, env allowlist, aprovação, portas loopback, imagem/artifact verification e rollback são essenciais.

Fases propostas:
1. Creative Runtime manifesto/lifecycle/health.
2. Núcleo Penpot + Remotion + Three.js + preview e edição humana.
3. FFmpeg, Inkscape, Blender e operações estruturadas.
4. Recipes e capabilities verificadas via Experience Compiler.

O refinamento de implementação posterior separou documentação, gate upstream-first, vertical React/SVG + FFmpeg, editores visuais e aprendizagem. **O roadmap Workstation atual é autoridade sobre ordem real**, inclusive blockers H-080A/H-080B e safety. Nenhuma integração está declarada implementada apenas por este registro.

## Conclusão registrada

A maior oportunidade é um workspace em que pessoa e Hermes compartilham a fonte do projeto, cada um com seu mecanismo de edição e verificação, e o sistema aprende apenas aquilo que foi externamente validado. Integração de vinte ferramentas antes de uma vertical real aumentaria dívida e risco.
