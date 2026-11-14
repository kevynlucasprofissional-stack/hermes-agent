# Prompt 05 — Handoff de integração e inserções documentais (2026-10-27)

**Resumo operacional:** P05 tem implementação e prova nativa offline de áudio PT-BR no venv do Hermes, mas **não** está qualificado para release ou consumo automático pelo Workstation. Relatório autossuficiente: `workstation/context/AUDIO_LOCAL_QUALIFICATION_P05_20261027.md`.

## Ownership e preservação
Branch inicial/final `main`, HEAD observado `f1d5ab2f030e940ed4571371b0de45a21a009c9e`; WIP pré-existente em docs oficiais de `chatgpt-whatsapp-m3`. Claim `chatgpt-audio-p05` / `p05-audio-qualification` em seis arquivos novos: `workstation/audio_local_runtime.py`, `workstation/tests/test_audio_local_runtime.py`, `workstation/tests/test_audio_local_native.py`, `workstation/tests/fixtures/sapi_ptbr_fixture.ps1`, `workstation/context/AUDIO_LOCAL_QUALIFICATION_P05_20261027.md` e este handoff. Nenhum arquivo existente de TTS, STT ou Cron modificado. Commit integrator não designado; sem Git reset/stash/checkout/branch/commit/push.

## Inserir em workstation/ROADMAP.md — owner documental M3
`HW-IMP-05 AUDIO_LOCAL_ADAPTER_IMPLEMENTED / SYNTHETIC_NATIVE_STT_TTS_PASS / CRON_MODEL_PRECEDENCE_PASS / FULL_WORKSTATION_BOOTSTRAP_HOLD / RELEASE_HOLD`. Adapter determinístico `path -> tools.transcription_tools.transcribe_audio -> {text,language,provenance}` para WAV mono PCM16 local dentro de 25 MiB, modelo faster-whisper snapshot pré-cached sem download; estrito somente provider STT local do perfil efetivo. TTS existente via `text_to_speech_tool` em provider command isolado Microsoft SAPI pt-BR (não persistiu no perfil do usuário); sem VoiceStudio, Google AI Studio, nova engine ou env config global. Python global test GREEN e native proof em venv 3.11. Cron `job.model > cron.model > model.default` validado com configuração temporária. Nenhum WhatsApp.

## Inserir em workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md
ASR local é operação factual, sem LLM nem rede autorizada. O envelope devolve transcript e idioma **como hint configurado**, não detecção acústica; inclui hash SHA256 de arquivo e duração, sem armazenar áudio. O source não concede autoridade a Bot/TaskRun nem autoriza envio externo. A prova de TTS usa o command provider de TTS existente sobre Microsoft SAPI (voz Maria Desktop pt-BR instalada), apenas fixture de teste. O modelo `Systran/faster-whisper-base` de ~145 MB, licença MIT, foi encontrado no cache; não houve downloads. Remoto/disabled/model miss/symlink/input inválido abortam antes do backend. Condicionar rollout ao bootstrap real da Workstation e gate de canal.

## Inserir em workstation/context/engineering-journal/CURRENT.md
Preflight no checkout `main` e claims confirmado; código preexistente de STT/TTS/Cron permaneceu intocado. RED `python -m pytest -q workstation/tests/test_audio_local_runtime.py` => ModuleNotFoundError, exit 2. Após correção: 13 PASS/1 SKIP, exit 0, cobrindo os casos de segurança, idioma e model precedence. Primeiro native invocado com venv `...\hermes-agent\venv\Scripts\python.exe` falhou devido a `snowballstemmer` ausente no bootstrap Workstation; ensaio isolado importando apenas adapter sem inicializar supervisão mostrou TTS SAPI real e ASR faster-whisper real offline, `WER=0` em uma frase sintética, `ffprobe` validou WAV mono 22.050 Hz 16-bit 5,451s. Dois runs observados: TTS 16,624s e 5,553s, ASR 11,832s e 10,514s, RSS process Python 222,4 e 218 MiB; 0 tentativas network, 0 LLM. Regressão grande existente 168 PASS/4 SKIP/1 FAIL (teste STT comando progress watchdog no Windows) e reexecução isolada do mesmo teste 1 PASS, exit 0. Ruff desconhecido. Teste pós-admissão efetiva do perfil incluído. Nenhuma gravação preservada.

