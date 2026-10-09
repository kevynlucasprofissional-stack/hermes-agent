# CW-03A editable project persistence — incremental implementation

Development proceeds under the maintainer's documented development exception.
Baseline issues remain NOT RESOLVED; this is not phase qualification.

`workstation/creative_project_store.py` adds profile-local, portable source
revisions for the Electron/SVG adapter. Each revision contains an editable JSON
source and a schema-versioned manifest with its content hash and parent revision.
New revisions use unique paths and exclusive file creation; there is no mutable
head pointer, execution database, approval authority or replacement TaskRun.
The manifest is written last, so a source-only partial write cannot reopen as a
complete revision. External edits are refused rather than silently overwritten.

The store does not admit operations or certify output. The new
`creative_project_runtime.py` caller checks the opt-in, active profile, distinct
approval key and durable session ID, and the real canonical task/run/claim before
writing. It refuses terminal, superseded, expired or foreign runs. Source and
manifest become unique ArtifactStore entries linked in the canonical journal.
The manifest retains the prepared operation ID for uncertain-write reconciliation;
source bytes are flushed before the manifest commit marker. This is file
persistence, not a second task database or an execution certificate.

The `python -m workstation.creative --task-id TASK --run-id RUN` entrypoint offers
`save --source FILE`, `inspect --project-id ID --revision-id REV`, and
`render --project-id ID --revision-id REV --browser-task-id BROWSER_TASK`.
It inherits real Hermes session/profile context; there are no arguments that mint
session identity or permission. Active profile config must explicitly contain
`creative.enabled: true`. The existing task workspace must contain the source
and project destination. A new project requires a workspace containing
`workstation/creative/projects`; later revisions can use its narrower project
directory. This CLI does not create a Kanban task or BrowserTask on the user's behalf.

`creative_render.py` dispatches through the existing authoritative Browser adapter,
keeping BrowserTask identity separate from the Kanban card. It reads the owner
receipt and tab lineage from canonical `Runtime/browser-session.json`, checks
source/output hashes, decodes the PNG independently and publishes SVG/PNG through
ArtifactStore and journal. The old separate browser-tasks path is not used for
Creative effect proof. A failure after dispatch is `EFFECT_UNCERTAIN` with operation
ID and no automatic retry or fallback; a subsequent terminal run refuses before I/O.
The source format here is for Electron/SVG only, not yet the complete CW-06
multi-engine manifest or collaborative revision protocol.

Validation: canonical runner on project store/runtime, render adapter, media
readback and Browser broker contracts: 17 passed, 0 failed, 0 skipped. After adding
the operation ID/flush contract, the three affected files were rerun: 6 passed.
Persistence tests use real files, real Kanban DB/run/claim, ArtifactStore and journal,
A→B→A profile changes, immutable parents and external human edits. Render adapter
contracts use a **simulated** owner over actual authenticated loopback HTTP;
receipt mismatch and post-dispatch cancellation prevent publication and retry.
Those simulated-owner tests are not native qualification.

`node apps/desktop/scripts/test-creative-project-native.mjs ABSOLUTE_HERMES_PYTHON`
bundles the actual Electron runtime and invokes the actual product CLI in an
ephemeral profile. It creates a real canonical fixture task/run and an owner-bound
BrowserTask, checks foreground preservation, pixels, human-control/session negatives,
then restarts Electron and reopens the same persisted project; a source variation
is also asserted after restart. Its test window uses showInactive and closes on exit.

Observed native results are **intermittent / NOT QUALIFIED**: one integrated
create/reopen trial passed with identical PNG hash
`63e95a4f0c3006193dc7386b2d46d26165524f1293179a7911205537b282e353` in
distinct Electron processes, including foreground and owner negatives. Later
executions, including the final variant/pixel-enriched fixture, failed
`creative_paint_timeout` or `Current display surface not available for capture`.
The earlier standalone native fixture also reproduced paint timeout. Experimenting
with capture visibility and a temporary frame subscription did not reliably close
the fault; those unproven renderer changes were reverted. No final native pass,
variant pass, environment qualification or exact-head CI pass is claimed.
The reviewed Electron API references are
[capturePage](https://www.electronjs.org/docs/latest/api/web-contents#contentscapturepagerect-opts)
and [page visibility](https://www.electronjs.org/docs/latest/api/browser-window#page-visibility).
Keep the render failure open while independent development proceeds under the
documented exception. CW-03A/03B–07 requirements remain in scope.

Final local checks: Desktop typecheck PASS; the five Creative/Browser
task/admission/recovery/viewport regression files PASS (43 tests); strict seam
audit PASS (14 classified, 0 unclassified, 0 budget growth, 522 edge references).
The last workspace-publication fence was verified by rerunning runtime/render
contracts: 4 PASS. PR #59 remains draft. Its previous head had contracts and
core anchors passing, Windows in progress and Nix queued; those results do not
qualify the next head or the native failure above.

Upstream observation: `9d05e7ff92d3edd9abdf20fe3d04551905cb995e`, 22 commits after
`d48e598d443ca4567d573aed98562cab5fa3faa9`. Changes concern Desktop build/reuse/
native staging and tests, pinned installer/update performance, plugin toolset
reenablement and Solstice lazy transport. No diff in inspected Kanban DB/connect,
approval context, gateway session context, hermes_constants/platform, process
registry, Browser Workstation adapter or native Browser runtime. Build/package
changes remain relevant to the separate unqualified baseline and next sync cycle.
The fixed pin `517b5e10` remains unchanged and unadopted; no merge is performed.

CW-03B preparation found installed FFmpeg/ffprobe via the canonical passive
resolver (`C:\ProgramData\chocolatey\bin`). Version, actual shim target/build,
license, health and video rendering are not yet verified. Inkscape and Blender
were absent from this discovery scope. No engine was installed or executed by
discovery, and no support claim is inferred from presence.

Follow-up policy correction: the adapter initially named its filesystem action
`write_file`, while ScopedPolicyEngine's containment contract recognizes `write`.
A real-task negative control proved RED: a different task workspace allowed a
revision file to be created before publication refused it. Changed the caller to
canonical `write`; the negative now requires policy refusal before project I/O,
without bypassing REQUIRE_APPROVAL. This is an adapter fix, not a policy change.
