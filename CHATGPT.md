# ChatGPT sessions — Hermes Work collaborative coding

This file is a project guide, not a guarantee that ChatGPT automatically loads it or that a connector is already installed. Read [AGENTS.md](AGENTS.md) first. The current branch is the branch actually checked out (normally main); never switch/reset/stash just because a historical prompt names a branch.

## Current cooperation rules

The project-local P0/P1/P2 multi-agent coordinator, admission layer and Claude hooks were retired by the maintainer on 2026-10-28. The old .hermes-collab directory and engineering journals are retained as HISTORICAL evidence, not an active ownership service. Do not run removed scripts. Before editing a shared checkout, inspect Git dirty/untracked work and coordinate directly with other active writers. Direct terminal/Desktop Commander/Claude access does not enforce cross-agent claims. The separate local-mcp-bridge is not automatically connected to this Hermes checkout and does not universally fence raw writes.

ChatGPT's direct Controle Windows tools and Claude's direct tools are separate from the independent local-mcp-bridge. Neither implies per-conversation authentication, automatic claims or protection from concurrent writes. Preserve ongoing work, check HEAD/branch and all dirty/untracked paths, and request handoff for overlapping edits. Git mutation requires explicit authorization.
