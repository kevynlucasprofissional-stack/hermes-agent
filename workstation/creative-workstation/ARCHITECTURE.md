# Creative Runtime — arquitetura candidata

**Status: DESIGN PROPOSTO.** Não é uma descrição do que está em produção. Contratos devem ser reconciliados com o código real antes de implementar.

## 1. Limites e proprietários

```text
Hermes Session / TaskRun / Agent / Kanban (existentes)
      |
      v
OperationIntent -> Control Plane Router/Policy/Certificate (existentes)
      |
      v
TaskCompiler / verified execution -> capability adapter (novo, se necessário)
      |                             |                 |
      |                             |                 +--> Creative Project Manifest
      |                             +--> API / MCP / código / CLI
      v
Executor / Kernel / owner evidence / ArtifactStore / Journal (existentes)
      |
      +--> Preview Chromium Electron WebContentsView (surface existente)
      |
      +--> Verified Outcome -> Experience Compiler (existente)
                                      |
                                      +--> candidate / empirical validation /
                                           controlled replay / promotion gates
```

**Proibido:** outro roteador soberano, outro TaskRun, registry de skills executáveis concorrente com OperationalCapabilityRegistry, outro navegador/sessão ou um banco de projetos com autoridade sobre execução. O projeto criativo tem arquivos e referências, não uma segunda identidade operacional.

## 2. Contrato de capability e descoberta

Uma capability criativa é um adaptador de operação sob o Control Plane existente, **não** um agente irmão.

Campos candidatos (a validar na implementação): `capability_id`, `interface_kind` (mcp/api/cli/filesystem/web-bridge), `input_schema`, `output_schema`, `artifact_types`, `provider_ref`, `dependency_refs`, `required|optional`, `health`, `version_fingerprint`, `workspace_scope`, `effect_class`, `confirmation_policy`, `verification_contract`, `cleanup_policy`. Campos são proposta, não novo schema aprovado.

- Descoberta read-only e sem efeitos por padrão.
- Instalação explicitamente confirmada, origem/pin/hash/licença auditados, rollback possível.
- Processos locais loopback-only, porta negociada, token de sessão/nonce, permissões mínimas, nenhum token de MCP ou URL com segredo em logs/renderizações.
- Dados e workers restritos ao projeto/usuário/TaskRun, sem compartilhamento silencioso entre perfis ou conexões.
- `UNAVAILABLE`, `DEGRADED`, `STARTING`, `READY`, `STOPPED`, `UNHEALTHY` são estados **de apresentação propostos**, derivados do owner real; não introduzir segundo lifecycle.
- Em falha de dependência requerida, recusar explicitamente; opcional pode degradar apenas com política aprovada.
- A UI apresenta o processo ativo e a mesma fonte dos arquivos; não produz "verdade" independente de conclusão.

## 3. Creative Project Manifest

Definir um registro versionado e portável do projeto que aponte para originais nativos e artefatos derivados. Exemplo **ilustrativo, NÃO schema final**:

```json
{
  "schema_version": "draft-v0",
  "project_id": "example-brand-intro",
  "workspace_ref": "workspace-scoped-ref",
  "sources": [
    {"kind": "three-scene", "path": "scene.json", "sha256": "<hash>"},
    {"kind": "react-composition", "path": "src/Intro.tsx", "sha256": "<hash>"}
  ],
  "assets": [{"role": "brand-logo", "path": "assets/logo.svg", "sha256": "<hash>"}],
  "outputs": [{"kind": "video/mp4", "path": "renders/intro.mp4"}],
  "pipeline": ["creative.three", "creative.video.encode"],
  "tool_versions": {},
  "provenance_refs": [],
  "editable": true
}
```

Esse manifesto **não** garante conversão sem perdas. Objetos Penpot, React components, SVG e Three scene graph têm semânticas distintas; declaramos transformações explícitas, fidelidade conhecida, limites e rollback. Não colocar credenciais, PII ou URL com bearer token no manifesto.

Projetos ficam no workspace selecionado, arquivos originais versionáveis; outputs derivados recebem hash, tipo, dimensão/duração, dependências e referência de evidência do owner canônico. Mudanças manuais devem gerar nova revisão observável antes da próxima operação de agente para não sobrescrever edições concorrentes.

## 4. Adaptadores por superfície

