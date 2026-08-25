# Source reuse matrix

| Project | Decision | V1 use |
|---|---|---|
| NousResearch/hermes-agent | **KEEP + MODIFY MINIMALLY** | Core/Gateway/Desktop/Dashboard/Kanban remain source of truth |
| abundantbeing/hermes-browser-extension | **ADAPT PROTOCOL/SAFETY, DO NOT VENDOR WHOLE APP** | Fail-closed binding, leases/reconnect and safety design reference; extension remains an optional future compatibility lane |
| browser-use/desktop | **ADAPT CODE/PATTERNS** | `WebContentsView` lifecycle/background/session patterns |
| browser-use/browser-harness | **KEEP EXTERNAL** | Existing Hermes `browser_exec` power path |
| vercel-labs/agent-browser | **KEEP EXTERNAL** | Deterministic fallback |
| browser-use/browser-use | **KEEP EXTERNAL** | Power/adaptive backend already integrated by Hermes |
| browser-memory/browser-memory | **ADAPT IDEA/CONTRACT** | V2 procedural memory |
| apatureai/lattice | **ADAPT IDEA/CONTRACT** | V2 compact perception/provenance |
| aaronlab/browsertrace | **REFERENCE** | Execution journal/replay UX |
| EricFinland/witness | **REFERENCE** | Event/evidence/cost tracing |
| VasuBansal7576/driftlock | **REFERENCE** | Drift vs regression recovery |
| lamenting-hawthorn/browserbench | **REFERENCE/EVAL** | Exactly-once transaction safety |
| visnia-ai/browsewebapp-bench | **REFERENCE/EVAL** | Realistic browser task suite |
| visnia-ai/browser-agent | **BENCHMARK CANDIDATE** | Compare efficiency/reliability, not core runtime |
| browser-use/browsercode | **REFERENCE** | Confirms script-per-call Power Mode design |
| browseros-ai/BrowserOS | **UX REFERENCE ONLY** | AGPL source is not copied into MIT Workstation |
| Browser4 | **FUTURE EXTERNAL BACKEND** | Bulk crawl/extraction only if benchmark justifies |
| VibeSurf | **REFERENCE ONLY** | Workflow/preview ideas; avoid license/agent-in-agent coupling |
| Sabrina/openclaw-ai-browser | **REFERENCE ONLY** | Brain/Hands, risk gates, journal |
| nesquena/hermes-webui | **DO NOT INTEGRATE** | Official Desktop + Dashboard already own UI/state/LAN |
