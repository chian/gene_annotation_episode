"""Original manifest qualification, complete custody and offline replay."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.native_blast_acquisition import (
    VERSION, ORIGIN, capture_local_bundle, is_native_blast_target,
    original_source_payload, publish_original_source, validate_original_bundle,
)
from gene_annotation_episode.native_blast_contracts import requested_job_from_native
from gene_annotation_episode.state import Store
from test_blast_local_lifecycle import EXAMPLES, LABELS, launch, request


def retained(label=LABELS[0]):
    plan = json.loads((EXAMPLES / label / 'plan.json').read_bytes())
    return plan, json.loads((Path(plan['attempt_directory']) / 'bundle.json').read_bytes())


@pytest.mark.parametrize('label', LABELS)
def test_exact_retained_five_program_manifests_are_qualified_without_io(label, monkeypatch):
    plan, bundle = retained(label)
    def forbidden(*args, **kwargs): pytest.fail('pure manifest qualification performed I/O')
    for method in ('open', 'read_bytes', 'resolve', 'stat'):
        monkeypatch.setattr(Path, method, forbidden)
    assert validate_original_bundle(bundle, plan) == bundle


@pytest.mark.parametrize('fault', ['extra', 'identity', 'request', 'program', 'mode', 'software',
    'software_actual', 'argv', 'environment', 'bindings', 'input_duplicate', 'input_path_swap',
    'input_path_escape', 'input_original', 'input_size', 'input_hash', 'output_duplicate',
    'output_path_swap', 'output_escape', 'output_format', 'output_size', 'output_hash',
    'missing_success_output', 'timestamp', 'time_order', 'unsealed', 'failure_shape', 'returncode',
    'input_role_type', 'output_role_type', 'failure_wrong_output', 'failure_wrong_returncode',
    'executed_wrong_input', 'missing_failed_output_reason'])
def test_manifest_conflicts_do_not_become_valid_original_results(fault):
    plan, bundle = retained()
    if fault == 'extra': bundle['fabricated_fields'] = []
    elif fault == 'identity': bundle['identity']['episode_id'] = 'other'
    elif fault == 'request': bundle['requested_job']['native_blast']['metadata']['changed'] = True
    elif fault == 'program': bundle['program'] = 'blastp'
    elif fault == 'mode': bundle['mode'] = 'database'
    elif fault == 'software': bundle['software']['declared_engine_version'] = 'other'
    elif fault == 'software_actual': bundle['software']['actual_sha256'] = '0' * 64
    elif fault == 'argv': bundle['realized_argv'][-1] = '/outside/report.json'
    elif fault == 'environment': bundle['environment']['TMPDIR'] = '/tmp'
    elif fault == 'bindings': bundle['operand_bindings'] = []
    elif fault == 'input_duplicate': bundle['inputs'][1] = deepcopy(bundle['inputs'][0])
    elif fault == 'input_path_swap':
        first, second = bundle['inputs']; first['relative_path'], second['relative_path'] = second['relative_path'], first['relative_path']
    elif fault == 'input_path_escape': bundle['inputs'][0]['relative_path'] = '../query.fa'
    elif fault == 'input_original': bundle['inputs'][0]['original_path'] += '-other'
    elif fault == 'input_size': bundle['inputs'][0]['size_bytes'] = True
    elif fault == 'input_hash': bundle['inputs'][0]['actual_sha256'] = 'bad'
    elif fault == 'output_duplicate': bundle['artifacts'].append(deepcopy(bundle['artifacts'][0]))
    elif fault == 'output_path_swap':
        first, second = bundle['artifacts'][:2]; first['relative_path'], second['relative_path'] = second['relative_path'], first['relative_path']
    elif fault == 'output_escape': bundle['artifacts'][0]['relative_path'] = '/outside'
    elif fault == 'output_format': bundle['artifacts'][-1]['format'] = 'text'
    elif fault == 'output_size': bundle['artifacts'][0]['size_bytes'] = -1
    elif fault == 'output_hash': bundle['artifacts'][0]['sha256'] = 'bad'
    elif fault == 'missing_success_output': bundle['artifacts'].pop()
    elif fault == 'timestamp': bundle['finished_at'] = 'yesterday'
    elif fault == 'time_order': bundle['finished_at'] = '1900-01-01T00:00:00+00:00'
    elif fault == 'unsealed': bundle['finished_at'] = None
    elif fault == 'failure_shape': bundle['failures'] = [{'code': 'failed'}]
    elif fault == 'returncode': bundle['returncode'] = None
    elif fault == 'input_role_type': bundle['inputs'][0]['role'] = []
    elif fault == 'output_role_type': bundle['artifacts'][0]['role'] = []
    elif fault == 'failure_wrong_output':
        bundle['failures'] = [{'stage': 'outputs', 'code': 'native_blast_missing_output',
            'role': 'primary_report', 'detail': {'relative_path': 'other'}}]
    elif fault == 'failure_wrong_returncode':
        bundle['returncode'] = 2
        bundle['failures'] = [{'stage': 'execution', 'code': 'native_blast_nonzero_returncode',
            'role': None, 'detail': {'returncode': 3}}]
    elif fault == 'executed_wrong_input':
        bundle['inputs'][0]['actual_sha256'] = '0' * 64
        bundle['failures'] = [{'stage': 'inputs', 'code': 'native_blast_input_digest_mismatch',
            'role': 'query_sequence', 'detail': {}}]
    elif fault == 'missing_failed_output_reason':
        bundle['returncode'] = 2; bundle['artifacts'].pop()
        bundle['failures'] = [{'stage': 'execution', 'code': 'native_blast_nonzero_returncode',
            'role': None, 'detail': {'returncode': 2}}]
    with pytest.raises(ValueError):
        validate_original_bundle(bundle, plan)


def test_real_complete_capture_source_and_replay_use_retained_bytes(tmp_path, monkeypatch):
    origin = launch(tmp_path)
    bundle = json.loads((origin.root / 'bundle.json').read_bytes())
    with Store(tmp_path / 'store') as store:
        capture = capture_local_bundle(store, target=origin.target, directory=tmp_path / 'capture')
        assert set(capture) == {'version', 'bundle_artifact_ref', 'bundle_validated',
            'artifacts', 'invalid_artifacts', 'failures', 'complete'}
        assert capture['version'] == VERSION and capture['complete'] and capture['bundle_validated']
        assert len(capture['artifacts']) == 5 and not capture['invalid_artifacts'] and not capture['failures']
        expected = {row['relative_path']: (row['actual_sha256'], row['size_bytes']) for row in bundle['inputs']}
        expected.update({row['relative_path']: (row['sha256'], row['size_bytes']) for row in bundle['artifacts']})
        for row in capture['artifacts']:
            recorded = store.get(row['artifact_ref'])
            assert (recorded['sha256'], recorded['size']) == expected[row['relative_path']]
            assert artifact_path(store, row['artifact_ref']).read_bytes() == (origin.root / row['relative_path']).read_bytes()
        prepared = {'source_grading_artifact_ref': store.artifact(b'fixture prepared source', 'application/json')}
        payload = original_source_payload(bundle=bundle, capture=capture, prepared=prepared)
        reference = publish_original_source(store, bundle=bundle, capture=capture, prepared=prepared)
        source = store.get(reference)
        assert all(source[key] == value for key, value in payload.items())
        assert source['retrieved_at'] == bundle['finished_at']
        assert source['version'] == 'native_blast_bundle_v1' and source['artifact_ref'] == capture['bundle_artifact_ref']
        assert source['uri'] is source['text_ref'] is source['request_ref'] is None
        assert source['auxiliary_artifact_refs'] == sorted({row['artifact_ref'] for row in capture['artifacts']} |
            {prepared['source_grading_artifact_ref']})
        assert ORIGIN['content_location'] == 'retained_complete_producer_bundle'
        (tmp_path / 'capture-example.json').write_text(json.dumps({'capture': capture, 'source': payload,
            'expected_original_hashes_and_lengths': expected}, indent=2) + '\n')
        # Remove the live job location entirely. Replay must not depend on it.
        origin.handle.path.parent.rename(origin.handle.path.parent.with_name('offline-original-attempt'))
        monkeypatch.setattr('gene_annotation_episode.native_blast_acquisition.local_blast_plan',
            lambda *a, **k: pytest.fail('replay read the live attempt'))
        monkeypatch.setattr(native, 'start_prepared', lambda *a, **k: pytest.fail('capture submitted work'))
        assert capture_local_bundle(store, target=origin.target, directory=tmp_path / 'capture') == capture


@pytest.mark.parametrize('field', ['run_id', 'origin_episode_id', 'resource_id', 'request_sha256',
    'original_operation_key', 'attempt_id'])
def test_capture_rejects_different_original_owner_even_with_same_program(tmp_path, field):
    origin = launch(tmp_path)
    target = deepcopy(origin.target); target[field] = '0' * 64 if field == 'request_sha256' else 'other'
    with Store(tmp_path / 'store') as store, pytest.raises(ValueError, match='original_target_owner_conflict'):
        capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
    assert len(list(tmp_path.rglob('native.json'))) == 1


@pytest.mark.parametrize('role', ['query_sequence', 'subject_sequence', 'primary_report', 'stderr'])
def test_changed_staged_input_or_sealed_output_is_retained_as_invalid(tmp_path, role):
    origin = launch(tmp_path)
    bundle = json.loads((origin.root / 'bundle.json').read_bytes())
    original = next(row for row in bundle['inputs'] + bundle['artifacts'] if row['role'] == role)
    path = origin.root / original['relative_path']; wrong = path.read_bytes() + b'changed after seal\n'
    path.write_bytes(wrong)
    with Store(tmp_path / 'store') as store:
        capture = capture_local_bundle(store, target=origin.target, directory=tmp_path / 'capture')
        assert capture['bundle_validated'] and not capture['complete']
        invalid, = capture['invalid_artifacts']
        assert invalid['role'] == role and store.get_artifact(invalid['artifact_ref']) == wrong
        assert len(capture['artifacts']) == 4
        assert capture['failures'][0]['code'].startswith('native_blast_sealed_artifact_digest_mismatch:')
        path.write_bytes(b'repaired live bytes are not recaptured')
        assert capture_local_bundle(store, target=origin.target, directory=tmp_path / 'capture') == capture


@pytest.mark.parametrize('fault', ['missing_bundle', 'malformed_bundle', 'missing_output', 'escaped_output'])
def test_partial_acquisition_preserves_original_files_and_immutable_failure(tmp_path, fault):
    origin = launch(tmp_path)
    manifest = origin.root / 'bundle.json'
    bundle = json.loads(manifest.read_bytes())
    report = origin.root / next(row['relative_path'] for row in bundle['artifacts'] if row['role'] == 'primary_report')
    if fault == 'missing_bundle': manifest.rename(origin.root / 'withheld-bundle.json')
    elif fault == 'malformed_bundle': manifest.write_bytes(b'{malformed')
    elif fault == 'missing_output': report.unlink()
    else:
        outside = tmp_path / 'outside'; outside.write_bytes(b'outside bytes must not be captured')
        report.unlink(); report.symlink_to(outside)
    with Store(tmp_path / 'store') as store:
        capture = capture_local_bundle(store, target=origin.target, directory=tmp_path / 'capture')
        assert not capture['complete'] and capture['failures']
        assert {row['role'] for row in capture['artifacts']} >= {'query_sequence', 'subject_sequence'}
        assert all(row['record_key'] is None and set(row) == {'stage', 'code', 'record_key'} for row in capture['failures'])
        if fault in {'missing_bundle', 'malformed_bundle'}:
            assert not capture['bundle_validated'] and len(capture['invalid_artifacts']) == 3
        else:
            assert capture['bundle_validated'] and not capture['invalid_artifacts']
        assert capture_local_bundle(store, target=origin.target, directory=tmp_path / 'capture') == capture
        assert len(list(tmp_path.rglob('native.json'))) == 1


@pytest.mark.parametrize('fault', ['missing', 'changed', 'intent'])
def test_replay_detects_missing_changed_retained_bytes_or_changed_target(tmp_path, fault):
    origin = launch(tmp_path)
    with Store(tmp_path / 'store') as store:
        capture = capture_local_bundle(store, target=origin.target, directory=tmp_path / 'capture')
        target = deepcopy(origin.target)
        if fault == 'intent': target['run_id'] = 'different'
        else:
            path = artifact_path(store, capture['bundle_artifact_ref'])
            if fault == 'missing': path.unlink()
            else: path.write_bytes(b'altered retained bytes')
        with pytest.raises((ValueError, OSError)):
            capture_local_bundle(store, target=target, directory=tmp_path / 'capture')
        assert len(list(tmp_path.rglob('native.json'))) == 1


def test_empty_successful_native_report_and_malformed_report_bytes_are_capture_only(tmp_path):
    origin = launch(tmp_path, label='blastn_no_hits_tabular6')
    manifest = origin.root / 'bundle.json'
    bundle = json.loads(manifest.read_bytes())
    report_row = next(row for row in bundle['artifacts'] if row['role'] == 'primary_report')
    assert report_row['size_bytes'] == 0
    with Store(tmp_path / 'store') as store:
        empty = capture_local_bundle(store, target=origin.target, directory=tmp_path / 'empty-capture')
        assert empty['complete'] and origin.result.returncode == 0
        # Synthetic corruption with a synthetic matching manifest verifies
        # custody/parser separation; these bytes are not a native measurement.
        malformed = b'\xffnot a native tabular report\x00'
        (origin.root / report_row['relative_path']).write_bytes(malformed)
        report_row.update(size_bytes=len(malformed), sha256=hashlib.sha256(malformed).hexdigest())
        manifest.write_text(json.dumps(bundle))
        captured = capture_local_bundle(store, target=origin.target, directory=tmp_path / 'synthetic-malformed-capture')
        assert captured['complete']
        report = next(row for row in captured['artifacts'] if row['role'] == 'primary_report')
        assert store.get_artifact(report['artifact_ref']) == malformed


def test_native_failure_can_have_complete_partial_output_custody(tmp_path):
    job = request(LABELS[1])['native_blast']
    job['options'] += ['-matrix', 'NOT_A_NATIVE_MATRIX']
    origin = launch(tmp_path, selected=requested_job_from_native(job))
    assert origin.result.returncode != 0
    bundle = json.loads((origin.root / 'bundle.json').read_bytes())
    assert bundle['returncode'] != 0 and bundle['failures']
    with Store(tmp_path / 'store') as store:
        capture = capture_local_bundle(store, target=origin.target, directory=tmp_path / 'capture')
        assert capture['bundle_validated'] and capture['complete']
        assert len(capture['artifacts']) == len(bundle['inputs']) + len(bundle['artifacts'])
        assert not capture['failures']  # Native failure is preserved in the original bundle.


def test_native_input_mismatch_keeps_actual_wrong_staged_bytes_invalid(tmp_path):
    job = request()['native_blast']; job['operands'][0]['sha256'] = '0' * 64
    origin = launch(tmp_path, selected=requested_job_from_native(job))
    assert origin.result.returncode != 0
    bundle = json.loads((origin.root / 'bundle.json').read_bytes())
    assert bundle['returncode'] is None
    with Store(tmp_path / 'store') as store:
        capture = capture_local_bundle(store, target=origin.target, directory=tmp_path / 'capture')
        assert capture['bundle_validated'] and not capture['complete']
        invalid, = capture['invalid_artifacts']
        assert invalid['role'] == 'query_sequence'
        assert [row['role'] for row in capture['artifacts']] == ['subject_sequence']


def test_only_explicit_local_native_blast_targets_are_selected():
    selected = {'resource_kind': 'local', 'assignment': {'requested_job': request()}}
    assert is_native_blast_target(selected)
    assert not is_native_blast_target({**selected, 'resource_kind': 'hpc'})
    assert not is_native_blast_target({'resource_kind': 'local', 'assignment': {'requested_job': {'argv': ['blastn']}}})


def test_source_and_saved_receipt_cannot_swap_valid_artifact_associations(tmp_path):
    from gene_annotation_episode.practical_execution_records import canonical
    origin = launch(tmp_path)
    bundle = json.loads((origin.root / 'bundle.json').read_bytes())
    with Store(tmp_path / 'store') as store:
        capture = capture_local_bundle(store, target=origin.target, directory=tmp_path / 'capture')
        other_bundle = deepcopy(bundle); other_bundle['identity']['run_id'] = 'other'
        with pytest.raises(ValueError, match='source_bundle_association_conflict'):
            publish_original_source(store, bundle=other_bundle, capture=capture, prepared=None)
        altered = deepcopy(capture)
        altered['artifacts'][0]['artifact_ref'] = altered['artifacts'][1]['artifact_ref']
        with pytest.raises(ValueError, match='artifact_association_conflict'):
            publish_original_source(store, bundle=bundle, capture=altered, prepared=None)
        # A canonical JSON rewrite is not allowed to change retained meaning.
        (tmp_path / 'capture/capture.json').write_text(canonical(altered) + '\n')
        with pytest.raises(ValueError, match='artifact_association_conflict'):
            capture_local_bundle(store, target=origin.target, directory=tmp_path / 'capture')
