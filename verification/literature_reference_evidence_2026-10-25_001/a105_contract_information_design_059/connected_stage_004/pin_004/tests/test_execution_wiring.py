"""Connected shared-loop wiring with real local work and controlled HTTP.

Choices and root/monitor continuation are explicit fixtures. Resource/family
completion uses the actual validated endpoint estimator. No model or remote job
runs here; no fixture cadence or action limit is installed in production.
"""
import asyncio
import base64
from copy import deepcopy
import json
import sys
from pathlib import Path

import pytest
from method_loop.archive import iter_json

from gene_annotation_episode import independent_execution as reconstruction
from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.episode_reports import report_sources
from gene_annotation_episode.episode_monitoring import MonitorEpisodes
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.runtime import Workflow, assemble_workflow, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from gene_annotation_episode.tools import ToolRegistry
from test_execution_episodes_family import launch_assignment, native_assignment
from test_practical_reconstruction import BeforeModel
from test_practical_runtime import selected
from test_public_search import Client


def form(reference_field):
    return {'type': 'object', 'properties': {
        'completed': {'type': 'boolean', 'x-source': 'execution_completed'},
        'references': {'type': 'array', 'uniqueItems': True, 'items': {
            'type': 'string', 'format': 'reference',
            'x-reference-namespace': ('execution_handoff' if reference_field == 'execution_handoff_refs'
                                      else 'execution_result')}, 'x-source': reference_field},
        'yield': report_sources()['episode_yield']['report_schema']},
        'required': ['completed', 'references', 'yield'], 'additionalProperties': False}


def child(role, assignment, scope, schema):
    return {'selection': {'kind': 'episode_child', 'role': role, 'goal': 'Run this exact fixture commission',
        'scope': scope, 'purpose': 'Return the requested original recorded information',
        'assignment': assignment, 'schema_json': json.dumps(schema), 'initial_report_json': '{}'},
        'report_update': {}}


def controller(path, initial):
    role = path[-1][0]
    def estimate(history, parameters, contexts):
        count = 3 if role == 'annotation' else 1
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= count else 1),
            parameters, {'fixture': 'root_and_monitor_continuation_only'})
    return YieldController(str(path), initial, 0, YieldParameters(100, 50),
        estimate_with_context=estimate if role in {'annotation', 'monitor'} else None)


