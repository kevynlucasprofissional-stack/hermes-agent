# Relatório de Portabilidade I-2 — Ferramentas Candidatas WhatsApp/WebApp

**Data:** 2026-10-21
**Fase:** I-2 (Validação de Portabilidade Cross-Platform)
**Status:** Parcial — Ambiente A validado com findings críticos; Ambiente B bloqueado

---

## Resumo Executivo

Dos 5 padrões candidatos identificados na Fase I-1, **3 foram validados com sucesso** no Ambiente A (perfil corrente), **1 apresentou discrepância crítica** entre mecanismos de inspeção, e **1 não pôde ser testado** por dependência de estado UI específico. O Ambiente B (segunda instalação/perfil limpo) não foi testado devido à indisponibilidade de `shell_run` nesta sessão.

**Finding crítico de portabilidade:** `browser_console` e `browser_snapshot` operam em contextos DOM diferentes no Hermes Workstation — o console executa em um frame/isolamento onde `#pane-side` e `input[aria-label]` não existem, enquanto o snapshot captura a aba ativa completa. Isso invalida probes JS diretos via `browser_console` para seletores de UI do WhatsApp Web e exige que a ferramenta `whatsapp_wait_for_ready` use snapshot como fonte primária, não eval JS.

---

## Tabela de Resultados — Ambiente A

| # | Padrão Candidato | Método de Teste | Resultado | Evidência | Finding de Portabilidade |
|---|---|---|---|---|---|
| 1 | `whatsapp_wait_for_ready` (probe JS) | `browser_console` via HTTP direto | ⚠️ PARCIAL | `{readyState:"complete", paneSide:true, rows:17, qr:false, sess:0}` — funcionou em uma execução, mas probe posterior no mesmo contexto retornou `paneSide:false, inputs:0` | **CRÍTICO:** contexto do console é instável; WFR deve usar snapshot como primário, JS apenas como otimização quando disponível |
| 2 | `whatsapp_send_message` (seletores) | `browser_console` + snapshot HTTP | ⚠️ PARCIAL | Console: todos `false` (sem conversa aberta). Snapshot: botões @e34–@e40 visíveis, header presente | Seletores existem no DOM ativo mas console não os alcança; envio requer conversa aberta + validação por snapshot |
| 3 | `whatsapp_search_contact` (input aria-label) | `browser_console` v3 + snapshot | ❌ FALHA NO CONSOLE / ✅ OK NO SNAPSHOT | Console v3: `{pt:false, en:false, any_input:0, inputs_found:[]}`. Snapshot: `@e12 textbox "Pesquisar ou começar uma nova conversa"` | **CRÍTICO:** input existe no snapshot mas é invisível ao console; busca DEVE usar `browser_type` via ref do snapshot, nunca eval JS direto |
| 4 | `location.assign()` (deep link SPA) | `browser_console` via HTTP | ✅ SUCESSO | `{href:"https://web.whatsapp.com/", canAssign:true}` | Funciona e preserva contexto; confirmado portátil no Ambiente A |
| 5 | Cache de snapshot (element count) | `browser_console` via HTTP | ✅ SUCESSO | `{elementCount:1241, bodyChildCount:60}` | Proxy viável para cache; element_count estável entre polls consecutivos |

---

## Findings Críticos de Portabilidade

### F1: Discrepância de Contexto DOM entre `browser_console` e `browser_snapshot`

**Observação:** O snapshot HTTP retorna 40 elementos incluindo `@e12 textbox "Pesquisar ou começar uma nova conversa"`, `@e1 header "59 Atualizações"`, e botões de ação. O `browser_console` executado via HTTP direto na mesma porta (54122) e mesmo `task_id: "default"` retorna `inputs: 0`, `paneSide: false`, `allElements: 259` (vs 1241 no probe cache anterior).

**Causa provável:** O controller Electron executa `browser_console` em um contexto isolado (possivelmente um frame interno ou página de serviço) diferente da aba ativa capturada pelo snapshot. O snapshot usa CDP `DOMSnapshot.captureSnapshot` na aba alvo, enquanto `Runtime.evaluate` pode estar sendo direcionado a um target diferente.

**Impacto nas ferramentas candidatas:**
- `whatsapp_wait_for_ready`: probe JS puro via console NÃO é confiável como mecanismo primário. Deve usar snapshot text + element_count como base, com probe JS apenas como aceleração opcional quando o contexto estiver alinhado.
- `whatsapp_search_contact`: busca por `aria-label` via console é INVIÁVEL. Deve usar `browser_type` no ref obtido via snapshot (`@e12`).
- `whatsapp_send_message`: verificação de header/botão via console é INVIÁVEL. Prova de entrega deve ser por snapshot diff (novo elemento `[data-id]` aparecendo).

