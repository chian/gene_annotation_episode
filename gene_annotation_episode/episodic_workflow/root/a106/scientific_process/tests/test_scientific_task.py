"""Scientific task boundaries with controlled operations and original progress semantics."""
import asyncio
from contextlib import nullcontext
from copy import deepcopy
import importlib
import json
from types import SimpleNamespace

import pytest

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a106'
runtime = importlib.import_module(PACKAGE + '.runtime')
Binding = importlib.import_module(PACKAGE + '.scientific_process.episode').ScientificProcessEpisode


def make_task(outcome):
    saved, calls, events = {}, [], []
    journal = SimpleNamespace(row=lambda table, episode, index: saved.get(index),
        save=lambda table, row: saved.__setitem__(row['decision_index'], row),
        measure=lambda *args: nullcontext())
    async def execute(source, name, arguments, **kwargs):
        calls.append((name, deepcopy(arguments), kwargs['operation_key']))
        return deepcopy(outcome)
    async def score(source, index, result):
        events.append('grading')
        return result
    task_type = getattr(Binding, 'decision_source_type', runtime.DecisionSource)
    task = object.__new__(task_type)
    task.episode_id, task.path, task.scope = 'science', (('scientific_process', 'science'),), {}
    task.checkpoint = lambda: None
    task.workflow = SimpleNamespace(journal=journal, run_id='run', execution_binding=None,
        wait_inputs_version=None, completed_action_inputs_version=None, execute=execute,
        scientific_process_binding=SimpleNamespace(validate_execution_context=lambda context: None),
        binding_context=lambda source: source,
        receive_native_outcome=lambda *args: None,
        receive_outcome=lambda source, selection, result, index: events.append('received'),
        automatic_score_updates=score,
        source_credit_view=lambda source: events.append('credit') or {'credit': 2.5},
        controller_value=lambda source, index, credit: {'index': index, 'credit': credit})
    return task, saved, calls, events


@pytest.mark.parametrize('status', ['completed', 'partial', 'invalid', 'failed', 'unavailable'])
def test_executed_outcome_reaches_original_progress_and_replays_once(status):
    task, saved, calls, events = make_task({'status': status, 'record_refs': [],
        'changed_record_refs': [], 'result': None, 'feedback': None})
    selection = {'kind': 'tool', 'tool': 'source.read', 'arguments': {'source_ref': 'original'}}
    first = asyncio.run(task.execute(selection, 3))
    second = asyncio.run(task.execute(selection, 3))
    assert first == second == {'index': 3, 'credit': 2.5}
    assert calls == [('source.read', {'source_ref': 'original'}, 'run:science:3')]
    assert events == ['received', 'grading', 'credit']
    assert json.loads(saved[3]['action']) == selection
    assert json.loads(saved[3]['result'])['status'] == status


def test_replay_rejects_changed_original_action():
    task, saved, calls, events = make_task({'status': 'completed', 'record_refs': [], 'changed_record_refs': []})
    selection = {'kind': 'tool', 'tool': 'source.read', 'arguments': {}}
    asyncio.run(task.execute(selection, 2))
    with pytest.raises(runtime.WorkflowError, match='reconstructed selected work changed'):
        asyncio.run(task.execute({**selection, 'tool': 'source.locate'}, 2))
    assert len(calls) == 1


def test_reasoning_is_one_original_action_with_same_credit_path():
    task, saved, calls, events = make_task({})
    task.workflow.specialist = lambda source: SimpleNamespace(execute_reasoning=lambda context, selection, key:
        {'status': 'completed', 'record_refs': ['finding'], 'changed_record_refs': ['finding']})
    selection = {'kind': 'reason', 'commit': {}}
    assert asyncio.run(task.execute(selection, 4)) == {'index': 4, 'credit': 2.5}
    assert calls == [] and events == ['received', 'grading', 'credit']
    assert json.loads(saved[4]['result'])['record_refs'] == ['finding']


def test_wait_preserves_previous_credit_without_scientific_grading():
    task, saved, calls, events = make_task({})
    async def wait(source, condition, index):
        return {'status': 'completed', 'condition': condition}
    task.workflow.perform_selected_wait = wait
    task.workflow.last_observed_credit = lambda source: 1.25
    selection = {'kind': 'wait', 'condition': {'original': True}}
    assert asyncio.run(task.execute(selection, 5)) == {'index': 5, 'credit': 1.25}
    assert calls == [] and events == ['received']


def test_report_reuses_saved_form_without_recalculating_or_reacquiring():
    task, saved, calls, events = make_task({})
    releases = []
    async def release(episode):
        releases.append(episode)
    task.request = SimpleNamespace(report_contract=object())
    task.workflow.journal.row = lambda table, episode: {'form': json.dumps({'qualified': 'partial'})}
    task.workflow.release = release
    task.workflow.facts = lambda *args, **kwargs: pytest.fail('saved report must not be rebuilt')
    assert asyncio.run(task.finish(None)).as_record() == {'form': {'qualified': 'partial'}}
    assert releases == ['science'] and calls == [] and events == []


def test_assignment_schema_and_role_boundaries_remain_explicit():
    binding = object.__new__(Binding)
    schema = binding.assignment_schema('scientific_process')
    assert schema['additionalProperties'] is False
    assert set(schema['required']) == {'selection', 'evidence_refs', 'constraints', 'context'}
    with pytest.raises(ValueError, match='scientific_process_role_not_bound'):
        binding.assignment_schema('monitor')
    schema['required'].append('changed')
    assert 'changed' not in binding.assignment_schema('scientific_process')['required']


def test_continuation_uses_original_declared_credit_and_settings():
    binding = object.__new__(Binding)
    definition = {'kind': 'fixture_findings'}
    binding.credit_projector = lambda context: SimpleNamespace(as_record=lambda: definition, yield_method='accumulation')
    binding._yield_bindings = {'A106:whole_axis_findings': {'kind': 'accumulation', 'cutoff': 0.125,
        'parameters': {'uncertainty_alpha': 0.05}, 'credit_definition': definition}}
    context = SimpleNamespace(role='scientific_process', assignment={'context': {}})
    actual = binding.yield_controller(context, 2, 'epoch')
    numeric = importlib.import_module(PACKAGE + '.numerical')
    expected = numeric.YieldController('epoch', 2, 0.125, numeric.YieldParameters(uncertainty_alpha=0.05))
    assert actual.state() == expected.state()
    binding._yield_bindings['A106:whole_axis_findings']['credit_definition'] = {'kind': 'other'}
    with pytest.raises(ValueError, match='scientific_yield_credit_definition_mismatch'):
        binding.yield_controller(context, 2, 'epoch')
