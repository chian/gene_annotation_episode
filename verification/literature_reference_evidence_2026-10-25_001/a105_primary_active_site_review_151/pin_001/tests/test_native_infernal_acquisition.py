"""Original-attempt custody, with synthetic and already retained native bytes.

Synthetic plan lookup is explicitly stubbed; real retained cases also exercise
the actual local plan reader. Nothing in this suite executes Infernal.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess

import pytest

from gene_annotation_episode import native_infernal_acquisition as acquisition
from gene_annotation_episode.native_infernal_contracts import (compile_native_infernal_job,
    native_infernal_digest as digest, requested_job_from_infernal)
from gene_annotation_episode.practical_execution_state import canonical
from gene_annotation_episode.state import Store


FIXTURES = Path(__file__).parent / 'fixtures/native_infernal_acquisition'
NATIVE_INDEX = Path(__file__).resolve().parents[1] / (
    'verification/tool_graders_infernal_native_execution_2026-10-26_222/runs/index.json')


def forbidden(*args, **kwargs):
    raise AssertionError('execution, network, grading or reacquisition is forbidden')


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def sealed_case(tmp_path, monkeypatch, program='cmsearch'):
    workspace = tmp_path / 'workspace'
    identity = {'run_id': 'synthetic-acquisition', 'episode_id': 'local-child',
        'resource_id': 'local', 'operation_key': 'selected-original-operation'}
    action = workspace / '.episode-operations' / digest({
        'run': identity['run_id'], 'episode': identity['episode_id']}) / digest(identity['operation_key'])
    root = action / 'infernal-attempt'
    (root / 'inputs').mkdir(parents=True)
    identity.update(execution_id=str(action / 'native.json'), attempt_id=digest(identity['operation_key']))
    contents = {'models': (FIXTURES / 'models.cm').read_bytes(),
        'sequences': (FIXTURES / 'sequences.fa').read_bytes()}
    formats = {'models': 'infernal_ascii', 'sequences': 'fasta'}
    original = {'models': '/selected/original/models.cm', 'sequences': '/selected/original/query.fa'}
    if program == 'cmscan':
        for suffix in ('i1f', 'i1i', 'i1m', 'i1p'):
            role = 'models_' + suffix
            contents[role], formats[role] = b'\0synthetic pressed ' + suffix.encode(), 'infernal_' + suffix
            original[role] = original['models'] + '.' + suffix
    output_files = {'stdout': ('infernal_stdout', b'original synthetic stdout\n'), 'stderr': ('text', b'')}
    if program == 'cmalign':
        output_files.update(stockholm=('stockholm', b'# STOCKHOLM 1.0\nq1 ACGU\n//\n'),
            scores=('cmalign_sfile', b'# synthetic score table\n'),
            inserts=('cmalign_ifile', b'# synthetic insert table\n'),
            local_ends=('cmalign_elfile', b'# synthetic EL table\n'),
            traceback=('cmalign_tfile', b'# synthetic traceback\n'))
    else:
        output_files['tblout'] = ('infernal_tblout', (FIXTURES / 'hits.tblout').read_bytes())
        if program == 'cmsearch':
            output_files['included_msa'] = ('stockholm', b'# STOCKHOLM 1.0\n//\n')
    job = {'version': 'native_infernal_job_v1', 'program': program,
        'software': {'executable': '/selected/bin/' + program, 'sha256': 'a' * 64, 'engine_version': None},
        'environment': {'LC_ALL': 'C'}, 'options': ['--cpu', '1'],
        'table_format': None if program == 'cmalign' else 2 if program == 'cmscan' else 3,
        'operands': [{'role': role, 'format': formats[role], 'path': original[role],
            'artifact_ref': None, 'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data)}
            for role, data in contents.items()],
        'operand_bindings': [{'operand_role': 'sequences', 'record_ordinal': 0,
            'native_name': 'q1', 'native_accession': None, 'subject_ref': None, 'reference_ref': None}],
        'outputs': [{'role': role, 'format': fmt, 'relative_path': 'outputs/' + role}
            for role, (fmt, _) in output_files.items()], 'metadata': {'known_zero': 0, 'unknown': None},
        'grading_parameters': {}}
    request = requested_job_from_infernal(job)
    identity['requested_job_sha256'] = digest(request)
    plan = {'version': 'native_infernal_run_plan_v1', 'identity': identity,
        'requested_job': request, 'attempt_directory': str(root),
        'policy': {'memory_bytes': 20 * 1024**3, 'scratch_bytes': 4 * 1024**3, 'wall_seconds': None}}
    inputs = []
    for operand in job['operands']:
        relative = acquisition._staged_relative(operand)
        (root / relative).write_bytes(contents[operand['role']])
        inputs.append({'role': operand['role'], 'format': operand['format'],
            'original_path': operand['path'], 'relative_path': relative, 'artifact_ref': operand['artifact_ref'],
            'expected_sha256': operand['sha256'], 'actual_sha256': operand['sha256'],
            'expected_size_bytes': operand['size_bytes'], 'size_bytes': operand['size_bytes']})
    artifacts = []
    for output in job['outputs']:
        data = output_files[output['role']][1]
        path = root / output['relative_path']
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(data)
        artifacts.append({**output, 'size_bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    compiled = compile_native_infernal_job(job, input_paths={row['role']: str(root / row['relative_path'])
        for row in inputs}, output_directory=str(root))
    bundle = {'version': 'native_infernal_bundle_v1', 'identity': deepcopy(identity),
        'requested_job': deepcopy(request), 'program': program, 'table_format': job['table_format'],
        'software': {'executable': job['software']['executable'], 'expected_sha256': 'a' * 64,
            'actual_sha256': 'a' * 64, 'declared_engine_version': None},
        'realized_argv': compiled['argv'], 'environment': {**compiled['environment'],
            **{key: str(root / 'tmp') for key in ('TMPDIR', 'TMP', 'TEMP')}, 'XDG_CACHE_HOME': str(root / 'cache')},
        'inputs': inputs, 'operand_bindings': deepcopy(job['operand_bindings']),
        'returncode': 0, 'artifacts': artifacts, 'failures': [],
        'started_at': '2026-10-26T01:00:00+00:00', 'finished_at': '2026-10-26T01:00:01+00:00'}
    write_json(root / 'bundle.json', bundle)
    assignment = {'resource_kind': 'local', 'resource_id': 'local', 'workspace': str(workspace),
        'requested_job': deepcopy(request)}
    target = make_target(plan, assignment)
    monkeypatch.setattr(acquisition, 'local_infernal_plan', lambda *args: deepcopy(plan))
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    return root, plan, bundle, target


def make_target(plan, assignment):
    identity = plan['identity']
    return {'version': 'execution_target_v1', 'handle': 'source_original_handoff',
        'run_id': identity['run_id'], 'origin_episode_id': identity['episode_id'],
        'resource_kind': 'local', 'resource_id': identity['resource_id'],
        'execution_id': identity['execution_id'], 'request_sha256': identity['requested_job_sha256'],
        'assignment': assignment, 'scope': {}}


@pytest.mark.parametrize('program', ['cmsearch', 'cmscan', 'cmalign'])
def test_complete_original_capture_and_saved_replay_without_originals(tmp_path, monkeypatch, program):
    root, plan, bundle, target = sealed_case(tmp_path, monkeypatch, program)
    with Store(tmp_path / 'state') as store:
        captured = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        assert captured['bundle_validated'] and captured['complete'], captured['failures']
        assert captured['failures'] == captured['invalid_artifacts'] == []
        assert len(captured['artifacts']) == len(bundle['inputs']) + len(bundle['artifacts'])
        assert store.get_artifact(captured['bundle_artifact_ref']) == (root / 'bundle.json').read_bytes()
        for row in captured['artifacts']:
            assert store.get_artifact(row['artifact_ref']) == (root / row['relative_path']).read_bytes()
        retained = json.loads(store.get_artifact(captured['bundle_artifact_ref']))
        assert retained['returncode'] == 0 and retained['software']['declared_engine_version'] is None
        assert retained['requested_job']['native_infernal']['metadata'] == {'known_zero': 0, 'unknown': None}
        stderr = next(row for row in captured['artifacts'] if row['role'] == 'stderr')
        assert store.get(stderr['artifact_ref'])['size'] == 0
        shutil.rmtree(root.parent)
        monkeypatch.setattr(acquisition, 'local_infernal_plan', forbidden)
        monkeypatch.setattr(acquisition, 'artifact_file', forbidden)
        assert acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture') == captured


def test_pure_validation_copies_and_does_no_io(tmp_path, monkeypatch):
    _, plan, bundle, _ = sealed_case(tmp_path, monkeypatch)
    monkeypatch.setattr(Path, 'open', forbidden)
    monkeypatch.setattr(Path, 'stat', forbidden)
    result = acquisition.validate_original_bundle(bundle, plan)
    result['requested_job']['native_infernal']['metadata']['changed'] = True
    assert 'changed' not in bundle['requested_job']['native_infernal']['metadata']


@pytest.mark.parametrize('field', ['run_id', 'episode_id', 'resource_id', 'execution_id', 'operation_key',
    'attempt_id', 'requested_job_sha256'])
def test_every_original_identity_field_is_bound(tmp_path, monkeypatch, field):
    _, plan, bundle, _ = sealed_case(tmp_path, monkeypatch)
    bundle['identity'][field] = 'wrong-original-job'
    with pytest.raises(ValueError, match='identity_conflict'):
        acquisition.validate_original_bundle(bundle, plan)


@pytest.mark.parametrize('fault', ['request', 'program', 'format', 'binding', 'software_hash', 'software_name',
    'software_version', 'input_role', 'input_format', 'input_original_path', 'input_staged_path',
    'input_expected_hash', 'input_expected_size', 'input_actual_hash', 'input_actual_size', 'input_unknown',
    'input_duplicate', 'output_role', 'output_format', 'output_path', 'output_duplicate', 'hash_type',
    'hash_uppercase', 'size_bool', 'size_negative', 'argv', 'environment', 'returncode_bool',
    'started_missing', 'finished_naive', 'backwards_time', 'failure_stage', 'failure_role', 'nonfinite'])
def test_manifest_rejects_wrong_associations_and_typed_measurements(tmp_path, monkeypatch, fault):
    _, plan, bundle, _ = sealed_case(tmp_path, monkeypatch)
    if fault == 'request':
        bundle['requested_job']['native_infernal']['metadata']['wrong'] = 1
    elif fault in {'program', 'format', 'binding'}:
        bundle[{'program': 'program', 'format': 'table_format', 'binding': 'operand_bindings'}[fault]] = 'wrong'
    elif fault.startswith('software_'):
        bundle['software'][{'hash': 'actual_sha256', 'name': 'executable', 'version': 'declared_engine_version'}[
            fault.removeprefix('software_')]] = 'b' * 64
    elif fault.startswith('input_'):
        key = fault.removeprefix('input_')
        if key == 'duplicate':
            bundle['inputs'][1] = deepcopy(bundle['inputs'][0])
        elif key == 'unknown':
            bundle['inputs'][0].update(actual_sha256=None, size_bytes=None)
        else:
            field = {'role': 'role', 'format': 'format', 'original_path': 'original_path',
                'staged_path': 'relative_path', 'expected_hash': 'expected_sha256', 'expected_size': 'expected_size_bytes',
                'actual_hash': 'actual_sha256', 'actual_size': 'size_bytes'}[key]
            bundle['inputs'][0][field] = 0 if 'size' in key else 'b' * 64
    elif fault.startswith('output_'):
        key = fault.removeprefix('output_')
        if key == 'duplicate':
            bundle['artifacts'][1] = deepcopy(bundle['artifacts'][0])
        else:
            bundle['artifacts'][0][{'role': 'role', 'format': 'format', 'path': 'relative_path'}[key]] = 'wrong'
    elif fault.startswith('hash_'):
        bundle['artifacts'][0]['sha256'] = 1 if fault == 'hash_type' else 'A' * 64
    elif fault.startswith('size_'):
        bundle['artifacts'][0]['size_bytes'] = True if fault == 'size_bool' else -1
    elif fault in {'argv', 'environment'}:
        bundle['realized_argv' if fault == 'argv' else 'environment'] = []
    elif fault == 'returncode_bool':
        bundle['returncode'] = False
    elif fault in {'started_missing', 'finished_naive', 'backwards_time'}:
        bundle['started_at' if fault == 'started_missing' else 'finished_at'] = {
            'started_missing': None, 'finished_naive': '2026-10-26T01:00:01',
            'backwards_time': '2026-10-25T01:00:01+00:00'}[fault]
    elif fault.startswith('failure_'):
        bundle['failures'] = [{'stage': 'made_up' if fault == 'failure_stage' else 'inputs',
            'code': 'test', 'role': 'unselected', 'detail': {}}]
    else:
        bundle['failures'] = [{'stage': 'execution', 'code': 'test', 'role': None, 'detail': {'x': float('nan')}}]
    with pytest.raises(ValueError):
        acquisition.validate_original_bundle(bundle, plan)


@pytest.mark.parametrize('role', ['stdout', 'included_msa'])
def test_success_requires_every_selected_output(tmp_path, monkeypatch, role):
    _, plan, bundle, _ = sealed_case(tmp_path, monkeypatch)
    bundle['artifacts'] = [row for row in bundle['artifacts'] if row['role'] != role]
    with pytest.raises(ValueError, match='successful_bundle_missing_outputs'):
        acquisition.validate_original_bundle(bundle, plan)


@pytest.mark.parametrize('field', ['run_id', 'origin_episode_id', 'resource_id', 'execution_id', 'request_sha256'])
def test_target_identity_cannot_substitute_original_job(tmp_path, monkeypatch, field):
    _, _, _, target = sealed_case(tmp_path, monkeypatch)
    target[field] = 'f' * 64
    with Store(tmp_path / 'state') as store, pytest.raises(ValueError, match='original_target_conflict'):
        acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')


@pytest.mark.parametrize('fault', ['hash', 'size', 'missing', 'symlink', 'directory', 'fifo', 'parent_symlink'])
@pytest.mark.parametrize('category', ['inputs', 'artifacts'])
def test_custody_fault_keeps_valid_siblings_and_mismatched_bytes(tmp_path, monkeypatch, fault, category):
    root, _, bundle, target = sealed_case(tmp_path, monkeypatch)
    selected = bundle[category][0]
    path, raw = root / selected['relative_path'], (root / selected['relative_path']).read_bytes()
    if fault == 'hash':
        path.write_bytes(b'!' + raw[1:])
    elif fault == 'size':
        path.write_bytes(raw + b'extra')
    elif fault == 'parent_symlink':
        destination = tmp_path / 'outside'
        shutil.move(path.parent, destination)
        path.parent.symlink_to(destination, target_is_directory=True)
    else:
        path.unlink()
        if fault == 'symlink':
            outside = tmp_path / 'outside'
            outside.write_bytes(raw)
            path.symlink_to(outside)
        elif fault == 'directory':
            path.mkdir()
        elif fault == 'fifo':
            os.mkfifo(path)
    with Store(tmp_path / 'state') as store:
        capture = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        assert capture['bundle_validated'] and not capture['complete'] and capture['failures']
        assert capture['artifacts']
        assert not any(row['role'] == selected['role'] for row in capture['artifacts'])
        if fault in {'hash', 'size'}:
            invalid, = capture['invalid_artifacts']
            assert store.get_artifact(invalid['artifact_ref']) == path.read_bytes()
        else:
            assert capture['invalid_artifacts'] == []
        shutil.rmtree(root)
        monkeypatch.setattr(acquisition, 'artifact_file', forbidden)
        monkeypatch.setattr(acquisition, 'local_infernal_plan', forbidden)
        assert acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture') == capture


@pytest.mark.parametrize('raw', [b'{', b'null', b'[]', b'\xff', b'{"version":1,"version":2}', b'{"a":NaN}'])
def test_malformed_manifest_bytes_are_retained_and_replayable(tmp_path, monkeypatch, raw):
    root, _, _, target = sealed_case(tmp_path, monkeypatch)
    (root / 'bundle.json').write_bytes(raw)
    with Store(tmp_path / 'state') as store:
        capture = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        assert not capture['bundle_validated'] and not capture['complete']
        assert capture['artifacts'] == capture['invalid_artifacts'] == []
        assert store.get_artifact(capture['bundle_artifact_ref']) == raw
        shutil.rmtree(root)
        monkeypatch.setattr(acquisition, 'local_infernal_plan', forbidden)
        assert acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture') == capture


def failed_case(root, bundle, *, missing_input=False, partial_input=False):
    bundle['returncode'] = None if missing_input or partial_input else 7
    bundle['failures'] = [] if bundle['returncode'] is None else [
        {'stage': 'execution', 'code': 'native_infernal_nonzero_returncode', 'role': None,
            'detail': {'returncode': 7}}]
    for row in list(bundle['artifacts']):
        if row['role'] in {'tblout', 'included_msa'}:
            (root / row['relative_path']).unlink()
            bundle['artifacts'].remove(row)
            bundle['failures'].append({'stage': 'outputs', 'code': 'native_infernal_missing_output',
                'role': row['role'], 'detail': {'relative_path': row['relative_path']}})
    if missing_input or partial_input:
        row = bundle['inputs'][1]
        if missing_input:
            (root / row['relative_path']).unlink()
            row.update(actual_sha256=None, size_bytes=None)
        else:
            (root / row['relative_path']).write_bytes(b'>q1\n')
            row.update(actual_sha256=hashlib.sha256(b'>q1\n').hexdigest(), size_bytes=4)
        bundle['failures'].append({'stage': 'inputs', 'code': 'native_infernal_input_missing'
            if missing_input else 'native_infernal_input_size_mismatch', 'role': row['role'], 'detail': {}})
    write_json(root / 'bundle.json', bundle)


@pytest.mark.parametrize('condition', ['native_nonzero', 'missing_input', 'partial_input'])
def test_failed_original_attempt_retains_known_partial_and_unknown_measurements(tmp_path, monkeypatch, condition):
    root, plan, bundle, target = sealed_case(tmp_path, monkeypatch)
    failed_case(root, bundle, missing_input=condition == 'missing_input', partial_input=condition == 'partial_input')
    assert acquisition.validate_original_bundle(bundle, plan) == bundle
    with Store(tmp_path / 'state') as store:
        capture = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        assert capture['bundle_validated'] and capture['complete'] and capture['failures'] == []
        retained = json.loads(store.get_artifact(capture['bundle_artifact_ref']))
        assert retained == bundle
        assert len(capture['artifacts']) == len(bundle['inputs']) + len(bundle['artifacts']) - (
            condition == 'missing_input')
        shutil.rmtree(root)
        monkeypatch.setattr(acquisition, 'local_infernal_plan', forbidden)
        assert acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture') == capture


def test_unlisted_selected_file_is_retained_separately(tmp_path, monkeypatch):
    root, _, bundle, target = sealed_case(tmp_path, monkeypatch)
    failed_case(root, bundle)
    (root / 'outputs/tblout').write_bytes(b'late bytes after original sealed failure')
    with Store(tmp_path / 'state') as store:
        capture = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        assert not capture['complete'] and capture['bundle_validated']
        invalid, = capture['invalid_artifacts']
        assert invalid['role'] == 'tblout'
        assert capture['failures'][0]['code'].startswith('native_infernal_unlisted_file_present:')
        assert store.get_artifact(invalid['artifact_ref']) == b'late bytes after original sealed failure'
        assert acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture') == capture


@pytest.mark.parametrize('fault', ['wrong_reference', 'role', 'format', 'path', 'missing_row', 'duplicate',
    'misclassified_valid', 'complete', 'failure', 'manifest_reference', 'unvalidated'])
def test_replay_validates_stored_associations_not_just_file_existence(tmp_path, monkeypatch, fault):
    root, _, _, target = sealed_case(tmp_path, monkeypatch)
    with Store(tmp_path / 'state') as store:
        capture = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        changed = deepcopy(capture)
        if fault == 'wrong_reference':
            changed['artifacts'][0]['artifact_ref'] = store.artifact('unrelated data')
        elif fault in {'role', 'format', 'path'}:
            changed['artifacts'][0]['relative_path' if fault == 'path' else fault] = 'wrong'
        elif fault == 'missing_row':
            changed['artifacts'].pop()
        elif fault == 'duplicate':
            changed['artifacts'].append(deepcopy(changed['artifacts'][0]))
        elif fault == 'misclassified_valid':
            changed['invalid_artifacts'].append(changed['artifacts'].pop())
        elif fault == 'complete':
            changed['complete'] = False
        elif fault == 'failure':
            changed['failures'].append({'stage': 'capture', 'code': 'fake', 'record_key': None})
        elif fault == 'manifest_reference':
            changed['bundle_artifact_ref'] = store.artifact('{}')
        else:
            changed['bundle_validated'] = False
        (tmp_path / 'capture/capture.json').write_text(canonical(changed) + '\n')
        shutil.rmtree(root)
        monkeypatch.setattr(acquisition, 'local_infernal_plan', forbidden)
        monkeypatch.setattr(acquisition, 'artifact_file', forbidden)
        with pytest.raises(ValueError):
            acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')


@pytest.mark.parametrize('fault', ['bytes', 'stored_size', 'symlink'])
def test_replay_rejects_corrupt_retained_store_artifact(tmp_path, monkeypatch, fault):
    _, _, _, target = sealed_case(tmp_path, monkeypatch)
    with Store(tmp_path / 'state') as store:
        capture = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        reference = capture['artifacts'][0]['artifact_ref']
        path = acquisition.artifact_path(store, reference)
        if fault == 'bytes':
            path.write_bytes(path.read_bytes() + b'changed')
        elif fault == 'stored_size':
            store.db.execute('UPDATE artifacts SET size=size+1 WHERE id=?', (reference,))
        else:
            outside = tmp_path / 'outside'
            outside.write_bytes(path.read_bytes())
            path.unlink()
            path.symlink_to(outside)
        with pytest.raises((ValueError, OSError)):
            acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')


def test_capture_target_is_immutable_and_hpc_recognition_is_not_binding(tmp_path, monkeypatch):
    _, _, _, target = sealed_case(tmp_path, monkeypatch)
    assert acquisition.is_native_infernal_target(target)
    hpc = {**target, 'resource_kind': 'hpc'}
    assert acquisition.is_native_infernal_target(hpc)
    assert not acquisition.is_native_infernal_target({'resource_kind': 'api', 'assignment': target['assignment']})
    assert not acquisition.is_native_infernal_target(None)
    assert not acquisition.is_native_infernal_target({'resource_kind': []})
    with Store(tmp_path / 'state') as store:
        acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        with pytest.raises(ValueError, match='local_capture_binding_required'):
            acquisition.capture_local_bundle(store, target=hpc, directory=tmp_path / 'hpc')
        changed = {**target, 'handle': 'another-source'}
        with pytest.raises(ValueError, match='immutable_record_conflict'):
            acquisition.capture_local_bundle(store, target=changed, directory=tmp_path / 'capture')


@pytest.mark.parametrize('fault', ['missing', 'symlink'])
def test_unavailable_manifest_is_frozen_without_following_or_reacquiring(tmp_path, monkeypatch, fault):
    root, _, _, target = sealed_case(tmp_path, monkeypatch)
    path = root / 'bundle.json'
    raw = path.read_bytes()
    path.unlink()
    if fault == 'symlink':
        outside = tmp_path / 'outside.json'
        outside.write_bytes(raw)
        path.symlink_to(outside)
    with Store(tmp_path / 'state') as store:
        capture = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        assert capture['bundle_artifact_ref'] is None and not capture['bundle_validated']
        assert not capture['complete'] and capture['artifacts'] == capture['invalid_artifacts'] == []
        assert capture['failures'] == [{'stage': 'capture',
            'code': 'native_infernal_sealed_bundle_unavailable', 'record_key': None}]
        # A later file repair belongs to a new explicit acquisition selection.
        if path.is_symlink():
            path.unlink()
        path.write_bytes(raw)
        monkeypatch.setattr(acquisition, 'local_infernal_plan', forbidden)
        monkeypatch.setattr(acquisition, 'artifact_file', forbidden)
        assert acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture') == capture


def test_capture_directory_symlink_rejects_before_writing(tmp_path, monkeypatch):
    _, _, _, target = sealed_case(tmp_path, monkeypatch)
    outside = tmp_path / 'outside'
    outside.mkdir()
    (tmp_path / 'capture').symlink_to(outside, target_is_directory=True)
    with Store(tmp_path / 'state') as store, pytest.raises(ValueError, match='capture_directory_escape'):
        acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
    assert not list(outside.iterdir())


def test_source_keeps_all_captured_bytes_and_ignores_projection(tmp_path, monkeypatch):
    root, _, bundle, target = sealed_case(tmp_path, monkeypatch)
    (root / 'outputs/tblout').write_bytes(b'changed native bytes')
    with Store(tmp_path / 'state') as store:
        capture = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        grading = store.artifact('separate grading receipt')
        one = {'source_grading_artifact_ref': grading, 'selection': {'rows': [0], 'metrics': ['one']}}
        other = {'source_grading_artifact_ref': grading, 'selection': {'rows': [1], 'metrics': ['another']}}
        payload = acquisition.original_source_payload(bundle=bundle, capture=capture, prepared=one)
        assert acquisition.original_source_payload(bundle=bundle, capture=capture, prepared=other) == payload
        assert payload['accession'] == 'native_infernal_' + digest(bundle['identity'])
        assert payload['retrieved_at'] == bundle['finished_at'] and payload['text_ref'] is None
        assert payload['auxiliary_artifact_refs'] == sorted({grading, *[
            row['artifact_ref'] for row in capture['artifacts'] + capture['invalid_artifacts']]})
        first = acquisition.publish_original_source(store, bundle=bundle, capture=capture, prepared=one)
        second = acquisition.publish_original_source(store, bundle=bundle, capture=capture, prepared=other)
        assert first == second
        assert store.get(first)['origin'] == 'tool'
        changed = deepcopy(bundle)
        changed['identity']['run_id'] = 'other'
        with pytest.raises(ValueError, match='source_bundle_association_conflict'):
            acquisition.publish_original_source(store, bundle=changed, capture=capture, prepared=one)


@pytest.mark.parametrize('case', ['cmsearch', 'cmscan', 'cmalign', 'cmalign_native_failure'])
def test_actual_retained_native_producer_bundle_uses_real_plan_lookup(tmp_path, monkeypatch, case):
    if not NATIVE_INDEX.is_file():
        pytest.skip('workload 222 retained native examples are not installed')
    record = json.loads(NATIVE_INDEX.read_bytes())[case]
    action = Path(record['action_directory'])
    plan = json.loads((action / 'infernal-plan.json').read_bytes())
    assignment = json.loads((action / 'assignment.json').read_bytes())
    target = make_target(plan, assignment)
    original = Path(plan['attempt_directory'])
    bundle = json.loads((original / 'bundle.json').read_bytes())
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    with Store(tmp_path / 'state') as store:
        capture = acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        assert capture['complete'] and capture['bundle_validated'], capture['failures']
        assert len(capture['artifacts']) == len(bundle['inputs']) + len(bundle['artifacts'])
        for row in capture['artifacts']:
            assert store.get_artifact(row['artifact_ref']) == (original / row['relative_path']).read_bytes()
        source = acquisition.publish_original_source(store, bundle=bundle, capture=capture, prepared=None)
        assert store.get(source)['artifact_ref'] == capture['bundle_artifact_ref']
        monkeypatch.setattr(acquisition, 'local_infernal_plan', forbidden)
        monkeypatch.setattr(acquisition, 'artifact_file', forbidden)
        assert acquisition.capture_local_bundle(store, target=target, directory=tmp_path / 'capture') == capture
        assert bundle['returncode'] == (1 if case == 'cmalign_native_failure' else 0)