## Inserir em KNOWN_ISSUES.md
`HW-AUDIO-P05-01` instalação Hermes venv contém Faster-Whisper mas não `snowballstemmer`; supervisão obrigatória `workstation.__init__` não inicializa. Não desabilitar a supervisão no produto; a prova nativa usou import de arquivo em subprocesso offline, não bootstrap completo. `HW-AUDIO-P05-02` Piper/KittenTTS/NeuTTS locais não instalados; SAPI Windows por provider COMMAND só configura TTS em fixture temporária, não padrão de produção. `HW-AUDIO-P05-03` apenas um enunciado pt-BR sintético, falha STT command idle-progress sob carga, passou isoladamente; CI e corpus de qualidade pendentes. `HW-AUDIO-P05-04` módulo novo ainda não conectado ao consumidor Workstation nem à interface de WhatsApp; não afirmar voz nativa do WhatsApp. `HW-AUDIO-P05-05` o comando STT existente pode auto-download no cache miss, por isso adapter novo exige snapshot completo local e perfil local; pipelines STT legados fora desse adapter conservam comportamento anterior.

## Regra de continuidade
Manter a sequência do plano: P05 código e provas locais prontos, **não** exigir homologação produtiva como bloqueio de prompts independentes. Integrador confirma claims/HEAD antes de Git; owner documental aplica inserts respeitando WIP. Para release: reparar dependências de bootstrap Hermes em ciclo de dependência autorizado, testar import normal e perfil isolado, múltiplos clips consentidos para acurácia, CPU/RAM peak, ffprobe e licença TTS, incorporar adapter no consumidor adequado, qualificar CI e canais separadamente. Não configurar TTS cloud por engano, não baixar modelo pesado automaticamente.

## 8. Atualização final de qualificação — três execuções reais offline

Três runs NATIVE_OFFLINE_PASS, sempre com WER 0.0 na mesma frase sintética, nenhuma conexão de socket detectada e zero LLM:

| Execução | TTS (s) | ASR (s) | RSS Python ao final (MiB) | Exit |
|---|---:|---:|---:|---:|
| 1 | 16.624 | 11.832 | 222.4 | 0 |
| 2 | 5.553 | 10.514 | 218.0 | 0 |
| 3 (após guard de perfil efetivo) | 8.897 | 7.917 | 217.7 | 0 |

Variabilidade observada: TTS 5.553–16.624 s; ASR 7.917–11.832 s; RSS final 217.7–222.4 MiB. RSS não inclui subprocessos ou pico agregado.

Último comando nativo: Python 3.11.15 do venv Hermes executando workstation/tests/test_audio_local_native.py => P05_NATIVE_FINAL_POST_GUARD_EXIT=0.
Regressão final focada: python -m pytest -q workstation/tests/test_audio_local_runtime.py tests/tools/test_transcription.py tests/tools/test_stt_resolution_passive.py tests/tools/test_tts_command_providers.py tests/cron/test_cron_pinned_job_fallback.py => 91 PASS, 3 SKIP, exit 0.
Compilação de três arquivos P05 com python -m compileall -q => exit 0.

A matriz anterior de 168 PASS, 4 SKIP e 1 FAIL continua registrada. O teste existente do STT command idle-timeout falhou sob carga e passou isoladamente (1 PASS, exit 0). Nenhum código upstream foi modificado.
Adicionado guard de provider EFETIVO (local apenas) para impedir que config fornecida pelo caller transforme uma execução real em requisição STT remota. Em invocação real, o hint do idioma é proveniente do profile efetivo, não de uma alegação do caller.
