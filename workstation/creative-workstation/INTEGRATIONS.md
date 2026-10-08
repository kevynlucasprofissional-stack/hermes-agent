# Integrações e skills — catálogo de descoberta

**Data-base da pesquisa:** 2026-10-08. **Importante:** nomes e links são candidatos; existência de integração pública não prova funcionamento no Hermes fork. Fixar commits e auditar código/licença antes de instalação. O registro oficial de referências e decisão de adoção é [SOURCE_MATRIX.md](../SOURCE_MATRIX.md).

## Matriz de ferramentas

| Prioridade | Engine/ferramenta | Interface pretendida | MCP | Skill | Licença/risco | Estado |
| --- | --- | --- | --- | --- | --- | --- |
| P0 | Penpot | web + MCP oficial | oficial | Penpot AI Kit (licença separada) | Core MPL-2.0; AI Kit CC-BY-4.0; plugin executa código | PARTIAL (compatibilidade NV) |
| P0 | Remotion | código TSX, Studio, CLI | comunitário opcional | oficial remotion-dev/skills | licença própria; product/distribution gate | PARTIAL |
| P0 | Three.js Editor | app web, bridge tipada, scene JSON | oficial não confirmado | comunitárias | MIT; editor internals instáveis | PARTIAL |
| P0 | FFmpeg/ffprobe | CLI tipada | não necessário | própria futura | LGPL/GPL conforme build/codec | PARTIAL |
| P1 | Inkscape | SVG + CLI | comunitário | não validada | GPL | PARTIAL |
| P1 | Blender | Python bpy + headless | comunitário | comunitária | GPL | PARTIAL |
| P2 | Graphite | web/node graph | oficial não confirmado | não validada | MIT/Apache-2.0 (assets/branding separados) | PESQUISA |
| P2 | GIMP | PDB/Python/GEGL | comunitário | não validada | GPL | PESQUISA |
| P2 | Krita | Python/Qt/CLI | comunitário | não validada | GPL | PESQUISA |
| P2 | Tone.js / Strudel | JS/browser | oficial não confirmado | Strudel comunitária | conferir por pacote | PESQUISA |
| P3 | PartMode | CAD web/agente | nativo/documentado (modo hospedado deve ser conferido) | não validada | AGPL-3.0 | PESQUISA |
| P3 | replicad / JSCAD | bibliotecas JS | desnecessário para V1 | não validada | conferir ref | PESQUISA |
| P3 | Godot | CLI/editor | comunitário | não validada | MIT (core) | PESQUISA |
| P3 | PixiJS / p5.js | JS/browser | desnecessário para V1 | não validada | conferir por pacote | PESQUISA |
| P3 | Scribus | script/CLI | não confirmado | não validada | GPL | PESQUISA |
| baixa | Blockbench/SculptGL | plugin/web | não priorizado | não validada | conferir ref/manutenção | NÃO PRIORIZAR |

## Distinção de licenças por camada

- **Penpot core/server/editor:** MPL-2.0 conforme versão, com obrigações sobre arquivos modificados relevantes.
- **Penpot AI Kit (skills/workflows):** repositório oficial `penpot/penpot-ai-kit` informa licença **CC-BY-4.0** na metadata GitHub, confirmada durante a revisão documental de 2026-10-08. Essa licença **não é automaticamente a licença do Penpot core**. Conferir LICENSE, fontes/assets compartilhados e atribuição antes de copiar ou redistribuir o kit; autorização da instalação não dispensa atribuição.
- **Remotion e pacote de skills:** separar licença de código, serviços, templates e materiais; não presumir que a licença do repo de skills conceda direito de redistribuir o Remotion engine.
- **FFmpeg:** revisar licença da build binária específica, incluindo codecs/flags; a licença do projeto genérico não comprova redistributabilidade da build escolhida.
- **Graphite e PartMode:** verificar código, dependências e termos de branding, plugins e execução via rede no pin exato.

