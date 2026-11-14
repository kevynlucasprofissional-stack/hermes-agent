# PROMPT 05 — Homologação ASR/TTS local e configuração de modelo por automação

**Missão.** Transformar mecanismos de áudio e seleção de modelos já existentes em capacidade qualificada do Hermes, sem instalar VoiceStudio, duplicar TTS ou automatizar Google AI Studio.

**Preflight.** Reservar somente configuração de runtime de áudio e testes; conferir `tools/transcription_tools.py::transcribe_audio`, `tools/transcription_local.py`, `agent/transcription_provider.py`, `tools/tts_tool.py::text_to_speech_tool`, `tools/tts_tool_local.py`, `agent/tts_provider.py`, `tools/cronjob_job_args.py` e configuração `cron.model`/`cron.model_provider`. Não instalar modelos pesados automaticamente em máquina compartilhada; verificar licenças, dependências e memória antes.

**Execução.** (1) Criar fixtures de áudio sintético/consentido e texto português em diretório temporário; (2) diagnosticar dependências instaladas por provedor sem imprimir segredos, testar `faster-whisper` local com presets pequenos (por ex. `base`/`small` + `int8` em CPU se suportado) e TTS já configurado, medindo latência, RSS, qualidade e formato; (3) adicionar ou reparar adaptador determinístico `path -> transcribe_audio -> {text,language,provenance}` no runtime existente, sem chamar LLM durante transcrição; (4) teste de síntese `text -> áudio real` com ffprobe quando disponível; (5) validar precedência modelo do job > default Cron > modelo do agente, sem criar configuração global duplicada.

**Testes e aceite.** RED para falhas de dependência, input ausente, arquivo grande, língua pt-BR, áudio inválido, provedor desabilitado, outbound network acidental; GREEN com fixture de áudio verdadeiro e comando real. Registrar comandos, provider, versionamentos, CPU/RAM e variabilidade. Não afirmar voz nativa WhatsApp; isso fica em gate separado. Evitar distribuir gravações ou dados de voz de pessoas.

---

## Formato de entrega obrigatório para CADA prompt

Entregar ao final: (a) HEAD/branch/dirty inicial e final; (b) caminhos sob claim do agente e integrador dono de commit; (c) contrato/decisões e desvios justificados; (d) diffs por arquivo; (e) evidência RED + GREEN com comandos e exits; (f) validação nativa onde exigida; (g) segurança e riscos residuais; (h) Known Issues que continuam abertos; (i) atualização incremental do `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md` e `workstation/context/engineering-journal/CURRENT.md` somente pelo owner documental, ou handoff de inserts caso esses arquivos estejam claimed. Não chamar `DONE/RELEASE` para teste sintético ou código não integrado.
