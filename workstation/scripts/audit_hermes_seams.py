#!/usr/bin/env python3
"""Audit Hermes -> Workstation integration seams.

H-078/H-078A does NOT pursue zero seams. The policy is:

- remove accidental coupling when generic Hermes contracts have full parity;
- upstream-abstract legitimate capability when the generic extension point is missing;
- preserve narrow first-party seams when privileged lifecycle/native integration is
  materially required.

The machine-readable policy is workstation/first_party_seams.json.

Examples:
    python workstation/scripts/audit_hermes_seams.py
    python workstation/scripts/audit_hermes_seams.py --json
    python workstation/scripts/audit_hermes_seams.py --strict
    python workstation/scripts/audit_hermes_seams.py --policy workstation/first_party_seams.json
    python workstation/scripts/audit_hermes_seams.py --write-baseline workstation/seam-baseline.json
    python workstation/scripts/audit_hermes_seams.py --check workstation/seam-baseline.json
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

CORE_ROOTS = ("agent", "tools", "hermes_cli", "gateway")
TOP_LEVEL_CORE = ("run_agent.py", "cli.py", "model_tools.py")
EDGE_ROOTS = ("apps/desktop",)
DEFAULT_POLICY = "workstation/first_party_seams.json"
DEFAULT_EXCLUDES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
}

VALID_DISPOSITIONS = {"REMOVE", "UPSTREAM_ABSTRACT", "PRESERVE_FIRST_PARTY"}


@dataclass(frozen=True, order=True)
class Seam:
    path: str
    line: int
    kind: str
    target: str

    @property
    def key(self) -> str:
        return f"{self.path}:{self.line}:{self.kind}:{self.target}"


def _python_imports(path: Path, root: Path) -> list[Seam]:
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return []

    rel = path.relative_to(root).as_posix()
    seams: list[Seam] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "workstation" or module.startswith("workstation."):
                seams.append(Seam(rel, node.lineno, "python_import", module))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "workstation" or alias.name.startswith("workstation."):
                    seams.append(Seam(rel, node.lineno, "python_import", alias.name))
    return seams


def _edge_references(path: Path, root: Path) -> list[Seam]:
    """Report Workstation references at product edges without declaring them violations."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    rel = path.relative_to(root).as_posix()
    seams: list[Seam] = []
    for idx, line in enumerate(text.splitlines(), 1):
        if "workstation" in line.lower():
            seams.append(Seam(rel, idx, "edge_reference", line.strip()[:180]))
    return seams


def _iter_files(root: Path, base: str) -> Iterable[Path]:
    target = root / base
    if not target.exists():
        return []
    if target.is_file():
        return [target]
    out: list[Path] = []
    for path in target.rglob("*"):
        if not path.is_file():
            continue
        if any(part in DEFAULT_EXCLUDES for part in path.parts):
            continue
        out.append(path)
    return out


def scan(root: Path) -> tuple[list[Seam], list[Seam]]:
    core: list[Seam] = []
    edges: list[Seam] = []

    for base in (*CORE_ROOTS, *TOP_LEVEL_CORE):
        for path in _iter_files(root, base):
            if path.suffix == ".py":
                core.extend(_python_imports(path, root))

    for base in EDGE_ROOTS:
        for path in _iter_files(root, base):
            if path.suffix in {".py", ".ts", ".tsx", ".js", ".jsx"}:
                edges.extend(_edge_references(path, root))

    return sorted(set(core)), sorted(set(edges))


def _load_policy(root: Path, policy_arg: str | None) -> tuple[Path | None, dict[str, dict]]:
    raw = policy_arg or DEFAULT_POLICY
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        return None, {}

    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"{path}: policy entries must be a list")

    by_path: dict[str, dict] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError(f"{path}: policy entry must be an object")
        seam_path = str(item.get("path") or "").strip().replace("\\", "/")
        disposition = str(item.get("disposition") or "").strip()
        if not seam_path:
            raise ValueError(f"{path}: policy entry is missing path")
        if disposition not in VALID_DISPOSITIONS:
            raise ValueError(
                f"{path}: {seam_path} has invalid disposition {disposition!r}; "
                f"expected one of {sorted(VALID_DISPOSITIONS)}"
            )
        if seam_path in by_path:
            raise ValueError(f"{path}: duplicate seam policy path {seam_path}")
        by_path[seam_path] = item
    return path, by_path


def _classified(core: list[Seam], policy: dict[str, dict]) -> tuple[list[dict], list[Seam], list[dict]]:
    grouped: dict[str, list[Seam]] = {}
    for seam in core:
        grouped.setdefault(seam.path, []).append(seam)

    classified: list[dict] = []
    unclassified: list[Seam] = []
    budget_regressions: list[dict] = []

    for path, seams in sorted(grouped.items()):
        rule = policy.get(path)
        if rule is None:
            unclassified.extend(seams)
            continue

        baseline_count = rule.get("current_direct_imports")
        current_count = len(seams)
        if isinstance(baseline_count, int) and current_count > baseline_count:
            budget_regressions.append(
                {
                    "path": path,
                    "rule_id": rule.get("id"),
                    "disposition": rule.get("disposition"),
                    "baseline_direct_imports": baseline_count,
                    "current_direct_imports": current_count,
                }
            )

        classified.append(
            {
                "path": path,
                "rule_id": rule.get("id"),
                "disposition": rule.get("disposition"),
                "current_direct_imports": current_count,
                "baseline_direct_imports": baseline_count,
                "target": rule.get("target"),
                "seams": [asdict(item) | {"key": item.key} for item in seams],
            }
        )

    return classified, sorted(unclassified), budget_regressions


