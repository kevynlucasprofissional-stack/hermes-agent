import json
from types import SimpleNamespace

from tools.effects import ToolEffect, tool_effect
from workstation.batch_detection import record_mutation
from workstation.tests.test_durable_hardening import call


def agent(*, closure=True):
    proof = {
        'deterministic_representation': True, 'executable_primitive': True,
        'compatible_route': True, 'authority_policy_compatible': True,
        'verifier_readback': True, 'certified_dispatch': True,
        'uncertainty_clear': True,
    }
    return SimpleNamespace(
        valid_tool_names={'work_execute'}, _work_repeatability_hint=True,
        session_id='owner', _conversation_root_id=lambda: 'owner',
        operational_closure_for_call=(lambda _name, _args: proof) if closure else None,
    )


def test_repeatability_hint_does_not_block_stateful_browser():
    from workstation.execution_policy import CompilationDecision, decisions_for_calls
    a = agent()
    calls = [call(n, args) for n, args in [
        ('browser_navigate', {'url': 'https://example.com'}),
        ('browser_snapshot', {}), ('browser_type', {'ref': '@e32', 'text': 'hello'}),
        ('browser_press', {'key': 'Enter'}), ('browser_snapshot', {})]]
    assert all(d != CompilationDecision.REQUIRE_COMPILE for d in decisions_for_calls(a, calls))


def test_threshold_is_operation_scoped():
    from workstation.execution_policy import CompilationDecision, decisions_for_calls
    a = agent()
    calls = [call('write_file', {'path': 'output.json', 'content': f'x{i}'}) for i in range(4)]
    assert decisions_for_calls(a, calls) == [CompilationDecision.ALLOW_ADAPTIVE,
        CompilationDecision.SUGGEST_COMPILE, CompilationDecision.REQUIRE_COMPILE,
        CompilationDecision.REQUIRE_COMPILE]
    for i in range(2):
        record_mutation(a, 'write_file', {'path': 'output.json', 'content': f'x{i}'}, {'ok': True})
    assert decisions_for_calls(a, [calls[2]]) == [CompilationDecision.REQUIRE_COMPILE]
    assert decisions_for_calls(a, [call('browser_click', {'ref': '@e1'})]) == [CompilationDecision.ALLOW_ADAPTIVE]


def test_effects_have_one_authority():
    from agent.tool_guardrails import ToolCallGuardrailController
    guard = ToolCallGuardrailController()
    for name, expected in [('browser_snapshot', ToolEffect.PURE_READ),
                           ('browser_extract_items', ToolEffect.DISCOVERY),
                           ('browser_console', ToolEffect.MUTATION),
                           ('browser_type', ToolEffect.MUTATION)]:
        assert tool_effect(name) == expected
        assert guard._is_idempotent(name) == (expected in {ToolEffect.PURE_READ, ToolEffect.DISCOVERY})


def test_native_route_normalization_is_runtime_scoped():
    import pytest
    from workstation.routing import canonical_route_for_tool, require_allowed_route, ConstraintViolation
    assert canonical_route_for_tool('browser_type', runtime='internal') == 'native_browser'
    require_allowed_route('native_browser', {'allowed_routes': ['browser_type', 'browser_click']})
    with pytest.raises(ConstraintViolation):
        require_allowed_route('browser-exec', {'allowed_routes': ['browser_type']})
    assert canonical_route_for_tool('browser_unknown', runtime='internal') != 'native_browser'


def test_uncertain_adaptive_effect_requires_human():
    from workstation.execution_policy import CompilationDecision, decisions_for_calls
    a = agent()
    record_mutation(a, 'browser_press', {'key': 'Enter'}, {'error': 'connection lost'})
    assert decisions_for_calls(a, [call('browser_press', {'key': 'Enter'})]) == [CompilationDecision.REQUIRE_HUMAN]


