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
            'model_inadequacy': not m.get('model_inadequacy_detected', False)
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
            'verifier_validated': self._validated_verifier(cap),
        }
        reasons.extend(k for k, passed in checks.items() if not passed)
        return PromotionAdmission(not reasons, tuple(reasons))

    @staticmethod
    def _validated_verifier(cap):
        from workstation.control_plane.verification import (
            VerificationContract, VerificationLifecycle, validate_verifier_sensitivity,
        )
        contract = VerificationContract.from_dict(cap.verifier_contract or {})
        sensitive, _ = validate_verifier_sensitivity(list(contract.validation_receipts))
        return contract.lifecycle == VerificationLifecycle.VALIDATED and sensitive


def derive_formal_contract(capability, traces=None):
    """Conservatively derive CapabilityFormalContract from verified operational experience.

    If any essential requirement cannot be proven with positive evidence,
    returns None (limiting the capability to exact replay/ephemeral reuse without generic routing).
    """
    from workstation.control_plane.contract import CapabilityFormalContract
    from workstation.control_plane.ir import EQ, SET, CALL
    from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope

    m = capability.learning_metadata or {}

    # 1. Operation & Target Families
    op_families = m.get('operation_families') or []
    target_families = m.get('target_families') or []
    if not op_families and m.get('families'):
        op_families = list(m['families'])
    if not target_families and m.get('targets'):
        target_families = list(m['targets'])

    if len(set(op_families)) > 1 or len(set(m.get('families', []))) > 1:
        return None
    if len(set(target_families)) > 1 or len(set(m.get('targets', []))) > 1:
        return None

    op_family = op_families[0] if op_families else (
        capability.implementation.get('steps', [{}])[-1].get('primitive', '')
        if isinstance(capability.implementation, dict) else ''
    )
    target_family = target_families[0] if target_families else str(
        capability.scope.get('target_family') or capability.route or 'workstation'
    )
    if not op_family or not target_family:
        return None

    # 2. Typed Preconditions
    preconditions = []
    pre_dict = m.get('preconditions')
    if isinstance(pre_dict, dict):
        for k, v in sorted(pre_dict.items()):
            preconditions.append(EQ(k, v))
    elif isinstance(capability.preconditions, list):
        for p in capability.preconditions:
            if isinstance(p, dict) and 'key' in p:
                preconditions.append(EQ(p['key'], p.get('expected')))

    # 3. Typed Postconditions (must have at least one verified effect)
    postconditions = []
    eff_dict = m.get('effects')
    if isinstance(eff_dict, dict):
        for k, v in sorted(eff_dict.items()):
            postconditions.append(EQ(k, v))
    elif isinstance(capability.postconditions, list):
        for p in capability.postconditions:
            if isinstance(p, dict) and 'key' in p:
                postconditions.append(EQ(p['key'], p.get('expected')))

    if not postconditions and capability.effect != 'read_only':
        return None

    # 4. Effect Footprint
    effect_footprint = []
    if capability.effect == 'read_only':
        effect_footprint = []
    else:
        for k, v in sorted((eff_dict or {}).items()):
            effect_footprint.append(SET(k, v))
        if not effect_footprint and op_family:
            effect_footprint.append(CALL(op_family, target_family))

    # 5. Authority Required
    # Derived strictly from proven authority in samples
    if capability.effect in {'read_only', 'PURE_READ', 'DISCOVERY'}:
        authority_required = AuthorityScope(
            level=AuthorityLevel.READ,
            allowed_actions={"read"},
            allowed_resources={target_family},
        )
    else:
        origins = capability.provenance.get('origins', []) if isinstance(capability.provenance, dict) else []
        scopes = [
            o.get('authority_scope') for o in origins
            if isinstance(o, dict) and o.get('authority_scope')
        ]
        if not scopes and isinstance(capability.provenance, dict) and capability.provenance.get('authority_scope'):
            scopes = [capability.provenance['authority_scope']]
        if not scopes and isinstance(m.get('explicit_authority_scope'), dict):
            scopes = [m['explicit_authority_scope']]

        if scopes:
            authority_required = AuthorityScope.from_dict(scopes[0]) if isinstance(scopes[0], dict) else scopes[0]
        else:
            # Learned mutation without trusted explicit authority scope does NOT become generically routable
            return None

    # 6. Verifier
    from workstation.control_plane.verification import VerificationContract
    verifier = VerificationContract.from_dict(capability.verifier_contract or {})

    return CapabilityFormalContract(
        operation_family=op_family,
        target_family=target_family,
        typed_preconditions=preconditions,
        typed_postconditions=postconditions,
        effect_footprint=effect_footprint,
        authority_required=authority_required,
        verifier=verifier,
    )


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
