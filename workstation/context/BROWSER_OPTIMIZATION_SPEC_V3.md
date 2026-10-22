# Browser Optimization Spec V3 — Viewport Filter, PageFingerprint & Extraction LLM

> **Status:** Aprovado para Implementação (Investigação 3 Concluída)
> **Data:** 2026-10-22
> **Base:** Investigação Adversarial V2 + Refinamento Técnico V3

## 1. Visão Geral e Contratos de Interface

Esta especificação define a implementação de três vetores de otimização de browser inspirados no `browser-use`, adaptados à arquitetura do Hermes Workstation com mitigações de segurança e precisão validadas adversarialmente.

### 1.A Viewport Soft-Filter Schema

O payload projetado em `project_model_browser_payload()` (`tools/browser_workstation.py:969`) receberá marcação `offscreen` em vez de remoção silenciosa. Elementos semânticos nunca são descartados.

```json
{
  "snapshot": "...",
  "element_count": 45,
  "elements_projected": true,
  "element_index": {
    "@e1": {"name": "prompt"},
    "@e12": {"testid": "submit-btn", "offscreen": true, "y_offset": 1450}
  },
  "viewport_filter": {
    "enabled": true,
    "threshold_px": 1500,
    "offscreen_count": 3,
    "preserved_semantic_count": 2
  }
}
```

**Regras de Preservação:**
- Elementos com `role`, `testid` ou `name` definidos → sempre mantidos no `element_index` com `offscreen: true`.
- Elementos puramente decorativos fora do viewport → podem ser omitidos se `element_count > 20`.
- Fail-open obrigatório: se `element_count < 5` OU se `_find_ref_by_anchor` falhar 2x consecutivas para elementos `offscreen`, filtro desativa automaticamente.

### 1.B PageFingerprint Cache Contract

Cache implementado como wrapper no `_dispatch` (`tools/browser_workstation.py:1046`). Chave composta com invalidação imediata em mutações.

```python
# Chave de Cache
cache_key = f"{url_canonical}|{revision}|{mutation_count}|{sha256(snapshot_text[:500])[:32]}"

# Retorno HIT
{"status": "unchanged", "cached_revision": 42, "fingerprint": "a1b2c3d4...", 
 "hint": "DOM identical to previous snapshot. Use cached context."}

# Invalidação Automática
# mutation_count incrementa em: browser_click, browser_type, browser_fill,
# browser_batch_actions, browser_scroll, browser_select_option
# TTL máximo: 5 segundos (mesmo sem mutação)
```

### 1.C Extraction Router Interface

Injetado em `process_extracted_items_durably()` (`workstation/browser_projection.py:39`) ou no handler de extração.

```python
def should_use_extraction_llm(item_count: int, schema: dict | None) -> bool:
    if item_count <= 10:
        return False  # Overhead supera economia
    if schema and len(schema.get("required", [])) > 5:
        return True   # Complexidade justifica modelo dedicado
    return item_count > 10

# Fallback obrigatório:
# Se extraction_llm falhar (timeout, parse error, schema_invalid),
# retry imediato com modelo principal.
# Métrica: telemetry.record("extraction_fallback_rate", ...)
```

---

## 2. Mapa de Integração por Arquivo/Função

| Vetor | Arquivo | Função/Região | Ação |
| :--- | :--- | :--- | :--- |
| Viewport Filter | `tools/browser_workstation.py` | `project_model_browser_payload()` L969-1040 | Adicionar marcação `offscreen` no `element_index` baseado em `bounds.y` vs viewport height. |
| Viewport Filter | `workstation/operational_kernel.py` | `_find_ref_by_anchor()` L367-389 | Se ref não encontrado e elemento existe como `offscreen`, retornar erro estruturado `ELEMENT_OFFSCREEN_NEEDS_SCROLL`. |
| PageFingerprint | `tools/browser_workstation.py` | `_dispatch()` / `workstation_routed_browser_handler()` L1046+ | Wrapper de cache com chave composta. Incrementar `mutation_count` em ações de escrita. |
| Extraction LLM | `workstation/browser_projection.py` | `process_extracted_items_durably()` L39-200 | Gate condicional antes da persistência. Rota cheap-model com fallback. |
| Telemetria | `workstation/telemetry/browser_observation.py` | Novo módulo | Campos: `viewport_offscreen_count`, `snapshot_cache_hit`, `extraction_fallback_rate`. |

---

## 3. Feature Flags e Rollback

Todas as otimizações são opt-in via env var. Default: **disabled**.

| Flag | Env Var | Default | Descrição |
| :--- | :--- | :--- | :--- |
| Viewport Filter | `HERMES_BROWSER_VIEWPORT_FILTER` | `0` | Ativa soft-tag de elementos offscreen |
| Snapshot Cache | `HERMES_BROWSER_SNAPSHOT_CACHE` | `0` | Ativa deduplicação por fingerprint |
| Extraction LLM | `HERMES_BROWSER_EXTRACTION_LLM` | `0` | Ativa roteamento para modelo barato |