@pytest.mark.parametrize('resource_kind', ['local', 'api'])
def test_shared_loop_launch_resource_monitor_results_and_exact_zero(tmp_path, resource_kind):
    project = tmp_path/'project'
    project.mkdir()
    output = project/'requested.bin'
    invocation = project/'invocations'
    client = Client()
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        if resource_kind == 'local':
            resources = {'here': {'kind': 'local', 'workspace': str(project), 'policy': {
                'memory_bytes': 128*1024**2, 'scratch_bytes': 8*1024**2, 'wall_seconds': None}}}
            assignment = native_assignment(project, argv=[sys.executable, '-c',
                'from pathlib import Path; Path('+repr(str(invocation))+').write_text("once"); '
                'Path('+repr(str(output))+').write_bytes(bytes([0,255,65,10]))'])
            resource_id, resource_role = 'here', 'launch_local'
        else:
            resources = {'ebi': {'kind': 'hmmer_api'}}
            assignment = {'version': 'api_execution_assignment_v1', 'resource_id': 'ebi',
                'service': 'ebi_hmmer', 'subject_ref': target, 'algorithm': 'phmmer',
                'database': 'swissprot', 'parameters': {}, 'page_size': 1,
                'endpoint': 'usable_handoff', 'constraints': {}}
            resource_id, resource_role = 'ebi', 'launch_api'
        factory = ExecutionServiceFactory(resources, {}, 3, 2, .5, log_window_bytes=128)
        launch = launch_assignment({resource_id: assignment})
        handoff_form, result_form = form('execution_handoff_refs'), form('execution_result_refs')
        monitor_form = {'type': 'object', 'properties': {
            'progress': MonitorEpisodes(None).fact_sources('monitor')['monitoring_progress_refs']['report_schema']},
            'required': ['progress'], 'additionalProperties': False}

        class Choices:
            def __init__(self):
                self.root_count = self.api_count = 0
                self.contexts = []
                self.handoff = None
            async def complete(self, episode_id, role, instructions, context, schema):
                self.contexts.append((episode_id, deepcopy(context)))
                assert context.get('feedback') is None, context.get('feedback')
                if 'practical_assignment' in context:
                    assert context['practical_assignment'] == assignment
                    return selected('practical.job.start')
                execution = context.get('execution_assignment', {})
                if execution.get('version') == 'execution_launch_assignment_v1':
                    assert context['execution_resource_capabilities'][0]['resource_id'] == resource_id
                    return child(resource_role, assignment, scope, handoff_form)
                if execution.get('version') == 'api_execution_assignment_v1':
                    names = ['api.hmmer.prepare', 'api.hmmer.submit', 'api.hmmer.check_handoff']
                    name = names[self.api_count]
                    self.api_count += 1
                    return selected(name)
                if 'monitor_assignment' in context:
                    return selected('progress.observe', {'requested_fields': ['execution_status', 'measurements', 'log_windows']})
                if execution.get('version') == 'execution_results_assignment_v1':
                    return selected('execution.results.collect' if resource_kind == 'local' else 'api.hmmer.result')
                self.root_count += 1
                if self.root_count == 1:
                    return child('launch', launch, scope, handoff_form)
                if self.root_count == 2:
                    received = context['child_reports'][-1]
                    assert received['completed'] is True
                    assert received['yield']['expected_next_gain'] == NumericBand.exact(0).as_record()
                    self.handoff, = received['references']
                    target_info = workflow.progress_provider.job_provider.targets.read_target(self.handoff, scope)
                    if resource_kind == 'local':
                        # Fixture synchronization waits for the actual tiny job;
                        # this is not a production polling or completion rule.
                        assert (await asyncio.to_thread(native.wait_job,
                            native.NativeJobHandle(Path(target_info['execution_id'])))).returncode == 0
                    return child('monitor', {'version': 'monitor_assignment_v1',
                        'target_handle': self.handoff, 'requested_fields': ['execution_status', 'measurements', 'log_windows'],
                        'known_progress_refs': [], 'permitted_committed_record_types': []}, scope, monitor_form)
                assert self.root_count == 3
                received = context['child_reports'][-1]
                assert received['progress']
                progress = workflow.progress_provider.read_progress(received['progress'][0], scope)
                assert progress['execution_status']['version'] == 'resource_execution_status_v1'
                assert progress['execution_status']['lifecycle_state'] == 'returned'
                return child('results', {'version': 'execution_results_assignment_v1',
                    'handoff_ref': self.handoff,
                    'selector': {'paths': [str(output)]} if resource_kind == 'local' else {'page': 1}},
                    scope, result_form)
            async def release(self, episode_id):
                pass

        provider = Choices()
        workflow = Workflow(store, ToolRegistry(store, clients=client), provider, tmp_path/'run',
            'connected-execution-'+resource_kind, controller_factory=controller,
            project_credit=lambda *_: 0, episode_service_factory=factory,
            episode_service_binding=factory.as_record(), episode_service_inputs='actual_tool_registry_v1',
            annotation_child_roles=('launch', 'monitor', 'results'),
            episode_record_receipts=True, initial_known_record_refs=[])
        episode = workflow.build('annotation', 'root', 'Acquire the requested fixture result', scope)
        async def run():
            record = await episode.run_async(workflow.context)
            await episode.build_result(record)
            return record
        record = asyncio.run(run())
        assert record.units_consumed == 3
        assert set(workflow.episode_bindings.roles) == {'launch', 'launch_api', 'launch_local', 'launch_hpc', 'results', 'monitor'}
        # Closed descendants have released their live recursive records; read
        # the verified disk archive rather than expecting a retained live tree.
        archived = json.loads(''.join(iter_json(record.as_record())))
        launch_record = archived['units'][0]['child']
        resource_record = launch_record['units'][0]['child']
        results_record = archived['units'][2]['child']
        for completed in (launch_record, resource_record, results_record):
            assert completed['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
            assert completed['units'][-1]['controller_step']['marginal_credit'] > 0
        assert launch_record['units_consumed'] == 1
        assert resource_record['units_consumed'] == (1 if resource_kind == 'local' else 3)
        assert results_record['units_consumed'] == 1
        row = workflow.journal.row('runtime_forms', results_record['episode_id'])
        returned = json.loads(row['form'])
        assert returned['completed'] and returned['references']
        if resource_kind == 'local':
            assert invocation.read_text() == 'once'
            source = store.get(returned['references'][0])
            body = json.loads(store.get_artifact(source['artifact_ref']))
            assert base64.b64decode(body['windows'][0]['bytes_base64']) == bytes([0,255,65,10])
        else:
            assert client.submissions == 1 and client.status_calls == 2
            assert store.count('observation') > 0


def test_all_three_resources_reconstruct_before_model_entry_without_work(tmp_path, monkeypatch):
    resources = {'here': {'kind': 'local', 'workspace': str(tmp_path/'local'), 'policy': {
            'memory_bytes': 128*1024**2, 'scratch_bytes': 8*1024**2, 'wall_seconds': None}},
        'aurora': {'kind': 'pbs_ssh', 'workspace': '/lus/flare/projects/BioReason-Aurora-Test',
            'ssh_argv': ['unexecuted-ssh', 'user-supplied-host'], 'account': 'EpiCalib',
            'python_executable': '/usr/bin/python3'}, 'ebi': {'kind': 'hmmer_api'}}
    factory = ExecutionServiceFactory(resources, {}, 3, 2, .5)
    expected = factory.as_record()
    resources['here']['workspace'] = '/changed'
    assert factory.as_record() == expected
    directory, workspace = tmp_path/'run', tmp_path/'state'
    async def before_model(connection):
        with Store(workspace) as reopened:
            settings = json.loads(reopened.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])
            options = reconstruction._standard_bindings(reopened, directory, settings)
            reconstruction._check_bindings(options, settings)
            restored = assemble_workflow(reopened, build_tools(reopened), object(), directory,
                json.loads((directory/'run.json').read_text())['run_id'], settings,
                **{key: value for key, value in options.items() if key != 'binding_definitions'})
            assert restored.episode_bindings.as_record() == settings['episode_bindings']
            assert options['episode_service_factory'].as_record() == expected
            assert options['episode_service_inputs'] == 'actual_tool_registry_v1'
            assert len(restored.resource_capabilities) == 3
            assert not (tmp_path/'local').exists()
            for table in ('runtime_episodes', 'runtime_actions', 'provider_jobs'):
                assert reopened.db.execute('SELECT count(*) FROM '+table).fetchone()[0] == 0
        raise BeforeModel
    monkeypatch.setattr(ModelConnection, '__aenter__', before_model)
    with Store(workspace) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        with pytest.raises(BeforeModel):
            asyncio.run(run_workflow(store, build_tools(store), run_dir=directory,
                episode_service_factory=factory, episode_service_binding=factory.as_record(),
                episode_service_inputs='actual_tool_registry_v1', annotation_child_roles=('launch', 'monitor', 'results')))
