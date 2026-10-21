"""Cooperative, local-first coordination for agents sharing one Git checkout.

No background service, no branch/worktree creation, no automatic stale-lock stealing.
The shared Git index is written only by the designated integration coordinator.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

IDENTIFIER = re.compile(r"^[a-z][a-z0-9-]{1,49}$")


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def validate_id(value: str) -> str:
    if not IDENTIFIER.fullmatch(value):
        raise ValueError("Identifier must be 2-50 lowercase ASCII letters/digits/hyphens")
    return value


def normalize_path(raw: str) -> str:
    value = raw.replace("\\", "/").strip("/")
    segments = value.split("/")
    if not value or raw.startswith(("/", "\\")) or ":" in value or any(
        part in ("", ".", "..") for part in segments
    ):
        raise ValueError(f"Unsafe claim path: {raw!r}")
    return value.casefold()


def overlaps(a: str, b: str) -> bool:
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def state_root(repo: Path) -> Path:
    return repo / ".hermes-collab"


@contextmanager
def registry_guard(folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    guard = folder / ".registry.lock"
    try:
        guard.mkdir()  # atomic on the same Windows filesystem
    except FileExistsError as error:
        raise RuntimeError(
            "Registry is being modified; retry later. If abandoned, inspect before manual cleanup."
        ) from error
    try:
        yield
    finally:
        guard.rmdir()


def write_json(path: Path, payload: dict) -> None:
    # Atomic replace prevents readers observing a half-written heartbeat.
    fd, temp = tempfile.mkstemp(prefix="claim-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def read_claims(folder: Path) -> list[dict]:
    result = []
    for lock in sorted(folder.glob("*.claim")):
        if not lock.is_dir():
            continue
        manifest = lock / "owner.json"
        if manifest.exists():
            result.append(json.loads(manifest.read_text(encoding="utf-8")))
        else:
            result.append({"lane": lock.name.removesuffix(".claim"), "status": "INCOMPLETE_CLAIM"})
    return result


def claim(repo: Path, agent: str, lane: str, paths: list[str], task: str) -> dict:
    agent, lane = validate_id(agent), validate_id(lane)
    normalized = sorted({normalize_path(p) for p in paths})
    if not normalized or not task.strip():
        raise ValueError("A claimed lane requires --paths and a meaningful --task")
    folder = state_root(repo)
    with registry_guard(folder):
        dest = folder / f"{lane}.claim"
        for active in read_claims(folder):
            if active["lane"] == lane:
                raise RuntimeError(f"Lane {lane} is already claimed (do not steal)")
            for path in normalized:
                for existing in active.get("paths", []):
                    if overlaps(path, existing):
                        raise RuntimeError(
                            f"Path conflict: {path} overlaps {existing}, owned by {active.get('agent')}"
                        )
        dest.mkdir()
        payload = {
            "agent": agent, "lane": lane, "paths": normalized,
            "task": task.strip(), "status": "ACTIVE",
            "started_at": utc_now(), "heartbeat_at": utc_now(), "next_action": "",
        }
        write_json(dest / "owner.json", payload)
        return payload


def update(repo: Path, agent: str, lane: str, status: str, next_action: str) -> dict:
    folder = state_root(repo)
    with registry_guard(folder):
        path = folder / f"{validate_id(lane)}.claim" / "owner.json"
        if not path.is_file():
            raise RuntimeError(f"No live claim for {lane}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["agent"] != validate_id(agent):
            raise RuntimeError(f"Owner mismatch: lane {lane} belongs to {data['agent']}")
        data.update(status=status, next_action=next_action, heartbeat_at=utc_now())
        write_json(path, data)
        return data


def release(repo: Path, agent: str, lane: str) -> dict:
    folder = state_root(repo)
    with registry_guard(folder):
        dest = folder / f"{validate_id(lane)}.claim"
        manifest = dest / "owner.json"
        if not manifest.is_file():
            raise RuntimeError(f"No valid claim for {lane}; inspect manually if incomplete")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if data["agent"] != validate_id(agent):
            raise RuntimeError(f"Only {data['agent']} can release {lane}")
        shutil.rmtree(dest)
        return {"released": lane, "agent": agent}


def check_path(repo: Path, path: str, agent: str | None = None) -> dict:
    """Check if a path is claimed by another agent. Returns {allowed, owner, lane}."""
    try:
        normalized = normalize_path(path)
    except ValueError:
        # Invalid path → fail open (allow) but warn
        return {"allowed": True, "owner": None, "lane": None, "warning": f"Invalid path format: {path!r}"}
    folder = state_root(repo)
    if not folder.exists():
        return {"allowed": True, "owner": None, "lane": None}
    for active in read_claims(folder):
        if active.get("status") != "ACTIVE":
            continue
        for claimed_path in active.get("paths", []):
            if overlaps(normalized, claimed_path):
                owner = active.get("agent")
                # Allow if the requesting agent owns the claim
                if agent and owner == agent:
                    return {"allowed": True, "owner": owner, "lane": active.get("lane")}
                return {"allowed": False, "owner": owner, "lane": active.get("lane"), "path": claimed_path}
    return {"allowed": True, "owner": None, "lane": None}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("claim", help="Atomically reserve a lane and its files")
    c.add_argument("--agent", required=True)
    c.add_argument("--lane", required=True)
    c.add_argument("--paths", nargs="+", required=True)
    c.add_argument("--task", required=True)
    u = sub.add_parser("update", help="Publish current action and heartbeat")
    u.add_argument("--agent", required=True)
    u.add_argument("--lane", required=True)
    u.add_argument("--status", required=True)
    u.add_argument("--next", default="")
    r = sub.add_parser("release", help="Release only your own lane after handoff")
    r.add_argument("--agent", required=True)
    r.add_argument("--lane", required=True)
    sub.add_parser("status", help="Read current local claims")
    cp = sub.add_parser("check-path", help="Check if a path is claimed (for hooks)")
    cp.add_argument("path", help="Repo-relative path to check")
    cp.add_argument("--agent", default=None, help="Requesting agent ID (allowed if owner)")
    args = parser.parse_args(argv)
    try:
        if args.command == "claim":
            output = claim(args.root, args.agent, args.lane, args.paths, args.task)
        elif args.command == "update":
            output = update(args.root, args.agent, args.lane, args.status, args.next)
        elif args.command == "release":
            output = release(args.root, args.agent, args.lane)
        elif args.command == "check-path":
            output = check_path(args.root, args.path, args.agent)
        else:
            output = {"claims": read_claims(state_root(args.root))}
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"COLLAB_BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