def test_dispatched_adaptive_effect_survives_restart():
    from workstation.batch_detection import prepare_mutation
    from workstation.execution_policy import CompilationDecision, decisions_for_calls
    a = agent()
    prepare_mutation(a, 'browser_press', {'key': 'Enter'})
    restarted = agent()
    assert decisions_for_calls(restarted, [call('browser_press', {'key': 'Enter'})]) == [CompilationDecision.REQUIRE_HUMAN]


def test_final_arguments_cannot_bypass_dispatch_threshold():
    import pytest
    from workstation.batch_detection import prepare_mutation
    a = agent()
    for i in range(2):
        args = {'path': 'target.json', 'content': f'x{i}'}
        prepare_mutation(a, 'write_file', args)
        record_mutation(a, 'write_file', args, {'ok': True})
    with pytest.raises(RuntimeError, match='REQUIRE_COMPILE'):
        prepare_mutation(a, 'write_file', {'path': 'target.json', 'content': 'middleware_rewritten'})
    assert sum(a._work_mutation_shapes.values()) == 2


def test_heterogeneous_stateful_browser_never_requires_compile():
    from workstation.execution_policy import CompilationDecision, decisions_for_calls
    a = agent()
    calls = [
        call('browser_navigate', {'url': 'https://example.com/login'}),
        call('browser_snapshot', {}),
        call('browser_type', {'ref': '@e1', 'text': 'user_a', 'semantic_anchor': {'type': 'testid', 'value': 'username'}}),
        call('browser_snapshot', {}),
        call('browser_click', {'ref': '@e2', 'semantic_anchor': {'type': 'testid', 'value': 'next_btn'}}),
        call('browser_snapshot', {}),
        call('browser_type', {'ref': '@e3', 'text': 'pass_123', 'semantic_anchor': {'type': 'testid', 'value': 'password'}}),
        call('browser_snapshot', {}),
        call('browser_click', {'ref': '@e4', 'semantic_anchor': {'type': 'testid', 'value': 'submit_btn'}}),
        call('browser_snapshot', {}),
        call('browser_type', {'ref': '@e5', 'text': 'search_term', 'semantic_anchor': {'type': 'testid', 'value': 'search_box'}}),
    ]
    decisions = decisions_for_calls(a, calls)
    assert all(d != CompilationDecision.REQUIRE_COMPILE for d in decisions)


def test_homogeneous_fanout_requires_compile_on_third_mutation():
    from workstation.execution_policy import CompilationDecision, decisions_for_calls
    a = agent()
    calls = [
        call('browser_type', {'ref': '@e1', 'text': 'val1', 'target_family': 'row_amount_field'}),
        call('browser_type', {'ref': '@e2', 'text': 'val2', 'target_family': 'row_amount_field'}),
        call('browser_type', {'ref': '@e3', 'text': 'val3', 'target_family': 'row_amount_field'}),
    ]
    decisions = decisions_for_calls(a, calls)
    assert decisions[0] == CompilationDecision.ALLOW_ADAPTIVE
    assert decisions[1] == CompilationDecision.SUGGEST_COMPILE
    assert decisions[2] == CompilationDecision.REQUIRE_COMPILE


def test_homogeneous_fanout_without_operational_closure_only_suggests():
    from workstation.execution_policy import CompilationDecision, decisions_for_calls
    a = agent(closure=False)
    calls = [
        call('browser_type', {'ref': f'@e{i}', 'text': f'val{i}', 'target_family': 'row_amount_field'})
        for i in range(1, 4)
    ]
    assert decisions_for_calls(a, calls)[2] == CompilationDecision.SUGGEST_COMPILE


def test_unknown_semantic_family_does_not_fabricate_homogeneity():
    from workstation.execution_policy import CompilationDecision, decisions_for_calls
    a = agent()
    calls = [
        call('browser_type', {'ref': '@e1', 'text': 'val1'}),
        call('browser_type', {'ref': '@e2', 'text': 'val2'}),
        call('browser_type', {'ref': '@e3', 'text': 'val3'}),
    ]
    decisions = decisions_for_calls(a, calls)
    assert decisions[2] != CompilationDecision.REQUIRE_COMPILE


