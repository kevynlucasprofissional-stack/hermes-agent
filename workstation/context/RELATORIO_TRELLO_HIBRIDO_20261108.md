# Hermes Work — Trello/Database: QA3 homologado e política de transporte (08/11/2026)

## Resultado

**QA3 — Hermes → Trello (título): HOMOLOGADO no Browser nativo, em quadro privado isolado.**

- Cartão: https://trello.com/c/nzlI4GhN (quadro privado `Hermes Sync QA`, lista `QA`).
- Título anterior: `Hermes Sync QA - two operation test`.
- Título novo: `Hermes Sync QA - two step push validated 20261108`.
- Cópia local QA: `%LOCALAPPDATA%\HermesWorkstation\QA\trello-push-3-20261108` (separada dos dados institucionais).
- BrowserTask: `trello-qa3-push-20261108`; operação submetida exatamente **uma vez**.
- Baseline igual confirmada por leitura do Browser; edição local via overlay `expected_revision=0 → 1`, planejamento por campo `push`, intenção durável registrada ANTES das operações de escrita.
- Intenção `12be978fa45c39829709d3214282a1de`: estado final `verified`, sem falha; recibo da ação `type` (`...:0:...`) e recibo independente do `browser_press Enter` (`...-commit:...`) registrados; recarga da página e leitura de volta confirmaram o título.
- **Verificação externa independente**: `trelloReadCard(get)` do cartão QA3 confirmou o mesmo título no servidor Trello. Não houve reenvio.
- QA1 e QA2 anteriores continuam em `uncertain`, **não foram repetidos nem reconciliados automaticamente**.

## Nova regra: transporte selecionado por permissão

**Decisão do usuário:** para quadros sob administração/controle de sua conta, permitir **API oficial Trello**; para quadros nos quais é apenas membro comum, usar **Browser nativo controlado pelo agente**.

- Novo `workstation/trello_sync_transport.py::route_for_board`: usa o cliente REST já existente `workstation.prefabs.trello.TrelloClient` e três leituras autenticadas pela mesma credencial: `GET /1/members/me`, `GET /1/boards/{id}`, `GET /1/boards/{id}/memberships`. Cruza o ID real do usuário com a participação naquele quadro; `memberType=admin → api`, `normal → browser`, outro/ausente/inativo/inconsistente → `hold`. Rejeita quadro arquivado, identidade divergente e IDs inválidos. Nenhuma mutação no Trello.
- Plugin do runtime `plugins/workstation_database_agent`: oitava ferramenta `workstation_db_trello_route` com consulta de permissão **somente leitura**, resolvendo credenciais via `Credential.from_secret_scope()` do perfil. Não faz fallback para segredos globais de outro perfil; se credenciais faltarem ou API falhar, responde `hold`, sem presumir controle.
- **Dados atuais da conta, verificados pelo Trello conectado ao ChatGPT**: `ACIRV + VCOM: SCRUM` (ID `69f88f4f1f2e22c6a422976b`), `Vontade SMART` (`6a1cf65f87936426c577963b`), `+Bela` (`6a25de338bd463ea5f20ed90`) e `Hermes Sync QA` (`6aefcc8e38ac0595e0035341`) apresentaram papel `admin` para a conta conectada. **Isso é uma evidência pontual, não uma lista permanente de permissões.** O Hermes revalida no momento de decidir.
- **Browser de quadro compartilhado**: nova BrowserTask `trello-member-read-20261108` abriu em leitura `https://trello.com/c/DfKQAXnQ` e confirmou o cartão no quadro `LEADS DE ASSOCIADOS`, lista `Organizar`, status aberto. A interface agrupava esse quadro em áreas de trabalho do convidado. **A participação `normal` ainda não foi confirmada via API; nenhuma escrita.**

## Testes e preservação

