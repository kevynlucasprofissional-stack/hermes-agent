# Hermes Creative Workstation — CWN Baseline Audit (CWN-00)

**Data:** 10/10/2026  
**Status do Gate:** `DEVELOPMENT_ONLY` / `BLOCKED_FOR_PROMOTION` (promoção externa bloqueada até qualificação completa; desenvolvimento isolado autorizado)  
**Referência Canônica:** D-043 (`workstation/creative-workstation/ENGINE_NEUTRAL_ARCHITECTURE_2026-10-10.md` e `ENGINE_NEUTRAL_IMPLEMENTER_HANDOFF_2026-10-10.md`)  
**Base Pinned:** `origin/main` @ `f21e803b3525b70ee6be2305e579c1cc1f930e74`  
**Branch de Implementação:** `codex/creative-d043-engine-neutral`  

---

## 1. Auditoria dos PRs #57 a #64 e Ancestralidade Git

| PR | Branch | Base | Título / Escopo | Status CI / Blocker | Status de Reaproveitamento D-043 |
|---|---|---|---|---|---|
| **#57** | `codex/creative-stage-a-20261008` | `f21e803b35` (`main`) | `ci(workstation): compose baseline gate repairs for Creative Stage A` | `desktop-typecheck` falhou em CI Windows runner (conflito npm-audit histórico); localmente `npm run typecheck` passa (0 erros). | **ADOTADO**: reparos de baseline e tipagens validados. |
| **#58** | `codex/creative-cw02-20261008` | `3417d57b5c` (#57) | `feat(workstation): add opt-in Creative CLI lifecycle and health` | CI falhou no mesmo check de runner. | **ADOTADO**: `creative_apps.py`, `creative_process.py`, `creative_runtime.py` incorporados. |
| **#59** | `codex/creative-cw03a-20261008` | `480d8092a0` (#58) | `feat(workstation): add versioned Creative projects and owned PNG rendering` | CI falhou no mesmo check de runner. | **ADOTADO**: `creative_project_store.py`, `creative_project_runtime.py`, `creative_render.py`, `creative_media.py`. |
| **#60** | `codex/creative-cw03b-20261008` | `bd22814c52` (#59) | `feat(workstation): export owned still-image MP4 with decoded verification` | CI falhou no mesmo check de runner. | **ADOTADO**: `creative_video.py`, `creative_video_metadata.py`, `creative_video_process.py`. |
| **#61** | `codex/creative-cw03c-20261008` | `6f784adccd` (#60) | `feat(workstation): preserve editable Remotion project sources` | CI falhou no mesmo check de runner. | **RESERVADO/OPCIONAL**: `creative_remotion_source.py` mantido sob gate de licença explícito. |
| **#62** | `docs/creative-hyperframes-first-20261009` | `f21e803b35` (`main`) | `docs(workstation): D-041 HyperFrames-first Creative Studio roadmap` | Draft documental. | **SUBSTITUÍDO PARCIALMENTE POR D-043**: HyperFrames passa de autoridade soberana a motor intercambiável. Código de suporte (`creative_nle.py`, `creative_operations.py`, `creative_3d.py`, `creative_studio_service.py`) reaproveitado e neutralizado. |
| **#63** | `docs/dogfood-causal-product-gate-20261009` | `f21e803b35` (`main`) | `docs(workstation): D-042 Dogfood product gate and causal implementation handoff` | Draft documental. | **PRESERVADO INTEGRALMENTE**: regras de dogfood causal e restrições de produto D-042 ativas. Alterações não commitadas em `dados/` preservadas intactas. |
| **#64** | `docs/cw-engine-neutral-human-ai-20261010` | `f21e803b35` (`main`) | `docs(creative): D-043 engine-neutral CW, shared editing and executable CWN-00–09 handoff` | Canônico. | **FONTE AUTORITATIVA D-043**: Especificação completa e matriz de verificação integradas na branch de trabalho. |

---

## 2. Matriz por Módulo (Source Matrix & Owners)

