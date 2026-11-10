"""Original pending-intent reservation and shared-lifecycle execution checks."""
from copy import deepcopy
from importlib import import_module
import ctypes
import json
import os
from pathlib import Path
import select
import struct
import time

import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_genomic_overlap_contracts import (
    POLICY, RUN_PLAN_FILENAME, BATCH_FILENAME, ATTEMPT_DIRECTORY_NAME,
    genomic_overlap_driver_argv, genomic_overlap_environment,
)
from gene_annotation_episode.native_genomic_overlap_local import (
    prepare_local_genomic_overlap, local_genomic_overlap_plan,
)
from gene_annotation_episode.native_genomic_overlap_driver import _immutable
from gene_annotation_episode.practical_execution_state import PracticalState
from gene_annotation_episode.practical_execution_records import assess_validations

f = import_module('verification.tool_graders_genomic_overlap_native_driver_2026-10-27_427.fixture_helpers')


def selected_state(directory, *, begin=True, tool='practical.job.start', software_change=None, data=None):
    assignment = f.make_assignment(directory, software_change=software_change, data=data)
    state = PracticalState(directory / 'practical-state', 'component-run', 'local-child', assignment)
    key = 'selected-start'
    if begin:
        state.begin(key, tool, {})
    root = directory / '.episode-operations' / digest({'run': state.run_id, 'episode': state.episode_id}) / digest(key)
    return state, key, root


def reserve(directory, **kwargs):
    state, key, root = selected_state(directory, **kwargs)
    handle = prepare_local_genomic_overlap(state, key, root=root, policy=LocalJobPolicy(**POLICY))
    return state, key, root, handle


def test_preparation_only_freezes_pending_action_and_replays_exactly(tmp_path, monkeypatch):
    monkeypatch.setattr(native, 'start_prepared', lambda *a, **k: pytest.fail('preparation dispatched'))
    monkeypatch.setattr(native, 'resume_start', lambda *a, **k: pytest.fail('preparation resumed'))
    state, key, root, handle = reserve(tmp_path)
    body = handle.read()
    assert body['stage'] == 'prepared' and body['started_at'] is None
    assert not (root / ATTEMPT_DIRECTORY_NAME).exists()
    assert not Path(body['paths']['ready']).exists()
    plan = local_genomic_overlap_plan(state.assignment, str(handle.path))
    assert plan['identity']['assignment_sha256'] == digest(state.assignment)
    assert body['command'] == genomic_overlap_driver_argv(plan)
    request = json.loads(Path(body['paths']['request']).read_bytes())
    assert request['env'] == genomic_overlap_environment(plan['requested_job']['native_genomic_overlap'], attempt_directory=plan['attempt_directory'])
    assert json.loads((root / 'invoke.json').read_bytes()) == {
        'cwd': str(root), 'argv': state.assignment['requested_job']['argv'],
        'environment': {'LC_ALL': 'C'}, 'native_genomic_overlap_plan': RUN_PLAN_FILENAME}
    before = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
    monkeypatch.setattr(native, 'prepare_job', lambda *a, **k: pytest.fail('reservation repeated'))
    assert prepare_local_genomic_overlap(state, key, root=root, policy=LocalJobPolicy(**POLICY)).path == handle.path
    assert {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()} == before
    # This read authenticates original controls, not today's large operands.
    Path(plan['requested_job']['native_genomic_overlap']['inputs'][0]['path']).unlink()
    assert local_genomic_overlap_plan(state.assignment, str(handle.path)) == plan


@pytest.mark.parametrize('begin,tool', [(False, 'practical.job.start'), (True, 'practical.inspect')])
def test_only_existing_selected_start_can_reserve(tmp_path, begin, tool):
    state, key, root = selected_state(tmp_path, begin=begin, tool=tool)
    with pytest.raises(ValueError, match='selected_pending_start_required'):
        prepare_local_genomic_overlap(state, key, root=root, policy=LocalJobPolicy(**POLICY))
    assert not root.exists()


def test_completed_intent_cannot_reserve_again(tmp_path):
    state, key, root = selected_state(tmp_path)
    outcome = {'facts': {}}
    validations = assess_validations(state.assignment, outcome, state.context())
    state.finish(key, outcome, validations)
    with pytest.raises(ValueError, match='selected_pending_start_required'):
        prepare_local_genomic_overlap(state, key, root=root, policy=LocalJobPolicy(**POLICY))
    assert not root.exists()


@pytest.mark.parametrize('field', ['assignment_id', 'resource_id', 'workspace', 'requested_job', 'allocation'])
def test_assignment_or_allocation_changes_cannot_relabel_original_reservation(tmp_path, field):
    state, key, root, handle = reserve(tmp_path)
    changed = deepcopy(state.assignment)
    if field == 'requested_job':
        changed['requested_job']['native_genomic_overlap']['request']['region_sets'][0]['display_label'] = 'changed'
    elif field == 'allocation':
        changed['constraints']['allocation']['memory_bytes'] -= 1
    else:
        changed[field] += '-changed'
    with pytest.raises(ValueError):
        local_genomic_overlap_plan(changed, str(handle.path))


