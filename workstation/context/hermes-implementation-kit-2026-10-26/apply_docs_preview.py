#!/usr/bin/env python3
"""Preview append-only updates. NEVER checks external agent claims.

Only the authorized doc owner may use --apply after verifying project/claims.
Refuses tracked, locally modified target files to avoid overwriting WIP.
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path
import os

PACKET = Path(__file__).resolve().parent
MAP = {
    'updates/ROADMAP.md': 'workstation/ROADMAP.md',
    'updates/HERMES_WORKSTATION_INTELLIGENCE.md': 'workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md',
    'updates/engineering-journal-CURRENT.md': 'workstation/context/engineering-journal/CURRENT.md',
    'updates/DECISIONS.md': 'workstation/context/DECISIONS.md',
    'updates/KNOWN_ISSUES.md': 'workstation/context/KNOWN_ISSUES.md',
}
MARKER = '<!-- HERMES-WORK-PLAN-20261026:PLAN_ONLY -->'


def validate_repo(repo: Path) -> None:
    proc = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--show-toplevel'],
                          capture_output=True, text=True, check=True)
    if Path(proc.stdout.strip()).resolve() != repo.resolve():
        raise RuntimeError('repo must point to Git toplevel')
    if repo.name != 'hermes-agent' or not (repo / 'workstation' / 'ROADMAP.md').is_file():
        raise RuntimeError('not the expected Hermes checkout')


def dirty(repo: Path, relative: str) -> bool:
    result = subprocess.run(['git', '-C', str(repo), 'status', '--porcelain', '--', relative],
                            capture_output=True, text=True, check=True)
    return bool(result.stdout.strip())


def stage_text(existing: str, appendix: str) -> str:
    if MARKER in existing:
        return existing
    newline = '\r\n' if '\r\n' in existing else '\n'
    addition = '\n\n' + MARKER + '\n\n' + appendix.rstrip() + '\n'
    return existing.rstrip('\r\n') + addition.replace('\n', newline)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--apply', action='store_true', help='opt-in AFTER current claim verified manually')
    parser.add_argument('--claims-reviewed', action='store_true', help='affirm exact doc ownership/claims')
    args = parser.parse_args()
    repo = args.repo.resolve()
    validate_repo(repo)
    if args.apply and not args.claims_reviewed:
        parser.error('--apply requires --claims-reviewed (manual real verification, not asserted by tool)')

    blocked = []
    pending = []
    for src, dest in MAP.items():
        target = (repo / dest).resolve()
        if not target.is_relative_to(repo):
            raise RuntimeError('outside checkout')
        if not target.is_file() or target.is_symlink():
            raise RuntimeError(f'not a regular tracked target: {dest}')
        content = target.read_text(encoding='utf-8-sig')
        append = (PACKET / src).read_text(encoding='utf-8')
        if MARKER in content:
            print(f'SKIP already tagged: {dest}')
            continue
        if dirty(repo, dest):
            blocked.append(dest)
            print(f'BLOCKED existing WIP: {dest}; manually merge by doc owner')
            continue
        pending.append((target, stage_text(content, append)))
        print(f'{"APPLY" if args.apply else "PREVIEW"} append: {dest}')
    if blocked and args.apply:
        print('NO WRITE: one or more target docs are dirty. Preserve owner work.')
        return 2
    if args.apply:
        for target, new_text in pending:
            fd, fname = tempfile.mkstemp(prefix='.hermes-doc-', dir=str(target.parent))
            try:
                with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
                    f.write(new_text)
                os.replace(fname, target)
            finally:
                if os.path.exists(fname):
                    os.unlink(fname)
        print('Appended to clean, permitted paths. Run git diff; NOT release-qualified.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
