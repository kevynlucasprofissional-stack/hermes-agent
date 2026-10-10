# Operational speed P0 development evidence — 2026-10-10

Status: DEVELOPMENT ONLY; CI skipped by explicit maintainer instruction “Pode pular os CI e continue o trabalho.” No main merge, release qualification, native E1–E3 completion or measured product savings.

Baseline: `217742e7bfc66310f9352155e4a0b1a30bab2b98`.
Immutable upstream pin: `66605471e9f0b0832abbefaf625ce08e948ca540`.
Runtime branch: `codex/operational-speed-runtime-20261010`.
Stage A and runtime feature commits remain separate. Local Stage A native failures remain listed in the Stage A report; this exception does not relabel them.

## P0.2 authenticated DIRECT

RED: official runner on original runtime: 7 passed, 2 failed (11.9s). Both failures reproduce forging an unkeyed digest, including changing a revoked read-only qualification into an active mutation qualification.

GREEN: official runner: attestation 9 passed, real profile boundary 2 passed, online safety 37 passed. These ran with seven telemetry contracts: 55 passed, zero failed, 102.9s wall (two workers). The online safety file exercises real TaskRun mining, compilation, validation and local filesystem adoption; the seven-item contract verifies three initial items and four reused items. This is local integration evidence, not native Trello or LLM savings.

Changes: v2 HMAC-SHA256; operator-selected profile-scoped secret via existing secret_scope; issuer/key ID and all claims authenticated. Exact trusted bindings cover code, provider/model/revision, operation family, effect class, semantic verifier and environment. Finite validity (maximum 24h), external operator revocation, and offer-time revalidation fail closed to SHADOW. Legacy v1 hashes are rejected. Validated verifier lifecycle/receipt metadata remains checked by the existing runtime; qualification compares its semantic fields.

Operator configuration lives in existing config.yaml under:
`workstation.online_compilability.qualification_trust`, with `issuer`, `key_id`, `secret_ref`, `bindings` (list of exact qualified claim mappings), and `revoked_attestation_ids`.
The named secret must be at least 32 random bytes encoded as Base64, provisioned through the existing profile secret infrastructure. No key is generated, persisted or installed by this patch. Artifacts cannot select their own key. Operators must qualify the deployed code/model/environment and update the trusted exact binding when those change. Tests use isolated dummy keys only.

The authenticated claim is qualification evidence, not an authorization grant. Existing TaskRun, permission, effect budget, target, readback and global-promotion gates still apply. Historical narrative success is insufficient.

## Pending

P0.1 telemetry and real baseline completion; P1 new-intent routing/browser/artifact/HyperFrames operations; P2 concurrent human edit protection and durable learning queue closure; P3 native E1–E3 and controlled repeated benchmarks. No external Trello writes performed. Latency, real LLM avoidance, tokens saved and cost savings: UNKNOWN.


## Operational speed P0.1 — instrumentation development (2026-10-10)

Existing local telemetry now persists nullable canonical cost/source, actual cache tokens, call IDs and application UTF-8 byte counts; repeated event delivery is deduplicated. Provider usage comes from the existing pricing/accounting owner. Tool timing/fingerprints store no raw Browser content. Telemetry failure cannot prevent mutation bookkeeping. Session economics reports unknown values when usage/pricing is absent, and flags calls without run lineage; per-run attribution is not complete. Server admission latency excludes UI/transport and remains unknown for ambiguous turn lineage.
RED: SQLite lost cost_usd and repeated delivery charged twice (2 failures). GREEN: 34 focused telemetry/core/System-1 contracts; final usage-owner and SQLite recheck 12 passed. Full Workstation regression running, not yet qualified. Strict seam classification: 14 classified, zero unclassified/growth. Exact historical seam manifest remains divergent on 14 unchanged tools-file line keys.
Real Trello/HyperFrames/repetition baseline BLOCKED: installed native controller health returned false; no real end-user latency, token savings or monetary savings available. CI skipped by maintainer authorization, development only. Evidence: workstation/context/engineering-journal/operational-speed-p0-2026-10-10.md.