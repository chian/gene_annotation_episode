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
            resources = {'here': {'kind': 'local', 'workspace': str(project), 'policy': {'memory_bytes': 128 * 1024 ** 2, 'scratch_bytes': 8 * 1024 ** 2}}}
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
    resources = {'here': {'kind': 'local', 'workspace': str(tmp_path/'local'), 'policy': {'memory_bytes': 128 * 1024 ** 2, 'scratch_bytes': 8 * 1024 ** 2}},
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


def _molecular_binding_no_work(*args, **kwargs):
    raise AssertionError('owner construction must not execute work')


def _guard_molecular_binding_construction(monkeypatch):
    from gene_annotation_episode.acquisition import PublicClients
    monkeypatch.setattr(native, 'prepare_job', _molecular_binding_no_work)
    monkeypatch.setattr(PublicClients, '_http', _molecular_binding_no_work)
    monkeypatch.setattr(ModelConnection, '__init__', _molecular_binding_no_work)
    monkeypatch.setattr(ToolRegistry, 'execute_async', _molecular_binding_no_work)


def _molecular_binding_factory(tmp_path):
    # Declared local metadata only: no installed ORF deployment or executable.
    return ExecutionServiceFactory({'here': {'kind': 'local',
        'workspace': str(tmp_path / 'uncreated-local-workspace'), 'policy': {'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}}}, {}, 3, 2, .5)


def _molecular_binding_workflow(store, tools, factory, directory, run_id):
    # Construction stops before build/run; this provider has no callable port.
    return Workflow(store, tools, object(), directory, run_id, controller_factory=controller,
        project_credit=lambda *args, **kwargs: 0, episode_service_factory=factory,
        episode_service_binding=factory.as_record(), episode_service_inputs='actual_tool_registry_v1',
        annotation_child_roles=('launch', 'monitor', 'results'),
        episode_record_receipts=True, initial_known_record_refs=[])


def _assert_molecular_binding_created_no_work(store, tmp_path):
    assert store.db.execute('SELECT count(*) FROM records').fetchone()[0] == 0
    assert store.db.execute('SELECT count(*) FROM artifacts').fetchone()[0] == 0
    tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in ('runtime_runs', 'runtime_episodes', 'runtime_actions', 'runtime_observations',
            'runtime_model_calls', 'runtime_forms', 'runtime_report_attempts', 'tool_operations',
            'provider_jobs', 'api_execution_episodes', 'api_execution_actions'):
        if table in tables:
            assert store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0, table
    assert not (tmp_path / 'uncreated-local-workspace').exists()


def test_molecular_result_owner_binds_only_actual_composed_services(tmp_path, monkeypatch):
    from gene_annotation_episode.domain import ContractError
    from gene_annotation_episode.molecular_sequence_results import MolecularSequenceResults
    _guard_molecular_binding_construction(monkeypatch)
    with Store(tmp_path / 'state') as store:
        tools = ToolRegistry(store)
        factory = _molecular_binding_factory(tmp_path)
        bound = []
        original_bind = tools.bind_molecular_sequence_results
        def bind(owner):
            bound.append(owner)
            return original_bind(owner)
        monkeypatch.setattr(tools, 'bind_molecular_sequence_results', bind)
        _assert_molecular_binding_created_no_work(store, tmp_path)
        application = factory(store, run_id='actual-owner-A', directory=tmp_path / 'descriptor-only',
            tool_registry=tools)
        assert any(row['binding_id'] == 'execution_episodes'
            for row in application.episode_binding_descriptors)
        assert bound == []
        with pytest.raises(ContractError, match='molecular_sequence_result_owner_unavailable'):
            tools.molecular_sequence_results_for('actual-owner-A')
        _assert_molecular_binding_created_no_work(store, tmp_path)
        workflow = _molecular_binding_workflow(store, tools, factory, tmp_path / 'composed', 'actual-owner-A')
        execution = workflow.episode_bindings.for_role('results')
        owner = execution.molecular_sequence_results
        assert type(owner) is MolecularSequenceResults and bound == [owner]
        assert tools.molecular_sequence_results_for(workflow.run_id) is owner
        assert owner.owner is execution and execution.services is workflow.services
        assert owner.store is execution.store is store and execution.tool_registry is tools
        assert owner.run_id == execution.run_id == workflow.run_id
        _assert_molecular_binding_created_no_work(store, tmp_path)


def test_molecular_result_owner_lookup_keeps_two_actual_runs_separate(tmp_path, monkeypatch):
    _guard_molecular_binding_construction(monkeypatch)
    with Store(tmp_path / 'state') as store:
        tools = ToolRegistry(store)
        factory = _molecular_binding_factory(tmp_path)
        first = _molecular_binding_workflow(store, tools, factory, tmp_path / 'first', 'owner-run-A')
        first_owner = first.episode_bindings.for_role('results').molecular_sequence_results
        assert tools.molecular_sequence_results_for(first.run_id) is first_owner
        second = _molecular_binding_workflow(store, tools, factory, tmp_path / 'second', 'owner-run-B')
        second_owner = second.episode_bindings.for_role('results').molecular_sequence_results
        assert first_owner is not second_owner
        assert tools.molecular_sequence_results_for(first.run_id) is first_owner
        assert tools.molecular_sequence_results_for(second.run_id) is second_owner
        for workflow, owner in ((first, first_owner), (second, second_owner)):
            assert owner.store is store and owner.owner.tool_registry is tools
            assert owner.run_id == workflow.run_id and owner.owner.services is workflow.services
            assert owner.owner.directory.resolve() == workflow.directory.resolve()
        _assert_molecular_binding_created_no_work(store, tmp_path)


def test_molecular_result_owner_construction_preserves_legacy_tools_without_setter(tmp_path, monkeypatch):
    from test_scientific_process_runtime import Tools
    _guard_molecular_binding_construction(monkeypatch)
    with Store(tmp_path / 'state') as store:
        tools = Tools(store)
        assert not hasattr(tools, 'bind_molecular_sequence_results')
        monkeypatch.setattr(tools, 'execute', _molecular_binding_no_work)
        factory = _molecular_binding_factory(tmp_path)
        application = factory(store, run_id='legacy-owner', directory=tmp_path / 'descriptor-only',
            tool_registry=tools)
        assert any(row['binding_id'] == 'execution_episodes'
            for row in application.episode_binding_descriptors)
        workflow = _molecular_binding_workflow(store, tools, factory, tmp_path / 'legacy-run', 'legacy-owner')
        execution = workflow.episode_bindings.for_role('results')
        assert execution.services is workflow.services and execution.tool_registry is tools
        assert execution.molecular_sequence_results.owner is execution
        assert tools.calls == []
        _assert_molecular_binding_created_no_work(store, tmp_path)


from tests.test_molecular_sequence_ordinary import selected_call


def test_configured_ordinary_orf_reconstructs_actual_factory_and_services_without_work(
        tmp_path, monkeypatch, selected_call):
    """Real composition with engineered deployment metadata, not installed native availability."""
    from gene_annotation_episode.domain import ContractError
    from gene_annotation_episode.molecular_sequence_results import MolecularSequenceResults
    from gene_annotation_episode.molecular_sequence_tools import BINDING_VERSION, ORF_TOOL
    from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
    call, calls = selected_call
    selected = call['selected']
    _guard_molecular_binding_construction(monkeypatch)
    monkeypatch.setattr(MolecularSequenceResults, 'capture_ordinary_orf', _molecular_binding_no_work)
    monkeypatch.setattr(MolecularSequenceResults, 'publish_ordinary_orf', _molecular_binding_no_work)
    monkeypatch.setattr('gene_annotation_episode.molecular_sequence_ordinary.prepare_ordinary_orf_attempt',
        _molecular_binding_no_work)
    binding = {'version': BINDING_VERSION, 'operation': ORF_TOOL,
        'deployment': deepcopy(selected['deployment']), 'software': deepcopy(selected['software'])}
    resources = {selected['resource_id']: {'kind': 'local', 'workspace': selected['workspace'],
        'policy': call['policy'].to_dict(), 'native_molecular_sequence': [binding]}}
    environments = [{'operation': ORF_TOOL, 'resource_id': selected['resource_id'],
        'binding_ordinal_0based': 0, 'environment': deepcopy(selected['environment'])}]
    local_resource = resources[selected['resource_id']]
    assert LocalPracticalOperations(local_resource).configuration == local_resource
    invalid_binding = deepcopy(local_resource)
    invalid_binding['native_molecular_sequence'][0]['operation'] = 'unsupported_sequence_operation'
    with pytest.raises(ValueError, match='ordinary_orf_binding_operation_invalid'):
        LocalPracticalOperations(invalid_binding)
    with pytest.raises(ValueError, match='explicit_local_practical_configuration_required'):
        LocalPracticalOperations({**local_resource, 'native_unsupported_sequence': []})
    factory = ExecutionServiceFactory(resources, {}, 3, 2, .5,
        molecular_sequence_environments=environments)
    recorded = factory.as_record()
    assert recorded['molecular_sequence_environments'] == environments
    restored = ExecutionServiceFactory.from_record(recorded)
    assert restored.as_record() == recorded
    resources[selected['resource_id']]['native_molecular_sequence'][0]['software']['python_version'] = 'changed caller metadata'
    environments[0]['environment']['changed_caller_metadata'] = True
    assert factory.as_record() == restored.as_record() == recorded
    run_id = 'configured-ordinary-orf-owner'
    with Store(tmp_path / 'state') as store:
        descriptor_tools = ToolRegistry(store, job_limits=call['policy'].to_dict())
        assert ORF_TOOL not in descriptor_tools.catalog()
        application = restored(store, run_id=run_id, directory=tmp_path / 'descriptor-only',
            tool_registry=descriptor_tools)
        descriptor, = [row for row in application.episode_binding_descriptors
            if row['binding_id'] == 'execution_episodes']
        assert descriptor['configuration']['resources'] == recorded['resources']
        descriptor_catalog = descriptor_tools.catalog()[ORF_TOOL]
        assert descriptor_catalog['invocation_route'] == {'kind': 'direct'}
        with pytest.raises(ContractError, match='molecular_sequence_result_owner_unavailable'):
            descriptor_tools.molecular_sequence_results_for(run_id)
        _assert_molecular_binding_created_no_work(store, tmp_path)
        # A fresh registry has not been manually configured. The reconstructed
        # actual factory must configure it before rebuilding the execution owner.
        tools = ToolRegistry(store, job_limits=call['policy'].to_dict())
        assert ORF_TOOL not in tools.catalog()
        workflow = _molecular_binding_workflow(store, tools, restored, tmp_path / 'composed', run_id)
        execution = workflow.episode_bindings.for_role('results')
        owner = execution.molecular_sequence_results
        assert type(owner) is MolecularSequenceResults
        assert tools.molecular_sequence_results_for(run_id) is owner
        assert owner.owner is execution and execution.services is workflow.services
        assert owner.store is store and execution.tool_registry is tools
        assert owner.run_id == execution.run_id == workflow.run_id == run_id
        assert execution.resources == recorded['resources']
        assert workflow.episode_application_services_binding['definition'] == recorded
        assert workflow.episode_application_services_binding['inputs'] == 'actual_tool_registry_v1'
        assert tools.catalog()[ORF_TOOL] == descriptor_catalog
        information, = [row for row in workflow.services.tool_information_catalog(None)
            if row['name'] == ORF_TOOL]
        assert information['invocation_route'] == {'kind': 'direct'}
        assert information['input_schema'] == descriptor_catalog['input_schema']
        assert restored.as_record()['molecular_sequence_environments'] == recorded['molecular_sequence_environments']
        assert calls == [] and list(Path(selected['workspace']).iterdir()) == []
        _assert_molecular_binding_created_no_work(store, tmp_path)


@pytest.mark.parametrize('invalid', [0, 1, 'true', None])
def test_saved_orf_factory_requires_an_explicit_boolean(tmp_path, invalid):
    recorded = _molecular_binding_factory(tmp_path).as_record()
    assert 'molecular_sequence_saved_modes' not in recorded
    assert ExecutionServiceFactory.from_record(recorded).as_record() == recorded
    with pytest.raises(ValueError, match='explicit_molecular_sequence_saved_modes_boolean_required'):
        ExecutionServiceFactory.from_record({**recorded, 'molecular_sequence_saved_modes': invalid})


def test_saved_only_orf_factory_reconstructs_owner_without_native_deployment(tmp_path, monkeypatch):
    from gene_annotation_episode.domain import ContractError
    from gene_annotation_episode.molecular_sequence_results import MolecularSequenceResults
    from gene_annotation_episode.molecular_sequence_tools import ORF_TOOL
    _guard_molecular_binding_construction(monkeypatch)
    recorded = {**_molecular_binding_factory(tmp_path).as_record(),
        'molecular_sequence_saved_modes': True}
    factory = ExecutionServiceFactory.from_record(recorded)
    assert factory.as_record() == recorded
    with pytest.raises(ValueError, match='actual_molecular_sequence_tool_registry_required'):
        factory.configure_tool_registry(object())
    with Store(tmp_path / 'state') as store:
        tools = ToolRegistry(store)
        assert ORF_TOOL not in tools.catalog()
        workflow = _molecular_binding_workflow(store, tools, factory, tmp_path / 'composed', 'saved-only-orf')
        owner = workflow.episode_bindings.for_role('results').molecular_sequence_results
        assert type(owner) is MolecularSequenceResults
        assert tools.molecular_sequence_results_for(workflow.run_id) is owner
        assert owner.owner.services is workflow.services
        assert workflow.episode_application_services_binding['definition'] == recorded
        entry = tools.catalog()[ORF_TOOL]
        assert entry['invocation_route'] == {'kind': 'direct'}
        assert {branch['properties']['mode']['const'] for branch in entry['input_schema']['anyOf']} == {
            'read_stored', 'calculate_saved'}
        assert all('subject_ref' not in branch['properties'] for branch in entry['input_schema']['anyOf'])
        assert 'native_molecular_sequence_tools' not in tools.resource_binding()
        assert tools.resource_binding()['molecular_sequence_saved_modes'] is True
        information, = [row for row in workflow.services.tool_information_catalog(None)
            if row['name'] == ORF_TOOL]
        assert information['input_schema'] == entry['input_schema']
        factory.configure_tool_registry(tools)
        assert tools.catalog()[ORF_TOOL] == entry
        with pytest.raises(ContractError, match='molecular_sequence_saved_modes_changed'):
            tools.configure_molecular_sequence_resources(recorded['resources'], [])
        assert tools.catalog()[ORF_TOOL] == entry
        _assert_molecular_binding_created_no_work(store, tmp_path)


@pytest.mark.parametrize('invalid', [0, 1, 'true', None])
def test_saved_homer_factory_requires_an_explicit_boolean(tmp_path, invalid):
    recorded = _molecular_binding_factory(tmp_path).as_record()
    assert 'homer_environments' not in recorded and 'homer_saved_modes' not in recorded
    assert ExecutionServiceFactory.from_record(recorded).as_record() == recorded
    with pytest.raises(ValueError, match='explicit_homer_saved_modes_boolean_required'):
        ExecutionServiceFactory.from_record({**recorded, 'homer_saved_modes': invalid})


def test_saved_only_homer_factory_reconstructs_actual_owner_without_work(tmp_path, monkeypatch):
    from gene_annotation_episode.domain import ContractError
    _guard_molecular_binding_construction(monkeypatch)
    tool = 'find_enriched_motifs_with_homer'
    recorded = {**_molecular_binding_factory(tmp_path).as_record(), 'homer_saved_modes': True}
    factory = ExecutionServiceFactory.from_record(recorded)
    assert factory.as_record() == recorded
    with pytest.raises(ValueError, match='actual_homer_tool_registry_required'):
        factory.configure_tool_registry(object())
    with Store(tmp_path / 'state') as store:
        tools = ToolRegistry(store)
        assert tool not in tools.catalog()
        factory(store, run_id='homer-owner', directory=tmp_path / 'descriptor-only',
            tool_registry=tools)
        with pytest.raises(ContractError, match='execution_owner_unavailable'):
            tools.execution_owner_for('homer-owner')
        workflow = _molecular_binding_workflow(store, tools, factory,
            tmp_path / 'composed', 'homer-owner')
        owner = workflow.episode_bindings.for_role('results')
        assert tools.execution_owner_for(workflow.run_id) is owner
        assert owner.services is workflow.services and owner.store is store
        assert workflow.episode_application_services_binding['definition'] == recorded
        entry = tools.catalog()[tool]
        assert entry['invocation_route'] == {'kind': 'direct'}
        assert {branch['properties']['mode']['const'] for branch in entry['input_schema']['anyOf']} == {
            'read_stored', 'calculate_saved'}
        information, = [row for row in workflow.services.tool_information_catalog(None)
            if row['name'] == tool]
        assert information['input_schema'] == entry['input_schema']
        assert tools.resource_binding()['homer_tools']['saved_modes'] is True
        factory.configure_tool_registry(tools)
        assert tools.catalog()[tool] == entry
        with pytest.raises(ContractError, match='homer_configuration_changed'):
            tools.configure_homer_resources(recorded['resources'], [])
        assert tools.catalog()[tool] == entry
        second = _molecular_binding_workflow(store, tools, factory,
            tmp_path / 'second', 'homer-owner-B')
        second_owner = second.episode_bindings.for_role('results')
        assert second_owner is not owner
        assert tools.execution_owner_for('homer-owner-B') is second_owner
        assert tools.execution_owner_for('homer-owner') is owner
        with pytest.raises(ContractError, match='execution_owner_unavailable'):
            tools.execution_owner_for('unbound-run')
        original_directory = owner.directory
        owner.directory = tmp_path / 'changed-owner'
        try:
            with pytest.raises(ContractError, match='execution_owner_changed'):
                tools.execution_owner_for('homer-owner')
        finally:
            owner.directory = original_directory
        assert tools.execution_owner_for('homer-owner') is owner
        _assert_molecular_binding_created_no_work(store, tmp_path)
