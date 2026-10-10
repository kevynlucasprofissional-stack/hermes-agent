# Engineering Journal — Dogfood-first gap audit and execution decision (2026-10-09)

**Classification:** INDEPENDENT STATIC/DOCUMENT AUDIT + MAINTAINER SOURCE REVIEW. **No implementation, build, runtime test, local Electron run, or exact-head CI was executed in this audit.** Reported user-local HyperFrames success is real-world user testimony, NOT independently inspected or contradicted. No claims of unchanged current status after this reference date.

## Hypothesis / falsification target

The architecture has real BrowserTask, ExperienceCompiler, hierarchical capability, Laya/System-1 and RunLocalAdopter owners, but may be unable to turn observed ordinary user activity into VERIFIED, reusable deterministic operations during a normal TaskRun. The human dogfood records define the required outcomes; unit tests alone cannot prove them.

**Source set:** all seven markdown files in `workstation/dogfood/`, plus provided full 2026-10-09 audit. Do not treat Obsidian workspace's list of other local files as repository content. The maintainer places maximum priority on original handwritten notes; preserve and cite their meaning without inventing execution evidence.

## Repository snapshot

- GitHub main at audit: `f21e803b3525b70ee6be2305e579c1cc1f930e74`.
- Candidate creative predecessor PRs #57–#61: draft, unmerged; PR #62 documents HyperFrames-first D-041 in `docs/creative-hyperframes-first-20261009`, draft/unmerged at audit. Code installed in the user's local Work was not found on accessible remote branches. **Preserve local WIP; locate and compare before modifying it.**
- Previous independent work: `context/LAYA_ADAPTIVE_AUTONOMY_AND_DURABLE_LEARNING_2026-10-08.md` (D-039 accepted/unimplemented) and `context/engineering-journal/h080b-real-use-experience-loop-audit-2026-09-23.md` (native browser real-run problems); avoid duplicating those decisions.

## Verified code facts and impact

1. `experience_compiler/compilability_monitor.py::process_event`: `mode != DIRECT` returns after shadow receipt, without calling `mine_candidate_in_run`/validation. The test `test_shadow_records_decisions_but_never_mines_validates_or_offers` explicitly asserts zero mining. **Gap:** D-039 desired observe/mine-even-with-effect-SHADOW. Correction must preserve no unqualified effects.
2. `resolve_policy` accepts any nonempty `direct_qualification_ref` when selecting DIRECT; later validation still enforces effects, so distinguish the **weak mode gate** from a proven execution bypass. Replace with code/model/schema/family/owner/version-bound verified attestation.
3. `schedule_event` sheds on queue full; `_get_window` evicts after 900s default; `stop` discards pending work; static limits 3 compile / 3 validation. **Gap:** missing durable opportunity preservation and evidence-revision retry, not a reason to remove CPU/memory caps.
4. `integrations/hermes/tool_observer.py` captures ordinary post-tool mutation as `uncertain` unless canonical verifier later upgrades. This is correctly conservative but may starve ExperienceCorpus without separate real acceptance post-effect evidence. **Gap:** show real owner readback/accepted samples rather than trust acknowledgements.
5. `run_local_adoption.py` and `run_adoption.py` already own the pre-reasoning checkpoint, item-scope authority and readback. **Retain**, do not introduce parallel adopter. Current positive tests use safe verifier/model doubles in parts; require one full product path.
6. `browser_controller.py`/broker + `agent/subagent_lifecycle.py` exist but combined subagent Browser Hub-visible native lifecycle is **unverified**. Mark as proof gap, not absent.
7. H-080B real-use notes document BrowserClaw detours, unneeded browser vision and INCONCLUSIVE learning samples. Browser readiness/expected URL readback is goal-proportionate for open-site; logged-in state is a separate predicate.
8. Creative predecessor #58 process ownership, #59 immutable SVG/project revisions and Electron PNG capture, #60 still-PNG MP4 verification, #61 Remotion TSX source are useful isolated code; they do **not** establish HyperFrames native editor lifecycle or animated export. Source D-041 is design, not merged implementation.

## Decision recorded: D-042 Dogfood as release/acceptance authority

**Accepted for documentation and implementation direction; code OPEN.** Give maintainer Dogfood requirements first-class traceable IDs and empirical native product gates; implement D-039 across main product with separate effect authority; produce opportunity ledger; prove native subagent BrowserTask and HyperFrames interactive shared-edit; assess lower-priority integrations without hijacking root owners. Remain under H-079 upstream-first and D-038 verified authority. Do not convert desired status into an implemented status.

## Directed implementation

Follow `../DOGFOOD_PRODUCT_GATE_2026-10-09.md` for ID-by-ID matrix and `../DOGFOOD_IMPLEMENTER_HANDOFF_2026-10-09.md` for staged file-level execution. Prioritize DF0 baseline/real local-worktree recovery; DF1 evidence capture and active mining; DF2 durable opportunity queue/recovery; DF3 attestation, isolated verifier and same-run adoption; DF4 native browser and delegated subagent parity; DF5 history/replay/site prep/recorder; DF6 real HyperFrames E2E; DF7 empirical dogfood and CI; DF8 optional backlog.

## Safety/negative criteria

No forged receipts, inferred `LOCAL_MUTATION`, privilege crossing, raw HTML creds, cloned browser owner, leaked profile, forced external BrowserClaw fallback on a bound native task, blind retries after uncertain side effects, hidden failing CI, fictional token savings or synthetic 8-billion-agent claims. A blocked item is documented with root cause and precise gate, not mislabeled DONE.

**Outcome of this journal entry:** evidence and implementation contract recorded only; all DF implementation gates remain OPEN unless independently demonstrated later.
