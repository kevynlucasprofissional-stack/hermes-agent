from __future__ import annotations

import logging
import hashlib
import json
from typing import Any
from workstation.batch_detection import prepare_mutation, record_mutation
from workstation.task_compiler import capture_raw_result

logger = logging.getLogger(__name__)


def workstation_pre_dispatch_hook(
    tool_name: str,
    final_args: dict[str, Any],
    call_id: str,
    context: dict[str, Any],
) -> None:
    """Invoked at the authorized pre-effect boundary before real external I/O."""
    agent = context.get("agent")
    if agent is None:
        return
    ledger = getattr(agent, "_work_tool_observations", None)
    # Determine effect whether or not the optional observation ledger exists.
    try:
        from tools.effects import tool_effect
        effect = tool_effect(tool_name, args=final_args).value
    except Exception:
        effect = "UNKNOWN"
    if isinstance(ledger, list):
        # Recorded before I/O. Missing post-tool receipt is NOT successful read.
        ledger.append({"call_id": call_id, "tool": tool_name,
                       "effect": effect, "status": "started"})
        # Only immutable, non-secret coordinates enter the recovery ticket.
        if tool_name == "workstation_db_trello_api_push":
            ledger[-1]["recovery_descriptor"] = {
                "tool": tool_name,
                "card_id": str(final_args.get("card_id", ""))[:80],
                "review_run_id": str(final_args.get("review_run_id", ""))[:110],
            }
        elif tool_name == "whatsapp_send_message":
            ledger[-1]["recovery_descriptor"] = {
                "tool": tool_name,
                "operation_id": str(call_id)[:128],
            }
    try:
        # A recovery child or resumed parent must NEVER repeat an uncertain
        # external mutation. The fence applies before the real tool handler.
        if effect not in {"PURE_READ", "DISCOVERY"}:
            from workstation.evidence_recovery import enforce_recovery_scope
            enforce_recovery_scope(getattr(agent, "_canonical_work_task_id", None),
                                   tool_name, final_args)
        prepare_mutation(agent, tool_name, final_args)
    except Exception as exc:
        logger.warning("Workstation prepare_mutation hook failed: %s", exc)
        raise


