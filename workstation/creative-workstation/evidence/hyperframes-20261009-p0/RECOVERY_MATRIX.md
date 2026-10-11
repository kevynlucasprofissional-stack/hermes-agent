# Matriz de Recuperação e Estabilização P0 — Hermes Creative Workstation

Data de consolidação: 9 de outubro de 2026  
Status: **P0 QUALIFIED PARA EXPERIMENTO (GO_FOR_EXPERIMENT) / BLOCKED PARA MERGE EM MAIN**  
Branch: `codex/creative-hyperframes-20261009`  
Base SHA: `f21e803b3525b70ee6be2305e579c1cc1f930e74` (main)  
Head Documental PR #62: `4c5c9737e3`  
Upstream Hermes Observado: `b624a38f21f2f674d5a8ccf387687c1b481e23f6`  
Upstream Pin Adotado em Main: `71a2fe399bbd7a219c71f9d9fca2b313b01f2057`  
Upstream Pin Candidato Stage A: `517b5e10febd619ce30bb22580e29b160266eb43`  
HyperFrames Pin Candidato: `3aa68869f7d4cec8b37cdfcb9cd539389b63abed` / versão `0.8.143` (Apache-2.0)

---

## 1. Inventário de Arquivos e Decisão de Reaproveitamento

| Caminho | PR / Branch Origem | Owner Canônico | Decisão | Risco / Limite | Testes Existentes | Pendências |
|---|---|---|---|---|---|---|
| `workstation/creative_apps.py` | PR #58 (`codex/creative-cw02-20261008`) | AppResolver / ProcessRegistry | **REAPROVEITAR E ADAPTAR** | Registrar executáveis absolutos e probes fixos para `hyperframes` CLI e Node runtime; proibir comandos arbitrários | Testes unitários de manifesto, probes e hash SHA-256 | Registrar assinatura de `hyperframes` e runtime Node |
| `workstation/creative_process.py` | PR #58 (`codex/creative-cw02-20261008`) | ProcessRegistry / ScopedPolicyEngine | **REAPROVEITAR E ADAPTAR** | Spawn sem shell, allowlist estrita de env vars (sem vazar segredos/tokens), lifecycle do servidor HyperFrames Studio | Testes de cancelamento, timeout, recuperação e isolamento de env | Implementar gerenciamento do subprocesso `hyperframes preview` |
| `workstation/creative_runtime.py` | PR #58 (`codex/creative-cw02-20261008`) | RuntimeCapabilityRegistry / AppResolver | **REAPROVEITAR E ADAPTAR** | Descoberta passiva; não instala automaticamente em tempo de execução sem consentimento | Testes de discovery, opt-in/opt-out por feature flag | Integrar descoberta do serviço `hyperframes.studio` |
| `workstation/creative_project_store.py` | PR #59 (`codex/creative-cw03a-20261008`) | ArtifactStore / ExecutionJournal | **REAPROVEITAR E ADAPTAR** | Manter arquivos nativos (`index.html`, CSS, JS, assets) e manifesto fino com revisões imutáveis, hashes SHA-256 e ETag (HTTP 409) | Testes de integridade de escrita, revisões e detecção de drift | Mapear storage para o layout de projeto HyperFrames (`hyperframes.json`) |
| `workstation/creative_project_runtime.py` | PR #59 (`codex/creative-cw03a-20261008`) | Session / TaskRun / ControlPlane | **REAPROVEITAR E ADAPTAR** | Exigir TaskRun ativo e válido; validar escopo de perfil e workspace; registrar no journal | Testes de autoridade negada, auditoria e rollback | Ligar transações aos metadados do projeto HyperFrames |
| `workstation/creative_render.py` / `creative_media.py` | PR #59 (`codex/creative-cw03a-20261008`) | ArtifactStore / Verifier | **REAPROVEITAR** | Verificação independente de PNGs com Pillow (dimensões, decodificação, hashes); não mascarar falhas | Testes de verificação positiva e negativa de imagem | Reaproveitar para validar frames exportados pelo HyperFrames |
| `workstation/creative_video*.py` | PR #60 (`codex/creative-cw03b-20261008`) | ProcessRegistry / ArtifactStore | **REAPROVEITAR** | Limites estritos de processo FFmpeg/ffprobe; verificação de codecs H.264, duração e contagem de frames | Testes de execução FFmpeg, leitura de log de version header, cancelamento de subprocesso | Ligar verificação ao output MP4 do render HyperFrames |
| `apps/desktop/electron/workstation-creative-frame.ts` | PR #59 + worktree capture fix | BrowserTask / WebContentsView | **REAPROVEITAR E ADAPTAR** | Lock transitório, restauração de ordem de views, geometria e zoom nativos no Electron | 47 testes de layout, captura e UI no Desktop | Adaptar montagem de view para hospedar a URL do HyperFrames Studio local |
| `apps/desktop/electron/workstation-browser-runtime.ts` | PR #59 + worktree capture fix | BrowserRuntime / WebContentsView | **REAPROVEITAR E ADAPTAR** | Garantir que a view criativa permaneça sob autoridade do BrowserTask, sem criar segunda janela Electron | Testes de reconnect, ciclo de vida e autoridade de navegação | Adicionar rota e superfície "Creative Studio" |
| `workstation/creative-workstation/evidence/hyperframes-20261009-p0/native-capture-backup/` | Worktree local | Repositório | **PRESERVADO** | Backup íntegro dos 7 arquivos locais com manifesto SHA-256 | Testes de integridade de hash | Preservado para aplicação sem perda |
| Remotion sources (`Invitation.tsx`, etc.) | PR #61 (`codex/creative-cw03c-20261008`) | N/A | **SUSPENDER** | Preservar no histórico do Git. Não ativar em produção devido à decisão D-041 (HyperFrames-first) | 9 testes em PR #61 | Suspenso até necessidade futura comprovada |

