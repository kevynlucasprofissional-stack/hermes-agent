# Source reuse matrix

<!-- creative-workstation-intake:2026-10-08 -->
## Creative Workstation external-reference intake — 2026-10-08

**Licensing refinement (2026-10-08):** Penpot **core** MPL-2.0 and `penpot/penpot-ai-kit` **CC-BY-4.0** (official GitHub repository metadata) are distinct; skills/assets reuse and attribution need an individual license audit. Remotion, FFmpeg codec builds, community MCP trust, Graphite assets and source pins each require their own admission decision. [Security and verification matrix](creative-workstation/VERIFICATION_MATRIX.md).


**RESEARCH LEADS ONLY; runtime compatibility NOT VERIFIED.** See [Creative Workstation integrations](creative-workstation/INTEGRATIONS.md) for links, skills, license caveats and status. This matrix alone does not approve vendoring/installation; pin exact upstream SHA and inspect code/headers before implementation.

| Reference | Disposition | Research target / status |
| --- | --- | --- |
| `penpot/penpot` (`mcp/`) and `penpot/penpot-ai-kit` | KEEP EXTERNAL + ADAPT MCP/SKILLS | Official MCP moved to main monorepo (prior `penpot-mcp` archived), auth/plugin code execution, self-host/remote mode, MPL; Hermes integration NV |
| `remotion-dev/remotion` and `remotion-dev/skills` | KEEP EXTERNAL + EVAL | React/Studio/CLI, official skills; special license requires distribution/use-case review; Hermes E2E NV |
| `mrdoob/three.js` (`editor/`) | ADAPT IDEA/CONTRACT | Thin typed bridge, scene identities, versioned editor internals, MIT; Hermes E2E NV |
| FFmpeg | KEEP EXTERNAL | Typed CLI / ffprobe proof; build/license/codec must be audited |
| Blender; Inkscape | KEEP EXTERNAL | `bpy`/headless, SVG/CLI, community MCP optional, GPL; Hermes E2E NV |
| GraphiteEditor/Graphite | REFERENCE + EXPERIMENT | Graph-based procedural editor, software MIT/Apache; separate asset license, stable agent graph interface NV |
| BOMWiki/partmode; sgenoud/replicad | REFERENCE | Agent-oriented CAD operations and JS CAD; hosted MCP/auth/AGPL analysis |
| GIMP; Krita; Godot; PixiJS; p5.js; Tone.js; Strudel; Scribus | RESEARCH/KEEP EXTERNAL | Specialized engines, compatibility and source/license ref NV |
| Community MCPs for Blender/Inkscape/GIMP/Krita/Remotion/Godot | REFERENCE/EVAL | Code execution and secret/FS isolation, pinned versions, negative effect tests required |
| n8n | KEEP EXTERNAL, not creative core | Existing optional MCP catalogue, do not duplicate workflow runtime |

Classification: upstream capabilities are source-documented FACT/PARTIAL where linked; compatibility, qualification, redistributability and skill installation in the Hermes fork are **NV**, not ABSENT.



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

## Plugin / connector / MCP host references

These projects are research references for the Hermes Work integration surface: plugin discovery, connector lifecycle, MCP hosting, OAuth/credentials, tool routing, permissions, action confirmation, multi-user isolation and external-service UX. They are **not** approved runtime owners or dependencies by virtue of appearing here.

| Project | Decision | V1/current use |
|---|---|---|
| modelcontextprotocol/typescript-sdk | **REFERENCE + BENCHMARK CANDIDATE** | Protocol-first baseline for MCP client/server contracts, tools/resources/prompts, transports, authorization boundaries and host/server separation; study before framework-specific abstractions |
| LibreChat-AI/LibreChat | **BENCHMARK CANDIDATE** | High-priority full-stack reference for MCP hosting, connector/tool integration, OAuth/auth boundaries, multi-user isolation, agent/tool surfaces and ChatGPT-like extensibility |
| open-webui/open-webui | **REFERENCE + BENCHMARK CANDIDATE** | Extensibility model: tools, functions, pipes/filters/actions/events, MCP/OpenAPI bridges, permissions and UI-to-tool lifecycle; verify current license/ref before any code reuse |
| Mintplex-Labs/anything-llm | **BENCHMARK CANDIDATE** | Tool discovery/routing at scale, MCP servers, agent skills and dynamic reduction of tool schemas/context pressure |
| langgenius/dify | **REFERENCE + BENCHMARK CANDIDATE** | Plugin lifecycle/marketplace architecture, provider/tool/agent-strategy boundaries, credentials/configuration and packaging model |
| janhq/jan | **REFERENCE + BENCHMARK CANDIDATE** | Smaller desktop MCP-host reference: tool routing, local-first integration, permissions/confirmation and host-to-server execution path |
| CherryHQ/cherry-studio | **REFERENCE** | Desktop client integration patterns, MCP/server management, user-facing connector configuration and multi-provider UX |
| lobehub/lobehub | **REFERENCE + BENCHMARK CANDIDATE** | Current repository identity for the former LobeChat project; study plugin/tool ecosystem, agent integration and extensible chat UX. Historical references to `lobehub/lobe-chat` must resolve to the current repo/ref before audit |
| FlowiseAI/Flowise | **REFERENCE / ARCHIVED SNAPSHOT** | Visual agent/tool/MCP orchestration reference. GitHub repository was marked archived at intake (2026-09-30); treat as historical architecture evidence unless an active successor repository is pinned |

