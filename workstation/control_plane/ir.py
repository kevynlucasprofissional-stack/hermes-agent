"""Typed, declarative, canonicalizable Predicate and Effect Intermediate Representations (IR).

Strictly deterministic, bounded, verifiable. Arbitrary Python/JS execution is strictly forbidden.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Sequence


def _lookup_path(state: Any, path: str) -> tuple[bool, Any]:
    """Resolve dotted path in state dictionary or object, returning (found, value)."""
    if not path:
        return True, state
    parts = path.split(".")
    curr = state
    for part in parts:
        if isinstance(curr, dict):
            if part in curr:
                curr = curr[part]
            else:
                return False, None
        elif isinstance(curr, (list, tuple)):
            try:
                idx = int(part)
                if 0 <= idx < len(curr):
                    curr = curr[idx]
                else:
                    return False, None
            except ValueError:
                return False, None
        elif hasattr(curr, part):
            curr = getattr(curr, part)
        else:
            return False, None
    return True, curr


class Predicate(ABC):
    """Abstract base class for all typed, serializable predicates."""

    @abstractmethod
    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        """Evaluate predicate deterministically against observed semantic state."""
        ...

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Serialize predicate to a dictionary."""
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Predicate:
        """Deserialize dictionary to a concrete Predicate."""
        pred_type = data.get("type")
        if pred_type == "TRUE":
            return TRUE()
        if pred_type == "FALSE":
            return FALSE()
        if pred_type == "EQ":
            return EQ(data["path"], data["value"])
        if pred_type == "NEQ":
            return NEQ(data["path"], data["value"])
        if pred_type == "EXISTS":
            return EXISTS(data["path"])
        if pred_type == "ABSENT":
            return ABSENT(data["path"])
        if pred_type == "AND":
            return AND(*(cls.from_dict(o) for o in data.get("operands", [])))
        if pred_type == "OR":
            return OR(*(cls.from_dict(o) for o in data.get("operands", [])))
        if pred_type == "NOT":
            return NOT(cls.from_dict(data["operand"]))
        if pred_type == "IN":
            return IN(data["item"], data["collection_path"])
        if pred_type == "SUBSET":
            return SUBSET(data["subset"], data["collection_path"])
        if pred_type == "LT":
            return LT(data["path"], data["value"])
        if pred_type == "LTE":
            return LTE(data["path"], data["value"])
        if pred_type == "GT":
            return GT(data["path"], data["value"])
        if pred_type == "GTE":
            return GTE(data["path"], data["value"])
        if pred_type == "UNCHANGED":
            return UNCHANGED(data["path"])
        if pred_type == "TRANSITION":
            return TRANSITION(data["path"], data["before"], data["after"])
        raise ValueError(f"Unknown predicate type: {pred_type}")

    def canonical_json(self) -> str:
        """Deterministic canonical JSON representation."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def fingerprint(self) -> str:
        """Stable SHA-256 fingerprint."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Predicate):
            return False
        return self.canonical_json() == other.canonical_json()

    def __hash__(self) -> int:
        return hash(self.canonical_json())


class TRUE(Predicate):
    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        return True

    def to_dict(self) -> dict[str, Any]:
        return {"type": "TRUE"}


class FALSE(Predicate):
    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {"type": "FALSE"}


class EQ(Predicate):
    def __init__(self, path: str, value: Any):
        self.path = str(path)
        self.value = value

    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        found, val = _lookup_path(state, self.path)
        return found and val == self.value

    def to_dict(self) -> dict[str, Any]:
        return {"type": "EQ", "path": self.path, "value": self.value}


class NEQ(Predicate):
    def __init__(self, path: str, value: Any):
        self.path = str(path)
        self.value = value

    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        found, val = _lookup_path(state, self.path)
        return (not found) or (val != self.value)

    def to_dict(self) -> dict[str, Any]:
        return {"type": "NEQ", "path": self.path, "value": self.value}


