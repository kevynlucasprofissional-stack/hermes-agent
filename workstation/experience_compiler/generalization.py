"""Structural anti-unification and conservative positive/negative action models."""
from dataclasses import dataclass, field
from pathlib import PurePosixPath
import re
from urllib.parse import urlsplit

from .models import StateDelta, normalized

_INSTANCE_FIELDS = {'url', 'path', 'src', 'dst', 'source', 'destination', 'content', 'text',
                    'value', 'email', 'pr', 'pr_number', 'repo', 'customer_id'}
_INCIDENTAL = {'clock', 'timestamp', 'scroll', 'notification_count', 'incidental', 'url',
               'hash', 'sha256', 'size', 'basename', 'extension'}


@dataclass
class Generalization:
    template: dict
    schema: dict
    bindings: list[dict]
    relations: list[dict] = field(default_factory=list)


def anti_unify(examples):
    if not examples or len(examples) > 64:
        raise ValueError('bounded examples required')
    examples = [normalized(e) for e in examples]
    properties, bindings, relations = {}, [{} for _ in examples], []

    def variable(values, name, fmt=None):
        base = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        name = base
        suffix = 1
        while name in properties:
            suffix += 1
            name = base + str(suffix)
        types = {type(v) for v in values}
        if len(types) != 1 or next(iter(types)) not in {str, int, float, bool}:
            raise ValueError('incompatible parameter types')
        kind = {str: 'string', int: 'integer', float: 'number', bool: 'boolean'}[type(values[0])]
        definition = {'type': kind}
        if fmt:
            definition['format'] = fmt
        if kind == 'integer' and all(v > 0 for v in values):
            definition['minimum'] = 1
        if kind == 'string' and fmt not in {'path'}:
            definition['enum'] = sorted(set(values))
        properties[name] = definition
        for binding, value in zip(bindings, values):
            binding[name] = value
        return '$inputs.' + name

    def visit(values, field_name='root', path='root'):
        if all(v == values[0] for v in values):
            return values[0]
        if all(isinstance(v, dict) for v in values):
            keys = set(values[0])
            if any(set(v) != keys for v in values):
                raise ValueError('different structure requires a branch')
            return {k: visit([v[k] for v in values], k, path + '_' + k) for k in sorted(keys)}
        if all(isinstance(v, list) for v in values):
            if len({len(v) for v in values}) != 1:
                raise ValueError('different sequences require alignment')
            return [visit([v[i] for v in values], field_name, path + str(i)) for i in range(len(values[0]))]
        if field_name not in _INSTANCE_FIELDS:
            raise ValueError('contract differences cannot become parameters: ' + field_name)
        if field_name == 'url':
            urls = [urlsplit(v) for v in values]
            if any(u.username or u.password or u.query or u.fragment for u in urls):
                raise ValueError('unsafe URL cannot be generalized')
            if len({(u.scheme, u.netloc) for u in urls}) != 1:
                raise ValueError('host/route generalization is forbidden')
            parts = [u.path.split('/') for u in urls]
            if len({len(p) for p in parts}) != 1:
                raise ValueError('different page families')
            result = []
            for i, column in enumerate(zip(*parts)):
                if len(set(column)) == 1:
                    result.append(column[0])
                elif all(v.isdigit() for v in column):
                    result.append(variable([int(v) for v in column], 'url_number_' + str(i)))
                elif i > 0 and parts[0][i-1] in {'pull', 'issues'}:
                    raise ValueError('numeric entity contract required')
                else:
                    result.append(variable(list(column), 'url_segment_' + str(i)))
            return urls[0].scheme + '://' + urls[0].netloc + '/'.join(result)
        if field_name in {'path', 'src', 'dst', 'source', 'destination'}:
            paths = [PurePosixPath(v.replace('\\', '/')) for v in values]
            if len({str(p.parent) for p in paths}) != 1:
                raise ValueError('path scope differs')
            return variable(values, field_name, 'path')
        return variable(values, field_name)

    template = visit(examples)
    names = list(properties)
    for i, a in enumerate(names):
        for b in names[i+1:]:
            av, bv = [x[a] for x in bindings], [x[b] for x in bindings]
            if av == bv:
                relations.append({'relation': 'equal', 'left': a, 'right': b})
            if properties[a].get('format') == properties[b].get('format') == 'path':
                for relation, getter in [('basename_equal', lambda p: PurePosixPath(p.replace('\\', '/')).name),
                                         ('extension_equal', lambda p: PurePosixPath(p.replace('\\', '/')).suffix)]:
                    if all(getter(x) == getter(y) for x, y in zip(av, bv)):
                        relations.append({'relation': relation, 'left': a, 'right': b})
    return Generalization(template, {'type': 'object', 'properties': properties,
        'required': sorted(properties), 'additionalProperties': False}, bindings, relations)


@dataclass
class ActionModel:
    preconditions: dict
    effects: dict
    failure_discriminated: bool = False
    unresolved_counterexamples: int = 0


def _intersection(dicts):
    return {k: v for k, v in dicts[0].items() if k not in _INCIDENTAL
            and all(k in d and d[k] == v for d in dicts[1:])} if dicts else {}


def infer_action_model(successes, failures=()):
    pre = _intersection([t[0].state_before.semantic_predicates for t in successes])
    effects = []
    for trace in successes:
        delta = StateDelta.between(trace[0].state_before, trace[-1].state_after)
        changed = {**delta.added, **{k: v[1] for k, v in delta.changed.items()}}
        verified = trace[-1].verification.verified_predicates
        effects.append({k: v for k, v in changed.items() if k in verified and verified[k] == v})
    unresolved = sum(not any(k in t[0].state_before.semantic_predicates
        and t[0].state_before.semantic_predicates[k] != v for k, v in pre.items()) for t in failures)
    return ActionModel(pre, _intersection(effects), bool(failures) and unresolved == 0, unresolved)


def validate_inputs(schema, relations, inputs):
    """Enforce the bounded schema/relations this compiler emits, before any effect."""
    props = schema.get('properties', {})
    if any(k not in inputs for k in schema.get('required', [])):
        raise ValueError('missing learned capability parameter')
    if schema.get('additionalProperties') is False and inputs.keys() - props.keys():
        raise ValueError('unexpected learned capability parameter')
    for key, definition in props.items():
        if key not in inputs:
            continue
        value = inputs[key]
        typ = definition['type']
        if not {'integer': type(value) is int, 'number': type(value) in {int, float},
                'boolean': type(value) is bool, 'string': isinstance(value, str)}.get(typ, False):
            raise ValueError('learned parameter type mismatch: ' + key)
        if 'enum' in definition and value not in definition['enum']:
            raise ValueError('learned parameter domain mismatch')
        if 'minimum' in definition and value < definition['minimum']:
            raise ValueError('learned parameter outside numeric domain')
    for relation in relations:
        a, b = inputs[relation['left']], inputs[relation['right']]
        kind = relation['relation']
        if kind == 'basename_equal':
            a, b = PurePosixPath(a.replace('\\', '/')).name, PurePosixPath(b.replace('\\', '/')).name
        elif kind == 'extension_equal':
            a, b = PurePosixPath(a.replace('\\', '/')).suffix, PurePosixPath(b.replace('\\', '/')).suffix
        elif kind != 'equal':
            raise ValueError('unknown learned relation')
        if a != b:
            raise ValueError('learned parameter relation violated')
