# Plano de implementação — Hermes Creative Workstation

## Plano executivo vigente D-041 — priorizar Hermes Workstation (2026-10-09)

**Este bloco substitui a sequência histórica CW-00–CW-07 abaixo para tool selection/priority.** Aquele histórico preserva evidências e requisitos de segurança; não deve ser seguido como ordem de novos editores. Fonte integral: [HYPERFRAMES_ADOPTION_2026-10-09.md](HYPERFRAMES_ADOPTION_2026-10-09.md); execução diretamente delegável: [HYPERFRAMES_IMPLEMENTER_HANDOFF_2026-10-09.md](HYPERFRAMES_IMPLEMENTER_HANDOFF_2026-10-09.md).

| Prioridade | Entrega | Owners / fontes | Aceite indispensável |
| --- | --- | --- | --- |
| P0 | Resgatar draft #57–61, preservar correção nativa local, auditar H-079/CI/seams, pin externo | PR #57–61, contexto canônico, HyperFrames repos | inventário de código/SHAs/locks, não perder trabalho; blocked vs experimental explicitados |
| P1 | HyperFrames Studio servido localmente e embutido no **Chromium atual** | `creative_apps.py`, `creative_process.py`, `creative_runtime.py` (PR #58); `apps/desktop/electron/workstation-browser-runtime.ts`; `packages/studio`, `studio-server` | **M1a**: interação GUI Windows/Electron, health real, token/origin/port/profile/stop/restart |
| P2 | Fonte nativa HTML/CSS/JS/assets + ETag, revisions e PNG/MP4 | `creative_project_store.py`/#59, `creative_video*.py`/#60; HyperFrames file writer/CLI | editar/salvar/reabrir/exportar e decodificar, sem flatten, fonte humana preservada |
| P3 | Bridge de operações criativas do Hermes Agent | Control Plane, TaskCompiler, Browser/Project Store | **M1b**: edit humano → agent → humano e reabertura, conflitos/denials/replay |
| P4 | NLE/design gaps por uso real | HyperFrames primeiro; OpenReel/Diffusion referências | composição com vídeo/áudio/texto editável, testes reais |
| P5 | 3D opcional por demanda | Three.js in HyperFrames; outros adapters separados | GLB/scene/undo/revision real ou bloqueio justificado |
| P6 | Qualificação e Experience Compiler | H-079/H-080/H-081/H-082, owner receipts/verifier | E2E Electron exato, CI/rollback e reuso verificado sem auto-certificação |

**Procedimento:** PR por etapa, RED/green, status e receipts reais. A exceção de desenvolvimento 2026-10-08 permite experimentos P1 isolados mesmo com baseline pendente, **não** libera merge, runtime inseguro, install automático ou bypass do H-079 preflight. Se bloqueado, documentar e continuar apenas tarefas independentes seguras; não encerrar a missão após P0 se P1 experimental for admissível.


**Estado:** BACKLOG PLANEJADO, documentação inicial. **Este arquivo não libera expansão runtime.**
**Autoridade de prioridade:** [../ROADMAP.md](../ROADMAP.md).  
**Pré-condições:** [H-079 upstream-first](../context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md), H-080A/H-080B e bloqueios de [CURRENT_STATE](../context/CURRENT_STATE.md).

## Contrato de execução por fase

**Fontes:** [Execution Brief](EXECUTION_BRIEF.md) para iniciar sem duplicar históricos; [Verification Matrix](VERIFICATION_MATRIX.md) para testes/security/provas; [Phase Prompts](PHASE_PROMPTS.md) para instrução específica. Leitura obrigatória definida por `AGENTS.md` e `context/README.md` não pode ser abreviada por este briefing.

**Estados permitidos:** `PLANNED` (documentado), `BLOCKED` (gate externo), `IMPLEMENTED` (código presente), `INTEGRATION_PASS` (efeito real), `E2E_PASS` (ambiente produto), `QUALIFIED` (gates exatos + efeitos + safety). `DOCUMENTED` não implica `IMPLEMENTED`. Atualizar journal com evidência real, não estados presumidos.

### Unidades de PR e entregas verificáveis

| Unidade | Entra quando | Muda o quê | Só sai quando |
| --- | --- | --- | --- |
| CW-00 | Agora | Documentação e proveniência | Arquivos e links válidos, análise integral preservada, zero runtime |
| CW-01 | Antes de qualquer código | Auditoria upstream/baseline/source/owners | GO/BLOCKED explícito com SHAs, riscos, contratos e CI |
| CW-02 | Gate CW-01=GO | Discovery/health/lifecycle mínimo opt-in | Spawn/stop/rollback/isolamento verificados + testes negativos |
| CW-03A | CW-02 qualificada | React/SVG → Electron preview → PNG | Projeto nativo reabre; PNG e owner receipts reais |
| CW-03B | CW-03A qualificada | FFmpeg/ffprobe tipados | MP4/codec/duração/dimensões/hash e cancelamento verificáveis |
| CW-03C | CW-03A/B + licença admitida | Remotion/Studio opcional | License gate + render/vídeo E2E; caso contrário omitir |
| CW-04 | Vertical + gates | Penpot MCP/UI em PR separado | Humano e agente preservam revisões e escopo |
| CW-05 | Vertical + gates | Three.js Editor/bridge em PR separado | Scene/GLB, revision/undo, comando allowlisted |
| CW-06 | Caso de uso concreto | Adapter Inkscape ou Blender por PR | Outputs e isolamento de cada engine |
| CW-07 | Pelo menos uma vertical qualificada | Experience Compiler existente | Candidate→prova empírica→replay→promote→reuso real sem auto-certificar |

**Sequenciamento:** CW-04 e CW-05 são independentes entre si. CW-07 pode começar depois da **primeira** vertical já comprovada e não exige que Penpot + Three.js + Blender estejam todos prontos. Não realizar deploy automático de ferramentas externas apenas porque são P0.

### Dependência e parada

- Dependência **requerida** indisponível → `BLOCKED` com motivo; sem fallback silencioso.
- Dependência **opcional** indisponível → seguir sem ela somente se o contrato permitir, informando redução de escopo.
- H-079 / CI / segurança / licença vermelhos → bloquear *runtime*; pode continuar evidência/doc do CW-01.
- Toda fase gera um PR com owner alterado, testes determinísticos + negativos, artifact/receipt e rollback. Nada pode ser chamado `QUALIFIED` somente por passar unit tests.

## Estratégia de entrega

Evitar um único PR gigante. Escolher **uma fatia vertical com evidências independentes** antes de adicionar os outros editores. Cada fase tem owner, contrato, aceitação negativa e saída de rollback. Qualificações fora desta fase não podem ser inferidas.

### CW-00 — Documentação e triagem [esta PR]

**Mudanças:** criar `workstation/creative-workstation/`; atualizar as referências canônicas `ROADMAP.md`, `SOURCE_MATRIX.md`, `context/HERMES_WORKSTATION_INTELLIGENCE.md`, `context/CURRENT_STATE.md` e `context/engineering-journal/CURRENT.md`. Registrar princípios em `context/DECISIONS.md` apenas como proposta, não decisão final.

**Aceite:** arquivos presentes, links internos válidos, [dois textos-base completos](research/) acessíveis, propostas/FACT/PARTIAL/NV marcados, docs não afirmam código em execução, zero changes em runtime/deps/CI. Não promover entrega funcional.

### CW-01 — Audit + preflight / gate [BLOCKED até upstream/CI aptos]

**Antes de tocar código**:
1. ler `AGENTS.md`, `workstation/AGENTS.md`, `workstation/context/README.md` na ordem obrigatória; `workstation/context/engineering-journal/CURRENT.md`;
2. executar H-079, registrar DOWNSTREAM_MAIN_SHA, UPSTREAM_MAIN_SHA_OBSERVED, CURRENT_PIN_SHA, merge-base, ahead/behind, required CI e owners/seams afetados;
3. verificar H-080A, H-080B.3, KI-024 e eventuais bloqueios P0: se algum gate de mudança estiver vermelho, não iniciar expansão funcional;
4. pesquisar implementação existente de adapter/plugin/process lifecycle, MCP hub, Electron Browser, skills, ArtifactStore e operational registry, sem criar duplicatas;
5. inspecionar refs/licenças/versionamento (não só README) de Penpot/Remotion/Three/FFmpeg; atualizar Source Matrix como FACT/PARTIAL/NV.

**Aceite:** documento de auditoria com caminhos/símbolos reais, refs pinadas, contratos reutilizáveis, falhas e riscos; baseline exato qualificado; implementação permitida pela política. Se bloqueado: produzir relatório e parar mudanças funcionais.

### CW-02 — Creative Runtime mínimo (modelo de app, não novo lifecycle)

**Prováveis pontos de leitura:** `workstation/capabilities.py`, `control_plane/`, `operational_capabilities.py`, `workstation/health.py`, `workstation/host.py`, `apps/desktop/electron/`, `workstation/components.lock.json`.

Implementar a menor extensão necessária para: descobrir engine/capability; detectar instalação; exigir consentimento; iniciar/inspecionar/parar processo autorizado com lock de porta e owner scoped; reportar saúde/status derivados; preservar e recuperar workspace e outputs. App manifesto versionado e tipado, sem banco/profiling paralelo. A instalação fica separada da descoberta e não executa código remoto implicitamente.

**Teste:** unit contrato + processo fake, falha de instalação, porta ocupada, timeout, cancelamento, troca de perfil, restart, env secret leak, falha requerida sem fallback inseguro. **Aceite:** processo acessível apenas no escopo autorizado e encerrado sem órfãos, health receipt real, UI/status coerentes.

### CW-03A/B/C — Primeiro fluxo criativo ponta a ponta

**Subfases independentes:** CW-03A gera/abre PNG com React/SVG; CW-03B codifica vídeo via FFmpeg; CW-03C integra Remotion **somente após aprovação do cenário de licenciamento**. Cada subfase tem seu próprio PR, testes e rollback; o uso de FFmpeg não depende do Remotion.

Preferir **React/SVG -> preview no Chromium -> imagem estática verificada**, e **FFmpeg** para encodar assets de teste; adicionar Remotion depois do license gate.

Se elegível, evoluir para `TSX -> Remotion Studio -> CLI render -> FFprobe`; manter fontes e renders ligados ao Creative Project Manifest. Não aceitar saída apenas porque CLI retornou exit 0; validar arquivo real, duração/dimensões, codec e capturar preview como evidência distinta.

**Teste de prova:** gerar convite com logo/texto/paleta, renderizar PNG; variá-lo; opcional MP4 vertical de 8s; verificar métricas/artefatos; fechar/reabrir o app e restaurar projeto. Reproduzir entrada malformada, asset ausente, falha de render e efeitos incertos. Medir chamadas LLM, tempo, custo e resultados apenas quando há dados reais.

**Aceite:** demonstrar resultado no **Electron/Chromium real**, não somente jsdom/node mock, com artefatos reproduzíveis e rastreáveis; sem interferir com BrowserTask do usuário.

### CW-04 — Penpot: design compartilhado humano/agente

Investigar self-host vs MCP remoto, plugin MCP atual do monorepo, autorização/keys e política de escopo. Instalar somente mediante consentimento. Expor operações tipadas de tokens, frames/componentes, alteração, leitura e exportação; preview em WebContentsView existente.

**Teste de prova:** agente cria layout, humano edita texto no Penpot, Hermes atualiza outro elemento preservando alteração humana; detectar revisão conflituosa e pedir reconciliação. **Aceite:** referência do design preservada, evidência de leitura após efeito, sem sobrescrever edição concorrente.

### CW-05 — Three.js Editor: preview 3D agentic

Inicialmente engine Three.js + cena JSON/código. Só forkar editor se a bridge tipada não puder ser implementada de forma estável como adapter fino. Métodos mínimos: inspect/add/transform/material/light/camera/import/export/snapshot/undo. Fixar Three.js SHA e testar mudança de versão.

**Teste de prova:** gerar logo 3D, inspecionar objeto por ID semântico, alterar luz manualmente no editor, agente modifica câmera, reabrir cena, exportar GLB e validar integridade. **Aceite:** edits humanos preservados, transações e rollback, sem injeção arbitrária em Electron privilegiado.

### CW-06 — Engines de extensão

Prioridade: **Inkscape CLI** (SVG/export) -> **Blender bpy/headless** (modelagem/render) -> GIMP/Krita opcionais. FFmpeg faz parte da vertical mínima. Cada adapter deve possuir versão, health, isolamento, IO schema, recibo e teste independente; MCP comunitário pode permanecer opt-in.

**Aceite:** prova operacional real de cada motor antes de anunciá-lo como suportado. Integração futura de Graphite depende de um spike de edição de grafos/versionamento/exportação; áudio, CAD, Godot e creative coding ficam em backlog.

### CW-07 — Experience Compiler com capabilities criativas

Usar os owners `workstation/experience_compiler/`, `workstation/operational_capabilities.py`, policy/verifier existente, sem nova store. Capturar invocações e artefatos; registrar candidates; validar com recibos externos e negativos em sandbox; controlled replay; promover apenas por policy.

**Teste de prova:** primeira execução validada vs repetição parametrizada; drift de versão/schema/scope bloqueia reuse; resultado incerto não desencadeia retry mutante. Comparar cost per verified outcome onde telemetria for completa.

**Aceite:** segunda execução realmente resolve pela rota certificada, respeita risco/autoridade e fornece evidência com menor ou igual custo observado; não depender de auto-certificação.

## Qualidade e segurança — oráculos obrigatórios

Usar [VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md) como check list de falsificação por etapa (S-01 consentimento; S-02 isolamento/processo; S-03 integridade/revisões; S-04 supply chain/licença; S-05 aprendizado).

**DoD por PR:** 1) owner/arquivo/símbolo real e scope; 2) contrato de entrada/saída e segurança; 3) teste happy path e ao menos teste negativo para cada domínio afetado; 4) receipt/readback externo e artefato real; 5) cancelamento/restart/drift se aplicável; 6) regressões + Electron E2E para UI; 7) CI HEAD exato, seam audit e upstream drift; 8) relatório/rollback. Se alguma prova é inviável, registrar `NOT_RUN` ou `BLOCKED`, não preencher PASS por intenção.

