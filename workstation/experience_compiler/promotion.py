"""Learned admission is independent of validation counts and candidate retrieval."""
from dataclasses import dataclass
from copy import deepcopy
import json

from .models import CausalGrade


@dataclass(frozen=True)
class PromotionAdmission:
    admitted: bool
    reasons: tuple[str, ...]
    policy_version: str = 'experience-v1'


class ExperiencePromotionPolicy:
    def evaluate(self, cap):
        m, reasons = cap.learning_metadata, []
        checks = {
            'semantic_closure': bool(m.get('semantic_closure')) and bool(cap.postconditions),
            'exact_compatibility': bool(cap.semantic_fingerprint and cap.compatibility_fingerprint),
            'parameterization': m.get('parameterization_quality') is True,
            'causal_grade': cap.causal_grade >= CausalGrade.REPLAY_VALIDATED,
            'effect_evidence': m.get('evidence_strength', 0) >= (2 if cap.effect != 'read_only' else 1),
            'provenance': m.get('provenance_complete') is True,
            'trust': cap.trust_class == 'trusted_runtime' and not cap.taint,
            'authority': bool(m.get('authority_origins')) and set(m['authority_origins']) <= {'user', 'system'},
            'cross_run_diversity': len(set(m.get('run_ids', []))) >= 2,
            'drift': cap.drift_state == 'healthy' and m.get('drift_rate', 1) <= .1
                     and not m.get('unresolved_counterexamples', 0),
            'utility': m.get('utility', 0) > 0,
            'risk': m.get('risk', 'ordinary') == 'ordinary' and m.get('blast_radius', 1) <= 1,
            # No global automatic authority for external/high-impact effects in V1.
            'effect_admission': cap.effect in {'read_only', 'state_mutation', 'PURE_READ', 'DISCOVERY', 'MUTATION', 'IDEMPOTENT_WRITE'}
                                and not cap.scope.get('external'),
            'approval': not m.get('requires_approval', False),
            'replay': any(e.get('kind') == 'controlled_replay' and e.get('passed') is True
                          and e.get('compatibility_fingerprint') == cap.compatibility_fingerprint
                          and e.get('result', {}).get('evidence_refs')
                          and e.get('result', {}).get('evidence_strength', 0) >= 1
                          for e in cap.validation_evidence),
        }
        reasons.extend(k for k, passed in checks.items() if not passed)
        return PromotionAdmission(not reasons, tuple(reasons))


def contract_fingerprint(capability):
    from workstation.recipes import digest, sanitize
    fields = ('input_schema', 'output_schema', 'implementation', 'dependencies', 'preconditions',
              'postconditions', 'verifier_contract', 'scope', 'route', 'effect',
              'semantic_fingerprint', 'compatibility_fingerprint')
    body = capability.to_dict()
    return digest(sanitize({k: body[k] for k in fields}))


def pin_capability(store, plan_id, capability):
    """CAS-style metadata update in the existing WorkPlan SQLite transaction."""
    with store._lock, store.get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT metadata, run_id FROM work_plans WHERE id=?', (plan_id,)).fetchone()
        if not row:
            raise ValueError('owning WorkPlan missing')
        metadata = json.loads(row[0] or '{}')
        pins = metadata.get('capability_pins', {})
        pin = pins.get(capability.id)
        if pin is None:
            # Reuse prior selections in the same canonical run, across WorkPlans.
            if row[1]:
                for previous in conn.execute('SELECT metadata FROM work_plans WHERE run_id=?', (row[1],)):
                    pin = json.loads(previous[0] or '{}').get('capability_pins', {}).get(capability.id)
                    if pin:
                        break
            pin = pin or {'capability_id': capability.id, 'version': capability.version,
                'semantic_fingerprint': capability.semantic_fingerprint,
                'compatibility_fingerprint': capability.compatibility_fingerprint,
                'contract_fingerprint': contract_fingerprint(capability)}
            pins[capability.id] = pin
            metadata['capability_pins'] = pins
            conn.execute('UPDATE work_plans SET metadata=? WHERE id=?', (json.dumps(metadata, sort_keys=True), plan_id))
        return deepcopy(pin)


@dataclass(frozen=True)
class EphemeralCompiledSegment:
    run_id: str
    capability: object

    def for_run(self, run_id):
        if not self.run_id or self.run_id != run_id:
            raise PermissionError('ephemeral segment belongs to another TaskRun')
        if self.capability.causal_grade < CausalGrade.REPLAY_VALIDATED:
            raise PermissionError('ephemeral segment lacks local replay validation')
        return deepcopy(self.capability)
