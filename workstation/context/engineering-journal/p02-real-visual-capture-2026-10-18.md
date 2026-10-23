# HLM-P02: Captura Visual Real do Modo Aprender — Recibo de Engenharia
**Data**: 2026-10-18  
**Autor / Agente**: `learning-mode-p02-agent`  
**Branch**: `feat/hermes-learning-mode-p02-real-capture`  
**Base commit**: `2e5b042e4ca1701e1494ae6d288d6b9ea0b7405e` (main)  
**Decisão**: [D-048](../DECISIONS.md#d-048-captura-visual-real-e-sincronizada-de-sessões-de-aprendizado-do-browser-hlm-p02)  
**Defeito**: [KI-049](../KNOWN_ISSUES.md#ki-049-gravação-de-vídeo-sintética-de-1-segundo-e-snapshots-vazios-no-learning-mode-resolvido-em-hlm-p02)  

---

## 1. Contexto e Diagnóstico

Na implementação inicial do MVP do Learning Mode (HLM-MVP, D-047), a captura de vídeo do `LearningSessionRecorder` em `apps/desktop/electron/workstation-learning-session.ts` chamava:

```ts
const ffmpeg = spawn('ffmpeg', [
  '-f', 'lavfi',
  '-i', 'color=c=black:s=1280x720:r=15',
  '-t', '1',
  videoPath
])
```

Esse gerador sintético produzia um arquivo preto de 1 segundo (~3.7 KB) independentemente da duração da sessão humana. Além disso, o diretório `snapshots/` permanecia vazio e os eventos em `events.jsonl` não continham correlação com frames codificados.

---

## 2. Solução Implementada

### 2.1. Pipeline de Frames da Aba Autorizada
Reutilizada a infraestrutura existente de `WebContentsView` em `apps/desktop/electron/workstation-browser-runtime.ts`:
- Chamada direta a `entry.view.webContents.capturePage()`.
- Normalização dimensional obrigatória via `NativeImage.resize({ width: 1280, height: 720, quality: 'good' })`.
- Conversão para buffer PNG consistente alimentado diretamente no stdin do FFmpeg via `image2pipe`.
- Verificação prévia de URL segura (bloqueio antes de capturar telas de autenticação ou fora do domínio autorizado).

### 2.2. Encoder FFmpeg e Gestão de Backpressure
Configuração do encoder:
```ts
const ffmpegArgs = [
  '-y',
  '-f', 'image2pipe',
  '-framerate', '3',
  '-vcodec', 'png',
  '-i', 'pipe:0',
  '-an',
  '-c:v', 'libvpx-vp9',
  '-deadline', 'realtime',
  '-cpu-used', '5',
  '-pix_fmt', 'yuv420p',
  videoPath
]
```
- Taxa serializada de ~3 fps com controle de concorrência (`isCapturingFrame`).
- Backpressure de stdin com monitoramento do retorno de `write()` e espera pelo evento `drain`.
- Handler de `proc.stdin.on('error')` prevenindo crash de `EPIPE`.

### 2.3. Indexação e Snapshots Persistentes
- `media/frame_index.jsonl`: grava cada frame codificado com `frame_number`, `pts_ms`, `timestamp_ms`, `relative_ms`, `width`, `height`, `bytes`.
- `snapshots/snap_<eventId>_<timeMs>.png`: captura de imagem em tamanho real no momento de cliques e atalhos modificados.
- `events.jsonl`: eventos associados com `event.frame_number` e `event.snapshot_ref`.

### 2.4. Ciclo de Vida Fail-Closed
- Método `stop()` encerra captura, envia `end()` no stdin e aguarda evento `close` do FFmpeg.
- Validação pós-gravação: existência de arquivo com tamanho > 0, contagem de frames codificados > 0 e exitCode === 0. Caso contrário, status é marcado como `'error'` ou `'blocked'`.

---

## 3. Matriz de Evidências

### 3.1. Testes Automatizados (Vitest)
Executados com:
`npm test -- workstation-learning`

Resultados:
- `workstation-learning-events.test.ts`: 7/7 PASS
- `workstation-learning-session.test.ts`: 13/13 PASS
- `workstation-learning-vertical-slice.test.ts`: 4/4 PASS
- `workstation-learning-question-policy.test.ts`: 3/3 PASS
- `workstation-learning-visual-acceptance.test.ts`: 2/2 PASS

**Total: 29/29 testes PASS**

### 3.2. Prova de Aceitação Visual (30 Segundos / ffprobe)
Executado em `workstation-learning-visual-acceptance.test.ts`:
- 90 frames dinâmicos codificados via FFmpeg real.
- Inspeção por `ffprobe`:
  - `codec_name`: `vp9`
  - `duration`: `30.000000`
  - `format_name`: `matroska,webm`
- Verificada distinção de quadros e ausência de fonte sintética preta.

### 3.3. Prova em Electron Real (Chromium 144 / Electron 40.10.2)
Runner: `apps/desktop/electron/fixtures/run-electron-learning-proof.ts` compilado e executado sob o binário nativo do Electron:
Recibo emitido: `apps/desktop/electron/fixtures/real-electron-recording-proof.json`:
```json
{
  "testRunTimestamp": "2026-10-18T13:48:47.345Z",
  "sessionId": "real-electron-proof-1792268924610",
  "electronVersion": "40.10.2",
  "chromeVersion": "144.0.7559.2",
  "videoPath": "C:\\Users\\Kevyn Lucas\\.hermes\\learning_sessions\\real-electron-proof-1792268924610\\media\\recording.webm",
  "videoSizeBytes": 94331,
  "videoStatus": "completed",
  "framesCount": 10,
  "snapshotsCount": 5,
  "eventsCount": 5,
  "eventsWithSnapshots": 5,
  "verificationPassed": true
}
```

### 3.4. Code Health e Tipagem
- `npm run typecheck`: exit code 0
- `npx eslint`: 0 errors, 0 warnings
- `python scripts/check --only health`: 0 blocking findings, 0 advisory findings

---

## 4. Declaração de Escopo e Status dos Marcos

- **P02 / KI-049**: CONCLUÍDO E VERIFICADO.
- **M0, M1, M2**: Estáveis e integrados ao pipeline visual real.
- **M3 (Replay Autônomo Condicionado)**: Permanece estritamente em **HOLD**.
- **Question Engine / Chat UI**: Preservados sem alterações.
- **Git / Main**: Trabalho mantido na branch de feature `feat/hermes-learning-mode-p02-real-capture`, sem push ou merge não autorizado.
