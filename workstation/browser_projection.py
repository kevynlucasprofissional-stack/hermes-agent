"""Workstation-owned projection of raw browser results into durable domain records.

The generic browser route (``tools/browser_tool`` → ``gateway.browser_control_broker``
→ the selected controller) owns transport: it takes an action and returns the
engine's raw result. What happens to that result *as Workstation domain data* —
which artifact it is stored as, which WorkPlan/WorkItems record it, which
validation verdict each item carries, and what compact shape is handed back to
the model — is a Workstation decision and belongs to a Workstation module.

Keeping it anywhere else inverts the dependency: a generic tool module would own
Hermes Work semantics and would have to import Workstation stores to do it. This
module is the Workstation side of that split, and the controller reaches it
through the ordinary import below, not through a private import of an upstream
tool module.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from workstation.artifacts import ArtifactStore
from workstation.durable_tasks import DurableTaskStore
from workstation.semantic_validation import SemanticValidator

logger = logging.getLogger(__name__)

# A small extraction is cheaper to return inline than to persist and reference.
INLINE_ITEM_LIMIT = 5

# Anomaly detail is evidence, not content: the model gets a bounded sample and
# the full record stays in the validated WorkItems.
ANOMALY_SAMPLE_LIMIT = 5
PREVIEW_SAMPLE_LIMIT = 2


def process_extracted_items_durably(raw_result: Any, args: dict, kw: dict) -> str:
    """Project a ``browser_extract_items`` result into durable Workstation records.

    Returns a compact JSON summary rather than the extracted payload itself: the
    full dataset goes to the ArtifactStore and the per-item verdicts go to the
    canonical WorkPlan, so the model does not carry the dataset in prompt context.

    Every step degrades visibly. A failed artifact write is reported as
    ``durable: false`` with ``artifact_error`` set, never silently reported as a
    durable result, and a failed WorkPlan write is logged while the summary still
    distinguishes the two outcomes for the caller.
    """
    if isinstance(raw_result, str):
        try:
            data = json.loads(raw_result)
        except Exception:
            return raw_result
    elif isinstance(raw_result, dict):
        data = raw_result
    else:
        return str(raw_result)

    items = data.get("items")
    if not isinstance(items, list):
        return json.dumps(data, ensure_ascii=False)

    output_artifact = args.get("output_artifact", True)
    if not output_artifact and len(items) <= INLINE_ITEM_LIMIT:
        return json.dumps(data, ensure_ascii=False)

    # Pre-flight capability check: reports what this host can actually do, and is
    # deliberately non-fatal — an unreported audit note must not lose extracted data.
    try:
        from workstation.capabilities import RuntimeCapabilityRegistry

        RuntimeCapabilityRegistry.audit_environment()
    except Exception as exc:
        logger.debug("RuntimeCapabilityRegistry audit note: %s", exc)

    task_id = str(kw.get("task_id") or "browser_batch")

    # 1. Store the complete extracted raw dataset into the ArtifactStore.
    artifact_ref = None
    artifact_path = None
    artifact_error = None
    try:
        store = ArtifactStore()
        payload = {
            "source": "browser_extract_items",
            "selector_used": data.get("selector_used"),
            "url": data.get("url"),
            "title": data.get("title"),
            "count": len(items),
            "items": items,
        }
        digest = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        artifact_ref = store.store_json(
            payload,
            task_id=task_id,
            name=f"browser-extract-{digest}.json",
            schema="browser_extract_items/v1",
            summary={"count": len(items)},
        )
        resolved = store.resolve_path(artifact_ref)
        artifact_path = str(resolved) if resolved is not None else None
        if artifact_path is None:
            raise RuntimeError("ArtifactStore returned an unresolved artifact_ref")
    except Exception as exc:
        artifact_error = str(exc)
        logger.warning("Failed to store extraction to ArtifactStore: %s", exc)

    # 2. Persist the durable WorkPlan and WorkItems in the canonical kanban_db.
    anomalies: list[dict] = []
    try:
        with DurableTaskStore() as task_store:
            plan = task_store.create_plan(
                task_id,
                f"Extraction: {data.get('title') or data.get('selector_used') or 'Items'} ({len(items)} items)",
                [{"index": i, "payload": it} for i, it in enumerate(items)],
                metadata={"source": "browser_extract_items", "artifact_ref": artifact_ref},
            )
            work_items = task_store.get_work_items(plan.id)
            validator = SemanticValidator(required_fields=["title"])
            for i, it in enumerate(items):
                val_res = validator.validate_item(it)
                item_id = work_items[i].id if i < len(work_items) else None
                ref_handle = artifact_ref or "artifact://raw"
                if not val_res.get("valid", True):
                    issues = val_res.get("issues", [])
                    anomalies.append({
                        "index": i,
                        "title": (it.get("title") or "")[:40],
                        "violations": issues,
                    })
                    if item_id:
                        task_store.mark_item_captured(item_id, raw_output_ref=ref_handle)
                        task_store.mark_item_validated(item_id, validation_result=val_res)
                        task_store.fail_item(item_id, error="; ".join(issues), can_retry=False)
                else:
                    if item_id:
                        task_store.mark_item_captured(item_id, raw_output_ref=ref_handle)
                        task_store.mark_item_persisted(item_id, normalized_output_ref=ref_handle)
                        task_store.mark_item_validated(item_id, validation_result=val_res)
                        task_store.complete_item(item_id)
    except Exception as exc:
        logger.debug("Durable task creation note: %s", exc)

    # 3. Return a compact executive summary so the dataset stays out of prompt context.
    summary = {
        "success": True,
        "total_extracted": len(items),
        "valid_count": len(items) - len(anomalies),
        "anomalies_count": len(anomalies),
        "selector_used": data.get("selector_used"),
        "artifact_ref": artifact_ref,
        "artifact_path": artifact_path,
        "sample_preview": items[:PREVIEW_SAMPLE_LIMIT] if items else [],
        "anomalies": anomalies[:ANOMALY_SAMPLE_LIMIT] if anomalies else [],
        "durable": artifact_ref is not None,
        "artifact_error": artifact_error,
        "note": (
            f"Complete {len(items)} items saved durably to task-scoped ArtifactStore and kanban_db WorkPlan. Prompt context protected."
            if artifact_ref is not None
            else f"Extracted {len(items)} items, but durable artifact persistence failed; result is not marked durable."
        ),
    }
    return json.dumps(summary, ensure_ascii=False)
