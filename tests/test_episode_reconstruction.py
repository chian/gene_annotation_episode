"""Actual application child reconstruction and subprocess placement.

The model transport and policy are explicit engineering fixtures. No live
model, biological interpretation or production scientific continuation claim.
"""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

import pytest

from method_loop import EpisodeGoal
from method_loop.archive import ArchivedRecord
from method_loop.durable import DurableExecutionError, DurableExecutionStore, content_digest
from gene_annotation_episode.case_execution import (prepare_case_run, prepared_case_bindings,
                                                    run_prepared_case)
from gene_annotation_episode.independent_execution import make_runtime_binding, open_commission
from gene_annotation_episode.runtime import TypedReportContract, assemble_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from test_case_execution import PARAMETERS, prepared
from test_homology_episode_runtime import Provider
from test_runtime import obj


# A fresh process speaks the real ModelConnection RPC protocol. Its actions
# change with prior outcomes. Only the commissioned child can request turns.
TRANSPORT = '''import json, os, sys
from pathlib import Path
log = Path(sys.argv[1])
gate = Path(str(log)+'.gate')
if gate.exists():
    with gate.open('rb', buffering=0) as stream:
        assert stream.read(1) == b'1'
    gate.unlink()
def emit(value):
    print(json.dumps(value), flush=True)
for line in sys.stdin:
    message = json.loads(line)
    method, params = message.get('method'), message.get('params', {})
    if 'id' not in message:
        continue
    if method == 'initialize':
        result = {}
    elif method == 'thread/start':
        result = {'thread': {'id': 'fixture-child-thread'}, 'model': params['model'],
                  'reasoningEffort': params['config']['model_reasoning_effort']}
    elif method == 'turn/start':
        context = json.loads(params['input'][0]['text'])
        previous = context['last_local_outcome']
        turn = 'second' if previous else 'first'
        with log.open('a') as stream:
            stream.write(json.dumps({'pid': os.getpid(), 'context': context, 'turn': turn})+'\\n')
        response = {'selection': {'kind': 'tool', 'tool': 'state.query',
            'arguments': {'refs': context['scope']['subject_refs']}},
            'report_update': {'finding_state': 'qualified' if previous else 'unknown'}}
        emit({'id': message['id'], 'result': {'turn': {'id': turn}}})
        emit({'method': 'item/completed', 'params': {'threadId': params['threadId'],
            'item': {'type': 'agentMessage', 'text': json.dumps(response)}}})
        emit({'method': 'turn/completed', 'params': {'threadId': params['threadId'],
            'turn': {'id': turn, 'status': 'completed'}}})
        continue
    else:
        raise AssertionError(method)
    emit({'id': message['id'], 'result': result})
'''


