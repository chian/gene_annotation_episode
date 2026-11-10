"""Replay original oversized HPC inputs without executing a model or native job."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.hpc_prompt import plan_outcome_view, render_hpc_prompt
from gene_annotation_episode.component_axis_literature_prompt import with_fact_contract_instructions


FIXTURE = Path(__file__).parent / 'fixtures/hpc/a107-genomic01-payload-context.json.gz'
HISTORY_FIXTURE = Path(__file__).parent / 'fixtures/hpc/a107-genomic03-plan-history-context.json.gz'


@pytest.fixture(scope='module')
def original_inputs():
    with gzip.open(FIXTURE, 'rt') as handle:
        return json.load(handle)['cases']


@pytest.mark.parametrize('case_index', [0, 1])
def test_original_failed_input_retains_operands_without_repeating_frozen_bytes(original_inputs, case_index):
    case = original_inputs[case_index]
    state = case['state']
    original = deepcopy(state)
    assert len(case['actual_input']) == case['actual_characters']
    assert case['actual_characters'] > case['transport_max_characters']
    rendered = with_fact_contract_instructions(
        render_hpc_prompt(state, case['instructions']), state)
    assert len(rendered) < case['transport_max_characters']
    assert state == original
    for candidate in state['hpc_candidates']:
        assert candidate['id'] in rendered
        for item in candidate.get('files', []):
            raw = item['text'].encode('utf-8')
            assert item['path'] in rendered
            assert hashlib.sha256(raw).hexdigest() in rendered
            assert 'text_size_bytes: ' + str(len(raw)) in rendered
            assert item['text'] not in rendered
    assert 'hpc_execution_job.supplied_input_file' in rendered
    assert state['hpc_child_commission']['commission_source_ref'] in rendered
    plan = state.get('last_local_outcome', {}).get('result', {})
    if 'launch_assignment' in plan:
        assert plan['plan_ref'] in rendered
        assert plan['manifest_sha256'] in rendered
        for arg in plan['practical_assignment']['requested_job']['argv']:
            assert arg in rendered


def test_plan_file_projection_preserves_original_bytes_and_all_launch_operands(original_inputs):
    outcome = original_inputs[1]['state']['last_local_outcome']
    original = deepcopy(outcome)
    shown = plan_outcome_view(outcome)
    assert outcome == original
    for key, value in original['result'].items():
        if key not in ('prediction_episode_id', 'supplied_files'):
            assert shown['result'][key] == value
    for saved, displayed in zip(original['result']['supplied_files'], shown['result']['supplied_files']):
        assert 'text' in saved and 'text' not in displayed
        assert displayed['path'] == saved['path']
        assert displayed['sha256'] == saved['sha256']
        assert displayed['text_sha256'] == hashlib.sha256(saved['text'].encode()).hexdigest()
        assert displayed['text_size_bytes'] == len(saved['text'].encode())


def test_file_descriptors_use_utf8_bytes_and_keep_declared_digest_visible():
    text = '# molecule \u03b1\n'
    outcome = {'result': {'plan_id': 'plan-original', 'original_prediction': {},
        'practical_assignment': {'requested_job': {'argv': ['actual-command']}},
        'supplied_files': [{'path': '/actual/input.py', 'text': text, 'sha256': 'declared-digest'}]}}
    saved = deepcopy(outcome)
    shown = plan_outcome_view(outcome)['result']['supplied_files'][0]
    assert outcome == saved
    assert shown['sha256'] == 'declared-digest'
    assert shown['text_sha256'] == hashlib.sha256(text.encode('utf-8')).hexdigest()
    assert shown['text_size_bytes'] == len(text.encode('utf-8'))
    assert plan_outcome_view({'result': {'stdout': text}})['result']['stdout'] == text


def test_actual_plan_history_failure_preserves_launch_inputs_without_copying_file_text():
    with gzip.open(HISTORY_FIXTURE, 'rt') as handle:
        case = json.load(handle)
    state = case['state']
    original = deepcopy(state)
    assert len(case['actual_input']) == case['failure']['input_chars']
    assert case['failure']['input_chars'] > case['failure']['provider_max_chars']
    rendered = with_fact_contract_instructions(
        render_hpc_prompt(state, case['instructions']), state)
    # Recorded transport capacity, not an application or research budget.
    assert len(rendered) < case['failure']['provider_max_chars']
    assert state == original
    assert 'launch_assignment' in rendered and 'hpc_launch_report_form' in rendered
    assert 'plan_ref' in rendered and 'plan_id' in rendered

    def plans(value):
        if isinstance(value, dict):
            if {'plan_id', 'original_prediction', 'practical_assignment'} <= value.keys():
                yield value
            for child in value.values():
                yield from plans(child)
        elif isinstance(value, list):
            for child in value:
                yield from plans(child)

    for field in ('requested_action_history', 'last_local_outcome'):
        originals = list(plans(state[field]))
        shown = list(plans(plan_outcome_view(state[field])))
        assert originals and len(originals) == len(shown)
        for saved, displayed in zip(originals, shown):
            for key, value in saved.items():
                if key not in ('prediction_episode_id', 'supplied_files'):
                    assert displayed[key] == value
            for saved_file, displayed_file in zip(saved['supplied_files'], displayed['supplied_files']):
                raw = saved_file['text'].encode('utf-8')
                assert displayed_file['path'] == saved_file['path']
                assert displayed_file['sha256'] == saved_file['sha256']
                assert displayed_file['text_sha256'] == hashlib.sha256(raw).hexdigest()
                assert displayed_file['text_size_bytes'] == len(raw)
                assert 'text' not in displayed_file
                if saved_file['text']:
                    assert saved_file['text'] not in rendered
                    assert json.dumps(saved_file['text'], ensure_ascii=False)[1:-1] not in rendered


def test_historical_plan_projection_preserves_unrelated_measurements_and_output_text():
    scientific = {'native_components': {'value': None, 'units': 'nmol/min'},
        'stdout': 'Original measured result\n',
        'files': [{'path': 'result.txt', 'text': 'Actual observation', 'sha256': 'original'}]}
    assert plan_outcome_view(scientific) == scientific


def test_nested_launch_parameters_are_preserved_as_exact_operands():
    candidate = {'id': 'original', 'queue': 'assigned', 'nodes': 1, 'wall_seconds': 900,
        'units': [], 'preparation': '', 'files': [
            {'path': 'original.txt', 'text': 'Frozen operand\n', 'sha256': 'declared'}]}
    plan = {'plan_id': 'original-plan', 'original_prediction': {},
        'practical_assignment': {'parameters': candidate},
        'launch_assignment': {'parameters': candidate},
        'supplied_files': deepcopy(candidate['files'])}
    original = deepcopy(plan)
    shown = plan_outcome_view({'history': [{'outcome': {'result': plan}}]})['history'][0]['outcome']['result']
    assert shown['practical_assignment'] == original['practical_assignment']
    assert shown['launch_assignment'] == original['launch_assignment']
    assert 'text' not in shown['supplied_files'][0]
    assert plan == original