@pytest.mark.parametrize('kind', ['command', 'cwd', 'policy', 'stdout', 'duplicate_control', 'request_hash', 'request_bytes'])
def test_original_native_tuple_and_bytes_are_authenticated(tmp_path, kind):
    state, key, root, handle = reserve(tmp_path)
    body = handle.read()
    if kind == 'command':
        body['command'][0] = '/different/python'
    elif kind == 'cwd':
        body['cwd'] = str(tmp_path)
    elif kind == 'policy':
        body['metadata']['policy']['scratch_bytes'] -= 1
    elif kind == 'stdout':
        body['stdout'] = str(root / 'different.log')
    elif kind == 'duplicate_control':
        body['paths']['ready'] = body['paths']['request']
    elif kind == 'request_hash':
        body['request_sha256'] = 'a' * 64
    else:
        Path(body['paths']['request']).write_bytes(b'{}\n')
    handle.path.write_text(json.dumps(body))
    with pytest.raises(ValueError, match='original_attempt_mismatch'):
        local_genomic_overlap_plan(state.assignment, str(handle.path))


@pytest.mark.parametrize('which', ['plan', 'handle', 'request', 'component'])
def test_symlink_controls_and_directory_components_rejected(tmp_path, which):
    state, key, root, handle = reserve(tmp_path)
    if which == 'component':
        relocated = root.with_name(root.name + '-real')
        root.rename(relocated)
        root.symlink_to(relocated, target_is_directory=True)
    else:
        target = root / RUN_PLAN_FILENAME if which == 'plan' else handle.path if which == 'handle' else Path(handle.read()['paths']['request'])
        original = target.with_name(target.name + '-real')
        target.rename(original)
        target.symlink_to(original)
    with pytest.raises(ValueError, match='invalid_output_path'):
        local_genomic_overlap_plan(state.assignment, str(handle.path))


def test_prepublication_plan_and_inert_request_can_resume_without_dispatch(tmp_path, monkeypatch):
    state, key, root = selected_state(tmp_path)
    original = native.prepare_job
    def interrupted(*args, **kwargs):
        handle = original(*args, **kwargs)
        # Simulate a crash at prepare_job's last publication, before any start.
        handle.path.unlink()
        raise OSError('synthetic prepublication crash')
    monkeypatch.setattr(native, 'prepare_job', interrupted)
    with pytest.raises(OSError):
        prepare_local_genomic_overlap(state, key, root=root, policy=LocalJobPolicy(**POLICY))
    orphan_requests = sorted(root.glob('.local-job-*.request'))
    assert len(orphan_requests) == 1
    monkeypatch.setattr(native, 'prepare_job', original)
    handle = prepare_local_genomic_overlap(state, key, root=root, policy=LocalJobPolicy(**POLICY))
    assert handle.read()['stage'] == 'prepared'
    assert orphan_requests[0].is_file() and len(list(root.glob('.local-job-*.request'))) == 2
    assert not (root / ATTEMPT_DIRECTORY_NAME).exists()


@pytest.mark.parametrize('evidence', ['attempt', 'ready', 'release', 'status', 'result', 'launcher', 'stdout'])
def test_uncertain_side_effect_evidence_never_gets_new_reservation(tmp_path, monkeypatch, evidence):
    state, key, root = selected_state(tmp_path)
    root.mkdir(parents=True)
    if evidence == 'attempt':
        (root / ATTEMPT_DIRECTORY_NAME).mkdir()
    else:
        (root / ('stdout.log' if evidence == 'stdout' else '.local-job-orphan.' + evidence)).write_text('observed')
    monkeypatch.setattr(native, 'prepare_job', lambda *a, **k: pytest.fail('uncertain work re-reserved'))
    with pytest.raises(ValueError, match='unsealed_native_attempt'):
        prepare_local_genomic_overlap(state, key, root=root, policy=LocalJobPolicy(**POLICY))
    assert not (root / 'native.json').exists()


def test_real_selected_interpreter_driver_under_existing_lifecycle(tmp_path):
    state, key, root, handle = reserve(tmp_path)
    native.start_prepared(handle)
    result = native.wait_job(handle)
    assert result.returncode == 0
    assert result.metadata['policy'] == POLICY
    assert result.metadata['verified_cgroup'] == {'memory_max': POLICY['memory_bytes'], 'memory_swap_max': 0,
        'kill_mode': 'control-group', 'oom_policy': 'kill'}
    plan = local_genomic_overlap_plan(state.assignment, str(handle.path))
    bundle = json.loads(Path(plan['attempt_directory'], BATCH_FILENAME).read_bytes())
    assert bundle['batch_status'] == 'complete'
    assert [row['disposition'] for row in bundle['pairs']] == ['native_succeeded'] * 3
    (tmp_path / 'ACTUAL_LIFECYCLE.json').write_text(json.dumps({'metadata': result.metadata,
        'plan': plan, 'batch': bundle, 'status': native.status(handle)}, indent=2) + '\n')
    # Read-only original reservation authentication never resumes the service.
    assert local_genomic_overlap_plan(state.assignment, str(handle.path)) == plan