Rollback: Desativar flag restaura comportamento anterior instantaneamente. Nenhum estado persistente é criado.

---

## 4. Critérios de Aceite Quantitativos

| Métrica | Target | Medição |
| :--- | :--- | :--- |
| Redução tokens/snapshot | 20-40% | `len(json.dumps(payload))` antes/depois em páginas teste |
| Cache hit rate (polling) | >60% | `snapshot_cache_hit / total_snapshot_calls` em sessões WhatsApp |
| Extraction cost reduction | 30-50% | Tokens cheap vs principal em tarefas >10 itens |
| Regressão anchor resolution | 0% | Testes E2E existentes passam sem modificação |
| Fallback rate (extraction) | <5% | `extraction_fallback_rate` em telemetria |

---

## 5. Testes Obrigatórios Pré-Implementação

1. **Viewport Soft-Filter Regression:** `test_browser_model_payload_projection.py` completo + novo teste: elemento com `testid` fora do viewport DEVE permanecer no payload.
2. **Cache Invalidation on Mutation:** Teste unitário simulando `snapshot → click → snapshot`; segundo NÃO retorna `{unchanged: true}`.
3. **Extraction Fallback E2E:** Mock extraction LLM barato retorna erro; resultado final válido veio do modelo principal.
4. **SPA Content Change Detection:** Página React que altera layout via CSS sem mudar texto; fingerprint detecta mudança via `revision/mutation_count`.
5. **Anchor Offscreen Scroll:** Elemento marcado `offscreen: true` é resolvido após auto-scroll ou retorna erro estruturado.

---

## 6. Plano de Rollout Incremental

| Fase | Vetor | Esforço | Dependências | Risk |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Viewport Soft-Tag | 4-6h | Nenhuma | Baixo (fail-open existente) |
| 2 | PageFingerprint Cache | 6-8h | Fase 1 completa | Médio (invalidação correta) |
| 3 | Extraction LLM Router | 4-6h | Telemetria base | Médio (fallback confiável) |

Total estimado: 14-20h incluindo testes e validação.

---

## 7. Prompt de Continuação para Implementação Fase 1

```markdown
# Prompt de Continuação: Implementação Fase 1 — Viewport Filter Soft-Tag

## Objetivo
Implementar o vetor "Viewport Filter Soft-Tag" conforme BROWSER_OPTIMIZATION_SPEC_V3.md §1A e §2, com testes unitários e de integração passando antes de prosseguir.

## Contexto Validado
- Spec completa em workstation/context/BROWSER_OPTIMIZATION_SPEC_V3.md
- Ponto de inserção: tools/browser_workstation.py:969-1040 (project_model_browser_payload)
- Integração anchor: workstation/operational_kernel.py:367-389 (_find_ref_by_anchor)
- Feature flag: HERMES_BROWSER_VIEWPORT_FILTER=1 (default disabled)
- Fail-open: element_count < 5 ou anchor failure consecutiva desativa filtro
- Elementos com role/testid/name NUNCA removidos, apenas marcados offscreen: true

## Fases de Implementação

### Fase A: Core Filter Logic
1. Em tools/browser_workstation.py, adicionar função _apply_viewport_soft_filter(elements, snapshot_text, viewport_height, threshold=1500)
2. Integrar chamada em project_model_browser_payload() APÓS deduplicação existente
3. Respeitar feature flag: se HERMES_BROWSER_VIEWPORT_FILTER não setado, retornar payload inalterado
4. Adicionar campo viewport_filter ao payload projetado com métricas

### Fase B: Anchor Resolution Integration
1. Em workstation/operational_kernel.py:_find_ref_by_anchor(), verificar se elemento alvo tem offscreen: true
2. Se sim, retornar {"error": "ELEMENT_OFFSCREEN_NEEDS_SCROLL", "ref": ref, "y_offset": offset}
3. No caller (_execute_primitive), tratar erro como sinal para auto-scroll + re-resolve (máx 1 tentativa)
4. Se re-resolve falhar, propagar erro original

### Fase C: Testes e Validação
1. Adicionar testes em test_browser_model_payload_projection.py:
   - test_offscreen_elements_preserved_with_semantic_attributes
   - test_viewport_filter_disabled_by_default
   - test_fail_open_on_low_element_count
2. Adicionar teste em test_browser_operational_admission.py:
   - test_anchor_resolution_triggers_scroll_for_offscreen_element
3. Executar suite completa browser para validar zero regressão
4. Medir redução tokens em 3 páginas teste

## Instruções Operacionais
- Leia BROWSER_OPTIMIZATION_SPEC_V3.md completo antes de codar
- Feature flag DEVE ser verificada antes de qualquer lógica nova
- Commits separados por fase (A, B, C)
- Se divergência spec/código, pare e atualize spec ANTES de continuar

## Entregável Final
1. Código implementado e testado nas fases A, B, C
2. Relatório de métricas: tokens antes/depois, testes passando
3. Prompt de Continuação para Implementação Fase 2 (PageFingerprint Cache)
```