---

## 2. Auditoria Preflight H-079 e Seam Gate

- **DOWNSTREAM_MAIN_SHA:** `f21e803b3525b70ee6be2305e579c1cc1f930e74`
- **UPSTREAM_MAIN_SHA_OBSERVED:** `b624a38f21f2f674d5a8ccf387687c1b481e23f6`
- **CURRENT_PIN_SHA (Adotado):** `71a2fe399bbd7a219c71f9d9fca2b313b01f2057`
- **git merge-base:** `71a2fe399bbd7a219c71f9d9fca2b313b01f2057`
- **Commits Ahead:** 857
- **Commits Behind:** 10.723
- **Auditoria de Seams (`audit_hermes_seams.py`):**
  - Total core seams: 14 (14 classificados, 0 desclassificados, 0 regressões de orçamento).
  - Classificações:
    - `tools/browser_tool.py`: 2 [UPSTREAM_ABSTRACT] (FPS-BROWSER-001)
    - `tools/browser_workstation.py`: 5 [REMOVE] (FPS-BROWSER-LEGACY)
    - `tools/vault_tools.py`: 1 [PRESERVE_FIRST_PARTY] (FPS-VAULT-001)
    - `tools/workstation_extensions.py`: 4 [PRESERVE_FIRST_PARTY] (FPS-WS-EXT-001)
    - `tools/workstation_work.py`: 2 [PRESERVE_FIRST_PARTY] (FPS-WS-WORK-001)
- **Status do Gate H-079:**
  - Adoção de pin completo e merge de upstream estão separados na lane Stage A (PR #57).
  - O desenvolvimento na lane Creative prossegue isoladamente sob a **Exceção de Desenvolvimento de 08/10/2026**, autorizada expressamente pelo mantenedor ("Está autorizado").
  - O merge em `main` e a promoção operacional permanecem **BLOQUEADOS** até qualificação completa.

---

## 3. Investigação da Falha de CI no PR #61

- **Check afetado:** `desktop-typecheck` (GitHub Actions Run `37866692641`).
- **Etapa exata com falha:** `Release qualification gate` (`workstation.release_qualification`).
- **Comando disparado:**
  `& .venv\Scripts\python.exe -m workstation.release_qualification --root . --python .venv\Scripts\python.exe --timeout 1800 ...`
- **Causa Raiz 1 (Timeout):** O subestágio `workstation_smoke` executou `scripts/run_tests_parallel.py workstation/tests -j 4 --file-timeout 1800.0` e atingiu o limite de 1.800 segundos (30 minutos) no runner Windows.
- **Causa Raiz 2 (Dependência de Ambiente):** Log registrou aviso repetido `Could not register LayaDecisionProvider: No module named 'laya'`.
- **Comportamento dos checks individuais do Desktop:**
  - ESLint: pass
  - Prettier: pass
  - Browser foundation focused tests: pass
  - Native BrowserSessionState smoke: pass
  - Native Browser runtime reconnect soak: pass
  - Headless backend multi-session reconnect soak: pass
  - Desktop UI tests: pass
  - Desktop platform tests: pass
  - Workstation doctor: pass
  - Workstation reconnect soak: pass
  - Dashboard cross-engine smoke: pass
  - Desktop unpacked package: pass
  - Packaged Desktop GUI E2E: pass
  - Integrated Desktop Browser headless load E2E: pass
  - *Todos os 14 checks de TypeScript/Desktop passaram com sucesso.* A falha foi puramente no runner de testes paralelos em Python/Laya durante a qualificação de release agregada.

---

## 4. Auditoria e Validação Técnica do HyperFrames (0.8.143)

- **Pacotes Auditados:**
  - `hyperframes@0.8.143` (CLI autossuficiente com assets de Studio embutidos)
  - `@hyperframes/studio@0.8.143` (UI React com CodeMirror, player e dockview)
  - `@hyperframes/studio-server@0.8.143` (API Hono com manipulação de fontes e proxy)
- **Licença:** Apache-2.0
- **Ferramental Validado na Máquina Local:**
  - Node: v26.7.0 (compatível com `engines: node >= 22`)
  - Bun: 1.3.11
  - FFmpeg: 8.1.1 Gyan Full
  - ffprobe: 8.1.1 Gyan Full
  - Google Chrome: Instalado em `C:\Program Files\Google\Chrome\Application\chrome.exe`
- **Evidência Experimental Isolada:**
  1. Criação de projeto `hyperframes init test-project --example blank --non-interactive` com sucesso.
  2. Inicialização do servidor Studio em `127.0.0.1:3032` via `hyperframes preview --no-open --port 3032`.
  3. Resposta HTTP 200 OK retornando a interface do Studio e APIs `/__hyperframes_config` e `/api/environment/ffmpeg`.
  4. Renderização real de vídeo MP4 via `hyperframes render -o out.mp4`.
  5. Inspeção ffprobe comprovando H.264, 1920x1080, 30 fps, 60 frames, duração exata de 2.0s, sem frames estáticos e com encoder libx264.
  6. Encerramento limpo sem processos órfãos.

---

## 5. Critério de Saída P0

A matriz comprova exatamente quais componentes recuperar de PRs anteriores (#58, #59, #60), quais preservar como backup (captura nativa), quais suspender (Remotion #61) e como orquestrar a fundação do HyperFrames Studio (D-041). O caminho está liberado para a implementação do P1 sob a exceção de desenvolvimento.
