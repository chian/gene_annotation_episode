"""Local routing/ownership checks with a controlled native backend.

The real fluorescence reservation and validators are used. Software pins and
supplied inputs are declared test fixtures; no installed producer, scientific
calculation, native subprocess or complete Workflow is claimed by these tests.
"""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import base64

import pytest

from gene_annotation_episode import native_fluorescence_local as fluorescence
from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.fluorescence_execution_common import canonical, digest, identity
from gene_annotation_episode.native_fluorescence_contracts import (
    OPERATIONS, POLICY, fluorescence_environment, fluorescence_output_files,
    requested_job_from_fluorescence,
)
from gene_annotation_episode.native_fluorescence_storage import immutable_json, read_json
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from test_native_fluorescence_contracts import event_input, job


def assignment_and_configuration(directory, *, operation=OPERATIONS[0], parsers=('csv',)):
    inputs = [event_input(directory / 'inputs', index=i, parser=parser)
        for i, parser in enumerate(parsers)]
    selected = job(directory / 'inputs', inputs=inputs, operation=operation)
    workspace = directory / 'workspace'
    workspace.mkdir(parents=True, exist_ok=True)
    request = requested_job_from_fluorescence(selected, environment=fluorescence_environment(
        selected['software'], attempt_directory=str(workspace / 'caller-temporaries')))
    assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'supplied-event-job',
        'resource_kind': 'local', 'resource_id': 'caller-selected-local', 'workspace': str(workspace),
        'endpoint': 'usable_handoff', 'requested_job': request,
        'progress_requirements': [{'key': 'handoff', 'credit': 1,
            'predicate': {'kind': 'requested_job_handoff'}}], 'completion_keys': ['handoff'],
        'initial_context': {'revision': 0, 'cwd': str(workspace),
            'environment': {'UNRELATED_PREPARATION_ENV': 'must-not-substitute'}},
        'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}
    configuration = {'kind': 'local', 'workspace': str(workspace), 'policy': deepcopy(POLICY),
        'native_fluorescence': [{'operation': operation, 'mode': selected['mode'],
            'parsers': list(dict.fromkeys(parsers)), 'software': deepcopy(selected['software'])}]}
    return assignment, configuration


class SelectedState:
    """Only the practical state interface used by original-job routing."""
    run_id, episode_id = 'routing-run', 'routing-episode'

    def __init__(self, assignment, operation_key='selected-start'):
        self.assignment, self.saved = assignment, []
        self.select(operation_key)

    def select(self, operation_key):
        self.pending = {'operation_key': operation_key, 'tool_name': 'practical.job.start',
            'run_id': self.run_id, 'episode_id': self.episode_id,
            'assignment_sha256': digest(self.assignment)}

    @contextmanager
    def _locked(self):
        yield

    def _load(self):
        return None, None, None, None, self.pending

    def context(self):
        return deepcopy(self.assignment['initial_context'])

    def receipts(self):
        return deepcopy(self.saved)

    def remember(self, outcome):
        self.saved.append({'outcome': deepcopy(outcome)})


def native_view(*, state='running', terminal=False, returncode=None, elapsed=1.25, killed=False):
    return {'version': native.VERSION, 'state': state, 'terminal': terminal,
        'quiescent': terminal, 'metadata': {'policy': deepcopy(POLICY),
            'native_returncode': returncode, 'elapsed_seconds': elapsed,
            'duration_measure': 'systemd_service_wall_seconds',
            'service_exit': {'EXIT_CODE': 'killed' if killed else 'exited'} if terminal else None},
        'native_receipt': None, 'files': {}}


