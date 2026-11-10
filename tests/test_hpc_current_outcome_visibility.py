"""HPC decisions retain actual callable operands and execution output."""
from gene_annotation_episode.hpc_prompt import render_hpc_prompt


def test_current_plan_return_keeps_launch_operands_beside_credit_summary():
    state = {'hpc_commission': {'objective': 'Synthetic execution custody'},
        'completed_action_reports': [], 'last_local_outcome': {
            'status': 'completed', 'result': {
                'plan_id': 'actual_plan_identity_7a2e',
                'original_prediction': {'expected_seconds': 8.5},
                'prediction_episode_id': 'audit_id_not_an_execution_operand',
                'model_ref': 'actual_prediction_model_2f1b',
                'practical_assignment': {'requested_job': {
                    'argv': ['/usr/bin/python', 'actual_native_command_3c4d']}},
                'launch_assignment': {'resource_id': 'aurora',
                    'exact_operand': 'actual_launch_assignment_4d5e'}}}}
    rendered = render_hpc_prompt(state, 'Use the actual assigned operation.')
    assert 'actual_launch_assignment_4d5e' in rendered
    assert 'actual_native_command_3c4d' in rendered
    assert 'actual_prediction_model_2f1b' in rendered
    assert 'audit_id_not_an_execution_operand' not in rendered


def test_current_command_result_is_visible_to_hpc_execution_role():
    state = {'hpc_execution_job': {'plan_id': 'synthetic-plan'},
        'completed_action_reports': [], 'last_local_outcome': {
            'status': 'completed', 'result': {'outcome': {'native_outcome': {
                'returncode': 1, 'stdout': 'actual_native_stdout_5e6f',
                'stderr': 'actual_native_diagnostic_6f7a'}}}}}
    rendered = render_hpc_prompt(state, 'Use the actual assigned operation.')
    assert 'actual_native_stdout_5e6f' in rendered
    assert 'actual_native_diagnostic_6f7a' in rendered


def test_current_scope_and_resource_inputs_reach_hpc_launch():
    state = {'hpc_execution_job': {'plan_id': 'synthetic-plan'},
        'scope': {'subject_refs': ['input_' + 'a' * 24]},
        'resource_context': {'whole_workflow': {'cpu_percent': 100,
            'memory_bytes': 5368709120, 'swap_bytes': 0}},
        'execution_resource_capabilities': {'resource_marker': 'actual_execution_resource_7a8b'},
        'execution_initial_information': {'inventory_marker': 'actual_initial_observation_8b9c'}}
    rendered = render_hpc_prompt(state, 'Use the actual assigned operation.')
    assert 'input_' + 'a' * 24 in rendered
    assert 'cpu_percent: 100' in rendered
    assert 'memory_bytes: 5368709120' in rendered
    assert 'swap_bytes: 0' in rendered
    assert 'actual_execution_resource_7a8b' in rendered
    assert 'actual_initial_observation_8b9c' in rendered


def test_explicitly_requested_history_survives_a_different_latest_read():
    state = {'hpc_execution_job': {'plan_id': 'synthetic-plan'},
        'requested_action_history': [{'last_requested_at_decision': 38,
            'record': {'decision_index': 36, 'tool': 'exec_command', 'outcome': {
                'result': {'stdout': 'retained_runner_contract_59a6'}}}}],
        'last_local_outcome': {'status': 'completed', 'result': {'view': 'records',
            'records': [{'decision_index': 37, 'outcome': {'result': {
                'text': 'current_resource_contract_6ab7'}}}]}}}
    rendered = render_hpc_prompt(state, 'Use the original assigned operation.')
    assert 'retained_runner_contract_59a6' in rendered
    assert 'current_resource_contract_6ab7' in rendered
