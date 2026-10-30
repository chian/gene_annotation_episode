"""Actual detached scientific worker using the new caller and scripted transport.

Only loopback HTTP and fixture decisions run. The fixture continuation law is
explicit in its saved caller; it establishes no production numerical policy.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
import sys

import pytest

from gene_annotation_episode import case_execution, independent_execution, tool_configuration
from gene_annotation_episode.case_execution import (
    prepare_case_run, prepared_case_bindings, run_prepared_case,
)
from gene_annotation_episode.runtime import Workflow, assemble_workflow
from gene_annotation_episode.state import Store
from method_loop.archive import ArchivedRecord
from method_loop.durable import DurableExecutionStore
from test_api_execution_planning_connected import synthetic_ap_source
from test_api_timing_connected import reported_service
from test_api_timing_reconstruction import BOOTSTRAP, fixture_tools
from test_case_execution import prepared
from test_direct_hmmer_timing_binding import direct_parameters
from test_direct_hmmer_timing_connected import assert_final_owners
from test_homology_episode_runtime import Provider
from test_resource_receipt_runtime import own
from test_resource_receipt_reconstruction import BeforeRoot
from test_runtime import ScriptedProvider, obj


POLICY = '''from dataclasses import replace
from gene_annotation_episode.api_planning_case_policy import create_policy as actual_policy
from gene_annotation_episode.numerical import YieldController, YieldEstimate, NumericBand

def create_policy(parameters):
    base = actual_policy(parameters)
    original = parameters['policy']['controller']
    settings = {k:v for k,v in original.items() if k not in ('cost','cost_by_role')}
    def fixture_estimate(history, settings, contexts):
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history)>=3 else 1),
            settings, {'kind':'isolated_scripted_worker_fixture'})
    def controller(path, initial):
        cost = original['cost_by_role'].get(path[-1][0], original['cost'])
        return YieldController(str(path), initial, cost, settings,
            estimate_with_context=fixture_estimate)
    return replace(base, controller_factory=controller,
        controller_definition={'kind':'isolated_scripted_worker_fixture',
            'completed_own_actions':3, 'original_operands':original})
'''

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
        result={'thread':{'id':'direct-timing-fixture-thread'},'model':params['model'],
            'reasoningEffort':params['config']['model_reasoning_effort']}
    elif method=='turn/start':
        context=json.loads(params['input'][0]['text'])
        process=context['scientific_process']
        previous=context['last_local_outcome']
        if previous is None:
            assert context['monitoring_information_credit']==0
            selected={'kind':'tool','tool':'public.hmmer.search',
                'arguments':process['assignment']['context']['search_arguments']}
        elif 'api_execution_proposal' not in context:
            assert previous['status']=='completed'
            assert previous['result']['job_ref']
            assert context['monitoring_information_credit']==1
            selected={'kind':'tool','tool':'execution.estimate',
                'arguments':process['assignment']['context']['estimate_input']}
        else:
            assert context['api_execution_proposal']==previous['result']
            forecast,=context['api_reported_execution_forecasts']
            assert forecast['reported_result_support']=={'reported_result_count':1}
            assert forecast['expected_total_seconds']==2.75
            assert context['monitoring_information_credit']==1
            selected={'kind':'tool','tool':'episode.history',
                'arguments':{'view':'records','decision_indices':[0,1]}}
        with log.open('a') as f:f.write(json.dumps(context)+'\n')
        response={'selection':selected,'report_update':{}}
        emit({'id':message['id'],'result':{'turn':{'id':'direct-timing-fixture-turn'}}})
        emit({'method':'item/completed','params':{'threadId':params['threadId'],
            'item':{'type':'agentMessage','text':json.dumps(response)}}})
        emit({'method':'turn/completed','params':{'threadId':params['threadId'],
            'turn':{'id':'direct-timing-fixture-turn','status':'completed'}}})
        continue
    else: raise AssertionError(method)
    emit({'id':message['id'],'result':result})
'''

NATIVE_BOOTSTRAP = '''
if 'GENE_EPISODE_HTTP_FIXTURE_BASE' in os.environ:
    from gene_annotation_episode.resource_episodes import HomologyResourceAdapter
    def _declared_native_fixture_capability(self):
        return {'resource_id':self.resource_id,'kind':'local','availability':'unknown',
            'observed_at':'2026-10-22T00:00:00+00:00','provenance_refs':[],
            'knowledge_entry_ids':[],'tool_names':[]}
    HomologyResourceAdapter.capability = _declared_native_fixture_capability
'''


def native_fixture_capability(adapter):
    return {'resource_id': adapter.resource_id, 'kind': 'local', 'availability': 'unknown',
        'observed_at': '2026-10-22T00:00:00+00:00', 'provenance_refs': [],
        'knowledge_entry_ids': [], 'tool_names': []}


def test_real_detached_direct_search_restores_caller_map_timing_and_original_forecast(
        tmp_path, monkeypatch):
    with reported_service() as (http, client):
        monkeypatch.setenv('GENE_EPISODE_HTTP_FIXTURE_BASE', client.base)
        bootstrap = tmp_path / 'fixture-bootstrap'
        bootstrap.mkdir()
        (bootstrap / 'sitecustomize.py').write_text(BOOTSTRAP + NATIVE_BOOTSTRAP)
        monkeypatch.syspath_prepend(str(bootstrap))
        from gene_annotation_episode.resource_episodes import HomologyResourceAdapter
        monkeypatch.setattr(HomologyResourceAdapter, 'capability', native_fixture_capability)
        original_builder = tool_configuration.build_tools
        def builder(store, configuration=None):
            return fixture_tools(original_builder, store, configuration)
        monkeypatch.setattr(tool_configuration, 'build_tools', builder)
        monkeypatch.setattr(case_execution, 'build_tools', builder)
        case, configuration, policy = prepared(tmp_path)
        configuration['local_jobs'] = {'memory_bytes': 20 * 1024**3,
            'scratch_bytes': 4 * 1024**3}
        policy.write_text(POLICY)
        transport, turns = tmp_path / 'transport.py', tmp_path / 'turns.jsonl'
        transport.write_text(TRANSPORT)
        configuration['models']['connection']['command'] = [
            sys.executable, str(transport), str(turns)]
        source = synthetic_ap_source(tmp_path / 'synthetic-options')
        directory = tmp_path / 'run'
        manifest = prepare_case_run(case, directory, configuration)
        product = json.loads((case / 'evidence-refs.json').read_text())['product_ref']
        parameters = direct_parameters(tmp_path, client=client)
        parameters['services']['source_directory'] = str(source)
        parameters['policy']['operational']['registry_ref'] = manifest[
            'registry_configuration']['registry_ref']
        parameters['policy']['scientific_progress']['initial_known_record_refs'] = [
            manifest['target_ref'], product]
        from gene_annotation_episode.run_statistics import RunHistory
        RunHistory(parameters['services']['api_timing']['history_path']).close()
        with monkeypatch.context() as patched:
            patched.setattr(Workflow, 'build', lambda *_a, **_k:
                (_ for _ in ()).throw(BeforeRoot()))
            with pytest.raises(BeforeRoot):
                asyncio.run(run_prepared_case(directory, policy_file=policy,
                    parameters=parameters, provider=Provider([])))
        saved = json.loads((directory / 'run.json').read_text())
        run_id = saved['run_id']
        settings = {k: v for k, v in saved.items() if k != 'run_id'}
        workspace = case / 'workspace'
        with Store(workspace) as store, prepared_case_bindings(store, directory) as (_, options):
            workflow = assemble_workflow(store, builder(store, manifest['configuration']),
                Provider([]), directory, run_id, settings,
                **{k: v for k, v in options.items() if k != 'binding_definitions'})
            from types import SimpleNamespace
            assert_final_owners(SimpleNamespace(workflow=workflow, tools=workflow.tools))
            scope = {'subject_refs': [manifest['target_ref']]}
            root = workflow.build('annotation', 'root', settings['goal'], scope)
            sequence = store.get_artifact(store.get(product)['sequence_ref'])
            search = {'subject_ref': product, 'algorithm': 'phmmer',
                'database': 'fixture', 'parameters': {}, 'page_size': 2}
            adapter = next(a for a in workflow.episode_bindings.for_role('launch').adapters.values()
                if a.capability()['kind'] == 'api')
            estimate = {'tool': 'public.hmmer.search', 'arguments': deepcopy(search),
                'resource_selection': adapter.information.selection(),
                'constraints': {'allowed_kinds': ['api']},
                'immutable_input_versions': [{'reference': product, 'version': None,
                    'content_sha256': hashlib.sha256(sequence).hexdigest()}]}
            library = workflow.scientific_process_binding.library
            schema = obj({name: deepcopy(workflow.report_sources('scientific_process')[
                source_name]['report_schema']) for name, source_name in (
                    ('timing', 'api_execution_measurements'),
                    ('forecasts', 'api_reported_execution_forecasts'))})
            selection = {'kind': 'episode_child', 'role': 'scientific_process',
                'goal': 'Acquire a fixture sequence comparison and inspect its timing support',
                'scope': scope, 'purpose': 'Return only original timing and forecast facts',
                'schema_json': json.dumps(schema), 'initial_report_json': '{}',
                'assignment': {'selection': {'version': 'scientific_process_selection_v2',
                    'annotation_ref': library.reference('A01'),
                    'thought_ref': library.reference('P01'),
                    'tools': ['execution.estimate', 'public.hmmer.search']},
                    'evidence_refs': [product], 'constraints': {'target_only': True},
                    'context': {'search_arguments': search, 'estimate_input': estimate}}}
            workflow.configure_execution(independent_execution.make_runtime_binding(
                store, directory, kind='fixed_case'))
            workflow.provider = ScriptedProvider([{'selection': selection, 'report_update': {}}])
            response, index, context, action_schema = asyncio.run(root.source.call(
                {'visible_record_refs': []}, workflow.action_schema(root.source)))
            assert root.source.apply_response(response, index, context, action_schema) is not None
            spec, = workflow.commissions.recover_selected(root.source.episode_id)
            original_request = deepcopy(spec['child']['request'])
            original_manifest = workflow.receipts.manifest(spec['child']['episode_id'])
            original_map = deepcopy(workflow.tools.catalog())
            assert not http.calls and not turns.exists()
            assert store.db.execute('SELECT count(*) FROM provider_jobs').fetchone()[0] == 0
        policy.write_text('raise AssertionError("Use the original saved caller")\n')
        backend = DurableExecutionStore(directory / 'episode-execution')
        backend.commission(spec)
        started = backend.start(spec['handle'])
        async def wait_return():
            await asyncio.wait_for(backend.wait_events({'version': 'event_condition_v1',
                'events': [{'handle': spec['handle'], 'event': 'returned', 'after_cursor': 0}],
                'reconsider_at': None}), 60)  # Isolated test deadline only.
        asyncio.run(wait_return())
        status = backend.status(spec['handle'])
        returned = backend.load_return(spec['handle'], status['return_id'])
        assert started['execution_identity']['pid'] != os.getpid()
        assert returned['outcome'] == 'closed' and returned['failure'] is None, returned
        assert returned['completion']['units_consumed'] == 3
        fact, = returned['form']['timing']
        forecast, = returned['form']['forecasts']
        assert fact['elapsed_seconds'] == forecast['expected_total_seconds'] == http.elapsed
        assert forecast['reported_result_support'] == {'reported_result_count': 1}
        assert [c[0] for c in http.calls] == ['POST', 'GET', 'GET']
        calls = [json.loads(line) for line in turns.read_text().splitlines()]
        assert len(calls) == 3
        assert calls[2]['api_reported_execution_forecasts'] == [forecast]
        with Store(workspace) as store, prepared_case_bindings(store, directory) as (_, options):
            workflow = assemble_workflow(store, builder(store, manifest['configuration']),
                Provider([]), directory, run_id, settings,
                **{k: v for k, v in options.items() if k != 'binding_definitions'})
            assert_final_owners(SimpleNamespace(workflow=workflow, tools=workflow.tools))
            assert workflow.tools.catalog() == original_map
            assert workflow.receipts.manifest(spec['child']['episode_id']) == original_manifest
            child = workflow.journal.row('runtime_episodes', spec['child']['episode_id'])
            assert json.loads(child['request']) == original_request
            assert store.db.execute('SELECT count(*) FROM runtime_observations '
                'WHERE episode_id=?', (spec['child']['episode_id'],)).fetchone()[0] == 3
            assert store.db.execute('SELECT count(*) FROM runtime_observations '
                'WHERE episode_id=?', (spec['parent']['episode_id'],)).fetchone()[0] == 0
            assert store.count('native_execution') == 0
            original = workflow.journal.row('runtime_actions', spec['child']['episode_id'], 0)
            assert json.loads(original['result'])['api_timing_refs'] == [fact['receipt_ref']]

        # The original scientific parent resumes through the ordinary public
        # entrypoint. C3/C4 admission and its observation precede the callbacks.
        integrated = []
        def parent_estimate(context):
            assert context['child_reports'] == [returned['form']]
            assert context['monitoring_information_credit'] == 1
            assert context['current_credit'] == 0
            assert 'api_execution_proposal' not in context
            integrated.append(deepcopy(context['child_reports'][0]))
            return own('execution.estimate', **estimate)
        def parent_history(context):
            forecast, = context['api_reported_execution_forecasts']
            assert forecast['reported_result_support'] == {'reported_result_count': 1}
            assert forecast['expected_total_seconds'] == http.elapsed
            assert context['monitoring_information_credit'] == 1
            return own('episode.history', view='records', decision_indices=[0, 1])
        asyncio.run(run_prepared_case(directory, resume=True,
            provider=ScriptedProvider([parent_estimate, parent_history])))
        assert integrated == [returned['form']]
        assert [c[0] for c in http.calls] == ['POST', 'GET', 'GET']
        with Store(workspace) as store:
            row = store.db.execute('SELECT admission FROM runtime_return_admissions '
                'WHERE parent_episode_id=?', (spec['parent']['episode_id'],)).fetchone()
            admission = json.loads(row[0])
            assert admission['state'] == 'admitted' and admission['report'] == returned['form']
            assert store.db.execute('SELECT count(*) FROM runtime_observations '
                'WHERE episode_id=?', (spec['parent']['episode_id'],)).fetchone()[0] == 3
            receipt = store.db.execute('SELECT receipt_kind FROM runtime_record_receipts '
                'WHERE episode_id=? AND record_ref=?',
                (spec['parent']['episode_id'], fact['receipt_ref'])).fetchone()
            assert receipt[0] == 'child_form'
        for name in ('episode_archive', 'result_archive', 'facts_archive'):
            item = returned[name]
            assert ArchivedRecord(directory / 'archive' / item['file'],
                item['sha256'], item['index_sha256']).load()
        assert backend.start(spec['handle'])['execution_identity'] == started['execution_identity']
        assert backend.load_return(spec['handle'], status['return_id']) == returned
        assert [c[0] for c in http.calls] == ['POST', 'GET', 'GET']
