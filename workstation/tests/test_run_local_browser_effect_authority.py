"""EC-03: native browser navigation must not be admitted as a read-only adoption."""

from workstation.control_plane.ir import CALL
from workstation.run_adoption import effects_for_step


def test_browser_navigation_requires_effect_and_readback():
    effect = effects_for_step(
        "browser_navigate", {"url": "https://trello.com/"}, {"host": "trello.com"}
    )
    assert effect == [CALL("browser.navigate", "trello.com")]


def test_browser_navigation_rejects_out_of_scope_or_unverifiable_destination():
    assert effects_for_step(
        "browser_navigate", {"url": "https://another.example/"}, {"host": "trello.com"}
    ) is None
    assert effects_for_step(
        "browser_navigate", {"url": "https://trello.com/"}, {}
    ) is None
    assert effects_for_step(
        "browser_navigate", {"url": "javascript:alert(1)"}, {"host": "trello.com"}
    ) is None

from workstation.artifacts import ArtifactStore
from workstation.control_plane.lattice import AuthorityScope, AuthorityLevel
from workstation.run_adoption import (
    AdoptionOffer, CanonicalRunSnapshot, DurableRunAdoptionOwner,
    PendingRunItem, plan_item_adoption,
)


def test_browser_navigation_requires_canonical_owner_readback_before_adoption(tmp_path):
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    owner = DurableRunAdoptionOwner(
        lambda: None, artifact_store,
        authority_for_task=lambda task: AuthorityScope(),
        dispatch_fn=lambda *args: None,
        supported_primitives=("browser_navigate",),
        readback_primitives=(),  # owner does not certify browser state
    )
    offer = AdoptionOffer(
        offer_id="offer", task_id="task", run_id="run", candidate_id="cap",
        proof=None, steps=[{
            "id": "navigate", "primitive": "browser_navigate",
            "args": {"url": "$inputs.url"},
        }],
        input_schema={"type": "object", "properties": {"url": {"type": "string"}},
                      "required": ["url"]},
        relations=[], operation_family="browser.open_site",
        target_family="native_browser", route="native_browser",
        scope={"host": "trello.com"},
    )
    snap = CanonicalRunSnapshot(
        task_id="task", run_id="run", plan_id="plan",
        authority=AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE,
                                 allowed_actions={"*"}, allowed_resources={"*"}),
        effect_budget=(CALL("browser.navigate", "trello.com"),),
        lease_valid=True, termination="", uncertain_mutations=(),
        pending_items=(PendingRunItem(
            item_id="item", item_index=0, payload={"url": "https://trello.com/"},
            status="pending", attempts=0, has_checkpoints=False,
            operation_family="browser.open_site", target_family="native_browser",
        ),),
        remaining_items_ref="artifact://tasks/task/pending",
        allowed_targets=frozenset({"native_browser"}),
    )
    plan, reasons = plan_item_adoption(snap, offer, owner)
    assert plan is None
    assert reasons == ["readback_unavailable:browser_navigate"]

    # Once a real independent verifier exists, the canonical lease and the
    # exact effect budget must still be revalidated before any dispatch.
    from dataclasses import replace

    owner._readback = lambda *_: {"ok": True}
    owner._readback_primitives.add("browser_navigate")
    plan, reasons = plan_item_adoption(replace(snap, lease_valid=False), offer, owner)
    assert plan is None and reasons == ["lease_not_valid"]
    plan, reasons = plan_item_adoption(replace(snap, effect_budget=()), offer, owner)
    assert plan is None and reasons == ["effect_budget_missing"]


