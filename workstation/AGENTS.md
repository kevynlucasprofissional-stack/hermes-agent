# Hermes Workstation — Agent Instructions

This directory is the downstream Hermes Workstation product layer. Repository-wide rules in the root `AGENTS.md` remain authoritative.

Before editing anything under `workstation/` or any Workstation-owned integration point elsewhere in the repository, read [`context/README.md`](context/README.md) and follow its required reading order. Then inspect the current `main` code and tests for the subsystem being changed.

Do not create parallel SessionDB, Kanban, Memory, approval, or Browser state systems. Keep the upstream delta explicit and preserve the Browser/session/security invariants recorded in the Workstation context.