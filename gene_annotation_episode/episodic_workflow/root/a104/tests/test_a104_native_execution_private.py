"""Twelve actual native owners with real journals/state and controlled execution.

Only TerminalExecution.execute is controlled in command tests. Actual request,
policy, intent, receipt, publication, validation, projection and replay bodies
remain installed. A controlled command result is not a producing native run.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import importlib
import json
from types import SimpleNamespace

import pytest
from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources
from gene_annotation_episode.episodic_workflow.root.tests.hpc_planning_allocation_task_behavior import PlanningAllocationTaskBehavior

PARENTS = ('', 'scientific_process', 'hpc_work_planning',
    'hpc_work_planning/hpc_allocation_execution', 'scientific_process/hpc_work_planning',
    'scientific_process/hpc_work_planning/hpc_allocation_execution')
HOMES = tuple('/'.join(part for part in (parent, 'execution_job_submission', native) if part)
    for parent in PARENTS for native in ('local_job_execution', 'hpc_job_execution'))


def own_module(name):
    return importlib.import_module('gene_annotation_episode.episodic_workflow.root.a104.' + name.replace('/', '.'))


def ancestry(home):
    path = (('annotation', 'root'),)
    if home.startswith('scientific_process/'):
        path += (('scientific_process', 'original-science'),)
    if '/hpc_work_planning/' in '/' + home:
        path += (('hpc', 'original-plan-owner'),)
    if '/hpc_allocation_execution/' in home:
        path += (('hpc_execution', 'original-allocation'),)
    return path + (('launch', 'original-launch'),)


@pytest.fixture(params=HOMES)
def native_home(request): return request.param


@pytest.fixture
def native_frame(tmp_path, native_home):
    role = 'launch_local' if native_home.endswith('/local_job_execution') else 'launch_hpc'
    kind = role.removeprefix('launch_')
    local_workspace = tmp_path / 'resource'
    local_workspace.mkdir()
    # Read current approved defaults through the real active-workflow clamp;
    # no historical policy or invented live launch fields are substituted.
    policy = own_module('local_jobs').LocalJobPolicy.from_config().to_dict()
    configuration = {**resources(), 'local-test': {'kind': 'local', 'workspace': str(local_workspace), 'policy': policy}}
    resource_id = 'local-test' if kind == 'local' else 'aurora'
    workspace = configuration[resource_id]['workspace']
    assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'original-controlled-native',
        'resource_id': resource_id, 'resource_kind': kind, 'workspace': workspace, 'endpoint': 'usable_handoff',
        'requested_job': {'argv': ['/not-an-executable-native-contract-fixture'], 'environment': {}},
        'progress_requirements': [
            {'key': 'prepared-context', 'credit': 1., 'predicate': {'kind': 'context_environment', 'name': 'A104_FIXTURE', 'value': 'prepared'}},
            {'key': 'handoff', 'credit': 1., 'predicate': {'kind': 'requested_job_handoff'}}],
        'completion_keys': ['handoff'],
        'initial_context': {'revision': 0, 'cwd': workspace, 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {}}
    parent_assignment = {'version': 'execution_launch_assignment_v1', 'requests': {resource_id: deepcopy(assignment)},
        'immutable_input_versions': [], 'constraints': {}}
    runtime = own_module('runtime')
    Context, EpisodeRef = own_module('episode_bindings').BindingContext, own_module('method_loop.identities').EpisodeRef
    with own_module('state').Store(tmp_path / 'store') as store:
        scope = {'subject_refs': store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']}
        run_id = 'a104-native-private'
        journal = own_module('episode_journal').Journal(store, run_id)
        services = SimpleNamespace(annotation_task_required=lambda: False)
        options = dict(store=store, run_id=run_id, directory=tmp_path / 'workflow', resources=configuration,
            initial_information={}, tool_registry=None, handoff_unit=1., acquired_record_unit=1.,
            log_window_bytes=1024, log_roles=('stdout', 'stderr'), require_private_yield=True,
            task_yield_profiles={role + ':practical_' + kind + '_handoff': {'cutoff': .5, 'parameters': {}}})
        binding = own_module(native_home + '/episode').ExecutionEpisode(services, **options)
        parent_binding = own_module(native_home.rsplit('/', 1)[0] + '/episode').ExecutionEpisode(services, **options)
        parent_path = ancestry(native_home)
        parent = Context(run_id, EpisodeRef(run_id, parent_path).episode_id, 'launch', parent_path,
            scope, parent_assignment, {'message': {'scope': scope, 'episode_assignment': parent_assignment}})
        path = parent_path + ((role, 'child_1'),)
        context = replace(parent, episode_id=EpisodeRef(run_id, path).episode_id, role=role, path=path,
            assignment=assignment, request={'message': {'scope': scope, 'episode_assignment': assignment}})
        for value in (parent, context):
            journal.save('runtime_episodes', {'episode_id': value.episode_id, 'path': runtime._json(value.path),
                'request': runtime._json(value.request), 'initial_credit': 0., 'state': 'active',
                'completion': None, 'archive': None})
        # This separately constructed service fixture does not claim that a
        # failed outer admission succeeded. Its real context/journal is explicit.
        service = binding._practical[resource_id]
        service.initialize(context)
        yield SimpleNamespace(home=native_home, binding=binding, parent_binding=parent_binding,
            parent=parent, context=context, service=service, store=store, journal=journal,
            runtime=runtime, configuration=configuration, options=options,
            c={'objective': 'Preserve original native execution outcomes'})


def select_action(frame, arguments, index=0):
    frame.journal.save('runtime_actions', {'episode_id': frame.context.episode_id, 'decision_index': index,
        'action': frame.runtime._json({'kind': 'tool', 'tool': 'exec_command', 'arguments': arguments}),
        'result': None, 'credit': None})
    return f'{frame.context.run_id}:{frame.context.episode_id}:{index}'


def test_real_parent_admission_once_and_original_role(native_frame):
    frame = native_frame
    assert frame.binding.commissioning_parent == frame.home.rsplit('/', 1)[0]
    assert frame.binding.roles == (frame.context.role,)
    original = own_module('communication').plain(frame.context.assignment)
    callback = getattr(frame.parent_binding, 'prepare_child_request', None)
    selected = original if callback is None else callback(frame.parent, frame.context.role, original)
    assert selected is original
    # Direct/scientific copied-parent failures remain real baseline failures.
    admitted = frame.binding.prepare_assignment(frame.parent, frame.context.role, selected,
        frame.context.scope, f'{frame.context.run_id}:{frame.parent.episode_id}:1')
    assert admitted == original and admitted is not original
    with pytest.raises(ValueError, match='unknown_execution_episode_role'):
        frame.binding.assignment_schema('launch', internal=True)


@pytest.mark.parametrize('failure', (False, True))
def test_actual_intent_receipt_publication_credit_and_replay(native_frame, monkeypatch, failure):
    frame = native_frame
    calls = []
    async def controlled(operations, state, name, arguments, operation_key):
        calls.append((name, deepcopy(arguments), operation_key))
        if failure:
            raise OSError('controlled native operation unavailable')
        return {'facts': {}, 'native_outcome': {'controlled_execution_port': True,
            'qualification': 'no producing native work asserted'}}, None
    monkeypatch.setattr(own_module('library.native_terminal_transport').TerminalExecution, 'execute', controlled)
    arguments = {'cmd': 'controlled command port', 'workdir': frame.context.assignment['workspace'],
        'env': {} if failure else {'A104_FIXTURE': 'prepared'}}
    key = select_action(frame, arguments)
    result = asyncio.run(frame.service.execute(frame.context, 'exec_command', deepcopy(arguments), key))
    assert result['status'] == 'completed' and len(result['record_refs']) == 1
    receipt = result['result']
    if failure:
        assert receipt['outcome']['native_outcome']['failure'] == {
            'code': 'execution_action_failed', 'exception_type': 'OSError',
            'detail': 'controlled native operation unavailable'}
    else:
        assert receipt['outcome']['native_outcome']['controlled_execution_port'] is True
    assert frame.service.state(frame.context).completion_proof() is None
    # Credit is computed by the original PracticalState validators, not a test projector.
    view = frame.service.credit_view(frame.context, None)
    assert view['credit'] == (0. if failure else 1.)
    frame.journal.save('runtime_actions', {'episode_id': frame.context.episode_id, 'decision_index': 0,
        'action': frame.runtime._json({'kind': 'tool', 'tool': 'exec_command', 'arguments': arguments}),
        'result': frame.runtime._json(result), 'credit': view['credit']})
    replay = asyncio.run(frame.service.execute(frame.context, 'exec_command', deepcopy(arguments), key))
    assert replay == result and len(calls) == 1
    reader = own_module('practical_receipt_information').PracticalReceiptInformation(frame.store, frame.context.run_id)
    assert reader.read(result['record_refs'][0], frame.context.scope)['receipt'] == receipt
    assert reader.resolve(frame.parent, result['record_refs'][0], 'practical_receipt') is True
    assert len(frame.service.state(frame.context).receipts()) == 1
    facts = frame.service.facts(frame.context, {})
    field = frame.service.fact_sources(frame.context.role)['practical_receipt_refs']['report_schema']
    schema = {'type': 'object', 'properties': {'receipts': field}, 'required': ['receipts'], 'additionalProperties': False}
    form = {'receipts': facts['practical_receipt_refs']}
    frame.service.validate_report(frame.context, form, schema)
    frame.service.validate_report(frame.context, deepcopy(form), deepcopy(schema))
    assert form['receipts'] == result['record_refs']
    with pytest.raises(ValueError, match='execution_report_disagrees_with_recorded_facts'):
        frame.service.validate_report(frame.context, {'receipts': []}, schema)
    with pytest.raises(ValueError, match='practical_receipt_outside_receiving_scope'):
        reader.read(result['record_refs'][0], {'subject_refs': []})


def test_invalid_command_returns_without_native_intent(native_frame, monkeypatch):
    frame = native_frame
    async def forbidden(*args, **kwargs):
        raise AssertionError('invalid command acquired native work')
    monkeypatch.setattr(own_module('library.native_terminal_transport').TerminalExecution, 'execute', forbidden)
    before = list(frame.service.state(frame.context).receipts())
    result = asyncio.run(frame.service.execute(frame.context, 'exec_command', {'unknown': True}, 'invalid-selection'))
    assert result['status'] == 'invalid'
    assert list(frame.service.state(frame.context).receipts()) == before


@pytest.mark.parametrize('status', ('completed', 'invalid', 'failed', 'unavailable'))
def test_returned_native_outcome_enters_original_task_once(native_frame, tmp_path, status):
    frame = native_frame
    adapter = SimpleNamespace(setup=lambda _: frame, module=own_module)
    case = PlanningAllocationTaskBehavior.fixture(adapter, tmp_path)
    payload = {'status': status, 'record_refs': [], 'changed_record_refs': [],
        'result': {'original_native_owner': frame.home, 'qualification': ['full', 'original', 'payload']},
        'feedback': {'code': 'controlled-native-return'}}
    calls = []
    async def returned(source, name, arguments, **kwargs):
        calls.append(kwargs['operation_key'])
        return deepcopy(payload)
    case.task.workflow.execute = returned
    selected = {'kind': 'tool', 'tool': 'exec_command', 'arguments': {'retained': True}}
    outcome = asyncio.run(case.task.execute(selected, 4))
    assert asyncio.run(case.task.execute(selected, 4)) == outcome
    assert json.loads(case.saved[4]['result']) == payload and json.loads(case.saved[4]['action']) == selected
    assert case.receipts == [(4, status)] and len(calls) == len(case.projections) == 1


@pytest.mark.parametrize('kind,status', (('wait', 'completed'), ('wait', 'failed'), ('reason', 'completed')))
def test_native_saved_action_preserves_original_credit(native_frame, tmp_path, kind, status):
    adapter = SimpleNamespace(setup=lambda _: native_frame, module=own_module)
    case = PlanningAllocationTaskBehavior.fixture(adapter, tmp_path)
    selected = {'kind': kind, **({'condition': {'original': 'saved'}} if kind == 'wait' else {'reasoning': {'original': 'saved'}})}
    payload = {'status': status, 'record_refs': [], 'changed_record_refs': [],
        'result': {'original': 'saved payload'}, 'feedback': {'code': 'saved-qualification'}}
    case.saved[8] = {'episode_id': case.task.episode_id, 'decision_index': 8,
        'action': case.runtime._json(selected), 'result': case.runtime._json(payload), 'credit': 7.25}
    if kind == 'wait' and status == 'failed':
        with pytest.raises(case.runtime.ActionFailure): asyncio.run(case.task.execute(selected, 8))
    else:
        assert asyncio.run(case.task.execute(selected, 8)) == {'index': 8, 'credit': 7.25}
    assert case.executions == case.receipts == case.projections == []
    assert json.loads(case.saved[8]['result']) == payload


def test_actual_runtime_selects_each_private_native_task(native_frame, tmp_path, monkeypatch):
    adapter = SimpleNamespace(setup=lambda _: native_frame, module=own_module, role=native_frame.context.role)
    PlanningAllocationTaskBehavior.test_original_runtime_build_selects_this_binding_task(adapter, tmp_path, monkeypatch)


def test_original_yield_callback_record_and_observation_replay(native_frame, tmp_path):
    frame = native_frame
    home_module = 'gene_annotation_episode.episodic_workflow.root.a104.' + frame.home.replace('/', '.')
    controller = frame.binding.yield_controller(frame.context, 0., 'original-native-epoch')
    actual = controller.estimator.estimate_with_context.as_record()
    expected = home_module + '.yield_estimator.ExecutionEpisodeYield._' + frame.context.role + '_yield_controller.<locals>.<lambda>'
    assert actual['completion_verifier'] == expected
    assert frame.binding.practical_estimator.__func__.__module__ == home_module + '.yield_estimator'
    assert frame.binding.practical_estimator.__func__.__qualname__ == 'ExecutionEpisodeYield.practical_estimator'
    service_record = frame.binding.practical_estimator(frame.context).as_record()
    assert service_record['completion_verifier'] == 'gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state.PracticalState.verify_completion'
    before = controller.state().as_record()
    values = [{'credit': 0.}, {'credit': 1.}, {'credit': 1.}]
    observed = [controller.observe(str(index), deepcopy(value)).as_record() for index, value in enumerate(values)]
    restored = frame.binding.yield_controller(frame.context, 0., 'original-native-epoch')
    assert restored.state().as_record() == before
    assert [restored.observe(str(index), deepcopy(value)).as_record() for index, value in enumerate(values)] == observed
    assert restored.state().as_record() == controller.state().as_record()
    # Durable per-test evidence supports baseline/connected comparison. This is
    # actual controller replay, distinct from full closed-carrier reconstruction.
    (tmp_path / 'yield_identity.json').write_text(json.dumps({'home': frame.home,
        'estimator': actual, 'service_estimator': service_record, 'initial_state': before,
        'observed': observed, 'final_state': controller.state().as_record()}, sort_keys=True, indent=2) + '\n')


@pytest.mark.parametrize('text_context', (False, True))
def test_actual_native_presentation_preserves_original_frames(native_frame, text_context):
    kind = own_module('providers')._SessionConnection
    original, selected = object.__new__(kind), object.__new__(kind)
    original.scientific_prompt_states, selected.scientific_prompt_states = {}, {}
    renderer = getattr(native_frame.binding, 'decision_prompt_renderer', None)
    decision = own_module('decision_context')
    state = {'retained_execution': {'status': 'partial', 'qualification': ['original']}}
    if text_context: state['hpc_execution_job'] = {'original_request': 'retained'}
    updated = {**deepcopy(state), 'retained_execution': {'status': 'failed'}}
    for context in (state, decision.state_frame(state), decision.state_frame(updated, state),
            {'version': decision.VERSION, 'kind': 'decision_lookup_result', 'result': {'original': ['lookup']}}):
        expected = original._presentation(native_frame.context.episode_id, 'REASONING', 'Original goal', deepcopy(context))
        actual = selected._presentation(native_frame.context.episode_id, 'REASONING', 'Original goal', deepcopy(context), prompt_renderer=renderer)
        assert actual == expected and selected.scientific_prompt_states == original.scientific_prompt_states


def test_pending_owned_child_and_rejected_redelivery_preserve_task_state(native_frame, tmp_path):
    adapter = SimpleNamespace(setup=lambda _: native_frame, module=own_module)
    adapter.fixture = lambda path: PlanningAllocationTaskBehavior.fixture(adapter, path)
    PlanningAllocationTaskBehavior.test_ready_original_child_is_collected_before_another_decision(adapter, tmp_path)
    PlanningAllocationTaskBehavior.test_redelivery_rejects_changed_interpretation_before_acquisition(adapter, tmp_path)
