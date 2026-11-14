# Hermes Work — código preparado, contratos e testes de referência (25/10/2026)

**Não aplicar automaticamente.** Conteúdo para as missões Q1–Q7 em `QUALITY_GATES_IMPLEMENTATION_2026-10-25.md`. São trechos concretos para adaptação após aferir o HEAD, claims, testes e Stage A. Não constituem alteração do runtime nesta fase. Onde o Hermes já implementa a mesma função, reutilizar e descartar o exemplo.

## R1 — Q2: estimativa de economia na projeção (função pura)

**Local preferencial:** adaptar à implementação existente em `workstation/telemetry/browser_optimization_metrics.py`; **não criar nova fonte de métricas**. O ponto de observação é `tools/browser_workstation.py::_dispatch`: antes da serialização final, depois de `project_model_browser_payload`, com `model_facing=True`. Usar somente contadores no sink existente, nunca o payload.

```python
from typing import Any
from workstation.token_estimate import estimate_json_output_tokens

def estimated_projection_cost(raw_result: Any, projected: Any) -> dict[str, int]:
    """Pure, provider-neutral estimate; NEVER store either payload."""
    raw_tokens = estimate_json_output_tokens(raw_result)
    projected_tokens = estimate_json_output_tokens(projected)
    # Saving is an estimate for this SAME payload, not billed tokens.
    return {
        "raw_estimated_tokens": max(0, raw_tokens),
        "model_estimated_tokens": max(0, projected_tokens),
        "saved_estimated_tokens": max(0, raw_tokens - projected_tokens),
    }
```

**Regras de integração:** só calcular quando `model_facing`; nenhuma serialização duplicada se houver contadores equivalentes existentes; clamp ao limite aceito pelo sink; não expor dados internos `__telemetry`; uma projeção não equivale ao total de tokens do turno; cache hit é outra dimensão (evitar dupla contabilização). Decidir se `raw_result` deve ser medido **após** `strip_private_browser_telemetry`/`_force_redact` para comparar apenas conteúdos que poderiam ser expostos; nunca salvar o bruto. O modelo recebe o texto `json.dumps(projected)`; comparar a serialização realmente enviada, não usar exemplos artificiais diferentes.

**Contrato de teste:**
```python
def test_projection_estimate_is_nonnegative_and_does_not_mutate():
    raw = {"snapshot": "Interactive elements:\n- [@e1] button", "elements": [{"ref": "@e1"}]}
    projected = {"snapshot": raw["snapshot"], "elements_projected": True}
    before = repr((raw, projected))
    value = estimated_projection_cost(raw, projected)
    assert all(isinstance(x, int) and x >= 0 for x in value.values())
    assert repr((raw, projected)) == before
```

Adicionar ao teste existente, com import da função escolhida pelo implementador e fixture realista de `_payload()` em `workstation/tests/test_browser_model_payload_projection.py`; usar runner `scripts/run_tests.sh`.

## R2 — Q1: adaptador de preflight NÃO é um segundo `GuardRegistry`

**Evidência do código:** `_dispatch` executa `_validate_navigation(args)`, `resolve_browser_type_text`, `STALE_RUN`, e depois envia `_request_json`. `GuardRegistry.run_all` é async e `binding_guard` requer binding para todos os `browser_*`; aplicada sem escopo, ela introduz regressão. **Não inserir um preflight async no `_dispatch` síncrono.**

Esqueleto de regressão a adicionar/adaptar em `workstation/tests/test_browser_workstation_route.py` (usar `pytest.raises` conforme a exceção concreta de `_validate_navigation`; não inventar código de erro):

```python
def test_forbidden_navigation_rejects_before_controller(monkeypatch):
    from tools import browser_workstation as bw

    calls = []
    monkeypatch.setattr(bw, "_request_json", lambda *a, **kw: calls.append((a, kw)))
    try:
        bw._dispatch("browser_navigate", {"url": "file:///C:/private.txt"}, model_facing=True)
    except (ValueError, bw.WorkstationBrowserError):
        pass
    else:
        raise AssertionError("forbidden navigation unexpectedly allowed")
    assert calls == [], "invalid scheme crossed the Browser transport"
```

**Complementar antes de aceitar:** preservar URL parse existente; `browser_read_http` e ação read-only em sessão autorizada; partial binding = stale; lease humano; falha `_request_json` após efeito possível = incerto e nenhum retry. Teste acima é negativo, não prova todos os gates.

**Erros:** `workstation/browser_error_messages.py::classify_browser_error` já classifica `CIRCUIT_OPEN`, `UNBOUND_CALL`. Não substituir o tratamento canônico `WorkstationBrowserError` por dict `GuardResult.error_response()` sem teste do contrato do consumidor. Se não houver caso RED, melhor marcar guard experiment como não adotado.

## R3 — Q3: matriz de teste de aprendizagem antes de alteração

**Local:** testes Electron junto a `workstation-learning-session.test.ts`, `workstation-learning-capture.test.ts`, `workstation-learning-vertical-slice.test.ts`, e o hook de chat correspondente. A estrutura abaixo é uma **matriz de asserts**, não um mock de API inventada:

