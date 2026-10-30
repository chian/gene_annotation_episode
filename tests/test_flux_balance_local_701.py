"""Real pending/reservation controls with explicitly synthetic custody metadata.

Original688 supplies software/model metadata only. No model is loaded; this
suite does not authenticate its synthetic receipt as received episode input.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_flux_balance_contracts import (
    ATTEMPT_DIRECTORY_NAME, OWNER_FILENAME, POLICY, RUN_PLAN_FILENAME, STARTED_FILENAME,
    flux_balance_driver_argv, flux_balance_environment,
)
from gene_annotation_episode.native_flux_balance_local import (
    INPUT_BINDING_FILENAME, local_flux_balance_plan, prepare_local_flux_balance,
)
from gene_annotation_episode.practical_execution_state import PracticalState

pytestmark = pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ, reason='requires bounded529')
ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / 'verification/tool_graders_hmmer_map_verification_2026-10-28_529/check151c_producer688/producer-emissions/sbml/selected-plan.json'
SELECTION = {'version': 'flux_balance_execution_selection_v1',
             'environment_realization': 'operation_scoped_tmp_and_cache_v1'}


def _write(path, value):
    path.chmod(0o600)
    path.write_text(canonical(value) + '\n')


def _control_file(receipt):
    raw = canonical(receipt).encode('utf-8')
    sha = hashlib.sha256(raw).hexdigest()
    return {'artifact_ref': 'artifact_' + sha, 'sha256': sha, 'size_bytes': len(raw),
            'format': 'flux_balance_input_binding_receipt_v1'}


@pytest.fixture(autouse=True)
def no_dispatch(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('reservation attempted dispatch, polling, cancellation or scientific execution')
    for name in ('start_prepared', 'start_job', 'resume_start', 'status', 'collect', 'cancel', 'run_blocking', 'wait_job'):
        monkeypatch.setattr(native, name, forbidden)
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)


@pytest.fixture
def setup(tmp_path):
    def make(*, literal=False, pending_tool='practical.job.start', pending_key='selected start', pending=True):
        workspace = tmp_path / ('literal' if literal else 'realized')
        workspace.mkdir()
        operation = 'selected start'
        root = workspace / '.episode-operations' / digest({'run': 'run701', 'episode': 'episode701'}) / digest(operation)
        job = json.loads(ORIGINAL.read_text())['requested_job']
        if literal:
            job['environment'] = flux_balance_environment(job['native_flux_balance']['software'],
                attempt_directory=str(root / ATTEMPT_DIRECTORY_NAME), lifecycle_directory=str(root))
        assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'assignment701',
            'resource_kind': 'local', 'resource_id': 'selected-local-701', 'workspace': str(workspace),
            'endpoint': 'usable_handoff', 'requested_job': job,
            'progress_requirements': [{'key': 'handoff', 'credit': 1,
                'predicate': {'kind': 'requested_job_handoff'}}], 'completion_keys': ['handoff'],
            'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
            'inventory_snapshot': {'fixture': 'synthetic custody; original688 software metadata only'},
            'constraints': {'allocation': deepcopy(POLICY), **POLICY}}
        if not literal:
            assignment['native_flux_balance_execution'] = deepcopy(SELECTION)
        state = PracticalState(tmp_path / ('state-literal' if literal else 'state-realized'),
                               'run701', 'episode701', assignment)
        if pending:
            state.begin(pending_key, pending_tool, {})
        # Deliberately synthetic; these values confer no authority or access.
        receipt = {'version': 'flux_balance_input_binding_receipt_v1', 'binding': {
            'version': 'flux_balance_input_binding_v1', 'run_id': state.run_id, 'episode_id': state.episode_id,
            'request_sha256': '7' * 64, 'assignment_sha256': digest(assignment),
            'scope': {'fixture': 'synthetic701'}, 'inheritance_manifest': {'fixture': 'synthetic701'},
            'input_versions': [{'reference': 'artifact_' + '8' * 64, 'version': '1', 'content_sha256': '8' * 64}],
            'model': {'file': {'artifact_ref': 'artifact_' + '8' * 64, 'sha256': '8' * 64,
                'size_bytes': 1, 'format': 'sbml'}, 'path': '/synthetic701/model', 'uses': [], 'witnesses': []},
            'prior_sources': []}, 'witness_records': []}
        return {'state': state, 'operation': operation, 'root': root,
                'policy': LocalJobPolicy(**POLICY), 'receipt': receipt, 'file': _control_file(receipt)}
    return make


def _prepare(case, **changes):
    arguments = {'root': case['root'], 'policy': case['policy'],
                 'input_binding_receipt': case['receipt'], 'input_binding_file': case['file'], **changes}
    return prepare_local_flux_balance(case['state'], case['operation'], **arguments)


@pytest.mark.parametrize('literal', [False, True])
def test_reservation_preserves_selection_without_execution_or_credit(setup, literal, monkeypatch):
    case = setup(literal=literal)
    state = case['state']
    before = deepcopy(state.assignment)
    before_credit = state.credit_view()
    real_prepare = native.prepare_job
    calls = []
    def counted(*args, **kwargs):
        calls.append((args, kwargs))
        return real_prepare(*args, **kwargs)
    monkeypatch.setattr(native, 'prepare_job', counted)
    handle = _prepare(case)
    plan = local_flux_balance_plan(state.assignment, str(handle.path))
    assert handle.path == case['root'] / 'native.json'
    assert plan['version'] == ('flux_balance_run_plan_v1' if literal else 'flux_balance_run_plan_v2')
    assert plan['requested_job'] == before['requested_job']
    assert plan['identity']['assignment_sha256'] == digest(before)
    assert plan['identity']['requested_job_sha256'] == digest(before['requested_job'])
    assert state.assignment == before and state.receipts() == [] and state.completion_proof() is None
    assert state.credit_view() == before_credit and len(state._load()[1]) == 1
    body = handle.read()
    assert body['stage'] == 'prepared' and body['started_at'] is None and body['boot_id'] is None
    assert body['command'] == flux_balance_driver_argv(plan)
    actual_request = json.loads(Path(body['paths']['request']).read_text())
    invoke = json.loads((case['root'] / 'invoke.json').read_text())
    assert invoke['argv'] == before['requested_job']['argv']
    assert invoke['environment'] == before['requested_job']['environment']
    assert invoke['native_flux_balance_input_binding_file'] == case['file']
    assert (case['root'] / INPUT_BINDING_FILENAME).read_bytes() == canonical(case['receipt']).encode('utf-8')
    assert not Path(plan['attempt_directory']).exists()
    assert actual_request['env']['TMPDIR'] == str(case['root'])
    assert actual_request['env']['XDG_CACHE_HOME'] == str(case['root'] / ATTEMPT_DIRECTORY_NAME / 'cache')
    if not literal:
        assert invoke['environment']['TMPDIR'] != actual_request['env']['TMPDIR']
        assert plan['environment_binding']['selection'] == SELECTION
        assert [r['name'] for r in plan['environment_binding']['relocations']] == ['TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME', 'PIP_CACHE_DIR']
    assert _prepare(case) == handle and len(calls) == 1
    assert state.assignment == before and state.credit_view() == before_credit


@pytest.mark.parametrize('fault', ['missing', 'wrong_tool', 'wrong_operation', 'wrong_run', 'wrong_episode'])
def test_actual_pending_start_required(setup, fault):
    case = setup(pending=fault != 'missing', pending_tool='practical.file.inspect' if fault == 'wrong_tool' else 'practical.job.start',
                 pending_key='different start' if fault == 'wrong_operation' else 'selected start')
    if fault == 'wrong_run': case['state'].run_id = 'another-run'
    if fault == 'wrong_episode': case['state'].episode_id = 'another-episode'
    with pytest.raises(ValueError): _prepare(case)
    assert not case['root'].exists()


@pytest.mark.parametrize('fault', ['run', 'episode', 'assignment', 'version', 'receipt_keys', 'file_digest', 'file_size', 'file_format', 'file_reference'])
def test_input_owner_and_canonical_file_identity(setup, fault):
    case = setup()
    if fault in ('run', 'episode', 'assignment'):
        key = {'run': 'run_id', 'episode': 'episode_id', 'assignment': 'assignment_sha256'}[fault]
        case['receipt']['binding'][key] = 'different' if fault != 'assignment' else 'b' * 64
        case['file'] = _control_file(case['receipt'])
    elif fault == 'version': case['receipt']['version'] = 'auto'
    elif fault == 'receipt_keys': case['receipt']['extra'] = True
    elif fault == 'file_digest': case['file']['sha256'] = 'c' * 64
    elif fault == 'file_size': case['file']['size_bytes'] += 1
    elif fault == 'file_format': case['file']['format'] = 'sbml'
    else: case['file']['artifact_ref'] = 'artifact_' + 'd' * 64
    with pytest.raises(ValueError): _prepare(case)
    assert not case['root'].exists()


@pytest.mark.parametrize('fault', ['memory', 'scratch', 'wall', 'root', 'resource', 'constraint'])
def test_original_allocation_and_directory_exact(setup, fault):
    case = setup()
    changes = {}
    if fault in ('memory', 'scratch', 'wall'):
        policy = deepcopy(POLICY)
        policy[{'memory': 'memory_bytes', 'scratch': 'scratch_bytes', 'wall': 'wall_seconds'}[fault]] = 1
        changes['policy'] = LocalJobPolicy(**policy)
    elif fault == 'root': changes['root'] = case['root'].parent / 'another'
    elif fault == 'resource': case['state'].assignment['resource_kind'] = 'hpc'
    else: case['state'].assignment['constraints']['allocation']['memory_bytes'] = 1
    with pytest.raises(ValueError): _prepare(case, **changes)
    assert not case['root'].exists()


def test_literal_request_cannot_relocate_without_original_selection(setup):
    case = setup()
    del case['state'].assignment['native_flux_balance_execution']
    with pytest.raises(ValueError, match='fba_runtime_environment_mismatch'): _prepare(case)
    assert not case['root'].exists()


def test_repeated_reservation_cannot_substitute_another_self_consistent_receipt(setup):
    case = setup()
    handle = _prepare(case)
    before = (case['root'] / INPUT_BINDING_FILENAME).read_bytes()
    case['receipt']['binding']['request_sha256'] = '9' * 64
    case['file'] = _control_file(case['receipt'])
    with pytest.raises(ValueError, match='fba_original_control_conflict'):
        _prepare(case)
    assert (case['root'] / INPUT_BINDING_FILENAME).read_bytes() == before
    assert local_flux_balance_plan(case['state'].assignment, str(handle.path))['requested_job'] == case['state'].assignment['requested_job']


def test_exact_controls_survive_failure_before_native_reservation(setup, monkeypatch):
    case = setup()
    real_prepare = native.prepare_job
    def failed_before_reservation(*args, **kwargs):
        raise OSError('explicit fixture failure before native.prepare_job')
    monkeypatch.setattr(native, 'prepare_job', failed_before_reservation)
    with pytest.raises(OSError, match='explicit fixture failure'):
        _prepare(case)
    assert not (case['root'] / 'native.json').exists()
    before = {p.name: p.read_bytes() for p in case['root'].iterdir()}
    monkeypatch.setattr(native, 'prepare_job', real_prepare)
    handle = _prepare(case)
    assert handle.read()['stage'] == 'prepared'
    assert all((case['root'] / name).read_bytes() == raw for name, raw in before.items())
    assert case['state'].receipts() == [] and case['state'].completion_proof() is None


@pytest.mark.parametrize('fault', ['plan', 'invoke', 'input', 'handle_command', 'handle_policy', 'request_hash', 'request_environment', 'duplicate_path', 'outside_path', 'stdout', 'invoke_null', 'invoke_array', 'metadata_null', 'metadata_array'])
def test_existing_reservation_control_and_wrapper_tamper(setup, fault):
    case = setup()
    handle = _prepare(case)
    body = handle.read()
    if fault == 'plan':
        path = case['root'] / RUN_PLAN_FILENAME
        value = json.loads(path.read_text());value['identity']['resource_id'] = 'another'
        _write(path, value)
    elif fault == 'invoke':
        path = case['root'] / 'invoke.json'
        value = json.loads(path.read_text());value['environment']['TMPDIR'] = '/another'
        _write(path, value)
    elif fault == 'input':
        path = case['root'] / INPUT_BINDING_FILENAME
        value = json.loads(path.read_text());value['binding']['input_versions'] = []
        _write(path, value)
    elif fault == 'request_hash':
        path = Path(body['paths']['request']);path.write_text(path.read_text() + ' ')
    elif fault == 'request_environment':
        path = Path(body['paths']['request'])
        value = json.loads(path.read_text());value['env']['TMPDIR'] = '/another'
        _write(path, value)
        body['request_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        _write(handle.path, body)
    elif fault in ('invoke_null', 'invoke_array'):
        _write(case['root'] / 'invoke.json', None if fault == 'invoke_null' else [])
    else:
        if fault == 'handle_command': body['command'][0] = '/unselected/python'
        elif fault == 'handle_policy': body['metadata']['policy']['scratch_bytes'] = 1
        elif fault == 'duplicate_path': body['paths']['status'] = body['paths']['request']
        elif fault == 'outside_path': body['paths']['status'] = str(case['root'].parent / 'status')
        elif fault == 'stdout': body['stdout'] = str(case['root'] / 'other.log')
        elif fault == 'metadata_null': body['metadata'] = None
        elif fault == 'metadata_array': body['metadata'] = []
        _write(handle.path, body)
    with pytest.raises(ValueError): local_flux_balance_plan(case['state'].assignment, str(handle.path))
    with pytest.raises(ValueError): _prepare(case)


@pytest.mark.parametrize('target', ['root', 'input', 'handle', 'request', 'attempt'])
def test_symlink_controls_and_directories_rejected(setup, tmp_path, target):
    case = setup()
    if target == 'root':
        destination = tmp_path / 'elsewhere';destination.mkdir()
        case['root'].parent.mkdir(parents=True)
        case['root'].symlink_to(destination, target_is_directory=True)
        with pytest.raises(OSError): _prepare(case)
        assert list(destination.iterdir()) == []
        return
    handle = _prepare(case)
    body = handle.read()
    path = {'input': case['root'] / INPUT_BINDING_FILENAME,
            'handle': handle.path, 'request': Path(body['paths']['request']),
            'attempt': case['root'] / ATTEMPT_DIRECTORY_NAME}[target]
    if target == 'attempt':
        destination = tmp_path / 'elsewhere';destination.mkdir()
    else:
        destination = tmp_path / 'elsewhere';destination.write_bytes(path.read_bytes());path.unlink()
    path.symlink_to(destination, target_is_directory=target == 'attempt')
    with pytest.raises((ValueError, OSError)): local_flux_balance_plan(case['state'].assignment, str(handle.path))


@pytest.mark.parametrize('fault', ['unsealed_attempt', 'unknown_file', 'nonempty_stdout', 'conflicting_plan'])
def test_unsealed_work_not_repaired_or_dispatched(setup, fault):
    case = setup()
    case['root'].mkdir(parents=True)
    if fault == 'unsealed_attempt': (case['root'] / ATTEMPT_DIRECTORY_NAME).mkdir()
    elif fault == 'unknown_file': (case['root'] / 'unknown.bin').write_bytes(b'retained partial work')
    elif fault == 'nonempty_stdout': (case['root'] / 'stdout.log').write_bytes(b'prior work')
    else: (case['root'] / RUN_PLAN_FILENAME).write_bytes(b'{}\n')
    with pytest.raises(ValueError): _prepare(case)
    assert not (case['root'] / 'native.json').exists()


@pytest.mark.parametrize('literal', [False, True])
def test_owner_started_join_without_environment_reinterpretation(setup, literal):
    case = setup(literal=literal)
    handle = _prepare(case)
    plan = local_flux_balance_plan(case['state'].assignment, str(handle.path))
    attempt = case['root'] / ATTEMPT_DIRECTORY_NAME;attempt.mkdir()
    (attempt / OWNER_FILENAME).write_text(canonical(plan) + '\n')
    started = {'plan_sha256': digest(plan), 'started_at': '2026-10-29T00:00:00+00:00'}
    if not literal: started['environment_observation_sha256'] = 'e' * 64
    (attempt / STARTED_FILENAME).write_text(canonical(started) + '\n')
    assert local_flux_balance_plan(case['state'].assignment, str(handle.path)) == plan
    started['plan_sha256'] = 'f' * 64
    _write(attempt / STARTED_FILENAME, started)
    with pytest.raises(ValueError, match='fba_original_attempt_mismatch'):
        local_flux_balance_plan(case['state'].assignment, str(handle.path))


@pytest.mark.parametrize('fault', ['owner', 'missing_owner', 'started_extra', 'started_v1_shape', 'invalid_environment_pin'])
def test_owner_started_conflicts_stay_failures(setup, fault):
    case = setup()
    handle = _prepare(case)
    plan = local_flux_balance_plan(case['state'].assignment, str(handle.path))
    attempt = case['root'] / ATTEMPT_DIRECTORY_NAME;attempt.mkdir()
    owner = deepcopy(plan)
    if fault == 'owner': owner['identity']['resource_id'] = 'another'
    if fault != 'missing_owner': (attempt / OWNER_FILENAME).write_text(canonical(owner) + '\n')
    started = {'plan_sha256': digest(plan), 'started_at': '2026-10-29T00:00:00+00:00', 'environment_observation_sha256': 'e' * 64}
    if fault == 'started_extra': started['extra'] = True
    elif fault == 'started_v1_shape': del started['environment_observation_sha256']
    elif fault == 'invalid_environment_pin': started['environment_observation_sha256'] = 'missing'
    (attempt / STARTED_FILENAME).write_text(canonical(started) + '\n')
    with pytest.raises(ValueError, match='fba_original_attempt_mismatch'):
        local_flux_balance_plan(case['state'].assignment, str(handle.path))
