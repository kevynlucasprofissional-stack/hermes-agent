"""AFB-v0.1 test-only independent-oracle harness.

The SUT and oracle are separate callables: scenarios never hand-label an external
outcome in the row consumed by ``evaluate_external_validity``.
"""
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class AFBScenarioResult:
    scenario_id: str
    internal_status: str
    internal_verified: bool
    external_success: bool | None
    oracle_evidence: dict[str, Any]
    mutation_applied: bool = False
    recovery_state: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def metric_row(self) -> dict[str, Any]:
        return {"scenario_id": self.scenario_id, "internal_status": self.internal_status,
                "internal_verified": self.internal_verified, "external_success": self.external_success,
                "mutation_applied": self.mutation_applied, "recovery_state": self.recovery_state,
                "oracle_evidence": self.oracle_evidence, **self.metadata}


def run_afb_scenario(scenario_id: str, system_under_test: Callable[[], dict[str, Any]],
                     hidden_oracle: Callable[[], tuple[bool | None, dict[str, Any]]], *,
                     metadata: dict[str, Any] | None = None) -> AFBScenarioResult:
    internal = system_under_test()
    external_success, oracle_evidence = hidden_oracle()
    return AFBScenarioResult(scenario_id=scenario_id,
        internal_status=str(internal.get("verification_result", {}).get("status", internal.get("status", "INCONCLUSIVE"))),
        internal_verified=bool(internal.get("verification_result", {}).get("accepted", internal.get("success", False))),
        external_success=external_success, oracle_evidence=dict(oracle_evidence),
        mutation_applied=bool(internal.get("mutation_applied", False)),
        recovery_state=str(internal.get("recovery_state", "unknown")), metadata=dict(metadata or {}))