def test_missing_interpreter_has_lifecycle_failure_and_no_driver_facts(tmp_path):
    state, key, root, handle = reserve(tmp_path,
        software_change=lambda s: s.update(python_executable=str(tmp_path / 'missing-interpreter')))
    native.start_prepared(handle)
    with pytest.raises(AcquisitionError, match='local_job_execution_error'):
        native.wait_job(handle)
    view = native.status(handle)
    assert view['terminal'] and view['native_receipt']['native_returncode'] is None
    assert view['native_receipt']['execution_failure']['exception_type'] == 'FileNotFoundError'
    assert not (root / ATTEMPT_DIRECTORY_NAME).exists()
    (tmp_path / 'ACTUAL_NEVER_STARTED.json').write_text(json.dumps(view, indent=2) + '\n')


def test_actual_lifecycle_kill_after_first_pair_seal_preserves_unsealed_attempt(tmp_path, monkeypatch):
    # The operator test explicitly selects this kill. No driver/runtime retry,
    # stopping rule, timeout, or monitoring itinerary is installed by it.
    state, key, root, handle = reserve(tmp_path, data=[*f.DEFAULT_DATA[:2], b'chr1\t10\t20\n' * 50_000])
    plan = local_genomic_overlap_plan(state.assignment, str(handle.path))
    directory = Path(plan['attempt_directory'])
    pair_directory = directory / 'overlap/pairs/p0'
    native.start_prepared(handle)
    fd = None
    try:
        while not pair_directory.exists():
            assert not native.status(handle)['terminal'], 'driver exited before pair directory'
            time.sleep(.01)
        # Watch publication of the first immutable seal while C normalizes.
        libc = ctypes.CDLL(None, use_errno=True)
        fd = libc.inotify_init1(os.O_CLOEXEC)
        assert fd >= 0
        watch = libc.inotify_add_watch(fd, os.fsencode(pair_directory), 0x100)  # IN_CREATE
        assert watch >= 0
        second_path = directory / 'overlap/pairs/p1/overlap.wo.tsv'
        second_watch = libc.inotify_add_watch(fd, os.fsencode(second_path.parent), 0x102)  # CREATE | MODIFY
        assert second_watch >= 0
        sealed = (pair_directory / 'manifest.json').exists()
        while not sealed:
            ready, _, _ = select.select([fd], [], [], .1)
            if not ready:
                assert not native.status(handle)['terminal'], 'driver exited before first seal'
                continue
            raw = os.read(fd, 65536)
            offset = 0
            while offset < len(raw):
                _, _, _, length = struct.unpack_from('iIII', raw, offset)
                name = raw[offset+16:offset+16+length].rstrip(b'\0')
                sealed |= name == b'manifest.json'
                offset += 16 + length
        # Preserve an actually written, still unsealed second-pair output as
        # well as the earlier seal. Its unknown extent is never inferred from
        # parseability or the presence of bytes.
        while not second_path.exists() or second_path.stat().st_size == 0:
            ready, _, _ = select.select([fd], [], [], .1)
            if ready:
                os.read(fd, 65536)
            else:
                assert not native.status(handle)['terminal'], 'driver exited before second-pair bytes'
        native.cancel(handle)
        view = native.status(handle)
        assert view['terminal'] and view['quiescent']
        assert (pair_directory / 'manifest.json').is_file()
        assert second_path.is_file() and second_path.stat().st_size > 0
        assert not (directory / BATCH_FILENAME).exists()
        (tmp_path / 'ACTUAL_KILLED.json').write_text(json.dumps({'label': 'actual_operator_selected_lifecycle_kill',
            'plan': plan, 'status': view, 'first_pair': json.loads((pair_directory / 'manifest.json').read_bytes()),
            'retained_files': [str(path.relative_to(directory)) for path in directory.rglob('*') if path.is_file()]}, indent=2) + '\n')
        before = handle.path.read_bytes()
        monkeypatch.setattr(native, 'prepare_job', lambda *a, **k: pytest.fail('killed attempt re-reserved'))
        assert prepare_local_genomic_overlap(state, key, root=root, policy=LocalJobPolicy(**POLICY)).path == handle.path
        assert handle.path.read_bytes() == before
        from gene_annotation_episode.native_genomic_overlap_driver import run_genomic_overlap_driver
        with pytest.raises(ValueError, match='unsealed_native_attempt'):
            run_genomic_overlap_driver(plan)
    finally:
        if fd is not None:
            os.close(fd)
        if not native.status(handle)['quiescent']:
            native.cancel(handle)
