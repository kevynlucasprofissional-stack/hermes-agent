from __future__ import annotations

import hashlib
import logging
import json
from typing import Any, Optional
from collections.abc import Iterable
import sqlite3
from datetime import datetime, timezone

from hermes_cli import kanban_db, kanban_db_connect
from workstation.config import load_workstation_config
from workstation.contracts import BrowserTaskReport, DiscoveredTask, ExecutionEventKind, RiskLevel
from workstation.journal import ExecutionJournal
from workstation.contracts import (AcceptanceContract, AcceptanceEvaluator, MessageEnvelope, OutcomeStatus, TaskOutcome)
from dataclasses import asdict

_log = logging.getLogger(__name__)


def _advisory_observation_issues(observed_tools, *, trace_truncated: bool) -> list[str]:
    """A read-only answer cannot be accepted if the complete tool lane is unknown."""
    if trace_truncated or not isinstance(observed_tools, list):
        return ["Read-only tool observation is incomplete"]
    if not observed_tools:
        return ["Read-only work has no observed source read"]
    for item in observed_tools:
        if (not isinstance(item, dict)
                or item.get("effect") not in {"PURE_READ", "DISCOVERY"}
                or item.get("status") != "completed"):
            return ["Read-only task has an unverified, failed, or mutable tool operation"]
    return []


def _persist_advisory_result(artifacts, task_id: str, session_id: str, run_id: str, result: str):
    """Prove a user-visible advisory result exists in the owner's durable store.

    This proves delivery/persistence, not the factual correctness of the answer.
    """
    from workstation.contracts import EvidenceRef
    payload = {"task_id": task_id, "session_id": session_id,
               "run_id": run_id, "result": result}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    stored = artifacts.store(task_id, f"advisory_result_{digest}.json", payload,
                             schema="hermes.advisory_result.v1")
    readback = artifacts.resolve_structured(stored.ref)
    if readback.get("content") != payload or readback.get("sha256") != stored.sha256:
        raise ValueError("Advisory result persisted readback does not match the turn")
    evidence = EvidenceRef("advisory_result", stored.ref, sha256=stored.sha256,
                           task_id=task_id, run_id=run_id, verifier="advisory_result_readback")
    verifier = {"verifier": "advisory_result_readback", "passed": True,
                "evidence_ref": stored.ref, "task_id": task_id, "run_id": run_id}
    return evidence, verifier