def fixture_commission(tmp_path, *, transport_source=TRANSPORT):
    case, configuration, policy_file = prepared(tmp_path, with_protein=False)
    transport, turn_log = tmp_path/'fixture_transport.py', tmp_path/'turns.jsonl'
    transport.write_text(transport_source)
    configuration['models']['connection']['command'] = [sys.executable, str(transport), str(turn_log)]
    run = tmp_path/'run'
    manifest = prepare_case_run(case, run, configuration)
    # Create the saved parent assignment, but run no parent scientific action.
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(run_prepared_case(run, policy_file=policy_file,
            parameters={**PARAMETERS, 'stop_after': 2}, provider=Provider([KeyboardInterrupt()])))
    with Store(case/'workspace') as store:
        saved = json.loads((run/'run.json').read_text())
        run_id, settings = saved.pop('run_id'), saved
        parent_row = store.db.execute('SELECT * FROM runtime_episodes WHERE run_id=?', (run_id,)).fetchone()
        parent_request, parent_path = json.loads(parent_row['request']), json.loads(parent_row['path'])
        scope = store.validate_scope({'subject_refs': [manifest['target_ref']],
            'segments': [{'target_ref': manifest['target_ref'], 'start': 0, 'end': 30, 'unit': 'nt'}]})
        schema = obj({'finding_state': {'type': 'string', 'enum': ['unknown', 'qualified']},
            'subjects': {'type': 'array', 'items': {'type': 'string', 'format': 'reference',
                'x-reference-namespace': 'input'}, 'x-source': 'subject_refs'},
            'local_credit': {'type': 'number', 'x-source': 'credit'}})
        with prepared_case_bindings(store, run) as (_, options):
            workflow = assemble_workflow(store, build_tools(store, manifest['configuration']), Provider([]),
                run, run_id, settings, **{key: value for key, value in options.items() if key != 'binding_definitions'})
            contract = TypedReportContract('Return the bounded fixture interpretation', schema,
                                          workflow.resolver(scope, grain='improvement'))
            episode = workflow.build('improvement', 'selected_child', 'Investigate the assigned fixture bounds', scope,
                parent=EpisodeGoal.from_record(parent_request['goal']),
                parent_path=tuple(tuple(part) for part in parent_path), contract=contract,
                initial={'finding_state': 'unknown'})
        spec = {'version': 'episode_commission_v1', 'handle': 'episode:bounded_fixture_child',
            'operation_key': run_id+':selected_fixture_child', 'run_id': run_id,
            'parent': {'episode_id': parent_row['episode_id'], 'goal_id': parent_request['goal']['goal_id'],
                       'path': parent_path},
            'child': {'episode_id': episode.source.episode_id, 'role': 'improvement', 'key': episode.key,
                'path': [list(part) for part in episode.source.path], 'request': episode.request.as_record(), 'scope': scope},
            'input_versions': [{'reference': manifest['target_ref'], 'version': None,
                                'content_sha256': content_digest(store.get(manifest['target_ref']))}],
            'runtime_binding': make_runtime_binding(store, run, kind='fixed_case'),
            'constraints': {'scope': scope, 'fixture_only': True}, 'resource_selection': None,
            'expectation_snapshot_refs': []}
    return spec, run, case/'workspace', turn_log


def load_return(backend, spec):
    async def wait():
        return await asyncio.wait_for(backend.wait_events({'version': 'event_condition_v1',
            'events': [{'handle': spec['handle'], 'event': 'returned', 'after_cursor': 0}],
            'reconsider_at': None}), 20)
    asyncio.run(wait())
    status = backend.status(spec['handle'])
    return backend.load_return(spec['handle'], status['return_id'])


def test_subprocess_reconstructs_only_selected_ordinary_child_and_original_form(tmp_path):
    spec, run, workspace, turns = fixture_commission(tmp_path)
    backend = DurableExecutionStore(run/'episode-execution')
    backend.commission(spec)
    gate = Path(str(turns)+'.gate')
    os.mkfifo(gate)
    starter = subprocess.run([sys.executable, '-c',
        'import json,sys; from method_loop.durable import DurableExecutionStore; '
        'print(json.dumps(DurableExecutionStore(sys.argv[1]).start(sys.argv[2])))',
        str(run/'episode-execution'), spec['handle']], capture_output=True, text=True, check=True, timeout=20)
    status = json.loads(starter.stdout)
    # The commissioning process has exited before the child's provider is
    # allowed to do work. Test polling below releases this explicit fixture gate.
    deadline = time.monotonic()+15
    while True:
        try:
            descriptor = os.open(gate, os.O_WRONLY | os.O_NONBLOCK)
            break
        except OSError:
            assert time.monotonic() < deadline, backend.status(spec['handle'])
            time.sleep(.01)
    with os.fdopen(descriptor, 'wb', buffering=0) as stream:
        stream.write(b'1')
    returned = load_return(backend, spec)
    assert status['execution_identity']['pid'] != os.getpid()
    assert returned['outcome'] == 'closed', returned
    assert returned['failure'] is None
    assert returned['completion']['units_consumed'] == 2
    assert returned['form'] == {'finding_state': 'qualified',
        'subjects': spec['child']['scope']['subject_refs'], 'local_credit': 0}
    calls = [json.loads(line) for line in turns.read_text().splitlines()]
    assert [call['turn'] for call in calls] == ['first', 'second']
    assert all(call['context']['scope'] == spec['child']['scope'] for call in calls)
    assert all(call['context']['goal'] == spec['child']['request']['goal'] for call in calls)
    with Store(workspace) as store:
        assert store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?',
            (spec['parent']['episode_id'],)).fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?',
            (spec['child']['episode_id'],)).fetchone()[0] == 2
        assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 2
    for field in ('episode_archive', 'result_archive', 'facts_archive'):
        descriptor = returned[field]
        archived = ArchivedRecord(run/'archive'/descriptor['file'], descriptor['sha256'], descriptor['index_sha256'])
        assert archived.load()
    retired = list((run/'providers').glob('*/retired-sessions/*.json'))
    assert len(retired) == 2
    for path in retired:
        retirement = json.loads(path.read_text())
        assert retirement['remaining_active_workers'] == 0 and retirement['local_session_removed']
        assert retirement['episode_id'] == spec['child']['episode_id']
    assert backend.start(spec['handle'])['execution_identity'] == status['execution_identity']
    assert load_return(DurableExecutionStore(run/'episode-execution'), spec) == returned