class EXISTS(Predicate):
    def __init__(self, path: str):
        self.path = str(path)

    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        found, val = _lookup_path(state, self.path)
        if not found or val is None or val is False:
            return False
        if isinstance(val, dict) and val.get("exists") is False:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {"type": "EXISTS", "path": self.path}


class ABSENT(Predicate):
    def __init__(self, path: str):
        self.path = str(path)

    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        found, val = _lookup_path(state, self.path)
        if not found or val is None or val is False:
            return True
        if isinstance(val, dict) and val.get("exists") is False:
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {"type": "ABSENT", "path": self.path}


class AND(Predicate):
    def __init__(self, *operands: Predicate):
        # Flatten nested ANDs and sort canonically by canonical_json
        flat_ops: list[Predicate] = []
        for op in operands:
            if isinstance(op, AND):
                flat_ops.extend(op.operands)
            else:
                flat_ops.append(op)
        # Canonical sort
        self.operands = sorted(flat_ops, key=lambda p: p.canonical_json())

    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        return all(op.evaluate(state, context) for op in self.operands)

    def to_dict(self) -> dict[str, Any]:
        return {"type": "AND", "operands": [op.to_dict() for op in self.operands]}


class OR(Predicate):
    def __init__(self, *operands: Predicate):
        flat_ops: list[Predicate] = []
        for op in operands:
            if isinstance(op, OR):
                flat_ops.extend(op.operands)
            else:
                flat_ops.append(op)
        self.operands = sorted(flat_ops, key=lambda p: p.canonical_json())

    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        return any(op.evaluate(state, context) for op in self.operands)

    def to_dict(self) -> dict[str, Any]:
        return {"type": "OR", "operands": [op.to_dict() for op in self.operands]}


class NOT(Predicate):
    def __init__(self, operand: Predicate):
        self.operand = operand

    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        return not self.operand.evaluate(state, context)

    def to_dict(self) -> dict[str, Any]:
        return {"type": "NOT", "operand": self.operand.to_dict()}


class IN(Predicate):
    def __init__(self, item: Any, collection_path: str):
        self.item = item
        self.collection_path = str(collection_path)

    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        found, coll = _lookup_path(state, self.collection_path)
        if not found or not isinstance(coll, (list, tuple, set, dict)):
            return False
        return self.item in coll

    def to_dict(self) -> dict[str, Any]:
        return {"type": "IN", "item": self.item, "collection_path": self.collection_path}


class SUBSET(Predicate):
    def __init__(self, subset: Sequence[Any], collection_path: str):
        self.subset = list(subset)
        self.collection_path = str(collection_path)

    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        found, coll = _lookup_path(state, self.collection_path)
        if not found or not isinstance(coll, (list, tuple, set)):
            return False
        coll_set = set(coll)
        return all(item in coll_set for item in self.subset)

    def to_dict(self) -> dict[str, Any]:
        return {"type": "SUBSET", "subset": self.subset, "collection_path": self.collection_path}


class LT(Predicate):
    def __init__(self, path: str, value: Any):
        self.path = str(path)
        self.value = value

    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        found, val = _lookup_path(state, self.path)
        return found and val is not None and val < self.value

    def to_dict(self) -> dict[str, Any]:
        return {"type": "LT", "path": self.path, "value": self.value}


class LTE(Predicate):
    def __init__(self, path: str, value: Any):
        self.path = str(path)
        self.value = value

    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        found, val = _lookup_path(state, self.path)
        return found and val is not None and val <= self.value

    def to_dict(self) -> dict[str, Any]:
        return {"type": "LTE", "path": self.path, "value": self.value}


class GT(Predicate):
    def __init__(self, path: str, value: Any):
        self.path = str(path)
        self.value = value

    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        found, val = _lookup_path(state, self.path)
        return found and val is not None and val > self.value

    def to_dict(self) -> dict[str, Any]:
        return {"type": "GT", "path": self.path, "value": self.value}


