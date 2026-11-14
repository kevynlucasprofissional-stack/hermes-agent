## 2026-10-26 — Direção 80/20: eventos, upload Browser e execução verificável (PLANNED / NOT RELEASE)

**Referência:** kit de implementação `PLANO_IMPLEMENTACAO.md` e `PROMPTS_IMPLEMENTADOR.md` (gerado fora do repositório). **Estado:** investigação de leitura e código de referência isolado; nenhum commit, merge, escrita direta no Hermes ou qualificação de release nesta etapa.

### Sequência proposta, respeitando claims e gates

1. **HW-IMP-01 (alta prioridade):** corrigir `browser_file_upload` existente. Atualmente CDP `DOM.setFileInputFiles` está no Browser Electron, mas a ação não aparece no `mutating` Set observado. Corrigir autorização/admission, `realpath`, escopo de arquivos, pós-condição/recibo, privacidade de caminhos e teste Electron real. Não disparar envios WhatsApp.
2. **HW-IMP-02:** estender `TrelloClient` com leitura oficial de `/actions`, paginação real e journal idempotente, sem novo Kanban. Tabelas de eventos/checkpoints com migration na base canônica aprovada, fonte Trello permanece autoridade de cartões.
3. **HW-IMP-03:** Bot narrativo diário fundado no journal Trello; primeiro entrega interna/dry-run, depois canais externos autorizados e qualificados.
4. **HW-IMP-04:** adapter de eventos de negócio → `execute_job_for_event()` já existente, com outbox/idempotência e nenhuma atribuição automática de intenção a eventos genéricos.
5. **HW-IMP-05:** qualificar ASR/TTS locais e seleção de modelo de Cron/Bots existente em um único pacote técnico. Não criar modelos/transcritores paralelos.
6. **HW-IMP-06:** MVP de um monitor de página/elemento, configurável e observacional. O `MutationObserver` de cache/aprendizagem não é monitor durável. Respeitar browser lease, origem, logout e cleanup.
7. **HW-IMP-07:** fechar WA-M3-01 com projeção nativa de evidência, sem envio real. M4–M6 continuam HOLD sem gate.
8. **HW-IMP-08/09:** memória semântica por contato e demandas WhatsApp → triagem Kanban como duas entregas separadas, com privacidade, fonte e dedup.
9. **HW-IMP-10:** replay supervisionado Modo Aprender com TaskRun/readback independente; CandidateLesson permanece inerte até sucesso comprovado.
10. **HW-IMP-11/12 (opcionais):** benchmarks isolados Moli e EmbeddingGemma 2. Sem incorporação antecipada.

### Gates

- Todas as implementações: claim exclusivo de paths, preservação de WIP, testes RED/GREEN, regressão e journal com evidências reproduzíveis.
- Browser: autoridade de sessão/TaskRun, operação idempotente, controle de mutação, Electron/Chromium real, sem falso sucesso.
- WhatsApp: `WA-M3-01` mantém HOLD; `UNCERTAIN` não pode ser tratado como `FAILED` reutilizável.
- Nenhum status `RELEASE_QUALIFIED` deriva de snippets ou testes em sandbox separado.
