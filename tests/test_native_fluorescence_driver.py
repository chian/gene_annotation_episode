"""Finite producer tests inside the coordinator's bounded test process.

The finite-control fixtures stub software verification explicitly; they do not
claim an installed decoder or live-resource verification. Existing authentic
FCS format tests remain the format evidence. Actual configured subprocess tests
are selected separately by the coordinator.
"""
from contextlib import contextmanager
from copy import deepcopy
import errno
import json
from pathlib import Path

import pytest

from gene_annotation_episode import native_fluorescence_driver as driver
from gene_annotation_episode import native_fluorescence_local as local
from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.fluorescence_execution_common import canonical, digest, identity
from gene_annotation_episode import fluorescence_event_contracts as core
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_fluorescence_contracts import (POLICY, fluorescence_environment,
    validate_fluorescence_manifest, validate_fluorescence_parsed_batch)
from gene_annotation_episode.native_fluorescence_storage import immutable_bytes, immutable_json, read_json
from test_native_fluorescence_contracts import event_input, job, plan, software


def finite_driver(monkeypatch, original):
    """Explicit structural fixture: actual software trust is not mocked as fact."""
    calls = []
    monkeypatch.setattr(driver, 'verify_fluorescence_software', lambda supplied: calls.append(deepcopy(supplied)))
    selected = original['requested_job']['native_fluorescence']
    environment = fluorescence_environment(selected['software'], attempt_directory=original['attempt_directory'])
    environment.update({name: str(Path(original['identity']['execution_id']).parent) for name in ('TMPDIR', 'TMP', 'TEMP')})
    for key, value in environment.items(): monkeypatch.setenv(key, value)
    return calls


def output(original, role):
    row = next(row for row in original['outputs'] if row['role'] == role)
    return Path(original['attempt_directory']) / row['relative_path']


@pytest.mark.parametrize('operation', ['perform_facs_cell_sorting', 'analyze_cytokine_production_in_cd4_tcells'])
@pytest.mark.parametrize('parser', ['csv', 'table_snapshot'])
def test_driver_keeps_complete_originals_and_same_explicit_origin(tmp_path, monkeypatch, operation, parser):
    raw = b'signal\n10\n20\n' if parser == 'csv' else b'{"schema":"fluorescence_event_table_v1","columns":["signal"],"rows":[[10],[20]]}'
    original = plan(tmp_path, selected_job=job(tmp_path, inputs=[event_input(tmp_path, raw=raw, parser=parser)], operation=operation))
    checks = finite_driver(monkeypatch, original)
    manifest = driver.run_fluorescence_driver(original)
    assert len(checks) == 3
    assert validate_fluorescence_manifest(manifest, original_plan=original) == manifest
    assert output(original, 'event_input:0').read_bytes() == raw
    batch_raw = output(original, 'event_batch:0').read_bytes()
    batch = read_json(output(original, 'event_batch:0'))
    assert batch_raw == core.canonical(batch) + b'\n'
    assert batch_raw != canonical(batch) + b'\n'
    assert [row['values'][0]['measurement']['value'] for row in batch['parse']['events']] == [10, 20]
    assert {row['values'][0]['measurement']['state'] for row in batch['parse']['events']} == {'supplied_predicted'}
    assert manifest['inputs'][0]['batch_file'] == identity(batch_raw, format='fluorescence_parsed_batch_v1')
    assert manifest['failures'] == []
    assert output(original, 'manifest').read_bytes() == canonical(manifest) + b'\n'
    with pytest.raises(ValueError, match='already_started'): driver.run_fluorescence_driver(original)


@pytest.mark.parametrize('broken', ['missing', 'changed', 'partial', 'empty', 'domain_failed'])
def test_second_source_keeps_first_valid_batch_and_zero_is_not_unavailable(tmp_path, monkeypatch, broken):
    first = event_input(tmp_path, index=0)
    second = event_input(tmp_path, raw=b'signal\n' if broken == 'empty' else b'signal\n30\n"bad' if broken == 'partial' else b'signal\n30\n', index=1)
    if broken == 'domain_failed': second['domain']['state'] = 'failed'
    original = plan(tmp_path, selected_job=job(tmp_path, inputs=[first, second]))
    if broken == 'missing': Path(second['path']).unlink()
    if broken == 'changed': Path(second['path']).write_bytes(b'changed bytes')
    finite_driver(monkeypatch, original)
    manifest = driver.run_fluorescence_driver(original)
    assert manifest['inputs'][0]['extent'] == 'complete'
    assert validate_fluorescence_parsed_batch(read_json(output(original, 'event_batch:0')), original_plan=original, input_index=0)
    batch = read_json(output(original, 'event_batch:1'))
    expected = 'complete' if broken == 'empty' else 'partial' if broken == 'partial' else 'unavailable'
    assert batch['parse']['source']['extent'] == manifest['inputs'][1]['extent'] == expected
    assert batch['parse']['source']['file'] == second['source']['file']
    if broken in ('missing', 'changed'):
        assert not output(original, 'event_input:1').exists()
        assert manifest['failures'][0]['code'] == ('input_file_unavailable' if broken == 'missing' else 'input_identity_mismatch')
    if broken == 'empty':
        assert batch['parse']['events'] == [] and batch['parse']['issues'] == []