### Connector-study questions

For each project, the audit should answer at minimum:

1. How are tools/connectors discovered, registered and versioned?
2. Where are credentials, OAuth scopes and user/tenant identity bound?
3. How does the host decide which tools reach model context when the catalog is large?
4. What requires user confirmation, and where is authorization enforced versus merely represented in UI?
5. How are tool schemas normalized across MCP, OpenAPI/native functions and project-specific plugin formats?
6. What are the failure, retry, timeout, cancellation and recovery semantics?
7. How are external effects, provenance, receipts and audit history represented?
8. Which parts belong in Hermes Work versus remaining external MCP/plugin servers?
9. Which invariants can be adapted without importing another framework's lifecycle or state ownership?

## System-1 decision-engine runtime

Laya is no longer only a research lead. D-033/D-034 approve it as an **experimental runtime dependency on an isolated branch**, with mainline promotion still evidence-gated. This is the explicit exception to the general Source Matrix intake-only rule.

| Project | Decision | V1/current use |
|---|---|---|
| NandhaKishorM/laya @ `4aa6761be8173de4ce6d92c31b3e40b6eaf59a7c` | **APPROVED EXPERIMENTAL RUNTIME + PINNED SECONDARY UPSTREAM** | First `System1DecisionProvider`; typed decisions, candidate ranking, abstention/calibration/evals; planned git subtree at `workstation/third_party/laya`. Laya 0.3.23, Apache-2.0. It may influence bounded choices but never owns authority, certification, verification or capability promotion. |

Canonical: [`context/LAYA_SYSTEM1_DIRECT_INTEGRATION_2026-10-02.md`](context/LAYA_SYSTEM1_DIRECT_INTEGRATION_2026-10-02.md).

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


## Plugin platform / ChatGPT-style integration references — 2026-09-24 intake

Target: evolve Hermes Work so its plugin experience and operational semantics are as close as practical to the observable ChatGPT Plugins/Apps behavior, while preserving Hermes' own invariants. **ChatGPT itself is a closed-source product reference, not a code-to-code source**: use it as a black-box behavioral/UX contract and use the open-source projects below for implementation evidence.

Before proposing new architecture, audit the existing Hermes plugin stack on current `main`: `plugins/`, `plugin-catalog/`, `hermes_cli/plugins.py`, `hermes_cli/plugin_catalog.py`, the existing `hermes_cli/mcp_*` surfaces, compatibility contracts, install provenance/security scanning, degraded boot and prompt-cache constraints. Extend these owners where possible. **Do not create a second plugin manager, registry, catalog, secrets store or MCP owner merely to imitate ChatGPT.**

| Project / surface | Decision | V1/current use |
|---|---|---|
| OpenAI ChatGPT Plugins / Apps | **REFERENCE** | Behavioral/UX oracle only: discovery/search/suggestion, explicit install/connect, account authorization, per-plugin permissions, read-vs-write confirmation, capability invocation from natural language, multi-plugin composition, status/disable/uninstall and user-visible failure/approval flows. No proprietary implementation assumptions. |
| langgenius/dify | **BENCHMARK CANDIDATE** | End-to-end plugin platform architecture, marketplace/product integration, plugin SDK boundaries and lifecycle ownership. |
| langgenius/dify-plugin-daemon | **BENCHMARK CANDIDATE + ADAPT CODE/PATTERNS** | High-priority code-to-code target for plugin process/runtime lifecycle, isolation, install/load/update behavior, execution and failure containment. |
| langgenius/dify-official-plugins | **REFERENCE + BENCHMARK CANDIDATE** | Concrete plugin manifests/tool/provider patterns and the contract between host, SDK and installed plugin packages. |
| lobehub/lobe-chat | **BENCHMARK CANDIDATE + REFERENCE** | High-priority UX/marketplace comparison: discover -> connect/install -> expose MCP/tool capabilities to an agent with minimal setup friction. |
| lobehub/lobe-chat-plugins | **REFERENCE** | Plugin index/registry representation and catalog UX patterns; verify current license and compatibility before adapting code. |
| open-webui/open-webui | **BENCHMARK CANDIDATE** | Tools/Functions/MCP/OpenAPI extensibility, community extension loading, server-side execution boundaries and security/degraded-mode trade-offs. |
| LibreChat-AI/LibreChat | **BENCHMARK CANDIDATE** | Agent + MCP tool selection, OpenAPI Actions, per-agent capability attachment and configuration/authorization boundaries. |
| modelcontextprotocol/modelcontextprotocol | **REFERENCE + BENCHMARK CANDIDATE** | Protocol baseline for tool/resource discovery and invocation. MCP is an adapter/protocol under the plugin layer, not by itself the full marketplace/auth/permissions/runtime product. |

