# Creative development exception — 2026-10-08

The maintainer explicitly authorized proceeding with implementation after asking
whether the outstanding baseline issues could be recorded as unresolved. The
answer described a development-only exception, and the maintainer replied:
“Está autorizado”. This exception applies to the current Creative development
lane, beginning with CW-02 on branch `codex/creative-cw02-20261008`, based on
`3417d57b5c6dc3b3303052fa0fb34659dfc0e5fe`.

This supersedes the earlier checkpoint's blanket prohibition on starting target
development. It does not qualify the baseline, resolve conflicts, authorize a
main merge, or waive execution authority, isolation, license or output verification.

| Outstanding item | Disposition |
| --- | --- |
| Fixed upstream pin adoption / 56 semantic conflicts | NOT RESOLVED |
| Combined exact-head baseline CI and native release proof | NOT RESOLVED |
| Worktree locked Python environment / Laya provenance failures | NOT RESOLVED |
| KI-024 input authority and KI-025 startup | NOT RESOLVED; preserve existing controls, assess applicability per operation |
| H-080B.3 empirical native proof | NOT RESOLVED |

CW-01 remains not qualified. CW-02 implementation may proceed under this explicit
exception; qualification and promotion must report these gaps independently.
Existing evidence is retained; no failure is relabeled as passing.

Initial implementation: opt-in passive executable discovery through the existing
RuntimeCapabilityRegistry and hermes_platform resolver. Version and health remain
not checked. No engine is installed or launched by discovery. Process lifecycle,
admission and Creative UI integration remain subsequent implementation work.
