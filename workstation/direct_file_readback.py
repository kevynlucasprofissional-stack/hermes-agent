"""Owner-bound readback for direct write_file tool calls.

The result of write_file is a dispatch acknowledgement, not the acceptance
evidence. This module performs a fresh independent filesystem read, stores
a durable receipt, and rechecks it at the Kanban completion boundary.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _normalized(text: str) -> str:
    # ShellFileOperations intentionally preserves pre-existing BOM / CRLF.
    return text.removeprefix("\ufeff").replace("\r\n", "\n")


def capture_file_write_readback(
    tool: str, args: dict, raw: Any, *, task_id: str | None,
    run_id: str | int | None, session_id: str | None, call_id: str,
) -> dict | None:
    """Return a verified receipt only for the actual owner-bound write_file."""
    if (tool != "write_file" or not task_id or run_id is None or not session_id
            or not isinstance(args, dict) or not isinstance(args.get("content"), str)):
        return None
    try:
        result = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(result, dict) or result.get("verified") is not True or result.get("error"):
            return None
        path = result.get("resolved_path") or args.get("path")
        if not isinstance(path, str) or not Path(path).is_absolute():
            return None
        resolved = Path(path).resolve(strict=True)
        if not resolved.is_file():
            return None
        data = resolved.read_bytes()
        observed = data.decode("utf-8", "surrogateescape")
        if _normalized(observed) != _normalized(args["content"]):
            return None
        from workstation.artifacts import ArtifactStore
        from workstation.batch_detection import call_key

        digest = hashlib.sha256(data).hexdigest()
        operation_id = call_key(tool, args)
        payload = {
            "task_id": str(task_id), "session_id": str(session_id),
            "run_id": str(run_id), "call_id": str(call_id),
            "operation_id": operation_id, "tool": tool,
            "path": str(resolved), "observed_sha256": digest,
            "expected_text_sha256": hashlib.sha256(
                _normalized(args["content"]).encode("utf-8", "surrogateescape")
            ).hexdigest(),
        }
        store = ArtifactStore()
        call_suffix = hashlib.sha256(str(call_id).encode()).hexdigest()[:12]
        saved = store.store(task_id, f"file_readback_{operation_id}_{call_suffix}.json",
                            payload, schema="hermes.direct_file_readback.v1")
        persisted = store.resolve_structured(saved.ref)
        if persisted.get("content") != payload or persisted.get("sha256") != saved.sha256:
            return None
        return {"evidence_ref": saved.ref, "sha256": saved.sha256,
                "operation_id": operation_id, "task_id": str(task_id),
                "run_id": str(run_id), "call_id": str(call_id)}
    except (OSError, ValueError, TypeError, UnicodeError, KeyError):
        return None


def verify_file_write_receipts(
    observations: list[dict] | None, *, task_id: str, session_id: str,
    run_id: str, trace_truncated: bool,
) -> tuple[list, list, list[str]]:
    """Reject the entire direct-tool lane unless every effect is verified."""
    from workstation.artifacts import ArtifactStore
    from workstation.contracts import EvidenceRef

    if trace_truncated or not isinstance(observations, list) or not observations:
        return [], [], ["Tool observation is incomplete"]
    store = ArtifactStore()
    evidence, verifiers, pending = [], [], []
    saw_write = False
    # Intermediate writes are proven at dispatch time. At acceptance, only
    # the final write to each path must still match disk state.
    last_write_by_path: dict[str, int] = {}
    for index, item in enumerate(observations):
        if not isinstance(item, dict) or item.get("tool") != "write_file":
            continue
        proof = item.get("file_readback")
        if isinstance(proof, dict) and proof.get("evidence_ref"):
            try:
                payload = store.resolve_structured(proof["evidence_ref"])["content"]
                if isinstance(payload, dict) and isinstance(payload.get("path"), str):
                    last_write_by_path[payload["path"]] = index
            except (OSError, ValueError, KeyError, TypeError):
                pass
    for index, item in enumerate(observations):
        if not isinstance(item, dict) or item.get("status") != "completed":
            pending.append("Unfinished or failed tool operation")
            continue
        if item.get("effect") in {"PURE_READ", "DISCOVERY"}:
            continue
        if item.get("effect") not in {"MUTATION", "IDEMPOTENT_WRITE"}:
            pending.append("Tool effect provenance is unknown")
            continue
        from workstation.external_readback import SUPPORTED, verify_external_receipt
        if item.get("tool") in SUPPORTED:
            saw_write = True
            verified = verify_external_receipt(
                item, task_id=task_id, session_id=session_id, run_id=run_id,
            )
            if verified is None:
                pending.append("External operation has no owner-verified readback")
            else:
                ref, verifier = verified
                evidence.append(ref)
                verifiers.append(verifier)
            continue
        if item.get("tool") != "write_file":
            pending.append(f"No verified readback for {item.get('tool', 'unknown')}")
            continue
        saw_write = True
        proof = item.get("file_readback")
        if not isinstance(proof, dict) or not proof.get("evidence_ref"):
            pending.append("write_file has no independent readback")
            continue
        try:
            ref = store.resolve_structured(proof["evidence_ref"])
            payload = ref["content"]
            if (payload["task_id"] != task_id or payload["session_id"] != session_id
                    or payload["run_id"] != run_id or
                    payload["call_id"] != item["call_id"] or
                    payload["operation_id"] != proof["operation_id"] or
                    payload["tool"] != "write_file" or
                    ref["sha256"] != proof["sha256"]):
                raise ValueError("readback ownership mismatch")
            path = Path(payload["path"])
            if not path.is_absolute():
                raise ValueError("readback path was not absolute")
            if last_write_by_path.get(payload["path"]) == index:
                if not path.is_file():
                    raise ValueError("file missing at completion")
                if hashlib.sha256(path.read_bytes()).hexdigest() != payload["observed_sha256"]:
                    raise ValueError("final file state differs from last verified write")
            evidence.append(EvidenceRef(
                "file_persisted_readback", proof["evidence_ref"], sha256=ref["sha256"],
                task_id=task_id, run_id=run_id, operation_id=proof["operation_id"],
                verifier="direct_write_file_readback",
            ))
            verifiers.append({
                "verifier": "direct_write_file_readback", "passed": True,
                "evidence_ref": proof["evidence_ref"], "task_id": task_id,
                "run_id": run_id, "operation_id": proof["operation_id"],
            })
        except (OSError, ValueError, KeyError, TypeError):
            pending.append("write_file readback is stale or lacks valid provenance")
    if not saw_write:
        pending.append("No verified file mutation observed")
    return evidence, verifiers, pending
