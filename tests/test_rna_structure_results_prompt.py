"""Original results instructions from retained360 and explicit selected fixtures."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.native_rna_structure_acquisition import ORIGIN
from gene_annotation_episode.rna_structure_prompt import (
    render_rna_structure_results_prompt, rna_structure_results_instructions,
)
from gene_annotation_episode.rna_structure_result_views import (
    FAMILY_METRICS, FAMILY_SOURCES, REFERENCE_SOURCE, SAVED_SOURCE, rna_structure_fact_sources,
)


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'verification/tool_graders_rna_structure_integration_2026-10-26_360/NUMERICAL_EXAMPLES.json'


def recorded_state(case_index=4, result_index=0, *, collected=True):
    case = json.loads(EXAMPLES.read_text())['examples'][case_index]
    result = case['results'][result_index]
    body = deepcopy(result['original_result_receipt'])
    form = deepcopy(case['requested_forms']['results'])
    progress = {source: [] for source in FAMILY_SOURCES.values()}
    progress.update({REFERENCE_SOURCE: [], SAVED_SOURCE: [], 'execution_result_refs': [],
        'execution_completed': False, 'execution_result_origin': None})
    if collected:
        for field, node in form['properties'].items():
            source = node.get('x-source')
            if source is not None and field in result['requested_return']:
                progress[source] = deepcopy(result['requested_return'][field])
        progress['execution_result_refs'] = deepcopy(progress[REFERENCE_SOURCE])
        if body['assignment']['selector']['acquisition'] == 'complete_bound_bundle' and body['native_success']:
            progress['execution_result_origin'] = deepcopy(ORIGIN)
    return {
        'execution_assignment': deepcopy(body['assignment']),
        'execution_target': deepcopy(body['target']),
        'execution_target_description': {'private_path': '/PRIVATE_PRODUCER_PATH', 'sha256': 'PRIVATE_TARGET_DIGEST'},
        'execution_progress': progress,
        'last_local_outcome': {'status': 'completed', 'record_refs': body['record_refs'],
            'changed_record_refs': [], 'result': body, 'feedback': None} if collected else None,
        'goal': {'objective': 'Return the selected original RNA measurements for the supplied sequence.',
            'task_context': {'constraint': 'Keep the original input and energy meaning fixed.'},
            'result_contract': deepcopy(form), 'host_id': 'PRIVATE_GOAL_ID'},
        'scope': deepcopy(body['scope']),
        'requested_report_purpose': 'Return the requested RNA values and specific unavailable reasons.',
        'requested_form': form,
        'available_report_facts': rna_structure_fact_sources(),
        'report_lifecycle': 'Recorded facts are automatic; interpretations use the separately declared allowed values.',
        'selected_launch_instructions': {'sections': [{'text': 'Preserve the assigned RNA inputs and local resource allocation.'}]},
        'action_yields': {'rows': [{'category': 'tool/execution.results.collect', 'completed_actions': 1,
            'total_yield': 0, 'attempted_uncompleted': 0, 'expected_yield': {'status': 'unavailable',
                'band': None, 'unavailable_reason': 'insufficient completed actions'}}]} if collected else {'rows': []},
    }


def instructions(state):
    owner = ExecutionEpisodes.__new__(ExecutionEpisodes)
    owner._target = lambda context: state['execution_target']
    return owner.instructions(SimpleNamespace(role='results', assignment=state['execution_assignment']))


@pytest.mark.parametrize('case_index,result_index', [(4, 0), (5, 0), (6, 0), (1, 1), (2, 0)])
def test_original_results_task_preserves_actual_mode_selection_and_return(case_index, result_index):
    state = recorded_state(case_index, result_index)
    before = deepcopy(state)
    text = render_rna_structure_results_prompt(state, instructions(state))
    task, steering = text.split('\n\nSTEERING\n', 1)
    assert task.startswith('TASK\n\n')
    assert state['goal']['objective'] in task
    assert 'Keep the original input and energy meaning fixed.' in task
    assert 'Preserve the assigned RNA inputs and local resource allocation.' in task
    assert 'execution.results.status' in task and 'execution.results.collect' in task
    assert 'no prescribed order' in task and 'exact zero immediately' in task
    assert '20 GiB RAM and 4 GiB scratch' in task and 'no wall-time budget' in task
    assert 'Only actual complete acquisition establishes this endpoint' not in task
    assert '| tool/execution.results.collect | 1 | 0 | unavailable |' in steering
    assert 'native_rna_structure_acquired_result_v1' not in text
    assert '/PRIVATE_PRODUCER_PATH' not in text and 'PRIVATE_TARGET_DIGEST' not in text
    assert 'PRIVATE_GOAL_ID' not in text and 'bytes_base64' not in text
    # Automatic source schemas are not instructions for the model to fill cells.
    assert 'return.summary[].calculation_key' not in task
    assert 'rna_calculation_parameters_v1' not in task
    assert state == before
    if result_index:
        assert 'does not run a new prediction or energy evaluation' in task
        assert 'retained original' in steering.lower()
    elif case_index == 4:
        assert 'predicts a minimum-free-energy secondary structure' in task
    else:
        assert 'analyzes a supplied secondary structure' in task


@pytest.mark.parametrize('family', tuple(FAMILY_METRICS))
def test_selected_row_and_metric_meanings_are_complete_without_unselected_family_fields(family):
    state = recorded_state(collected=False)
    assignment = state['execution_assignment']
    assignment['selector']['projection'] = {'family': family, 'rows': {'record_keys': ['original-record:selected-row']},
        'metrics': list(FAMILY_METRICS[family])}
    text = rna_structure_results_instructions(assignment,
        job=state['execution_target']['assignment']['requested_job']['native_rna_structure'])
    assert 'original-record:selected-row' in text
    for metric in FAMILY_METRICS[family]:
        assert '| ' + metric + ' |' in text
    if family == 'failure':
        assert 'A failure row has no numerical score' in text
        assert 'Requested numerical fields' not in text
    elif family in {'pair', 'stem', 'region'}:
        assert 'zero based' in text and 'half open [start, end)' in text
        assert 'mfe_kcal_mol' not in text


def test_selected_energy_and_normalization_have_separate_exact_meanings():
    state = recorded_state(collected=False)
    job = state['execution_target']['assignment']['requested_job']['native_rna_structure']
    choice = state['execution_assignment']['selector']['projection']
    choice['metrics'] = ['mfe_kcal_mol']
    original = instructions(state)
    assert 'kcal/mol; a prediction' in original
    assert 'evaluated_energy_kcal_mol' not in original and 'paired_fraction' not in original
    assert 'Original' in original and 'temperature_c | 37.0' in original
    assert 'rna_module_sha256' not in original and job['software']['python_sha256'] not in original
    choice['metrics'] = ['evaluated_energy_per_nt']
    normalized = instructions(state)
    assert 'kcal/mol/nt' in normalized and 'energy_normalization | per_nt' in normalized
    assert 'requested settings alone do not prove compatibility' in normalized


def test_parent_interpretation_constraints_are_preserved_separately_from_automatic_facts():
    state = recorded_state(collected=False)
    state['requested_form']['properties']['qualification'] = {'type': 'string', 'enum': ['usable', 'qualified'],
        'description': 'Use the actual unavailable fields.'}
    state['requested_form']['required'].append('qualification')
    state['goal']['result_contract'] = deepcopy(state['requested_form'])
    text = render_rna_structure_results_prompt(state, instructions(state))
    assert 'usable' in text and 'qualified' in text and 'Use the actual unavailable fields.' in text
    assert 'return.summary[].measurements' not in text
    assert text.count('Assigned result contract') == 0


def test_wrong_original_mode_operation_is_not_rendered_as_the_assigned_job():
    state = recorded_state(collected=False)
    job = state['execution_target']['assignment']['requested_job']['native_rna_structure']
    job['operation'] = 'not_the_selected_operation'
    with pytest.raises(ValueError, match='rna_input_identity_mismatch'):
        instructions(state)