### Penpot
- Ambiente self-hosted **opcional**, gerenciado segundo documentação/licença/dependências oficiais; remote MCP também pode ser opção configurada pelo usuário.
- MCP oficial vive atualmente em `penpot/penpot/mcp` (antigo `penpot/penpot-mcp` arquivado). Conferir modo de conexão, plugin, permissões e instruções vigentes na versão pinada.
- Nunca tratar plugin MCP com execução de código como seguro por origem: autorização por documento/operação, origem confiável e validação antes de editar.
- Preview no Chromium já existente; inspeção/alteração de componentes/tokens/páginas via contrato tipado.

### Remotion e vídeo
- Agente edita TSX/React/assets, Studio é um preview; render CLI + FFmpeg e provas de arquivo, duração, codec e dimensões.
- Remotion tem licença própria; validar elegibilidade e distribuição antes de admitir como componente. Se não admissível, manter vertical inicial com React/SVG, preview e FFmpeg sem usar Remotion.
- Sem tratar render ou screenshot como garantia da qualidade estética: inspeção visual humana ou oráculo separado para qualidade visual.

### Three.js Editor
- Substrato preferencial de cena 3D web; adapter/fork fino e pinado se os internals do editor exigirem. Não assumir API interna estável ou `window.editor` como contrato público permanente.
- Métodos candidatos: `inspectScene`, `createObject`, `modifyGeometry`, `setMaterial`, `configureLights`, `configureCamera`, `addAnimation`, `importGLB`, `exportScene`, `capturePreview`, `undoTransaction`.
- A bridge deve usar comandos whitelisted, IDs semânticos persistentes, revision checks/optimistic concurrency, operações reversíveis, transações e trilha de efeitos. Evitar JS arbitrário originado de MCP/chat no renderer privilegiado.

### CLI/backends
- FFmpeg: templates de comandos por entrada tipada, allowlist de codecs/paths, timeout, saída com hash e ffprobe.
- Inkscape: SVG/CLI e batch/export; não criar bridge de clicks.
- Blender: `bpy`/headless com scripts auditados e filesystem isolado; usar Three.js para preview de GLB/glTF quando possível.
- GIMP/Krita: adaptadores especializados opcionais; MCP comunitário permanece uma hipótese de compatibilidade e risco, não dependência padrão.
- Graphite: spike separado para inspeção e edição programática de grafos, sem dependência até contrato estável comprovado.

## 5. Integração ao aprendizado

As três camadas não se confundem:
- **Skill (.md + recursos):** instruções; não concede efeito nem verificação.
- **MCP/API/CLI:** ferramentas concretas, com efeitos e credenciais próprias.
- **OperationalCapability:** objeto promovido e executável sob autoridade do Control Plane.

Fluxo: trace/receipts -> candidate -> verifier empírico e controles negativos isolados -> replay controlado -> política de promoção -> registry canônico. Laya/System-1 pode propor famílias/recursos, mas nunca aprovar instalação, mutações, certificação ou promoção.

Antes de executar uma receita aprendida, validar fingerprint de ferramenta/schema/scope/artefatos/versões e entradas. Em drift ou resultado incerto, não repetir mutação; pausar e retornar ao raciocínio autorizado. Respeitar H-080B.3 de prova Electron real.

## 6. Fronteiras de segurança e privacidade

- Não fazer download, `npm install`, `docker compose up`, abrir serviços, rodar código de origem externa ou aceitar licença sem permissão do usuário.
- MCPs de terceiros: pinned, isolados, env allowlist, sem herdar segredos globais; privilégios mínimos para shell/Python, bloqueio de acesso a paths externos.
- WebContentsView é browser existente: não criar novo persistent profile. Respeitar BrowserTask binding, host fencing, request/identity scope e aprovações.
- Lidar com cancelamento/restart: matar subprocessos órfãos, preservar fonte, marcar outputs parciais, recuperar sem reexecutar efeitos incertos.
- Nunca promover capability por sucesso de teste sintético, screenshot autocertificado ou recorrência estatística.
- License gate explícito para GPL/AGPL/MPL/Remotion; imagens/fontes/assets terceiros também sujeitos a licenças próprias.

## 7. Código candidato para investigação (não mandato de edição)

`workstation/capabilities.py`; `workstation/control_plane/{router,contract,dispatcher,verification}.py`; `workstation/task_compiler.py`; `workstation/operational_capabilities.py`; `workstation/experience_compiler/`; `workstation/artifacts.py`; `workstation/browser_runtime.py`; `apps/desktop/electron/`; `apps/desktop/src/`; `workstation/components.lock.json`; `workstation/first_party_seams.json`; `workstation/UPSTREAM_DELTA.md`.

Inspecionar adapters, lifecycle managers e superfícies upstream já existentes antes de escolher novo path. Toda mudança deve reduzir ou justificar seams e produzir testes de owner, não apenas unit tests do adaptador.
