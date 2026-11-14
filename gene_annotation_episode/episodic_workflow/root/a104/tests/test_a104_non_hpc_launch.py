"""Direct/scientific Launch preservation at actual Store and task boundaries.

The native request is an explicitly unlaunchable contract fixture. No HPC plan,
allocation, transport, native operation or provider is executed. The parent
context is real data; the absent annotation binding is not fabricated.
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


def own_module(name):
    return importlib.import_module('gene_annotation_episode.episodic_workflow.root.a104.' + name.replace('/', '.'))


@pytest.fixture(params=('execution_job_submission', 'scientific_process/execution_job_submission'))
def launch_home(request):
    return request.param


@pytest.fixture
def launch_frame(tmp_path, launch_home):
    config = resources()
    workspace = config['aurora']['workspace']
    native = {'version': 'practical_assignment_v1', 'assignment_id': 'non-hpc-parent-contract',
        'resource_kind': 'hpc', 'resource_id': 'aurora', 'workspace': workspace,
        'endpoint': 'usable_handoff',
        'requested_job': {'argv': ['/not-an-executable-non-hpc-contract-fixture'], 'environment': {}},
        'progress_requirements': [{'key': 'handoff', 'credit': 1., 'predicate': {'kind': 'requested_job_handoff'}}],
        'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': workspace, 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {'account': config['aurora']['account']}}
    assignment = {'version': 'execution_launch_assignment_v1', 'requests': {'aurora': native},
        'immutable_input_versions': [], 'constraints': {}}
    Context = own_module('episode_bindings').BindingContext
    EpisodeRef = own_module('method_loop.identities').EpisodeRef
    runtime = own_module('runtime')
    with own_module('state').Store(tmp_path / 'state') as store:
        scope = {'subject_refs': store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']}
        run_id = 'a104-non-hpc-contract'
        journal = own_module('episode_journal').Journal(store, run_id)
        services = SimpleNamespace(annotation_task_required=lambda: False)
        options = dict(store=store, directory=tmp_path / 'workflow', run_id=run_id,
            resources=config, initial_information={}, tool_registry=None,
            handoff_unit=1., acquired_record_unit=1., log_window_bytes=1024,
            log_roles=('stdout', 'stderr'))
        binding = own_module(launch_home + '/episode').ExecutionEpisode(services, **options)
        path = (('annotation', 'root'),)
        if launch_home.startswith('scientific_process/'):
            path += (('scientific_process', 'original-A104'),)
        parent = Context(run_id, EpisodeRef(run_id, path).episode_id, path[-1][0], path, scope, {}, {})
        selected = binding.prepare_assignment(parent, 'launch', deepcopy(assignment), scope,
            f'{run_id}:{parent.episode_id}:1')
        path += (('launch', 'child_1'),)
        context = replace(parent, role='launch', path=path, episode_id=EpisodeRef(run_id, path).episode_id,
            assignment=selected, request={'message': {'scope': scope, 'episode_assignment': selected}})
        for value in (parent, context):
            journal.save('runtime_episodes', {'episode_id': value.episode_id, 'path': runtime._json(value.path),
                'request': runtime._json(value.request), 'initial_credit': 0., 'state': 'active',
                'completion': None, 'archive': None})
        binding.initialize(context)
        yield SimpleNamespace(binding=binding, context=context, parent=parent, store=store,
            journal=journal, services=services, options=options, native=native, assignment=assignment,
            c={'objective': 'Preserve direct and scientific Launch semantics'})


def task_case(frame, tmp_path):
    adapter = SimpleNamespace(setup=lambda _: frame, module=own_module)
    return PlanningAllocationTaskBehavior.fixture(adapter, tmp_path)


def test_actual_non_hpc_admission_and_actions(launch_frame, launch_home):
    frame = launch_frame
    assert all(role not in {'hpc', 'hpc_execution'} for role, _ in frame.context.path)
    assert own_module('communication').plain(frame.context.assignment) == frame.assignment
    assert frame.binding.binding_path == launch_home
    assert frame.binding.permitted_common_actions(frame.context) == ('tool', 'reason', 'child', 'wait', 'redeliver_report')
    assert frame.binding.allowed_children(frame.context, {}) == ('launch_hpc',)
    record = frame.binding.as_record()
    assert record == frame.binding.as_record()
    assert 'implementation_sha256' not in record
    assert record['configuration']['resources'] == resources()


def test_actual_capability_outcome_invalid_arguments_and_original_credit(launch_frame, tmp_path):
    case = task_case(launch_frame, tmp_path)
    for index, arguments in enumerate(({}, {'unrequested': True})):
        selected = {'kind': 'tool', 'tool': 'execution.capabilities', 'arguments': arguments}
        result = asyncio.run(case.task.execute(selected, index))
        assert asyncio.run(case.task.execute(selected, index)) == result
        assert json.loads(case.saved[index]['action']) == selected
        assert json.loads(case.saved[index]['result'])['status'] == ('completed' if index == 0 else 'invalid')
    assert case.receipts == [(0, 'completed'), (1, 'invalid')]
    assert len(case.executions) == len(case.projections) == 2


@pytest.mark.parametrize('status', ('failed', 'unavailable'))
def test_returned_failure_enters_original_iterator_once(launch_frame, tmp_path, status):
    case = task_case(launch_frame, tmp_path)
    payload = {'status': status, 'record_refs': [], 'changed_record_refs': [],
        'result': {'original': ['complete', 'qualified', 'payload']}, 'feedback': {'code': 'controlled-return'}}
    calls = []
    async def returned(source, name, arguments, **kwargs):
        calls.append((name, deepcopy(arguments), kwargs['operation_key']))
        return deepcopy(payload)
    case.task.workflow.execute = returned
    selected = {'kind': 'tool', 'tool': 'execution.capabilities', 'arguments': {}}
    expected = asyncio.run(case.task.execute(selected, 4))
    assert asyncio.run(case.task.execute(selected, 4)) == expected
    assert json.loads(case.saved[4]['result']) == payload
    assert case.receipts == [(4, status)] and len(calls) == len(case.projections) == 1


@pytest.mark.parametrize('kind,status', (('wait', 'completed'), ('wait', 'failed'), ('reason', 'completed')))
def test_saved_action_preserves_original_credit_and_outcome(launch_frame, tmp_path, kind, status):
    case = task_case(launch_frame, tmp_path)
    selected = {'kind': kind, **({'condition': {'original': 'saved'}} if kind == 'wait' else {'reasoning': {'original': 'saved'}})}
    payload = {'status': status, 'record_refs': [], 'changed_record_refs': [],
        'result': {'full': 'original result'}, 'feedback': {'code': 'original-qualification'}}
    case.saved[9] = {'episode_id': case.task.episode_id, 'decision_index': 9,
        'action': case.runtime._json(selected), 'result': case.runtime._json(payload), 'credit': 7.25}
    if kind == 'wait' and status == 'failed':
        with pytest.raises(case.runtime.ActionFailure):
            asyncio.run(case.task.execute(selected, 9))
    else:
        assert asyncio.run(case.task.execute(selected, 9)) == {'index': 9, 'credit': 7.25}
    assert json.loads(case.saved[9]['action']) == selected and json.loads(case.saved[9]['result']) == payload
    assert case.executions == case.receipts == case.projections == []


def test_original_runtime_selects_actual_non_hpc_task(launch_frame, tmp_path, monkeypatch):
    adapter = SimpleNamespace(setup=lambda _: launch_frame, module=own_module, role='launch')
    PlanningAllocationTaskBehavior.test_original_runtime_build_selects_this_binding_task(adapter, tmp_path, monkeypatch)


def test_actual_child_admission_receives_selected_object_once(launch_frame, launch_home, monkeypatch):
    frame = launch_frame
    child = own_module(launch_home + '/hpc_job_execution/episode').ExecutionEpisode(frame.services, **frame.options)
    callback = getattr(frame.binding, 'prepare_child_request', None)
    selected = deepcopy(frame.native)
    outgoing = selected if callback is None else callback(frame.context, 'launch_hpc', selected)
    assert outgoing is selected
    calls = []
    original = child.prepare_assignment
    def observed(parent, role, assignment, scope, key):
        calls.append((parent, role, assignment, scope, key))
        return original(parent, role, assignment, scope, key)
    monkeypatch.setattr(child, 'prepare_assignment', observed)
    # This is the actual original child body; any inherited contract failure
    # remains a baseline failure, never a stubbed successful commission.
    admitted = child.prepare_assignment(frame.context, 'launch_hpc', outgoing,
        frame.context.scope, f'{frame.context.run_id}:{frame.context.episode_id}:2')
    assert len(calls) == 1 and calls[0][2] is selected and admitted == selected


@pytest.mark.parametrize('text_context', (False, True))
def test_actual_presentation_frames_keep_original_precedence(launch_frame, text_context):
    provider_type = own_module('providers')._SessionConnection
    original, selected = object.__new__(provider_type), object.__new__(provider_type)
    original.scientific_prompt_states, selected.scientific_prompt_states = {}, {}
    renderer = getattr(launch_frame.binding, 'decision_prompt_renderer', None)
    decision = own_module('decision_context')
    state = {'retained_execution': {'status': 'partial', 'qualification': ['original']}}
    if text_context:
        state['hpc_execution_job'] = {'original_request': 'retained'}
    updated = {**deepcopy(state), 'retained_execution': {'status': 'failed'}}
    for context in (state, decision.state_frame(state), decision.state_frame(updated, state),
            {'version': decision.VERSION, 'kind': 'decision_lookup_result', 'result': {'original': ['lookup']}}):
        expected = original._presentation(launch_frame.context.episode_id, 'REASONING', 'Original goal', deepcopy(context))
        actual = selected._presentation(launch_frame.context.episode_id, 'REASONING', 'Original goal', deepcopy(context), prompt_renderer=renderer)
        assert actual == expected and selected.scientific_prompt_states == original.scientific_prompt_states
