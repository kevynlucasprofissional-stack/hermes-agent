# Protocolo de Bateria E2E Comparativa — Fase D-2

**Data:** 2026-10-23
**Task ID ativo:** `20261023_011843_600d99`
**Contato de teste:** próprio número do usuário (+55 64 9247-0988) — seguro, não envia para terceiros
**Critério de aceite:** ≥15% redução de wall time mediano sem regressão na taxa de sucesso

---

## Cenário Padronizado

Cada sessão executa a sequência: **wait-for-ready → search contact → send message**.

### Mensagem de teste
```
[E2E-TEST] Sessão {tipo}-{número} às {timestamp}. Ignorar.
```

### Métricas coletadas por sessão
| Métrica | Unidade | Como medir |
|---------|---------|------------|
| Wall time total | segundos | `time.monotonic()` início→fim |
| Nº chamadas de ferramenta | contagem | contador manual |
| Sucesso | bool | mensagem entregue (prova de entrega) |
| Estado final WFR | string | `state` retornado |

---

## Baseline (3 sessões) — Composição Manual

Para cada sessão N ∈ {1,2,3}:

1. `browser_snapshot(full=False)` → verificar `#pane-side` ou `Conversas`
2. `browser_click(ref=@e12)` → clicar no textbox de busca
3. `browser_type(ref=@e12, text="Kevyn")` → digitar nome
4. `browser_snapshot(full=False)` → identificar conversa nos resultados
5. `browser_click(ref=<resultado>)` → abrir conversa
6. `browser_snapshot(full=False)` → confirmar header `[data-testid="conversation-info-header"]`
7. `browser_navigate(url="https://web.whatsapp.com/send?phone=556492470988&text=<encoded>")` → deep link
8. `browser_snapshot(full=False)` → confirmar composer preenchido
9. `browser_click(ref=<send_button>)` → enviar
10. `browser_snapshot(full=False)` → provar entrega (`[data-id]` + ack)

Registrar em `e2e-results/baseline-session-{N}.json`.

---

## Otimizado (3 sessões) — Ferramentas Nativas

Para cada sessão N ∈ {1,2,3}:

1. `whatsapp_wait_for_ready(timeout_seconds=15, task_id=TASK_ID)`
2. `whatsapp_search_contact(query="Kevyn", task_id=TASK_ID)`
3. `whatsapp_send_message(phone_digits="556492470988", message="[E2E-TEST] otimizada-{N} {timestamp}", task_id=TASK_ID)`

Registrar em `e2e-results/optimized-session-{N}.json`.

---

## Análise Comparativa

```
delta_pct = (baseline_median - optimized_median) / baseline_median × 100
APROVA se delta_pct ≥ 15 AND success_rate_optimized ≥ success_rate_baseline
```

## Notas Operacionais

- Cache habilitado: `HERMES_BROWSER_SNAPSHOT_CACHE=1`
- Correção aplicada: falso positivo de QR screen quando "QR Code" aparece em corpo de mensagem
- Não enviar para contatos reais de produção
- Se `/v1/action` timeout, verificar known issue de admissões unbound