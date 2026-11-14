"""Agent-facing Workstation Database plugin, independent from the Database UI importer."""
from __future__ import annotations

import json
from typing import Any

from . import store


def _schema(name: str, description: str, properties: dict, required: list[str] | None = None) -> dict:
    return {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties,
                           "required": required or [], "additionalProperties": False}}


SCHEMAS = {
    "workstation_db_catalog": _schema(
        "workstation_db_catalog",
        "Discover available Hermes Workstation Database collections and tables. Imported ACIRV/Trello snapshots support versioned local edits through workstation_db_update; agent-generated control records are writable via workstation_db_save. Check this catalog before deciding where durable project/task/control data belongs. Do not use the Database as a replacement for source files, transcripts, secrets, binary artifacts or canonical Hermes session/task state.",
        {},
    ),
    "workstation_db_query": _schema(
        "workstation_db_query",
        "Query a Hermes Workstation Database dataset, without raw SQL. Read ACIRV/Trello snapshots with pending local edits applied by dataset/table, or read 'agent' records by namespace/key. For imported tables, use explicit columns and a small limit to avoid unnecessary private data. Inspect source/provenance before making operational decisions.",
        {
            "dataset": {"type": "string", "description": "Dataset ID from workstation_db_catalog; 'agent' for generated records."},
            "table": {"type": "string", "description": "Imported dataset table name, from catalog."},
            "record_id": {"type": "string", "description": "Optional primary key to fetch a specific imported row."},
            "columns": {"type": "array", "items": {"type": "string"}, "description": "Optional imported-table field projection."},
            "status": {"type": "string", "description": "Optional exact status filter for imported table with status column."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            "namespace": {"type": "string", "description": "Required with key for agent records, otherwise optional filter."},
            "key": {"type": "string", "description": "Stable agent record key in a namespace."},
            "kind": {"type": "string", "description": "Optional agent record type filter."},
        },
        ["dataset"],
    ),
    "workstation_db_save": _schema(
        "workstation_db_save",
        "Persist useful structured data the Hermes agent GENERATES: task-control records, decisions, checkpoints, reports, inventories, summarized operations and references to files. Prefer this when a durable structured control record will be reused; keep original files and canonical task/session state unchanged. Store file metadata/path in data, not full binary files. Never save passwords, tokens, API keys or unneeded personal data. This writes ONLY to the private agent-generated Workstation dataset, NOT imported ACIRV/Trello snapshots. Reuse a stable namespace+key; for updates read current revision first and set expected_revision (no silent overwrite). Do not write transient reasoning, every message or every tool call.",
        {
            "namespace": {"type": "string", "description": "Project or workflow, e.g. 'acirv' or 'hermes_control'."},
            "key": {"type": "string", "description": "Stable idempotency key e.g. 'daily-report-2026-11-07'."},
            "kind": {"type": "string", "description": "Record kind e.g. 'report', 'control', 'checkpoint', 'artifact_ref', 'decision'."},
            "title": {"type": "string", "description": "Short human-readable title."},
            "data": {"type": "object", "description": "Structured JSON payload; for files include paths/provenance/checksum rather than binary content.", "additionalProperties": True},
            "expected_revision": {"type": "integer", "minimum": 1, "description": "Required for changes to an existing key; omitted for new record."},
        },
        ["namespace", "key", "kind", "title", "data"],
    ),
    "workstation_db_update": _schema(
        "workstation_db_update",
        "Edit an existing relational Database row in Hermes. Uses the same versioned local edit queue as the human UI. Never changes the imported snapshots or Trello remotely. First read the row with workstation_db_query to obtain local_revision, then send ONLY the changed scalar fields; expected_revision=0 if never locally edited. A revision conflict must be reviewed, not overwritten. Primary/foreign keys cannot be edited.",
        {
            "dataset": {"type": "string"},
            "table": {"type": "string"},
            "record_id": {"type": "string"},
            "expected_revision": {"type": "integer", "minimum": 0},
            "changes": {"type": "object", "additionalProperties": True},
        },
        ["dataset", "table", "record_id", "expected_revision", "changes"],
    ),
    "workstation_db_trello_plan": _schema(
        "workstation_db_trello_plan",
        "Read a bound native Hermes BrowserTask and compare the observed Trello card TITLE with the corresponding Database record. Persist per-field review/conflicts; never trust agent-supplied remote values. Does not write to Trello, change the imported snapshot or authorize retries. First navigate the BrowserTask to the card; supply card ID, URL, task ID and stable run ID.",
        {
            "card_id": {"type": "string", "description": "Existing 24-character Trello card ID, from Database."},
            "source_url": {"type": "string", "description": "Trello card URL observed in native Browser; shortlink must match Database."},
            "run_id": {"type": "string", "description": "Stable run/occurrence ID for idempotent review."},
            "browser_task_id": {"type": "string", "description": "Existing native BrowserTask ID already at this card; the tool independently reads its title/status. The agent cannot supply remote fields or declare the card open."}
        },
        ["card_id", "source_url", "run_id", "browser_task_id"],
    ),
    "workstation_db_trello_pull": _schema(
        "workstation_db_trello_pull",
        "Apply only verified, conflict-free per-field Trello->Hermes changes from a previously recorded review into the local revisioned Database overlay. Does not modify imported Trello snapshots nor remote Trello. Requires expected_revision from workstation_db_query. Never retry an uncertain effect.",
        {
            "card_id": {"type": "string"},
            "run_id": {"type": "string"},
            "expected_revision": {"type": "integer", "minimum": 0}
        },
        ["card_id", "run_id", "expected_revision"],
    ),
    "workstation_db_trello_push": _schema(
        "workstation_db_trello_push",
        "QA ONLY. Push a previously reviewed local Trello card title to a card on the dedicated Hermes Sync QA board, using the authenticated native BrowserTask. Persist intent BEFORE effects, require BrowserOwner step receipts and independent readback; on uncertain results HOLD permanently until manual reconciliation. Never retry the same review. Not for ACIRV production cards.",
        {
            "card_id": {"type": "string"},
            "review_run_id": {"type": "string"},
            "browser_task_id": {"type": "string"},
            "expected_revision": {"type": "integer", "minimum": 1}
        },
        ["card_id", "review_run_id", "browser_task_id", "expected_revision"],
    ),
    "workstation_db_trello_api_plan": _schema(
        "workstation_db_trello_api_plan",
        "QA only. Read a Trello card title and administrator authority via official REST API using this Hermes profile's credentials. Save an immutable comparison in the existing Database edit journal; no external write.",
        {"card_id": {"type": "string"}, "run_id": {"type": "string"}},
        ["card_id", "run_id"],
    ),
    "workstation_db_trello_api_push": _schema(
        "workstation_db_trello_api_push",
        "QA only: one non-retriable PUT of a previously reviewed local card title through authenticated Trello API, restricted to private Hermes Sync QA. Durable intent before effects; GET readback after. UNKNOWN/HOLD requires manual reconciliation.",
        {"card_id": {"type": "string"}, "review_run_id": {"type": "string"},
         "expected_revision": {"type": "integer", "minimum": 1}},
        ["card_id", "review_run_id", "expected_revision"],
    ),
    "workstation_db_trello_route": _schema(
        "workstation_db_trello_route",
        "Read-only Trello permission routing using the active profile Trello API credentials. Verified board admin -> API; ordinary member -> agent-controlled native Browser; unknown or missing credentials -> HOLD. Does not modify any Trello data or infer authority from workspace membership. Input the 24-hex board ID, not a board URL.",
        {"board_id": {"type": "string", "description": "Trello board 24-character hexadecimal ID"}},
        ["board_id"],
    ),
}


def _result(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, default=str)
    if len(payload) > 120000:
        return json.dumps({"ok": False, "error": "Result too large; select fewer columns or records"})
    return payload


def _catalog(_args: dict) -> str:
    from workstation.acirv_datasets import list_datasets
    catalog = list_datasets()
    return _result({"ok": True, "writable": {"dataset": "agent", "table": "agent_records",
                                           "tool": "workstation_db_save", "max_payload_bytes": 131072},
                    "imported_writable_local": catalog.get("datasets", []),
                    "views": catalog.get("views", [])})


def _query(args: dict) -> str:
    name = args.get("dataset")
    if name == "agent":
        return _result(store.list_records(namespace=args.get("namespace"), key=args.get("key"),
                                          kind=args.get("kind"), limit=args.get("limit", 20)))
    from workstation.acirv_datasets import get_record, list_records
    table = args.get("table")
    if not isinstance(table, str) or not table:
        raise ValueError("table is required for imported datasets")
    if args.get("record_id") is not None:
        return _result({"ok": True, "local_edits": True,
                        "record": get_record(None, name, table, str(args["record_id"]))})
    return _result({"ok": True, "local_edits": True,
                    "result": list_records(None, name, table, limit=args.get("limit", 20),
                                           columns=args.get("columns"), status=args.get("status"))})


def _update(args: dict) -> str:
    from workstation.dataset_edits import update_record
    return _result(update_record(None, args["dataset"], args["table"], str(args["record_id"]),
                                 changes=args["changes"], expected_revision=args["expected_revision"],
                                 actor="agent"))


def _plan_trello(args: dict) -> str:
    """Persist an effect-free review of one observed card in the existing edit journal."""
    import re
    from urllib.parse import urlsplit

    from workstation.acirv_datasets import get_record
    from workstation.trello_sync_reconcile import (compare_card, read_reviews,
        save_review, verified_browser_card_title)

    card_id = args["card_id"]
    if not isinstance(card_id, str) or not re.fullmatch(r"[a-f0-9]{24}", card_id):
        raise ValueError("card_id must be a 24-character Trello ID")

    def shortlink(value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("invalid Trello card URL")
        parsed = urlsplit(value)
        parts = parsed.path.split("/")
        if (parsed.scheme != "https" or parsed.netloc != "trello.com"
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or len(parts) < 3 or parts[1] != "c"
                or not re.fullmatch(r"[A-Za-z0-9]{8}", parts[2])):
            raise ValueError("untrusted Trello card URL")
        return parts[2]

    card = get_record(None, "trello", "cards", card_id)["record"]
    source_url = args["source_url"]
    if shortlink(source_url) != shortlink(card.get("url", "")):
        raise ValueError("Trello card URL is not the selected Database record")
    if card.get("status") != "em_aberto":
        raise ValueError("historical/closed card is not eligible for sync")

    observation = verified_browser_card_title(args["browser_task_id"])
    if shortlink(observation["url"]) != shortlink(source_url):
        raise ValueError("native Browser is showing a different Trello card")
    # First implementation synchronizes TITLE only. Other fields, comments,
    # checklists, activity, archived state and list transitions are not writable.
    # Never trust model-supplied values for remote state or card completion.
    previous = read_reviews(None, card_id)
    baseline: dict[str, Any] = {}
    for review in previous:
        prior = review["plan"]
        if prior.get("native_observed") is not True or not prior.get("remote_open_verified"):
            continue
        for field, decision in prior.get("fields", {}).items():
            if field not in baseline and decision.get("action") == "equal" and "value" in decision:
                baseline[field] = decision["value"]

    plan = compare_card(
        local=card, remote={"name": observation["name"]}, baseline=baseline or None,
        observed_fields=["name"],
        remote_open_verified=observation["open"],
    )
    plan["native_observed"] = True
    plan["browser_task_id"] = observation["browser_task_id"]
    plan["browser_list_name"] = observation["list_name"]
    result = save_review(
        None, run_id=args["run_id"], card_id=card_id,
        source_url=source_url, plan=plan,
    )
    return _result({"ok": result["ok"], "review": result, "plan": plan,
                    "external_trello_writes": 0})


def _pull_trello(args: dict) -> str:
    from workstation.trello_sync_reconcile import apply_reviewed_pull
    return _result(apply_reviewed_pull(
        None, run_id=args["run_id"], card_id=args["card_id"],
        expected_revision=args["expected_revision"],
    ))


def _push_trello(args: dict) -> str:
    from workstation.trello_sync_push import push_reviewed_title
    return _result(push_reviewed_title(
        None, card_id=args["card_id"], review_run_id=args["review_run_id"],
        browser_task_id=args["browser_task_id"],
        expected_revision=args["expected_revision"],
    ))


def _route_trello(args: dict) -> str:
    from workstation.prefabs.trello import Credential, TrelloClient, TrelloAccessError
    from workstation.trello_sync_transport import route_for_board
    try:
        # Never substitute process-wide variables for another profile's secret scope.
        cred = Credential.from_secret_scope()
    except TrelloAccessError:
        return _result({"ok": False, "transport": "hold",
                        "reason": "trello_profile_credentials_unavailable"})
    try:
        route = route_for_board(TrelloClient(credential=cred), args["board_id"])
    except TrelloAccessError:
        return _result({"ok": False, "transport": "hold",
                        "reason": "trello_permission_check_failed"})
    return _result({"ok": route["transport"] != "hold", **route})


def _api_trello_client():
    from workstation.prefabs.trello import Credential, TrelloClient
    return TrelloClient(credential=Credential.from_secret_scope())


def _api_trello_plan(args: dict) -> str:
    from workstation.prefabs.trello import TrelloAccessError
    from workstation.trello_sync_api import plan_api_title
    try:
        return _result(plan_api_title(
            None, _api_trello_client(), card_id=args["card_id"], run_id=args["run_id"]))
    except TrelloAccessError:
        return _result({"ok": False, "transport": "hold",
                        "reason": "trello_api_credentials_or_permission_unavailable"})


def _api_trello_push(args: dict) -> str:
    from workstation.prefabs.trello import TrelloAccessError
    from workstation.trello_sync_api import push_api_title
    try:
        return _result(push_api_title(
            None, _api_trello_client(), card_id=args["card_id"],
            review_run_id=args["review_run_id"],
            expected_revision=args["expected_revision"]))
    except TrelloAccessError:
        return _result({"ok": False, "transport": "hold",
                        "reason": "trello_api_credentials_or_permission_unavailable"})


def _save(args: dict) -> str:
    return _result(store.save_record(namespace=args["namespace"], key=args["key"], kind=args["kind"],
                                     title=args["title"], data=args["data"],
                                     expected_revision=args.get("expected_revision")))


_HANDLERS = {"workstation_db_catalog": _catalog, "workstation_db_query": _query,
             "workstation_db_save": _save, "workstation_db_update": _update,
             "workstation_db_trello_plan": _plan_trello,
             "workstation_db_trello_pull": _pull_trello,
             "workstation_db_trello_push": _push_trello,
             "workstation_db_trello_route": _route_trello,
             "workstation_db_trello_api_plan": _api_trello_plan,
             "workstation_db_trello_api_push": _api_trello_push}


def _handle(name: str, args: dict) -> str:
    try:
        if not isinstance(args, dict):
            raise ValueError("arguments must be an object")
        return _HANDLERS[name](args)
    except (ValueError, KeyError, TypeError) as exc:
        return _result({"ok": False, "error": str(exc)})


def register(ctx) -> None:
    # Existing 'file' toolset is in the default agent tool bundle; no core or
    # platform toolset changes and no prompt-cache-breaking dynamic injection.
    for name, schema in SCHEMAS.items():
        ctx.register_tool(name=name, toolset="file", schema=schema,
                          handler=lambda args, name=name, **_kw: _handle(name, args))
