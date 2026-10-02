This directory contains license notices and, by explicit architectural exception, pinned third-party source that is part of a Hermes Workstation runtime experiment.

The default remains: full external projects are **not** vendored here. Exact source roles and pinned references live in `../components.lock.json`.

## Approved exception: Laya

D-034 authorizes `NandhaKishorM/laya` as a secondary upstream for the active System-1 lane.

Target: `workstation/third_party/laya/`  
Method: pinned `git subtree --squash` at one exact upstream SHA.

The import/update commit must preserve Apache-2.0 notices, update `../components.lock.json` with exact SHA/version/license/path and `vendored: true`, keep Workstation integration outside the subtree where possible, and make the Hermes environment import the vendored package through normal packaging/install semantics rather than a runtime `sys.path` hack.

Reviewed initial pin: `4aa6761be8173de4ce6d92c31b3e40b6eaf59a7c` (Laya 0.3.23, Apache-2.0).

Canonical: [`../context/LAYA_SYSTEM1_DIRECT_INTEGRATION_2026-10-02.md`](../context/LAYA_SYSTEM1_DIRECT_INTEGRATION_2026-10-02.md).
