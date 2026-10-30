"""Actual controlled provider text for RNA results and receiving parent episodes."""
import asyncio
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.decision_context import INSTRUCTIONS, state_frame
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.providers import _rna_comparison_receiver_context
from gene_annotation_episode.rna_structure_comparison_presentation import render_rna_comparison_projections
from gene_annotation_episode.rna_structure_comparison_views import PROJECTION_SOURCE, rna_comparison_fact_sources
from gene_annotation_episode.scientific_process_prompt import text_instructions
from test_scientific_process_prompt_delivery import ScientificWire, OUTPUT_SCHEMA, snapshot
from test_rna_comparison_presentation import pair, scan
from test_rna_comparison_receiver_prompt import root_state, legacy_state, SUPPLIED_INSTRUCTIONS

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / 'verification/tool_graders_rna_comparison_prompt_delivery_2026-10-27_383'
SPEC = importlib.util.spec_from_file_location('gene_annotation_episode._provider_baseline_383',
    PACKET / 'baseline_providers.py')
baseline = importlib.util.module_from_spec(SPEC)
# dataclasses resolves its defining module when retaining annotation metadata.
import sys
sys.modules[SPEC.name] = baseline
SPEC.loader.exec_module(baseline)


def parts(text):
    assert text.startswith('TASK\n\n') and text.count('\n\nSTEERING\n') == 1
    return text.split('\n\nSTEERING\n', 1)


def instructions(state):
    if 'execution_assignment' in state:
        owner = ExecutionEpisodes.__new__(ExecutionEpisodes)
        context = SimpleNamespace(role='results', assignment=state['execution_assignment'])
        return owner.instructions(context) + '\n' + INSTRUCTIONS
    return SUPPLIED_INSTRUCTIONS + '\n' + INSTRUCTIONS


def complete(wire, state, *, context=None, episode='episode'):
    return wire.complete(episode, 'REASONING', instructions(state),
        state_frame(state) if context is None else context, OUTPUT_SCHEMA)


def recorded_case(kind):
    name = 'FILLED_ACTUAL_PAIR_001.json' if kind == 'pair' else 'FILLED_ACTUAL_SCAN_001.json'
    path = ROOT / 'verification/tool_graders_rna_comparison_shared_integration_2026-10-26_372' / name
    return json.loads(path.read_text())['workflow_case']


def comparison_form():
    facts = rna_comparison_fact_sources()[PROJECTION_SOURCE]
    return {'type': 'object', 'properties': {
        'requested_comparison': {**deepcopy(facts['report_schema']),
            'description': 'The exact comparison values requested in this assignment.'},
        'interpretation': {'type': 'string', 'enum': ['qualified', 'unresolved']}},
        'required': ['requested_comparison', 'interpretation'], 'additionalProperties': False}


def results_state(kind='pair', *, collected=False, status=False):
    from gene_annotation_episode.rna_structure_comparison_results import operation_catalog
    case = recorded_case(kind)
    state = root_state()
    state.pop('received_rna_comparison_values')
    state.pop('selected_launch_instructions')
    state.pop('child_options')
    state['goal'] = {'objective': 'Return the parent-selected comparison of retained RNA results.'}
    state['execution_assignment'] = {'version': 'execution_results_assignment_v1',
        'handoff_ref': case['body']['anchor_handoff_ref'], 'selector': deepcopy(case['selector'])}
    state['tools'] = operation_catalog()
    state['requested_report_purpose'] = 'Return the selected comparison facts with their actual qualifications.'
    state['requested_form'] = comparison_form()
    state['available_report_facts'] = rna_comparison_fact_sources()
    state['execution_progress'] = {PROJECTION_SOURCE: deepcopy(case['body']['projection_rows']) if collected else [],
        'execution_completed': collected}
    state['last_local_outcome'] = None
    state['action_yields'] = {'rows': []}
    if collected or status:
        body = deepcopy(case['body'])
        body['tool_name'] = 'execution.results.status' if status else 'execution.results.collect'
        if status:
            body.update(projection_rows=[], delivery_complete=False)
        state['last_local_outcome'] = {'status': 'completed', 'record_refs': [],
            'changed_record_refs': [], 'result': body, 'feedback': None}
        state['action_yields']['rows'] = [{'category': 'tool/' + body['tool_name'], 'completed_actions': 1,
            'total_yield': 0, 'attempted_uncompleted': 0, 'expected_yield': {
                'status': 'unavailable', 'unavailable_reason': 'insufficient completed actions', 'band': None}}]
    return state


