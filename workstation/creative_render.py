"""Native Creative render adapter with owner receipt and independent media readback."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import uuid4

from tools.browser_workstation import _workstation_home
from workstation.artifacts import ArtifactStore
from workstation.config import WorkstationConfig
from workstation.contracts import ExecutionEventKind
from workstation.creative_media import inspect_creative_png
from workstation.creative_project_runtime import CreativeEffectUncertain, CreativeRunContext
from workstation.creative_project_store import load_creative_revision
from workstation.integrations.hermes.browser_controller import dispatch_workstation_browser_authoritative
from workstation.journal import ExecutionJournal


def _owner_receipt(context: CreativeRunContext, browser_task_id: str, operation_id: str) -> dict:
    path = _workstation_home() / "Runtime" / "browser-session.json"
    if path.stat().st_size > 1_000_000:
        raise ValueError("Creative BrowserTask readback exceeds budget")
    state = json.loads(path.read_bytes())
    if not isinstance(state, dict) or state.get("version") != 1:
        raise ValueError("Invalid Creative BrowserTask projection")
    projection = state.get("browserTasks")
    if not isinstance(projection, dict) or projection.get("version") != 1:
        raise ValueError("Invalid Creative BrowserTask projection")
    matches = [task for task in projection.get("tasks", [])
               if isinstance(task, dict) and task.get("taskId") == browser_task_id]
    if len(matches) != 1:
        raise ValueError("Creative BrowserTask is missing or ambiguous")
    task = matches[0]
    if (task.get("sessionHost") != context.session_id or str(task.get("runId")) != str(context.run_id)
            or task.get("kanbanCardId") != context.task_id):
        raise PermissionError("Creative BrowserTask lineage drift")
    receipt = task.get("lastReceipt")
    if (not isinstance(receipt, dict) or receipt.get("action") != "browser_creative_render"
            or receipt.get("operationId") != operation_id or receipt.get("taskId") != browser_task_id
            or receipt.get("browserTaskId") != browser_task_id
            or str(receipt.get("runId")) != str(context.run_id)
            or type(receipt.get("revision")) is not int or type(task.get("revision")) is not int
            or receipt["revision"] != task.get("revision") or not receipt.get("tabId")):
        raise ValueError("Creative render owner receipt mismatch")
    owned_tabs = [tab for tab in state.get("tabs", [])
                  if isinstance(tab, dict) and tab.get("browserTaskId") == browser_task_id]
    if (len(owned_tabs) != 1 or owned_tabs[0].get("id") != receipt.get("tabId")
            or owned_tabs[0].get("recoveryState") != "live"
            or task.get("status") not in {"visible", "hidden", "parked"}):
        raise ValueError("Creative native tab readback mismatch")
    return receipt


def render_project_for_run(config: WorkstationConfig, context: CreativeRunContext, *,
                           project_id: str, revision_id: str, browser_task_id: str) -> dict:
    workspace = context.validate(config)
    revision = load_creative_revision(project_id, revision_id)
    if revision.engine != "electron-svg":
        raise ValueError("Native SVG renderer cannot render this project engine")
    if not revision.source_path.is_relative_to(workspace):
        raise PermissionError("Creative source is outside the TaskRun workspace")
    if not browser_task_id or len(browser_task_id) > 256:
        raise ValueError("Creative BrowserTask identity required")
    source_bytes = revision.source_path.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != revision.source_sha256:
        raise ValueError("Creative source changed before render")
    document = json.loads(source_bytes)
    operation_id = uuid4().hex
    journal = ExecutionJournal(task_id=context.task_id, session_id=context.session_id)
    journal.record(ExecutionEventKind.ACTION, "Creative native render prepared", metadata={
        "operation_id": operation_id, "run_id": context.run_id,
        "project_id": project_id, "revision_id": revision_id, "browser_task_id": browser_task_id,
    })
    context.validate(config)
    try:
        raw = dispatch_workstation_browser_authoritative(
            "browser_creative_render", {"source_json": source_bytes.decode("utf-8"),
                                        "source_sha256": revision.source_sha256, "operation_id": operation_id},
            task_id=browser_task_id, session_id=context.session_id, run_id=str(context.run_id),
            kanban_card_id=context.task_id,
        )
        return _publish_render(config, context, project_id, revision_id, browser_task_id,
                               operation_id, raw, document, revision.source_sha256, journal)
    except Exception as error:
        # Dispatch can load a document before capture/receipt fails. The prepared
        # operation remains in the journal even if publication loses authority.
        raise CreativeEffectUncertain(operation_id) from error


def _publish_render(config, context, project_id, revision_id, browser_task_id,
                    operation_id, raw, document, source_sha256, journal):
    result = json.loads(raw) if isinstance(raw, str) else raw
    context.validate(config)
    receipt = _owner_receipt(context, browser_task_id, operation_id)
    if (result.get("success") is not True or result.get("runtime") != "electron-chromium"
            or result.get("source_sha256") != source_sha256 or result.get("receipt") != receipt
            or result.get("tab_id") != receipt.get("tabId")):
        raise ValueError("Creative native render receipt/readback mismatch")
    target = Path(result["screenshot_path"])
    # Reuse the Browser owner's platform-aware capture root, not a second path table.
    capture_root = (_workstation_home() / "Browser" / "Screenshots").resolve()
    if target.is_symlink() or not target.is_absolute() or target.resolve().parent != capture_root:
        raise PermissionError("Creative PNG escaped the native capture root")
    facts = inspect_creative_png(target, width=document["width"], height=document["height"], sha256=result["sha256"])
    png = target.read_bytes()
    svg = result["svg_source"].encode("utf-8")
    if (hashlib.sha256(png).hexdigest() != facts["sha256"]
            or hashlib.sha256(svg).hexdigest() != result.get("svg_sha256")):
        raise ValueError("Creative output changed before publication")
    load_creative_revision(project_id, revision_id)
    context.validate(config)
    store = ArtifactStore()
    png_ref = store.store(context.task_id, f"creative-render-{operation_id}.png", png, media_type="image/png")
    svg_ref = store.store(context.task_id, f"creative-render-{operation_id}.svg", svg, media_type="image/svg+xml")
    context.validate(config)
    payload = {"project_id": project_id, "revision_id": revision_id, "task_id": context.task_id,
               "run_id": context.run_id, "session_id": context.session_id, "operation_id": operation_id,
               "browser_task_id": browser_task_id, "owner_receipt": receipt, "media_readback": facts,
               "source_sha256": source_sha256, "png_artifact": png_ref.to_dict(),
               "svg_artifact": svg_ref.to_dict()}
    journal.record(ExecutionEventKind.DELIVERABLE, "Creative native output read back and persisted", metadata=payload)
    return payload
