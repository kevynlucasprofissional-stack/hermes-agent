## D-20261026-PROPOSED — Evolução incremental Hermes Work 80/20 (AGUARDANDO INTEGRAÇÃO)

1. **Preferir adapters existentes:** Browser upload CDP, Cron event trigger, Trello REST, Kanban bridge, ASR/TTS e Modo Aprender existentes. Proibido duplicar scheduler/Kanban/LLM watcher.
2. **Separar observação e intenção:** eventos não correlacionados não autorizam criar tarefas automaticamente; evento de negócio exige identidade estável, trilha imutável, dedup e outbox.
3. **Menor intervenção com maior impacto:** primeiro hardening de upload e vertical Trello (captura → relato), depois monitoramento e inteligência WhatsApp.
4. **No release sem prova nativa:** `WA-M3-01` e M3 Learning são HOLD; nenhuma decisão deste planejamento revoga os gates.
5. **Arquitetura de dados:** journal de mudanças é evidência/projeção na store explicitamente autorizada, nunca substituto do estado canônico. Trello permanece fonte oficial de cartão; Kanban local é fonte de TaskRun.
6. **Privacidade e prompt injection:** conteúdos de terceiros são dados não confiáveis, nunca instruções; minimização, retenção, provenance, segredos fora de logs e Git; nenhuma comunicação externa automatizada inicialmente.
7. **Governança:** nenhum agente sem projeto Hermes e claim de paths pode editar os arquivos locais, mesmo que outro MCP permita escrita irrestrita.

**Status:** PROPOSED / plan-only; aceitar no registro canônico apenas após revisão de owner e integrador.
