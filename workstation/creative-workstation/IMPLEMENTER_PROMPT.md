# Hermes Creative Workstation — prompt mestre de execução após CW-01 (atualizado 2026-10-08)

> **Use este prompt para uma IA com acesso ao checkout e ao GitHub.** A CW-01 já foi auditada: `BLOCKED`. Não gastar uma nova sessão produzindo a mesma auditoria. O primeiro reparo é **R1: paridade do extra Laya na Workstation CI**. Este documento dá a ordem e os caminhos; a autoridade normativa permanece em `AGENTS.md`, `workstation/AGENTS.md`, `workstation/context/README.md`, H-079 e nos gates de teste.

## Missão

Desbloqueie a base do fork `kevynlucasprofissional-stack/hermes-agent` e avance incrementalmente até o Creative Workstation, permitindo criar/editar/reabrir projetos por humano e agente, visualizá-los no Electron/Chromium, exportar outputs de imagem/vídeo e futuramente reutilizar capacidades verificadas pelo Experience Compiler. **Nenhum merge automático no main; PR isolado por reparo/fase; nenhum runtime criativo declarado qualificado sem prova real.**

### Fatos iniciais a confirmar, não assumidos eternamente

- Baseline observado: `main@f21e803b3525b70ee6be2305e579c1cc1f930e74`, Laya branch D-038/D-039 **já integrada** (notas antigas de branch “not merged” são históricas).
- PR #52 `codex/creative-cw01-refresh-20261008@989e4aabd033` estava aberto e sem merge; seu relatório `workstation/creative-workstation/CW01_REFRESH_2026-10-08.md` não está em main até incorporação.
- [Workstation CI main 37826432518](https://github.com/kevynlucasprofissional-stack/hermes-agent/actions/runs/37826432518): 7 failed / 893 passed / 2 skipped; todas as 7 falhas `ModuleNotFoundError: No module named 'laya'`; anchors PASS; as regressões posteriores foram SKIPPED.
- Causa imediata confirmada: `.github/workflows/workstation-ci.yml` executa `uv sync --locked --python 3.13 --extra dev --extra anthropic`; omite `workstation-laya`, existente no `pyproject.toml` e usado no workflow `.github/workflows/laya-system1-qualification.yml`.
- [Windows PR #52 37829895692](https://github.com/kevynlucasprofissional-stack/hermes-agent/actions/runs/37829895692): `npm audit --omit=dev --audit-level=moderate` falhou com **19** vulnerabilidades (2 critical/5 high/4 moderate/8 low); build/GUI/Electron pós-audit não executados. Número histórico local da CW-01 é **18**, amostra distinta.
- H-079: pin adotado `71a2fe399bbd7a219c71f9d9fca2b313b01f2057`; upstream candidato observado `517b5e10febd619ce30bb22580e29b160266eb43`; 857 downstream-only/10.510 upstream-only commits no refresh do PR #52; overlap material e Stage A não qualificada.
- KI-024 voice input-authority P0, H-080B.3 real Electron e KI-025/H-082 warm bootstrap seguem sem prova de fechamento. Remotion exige aceite de licença para o modo de uso/redistribuição.

## Passo 0 — Preflight obrigatório enxuto e reprodutível

1. Confirme `origin/main`, commit, branch atual, working tree, remotes, pin upstream, head observado, CI required, branch/PR #52 e alterações concorrentes. Preserve quaisquer mudanças locais; prefira worktree/branch limpa, sem reset destrutivo.
2. Leia as instruções obrigatórias `AGENTS.md`, `workstation/AGENTS.md`, `workstation/context/README.md` e a ordem imposta por esse índice; inclua `workstation/context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md`, `workstation/context/TESTING.md`, `workstation/context/KNOWN_ISSUES.md`, `workstation/context/DECISIONS.md` (D-040/D-041), `workstation/creative-workstation/BASELINE_UNBLOCK_EXECUTION_2026-10-08.md`, `IMPLEMENTATION_PLAN.md` e `VERIFICATION_MATRIX.md`. Não leia históricos de pesquisas fora do necessário; mas **não** pule leitura mandatória.
3. Registre `DOWNSTREAM_MAIN_SHA`, `UPSTREAM_MAIN_SHA_OBSERVED`, `CURRENT_PIN_SHA`, `merge-base`, ahead/behind, owner/seams, required CI e impacto. Distinguir gate-repair de implementação runtime: reparos de baseline não concedem autorização para criar CW-02.
4. Reavalie se os bloqueios já foram resolvidos por outro PR/commit desde o relatório; se sim, não refaça trabalho, prove o novo estado e avance para a primeira lane ainda aberta.

## R1 — CORRIGIR JÁ o perfil CI Laya (PR independente, mudança mínima)

**Arquivo a alterar:** `.github/workflows/workstation-ci.yml` > job `contracts` > step `Install locked project environment`.

**Antes:**
```bash
uv sync --locked --python 3.13 --extra dev --extra anthropic
```

**Depois, candidato obrigatório:**
```bash
uv sync --locked --python 3.13 --extra dev --extra anthropic --extra workstation-laya
```

**Arquivos a INSPECIONAR, não alterar sem outra causa comprovada:** `pyproject.toml` (extras `system1-laya`/`workstation-laya`), `uv.lock`, `workstation/third_party/laya`, `.github/workflows/laya-system1-qualification.yml`, `workstation/system1/provenance.py`, `workstation/tests/test_laya_real_contract.py`, `test_laya_vendor_provenance.py`, `test_system1_receipts_provenance.py` e `test_system1_telemetry.py`.

**Verificações:** locked install, import de Laya do subtree aprovado e fingerprint, sete antigos testes problemáticos, suíte `workstation/tests` inteira, `validate_lock.py`, `verify_licenses.py`, `apply_core_integration.py --root . --check`, seam audit strict, `tests/tools/test_registry.py` + demais regressões durable core registradas no workflow e `workstation.benchmarks.trello_regression`. Repita GitHub Workstation CI no HEAD exato, coletando logs dos passos antes SKIPPED.

**Saída:** PR `fix(ci): install locked workstation-laya extra for contract tests`, SHA, CI, teste, alcance, rollback de uma linha. Se o import foi resolvido mas outros erros apareceram, registrar causa nova; não alterar testes para verde nem concluir qualificação fictícia. Não misturar R2/R3.

## R2 — Vulnerabilidades npm Windows (PR independente)

**Ler:** `.github/workflows/workstation-browser-windows.yml` (step `Production dependency audit`), `package.json`, `package-lock.json`, `.npmrc` e manifests workspaces efetivamente afetados. Pegar evidência bruta dos jobs do PR #52. Grupos reportados: `@simple-git/argv-parser/simple-git`, `brace-expansion`, `mermaid/dompurify`, `katex/@streamdown/math`, `http-cache-semantics`, `ip-address/socks`, `postcss-selector-parser`, `source-map-js`, `undici`. KaTeX foi apresentado como “no fix available” naquela execução; verificar opções hoje e mitigação pelo owner sem inventar upgrade.

1. Construir tabela advisory GHSA/CVE → severidade → version range → árvore direta/transitiva → superfície realmente executável → versão corrigida disponível → risco de breaking/compatibilidade → ação e teste.
2. Corrigir manifest/overrides e lock **pontualmente**, respeitando `engine-strict`, `min-release-age`, pins e os workspaces. Não usar `npm audit fix --force` ou alterar `audit-level`/skip/supressão para ocultar vulnerabilidade.
3. Executar `npm ci`, `npm audit --omit=dev --audit-level=moderate`, build/typecheck, Electron UI/platform/packaged E2E aplicáveis e o workflow Windows completo. Para audit local que envie metadados ao registry, primeiro verificar escopo/pacotes privados/secrets e obter autorização; um bloqueio local de consentimento **não** apaga o audit remoto já ocorrido.
4. Quando não houver correção, registrar exceção de risco específica com owner, exposição, mitigação, validade e aprovação exigida; manter gate vermelho até autorização devida. PR separado, sem merge.

## R3 — H-079 Stage A upstream fixo (branch de integração, NÃO de Creative feature)

**Ler:** `workstation/context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md`, `UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md`, `FIRST_PARTY_SEAM_POLICY.md`, `workstation/scripts/audit_hermes_seams.py`, documentos H-079. Verificar `git remote -v`/fetch. Selecionar **um** SHA upstream fixo para o ciclo e provar ancestry/merge-base/drift e owners sobrepostos.

Em branch `integration/upstream-<date>-<sha>` compatível com políticas do repo, integrar upstream real (não copiar arquivos isolados simulando merge), tratar conflitos semanticamente por concern (`ADOPT_UPSTREAM | KEEP_WORKSTATION | SEMANTIC_PORT | EXTRACT_BOUNDARY`) e preservar ProcessRegistry, BrowserTask, MCP, AppResolver, SessionDB, TaskRun, Router/Policy, TaskCompiler, ArtifactStore/Journal, OperationalCapabilityRegistry e Experience Compiler; não criar segundo owner. Provar strict seams, anchors, full Workstation, H-077/H-078 pertinentes, CI, Windows/Electron, native-browser e bootstrap. Reclassificar REMOVE debt quando aplicável.

**Regra:** 10.510 commits upstream não são 10.510 bugs; delta material não autoriza merge cego. Se o pin for comprovadamente quebrado/inadotável, a H-079 prevê exceção temporária escrita em CURRENT_STATE + journal; não a assuma, não faça waiver só pela divergência. Após Stage A qualificada, snapshot final de drift, sem reabrir merge só porque upstream andou. Nunca merge automático no main.

## R4 — Fechar segurança/experiência de produto aplicáveis (PRs separados)

**KI-024 P0 voz:** `workstation/context/VOICE_AUTOSTART_INPUT_AUTHORITY_INCIDENT_2026-10-03.md`, `KNOWN_ISSUES.md`, `apps/desktop/src/store/composer.ts`, `use-composer-voice.ts` (descobrir path real), transições STT/voice/submissão. Exigir intenção explícita e atribuível a janela/sessão antes de `role=user`; testar idle longo, listening armed, session new/switch/remount, múltiplas superfícies e handoff legítimo. A hipótese de stale latch é apenas parcial, não causa fechada.

**H-080B.3:** provar produto real Electron/WebContentsView + backend, startup/restart, sessão, artefatos, readback, autoridade e telemetria com oracle independente. Não usar screenshot ou mock como comprovante de mutação real.

**KI-025/H-082:** `workstation/context/WORKSTATION_BOOTSTRAP_STARTUP_RELIABILITY_2026-10-07.md`, `workstation/install.ps1`/`install.cmd` e one-click launcher. Provar healthy warm-start com PyPI/npm inacessíveis sem re-instalar/resolver deps; invalidar readiness ao mudar locks; reparo explícito para ambiente danificado; Windows clean start e checkout limpo. Resolver H-081/provenance/learning release gaps quando necessários e distinguir dos CW gates.

Reportar em quais fases cada bloqueio é crítico. **Não começar implementação criativa contra baseline não qualificada, com P0 de autoridade sem contenção ou CI necessária vermelha.**

## R5 — Implementar fases CW após GO verificável, sem voltar à CW-01

**CW-02:** em PR isolado, contrato mínimo tipado/discovery/health de app/capability opt-in. Primeiros owners: `hermes_platform/resolver/app.py::AppResolver.locate/inspect/probe`, `workstation/capabilities.py::RuntimeCapabilityRegistry.inspect_environment`, `workstation/health.py::WorkstationHealth`, `tools/process_registry.py::ProcessRegistry.spawn_local/poll/kill_process`, `workstation/workers.py`, `workstation/host.py` e `tools/mcp_tool.py`. Não alterar AppResolver/process registry se os contratos atuais bastarem. Distinga presente/saudável/autorizado; version/fingerprint, opt-in e typed process args. Testes deny/porta/cross-profile/env secreto/cancel/crash/restart, owner/readback, feature flag off. Nenhuma engine externa auto-instalada.

**CW-03A:** React/SVG editável → preview Chromium no `apps/desktop/electron/workstation-browser-runtime.ts` BrowserTask/WebContentsView existente → PNG decodificável, hash/dimensões corretos, fonte/manifest no workspace, revisão e reabertura/restart; ArtifactStore/Journal como autoridade. Negativos invalid source/path/asset, stale revision, isolamento de perfil, navegador indisponível e efeito incerto. Primeiro caso real pode ser convite visual. E2E nativo necessário.

**CW-03B:** FFmpeg/ffprobe com binário/SHA/licença/codec revisados, CLI tipado allowlisted, entrada restrita ao workspace, cancelamento/timeout/limpeza segura, MP4 real com codec/duração/dimensões/hash verificados e readback.

**CW-03C (OPCIONAL):** Remotion Studio/CLI **somente** depois de decisão explícita da licença para uso/embedding/redistribuição concretos. Se bloqueado por licença, marcar BLOCKED/LICENSE e continuar trilhas independentes sem Remotion; nunca impedir CW-03A/B por isto.

**CW-04 (independente de CW-05):** Penpot web/MCP oficial no pin auditado; autenticação/role/document scope/revision/concorrência. Provar agente cria projeto, humano edita, agente altera outra parte preservando revisão humana. Proibir segredos/logs ou mutação cross-profile. Penpot core MPL não implica licença do AI Kit CC-BY.

**CW-05 (independente de CW-04):** Three.js Editor pinado; bridge com comandos tipados inspect/add/transform/material/camera/light/export/undo, sem JS arbitrário privilegiado. Provar cena/GLB salva/reabre, revisão/undo e preservação de edições humanas. Negativos command/owner/revision/export.

**CW-06 (demanda real):** Inkscape CLI ou Blender headless como engines opt-in isoladas; um adapter/PR por uso, com licença, fontes, sandbox, outputs e rollback. Graphite, CAD, áudio e Godot permanecem exploração até caso concreto.

**CW-07:** só após uma vertical comprovada, ligar receipts/revisions/artifacts reais ao `workstation/experience_compiler/` e `workstation/operational_capabilities.py`, reutilizando `workstation/task_compiler.py` e `workstation/control_plane/`. Demonstrar observação → candidate → replay/verifier independente + negativos → policy promotion → execução nova realmente verificada. Drift de engine/schema/escopo/owner impede reuse; Laya/System-1 não concede autoridade, outcomes ou promoções.

## Padrão obrigatório de execução e entrega

- Para **cada** R ou CW: branch e PR pequenos; owner `arquivo::símbolo` real; problema; diff limitado; testes positivos + negativos + E2E quando exigido; resultados efetivos e comandos; recibos/links/hashes; rollback; `main SHA` e upstream pin; required CI HEAD.
- Estados: `PLANNED`, `BLOCKED`, `IMPLEMENTED`, `INTEGRATION_PASS`, `E2E_PASS`, `QUALIFIED` e `NOT_RUN` sem confusões; `PASS` somente após execução. Sem screenshots como única prova de efeito.
- Atualizar `workstation/ROADMAP.md`, `workstation/context/CURRENT_STATE.md`, `workstation/context/engineering-journal/CURRENT.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md`, `workstation/SOURCE_MATRIX.md` (quando houver fontes externas realmente auditadas) e DECISIONS quando a decisão for aceita; preservar históricos.
- Não substituir AST/contract e oráculos reais por testes que leem strings no source; não fazer instalação/execução de terceiros sem consentimento necessário; não borrar logs de evidência ou expor tokens; não conceder authority a skill/Laya nem criar owner paralelo.
- Se o gate impedir uma lane, publique o status e a menor correção verificável; avance apenas outra lane independente permitida. Não alegar trabalho pendente como concluído. Não pedir novamente informações já determinadas no repo; só exigir aprovação humana para autorização real, licença, risco residual e merge quando aplicável.
- Resposta de cada etapa:
  `FASE/STATUS | HEAD/pin | FILES/OWNERS | DIFF | TESTS + NEGATIVES | EVIDENCE | CI | BLOCKERS | NEXT ACTION | BRANCH/PR/MERGE STATUS`.

**COMECE AGORA por R1**: verificar que a ausência do extra ainda existe no HEAD, executar preflight H-079, criar PR mínimo do workflow CI, verificar proveniência real e retestar o HEAD corrigido. Não devolva apenas uma nova auditoria CW-01.
