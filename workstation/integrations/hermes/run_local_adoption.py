"""Hermes binding of run-local adoption: the runtime owner and its safe checkpoint.

``build_run_adoption_owner`` supplies canonical facts and certified dispatch for ONE agent's
TaskRun; ``workstation_run_local_checkpoint`` is called from the pre-reasoning boundary
(``workstation_operational_resolution``), where no tool is in flight and the agent thread
owns the run. It never starts the learning plane, never answers the turn, and when anything
is not provable it simply returns so ordinary reasoning continues.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from typing import Any, Optional

from workstation.artifacts import ArtifactStore
from workstation.durable_tasks import DurableTaskStore
from workstation.integrations.hermes.effect_authority import trusted_effect_authority_from_agent
from workstation.run_adoption import AdoptionReport, DurableRunAdoptionOwner, RunLocalAdopter

logger = logging.getLogger(__name__)

# Primitives the Hermes durable dispatcher can run and read back independently today.
_SUPPORTED = ("write_file", "read_file")
_READBACK = ("write_file",)
_GUTTER = re.compile(r"^\s*\d+\|", re.M)


def _readback_write_file(dispatch, artifacts: ArtifactStore, task_id: str):
    """Independent read-after-write through the agent's own ``read_file``; exact content match."""
    def readback(primitive: str, bound_args: dict, raw: Any) -> Optional[dict]:
        if primitive != "write_file" or "content" not in bound_args or "path" not in bound_args:
            return None
        try:
            observed = json.loads(dispatch("read_file", {"path": bound_args["path"]}))
            text = _GUTTER.sub("", str(observed.get("content", "")))
        except Exception:
            return {"ok": False, "evidence_ref": None}
        expected = str(bound_args["content"])
        ok = text.rstrip("\n") == expected.rstrip("\n")
        ref = artifacts.store(task_id, f"readback_{uuid.uuid4().hex[:10]}.json", {
            "primitive": primitive, "path": bound_args["path"], "matched": ok,
            "observed_sha": hashlib.sha256(text.encode()).hexdigest(),
            "expected_sha": hashlib.sha256(expected.encode()).hexdigest(),
        }, schema="workstation.run_local_readback.v1").ref
        return {"ok": ok, "evidence_ref": ref}
    return readback


def build_run_adoption_owner(agent: Any, *, system2_counter=None) -> Optional[DurableRunAdoptionOwner]:
    """Owner for this agent's canonical TaskRun, or ``None`` when the agent has no bound run."""
    task_id = getattr(agent, "_canonical_work_task_id", None)
    run_id = getattr(agent, "_canonical_work_run_id", None)
    if not task_id or run_id is None:
        return None
    cached = getattr(agent, "_run_adoption_owner", None)
    if cached is not None:
        return cached

    from workstation.integrations.hermes.scoped_execution import (
        workstation_durable_dispatch,
        workstation_scoped_execution,
    )

    session_id = str(getattr(agent, "_conversation_root_id", lambda: None)() or getattr(agent, "session_id", "") or "")
    inner = workstation_durable_dispatch(agent)
    artifacts = ArtifactStore()

    def dispatch(tool: str, args: dict) -> Any:
        with workstation_scoped_execution(agent, str(task_id), None):
            return inner(tool, args, str(task_id), f"runlocal_{uuid.uuid4().hex[:10]}")

    owner = DurableRunAdoptionOwner(
        DurableTaskStore, artifacts,
        authority_for_task=lambda task: trusted_effect_authority_from_agent(agent, session_id, task),
        dispatch_fn=dispatch,
        readback_fn=_readback_write_file(dispatch, artifacts, str(task_id)),
        readback_primitives=_READBACK, supported_primitives=_SUPPORTED, system2_counter=system2_counter,
    )
    from workstation.experience_compiler.lifecycle import (
        get_validation_environment_provider,
        register_validation_environment_provider,
        create_local_canary_validation_provider,
    )
    if get_validation_environment_provider() is None:
        register_validation_environment_provider(create_local_canary_validation_provider(artifacts))
    try:
        agent._run_adoption_owner = owner
    except AttributeError:
        pass
    return owner


def workstation_run_local_checkpoint(context: Any) -> Optional[AdoptionReport]:
    """Adopt the next verified-equivalent pending items of this run, or do nothing."""
    from workstation.experience_compiler.compilability_monitor import DIRECT, peek_compilability_monitor

    agent = getattr(context, "agent", None)
    monitor = peek_compilability_monitor()
    if agent is None or monitor is None or not monitor.enabled or monitor.mode != DIRECT:
        return None
    task_id = getattr(agent, "_canonical_work_task_id", None)
    run_id = getattr(agent, "_canonical_work_run_id", None)
    if not task_id or run_id is None or not monitor.ready_offers(str(task_id), str(run_id)):
        return None
    owner = build_run_adoption_owner(agent)
    if owner is None:
        return None
    owner.bind_system2_counter(lambda: int(getattr(context, "api_call_count", 0) or 0))
    try:
        report = RunLocalAdopter(owner, monitor).run_checkpoint(str(task_id), str(run_id))
    except Exception:
        logger.warning("run-local adoption checkpoint failed closed", exc_info=True)
        return None
    finally:
        owner.bind_system2_counter(None)
    if report.items:
        agent._run_local_adoption_reports = [*getattr(agent, "_run_local_adoption_reports", []), report]
    return report
