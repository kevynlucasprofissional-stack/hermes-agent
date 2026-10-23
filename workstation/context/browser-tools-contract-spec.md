# Especificação de Contrato I-3 — Ferramentas Browser Workstation

**Data:** 2026-10-22
**Fase:** I-3 (Refinamento de Contrato de Ferramenta)
**Status:** Completo — pronto para aprovação antes da Fase D-1
**Dependências:** [browser-tools-portability-report.md](./browser-tools-portability-report.md) (Findings F1–F3)

---

## Princípios Arquiteturais Obrigatórios

1. **Snapshot-first, console-optional** (Finding F1): toda validação de UI usa `browser_snapshot` como fonte primária. `browser_console` só é usado como otimização condicional e nunca como única prova.
2. **Estados explícitos**: cada ferramenta define pré-condições verificáveis e retorna códigos de erro específicos quando não atendidas.
3. **Refs diretos do snapshot**: busca e interação usam `@eN` obtido no snapshot corrente; seletores CSS/aria-label hardcoded são proibidos como caminho primário.
4. **Idempotência e segurança**: nenhuma ferramenta executa mutação destrutiva sem verificação prévia; provas de entrega são append-only.
5. **Timeout e retry**: todas as ferramentas respeitam o timeout do controller (`HERMES_WORKSTATION_BROWSER_TIMEOUT`) e não fazem retry automático de mutações (apenas reads).

---

## 1. `whatsapp_wait_for_ready`

### Propósito
Aguardar até que o WhatsApp Web esteja em estado utilizável (logado, lista de conversas visível), distinguindo QR screen, loading e ready.

### Schema de Entrada
```python
def whatsapp_wait_for_ready(
    *,
    timeout_seconds: float = 30.0,
    poll_interval: float = 1.0,
    require_logged_in: bool = True,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
```

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `timeout_seconds` | float | Não | Tempo máximo de espera (default 30s) |
| `poll_interval` | float | Não | Intervalo entre polls (default 1s) |
| `require_logged_in` | bool | Não | Se True, falha quando QR screen detectado |
| `task_id` | str | Não | Binding de task para dispatch |
| `session_id` | str | Não | Binding de sessão para dispatch |

