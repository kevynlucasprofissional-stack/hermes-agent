from __future__ import annotations

from dataclasses import dataclass
from workstation.contracts import RiskLevel

import re

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
        "checkout",
        "subscribe",
        "authorise",
        "authorize",
        "transfer_funds",
        "wire",
        "wire_transfer",
        "send_email",
        "delete_account",
        "erase",
        "drop_database",
        "revoke_token",
        "rotate_key",
        "grant_admin",
        "modify_billing",
        "place_order",
    }
)


@dataclass(frozen=True, slots=True)
class SafetyDecision:
    action: str
    risk: RiskLevel
    approval_required: bool
    reason: str


def classify_action(action: str) -> SafetyDecision:
    # Normalize camelCase to snake_case, then hyphens and whitespace
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", action.strip())
    key = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower().replace("-", "_").replace(" ", "_")

    if key in APPROVAL_REQUIRED_ACTIONS:
        return SafetyDecision(key, RiskLevel.HIGH, True, "Workstation approval boundary")
    if key in {"navigate", "read", "search", "inspect", "draft", "organize"}:
        return SafetyDecision(key, RiskLevel.LOW, False, "Reversible/read-oriented action")
    return SafetyDecision(key, RiskLevel.MEDIUM, False, "Unclassified action; journal and verify")
