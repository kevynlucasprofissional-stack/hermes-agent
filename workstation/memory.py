from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from hermes_constants import get_hermes_home


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProceduralMemoryResult(str, Enum):
    FOUND = "found"
    MISS = "miss"
    BROKEN = "broken"


@dataclass(slots=True)
class ProcedureStep:
    action: str
    target: str = ""
    value: str = ""
    expectation: str = ""
    required: bool = True
    anchor_type: str = "selector"
    fallback_anchors: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "target": self.target,
            "value": self.value,
            "expectation": self.expectation,
            "required": self.required,
            "anchor_type": self.anchor_type,
            "fallback_anchors": self.fallback_anchors,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProcedureStep:
        return cls(
            action=str(data.get("action", "")),
            target=str(data.get("target", "")),
            value=str(data.get("value", "")),
            expectation=str(data.get("expectation", "")),
            required=bool(data.get("required", True)),
            anchor_type=str(data.get("anchor_type", "selector")),
            fallback_anchors=list(data.get("fallback_anchors", [])),
        )

    def resolve_anchor(self, available_elements: list[dict[str, Any]]) -> str | None:
        """Resolve the best target identifier across multi-facet fallback anchors.

        Prioritizes semantic stability: testid -> role_name -> text content -> CSS selector.
        """
        if not available_elements:
            return self.target or None

        # 1. Search by testid if present
        for anchor in self.fallback_anchors:
            if anchor.get("type") == "testid":
                val = anchor.get("value", "").lower()
                for el in available_elements:
                    attrs = el.get("attributes", {})
                    tid = str(attrs.get("data-testid", attrs.get("data-test", el.get("testid", "")))).lower()
                    if val and val == tid:
                        return str(el.get("ref", el.get("selector", self.target)))

        # 2. Search by role_name
        for anchor in self.fallback_anchors:
            if anchor.get("type") == "role_name":
                val = anchor.get("value", "").lower()
                role_filter, _, name_filter = val.partition(":")
                for el in available_elements:
                    el_role = str(el.get("role", el.get("tag", ""))).lower()
                    el_name = str(el.get("name", el.get("text", ""))).lower()
                    if role_filter in el_role and name_filter in el_name:
                        return str(el.get("ref", el.get("selector", self.target)))

        # 3. Search by semantic text
        for anchor in self.fallback_anchors:
            if anchor.get("type") == "text":
                val = anchor.get("value", "").lower()
                for el in available_elements:
                    el_name = str(el.get("name", el.get("text", ""))).lower()
                    if val and val in el_name:
                        return str(el.get("ref", el.get("selector", self.target)))

        # 4. Fallback to original target selector
        for el in available_elements:
            el_sel = str(el.get("selector", el.get("path", "")))
            if self.target and self.target == el_sel:
                return str(el.get("ref", self.target))

        return self.target or None


@dataclass(slots=True)
class WebProcedure:
    id: str
    name: str
    site: str
    intent: str
    side_effect: str = "read_write"
    steps: list[ProcedureStep] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    success_count: int = 1
    failure_count: int = 0
    confidence: float = 1.0
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "site": self.site,
            "intent": self.intent,
            "side_effect": self.side_effect,
            "steps": [s.to_dict() for s in self.steps],
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WebProcedure:
        steps = [ProcedureStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            id=str(data.get("id", uuid4())),
            name=str(data.get("name", "Unnamed Procedure")),
            site=str(data.get("site", "")),
            intent=str(data.get("intent", "")),
            side_effect=str(data.get("side_effect", "read_write")),
            steps=steps,
            preconditions=list(data.get("preconditions", [])),
            postconditions=list(data.get("postconditions", [])),
            success_count=int(data.get("success_count", 1)),
            failure_count=int(data.get("failure_count", 0)),
            confidence=float(data.get("confidence", 1.0)),
            created_at=str(data.get("created_at", _utc_now())),
            updated_at=str(data.get("updated_at", _utc_now())),
            version=int(data.get("version", 1)),
        )