```text
A: storedSessionId="stored-A"; ownerTaskId="task-A"; task.sessionHost="stored-A"
B: storedSessionId="stored-B"; ownerTaskId="task-B"; task.sessionHost="stored-B"

startLearning(tabA, A)
ingest(eventA with eventId="evt-A")
assert chat[A] contains exactly one question evt-A
assert chat[B] contains zero evt-A
switch active B; reconnect; replay evt-A
assert chat[A] contains exactly one evt-A (dedupe)
assert chat[B] contains zero evt-A
stopLearning; captureFrame fail
assert status captures error/uncertainty; no fabricated frame proof
```

O código atual **já** tem `startLearning` lendo `task.sessionHost`; não regressar para fallback `st-<tabId>`. A captura usa `captureNextFrame`/`frameIndexEntries`; fixture só comprova circuito de código, não WebContents real.

## R4 — Q4: fail-closed na mutação JS legada (somente se inexistente no HEAD novo)

**Alvo:** `site-ops/scripts/site-ops/whatsapp-web.mjs` e rota em `apps/desktop/electron/ipc/site-ops.ts` estão **reivindicadas por outro agente**. Trecho conceitual para teste/adaptação, jamais colar sem conferir a função e o contrato existentes:

```javascript
// At the legacy JS/CDP dispatch boundary, BEFORE any click or send:
if (operation === 'send-message' || operation === 'send-attachment') {
  return {
    success: false,
    error: 'MUTATION_REQUIRES_CANONICAL_NATIVE_EXECUTOR'
  };
}
// Read-only inventory/deep map uses the already-authorized read path.
```

Caso já haja rejeição idêntica, o trabalho é **teste negativo**, não novo if. A rota alternativa permitida para mutação é a ferramenta Python já existente com TaskRun, OperationId, Browser lease e approval; nunca automatizar um segundo executor CDP. O contrato requer `UNCERTAIN` para pós-efeito, não `FAILED` + repetição.

## R5 — Q5: matriz causal M3 (não criar executor)

```text
pre-click baseline snapshot: outbound set {id0}; target chat identified by verified unique identity
CLICK allowed only after canonical Work admission + operation reserved
post-click snapshot: outbound set {id0, id1}
CONFIRMED only if:
  id1 not in baseline
  direction(id1) == OUTBOUND
  recipient(id1) == verified recipient
  normalized_body_or_digest(id1) == intended
  ACK(id1) is tied to id1, NOT to stale msg-meta
else:
  UNCERTAIN (do not resend automatically)
```

Aplicar **no `whatsapp_send_message`/executor já existente**, não reintroduzir raw phone no modelo, nem gravar corpo no journal. READ-only coleta de metadados nativos antes de considerar patch; falta de atributos = HOLD. `verify_delivery=False` não prova envio; review de mensagem não implica consentimento. A Stage A de outras missões não libera efeitos.

## R6 — Q6: critérios de teste do EmailBatchSender

Usar `workstation/tests/test_email_provider.py` e `GmailApiProvider/GmailBrowserFallbackProvider/EmailBatchSender` existentes. FakeProvider determinístico com 3 mensagens sintéticas; assert 1 chamada por idempotency key após replay, senha/token ausentes dos outputs, auth_missing bloqueia fallback automático, timeout após provider send = incerto e não reenvia sem reconciliação. Não alterar app credentials reais, não rodar Gmail/WhatsApp externos sem confirmação.

## R7 — Q7: captura read-only de telemetria de boot

No PowerShell, executar só em **perfil de teste** e salvar fora da árvore Git; o exemplo NÃO inicia/reinicia/mata processo:

```powershell
$source = Join-Path $env:LOCALAPPDATA 'hermes\logs\desktop.log'
$destination = Join-Path $env:TEMP 'hermes-boot-perf-audit.txt'
if (!(Test-Path -LiteralPath $source)) { throw "Log não encontrado: $source" }
Select-String -LiteralPath $source -Pattern '\[boot-perf\]|backend-ready|hydration' |
    ForEach-Object { $_.Line } |
    Set-Content -LiteralPath $destination -Encoding UTF8
Write-Host "Métricas coletadas: $destination"
```

`/api/health` positivo mede disponibilidade **naquele instante**, não confiabilidade de attach/reap. Não enviar logs com tokens nem contar períodos não equivalentes. Métricas cold/warm p50/p95 dependem de 5+ repetições cada e de baseline idêntico.

## Regras de revisão dos snippets

- Tratar código acima como **seed** sujeito a revisão crítica; aproveitar as importações reais do código de HEAD, não escrever novo framework.
- Primeiro teste RED que reproduza o requisito; depois a alteração mínima; GREEN; regressão de comportamento de usuário; code review.
- Não promover mocks/sintéticos para “validado no Browser nativo”. Não executar mutation WhatsApp real, Gmail send, checkout Git ou alteração dos arquivos com claims existentes.
