# Hermes Work — P05 | ASR/TTS local + modelo por automação

Data: 2026-10-27. **STATUS: IMPLEMENTED_LOCALLY / NATIVE_OFFLINE_SMOKE_PASS / RELEASE_HOLD.** Nenhuma alteração de branch, nenhum commit, nenhum download/instalação de modelo, VoiceStudio ou automação Google AI Studio.

## 1. Fonte de verdade e configuração

Preflight dos módulos existentes:
- `tools/transcription_tools.py::transcribe_audio` é o dispatcher nativo; `tools/transcription_local.py` implementa `faster-whisper` e `local_command`. `agent/transcription_provider.py` descreve contratos de extensão, não demanda novo provedor.
- `tools/tts_tool.py::text_to_speech_tool` possui provider configurável e `type: command` via `tools/tts_command_provider.py`; `tools/tts_tool_local.py` já suporta Piper, KittenTTS e NeuTTS, mas esses pacotes não estão instalados no ambiente verificado.
- `cron/scheduler.py::_load_cron_job_config` e `_resolve_job_runtime` implementam `job.model` > `cron.model` > `model.default` do agente e `job.provider` > `cron.model_provider`, sem adicionar seletor paralelo; testes de precedência executados com config isolada. `tools/cronjob_job_args.py` não foi alterado.
- O Python global 3.13.12 **não** tem `faster_whisper`/`ctranslate2`, mas o Python 3.11.15 do venv atual do Hermes contém `faster-whisper 1.2.1`, `CTranslate2 4.8.1` e `edge-tts 7.2.7`. Edge-TTS é online e **não** foi usado.
- Modelo já em cache: `Systran/faster-whisper-base`, snapshot `ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66`, `model.bin` 145.217.532 bytes. Não baixar `small` automaticamente. `faster-whisper`, CTranslate2 e model card base: MIT; nenhuma licença de voz Microsoft foi redistribuída. Microsoft SAPI é recurso nativo do Windows, não distribuir arquivos de voz.

## 2. Alterações aplicadas em paths isolados com claim

- `workstation/audio_local_runtime.py` (novo): `resolve_cached_whisper_model(hub_dir,preset)` e `transcribe_cached_local(path,model_snapshot,config,max_bytes,transcriber)`. Adaptador restritivo em cima do **mesmo** `tools.transcription_tools.transcribe_audio`: aceita somente WAV mono PCM16 até 25 MiB e cinco minutos, recusa links simbólicos e diretórios, desabilitado/remote/local_command, exige snapshot local completo e confirma provider da configuração EFETIVA quando em execução real. Resultado `{text,language,provenance}` com SHA256 do arquivo, duração e base do idioma (`configured_hint`, não medição acústica). Não aciona LLM nem roteadores de rede; não é um novo provider nem download manager.
- `workstation/tests/test_audio_local_runtime.py` (novo): TDD RED inicial import ausente (exit 2), validação, metadata, provider disabled, remote, missing model/dependency, input inválido, tamanho, hash, pt-BR e precedência real do Cron. Unit tests executados com Python global; transcriber fake não causa rede.
- `workstation/tests/fixtures/sapi_ptbr_fixture.ps1` (novo): script de prova de síntese apenas com Microsoft SAPI, selecionando voz instalada `Microsoft Maria Desktop`, cultura `pt-BR`, e gerando WAV apenas em diretório temporário. Não é novo provedor, não incorpora voz ou mídia ao repositório.
- `workstation/tests/test_audio_local_native.py` (novo): CLI de prova nativa sob Python do Hermes 3.11.15, TTS **através do provider de comando já existente**, `text_to_speech_tool`, no HERMES_HOME temporário; depois `transcribe_cached_local` com modelo local CPU/int8, `ffprobe`, WER, RSS, durações e bloqueio de conexões no processo Python. Exclui WAV e config ao encerrar. **Não instala SAPI como provedor padrão do usuário**.
- `workstation/context/AUDIO_LOCAL_QUALIFICATION_P05_20261027.md` (este relatório) e handoff do P05 são arquivos novos.

## 3. Métricas do ensaio nativo — uma frase sintética, não corpus de qualidade

Frase sintética: “Bom dia, este é um teste de voz em português brasileiro.” Gerada por Windows Microsoft SAPI pt-BR (voz Maria Desktop) em WAV PCM s16le, mono, 22.050 Hz, 16 bits e 5,451 s, validado por `ffprobe 8.1.1`.
- Execução nativa inicial: `tts_seconds=16.624`, `asr_seconds=11.832`; transcrição exatamente igual à frase, WER=0.0; RSS do processo Python ao final=222,4 MiB (**não é pico nem inclui subprocessos**).
- Hash SHA256 do áudio temporário = `6d852d72e62d8c2cef31fee238d7fe2c1c0c1cf68608ad0257a04e0f2a22bad3`. Audio removido pelo diretório temporário após prova; não redistribuir clips de voz de terceiros.
- Conexões externas do processo Python registradas durante o ensaio: 0; chamadas LLM: 0; Google AI Studio/WhatsApp: 0; consumo externo de tokens: 0.
- Nesta amostra única, WER 0% **não** prova qualidade geral nem ausência de variação com sotaques, ruído, duração ou vocabulário. Repetir com múltiplos fixtures consentidos antes de release.