| Caminho | Símbolo Principal | Owner Canônico | Origem | Estado e Testes | Ação D-043 |
|---|---|---|---|---|---|
| `workstation/creative_apps.py` | `CreativeAppDescriptor`, `list_creative_apps` | AppResolver / ProcessRegistry | PR #58 | 6/6 testes PASS (`test_creative_apps.py`) | **REUTILIZAR**: Descoberta declarativa de engines e ferramentas CLI. |
| `workstation/creative_process.py` | `CreativeProcessSupervisor`, `probe_creative_health` | ProcessRegistry / TaskRun | PR #58 | 5/5 testes PASS (`test_creative_process.py`) | **REUTILIZAR**: Supervisão de ciclo de vida de processos, portas loopback e graceful shutdown sem órfãos. |
| `workstation/creative_runtime.py` | `CreativeRuntimeManager` | Creative Runtime | PR #58 | 4/4 testes PASS (`test_creative_runtime.py`) | **REUTILIZAR**: Resolução e ativação opt-in do subsistema Creative. |
| `workstation/creative_project_store.py` | `CreativeProjectStore`, `CreativeProjectRevision` | ArtifactStore / Session Storage | PR #59 | 6/6 testes PASS (`test_creative_project_store.py`) | **ADAPTAR (CWN-01)**: Base para versionamento do Creative Document, isolamento de perfil, hash de integridade e controle de concorrência com 409 Conflict. |
| `workstation/creative_project_runtime.py` | `CreativeRunContext`, `save_project_for_run` | TaskRun / Context Fencing | PR #59 | 4/4 testes PASS (`test_creative_project_runtime.py`) | **REUTILIZAR**: Fencing estrito sob TaskRun ativo, isolamento de perfil e workspace. |
| `workstation/creative_render.py` | `render_project_for_run`, `CreativeRenderBackend` | BrowserTask / Render Pipeline | PR #59 | 5/5 testes PASS (`test_creative_render.py`) | **REUTILIZAR & ESTENDER (CWN-06)**: Renderização de frames SVG/HTML em PNG via Electron WebContentsView com recibos tipados. |
| `workstation/creative_media.py` | `CreativeMediaAsset`, `validate_media_asset` | Media Asset Pipeline | PR #59 | 4/4 testes PASS (`test_creative_media.py`) | **REUTILIZAR**: Validação de proveniência de assets, MIME types e hashes SHA-256. |
| `workstation/creative_video.py` | `encode_still_video`, `CreativeStillVideoRequest` | Media Engine (FFmpeg) | PR #60 | 5/5 testes PASS (`test_creative_video_process.py`, `test_creative_video_metadata.py`) | **REUTILIZAR**: Exportação de vídeo bounded com ffprobe independente. |
| `workstation/creative_nle.py` | `NLETrack`, `NLEClip`, `NLETimeline` | Creative Timeline | Local (`edcc949677`) | 9/9 testes PASS (`test_creative_nle.py`) | **ADAPTAR (CWN-01 / CWN-03)**: Integrar tempo canônico racional (`creative_time.py`) e comandos de edição não linear (`clip.split`, `trim`, `rippleDelete`, `slip`, `slide`, `roll`, `setSpeed`). |
| `workstation/creative_operations.py` | `apply_operation`, `CreativeOperation` | Creative Operations | Local (`edcc949677`) | 5/5 testes PASS (`test_creative_operations.py`) | **ADAPTAR (CWN-02)**: Evoluir para Command Bus unificado com `expectedRevision`, atomicidade, idempotência e Undo/Redo canônico. |
| `workstation/creative_3d.py` | `GLBValidator`, `ThreeViewportConfig` | 3D Parser / Viewport | Local (`edcc949677`) | 6/6 testes PASS (`test_creative_3d.py`) | **REUTILIZAR (CWN-05)**: Suporte a Three.js e parser de GLB com defesa contra path traversal e limites de geometria. |
| `workstation/creative_studio_service.py` | `HyperFramesStudioService` | Creative Service | Local (`edcc949677`) | 8/8 testes PASS (`test_creative_studio_service.py`) | **REUTILIZAR COMO ADAPTER**: Serviço local sob loopback e CSRF tokens. Sob D-043, atua como engine adapter e não autoridade central. |
| `apps/desktop/electron/workstation-creative-frame.ts` | `WorkstationCreativeFrame` | Electron Desktop | PR #59 / Local | 8/8 vitest PASS (`apps/desktop/electron/*.test.ts`) | **REUTILIZAR**: Superfície nativa WebContentsView com isolamento de contexto e IPC restrito. |
| `apps/desktop/src/app/` | Creative UI components | Desktop Workspace UI | Local / PR #59 | Typecheck limpo (0 erros tsc) | **EVOLUIR (CWN-07)**: Workspaces contextuais (Montagem, Motion, Design, 3D) sobre o mesmo documento. |

