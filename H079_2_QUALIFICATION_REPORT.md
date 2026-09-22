# H-079.2 Qualification Report

Status: local qualification green; exact-final-head GitHub Actions and final upstream drift pending.

## Baseline and ancestry

- Starting downstream main: `964c13361e95a49e680deb2b16479d5f85c63011`
- Initially selected upstream pin: `118984d7a02f8a8baec11255002cbbab7c202e06`
- Final selected upstream pin after material drift: `afc3b7c6f397c6d21fd2c129ca17b18b544dd8dc`
- Merge-base before: `c1488ac947c9bc33fd65ec464548dc9d8edd6122`
- Ahead/behind before: 547 / 484
- Integration branch: `integration/upstream-20260920-118984d7-h0792`
- Upstream merge: `3d1c1875297529072b6e8b58cc1c2492d912e920`
- Merge parents: `2ce363292c...`, `118984d7a0...`
- Conflicts: `cron/jobs.py`, `hermes_cli/config.py`, `tests/plugins/test_kanban_dashboard_plugin.py`
- Resolution: preserve upstream model pins and current generic owners while retaining Workstation drift snapshots/config helpers; accept current upstream Kanban behavior.
- Ancestry proof: selected pin is ancestor of merge/candidate; behind selected pin is 0.
- Final upstream refresh merge: `fde9e51...` (second parent `afc3b7c6f3...`); conflicts in Cron editor and preview store were resolved by preserving model-policy semantics while adopting upstream opaque model choices and the upstream canonical profile-scoped preview owner.

## Seams and target fixes

- Strict seam audit: 18 classified, 0 unclassified, 0 budget regressions.
- Core integration dry-run: PASS.
- Remaining `REMOVE` seams: none newly introduced by H-079.2.
- Remaining first-party seams: the 18 registered entries in `workstation/first_party_seams.json`; no unregistered seam was added.
- Installer root cause: a supported uv-managed venv may intentionally have no pip, while the old installer equated valid venv with pip availability.
- Installer implementation: prefer `uv pip install --python`; otherwise probe pip, bootstrap via `ensurepip`, verify, then install. Existing interpreter validation now requires a Python-emitted marker.

## Installer matrix

- A — no `.venv`: PASS; real installer created Python 3.13 venv, installed Hermes via uv, ran npm lock install, imported `hermes_cli`, and preserved tracked source.
- B — existing venv + pip: PASS; reused Python 3.11 venv and completed editable pip install.
- C — existing pipless venv + uv: PASS; real `--without-pip` fixture reused, Hermes installed via uv, pip remained unnecessary, doctor passed.
- D — existing pipless venv without uv: PASS; uv was removed from PATH, `ensurepip --upgrade` created pip, pip probe and editable install succeeded.
- E — broken/incompatible venv: PASS; a non-Python `python.exe` fixture failed explicitly before dependency installation, without silently replacing the environment.
- F — checkout before/after: PASS for tracked content; user-owned untracked `workstation/dogfood/readme.md` was preserved and excluded.

## Verification and provider contracts

- H-077 negative ACK without `actual_delta`: PASS; ACK does not reset verified progress.
- H-077 positive `actual_delta=True`: PASS.
- Anthropic routing unit: PASS.
- Real installed Anthropic SDK construction, no network: PASS.

## Windows and Desktop closure

Root causes included POSIX-only real-filesystem/shell fixtures running on Windows, host-path assumptions, locale-sensitive copy, native-title policy, and a 5-second real-Git payload timeout below observed Windows cost. Fixtures were scoped by capability/platform while portable behavior remained asserted. The final upstream refresh replaced the downstream session-tab persistence seam with upstream's canonical profile-scoped preview owner.

- Full Workstation: 81 files, 742 passed, 0 failed, 2 skipped.
- Durable core seam regressions: 331 passed, 0 failed.
- Desktop typecheck: PASS.
- Desktop build: PASS.
- Desktop UI: 942 files, 8,592 passed, 1 skipped.
- Desktop Electron/platform: 215 files passed, 5 skipped; 2,453 tests passed, 40 skipped (bounded to 4 workers on the Windows host).
- H004: `H004_CLASSIFICATION=VALIDATED`.
- H013 sustained: 3/3; evidence accepted for 16 tasks, 300 requested rounds, 121,338 ms observed, 8 chat turns.
- Work100: 30 PASS, 0 COVERAGE_GAP, 0 NOT_RUN_ENVIRONMENT, 0 FAIL.
- Production dependency audit: 0 vulnerabilities.

## Promotion evidence

- GitHub Actions URLs: pending push/PR exact head.
- Final upstream drift: a 298-commit material delta was detected and adopted through `fde9e51...`; a fresh check is still required immediately before promotion.
- PR #43 canonical documentation: incorporated by authored cherry-picks; this report and the canonical H-079.2 document are the single candidate truth.

`READY_FOR_MAIN: NO` — exact-final-head required checks and final upstream drift are not yet complete.
