"""Actual shared-loop native facts and original operation metadata, offline."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json

from gene_annotation_episode.blast_result_views import BLAST_HSP_FACT_SCHEMA
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_blast_service import Client
from test_api_service_integration import assignment
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import child, controller, form
from test_practical_runtime import selected


def test_parent_receives_native_scores_and_scoped_hsp_without_per_tool_task_prose(tmp_path):
    class Responses(Client):
        def blast(self, action, **arguments):
            response = super().blast(action, **arguments)
            if action == 'fetch':
                body = json.loads(response.content)
                hsp = body['BlastOutput2'][0]['report']['results']['search']['hits'][0]['hsps'][0]
                hsp.update(qseq='MACDEFGH', hseq='MACAEFGH', midline='||| ||||')
                response = replace(response, content=json.dumps(body).encode())
            return response

    client = Responses()
    resources = {'blast': {'kind': 'api', 'service': 'ncbi_blast'}}
    factory = ExecutionServiceFactory(resources, {}, 3, 2, .5)
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        request = assignment('blast', 'ncbi_blast', {'subject_ref': target, 'program': 'blastp', 'database': 'swissprot'})
        launch = launch_assignment({'blast': request})
        handoff_form = form('execution_handoff_refs')
        result_form = {'type': 'object', 'additionalProperties': False,
            'properties': {'complete': {'type': 'boolean', 'x-source': 'execution_completed'},
                'matches': {**deepcopy(BLAST_HSP_FACT_SCHEMA), 'x-source': 'execution_blast_hsps'}},
            'required': ['complete', 'matches']}
        monitor_form = {'type': 'object', 'additionalProperties': False,
            'properties': {'ready': {'type': ['boolean', 'null'], 'x-source': 'monitoring_result_available'}},
            'required': ['ready']}

        class Choices:
            root_calls = 0
            handoff = None

            async def complete(self, episode_id, role, instructions, current, schema):
                assert not current.get('feedback'), current.get('feedback')
                execution = current.get('execution_assignment', {})
                if execution.get('version') == 'execution_launch_assignment_v1':
                    return child('launch_api', request, scope, handoff_form)
                if execution.get('version') == 'api_service_assignment_v1':
                    return selected('api.blast.submit')
                if 'monitor_assignment' in current:
                    info = current['monitor_target_description']
                    assert info['called_operation'] == 'api.blast.submit'
                    assert info['resource_kind'] == 'api' and info['operation'] == 'blastp'
                    status = next(row for row in info['extractors'] if row['operation'] == 'api.blast.status')
                    assert status['implementation'] == 'gene_annotation_episode.blast_search.status'
                    assert status['native_return_schema']['properties']['status']['enum'] == ['WAITING', 'READY', 'FAILED', 'UNKNOWN']
                    return selected('progress.observe', {'requested_fields': ['execution_status', 'result_available']})
                if execution.get('version') == 'execution_results_assignment_v1':
                    info = current['execution_target_description']
                    assert info['called_operation'] == 'api.blast.submit'
                    assert info['output_format'] == 'blast_json2'
                    assert 'api.blast.fetch' in info['acquisition_operations']
                    return selected('api.blast.fetch')
                self.root_calls += 1
                if self.root_calls == 1:
                    return child('launch', launch, scope, handoff_form)
                if self.root_calls == 2:
                    self.handoff, = current['child_reports'][-1]['references']
                    return child('monitor', {'version': 'monitor_assignment_v1', 'target_handle': self.handoff,
                        'requested_fields': ['execution_status', 'result_available'], 'known_progress_refs': [],
                        'permitted_committed_record_types': []}, scope, monitor_form)
                assert self.root_calls == 3
                return child('results', {'version': 'execution_results_assignment_v1',
                    'handoff_ref': self.handoff, 'selector': {}}, scope, result_form)

            async def release(self, episode_id):
                pass

        workflow = Workflow(store, ToolRegistry(store, clients=client), Choices(), tmp_path/'run',
            'typed-blast-facts', controller_factory=controller, project_credit=lambda *_: 0,
            episode_service_factory=factory, episode_service_binding=factory.as_record(),
            episode_service_inputs='actual_tool_registry_v1', annotation_child_roles=('launch', 'monitor', 'results'),
            episode_record_receipts=True, initial_known_record_refs=[])
        root = workflow.build('annotation', 'root', 'Obtain native BLAST evidence', scope)

        async def run():
            record = await root.run_async(workflow.context)
            await root.build_result(record)
            return record

        record = asyncio.run(run())
        assert record.units_consumed == 3
        row = store.db.execute("SELECT episode_id,path,request FROM runtime_episodes WHERE run_id=? AND json_extract(path,'$[#-1][0]')='results'",
            (workflow.run_id,)).fetchone()
        returned = json.loads(workflow.journal.row('runtime_forms', row['episode_id'])['form'])
        assert returned['complete'] and len(returned['matches']) == 1
        match = returned['matches'][0]
        assert match['bitscore'] == 31.5 and match['evalue'] == 1e-5 and match['alignment_score'] == 60
        known = tuple(workflow.receipts.known(record.episode_id))
        assert match['hsp_ref'] in known and match['reference_ref'] in known
        read = workflow.tools.execute('result.blast.hsp', {'observation_ref': match['hsp_ref'],
            'column_offset': 2, 'column_limit': 3}, scope=scope, operation_key='later-scoped-read',
            permitted_record_refs=known)
        assert read['status'] == 'completed' and read['result']['alignment']['query'] == 'CDE'
        assert [operation for operation, _ in client.calls] == ['submit', 'status', 'fetch']
        original = json.loads(row['request'])
        context = BindingContext(workflow.run_id, row['episode_id'], 'results',
            tuple(tuple(part) for part in json.loads(row['path'])), scope,
            original['message']['episode_assignment'], original)
        reopened = ExecutionEpisodes(None, store=store, directory=tmp_path/'run', run_id=workflow.run_id,
            resources=resources, initial_information={}, tool_registry=workflow.tools,
            handoff_unit=3, acquired_record_unit=2, log_window_bytes=8192, log_roles=('stdout', 'stderr'))
        reopened.validate_report(context, returned, result_form)
        assert reopened.facts(context, {})['execution_blast_hsps'] == returned['matches']
        assert [operation for operation, _ in client.calls] == ['submit', 'status', 'fetch']
        assert store.count('annotation') == 0
