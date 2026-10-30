"""Original RNA facts at controlled provider boundaries, using retained360 data."""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.decision_context import INSTRUCTIONS, state_frame
from gene_annotation_episode.rna_structure_presentation import render_rna_structure_groups
from gene_annotation_episode.rna_structure_result_views import FAMILY_SOURCES, REFERENCE_SOURCE, SAVED_SOURCE
from gene_annotation_episode.scientific_process_prompt import text_instructions
from test_rna_structure_results_prompt import recorded_state, instructions as results_instructions
from test_scientific_process_prompt_delivery import ScientificWire, OUTPUT_SCHEMA, snapshot
from test_rna_comparison_receiver_prompt import root_state, legacy_state, SUPPLIED_INSTRUCTIONS
from test_rna_comparison_prompt_delivery import results_state as comparison_state


def parts(text):
    assert text.startswith('TASK\n\n') and text.count('\n\nSTEERING\n') == 1
    return text.split('\n\nSTEERING\n', 1)


def instructions(state):
    supplied = results_instructions(state) if 'execution_assignment' in state else SUPPLIED_INSTRUCTIONS
    return supplied + '\n' + INSTRUCTIONS


def complete(wire, state, *, context=None):
    return wire.complete('original-rna', 'REASONING', instructions(state),
        state_frame(state) if context is None else context, OUTPUT_SCHEMA)


def groups_from_progress(progress):
    sources = (*FAMILY_SOURCES.values(), REFERENCE_SOURCE, SAVED_SOURCE)
    return [{'fact_source': source, 'facts': deepcopy(progress[source])}
        for source in sources if progress.get(source)]


def parent_state(kind, *, received=True, case_index=4):
    original = recorded_state(case_index)
    if kind == 'published':
        state = snapshot()
    elif kind == 'root':
        state = root_state()
    else:
        state = legacy_state(older=kind == 'older_legacy')
    state.pop('received_rna_comparison_values', None)
    state['received_rna_structure_values'] = groups_from_progress(original['execution_progress']) if received else []
    state['requested_form'] = deepcopy(original['requested_form'])
    state['available_report_facts'] = deepcopy(original['available_report_facts'])
    state['requested_report_purpose'] = 'Retain the requested RNA values for the parent investigation.'
    if received:
        state['child_reports'] = [{'arbitrary_parent_field_' + str(i): deepcopy(group['facts'])}
            for i, group in enumerate(state['received_rna_structure_values'])]
    else:
        state['child_reports'] = []
    return state


@pytest.mark.parametrize('kind', ['root', 'legacy', 'older_legacy', 'published'])
def test_actual_receiver_input_preserves_parent_task_and_selected_original_values(tmp_path, kind):
    state = parent_state(kind)
    original = deepcopy(state)
    expected = render_rna_structure_groups(state['received_rna_structure_values'])
    wire = ScientificWire(tmp_path / 'wire')
    asyncio.run(complete(wire, state))
    turn = wire.turns_sent()[0]
    text = turn['input'][0]['text']
    task, steering = parts(text)
    assert SUPPLIED_INSTRUCTIONS in task
    assert state['goal']['objective'] in task
    assert expected not in task and steering.count(expected) == 1
    assert 'native_rna_structure_acquired_result_v1' not in text
    assert 'return.summary[].measurements' not in task
    assert turn['outputSchema'] == OUTPUT_SCHEMA and state == original
    saved = json.loads((tmp_path / 'wire/call-00001/request.json').read_text())
    assert saved['context'] == state_frame(state)
    assert saved['input'] == turn['input']
    if kind == 'published':
        process = state['scientific_process']
        assert process['evidence_axis']['investigation_instructions'] in task
        assert process['child_tool_info'][0]['instructions'] in task
    (tmp_path / (kind + '_ORIGINAL_RNA_PARENT_ACTUAL_INPUT.txt')).write_text(text + '\n')