class GTE(Predicate):
    def __init__(self, path: str, value: Any):
        self.path = str(path)
        self.value = value

    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        found, val = _lookup_path(state, self.path)
        return found and val is not None and val >= self.value

    def to_dict(self) -> dict[str, Any]:
        return {"type": "GTE", "path": self.path, "value": self.value}


class UNCHANGED(Predicate):
    def __init__(self, path: str):
        self.path = str(path)

    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        baseline = (context or {}).get("baseline_state", {})
        found_base, val_base = _lookup_path(baseline, self.path)
        found_curr, val_curr = _lookup_path(state, self.path)
        if not found_base and not found_curr:
            return True
        return found_base == found_curr and val_base == val_curr

    def to_dict(self) -> dict[str, Any]:
        return {"type": "UNCHANGED", "path": self.path}


class TRANSITION(Predicate):
    def __init__(self, path: str, before: Any, after: Any):
        self.path = str(path)
        self.before = before
        self.after = after

    def evaluate(self, state: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
        baseline = (context or {}).get("baseline_state", {})
        found_base, val_base = _lookup_path(baseline, self.path)
        found_curr, val_curr = _lookup_path(state, self.path)
        return found_base and val_base == self.before and found_curr and val_curr == self.after

    def to_dict(self) -> dict[str, Any]:
        return {"type": "TRANSITION", "path": self.path, "before": self.before, "after": self.after}


def entails(p1: Predicate, p2: Predicate) -> bool:
    """Check if p1 entails p2 (p1 => p2) under bounded algebraic logic."""
    if p1 == p2 or p1.fingerprint() == p2.fingerprint():
        return True
    if isinstance(p2, TRUE):
        return True
    if isinstance(p1, FALSE):
        return True
    if isinstance(p1, AND):
        # AND(A, B) entails C if any operand entails C
        if any(entails(op, p2) for op in p1.operands):
            return True
        # If p2 is also AND, p1 must entail every operand of p2
        if isinstance(p2, AND) and all(entails(p1, op2) for op2 in p2.operands):
            return True
    if isinstance(p2, OR):
        # p1 entails OR(A, B) if p1 entails any operand of p2
        if any(entails(p1, op) for op in p2.operands):
            return True
    if isinstance(p1, EQ) and isinstance(p2, EXISTS):
        # EQ(path, val) entails EXISTS(path)
        return p1.path == p2.path
    if isinstance(p1, EQ) and isinstance(p2, EQ):
        return p1.path == p2.path and p1.value == p2.value
    if isinstance(p1, TRANSITION) and isinstance(p2, EQ):
        # TRANSITION(path, before, after) entails EQ(path, after)
        return p1.path == p2.path and p1.after == p2.value
    return False


# =============================================================================
# Effect IR
# =============================================================================

class Effect(ABC):
    """Abstract base class for typed semantic effects."""

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Effect:
        kind = data.get("kind")
        if kind == "SET":
            return SET(data["path"], data.get("value"))
        if kind == "CREATE":
            return CREATE(data["resource"])
        if kind == "DELETE":
            return DELETE(data["resource"])
        if kind == "MOVE":
            return MOVE(data["source"], data["destination"])
        if kind == "CALL":
            return CALL(data["operation_family"], data["target"])
        if kind == "SEND":
            return SEND(data["channel"], data["target"])
        raise ValueError(f"Unknown effect kind: {kind}")

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def fingerprint(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Effect):
            return False
        return self.canonical_json() == other.canonical_json()

    def __hash__(self) -> int:
        return hash(self.canonical_json())


class SET(Effect):
    def __init__(self, path: str, value: Any = None):
        self.path = str(path)
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "SET", "path": self.path, "value": self.value}


class CREATE(Effect):
    def __init__(self, resource: str):
        self.resource = str(resource)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "CREATE", "resource": self.resource}


class DELETE(Effect):
    def __init__(self, resource: str):
        self.resource = str(resource)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "DELETE", "resource": self.resource}