@pytest.mark.parametrize('changed', ['implementation', 'settings', 'scope', 'inputs', 'policy'])
def test_worker_rejects_changed_pinned_inputs_before_any_model_work(tmp_path, changed):
    spec, run, workspace, turns = fixture_commission(tmp_path)
    if changed == 'implementation':
        spec['runtime_binding']['implementation_sha256'] = '0'*64
    elif changed == 'settings':
        spec['runtime_binding']['settings_sha256'] = '0'*64
    elif changed == 'scope':
        spec['child']['scope']['segments'][0]['end'] = 31
    elif changed == 'inputs':
        spec['input_versions'][0]['content_sha256'] = '0'*64
    else:
        recorded = json.loads((run/'policy-binding.json').read_text())
        (run/recorded['snapshot_file']).write_text('raise AssertionError("changed saved policy")')
    backend = DurableExecutionStore(run/'episode-execution')
    backend.commission(spec)
    backend.start(spec['handle'])
    returned = load_return(backend, spec)
    assert returned['outcome'] == 'execution_failed'
    assert returned['failure']['code'] == 'identity_conflict'
    assert not turns.exists()
    assert returned['completion'] is None and returned['form'] is None


def test_unreconstructible_custom_closures_are_an_explicit_capability_failure(tmp_path):
    spec, run, workspace, turns = fixture_commission(tmp_path)
    with pytest.raises(DurableExecutionError) as error:
        make_runtime_binding(workspace, run, kind='standard_default')
    assert error.value.failure['code'] == 'unavailable_binding'
    assert not turns.exists()


def test_execution_failure_preserves_committed_partial_child_records(tmp_path):
    transport = TRANSPORT.replace("        previous = context['last_local_outcome']",
        "        previous = context['last_local_outcome']\n"
        "        if previous:\n            sys.exit(3)")
    transport = transport.replace("'tool': 'state.query'", "'tool': 'sequence.translate'")
    transport = transport.replace("'arguments': {'refs': context['scope']['subject_refs']}",
        "'arguments': {'subject_ref': context['scope']['subject_refs'][0], 'code': 11, 'cds': False, "
        "'start': context['scope']['segments'][0]['start'], 'end': context['scope']['segments'][0]['end']}")
    spec, run, workspace, turns = fixture_commission(tmp_path, transport_source=transport)
    backend = DurableExecutionStore(run/'episode-execution')
    backend.commission(spec)
    backend.start(spec['handle'])
    returned = load_return(backend, spec)
    assert returned['outcome'] == 'execution_failed'
    assert returned['completion'] is None and returned['form'] is None
    failure = returned['failure']
    assert failure['code'] == 'execution_failed' and failure['partial_record_refs']
    with Store(workspace) as store:
        retained = [store.get(ref) for ref in failure['partial_record_refs']]
        assert any(record['record_type'] == 'product' for record in retained)
        assert store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?',
            (spec['child']['episode_id'],)).fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?',
            (spec['parent']['episode_id'],)).fetchone()[0] == 0
    assert len(list((run/'providers').glob('*/retired-sessions/*.json'))) == 2


def test_direct_factory_releases_only_its_own_provider_resources_on_interruption(tmp_path):
    spec, run, workspace, turns = fixture_commission(tmp_path)
    released, exits = [], []
    from gene_annotation_episode.providers import ModelConnection
    original_release, original_exit = ModelConnection.release, ModelConnection.__aexit__

    async def release(self, episode_id):
        released.append(episode_id)
        return await original_release(self, episode_id)

    async def close(self, *exception):
        exits.append(self.directory)
        return await original_exit(self, *exception)

    async def interrupted():
        with patch.object(ModelConnection, 'release', release), patch.object(ModelConnection, '__aexit__', close):
            with pytest.raises(RuntimeError, match='fixture interruption'):
                async with open_commission(spec) as runtime:
                    assert runtime['context'].path == tuple(tuple(part) for part in spec['parent']['path'])
                    assert runtime['episode'].request.as_record() == spec['child']['request']
                    raise RuntimeError('fixture interruption')

    asyncio.run(interrupted())
    assert released == [spec['child']['episode_id']]
    assert len(exits) == 1
    assert not turns.exists()


