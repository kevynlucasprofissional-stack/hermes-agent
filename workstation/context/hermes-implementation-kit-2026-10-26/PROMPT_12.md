# PROMPT 12 (OPCIONAL, NÃO PRIORITÁRIO) — Pesquisa EmbeddingGemma 2

**Missão.** Validar exclusivamente a utilidade de EmbeddingGemma 2 na **recuperação** multimodal, não transcrição ASR ou raciocínio. Inspecionar `agent/memory_provider.py`, indexadores existentes, licença/model card e configuração local. Não adicionar ao caminho crítico nem armazenar WhatsApp bruto.

**Etapas.** Propor corpus sintético consentido com texto/imagem/áudio/documentos e consultas cruzadas; comparar com busca determinística/BM25/embedding existente, medindo recall@k, latência, RSS, custo de indexação e falsos positivos. Executar benchmark isolado e produzir API pequena de backend candidato apenas se superar baseline de forma significativa. Proibir migração de dados reais sem consentimento e plano de rollback. Emitir GO/NO-GO; não apresentar como alternativa ao faster-whisper.

---

## Formato de entrega obrigatório para CADA prompt

Entregar ao final: (a) HEAD/branch/dirty inicial e final; (b) caminhos sob claim do agente e integrador dono de commit; (c) contrato/decisões e desvios justificados; (d) diffs por arquivo; (e) evidência RED + GREEN com comandos e exits; (f) validação nativa onde exigida; (g) segurança e riscos residuais; (h) Known Issues que continuam abertos; (i) atualização incremental do `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md` e `workstation/context/engineering-journal/CURRENT.md` somente pelo owner documental, ou handoff de inserts caso esses arquivos estejam claimed. Não chamar `DONE/RELEASE` para teste sintético ou código não integrado.
