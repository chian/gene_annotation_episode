"""Small live public requests through actual Workflow launch/monitor/results.

Choices and root/monitor continuation are explicit engineering fixtures. There
are no model calls, scientific conclusions, remote job submissions or changes
to active runs. The supplied fixed-case protein is the input in each fresh store.
"""
import asyncio
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(1, str(REPO/'tests'))

from method_loop.archive import iter_json
from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.episode_monitoring import MonitorEpisodes
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import child, controller, form
from test_practical_runtime import selected


CASES = [
    ('uniprot', 'uniprot', {'operation': 'record', 'accession': 'P0AAW1'},
        'api.uniprot.record', 'api.uniprot.collect'),
    ('bvbrc', 'bvbrc_data', {'collection': 'genome_feature',
        'filters': [{'field': 'gene', 'operator': 'eq', 'value': 'ybhP'}],
        'fields': ['feature_id', 'genome_id', 'genome_name', 'gene', 'product',
                   'accession', 'start', 'end', 'strand', 'pgfam_id'],
        'offset': 0, 'limit': 1}, 'api.bvbrc.query', 'api.bvbrc.result'),
]


def verify(base, resource_id, service, request, launch_tool, result_tool):
    directory = base/resource_id
    directory.mkdir()
    with Store(directory/'state') as store:
        target, = store.create_problem(REPO/'cases/gene_001/target.faa',
            molecule='protein', format='fasta')['subject_refs']
        scope = {'subject_refs': [target]}
        assignment = {'version': 'api_service_assignment_v1', 'resource_id': resource_id,
            'service': service, 'request': request, 'endpoint': 'usable_handoff', 'constraints': {}}
        factory = ExecutionServiceFactory({resource_id: {'kind': 'api', 'service': service}}, {}, 3, 2, .5)
        handoff_form, result_form = form('execution_handoff_refs'), form('execution_result_refs')
        monitor_form = {'type': 'object', 'properties': {'progress': MonitorEpisodes(None)
            .fact_sources('monitor')['monitoring_progress_refs']['report_schema']},
            'required': ['progress'], 'additionalProperties': False}

        class Choices:
            def __init__(self):
                self.root = 0
                self.handoff = None
                self.native_progress = None

            async def complete(self, episode_id, role, instructions, current, schema):
                if current.get('feedback') is not None:
                    raise RuntimeError(json.dumps(current['feedback']))
                execution = current.get('execution_assignment', {})
                if execution.get('version') == 'execution_launch_assignment_v1':
                    return child('launch_api', assignment, scope, handoff_form)
                if execution.get('version') == 'api_service_assignment_v1':
                    return selected(launch_tool)
                if 'monitor_assignment' in current:
                    return selected('progress.observe', {'requested_fields': ['execution_status', 'measurements']})
                if execution.get('version') == 'execution_results_assignment_v1':
                    return selected(result_tool)
                self.root += 1
                if self.root == 1:
                    return child('launch', launch_assignment({resource_id: assignment}), scope, handoff_form)
                if self.root == 2:
                    returned = current['child_reports'][-1]
                    assert returned['completed']
                    self.handoff, = returned['references']
                    return child('monitor', {'version': 'monitor_assignment_v1',
                        'target_handle': self.handoff, 'requested_fields': ['execution_status', 'measurements'],
                        'known_progress_refs': [], 'permitted_committed_record_types': []}, scope, monitor_form)
                progress_ref, = current['child_reports'][-1]['progress']
                self.native_progress = workflow.progress_provider.read_progress(progress_ref, scope)
                assert self.native_progress['result_available']
                return child('results', {'version': 'execution_results_assignment_v1',
                    'handoff_ref': self.handoff, 'selector': {}}, scope, result_form)

            async def release(self, episode_id):
                pass

        choices = Choices()
        workflow = Workflow(store, ToolRegistry(store, clients=PublicClients()), choices, directory/'run',
            'live-public-'+resource_id, controller_factory=controller, project_credit=lambda *_: 0,
            episode_service_factory=factory, episode_service_binding=factory.as_record(),
            episode_service_inputs='actual_tool_registry_v1',
            annotation_child_roles=('launch', 'monitor', 'results'),
            episode_record_receipts=True, initial_known_record_refs=[])
        root = workflow.build('annotation', 'root', 'Verify original public source acquisition', scope)

        async def run():
            record = await root.run_async(workflow.context)
            await root.build_result(record)
            return record

        record = asyncio.run(run())
        archived = json.loads(''.join(iter_json(record.as_record())))
        launch_record = archived['units'][0]['child']
        api_record = launch_record['units'][0]['child']
        results_record = archived['units'][2]['child']
        for completed in (launch_record, api_record, results_record):
            assert completed['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
            assert completed['units_consumed'] == 1
            assert completed['units'][0]['controller_step']['marginal_credit'] > 0
        returned = json.loads(workflow.journal.row('runtime_forms', results_record['episode_id'])['form'])
        assert returned['completed'] and returned['references']
        assert store.count('annotation') == 0
        family = workflow.episode_bindings.for_role('launch_api')
        acquired = family.api_execution.read_result(returned['references'][0], scope)
        source = store.get(acquired['source_ref'])
        original = family.api_execution._read_handoff(choices.handoff, scope)
        assert source['artifact_ref'] == original['snapshot']['content_ref']
        from gene_annotation_episode.execution_contracts import digest
        from gene_annotation_episode.practical_execution_state import _read
        result_key = f'{workflow.run_id}:{results_record["episode_id"]}:0'
        intent_path = family.api_execution._episode_directory(results_record['episode_id'])/'actions'/digest(result_key)/'intent.json'
        assert _read(intent_path)['prepared']['cache_original'] is True
        native = json.loads(store.get_artifact(source['artifact_ref']))
        report = {'service': service, 'input': 'cases/gene_001/target.faa',
            'configured_model': False, 'live_requests': True, 'remote_job_submitted': False,
            'launch_completed': True, 'monitor_state': choices.native_progress['execution_status']['lifecycle_state'],
            'results_completed': True, 'original_response_reused': True,
            'source_provider': source['provider'], 'retrieved_at': source['retrieved_at'],
            'source_bytes': len(store.get_artifact(source['artifact_ref'])),
            'native_accession': native.get('primaryAccession') if isinstance(native, dict) else None,
            'native_rows': len(native) if isinstance(native, list) else None,
            'target_annotation_count': store.count('annotation'), 'practical_future_yield': 0}
        (directory/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report), flush=True)
        return report


if __name__ == '__main__':
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('live_public_001')
    base.mkdir(exist_ok=False)
    reports = [verify(base, *case) for case in CASES]
    (base/'report.json').write_text(json.dumps(reports, indent=2)+'\n')
