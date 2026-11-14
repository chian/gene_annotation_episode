"""Required source proposal: native constructor/returned-action observations.

Actual Store, Journal, private bindings, full registry, selected task constructor,
execute/checkpoint and persisted replay. Identity allocation and work/projection
ports are controlled explicitly. No native command, network, model decision,
full iterator, real native progress, Workflow.build admission or scientific
validation is claimed. Missing genuine root/local operands remain recorded gaps.
"""
from __future__ import annotations
import argparse
import asyncio
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import traceback
from unittest.mock import patch

AXIS = 'a107'
PREFIX = 'gene_annotation_episode.episodic_workflow.root.' + AXIS + '.'
PARENTS = ('', 'scientific_process', 'hpc_work_planning',
    'hpc_work_planning/hpc_allocation_execution', 'scientific_process/hpc_work_planning',
    'scientific_process/hpc_work_planning/hpc_allocation_execution')

def module(name): return importlib.import_module(PREFIX + name.replace('/', '.'))
def forbidden(*args, **kwargs): raise AssertionError('native_boundary_probe_external_execution_forbidden')
def observe(callback):
    try: return {'status': 'returned', 'value': callback()}
    except Exception as error:
        return {'status': 'raised', 'type': type(error).__module__ + '.' + type(error).__qualname__,
            'message': str(error), 'traceback': traceback.format_exc()}