## Ordem / dependências

```text
CW-00 (docs)
   -> CW-01 (H-079 + baseline gates + license/source audit)
   -> CW-02 (capability app contract)
   -> CW-03A (React/SVG + preview Electron + PNG)
   -> CW-03B (FFmpeg/ffprobe)
   -> CW-03C (Remotion somente após licença, independente)
   +-> CW-04 Penpot (PR próprio após vertical)
   +-> CW-05 Three.js (PR próprio após vertical)
   +-> CW-06 engines sob demanda
   +-> CW-07 aprendizado/reuso (após primeira vertical qualificada)
```

CW-04 e CW-05 podem ter PRs independentes após a vertical e os gates; não colocar ambos e CW-07 num patch só.

## Qualificação e rollback por PR

- Antes/depois: mesmos owners, baseline e head exatos; testes próprios, regressões Workstation, Desktop typecheck e Electron E2E quando afetado.
- A cada mutação: verificar mecanismo/receipt, autoridade explícita e efeitos reais; testes negativos de usuário, perfil, path, porta, auth e versão.
- Feature flag desabilitada por padrão nas primeiras integrações; rollback limpa processos mas não destrói projetos.
- Final upstream drift snapshot e seam audit; atualizar `UPSTREAM_DELTA.md` + `first_party_seams.json` se forem necessárias seams.
- Registrar em engineering-journal hipóteses/falsificadores/resultados **antes** do experimento; não chamar plano de CI PASS.
- Somente entregar PR para review; não realizar merge automático nem marcar H-080/H-079 como completos sem evidência.

## Riscos / não objetivos

Não criar editor gráfico novo na V1; não garantir conversão sem perdas entre formatos; não instalar todos os softwares por padrão; não importar projetos GPL/AGPL inteiros; não substituir os owners atuais de Browser, TaskRun, policy ou registry; não tentar adaptar n8n/Dify/Langflow como coração do Creative Workstation.