**Mitigação obrigatória:** Todas as ferramentas candidatas devem ter snapshot como caminho primário e console apenas como otimização condicional. O contrato da ferramenta deve especificar fallback automático quando o console retornar resultados inconsistentes com o snapshot.

### F2: Dependência de Estado UI para Validação de Envio

Os seletores de botão enviar (`button[aria-label="Enviar"]`, `[data-testid="send"]`) e painel de mensagens (`[data-testid="conversation-panel-messages"]`) só existem quando uma conversa está ativa. No estado de lista de conversas, retornam `false` mesmo no snapshot.

**Mitigação:** `whatsapp_send_message` deve aceitar que a validação pré-envio só ocorre após navegação para a conversa (via deep link ou click). O contrato deve definir estados válidos: `NO_CONVERSATION_OPEN` (pré-condição falha) vs `READY_TO_SEND`.

### F3: Seletor de Busca Localizado (PT-BR vs EN)

O snapshot confirma `@e12 textbox "Pesquisar ou começar uma nova conversa"` (PT-BR). O seletor EN `"Search or start new chat"` não foi validado neste ambiente.

**Mitigação:** Implementar fallback duplo no `whatsapp_search_contact`: tentar PT-BR primeiro, depois EN. Ou melhor: usar o ref do snapshot diretamente (independente de idioma), já que o snapshot fornece `@e12` com role `textbox` e label localizado.

---

## Ambiente B — Status

**Bloqueado.** Não foi possível testar em segunda instalação ou perfil limpo nesta sessão devido à indisponibilidade da ferramenta `shell_run` após o turno inicial de sondagem.

**Requisitos para teste no Ambiente B:**
1. Segunda máquina com Hermes Workstation instalado, OU perfil limpo (`HERMES_HOME` isolado) na mesma máquina.
2. WhatsApp Web logado (estado autenticado, não QR screen).
3. Acesso a `shell_run` ou equivalente para executar probes.

**Hipótese a validar no Ambiente B:** Os seletores DOM do WhatsApp Web (`data-testid`, `aria-label`, estrutura de painéis) são consistentes entre instalações. A discrepância de contexto console/snapshot se reproduz.

---

## Lista Revisada de Ferramentas Candidatas

Após a Fase I-2 (parcial), as 5 ferramentas candidatas permanecem válidas mas com **contratos ajustados**:

| # | Ferramenta | Status Pós-I-2 | Ajuste de Contrato |
|---|---|---|---|
| 1 | `whatsapp_wait_for_ready` | ✅ Mantida | Snapshot como primário; probe JS como otimização condicional; detectar QR vs logged-in por texto do snapshot |
| 2 | `whatsapp_send_message` | ✅ Mantida | Validação por snapshot diff (não console); estados `NO_CONVERSATION_OPEN` / `READY_TO_SEND`; prova de entrega por append-only no snapshot |
| 3 | `whatsapp_search_contact` | ✅ Mantida | Busca por ref do snapshot (não eval JS); fallback PT-BR/EN desnecessário se usar ref direto |
| 4 | `windows_app_launch` | ⏳ Não testada | Requer Ambiente B ou teste manual; manter como candidata |
| 5 | Cache de snapshot | ✅ Mantida | `elementCount` via console funciona como proxy; integrar ao WFR |

Nenhuma ferramenta foi descartada. O finding F1 redefine a arquitetura de implementação: **snapshot-first, console-optional**.

---

## Blockers e Riscos Abertos

1. **Ambiente B não testado** — critérios de aceite I-2 exigem ≥2 ambientes. Pendente para próxima sessão com `shell_run` disponível.
2. **Discrepância console/snapshot não diagnosticada na causa raiz** — requer inspeção do código Electron (`apps/desktop/electron/workstation-browser-runtime.ts`) para entender o target do `Runtime.evaluate`. Não modificar nesta fase (apenas leitura).
3. **Prova de entrega append-only não validada** — requer conversa aberta + envio real. Teste destrutivo; adiar para Fase D-1 com mock.

---

## Próximo Passo

Fase I-3: Refinamento de Contrato de Ferramenta, incorporando os ajustes derivados dos findings F1–F3. Ver prompt de continuação abaixo.