def workstation_raw_post_tool_observer(
    tool_name: str,
    final_args: dict[str, Any],
    call_id: str,
    raw_result: Any,
    duration: float,
    context: dict[str, Any],
) -> None:
    """Invoked immediately after tool handler returns, before any output truncation or spill."""
    agent = context.get("agent")
    if agent is not None:
        ledger = getattr(agent, "_work_tool_observations", None)
        if isinstance(ledger, list):
            from agent.tool_guardrails import classify_tool_failure
            try:
                text_result = raw_result if isinstance(raw_result, str) else json.dumps(raw_result)
                status = ("denied" if not context.get("dispatched", True) else
                          "failed" if classify_tool_failure(tool_name, text_result)[0] else "completed")
                if tool_name == "browser_click" and status == "completed":
                    structured = json.loads(text_result) if text_result.lstrip().startswith("{") else {}
                    if isinstance(structured, dict) and structured.get("success") is False:
                        status = "failed"
            except Exception:
                status = "unknown"
            for record in reversed(ledger):
                if (record.get("call_id") == call_id and record.get("tool") == tool_name
                        and record.get("status") == "started"):
                    record["status"] = status
                    if tool_name == "whatsapp_send_message" and status == "failed":
                        try:
                            verdict = json.loads(text_result)
                        except (ValueError, TypeError):
                            verdict = {}
                        if (isinstance(verdict, dict)
                                and verdict.get("sent") is False
                                and verdict.get("state") == "FAILED"
                                and verdict.get("failure_phase") in {"PRE_SEND", "RESOLVE_RECIPIENT"}):
                            record["no_effect"] = True
                    if tool_name == "browser_click" and status == "failed":
                        try:
                            failure = json.loads(text_result) if isinstance(text_result, str) else {}
                        except (ValueError, TypeError):
                            failure = {}
                        if isinstance(failure, dict):
                            # model_tools serializes a raised native Browser error
                            # as "Error executing browser_click: <native reason>".
                            # Match only this exact tool/error combination.
                            reason = "browser_input_delivery_unverified"
                            error_text = str(failure.get("error") or failure.get("message") or "")
                            if (failure.get("error_code") == reason
                                    or error_text in {
                                        reason,
                                        f"Error executing browser_click: {reason}",
                                        f"Error executing tool 'browser_click': {reason}",
                                    }):
                                record["browser_uncertain_error"] = reason
                    break
            else:
                # A post-only call did not cross the observed pre-dispatch gate.
                # Never certify the turn as read-only from an incomplete ledger.
                ledger.append({"call_id": call_id, "tool": tool_name,
                               "effect": "UNKNOWN", "status": status})
        dispatched = context.get("dispatched", True)
        duration_ms = duration * 1000 if duration is not None else None
        from workstation.task_compiler import durable_execution_active
        if dispatched and durable_execution_active():
            from workstation.experience_compiler.progressive import capture_progressive
            from workstation.artifacts import ArtifactStore
            from tools.effects import tool_effect, READ_EFFECTS
            from workstation.routing import canonical_route_for_tool
            from agent.tool_guardrails import classify_tool_failure
            text = raw_result if isinstance(raw_result, str) else json.dumps(raw_result)
            failed = classify_tool_failure(tool_name, text)[0]
            t_id = getattr(agent, "_canonical_work_task_id", None)
            r_id = getattr(agent, "_canonical_work_run_id", None)
            op_id = getattr(agent, "_current_operation_id", None) or call_id
            c_route = canonical_route_for_tool(tool_name)
            outcome = "failed" if failed else "observed" if tool_effect(tool_name) in READ_EFFECTS else "uncertain"
            artifacts = ArtifactStore()
            from workstation.recipes import sanitize
            raw_data = raw_result if isinstance(raw_result, (dict, list)) else (
                json.loads(raw_result) if isinstance(raw_result, str) and raw_result.strip().startswith(("{", "[")) else {"raw": raw_result}
            )
            try:
                raw_ref = artifacts.store(
                    t_id or "experience",
                    f"raw_result_{op_id}.json",
                    sanitize(raw_data),
                    schema="workstation.raw_tool_result.v1",
                ).ref
            except Exception:  # health: allow BLE001 -- artifact store failure in telemetry observer falls back cleanly to None
                raw_ref = None
            agent._last_raw_result_ref = raw_ref
            agent._current_operation_id = op_id
            ref = capture_progressive(artifacts, task_id=t_id,
                run_id=r_id,
                operation_id=op_id,
                primitive=tool_name, route=c_route,
                outcome=outcome,
                raw_result_ref=raw_ref,
                state=raw_data if isinstance(raw_data, dict) else None)
            agent._last_progressive_ref = ref
            if ref:
                try:
                    from workstation.experience_compiler.compilability_monitor import notify_online_compilability
                    from workstation.integrations.hermes.run_local_adoption import build_run_adoption_owner
                    notify_online_compilability(
                        ref=ref,
                        task_id=t_id,
                        run_id=r_id,
                        operation_id=op_id,
                        primitive=tool_name,
                        route=c_route,
                        outcome=outcome,
                        event_kind="tool_finished",
                        agent=agent,
                        owner=build_run_adoption_owner(agent),
                    )
                except Exception as mon_exc:
                    logger.debug("notify_online_compilability skipped: %s", mon_exc)
        try:
            record_mutation(
                agent,
                tool_name,
                final_args,
                raw_result,
                dispatched=dispatched,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            logger.warning("Workstation record_mutation observer failed: %s", exc)

        # Capture an independent, owner-bound file readback before the turn ends.
        # This is a read-only probe; never repeat the write when verification fails.
        if tool_name == "write_file" and dispatched:
            try:
                from workstation.direct_file_readback import capture_file_write_readback
                session_id = (getattr(agent, "_conversation_root_id", lambda: None)()
                              or getattr(agent, "session_id", None))
                proof = capture_file_write_readback(
                    tool_name, final_args, raw_result,
                    task_id=getattr(agent, "_canonical_work_task_id", None),
                    run_id=getattr(agent, "_canonical_work_run_id", None),
                    session_id=session_id, call_id=call_id,
                )
                if proof:
                    for row in reversed(getattr(agent, "_work_tool_observations", [])):
                        if row.get("call_id") == call_id and row.get("tool") == tool_name:
                            row["file_readback"] = proof
                            break
                    from workstation.batch_detection import call_key
                    mutation = getattr(agent, "_work_mutation_evidence", {}).get(
                        call_key(tool_name, final_args))
                    if isinstance(mutation, dict) and (
                        str(mutation.get("task_id")) == proof["task_id"]
                        and str(mutation.get("run_id")) == proof["run_id"]
                    ):
                        mutation.update({"status": "persisted", "persisted": True,
                                         "verifier_status": "verified",
                                         "verification_evidence_ref": proof["evidence_ref"]})
                        from workstation.artifacts import ArtifactStore
                        ArtifactStore().store(
                            str(session_id), "mutation_" + proof["operation_id"] + ".json",
                            mutation,
                        )
            except Exception:
                logger.warning("Direct file readback failed closed", exc_info=True)

    # Provider-specific read-only probes reuse existing authority and receipts.
    # Never redispatch an external mutation when its acknowledgement is lost.
    if (agent is not None and context.get("dispatched", True)
            and tool_name in {"workstation_db_trello_api_push", "whatsapp_send_message"}):
        try:
            from workstation.external_readback import capture_external_readback
            session_id = (getattr(agent, "_conversation_root_id", lambda: None)()
                          or getattr(agent, "session_id", None))
            proof = capture_external_readback(
                tool_name, final_args, raw_result,
                task_id=getattr(agent, "_canonical_work_task_id", None),
                run_id=getattr(agent, "_canonical_work_run_id", None),
                session_id=session_id, call_id=call_id,
            )
            if proof:
                for row in reversed(getattr(agent, "_work_tool_observations", [])):
                    if (row.get("call_id") == call_id and row.get("tool") == tool_name
                            and row.get("effect") in {"MUTATION", "IDEMPOTENT_WRITE"}
                            and row.get("status") == "completed"):
                        row["external_readback"] = proof
                        from workstation.batch_detection import call_key
                        mutation = getattr(agent, "_work_mutation_evidence", {}).get(
                            call_key(tool_name, final_args))
                        if (isinstance(mutation, dict)
                                and str(mutation.get("task_id")) == proof["task_id"]
                                and str(mutation.get("run_id")) == proof["run_id"]):
                            mutation.update({
                                "status": "persisted", "persisted": True,
                                "verifier_status": "verified",
                                "verification_evidence_ref": proof["evidence_ref"],
                            })
                            from workstation.artifacts import ArtifactStore
                            ArtifactStore().store(
                                str(session_id),
                                "mutation_" + call_key(tool_name, final_args) + ".json",
                                mutation,
                            )
                        break
        except Exception:
            logger.warning("External owner readback failed closed", exc_info=True)

    # P1: same-owner causal ACK + a NEW native read, never external completion.
    # Do not promote an observed DOM into a persisted remote mutation receipt.
    if (agent is not None and context.get("dispatched", True)
            and tool_name in {"browser_click", "browser_type"}):
        try:
            task_id = getattr(agent, "_canonical_work_task_id", None)
            run_id = getattr(agent, "_canonical_work_run_id", None)
            session_id = (getattr(agent, "_conversation_root_id", lambda: None)()
                          or getattr(agent, "session_id", None))
            if task_id and run_id is not None and session_id:
                from tools.browser_workstation import call_workstation_browser
                from workstation.native_browser_evidence import capture_native_browser_operation

                def fresh_snapshot():
                    return call_workstation_browser(
                        "browser_snapshot", {"full": False}, task_id=str(task_id),
                        session_id=str(session_id), run_id=str(run_id),
                        kanban_card_id=str(task_id), model_facing=False,
                    )

                proof = capture_native_browser_operation(
                    tool_name, raw_result, task_id=str(task_id),
                    session_id=str(session_id), run_id=str(run_id),
                    call_id=str(call_id), snapshot_reader=fresh_snapshot,
                )
                if proof:
                    for row in reversed(getattr(agent, "_work_tool_observations", [])):
                        if (row.get("call_id") == call_id and
                                row.get("tool") == tool_name and
                                "native_browser_evidence" not in row):
                            row["native_browser_evidence"] = proof
                            break
        except Exception:
            logger.warning("Native browser observation failed closed", exc_info=True)

    try:
        capture_raw_result(call_id, raw_result)
    except Exception as exc:
        logger.warning("Workstation capture_raw_result observer failed: %s", exc)

    try:
        from workstation.telemetry import TelemetryEventType, emit_event
        from workstation.recipes import sanitize, canonical_bytes
        from workstation.routing import canonical_route_for_tool
        from agent.runtime_events import serialized_size

        dispatched = context.get("dispatched", True)
        emit_event(TelemetryEventType.TOOL_COMPLETED, source_owner="workstation.tool_observer",
            session_id=getattr(agent, "session_id", None),
            task_id=getattr(agent, "_canonical_work_task_id", None),
            run_id=getattr(agent, "_canonical_work_run_id", None), call_id=call_id,
            operation_id=getattr(agent, "_current_operation_id", None) or call_id,
            route=canonical_route_for_tool(tool_name), tool_calls=1 if dispatched else 0,
            status="observed" if dispatched else "denied", duration_ms=duration * 1000 if duration is not None else None,
            request_bytes=serialized_size(final_args), result_bytes=serialized_size(raw_result),
            dedupe_key=f"tool:{getattr(agent, 'session_id', None)}:{call_id}" if call_id else None,
            payload={"tool_name": tool_name,
                     "read_fingerprint": hashlib.sha256(canonical_bytes(sanitize(final_args))).hexdigest()
                     if tool_name in {"browser_snapshot", "browser_extract_items", "browser_console"} else None})
    except Exception:
        logger.debug("Tool telemetry unavailable", exc_info=True)

    if tool_name in {"browser_navigate", "browser_tab_activate", "browser_show", "browser_create"}:
        try:
            from workstation.system1.contextual_preload import maybe_preload_after_browser_tool

            maybe_preload_after_browser_tool(
                tool_name, raw_result, dispatched=context.get("dispatched", True),
            )
        except Exception:
            logger.warning("Browser-triggered Laya preload check failed", exc_info=True)