@pytest.mark.parametrize('kind', ['root', 'legacy', 'older_legacy'])
@pytest.mark.parametrize('family', range(8))
def test_actual_parent_turn_keeps_its_task_and_only_selected_facts(tmp_path, pair, scan, kind, family):
    row = (pair + scan)[family]
    state = root_state([row]) if kind == 'root' else legacy_state([row], older=kind == 'older_legacy')
    state['child_reports'] = [{'caller_chosen_name': [deepcopy(row)], 'unrelated_value': -0.25}]
    original = deepcopy(state)
    wire = ScientificWire(tmp_path / 'wire')
    asyncio.run(complete(wire, state))
    turn = wire.turns_sent()[0]
    task, steering = parts(turn['input'][0]['text'])
    assert SUPPLIED_INSTRUCTIONS in task and state['goal']['objective'] in task
    assert state['selected_constraints']['material'] in task
    assert state['working_state']['materials'][0]['text'] in task
    expected = render_rna_comparison_projections([row])
    assert expected not in task and steering.count(expected) == 1
    assert 'unrelated_value | -0.25' in steering
    assert '| child/results | 1 | 0 | unavailable |' in steering
    if row['family'] != 'structures':
        assert '(((...)))' not in steering and '((.....))' not in steering
    for secret in ('HOST_GOAL', 'HOST_PARENT', row['result_receipt_key'], row['calculation_key'], 'input_paths'):
        assert secret not in task + steering
    assert turn['outputSchema'] == OUTPUT_SCHEMA and state == original
    saved = json.loads((tmp_path / 'wire/call-00001/request.json').read_text())
    assert saved['context'] == state_frame(state) and saved['instructions'] == instructions(state)
    assert saved['input'] == turn['input']
    if kind == 'root' and row['family'] in {'structures', 'scan_energy'}:
        (tmp_path / (row['family'] + '_ROOT_ACTUAL_TURN.txt')).write_text(turn['input'][0]['text'] + '\n')


@pytest.mark.parametrize('kind', ['root', 'legacy', 'older_legacy'])
def test_first_child_return_arrives_after_empty_bootstrap_without_changing_task_or_thread(tmp_path, pair, kind):
    first = root_state() if kind == 'root' else legacy_state(older=kind == 'older_legacy')
    first['received_rna_comparison_values'] = []  # exact initial service output
    second = deepcopy(first)
    second['received_rna_comparison_values'] = [{'fact_source': PROJECTION_SOURCE, 'facts': [pair[0]]}]
    second['child_reports'] = [{'energy_answer': [pair[0]]}]
    update = state_frame(second, first)
    assert 'goal' not in update['fields'] and 'scope' not in update['fields']
    lookup_value = {'status': 'completed', 'result': [pair[1]]}
    lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result', 'result': lookup_value}
    restored = state_frame(second)
    restored.update(restored_pending_decision_index=2, restored_public_exchanges=[
        {'exchange_index': 1, 'response': {'private': 'PRIVATE_TRANSCRIPT'}, 'lookup_result': lookup_value}])
    wire, fresh = ScientificWire(tmp_path / 'wire'), ScientificWire(tmp_path / 'fresh')
    async def exercise():
        await complete(wire, first)
        await complete(wire, second, context=update)
        await complete(wire, second, context=lookup)
        await complete(fresh, second, context=restored)
    asyncio.run(exercise())
    turns = wire.turns_sent() + fresh.turns_sent()
    texts = [p['input'][0]['text'] for p in turns]
    tasks = [parts(t)[0] for t in texts]
    assert len(set(tasks)) == 1
    assert 'Requested RNA ' not in parts(texts[0])[1]
    assert parts(texts[1])[1].count('Requested RNA energy comparison') == 1
    assert parts(texts[2])[1].count('Requested RNA structures') == 1
    assert turns[2]['input'] == turns[3]['input']
    assert all('PRIVATE_TRANSCRIPT' not in text for text in texts)
    assert sum(method == 'thread/start' for method, _ in wire.sent) == 1
    developers = [p['developerInstructions'] for connection in (wire, fresh)
        for method, p in connection.sent if method == 'thread/start']
    assert developers == [text_instructions(instructions(first))] * 2
    assert all(p['outputSchema'] == OUTPUT_SCHEMA for p in turns)
    assert wire.scientific_prompt_states[('episode', 'REASONING')] == second
    (tmp_path / 'RESTORED_PARENT_ACTUAL_TURN.txt').write_text(texts[-1] + '\n')


