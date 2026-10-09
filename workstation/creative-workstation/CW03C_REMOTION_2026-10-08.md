# CW-03C: editable source foundation, render execution pending

This incremental change runs under the development exception. It does not claim
Remotion installation, Studio integration, animation rendering or phase qualification.
The personal-use disposition remains scoped to the user's current personal use.

Implemented:

- Strict invitation source: text, hex colors, bounded even dimensions, frame rate,
  duration and logo geometry. Unknown executable/resource fields are refused.
- Original Hermes TSX invitation template with a one-second entrance and animated
  logo pulse. Text remains React text content, without HTML or script interpolation.
- Explicit project engine identity. Existing SVG revisions reopen unchanged;
  a revision lineage cannot silently switch engines. The native SVG adapter refuses
  a Remotion project before Browser dispatch.
- Remotion revisions retain native TSX/index/package files with per-file hashes.
  Manifest is the last commit marker. Changed human source refuses append instead
  of being overwritten. Canonical ArtifactStore/journal publish the native sources
  alongside the declarative source and manifest.
- CLI `save --engine remotion` validates the typed source before preparing writes.
  It inherits existing profile/session/TaskRun authority. `inspect` reports engine.
- Partial native writes return EFFECT_UNCERTAIN and cannot publish a successful
  project deliverable. Malformed source and engine-lineage changes refuse before
  preparing writes. No automatic retry or alternate execution owner was added.

Validation: nine contracts pass across source, store, live TaskRun, render dispatch
and injected partial-write tests. These cover real filesystem/DB/ArtifactStore
paths, not Remotion rendering. Existing esbuild bundled the TSX syntax successfully
with React/Remotion external; that is not an installed-SDK typecheck or runtime proof.

Candidate external engine: Remotion 4.0.534, all Remotion dependencies pinned
together; React/ReactDOM 19.2.7 match the existing Desktop pins. The template
package is private and is not part of the root workspace installation. No vendor
package or executable is bundled into Hermes by this change.

Static audit downloaded only the published renderer archive with scripts disabled.
Its bytes matched the npm registry integrity exactly:

`sha512-CLZiNRibavsEpDWSm1WsD//xLGCUA/OwhFektjiAbRNkX75Ee3bOV4cjpyihaEd0HaiUv3bUT0QLnvdwynor/w==`

The [tagged license](https://github.com/remotion-dev/remotion/blob/v4.0.534/LICENSE.md)
was reviewed for the existing personal-use disposition. The package was not imported
or executed. Its renderer declares platform compositor optional dependencies;
bundler/CLI add further transitive packages that still require lock/audit before use.

Concrete isolation findings: the selected renderer's
[port configuration](https://github.com/remotion-dev/remotion/blob/v4.0.534/packages/renderer/src/port-config.ts)
binds wildcard interfaces, and its
[browser launcher](https://github.com/remotion-dev/remotion/blob/v4.0.534/packages/renderer/src/open-browser.ts)
includes sandbox-disabling arguments. Neither default is accepted as the final
Creative execution boundary. A pinned adapter must enforce loopback/owner access,
private browser profile, bounded lifecycle and appropriate isolation, then prove
positive/negative real execution. No unsafe default renderer was wired into the CLI.

Pending: explicit consent for isolated installation (question issued separately),
complete dependency audit, runtime isolation, typed render/Studio entrypoints,
independent animation frame readback, restart/variation/concurrent-edit E2E and
exact-head CI. Existing CW-03A capture failures also remain open.

Final upstream observation: `1e0c7730d791f5ce855c5c78935cfea6fb1e43a9`, sixteen
commits after the previous observation `9d05e7ff92d3edd9abdf20fe3d04551905cb995e`.
Broad linter changes touch 552 files; inspected Creative owners show optional type
annotation changes in ProcessRegistry/LocalEnvironment/Kanban and export ordering
in deadline, without altered admission semantics there. Gateway service-definition
home-owner corrections are relevant to next-cycle profile qualification and should
be evaluated for ADOPT_UPSTREAM then. Plugin catalog delisting is unrelated to
this source adapter. Fixed selected pin remains
`517b5e10febd619ce30bb22580e29b160266eb43`; no second sync or baseline promotion.
