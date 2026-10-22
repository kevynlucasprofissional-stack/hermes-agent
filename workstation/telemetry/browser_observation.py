"""Non-authoritative native Browser metrics derived at the existing bridge boundary.

Never stores DOM contents, URLs, form values, prompts, screenshots, or tokens.
Neither a controller ACK nor local DOM observation is external outcome proof.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from . import TelemetryEventType, emit_event

_ALLOWED_ACTIONS = frozenset({
    "browser_navigate", "browser_snapshot", "browser_click", "browser_type",
    "browser_press", "browser_scroll", "browser_back", "browser_extract_items",
    "browser_batch_actions", "browser_read_http", "browser_console",
    "browser_vision", "browser_get_images",
})
_ALLOWED_ERRORS = frozenset({
    "CONTROLLER_DOWN", "TIMEOUT", "TIMEOUT_UNCERTAIN", "USER_CONTROL_ACTIVE",
    "STALE_REF", "NO_BOUND_TAB", "AUTH_REQUIRED", "CAPABILITY_MISSING",
    "INVALID_ARGUMENT", "FORBIDDEN_DESTINATION", "NETWORK_ERROR",
    "PAYLOAD_TOO_LARGE", "STALE_RUN",
})
_ALLOWED_SOURCE = frozenset({"ax", "dom", "dom_fallback"})
_ALLOWED_READINESS = frozenset({"stable", "transient", "ambiguous"})
_ALLOWED_REASONS = frozenset({
    "input_value_mismatch", "input_readback_unavailable", "readback_unavailable",
    "document_changed", "stale_or_replaced_target", "scroll_effect_not_observed",
    "scroll_not_observable", "click_postcondition_not_observed",
    "key_postcondition_not_observed", "batch_owner_or_document_changed",
    "renderer_crashed", "prior_batch_effect_requires_reconciliation",
    "verification_or_checkpoint_failed", "unverified_effect",
    "authority_or_precondition_denied", "effect_state_unknown",
})


def _bounded_number(value: Any, maximum: float = 1e12) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    val = float(value)
    return val if math.isfinite(val) and 0 <= val <= maximum else None


def _nonnegative_int(value: Any, maximum: int = 1_000_000_000) -> int | None:
    bounded = _bounded_number(value, maximum)
    return int(bounded) if bounded is not None and bounded == int(bounded) else None


def strip_private_browser_telemetry(result: Any) -> Any:
    """Remove internal measurements before data crosses the model-facing boundary."""
    if isinstance(result, dict) and "__telemetry" in result:
        return {key: value for key, value in result.items() if key != "__telemetry"}
    return result


def emit_native_browser_observation(
    *, action: str, result: Mapping[str, Any] | None,
    session_id: str | None, task_id: str | None, run_id: str | None,
    operation_id: str | None, duration_ms: float | None,
    request_bytes: int | None = None, response_bytes: int | None = None,
    error_code: str | None = None,
    operation_id_override: str | None = None,
    stage: str = "result",
) -> None:
    """Best-effort browser telemetry; never controls runtime execution."""
    try:
        action = action if action in _ALLOWED_ACTIONS else "other"
        data = result if isinstance(result, Mapping) else {}
        extra = data.get("__telemetry")
        diagnostics = extra if isinstance(extra, Mapping) else {}
        if stage == "attempt":
            status = "REQUEST_ATTEMPTED"
        elif error_code:
            status = "ERROR"
        elif action == "browser_batch_actions":
            state = data.get("status")
            status = {"verified": "LOCAL_VERIFIED", "uncertain": "UNCERTAIN",
                      "rejected": "REJECTED"}.get(state, "ACKNOWLEDGED")
        elif action in {"browser_click", "browser_type", "browser_press",
                        "browser_scroll", "browser_navigate", "browser_back"}:
            status = "ACKNOWLEDGED"
        else:
            status = "OBSERVED"

        payload: dict[str, Any] = {"action": action}
        for name in ("cdp_calls", "snapshot_chars", "delta_chars",
                     "element_count", "renderer_pid", "renderer_memory_bytes",
                     "main_rss_bytes", "main_cpu_us", "spa_waits",
                     "completed_steps", "verified_steps"):
            value = diagnostics.get(name) if name in diagnostics else data.get(name)
            parsed = _nonnegative_int(value)
            if parsed is not None:
                payload[name] = parsed
        engine = diagnostics.get("snapshot_source")
        if engine in _ALLOWED_SOURCE:
            payload["snapshot_source"] = engine
        readiness = data.get("readiness")
        if readiness in _ALLOWED_READINESS:
            payload["readiness"] = readiness
        for boolean_field in ("cached", "truncated", "wall_detected"):
            if isinstance(data.get(boolean_field), bool):
                payload[boolean_field] = data[boolean_field]
        reason = data.get("reason")
        if reason in _ALLOWED_REASONS:
            payload["uncertainty_reason"] = reason
        diagnostic_duration = _bounded_number(diagnostics.get("duration_ms"))
        if diagnostic_duration is not None:
            payload["snapshot_duration_ms"] = round(diagnostic_duration, 3)

        emit_event(
            TelemetryEventType.BROWSER_OPERATION_OBSERVED,
            source_owner="workstation.native_browser_bridge",
            session_id=session_id, task_id=task_id, run_id=run_id,
            operation_id=operation_id_override or operation_id,
            route="native_browser", phase=action, status=status,
            reason_code=error_code if error_code in _ALLOWED_ERRORS else (
                "OTHER_ERROR" if error_code else None),
            duration_ms=_bounded_number(duration_ms),
            request_bytes=_nonnegative_int(request_bytes),
            result_bytes=_nonnegative_int(response_bytes),
            payload=payload,
        )

        # Fase 3 — Unified telemetry aggregator hook (best-effort, fail-open).
        # Feeds the in-memory BrowserOptimizationMetrics without altering the
        # event stream above. Never raises into the caller path.
        try:
            from .browser_optimization_metrics import record_browser_observation

            viewport_filter = data.get("viewport_filter") if isinstance(data, Mapping) else None
            offscreen_count = 0
            semantic_count = 0
            viewport_enabled = False
            original_chars = 0
            if isinstance(viewport_filter, Mapping):
                offscreen_count = _nonnegative_int(viewport_filter.get("offscreen_count")) or 0
                semantic_count = _nonnegative_int(viewport_filter.get("preserved_semantic_count")) or 0
                viewport_enabled = bool(viewport_filter.get("enabled"))
                # Estimate original chars from projected + savings when available.
                proj_chars = payload.get("snapshot_chars") or 0
                delta = payload.get("delta_chars") or 0
                original_chars = proj_chars + delta if (proj_chars and delta) else 0

            items_count = 0
            if action == "browser_extract_items":
                items_raw = data.get("items") if isinstance(data, Mapping) else None
                if isinstance(items_raw, list):
                    items_count = len(items_raw)

            record_browser_observation(
                session_id,
                action=action,
                chars=payload.get("snapshot_chars") or 0,
                cached=bool(payload.get("cached")),
                offscreen_count=offscreen_count,
                semantic_count=semantic_count,
                viewport_filter_enabled=viewport_enabled,
                original_chars=original_chars,
                items_count=items_count,
            )
        except Exception:
            pass
    except Exception:
        # The analytics projection never controls an effect or exception route.
        return
