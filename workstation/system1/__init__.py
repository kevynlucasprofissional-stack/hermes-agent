"""Hermes Workstation System-1 subsystem.

Provides fast, calibrated, non-autoregressive semantic decisions
(classification, ranking, shortlisting, progress recognition) to amortize
routine reasoning outside the LLM path.
"""

from agent.system1_decision import (
    DecisionRequest,
    DecisionResult,
    System1DecisionProvider,
    decide_system1,
    register_system1_decision_provider,
    system1_decision_metrics,
    system1_decision_providers,
    unregister_system1_decision_provider,
)
from workstation.system1.contracts import (
    AmbiguityKind,
    DecisionInfluenceMode,
    NeutralChoice,
    ProgressClass,
)
from workstation.system1.provenance import (
    get_laya_provenance,
    verify_laya_provenance,
)
from workstation.system1.receipts import (
    DecisionReceipt,
    persist_decision_receipt,
)

__all__ = [
    "DecisionRequest",
    "DecisionResult",
    "System1DecisionProvider",
    "decide_system1",
    "register_system1_decision_provider",
    "unregister_system1_decision_provider",
    "system1_decision_providers",
    "system1_decision_metrics",
    "NeutralChoice",
    "AmbiguityKind",
    "ProgressClass",
    "DecisionInfluenceMode",
    "get_laya_provenance",
    "verify_laya_provenance",
    "DecisionReceipt",
    "persist_decision_receipt",
]