@pytest.fixture
def backend(monkeypatch):
    calls = {'prepare': [], 'start': [], 'resume': [], 'status': []}
    views = {}

    def reserve(command, *, cwd, policy, handle_path, env):
        root = Path(cwd)
        original = read_json(root / 'fluorescence-plan.json')
        assert policy.to_dict() == POLICY
        assert original['identity']['execution_id'] == str(handle_path)
        assert original['requested_job']['native_fluorescence']['operation'] in OPERATIONS
        paths = {key: str(root / ('fixture.' + key))
            for key in ('request', 'ready', 'release', 'status', 'result', 'launcher')}
        request = fluorescence.fluorescence_native_request(original, paths)
        assert request['command'] == command and request['env'] == env
        immutable_json(paths['request'], request)
        for role in ('stdout', 'stderr'):
            (root / (role + '.log')).write_bytes(b'')
        immutable_json(handle_path, {'version': native.VERSION, 'stage': 'prepared',
            'command': command, 'cwd': str(root), 'metadata': {'policy': policy.to_dict()},
            'paths': paths, 'stdout': str(root / 'stdout.log'), 'stderr': str(root / 'stderr.log'),
            'request_sha256': identity(Path(paths['request']).read_bytes(), format='json')['sha256']})
        calls['prepare'].append(str(handle_path))
        views[str(handle_path)] = native_view()
        return native.NativeJobHandle(Path(handle_path))

    def released(handle, category):
        calls[category].append(str(handle.path))
        body = handle.read()
        body['stage'] = 'released'
        handle.path.write_bytes(canonical(body) + b'\n')
        return handle

    def observe(handle):
        calls['status'].append(str(handle.path))
        return deepcopy(views[str(handle.path)])

    monkeypatch.setattr(native, 'prepare_job', reserve)
    monkeypatch.setattr(native, 'start_prepared', lambda handle: released(handle, 'start'))
    monkeypatch.setattr(native, 'resume_start', lambda handle: released(handle, 'resume'))
    monkeypatch.setattr(native, 'status', observe)
    for name in ('wait_job', 'collect', 'cancel', 'start_job'):
        monkeypatch.setattr(native, name, lambda *args, **kwargs: pytest.fail('unexpected native operation'))
    return SimpleNamespace(calls=calls, views=views)


def start(directory, backend, *, operation=OPERATIONS[0]):
    assignment, configuration = assignment_and_configuration(directory, operation=operation)
    operations, state = LocalPracticalOperations(configuration), SelectedState(assignment)
    outcome, updated = operations._execute(state, 'practical.job.start', {}, 'selected-start')
    assert updated is None
    state.remember(outcome)
    execution = outcome['facts']['requested_job']['execution_id']
    return operations, state, execution, outcome


def target_identity(state, original):
    owner = original['identity']
    return {'run_id': state.run_id, 'origin_episode_id': state.episode_id,
        'attempt_id': owner['attempt_id'], 'requested_job_sha256': owner['requested_job_sha256'],
        'original_operation_key': owner['operation_key'], 'resource_id': owner['resource_id']}


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('parser', ['csv', 'table_snapshot', 'fcs_encoded'])
def test_exact_configured_operation_and_parser_are_validated(tmp_path, operation, parser):
    assignment, configuration = assignment_and_configuration(tmp_path, operation=operation, parsers=(parser,))
    before = deepcopy(assignment)
    operations = LocalPracticalOperations(configuration)
    assert operations.validate_assignment(assignment) is None
    assert assignment == before
    assert operations.configuration == configuration
    assert operations.policy.to_dict() == POLICY


@pytest.mark.parametrize('change', ['empty_parsers', 'duplicate_parsers', 'unknown_parser', 'missing_flowio'])
def test_invalid_capability_configuration_is_rejected(tmp_path, change):
    _, configuration = assignment_and_configuration(tmp_path)
    binding = configuration['native_fluorescence'][0]
    binding['parsers'] = {'empty_parsers': [], 'duplicate_parsers': ['csv', 'csv'],
        'unknown_parser': ['unknown'], 'missing_flowio': ['fcs_encoded']}[change]
    with pytest.raises(ValueError, match='fluorescence'):
        LocalPracticalOperations(configuration)


@pytest.mark.parametrize('mismatch', ['operation', 'software', 'unbound'])
def test_declared_job_does_not_substitute_a_configured_capability(tmp_path, mismatch):
    assignment, configuration = assignment_and_configuration(tmp_path)
    if mismatch == 'operation':
        configuration['native_fluorescence'][0]['operation'] = OPERATIONS[1]
    elif mismatch == 'software':
        configuration['native_fluorescence'][0]['software']['python_version'] = 'another installation'
    else:
        configuration['native_fluorescence'] = []
    with pytest.raises(ValueError, match='operation_mode_software_not_bound'):
        LocalPracticalOperations(configuration).validate_assignment(assignment)


def test_all_input_parsers_must_belong_to_one_matching_binding(tmp_path):
    assignment, configuration = assignment_and_configuration(tmp_path, parsers=('csv', 'table_snapshot'))
    complete = deepcopy(configuration['native_fluorescence'][0])
    csv_only, table_only = deepcopy(complete), deepcopy(complete)
    csv_only['parsers'], table_only['parsers'] = ['csv'], ['table_snapshot']
    configuration['native_fluorescence'] = [csv_only, table_only]
    with pytest.raises(ValueError, match='parser_not_bound'):
        LocalPracticalOperations(configuration).validate_assignment(assignment)
    table_only['operation'] = OPERATIONS[1]
    with pytest.raises(ValueError, match='parser_not_bound'):
        LocalPracticalOperations(configuration).validate_assignment(assignment)
    configuration['native_fluorescence'].append(complete)
    LocalPracticalOperations(configuration).validate_assignment(assignment)


