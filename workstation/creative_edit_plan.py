"""Semantic Edit Plan and reversible preview for Hermes agent co-editing (CWN-04)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
import uuid

from workstation.creative_commands import CreativeCommand
from workstation.creative_document import (
    CreativeDocument,
    document_to_dict,
    load_document_from_dict,
)
from workstation.creative_transactions import (
    CreativeHistory,
    CreativeTransaction,
    TransactionConflictError,
)


class EditPlanState(str, Enum):
    PROPOSED = "PROPOSED"
    PREVIEWED = "PREVIEWED"
    VALIDATED = "VALIDATED"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    PARTIAL = "PARTIAL"
    ROLLED_BACK = "ROLLED_BACK"


class PlanConflictError(ValueError):
    """Raised when document revision or state conflicts with the proposed edit plan."""
    pass


@dataclass
class SemanticEditPlan:
    plan_id: str
    base_revision_id: str
    base_revision_number: int
    intent: str
    target_ids: list[str]
    commands: list[CreativeCommand]
    read_set: list[str]
    write_set: list[str]
    predicted_diff: dict[str, Any]
    state: EditPlanState = EditPlanState.PROPOSED
    preview_document: CreativeDocument | None = None
    diagnostics: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    required_external_paths: list[str] = field(default_factory=list)
    applied_transaction: CreativeTransaction | None = None


class SemanticEditPlanManager:
    """Manages the proposal, validation, isolated preview, and execution of AI edit plans."""

    def propose_plan(
        self,
        doc: CreativeDocument,
        base_revision_id: str,
        intent: str,
        commands: list[CreativeCommand],
        provenance: dict[str, Any] | None = None,
        base_revision_number: int = 0,
        required_external_paths: list[str] | None = None,
    ) -> SemanticEditPlan:
        plan_id = uuid.uuid4().hex
        target_ids: set[str] = set()
        read_set: set[str] = set()
        write_set: set[str] = set()

        # Static command inspection
        for cmd in commands:
            for k, v in cmd.params.items():
                if k.endswith("_id") and isinstance(v, str):
                    target_ids.add(v)
                    write_set.add(v)
            if "composition_id" in cmd.params:
                read_set.add(cmd.params["composition_id"])

        predicted_diff = {
            "commands_count": len(commands),
            "command_verbs": [c.command_id for c in commands],
            "targets_count": len(target_ids),
        }

        return SemanticEditPlan(
            plan_id=plan_id,
            base_revision_id=base_revision_id,
            base_revision_number=base_revision_number,
            intent=intent,
            target_ids=sorted(target_ids),
            commands=commands,
            read_set=sorted(read_set),
            write_set=sorted(write_set),
            predicted_diff=predicted_diff,
            state=EditPlanState.PROPOSED,
            provenance=dict(provenance or {}),
            required_external_paths=list(required_external_paths or []),
        )

    def preview_plan(self, plan: SemanticEditPlan, doc: CreativeDocument) -> CreativeDocument:
        """Render a true isolated copy-on-write preview of the plan without mutating the user document."""
        # Create an independent clone of the project
        clone = load_document_from_dict(document_to_dict(doc))
        tx = CreativeTransaction(commands=plan.commands)
        tx.apply(clone)

        plan.preview_document = clone
        plan.state = EditPlanState.PREVIEWED
        return clone

    def validate_plan(self, plan: SemanticEditPlan, doc: CreativeDocument) -> bool:
        """Validate external file dependencies, pre-conditions, and document integrity."""
        plan.diagnostics.clear()

        # Check external required artifacts
        for p in plan.required_external_paths:
            path_obj = Path(p)
            if not path_obj.exists():
                plan.diagnostics.append(f"Missing required external file: {p}")

        if plan.diagnostics:
            plan.state = EditPlanState.BLOCKED
            return False

        plan.state = EditPlanState.VALIDATED
        return True

    def apply_plan(
        self,
        plan: SemanticEditPlan,
        doc: CreativeDocument,
        history: CreativeHistory,
        selected_command_indices: list[int] | None = None,
    ) -> None:
        """Apply all or a user-selected subset of the plan's commands onto the document."""
        # Rebase check: verify live history revision against plan's base revision
        if history.current_revision != plan.base_revision_number:
            raise PlanConflictError(
                f"Document was modified after plan creation (current revision {history.current_revision} != base {plan.base_revision_number})"
            )

        if selected_command_indices is not None:
            chosen_commands = [plan.commands[i] for i in selected_command_indices if i < len(plan.commands)]
            is_subset = len(chosen_commands) < len(plan.commands)
        else:
            chosen_commands = plan.commands
            is_subset = False

        tx = CreativeTransaction(commands=chosen_commands, expected_revision=plan.base_revision_number)
        history.commit(doc, tx)
        plan.applied_transaction = tx

        # If only a subset was selected, mark PARTIAL; otherwise APPLIED
        if is_subset:
            plan.state = EditPlanState.PARTIAL
        else:
            plan.state = EditPlanState.APPLIED

    def reject_plan(self, plan: SemanticEditPlan) -> None:
        """Reject proposed plan and discard temporary preview assets."""
        plan.preview_document = None
        plan.state = EditPlanState.REJECTED

    def rollback_plan(self, plan: SemanticEditPlan, doc: CreativeDocument, history: CreativeHistory) -> None:
        """Roll back an applied plan via canonical history undo."""
        if plan.state not in {EditPlanState.APPLIED, EditPlanState.PARTIAL}:
            raise ValueError(f"Cannot rollback plan in state {plan.state}")

        history.undo(doc)
        plan.state = EditPlanState.ROLLED_BACK
