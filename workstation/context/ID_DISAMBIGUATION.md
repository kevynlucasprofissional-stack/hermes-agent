# Identifier disambiguation index

**Status:** canonical index, established 2026-09-20.
**Scope:** the `H-*` hypothesis/experiment identifiers used by the engineering journal and the
`KI-*` / `RI-*` identifiers used by `KNOWN_ISSUES.md`.

## Why this file exists

The journal and the known-issues registry were written incrementally across many cycles, and
several numbers were **reused for unrelated work**. A reader who resolves `H-047` or `KI-008` by
number alone will land on the wrong subject roughly half the time, and the cross-references inside
the journal do not always say which series they mean.

This file does not renumber anything. Historical records are evidence: rewriting an identifier
would orphan the references listed below and would make past evidence reports unverifiable.
Instead, each collision is mapped here, and readers should resolve an ambiguous identifier
**through this index** rather than by first match.

Citations below are **by heading text, not by line number**, because line numbers shift whenever a
document above them is edited. The journal is newest-first, so in a collision the *lower* line
number is the *later* entry.

## Numbering conventions

- `H-nnn` — journal hypotheses/experiments, in `context/engineering-journal/CURRENT.md`.
- `KI-nnn` — known issues, in `context/KNOWN_ISSUES.md`.
- `D-nnn` — architectural decisions, in `context/DECISIONS.md`.
- `RI-nnn` — repository-integrity findings, same registry as `KI-*`.

Sub-identifiers exist and are **not** colliding: `AEPC-E001`/`AEPC-E002`, `EC0..EC8`,
`G-001`/`G-002`, `WP-01`/`WP-02`, `CT-001..CT-007`, `RT-001..RT-012`, `E-001..E-022`,
`BOR-E001..E005`, `H072-E001..E005`.

`CURRENT.md` and the top level of `KNOWN_ISSUES.md` are written **newest-first**; `DECISIONS.md` is
not — see the ordering section below.

## H-series collisions

`H-046` … `H-051` and `H-054` are each used by **two different series**, both live in `CURRENT.md`.

**Series A — the later series** (higher in the file). Capability/product lanes registered from
2026-09-14 onward:

| ID | Heading |
|---|---|
| `H-046` | `## H-046 — Chrome Web Store support is not yet an agentic capability boundary` |
| `H-047` | `## H-047 — Hermes Vault: Local-First Agentic PKM Subsystem (Obsidian-Compatible Knowledge Core)` |
| `H-048` | `## H-048 — Hybrid Kanban must extend canonical Kanban without inheriting Agentic status semantics` |
| `H-049` | `## H-049 — Workstation Browser Automation Ergonomics: Input Hygiene, Proactive Human Handoff, Canvas Awareness, and Batch Extraction` |
| `H-050` | `## H-050 — Durable execution routing / reference boundary (2026-09-16)` |
| `H-051` | `## H-051 — Final durable execution hardening (2026-09-16)` |
| `H-054` | `## H-054 — Corpus hardening audit: retain only gaps reproducible on current main` |

**Series B — the earlier series** (lower in the file). The 2026-09-12 H013 sustained-load and
clean-install evidence track:

| ID | Heading |
|---|---|
| `H-046` | `## H-046 — Shared Desktop viewport geometry is host-aware` |
| `H-047` | `## H-047 — H013 sustained Desktop/Browser load expansion` |
| `H-048` | `## H-048 — H013 formatted rerun and final process cleanup` |
| `H-049` | `## H-049 — Parametric H013 production-load profile` |
| `H-050` | `## H-050 — H013 scaled evidence report and release assertion` |
| `H-051` | `## H-051 — Full configured H013 candidate-profile local run` |
| `H-054` | `## H-054 — Clean-install evidence must name the isolated Workstation home` |

Also in the older block, but **not reused** anywhere in the journal, so unambiguous: `H-052`
(H013 full resource/event projection parity) and `H-053` (Clean-machine install and doctor profile
isolation), plus `H-055` … `H-061` (clean-install / H013 release-evidence hardening).

Non-colliding journal ranges: `H-001..H-012` (Implementation 4 / WP-01 browser session state),
`H-013..H-045` (V3), `H-062..H-079` (2026-09-16 onward).

## Cross-document collision: `H-053`

Unlike the series collisions above, this one spans documents:

| Meaning | Where |
|---|---|
| Clean-machine install and doctor profile isolation | journal: `## H-053 — Clean-machine install and doctor profile isolation` |
| Hybrid Kanban Real-time Invalidation & Full Lifecycle | `CURRENT_STATE.md` bullet `- **Hybrid Kanban Real-time Invalidation & Full Lifecycle (H-053)**:` and `HERMES_WORKSTATION_INTELLIGENCE.md` § `### 15.6. H-053: Kanban híbrido em tempo real` |

Resolve by document: inside the journal, `H-053` is the clean-install audit; inside
`CURRENT_STATE.md` and `HERMES_WORKSTATION_INTELLIGENCE.md`, it is the Hybrid Kanban real-time
slice.

## KI-series collisions

`KNOWN_ISSUES.md` contains **two numbering scopes**: the file-level registry (`##` headings,
newest-first from the top) and a self-contained closing section (`###` headings) that restarts its
own numbering.

### File-level registry (`##` headings)

