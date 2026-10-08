"""Progressive artifact capture; observation never implies promotion."""
import logging
from .models import TransitionSample, TransitionOutcome, Operation, Provenance, SemanticState, Verification
from .corpus import ExperienceCorpus
from .state_abstraction import abstract_state

logger = logging.getLogger(__name__)


def capture_progressive(artifacts, *, task_id, run_id, operation_id, primitive, route, outcome,
                        state=None, evidence_refs=(), verification=None):
    if not task_id or not run_id or not operation_id:
        return None
    sample = TransitionSample(operation=Operation(primitive=primitive, canonical_route=route),
        state_after=abstract_state(route, state or {}),
        outcome=TransitionOutcome(outcome), provenance=Provenance(task_id=task_id, run_id=str(run_id),
            operation_id=operation_id, source="progressive_owner", trust_class="trusted_runtime"),
        verification=verification or Verification(evidence_refs=list(evidence_refs)))
    try:
        return ExperienceCorpus(artifacts).capture(sample)
    except (OSError, ValueError):
        logger.warning("Progressive learning capture failed", exc_info=True)
        return None
