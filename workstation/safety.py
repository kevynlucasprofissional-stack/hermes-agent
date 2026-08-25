from __future__ import annotations

from dataclasses import dataclass
from workstation.contracts import RiskLevel

APPROVAL_REQUIRED_ACTIONS = frozenset(
    {
        "purchase",
        "pay",
        "send",
        "publish",
        "delete",
        "accept_contract",
        "accept_terms",
        "change_credentials",
        "change_permissions",
        "move_money",
        "irreversible",
        "reveal_secret_new_context",
        "insert_secret_new_context",
    }
)


@dataclass(frozen=True, slots=True)
class SafetyDecision:
    action: str
    risk: RiskLevel
    approval_required: bool
    reason: str


def classify_action(action: str) -> SafetyDecision:
    key = action.strip().lower().replace("-", "_").replace(" ", "_")
    if key in APPROVAL_REQUIRED_ACTIONS:
        return SafetyDecision(key, RiskLevel.HIGH, True, "Workstation approval boundary")
    if key in {"navigate", "read", "search", "inspect", "draft", "organize"}:
        return SafetyDecision(key, RiskLevel.LOW, False, "Reversible/read-oriented action")
    return SafetyDecision(key, RiskLevel.MEDIUM, False, "Unclassified action; journal and verify")