@pytest.mark.parametrize('mismatch,code', [
    ('resource_kind', 'local_resource_required'), ('resource_id', 'resource_identity_required'),
    ('workspace', 'outside_workspace'), ('constraint', 'allocation_constraint_mismatch'),
    ('allocation', 'allocation_constraint_mismatch'), ('policy', 'local_policy_conflict'),
])
def test_original_resource_workspace_and_caller_allocation_are_not_replaced(tmp_path, mismatch, code):
    assignment, configuration = assignment_and_configuration(tmp_path)
    if mismatch == 'resource_kind':
        assignment['resource_kind'] = 'hpc'
    elif mismatch == 'resource_id':
        assignment['resource_id'] = ''
    elif mismatch == 'workspace':
        assignment['workspace'] = str(tmp_path / 'elsewhere')
    elif mismatch == 'constraint':
        assignment['constraints']['scratch_bytes'] = POLICY['scratch_bytes'] - 1
    elif mismatch == 'allocation':
        assignment['constraints']['allocation']['memory_bytes'] -= 1
    else:
        configuration['policy']['wall_seconds'] = 5
    with pytest.raises(ValueError, match=code):
        LocalPracticalOperations(configuration).validate_assignment(assignment)


@pytest.mark.parametrize('operation', OPERATIONS)
def test_selected_start_uses_original_fluorescence_preparer_and_request(tmp_path, backend, operation):
    operations, state, execution, outcome = start(tmp_path, backend, operation=operation)
    original = operations._fluorescence_plan(state.assignment, execution,
        run_id=state.run_id, origin_episode_id=state.episode_id)
    request = state.assignment['requested_job']
    assert original['requested_job'] == request
    assert original['identity']['resource_id'] == 'caller-selected-local'
    assert original['identity']['assignment_sha256'] == digest(state.assignment)
    assert original['identity']['operation_key'] == 'selected-start'
    assert original['policy'] == state.assignment['constraints']['allocation'] == POLICY
    native_request = read_json(read_json(execution)['paths']['request'])
    assert native_request['env'] == fluorescence_environment(request['native_fluorescence']['software'],
        attempt_directory=original['attempt_directory'])
    assert 'UNRELATED_PREPARATION_ENV' not in native_request['env']
    expected_outputs = sorted(str(Path(original['attempt_directory']) / row['relative_path'])
        for row in fluorescence_output_files(request['native_fluorescence']))
    fact = outcome['facts']['requested_job']
    assert fact['argv'] == request['argv'] and fact['environment'] == request['environment']
    assert fact['requested_job_sha256'] == digest(request)
    assert fact['output_paths'] == expected_outputs
    assert fact['handoff']['execution_id'] == execution
    assert outcome['native_outcome']['attempt_id'] == digest('selected-start')
    assert backend.calls['prepare'] == backend.calls['start'] == [execution]
    assert backend.calls['resume'] == []


@pytest.mark.parametrize('stage,started,resumed', [('prepared', 1, 0), ('submitting', 0, 1), ('released', 0, 0)])
def test_pending_start_resumes_same_reservation_without_replacement(tmp_path, backend, stage, started, resumed):
    assignment, configuration = assignment_and_configuration(tmp_path)
    operations, state = LocalPracticalOperations(configuration), SelectedState(assignment)
    root = operations._action_directory(state, 'selected-start')
    handle = fluorescence.prepare_local_fluorescence(state, 'selected-start', root=root, policy=operations.policy)
    body = handle.read()
    body['stage'] = stage
    handle.path.write_bytes(canonical(body) + b'\n')
    original_request = Path(body['paths']['request']).read_bytes()
    original_plan = (root / 'fluorescence-plan.json').read_bytes()
    outcome, _ = operations._execute(state, 'practical.job.start', {}, 'selected-start')
    assert outcome['facts']['requested_job']['execution_id'] == str(handle.path)
    assert backend.calls['prepare'] == [str(handle.path)]
    assert len(backend.calls['start']) == started and len(backend.calls['resume']) == resumed
    assert Path(body['paths']['request']).read_bytes() == original_request
    assert (root / 'fluorescence-plan.json').read_bytes() == original_plan