| ID | Title | State |
|---|---|---|
| `KI-016` | Post-H-076/H-077 false-confidence residuals can still overstate operational truth | IMPLEMENTED — exact-head CI pending |
| `KI-015` | "Verified" could encode correlated, stale or under-specified evidence | RESOLVED — H-076 |
| `KI-014` | Verified adaptive procedure stays in the LLM loop instead of handing off in-flight | RESOLVED — H-075 |
| `KI-013` | Operational knowledge hierarchy is not closed end to end | RESOLVED — H-075 |
| `KI-012` | Browser ownership/recovery residual gaps after first corrective implementation | REOPENED — 2026-09-19 |
| `KI-011` | Durable compiler can obstruct stateful native-browser work | CORRECTIVE IMPLEMENTED — exact-head CI pending |
| `KI-012` | Upstream-derived ownership/resync/Kanban/recovery gaps | RESOLVED IN WORK P0 HARNESS — 2026-09-18 |
| `KI-002` | Preview and Workstation Browser are separate browser lanes | — |
| `KI-004` | Native browser surface can overlap another Desktop pane | — |
| `KI-006` | Broad Windows Desktop suites contain pre-existing portability/test failures | RESOLVED |
| `KI-007` | `Session not found` / exported `session: null` | NOT_REPRODUCED |
| `KI-008` | V3 product-level acceptance evidence is still open | OPEN |

**`KI-012` is duplicated even inside this scope**: the reopened browser-ownership issue and the
2026-09-18 upstream-derived issue are unrelated subjects. Note the collision is not only across
scopes but *within* one scope.

### Under `## Resolved regression classes`

These use `###` headings and continue the file-level numbering (they are **not** a restart):

| ID | Title |
|---|---|
| `KI-010` | Vault paths were contained only after write |
| `KI-003` | Complete logical BrowserSessionState did not survive restart |
| `KI-005` | BrowserTask lifecycle was implicit on pre-Implementation-4 `main` |
| `KI-001` | Desktop Browser capability could disappear from the model schema |
| `RI-001` | Normal Workstation install rewrote tracked source before validation |

### `## Canonical Work Loop Reliability Gaps — RESOLVED (2026-09-17)`

This closing section **restarts numbering**. Its identifiers do **not** denote the file-level
issues of the same name:

| ID | Title |
|---|---|
| `KI-007` | Stale run late completion could corrupt task state |
| `KI-008` | Terminal parents left live descendants |
| `KI-009` | Missing canonical lineage across WorkPlans and reports |
| `KI-010` | O(N²) ExecutionJournal append scaling degradation |

So `KI-008` alone denotes **three** distinct subjects: the open V3 acceptance-evidence gap, the
resolved terminal-parents gap, and — per the journal references below — a clean-machine /
full-duration evidence gate. Likewise `KI-009` denotes both the resolved packaged-GUI issue and
the resolved canonical-lineage gap.

## `DECISIONS.md` ordering

`DECISIONS.md` is read **ascending by decision number** (`D-001` … `D-032`) with a "Reading this
file" note at the top. This was repaired on 2026-09-20: `D-028`, `D-029` and `D-030` had been
prepended above `D-001`. `D-031` and `D-032` were subsequently appended in canonical order. New decisions are **appended**, not prepended.

## Cross-reference register

Ambiguous identifiers referenced elsewhere. The right-hand column is the series/section the
reference means, as established from context.

| Reference | Means |
|---|---|
| journal: `Origin: H-053 install/doctor profile isolation audit` | H-series **series B** |
| journal: `Origin: H-054 clean-install evidence contract hardening` | H-series **series B** |
| journal: `regression after H-053 through H-055 release-evidence changes` | H-series **series B** |
| journal: `Origin: H-051/H-050 candidate-load report audit` | H-series **series B** |
| journal: `Origin: H-050 report-based scaled-load gate` | H-series **series B** |
| journal: `Origin: H-049 scaled-load gate hardening` | H-series **series B** |
| journal: `the 36.6s run in H-047 remains valid prior-run evidence` | H-series **series B** |
| journal: `Origin: KI-008 current-client parity evidence boundary` | KI file-level (V3 acceptance) |
| journal: `Origin: KI-008 clean-machine release evidence audit` | KI file-level (V3 acceptance) |
| journal: `Origin: KI-008 full-duration/production-scale Desktop/Browser evidence gate` | KI file-level (V3 acceptance) |
| `PATCH_MANIFEST.md`: `H-021/KI-009 remain resolved` | KI file-level (packaged GUI) |
| `CURRENT_STATE.md`: "KI-009 is resolved: the packaged Desktop GUI Playwright smoke passes" | KI file-level (packaged GUI) |
| `OPERATIONAL_GUIDELINES.md`: "tensão de 86 itens (`H-050` / ChatGPT-…)" | **Unresolved** — matches neither `H-050` entry cleanly; do not assume |

## Rules going forward

1. **Never reuse a retired number.** Take the next unused identifier in the series: `H-080` and
   above in the journal, `KI-017` and above in the known-issues registry. Old series are not
   available for recycling even where an entry is closed.
2. New journal hypotheses are **appended above** existing ones (`CURRENT.md` is newest-first);
   new decisions are **appended below** existing ones (`DECISIONS.md` is ascending).
3. When citing an ambiguous identifier in a new document, qualify it: write
   `H-047 (series B, H013 load)` or `KI-008 (V3 acceptance)`, so the reference survives without
   this index.
4. Cite by heading text, not line number, wherever the identifier is ambiguous.
5. If a new collision is created despite rule 1, record it here in the same change.

Canonical related documents: [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md),
[`engineering-journal/CURRENT.md`](engineering-journal/CURRENT.md),
[`DECISIONS.md`](DECISIONS.md).
