"""Conservative three-way Trello<->Database field reconciliation.

Pure decision logic; it NEVER accesses Trello or writes to either database.
A baseline is trusted only after the same values were verified on both sides.
Unobserved remote fields and first-run mismatches never become deletions/writes.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# Scalar fields currently represented in trello.sqlite and observable in Trello.
# A caller must explicitly attest which fields were actually read, not merely
# insert None for fields the Browser omitted.
FIELDS = frozenset({"name", "description", "list_name", "due"})
MAX_FIELD_CHARS = 20000


def _value(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > MAX_FIELD_CHARS:
        raise ValueError(f"invalid {field} value")
    return value


def compare_card(
    *, local: Mapping[str, Any],
    remote: Mapping[str, Any],
    baseline: Mapping[str, Any] | None,
    observed_fields: list[str],
    remote_open_verified: bool,
) -> dict[str, Any]:
    """Plan pull/push/conflicts without effects.

    'baseline=None' means no common acknowledged sync version exists.
    For those first observations, equality is safe; any mismatch is an
    unresolved initial conflict, even if the imported snapshot is old.
    """
    if not isinstance(local, Mapping) or not isinstance(remote, Mapping):
        raise ValueError("local and remote must be mappings")
    if baseline is not None and not isinstance(baseline, Mapping):
        raise ValueError("baseline must be an object or None")
    if type(remote_open_verified) is not bool:
        raise ValueError("remote_open_verified must be bool")
    if not isinstance(observed_fields, list) or not observed_fields:
        raise ValueError("explicit observed_fields required")
    if len(set(observed_fields)) != len(observed_fields) or any(
        type(f) is not str or f not in FIELDS for f in observed_fields
    ):
        raise ValueError("unrecognized or duplicate observed field")
    decisions: dict[str, dict] = {}
    for field in observed_fields:
        if field not in remote or field not in local:
            decisions[field] = {"action": "defer", "reason": "field_unavailable"}
            continue
        lhs = _value(local[field], field)
        rhs = _value(remote[field], field)
        if baseline is None or field not in baseline:
            if lhs == rhs:
                decisions[field] = {"action": "equal", "value": lhs}
            else:
                decisions[field] = {
                    "action": "conflict", "reason": "no_verified_baseline",
                    "local": lhs, "remote": rhs, "baseline": None,
                }
            continue
        base = _value(baseline[field], field)
        if lhs == rhs:
            decisions[field] = {"action": "equal", "value": lhs}
        elif lhs == base:
            decisions[field] = {
                "action": "pull", "baseline": base, "local": lhs, "remote": rhs,
            }
        elif rhs == base:
            decisions[field] = {
                "action": "push", "baseline": base, "local": lhs, "remote": rhs,
            }
        else:
            decisions[field] = {
                "action": "conflict", "reason": "both_changed",
                "baseline": base, "local": lhs, "remote": rhs,
            }

    # Exclude completed/archived or unverified cards entirely: neither a
    # pull nor a push may silently reactivate or change historical items.
    if not remote_open_verified:
        for decision in decisions.values():
            if decision["action"] in {"push", "pull"}:
                decision["action"] = "defer"
                decision["reason"] = "remote_open_not_verified"

    actions = {field: d["action"] for field, d in decisions.items()}
    conflicts = [f for f, action in actions.items() if action == "conflict"]
    pushes = [f for f, action in actions.items() if action == "push"]
    pulls = [f for f, action in actions.items() if action == "pull"]
    return {
        "status": "conflict" if conflicts else ("changes_pending" if pushes or pulls else "read_only"),
        "remote_open_verified": remote_open_verified,
        "fields": decisions,
        "conflicts": conflicts,
        "pull": pulls,
        "push": pushes,
        "ready_for_external_write": False,  # Only a verified Browser executor can grant this.
    }


# The dry-run and unresolved two-sided values live alongside the established
# local edit journal, not in imported trello.sqlite or a third task database.
def save_review(
    home: "Path | None", *, run_id: str, card_id: str, source_url: str,
    plan: dict[str, Any],
) -> dict[str, Any]:
    """Append one reviewed observation, idempotent per (run, card).

    A changed duplicate is a conflict, never silent last-writer-wins.
    Does not queue or execute any remote mutation.
    """
    import json
    import re
    from contextlib import closing
    from datetime import datetime, timezone
    from workstation.dataset_edits import _connect

    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", run_id):
        raise ValueError("invalid run_id")
    if not isinstance(card_id, str) or not re.fullmatch(r"[a-f0-9]{24}", card_id):
        raise ValueError("invalid card_id")
    if not isinstance(source_url, str) or not source_url.startswith("https://trello.com/c/"):
        raise ValueError("invalid source_url")
    if not isinstance(plan, dict) or plan.get("ready_for_external_write") is not False:
        raise ValueError("review plan must be effect-free")
    encoded = json.dumps(plan, ensure_ascii=False, allow_nan=False, sort_keys=True)
    if len(encoded.encode("utf-8")) > 131072:
        raise ValueError("review exceeds 128 KiB")
    with closing(_connect(home)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trello_sync_reviews(
                run_id TEXT NOT NULL,
                card_id TEXT NOT NULL,
                source_url TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                PRIMARY KEY(run_id, card_id)
            )""")
        conn.execute("BEGIN IMMEDIATE")
        try:
            existing = conn.execute(
                "SELECT plan_json,source_url FROM trello_sync_reviews WHERE run_id=? AND card_id=?",
                (run_id, card_id),
            ).fetchone()
            if existing:
                conn.commit()
                if existing["plan_json"] == encoded and existing["source_url"] == source_url:
                    return {"ok": True, "status": "unchanged", "run_id": run_id, "card_id": card_id}
                return {"ok": False, "error": "same_run_changed", "run_id": run_id, "card_id": card_id}
            conn.execute(
                "INSERT INTO trello_sync_reviews(run_id,card_id,source_url,plan_json,recorded_at) "
                "VALUES(?,?,?,?,?)",
                (run_id, card_id, source_url, encoded, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            return {"ok": True, "status": "recorded", "run_id": run_id, "card_id": card_id}
        except Exception:
            conn.rollback()
            raise


def read_reviews(home: "Path | None", card_id: str) -> list[dict[str, Any]]:
    """Return bounded, immutable review history for human conflict resolution."""
    import json
    import re
    from contextlib import closing
    from workstation.dataset_edits import _connect, path

    if not isinstance(card_id, str) or not re.fullmatch(r"[a-f0-9]{24}", card_id):
        raise ValueError("invalid card_id")
    if not path(home).exists():
        return []
    with closing(_connect(home)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trello_sync_reviews(
                run_id TEXT NOT NULL, card_id TEXT NOT NULL, source_url TEXT NOT NULL,
                plan_json TEXT NOT NULL, recorded_at TEXT NOT NULL,
                PRIMARY KEY(run_id, card_id)
            )""")
        return [
            {"run_id": row["run_id"], "source_url": row["source_url"],
             "recorded_at": row["recorded_at"], "plan": json.loads(row["plan_json"])}
            for row in conn.execute(
                "SELECT * FROM trello_sync_reviews WHERE card_id=? "
                "ORDER BY recorded_at DESC, run_id DESC LIMIT 25",
                (card_id,),
            )
        ]


def apply_reviewed_pull(
    home: "Path | None", *, run_id: str, card_id: str, expected_revision: int,
) -> dict[str, Any]:
    """Apply ONLY reviewed Trello->Hermes scalar fields using the existing CAS journal.

    Imported Trello snapshots and the remote Trello card are never written.
    Unverified/unknown source identity or drift returns a conflict, not a retry.
    """
    import re
    import json
    from contextlib import closing
    from workstation.dataset_edits import _connect, update_record
    from workstation.acirv_datasets import get_record

    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", run_id):
        raise ValueError("invalid run_id")
    if not isinstance(card_id, str) or not re.fullmatch(r"[a-f0-9]{24}", card_id):
        raise ValueError("invalid card_id")
    if type(expected_revision) is not int or expected_revision < 0:
        raise ValueError("invalid expected_revision")

    with closing(_connect(home)) as conn:
        try:
            row = conn.execute(
                "SELECT plan_json FROM trello_sync_reviews WHERE run_id=? AND card_id=?",
                (run_id, card_id),
            ).fetchone()
        except Exception as exc:
            if "no such table" in str(exc):
                row = None
            else:
                raise
    if row is None:
        return {"ok": False, "error": "review_missing"}
    plan = json.loads(row["plan_json"])
    if (plan.get("native_observed") is not True or not plan.get("remote_open_verified")
            or plan.get("ready_for_external_write") is not False
            or not isinstance(plan.get("browser_task_id"), str)):
        return {"ok": False, "error": "review_not_qualified"}
    # Saved previews are not authority. Verify native Browser state again.
    try:
        observed = verified_browser_card_title(plan["browser_task_id"])
    except Exception:
        return {"ok": False, "error": "native_browser_readback_unavailable"}
    from urllib.parse import urlsplit
    url_path = urlsplit(observed["url"]).path.split("/")
    if (not observed["open"] or len(url_path) < 3
            or plan.get("browser_list_name") != observed["list_name"]):
        return {"ok": False, "error": "remote_card_changed"}
    details = get_record(home, "trello", "cards", card_id)
    expected_path = urlsplit(details["record"]["url"]).path.split("/")
    if len(expected_path) < 3 or expected_path[2] != url_path[2]:
        return {"ok": False, "error": "remote_identity_changed"}
    current = details["record"]
    if current.get("status") != "em_aberto" or details.get("source_conflict_fields"):
        return {"ok": False, "error": "source_or_status_changed"}
    changes: dict[str, str | None] = {}
    for field, decision in plan.get("fields", {}).items():
        if decision.get("action") != "pull":
            continue
        if field != "name":
            return {"ok": False, "error": "unsupported_native_pull_field"}
        local_value = decision.get("local")
        remote_value = decision.get("remote")
        if observed["name"] != remote_value:
            return {"ok": False, "error": "remote_field_changed", "field": field}
        if current.get(field) == remote_value:
            continue  # previous pull already applied
        if current.get(field) != local_value:
            return {"ok": False, "error": "local_field_changed", "field": field}
        changes[field] = _value(remote_value, field)
    if not changes:
        return {"ok": True, "status": "no_changes", "external_trello_writes": 0}
    if details.get("local_revision") != expected_revision:
        return {
            "ok": False, "error": "revision_conflict",
            "current_revision": details.get("local_revision"),
        }
    saved = update_record(
        home, "trello", "cards", card_id, changes=changes,
        expected_revision=expected_revision, actor="agent",
    )
    return {**saved, "external_trello_writes": 0, "review_run_id": run_id}


# Read-only, fixed DOM observation through the existing authenticated Electron
# BrowserTask controller. Never evaluate code provided by a Trello card or model.
_NATIVE_TRELLO_CARD_READ = """(() => {
  const title = document.querySelector('[data-testid="card-back-title-input"]');
  const done = [...document.querySelectorAll('[data-testid="card-done-state-completion-button"]')]
    .map(el => el.getAttribute('aria-label') || '');
  const bodyText = document.body?.innerText || '';
  const boardName = document.querySelector('[data-testid="board-name-display"]')?.textContent?.trim() || null;
  const listControl = [...document.querySelectorAll('button')].find(el =>
    (el.getAttribute('aria-label') || '').startsWith('Lista de alterações deste cartão, atualmente em '));
  const listLabel = listControl?.getAttribute('aria-label') || '';
  const listName = listLabel.startsWith('Lista de alterações deste cartão, atualmente em ')
    ? listLabel.slice('Lista de alterações deste cartão, atualmente em '.length).trim() : null;
  const incomplete = done.length > 0 && done.every(x => x.startsWith('Marcar este cartão como concluído ('));
  const archived = bodyText.includes('Este cartão está arquivado')
    || bodyText.includes('Este cartão foi arquivado');
  return {
    url: location.href,
    title: title ? title.value : null,
    boardName,
    listName,
    open: Boolean(incomplete && listName && !archived)
  };
})()"""


def verified_browser_card_title(browser_task_id: str) -> dict[str, Any]:
    """Observe title/open indicator from bound native BrowserTask; no navigation.

    A model-provided title or open flag alone is NOT acceptable proof.
    """
    import json
    import re
    from tools.browser_workstation import _dispatch
    if (not isinstance(browser_task_id, str)
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", browser_task_id)):
        raise ValueError("invalid BrowserTask ID")
    raw = _dispatch(
        "browser_console", {"expression": _NATIVE_TRELLO_CARD_READ},
        task_id=browser_task_id, model_facing=True,
    )
    response = json.loads(raw)
    result = response.get("result")
    if not response.get("success") or not isinstance(result, dict):
        raise ValueError("native Browser readback failed")
    from urllib.parse import urlsplit
    url = result.get("url")
    parsed = urlsplit(url) if isinstance(url, str) else None
    parts = parsed.path.split("/") if parsed else []
    if (not parsed or parsed.scheme != "https" or parsed.netloc != "trello.com"
            or parsed.query or parsed.fragment or len(parts) < 3
            or parts[1] != "c" or not re.fullmatch(r"[A-Za-z0-9]{8}", parts[2])):
        raise ValueError("native Browser is not on a Trello card")
    title = result.get("title")
    if not isinstance(title, str) or not title.strip() or len(title) > 500:
        raise ValueError("native Trello card title unavailable")
    if type(result.get("open")) is not bool:
        raise ValueError("native card completion state unavailable")
    list_name = result.get("listName")
    if not isinstance(list_name, str) or not list_name.strip() or len(list_name) > 255:
        raise ValueError("native card list unavailable")
    from workstation.trello_inventory import _DONE_LIST
    board_name = result.get("boardName")
    if board_name is not None and (not isinstance(board_name, str) or len(board_name) > 255):
        raise ValueError("invalid native board name")
    return {"url": url, "name": title, "list_name": list_name,
            "board_name": board_name,
            "open": result["open"] and not bool(_DONE_LIST.search(list_name)),
            "browser_task_id": browser_task_id}
