# Hermes Work — Database acessível ao runtime do agente (07/11/2026)

## Escopo executado
- Plugin interno `plugins/workstation_database_agent/`, habilitado no perfil local com `hermes plugins enable --no-allow-tool-override workstation_database_agent`. Sem alterações no core do Hermes.
- Três ferramentas registradas no toolset existente `file`: `workstation_db_catalog`, `workstation_db_query` e `workstation_db_save`. Descoberta confirmada em `model_tools.get_tool_definitions` inclusive com toolsets padrão.
- Consulta de snapshots relacionais existentes da ACIRV/Trello somente leitura via `workstation.acirv_datasets`; nenhuma alteração nesse importador.
- Persistência independente de registros estruturados do agente em `<HERMES_HOME>/workstation/datasets/agent-generated.sqlite`: namespace+key estáveis, tipo, título, JSON, revision, timestamps UTC; limite 128 KiB por registro, conflito explícito em atualização e idempotência de repetição. Dados sensíveis desnecessários, credenciais e binários não devem ser persistidos.
- Dados de controle a guardar quando úteis: checkpoints, decisões, relatórios estruturados, inventários, referências a artefatos com caminho/proveniência/checksum. Arquivos originais e estados canônicos de sessão/tarefa permanecem nos seus owners. Não arquivar cada mensagem/pensamento nem substituir arquivos reais por descrições.

## Evidências
- Causa da falha inicial: plugin descoberto, mas `enabled=False` por configuração do perfil. `hermes plugins show workstation_database_agent` agora indica `enabled`.
- Descoberta real do modelo: as três ferramentas aparecem em `get_tool_definitions(enabled_toolsets=['file'],skip_tool_search_assembly=True)` e na resolução padrão sem filtro de toolsets.
- `model_tools.handle_function_call` executou catálogo (3 fontes importadas), `workstation_db_save` (created/revision=1) e `workstation_db_query` (1 registro persistido e conteúdo exato), usando o perfil Windows real.
- Prova persistida: `namespace=hermes_control`, `key=workstation-db-agent-setup-2026-11-07`, no banco `agent-generated.sqlite`. Registro de controle não altera nenhum dataset ACIRV.
- `python -m pytest -q workstation/tests/test_workstation_database_agent.py`: 3 passed. `python -m py_compile`: OK.
- `node apps/desktop/scripts/hermes-nav.mjs status`: `aiControl=true`, backend v0.21.7+1590 (+1). Nenhum clique, envio de prompt ou alteração de sessão.

## Limites e continuidade
- A CLI informa que o plugin habilitado vale para **sessões seguintes**; gateway/backend já em execução pode precisar de reinicialização controlada para carregar o plugin. **Não reiniciado nesta missão**, para não interromper outra sessão.
- Não foi executada uma conversa real com o modelo tomando a decisão de persistir autonomamente. A prova cobre a lista de ferramentas do modelo e o despachante real, não uma decisão de LLM.
- O armazenamento `agent-generated.sqlite` está integrado às ferramentas do agente, mas **não é uma nova visualização do Dashboard Database** nesta missão. Não editar `workstation/acirv_datasets.py`, `plugins/workstation-board/`, snapshots Trello/ACIRV ou UI enquanto outra sessão mantém a integração dessas fontes.
- Uma inicialização de teste do `model_tools` também exibiu aviso independente de inicialização do Hermes Relay (`additional_plugins_toml`); o despacho das ferramentas Database concluiu com sucesso. Tratar separadamente se reproduzir em uso real.
- Nenhum commit ou push; worktree main compartilhado com alterações preexistentes preservadas.
