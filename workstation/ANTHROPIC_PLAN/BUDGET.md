# Anthropic API credits — provisional US$90 execution control

## Price evidence (Anthropic Claude Platform, checked 2026-10-08)
| Model | API ID | USD per million input tokens | USD per million output tokens | Policy |
| --- | --- | ---: | ---: | --- |
| Fable 5.1 | `claude-fable-5-1` | 10 | 50 | Reserve for hardest residual task / comparative failure |
| Opus 5.5 | `claude-opus-5-5` | 4 | 20 | Default premium model |
| Sonnet 5.5 | `claude-sonnet-5-5` | 2 | 10 | Smaller repair and verification only if cheaper external alternatives unavailable |

Official refs: https://platform.claude.com/docs/en/models/overview ; https://platform.claude.com/docs/en/models/fable-5-1/overview ; https://platform.claude.com/docs/en/models/opus-5-5/overview . Prices, promotional restrictions and availability must be rechecked before use.

## Initial envelope, not consumption target
- **US$55 Opus pool** — hard architecture/implementation tasks selected by tested packet.
- **US$15 Fable pool** — one truly difficult reasoning/verification task, only if an Opus output was insufficient or a falsifiable benchmark warrants it.
- **US$10 Sonnet pool** — limited integration corrections when premium context continuity matters; otherwise save it.
- **US$10 protected reserve** — emergency verified corrective loop and token-spend overshoot; not precommitted.
**Sum US$90**, with global pause once actual spend reaches US$80 unless the user explicitly decides to release reserve. Do not use all US$90 just to use them.

## Cost formula
`cost_usd = uncached_input_tokens * input_rate/1e6 + output_tokens * output_rate/1e6 + cache_write/read adjustments + any applicable service/tool charges`.
Track **actual** API `usage` fields per message, including thinking output, cache and repeated tool-turn contexts. Budget for multi-call agents, not just a single initial prompt; work-in-progress tool transcripts inflate repeated input.

## Required spend tracker (per API call)
`timestamp | packet_id | model | commit SHA | input_uncached | cache_write | cache_read | output | actual_cost | cumulative_cost | result/verified | next_action`.
After each call, record balances observed in Anthropic Console (not inferred as exact from token estimates); if Console does not offer a hard credit cap, configure an external proxy/wrapper with per-call approval and hard accounting. Billing alerts may not hard-stop usage.

## Optimization controls
1. Initial packet ~1–4k instruction/context tokens where feasible, with **only relevant source excerpts**, ideally bounded total context 8–16k; these are design targets, not token count guarantees.
2. Never send `ROADMAP.md` (~184KiB), `HERMES_WORKSTATION_INTELLIGENCE.md` (~249KiB) or journal (~340KiB) wholesale. Preparation agent extracts **claims with immutable refs**.
3. Minimize repeated prompts through immutable system prefix / prompt caching where supported and economical; check TTL and cache accounting.
4. Set per-packet max output, effort where supported, tool-call and retry caps. Code should be emitted as diffs to narrowly designated files and validated locally.
5. Use small PRs; stop at first missing source signature, red gate, unverifiable outcome, or out-of-date commit instead of paying premium tokens to explore.
6. Independently validate with local tests and cheaper models before further expensive revisions. Keep at least one correction iteration in reserve.
7. Do not assume promotional credits work through third-party IDE subscriptions or marketplaces. Confirm the Anthropic API key, workspace, credit eligibility and route being billed.

## Prepaid session go/no-go
`PREPARED && PINNED && LEGAL && BASELINE_DISPOSITION && PACKETS_TESTED && SPENDING_GUARD && USER_GO`. Otherwise spend **US$0**.