- Suíte focal incluindo Cron, Database, cliente Browser, reconciliador, QA push e roteador: **103 Python PASS**, um aviso conhecido `StarletteDeprecationWarning`. Compilação dos módulos Python alterados PASS. Catálogo do agente: 8 ferramentas Database, incluindo `workstation_db_trello_route`.
- Fonte institucional `tarefas.sqlite`: **281 tarefas**; `trello.sqlite`: **395 cartões**; ambos `PRAGMA quick_check=ok`, acessados em somente leitura nesta verificação. Nenhuma reimportação, exclusão, atualização desses snapshots ou modificação dos journals QA1/QA2.
- Git: `main@f1d5ab2f03`, checkout compartilhado com alterações pré-existentes preservadas; **0 staged, nenhum commit, PR, worktree ou restart** desta intervenção. `git diff --check` nos documentos rastreados passou.
- O Trello conectado ao ChatGPT **não injeta automaticamente suas credenciais no runtime local**. O processo Python testado **não tinha** `TRELLO_API_KEY` e `TRELLO_TOKEN`. A política do roteador foi validada com transportes falsos, mas **não houve chamada de API Trello autenticada a partir do Hermes local**. A API está suportada no cliente existente; **o roteamento é de leitura, não é ainda um executor de push API**.
- Não configurar cron de sincronização enquanto faltar qualificação dos dois transportes e da reconciliação. O scheduler existente mantém `catch_up_missed=True`; não criar outro.

## Próximo gate, em ordem de prioridade

1. **API administrada:** configurar credenciais Trello com permissão adequada no escopo de segredos do **perfil Hermes** (não copiar cookies/tokens de sessões do Browser ou do ChatGPT). Provar `workstation_db_trello_route` no QA como `api`; depois implementar/aplicar uma operação de título via cliente REST já existente com intenção durável, pré-condição por versão/título e GET pós-PUT, sem retry em resultado incerto. Homologar em **novo cartão QA**, sem reusar QA1/QA2.
2. **Browser membro:** provar o papel `normal` de pelo menos um quadro compartilhado e realizar leitura paginada sem alteração. Para escrita, usar cartão de teste explicitamente autorizado em quadro de membro, com BrowserTask/lease/recibos/readback e resolução de conflitos; não criar QA em quadro institucional automaticamente.
3. Implementar mapeamento/inventário incremental de todos os cartões **abertos** e campos/coleções (checklists, comentários, anexos, atividade, arquivamento, etiquetas, prazos), preservando histórico e snapshots; o motor atual de `compare_card` cobre apenas campos escalares e ainda não implementa o ciclo completo.
4. Somente após qualificar API e Browser em ambos os sentidos, conflitos por campo e checkpoint: criar **um** cron diário do agente no scheduler existente, com `catch_up_missed=True` e sem disparos duplicados.

**Status final: QA3 Browser VERIFIED; roteador de permissão IMPLEMENTADO e TESTADO, API runtime bloqueada por credencial não configurada; sincronização bidirecional completa e Cron ainda PENDENTES.**

## Prova adicional do despachante do Hermes

O despacho real model_tools.handle_function_call(workstation_db_trello_route, QA_BOARD_ID) retornou ok=False, transport=hold, reason=trello_profile_credentials_unavailable (exit 0), sem chamada de escrita ou vazamento de chave/token. AI Control segue true.


## 2026-11-08 - API_REST_QA_P0_20261108: novo handoff

Nova fatia QA-only: workstation/trello_sync_api.py com planejamento por API e push de titulo por REST usando o TrelloClient existente, journal duravel da mesma base local-edits.sqlite, preflight da permissao admin, um PUT no maximo, readback e HOLD sem retry. Ferramentas do agente workstation_db_trello_api_plan e workstation_db_trello_api_push registradas. 114 testes Python PASS, um warning Starlette. Despacho real do agente com perfil local retornou HOLD porque TRELLO_API_KEY/TRELLO_TOKEN nao existem no escopo; nenhum API PUT real. Originais 281 tasks/395 cards integro; QA1/2 uncertain, QA3 verified e intocados. Relatorio detalhado RELATORIO_TRELLO_API_20261108.md. Nao ativar cron.
