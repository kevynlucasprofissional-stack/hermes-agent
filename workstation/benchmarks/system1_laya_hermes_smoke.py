"""Smoke do provedor Laya real no caminho System 1 do Hermes, sem perfil produtivo."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

from workstation.artifacts import ArtifactStore
from workstation.system1.laya_provider import LayaDecisionProvider
from workstation.system1.browser_read_fastpath import find_visible_control


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--native-stdin", action="store_true")
    args = ap.parse_args()
    home = Path(os.environ["HERMES_WORKSTATION_HOME"]).resolve()
    store = ArtifactStore(root_dir=home / "laya-smoke-artifacts")
    provider = LayaDecisionProvider(artifact_store=store)
    raw_snapshot = {
        "success": True, "runtime": "electron-chromium", "task_id": "qual-system1-task",
        "tab_id": "qual-tab", "revision": 1, "url": "https://example.org/test",
        "readiness": "stable", "truncated": False, "wall_detected": False,
        "elements": [
            {"ref": "@e1", "role": "button", "tag": "button",
             "label": "Abrir relatórios", "disabled": False},
            {"ref": "@e2", "role": "button", "tag": "button",
             "label": "Configurações", "disabled": False},
        ],
    }
    target = "Relatórios"
    fresh = dict(raw_snapshot)
    if args.native_stdin:
        snapshots = json.load(sys.stdin)["snapshots"]
        raw_snapshot, fresh = snapshots[:2]
        target = "Relatório"  # seleção parcial: força inferência real
    seen = []
    def decide(request):
        result = provider(request)
        seen.append(result)
        return result

    began = time.perf_counter()
    receipt = find_visible_control(raw_snapshot, ("button", target),
                                   lambda: fresh, decide=decide)
    duration = (time.perf_counter() - began) * 1000
    assert len(seen) == 1
    result = seen[0]
    proof = {
        "provider": result.provider,
        "source_verified": provider.provenance.source_bytes_verified,
        "requested": target,
        "source_snapshot_native": args.native_stdin,
        "real_model_answer": result.answers.get("preferred_candidate"),
        "model_confidence": result.confidence.get("preferred_candidate"),
        "fallback_recommended": result.fallback_recommended,
        "receipt_status": receipt.status,
        "verified_ref": receipt.ref,
        "response_reason": receipt.reason,
        "decision_receipt_ref_present": bool(result.details.get("receipt_ref")),
        "elapsed_ms": round(duration, 2),
    }
    print("SYSTEM1_LAYA_HERMES_PROOF=" + json.dumps(proof, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