def source_hashes():
    axis = Path(module('runtime').__file__).parent
    for component in (axis, *axis.parents):
        if component.is_symlink(): raise ValueError('native_source_symlink_component:' + str(component))
    fixture_root = axis / 'tests/fixtures'
    pending, found = [axis], []
    while pending:
        directory = pending.pop()
        for path in sorted(directory.iterdir()):
            if path.is_symlink():
                if path != fixture_root and path.is_relative_to(fixture_root) and path.suffix != '.py':
                    continue
                raise ValueError('native_source_symlink_entry:' + str(path))
            if path.is_dir(): pending.append(path)
            elif path.suffix == '.py':
                if not path.is_file(): raise ValueError('native_source_not_regular:' + str(path))
                for component in (path, *path.parents):
                    if component.is_symlink(): raise ValueError('native_source_symlink_component:' + str(component))
                found.append(path)
    return {str(path.relative_to(axis)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(found)}

def construct(case, binding, context, phase):
    runtime = module('runtime')
    selected = getattr(binding, 'decision_source_type', runtime.DecisionSource)
    assert (selected is runtime.DecisionSource) == (phase == 'baseline')
    if phase == 'connected':
        assert selected.__name__ == 'NativeTask'
        assert selected.__module__ == binding.__module__.removesuffix('.episode') + '.task'
    goal = runtime.EpisodeGoal.root(objective='Preserve the assigned native operation and its original returned outcome',
        result_contract={'role': context.role})
    request = runtime.EpisodeRequest(goal, runtime.Record({'scope': runtime._plain(context.scope),
        'initial_report': {}, 'episode_assignment': runtime._plain(context.assignment)}), None)
    # This port isolates identity allocation, not __init__. The actual selected
    # constructor is called, with its original request and all initial fields.
    workflow = SimpleNamespace(context=object(), grains={context.role: object()}, store=case.store,
        journal=case.journal, run_id=case.run_id, episode_bindings=case.registry,
        job_episodes=None, execution_binding=None, inprocess_replay=None,
        wait_inputs_version=None, completed_action_inputs_version=None,
        binding_context=lambda source: context,
        specialist=lambda source: case.registry.for_path(source.path))
    with patch.object(runtime.Episode, 'identity', lambda *args, **kwargs:
            SimpleNamespace(episode_id=context.episode_id)):
        task = selected(workflow, context.path, request, runtime._plain(context.scope))
    assert task.episode_id == context.episode_id and task.calls == 0
    assert task.last_outcome is task.last_outcome_index is task.feedback is None
    return task, workflow

def returned_actions(case, task, workflow):
    """Controlled returned outcomes; actual execution identity/persistence/replay."""
    rows, acquired, received, projected = [], [], [], []
    async def score(source, index, result): return result
    workflow.automatic_score_updates = score
    workflow.receive_native_outcome = lambda *args: None
    workflow.receive_outcome = lambda source, selection, result, index: received.append((index, deepcopy(result)))
    def credit(source):
        projected.append(source.episode_id)
        return {'credit': 0.0}
    workflow.source_credit_view = credit
    workflow.controller_value = lambda source, index, value: {'index': index, 'credit': value}
    for index, status in enumerate(('completed', 'partial', 'invalid', 'failed', 'unavailable')):
        selection = {'kind': 'tool', 'tool': 'controlled.returned_native_outcome', 'arguments': {'case': status}}
        outcome = {'status': status, 'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': None if status in {'completed', 'partial'} else {'category': 'controlled_return', 'code': status}}
        async def execute(source, name, arguments, **kwargs):
            assert name == selection['tool'] and arguments == selection['arguments']
            acquired.append(kwargs['operation_key']); return deepcopy(outcome)
        workflow.execute = execute
        before = (len(acquired), len(received), len(projected))
        value = asyncio.run(task.execute(deepcopy(selection), index))
        assert value == {'index': index, 'credit': 0.0}
        persisted = case.journal.row('runtime_actions', task.episode_id, index)
        assert json.loads(persisted['action']) == selection
        assert json.loads(persisted['result']) == outcome and persisted['credit'] == 0.0
        assert acquired[-1] == f'{case.run_id}:{task.episode_id}:{index}'
        assert tuple(len(values) - count for values, count in zip((acquired, received, projected), before)) == (1, 1, 1)
        first_counts = (len(acquired), len(received), len(projected))
        assert asyncio.run(task.execute(deepcopy(selection), index)) == value
        assert (len(acquired), len(received), len(projected)) == first_counts
        changed = observe(lambda: asyncio.run(task.execute({**selection, 'arguments': {'changed': True}}, index)))
        assert changed['status'] == 'raised' and changed['message'] == 'reconstructed selected work changed'
        rows.append({'selection': selection, 'returned': outcome, 'controller_input': value,
            'operation_key': acquired[-1], 'persisted_action': json.loads(persisted['action']),
            'persisted_outcome': json.loads(persisted['result']), 'persisted_credit': persisted['credit'],
            'acquisitions': 1, 'received_observations': 1, 'projections': 1,
            'replay_additional_acquisitions': 0, 'changed_selection': changed})
    return rows

def returned_waits(case, task, workflow):
    """Actual Task wait branch and persisted replay; controlled wait callback."""
    runtime = module('runtime')
    rows = []
    workflow.source_credit_view = forbidden
    workflow.automatic_score_updates = forbidden
    workflow.execute = forbidden
    for offset, kind in enumerate(('completed', 'partial', 'invalid', 'failed', 'unavailable', 'target_error'), 5):
        calls, received, native, credit_reads = [], [], [], []
        condition = {'controlled_selected_wait_case': kind}
        selection = {'kind': 'wait', 'condition': condition}
        outcome = {'status': kind, 'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'controlled_wait_return', 'code': kind}}
        async def wait(source, selected, index):
            assert source is task and selected == condition and index == offset
            calls.append({'episode_id': source.episode_id, 'condition': deepcopy(selected), 'index': index})
            if kind == 'target_error':
                raise runtime.EventTargetError('wait_target_unavailable',
                    affected_refs=[task.episode_id], detail='controlled_selected_wait_unavailable')
            return deepcopy(outcome)
        workflow.perform_selected_wait = wait
        workflow.receive_outcome = lambda source, selected, result, index: received.append(index)
        workflow.receive_native_outcome = lambda source, result, index: native.append(index)
        def last_credit(source):
            credit_reads.append(source.episode_id)
            return runtime.Workflow.last_observed_credit(workflow, source)
        workflow.last_observed_credit = last_credit
        first = observe(lambda: asyncio.run(task.execute(deepcopy(selection), offset)))
        saved = dict(case.journal.row('runtime_actions', task.episode_id, offset))
        assert json.loads(saved['action']) == selection
        expected = outcome if kind != 'target_error' else {
            'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'status': 'failed', 'category': 'wait_target', 'code': 'wait_target_unavailable',
                'affected_refs': [task.episode_id], 'detail': 'controlled_selected_wait_unavailable'}}
        assert json.loads(saved['result']) == expected
        observed = kind in ('completed', 'partial')
        if observed:
            assert first == {'status': 'returned', 'value': {'index': offset, 'credit': 0}}
            assert saved['credit'] == 0 and received == [offset] and credit_reads == [task.episode_id]
        else:
            assert first['status'] == 'raised' and first['type'] == PREFIX + 'runtime.ActionFailure'
            assert json.loads(first['message']) == expected['feedback']
            assert saved['credit'] is None and not received and not credit_reads
        assert len(calls) == 1 and native == [offset]
        replay = observe(lambda: asyncio.run(task.execute(deepcopy(selection), offset)))
        assert {key: value for key, value in replay.items() if key != 'traceback'} == {
            key: value for key, value in first.items() if key != 'traceback'}
        assert len(calls) == 1 and native == [offset, offset]
        assert received == ([offset] if observed else []) and len(credit_reads) == int(observed)
        assert dict(case.journal.row('runtime_actions', task.episode_id, offset)) == saved
        assert task.last_outcome == expected and task.last_outcome_index == offset
        rows.append({'case': kind, 'selection': selection, 'actual_wait_callback_calls': calls,
            'persisted_action': saved, 'first': first, 'replay': replay,
            'received_observations': len(received), 'native_receipt_calls_including_replay': len(native),
            'actual_last_observed_credit_reads': len(credit_reads), 'additional_replay_acquisitions': 0,
            'original_wait_repair_exception_preserved': not observed})
    return rows


def request_and_callback_boundaries(case, binding, context, parent_home, task, workflow):
    """Actual request utilities and explicit custom-service dispatch ports."""
    runtime = module('runtime')
    parent = case.parents[parent_home]
    launch, = [value for value in case.contexts if value.path == parent.path + (('launch', 'launch'),)]
    role = context.role
    request_rows = {
        'assignment_schema': observe(lambda: binding.assignment_schema(role)),
        'super_assignment_schema': observe(lambda: super(type(binding), binding).assignment_schema(role)),
        'parent_selected_schema': observe(lambda: binding.child_assignment_schema(launch, role)),
        'prepare_actual_or_missing_assignment': observe(lambda: binding.prepare_assignment(launch, role,
            runtime._plain(context.assignment), runtime._plain(context.scope),
            case.run_id + ':' + launch.episode_id + ':controlled_native_admission')),
        'default_foreign_schema': observe(lambda: binding.assignment_schema('results')),
    }
    assert request_rows['default_foreign_schema']['status'] == 'raised'
    assert request_rows['default_foreign_schema']['message'] == 'unknown_execution_episode_role'
    assert {key: value for key, value in request_rows['assignment_schema'].items() if key != 'traceback'} == {
        key: value for key, value in request_rows['super_assignment_schema'].items() if key != 'traceback'}
    credit_calls = []
    with patch.object(binding, 'credit_kind', lambda selected: credit_calls.append(selected) or 'operational'):
        request_rows['custom_credit_foreign_schema'] = observe(lambda: binding.assignment_schema('results'))
    assert credit_calls == ['results']
    request_rows['custom_credit_kind_calls'] = credit_calls
    callbacks = []
    marker = {'controlled_instruction_context': context.episode_id}
    def callback(source, value):
        assert source is task and value is marker
        callbacks.append('called'); return 'controlled_custom_instructions'
    class Spoof:
        def __init__(self):
            self.__func__ = module('episode_services').WorkflowServices.instructions
            self.__self__ = None
        def __call__(self, source, value): return callback(source, value)
    class CustomServices:
        def instructions(self, source, value): return callback(source, value)
    def raising(source, value):
        assert source is task and value is marker
        raise ValueError('controlled_custom_instruction_failure')
    custom = []
    for name, value in (('callable', callback), ('spoofed_default_metadata', Spoof()),
            ('custom_bound_method', CustomServices().instructions), ('custom_exception', raising)):
        workflow.services = SimpleNamespace(instructions=value)
        count = len(callbacks)
        result = observe(lambda: task.instructions(marker))
        if name == 'custom_exception':
            assert result['status'] == 'raised' and result['message'] == 'controlled_custom_instruction_failure'
            assert len(callbacks) == count
        else:
            assert result == {'status': 'returned', 'value': 'controlled_custom_instructions'}
            assert len(callbacks) == count + 1
        custom.append({'case': name, 'result': result, 'exact_original_operands': True})
    return {'requests': request_rows, 'custom_instruction_dispatch': custom}


def run(directory, phase):
    # This required helper runs only after promotion to own-axis tests.
    root = Path(__file__).resolve().parents[5]
    directory = directory.absolute()
    if any(path.is_symlink() for path in (directory, *directory.parents)):
        raise ValueError('probe_output_symlink_component')
    directory = directory.resolve()
    if directory == root / 'runs' or not directory.is_relative_to(root / 'runs'):
        raise ValueError('fresh_probe_output_under_runs_required')
    directory.mkdir(parents=True, exist_ok=False)
    before = source_hashes()
    fixture = module('tests/test_information_connected')
    case = fixture.InformationCase(directory / 'case', partial=False, connect=True)
    rows = []
    try:
        roles = ('launch_api', 'launch_local', 'launch_hpc') if AXIS == 'a107' else ('launch_local', 'launch_hpc')
        for parent in PARENTS:
            for role in roles:
                binding = case.execution[parent][role]
                original = case.parents[parent]
                path = original.path + (('launch', 'native-probe-launch'), (role, 'native-probe-' + role))
                # Only the four original HPC plans already produced by this
                # fixture supply genuine admitted native scientific operands.
                supported = role == 'launch_hpc' and parent in case.hpc_plans
                assignment = deepcopy(case.hpc_plans[parent]['practical_assignment']) if supported else {}
                context = case.context(path, assignment)
                assert case.registry.for_path(path) is binding
                task, workflow = construct(case, binding, context, phase)
                runtime = module('runtime')
                job_contexts = []
                for provider in (None, SimpleNamespace(roles=(role,)), SimpleNamespace(roles=('unrelated_role',))):
                    workflow.job_episodes = provider
                    job_contexts.append({'provider_roles': None if provider is None else list(provider.roles),
                        'is_job_source': runtime.Workflow.is_job_source(workflow, task),
                        'is_scientific_source': runtime.Workflow.is_scientific_source(workflow, task)})
                assert [row['is_job_source'] for row in job_contexts] == [False, True, False]
                assert [row['is_scientific_source'] for row in job_contexts] == [False, False, False]
                workflow.job_episodes = None
                boundaries = {
                    'permitted_common_actions': observe(lambda: list(binding.permitted_common_actions(context))),
                    'credit_kind': observe(lambda: binding.credit_kind(role)),
                    'child_roles': observe(lambda: list(binding.child_roles(role))),
                    'instructions': observe(lambda: binding.instructions(context)),
                    'decision_context': observe(lambda: binding.decision_context(context, {})),
                    'credit_view': observe(lambda: binding.credit_view(context, None)),
                    'practical_estimator': observe(lambda: binding.practical_estimator(context).as_record()),
                    'yield_controller': observe(lambda: binding.yield_controller(
                        context, 0.0, 'native-boundary-probe-original-epoch').state().as_record()),
                }
                actions = returned_actions(case, task, workflow)
                waits = returned_waits(case, task, workflow)
                request_callbacks = request_and_callback_boundaries(case, binding, context, parent, task, workflow)
                rows.append({'binding_path': binding.binding_path, 'role': role, 'context': context.as_record(),
                    'descriptor': binding.as_record(), 'task_class': type(task).__module__ + '.' + type(task).__qualname__,
                    'operand_scope': 'original_information_fixture_hpc_plan' if supported else 'explicit_missing_genuine_assignment',
                    'boundaries': boundaries, 'job_provider_contexts': job_contexts,
                    'returned_action_cases': actions, 'selected_wait_cases': waits,
                    'request_and_custom_callback_boundaries': request_callbacks})
                (directory / 'partial-observations.json').write_text(json.dumps(rows, indent=2, sort_keys=True) + '\n')
        assert len(rows) == (18 if AXIS == 'a107' else 12)
    finally:
        case.close()
    after = source_hashes(); assert before == after
    record = {'version': 'native_task_boundary_observation_v3', 'axis': AXIS, 'phase': phase,
        'rows': rows, 'source_hashes': before, 'source_unchanged': True,
        'controlled_ports': ['Episode.identity', 'constructed root goal and request envelope',
            'explicit probe epoch', 'job provider role inventory', 'returned tool outcome',
            'receive_native_outcome', 'receive_outcome', 'automatic_score_updates', 'zero projection', 'controller envelope',
            'selected wait callback and condition', 'custom credit-kind override', 'custom instruction service callbacks'],
        'no_native_or_network': True, 'application_ready': False,
        'unproven': ['Workflow.build admission', 'actual native action acquisition', 'real progress/grading',
            'whole iterator', 'genuine API/local/root-native operands', 'durable saved task restoration',
            'configured private yield controller records and replay', 'actual durable external wait and owned-child wait',
            'default full instruction composer with genuine configured context']}
    (directory / 'observations.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('phase', choices=['baseline', 'connected'])
    parser.add_argument('output', type=Path); args = parser.parse_args()
    with patch('subprocess.Popen', forbidden), patch('socket.socket.connect', forbidden), patch('socket.socket.connect_ex', forbidden):
        run(args.output, args.phase)
