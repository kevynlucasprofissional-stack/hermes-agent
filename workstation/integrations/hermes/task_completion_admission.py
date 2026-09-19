from __future__ import annotations

import json
import logging
from typing import Any
from workstation.contracts import (
    AcceptanceContract,
    AcceptanceEvaluator,
    EvidenceRef,
    OutcomeStatus,
    TaskOutcome,
)

logger = logging.getLogger(__name__)


def workstation_task_completion_admission(
    conn: Any,
    task_id: str,
    ws: Any,
    owned: Any,
    hybrid_owned: bool,
) -> bool:
    """Validate Workstation task completion and acceptance contract before DONE update."""
    if ((owned and owned[0] == "workstation") or hybrid_owned) and not isinstance(ws, dict):
        return False
    if not isinstance(ws, dict):
        return True

    data = ws.get("outcome")
    if not isinstance(data, dict) or ws.get("acceptance_approved") is not True:
        return False
    try:
        outcome = TaskOutcome(
            **{
                **data,
                "status": OutcomeStatus(data["status"]),
                "evidence_refs": [EvidenceRef(**e) for e in data.get("evidence_refs", [])],
            }
        )
        saved = conn.execute(
            "SELECT contract_json FROM task_acceptance_contracts WHERE task_id=?",
            (task_id,),
        ).fetchone()
        contract = AcceptanceContract(**json.loads(saved[0])) if saved else AcceptanceContract()
        if outcome.task_id != task_id or AcceptanceEvaluator().evaluate(outcome, contract):
            return False
        if contract.policy == "evidence":
            from agent.verification_evidence import outcome_verifiers_recorded
            if not outcome_verifiers_recorded(
                task_id,
                outcome.session_id,
                outcome.verifier_results,
                ws.get("verification_event_ids", []),
            ):
                return False
    except (TypeError, ValueError, KeyError) as exc:
        logger.debug("Workstation task completion validation failed: %s", exc)
        return False
    return True