def _verified_native_navigation(artifacts, trace, task_id: str, session_id: str, run_id: str):
    """Verify one adaptive navigation against Electron's persisted BrowserTask state."""
    from workstation.contracts import EvidenceRef
    from workstation.experience_compiler.models import TransitionSample
    from workstation.execution_policy import EvidenceStrength
    from workstation.recipes import digest
    from tools.browser_workstation import read_native_browser_session_state

    read_only_tools = {
        'browser_snapshot',
        'browser_vision',
        'browser_get_images',
        'browser_read_http',
        'browser_extract_items',
        'snapshot',
        'vision',
        'get_images',
        'read_http',
        'extract_items',
    }

    nav_actions = []
    for step in trace:
        tool = step.get('tool')
        outcome = step.get('outcome')
        if outcome == 'failed':
            raise ValueError("adaptive browser completion encountered a failed step in trace")
        if tool == 'browser_navigate':
            nav_actions.append(step)
        elif tool in read_only_tools:
            continue
        else:
            raise ValueError(f"adaptive browser completion requires exactly one bounded navigation and optional read-only observations, found unexpected action: {tool}")

    if len(nav_actions) != 1:
        raise ValueError("adaptive browser completion requires exactly one bounded navigation and optional read-only observations")
    action = nav_actions[0]
    if (action.get('tool') != 'browser_navigate' or action.get('route') != 'native_browser'
            or action.get('runtime') != 'electron-chromium'
            or action.get('outcome') != 'executed_unverified'
            or action.get('task_id') != task_id or str(action.get('run_id')) != run_id
            or not action.get('operation_id')):
        raise ValueError("adaptive navigation lineage or route is not verified")
    sample = TransitionSample.from_dict(artifacts.read_json(action['transition_ref']))
    if (sample.provenance.task_id != task_id or sample.provenance.run_id != run_id
            or sample.provenance.operation_id != action['operation_id']
            or sample.provenance.trust_class != 'trusted_runtime'
            or not sample.provenance.authority_ref or not sample.provenance.authority_scope):
        raise ValueError("adaptive navigation lacks trusted authority provenance")
    raw = artifacts.read_json(action['after_state_ref'])
    if (not isinstance(raw, dict) or raw.get('success') is not True
            or raw.get('runtime') != 'electron-chromium'
            or raw.get('readiness') != 'stable'):
        raise ValueError("native navigation did not report a stable successful effect")
    expected_url = str(action.get('arguments', {}).get('url') or '')
    from urllib.parse import urlsplit
    expected = urlsplit(expected_url)
    reported = urlsplit(str(raw.get('url') or ''))
    if (expected.scheme, expected.hostname, expected.path or '/') != (
            reported.scheme, reported.hostname, reported.path or '/'):
        raise ValueError("native navigation result drifted from the requested URL")
    expected_op_id = action.get('operation_id')
    readback = read_native_browser_session_state(
        task_id, session_id, run_id, expected_url,
        expected_operation_id=expected_op_id,
        require_owner_receipt=True,
    )
    last_receipt = readback.get('last_receipt') or {}
    proven_op_id = last_receipt.get('operationId')
    if not proven_op_id or proven_op_id != expected_op_id:
        raise ValueError(f"Browser owner receipt does not match expected operation identity: expected {expected_op_id}, got {proven_op_id}")
    saved_at_str = readback['saved_at']
    saved_at = datetime.fromisoformat(saved_at_str)
    captured_at = datetime.fromisoformat(action['captured_at'])
    if saved_at.tzinfo is None or captured_at.tzinfo is None or not -5 <= (captured_at - saved_at).total_seconds() <= 120:
        raise ValueError("BrowserSessionState readback is stale or temporally inconsistent")
    observed_at = saved_at_str
    evidence = {
        **readback,
        'operation_id': proven_op_id,
        'observer': 'workstation.browser_session_state',
        'source_kind': 'browser_local_persistence',
        'trust_class': 'trusted_runtime',
        'evidence_strength': int(EvidenceStrength.SEMANTIC_PERSISTED_READBACK),
        'resource_id': f"browser_task:{task_id}:tab:{readback['tab_id']}",
        'resource_version': str(readback.get('revision', 0)),
        'observed_at': observed_at,
        'read_after_write': True,
        'covered_predicates': ['host', 'url', 'page_family', 'recovery_state'],
        'raw_result_ref': action['after_state_ref'],
        'transition_ref': action['transition_ref'],
    }
    stored = artifacts.store(task_id, 'browser_readback_' + digest(evidence) + '.json',
                             evidence, schema='hermes.browser_local_readback.v1')
    ref = EvidenceRef('browser_local_persistence', stored.ref, sha256=stored.sha256,
                      task_id=task_id, run_id=run_id, operation_id=proven_op_id,
                      verifier='native_browser_session_state')
    verifier = {'verifier': 'native_browser_session_state', 'passed': True,
                'evidence_ref': stored.ref, 'task_id': task_id, 'run_id': run_id,
                'operation_id': proven_op_id, 'observer': evidence['observer'],
                'source_kind': evidence['source_kind'], 'trust_class': evidence['trust_class'],
                'evidence_strength': evidence['evidence_strength'],
                'covered_predicates': evidence['covered_predicates'],
                'observed_at': observed_at, 'read_after_write': True}
    return ref, verifier


def is_multistep_request(prompt: str) -> bool:
    """Conservative durable-work signal, never a single topic word.

    Browser, site, research and question words alone do not create responsibilities.
    A trusted ingress envelope is independently required by the bridge.
    """
    import re

    if not isinstance(prompt, str):
        return False
    text = " ".join(prompt.casefold().strip().split())
    if re.match(r"^(multistep workflow to|workflow para|pipeline para)\b", text):
        return True
    if re.search(r"\b(execute (this |the )?multistep workflow|execute este workflow)\b", text):
        return True
    if not text or re.match(
        r"^(como|qual|quais|porque|por que|o que|what|how|why|can you explain|explique|mostre|descreva|resuma|defina|me explique|me mostre|me ajude a entender|me diga|me conte)\b", text
    ):
        return False
    if re.search(
        r"\b(execute|implemente|crie|configure|automatize|rode|run|implement|create)\b"
        r".+\b(multistep|workflow|pipeline|passo a passo|lote de tarefas)\b", text
    ):
        return True
    if re.search(r"\b(first|primeiro)\b.+\b(then|depois|finally|por fim)\b", text):
        return True
    if re.search(r"\b(then|depois|em seguida)\b", text):
        verbs = re.findall(
            r"\b(extract|verify|create|generate|build|test|fix|implement|"
            r"extraia|verifique|crie|gere|implemente|corrija|teste|documente|"
            r"investigue|configure|salve|publique|escreva)\b", text
        )
        if len(verbs) >= 2:
            return True
    # Explicit multi-action assignments; prohibitions are constraints, not steps.
    actions = [
        match.group(1) for match in re.finditer(
            r"\b(investigue|corrija|implemente|teste|documente|crie|gere|"
            r"atualize|construa|configure|desenvolva|revise|integre|escreva|"
            r"fix|implement|build|generate|create|test|verify|deploy)\b", text
        )
        if not re.search(
            r"\b(?:do not|don't|never|n[aã]o)\s+$",
            text[max(0, match.start() - 16):match.start()],
        )
    ]
    return len(set(actions)) >= 2 and bool(re.search(r"[,;]|\b(e|and|depois)\b", text))