def test_executed_unverified_does_not_count_as_verified_success():
    from workstation.execution_policy import decisions_for_calls
    a = agent()
    record_mutation(a, 'write_file', {'path': 'test.json', 'content': 'x'}, {'ok': True})
    decisions_for_calls(a, [call('write_file', {'path': 'test2.json', 'content': 'y'})])
    candidates = getattr(a, '_work_compilation_candidates', {})
    for cand in candidates.values():
        assert cand.executed_occurrences >= 1
        assert cand.verified_successes == 0


def test_suggest_compile_checkpoint_preserves_evidence_without_forcing(tmp_path):
    """Etapa A: SUGGEST_COMPILE produces an observable checkpoint but never forces compilation."""
    from workstation.task_compiler import suggest_compilation_checkpoint
    from workstation.artifacts import ArtifactStore
    a = agent()
    calls = [call('write_file', {'path': 'output.json', 'content': f'x{i}'}) for i in range(3)]
    # First two calls produce ALLOW_ADAPTIVE and SUGGEST_COMPILE respectively
    result = suggest_compilation_checkpoint(a, calls[:2], task_id='task_a', run_id='run_1', artifacts=ArtifactStore(root_dir=tmp_path))
    assert result is not None
    assert result['decision'] == 'SUGGEST_COMPILE'
    assert result['suggested_call_count'] == 1
    assert len(result['checkpoint_refs']) >= 1
    # Checkpoint artifact exists and contains the candidate summary
    store = ArtifactStore(root_dir=tmp_path)
    payload = store.read_json(result['checkpoint_refs'][0])
    assert payload['schema'] == 'workstation.suggest_compile_checkpoint.v1'
    assert payload['total_suggested'] == 1
    assert payload['candidates'][0]['tool'] == 'write_file'
    # REQUIRE_COMPILE is NOT triggered by only two calls
    from workstation.execution_policy import CompilationDecision, decisions_for_calls
    decisions = decisions_for_calls(a, calls[:2])
    assert CompilationDecision.REQUIRE_COMPILE not in decisions


def test_consume_suggest_compile_checkpoint_rejects_opaque_traces(tmp_path):
    """Etapa B: opaque/JS-only traces are rejected with explicit reason, never silently dropped."""
    from workstation.task_compiler import consume_suggest_compile_checkpoint, suggest_compilation_checkpoint
    from workstation.artifacts import ArtifactStore
    a = agent()
    calls = [call('write_file', {'path': 'output.json', 'content': f'x{i}'}) for i in range(2)]
    checkpoint = suggest_compilation_checkpoint(a, calls, task_id='task_b', run_id='run_opaque', artifacts=ArtifactStore(root_dir=tmp_path))
    assert checkpoint is not None
    # Simulate opaque-only procedure trace (no semantic steps)
    a._work_procedure_trace = [
        {'execution_class': 'opaque_adaptive_execution', 'action': 'console', 'arguments': {}},
        {'execution_class': 'opaque_adaptive_execution', 'action': 'console', 'arguments': {}},
    ]
    receipt = consume_suggest_compile_checkpoint(a, checkpoint, task_id='task_b', run_id='run_opaque', artifacts=ArtifactStore(root_dir=tmp_path))
    assert receipt['status'] == 'rejected'
    assert receipt['reason'] == 'opaque_adaptive_traces_only'
    assert receipt['opaque_trace_count'] == 2
    assert receipt['semantic_trace_count'] == 0
    # Rejection evidence persisted
    store = ArtifactStore(root_dir=tmp_path)
    if receipt.get('evidence_ref'):
        rejection = store.read_json(receipt['evidence_ref'])
        assert rejection['schema'] == 'workstation.suggest_compile_rejection.v1'
        assert rejection['reason'] == 'opaque_adaptive_traces_only'
