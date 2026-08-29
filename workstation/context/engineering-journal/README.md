# Hermes Workstation Engineering Journal

This directory is the durable investigation memory for Workstation engineering work that is still in discovery, validation, stabilization, or promotion.

The repository remains the source of truth. Conversation history and agent messages are context only.

## Mandatory anti-repeat protocol

Before starting a new Workstation experiment or corrective change:

1. Read `CURRENT.md`.
2. Search the **Experiment / Failure Ledger** for the same error fingerprint, assumption, tool boundary, or already-refuted hypothesis.
3. Register the next hypothesis or experiment ID in `CURRENT.md` before executing it.
4. Define in advance:
   - the hypothesis;
   - evidence that would support it;
   - evidence that would refute it;
   - the smallest discriminating experiment;
   - whether the experiment changes product code or is evidence-only.
5. Run one logical hypothesis cycle at a time.
6. Immediately after the result, update `CURRENT.md` with:
   - observed evidence;
   - classification (`VALIDATED`, `PARTIAL`, `REFORMULATED`, `REFUTED`, `INCONCLUSIVE`);
   - practical implication;
   - exact error fingerprint when applicable;
   - the next materially relevant hypothesis.
7. Do not run another experiment until the previous experiment's result has been recorded.

## Do-not-repeat rule

A failed approach may only be repeated when at least one material input has changed and that change is recorded explicitly. Examples:

- different product SHA;
- different Electron/Node version;
- different execution boundary;
- corrected harness defect;
- new evidence that invalidates the previous classification.

Renaming a script, changing unrelated logging, or retrying the same command is **not** a material change.

## Scope

Use this journal for transient engineering knowledge that is important enough to prevent repeated mistakes but is not yet a settled architectural decision.

Once a finding becomes stable product truth, promote it to the appropriate canonical document (`DECISIONS.md`, `CONSTRAINTS.md`, `TESTING.md`, `KNOWN_ISSUES.md`, `UPSTREAM_DELTA.md`, etc.) and retain only a concise historical pointer here.