### Plugin-system code-to-code questions

Every project above must be compared against the current Hermes implementation, not against an imagined greenfield system:

1. **Registry / install ownership:** how are discovery, install records, provenance, version pins, dependencies, updates, rollback and uninstall represented?
2. **Connection/auth:** how are OAuth, API keys, account linking, scoped secrets and reconnect/revocation modeled?
3. **Permissions:** can the user define global defaults and per-plugin overrides; are reads, low-risk writes and important/sensitive writes distinguishable?
4. **Capability discovery:** how are tools/resources/actions surfaced to the model without uncontrolled prompt/tool-schema churn or cache invalidation?
5. **Invocation UX:** can natural language and an explicit plugin selector (for example an `@Plugin`-style affordance) converge on the same capability path?
6. **Multi-plugin composition:** can one task safely read from one plugin and write through another while preserving lineage, approvals, ordering and failure attribution?
7. **Isolation / degraded boot:** can one broken or malicious optional plugin fail independently without taking down core Hermes?
8. **Lifecycle / health:** install -> configure -> enable -> execute -> update -> disable -> uninstall must be observable, testable and restart-safe.
9. **Security / trust:** source provenance, exact-version review, requested capabilities, secret scope, sandboxing, approval gates and audit receipts must remain explicit.
10. **Surface parity:** Desktop, CLI/TUI and future remote clients should project the same canonical plugin state rather than becoming separate plugin implementations.

**Parity criterion:** the goal is not a visual clone or reverse engineering of proprietary ChatGPT internals. The goal is **observable behavioral parity where compatible**: a user should be able to discover a plugin, install/connect it, grant bounded permissions, ask Hermes naturally to use it, combine it with another plugin, review sensitive writes, inspect status and remove it with the same mental model and roughly the same interaction cost as ChatGPT.

## 2026-09-23 research intake

The attached benchmark research compared 17 external systems but explicitly reported that the collection did **not** complete a full code-to-code audit of all 17. Stagehand received concrete current-repository verification; many other matrix cells remained `NV`. That methodological honesty is now a Source Matrix invariant: **unverified is a work item, not a negative fact**.

Duplicate copies of the same benchmark report were deduplicated during intake. The separate architectural-falsification reports are retained as methodology input (external validity, independent oracle, anti-Goodhart, assumption/model-inadequacy tests), not duplicated as project rows. The unrelated future-human-curriculum report was excluded.

## Audit priority

**Wave A — Experience/self-improvement core:** Stagehand, FlowEvo, RethinkSkill, Double Ratchet, Ratchet, Trace2Skill, Memorizz, DeepSeek Harness.

**Wave B — harness/runtime comparison:** OpenHands, DeerFlow, OpenClaw, OpenManus, Browser Use, LangGraph, Cradle.

**Wave C — browser/perception/evaluation long tail:** existing Browser references plus Agent Workflow Memory, SkillRL, Voyager and external benchmark suites.

**Wave D — plugins/connectors/MCP architecture:** MCP TypeScript SDK first, then LibreChat, AnythingLLM, Open WebUI, Dify, Jan, LobeHub, Cherry Studio and the archived Flowise snapshot. Focus on discovery, auth/identity, tool routing, confirmation/effect safety, multi-user isolation and host/server ownership boundaries.

**Plugin-system lane — parallel research intake, implementation gated:** current Hermes plugin/catalog/MCP baseline -> ChatGPT black-box behavior matrix -> Dify + Plugin Daemon -> LobeHub/LobeChat -> Open WebUI + LibreChat -> MCP cross-cut -> gap synthesis -> separately reviewable Hermes proposals.

The waves are sequencing hints only. The canonical readiness gates and evidence schema live in `context/REFERENCE_CODE_TO_CODE_AUDIT_2026-09-23.md`.
