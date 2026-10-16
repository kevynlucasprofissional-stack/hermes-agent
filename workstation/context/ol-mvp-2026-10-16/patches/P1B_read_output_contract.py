"""P1B PROPOSED patch — output-only Browser read contract, NOT imported by runtime.

Target after Stage A authorization:
    workstation/experience_compiler/read_output_contract.py

This is a pure normalization/consistency helper, NOT a verifier or a source
of authority. Only a separately authorized canonical acceptance handler may
use its result, after resolving an owner-produced independent DOM receipt.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

CARD_FIELDS = ("id", "list", "title", "description")
READ_SHAPE = "native_browser.card_fields.v1"


class UnverifiedRead(ValueError):
    """Reject a read whose independent observable outcome cannot be matched."""


def _clean(value: Any) -> str:
    if not isinstance(value, str):
        raise UnverifiedRead("non_string_card_field")
    return re.sub(r"\s+", " ", value).strip()


def _items(extract_result: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    # Native controller responses can carry data under result.items or items;
    # never silently accept an empty/non-list collection.
    result = extract_result.get("result")
    body = result if isinstance(result, Mapping) else extract_result
    items = body.get("items")
    if not isinstance(items, list) or not items or len(items) > 64:
        raise UnverifiedRead("invalid_extraction_items")
    if body.get("success") is False or extract_result.get("success") is False:
        raise UnverifiedRead("extraction_unsuccessful")
    return items


def prepare_read_shape(
    extract_result: Mapping[str, Any],
    independent_dom_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare typed extraction against independent DOM readback; output is UNTRUSTED proposal.

    Call ONLY from canonical owner-verified acceptance; never call the compiler
    directly based on this function's output. Missing IDs, duplicates, text
    mismatch and partially observed rows reject closed.
    """
    extracted = _items(extract_result)
    if (not isinstance(independent_dom_rows, (tuple, list))
            or len(independent_dom_rows) != len(extracted)):
        raise UnverifiedRead("readback_cardinality_mismatch")

    oracle: dict[str, dict[str, str]] = {}
    for row in independent_dom_rows:
        if not isinstance(row, Mapping):
            raise UnverifiedRead("invalid_readback_row")
        canonical = {k: _clean(row.get(k)) for k in CARD_FIELDS}
        if not canonical["id"] or not canonical["title"] or not canonical["list"]:
            raise UnverifiedRead("empty_readback_identity")
        if canonical["id"] in oracle:
            raise UnverifiedRead("duplicate_readback_identity")
        oracle[canonical["id"]] = canonical

    seen: set[str] = set()
    for item in extracted:
        if not isinstance(item, Mapping):
            raise UnverifiedRead("invalid_extraction_row")
        attrs = item.get("attributes", {})
        if not isinstance(attrs, Mapping):
            raise UnverifiedRead("invalid_extraction_attributes")
        item_id, item_list = _clean(attrs.get("data-card-id")), _clean(attrs.get("data-list"))
        if not item_id or item_id in seen or item_id not in oracle:
            raise UnverifiedRead("unbound_or_duplicate_card")
        expected = oracle[item_id]
        if item_list != expected["list"]:
            raise UnverifiedRead("list_mismatch")
        visible = _clean(item.get("text"))
        # Native textContent can concatenate fields with or without DOM whitespace.
        # Require both non-overlapping semantic fields, in their DOM order, but
        # do not insist on a particular whitespace join between them.
        title, description = expected["title"], expected["description"]
        title_at = visible.find(title)
        desc_at = visible.find(description, title_at + len(title)) if title_at >= 0 else -1
        if title_at < 0 or (description and desc_at < 0):
            raise UnverifiedRead("title_description_mismatch")
        seen.add(item_id)
    if seen != set(oracle):
        raise UnverifiedRead("missing_readback_card")

    # Only invariant *schema* and verifiability can generalize across cards.
    # Do NOT encode particular IDs, titles, page text, URLs or passwords into
    # reusable predicates. The digest is an ephemeral audit correlation value.
    proof_digest = hashlib.sha256(
        json.dumps(sorted(oracle.values(), key=lambda x: x["id"]),
                   sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return {
        "shape": READ_SHAPE,
        "semantic_predicates": {
            "read.output_shape": READ_SHAPE,
            "read.fields_complete": True,
        },
        "proposed_verified_predicates": {
            "read.output_shape": READ_SHAPE,
            "read.fields_complete": True,
        },
        "result_digest": proof_digest,
        "result_count": len(oracle),
    }


def guarded_projection(
    extract_result: Mapping[str, Any],
    independent_dom_rows: Sequence[Mapping[str, Any]],
    *,
    task_id: str,
    run_id: str,
    operation_id: str,
    raw_result_ref: str,
    owner_readback_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Require owner-bound receipt metadata (caller MUST resolve artifact independently).

    This is defense-in-depth validation, not cryptographic authorization.
    Authority, provenance, real receipt integrity and ACCEPTED status must be
    attested by the existing Canonical Run owner and ExperienceCorpus.
    """
    if not all((task_id, run_id, operation_id, raw_result_ref)):
        raise UnverifiedRead("missing_canonical_identity")
    receipt = owner_readback_receipt
    required = {
        "task_id": task_id, "run_id": run_id, "operation_id": operation_id,
        "raw_result_ref": raw_result_ref, "observer": "workstation.browser_live_dom",
        "source_kind": "browser_live_dom", "trust_class": "trusted_runtime",
        "independent_readback": True, "status": "VERIFIED",
    }
    if not isinstance(receipt, Mapping) or any(receipt.get(k) != v for k, v in required.items()):
        raise UnverifiedRead("owner_readback_receipt_unbound")
    return prepare_read_shape(extract_result, independent_dom_rows)
