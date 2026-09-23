"""Bounded owner-state projections. Page prose is never interpreted as policy."""
import hashlib
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit

from .models import (SemanticState, StateDelta, TransitionSample, Operation, Verification,
                     Provenance, Metrics, TransitionOutcome, AuthorityOrigin, normalized)
from workstation.execution_policy import EvidenceStrength, semantic_target_family

_BROWSER_FIELDS = {'pr_state', 'mergeable', 'merge_control_available', 'authenticated',
                   'ready', 'wall_detected', 'cookie_banner_visible', 'modal_visible', 'value',
                   'recovery_state'}
_FS_FIELDS = {'exists', 'kind', 'size', 'hash', 'sha256', 'basename', 'extension', 'is_file', 'is_dir'}
_PROCESS_FIELDS = {'process_state', 'exit_code', 'stdout_contract', 'stderr_contract'}


def semantic_anchor(element):
    if element.get('testid'):
        return {'type': 'testid', 'value': element['testid']}
    role = element.get('role') or element.get('tag')
    name = element.get('name') or element.get('label')
    if role and name:
        return {'type': 'role_name', 'value': f'{role}:{name}'}
    return None


def abstract_state(route, data, artifact_ref=None):
    data = data if isinstance(data, dict) else {}
    fields = _BROWSER_FIELDS if route == 'native_browser' else _FS_FIELDS if route == 'filesystem' else _PROCESS_FIELDS
    predicates = {k: data[k] for k in sorted(fields & data.keys())
                  if isinstance(data[k], (str, int, float, bool)) or data[k] is None}
    if route == 'native_browser':
        if data.get('readiness') == 'stable':
            predicates['ready'] = True
        parsed = urlsplit(data.get('url', ''))
        if parsed.scheme in {'http', 'https'} and parsed.hostname:
            predicates.update(host=parsed.hostname,
                url=urlunsplit((parsed.scheme, parsed.hostname, parsed.path, '', '')),
                page_family=re.sub(r'/\d+(?=/|$)', '/:number', parsed.path or '/'))
        for element in data.get('elements', [])[:128]:
            anchor = semantic_anchor(element)
            if not anchor:
                continue
            for key in ('enabled', 'checked', 'selected', 'visible', 'value'):
                if key in element and isinstance(element[key], (str, bool, int)):
                    predicates[f"control.{anchor['type']}:{anchor['value']}.{key}"] = element[key]
    return SemanticState(artifact_ref, normalized(predicates))


def filesystem_state(path, artifact_ref=None, *, max_hash_bytes=8 * 1024 * 1024):
    path = Path(path)
    data = {'exists': path.exists(), 'basename': path.name, 'extension': path.suffix}
    if data['exists']:
        data.update(kind='file' if path.is_file() else 'directory', size=path.stat().st_size)
        if path.is_file() and data['size'] <= max_hash_bytes:
            data['hash'] = hashlib.sha256(path.read_bytes()).hexdigest()
    return abstract_state('filesystem', data, artifact_ref)


def sample_from_trace(trace, *, before=None, after=None, verification=None, provenance=None):
    before = before or SemanticState(trace.get('before_state_ref'))
    after = after or SemanticState(trace.get('after_state_ref'))
    outcome = trace.get('outcome', 'uncertain')
    if outcome == 'executed_unverified':
        outcome = 'uncertain'
    args = normalized(trace.get('arguments', {}))
    raw_result_ref = trace.get('after_state_ref')  # Reference to the stored raw result
    return TransitionSample(state_before=before, state_after=after,
        operation=Operation(trace.get('tool', ''), trace.get('route', ''),
            normalized(trace.get('semantic_anchor') or {}),
            semantic_target_family(trace.get('tool', ''), args) or '',
            trace.get('operation_family') or trace.get('tool', ''), args,
            trace.get('effect', 'unknown'), normalized(trace.get('scope', {})),
            trace.get('dependencies', {}), trace.get('boundary_signals', [])),
        delta=StateDelta.between(before, after), verification=verification or Verification(
            EvidenceStrength.SAME_SESSION_SEMANTIC_OBSERVATION if trace.get('tool') == 'browser_snapshot' else EvidenceStrength.TOOL_ACK_ONLY),
        outcome=TransitionOutcome(outcome),
        provenance=provenance or Provenance(task_id=trace.get('task_id'), run_id=trace.get('run_id'),
            operation_id=trace.get('operation_id'), runtime=trace.get('runtime', trace.get('route', '')),
            authority_origin=AuthorityOrigin.ENVIRONMENT, trust_class='runtime_observation'),
        metrics=Metrics(trace.get('duration_ms'), trace.get('provider_usage') or {}),
        raw_result_ref=raw_result_ref)