---

## 3. Preflight H-079 e Auditoria de Seams

Executado preflight canônico H-079 no ambiente:

1. **Auditoria de Seams (`python workstation/scripts/audit_hermes_seams.py`):**
   - Direct core seams: 14
   - Classified: 14 (100%)
   - Unclassified: 0
   - Budget regressions: 0
   - `tools/browser_tool.py`: 2 [UPSTREAM_ABSTRACT] FPS-BROWSER-001
   - `tools/browser_workstation.py`: 5 [REMOVE] FPS-BROWSER-LEGACY
   - `tools/vault_tools.py`: 1 [PRESERVE_FIRST_PARTY] FPS-VAULT-001
   - `tools/workstation_extensions.py`: 4 [PRESERVE_FIRST_PARTY] FPS-WS-EXT-001
   - `tools/workstation_work.py`: 2 [PRESERVE_FIRST_PARTY] FPS-WS-WORK-001
   - Edge Workstation references: 1013 (dentro do reportado)

2. **Verificação de Licenças (`python workstation/scripts/verify_licenses.py`):**
   - Status: `OK: Workstation license policy`

3. **Validação de Bloqueio de Componentes (`python workstation/scripts/validate_lock.py`):**
   - Status: `OK: components.lock.json`

4. **Verificação de Tipos TypeScript (`npm --prefix apps/desktop run typecheck`):**
   - Status: `PASS` (0 erros tsc em `apps/desktop`, `tsconfig.electron.json` e `tsconfig.e2e.json`).

5. **Suíte Python Atual:**
   - 49/49 testes em `workstation/tests/test_creative*.py` passando com sucesso.

---

## 4. Preservação de Trabalho Local e Regras de Segurança

1. **Alterações Não Commitadas Mantidas:**
   - As modificações em `workstation/dogfood/` e movimentações de `dados/` permanecem estritamente preservadas no diretório de trabalho, sem `git clean`, sem `git reset --hard`.
2. **Isolamento de Branches:**
   - Nova branch de desenvolvimento: `codex/creative-d043-engine-neutral`.
   - Nenhuma alteração empurrada automaticamente para `main`.
3. **Classificação de Admissão:**
   - Nenhuma dependência externa não autorizada foi instalada.
   - Nenhuma autoridade externa criada; TaskRun, BrowserTask, ProcessRegistry e ArtifactStore permanecem como únicos owners legítimos.

---

## 5. Sequência Executiva de Implementação (CWN-01 → CWN-09)

1. **CWN-01:** Implementar tempo canônico racional (`creative_time.py`) e estender o Creative Document versionado (`creative_document.py` / `creative_project_store.py`) com IDs estáveis e mapeamento source↔timeline.
2. **CWN-02:** Implementar Command Bus unificado e transações atômicas com `expectedRevision`, rastreabilidade de ator e Undo/Redo canônico (`creative_commands.py`, `creative_transactions.py`).
3. **CWN-03:** Implementar primitivas de timeline NLE (`split`, `trim`, `rippleDelete`, `slip`, `slide`, `roll`, `setSpeed`) com suporte a linked A/V e track locks.
4. **CWN-04:** Implementar Semantic Edit Plan com pré-visualização reversível em revisão isolada e aceitação seletiva (`creative_edit_plan.py`).
5. **CWN-05:** Implementar autoria freeform para SVG, Canvas e Three.js com seek determinístico e execução isolada (`creative_scene_adapters.py`).
6. **CWN-06:** Implementar renderização intercambiável e exportação com verificação independente de vídeo/áudio e receipts à prova de adulteração (`creative_render_adapters.py`).
7. **CWN-07:** Implementar interface contextual com workspaces progressivos e Graph Editor para curvas de easing e keyframes.
8. **CWN-08:** Integrar procedimentos criativos verificados ao Experience Compiler existente.
9. **CWN-09:** Otimizações avançadas, benchmarks de performance e adapters adicionais.
