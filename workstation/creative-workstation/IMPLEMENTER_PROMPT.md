# Prompt de handoff para IA implementadora — Creative Workstation

> Use o texto abaixo como instrução inicial em uma sessão que tenha acesso ao checkout/terminal e ao GitHub do fork.

**Repositório:** `kevynlucasprofissional-stack/hermes-agent`.  
**Documento de entrada:** `workstation/creative-workstation/README.md`.  
**Plano executável:** `workstation/creative-workstation/IMPLEMENTATION_PLAN.md`.  
**Estado inicial:** documentação aprovada para investigação; **nenhum runtime criativo está declarado pronto**.

## Sua missão

Implementar progressivamente o Hermes Creative Workstation **sem construir um segundo Hermes**. O produto deve permitir ao agente orquestrar projetos editáveis por APIs/MCP/código/CLI, apresentar Penpot/Remotion/Three.js no Chromium interno quando admissível, renderizar outputs com FFmpeg/engines e eventualmente reutilizar procedimentos certificados via Experience Compiler. Não instalar tudo ao mesmo tempo.

## Ordem estrita: faça nesta sequência

**0. Preparar.** Localize `main` atual e leia `AGENTS.md`, `workstation/AGENTS.md`, `workstation/context/README.md` e a leitura mandatória definida ali, `workstation/context/engineering-journal/CURRENT.md`; em seguida `workstation/creative-workstation/{README,ARCHITECTURE,IMPLEMENTATION_PLAN,INTEGRATIONS}.md`, `workstation/{ROADMAP,SOURCE_MATRIX,ARCHITECTURE}.md`, `workstation/context/{CURRENT_STATE,DECISIONS,HERMES_WORKSTATION_INTELLIGENCE}.md`. Estas são fontes de autoridade, não orientação opcional.

**1. Gate de código, ANTES de editar runtime.** Execute H-079 upstream-first: registre SHA da main e upstream, pin imutável, merge-base, ahead/behind, CI required e seams impactadas; reconcilie e qualifique baseline exato. Se H-080A/H-080B, KI-024 ou gate equivalente bloquear expansão, **não implemente features**. Produza relatório técnico de bloqueios e PR somente documental/evidência; não declare entrega funcional.

**2. Auditar o que existe.** Inspecione processos/apps/Plugin/MCP/skills no Hermes upstream e Workstation, Electron `WebContentsView` Browser, `workstation/control_plane/`, `task_compiler.py`, `operational_capabilities.py`, `experience_compiler/`, ArtifactStore, policy e verificadores. Reuse owners. Anote símbolos e arquivos concretos; nenhum path da proposta é mandato automático de alteração.

**3. Auditar dependências.** Penpot MCP atual em `penpot/penpot/mcp`, remotion-dev/skills e licença atual de Remotion, Three.js Editor, FFmpeg. Fixe SHA, licença, schema, pontos de extensão, dependências, risco de execução de código e testes necessários. MCP comunitário/skill externo só após análise e consentimento. Se Remotion não for legalmente admissível para o cenário de distribuição, implemente a vertical inicial apenas em React/SVG + FFmpeg.

**4. Creative Runtime mínimo.** Aproveite lifecycle/authority existentes para descobrir capabilities, verificar disponibilidade, pedir consentimento de instalação, iniciar/monitorar/parar uma ferramenta e produzir health/status derivados. App manifest tipado com path/hash/version e scopes; nenhuma nova DB ou lifecycle soberano. Projeto editável e outputs rastreados em ArtifactStore/Journal existentes.

**5. Uma vertical real.** Gere e abra no Electron um projeto React/SVG, exporte PNG verificável; depois renderize/valide vídeo vertical com FFmpeg e Remotion somente se license-gated. Exija confirmação humana para mutações sensíveis, evidência real e testes negativos (porta, auth, perfil, encerramento, crash, missing asset, render incorreto). Não pare em mocks.

**6. Edidores:** Penpot via MCP oficial + UI no Chromium; prove que edição humana não é sobrescrita. Depois Three.js Editor com bridge restrita (inspecionar, transformar, material, luz, câmera, importar/exportar/snapshot), IDs semânticos, revisões e rollback. Evite JS arbitrário privilegiado e não assuma estabilidade dos internals.

**7. Expansão separada:** FFmpeg e Inkscape CLI, Blender headless quando justificável; Graphite/áudio/CAD/Godot continuam de pesquisa até prova. Não importá-los como dependências first-party por conveniência.

**8. Reuso:** somente depois de verificar o pipeline, conecte ao Experience Compiler/registry já existentes; candidatos -> validação empírica -> replay -> policy -> promoção. Versões, schemas, identidade e scope compõem fingerprints; drift invalida execução sem reautorização.

**9. Qualificar e entregar.** PRs pequenos por fase, testes em regressão, real Electron, owner receipts, checks no HEAD exato, seam audit, drift snapshot. Atualize roadmap, Source Matrix, DECISIONS (apenas decisões aceitas), CURRENT_STATE, intelligence e journal com SHAs, testes e bloqueios. Não merge automaticamente e não marque H-080 ou capability VERIFIED sem prova.

## Contratos inegociáveis

- Upstream owns sessions/memory/Kanban; Workstation possui semântica operacional mínima.
- Chromium é interface visual, não owner de efeitos. Nunca introduzir outro Browser profile/BrowserTask router.
- Router/Policy/Certificate/Verifier existentes controlam execução; Laya/System-1 não autoriza efeitos.
- Skills não são executáveis certificados; MCP não elimina approval/verification.
- Instalações, portas e credenciais somente com autorização e isolamento; proibir secret leakage.
- UI não pode declarar sucesso antes do efeito verificado.
- Prioridade e bloqueios canônicos prevalecem sobre a lista criativa P0.

## Formato de relatório obrigatório em cada fase

```text
FASE / STATUS: IMPLEMENTED | BLOCKED | PARTIAL | VERIFIED
BASELINE: downstream SHA / upstream pin / CI / seam audit
CHANGES: arquivos, owners e contratos alterados
EXTERNAL: repo/ref/licença/integração verificada
TESTS: comando, ambiente, número real e resultado
EVIDENCE: receipts, artefatos, screenshots, URLs/SHAs, testes negativos
BLOCKERS: motivo e próxima menor ação
UPSTREAM DRIFT: estado e classificação
PR: link, head, merge status
```

Fazer **o máximo seguro dentro do gate atual**, sem pedir permissão repetida para detalhes já definidos; caso falhe um gate, parar a mutação insegura e apresentar resultado útil verificável. Nunca inventar testes, compatibilidade ou instalação.
