# Source reuse matrix

This file is the canonical intake registry for external projects, papers, benchmarks and implementation patterns that may help Hermes Work.

Canonical split of responsibility:
- `SOURCE_MATRIX.md` records **what should be studied and why**.
- `ROADMAP.md` records **when and how that study becomes executable work**.
- `context/REFERENCE_CODE_TO_CODE_AUDIT_2026-09-23.md` defines the evidence protocol for the deep code-to-code dogfood audit.

## Interpretation rules

1. A row is a **research lead**, not an adoption decision.
2. README/paper claims are discovery evidence. Code-level claims require an exact repository/ref plus file, symbol, test or executable receipt.
3. Use `FACT`, `PARTIAL` and `NV` (not verified). `NV` must never be rewritten as `absent`.
4. Do not copy external code until repository identity, exact ref, license, file headers and relevant dependency licenses are checked.
5. Prefer adapting invariants/contracts over importing a framework when Hermes already owns the lifecycle/state boundary.
6. External popularity or benchmark rank is never architecture authority. Findings must survive Hermes constraints, D-025 external-validity discipline and the normal upstream/change gates.
7. If a reference is learned from historical research but its current repository identity cannot be pinned, keep it as research debt rather than inventing a slug.

## Decision vocabulary

- **KEEP + MODIFY MINIMALLY** — first-party/base component remains an owner.
- **ADAPT CODE/PATTERNS** — selected implementation techniques may be ported after license and code audit.
- **ADAPT IDEA/CONTRACT** — copy the invariant/interface idea, not the implementation.
- **KEEP EXTERNAL** — useful backend/tool, but not a Workstation owner.
- **REFERENCE** — study architecture/UX/reliability patterns.
- **REFERENCE/EVAL** — use as an evaluation or falsification reference.
- **BENCHMARK CANDIDATE** — compare code-to-code before any adoption decision.
- **DO NOT INTEGRATE** — intentionally outside the architecture.

## Existing Browser / Workstation references

| Project | Decision | V1/current use |
|---|---|---|
| NousResearch/hermes-agent | **KEEP + MODIFY MINIMALLY** | Core/Gateway/Desktop/Dashboard/Kanban remain the base/reference reasoner; downstream semantics stay explicit |
| abundantbeing/hermes-browser-extension | **ADAPT PROTOCOL/SAFETY, DO NOT VENDOR WHOLE APP** | Fail-closed binding, leases/reconnect and safety reference; extension remains optional compatibility lane |
| browser-use/desktop | **ADAPT CODE/PATTERNS** | `WebContentsView` lifecycle/background/session patterns |
| browser-use/browser-harness | **KEEP EXTERNAL** | Existing Hermes `browser_exec` power path |
| vercel-labs/agent-browser | **KEEP EXTERNAL** | Deterministic browser fallback/reference |
| browser-use/browser-use | **KEEP EXTERNAL + BENCHMARK** | Adaptive browser backend already integrated by Hermes; compare observation/action efficiency with native Browser |
| browserbase/stagehand | **BENCHMARK CANDIDATE + ADAPT IDEA/CONTRACT** | High priority: deterministic vs model-mediated browser operations, self-healing, compact page context/token efficiency, drift-triggered intelligence |
| browser-memory/browser-memory | **ADAPT IDEA/CONTRACT** | Procedural/browser memory reference |
| apatureai/lattice | **ADAPT IDEA/CONTRACT** | Compact perception/provenance reference |
| aaronlab/browsertrace | **REFERENCE** | Execution journal/replay UX |
| EricFinland/witness | **REFERENCE** | Event/evidence/cost tracing |
| VasuBansal7576/driftlock | **REFERENCE** | Drift vs regression recovery |
| lamenting-hawthorn/browserbench | **REFERENCE/EVAL** | Exactly-once transaction safety |
| visnia-ai/browsewebapp-bench | **REFERENCE/EVAL** | Realistic browser task suite |
| visnia-ai/browser-agent | **BENCHMARK CANDIDATE** | Compare efficiency/reliability; not a core runtime owner |
| browser-use/browsercode | **REFERENCE** | Script-per-call / Power Mode reference |
| browseros-ai/BrowserOS | **UX REFERENCE ONLY** | Study browser-agent UX/ownership; do not copy incompatible code by assumption |
| Browser4 | **FUTURE EXTERNAL BACKEND / IDENTITY VERIFY** | Bulk crawl/extraction only if audit/benchmark justifies it |
| VibeSurf | **REFERENCE / IDENTITY VERIFY** | Workflow/preview ideas; avoid agent-in-agent coupling |
| Sabrina/openclaw-ai-browser | **REFERENCE** | Brain/Hands separation, risk gates, journal |
| nesquena/hermes-webui | **DO NOT INTEGRATE** | Official Desktop + Dashboard already own UI/state/LAN |

## Agent harness / durable-runtime references

