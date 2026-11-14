"""Actual private Results acquisition of an original API handoff.

These are explicitly saved singleton invocations. They test the existing raw
binding/action contract and do not authorize a scientific or HPC parent edge.
Only the original HTTP response fixture and task checkpoint port are controlled.
"""
import asyncio
from copy import deepcopy
import json
import os
from types import SimpleNamespace

import pytest

from .api_cases import Case, HOMES, canonical, module, rows, task_case


@pytest.fixture(params=HOMES, ids=HOMES)
def acquired(request, tmp_path):
    original = Case(tmp_path, request.param)
    try:
        launch = original.act('api.uniprot.record')
        assert launch['status'] == 'completed'
        handoff = launch['result']['handoff_ref']
        home = original.home.removesuffix('execution_job_submission/api_job_execution') + 'execution_result_acquisition'
        options = {**original.options, 'task_yield_profiles': {
            **original.options['task_yield_profiles'], 'results:api_uniprot': {'cutoff': .5, 'parameters': {}}}}
        binding = module(home + '/episode').ExecutionEpisode(original.services, **options)
        selected = {'version': 'execution_results_assignment_v1', 'handoff_ref': handoff, 'selector': {}}
        assignment = binding.prepare_assignment(original.context, 'results', selected,
            original.scope, original.run_id + ':' + original.episode_id + ':1')
        assert assignment == selected
        path = (('results', 'controlled-original-api-acquisition'),)
        episode_id = module('method_loop.identities').EpisodeRef(original.run_id, path).episode_id
        inherited = original.receipts.bind(episode_id)
        original.receipts.receive(episode_id, [*original.scope['subject_refs'], handoff], kind='initial')
        saved_request = {'message': {'scope': deepcopy(original.scope),
            'episode_assignment': deepcopy(assignment), 'knowledge_inheritance': inherited}}
        context = module('episode_bindings').BindingContext(original.run_id, episode_id, 'results',
            path, original.scope, assignment, saved_request)
        original.journal.save('runtime_episodes', {'episode_id': episode_id,
            'path': module('runtime')._json(path), 'request': module('runtime')._json(saved_request),
            'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
        binding.initialize(context)
        def selection():
            return {'run_id': original.run_id, 'episode_id': episode_id,
                'known_record_refs': list(original.receipts.known(episode_id)),
                'initial_known_record_refs': list(original.receipts.known(episode_id, baseline=True))}
        value = SimpleNamespace(store=original.store, journal=original.journal, receipts=original.receipts,
            run_id=original.run_id, scope=original.scope, path=path, episode_id=episode_id,
            request=saved_request, context=context, binding=binding, home=home, selection=selection,
            original=original, handoff=handoff, options=options)
        yield value
    finally:
        original.close()


def test_actual_results_acquires_retained_uniprot_payload_once(acquired, record_property):
    value = acquired; task = task_case(value)
    chosen = {'kind': 'tool', 'tool': 'api.uniprot.collect', 'arguments': {}}
    old_calls = deepcopy(value.original.client.calls)
    returned = asyncio.run(task.task.execute(chosen, 0))
    action = dict(value.journal.row('runtime_actions', value.episode_id, 0))
    payload = json.loads(action['result'])
    assert payload['status'] in {'completed', 'partial'} and payload['record_refs']
    assert json.loads(action['action']) == chosen
    assert value.original.client.calls == old_calls
    assert len(task.executions) == len(task.observations) == len(task.projections) == 1
    assert returned.as_record()['credit'] == action['credit']
    assert task.task.last_outcome == payload
    known = set(value.selection()['known_record_refs'])
    assert set(payload['record_refs']) <= known and value.handoff in known
    before = rows(value.store)
    assert asyncio.run(task.task.execute(chosen, 0)).as_record() == returned.as_record()
    assert rows(value.store) == before and len(task.executions) == 1
    assert value.original.client.calls == old_calls
    if os.environ.get('A104_API_OWNER_PHASE') == 'connected':
        assert type(value.binding.api_execution) is module(value.home + '/api_acquisition').APIResultAcquisition
    record_property('original_results_acquisition', json.dumps(canonical({
        'home': value.home, 'context': value.context.as_record(), 'selected': chosen,
        'action_row': action, 'returned_payload': payload, 'controller_input': returned.as_record(),
        'credit_view': task.projections[0], 'http_calls': old_calls,
        'receipt_rows': before['runtime_record_receipts'], 'same_key_replay_all_rows_unchanged': True,
        'controlled_singleton_invocation_not_parent_commission': True}), sort_keys=True))


def test_results_rejects_submission_without_losing_returned_invalid(acquired, record_property):
    value = acquired; task = task_case(value)
    chosen = {'kind': 'tool', 'tool': 'api.uniprot.record', 'arguments': {}}
    calls = deepcopy(value.original.client.calls)
    result = asyncio.run(task.task.execute(chosen, 0))
    row = dict(value.journal.row('runtime_actions', value.episode_id, 0))
    payload = json.loads(row['result'])
    assert payload['status'] == 'invalid'
    assert json.loads(row['action']) == chosen
    assert task.observations == [(0, chosen, payload)] and len(task.projections) == 1
    assert value.original.client.calls == calls
    before = rows(value.store)
    assert asyncio.run(task.task.execute(chosen, 0)).as_record() == result.as_record()
    assert rows(value.store) == before and len(task.executions) == 1
    record_property('original_wrong_operation_return', json.dumps(canonical({'selection': chosen,
        'payload': payload, 'controller_input': result.as_record(), 'action_row': row,
        'original_return_observed_once': True, 'http_calls': calls}), sort_keys=True))
