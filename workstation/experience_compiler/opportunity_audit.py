"""Compilability opportunity audit and historical narrative backfill.

Implements DF-018 and DF-019 (Phase DF5):
- Historical conversation markdown ingestion with evidence linking
- Bounded opportunity completeness audit against labeled benchmark cases
- Strict preservation: unverified narrative markdown never enters as VERIFIED_SUCCESS
"""
import re
import time
from typing import Any

from workstation.artifacts import ArtifactStore
from workstation.execution_policy import EvidenceStrength
from workstation.experience_compiler.corpus import ExperienceCorpus
from workstation.experience_compiler.models import (
    CausalGrade,
    Operation,
    Provenance,
    TransitionOutcome,
    TransitionSample,
    Verification,
)
from workstation.recipes import digest

OPPORTUNITY_AUDIT_SCHEMA = "workstation.compilability_opportunity_audit.v1"


def import_historical_conversation_markdown(
    content: str,
    source_path: str,
    corpus: ExperienceCorpus,
    artifacts: ArtifactStore,
) -> dict[str, Any]:
    """Ingest historical conversation markdown into ExperienceCorpus.

    Narrative steps without verified execution receipts are captured as
    unverified narrative (TransitionOutcome.OBSERVED / CausalGrade.OBSERVED_ONCE).
    Steps linking directly to confirmed execution receipts in ArtifactStore
    are captured as VERIFIED_SUCCESS.
    """
    imported_count = 0
    linked_receipt_count = 0
    unverified_count = 0

    # Search for artifact references in markdown content
    artifact_pattern = re.compile(r"artifact://tasks/[a-zA-Z0-9_\-\./]+")
    found_refs = artifact_pattern.findall(content)

    linked_samples = []
    for ref in found_refs:
        try:
            data = artifacts.read_json(ref)
            if isinstance(data, dict):
                is_success = bool(data.get("success", False))
                action_name = str(data.get("action", "browser_navigate"))
                runtime = str(data.get("runtime", "electron-chromium"))
                sample = TransitionSample(
                    sample_id=f"retro_linked_{digest(ref + source_path)[:16]}",
                    operation=Operation(
                        primitive=action_name,
                        canonical_route="native_browser",
                        parameters={"url": data.get("url", "")},
                    ),
                    verification=Verification(
                        status="VERIFIED" if is_success else "INCONCLUSIVE",
                        evidence_refs=[ref],
                        evidence_strength=EvidenceStrength.TOOL_ACK_ONLY,
                    ),
                    outcome=TransitionOutcome.VERIFIED_SUCCESS if is_success else TransitionOutcome.FAILED,
                    provenance=Provenance(
                        task_id="retro_import",
                        runtime=runtime,
                        source=source_path,
                        trust_class="historical_receipt" if is_success else "untrusted",
                    ),
                    causal_grade=CausalGrade.OBSERVED_ONCE,
                )
                corpus.capture(sample)
                linked_samples.append(sample)
                linked_receipt_count += 1
                imported_count += 1
        except Exception:
            pass

    # If no verified receipts were found, parse narrative steps
    if not linked_samples:
        step_pattern = re.compile(r"^\s*(?:\d+[\.\)]|\-|\*)\s+(.+)$", re.MULTILINE)
        steps = step_pattern.findall(content)

        if not steps:
            # Fallback: treat entire markdown as a single narrative entry if non-empty
            stripped = content.strip()
            if stripped:
                steps = [stripped[:200]]

        for idx, step_text in enumerate(steps):
            sample = TransitionSample(
                sample_id=f"retro_unverified_{digest(f'{source_path}_{idx}_{step_text}')[:16]}",
                operation=Operation(
                    primitive="historical_narrative_step",
                    parameters={"step_text": step_text},
                ),
                verification=Verification(
                    status="INCONCLUSIVE",
                    evidence_refs=[],
                    evidence_strength=EvidenceStrength.TOOL_ACK_ONLY,
                ),
                outcome=TransitionOutcome.OBSERVED,
                provenance=Provenance(
                    task_id="retro_import",
                    runtime="",
                    source=source_path,
                    trust_class="untrusted",
                ),
                causal_grade=CausalGrade.OBSERVED_ONCE,
            )
            corpus.capture(sample)
            unverified_count += 1
            imported_count += 1

    return {
        "imported_count": imported_count,
        "provenance_source": source_path,
        "linked_receipt_count": linked_receipt_count,
        "unverified_count": unverified_count,
    }


def generate_compilability_opportunity_audit(
    cases: list[dict[str, Any]],
    corpus: ExperienceCorpus,
    artifacts: ArtifactStore,
) -> dict[str, Any]:
    """Generate a compilability opportunity audit against labeled benchmark cases.

    Tracks eligible, detected, attempted, held, validated, promoted, run_local_reused,
    missed, unknown, and true_negative counts with explicit denominator len(cases).
    Stores durable audit artifact in ArtifactStore.
    """
    denominator = len(cases)

    eligible = 0
    detected = 0
    attempted = 0
    held = 0
    validated = 0
    promoted = 0
    run_local_reused = 0
    true_negative = 0
    missed = 0
    unknown = 0

    case_summaries = []

    for case in cases:
        case_id = case.get("case_id", "unknown_case")
        is_tn = bool(case.get("is_true_negative", False))
        reasons = list(case.get("reasons", []))

        if is_tn:
            true_negative += 1
            status = "true_negative"
        else:
            eligible += 1
            is_promoted = bool(case.get("promoted", False))
            is_validated = bool(case.get("validated", False))
            is_reused = bool(case.get("run_local_reused", False))
            is_verified = bool(case.get("verified_in_corpus", False))
            is_held = (
                bool(case.get("held", False))
                or "unverified_narrative_markdown" in reasons
                or (not is_verified and not is_promoted and bool(reasons))
            )
            is_detected = (
                bool(case.get("detected", False))
                or is_verified
                or is_promoted
                or is_held
            )
            is_attempted = (
                bool(case.get("attempted", False))
                or is_validated
                or is_promoted
            )

            if is_detected:
                detected += 1
            if is_attempted:
                attempted += 1
            if is_held:
                held += 1
            if is_validated:
                validated += 1
            if is_promoted:
                promoted += 1
            if is_reused:
                run_local_reused += 1

            if not is_detected and not is_held and not is_promoted:
                if "unknown" in reasons:
                    unknown += 1
                    status = "unknown"
                else:
                    missed += 1
                    status = "missed"
            elif is_held:
                status = "held"
            elif is_promoted:
                status = "promoted"
            elif is_validated:
                status = "validated"
            elif is_detected:
                status = "detected"
            else:
                status = "eligible"

        case_summaries.append({
            "case_id": case_id,
            "status": status,
            "reasons": reasons,
        })

    audit_payload: dict[str, Any] = {
        "schema": OPPORTUNITY_AUDIT_SCHEMA,
        "denominator": denominator,
        "counts": {
            "eligible": eligible,
            "detected": detected,
            "attempted": attempted,
            "held": held,
            "validated": validated,
            "promoted": promoted,
            "run_local_reused": run_local_reused,
            "true_negative": true_negative,
            "missed": missed,
            "unknown": unknown,
        },
        "cases_summary": case_summaries,
        "timestamp": time.time(),
    }

    stored_artifact = artifacts.store(
        "audit",
        f"opportunity_audit_{int(time.time() * 1000)}.json",
        audit_payload,
        schema=OPPORTUNITY_AUDIT_SCHEMA,
    )
    audit_payload["audit_artifact_ref"] = stored_artifact.ref

    return audit_payload
