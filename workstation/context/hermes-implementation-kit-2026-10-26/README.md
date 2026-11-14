# Kit de implementação Hermes Work — 26/10/2026

## Entrega e limite de acesso

Pacote **externo ao projeto** com roadmap, instruções de 12 prompts e referências de código verificadas isoladamente. A ferramenta nomeada pelo usuário, `Windows - Agent 01`, foi consultada e confirmou identidade, saúde e projetos autorizados; **somente** `p0-mcp-isolation-20261026-3e1a4935` está autorizado. Assim, **nenhum arquivo foi gravado em `C:\Github\hermes-agent` por esta preparação**. A leitura do código existente se apoiou em acesso de leitura já conectado, não em permissão de escrita do Agent 01.

O repositório tem alterações WIP, claims exclusivos e ao menos um gate WhatsApp em HOLD. Não use outro canal para ignorar o isolamento. Para integrar os documentos, é necessário habilitar o Hermes como projeto autorizado ao agente apropriado e adquirir claims de docs específicos. A operação Git de commit é responsabilidade do integrador designado.

## Conteúdo

- `PLANO_IMPLEMENTACAO.md` — decisões arquiteturais, evidência de arquivos/funções, dependências, prioridades, riscos e gates.
- `PROMPTS_IMPLEMENTADOR.md` — 10 prompts de execução principais, cada um autossuficiente; 2 experimentos opcionais, isolados do caminho crítico.
- `updates/ROADMAP.md`, `updates/HERMES_WORKSTATION_INTELLIGENCE.md`, `updates/engineering-journal-CURRENT.md`, `updates/DECISIONS.md`, `updates/KNOWN_ISSUES.md` — adições **preparadas** às fontes canônicas, não versões substitutas dos documentos existentes.
- `reference-code/trello_action_journal.py` — referência de journal SQLite de mudanças de Trello, com dedup, minimização de payload e cursor atômico. API e migration reais ainda devem ser integrados.
- `reference-tests/test_trello_action_journal.py` — 5 testes sintéticos aprovados.
- `reference-code/business_event_outbox.py` — outbox conservadora para rotas de eventos; eventos já reservados não são repetidos após falha sem reconciliação.
- `reference-tests/test_business_event_outbox.py` — 4 testes sintéticos aprovados.
- `reference-code/safe_upload_paths.mjs` — referência de validação host-side para upload; escopo explícito de raízes, `realpath` e verificação de arquivo regular. Não integra admission/recibos do Electron.
- `reference-tests/test_safe_upload_paths.mjs` — 5 testes sintéticos aprovados.
- `apply_docs_preview.py` — utilitário de prévia append-only e integração por owner **somente com claims verificados e arquivos-alvo limpos**. Recusa modificar docs WIP; não valida claims por si próprio.

## Execução

1. Um agente autorizado lê `PLANO_IMPLEMENTACAO.md` e confere os contratos reais/claims atuais.
2. Atribuir owner de documentação. Se os 5 documentos canônicos estiverem sujos, **fundir manualmente os blocos `updates/`** sem apagar conteúdo anterior; `apply_docs_preview.py` rejeita alterações locais e não deve ser usado para ultrapassar isso.
3. Com checkout limpo e autorizado, o owner pode usar `python apply_docs_preview.py --repo C:\Github\hermes-agent` para prévia e, após conferir claims manualmente, `--apply --claims-reviewed`. Uma segunda execução ignora um documento já marcado, de forma idempotente. Não executar sob uma identidade não autorizada.
4. Enviar somente o **PROMPT 01** à IA implementadora. Quando terminar com evidência, enviar 02 e assim por diante. Se claims colidirem, outras tarefas independentes (prompt 05) podem adiantar sem violações.
5. O implementador deve revisar criticamente os snippets. Eles são pontos de partida, não patches cegos. Cada versão aplicada exige TDD, regressão e qualificação nativa.

## Validação deste kit (não do Hermes)

```bash
pytest -q reference-tests/test_trello_action_journal.py reference-tests/test_business_event_outbox.py
# 9 passed
node --test reference-tests/test_safe_upload_paths.mjs
# 5 passed
python -m py_compile reference-code/trello_action_journal.py reference-code/business_event_outbox.py apply_docs_preview.py
```

## Achados importantes

- Upload CDP **já existe**, mas a ação não foi encontrada no bloco de mutações com admission; primeiro investigar/fixar essa falha específica.
- Cron event trigger, Client Trello, ASR/TTS, experiência de aprendizagem e persistência WhatsApp **já existem**; reutilizar.
- `WA-M3-01` continua HOLD: não inferir prova de envio por snapshot/ACK fraco.
- Primeiro caso de uso orientado a eventos: Trello read-only e resumo no próprio Hermes. Envio automático de relatórios por WhatsApp é etapa posterior com autorização e prova.
