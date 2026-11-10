"""The actual saved C1 factory reconstructs and executes one practical child.

Only model transport is a scripted fixture. This exercises the worker factory
in process, not a forked worker transport or a configured-model investigation.
"""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode import independent_execution as reconstruction
from gene_annotation_episode.episode_reports import report_sources
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.practical_execution_records import digest
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.practical_service_setup import PracticalServiceFactory
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.runtime import TypedReportContract, assemble_workflow, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from test_practical_reconstruction import BeforeModel
from test_practical_runtime import Choices, make_assignment, selected


@pytest.mark.parametrize('wired_family', [False, True])
def test_saved_c1_factory_executes_original_practical_commission_once(tmp_path, monkeypatch, wired_family):
    spec = make_assignment(tmp_path / 'project', reuse=True)
    workspace, directory = tmp_path / 'state', tmp_path / 'run'
    resources = {'local': {'kind': 'local', 'workspace': str(spec.workspace),
        'policy': {'memory_bytes': 128 * 1024 ** 2, 'scratch_bytes': 16 * 1024 ** 2}}}
    factory = (ExecutionServiceFactory(resources, {}, 3, 2, .5)
               if wired_family else PracticalServiceFactory(resources, {}))
    service_inputs = {'episode_service_inputs': 'actual_tool_registry_v1'} if wired_family else {}
    if wired_family:
        spec.assignment['resource_id'] = 'local'
    async def before_provider_entry(connection):
        raise BeforeModel
    with Store(workspace) as store:
        store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')
        with monkeypatch.context() as patched:
            patched.setattr(ModelConnection, '__aenter__', before_provider_entry)
            with pytest.raises(BeforeModel):
                asyncio.run(run_workflow(store, build_tools(store), run_dir=directory,
                    controller_settings={'cost': 0, 'window_size': 100, 'subsample_size': 50},
                    annotation_child_roles=('launch',) if wired_family else ('launch_local',),
                    episode_service_factory=factory, episode_service_binding=factory.as_record(),
                    **service_inputs))
        manifest = json.loads((directory / 'run.json').read_text())
        run_id = manifest['run_id']
        settings = json.loads(store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?',
            (run_id,)).fetchone()[0])
        runtime_binding = json.loads((directory / 'episode-execution-binding.json').read_text())
        assert runtime_binding == reconstruction.make_runtime_binding(store, directory)
        assert runtime_binding['implementation_sha256'] == reconstruction.implementation_sha256()
        form = {'type': 'object', 'properties': {
            'completed': {'type': 'boolean', 'x-source': 'practical_completed'},
            'receipts': {'type': 'array', 'uniqueItems': True, 'items': {
                'type': 'string', 'format': 'reference', 'x-reference-namespace': 'practical_receipt'},
                'x-source': 'practical_receipt_refs'},
            'yield': report_sources()['episode_yield']['report_schema']},
            'required': ['completed', 'receipts', 'yield'], 'additionalProperties': False}
        scope = store.validate_scope({'subject_refs': store.problem()['subject_refs']})
        selection = {'kind': 'episode_child', 'role': 'launch_local',
            'goal': 'Execute the original requested local job and validate its outputs',
            'scope': scope, 'purpose': 'Return the exact endpoint and its immutable execution receipts',
            'assignment': spec.assignment, 'schema_json': json.dumps(form), 'initial_report_json': '{}'}
        class ParentCommissionChoice:
            async def complete(self, episode_id, role, instructions, context, schema):
                return {'selection': deepcopy(selection), 'report_update': {}}
        options = reconstruction._standard_bindings(store, directory, settings)
        reconstruction._check_bindings(options, settings)
        workflow = assemble_workflow(store, build_tools(store), ParentCommissionChoice(), directory,
            run_id, settings, **{key: value for key, value in options.items()
                                if key != 'binding_definitions'})
        workflow.configure_execution(runtime_binding)
        parent = workflow.build('annotation', 'root', settings['goal'], scope)
        if wired_family:
            parent = workflow.build('launch', 'selected-launch', settings['goal'], scope,
                parent=parent.goal, parent_path=parent.source.path,
                contract=TypedReportContract('Return verified original launch completion',
                    {'type': 'object', 'properties': {
                        'completed': {'type': 'boolean', 'x-source': 'execution_completed'}},
                     'required': ['completed'], 'additionalProperties': False}, lambda *_: True),
                episode_assignment={'version': 'execution_launch_assignment_v1',
                    'requests': {'local': spec.assignment}, 'immutable_input_versions': [], 'constraints': {}})
        # Record the actual decision and validated commission using the normal
        # source boundary; do not run the scientific parent's episode loop.
        response, index, original_context, schema = asyncio.run(parent.source.call({
            'goal': parent.goal.as_record(), 'scope': scope,
            'visible_record_refs': list(scope['subject_refs'])}, workflow.action_schema(parent.source)))
        unit = parent.source.apply_response(response, index, original_context, schema)
        assert unit is not None
        commission, = workflow.commissions.recover_selected(parent.source.episode_id)
        assert commission['child']['request']['message']['episode_assignment'] == spec.assignment
        assert commission['runtime_binding'] == runtime_binding
        assert commission['child']['request']['report_contract']['measurements']['schema'] == form
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        # Publish the selected C2 identity without starting a worker transport.
        # The actual C1 factory body below is the subject of this test.
        workflow.execution_backend.commission(commission)
        original_commission = deepcopy(commission)

    connections = []
    class FixtureModelConnection(Choices):
        def __init__(self, models, audit_directory, run_directory, **kwargs):
            super().__init__([selected('practical.job.start')], collect_after=True)
            self.models = deepcopy(models)
            self.entered = False
            self.exited = False
            connections.append(self)
        async def __aenter__(self):
            self.entered = True
            return self
        async def __aexit__(self, *args):
            self.exited = True

    monkeypatch.setattr('gene_annotation_episode.providers.ModelConnection', FixtureModelConnection)
    async def execute_worker_factory():
        async with reconstruction.open_commission(commission) as opened:
            episode, context = opened['episode'], opened['context']
            restored = episode.source.workflow
            assert restored.store.path == workspace.resolve()
            assert episode.request.as_record() == original_commission['child']['request']
            assert context.path == tuple(tuple(item) for item in original_commission['parent']['path'])
            assert restored.execution_binding == runtime_binding
            assert restored.execution_handle == original_commission['handle']
            record = await episode.run_async(context)
            result = await episode.build_result(record)
            packed = opened['pack_result'](record, result)
            state = restored.specialist(episode.source).state(restored.binding_context(episode.source))
            receipts = state.receipts()
            proof = state.completion_proof()
            assert state.verify_completion(proof) is True
            assert proof['assignment_sha256'] == digest(spec.assignment)
            assert proof['receipt_sha256'] == digest(receipts[-1])
            assert record.unit_records[-1].controller_step.marginal_credit == 4
            assert record.controller_state.estimate.expected_next_gain == NumericBand.exact(0)
            assert record.units_consumed == len(receipts) == len(connections[0].contexts)
            assert packed['completion']['ended_by'] == 'yield_stop'
            assert packed['form'] == result.as_record()['form']
            assert packed['form']['completed'] is True
            assert packed['form']['yield']['expected_next_gain'] == NumericBand.exact(0).as_record()
            information = PracticalReceiptInformation(restored.store, run_id)
            assert len(packed['form']['receipts']) == len(receipts)
            assert [information.read(reference, scope)['receipt']
                    for reference in packed['form']['receipts']] == receipts
            assert restored.execution_backend.load_commission(commission['handle']) == original_commission
            starts = [receipt for receipt in receipts if receipt['tool_name'] == 'practical.job.start']
            assert len(starts) == 1
            if wired_family:
                dependencies = restored.progress_provider.direct_dependencies(
                    original_commission['handle'], scope)
                assert len(dependencies) == 1
                target = restored.progress_provider.job_provider.targets.read_target(
                    dependencies[0]['handle'], scope)
                assert target['origin_episode_id'] == episode.source.episode_id
                assert target['resource_id'] == 'local'
                assert target['execution_id'] == starts[0]['outcome']['facts']['requested_job']['execution_id']
            return record, packed
    record, packed = asyncio.run(execute_worker_factory())
    assert len(connections) == 1
    assert connections[0].entered and connections[0].exited
    assert connections[0].models == settings['models']
    assert (spec.work / 'invocations').read_text() == 'once\n'
    assert json.loads(spec.result.read_text()) == {'cwd': str(spec.work),
        'nonce': spec.nonce, 'value': 'job-specific'}
    assert commission == original_commission
    assert reconstruction.implementation_sha256() == runtime_binding['implementation_sha256']
    with Store(workspace) as store:
        saved_request = json.loads(store.db.execute('SELECT request FROM runtime_episodes '
            'WHERE run_id=? AND episode_id=?', (run_id, commission['child']['episode_id'])).fetchone()[0])
        assert saved_request == original_commission['child']['request']
        assert store.db.execute('SELECT count(*) FROM runtime_observations '
            'WHERE run_id=? AND episode_id=?', (run_id, commission['parent']['episode_id'])).fetchone()[0] == 0
