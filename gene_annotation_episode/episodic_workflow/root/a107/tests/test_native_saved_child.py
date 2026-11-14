"""Controlled Native child return and reopen; no controller or native transport.

The real HPC plan, assignment admission, task execution, live zero-credit
projection, facts, typed return, archive and registry reconstruction are used.
Observation delivery and source end are explicit test ports. They do not prove
iterator/yield operation, scientific execution, or the other 22 Native homes.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import importlib
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from . import private_saved_carriers as registry_fixture
from . import direct_saved_carriers as information_fixture
from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import recorded_queue

AXIS = 'a107'
PACKAGE = 'gene_annotation_episode.episodic_workflow.root.' + AXIS
PARENTS = (
    'hpc_work_planning',
    'hpc_work_planning/hpc_allocation_execution',
    'scientific_process/hpc_work_planning',
    'scientific_process/hpc_work_planning/hpc_allocation_execution',
)
STATUSES = ('completed', 'partial', 'invalid', 'failed', 'unavailable')
CLOSED = 'execution_closed_operational_credit_v1'
FORM = {'type': 'object', 'properties': {
    'handoffs': {'type': 'array', 'items': {'type': 'string', 'format': 'reference',
        'x-reference-namespace': 'execution_handoff'}, 'x-source': 'execution_handoff_refs'},
    'completed': {'type': 'boolean', 'x-source': 'execution_completed'}},
    'required': ['handoffs', 'completed'], 'additionalProperties': False}


def module(name):
    return importlib.import_module(PACKAGE + '.' + name.replace('/', '.'))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def forbidden(*args, **kwargs):
    raise AssertionError('controlled_native_saved_child_crossed_unprovided_port')


@pytest.fixture(autouse=True)
def no_transport(monkeypatch):
    monkeypatch.setattr('subprocess.Popen', forbidden)
    monkeypatch.setattr('socket.socket.connect', forbidden)
    monkeypatch.setattr('socket.socket.connect_ex', forbidden)


def publish(store, directory, *, resume=False):
    """Reuse original registry operands; reconstruct saved descriptors on reopen."""
    runtime = module('runtime')
    captured = []

    def before_root(workflow, *args, **kwargs):
        assert args[:2] == ('annotation', 'root')
        captured.append(workflow)
        raise registry_fixture.BeforeRootBuild()

    # Use the existing typed service setup for initial publication and resume.
    # The unselected monitor has the same explicit forbidden caller port on both
    # sides; no runtime attributes or saved role-credit definitions are patched.
    monitor = {'monitor': {'definition': {'kind': 'caller_supplied_monitor_control'},
                           'project': forbidden}}

    def setup(owned_store, *, run_id, directory, job_episodes=None, resource_estimator=None):
        if resume:
            descriptors = json.loads((directory / 'run.json').read_text())['episode_bindings']
        else:
            # Constructor-only operands use the actual setup context, as in the
            # existing service factory. Real workflow services are supplied by
            # the runtime's strict descriptor composer before a task can run.
            construction = SimpleNamespace(workflow=SimpleNamespace(
                store=owned_store, run_id=run_id, directory=directory))
            descriptors = [factory(construction).as_record()
                for factory in registry_fixture.factories(AXIS, directory)]
        return module('episode_application_services').EpisodeApplicationServices(
            episode_binding_descriptors=descriptors, role_credit_bindings=monitor,
            **information_fixture.information_options(AXIS))

    options = {'episode_service_factory': setup,
               'episode_service_binding': {'version': 'controlled_native_saved_child_setup_v1'}}

    with patch.object(runtime.Workflow, 'build', before_root):
        with pytest.raises(registry_fixture.BeforeRootBuild):
            asyncio.run(runtime._run_bound_workflow(store, module('tools').ToolRegistry(store),
                provider=object(), run_dir=directory / 'workflow', resume=resume,
                controller_factory=registry_fixture.controller_factory,
                project_credit=registry_fixture.project_credit,
                episode_record_receipts=True, initial_known_record_refs=[],
                annotation_child_roles=('hpc', 'scientific_process'), decision_protocol=None,
                **options))
    assert len(captured) == 1
    return captured[0]


def ancestor(workflow, path, scope, assignment, parent=None):
    """Controlled ancestor requests, with real goals, receipt links and IDs."""
    runtime = module('runtime')
    ident = module('method_loop.identities').EpisodeRef(workflow.run_id, path).episode_id
    goal = (runtime.EpisodeGoal.root(objective='Controlled Native return custody', result_contract={})
        if parent is None else runtime.EpisodeGoal.child(parent.request.goal,
            objective='Controlled Native commissioning ancestor', result_contract={}))
    message = {'scope': scope, 'initial_report': {}, 'episode_assignment': assignment,
        'knowledge_inheritance': workflow.receipts.bind(ident,
            None if parent is None else parent.episode_id)}
    request = runtime.EpisodeRequest(goal, runtime.Record(message), None)
    workflow.journal.save('runtime_episodes', {'episode_id': ident, 'path': canonical(path),
        'request': canonical(request.as_record()), 'initial_credit': 0, 'state': 'active',
        'completion': None, 'archive': None})
    if parent is None:
        workflow.receipts.receive(ident, scope['subject_refs'], kind='initial')
    source = SimpleNamespace(path=path, scope=scope, episode_id=ident, request=request)
    return source


def planned_launch(workflow, parent_home, scope):
    """Same mathematical plan operation and inputs as InformationCase."""
    path = (('annotation', 'root'),)
    parent = ancestor(workflow, path, scope, {})
    if parent_home.startswith('scientific_process/'):
        path += (('scientific_process', 'controlled_science'),)
        parent = ancestor(workflow, path, scope, {}, parent)
    path += (('hpc', 'original_plan'),)
    parent = ancestor(workflow, path, scope, {'commission_id': 'commission'}, parent)
    planner = workflow.episode_bindings.for_path(path)
    planner.initialize(workflow.binding_context(parent))
    if parent_home.endswith('/hpc_allocation_execution'):
        owner_id = parent.episode_id
        path += (('hpc_execution', 'original_allocation'),)
        parent = ancestor(workflow, path, scope,
            {'commission_id': 'commission', 'owner_episode_id': owner_id}, parent)
        planner = workflow.episode_bindings.for_path(path)
        planner.initialize(workflow.binding_context(parent))
    context = workflow.binding_context(parent)
    ledger = planner.state(context)
    queue_ref = ledger.put('queue', {'snapshot': recorded_queue(module('hpc_queue'))})
    outcome = asyncio.run(planner.execute(context, 'hpc.plan',
        {'candidate_id': ledger.commission['candidates'][0]['id'],
         'model_ref': 'reference_model', 'queue_ref': queue_ref},
        'native-saved-child-original-plan:' + parent_home))
    assert outcome['status'] == 'completed'
    plan = ledger.read(outcome['result']['plan_ref'])
    launch_owner = workflow.episode_bindings.for_child(path, 'launch')
    launch_assignment = launch_owner.prepare_assignment(context, 'launch',
        deepcopy(plan['launch_assignment']), scope, workflow.run_id + ':' + parent.episode_id + ':0')
    assert launch_assignment == plan['launch_assignment']
    runtime = module('runtime')
    contract = runtime.TypedReportContract('Return original handoff information', FORM,
        workflow.resolver(scope, context=context))
    launch = workflow.build('launch', 'original_launch', 'Retain the planned HPC work', scope,
        parent=parent.request.goal, parent_path=path, contract=contract,
        episode_assignment=launch_assignment)
    return launch, plan


def selection(scope, assignment):
    return {'kind': 'episode_child', 'role': 'launch_hpc', 'scope': scope,
        'assignment': deepcopy(assignment), 'purpose': 'Return actual handoffs and completion',
        'goal': 'Retain the original HPC assignment and all returned outcomes',
        'initial_report_json': '{}', 'schema_json': canonical(FORM)}


def acquire_and_close(workflow, unit):
    """Acquire real task actions; explicitly deliver observations and source end.

    No UnitRecord claims a controller step. A zero value comes from the actual
    private practical state, never a test projection. No command is executed.
    """
    child, acquired, records, expected = unit.child, [], [], []
    runtime, loop = module('runtime'), module('method_loop.episode')
    owner = workflow.specialist(child.source)
    context = workflow.binding_context(child.source)
    assert type(child.source) is owner.decision_source_type
    assert type(child.source).__name__ == 'NativeTask'
    assert owner.roles == ('launch_hpc',)
    assert set(owner.as_record()) == {'binding_id', 'version', 'configuration'}
    before_credit = workflow.source_credit_view(child.source)
    assert before_credit['credit'] == 0

    async def returned(source, tool, arguments, *, decision_index, operation_key):
        assert source is child.source and tool == 'exec_command'
        assert operation_key == f'{workflow.run_id}:{source.episode_id}:{decision_index}'
        status = STATUSES[decision_index]
        acquired.append(operation_key)
        return {'status': status, 'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': None if status in ('completed', 'partial') else
                {'category': 'controlled_native_return', 'code': status}}

    for index, status in enumerate(STATUSES):
        action = {'kind': 'tool', 'tool': 'exec_command', 'arguments': {
            'cmd': 'controlled returned outcome ' + status,
            'workdir': context.assignment['workspace'], 'env': {}}}
        with patch.object(workflow, 'execute', returned):
            value = asyncio.run(child.source.execute(deepcopy(action), index))
        row = workflow.journal.row('runtime_actions', child.source.episode_id, index)
        outcome = json.loads(row['result'])
        assert outcome['status'] == status and row['credit'] == 0
        assert value.as_record()['credit'] == 0
        assert workflow.source_credit_view(child.source) == before_credit
        # Explicit observation port: actual callback writes the original
        # action identity and actual returned projection, with no yield step.
        label = 'tool:' + str(index)
        ref = module('method_loop.identities').UnitRef(child.source.episode_id, index)
        slot = workflow.completions.stage(child.source.episode_id, index, label=label,
            kind='own_action', controller_input=value, child_return=None)
        assert slot['sequence'] == index
        view = loop.UnitView(label, value, None, 'controlled_observation_without_controller', ref)
        child.on_unit(SimpleNamespace(decision_index=index), loop.Contribution(value), view)
        records.append(loop.UnitRecord(label, value, None, view.epoch, ref))
        expected.append({'action': action, 'outcome': outcome, 'value': value.as_record()})
    assert len(acquired) == len(STATUSES)
    # This is an explicit fixture source failure, not a successful execution
    # receipt, an exhausted-science claim, or a production stopping policy.
    end = runtime.SourceEnd('source_failed')
    error = module('providers').ModelCallError('controlled_saved_child_source_unavailable')
    module('episode_source_failure').record_source_failure(workflow.store, workflow.run_id,
        child.source.episode_id, len(STATUSES), error)
    workflow.completions.checkpoint_source(child.source.episode_id, expected_revision=None,
        latest_effect_index=None, last_outcome_index=len(STATUSES) - 1,
        feedback=child.source.feedback)
    record = loop.EpisodeRecord('launch_hpc', child.key, len(records), end.kind,
        tuple(records), None, child.request, path=child.source.path, end_reason=end.kind,
        episode_ref=module('method_loop.identities').EpisodeRef(workflow.run_id, child.source.path))
    child.on_close(record)
    # The original child unit now builds the real Native report, validates it,
    # admits it to the actual Launch parent, and projects parent credit.
    returned_unit = asyncio.run(unit._finish_async(record))
    assert returned_unit.child_result.as_record() == {'form': {'handoffs': [], 'completed': False}}
    facts = workflow.facts(child.source)
    assert facts['practical_completed'] is False and facts['execution_completed'] is False
    assert facts[CLOSED]['view'] == before_credit
    assert not facts['execution_handoff_refs'] and not facts['practical_receipt_refs']
    assert owner._delegate(context).state(owner._practical_context(context)).receipts() == []
    return {'request': child.request.as_record(), 'context': context.as_record(),
        'home': owner.binding_path, 'descriptor': owner.as_record(), 'actions': expected,
        'facts': facts, 'credit': before_credit,
        'archive': json.loads(workflow.journal.row('runtime_episodes', context.episode_id)['archive'])}


def retained_rows(workflow, episode_id):
    return {name: [dict(row) for row in workflow.store.db.execute(
        'SELECT * FROM ' + name + ' WHERE run_id=? AND episode_id=? ORDER BY rowid',
        (workflow.run_id, episode_id))] for name in
        ('runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_forms')}


@pytest.mark.parametrize('parent_home', PARENTS)
def test_genuine_hpc_native_child_closes_and_reopens_with_original_outcomes(tmp_path, parent_home):
    directory = tmp_path / 'native-saved-child'
    directory.mkdir()
    registry_fixture.write_instruction_source(directory / 'instruction-source', AXIS)
    module('scientific_process_library').ScientificProcessLibrary.freeze(
        directory / 'workflow/scientific-process-library', source=directory / 'instruction-source')
    module('scientific_tool_library').ScientificToolLibrary.freeze(directory / 'workflow/scientific-tool-library', catalog=[])
    with module('state').Store(directory / 'store') as store:
        scope = {'subject_refs': store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']}
        workflow = publish(store, directory)
        launch, plan = planned_launch(workflow, parent_home, scope)
        chosen = selection(scope, plan['practical_assignment'])
        unit = workflow.selected(launch.source, chosen, 0)
        assert unit.child.source.path == launch.source.path + (('launch_hpc', 'child_0'),)
        assert workflow.specialist(unit.child.source).binding_path == (
            parent_home + '/execution_job_submission/hpc_job_execution')
        saved = acquire_and_close(workflow, unit)
        child_id = saved['context']['episode_id']
        original_rows = retained_rows(workflow, child_id)
        original_run = (directory / 'workflow/run.json').read_bytes()
        launch_request = launch.request.as_record()
        launch_context = workflow.binding_context(launch.source).as_record()
        parent_return = dict(workflow.journal.row('runtime_actions', launch.source.episode_id, 0))
        assert json.loads(parent_return['result'])['status'] == 'completed'
        assert json.loads(parent_return['result'])['child_completion']['result_status'] == 'partial'
        descriptors = workflow.episode_bindings.as_record()
    # Real Store close/reopen; factories are absent on this side. Fourth's
    # strict descriptor protocol must reconstruct the exact selected owners.
    with module('state').Store(directory / 'store') as store:
        restored = publish(store, directory, resume=True)
        assert restored.episode_bindings.as_record() == descriptors
        assert (directory / 'workflow/run.json').read_bytes() == original_run
        owner = restored.episode_bindings.for_path(tuple(tuple(v) for v in saved['context']['path']))
        assert owner.binding_path == saved['home'] and owner.as_record() == saved['descriptor']
        assert owner.commissioning_parent == parent_home + '/execution_job_submission'
        assert type(owner).__module__ == PACKAGE + '.' + saved['home'].replace('/', '.') + '.episode'
        runtime = module('runtime')
        # Recreate the authentic original Launch source, with its original
        # request, solely to select the already returned Native child.
        launch_owner = restored.episode_bindings.for_path(tuple(tuple(v) for v in launch_context['path']))
        launch_type = getattr(launch_owner, 'decision_source_type', runtime.DecisionSource)
        launch_source = launch_type(restored, tuple(tuple(v) for v in launch_context['path']),
            runtime.EpisodeRequest(runtime.EpisodeGoal.from_record(launch_request['goal']),
                runtime.Record(launch_request['message']), runtime.TypedReportContract(
                    launch_request['report_contract']['decision'],
                    launch_request['report_contract']['measurements']['schema'],
                    restored.resolver(scope, context=module('episode_return_records').EpisodeReturnRecords(
                        store, restored.run_id, failure_prefix='closed_commission_').context(launch_context['episode_id'])))), scope)
        rebuilt = restored.selected(launch_source, chosen, 0).child
        assert rebuilt.request.as_record() == saved['request']
        assert type(rebuilt.source) is owner.decision_source_type
        rebuilt.source.restore()
        rebuilt.source.restore_checkpoint()
        assert rebuilt.source.last_outcome == saved['actions'][-1]['outcome']
        assert rebuilt.source.last_outcome_index == len(STATUSES) - 1
        assert rebuilt.source._unfinished_own_actions == []
        with patch.object(restored, 'execute', forbidden), patch.object(owner, '_live_project_credit', forbidden):
            assert restored.source_credit_view(rebuilt.source) == saved['credit']
            for index, original in enumerate(saved['actions']):
                assert asyncio.run(rebuilt.source.execute(original['action'], index)).as_record() == original['value']
            changed = deepcopy(saved['actions'][0]['action'])
            changed['arguments']['cmd'] = 'changed original selected action'
            with pytest.raises(runtime.WorkflowError, match='reconstructed selected work changed'):
                asyncio.run(rebuilt.source.execute(changed, 0))
            assert asyncio.run(rebuilt.source.finish(None)).as_record() == {'form': {'handoffs': [], 'completed': False}}
        assert retained_rows(restored, child_id) == original_rows
        assert dict(restored.journal.row('runtime_actions', launch_source.episode_id, 0)) == parent_return
        assert restored.archive_reference(saved['archive']).load()['request'] == saved['request']