@pytest.mark.parametrize('kind', ['pair', 'scan'])
def test_actual_results_turn_uses_full_selected_assignment_and_selected_saved_values(tmp_path, kind):
    state = results_state(kind, collected=True)
    original = deepcopy(state)
    wire = ScientificWire(tmp_path / 'wire')
    asyncio.run(complete(wire, state))
    text = wire.turns_sent()[0]['input'][0]['text']
    task, steering = parts(text)
    assert 'execution.results.status' in task and 'execution.results.collect' in task
    assert 'Acquire the original selected execution results' not in task
    assert 'Acquire the original selected execution results' not in next(
        p['developerInstructions'] for method, p in wire.sent if method == 'thread/start')
    assert 'qualified' in task and 'unresolved' in task
    assert 'requested_comparison' in task
    for row in state['execution_progress'][PROJECTION_SOURCE]:
        assert steering.count(render_rna_comparison_projections([row])) == 1
        assert row['result_receipt_key'] not in text and row['calculation_key'] not in text
    for key in ('input_paths', 'sheet_sha256', 'assignment_digest', 'rna_comparison_projection_v1'):
        assert key not in text
    if kind == 'scan':
        assert 'baseline rank start | 2' in steering and 'baseline rank end | 3' in steering
        assert '| rank population count | 4 |' in steering
        assert 'Dot-bracket' not in steering and 'Selected member' not in steering
    else:
        assert '(((...)))' in steering and '((.....))' in steering
        assert 'energy delta | -1.0 | kcal/mol' in steering
    assert state == original
    (tmp_path / (kind.upper() + '_RESULTS_ACTUAL_TURN.txt')).write_text(text + '\n')


def test_results_status_update_and_restored_lookup_keep_assignment_and_delivery_distinction(tmp_path):
    first, second = results_state(), results_state(status=True)
    update = state_frame(second, first)
    assert 'execution_assignment' not in update['fields']
    case = recorded_case('pair')
    reply = {'status': 'completed', 'result': case['body']}
    lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result', 'result': reply}
    restored = state_frame(second)
    restored.update(restored_pending_decision_index=1, restored_public_exchanges=[{'lookup_result': reply}])
    wire, fresh = ScientificWire(tmp_path / 'wire'), ScientificWire(tmp_path / 'fresh')
    async def exercise():
        await complete(wire, first)
        await complete(wire, second, context=update)
        await complete(wire, second, context=lookup)
        await complete(fresh, second, context=restored)
    asyncio.run(exercise())
    turns = wire.turns_sent() + fresh.turns_sent()
    assert len({parts(p['input'][0]['text'])[0] for p in turns}) == 1
    assert '| execution.results.status | completed | false |' in turns[1]['input'][0]['text']
    assert turns[2]['input'] == turns[3]['input']
    assert 'Requested RNA energy comparison' in turns[2]['input'][0]['text']
    assert sum(method == 'thread/start' for method, _ in wire.sent) == 1


