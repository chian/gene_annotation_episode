"""Selected practical ports with real bounded native jobs on synthetic structures.

This exercises the existing resource binding, receipts and monitoring reader;
it does not claim full scientific episode construction or result delivery.
"""
import asyncio
import base64
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_progress import ExecutionProgressProvider, describe_execution_target
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_protein_structure_contracts import (
    BUNDLE_FILENAME, POLICY, RUN_PLAN_FILENAME, requested_job_from_protein_structure,
)
from gene_annotation_episode.native_protein_structure_local import prepare_local_protein_structure
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_execution_records import ASSIGNMENT_SCHEMA, validate_assignment
from gene_annotation_episode.practical_resource_episodes import PracticalResourceEpisodes
from gene_annotation_episode.state import Store

_f = import_module('verification.tool_graders_protein_structure_execution_2026-10-27_390.fixture_helpers')
RUN, EPISODE, RESOURCE = 'protein-local-run', 'protein-local-child', 'selected-local'
FIELDS = ['execution_status', 'measurements', 'log_windows', 'result_available']


def selected_job(directory, kind='inspect', mode=None):
    request, inputs = _f.requests(kind)
    if mode == 'evaluate_declared_transform_ca':
        request['parameters'].update(mode=mode, fit_selection=None, declared_transform={
            'version': 'protein_structure_transform_v1', 'direction': 'moving_to_fixed',
            'convention': 'row_vector_y_R_plus_t',
            'rotation': [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            'translation_A': [0.0, 0.0, 0.0],
            'fixed_selection': deepcopy(request['fixed_selection']),
            'moving_selection': deepcopy(request['moving_selection']), 'origin': 'supplied',
            'received_from': None})
    return requested_job_from_protein_structure(_f.job(directory, request=request, inputs=inputs))


def configuration(directory, request):
    job = request['native_protein_structure']
    science = job['request']
    return {'kind': 'local', 'workspace': str(directory), 'policy': deepcopy(POLICY),
        'native_protein_structure': [{'operation': science['operation'],
            'scientific_mode': science['parameters']['mode'] if science['operation'] == 'compare' else None,
            'software': deepcopy(job['software'])}]}


def assignment(directory, request):
    # An intentionally absent, caller-declared output keeps this port harness
    # open across status/collect selections. No endpoint completion is claimed.
    return {'version': 'practical_assignment_v1', 'assignment_id': 'selected-protein',
        'resource_kind': 'local', 'resource_id': RESOURCE, 'workspace': str(directory),
        'endpoint': 'completed_job_outputs', 'requested_job': request,
        'progress_requirements': [{'key': 'outputs', 'credit': 1,
            'predicate': {'kind': 'requested_job_outputs', 'output_paths': [str(directory/'unrequested-output')]}}],
        'completion_keys': ['outputs'], 'initial_context': {'revision': 0, 'cwd': str(directory), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}


class Harness:
    def __init__(self, directory, *, kind='inspect', mode=None, generic=False):
        directory.mkdir(parents=True, exist_ok=True)
        self.directory = directory
        request = ({'argv': [sys.executable, '-B', '-c', 'print("ordinary local output")'], 'environment': {}}
            if generic else selected_job(directory, kind, mode))
        self.config = ({'kind': 'local', 'workspace': str(directory), 'policy': deepcopy(POLICY)}
            if generic else configuration(directory, request))
        self.assignment = assignment(directory, request)
        self.store = Store(directory/'store')
        self.store.create_problem(raw_sequence='MAGST', molecule='protein')
        self.scope = self.store.validate_scope()
        message = {'message': {'scope': self.scope, 'episode_assignment': self.assignment}}
        self.context = BindingContext(RUN, EPISODE, 'launch_local', (('launch_local', 'selected'),),
            self.scope, self.assignment, message)
        self.journal = Journal(self.store, RUN)
        with self.store.transaction():
            self.journal.save('runtime_episodes', {'episode_id': EPISODE,
                'path': canonical(plain(self.context.path)), 'request': canonical(message),
                'initial_credit': 0, 'state': 'running'})
        self.binding = PracticalResourceEpisodes(None, directory=directory/'runtime',
            resources={'local': self.config}, store=self.store)
        self.state = self.binding.initialize(self.context)
        self.progress = ExecutionProgressProvider(self.store, run_id=RUN, directory=directory/'monitor',
            resources={RESOURCE: self.config}, api_execution=None, log_window_bytes=37, log_roles=('stdout', 'stderr'))
        self.operations = self.progress.targets.operations[RESOURCE]
        self.next_index = 0

    def action(self, name, arguments=None, *, index=None):
        arguments = {} if arguments is None else arguments
        if index is None:
            index = self.next_index
            self.next_index += 1
            with self.store.transaction():
                self.journal.save('runtime_actions', {'episode_id': EPISODE, 'decision_index': index,
                    'action': canonical({'kind': 'tool', 'tool': name, 'arguments': arguments}),
                    'result': None, 'credit': None})
        key = f'{RUN}:{EPISODE}:{index}'
        result = asyncio.run(self.binding.execute(self.context, name, arguments, key))
        with self.store.transaction():
            self.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
                (canonical(result), RUN, EPISODE, index))
        assert result['status'] == 'completed', result
        return result

    def close(self):
        for path in self.directory.rglob('native.json'):
            handle = native.NativeJobHandle(path)
            if not native.status(handle)['quiescent']:
                native.cancel(handle)
        self.store.close()


@pytest.fixture
def harnesses():
    values = []
    def create(directory, **kwargs):
        h = Harness(directory, **kwargs)
        values.append(h)
        return h
    yield create
    for h in values:
        h.close()


def execution(result):
    return result['result']['outcome']['facts']['requested_job']['execution_id']


def identity(plan):
    owner = plan['identity']
    return {'run_id': owner['run_id'], 'origin_episode_id': owner['episode_id'],
        'original_operation_key': owner['operation_key'], 'attempt_id': owner['attempt_id'],
        'resource_id': owner['resource_id']}


def reserve(directory, *, kind='inspect', mode=None):
    request = selected_job(directory, kind, mode)
    value = assignment(directory, request)
    operations = LocalPracticalOperations(configuration(directory, request))
    state = SimpleNamespace(assignment=value, run_id=RUN, episode_id=EPISODE)
    key = f'{RUN}:{EPISODE}:0'
    root = directory/'.episode-operations'/digest({'run': RUN, 'episode': EPISODE})/digest(key)
    handle = prepare_local_protein_structure(state, key, root=root, policy=LocalJobPolicy(**POLICY))
    plan = operations._protein_plan(value, str(handle.path))
    return operations, state, handle, plan


@pytest.mark.parametrize('kind,mode', [('inspect', None), ('extract_sequence', None),
    ('compare', 'fit_then_evaluate_ca'), ('compare', 'evaluate_declared_transform_ca')])
def test_actual_selected_resource_start_status_collect_and_original_receipt_replay(tmp_path, harnesses, monkeypatch, kind, mode):
    h = harnesses(tmp_path, kind=kind, mode=mode)
    Draft202012Validator(ASSIGNMENT_SCHEMA).validate(h.assignment)
    assert validate_assignment(h.assignment) == h.assignment
    start = h.action('practical.job.start')
    handle = native.NativeJobHandle(Path(execution(start)))
    completed = native.wait_job(handle)
    assert completed.returncode == 0
    assert completed.metadata['policy'] == POLICY
    assert completed.metadata['verified_cgroup'] == {'memory_max': POLICY['memory_bytes'], 'memory_swap_max': 0,
        'runtime_max': 'infinity', 'kill_mode': 'control-group', 'oom_policy': 'kill'}
    plan = h.operations._protein_plan(h.assignment, str(handle.path), run_id=RUN, origin_episode_id=EPISODE)
    root = Path(plan['attempt_directory'])
    bundle_before = (root/BUNDLE_FILENAME).read_bytes()
    assert json.loads(bundle_before)['native_status'] == 'complete'
    for name in ('practical.job.status', 'practical.job.collect'):
        selected = h.action(name)
        fact = selected['result']['outcome']['facts']['requested_job']
        native_outcome = selected['result']['outcome']['native_outcome']
        assert fact['execution_id'] == str(handle.path)
        assert fact['output_paths'] == sorted([str(root/r['relative_path'])
            for r in h.assignment['requested_job']['native_protein_structure']['outputs']] + [str(root/BUNDLE_FILENAME)])
        assert native_outcome['attempt_id'] == plan['identity']['attempt_id']
        assert native_outcome['attempt_operation_key'] == start['result']['operation_key']
        assert set(native_outcome['observed_logs']) == {'stdout', 'stderr'}
        assert all(r['available'] and r['writer_closed'] for r in native_outcome['observed_outputs'])
        reference, = selected['record_refs']
        target = h.progress.targets.read_target(reference, h.scope)
        assert describe_execution_target(target) == {'resource_kind': 'local', 'service_or_program': 'protein_structure_python',
            'operation': kind, 'mode': mode, 'output_format': 'native_protein_structure_bundle_v1'}
        assert h.progress.targets._native_identity(target) == {k: v for k, v in identity(plan).items() if k != 'resource_id'}
    first_reference, = start['record_refs']
    snapshot = h.progress.observe(first_reference, FIELDS, h.scope, operation_key='selected-monitor')
    assert snapshot['execution_status']['native']['state'] == 'completed'
    assert snapshot['measurements'][0]['name'] == 'systemd_service_wall_seconds'
    assert len(snapshot['log_windows']) == 2
    assert all(len(h.store.get_artifact(w['artifact_ref'])) <= 37 for w in snapshot['log_windows'])
    target = h.progress.targets.read_target(first_reference, h.scope)
    read = h.progress.targets.read_file(target, path=str(root/'result.json'), offset=5, limit=19)
    assert base64.b64decode(read['bytes_base64']) == (root/'result.json').read_bytes()[5:24]
    result = json.loads((root/'result.json').read_bytes())
    if kind == 'inspect':
        assert result['inventory']['chains'][0]['atom_count'] == 4
    elif kind == 'extract_sequence':
        assert (root/'sequence.txt').read_bytes() == b'AGST'
    else:
        assert result['sheet']['native_baseline']['counts']['mapped_pair_count']['value'] == 4
        assert result['sheet']['native_baseline']['evaluation']['evaluation_rmsd']['value'] == pytest.approx(0, abs=1e-14)
    # Replay returns the exact saved receipt even after other actions. No native
    # launch, status, parser or filesystem artifact read is needed for replay.
    with monkeypatch.context() as patch:
        patch.setattr(native, 'status', lambda *a, **k: pytest.fail('replay polled'))
        patch.setattr(native, 'start_prepared', lambda *a, **k: pytest.fail('replay launched'))
        assert h.action('practical.job.start', index=0) == start
        assert h.progress.observe(first_reference, FIELDS, h.scope, operation_key='selected-monitor') == snapshot
    assert (root/BUNDLE_FILENAME).read_bytes() == bundle_before
    assert len(list(tmp_path.rglob('native.json'))) == 1


@pytest.mark.parametrize('mutation,code', [
    ('unbound_operation', 'operation_mode_software_not_bound'), ('unbound_mode', 'operation_mode_software_not_bound'),
    ('unbound_software', 'operation_mode_software_not_bound'), ('missing_identity', 'resource_identity_required'),
    ('hpc', 'local_resource_required'), ('workspace', 'outside_workspace'),
    ('memory', 'local_policy_conflict'), ('scratch', 'local_policy_conflict'), ('wall', 'local_policy_conflict'),
    ('allocation', 'allocation_constraint_mismatch'), ('explicit_memory', 'allocation_constraint_mismatch'),
    ('unsupported_constraint', 'unsupported_explicit_local_constraint'), ('argv', 'original_commission_mismatch')])
def test_exact_selected_operation_mode_software_and_allocation_rejection(tmp_path, mutation, code):
    request = selected_job(tmp_path, 'compare')
    value, config = assignment(tmp_path, request), configuration(tmp_path, request)
    if mutation == 'unbound_operation': config['native_protein_structure'][0].update(operation='inspect', scientific_mode=None)
    elif mutation == 'unbound_mode': config['native_protein_structure'][0]['scientific_mode'] = 'evaluate_declared_transform_ca'
    elif mutation == 'unbound_software': config['native_protein_structure'][0]['software']['python_sha256'] = '0'*64
    elif mutation == 'missing_identity': del value['resource_id']
    elif mutation == 'hpc': value['resource_kind'] = 'hpc'
    elif mutation == 'workspace': value['workspace'] = str(tmp_path.parent/'outside')
    elif mutation in {'memory', 'scratch', 'wall'}:
        config['policy'][{'memory': 'memory_bytes', 'scratch': 'scratch_bytes', 'wall': 'wall_seconds'}[mutation]] = 1
    elif mutation == 'allocation': value['constraints']['allocation']['memory_bytes'] -= 1
    elif mutation == 'explicit_memory': value['constraints']['memory_bytes'] = 1
    elif mutation == 'unsupported_constraint': value['constraints']['arbitrary'] = True
    else: value['requested_job']['argv'].append('--not-selected')
    with pytest.raises(ValueError, match=code):
        LocalPracticalOperations(config).validate_assignment(value)
    assert not (tmp_path/'.episode-operations').exists()


@pytest.mark.parametrize('binding', [[], [{'operation': 'inspect'}]])
def test_configuration_uses_exact_binding_validator(binding, tmp_path):
    with pytest.raises(ValueError):
        LocalPracticalOperations({'kind': 'local', 'workspace': str(tmp_path), 'policy': POLICY,
            'native_protein_structure': binding})


@pytest.mark.parametrize('key', ['run_id', 'origin_episode_id', 'original_operation_key', 'attempt_id', 'resource_id'])
def test_wrong_original_identity_rejected_before_native_observation_or_read(tmp_path, monkeypatch, key):
    operations, state, handle, plan = reserve(tmp_path)
    expected = identity(plan)
    expected[key] = 'other'
    monkeypatch.setattr(native, 'status', lambda *a, **k: pytest.fail('unqualified native status'))
    with pytest.raises(ValueError, match='original_commission_mismatch'):
        operations.observe_execution(state.assignment, str(handle.path), **expected)
    with pytest.raises(ValueError, match='original_commission_mismatch'):
        operations.read_output(state.assignment, str(handle.path), path=str(Path(plan['attempt_directory'])/'result.json'),
            offset=0, limit=1, **expected)


def test_native_output_paths_and_byte_windows_remain_selected(tmp_path, monkeypatch):
    operations, state, handle, plan = reserve(tmp_path, kind='extract_sequence')
    attempt = Path(plan['attempt_directory'])
    attempt.mkdir()
    raw = b'\xff\x00native\xfe\x00'
    (attempt/'result.json').write_bytes(raw)
    (attempt/'stdout.log').write_bytes(b'original output\xff')
    (attempt/'stderr.log').write_bytes(b'')
    (attempt/'sequence.txt').write_bytes(b'AGST')
    # Presence alone intentionally remains availability, never schema validation.
    (attempt/BUNDLE_FILENAME).write_bytes(b'invalid bundle bytes')
    view = native.status(handle)
    calls = []
    monkeypatch.setattr(native, 'status', lambda selected: calls.append(selected.path) or view)
    observed = operations.observe_execution(state.assignment, str(handle.path), log_window_bytes=6, **identity(plan))
    assert calls == [handle.path]
    assert observed['result_available'] and observed['measurements'] == []
    assert {r['role'] for r in observed['logs']} == {'stdout', 'stderr'}
    assert all(not r['writer_closed'] for r in observed['outputs'])
    assert base64.b64decode(observed['logs'][0]['bytes_base64']) == b'utput\xff'
    assert not any('bytes_base64' in r for r in observed['outputs'])
    read = operations.read_output(state.assignment, str(handle.path), path=str(attempt/'result.json'), offset=1, limit=4,
        **identity(plan))
    assert base64.b64decode(read['bytes_base64']) == raw[1:5]
    for path in (handle.path.parent/'stdout.log', handle.path.parent/RUN_PLAN_FILENAME, tmp_path/'arbitrary'):
        with pytest.raises(ValueError, match='original_output_path_required'):
            operations.read_output(state.assignment, str(handle.path), path=str(path), offset=0, limit=1, **identity(plan))
    for offset, limit in [(-1, 1), (True, 1), (0, 0), (0, 1024*1024+1)]:
        with pytest.raises(ValueError, match='bounded_native_output_window_required'):
            operations.read_output(state.assignment, str(handle.path), path=str(attempt/'result.json'), offset=offset, limit=limit)
    (attempt/'result.json').unlink()
    (attempt/'result.json').symlink_to(attempt/'stdout.log')
    with pytest.raises(ValueError, match='invalid_output_path'):
        operations.read_output(state.assignment, str(handle.path), path=str(attempt/'result.json'), offset=0, limit=1)


def test_original_request_and_native_handle_cannot_change(tmp_path, monkeypatch):
    operations, state, handle, plan = reserve(tmp_path)
    monkeypatch.setattr(native, 'status', lambda *a, **k: pytest.fail('changed request polled'))
    changed = deepcopy(state.assignment)
    changed['requested_job']['environment']['SELECTED_VALUE'] = 'different'
    with pytest.raises(ValueError, match='original_commission_mismatch'):
        operations.observe_execution(changed, str(handle.path))
    native_body = handle.read()
    native_body['command'] = ['/bin/false']
    handle.path.write_text(json.dumps(native_body))
    with pytest.raises(ValueError, match='original_commission_mismatch'):
        operations.observe_execution(state.assignment, str(handle.path))


def test_injected_prepared_and_submitting_recovery_reuses_original_reservation(tmp_path, monkeypatch):
    operations, state, handle, plan = reserve(tmp_path)
    calls = []
    monkeypatch.setattr(native, 'start_prepared', lambda selected: calls.append(('start', selected.path)))
    monkeypatch.setattr(native, 'resume_start', lambda selected: calls.append(('resume', selected.path)))
    request = state.assignment['requested_job']
    for stage, expected in [('prepared', 'start'), ('submitting', 'resume')]:
        body = handle.read()
        body['stage'] = stage  # Deliberately injected lifecycle state, no native run.
        handle.path.write_text(json.dumps(body))
        reused = operations._handle(state, plan['identity']['operation_key'], request['argv'],
            cwd=tmp_path, env=request['environment'], native_protein_structure=True)
        assert reused.path == handle.path and calls[-1] == (expected, handle.path)
        assert operations._protein_plan(state.assignment, str(handle.path)) == plan
    assert len(calls) == 2 and len(list(tmp_path.rglob('native.json'))) == 1


def test_actual_failed_input_attempt_explicit_retry_preserves_old_handoff(tmp_path, harnesses, monkeypatch):
    h = harnesses(tmp_path)
    selected_input = Path(h.assignment['requested_job']['native_protein_structure']['inputs'][0]['path'])
    original_input = selected_input.read_bytes()
    selected_input.write_bytes(b'actual changed input rejected during native staging')
    first = h.action('practical.job.start')
    first_handle = native.NativeJobHandle(Path(execution(first)))
    assert native.wait_job(first_handle).returncode == 1
    failure = h.action('practical.job.collect')
    failure_ref, = failure['record_refs']
    original = h.progress.targets.read_target(failure_ref, h.scope)
    assert not h.progress.targets.usable_handoff(original)
    assert h.progress.targets.returnable_handoff(original)
    plan = h.operations._protein_plan(h.assignment, str(first_handle.path))
    bundle = Path(plan['attempt_directory'])/BUNDLE_FILENAME
    failed_bytes = bundle.read_bytes()
    assert any(f['code'] == 'input_digest_mismatch' for f in json.loads(failed_bytes)['failures'])
    selected_input.write_bytes(original_input)
    retried = h.action('practical.job.start', {'retry_failed_execution_id': str(first_handle.path)})
    retry_handle = native.NativeJobHandle(Path(execution(retried)))
    assert retry_handle.path != first_handle.path
    assert native.wait_job(retry_handle).returncode == 0
    new_plan = h.operations._protein_plan(h.assignment, str(retry_handle.path))
    assert new_plan['requested_job'] == plan['requested_job']
    assert new_plan['identity']['operation_key'] == retried['result']['operation_key']
    assert h.progress.targets.read_target(failure_ref, h.scope) == original
    observed = h.progress.targets.observe_target(original, operation_key='old-failure-after-retry')
    assert observed['state'] == 'failed' and observed['native']['execution_id'] == str(first_handle.path)
    assert bundle.read_bytes() == failed_bytes
    with monkeypatch.context() as patch:
        patch.setattr(native, 'status', lambda *a, **k: pytest.fail('replay polled'))
        patch.setattr(native, 'start_prepared', lambda *a, **k: pytest.fail('replay submitted'))
        assert h.action('practical.job.start', index=0) == first
        assert h.action('practical.job.start', {'retry_failed_execution_id': str(first_handle.path)}, index=2) == retried
    assert len(list(tmp_path.rglob('native.json'))) == 2


@pytest.mark.parametrize('state,terminal,returncode,service_exit', [
    ('execution_unknown', False, None, None), ('execution_unknown', True, 7, None),
    ('cancelled', True, 7, None), ('returned', True, None, None),
    ('returned', True, -9, {'EXIT_CODE': 'killed'}), ('returned', True, 0, None)])
def test_injected_nonfailed_lifecycle_never_retries(tmp_path, monkeypatch, state, terminal, returncode, service_exit):
    operations, reserved, handle, plan = reserve(tmp_path)
    view = native.status(handle)
    view.update(state=state, terminal=terminal)
    view['metadata'].update(native_returncode=returncode, service_exit=service_exit)
    fake = SimpleNamespace(**vars(reserved), context=lambda: reserved.assignment['initial_context'])
    monkeypatch.setattr(operations, '_job_handle', lambda unused: handle)
    monkeypatch.setattr(native, 'status', lambda selected: view)
    monkeypatch.setattr(operations, '_handle', lambda *a, **k: pytest.fail('injected nonfailure retried'))
    result, _ = operations._execute(fake, 'practical.job.start',
        {'retry_failed_execution_id': str(handle.path)}, f'{RUN}:{EPISODE}:1')
    assert result['native_outcome']['failure']['code'] == 'practical_retry_requires_original_failed_execution'
    assert result['native_outcome']['attempt_operation_key'] == plan['identity']['operation_key']
    assert len(list(tmp_path.rglob('native.json'))) == 1


def test_injected_wrong_retry_identity_and_changed_plan_cannot_launch(tmp_path, monkeypatch):
    operations, reserved, handle, plan = reserve(tmp_path)
    view = native.status(handle)
    view.update(state='returned', terminal=True)
    view['metadata']['native_returncode'] = 7
    fake = SimpleNamespace(**vars(reserved), context=lambda: reserved.assignment['initial_context'])
    monkeypatch.setattr(operations, '_job_handle', lambda unused: handle)
    monkeypatch.setattr(native, 'status', lambda selected: view)
    monkeypatch.setattr(operations, '_handle', lambda *a, **k: pytest.fail('unqualified retry launched'))
    result, _ = operations._execute(fake, 'practical.job.start', {'retry_failed_execution_id': '/another/native.json'}, 'retry')
    assert result['native_outcome']['failure']['code'] == 'practical_retry_requires_original_failed_execution'
    native_body = handle.read()
    native_body['command'].append('changed')
    handle.path.write_text(json.dumps(native_body))
    monkeypatch.setattr(native, 'status', lambda *a, **k: pytest.fail('changed plan polled'))
    with pytest.raises(ValueError, match='original_commission_mismatch'):
        operations._execute(fake, 'practical.job.start', {'retry_failed_execution_id': str(handle.path)}, 'retry')


def test_injected_receipt_attempt_path_disagreement_is_rejected(tmp_path, harnesses, monkeypatch):
    h = harnesses(tmp_path)
    result = h.action('practical.job.start')
    handle = native.NativeJobHandle(Path(execution(result)))
    native.wait_job(handle)
    reference, = result['record_refs']
    target, body = h.progress.targets._native(reference, h.scope)
    for kind in ('attempt_id', 'attempt_operation_key', 'execution_id'):
        changed = deepcopy(body)
        if kind == 'execution_id':
            job = changed['receipt']['outcome']['facts']['requested_job']
            job['execution_id'] = job['handoff']['execution_id'] = str(tmp_path/'other'/'native.json')
        else:
            changed['receipt']['outcome']['native_outcome'][kind] = 'wrong'
        with monkeypatch.context() as patch:
            patch.setattr(h.progress.targets.receipts, 'read', lambda *a, **k: changed)
            with pytest.raises(ValueError, match='original_commission_mismatch'):
                h.progress.targets._native(reference, h.scope)
    assert h.progress.targets.read_target(reference, h.scope) == target


def test_actual_ordinary_local_route_is_unchanged(tmp_path, harnesses):
    h = harnesses(tmp_path, generic=True)
    result = h.action('practical.job.start')
    handle = native.NativeJobHandle(Path(execution(result)))
    assert native.wait_job(handle).returncode == 0
    collected = h.action('practical.job.collect')
    assert collected['result']['outcome']['facts']['requested_job']['status'] == 'completed'
    assert 'ordinary local output' in collected['result']['outcome']['native_outcome']['observed_logs']['stdout']['tail_utf8']
    reference, = result['record_refs']
    target = h.progress.targets.read_target(reference, h.scope)
    assert describe_execution_target(target)['output_format'] is None
    assert h.progress.targets.usable_handoff(target)
    observed = h.progress.observe(reference, FIELDS, h.scope, operation_key='ordinary-monitor')
    assert observed['execution_status']['native']['state'] == 'completed'
    assert not (handle.path.parent/RUN_PLAN_FILENAME).exists()
