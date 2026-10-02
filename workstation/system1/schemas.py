"""Standard Question Schemas for System-1 decisions (Laya).

Defines bounded, versioned semantic decision schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from workstation.system1.contracts import NeutralChoice

SCHEMA_VERSION = "1.0.0"

# 1. Capability Family Schema
CAPABILITY_FAMILY_QUESTION = {
    "type": "choice",
    "instructions": "Which operational capability family is most appropriate for this objective and state?",
    "criteria": {
        "browser": "Browser navigation, interaction, web data extraction, clicking or reading web pages",
        "filesystem": "File read, write, create, patch, directory inspection",
        "shell": "Terminal command execution, CLI tools, subprocess management",
        "editor": "Code editing, file modification, syntax refactoring",
        "system": "System state inspection, environment configuration, process control",
        NeutralChoice.NO_MATCH.value: "No known capability family matches this request",
        NeutralChoice.ABSTAIN.value: "Uncertain or conflicting signals; escalate",
    },
}

# 2. Needs System-2 Reasoning Schema
NEEDS_SYSTEM2_QUESTION = {
    "type": "choice",
    "instructions": "Does this operational decision require System-2 (LLM) reasoning?",
    "criteria": {
        "yes": "Novel strategy, multi-step synthesis, open ambiguity, or unfamiliar domain",
        "no": "Known deterministic path, closed ranking, or verified capability exists",
        NeutralChoice.ABSTAIN.value: "Uncertain; default to safety and consult System-2",
    },
}

# 3. Ambiguity / Reasoning Gap Kind Schema
AMBIGUITY_KIND_QUESTION = {
    "type": "choice",
    "instructions": "What is the primary nature of the reasoning gap or execution impediment?",
    "criteria": {
        "none": "No ambiguity; execution can proceed",
        "missing_information": "A required parameter, resource ID, or predicate is missing",
        "wrong_operation_family": "The declared intent does not match the available capabilities",
        "known_recovery": "A routine error occurred that matches a known deterministic recovery path",
        "conflicting_goal": "Constraints or user requirements are contradictory",
        "novel_strategy": "An unprecedented problem requiring novel decomposition and synthesis",
        NeutralChoice.ABSTAIN.value: "Cannot categorize ambiguity with confidence",
    },
}

# 4. Progress / No-Progress Schema
PROGRESS_CLASS_QUESTION = {
    "type": "choice",
    "instructions": "Has the recent state transition achieved meaningful progress toward the objective?",
    "criteria": {
        "progressing": "Pending work reduced, verifiable side-effect committed, or new evidence observed",
        "stalled": "No change in state, no new evidence, or identical error repeated",
        "loop_suspected": "Alternating or repeating states without pending work reduction",
        "repetition": "Identical tool or candidate requested without intervening state change",
        NeutralChoice.ABSTAIN.value: "Uncertain progress signal",
    },
}

# 5. Known Recovery Path Schema
KNOWN_RECOVERY_PATH_QUESTION = {
    "type": "choice",
    "instructions": "Which recovery action is appropriate for this failure?",
    "criteria": {
        "none": "No recovery needed or failure is unrecoverable",
        "reprobe_state": "Fresh observation or readback needed before attempting action",
        "switch_alternative": "Current candidate failed; try next certifiable candidate in shortlist",
        "escalate_to_system2": "Novel failure requiring LLM replanning or user clarification",
        NeutralChoice.ABSTAIN.value: "Uncertain; fallback to standard handler",
    },
}

STANDARD_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "capability_family": {"capability_family": CAPABILITY_FAMILY_QUESTION},
    "needs_system2": {"needs_system2": NEEDS_SYSTEM2_QUESTION},
    "ambiguity_kind": {"ambiguity_kind": AMBIGUITY_KIND_QUESTION},
    "progress_class": {"progress_class": PROGRESS_CLASS_QUESTION},
    "known_recovery_path": {"known_recovery_path": KNOWN_RECOVERY_PATH_QUESTION},
}


def build_candidate_ranking_schema(
    candidates: List[str],
    instructions: Optional[str] = None,
    max_candidates: int = 20,
) -> Dict[str, Any]:
    """Construct a dynamic closed choice question for ranking candidate capabilities.

    Caps choices to <= max_candidates and includes neutral choices.
    """
    bounded_candidates = candidates[:max_candidates]
    criteria: Dict[str, str] = {}
    for c in bounded_candidates:
        criteria[c] = f"Candidate capability: {c}"

    # Neutral choices
    criteria[NeutralChoice.NO_MATCH.value] = "None of the provided candidates are appropriate"
    criteria[NeutralChoice.ABSTAIN.value] = "Uncertain between multiple candidates; abstain"

    return {
        "preferred_candidate": {
            "type": "choice",
            "instructions": instructions or "Select the best candidate capability for the objective and state.",
            "criteria": criteria,
        }
    }