class ProceduralMemory:
    """V2 procedural web memory: discover -> run -> explore -> learn.

    Manages persistent reusable multi-step browser procedures indexed by
    domain and intent, with confidence estimation and decay/reinforcement.
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        if storage_path is None:
            storage_path = get_hermes_home() / "workstation" / "memory" / "procedures.json"
        self.storage_path = Path(storage_path)
        self._procedures: dict[str, WebProcedure] = {}
        self._load()

    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                for item in raw:
                    if isinstance(item, dict) and "id" in item:
                        proc = WebProcedure.from_dict(item)
                        self._procedures[proc.id] = proc
        except Exception:
            # Corrupted storage resets to empty; atomic write prevents half-written state.
            self._procedures = {}

    def _persist(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        # Merge on write: read external updates from disk without dropping our in-memory changes
        if self.storage_path.exists():
            try:
                disk_raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
                if isinstance(disk_raw, list):
                    for item in disk_raw:
                        if isinstance(item, dict) and "id" in item:
                            disk_id = str(item["id"])
                            if disk_id not in self._procedures:
                                self._procedures[disk_id] = WebProcedure.from_dict(item)
            except Exception:
                pass

        temp_file = self.storage_path.with_suffix(".tmp")
        payload = [proc.to_dict() for proc in self._procedures.values()]
        temp_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        temp_file.replace(self.storage_path)

    def discover(self, site: str, goal: str) -> list[WebProcedure]:
        """Find procedures that match the given site and goal keywords."""
        site_norm = site.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
        goal_tokens = set(goal.strip().lower().split())

        candidates: list[tuple[float, WebProcedure]] = []
        for proc in self._procedures.values():
            proc_site = proc.site.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
            if site_norm and proc_site and site_norm not in proc_site and proc_site not in site_norm:
                continue

            # Compute intent relevance score
            proc_tokens = set(proc.intent.strip().lower().split()) | set(proc.name.strip().lower().split())
            overlap = len(goal_tokens & proc_tokens)
            relevance = (overlap / max(1, len(goal_tokens))) * proc.confidence

            if relevance > 0.1 or not goal_tokens:
                candidates.append((relevance, proc))

        candidates.sort(key=lambda item: item[0], reverse=True)
        return [proc for _, proc in candidates]

    def record_success(
        self,
        site: str,
        goal: str,
        steps: list[dict[str, Any] | ProcedureStep] | None = None,
        name: str | None = None,
        journal_id: str | None = None,
    ) -> WebProcedure:
        """Learn or reinforce a successful procedure."""
        parsed_steps: list[ProcedureStep] = []
        if steps:
            for s in steps:
                if isinstance(s, ProcedureStep):
                    parsed_steps.append(s)
                elif isinstance(s, dict):
                    parsed_steps.append(ProcedureStep.from_dict(s))

        # Check if an existing procedure matches site + intent closely
        existing = self.discover(site, goal)
        if existing and existing[0].confidence >= 0.5:
            proc = existing[0]
            proc.success_count += 1
            proc.confidence = min(1.0, proc.confidence + 0.05)
            proc.updated_at = _utc_now()
            if parsed_steps:
                proc.steps = parsed_steps
            self._persist()
            return proc

        # Otherwise create a new procedure
        proc_id = str(uuid4())
        proc_name = name or f"Workflow for {goal[:40]}"
        proc = WebProcedure(
            id=proc_id,
            name=proc_name,
            site=site,
            intent=goal,
            steps=parsed_steps,
            success_count=1,
            failure_count=0,
            confidence=0.8,
        )
        self._procedures[proc.id] = proc
        self._persist()
        return proc

    def record_failure(self, procedure_id: str, step_index: int = 0, reason: str = "") -> bool:
        """Record a failure during procedure replay, reducing its confidence."""
        proc = self._procedures.get(procedure_id)
        if not proc:
            return False
        proc.failure_count += 1
        proc.confidence = max(0.1, proc.confidence - 0.2)
        proc.updated_at = _utc_now()
        self._persist()
        return True

    def get_procedure(self, procedure_id: str) -> WebProcedure | None:
        return self._procedures.get(procedure_id)

    def delete_procedure(self, procedure_id: str) -> bool:
        if procedure_id in self._procedures:
            del self._procedures[procedure_id]
            self._persist()
            return True
        return False

    def list_procedures(self, site: str | None = None) -> list[WebProcedure]:
        if not site:
            return list(self._procedures.values())
        site_norm = site.strip().lower()
        return [p for p in self._procedures.values() if site_norm in p.site.lower()]