class MOVE(Effect):
    def __init__(self, source: str, destination: str):
        self.source = str(source)
        self.destination = str(destination)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "MOVE", "source": self.source, "destination": self.destination}


class CALL(Effect):
    def __init__(self, operation_family: str, target: str):
        self.operation_family = str(operation_family)
        self.target = str(target)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "CALL", "operation_family": self.operation_family, "target": self.target}


class SEND(Effect):
    def __init__(self, channel: str, target: str):
        self.channel = str(channel)
        self.target = str(target)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "SEND", "channel": self.channel, "target": self.target}


def effect_contained(effect: Effect, budget: Sequence[Effect]) -> bool:
    """Check if effect is subsumed/allowed by the effect budget."""
    for b in budget:
        if effect == b:
            return True
        # Path/resource prefix containment: e.g. budget allows modifying "github.pull_request/123"
        if isinstance(effect, SET) and isinstance(b, SET):
            if b.path == "*" or effect.path == b.path or effect.path.startswith(b.path + "."):
                return True
        if isinstance(effect, CREATE) and isinstance(b, CREATE):
            if b.resource == "*" or effect.resource == b.resource or effect.resource.startswith(b.resource + "/"):
                return True
        if isinstance(effect, DELETE) and isinstance(b, DELETE):
            if b.resource == "*" or effect.resource == b.resource:
                return True
        if isinstance(effect, CALL) and isinstance(b, CALL):
            family_match = (b.operation_family == "*" or effect.operation_family == b.operation_family
                            or effect.operation_family.startswith(b.operation_family + "."))
            target_match = (b.target == "*" or effect.target == b.target)
            if family_match and target_match:
                return True
        if isinstance(effect, SEND) and isinstance(b, SEND):
            if (b.channel == "*" or effect.channel == b.channel) and (b.target == "*" or effect.target == b.target):
                return True
    return False


def preserves_invariant(effect: Effect, invariant: Predicate) -> bool:
    """Check if effect preserves invariant (returns False if effect definitely threatens invariant)."""
    if isinstance(invariant, TRUE):
        return True
    if isinstance(invariant, AND):
        return all(preserves_invariant(effect, op) for op in invariant.operands)

    if isinstance(invariant, UNCHANGED):
        # UNCHANGED(path) is violated if effect mutates path or prefix
        inv_path = invariant.path
        if isinstance(effect, SET):
            if effect.path == inv_path or effect.path.startswith(inv_path + ".") or inv_path.startswith(effect.path + "."):
                return False
        elif isinstance(effect, (DELETE, CREATE)):
            if effect.resource == inv_path or effect.resource.startswith(inv_path + "/") or inv_path.startswith(effect.resource + "/"):
                return False
        elif isinstance(effect, MOVE):
            if effect.source == inv_path or effect.destination == inv_path:
                return False

    if isinstance(invariant, ABSENT):
        # ABSENT(res) is violated if effect creates or sets res
        inv_res = invariant.path
        if isinstance(effect, CREATE) and (effect.resource == inv_res or effect.resource.startswith(inv_res + "/")):
            return False
        if isinstance(effect, SET) and (effect.path == inv_res or effect.path.startswith(inv_res + ".")):
            return False

    if isinstance(invariant, EXISTS):
        # EXISTS(res) is violated if effect deletes or moves away res
        inv_res = invariant.path
        if isinstance(effect, DELETE) and (effect.resource == inv_res or inv_res.startswith(effect.resource + "/")):
            return False
        if isinstance(effect, MOVE) and effect.source == inv_res:
            return False

    if isinstance(invariant, EQ):
        # EQ(path, val) is threatened if effect sets path to a different value
        if isinstance(effect, SET) and effect.path == invariant.path:
            if effect.value is not None and effect.value != invariant.value:
                return False
        if isinstance(effect, DELETE) and (effect.resource == invariant.path or invariant.path.startswith(effect.resource + "/")):
            return False

    return True