class WorkstationKanbanBridge:
    """Bridge between Workstation tasks and the canonical Kanban SQLite database."""

    def __init__(self, *, board: str | None = None) -> None:
        self.board = board

    def get_connection(self) -> sqlite3.Connection:
        return kanban_db_connect.connect(board=self.board)

    def promote_request_if_multistep(
        self,
        prompt: str,
        *,
        session_id: str,
        title: str | None = None,
        force: bool = False,
        envelope: MessageEnvelope | None = None,
        acceptance_contract: AcceptanceContract | None = None,
        defer_execution: bool = False,
    ) -> str | None:
        """Automatically create a parent Kanban task for a multistep request."""
        if (envelope is None or not envelope.can_create_work
                or envelope.session_id != session_id or envelope.content != prompt):
            return None
        # A caller may only bypass automatic intent classification if
        # trusted ingress explicitly marked this request as delegated work.
        # Plain CREATE_WORK authority alone does not turn a point action
        # into a durable task through a force flag.
        if force and (not isinstance(envelope.metadata, dict)
                      or envelope.metadata.get("explicit_force_work") is not True):
            return None
        cfg = load_workstation_config()
        from workstation.work_intent import work_intent
        intent = work_intent(envelope)
        should_create = force or (
            cfg.raw.get("tasks", {}).get("create_kanban_for_multistep", True)
            and intent.requires_task
        )
        if not should_create:
            return None

        clean_title = (title or prompt.strip().split("\n")[0])[:80]
        claimed_run_id = None
        with self.get_connection() as conn:
            if defer_execution:
                # The caller's preflight is a separate read: two workers can
                # observe no task and both create. Serialize the admission at
                # the canonical SQLite owner across turns and processes.
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT id FROM tasks WHERE session_id=? AND body=? "
                    "AND created_by='workstation' "
                    "AND status IN ('triage','todo','ready','running','blocked','scheduled') "
                    "ORDER BY created_at DESC, id DESC LIMIT 1",
                    (session_id, prompt),
                ).fetchone()
                if row is not None:
                    conn.commit()
                    return str(row[0])
            task_id = kanban_db.create_task(
                conn,
                title=clean_title,
                body=prompt,
                created_by="workstation",
                session_id=session_id,
                board=self.board,
                initial_status="running", triage=defer_execution,
                idempotency_key=(
                    "workstation:" + hashlib.sha256(
                        f"{session_id}:{envelope.correlation_id}:{prompt}".encode()
                    ).hexdigest()
                    if defer_execution and envelope.correlation_id else None
                ),
            )
            if not defer_execution:
                claimed_task = kanban_db.claim_task(conn, task_id, claimer=f"workstation:{session_id}")
                if claimed_task and claimed_task.current_run_id:
                    claimed_run_id = claimed_task.current_run_id
            contract = acceptance_contract or AcceptanceContract()
            conn.execute("INSERT OR IGNORE INTO task_acceptance_contracts(task_id, contract_json) VALUES (?,?)",
                         (task_id, json.dumps(asdict(contract))))
            conn.commit()

        # Start journal for this task
        journal = ExecutionJournal(task_id, session_id)
        journal.record(
            ExecutionEventKind.TASK_CREATED,
            f"Workstation task promoted into Kanban: {clean_title}",
            metadata={"source": "automatic_multistep_promotion", "prompt": prompt, "run_id": claimed_run_id},
        )
        return task_id

    def start_triaged_task(self, task_id: str, *, session_id: str, objective: str) -> str:
        """Claim a run at the first real execution boundary; never adopt a foreign run.

        Existing Kanban transitions own CAS, parent checks and worker notification.
        No blocked/cancelled/revoked task is reopened here.
        """
        with self.get_connection() as conn:
            task = kanban_db.get_task(conn, task_id)
            if task is None or task.session_id != session_id or task.body != objective:
                raise PermissionError("canonical_task_session_or_objective_mismatch")
            if task.status == "triage":
                if not kanban_db.specify_triage_task(conn, task_id):
                    raise RuntimeError("triage_transition_lost")
                task = kanban_db.get_task(conn, task_id)
            if task.status != "ready" or task.current_run_id is not None:
                raise RuntimeError(f"canonical_task_not_claimable:{task.status}")
            claimed = kanban_db.claim_task(conn, task_id, claimer=f"workstation:{session_id}")
            if not claimed or not claimed.current_run_id:
                raise RuntimeError("canonical_run_claim_lost")
            return str(claimed.current_run_id)

    def record_discovered_followup(
        self,
        parent_task_id: str,
        followup: DiscoveredTask,
    ) -> str:
        """Record a discovered child task into Kanban with parent dependency."""
        followup.validate()

        evidence = [
            {"kind": item.kind, "uri": item.uri, "summary": item.summary, "sha256": item.sha256}
            for item in followup.evidence
        ]
        body = "\n".join([
            f"Reason: {followup.reason}",
            f"Discovered by: {followup.discovered_by}",
            f"Origin session: {followup.origin_session_id}",
            "Discovery evidence:",
            json.dumps(evidence, ensure_ascii=False),
        ])

        with self.get_connection() as conn:
            child_task_id = kanban_db.create_task(
                conn,
                title=followup.title,
                body=body,
                created_by=followup.discovered_by,
                # A required child must be runnable immediately while the
                # parent waits.  Kanban links encode prerequisites, so the
                # dependency is child -> parent (not parent -> child). The
                # durable parent_task_id remains in the child body/journal
                # projection as the product hierarchy identity.
                parents=[] if followup.required_for_parent else [parent_task_id],
                session_id=followup.origin_session_id,
                board=self.board,
            )
            if followup.required_for_parent:
                try:
                    parent_task = kanban_db.get_task(conn, parent_task_id)
                    expected_run_id = parent_task.current_run_id if parent_task else None
                    kanban_db.link_tasks(conn, child_task_id, parent_task_id, expected_child_run_id=expected_run_id)
                    kanban_db.block_task(
                        conn,
                        parent_task_id,
                        reason=f"Blocked by required follow-up child task {child_task_id}: {followup.title}",
                        kind="dependency",
                    )
                except Exception as e:
                    _log.warning("Could not transition parent task %s to blocked: %s", parent_task_id, e)

        # Update followup instance with assigned task_id
        followup.task_id = child_task_id

        # Record into journal
        journal = ExecutionJournal(parent_task_id, followup.origin_session_id)
        journal.record(
            ExecutionEventKind.FOLLOWUP_CREATED,
            f"Discovered child task {child_task_id}: {followup.title}",
            evidence=followup.evidence,
            metadata={
                "child_task_id": child_task_id,
                "reason": followup.reason,
                "discovered_by": followup.discovered_by,
                "origin_session_id": followup.origin_session_id,
                "parent_task_id": parent_task_id,
                "required_for_parent": followup.required_for_parent,
                "evidence": evidence,
            },
        )
        return child_task_id

    def complete_task_with_report(
        self,
        task_id: str,
        report: BrowserTaskReport,
        *,
        expected_run_id: int | None = None,
    ) -> bool:
        """Complete Kanban task with structured Workstation report metadata."""
        metadata = report.to_kanban_metadata()
        if report.task_id != task_id:
            raise ValueError("report task identity mismatch")
        status = report.outcome_status or (
            OutcomeStatus.VERIFIED_COMPLETED if report.completed else OutcomeStatus.BLOCKED
        )
        if not report.completed and status == OutcomeStatus.VERIFIED_COMPLETED:
            status = OutcomeStatus.BLOCKED
        target_run_id = expected_run_id
        if target_run_id is None and getattr(report, "run_id", None):
            try:
                target_run_id = int(report.run_id)
            except (ValueError, TypeError):
                target_run_id = None
        outcome = TaskOutcome(
            task_id=task_id, session_id=report.session_id, objective=report.objective,
            status=status, summary=report.result, evidence_refs=report.evidence,
            verifier_results=report.verifier_results, deliverables=report.deliverables,
            pending_items=report.pending_items, uncertain_mutation=report.uncertain_mutation,
            run_id=str(target_run_id) if target_run_id is not None else None,
            operation_id=report.operation_id,
        )
        with self.get_connection() as conn:
            cur_run_id = kanban_db._current_run_id(conn, task_id)
            if target_run_id is not None and cur_run_id is not None and cur_run_id != target_run_id:
                journal = ExecutionJournal(task_id, report.session_id)
                journal.record(
                    ExecutionEventKind.PROGRESS,
                    f"Stale run {target_run_id} rejected (current run is {cur_run_id})",
                    evidence=report.evidence,
                    metadata={"boundary": "acceptance_commit_failed", "task_id": task_id, "expected_run_id": target_run_id, "current_run_id": cur_run_id},
                )
                return False
            saved = conn.execute("SELECT contract_json FROM task_acceptance_contracts WHERE task_id=?", (task_id,)).fetchone()
        contract = AcceptanceContract(**json.loads(saved[0])) if saved else AcceptanceContract()
        reasons = AcceptanceEvaluator().evaluate(outcome, contract)
        if reasons:
            if outcome.uncertain_mutation:
                outcome.status = OutcomeStatus.UNCERTAIN
            elif outcome.status == OutcomeStatus.VERIFIED_COMPLETED:
                outcome.status = OutcomeStatus.FAILED if "verifier_failed" in reasons else OutcomeStatus.BLOCKED
            # 'needs_input' means an actual human decision is required.
            # Missing machine evidence is a capability/verification defect, not
            # an invitation to unblock and repeat a potentially mutable task.
            block_kind = (
                "needs_input" if outcome.uncertain_mutation
                or outcome.status == OutcomeStatus.WAITING_FOR_HUMAN or report.approvals
                else "transient" if outcome.status in {OutcomeStatus.FAILED, OutcomeStatus.UNCERTAIN}
                else "capability"
            )
            with self.get_connection() as conn:
                kanban_db.block_task(
                    conn, task_id,
                    reason="; ".join(reasons),
                    kind=block_kind,
                    expected_run_id=target_run_id,
                )
            ExecutionJournal(task_id, report.session_id).record(
                ExecutionEventKind.PROGRESS, report.result, evidence=report.evidence,
                metadata={"completed": False, "outcome": outcome.to_dict(), "acceptance_reasons": reasons},
            )
            return False
        metadata["workstation"]["outcome"] = outcome.to_dict()
        metadata["workstation"]["acceptance_approved"] = True
        metadata["workstation"]["acceptance_contract"] = asdict(contract)
        journal = ExecutionJournal(task_id, report.session_id)
        journal.read_events()  # Corrupt evidence fails closed before the canonical commit.
        if report.verifier_results:
            from agent.verification_evidence import record_outcome_verifiers
            metadata["workstation"]["verification_event_ids"] = record_outcome_verifiers(
                task_id, report.session_id, report.verifier_results, environment=journal.environment)
        journal.record(ExecutionEventKind.PROGRESS, "verified outcome submitted to canonical acceptance gate",
                       evidence=report.evidence, metadata={"boundary": "acceptance", "outcome": outcome.to_dict()})
        with self.get_connection() as conn:
            success = kanban_db.complete_task(
                conn,
                task_id=task_id,
                result=report.result,
                summary=report.result,
                metadata=metadata,
                expected_run_id=target_run_id,
            )

        if not success:
            journal.record(
                ExecutionEventKind.PROGRESS,
                "Canonical completion CAS rejected (stale run or state conflict)",
                evidence=report.evidence,
                metadata={"boundary": "acceptance_commit_failed", "task_id": task_id, "expected_run_id": target_run_id},
            )
            return False
        journal = ExecutionJournal(task_id, report.session_id)
        journal.record(
            ExecutionEventKind.TASK_COMPLETED,
            f"Workstation task completed: {report.result}",
            evidence=report.evidence,
            metadata={"completed": report.completed, "sites": report.sites,
                      "outcome": outcome.to_dict(), "acceptance_approved": True,
                      "verification_event_ids": metadata["workstation"].get("verification_event_ids", [])},
        )
        from workstation.telemetry import TelemetryEventType, emit_event
        emit_event(TelemetryEventType.OUTCOME_ACCEPTED,
                   source_owner="workstation.kanban", session_id=report.session_id,
                   task_id=task_id, run_id=str(target_run_id) if target_run_id is not None else None,
                   operation_id=report.operation_id, status=outcome.status.value,
                   evidence_refs=tuple(report.evidence),
                   dedupe_key=f"outcome:{task_id}:{target_run_id}",
                   payload={"verified": outcome.status == OutcomeStatus.VERIFIED_COMPLETED})
        # A verified read-only recovery child may now finish its parent by
        # fresh owner readback. This is post-commit and never repeats the write.
        try:
            from workstation.evidence_recovery import on_recovery_child_completed
            on_recovery_child_completed(task_id=task_id, board=self.board)
        except Exception:
            _log.warning("Evidence recovery projection failed after child DONE", exc_info=True)
        # A read-only advisory answer is not an operational procedure to mine.
        # Keep its verified DONE synchronous and independent of the optional
        # (and potentially expensive) Experience Compiler projection.
        if contract.policy == "advisory":
            return success
        from workstation.experience_compiler.corpus import ExperienceCorpus
        from workstation.experience_compiler.compiler import ExperienceCompiler
        from workstation.experience_compiler.lifecycle import ExperienceValidationPromotionCoordinator
        from workstation.operational_capabilities import OperationalCapabilityRegistry, CapabilityValidationError
        from workstation.artifacts import ArtifactStore
        artifacts = ArtifactStore()
        # Mining is a projection after canonical commit; insufficient state evidence
        # remains observations and cannot affect completion or grant write authority.
        corpus = None
        learned = []
        try:
            corpus = ExperienceCorpus(artifacts, discover=True)
            accepted_ref = corpus.accept_run(journal, outcome)
            if accepted_ref:
                # Only the canonical acceptance owner may introduce VERIFIED_SUCCESS
                # into the online monitor. Raw tool ACKs remain observations.
                try:
                    from workstation.experience_compiler.accepted_observer import notify_canonical_acceptance
                    notify_canonical_acceptance(corpus, accepted_ref, task_id, str(outcome.run_id))
                except Exception:
                    import logging
                    logging.getLogger(__name__).warning("Accepted experience learning notification failed", exc_info=True)
            registry = OperationalCapabilityRegistry(artifacts)
            compiler = ExperienceCompiler(registry, corpus)
            learned = compiler.mine()
            coordinator = ExperienceValidationPromotionCoordinator(
                registry,
                compiler,
                artifacts,
            )
            for capability in learned:
                journal.record(
                    ExecutionEventKind.ACTION,
                    'experience operational candidate discovered; causal validation required',
                    metadata={'capability_id': capability.id, 'capability_version': capability.version},
                )
                cycle_result = coordinator.process_candidate(
                    capability,
                    task_id=task_id,
                    run_id=str(target_run_id) if target_run_id is not None else None,
                    journal=journal,
                )
                if cycle_result.action == "promoted":
                    journal.record(
                        ExecutionEventKind.ACTION,
                        'experience operational candidate promoted under policy',
                        metadata={'capability_id': capability.id, 'capability_version': capability.version},
                    )
                elif cycle_result.action == "held_as_candidate":
                    journal.record(
                        ExecutionEventKind.ACTION,
                        'experience operational candidate validation pending',
                        metadata={'capability_id': capability.id, 'reasons': list(cycle_result.reasons)},
                    )
        except (OSError, ValueError, TypeError, CapabilityValidationError) as error:
            # Experience mining is optional and runs AFTER canonical DONE.
            # Legacy corpus/type failures cannot turn a committed task into
            # an apparent failed turn or invite an unsafe retry.
            _log.warning("Experience projection failed after accepted completion: %s",
                         type(error).__name__, exc_info=True)
            learned = []
        if report.repeatability_hint and report.procedure_steps and corpus is not None and not corpus.refs:
            from workstation.memory import ProceduralMemory
            from workstation.routines import RoutinePromotionService
            memory = ProceduralMemory()
            candidate = RoutinePromotionService(memory).experience_candidate(
                outcome, contract, site=report.procedure_scope,
                steps=report.procedure_steps, repeatable=True,
                metrics={"actions": len(report.actions), "tokens": report.input_tokens + report.output_tokens,
                         "duration_seconds": report.duration_seconds})
            if candidate:
                compatibility = report.procedure_compatibility
                if compatibility:
                    candidate.scope = compatibility['scope']
                    candidate.capability_fingerprint = compatibility['fingerprint']
                    candidate.preconditions = compatibility.get('preconditions', [])
                    candidate.postconditions = compatibility.get('postconditions', [])
                    candidate.runtime_family = 'hermes-work-v1'
                    memory.update_procedure(candidate)
                journal.record(ExecutionEventKind.ACTION, "experience candidate created; validation required",
                               metadata={"procedure_id": candidate.id})
        return success

    def finalize_turn_candidate(
        self,
        task_id: str,
        session_id: str,
        turn_result: dict,
        *,
        expected_run_id: int | None = None,
        observed_tools: list[dict] | None = None,
        trace_truncated: bool = False,
        native_browser_contract: Any | None = None,
    ) -> dict:
        """Verify persisted execution before submitting the turn's outcome candidate."""
        from workstation.artifacts import ArtifactStore
        from workstation.contracts import EvidenceRef
        artifacts = ArtifactStore()
        evidence, verifiers, pending, handoffs = [], [], [], []
        conn = self.get_connection()
        try:
            task = kanban_db.get_task(conn, task_id)
            if task is None or task.session_id != session_id:
                raise ValueError("Outcome candidate must belong to the canonical task/session")
            if task.status in {"blocked", "cancelled", "archived", "scheduled"}:
                # Historical/parked work must be explicitly reconciled or
                # unblocked; a later turn cannot silently close an old card.
                return {"task_id": task_id, "status": "not_running", "acceptance_approved": False}
            saved = conn.execute(
                "SELECT contract_json FROM task_acceptance_contracts WHERE task_id=?", (task_id,)
            ).fetchone()
            contract = AcceptanceContract(**json.loads(saved[0])) if saved else AcceptanceContract()
            advisory_issues = _advisory_observation_issues(
                observed_tools, trace_truncated=trace_truncated,
            )
            if (contract.policy == "advisory" and task.status == "running"
                    and (expected_run_id is None or task.current_run_id != expected_run_id)):
                return {"task_id": task_id, "status": "run_unbound", "acceptance_approved": False}
            if task.status in {"triage", "todo", "ready"} and task.current_run_id is None:
                # A read-only, completed turn may itself be the first real work
                # boundary. Claim this exact user/session objective only after
                # the complete tool lane and final answer have been checked.
                can_claim_advisory = (
                    contract.policy == "advisory" and not advisory_issues
                    and expected_run_id is None
                    and turn_result.get("completed") is True
                    and not turn_result.get("failed") and not turn_result.get("interrupted")
                    and bool(str(turn_result.get("final_response") or "").strip())
                )
                if not can_claim_advisory:
                    return {"task_id": task_id, "status": "queued_unstarted", "acceptance_approved": False}
                try:
                    expected_run_id = int(self.start_triaged_task(
                        task_id, session_id=session_id, objective=task.body,
                    ))
                except (PermissionError, RuntimeError, ValueError):
                    return {"task_id": task_id, "status": "queued_unstarted", "acceptance_approved": False}
                task = kanban_db.get_task(conn, task_id)
            if task.status == "done":
                run = kanban_db.latest_run(conn, task_id)
                metadata = run.metadata if run and isinstance(run.metadata, dict) else {}
                workstation = metadata.get("workstation") or {}
                accepted = workstation.get("acceptance_approved") is True and workstation.get("outcome", {}).get("status") == "verified_completed"
                return {"task_id": task_id, "status": "verified_completed" if accepted else "uncertain", "acceptance_approved": accepted}
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            plans = []
            if "work_plans" in tables:
                for row in conn.execute("SELECT id, status, metadata FROM work_plans WHERE session_id=?", (session_id,)):
                    metadata = json.loads(row[2] or "{}")
                    if metadata.get("canonical_task_id") == task_id:
                        plans.append((row[0], row[1], metadata))
            if not plans:
                if contract.policy == "advisory":
                    if advisory_issues:
                        pending.extend(advisory_issues)
                    elif (turn_result.get("completed") is not True
                          or turn_result.get("failed") or turn_result.get("interrupted")
                          or not str(turn_result.get("final_response") or "").strip()):
                        pending.append("Advisory result was not completed")
                    else:
                        try:
                            ref, verifier = _persist_advisory_result(
                                artifacts, task_id, session_id,
                                str(expected_run_id if expected_run_id is not None else task.current_run_id),
                                str(turn_result["final_response"]),
                            )
                            evidence.append(ref)
                            verifiers.append(verifier)
                        except (OSError, ValueError, KeyError, TypeError) as exc:
                            pending.append(f"Advisory result persistence is not verified: {exc}")
                else:
                    from workstation.external_readback import SUPPORTED as EXTERNAL_READBACK_TOOLS
                    browser_effect = (isinstance(observed_tools, list)
                        and any(isinstance(row, dict) and
                                row.get("tool") in {"browser_click", "browser_type"}
                                for row in observed_tools))
                    directly_verifiable = (isinstance(observed_tools, list)
                        and any(isinstance(row, dict) and
                                row.get("tool") in ({"write_file"} | EXTERNAL_READBACK_TOOLS)
                                for row in observed_tools))
                    if browser_effect:
                        from workstation.browser_operation_readback import verify_native_browser_receipts
                        browser_evidence, browser_verifiers, browser_issues = verify_native_browser_receipts(
                            observed_tools, task_id=task_id, session_id=session_id,
                            run_id=str(expected_run_id if expected_run_id is not None else task.current_run_id),
                            trace_truncated=trace_truncated, contract=native_browser_contract,
                        )
                        evidence.extend(browser_evidence)
                        verifiers.extend(browser_verifiers)
                        pending.extend(browser_issues)
                    elif directly_verifiable:
                        from workstation.direct_file_readback import verify_file_write_receipts
                        file_evidence, file_verifiers, file_issues = verify_file_write_receipts(
                            observed_tools, task_id=task_id, session_id=session_id,
                            run_id=str(expected_run_id if expected_run_id is not None else task.current_run_id),
                            trace_truncated=trace_truncated,
                        )
                        evidence.extend(file_evidence)
                        verifiers.extend(file_verifiers)
                        pending.extend(file_issues)
                    else:
                        trace = turn_result.get('_adaptive_trace') or []
                        if trace:
                            try:
                                ref, verifier = _verified_native_navigation(
                                    artifacts, trace, task_id, session_id,
                                    str(expected_run_id if expected_run_id is not None else task.current_run_id),
                                )
                                evidence.append(ref)
                                verifiers.append(verifier)
                            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                                pending.append(f"Adaptive browser evidence is not verified: {exc}")
                        else:
                            pending.append("No persisted execution verifies the acceptance contract")
            for plan_id, plan_status, metadata in plans:
                if metadata.get("handoff", {}).get("status") == "waiting-for-human":
                    handoffs.append(metadata["handoff"]["handoff_id"])
                if plan_status != "completed":
                    pending.append(f"Plan {plan_id} remains {plan_status}")
                rows = conn.execute("SELECT id, status, normalized_output_ref, validation_result, checkpoints FROM work_items WHERE plan_id=?", (plan_id,)).fetchall()
                if not rows:
                    pending.append(f"Plan {plan_id} has no verified items")
                for row in rows:
                    validation = json.loads(row[3] or "{}")
                    checkpoints = json.loads(row[4] or "{}")
                    if row[1] != "completed" or validation.get("valid") is not True or checkpoints.get("validate") != "ok":
                        pending.append(f"Item {row[0]} is not verified")
                        continue
                    try:
                        resolved = artifacts.resolve_structured(row[2])
                        output = resolved.get("content")
                        if not isinstance(output, dict) or output.get("valid") is not True:
                            raise ValueError("Persisted output is not a verified compiler result")
                        for result in output.get("results", []):
                            if result.get("verified") is not True:
                                raise ValueError("Step result is not verified")
                            artifacts.resolve_structured(result["artifact_ref"], max_content_bytes=0)
                        evidence.append(EvidenceRef("durable_proof", row[2], sha256=resolved["sha256"]))
                        verifiers.append({"verifier": "durable_item:" + row[0], "passed": True, "evidence_ref": row[2]})
                    except (OSError, ValueError, KeyError, TypeError) as exc:
                        pending.append(f"Item {row[0]} evidence cannot be verified: {exc}")
        finally:
            conn.close()
        stopped = not turn_result.get("completed") or turn_result.get("failed") or turn_result.get("interrupted")
        if stopped:
            pending.append("Execution stopped before a verified final outcome")
        verified = not pending and not handoffs and bool(verifiers)
        status = (OutcomeStatus.VERIFIED_COMPLETED if verified else OutcomeStatus.WAITING_FOR_HUMAN if handoffs
                  else OutcomeStatus.FAILED if turn_result.get("failed") else OutcomeStatus.UNCERTAIN if stopped
                  else OutcomeStatus.BLOCKED)

        target_run_id = expected_run_id
        if target_run_id is None and task is not None and task.current_run_id is not None:
            target_run_id = task.current_run_id

        # Recoverable external uncertainty becomes an actionable, read-only
        # dependent task. It is never a signal to redispatch the original write.
        if (not verified and not stopped and not plans and not trace_truncated
                and contract.policy == "evidence" and target_run_id is not None):
            try:
                from workstation.evidence_recovery import schedule_recovery
                child_id = schedule_recovery(
                    task_id=task_id, session_id=session_id,
                    run_id=int(target_run_id), observed_tools=observed_tools,
                    pending=pending, board=self.board,
                )
                if child_id:
                    return {"task_id": task_id, "status": "recovery_queued",
                            "acceptance_approved": False,
                            "recovery_task_id": child_id, "pending_items": pending}
            except Exception:
                _log.warning("Could not schedule read-only evidence recovery", exc_info=True)

        # A write/unknown-effect tool without a verified plan cannot be
        # replayed or certified as an advisory completion.
        uncertain_effect = bool(
            not plans and not verified and isinstance(observed_tools, list)
            and any(not isinstance(row, dict)
                    or row.get("effect") not in {"PURE_READ", "DISCOVERY"}
                    for row in observed_tools)
        )
        report = BrowserTaskReport(task_id, session_id, task.body or task.title,
            str(turn_result.get("final_response") or "Execution has no verified final result"), verified,
            pending_items=pending, evidence=evidence, verifier_results=verifiers,
            deliverables=[e.uri for e in evidence], outcome_status=status,
            run_id=str(target_run_id) if target_run_id is not None else None,
            uncertain_mutation=uncertain_effect)
        if len(verifiers) == 1 and verifiers[0].get('verifier') in {
                'native_browser_session_state', 'native_browser_external_readback'}:
            report.operation_id = verifiers[0]['operation_id']
        report.repeatability_hint = turn_result.get('_adaptive_repeatability_hint', False)
        report.procedure_steps = turn_result.get('_adaptive_procedure_steps', [])
        report.procedure_scope = session_id
        report.procedure_compatibility = turn_result.get('_adaptive_procedure_compatibility', {})
        if report.procedure_compatibility:
            report.procedure_scope = report.procedure_compatibility['scope']['host']
            for _, _, plan_metadata in plans:
                objective = artifacts.read_json(plan_metadata['objective_ref'])
                for step in objective.get('steps', []):
                    if step.get('tool') == 'browser_snapshot' and step.get('expect') and set(step['expect']) - {'ok', 'success', 'status_code', 'http_status', 'url'}:
                        report.procedure_compatibility['postconditions'] = [json.dumps(step['expect'], sort_keys=True)]
        accepted = self.complete_task_with_report(task_id, report, expected_run_id=target_run_id)
        return {"task_id": task_id, "status": status.value if accepted else "uncertain", "acceptance_approved": accepted,
                "pending_items": pending, "planned_handoffs": handoffs}
