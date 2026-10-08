# Phase-0 tracked Git-tree snapshot (partial directories)
**Main tree:** `f21e803b3525b70ee6be2305e579c1cc1f930e74`. **Method:** GitHub Git Trees API, recursive by subtree SHA, read-only. Source directory enumeration from GitHub Contents API. Counts below describe blob entries, **not files read semantically**.
**Coverage:** 12 surveyed root directories. The repository has **30 root directories** and **97 root files**; 18 directory trees are **NOT YET SURVEYED** in this file. No audited subtree returned `truncated=true`.

| Root directory | Tracked blob entries | Sum of blob bytes |
| --- | ---: | ---: |
| `.github` | 52 | 296,747 |
| `agent` | 320 | 6,379,116 |
| `apps` | 3,141 | 39,594,328 |
| `assets` | 1 | 12,333 |
| `evals` | 214 | 1,301,246 |
| `gateway` | 177 | 5,090,215 |
| `hermes_cli` | 547 | 11,207,049 |
| `hermes_platform` | 12 | 44,090 |
| `native` | 5 | 711,418 |
| `tests` | 5,002 | 48,512,510 |
| `tools` | 337 | 6,861,771 |
| `workstation` | 1,146 | 16,834,312 |
| **Surveyed only** | **10,954** | **136,845,135** |

Scope caution: `apps/` contains generated/images and other assets; `tests/` is not production code; `workstation/` contains vendored/external material. Git tree inventory must be followed by classification, SHA manifest, semantic source review and test-path mapping. Counting a file is NOT equivalent to understanding it.

**Outstanding 18 roots:** `acp_adapter/`, `contributors/`, `cron/`, `docker/`, `locales/`, `nix/`, `optional-mcps/`, `optional-skills/`, `plugin-catalog/`, `plugins/`, `providers/`, `scripts/`, `skills/`, `tests-js/`, `tui_gateway/`, `ui-tui/`, `web/`, `website/`. Also inspect all 97 root-level files and git submodule pointers where applicable.

Next reproducible preparation step: loop through remaining subtree SHAs in small, rate-limited batches, materialize a per-path manifest with `path,type,blob_sha,size,owner_domain,generated/vendor/license,test_links,review_status`, then build module and test dependency graph. The current session has **not** performed this full inventory.
