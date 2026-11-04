"""Real fixed_case detached scientific worker; all provider decisions are scripted.

No public provider or native computation is invoked. Existing fixture bootstrap
supplies the same explicit loopback client identity in the parent and worker.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

import pytest

from gene_annotation_episode import case_execution, independent_execution, tool_configuration
from gene_annotation_episode.case_execution import prepare_case_run, prepared_case_bindings, run_prepared_case
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.public_search_operations import hmmer_client_binding_sha256
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.runtime import Workflow, assemble_workflow
from gene_annotation_episode.state import Store
from method_loop.archive import ArchivedRecord
from method_loop.durable import DurableExecutionStore
from test_api_execution_planning_connected import MARKER, synthetic_ap_source
from test_api_timing_reconstruction import BOOTSTRAP, SETUP as TIMING_SETUP, fixture_tools
from test_assembled_service_setup import RETRIEVAL, ROOT_ROLES
from test_case_execution import PARAMETERS, POLICY, prepared
from test_hmmer_api_progress import local_service
from test_homology_episode_runtime import Provider
from test_resource_receipt_reconstruction import BeforeRoot
from test_runtime import ScriptedProvider, obj


SETUP = TIMING_SETUP.replace('bind_assembled_services_with_public_search_timing',
                            'bind_assembled_services_with_public_search_timing_planning')

TRANSPORT = r'''import json,sys
from pathlib import Path
log=Path(sys.argv[1])
def emit(value): print(json.dumps(value),flush=True)
for line in sys.stdin:
    message=json.loads(line)
    method,params=message.get('method'),message.get('params',{})
    if 'id' not in message: continue
    if method=='initialize': result={}
    elif method=='thread/start':
        result={'thread':{'id':'planning-fixture-thread'},'model':params['model'],
                'reasoningEffort':params['config']['model_reasoning_effort']}
    elif method=='turn/start':
        context=json.loads(params['input'][0]['text'])
        assert 'scientific_process' in context
        previous=context['last_local_outcome']
        if previous:
            assert context['api_execution_proposal']==previous['result']
            assert context['api_reported_execution_forecasts'][0]['reported_result_support']=={'reported_result_count':0}
            selected={'kind':'tool','tool':'episode.history','arguments':{'view':'records','decision_indices':[0]}}
        else:
            assert 'api_execution_proposal' not in context
            selected={'kind':'tool','tool':'execution.estimate',
                'arguments':context['scientific_process']['assignment']['context']['estimate_input']}
        with log.open('a') as stream: stream.write(json.dumps(context)+'\n')
        response={'selection':selected,'report_update':{}}
        emit({'id':message['id'],'result':{'turn':{'id':'planning-fixture-turn'}}})
        emit({'method':'item/completed','params':{'threadId':params['threadId'],
            'item':{'type':'agentMessage','text':json.dumps(response)}}})
        emit({'method':'turn/completed','params':{'threadId':params['threadId'],
            'turn':{'id':'planning-fixture-turn','status':'completed'}}})
        continue
    else: raise AssertionError(method)
    emit({'id':message['id'],'result':result})
'''


def assert_composed_owner(workflow):
    planner = workflow.tools.api_execution_planner
    adapter = next(a for a in workflow.episode_bindings.for_role('launch').adapters.values()
                   if a.capability()['kind'] == 'api')
    assert planner.ports is adapter.ports is workflow.api_timing_reader.ports
    assert planner.timing is adapter.timing is workflow.api_timing_reader.ledger
    assert planner.store is adapter.store is workflow.store
    assert planner.ports.operations.remote_searches is workflow.tools.remote_searches
    assert planner.ports.result_publisher.tools is workflow.tools
    assert planner.resource_estimator is workflow.resource_estimator
    return planner


def test_actual_scientific_worker_restores_planning_map_original_proposal_and_caller(tmp_path, monkeypatch):
    with local_service() as (http, client):
        monkeypatch.setenv('GENE_EPISODE_HTTP_FIXTURE_BASE', client.base)
        bootstrap = tmp_path / 'fixture-bootstrap'
        bootstrap.mkdir()
        (bootstrap / 'sitecustomize.py').write_text(BOOTSTRAP)
        monkeypatch.syspath_prepend(str(bootstrap))
        original_builder = tool_configuration.build_tools
        def builder(store, configuration=None):
            return fixture_tools(original_builder, store, configuration)
        monkeypatch.setattr(tool_configuration, 'build_tools', builder)
        monkeypatch.setattr(case_execution, 'build_tools', builder)
        case, configuration, policy = prepared(tmp_path)
        configuration['local_jobs'] = {'memory_bytes': 20 * 1024**3,
                                       'scratch_bytes': 4 * 1024**3}
        policy.write_text(POLICY + SETUP)
        transport, turns = tmp_path / 'transport.py', tmp_path / 'turns.jsonl'
        transport.write_text(TRANSPORT)
        configuration['models']['connection']['command'] = [sys.executable, str(transport), str(turns)]
        source = synthetic_ap_source(tmp_path / 'synthetic-options')
        directory = tmp_path / 'run'
        manifest = prepare_case_run(case, directory, configuration)
        registry = {'version': 'public_search_registry_v1',
            'registry_ref': 'execution_registry_api_planning_worker', 'resource_id': 'api-planning-worker',
            'provider': 'hmmer', 'client_binding_sha256': hmmer_client_binding_sha256(client)}
        from gene_annotation_episode.api_timing_records import ApiTimingBinding
        from gene_annotation_episode.run_statistics import RunHistory
        history = tmp_path / 'reported-history.sqlite'
        RunHistory(history).close()
        timing = ApiTimingBinding(ledger_path=tmp_path / 'api-timing.sqlite', history_path=history,
            resource_id=registry['resource_id'], monitoring_information_unit=.5)
        parameters = {**PARAMETERS, 'stop_after': 2, 'api_services': {
            'version': 'explicit_reconstructible_api_planning_fixture_v1',
            'api_execution_planning': deepcopy(MARKER), 'registry': registry,
            'source_directory': str(source), 'api_timing': timing.as_record(),
            'tool_retrieval': deepcopy(RETRIEVAL), 'scientific_child_roles': list(ROOT_ROLES)}}
        with monkeypatch.context() as patched:
            patched.setattr(Workflow, 'build', lambda *_a, **_k: (_ for _ in ()).throw(BeforeRoot()))
            with pytest.raises(BeforeRoot):
                asyncio.run(run_prepared_case(directory, policy_file=policy,
                    parameters=parameters, provider=Provider([])))
        saved = json.loads((directory / 'run.json').read_text())
        run_id, settings = saved['run_id'], {k: v for k, v in saved.items() if k != 'run_id'}
        workspace = case / 'workspace'
        with Store(workspace) as store, prepared_case_bindings(store, directory) as (_, options):
            workflow = assemble_workflow(store, builder(store, manifest['configuration']), Provider([]),
                directory, run_id, settings,
                **{k: v for k, v in options.items() if k != 'binding_definitions'})
            planner = assert_composed_owner(workflow)
            assert workflow.resource_estimator.as_record() == ResourceToolEstimator.with_reported_results().as_record()
            scope = {'subject_refs': [manifest['target_ref']]}
            root = workflow.build('annotation', 'root', settings['goal'], scope)
            product = json.loads((case / 'evidence-refs.json').read_text())['product_ref']
            sequence = store.get_artifact(store.get(product)['sequence_ref'])
            estimate_input = {'tool': 'public.hmmer.search',
                'arguments': {'subject_ref': product, 'algorithm': 'phmmer', 'database': 'fixture'},
                'resource_selection': next(a for a in workflow.episode_bindings.for_role('launch').adapters.values()
                    if a.capability()['kind'] == 'api').information.selection(),
                'constraints': {'allowed_kinds': ['api']},
                'immutable_input_versions': [{'reference': product, 'version': None,
                    'content_sha256': hashlib.sha256(sequence).hexdigest()}]}
            library = workflow.scientific_process_binding.library
            schema = obj({'forecasts': deepcopy(workflow.report_sources('scientific_process')[
                'api_reported_execution_forecasts']['report_schema'])})
            selection = {'kind': 'episode_child', 'role': 'scientific_process',
                'goal': 'Read original timing support for the caller-proposed search', 'scope': scope,
                'purpose': 'Return only the requested original forecast',
                'schema_json': json.dumps(schema), 'initial_report_json': '{}',
                'assignment': {'selection': {'version': 'scientific_process_selection_v2',
                    'annotation_ref': library.reference('A01'), 'thought_ref': library.reference('P01'),
                    'tools': ['execution.estimate']}, 'evidence_refs': [product],
                    'constraints': {'target_only': True}, 'context': {'estimate_input': estimate_input}}}
            runtime_binding = independent_execution.make_runtime_binding(store, directory, kind='fixed_case')
            workflow.configure_execution(runtime_binding)
            workflow.provider = ScriptedProvider([{'selection': selection, 'report_update': {}}])
            source_root = root.source
            answer, index, context, action_schema = asyncio.run(source_root.call(
                {'visible_record_refs': []}, workflow.action_schema(source_root)))
            unit = source_root.apply_response(answer, index, context, action_schema)
            assert unit is not None
            spec, = workflow.commissions.recover_selected(source_root.episode_id)
            original_request = deepcopy(spec['child']['request'])
            frozen = workflow.receipts.manifest(spec['child']['episode_id'])
            original_catalog = deepcopy(workflow.scientific_process_binding.tool_library.catalog())
            assert spec['resource_selection'] is None
            native_refs = list(dict.fromkeys(snapshot['ref'] for key in
                ('execution_expectations', 'native_execution_expectations')
                for snapshot in (context.get(key) or {}).get('snapshots', [])))
            assert spec['expectation_snapshot_refs'] == native_refs
            assert 'api_execution_proposal' not in context
            assert not turns.exists() and not http.calls
            assert store.db.execute('SELECT count(*) FROM provider_jobs').fetchone()[0] == 0
        policy.write_text('raise AssertionError("Use the saved explicit planning caller")\n')
        backend = DurableExecutionStore(directory / 'episode-execution')
        backend.commission(spec)
        started = backend.start(spec['handle'])
        async def wait_return():
            await asyncio.wait_for(backend.wait_events({'version': 'event_condition_v1',
                'events': [{'handle': spec['handle'], 'event': 'returned', 'after_cursor': 0}],
                'reconsider_at': None}), 60)  # Isolated test deadline, not runtime policy.
        asyncio.run(wait_return())
        status = backend.status(spec['handle'])
        returned = backend.load_return(spec['handle'], status['return_id'])
        assert started['execution_identity']['pid'] != os.getpid()
        assert returned['outcome'] == 'closed' and returned['failure'] is None, returned
        assert returned['completion']['units_consumed'] == 2
        forecast, = returned['form']['forecasts']
        assert forecast['reported_result_support'] == {'reported_result_count': 0}
        assert forecast['expected_total_seconds'] is None
        calls = [json.loads(line) for line in turns.read_text().splitlines()]
        assert len(calls) == 2
        original_proposal = calls[1]['api_execution_proposal']
        assert original_proposal['arguments'] == estimate_input['arguments']
        assert original_proposal['api_reported_execution_forecasts'] == [forecast]
        assert not http.calls
        with Store(workspace) as store, prepared_case_bindings(store, directory) as (_, options):
            workflow = assemble_workflow(store, builder(store, manifest['configuration']), Provider([]),
                directory, run_id, settings,
                **{k: v for k, v in options.items() if k != 'binding_definitions'})
            assert_composed_owner(workflow)
            assert workflow.scientific_process_binding.tool_library.catalog() == original_catalog
            assert workflow.receipts.manifest(spec['child']['episode_id']) == frozen
            row = workflow.journal.row('runtime_episodes', spec['child']['episode_id'])
            assert json.loads(row['request']) == original_request
            action = workflow.journal.row('runtime_actions', spec['child']['episode_id'], 0)
            assert json.loads(action['result'])['result'] == original_proposal
            assert store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?',
                (spec['child']['episode_id'],)).fetchone()[0] == 2
            assert store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?',
                (spec['parent']['episode_id'],)).fetchone()[0] == 0
            assert store.db.execute('SELECT count(*) FROM provider_jobs').fetchone()[0] == 0
            assert store.count('native_execution') == 0
        for name in ('episode_archive', 'result_archive', 'facts_archive'):
            item = returned[name]
            assert ArchivedRecord(directory / 'archive' / item['file'], item['sha256'], item['index_sha256']).load()
        assert backend.start(spec['handle'])['execution_identity'] == started['execution_identity']
        assert backend.load_return(spec['handle'], status['return_id']) == returned
        assert not http.calls