| Project | Decision | V1/current use |
|---|---|---|
| openclaw/openclaw | **BENCHMARK CANDIDATE** | Gateway/runtime, device/channel integration, state/memory, automation, browser/nodes, recovery and long-lived ownership |
| bytedance/deer-flow | **BENCHMARK CANDIDATE** | Long-horizon harness, subagents, memory, sandboxes, skills, recovery and research workflow |
| All-Hands-AI/OpenHands | **BENCHMARK CANDIDATE** | Agent server/runtime, workspace/event model, recovery, browser/computer interaction, automation and protocol boundaries |
| FoundationAgents/OpenManus | **REFERENCE + BENCHMARK CANDIDATE** | Agent -> Flow -> Tool decomposition, planning-flow ownership and simple harness structure |
| deepseek-ai/deepseek-harness | **BENCHMARK CANDIDATE** | High priority harness modularity: plugin kernel, models/tools/skills/sessions/sandboxes/storage/loops/scheduling/UI |
| BAAI-Agents/Cradle | **REFERENCE** | General computer control, self-improvement and skill curation under multimodal interaction |
| langchain-ai/langgraph | **REFERENCE** | Graph/state orchestration, resumability/checkpointing and compositional execution patterns |

## Experience Compiler / self-improving-agent references

| Project | Decision | V1/current use |
|---|---|---|
| DEFENSE-SEU/FlowEvo | **BENCHMARK CANDIDATE** | Highest-priority Experience Compiler comparison: successful trace -> executable skill, direct replay vs skill-conditioned workflow vs planning, curation/negative-transfer suppression |
| HKUST-KnowComp/rethinkskill | **REFERENCE/EVAL + BENCHMARK CANDIDATE** | Multi-round skill evolution; success/failure feedback, validation/test/robustness/transfer disagreement |
| amazon-science/Self-Evolving-Agents-Double-Ratchet | **REFERENCE/EVAL + BENCHMARK CANDIDATE** | Co-evolving skill library and evaluator; direct comparison for `who grades the grader?` and anti-Goodhart design |
| amazon-science/Self-Evolving-Agents-Ratchet | **REFERENCE/EVAL + BENCHMARK CANDIDATE** | Skill lifecycle, library drift, retirement/rollback and non-divergence hygiene |
| RichmondAlake/memorizz | **BENCHMARK CANDIDATE** | MemoRizz/Memorizz workflow memory -> skills, promotion, shadow evaluation and demotion; verify exact version/ref before comparison |
| Qwen-Applications/Trace2Skill | **BENCHMARK CANDIDATE** | Trace-local lesson extraction, multi-analyst patch proposal and conflict-free skill consolidation |
| zorazrw/agent-workflow-memory | **REFERENCE + BENCHMARK CANDIDATE** | Offline/online workflow induction from prior experience; workflow abstraction for web tasks |
| aiming-lab/SkillRL | **REFERENCE** | Hierarchical reusable skill discovery and recursive skill-augmented learning |
| MineDojo/Voyager | **REFERENCE** | Executable skill library learned from environment feedback; useful baseline for what Hermes verification/provenance should add |

## Evaluation / falsification references

| Project / benchmark | Decision | V1/current use |
|---|---|---|
| SWE-bench / SWE-bench Verified / SWE-Bench Pro | **REFERENCE/EVAL** | Benchmark-quality failure modes, hidden-oracle discipline, underspecification/test-quality caution; pin exact datasets/versions before use |
| OSWorld | **REFERENCE/EVAL** | Computer-use task coverage and external outcome evaluation; exact repo/version must be pinned by the audit |
| WebArena / Mind2Web | **REFERENCE/EVAL** | Web task generalization/workflow-memory comparison; use only with exact benchmark/version receipts |
| Playwright | **REFERENCE/ORACLE** | Deterministic browser test/readback surface where it provides an independent enough oracle; not automatically authoritative for every external effect |

## 2026-09-23 research intake

The attached benchmark research compared 17 external systems but explicitly reported that the collection did **not** complete a full code-to-code audit of all 17. Stagehand received concrete current-repository verification; many other matrix cells remained `NV`. That methodological honesty is now a Source Matrix invariant: **unverified is a work item, not a negative fact**.

Duplicate copies of the same benchmark report were deduplicated during intake. The separate architectural-falsification reports are retained as methodology input (external validity, independent oracle, anti-Goodhart, assumption/model-inadequacy tests), not duplicated as project rows. The unrelated future-human-curriculum report was excluded.

## Audit priority

**Wave A — Experience/self-improvement core:** Stagehand, FlowEvo, RethinkSkill, Double Ratchet, Ratchet, Trace2Skill, Memorizz, DeepSeek Harness.

**Wave B — harness/runtime comparison:** OpenHands, DeerFlow, OpenClaw, OpenManus, Browser Use, LangGraph, Cradle.

**Wave C — browser/perception/evaluation long tail:** existing Browser references plus Agent Workflow Memory, SkillRL, Voyager and external benchmark suites.

The waves are sequencing hints only. The canonical readiness gates and evidence schema live in `context/REFERENCE_CODE_TO_CODE_AUDIT_2026-09-23.md`.
