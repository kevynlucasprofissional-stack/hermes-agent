#!/usr/bin/env python3
"""Audit direct Hermes-core -> Workstation coupling.

This utility supports H-078 (Upstream Migration as Decoupling). It is intentionally
read-only unless --write-baseline is supplied. The migration goal is monotonic: direct
imports from generic Hermes core into Workstation should shrink, while edge adapters may
remain explicit and documented.

Examples:
    python workstation/scripts/audit_hermes_seams.py
    python workstation/scripts/audit_hermes_seams.py --json
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
DEFAULT_EXCLUDES = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
}


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
    """Report Workstation references at product edges without treating them as core violations."""
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


def _payload(core: list[Seam], edges: list[Seam]) -> dict:
    return {
        "schema": "hermes.workstation.seam-audit.v1",
        "policy": {
            "core_direction": "generic Hermes core must progressively stop importing workstation",
            "edge_direction": "explicit product adapters are reported but not automatically violations",
        },
        "core_seams": [asdict(item) | {"key": item.key} for item in core],
        "edge_references": [asdict(item) | {"key": item.key} for item in edges],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None, help="repository root (defaults to two parents above this script)")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--write-baseline", metavar="PATH", help="write current core seam keys as a baseline")
    parser.add_argument("--check", metavar="PATH", help="fail only when a core seam exists that is absent from baseline")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    core, edges = scan(root)
    payload = _payload(core, edges)

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
            print("NEW DIRECT HERMES -> WORKSTATION SEAMS:")
            for item in new:
                print(f"  {item.key}")
            return 1

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"Direct core seams: {len(core)}")
        for item in core:
            print(f"  {item.path}:{item.line} -> {item.target}")
        print(f"Edge Workstation references (reported, not failed): {len(edges)}")
        if args.check:
            print("No new direct core seams relative to baseline.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