def test_browser_extract_items_requires_readback_without_mutable_effects(tmp_path):
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    owner = DurableRunAdoptionOwner(
        lambda: None, artifact_store,
        authority_for_task=lambda task: AuthorityScope(),
        dispatch_fn=lambda *args: None,
        supported_primitives=("browser_extract_items",),
        readback_primitives=(),  # owner cannot read back browser_extract_items
    )
    offer = AdoptionOffer(
        offer_id="offer", task_id="task", run_id="run", candidate_id="cap",
        proof=None, steps=[{
            "id": "extract", "primitive": "browser_extract_items",
            "args": {"selector": "$inputs.selector"},
        }],
        input_schema={"type": "object", "properties": {"selector": {"type": "string"}},
                      "required": ["selector"]},
        relations=[], operation_family="browser.extract",
        target_family="native_browser", route="native_browser",
        scope={},
    )
    snap = CanonicalRunSnapshot(
        task_id="task", run_id="run", plan_id="plan",
        authority=AuthorityScope(level=AuthorityLevel.READ,
                                 allowed_actions={"*"}, allowed_resources={"*"}),
        effect_budget=(),
        lease_valid=True, termination="", uncertain_mutations=(),
        pending_items=(PendingRunItem(
            item_id="item", item_index=0, payload={"selector": "div.card"},
            status="pending", attempts=0, has_checkpoints=False,
            operation_family="browser.extract", target_family="native_browser",
        ),),
        remaining_items_ref="artifact://tasks/task/pending",
        allowed_targets=frozenset({"native_browser"}),
    )
    plan, reasons = plan_item_adoption(snap, offer, owner)
    assert plan is None
    assert reasons == ["readback_unavailable:browser_extract_items"]


def test_compiled_read_is_not_verified_when_readback_fails(tmp_path):
    from workstation.durable_tasks import DurableTaskStore, WorkItemStatus
    from workstation.run_adoption import RunLocalAdopter
    from workstation.run_closure import RunClosureProof

    store = DurableTaskStore()
    plan_obj = store.create_plan(
        task_id="task_fail", title="Extract Test", items=[{"selector": "article.card"}], session_id="run_1"
    )
    work_items = store.get_work_items(plan_obj.id)
    item_id = work_items[0].id
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    owner = DurableRunAdoptionOwner(
        lambda: store, artifact_store,
        authority_for_task=lambda task: AuthorityScope(level=AuthorityLevel.READ),
        dispatch_fn=lambda tool, args: '{"success": true}',
        readback_fn=lambda prim, args, raw: {"ok": False, "evidence_ref": None},
        supported_primitives=("browser_extract_items",),
        readback_primitives=("browser_extract_items",),
    )
    proof = RunClosureProof(
        task_id="task_fail",
        run_id="run_1",
        operation_id="op_1",
        semantic_fingerprint="fp",
        operation_family="browser.extract",
        target_family="native_browser",
        deterministic_representation_ref="artifact://tasks/task_fail/det.json",
        executable_primitive_or_capability="browser_extract_items",
        compatible_route="native_browser",
        authority_scope=AuthorityScope(level=AuthorityLevel.READ),
        effect_budget=(),
        verifier_contract={},
        first_verified_evidence_ref="artifact://tasks/task_fail/v1.json",
        replay_evidence_ref="artifact://tasks/task_fail/v2.json",
        uncertainty_clear=True,
        parameter_schema={},
        bindings={},
        remaining_items_ref="artifact://tasks/task_fail/pending",
        remaining_item_count=1,
        expected_operational_utility=10.0,
    )
    offer = AdoptionOffer(
        offer_id="off_fail", task_id="task_fail", run_id="run_1", candidate_id="cand_1",
        proof=proof, steps=[{
            "id": "step1", "primitive": "browser_extract_items",
            "args": {"selector": "$inputs.selector"},
        }],
        input_schema={"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]},
        relations=[], operation_family="browser.extract", target_family="native_browser",
        route="native_browser", scope={},
    )
    snap = CanonicalRunSnapshot(
        task_id="task_fail", run_id="run_1", plan_id=plan_obj.id,
        authority=AuthorityScope(level=AuthorityLevel.READ),
        effect_budget=(), lease_valid=True, termination="", uncertain_mutations=(),
        pending_items=(PendingRunItem(
            item_id=item_id, item_index=0, payload={"selector": "article.card"},
            status="pending", attempts=0, has_checkpoints=False,
            operation_family="browser.extract", target_family="native_browser",
        ),),
        remaining_items_ref="", allowed_targets=frozenset({"native_browser"}),
    )
    plan, _reasons = plan_item_adoption(snap, offer, owner)
    assert plan is not None
    adopter = RunLocalAdopter(owner, None)
    result = adopter._execute_item(offer, snap, plan)
    assert result["verified"] is False
    assert bool(result.get("failure"))
