"""Workstation board REST namespace. No upstream Kanban imports."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from workstation import kanban_local as board

router = APIRouter()


class BoardInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class CardInput(BaseModel):
    column_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=20000)


class MoveInput(BaseModel):
    column_id: str = Field(min_length=1, max_length=64)
    expected_revision: int = Field(ge=1)


class EditInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=20000)
    expected_revision: int = Field(ge=1)


def _invoke(fn, *args, **kwargs):
    try:
        with board.database() as conn:
            return fn(conn, *args, **kwargs)
    except board.BoardConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except board.BoardError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc


@router.get("/boards")
async def boards(include_archived: bool = False):
    return {"boards": await asyncio.to_thread(_invoke, board.list_boards, include_archived)}


@router.post("/boards", status_code=201)
async def new_board(data: BoardInput):
    return {"board": await asyncio.to_thread(_invoke, board.create_board, data.name)}


@router.get("/boards/{board_id}")
async def get_board(board_id: str, include_archived: bool = False):
    return {"board": await asyncio.to_thread(_invoke, board.get_board, board_id, include_archived)}


@router.post("/boards/{board_id}/columns", status_code=201)
async def new_column(board_id: str, data: BoardInput):
    return {"column": await asyncio.to_thread(_invoke, board.create_column, board_id, data.name)}


@router.post("/boards/{board_id}/cards", status_code=201)
async def new_card(board_id: str, data: CardInput):
    return {"card": await asyncio.to_thread(_invoke, board.create_card, board_id,
        data.column_id, data.title, data.description)}


@router.post("/cards/{card_id}/move")
async def move_card(card_id: str, data: MoveInput):
    return {"card": await asyncio.to_thread(_invoke, board.move_card,
        card_id, data.column_id, data.expected_revision)}


@router.patch("/cards/{card_id}")
async def edit_card(card_id: str, data: EditInput):
    return {"card": await asyncio.to_thread(_invoke, board.update_card,
        card_id, data.title, data.description, data.expected_revision)}


class ChecklistInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ChecklistItemInput(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class ChecklistItemUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    body: str | None = Field(default=None, min_length=1, max_length=2000)
    completed: bool | None = None


class ExpectedRevision(BaseModel):
    expected_revision: int = Field(ge=1)


@router.get("/cards/{card_id}")
async def card_details(card_id: str):
    return {"card": await asyncio.to_thread(_invoke, board.get_card_details, card_id)}


@router.post("/cards/{card_id}/checklists", status_code=201)
async def new_checklist(card_id: str, data: ChecklistInput):
    return {"checklist": await asyncio.to_thread(_invoke, board.create_checklist, card_id, data.title)}


@router.post("/checklists/{checklist_id}/items", status_code=201)
async def new_checklist_item(checklist_id: str, data: ChecklistItemInput):
    return {"item": await asyncio.to_thread(_invoke, board.create_checklist_item, checklist_id, data.body)}


@router.patch("/checklist-items/{item_id}")
async def edit_checklist_item(item_id: str, data: ChecklistItemUpdate):
    return {"item": await asyncio.to_thread(_invoke, board.update_checklist_item, item_id,
        data.expected_revision, data.body, data.completed)}


@router.post("/checklist-items/{item_id}/delete")
async def remove_checklist_item(item_id: str, data: ExpectedRevision):
    return {"deleted": await asyncio.to_thread(_invoke, board.delete_checklist_item, item_id, data.expected_revision)}


@router.post("/checklists/{checklist_id}/delete")
async def remove_checklist(checklist_id: str, data: ExpectedRevision):
    return {"deleted": await asyncio.to_thread(_invoke, board.delete_checklist, checklist_id, data.expected_revision)}


class ArchiveInput(BaseModel):
    expected_revision: int = Field(ge=1)
    archived: bool


@router.patch("/archive/{entity}/{entity_id}")
async def archive_entity(entity: str, entity_id: str, data: ArchiveInput):
    return {"entity": await asyncio.to_thread(
        _invoke, board.set_archived, entity, entity_id, data.expected_revision, data.archived)}


class ReorderColumnInput(BaseModel):
    expected_revision: int = Field(ge=1)
    before_id: str | None = None


class ReorderCardInput(ReorderColumnInput):
    target_column_id: str = Field(min_length=1, max_length=64)


@router.post("/columns/{column_id}/reorder")
async def reorder_column(column_id: str, data: ReorderColumnInput):
    return {"column": await asyncio.to_thread(
        _invoke, board.reorder_column, column_id, data.expected_revision, data.before_id)}


@router.post("/cards/{card_id}/reorder")
async def reorder_card(card_id: str, data: ReorderCardInput):
    return {"card": await asyncio.to_thread(
        _invoke, board.reorder_card, card_id, data.target_column_id,
        data.expected_revision, data.before_id)}


@router.post("/checklists/{checklist_id}/reorder")
async def reorder_checklist(checklist_id: str, data: ReorderColumnInput):
    return {"checklist": await asyncio.to_thread(
        _invoke, board.reorder_checklist, checklist_id, data.expected_revision, data.before_id)}


@router.post("/checklist-items/{item_id}/reorder")
async def reorder_checklist_item(item_id: str, data: ReorderColumnInput):
    return {"item": await asyncio.to_thread(
        _invoke, board.reorder_checklist_item, item_id, data.expected_revision, data.before_id)}


class CardMetadataInput(BaseModel):
    expected_revision: int = Field(ge=1)
    metadata: dict[str, object] = Field(default_factory=dict)


@router.patch("/cards/{card_id}/metadata")
async def update_card_metadata(card_id: str, data: CardMetadataInput):
    return {"card": await asyncio.to_thread(
        _invoke, board.update_card_metadata, card_id, data.expected_revision, data.metadata)}


class DelegationInput(BaseModel):
    confirmed: bool
    expected_revision: int = Field(ge=1)
    assignee: str | None = Field(default=None, max_length=100)
    new_attempt: bool = False


def _delegate(card_id: str, data: DelegationInput):
    from workstation import task_adapter

    with board.database() as conn:
        card = board.get_card_details(conn, card_id)
        intent = board.begin_delegation(conn, card_id, data.expected_revision,
                                        data.assignee, data.new_attempt)
    if intent["task_id"]:
        return intent
    try:
        task_id = task_adapter.create_official_task(
            title=card["title"], description=card["description"], card_id=card_id,
            board_id=card["board_id"], assignee=intent["assignee"],
            idempotency_key=intent["idempotency_key"])
    except Exception as exc:
        with board.database() as conn:
            board.record_delegation_error(conn, intent["id"], type(exc).__name__)
        raise HTTPException(status_code=503, detail="Official task gateway unavailable; intent preserved") from exc
    with board.database() as conn:
        return board.link_delegation(conn, intent["id"], task_id)


@router.post("/cards/{card_id}/delegate")
async def delegate(card_id: str, data: DelegationInput):
    if not data.confirmed:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required")
    return {"delegation": await asyncio.to_thread(_invoke_delegation, _delegate, card_id, data)}


def _sync_delegation(card_id: str):
    from workstation import task_adapter

    with board.database() as conn:
        entries = board.list_delegations(conn, card_id)
    if not entries or not entries[-1]["task_id"]:
        return entries[-1] if entries else None
    latest = entries[-1]
    try:
        status = task_adapter.get_official_task_status(latest["task_id"])
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Official task read unavailable") from exc
    if status is None:
        raise HTTPException(status_code=404, detail="Official task not found")
    with board.database() as conn:
        return board.reconcile_delegation(conn, latest["id"], status)


@router.post("/cards/{card_id}/delegation/sync")
async def sync_delegation(card_id: str):
    return {"delegation": await asyncio.to_thread(_invoke_delegation, _sync_delegation, card_id)}


def _invoke_delegation(fn, *args):
    try:
        return fn(*args)
    except board.BoardConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except board.BoardError as exc:
        raise HTTPException(
            status_code=404 if "not found" in str(exc).lower() else 400,
            detail=str(exc)) from exc


# Read-only relational snapshots are separate from the editable board/card domain.
# No upload, import, arbitrary file path, SQL, or message-sending endpoint is exposed.
from workstation import acirv_datasets, dataset_edits


class DatasetEditInput(BaseModel):
    expected_revision: int = Field(ge=0)
    changes: dict[str, str | int | float | None]


@router.patch("/datasets/{dataset_id}/tables/{table_name}/rows/{record_id}")
async def update_dataset_row(dataset_id: str, table_name: str, record_id: str,
                             data: DatasetEditInput):
    try:
        result = await asyncio.to_thread(
            dataset_edits.update_record, None, dataset_id, table_name, record_id,
            changes=data.changes, expected_revision=data.expected_revision, actor="human",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not result["ok"]:
        raise HTTPException(status_code=409, detail=result)
    return result


def _dataset_read(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/datasets")
async def datasets_catalog():
    return await asyncio.to_thread(_dataset_read, acirv_datasets.list_datasets)


@router.get("/datasets/{dataset_id}/tables/{table_name}")
async def dataset_table(
    dataset_id: str, table_name: str, limit: int = 200, offset: int = 0,
    columns: str | None = None, status: str | None = None,
):
    selected = columns.split(",") if columns else None
    return await asyncio.to_thread(
        _dataset_read, acirv_datasets.list_records,
        None, dataset_id, table_name, limit=limit, offset=offset, columns=selected, status=status
    )


@router.get("/datasets/{dataset_id}/tables/{table_name}/rows/{record_id}")
async def dataset_record(dataset_id: str, table_name: str, record_id: str):
    return await asyncio.to_thread(
        _dataset_read, acirv_datasets.get_record, None, dataset_id, table_name, record_id
    )
