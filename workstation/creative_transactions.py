"""Atomic transactions, history manager, and conflict detection for Creative Document (CWN-02)."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any
import uuid

from workstation.creative_commands import (
    CreativeCommand,
    CommandResult,
    execute_command,
)
from workstation.creative_document import (
    CreativeDocument,
    document_to_dict,
    load_document_from_dict,
)


class TransactionConflictError(ValueError):
    """Raised when expectedRevision does not match current project revision (409 Conflict)."""
    pass


class TransactionExecutionError(RuntimeError):
    """Raised when a command within an atomic batch fails, aborting the transaction."""
    pass


@dataclass
class CreativeTransaction:
    commands: list[CreativeCommand]
    expected_revision: int | None = None
    transaction_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def apply(self, doc: CreativeDocument) -> list[CreativeCommand]:
        """Apply all commands in this transaction atomically using copy-on-write semantics.

        If any command fails at step k, the original doc is left completely untouched.
        Returns the list of inverse commands in reverse order (for exact rollback/undo).
        """
        # Step 1: Copy-on-write clone of the document
        snapshot = load_document_from_dict(document_to_dict(doc))
        inverse_commands: list[CreativeCommand] = []

        for idx, cmd in enumerate(self.commands):
            try:
                res = execute_command(snapshot, cmd)
                if not res.success:
                    raise TransactionExecutionError(
                        f"Command {cmd.command_id} at step {idx + 1} failed: {res.error_message}"
                    )
                if res.inverse_command:
                    inverse_commands.append(res.inverse_command)
            except Exception as exc:
                raise TransactionExecutionError(
                    f"Command {cmd.command_id} at step {idx + 1} raised {type(exc).__name__}: {exc}"
                ) from exc

        # Step 2: All commands succeeded -> commit mutations into doc
        # Re-populate doc state from snapshot
        updated = load_document_from_dict(document_to_dict(snapshot))
        doc.compositions = updated.compositions
        doc.assets = updated.assets
        doc.metadata = updated.metadata
        doc.name = updated.name

        # Inverses are ordered in reverse so undo unwinds from step N down to step 1
        inverse_commands.reverse()
        return inverse_commands


class CreativeHistory:
    """Manages undo/redo history stacks, idempotency tracking, and revision numbering."""

    def __init__(self):
        self.current_revision: int = 0
        self._undo_stack: list[tuple[CreativeTransaction, list[CreativeCommand]]] = []
        self._redo_stack: list[tuple[CreativeTransaction, list[CreativeCommand]]] = []
        self._seen_idempotency_keys: set[str] = set()

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def commit(self, doc: CreativeDocument, tx: CreativeTransaction) -> None:
        """Commit an atomic transaction onto the document with revision and idempotency checks."""
        # 1. Revision check
        if tx.expected_revision is not None and tx.expected_revision != self.current_revision:
            raise TransactionConflictError(
                f"Revision mismatch: expected {tx.expected_revision}, current {self.current_revision}"
            )

        # 2. Idempotency check: if all commands in this transaction have already been applied, no-op
        keys = [cmd.idempotency_key for cmd in tx.commands if cmd.idempotency_key]
        if keys and all(k in self._seen_idempotency_keys for k in keys):
            # Already applied; do not re-execute or duplicate state
            return

        # 3. Apply transaction copy-on-write
        inverses = tx.apply(doc)

        # 4. Record idempotency keys
        for k in keys:
            self._seen_idempotency_keys.add(k)

        # 5. Push to undo stack, clear redo stack, bump revision
        self._undo_stack.append((tx, inverses))
        self._redo_stack.clear()
        self.current_revision += 1

    def undo(self, doc: CreativeDocument) -> None:
        """Undo the most recent committed transaction."""
        if not self.can_undo():
            raise ValueError("Nothing to undo")

        tx, inverses = self._undo_stack.pop()
        # Execute inverse commands atomically
        inverse_tx = CreativeTransaction(commands=inverses)
        inverse_tx.apply(doc)

        self._redo_stack.append((tx, inverses))
        self.current_revision += 1

    def redo(self, doc: CreativeDocument) -> None:
        """Redo the most recently undone transaction."""
        if not self.can_redo():
            raise ValueError("Nothing to redo")

        tx, inverses = self._redo_stack.pop()
        # Re-apply original transaction commands
        new_inverses = tx.apply(doc)

        self._undo_stack.append((tx, new_inverses))
        self.current_revision += 1
