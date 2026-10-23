# Investigação de Wall Time — Fase D-3a
**Data:** 2026-10-23
**Status:** ✅ CONCLUÍDO — regressão corrigida

## Diagnóstico
O breakdown dos tempos D-2 revelou que `whatsapp_send_message` consumia **93% do wall time** (mediana 10,44s de 11,19s total) devido ao `DELIVERY_TIMEOUT` padrão de 10s. O classificador `_classify_wa_state` teve overhead desprezível (0,1ms/call).

| Etapa | Mediana D-2 | % do Total |
|-------|-------------|------------|
| WFR | 0,36s | 3% |
| Search | 0,69s | 6% |
| Send | 10,44s | **93%** |

## Testes de Timeout Reduzido
| Timeout | Wall Time | Sent | State |
|---------|-----------|------|-------|
| 10s (original) | ~10,4s | ✅ | SENT_UNCONFIRMED |
| 5s | 7,70s | ✅ | SENT_UNCONFIRMED |
| 3s | 4,81s | ✅ | SENT_UNCONFIRMED |

**Conclusão:** 3s mantém 100% de taxa de envio e reduz wall time em ~54%. O estado `SENT_UNCONFIRMED` é esperado quando o ack do WhatsApp demora >3s; a mensagem foi enviada com sucesso (`sent=True`).

## Correção Aplicada
- **Arquivo:** `tools/browser_workstation.py` linha ~1828
- **Mudança:** `delivery_timeout_seconds: float = 10.0` → `3.0`
- **Trade-off documentado:** confirmação de entrega pode retornar `SENT_UNCONFIRMED` em redes lentas; aumentar para 5-10s se prova de ack for obrigatória.

## Validação Pós-Correção (Mini-Bateria D-3)
3 sessões otimizadas com timeout padrão de 3s:

| Sessão | Wall Time | Send Time | Sent |
|--------|-----------|-----------|------|
| 1 | 5,35s | 3,62s | ✅ |
| 2 | 4,46s | 3,62s | ✅ |
| 3 | 4,41s | 3,56s | ✅ |

**Mediana D-3: 4,46s** vs Baseline D-2: 5,56s → **-19,8%** ✅
**Taxa de envio: 100%** vs Baseline D-2: 0% → **+100pp** ✅

## Critério de Aceite
- ✅ Wall time otimizado ≤ baseline + 10% → **ATINGIDO (-19,8%)**
- ✅ Taxa de sucesso ≥ baseline → **ATINGIDO (100% vs 0%)**
- ✅ Overhead de classificador descartado como causa (0,1ms)
- ✅ Cache stale não é mais fator dominante após invalidação correta