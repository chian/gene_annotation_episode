"""Connected HPC subtree using controlled transport and a four-byte fixture job.

The production PBS worker and receipt owners execute against fake scheduler
commands. No model, SSH connection, cluster allocation or scientific algorithm
runs in this test; it does not establish a live HPC deployment.
"""
import asyncio
import base64
import json
import sys

from gene_annotation_episode.episode_monitoring import MonitorEpisodes
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_execution_episodes_family import launch_assignment, native_assignment
from test_execution_wiring import child, controller, form
from test_practical_pbs_operations import remote  # noqa: F401 - shared pytest fixture
from test_practical_runtime import selected


def test_pbs_subtree_delivers_original_job_bytes_once(tmp_path, monkeypatch, remote):
    monkeypatch.setenv('FAKE_PBS_EXECUTE', '1')
    output = remote.workspace / 'requested.bin'
    marker = remote.workspace / 'invocations'
    resource_id = 'configured-pbs'
    allocation = {'account': remote.configuration['account'], 'queue': 'fixture',
        'resources': ['select=1:ncpus=1:mem=128mb', 'walltime=00:01:00']}
    assignment = native_assignment(remote.workspace, resource_id, kind='hpc', argv=[
        sys.executable, '-c',
        'from pathlib import Path; p=Path(' + repr(str(marker)) + '); '
        'p.write_text(str(int(p.read_text())+1) if p.exists() else "1"); '
        'Path(' + repr(str(output)) + ').write_bytes(bytes([0,255,65,10]))'])
    assignment['constraints'] = allocation
    launch = launch_assignment({resource_id: assignment}, constraints=allocation)
    handoff_form, result_form = form('execution_handoff_refs'), form('execution_result_refs')
    monitor_form = {'type': 'object', 'properties': {
        'progress': MonitorEpisodes(None).fact_sources('monitor')['monitoring_progress_refs']['report_schema']},
        'required': ['progress'], 'additionalProperties': False}
    factory = ExecutionServiceFactory({resource_id: remote.configuration}, {}, 3, 2, .5,
        log_window_bytes=128)

    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}

        class Choices:
            def __init__(self):
                self.root_count = 0
                self.handoff = None
                self.target = None

            async def complete(self, episode_id, role, instructions, context, schema):
                assert context.get('feedback') is None, context.get('feedback')
                if 'practical_assignment' in context:
                    assert context['practical_assignment'] == assignment
                    return selected('practical.job.start', {
                        'queue': allocation['queue'], 'resources': allocation['resources']})
                execution = context.get('execution_assignment', {})
                if execution.get('version') == 'execution_launch_assignment_v1':
                    return child('launch_hpc', assignment, scope, handoff_form)
                if 'monitor_assignment' in context:
                    return selected('progress.observe', {
                        'requested_fields': ['execution_status', 'measurements', 'log_windows']})
                if execution.get('version') == 'execution_results_assignment_v1':
                    assert execution['handoff_ref'] == self.handoff
                    return selected('execution.results.collect')
                self.root_count += 1
                if self.root_count == 1:
                    return child('launch', launch, scope, handoff_form)
                if self.root_count == 2:
                    received = context['child_reports'][-1]
                    assert received['completed'] is True
                    self.handoff, = received['references']
                    self.target = workflow.progress_provider.job_provider.targets.read_target(self.handoff, scope)
                    assert self.target['execution_id'] == '12345.aurora'
                    assert self.target['resource_id'] == resource_id
                    return child('monitor', {'version': 'monitor_assignment_v1',
                        'target_handle': self.handoff,
                        'requested_fields': ['execution_status', 'measurements', 'log_windows'],
                        'known_progress_refs': [], 'permitted_committed_record_types': []}, scope, monitor_form)
                assert self.root_count == 3
                progress, = context['child_reports'][-1]['progress']
                observed = workflow.progress_provider.read_progress(progress, scope)
                assert observed['execution_status']['lifecycle_state'] == 'returned'
                return child('results', {'version': 'execution_results_assignment_v1',
                    'handoff_ref': self.handoff, 'selector': {'paths': [str(output)]}}, scope, result_form)

            async def release(self, episode_id):
                pass

        provider = Choices()
        workflow = Workflow(store, ToolRegistry(store), provider, tmp_path / 'workflow',
            'controlled-hpc-subtree', controller_factory=controller, project_credit=lambda *_: 0,
            episode_service_factory=factory, episode_service_binding=factory.as_record(),
            episode_service_inputs='actual_tool_registry_v1',
            annotation_child_roles=('launch', 'monitor', 'results'),
            episode_record_receipts=True, initial_known_record_refs=[])
        episode = workflow.build('annotation', 'root', 'Return the original HPC fixture bytes', scope)

        async def run():
            record = await episode.run_async(workflow.context)
            await episode.build_result(record)
            return record

        record = asyncio.run(run())
        assert record.units_consumed == provider.root_count == 3
        returned = json.loads(store.db.execute(
            "SELECT form FROM runtime_forms WHERE json_extract(form,'$.references[0]') IS NOT NULL "
            "AND json_extract(form,'$.completed')=1 ORDER BY rowid DESC LIMIT 1").fetchone()[0])
        source = store.get(returned['references'][0])
        assert source['id'] in workflow.binding_context(episode.source).received_record_refs
        body = json.loads(store.get_artifact(source['artifact_ref']))
        assert base64.b64decode(body['windows'][0]['bytes_base64']) == bytes([0,255,65,10])
        assert marker.read_text() == '1'
        assert (remote.database / 'submissions').read_text() == '1'
        qsub = json.loads((remote.database / 'qsub-argv.json').read_text())
        assert qsub[qsub.index('-A') + 1] == allocation['account']
        assert qsub[qsub.index('-q') + 1] == allocation['queue']
        assert [qsub[i + 1] for i, arg in enumerate(qsub) if arg == '-l'] == allocation['resources']
