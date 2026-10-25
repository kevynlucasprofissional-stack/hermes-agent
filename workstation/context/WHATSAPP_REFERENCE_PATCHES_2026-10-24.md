# Código-base proposto (não implantado) — WA M1/M3/M4

**Status:** referências adaptáveis, não runtime qualificado. A IA implementadora deve recusar/melhorar qualquer detalhe inadequado após conferir schema real e owners. Evite colocar código não conectado em produção.

## M1 — resolver telefone original por enrollment_id

**Destino sugerido:** `workstation/integrations/hermes/whatsapp_recipient_resolution.py` OU função interna equivalente do executor existente. A interface para IA aceita `campaign_id` + `enrollment_id`, não texto de telefone redigido. Este resolver fica **exclusivamente dentro do processo trusted**.

```python
from dataclasses import dataclass
import re
import sqlite3

class RecipientResolutionError(ValueError):
    pass

@dataclass(frozen=True)
class TrustedRecipient:
    contact_id: int
    enrollment_id: int
    campaign_id: int
    phone_digits: str  # nunca retorna ao modelo

def explicit_e164(raw: str) -> str:
    value = (raw or "").strip()
    if not re.fullmatch(r"\+[1-9]\d{7,14}", value):
        raise RecipientResolutionError("PHONE_INVALID_OR_MASKED")
    return value[1:]

def resolve_campaign_recipient(conn: sqlite3.Connection, *, campaign_id: int,
                               enrollment_id: int) -> TrustedRecipient:
    row = conn.execute(
        """SELECT e.id, e.campaign_id, e.contact_id, c.phone_raw, c.phone_number
           FROM campaign_enrollments e JOIN contacts c ON c.id=e.contact_id
           WHERE e.id=? AND e.campaign_id=?""",
        (enrollment_id, campaign_id),
    ).fetchone()
    if row is None:
        raise RecipientResolutionError("RECIPIENT_NOT_IN_CAMPAIGN")
    eid, cid, contact_id, phone_raw, phone_number = row
    for candidate in (phone_raw, phone_number):
        if not candidate:
            continue
        try:
            return TrustedRecipient(contact_id, eid, cid, explicit_e164(candidate))
        except RecipientResolutionError:
            continue
    raise RecipientResolutionError("PHONE_SOURCE_REQUIRES_REVIEW")
```

**Adaptar obrigatoriamente:** `phone_number` pode ser dígitos sem `+` no schema existente. Não assumir que são E.164 nem acrescentar DDI/DDDs. Converter formatos explícitos com provenance e testes. O snippet *não* valida autorização, opt-in ou consentimento: gates must run **before** resolver/dispatch. `TrustedRecipient` jamais serializado no tool result. Expor à LLM apenas `{contact_id, operation_id, state}`. Banco deve ser configurado, sem `get_default_db_path` hardcoded/fallback.

Testes iniciais:
```python
import pytest
def test_masked_not_reconstructed():
    with pytest.raises(RecipientResolutionError):
        explicit_e164("+155****0123")
def test_explicit_preserved():
    assert explicit_e164("+15555550123") == "15555550123"
```

## M3 — prova de mensagem nova e correlacionada

**Substituir/rever:** `_extract_delivery_evidence` e `whatsapp_send_message` em `workstation/integrations/hermes/whatsapp_browser_executor.py`. **Pseudocódigo**: funções abaixo são contratos, NÃO existem necessariamente.

```python
ids_before = read_outbound_ids(snapshot_before)
result = admitted_click(operation_id=operation_id)
if result.effect_uncertain:
    return {"state": "UNCERTAIN", "sent": False, "operation_id": operation_id}
items = read_outbound_evidence(snapshot_after, verified_target)
new_matches = [m for m in items if m.id not in ids_before
               and m.direction == "outbound"
               and m.message_digest == expected_digest]
if len(new_matches) != 1 or not new_matches[0].ack_evidence:
    return {"state": "UNCERTAIN", "sent": False, "operation_id": operation_id}
return {"state": "CONFIRMED", "sent": True, "operation_id": operation_id,
        "message_data_id": new_matches[0].id}
```

Na ausência de metadados suficientes, manter `UNCERTAIN`, nunca fabricar ACK; `verify_delivery=False` não comprova composer vazio. Não devolver URLs com dados pessoais.

## M3/M4 — SQL subordinado ao banco de campanha (não criar outro DB)

```sql
CREATE TABLE IF NOT EXISTS campaign_send_attempts (
  id INTEGER PRIMARY KEY,
  campaign_send_id INTEGER NOT NULL REFERENCES campaign_sends(id),
  operation_id TEXT NOT NULL UNIQUE,
  task_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN (
    'PREPARED','DISPATCHING','OBSERVED','CONFIRMED',
    'UNCERTAIN','FAILED','REVIEW_REQUIRED')),
  message_digest TEXT NOT NULL,
  evidence_ref TEXT,
  error_code TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_campaign_send_attempts_parent
  ON campaign_send_attempts(campaign_send_id,created_at);
```

**Revisão obrigatória:** admitir operação e persistir intenção *antes* de mutação; verificar unique existente em `campaign_sends`, distinguir passo de tentativa; `operation_id` não pode ser reaproveitado com digest diferente. Não inserir telefones/corpos integrais nem hashes sem chave de telefones no ledger; HMAC ou IDs estáveis quando necessário. Migração/rollback somente em DB temporário, backup e aprovação antes de dados reais. Browser session ledger e DB de campanha NÃO podem se substituir mutuamente.
