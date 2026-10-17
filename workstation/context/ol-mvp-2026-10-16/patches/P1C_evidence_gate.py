"""OL-MVP P1C: classify a native TaskRun evidence manifest (stdlib only).

This is an informational structural checker, NOT a verifier of artifact
authenticity, an authorization engine or a DIRECT qualification mechanism.
References must be inspected against the runtime's own ArtifactStore.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "workstation.ol_mvp.p1c.evidence.v1"


def _ref(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("artifact://tasks/") and len(value) > 24


def _item_valid(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    return (
        item.get("status") == "VERIFIED"
        and item.get("source") == "canonical_runtime"
        and item.get("route") in {"adaptive", "compiled"}
        and all(isinstance(item.get(k), str) and item[k] for k in ("item_id", "card_id", "operation_id"))
        and _ref(item.get("readback_ref"))
        and _ref(item.get("raw_result_ref"))
    )


def _run_valid(run: Any) -> bool:
    if not isinstance(run, dict):
        return False
    items = run.get("items")
    if (
        run.get("entrypoint") not in {"desktop_chat", "native_work_execute"}
        or not run.get("task_id")
        or not run.get("run_id")
        or not isinstance(items, list)
        or len(items) < 3
    ):
        return False
    identities = [(i.get("item_id"), i.get("operation_id")) for i in items if isinstance(i, dict)]
    return (
        len(identities) == len(items) == len(set(identities))
        and len({i[0] for i in identities}) == len(items)
        and all(_item_valid(i) for i in items)
    )


def assess(document: Any) -> dict[str, Any]:
    """Give a conservative status; never admit execution or certify evidence."""
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        return {"status": "INVALID", "reasons": ["invalid_schema"], "evidence_authenticity": "NOT_CHECKED"}
    reasons: list[str] = []
    if document.get("execution_surface") != "electron_native":
        reasons.append("not_native_electron")
    if document.get("evidence_origin") != "canonical_runtime":
        reasons.append("simulated_or_unknown_evidence_origin")
    first = document.get("first_run")
    if not _run_valid(first):
        reasons.append("first_run_missing_canonical_three_items")
    elif first:
        entries = first["items"]
        adaptive = [j for j, i in enumerate(entries) if i["route"] == "adaptive"]
        compiled = [j for j, i in enumerate(entries) if i["route"] == "compiled"]
        if not adaptive or not compiled or min(compiled) <= min(adaptive):
            reasons.append("inflight_reuse_not_demonstrated")
        if not _ref(first.get("candidate_ref")) or not _ref(first.get("qualified_offer_ref")):
            reasons.append("candidate_or_qualified_offer_missing")
        if not _ref(first.get("adoption_receipt_ref")):
            reasons.append("real_adoption_receipt_missing")
        if first.get("qualification_mode") != "DIRECT_AUTHORIZED":
            reasons.append("direct_qualification_unverified")
    second = document.get("second_run")
    if not _run_valid(second):
        reasons.append("cross_run_missing_or_unverified")
    elif first:
        if (str(first["task_id"]), str(first["run_id"])) == (str(second["task_id"]), str(second["run_id"])):
            reasons.append("second_run_identity_not_new")
        if not any(i["route"] == "compiled" for i in second["items"]):
            reasons.append("cross_run_compiled_execution_missing")
        if not _ref(second.get("capability_lookup_ref")) or not _ref(second.get("adoption_receipt_ref")):
            reasons.append("cross_run_lookup_or_receipt_missing")
    usage = document.get("provider_usage")
    metrics_known = (
        isinstance(usage, dict)
        and isinstance(usage.get("real_llm_calls"), int)
        and not isinstance(usage["real_llm_calls"], bool)
        and usage["real_llm_calls"] >= 0
        and _ref(usage.get("provider_usage_ref"))
    )
    return {
        "status": "READY_FOR_HUMAN_EVIDENCE_REVIEW" if not reasons else "PARTIAL_OR_HOLD",
        "reasons": reasons,
        "real_provider_usage_supported": bool(metrics_known),
        "evidence_authenticity": "NOT_CHECKED",
        "stage_a_qualified": False,
        "note": "Structure check only: independently audit artifact refs, owner and authorization.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    result = assess(json.loads(args.receipt.read_text(encoding="utf-8-sig")))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 2 if result["status"] == "INVALID" else 0


if __name__ == "__main__":
    raise SystemExit(main())