@pytest.mark.parametrize('tool_name', ['practical.job.start', 'practical.job.status', 'practical.job.collect'])
def test_existing_selected_handle_is_observed_without_new_work(tmp_path, backend, tool_name):
    operations, state, execution, original_outcome = start(tmp_path, backend)
    before = Path(execution).read_bytes()
    (Path(execution).parent / 'stdout.log').write_bytes(b'actual fixture log\n')
    outcome, _ = operations._execute(state, tool_name, {}, 'later-selected-action')
    assert outcome['facts']['requested_job']['execution_id'] == execution
    assert outcome['native_outcome']['attempt_id'] == original_outcome['native_outcome']['attempt_id']
    assert outcome['native_outcome']['attempt_operation_key'] == 'selected-start'
    assert backend.calls['prepare'] == backend.calls['start'] == [execution]
    assert backend.calls['resume'] == [] and Path(execution).read_bytes() == before
    if tool_name != 'practical.job.start':
        logs = outcome['native_outcome']['observed_logs']
        assert base64.b64decode(next(row for row in logs if row['role'] == 'stdout')['bytes_base64']) == b'actual fixture log\n'
        assert all(not row['writer_closed'] for row in outcome['native_outcome']['observed_outputs'])
    assert set(outcome['facts']) == {'requested_job', 'paths'}


@pytest.mark.parametrize('tool_name', ['practical.job.start', 'practical.job.status', 'practical.job.collect', 'retry'])
def test_existing_handle_with_wrong_owner_is_rejected_before_native_observation(tmp_path, backend, tool_name):
    operations, state, execution, _ = start(tmp_path, backend)
    state.run_id = 'unrelated-owner'
    before = deepcopy(backend.calls)
    arguments = {'retry_failed_execution_id': execution} if tool_name == 'retry' else {}
    with pytest.raises(ValueError, match='original_attempt_mismatch'):
        operations._execute(state, 'practical.job.start' if tool_name == 'retry' else tool_name,
            arguments, 'another-action')
    assert backend.calls == before


@pytest.mark.parametrize('field', ['run_id', 'origin_episode_id', 'attempt_id', 'requested_job_sha256'])
def test_plan_checks_each_supplied_original_identity(tmp_path, backend, field):
    operations, state, execution, _ = start(tmp_path, backend)
    with pytest.raises(ValueError, match='original_attempt_mismatch'):
        operations._fluorescence_plan(state.assignment, execution, **{field: 'different'})


@pytest.mark.parametrize('method', ['observe_execution', 'read_output'])
@pytest.mark.parametrize('field', ['run_id', 'origin_episode_id', 'attempt_id', 'requested_job_sha256',
    'original_operation_key', 'resource_id'])
def test_observation_and_output_reads_reject_every_mismatched_owner_field(tmp_path, backend, method, field):
    operations, state, execution, _ = start(tmp_path, backend)
    original = operations._fluorescence_plan(state.assignment, execution)
    expected = target_identity(state, original)
    expected[field] = 'unrelated'
    arguments = {} if method == 'observe_execution' else {'path': str(Path(execution).parent / 'stdout.log'),
        'offset': 0, 'limit': 16}
    before = deepcopy(backend.calls)
    with pytest.raises(ValueError, match='original_attempt_mismatch'):
        getattr(operations, method)(state.assignment, execution, **expected, **arguments)
    assert backend.calls == before


@pytest.mark.parametrize('case', ['running', 'unknown_returncode', 'boolean_returncode', 'killed', 'successful', 'wrong_handle'])
def test_retry_requires_original_confirmed_failed_attempt(tmp_path, backend, case):
    operations, state, execution, first = start(tmp_path, backend)
    selected = native_view(state='returned', terminal=True, returncode=2)
    requested_handle = execution
    if case == 'running':
        selected = native_view()
    elif case == 'unknown_returncode':
        selected['metadata']['native_returncode'] = None
    elif case == 'boolean_returncode':
        selected['metadata']['native_returncode'] = True
    elif case == 'killed':
        selected['metadata']['service_exit']['EXIT_CODE'] = 'killed'
    elif case == 'successful':
        selected['metadata']['native_returncode'] = 0
    else:
        requested_handle = str(tmp_path / 'another-native.json')
    backend.views[execution] = selected
    state.select('explicit-retry')
    outcome, _ = operations._execute(state, 'practical.job.start',
        {'retry_failed_execution_id': requested_handle}, 'explicit-retry')
    assert outcome['native_outcome']['failure']['code'] == 'practical_retry_requires_original_failed_execution'
    assert outcome['native_outcome']['attempt_id'] == first['native_outcome']['attempt_id']
    assert outcome['native_outcome']['attempt_operation_key'] == 'selected-start'
    assert outcome['facts']['requested_job']['execution_id'] == execution
    assert backend.calls['prepare'] == backend.calls['start'] == [execution]