Licenciamento é um **gate de admissão**, não uma observação superficial em README. A [matriz de segurança e verificação](VERIFICATION_MATRIX.md) exige decisão por cenário de uso/distribuição.

## Fontes e pontos de entrada

### MCPs
- Penpot oficial: https://help.penpot.app/mcp/ ; código atual https://github.com/penpot/penpot/tree/develop/mcp (antigo https://github.com/penpot/penpot-mcp está arquivado).
- PartMode: https://github.com/BOMWiki/partmode ; comprovar client auth/transporte/headless antes de afirmar MCP self-hosted.
- Blender comunitário: https://github.com/ahujasid/mcp-for-blender .
- Inkscape comunitário: https://github.com/jjjsood/inkscape-mcp-server .
- GIMP comunitário: https://github.com/TwelveTake-Studios/gimp-studio-mcp .
- Krita comunitário: https://github.com/SanSaSane/krita-mcp .
- Remotion comunitário: https://github.com/PratyushChauhan/remotion-mcp-server ; **não necessário** para editar projeto React diretamente.
- Godot comunitário: https://github.com/Coding-Solo/godot-mcp .

### Skills (candidatas, não instaladas nesta PR)
- Remotion oficial: https://github.com/remotion-dev/skills — composição, Studio, render, legendas, melhores práticas. Conferir as skills atuais no ref pinado; não assumir toda a lista da conversa como presente.
- Penpot AI Kit: https://github.com/penpot/penpot-ai-kit — skills/workflows/policies e referências compartilhadas; **CC-BY-4.0** (repositório oficial). Instalar preservando dependências e atribuição.
- Three.js community: https://github.com/noklip-io/agent-skills — verificar path de SKILL.md e compatibilidade antes de sugerir comando `hermes skills install`.
- Blender bpy community: https://github.com/libevm/agent-skills/blob/main/skills/blender/SKILL.md .
- Strudel community: https://github.com/eXodes/skills-workspace — confirmar skill/caminho no ref.

### Engines/docs/licenças
- Three.js Editor: https://threejs.org/editor/ ; https://github.com/mrdoob/three.js/tree/master/editor .
- Remotion licença: https://github.com/remotion-dev/remotion/blob/main/packages/core/LICENSE.md .
- Graphite código/licença: https://github.com/GraphiteEditor/Graphite ; marca/assets têm termos separados: https://graphite.art/license/ .
- FFmpeg licenciamento: https://ffmpeg.org/legal.html .
- Blender Python API: https://docs.blender.org/api/current/ .
- Penpot self-host: https://help.penpot.app/technical-guide/getting-started/ .

## Evidência mínima para aprovar uma integração

1. Repositório e SHA exatos, licença da versão e dependências; classificá-lo no Source Matrix.
2. Teste em perfil/ambiente isolado: instalação manual/opt-in, bootstrap, health, restart, shutdown e rollback.
3. Ferramentas disponíveis no MCP em runtime real, schema inspectado, env allowlist e variações de autorização.
4. Se for skill: path SKILL.md, recursos associados, interface de instalação Hermes no HEAD atual, fontes confiáveis e confirmação explícita.
5. Verificador de efeitos/arquivos, teste de falha negativa e compatibilidade Windows + Electron quando usada interface.
6. Custo de manutenção: upstream drift, licença redistributiva e impacto sobre first-party seams.
7. Resultado declarado como FACT/PARTIAL/NV, sem transformar catálogo em promessa de suporte.

## Regras de decisão

- Preferir API/CLI nativa quando ela é melhor que MCP. MCP não deve ser requisito universal.
- Não duplicar engines: PhotoGIMP é conveniência de GIMP, não capability adicional. Dify/Langflow/n8n ficam fora do core criativo; n8n já aparece como MCP opcional no Hermes.
- Graphite e PartMode permanecem referência/experimento, não bloqueiam a stack P0.
- Nenhuma skill/MCP externo fornece por si só authority, controle de risco ou certificação. Todo efeito obedece owners Hermes.