**Nota crítica de escopo:** o import normal de `workstation` no venv do Hermes dispara supervisão obrigatória e encontrou `snowballstemmer` ausente (falha antes do ASR). A prova nativa isolada carrega o novo arquivo adapter diretamente para não invocar esse bootstrap de produto, com TTS/ASR reais pelo Hermes; isso **não qualifica a inicialização completa do Hermes Workstation**. Não instalar dependências compartilhadas sem autorização. Código novo importa normalmente no Python global usado pelos testes; integração operacional completa depende de ambiente Hermes consistente.

## 4. Comandos e gates

```powershell
cd C:\Github\hermes-agent
python -m pytest -q workstation/tests/test_audio_local_runtime.py
& 'C:\Users\Kevyn Lucas\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe' workstation/tests/test_audio_local_native.py
python -m compileall -q workstation/audio_local_runtime.py workstation/tests/test_audio_local_runtime.py workstation/tests/test_audio_local_native.py
```

- TDD RED: módulo `workstation.audio_local_runtime` inexistente, `ModuleNotFoundError`, exit 2. GREEN inicial 9 PASS + 1 SKIP; depois expandido para 13 PASS + 1 SKIP, exit 0.
- Primeira tentativa nativa: FAIL, bootstrap supervisor obrigatório faltando `snowballstemmer`. Prova nativa isolada SAPI/Whisper: PASS, exit 0, métricas acima. Segunda execução pós-guard de perfil a registrar no histórico final.
- Regressão ampla em testes STT/TTS e Cron: 168 PASS, 4 SKIP, 1 FAIL, exit 1; teste com falha: `tests/tools/test_transcription_tools.py::test_command_stt_idle_timeout_preserves_transcription_contract[True]`. Reexecução isolada **1 PASS, exit 0**; indica sensibilidade a carga/timeout, não foi feita correção em módulo upstream. Regredir CI completo em ambiente apropriado.
- `compileall` P05: exit 0; `git diff --check` em módulos existentes não alterados: exit 0; lint Ruff não confirmado e não declarar PASS.

## 5. Modelo por Cron e recursos

Teste real de config `_load_cron_job_config` com `config.yaml` temporário:
1. `job.model=job-model` prevalece sobre `cron.model=cron-model`.
2. Sem modelo no job, `cron.model=cron-model` prevalece sobre `model.default=agent-model`.
3. Sem modelo específico no Cron, `model.default=agent-model` é aplicado.
4. `cron.model_provider=scoped-provider` permanece fallback de provedor se o job não fixa um; `job.provider` é o override validado pelo resolver existente.

Hardware: Windows 11; Ryzen 7 7735HS; RAM física ~16,44 GB; RTX 4050 disponível, não usada (CPU/int8). Modelo local ~145 MB em disco. Não modificar perfil ativo nem HERMES_HOME persistente nesta missão.

## 6. Pendências (Known Issues)

- `HW-AUDIO-P05-01`: venv Hermes não possui `snowballstemmer`, necessário ao bootstrap da supervisão Workstation; prova isolada não qualifica boot completo. Preservar isolamento até owner de dependências corrigir e testar instalação.
- `HW-AUDIO-P05-02`: Piper/Kitten/NeuTTS não presentes, Edge é backend com saída online e não foi exercitado. Via provider COMMAND já existente foi possível validar SAPI pt-BR no Windows; **não** há configuração de TTS local persistida no Bot ou perfil default. Para uso permanente, configurar explicitamente provider local aceito e licenças sem redistribuir voz.
- `HW-AUDIO-P05-03`: único áudio sintético; medir qualidade em variedade de palavras/ruído e variação frio/quente. Sem prova de entrega nativa via áudio de WhatsApp; isso é gate independente WA.
- `HW-AUDIO-P05-04`: adaptador é novo módulo importável/chamável, não houve integração ao consumidor de áudio Workstation e nem ativação de feature flag global. Nem todos os caminhos de voz automaticamente usam `transcribe_cached_local`.
- `HW-AUDIO-P05-05`: teste de timeout STT por comando falhou sob carga, passou isoladamente; não confundir ambiente carregado com baseline verde de CI.
- `HW-AUDIO-P05-06`: controles de symlink/realpath e extensão WAV não eliminam corrida TOCTOU para arquivo mutável. Teste de symlink ignorado no Windows sem direito de criar links.

## 7. Ownership e reversibilidade

Branch `main`, HEAD inicial `f1d5ab2f030e940ed4571371b0de45a21a009c9e`; arquivos oficiais ROADMAP/Intelligence/Journal estavam dirty e claimed por `chatgpt-whatsapp-m3`. P05 reservou somente seis caminhos novos sob `chatgpt-audio-p05` / `p05-audio-qualification`; owner de commit não foi definido. Nenhum commit/push/branch/worktree/reset/stash. Para remover a capacidade experimental basta retirar os novos arquivos (após aprovação do owner/integrador), pois nenhuma config persistente foi alterada.

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