def test_explicit_confirmed_failure_retry_gets_only_its_selected_new_attempt(tmp_path, backend):
    operations, state, execution, first = start(tmp_path, backend)
    backend.views[execution] = native_view(state='returned', terminal=True, returncode=2)
    old_bytes = Path(execution).read_bytes()
    state.select('explicit-retry')
    outcome, _ = operations._execute(state, 'practical.job.start',
        {'retry_failed_execution_id': execution}, 'explicit-retry')
    selected_execution = outcome['facts']['requested_job']['execution_id']
    assert selected_execution != execution
    assert outcome['native_outcome']['attempt_id'] == digest('explicit-retry')
    assert outcome['native_outcome']['attempt_operation_key'] == 'explicit-retry'
    assert backend.calls['prepare'] == backend.calls['start'] == [execution, selected_execution]
    assert Path(execution).read_bytes() == old_bytes
    assert state.receipts() == [{'outcome': first}]


@pytest.mark.parametrize('native_state,terminal,rc,expected,failure', [
    ('prepared', False, None, 'submitted', None), ('starting', False, None, 'submitted', None),
    ('running', False, None, 'running', None), ('execution_unknown', False, None, 'unknown', None),
    ('returned', True, 0, 'completed', None), ('returned', True, 2, 'failed', 'native_nonzero_returncode'),
    ('returned', True, None, 'failed', 'native_returncode_unavailable'),
])
def test_native_observation_keeps_actual_state_duration_and_manifest_availability(tmp_path, backend,
        native_state, terminal, rc, expected, failure):
    operations, state, execution, _ = start(tmp_path, backend)
    original = operations._fluorescence_plan(state.assignment, execution)
    backend.views[execution] = native_view(state=native_state, terminal=terminal, returncode=rc)
    stdout = Path(execution).parent / 'stdout.log'
    stdout.write_bytes(b'123456789')
    observation = operations.observe_execution(state.assignment, execution,
        **target_identity(state, original), log_window_bytes=3, log_roles=('stdout',))
    assert observation['state'] == expected and observation['failure_code'] == failure
    assert observation['result_available'] is False
    assert observation['measurements'] == ([{'measure': 'systemd_service_wall_seconds', 'seconds': 1.25}]
        if terminal else [])
    assert observation['logs'] == [{'role': 'stdout', 'path': str(stdout), 'offset': 6,
        'observed_size': 9, 'bytes_base64': base64.b64encode(b'789').decode('ascii')}]
    manifest = Path(original['attempt_directory']) / original['outputs'][-1]['relative_path']
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_bytes(b'file-availability fixture, not validated scientific data')
    second = operations.observe_execution(state.assignment, execution, **target_identity(state, original))
    assert second['result_available'] is True
    assert set(second) == {'observed_at', 'state', 'returncode', 'failure_code', 'result_available',
        'measurements', 'outputs', 'logs', 'provenance_refs', 'native'}
    assert backend.calls['prepare'] == [execution]


def test_output_read_uses_original_bounded_window_and_never_source_path(tmp_path, backend):
    operations, state, execution, _ = start(tmp_path, backend)
    original = operations._fluorescence_plan(state.assignment, execution)
    output = Path(original['attempt_directory']) / original['outputs'][0]['relative_path']
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b'\x00ABC\xffDEFG')
    before = deepcopy(backend.calls)
    result = operations.read_output(state.assignment, execution, path=output, offset=2, limit=4,
        **target_identity(state, original))
    assert result == {'path': str(output), 'offset': 2, 'returned_bytes': 4, 'size_bytes': 9,
        'bytes_base64': base64.b64encode(b'BC\xffD').decode('ascii'), 'text_utf8': 'BC\ufffdD'}
    source = state.assignment['requested_job']['native_fluorescence']['inputs'][0]['path']
    with pytest.raises(ValueError, match='original_output_path_required'):
        operations.read_output(state.assignment, execution, path=source, offset=0, limit=4)
    with pytest.raises(ValueError, match='bounded_native_output_window_required'):
        operations.read_output(state.assignment, execution, path=output, offset=0, limit=1024*1024+1)
    assert backend.calls == before
