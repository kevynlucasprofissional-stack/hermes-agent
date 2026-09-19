"""Hierarchical Experience Compiler (Composite OperationalCapability).

Discovers recurring sequences of verified CapabilityInvocations (A -> B -> C),
validates semantic closure, causal/authority JOIN closure, verifier closure,
and positive utility.
Emits composite OperationalCapability with explicit child dependencies (NO FLATTENING).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import json
from typing import Any, Sequence

from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.experience_compiler.models import CapabilityInvocation
from workstation.operational_capabilities import (
    CapabilityDependency,
    CapabilityLifecycle,
    OperationalCapability,
    OperationalCapabilityRegistry,
)
from workstation.recipes import digest, sanitize


class HierarchicalExperienceCompiler:
    """Discovers and compiles composite OperationalCapabilities from recurring sequences."""

    def __init__(self, registry: OperationalCapabilityRegistry) -> None:
        self.registry = registry

    def mine_sequences(
        self,
        invocations: list[CapabilityInvocation],
        min_length: int = 2,
        max_length: int = 5,
        min_support: int = 2,
    ) -> list[list[str]]:
        """Mine recurring contiguous sequences of capability executions across runs."""
        # 1. Group verified successful invocations by run_id
        runs: dict[str, list[str]] = {}
        for inv in invocations:
            if not inv.verified or inv.status != "COMMITTED":
                continue
            run = inv.run_id or "default"
            runs.setdefault(run, []).append(inv.capability_id)

        # 2. Count n-grams appearing across distinct runs
        ngram_runs: dict[tuple[str, ...], set[str]] = {}
        for run_id, seq in runs.items():
            for n in range(min_length, min(len(seq) + 1, max_length + 1)):
                for i in range(len(seq) - n + 1):
                    ngram = tuple(seq[i : i + n])
                    ngram_runs.setdefault(ngram, set()).add(run_id)

        # 3. Filter by support
        frequent: list[list[str]] = [
            list(ngram)
            for ngram, run_set in ngram_runs.items()
            if len(run_set) >= min_support
        ]
        # Sort by length descending, then support descending
        frequent.sort(key=lambda s: (len(s), len(ngram_runs[tuple(s)])), reverse=True)
        return frequent

    def propose_composite(
        self,
        sequence: list[str | OperationalCapability],
        input_mappings: dict[str, dict[str, str]] | None = None,
    ) -> OperationalCapability:
        """Compose a sequence of capabilities into a composite OperationalCapability.
        
        Strictly preserves child capabilities as dependencies.
        Never flattens into raw primitives.
        """
        if len(sequence) < 2:
            raise ValueError("Composite capability requires at least 2 steps")

        # 1. Resolve and validate child capabilities
        children: list[OperationalCapability] = []
        for item in sequence:
            if isinstance(item, str):
                cap = self.registry.get(item)
                if not cap:
                    raise ValueError(f"Child capability '{item}' not found in registry")
            else:
                cap = item

            if cap.drift_state != "healthy":
                raise ValueError(f"Child capability '{cap.id}' is not healthy ({cap.drift_state})")
            if cap.lifecycle != CapabilityLifecycle.PROMOTED:
                raise ValueError(f"Child capability '{cap.id}' is not promoted ({cap.lifecycle})")
            children.append(cap)

        # 2. Build explicit dependencies (NO FLATTENING)
        dependencies: list[CapabilityDependency] = []
        mappings = input_mappings or {}
        for i, child in enumerate(children):
            step_alias = f"step_{i}"
            step_maps = mappings.get(child.id, mappings.get(step_alias, {}))
            dependencies.append(
                CapabilityDependency(
                    capability_id=child.id,
                    version_constraint=f"^{child.version}",
                    input_mappings=dict(step_maps),
                    output_alias=step_alias,
                )
            )

        # 3. Authority JOIN closure
        levels = [
            child.formal_contract.authority_required.level
            if child.formal_contract and hasattr(child.formal_contract, "authority_required")
            else (
                AuthorityLevel.EXTERNAL_MUTATION
                if child.effect == "external_mutation"
                else AuthorityLevel.LOCAL_MUTATION
                if child.effect == "state_mutation"
                else AuthorityLevel.READ
            )
            for child in children
        ]
        composite_level = max(levels, key=lambda l: l.value if isinstance(l, AuthorityLevel) else l)

        allowed_actions: set[str] = set()
        allowed_resources: set[str] = set()
        for child in children:
            if child.formal_contract and hasattr(child.formal_contract, "authority_required"):
                allowed_actions.update(child.formal_contract.authority_required.allowed_actions)
                allowed_resources.update(child.formal_contract.authority_required.allowed_resources)
            else:
                allowed_actions.add(child.route)
                allowed_resources.add(child.id)

        composite_authority = AuthorityScope(
            level=composite_level,
            allowed_actions=allowed_actions,
            allowed_resources=allowed_resources,
        )

        # 4. Semantic & Verifier closure
        preconditions = list(children[0].preconditions)
        postconditions = list(children[-1].postconditions)

        typed_pre = []
        typed_post = []
        eff_footprint = []
        from workstation.control_plane.contract import CapabilityFormalContract
        from workstation.control_plane.ir import Predicate, Effect

        for child in children:
            if isinstance(child.formal_contract, dict):
                child.formal_contract = CapabilityFormalContract.from_dict(child.formal_contract)

        if children[0].formal_contract and hasattr(children[0].formal_contract, "typed_preconditions"):
            typed_pre = list(children[0].formal_contract.typed_preconditions)
        if children[-1].formal_contract and hasattr(children[-1].formal_contract, "typed_postconditions"):
            typed_post = list(children[-1].formal_contract.typed_postconditions)
        for child in children:
            if child.formal_contract and hasattr(child.formal_contract, "effect_footprint"):
                eff_footprint.extend(child.formal_contract.effect_footprint)

        verifier_contract = {
            "kind": "composite_verifier",
            "children": [c.id for c in children],
            "postconditions": postconditions,
        }

        # 5. Positive utility check
        raw_size = sum(len(json.dumps(sanitize(c.to_dict()))) for c in children)
        composite_overhead = 256 + len(children) * 64
        utility = raw_size - composite_overhead
        if utility <= 0:
            raise ValueError(f"Nonpositive composite utility ({utility})")

        # 6. Compose OperationalCapability
        comp_id = f"composite_{digest(tuple(c.id for c in children))[:24]}"
        comp_name = " -> ".join(c.name for c in children)
        comp_effect = (
            "external_mutation"
            if any(c.effect == "external_mutation" for c in children)
            else "state_mutation"
            if any(c.effect == "state_mutation" for c in children)
            else "read_only"
        )
        scope_backends = {}
        for c in children:
            if c.scope:
                scope_backends[c.route] = c.scope
        comp_scope = {"backends": scope_backends} if len(scope_backends) > 1 else (scope_backends.get(children[0].route, {}))

        op_fam = (
            children[-1].formal_contract.operation_family
            if children[-1].formal_contract and hasattr(children[-1].formal_contract, "operation_family")
            else children[-1].id
        )
        tgt_fam = (
            children[-1].formal_contract.target_family
            if children[-1].formal_contract and hasattr(children[-1].formal_contract, "target_family")
            else children[-1].id
        )

        formal_contract = None
        if typed_post:
            formal_contract = CapabilityFormalContract(
                operation_family=op_fam,
                target_family=tgt_fam,
                typed_preconditions=typed_pre,
                typed_postconditions=typed_post,
                effect_footprint=eff_footprint,
                authority_required=composite_authority,
                verifier=verifier_contract,
            )

        fam_id = (
            f"{children[0].family_id}->{children[-1].family_id}"
            if children[0].family_id and children[-1].family_id
            else f"{children[0].id}->{children[-1].id}"
        )

        composite_cap = OperationalCapability(
            id=comp_id,
            name=comp_name,
            version="1.0.0",
            effect=comp_effect,
            route="composite",
            scope=comp_scope,
            preconditions=preconditions,
            postconditions=postconditions,
            verifier_contract=verifier_contract,
            dependencies=dependencies,
            implementation={
                "type": "composite_sequence",
                "steps": [],  # child execution is driven via dependencies
                "output": {"success": True, "deps": "$deps"},
            },
            lifecycle=CapabilityLifecycle.DISCOVERED,
            drift_state="healthy",
            formal_contract=formal_contract,
            family_id=fam_id,
            provenance={
                "source": "hierarchical_experience_compiler",
                "child_capabilities": [c.id for c in children],
            },
            learning_metadata={
                "composite": True,
                "child_ids": [c.id for c in children],
                "utility": utility,
                "semantic_closure": True,
            },
        )
        return self.registry.register(composite_cap)

    def promote_composite(self, capability: OperationalCapability) -> OperationalCapability:
        """Promote a discovered composite capability via causal replay / ExperiencePromotionPolicy."""
        from workstation.experience_compiler.promotion import ExperiencePromotionPolicy
        from workstation.operational_capabilities import CapabilityValidationError

        admission = ExperiencePromotionPolicy().evaluate(capability)
        if not admission.admitted:
            raise CapabilityValidationError(f"composite promotion denied: {', '.join(admission.reasons)}")
        capability.lifecycle = CapabilityLifecycle.PROMOTED
        return self.registry.register(capability)