def _payload(
    core: list[Seam],
    edges: list[Seam],
    policy_path: Path | None,
    policy: dict[str, dict],
) -> dict:
    classified, unclassified, regressions = _classified(core, policy)
    policy_only = [
        {
            "path": path,
            "rule_id": rule.get("id"),
            "disposition": rule.get("disposition"),
            "target": rule.get("target"),
        }
        for path, rule in sorted(policy.items())
        if not any(item.path == path for item in core)
    ]
    return {
        "schema": "hermes.workstation.seam-audit.v2",
        "policy": {
            "name": "minimum-necessary-first-party-seams",
            "path": str(policy_path) if policy_path else None,
            "principle": (
                "minimize accidental coupling without sacrificing proven Workstation "
                "capability, lifecycle, correctness or first-party UX"
            ),
            "dispositions": sorted(VALID_DISPOSITIONS),
        },
        "summary": {
            "direct_core_seams": len(core),
            "classified_core_seams": sum(item["current_direct_imports"] for item in classified),
            "unclassified_core_seams": len(unclassified),
            "budget_regressions": len(regressions),
            "edge_references": len(edges),
        },
        "classified_core": classified,
        "unclassified_core": [asdict(item) | {"key": item.key} for item in unclassified],
        "budget_regressions": regressions,
        "policy_entries_without_current_python_import": policy_only,
        "edge_references": [asdict(item) | {"key": item.key} for item in edges],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None, help="repository root (defaults to two parents above this script)")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--policy", default=None, metavar="PATH", help=f"seam policy (default: {DEFAULT_POLICY})")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail on unclassified direct core seams or direct-import growth beyond a registered baseline",
    )
    parser.add_argument("--write-baseline", metavar="PATH", help="write exact current core seam keys as a baseline")
    parser.add_argument("--check", metavar="PATH", help="fail when an exact core seam exists that is absent from baseline")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    core, edges = scan(root)

    try:
        policy_path, policy = _load_policy(root, args.policy)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"invalid seam policy: {exc}") from exc

    payload = _payload(core, edges, policy_path, policy)

    if args.write_baseline:
        target = Path(args.write_baseline)
        if not target.is_absolute():
            target = root / target
        target.parent.mkdir(parents=True, exist_ok=True)
        baseline = {
            "schema": "hermes.workstation.seam-baseline.v1",
            "core_seam_keys": [item.key for item in core],
        }
        target.write_text(json.dumps(baseline, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    exact_baseline_failure = False
    if args.check:
        target = Path(args.check)
        if not target.is_absolute():
            target = root / target
        try:
            baseline = json.loads(target.read_text(encoding="utf-8"))
            known = set(baseline.get("core_seam_keys", []))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"invalid seam baseline {target}: {exc}") from exc
        new = [item for item in core if item.key not in known]
        if new:
            exact_baseline_failure = True
            print("NEW EXACT HERMES -> WORKSTATION SEAMS:")
            for item in new:
                print(f"  {item.key}")

    strict_failure = False
    if args.strict:
        unclassified = payload["unclassified_core"]
        regressions = payload["budget_regressions"]
        if unclassified:
            strict_failure = True
            print("UNCLASSIFIED HERMES -> WORKSTATION SEAMS:")
            for item in unclassified:
                print(f"  {item['key']}")
        if regressions:
            strict_failure = True
            print("FIRST-PARTY SEAM BUDGET REGRESSIONS:")
            for item in regressions:
                print(
                    f"  {item['path']}: {item['current_direct_imports']} direct imports "
                    f"> registered baseline {item['baseline_direct_imports']} "
                    f"({item['disposition']})"
                )

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        s = payload["summary"]
        print(f"Direct core seams: {s['direct_core_seams']}")
        print(f"  classified: {s['classified_core_seams']}")
        print(f"  unclassified: {s['unclassified_core_seams']}")
        print(f"  budget regressions: {s['budget_regressions']}")
        for item in payload["classified_core"]:
            print(
                f"  {item['path']}: {item['current_direct_imports']} "
                f"[{item['disposition']}] {item.get('rule_id') or ''}".rstrip()
            )
        for item in payload["unclassified_core"]:
            print(f"  UNCLASSIFIED {item['path']}:{item['line']} -> {item['target']}")
        print(f"Edge Workstation references (reported, not violations): {s['edge_references']}")
        if args.strict and not strict_failure:
            print("Seam policy check passed: no unclassified core seams or budget growth.")
        if args.check and not exact_baseline_failure:
            print("Exact seam baseline check passed.")

    return 1 if strict_failure or exact_baseline_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