@pytest.mark.parametrize('error', [MemoryError('fixture interruption'), OSError(errno.ENOSPC, 'fixture scratch failure')])
def test_later_resource_failure_leaves_independent_first_batch_without_manifest(tmp_path, monkeypatch, error):
    original = plan(tmp_path, selected_job=job(tmp_path, inputs=[event_input(tmp_path, index=i) for i in range(2)]))
    finite_driver(monkeypatch, original)
    actual = driver._parse
    def selected_failure(raw, binding):
        if binding['domain']['key'] == 'domain-1': raise error
        return actual(raw, binding)
    monkeypatch.setattr(driver, '_parse', selected_failure)
    with pytest.raises(type(error)): driver.run_fluorescence_driver(original)
    assert output(original, 'event_input:0').is_file() and output(original, 'event_input:1').is_file()
    assert not output(original, 'event_batch:1').exists() and not output(original, 'manifest').exists()
    batch = read_json(output(original, 'event_batch:0'))
    assert validate_fluorescence_parsed_batch(batch, original_plan=original, input_index=0)
    assert batch['parse']['source']['extent'] == 'complete'


def test_software_identity_failure_precedes_any_input_or_parser_access(tmp_path, monkeypatch):
    original = plan(tmp_path)
    finite_driver(monkeypatch, original)
    def mismatch(*args): raise ValueError('native_software_mismatch')
    monkeypatch.setattr(driver, 'verify_fluorescence_software', mismatch)
    monkeypatch.setattr(driver, '_retained_input', lambda *args: pytest.fail('input opened before software validation'))
    with pytest.raises(ValueError, match='native_software_mismatch'): driver.run_fluorescence_driver(original)
    assert not output(original, 'event_input:0').exists()


def test_real_software_verifier_does_not_accept_declaration_fixture():
    with pytest.raises(ValueError, match='native_software_mismatch'):
        driver.verify_fluorescence_software(software())


def test_no_replacement_or_partial_final_file_on_publication_failure(tmp_path, monkeypatch):
    target = tmp_path / 'batch.json'
    immutable_bytes(target, b'original')
    with pytest.raises(FileExistsError): immutable_bytes(target, b'replacement')
    assert target.read_bytes() == b'original'
    assert not list(tmp_path.glob('*.writing'))
    new = tmp_path / 'unpublished.json'
    def interrupted(*args): raise OSError(errno.ENOSPC, 'fixture scratch failure')
    monkeypatch.setattr('gene_annotation_episode.native_fluorescence_storage.os.fsync', interrupted)
    with pytest.raises(OSError): immutable_bytes(new, b'partial')
    assert not new.exists()


class SelectedState:
    run_id, episode_id = 'run-fixture', 'episode-fixture'
    def __init__(self, assignment, operation_key):
        self.assignment = assignment
        self.pending = {'operation_key': operation_key, 'tool_name': 'practical.job.start',
            'run_id': self.run_id, 'episode_id': self.episode_id, 'assignment_sha256': digest(assignment)}
    @contextmanager
    def _locked(self): yield
    def _load(self): return None, None, None, None, self.pending


def test_selected_reservation_reuses_exact_handle_and_public_native_request(tmp_path, monkeypatch):
    initial = plan(tmp_path)
    assignment = {'requested_job': initial['requested_job'], 'resource_kind': 'local',
        'resource_id': 'declared-local', 'workspace': str(tmp_path / 'workspace'), 'constraints': {}}
    operation_key = initial['identity']['operation_key']
    state = SelectedState(assignment, operation_key)
    root = Path(initial['identity']['execution_id']).parent
    calls = []
    def reserve(command, *, cwd, policy, handle_path, env):
        calls.append(list(command))
        original = read_json(root / 'fluorescence-plan.json')
        paths = {k: str(root / ('fixture.' + k)) for k in ('request', 'ready', 'release', 'status', 'result', 'launcher')}
        request = local.fluorescence_native_request(original, paths)
        assert request['command'] == command and request['env'] == env
        immutable_json(paths['request'], request)
        for role in ('stdout', 'stderr'): (root / (role + '.log')).write_bytes(b'')
        immutable_json(handle_path, {'version': native.VERSION, 'stage': 'prepared', 'command': command,
            'cwd': str(cwd), 'metadata': {'policy': policy.to_dict()}, 'paths': paths,
            'stdout': str(root / 'stdout.log'), 'stderr': str(root / 'stderr.log'),
            'request_sha256': identity(Path(paths['request']).read_bytes(), format='json')['sha256']})
        return native.NativeJobHandle(Path(handle_path))
    monkeypatch.setattr(native, 'prepare_job', reserve)
    monkeypatch.setattr(native, 'start_prepared', lambda *args: pytest.fail('preparation dispatched a process'))
    first = local.prepare_local_fluorescence(state, operation_key, root=root, policy=LocalJobPolicy(**POLICY))
    before = first.path.read_bytes()
    assert local.prepare_local_fluorescence(state, operation_key, root=root, policy=LocalJobPolicy(**POLICY)).path == first.path
    assert first.path.read_bytes() == before and len(calls) == 1
    original = local.local_fluorescence_plan(assignment, str(first.path))
    assert original['identity']['assignment_sha256'] == digest(assignment)
    state.pending = None
    with pytest.raises(ValueError, match='pending_start_required'):
        local.prepare_local_fluorescence(state, operation_key, root=root, policy=LocalJobPolicy(**POLICY))
    paths = read_json(first.path)['paths']
    changed = read_json(paths['request'])
    changed['env']['PYTHONPATH'] = '/substituted'
    Path(paths['request']).write_bytes(canonical(changed) + b'\n')
    with pytest.raises(ValueError, match='original_attempt_mismatch'):
        local.local_fluorescence_plan(assignment, str(first.path))