def test_standard_binding_restores_frozen_receipt_prefix_without_a_parent_loop(tmp_path):
    from gene_annotation_episode.default_scientific_binding import bind_default_science
    from gene_annotation_episode.runtime import controller_from_settings, run_workflow
    workspace, run = tmp_path/'workspace', tmp_path/'run'
    with Store(workspace) as store:
        target = store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')['subject_refs'][0]
        def source(label):
            artifact = store.artifact(label, 'text/plain')
            return store.put('source', {'provider': 'fixture.receipt_input', 'accession': label, 'uri': None,
                'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': 'fixture',
                'retrieved_at': None, 'parent_source_refs': [], 'operand_refs': [target]}, origin='tool')['id']
        inherited, later = source('original'), source('later')
        with pytest.raises(KeyboardInterrupt):
            asyncio.run(run_workflow(store, build_tools(store), provider=Provider([KeyboardInterrupt()]),
                run_dir=run, initial_known_record_refs=[inherited]))
        manifest = json.loads((run/'run.json').read_text())
        run_id, settings = manifest.pop('run_id'), manifest
        options = bind_default_science(store, run_dir=run, resume=True, provider_config=None,
            credit_policy=None, initial_known_record_refs=None, project_child_credit=None,
            project_annotation_score=None, binding_definitions=None)
        workflow = assemble_workflow(store, build_tools(store), Provider([]), run, run_id, settings,
            controller_factory=controller_from_settings(settings), **{key: options[key] for key in
                ('project_credit', 'project_child_credit', 'project_annotation_score', 'initial_known_record_refs')})
        row = store.db.execute('SELECT * FROM runtime_episodes WHERE run_id=?', (run_id,)).fetchone()
        parent_request, parent_path = json.loads(row['request']), json.loads(row['path'])
        scope = {'subject_refs': [target]}
        contract = TypedReportContract('Return received scientific information',
            obj({'state': {'type': 'string', 'enum': ['unknown', 'qualified']}}), workflow.resolver(scope))
        episode = workflow.build('improvement', 'frozen_child', 'Investigate original received evidence', scope,
            parent=EpisodeGoal.from_record(parent_request['goal']),
            parent_path=tuple(tuple(part) for part in parent_path), contract=contract, initial={'state': 'unknown'})
        frozen = episode.request.message.as_record()['knowledge_inheritance']
        original_known = set(workflow.receipts.known(episode.source.episode_id))
        workflow.receipts.receive(row['episode_id'], [later], kind='own_action', source_index=8)
        spec = {'version': 'episode_commission_v1', 'handle': 'episode:frozen_fixture',
            'operation_key': 'fixture:frozen_child', 'run_id': run_id,
            'parent': {'episode_id': row['episode_id'], 'goal_id': parent_request['goal']['goal_id'], 'path': parent_path},
            'child': {'episode_id': episode.source.episode_id, 'role': 'improvement', 'key': episode.key,
                'path': [list(part) for part in episode.source.path], 'request': episode.request.as_record(), 'scope': scope},
            'input_versions': [], 'runtime_binding': make_runtime_binding(store, run),
            'constraints': {'fixture_only': True}, 'resource_selection': None, 'expectation_snapshot_refs': []}

    async def inspect():
        async with open_commission(spec) as runtime:
            child = runtime['episode'].source
            receipts = child.workflow.receipts
            assert receipts.manifest(child.episode_id) == frozen
            assert set(receipts.known(child.episode_id)) == original_known
            assert {target, inherited} <= original_known
            assert later not in receipts.known(child.episode_id)
            assert child.workflow.execution_binding == spec['runtime_binding']
            assert runtime['episode'].request.as_record() == spec['child']['request']
    asyncio.run(inspect())
    with Store(workspace) as store:
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 2
