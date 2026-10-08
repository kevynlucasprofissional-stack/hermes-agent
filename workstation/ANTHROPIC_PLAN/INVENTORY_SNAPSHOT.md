# Phase-0 Git tree census (all top-level directories)

**GitHub baseline:** `main@f21e803b3525b70ee6be2305e579c1cc1f930e74` on 2026-10-08.
**Method:** enumerate root with GitHub Contents API; fetch each of **30 directory Git Trees with `recursive=1`** by immutable SHA. All 30 returned `truncated=false`. This is a **metadata inventory, not evidence that all code has been read**.

- Git-tree blobs in directories: **16,093**
- Additional root-level `file` entries from Contents API: **97**
- **Total observed regular tracked file/blob entries across the 30 directories plus root: 16,190** (subject to the distinction between Contents `file` and Git Trees `blob` / symlinks)
- Subtree blob byte sum: **198,711,571** bytes (excludes root files; repository storage size is different and can include history)

| Root directory | Tracked blob entries | Git blob bytes |
| --- | ---: | ---: |
| `.github/` | 52 | 296,747 |
| `acp_adapter/` | 14 | 218,938 |
| `agent/` | 320 | 6,379,116 |
| `apps/` | 3,141 | 39,594,328 |
| `assets/` | 1 | 12,333 |
| `contributors/` | 1,498 | 32,717 |
| `cron/` | 33 | 802,931 |
| `docker/` | 18 | 63,450 |
| `evals/` | 214 | 1,301,246 |
| `gateway/` | 177 | 5,090,215 |
| `hermes_cli/` | 547 | 11,207,049 |
| `hermes_platform/` | 12 | 44,090 |
| `locales/` | 17 | 639,871 |
| `native/` | 5 | 711,418 |
| `nix/` | 18 | 400,741 |
| `optional-mcps/` | 65 | 88,818 |
| `optional-skills/` | 788 | 10,273,908 |
| `plugin-catalog/` | 242 | 179,360 |
| `plugins/` | 394 | 8,200,092 |
| `providers/` | 3 | 49,265 |
| `scripts/` | 87 | 1,640,476 |
| `skills/` | 331 | 3,075,508 |
| `tests-js/` | 16 | 96,746 |
| `tests/` | 5,002 | 48,512,510 |
| `tools/` | 337 | 6,861,771 |
| `tui_gateway/` | 95 | 1,788,865 |
| `ui-tui/` | 499 | 3,762,668 |
| `web/` | 207 | 2,712,220 |
| `website/` | 814 | 27,839,862 |
| `workstation/` | 1,146 | 16,834,312 |
| **30 directories total** | **16,093** | **198,711,571** |

## Interpretation
- A directory can be heavy in *tests*, vendored material, generated/static assets, sample skill packs or UI assets. The large number of entries must not be interpreted as 16,190 independent production source modules.
- This census proves only that all 30 root directory **tree indexes** were enumerated. **The contents of the 16k files were NOT read.** A full per-file manifest (`path/blob_sha/size/type/owner/license/review_status`) and semantic analysis are still pending.
- For an efficient source audit: recursively materialize manifests without duplicating assets, classify paths first, extract source symbol/import graphs, map high-risk effect owners to tests, then read code fully with cheaper models where change impact warrants it. Do **not** upload the whole repository or giant context files to Anthropic.
- Source Matrix repositories are entirely separate repos: this inventory does **not** cover them. External reference auditing requires exact pin/license and relevance-based source inspections.

## Highest-priority code surfaces for audit next
1. `workstation/` (1,146 blobs), especially `task_compiler`, `run_adoption`, `run_closure`, `experience_compiler`, `system1`, Control Plane, creative-planning docs and tests.
2. `apps/` (3,141 blobs), particularly desktop Electron/WebContentsView, IPC, renderer, voice safety, package workspaces and native E2E.
3. `agent/`, `tools/`, `gateway/`, `hermes_cli/`, `hermes_platform/` and `tests/` for integration authority and affected regressions.
4. `workstation/SOURCE_MATRIX.md` for external references after local ownership boundaries are reconciled.

## Remaining work
- [x] Git tree root coverage across all 30 root directories (no truncation)
- [ ] Root 97 file-by-file semantic classification; Git tree file-level SHA/size exports
- [ ] Classify 16,190 entries into source, tests, docs, vendor, generated, binary/assets, license and relevance
- [ ] Full domain-by-domain cheap-model source reading with owner and test dependency graph
- [ ] Reconcile all open PRs, release gates and baseline pin at final packet SHA
- [ ] Source Matrix reference coverage and prioritized code-to-code audits
- [ ] Evidence-grade task packets ready for frontier session

Do not change `NOT_REVIEWED` into `READ` without actual source examination.
