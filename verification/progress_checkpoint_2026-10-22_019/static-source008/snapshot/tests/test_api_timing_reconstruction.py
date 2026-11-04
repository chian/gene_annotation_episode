"""Actual detached timing-enabled fixed-case worker with a local HTTP fixture.

The bootstrap supplies a declared fixture client to the existing caller tool
constructor in both processes. Production factory/source/assignment/receipt
comparisons and method_loop durable worker remain unchanged. The model-service
transport is scripted, so this is engineering evidence, not model science or
public HMMER deployment.
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
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.provider_jobs import RemoteSearches
from gene_annotation_episode.public_search_operations import hmmer_client_binding_sha256
from gene_annotation_episode.runtime import Workflow, TypedReportContract, assemble_workflow
from gene_annotation_episode.state import Store
from method_loop.archive import ArchivedRecord
from method_loop.durable import DurableExecutionError, DurableExecutionStore, content_digest
from test_assembled_service_setup import PUBLICATION, RETRIEVAL, ROOT_ROLES
from test_case_execution import PARAMETERS, POLICY, prepared
from test_hmmer_api_progress import LocalHmmerClient, local_service
from test_homology_episode_runtime import Provider
from test_resource_receipt_reconstruction import BeforeRoot, original_spec
from test_resource_receipt_runtime import FORM


def fixture_tools(original, store, configuration):
    tools = original(store, configuration)
    client = LocalHmmerClient(os.environ['GENE_EPISODE_HTTP_FIXTURE_BASE'])
    tools.clients = client
    tools.remote_searches = RemoteSearches(store, client)
    return tools


BOOTSTRAP = '''
import os
if 'GENE_EPISODE_HTTP_FIXTURE_BASE' in os.environ:
    from gene_annotation_episode import tool_configuration
    from test_hmmer_api_reconstruction import fixture_tools
    _original_tools = tool_configuration.build_tools
    def _explicit_fixture_tools(store, configuration=None):
        return fixture_tools(_original_tools, store, configuration)
    tool_configuration.build_tools = _explicit_fixture_tools
'''

SETUP = '''
from dataclasses import replace
from pathlib import Path
from gene_annotation_episode.assembled_service_setup import bind_assembled_services_with_public_search_timing
from gene_annotation_episode.resource_estimation import ResourceToolEstimator

_base_policy = create_policy

def create_policy(parameters):
    base = _base_policy(parameters)
    operands = parameters['api_services']
    def services(store, *, run_id, directory, job_episodes, resource_estimator,
                 tool_catalog, tool_registry):
        return bind_assembled_services_with_public_search_timing(store, run_id=run_id,
            api_timing=operands['api_timing'],
            directory=directory, job_episodes=job_episodes, resource_estimator=resource_estimator,
            source_directory=Path(operands['source_directory']), tool_catalog=tool_catalog,
            tool_retrieval=operands['tool_retrieval'],
            scientific_child_roles=tuple(operands['scientific_child_roles']),
            handoff_unit=3.25, acquired_record_unit=.375, monitoring_information_unit=.5,
            literature_outcome_page_size=7, monitor_outcome_page_size=13,
            log_window_bytes=123, log_roles=('native_stderr',),
            public_search_registry=operands['registry'], tool_registry=tool_registry)
    return replace(base, initial_known_record_refs=[], episode_record_receipts=True,
        annotation_child_roles=tuple(operands['scientific_child_roles']),
        execution_planning_roles=('annotation', 'scientific_process'),
        resource_estimator=ResourceToolEstimator.with_reported_results(),
        episode_service_factory=services, episode_service_binding=operands,
        episode_service_inputs='actual_tool_registry_v1')
'''

TRANSPORT = '''import json,sys
from pathlib import Path
log=Path(sys.argv[1])
def emit(value): print(json.dumps(value),flush=True)
for line in sys.stdin:
    message=json.loads(line)
    method,params=message.get('method'),message.get('params',{})
    if 'id' not in message: continue
    if method=='initialize': result={}
    elif method=='thread/start':
        result={'thread':{'id':'api-fixture-thread'},'model':params['model'],
                'reasoningEffort':params['config']['model_reasoning_effort']}
    elif method=='turn/start':
        context=json.loads(params['input'][0]['text'])
        assert context['role']=='launch_api'
        previous=context['last_local_outcome']
        name='api_search.check_handoff' if previous else 'api_search.submit'
        if previous:
            assert previous['result']['remote_id']
        with log.open('a') as stream: stream.write(json.dumps(context)+'\\n')
        response={'selection':{'kind':'tool','tool':name,
            'arguments':{} if previous else {'retry_of':None}},'report_update':{}}
        emit({'id':message['id'],'result':{'turn':{'id':'api-fixture-turn'}}})
        emit({'method':'item/completed','params':{'threadId':params['threadId'],
            'item':{'type':'agentMessage','text':json.dumps(response)}}})
        emit({'method':'turn/completed','params':{'threadId':params['threadId'],
            'turn':{'id':'api-fixture-turn','status':'completed'}}})
        continue
    else: raise AssertionError(method)
    emit({'id':message['id'],'result':result})
'''


def test_actual_timing_worker_reopens_original_binding_and_prechoice_snapshots(tmp_path, monkeypatch):
    with local_service() as (service, client):
        base_url = client.base
        monkeypatch.setenv('GENE_EPISODE_HTTP_FIXTURE_BASE', base_url)
        bootstrap = tmp_path/'fixture-bootstrap'
        bootstrap.mkdir()
        (bootstrap/'sitecustomize.py').write_text(BOOTSTRAP)
        monkeypatch.syspath_prepend(str(bootstrap))
        original_builder = tool_configuration.build_tools
        builder = lambda store, configuration=None: fixture_tools(original_builder, store, configuration)
        monkeypatch.setattr(tool_configuration, 'build_tools', builder)
        monkeypatch.setattr(case_execution, 'build_tools', builder)
        case, configuration, policy = prepared(tmp_path)
        configuration['local_jobs'] = {'memory_bytes': 20*1024**3, 'scratch_bytes': 4*1024**3}
        policy.write_text(POLICY + SETUP)
        transport, turns = tmp_path/'transport.py', tmp_path/'turns.jsonl'
        transport.write_text(TRANSPORT)
        configuration['models']['connection']['command'] = [sys.executable, str(transport), str(turns)]
        directory = tmp_path/'run'
        manifest = prepare_case_run(case, directory, configuration)
        registry = {'version': 'public_search_registry_v1', 'registry_ref': 'execution_registry_api_fixture',
            'resource_id': 'api_fixture_resource', 'provider': 'hmmer',
            'client_binding_sha256': hmmer_client_binding_sha256(client)}
        from gene_annotation_episode.api_timing_records import ApiTimingBinding
        from gene_annotation_episode.run_statistics import RunHistory
        history = tmp_path/'reported-history.sqlite'
        RunHistory(history).close()
        timing = ApiTimingBinding(ledger_path=tmp_path/'api-timing.sqlite', history_path=history,
            resource_id='api_fixture_resource', monitoring_information_unit=.5)
        parameters = {**PARAMETERS, 'stop_after': 2, 'api_services': {
            'version': 'explicit_reconstructible_api_fixture_v1',
            'registry': registry, 'source_directory': str(PUBLICATION),
            'api_timing': timing.as_record(),
            'tool_retrieval': deepcopy(RETRIEVAL), 'scientific_child_roles': list(ROOT_ROLES)}}
        with monkeypatch.context() as patched:
            patched.setattr(Workflow, 'build', lambda *a, **k: (_ for _ in ()).throw(BeforeRoot()))
            with pytest.raises(BeforeRoot):
                asyncio.run(run_prepared_case(directory, policy_file=policy,
                    parameters=parameters, provider=Provider([])))
        saved = json.loads((directory/'run.json').read_text())
        run_id, settings = saved['run_id'], {k:v for k,v in saved.items() if k!='run_id'}
        workspace = case/'workspace'
        with Store(workspace) as store, prepared_case_bindings(store, directory) as (_, options):
            workflow = assemble_workflow(store, builder(store, manifest['configuration']), Provider([]),
                directory, run_id, settings,
                **{k:v for k,v in options.items() if k!='binding_definitions'})
            scope = {'subject_refs': [manifest['target_ref']]}
            root = workflow.build('annotation', 'root', settings['goal'], scope)
            product = json.loads((case/'evidence-refs.json').read_text())['product_ref']
            sequence = artifact_path(store, store.get(product)['sequence_ref']).read_bytes()
            launch = {'version': 'resource_launch_assignment_v1', 'job_request': {
                    'provider': 'hmmer', 'subject_ref': product, 'algorithm': 'phmmer',
                    'database': 'fixture', 'parameters': {}, 'page_size': 2},
                'immutable_input_versions': [{'reference': product, 'version': None,
                    'content_sha256': hashlib.sha256(sequence).hexdigest()}],
                'constraints': {'allowed_kinds': ['api']}, 'resource_selection': None,
                'software_knowledge_refs': [], 'resource_knowledge_refs': []}
            contract = TypedReportContract('Return the original assigned API handoff', FORM,
                workflow.resolver(scope, grain='launch'))
            parent = workflow.build('launch', 'launch_parent', 'Establish the selected API work', scope,
                parent=root.goal, parent_path=root.source.path, contract=contract,
                initial={}, episode_assignment=launch)
            binding = workflow.episode_bindings.for_role('launch_api')
            api = next(a for a in binding.adapters.values() if a.capability()['kind']=='api')
            assigned = binding.prepare_assignment(workflow.binding_context(parent.source), 'launch_api',
                {**launch, 'resource_selection': api.information.selection()}, scope, run_id+':api_order')
            contract = TypedReportContract('Return the checked original API receiving interfaces', FORM,
                workflow.resolver(scope, grain='launch_api'))
            child = workflow.build('launch_api', 'api_child', 'Prepare and check assigned API execution', scope,
                parent=parent.goal, parent_path=parent.source.path, contract=contract,
                initial={}, episode_assignment=assigned)
            spec = original_spec(workflow, parent, child, inputs=[{'reference': product,
                'version': None, 'content_sha256': content_digest(store.get(product))}])
            original_order = deepcopy(assigned['adapter_assignment'])
            original_scope = api.ports.operations.open_scope(original_order['job_ref'])
            frozen = workflow.receipts.manifest(child.source.episode_id)
            assert service.calls == [] and not turns.exists()
        # A competing caller source cannot replace the saved policy snapshot.
        policy.write_text('raise AssertionError("Reopen the original saved caller")\n')
        backend = DurableExecutionStore(directory/'episode-execution')
        backend.commission(spec)
        started = backend.start(spec['handle'])

        async def wait_return():
            await asyncio.wait_for(backend.wait_events({'version': 'event_condition_v1',
                'events': [{'handle': spec['handle'], 'event': 'returned', 'after_cursor': 0}],
                'reconsider_at': None}), 60)  # Test deadline only.
        asyncio.run(wait_return())
        status = backend.status(spec['handle'])
        returned = backend.load_return(spec['handle'], status['return_id'])
        assert started['execution_identity']['pid'] != os.getpid()
        assert returned['outcome'] == 'closed' and returned['failure'] is None, returned
        assert returned['completion']['units_consumed'] == 2
        handoff = returned['form']['handoff']
        assert handoff['execution_handle'] == original_order['job_ref']
        assert handoff['resource_selection'] == spec['resource_selection']
        assert handoff['state'] == 'usable'
        calls = [json.loads(line) for line in turns.read_text().splitlines()]
        assert len(calls) == 2 and calls[1]['last_local_outcome']['result']['remote_id']
        assert [row[0] for row in service.calls] == ['POST','GET']
        assert saved['received_execution_timing_information']['api_reported_duration_facts']['ledger']['binding'] == timing.as_record()
        for context in calls:
            capture, = context['api_reported_execution_expectations']
            forecast, = context['api_reported_execution_forecasts']
            assert capture['status'] == 'available' and forecast['reported_result_support'] == {'reported_result_count': 0}
            assert context['api_execution_options'][0]['execution_class_ref'] == forecast['execution_class_ref']
        with Store(workspace) as store, prepared_case_bindings(store, directory) as (_, options):
            workflow = assemble_workflow(store, builder(store, manifest['configuration']), Provider([]),
                directory, run_id, settings,
                **{k:v for k,v in options.items() if k!='binding_definitions'})
            ports = workflow.services.public_search_ports(registry)
            assert ports.operations.open_order(original_order['job_ref']) == original_order
            assert ports.operations.open_scope(original_order['job_ref']) == original_scope
            assert workflow.receipts.manifest(spec['child']['episode_id']) == frozen
            rows = [json.loads(row[0]) for row in store.db.execute(
                'SELECT observation FROM runtime_observations WHERE episode_id=? ORDER BY unit_index',
                (spec['child']['episode_id'],))]
            assert [row['step']['marginal_credit'] for row in rows] == [0,3.25]
            assert store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?',
                (spec['parent']['episode_id'],)).fetchone()[0] == 0
        for name in ('episode_archive','result_archive','facts_archive'):
            item = returned[name]
            assert ArchivedRecord(directory/'archive'/item['file'], item['sha256'], item['index_sha256']).load()
        assert backend.start(spec['handle'])['execution_identity'] == started['execution_identity']
        assert backend.load_return(spec['handle'], status['return_id']) == returned
        assert [row[0] for row in service.calls] == ['POST','GET']