@pytest.mark.parametrize('kind', ['root', 'legacy', 'published'])
def test_empty_original_receiver_then_first_report_delta_lookup_and_restore(tmp_path, kind):
    first = parent_state(kind, received=False)
    second = parent_state(kind, received=True)
    update = state_frame(second, first)
    assert 'goal' not in update['fields'] and 'scope' not in update['fields']
    group = next(g for g in second['received_rna_structure_values'] if g['fact_source'] == FAMILY_SOURCES['summary'])
    selected = deepcopy(group['facts'][0])
    reply = {'status': 'completed', 'result': selected}
    lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result', 'result': reply}
    restored = state_frame(second)
    restored.update(restored_pending_decision_index=2, restored_public_exchanges=[
        {'exchange_index': 1, 'response': {'private': 'PRIVATE_EXCHANGE_HISTORY'}, 'lookup_result': reply}])
    wire, fresh = ScientificWire(tmp_path / 'wire'), ScientificWire(tmp_path / 'fresh')
    async def exercise():
        await complete(wire, first)
        await complete(wire, second, context=update)
        await complete(wire, second, context=lookup)
        await complete(fresh, second, context=restored)
    asyncio.run(exercise())
    turns = wire.turns_sent() + fresh.turns_sent()
    texts = [t['input'][0]['text'] for t in turns]
    assert len({parts(t)[0] for t in texts}) == 1
    assert 'Selected original RNA facts and callable operands' not in parts(texts[0])[1]
    assert 'Selected original RNA facts and callable operands' in parts(texts[1])[1]
    assert turns[2]['input'] == turns[3]['input']
    assert all('PRIVATE_EXCHANGE_HISTORY' not in text for text in texts)
    assert sum(method == 'thread/start' for method, _ in wire.sent) == 1
    developers = [params['developerInstructions'] for connection in (wire, fresh)
        for method, params in connection.sent if method == 'thread/start']
    assert developers == [text_instructions(instructions(first))] * 2
    assert all(turn['outputSchema'] == OUTPUT_SCHEMA for turn in turns)
    assert wire.scientific_prompt_states[('original-rna', 'REASONING')] == second
    (tmp_path / (kind + '_RESTORED_ORIGINAL_RNA.txt')).write_text(texts[-1] + '\n')


@pytest.mark.parametrize('case_index,result_index', [(4, 0), (5, 0), (6, 0), (1, 1), (2, 0)])
def test_original_results_provider_repeats_full_task_with_actual_collected_receipt(tmp_path, case_index, result_index):
    initial = recorded_state(case_index, result_index, collected=False)
    final = recorded_state(case_index, result_index, collected=True)
    before = deepcopy(final)
    wire = ScientificWire(tmp_path / 'wire')
    async def exercise():
        await complete(wire, initial)
        await complete(wire, final, context=state_frame(final, initial))
    asyncio.run(exercise())
    first, second = [turn['input'][0]['text'] for turn in wire.turns_sent()]
    task, steering = parts(second)
    assert parts(first)[0] == task
    assert final['goal']['objective'] in task and instructions(final).split('\n' + INSTRUCTIONS)[0] in task
    assert 'Last own original RNA result outcome' in steering
    assert 'native_rna_structure_acquired_result_v1' not in second
    assert 'bytes_base64' not in second and 'PRIVATE_TARGET_DIGEST' not in second
    assert final == before
    if result_index:
        assert 'retained original' in steering.lower()
    (tmp_path / 'ORIGINAL_RESULTS_ACTUAL_INPUT.txt').write_text(second + '\n')


def test_selected_original_and_comparison_facts_coexist_without_duplicate_returns(tmp_path):
    state = parent_state('root')
    other = comparison_state('scan', collected=True)
    comparison = other['last_local_outcome']['result']['projection_rows']
    source = 'execution_rna_structure_comparison_projections'
    state['received_rna_comparison_values'] = [{'fact_source': source, 'facts': comparison}]
    state['child_reports'].append({'mixed_comparison': deepcopy(comparison), 'unrelated_measurement': 0.125})
    before = deepcopy(state)
    wire = ScientificWire(tmp_path / 'wire')
    asyncio.run(complete(wire, state))
    text = wire.turns_sent()[0]['input'][0]['text']
    assert 'Selected RNA comparison facts' in text and 'Selected original RNA facts and callable operands' in text
    assert text.count('Requested RNA scan energy') == 1
    assert 'unrelated_measurement | 0.125' in text
    assert '(((...)))' not in text  # original numerical rows and scan rank do not request structures
    assert state == before


def test_original_receiver_capability_is_required_for_new_general_parent_route(tmp_path):
    state = parent_state('root', received=False)
    state.pop('received_rna_structure_values')
    wire = ScientificWire(tmp_path / 'wire')
    context = state_frame(state)
    asyncio.run(complete(wire, state, context=context))
    assert json.loads(wire.turns_sent()[0]['input'][0]['text']) == context


def test_missing_frame_base_is_not_fabricated_from_first_original_child_facts(tmp_path):
    first = parent_state('root', received=False)
    final = parent_state('root', received=True)
    wire = ScientificWire(tmp_path / 'wire')
    with pytest.raises(TypeError, match='previous_model_state_requires_object'):
        asyncio.run(complete(wire, final, context=state_frame(final, first)))
    assert not wire.turns_sent()

