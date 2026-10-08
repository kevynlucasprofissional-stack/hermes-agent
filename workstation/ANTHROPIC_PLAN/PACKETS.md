# Frontier task packets — source-ready handoff contract

## File convention
Create one file per selected intervention: `PACKET-Fxx-short-name.md`; place only after complete cheap-model preparation and branch/hash confirmation. Each packet should let a premium coder make a bounded patch immediately with minimal browsing and zero architecture archaeology.

## Mandatory packet schema
```markdown
# PACKET F-XX — narrow executable outcome
STATUS: READY | BLOCKED | STALE | EXECUTED | VERIFIED
SOURCE: repo@immutable_40_char_sha / upstream_pin@sha / branch / open PR collisions
MODEL: Opus 5.5 initially; Fable 5.1 only with justification
MAX_SPEND: USD amount; MAX_CALLS: int; MAX_OUTPUT: token cap
GOAL: one falsifiable behavior; explicitly what NOT to implement
ROOT_CAUSE: confirmed source+test evidence, not hypothesis
CURRENT_IMPLEMENTATION: precise files::symbols and relevant line-bounded excerpt (or separate bounded code appendix)
TASK: ordered edit operations with exact target signatures/schema/return/errors
EXISTING_OWNERS: authority, execution, persistence, renderer and readback
CONTRACTS_AND_INVARIANTS: effect/permission, version, tenant, retries, integrity, consent
REFERENCES: immutable source snippets + licensing; do not vendor by default
INPUTS / EXPECTED_OUTPUTS: exact shape, fixtures and example
RED_TESTS: tests to add and command; failing before edit
GREEN_TESTS: focused + regressions; Electron/CI E2E if needed
NEGATIVE_CONTROLS: at least revoked scope, missing verifier, duplicate effects, stale revision or relevant failures
ROLLBACK: one command/commit and no destructive user state migration
DONE: exact evidence and actual required CI; otherwise label BLOCKED
STOP: missing owner signature, SHA drift, code divergence, external auth, unsafe effect, cost exceeded
OUTPUT_FORMAT: git diff/commit + evidence table, not narrative dump
```

## Prompt stub to embed in a READY packet
"Implement only the bounded change described here. Apply the listed RED→GREEN sequence, edit only the allowed files, reuse existing canonical owners, do not invent receipts or authority, and produce exact diff plus tests/remaining blockers. All architectural and research context has already been compiled. Before editing, verify frozen commit, actual changed-file signatures, and test commands. If packet contradicts checked source or a mandatory gate is red, STOP and return a compact missing-evidence report; do not initiate a repository-wide read."

## Seed packet backlog (these are NOT READY)
- `F-01`: D-039 scoped autonomous learning (A0–A7); extract true main signatures from `compilability_monitor.py`, `compilability_validation.py`, `run_adoption.py`, `ExperienceCorpus`, `lifecycle.py`, `TaskCompiler`, `ArtifactStore`; include replay fail-closed and multi-run restart/queue/TTL tests.
- `F-03`: single H-079 Stage A **semantic conflict**, only once generated conflict map, pinned source, behavior/tests and selected subsystem are available; do not assign entire multi-thousand-commit merge to Fable.
- `F-04`: minimal creative capability/project contract, maps existing `AppResolver`, ProcessRegistry, BrowserTask, TaskCompiler, Journal/ArtifactStore and typed discovery/permission/revision safeguards; requires CW-01 GO.
- `F-05`: real Electron React/SVG→PNG vertical with native readback, editable source and tenant/version safety. Gate on prior CW-02 and E2E environment.

## Compression rules
- Prefer source signature and 30–150 relevant lines over whole module; include caller and exact test assertion to preserve causality.
- Include precise source/line/commit provenance in the packet and offline appendix. Never claim snippets are fresh after branch movement.
- A packet may need more context than 4k tokens to be safe; correctness outranks minimal text.
- Avoid reexplaining the entire Hermes architecture in each packet; retain a stable 10-line invariant header.
