# Upstream strategy

Primary upstream: `NousResearch/hermes-agent`.

Downstream fork: `kevynlucasprofissional-stack/hermes-agent`.

Initial base:

`057dcdf236f8a6a26721c10fcc6ccb72726e272a`

Recommended remotes:

```powershell
git remote add upstream https://github.com/NousResearch/hermes-agent.git
git fetch upstream
```

Rules:
- upstream Hermes remains authoritative for generic Hermes behavior.
- Workstation functionality lives under `workstation/` whenever practical.
- a core modification is allowed when it produces a cleaner first-class
  architecture; it must be recorded in `UPSTREAM_DELTA.md`.
- generic improvements should be structured so they can be proposed upstream.
- stable updates are promoted only after Workstation integration/E2E validation.
- edge follows upstream more aggressively for compatibility testing.
