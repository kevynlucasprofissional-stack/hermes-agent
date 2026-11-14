"""Produce a ready-to-review P0 coordinator patch without touching active runtime.

Usage from checkout root:
    python workstation/context/multi-agent-collaboration-2026-10-25/reference/build_p0_patch.py

This builder refuses unexpected source drift. It writes ONLY beside itself.
"""
from __future__ import annotations

import difflib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ORIGINAL = ROOT / "workstation/scripts/multi_agent_coordination.py"
CANDIDATE = HERE / "multi_agent_coordination_p0.py"
PATCH = HERE / "multi_agent_coordination_p0.patch"


def replace_exact(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one exact match, found {count}; source drift, review manually")
    return text.replace(old, new, 1)


def main() -> None:
    original = ORIGINAL.read_text(encoding="utf-8")
    edited = original

    edited = replace_exact(
        edited,
        '        for active in read_claims(folder):\n            if active["lane"] == lane:',
        '        for active in read_claims(folder):\n'
        '            if not isinstance(active, dict) or not isinstance(active.get("lane"), str) or not isinstance(active.get("agent"), str) or not isinstance(active.get("paths"), list) or not active["paths"] or not all(isinstance(p, str) for p in active["paths"]):\n'
        '                raise RuntimeError("Incomplete or invalid claim: manual recovery required")\n'
        '            if active["lane"] == lane:',
        "claim rejects incomplete records",
    )

    original_block = '''def check_path(repo: Path, path: str, agent: str | None = None) -> dict:
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


'''
    revised_block = '''def check_path(
    repo: Path, path: str, agent: str | None = None, require_claim: bool = False
) -> dict:
    """Cooperative ownership admission; claim lifecycle is independent of status.

    Legacy mode (require_claim=False) permits unclaimed paths for staged rollout.
    Strict mode rejects unclaimed writes. Claims remain held until explicit release.
    Agent names are NOT authenticated identities; a later phase adds session tokens.
    """
    try:
        normalized = normalize_path(path)
    except ValueError as exc:
        return {"allowed": False, "reason": "INVALID_PATH", "error": str(exc)}
    try:
        records = read_claims(state_root(repo))
        for active in records:
            if not isinstance(active, dict) or not isinstance(active.get("lane"), str) or not isinstance(active.get("agent"), str) or not isinstance(active.get("paths"), list) or not active["paths"] or not all(isinstance(p, str) for p in active["paths"]):
                raise RuntimeError("Incomplete or invalid claim")
            for claimed_path in active["paths"]:
                normalize_path(claimed_path)
    except (OSError, ValueError, RuntimeError) as exc:
        return {"allowed": False, "reason": "REGISTRY_UNAVAILABLE", "error": str(exc)}
    matched = [
        (active, claimed_path)
        for active in records
        for claimed_path in active["paths"]
        if overlaps(normalized, claimed_path)
    ]
    if len(matched) > 1:
        return {"allowed": False, "reason": "CONFLICTING_CLAIMS"}
    if matched:
        active, claimed_path = matched[0]
        owner = active["agent"]
        if agent and owner == agent:
            return {"allowed": True, "owner": owner, "lane": active.get("lane")}
        return {
            "allowed": False, "reason": "OWNED_BY_OTHER_AGENT",
            "owner": owner, "lane": active.get("lane"), "path": claimed_path,
        }
    if require_claim:
        return {"allowed": False, "reason": "CLAIM_REQUIRED", "owner": None, "lane": None}
    return {"allowed": True, "owner": None, "lane": None}


'''
    edited = replace_exact(edited, original_block, revised_block, "replace check_path")

    edited = replace_exact(
        edited,
        '    cp.add_argument("--agent", default=None, help="Requesting agent ID (allowed if owner)")\n',
        '    cp.add_argument("--agent", default=None, help="Requesting agent ID (allowed if owner)")\n'
        '    cp.add_argument("--require-claim", action="store_true", help="Deny unclaimed paths (strict admission)")\n',
        "CLI strict flag",
    )
    edited = replace_exact(
        edited,
        '            output = check_path(args.root, args.path, args.agent)\n',
        '            output = check_path(args.root, args.path, args.agent, args.require_claim)\n',
        "CLI strict dispatch",
    )
    CANDIDATE.write_text(edited, encoding="utf-8")
    diff = "".join(difflib.unified_diff(
        original.splitlines(keepends=True),
        edited.splitlines(keepends=True),
        fromfile="a/workstation/scripts/multi_agent_coordination.py",
        tofile="b/workstation/scripts/multi_agent_coordination.py",
    ))
    PATCH.write_text(diff, encoding="utf-8")
    print(f"Created {CANDIDATE.name} ({len(edited.splitlines())} lines) and {PATCH.name}; original untouched")


if __name__ == "__main__":
    main()