@pytest.mark.parametrize('groups,expected', [([], True),
    ([{'fact_source': PROJECTION_SOURCE, 'facts': []}], True), (None, False), ({}, False),
    ([{'fact_source': 'unrelated', 'facts': []}], False),
    ([{'fact_source': PROJECTION_SOURCE, 'facts': {}}], False),
    ([{'fact_source': PROJECTION_SOURCE, 'facts': [], 'extra': True}], False)])
def test_receiving_capability_is_exact_and_does_not_require_an_existing_result(groups, expected):
    assert _rna_comparison_receiver_context({'received_rna_comparison_values': groups}) is expected
    assert not _rna_comparison_receiver_context({}) and not _rna_comparison_receiver_context(None)


@pytest.mark.parametrize('kind', ['root_without_binding', 'legacy_without_binding', 'unrelated_group'])
def test_unrelated_legacy_inputs_preserve_original_json_and_instructions(tmp_path, kind):
    state = root_state() if kind == 'root_without_binding' else legacy_state()
    state.pop('received_rna_comparison_values')
    if kind == 'unrelated_group':
        state['received_rna_comparison_values'] = [{'fact_source': 'other', 'facts': []}]
    wire = ScientificWire(tmp_path / 'wire')
    frame = state_frame(state)
    expected = baseline._SessionConnection._presentation(wire, 'comparison', 'REASONING', instructions(state), frame)
    asyncio.run(complete(wire, state, context=frame))
    assert wire.turns_sent()[0]['input'][0]['text'] == expected[0]
    assert json.loads(expected[0]) == frame
    assert next(p['developerInstructions'] for method, p in wire.sent if method == 'thread/start') == expected[1]
    assert not wire.scientific_prompt_states


def test_published_scientific_template_keeps_priority_over_empty_receiver_marker(tmp_path):
    state = snapshot()
    state['received_rna_comparison_values'] = []
    wire = ScientificWire(tmp_path / 'wire')
    frame = state_frame(state)
    expected = baseline._SessionConnection._presentation(wire, 'before', 'REASONING', instructions(state), frame)
    asyncio.run(complete(wire, state, context=frame))
    assert wire.turns_sent()[0]['input'][0]['text'] == expected[0]
    assert next(p['developerInstructions'] for method, p in wire.sent if method == 'thread/start') == expected[1]


def test_literature_template_keeps_its_existing_priority(tmp_path):
    from test_literature_experimental_prompt_delivery import snapshot as literature_snapshot
    state = literature_snapshot()
    state['received_rna_comparison_values'] = []
    wire = ScientificWire(tmp_path / 'wire')
    frame = state_frame(state)
    expected = baseline._SessionConnection._presentation(wire, 'before', 'REASONING', instructions(state), frame)
    asyncio.run(complete(wire, state, context=frame))
    assert wire.turns_sent()[0]['input'][0]['text'] == expected[0]
    assert next(p['developerInstructions'] for method, p in wire.sent if method == 'thread/start') == expected[1]


def test_current_annotation_is_present_without_replaying_superseded_revisions(tmp_path, pair):
    state = root_state([pair[0]])
    state['working_state']['annotations'] = [
        {'id': 'annotation_old', 'value': 'SUPERSEDED_ANNOTATION_VALUE'},
        {'id': 'annotation_current', 'value': 'Current qualified functional interpretation', 'score': .75}]
    state['working_state']['received_revision_status'] = [
        {'record_ref': 'annotation_old', 'is_current_revision': False},
        {'record_ref': 'annotation_current', 'is_current_revision': True}]
    wire = ScientificWire(tmp_path / 'wire')
    asyncio.run(complete(wire, state))
    text = wire.turns_sent()[0]['input'][0]['text']
    assert 'Current qualified functional interpretation' in text
    assert 'SUPERSEDED_ANNOTATION_VALUE' not in text


def test_orphan_eligible_update_cannot_invent_missing_task(tmp_path):
    first = root_state()
    second = deepcopy(first)
    second['received_rna_comparison_values'] = []
    wire = ScientificWire(tmp_path / 'wire')
    with pytest.raises(TypeError, match='previous_model_state_requires_object'):
        asyncio.run(complete(wire, second, context=state_frame(second, first)))
    assert not wire.turns_sent()