### Schema de Saída
```json
{
  "ready": true,
  "state": "LOGGED_IN",
  "elapsed_seconds": 4.2,
  "element_count": 40,
  "snapshot_revision": 3
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `ready` | bool | True se condições satisfeitas |
| `state` | enum | `LOGGED_IN`, `QR_SCREEN`, `LOADING`, `TIMEOUT` |
| `elapsed_seconds` | float | Tempo decorrido |
| `element_count` | int | Elementos interativos no snapshot final |
| `snapshot_revision` | int | Revisão do snapshot (para cache) |
| `error_code` | str | Presente apenas se `ready=false` |

### Códigos de Erro
| Código | Condição | Ação Recomendada |
|--------|----------|------------------|
| `QR_SCREEN_DETECTED` | QR code visível no snapshot text | Usuário deve escanear QR |
| `LOADING_TIMEOUT` | Loading > timeout_seconds | Retry com backoff ou reload |
| `CONTROLLER_UNAVAILABLE` | Dispatch falha com TIMEOUT/UNAVAILABLE | Verificar controller |
| `STALE_SNAPSHOT` | element_count=0 após 3 polls consecutivos | Reload da página |

### Lógica de Detecção (Snapshot-first)
1. Poll `browser_snapshot(full=False)` a cada `poll_interval`.
2. Extrair texto do snapshot e buscar marcadores:
   - **LOGGED_IN**: texto contém `"Conversas"` OU `"Chats"` E `element_count >= 10` E ref com role `textbox` presente.
   - **QR_SCREEN**: texto contém `"Use seu telefone"` OU `"Scan the QR"` OU `"QR"`.
   - **LOADING**: texto contém `"Carregando"` OU `"Loading"` OU `element_count < 5`.
3. Probe JS via `browser_console` é OPCIONAL: se disponível e consistente com snapshot, acelera detecção; se inconsistente (Finding F1), descartar resultado do console.

### Validação Contra Pitfalls
| Pitfall | Mitigação no Contrato |
|---------|----------------------|
| `mcp__browserclaw__wait` espera menos que pedido (CRM §145) | Poll próprio com `time.monotonic()` e deadline explícito; nunca confiar em wait externo |
| Busca para de funcionar sem reload (CRM §144) | Estado `STALE_SNAPSHOT` dispara recomendação de reload |
| Console em contexto isolado (F1) | Snapshot como primário; console apenas como otimização condicional |

---

## 2. `whatsapp_send_message`

### Propósito
Enviar mensagem para contato via deep link + verificar entrega por snapshot diff append-only.

### Schema de Entrada
```python
def whatsapp_send_message(
    *,
    phone_digits: str,
    message: str,
    contact_name_hint: Optional[str] = None,
    verify_delivery: bool = True,
    delivery_timeout_seconds: float = 10.0,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
```

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `phone_digits` | str | Sim | Apenas dígitos (sem +, espaços, traços) |
| `message` | str | Sim | Texto da mensagem |
| `contact_name_hint` | str | Não | Nome esperado para validação de header |
| `verify_delivery` | bool | Não | Se True, aguarda confirmação append-only |
| `delivery_timeout_seconds` | float | Não | Timeout para prova de entrega |
| `task_id` | str | Não | Binding de task |
| `session_id` | str | Não | Binding de sessão |

### Schema de Saída
```json
{
  "sent": true,
  "state": "DELIVERED",
  "message_data_id": "false_5564996111840@c.us_ABCDEF1234567890",
  "ack_label": "Entregue",
  "header_verified": "João Silva",
  "composer_empty_after": true
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `sent` | bool | True se mensagem foi enviada |
| `state` | enum | `DELIVERED`, `SENT_UNCONFIRMED`, `NO_CONVERSATION_OPEN`, `HEADER_MISMATCH`, `COMPOSER_NOT_EMPTY` |
| `message_data_id` | str | `data-id` da última mensagem no painel |
| `ack_label` | str | `aria-label` do ícone de status (`Entregue`, `Lida`, etc.) |
| `header_verified` | str | Nome confirmado no header da conversa |
| `composer_empty_after` | bool | True se composer esvaziou após envio |
| `error_code` | str | Presente apenas se `sent=false` |

### Códigos de Erro
| Código | Condição | Ação Recomendada |
|--------|----------|------------------|
| `NO_CONVERSATION_OPEN` | Header/conversation panel ausente no snapshot | Navegar para conversa primeiro (deep link ou click) |
| `HEADER_MISMATCH` | Header não contém `contact_name_hint` | Abortar envio; verificar número/nome |
| `COMPOSER_NOT_EMPTY` | Composer não esvaziou após click em enviar | Mensagem pode não ter sido enviada; verificar snapshot |
| `DELIVERY_TIMEOUT` | Prova append-only não apareceu em `delivery_timeout_seconds` | Retornar `SENT_UNCONFIRMED`; não re-enviar automaticamente |
| `MASKED_PHONE` | `phone_digits` contém `*` ou não é puramente numérico | Rejeitar; solicitar número completo |
| `TEMPLATE_PLACEHOLDER_LEAK` | `message` contém `{NOME}` ou placeholder não substituído | Rejeitar; renderizar template antes de chamar |

### Fluxo de Execução
1. **Pré-validação**: rejeitar `phone_digits` com máscara; rejeitar `message` com placeholder não substituído.
2. **Deep link**: `browser_navigate(url=f"https://web.whatsapp.com/send?phone={phone_digits}&text={quote(message)}")`.
3. **Wait for conversation**: poll snapshot até `[data-testid="conversation-info-header"]` aparecer ou timeout.
4. **Header check**: se `contact_name_hint` fornecido, verificar presença no texto do header. Se mismatch → `HEADER_MISMATCH`.
5. **Composer assertion**: snapshot deve mostrar composer com texto normalizado igual à mensagem (`.replace(/\s+/g,' ').trim()`).
6. **Send**: `browser_click` no ref do botão `Enviar` (obtido via snapshot).
7. **Post-send proof**: poll snapshot até:
   - Composer vazio (texto do ref do composer é string vazia OU botão reverteu para "Mensagem de voz")
   - Novo `[data-id]` apareceu em `[data-testid="conversation-panel-messages"]`
8. **Delivery ack**: ler `aria-label` do último `[data-id]` para confirmar `Entregue`/`Lida`.

### Validação Contra Pitfalls
| Pitfall | Mitigação no Contrato |
|---------|----------------------|
| Stale assign: header não muda após navigate (batch-send §1B) | Header check explícito pós-navigate; `HEADER_MISMATCH` se stale |
| Composer vazio falso: zero-width node mantém innerText não-vazio (batch-send §6) | Prova de composer vazio por reversão do botão para "Mensagem de voz", não por innerText |
| Reutilizar corpo de mensagem anterior (batch-send §8, console-ui §38) | Rejeitar placeholder `{NOME}` não substituído; renderização é responsabilidade do caller |
| Telefone mascarado não gera deep link (console-ui §39) | Validação `MASKED_PHONE` na entrada |
| Mis-send não é reparável por automação (batch-send §8) | Abortar em `HEADER_MISMATCH`; nunca tentar delete sintético |
| Prova de entrega por `.message-out` é instável (batch-send §6) | Usar apenas `data-id` + `aria-label` do último elemento no painel |
| handoff_requested gate (console-ui checklist) | Respeitar gate; se recebido, retornar `handoff_id` e encerrar turno |

---

## 3. `whatsapp_search_contact`

### Propósito
Buscar contato/grupo/conversa por nome ou sufixo de telefone usando ref direto do snapshot.

### Schema de Entrada
```python
def whatsapp_search_contact(
    *,
    query: str,
    max_results: int = 5,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
```

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `query` | str | Sim | Nome, parte do nome ou últimos 4 dígitos |
| `max_results` | int | Não | Máximo de resultados retornados (default 5) |
| `task_id` | str | Não | Binding de task |
| `session_id` | str | Não | Binding de sessão |

### Schema de Saída
```json
{
  "found": true,
  "results": [
    {
      "ref": "@e16",
      "label": "João Silva",
      "subtitle": "+55 64 9987-1693",
      "type": "chat"
    }
  ],
  "search_ref": "@e12",
  "result_count": 3
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `found` | bool | True se ≥1 resultado |
| `results` | list | Lista de matches com ref, label, subtitle e type |
| `search_ref` | str | Ref do input de busca no snapshot atual |
| `result_count` | int | Total de resultados encontrados |
| `error_code` | str | Presente apenas se busca falhou |

### Códigos de Erro
| Código | Condição | Ação Recomendada |
|--------|----------|------------------|
| `SEARCH_INPUT_NOT_FOUND` | Input de busca ausente no snapshot | Reload da página (pitfall CRM §144) |
| `STALE_RESULTS` | Resultados idênticos para queries diferentes | Limpar campo, aguardar 600ms, re-buscar |
| `NO_RESULTS` | Painel mostra apenas "Mensagens" ou vazio | Contato pode não ter conversa individual; documentar como pendente |
| `CONTROLLER_TIMEOUT` | Dispatch falha | Retry com backoff |

### Fluxo de Execução
1. **Snapshot inicial**: obter ref do input de busca (role=`textbox`, label contém "Pesquisar" ou "Search").
2. **Se ref ausente**: retornar `SEARCH_INPUT_NOT_FOUND` com recomendação de reload.
3. **Type query**: `browser_type(ref=search_ref, text=query, mode="plain_text_paste")`.
4. **Wait for results**: poll snapshot até `element_count` mudar OU 2s decorridos.
5. **Parse results**: extrair refs com role `gridcell` ou `div` que contenham label + subtitle do texto do snapshot.
6. **Staleness check**: se caller fornecer `previous_result_refs` e forem idênticos aos atuais, retornar `STALE_RESULTS`.
7. **Retornar** top-N resultados com refs válidos.

### Validação Contra Pitfalls
| Pitfall | Mitigação no Contrato |
|---------|----------------------|
| Busca para de funcionar (CRM §144) | `SEARCH_INPUT_NOT_FOUND` recomenda reload; não insistir em múltiplas tentativas |
| Stale results entre queries (batch-send §2b) | `STALE_RESULTS` quando painel inalterado; limpar campo antes de re-buscar |
| Seletor localizado PT-BR vs EN (F3) | Usar ref do snapshot (role=textbox), não aria-label hardcoded |
| Contato sem conversa individual (CRM §151) | `NO_RESULTS` documenta pendência; não inventar dados |
| Painel de perfil abre no lugar da conversa (CRM §146) | Resultados incluem `type` field; caller decide se é chat/group/contact |

---

## 4. `windows_app_launch`

### Propósito
Lançar aplicativo Windows desktop, verificar janela visível (não apenas processo) e trazer para foreground.

### Schema de Entrada
```python
def windows_app_launch(
    *,
    app_name: str,
    exe_path: Optional[str] = None,
    bring_to_front: bool = True,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
```

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `app_name` | str | Sim | Nome do processo (ex: `notepad.exe`) ou título parcial |
| `exe_path` | str | Não | Caminho completo ao .exe ou .lnk; se omitido, buscar via Start Menu |
| `bring_to_front` | bool | Não | Se True, ShowWindow(SW_RESTORE) + SetForegroundWindow |
| `timeout_seconds` | float | Não | Timeout para verificação de janela |

### Schema de Saída
```json
{
  "launched": true,
  "pid": 12345,
  "window_handle": 654321,
  "window_title": "Notepad",
  "brought_to_front": true
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `launched` | bool | True se processo existe E janela visível |
| `pid` | int | PID do processo com MainWindowHandle != 0 |
| `window_handle` | int | Handle da janela principal |
| `window_title` | str | Título da janela |
| `brought_to_front` | bool | True se SetForegroundWindow executado com sucesso |
| `error_code` | str | Presente apenas se `launched=false` |

### Códigos de Erro
| Código | Condição | Ação Recomendada |
|--------|----------|------------------|
| `APP_NOT_FOUND` | Processo não encontrado após launch | Verificar `exe_path` ou nome |
| `WINDOW_NOT_VISIBLE` | Processo roda mas MainWindowHandle=0 | App pode ser tray-only ou ainda carregando |
| `FOREGROUND_FAILED` | SetForegroundWindow retornou false | Permissão UAC ou outra janela modal bloqueando |
| `NOT_WINDOWS` | Plataforma não é Windows | Usar alternativa POSIX |
| `LAUNCH_TIMEOUT` | Janela não apareceu em `timeout_seconds` | Verificar logs do app |

### Implementação Standalone
Esta ferramenta NÃO usa o dispatcher browser. Implementação via `subprocess.run` + PowerShell:
1. Se `exe_path` fornecido: lançar diretamente.
2. Se apenas `app_name`: resolver via `Get-StartApps` ou busca em Start Menu.
3. Verificar `MainWindowHandle != 0` via `Get-Process`.
4. Se `bring_to_front`: P/Invoke `ShowWindow(SW_RESTORE=9)` + `SetForegroundWindow`.
5. Sempre `background=true` (GUI apps são long-lived).

### Validação Contra Pitfalls
| Pitfall | Mitigação no Contrato |
|---------|----------------------|
| `cmd //c start` parece OK mas janela não aparece (win-launch §127) | Verificação obrigatória de `MainWindowHandle != 0`; nunca confiar em exit code |
| Chromium spawns 5-20 processos (win-launch §131) | Filtrar por `MainWindowHandle != 0`; apenas UM tem janela |
| "Didn't open" = opened behind others (win-launch §133) | `bring_to_front` com ShowWindow(SW_RESTORE) antes de SetForegroundWindow |
| MSYS `//` escaping quebra filtros (win-launch §129, §136) | Usar PowerShell nativo, não cmd/tasklist via MSYS |
| GUI apps são long-lived (win-launch §135) | Launch sempre em background; nunca esperar exit |

---

## 5. Cache de Snapshot Integrado ao WFR

### Propósito
Evitar snapshots redundantes durante polling quando o DOM não mudou, reduzindo latência e custo de tokens.

### Mecanismo
Integrado diretamente em `whatsapp_wait_for_ready` (não é ferramenta separada).

### Lógica
```
prev_element_count = None
prev_snapshot_text_hash = None
cache_hits = 0

for each poll:
    raw = browser_snapshot(full=False)
    current_count = raw.element_count
    current_hash = hash(raw.snapshot_text[:500])  # prefixo suficiente
    
    if current_count == prev_element_count and current_hash == prev_snapshot_text_hash:
        cache_hits += 1
        if cache_hits >= 3:
            # DOM estável demais; possível stale
            return STALE_SNAPSHOT
        continue  # reusar avaliação anterior
    
    # DOM mudou; reavaliar condições
    cache_hits = 0
    prev_element_count = current_count
    prev_snapshot_text_hash = current_hash
    evaluate_readiness(raw)
```

### Validação Contra Pitfalls
| Pitfall | Mitigação |
|---------|-----------|
| Snapshot desatualizado após navegação | Hash do texto detecta mudança; cache invalidado |
| element_count estável mas conteúdo mudou | Hash do prefixo do texto como segundo critério |
| 3+ caches consecutivos = possível stale | `STALE_SNAPSHOT` após 3 hits sem mudança |

---

## Matriz de Validação Contrato-vs-Pitfalls

| Pitfall (origem) | Ferramenta Afetada | Mitigação no Contrato | Status |
|------------------|--------------------|-----------------------|--------|
| Busca para de funcionar sem reload (CRM §144) | `whatsapp_search_contact` | `SEARCH_INPUT_NOT_FOUND` → recomenda reload | ✅ Coberto |
| `wait` espera menos que pedido (CRM §145) | `whatsapp_wait_for_ready` | Poll próprio com `time.monotonic()` | ✅ Coberto |
| Painel de perfil abre no lugar da conversa (CRM §146) | `whatsapp_search_contact` | Campo `type` nos resultados | ✅ Coberto |
| innerText ambíguo com citações (CRM §147) | `whatsapp_send_message` | Prova por `data-id`/`aria-label`, não innerText | ✅ Coberto |
| Progresso JSON corrompido por append (CRM §148) | Todas | N/A (não escrevem arquivos de progresso) | ⬜ Fora de escopo |
| Evaluate com JSON inválido (CRM §149) | `whatsapp_wait_for_ready` | Snapshot-first; console opcional | ✅ Coberto |
| Contato sem conversa individual (CRM §151) | `whatsapp_search_contact` | `NO_RESULTS` documenta pendência | ✅ Coberto |
| Stale assign não muda header (batch-send §1B) | `whatsapp_send_message` | Header check explícito; `HEADER_MISMATCH` | ✅ Coberto |
| Composer vazio falso por zero-width node (batch-send §6) | `whatsapp_send_message` | Prova por reversão do botão, não innerText | ✅ Coberto |
| Reutilizar corpo de msg anterior (batch-send §8) | `whatsapp_send_message` | Rejeitar placeholder não substituído | ✅ Coberto |
| Telefone mascarado não gera deep link (console-ui §39) | `whatsapp_send_message` | Validação `MASKED_PHONE` na entrada | ✅ Coberto |
| Mis-send não reparável por automação (batch-send §8) | `whatsapp_send_message` | Abortar em `HEADER_MISMATCH`; nunca delete sintético | ✅ Coberto |
| Prova `.message-out` instável (batch-send §6) | `whatsapp_send_message` | Usar apenas `data-id` + `aria-label` | ✅ Coberto |
| `handoff_requested` gate (console-ui checklist) | Todas | Respeitar gate; retornar `handoff_id` | ✅ Coberto |
| `cmd //c start` janela invisível (win-launch §127) | `windows_app_launch` | Verificação obrigatória `MainWindowHandle` | ✅ Coberto |
| Chromium múltiplos processos (win-launch §131) | `windows_app_launch` | Filtrar por `MainWindowHandle != 0` | ✅ Coberto |
| "Didn't open" = behind others (win-launch §133) | `windows_app_launch` | `bring_to_front` com SW_RESTORE | ✅ Coberto |
| MSYS `//` escaping (win-launch §129, §136) | `windows_app_launch` | PowerShell nativo, não cmd | ✅ Coberto |
| Console em contexto isolado (F1) | Todas browser | Snapshot-first; console opcional | ✅ Coberto |
| Seletores de envio só com conversa aberta (F2) | `whatsapp_send_message` | Estados `NO_CONVERSATION_OPEN` / `READY_TO_SEND` | ✅ Coberto |
| Seletor de busca localizado PT-BR (F3) | `whatsapp_search_contact` | Ref direto do snapshot | ✅ Coberto |

**Total:** 21 pitfalls mapeados, 20 cobertos pelo contrato, 1 fora de escopo (progresso JSON é responsabilidade do caller/skill).

---

## Regras Globais para Implementação (D-1)

1. **Não modificar arquivos `.ts` do Electron.**
2. **Todas as funções browser devem usar `_dispatch` com binding válido** (`task_id` + `session_id`).
3. **`windows_app_launch` é standalone**: usa `subprocess.run` + PowerShell, não entra no dispatcher.
4. **Docstrings Python** devem conter schema de entrada/saída e códigos de erro conforme este documento.
5. **Testes unitários** devem mockar `_dispatch` para validar lógica de parsing de snapshot sem controller real.
6. **`PYTHONIOENCODING=utf-8`** em todos os scripts Python.
7. **Respeitar claims ativos**: verificar `multi_agent_coordination.py status` antes de qualquer escrita em `tools/browser_workstation.py`.

---

## Próximo Passo

Fase D-1: Implementação Incremental. Ver prompt de continuação abaixo.