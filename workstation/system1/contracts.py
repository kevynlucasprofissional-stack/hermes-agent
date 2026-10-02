"""Contracts and types for Workstation System-1 integration."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Dict, List, Optional

from agent.system1_decision import DecisionRequest, DecisionResult


class NeutralChoice(str, Enum):
    """Standard neutral options in closed choice schemas."""

    ABSTAIN = "ABSTAIN"
    NO_MATCH = "NO_MATCH"
    KEEP_CURRENT = "KEEP_CURRENT"
    NO_PREFERENCE = "NO_PREFERENCE"
    OTHER = "OTHER"


class AmbiguityKind(str, Enum):
    """Classification of reasoning gaps or ambiguity."""

    NONE = "none"
    MISSING_INFORMATION = "missing_information"
    WRONG_OPERATION_FAMILY = "wrong_operation_family"
    KNOWN_RECOVERY = "known_recovery"
    CONFLICTING_GOAL = "conflicting_goal"
    NOVEL_STRATEGY = "novel_strategy"


class ProgressClass(str, Enum):
    """Semantic classification of progress over sequential steps."""

    PROGRESSING = "progressing"
    STALLED = "stalled"
    LOOP_SUSPECTED = "loop_suspected"
    REPETITION = "repetition"


class DecisionInfluenceMode(str, Enum):
    """How a System-1 decision influenced the runtime execution path."""

    DIRECT = "direct"
    RANKING_ONLY = "ranking_only"
    FALLBACK = "fallback"
    SHADOW = "shadow"


def compute_state_hash(state: Any) -> str:
    """Compute a canonical SHA-256 hash of minimal state dictionary."""
    if not state:
        return "empty"
    try:
        serialized = json.dumps(state, sort_keys=True, default=str)
    except Exception:
        serialized = str(state)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def compute_candidate_set_hash(candidates: List[str]) -> str:
    """Compute a canonical hash of an ordered candidate set."""
    if not candidates:
        return "empty"
    serialized = ",".join(sorted(candidates))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
