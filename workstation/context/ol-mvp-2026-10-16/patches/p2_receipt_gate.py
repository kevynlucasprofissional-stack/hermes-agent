"""P2 receipt sanity gate. Structural only; cannot authenticate Artifacts/owner/authority."""
from __future__ import annotations
import json
import sys
from pathlib import Path

BAD_VALUES = {'', 'real', 'test', 'fake', 'placeholder', 'none', 'unknown'}

def artifact_ref(v):
    return isinstance(v, str) and v.startswith('artifact://tasks/') and len(v.split('/')) >= 5

def evaluate(data):
    reasons = []
    if not isinstance(data, dict):
        return {'status': 'INVALID', 'reasons': ['not_an_object'], 'artifact_integrity_checked': False}
    schema = data.get('schema')
    if schema == 'hermes.ol_mvp.p1c_result.v1':
        for k in ('task_id', 'run_id'):
            value = str(data.get(k) or '').strip().lower()
            if value in BAD_VALUES:
                reasons.append(k + '_placeholder')
        refs = data.get('evidence_refs')
        if not isinstance(refs, list) or not refs or not all(artifact_ref(x) for x in refs):
            reasons.append('no_canonical_artifact_refs')
        if data.get('items_compiled', 0) and not data.get('adoption_receipt_refs'):
            reasons.append('compiled_adoption_unproven')
        if data.get('native_browser') is True and not data.get('native_run_e2e_ref'):
            reasons.append('native_electron_run_unproven')
        if data.get('real_llm_calls') is None:
            reasons.append('provider_cost_unknown')
    elif schema == 'workstation.ol_mvp.p1c.evidence.v1':
        first = data.get('first_run') or {}
        second = data.get('second_run') or {}
        if first.get('task_id') in BAD_VALUES or first.get('run_id') in BAD_VALUES:
            reasons.append('first_run_id_unbound')
        if not second or second.get('task_id') in BAD_VALUES or second.get('run_id') in BAD_VALUES:
            reasons.append('second_run_unbound')
        items = first.get('items') or []
        if len(items) < 3:
            reasons.append('fewer_than_three_items')
        if not items or any(not artifact_ref(i.get('raw_result_ref')) or not artifact_ref(i.get('readback_ref')) for i in items):
            reasons.append('item_artifact_refs_missing')
        if not artifact_ref(first.get('adoption_receipt_ref')):
            reasons.append('inflight_adoption_receipt_missing')
        if first.get('qualification_mode') != 'DIRECT_AUTHORIZED':
            reasons.append('direct_not_qualified')
    else:
        reasons.append('unsupported_schema')
    return {'status': 'REQUIRES_RECONCILIATION' if reasons else 'STRUCTURE_ONLY', 'reasons': reasons,
            'artifact_integrity_checked': False, 'owner_authority_checked': False,
            'real_electron_execution_verified': False}

def main():
    if len(sys.argv) != 2:
        print('usage: python p2_receipt_gate.py <receipt.json>', file=sys.stderr)
        return 2
    d = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
    print(json.dumps(evaluate(d), indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
