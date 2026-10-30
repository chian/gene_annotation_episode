"""Actual Store capture of retained native427 files in synthetic producer fixtures.

Copied native tables keep their original bytes. Rebased plans, pair/batch seals,
producer actions and closure refs are explicitly synthetic capture fixtures, not
original execution authority. No test invokes a worker, bedtools, network or model.
Run through packet433's local_jobs runner, which freezes sources and native data.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import native_file_capture as shared
from gene_annotation_episode import native_genomic_overlap_capture as capture
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.native_genomic_overlap_contracts import (
    genomic_overlap_driver_argv, genomic_overlap_environment, genomic_overlap_output_files,
    validate_genomic_overlap_batch, validate_genomic_overlap_independent_pair_manifest,
    validate_genomic_overlap_run_plan,
)
from gene_annotation_episode.state import Store


PACKET = Path(__file__).resolve().parents[1] / 'verification/tool_graders_genomic_overlap_native_capture_2026-10-27_433'
ACTION_REF = 'synthetic-fixture-original-selected-action'
CLOSURE_REF = 'synthetic-fixture-terminal-writer-closure'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8') + b'\n'


def native_identity(plan):
    original = plan['identity']
    return {**{k: original[k] for k in ('run_id', 'resource_id', 'execution_id', 'attempt_id', 'operation_key')},
            'origin_episode_id': original['episode_id']}


def synthetic_producer(tmp_path, case='three'):
    fixture = PACKET / 'fixtures' / case
    original = json.loads((fixture / 'plan.json').read_bytes())
    plan = deepcopy(original)
    identity = plan['identity']
    identity.update(run_id='synthetic-capture-run', episode_id='synthetic-capture-child',
                    operation_key='synthetic-capture-original-action')
    identity['attempt_id'] = digest(identity['operation_key'])
    root = tmp_path / 'synthetic-producer' / '.episode-operations' / digest(
        {'run': identity['run_id'], 'episode': identity['episode_id']}) / identity['attempt_id']
    identity['execution_id'] = str(root / 'native.json')
    plan['attempt_directory'] = str(root / 'genomic-overlap-attempt')
    plan = validate_genomic_overlap_run_plan(plan)
    attempt = Path(plan['attempt_directory'])
    attempt.mkdir(parents=True)
    specs = plan['requested_job']['native_genomic_overlap']['outputs']
    for specification in specs:
        source = fixture / 'native' / specification['relative_path']
        if source.exists():
            target = attempt / specification['relative_path']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    environment = genomic_overlap_environment(plan['requested_job']['native_genomic_overlap'],
                                                attempt_directory=str(attempt))
    request = plan['requested_job']['native_genomic_overlap']['request']
    manifests = {}
    for pair in request['comparisons']:
        spec = next(row for row in specs if row['file_key'] == f"p{pair['ordinal']}:manifest")
        path = attempt / spec['relative_path']
        if not path.exists():
            continue
        value = json.loads(path.read_bytes())
        value['identity'] = native_identity(plan)
        if value['derivation'] == 'bedtools_intersect':
            value['environment'] = environment
            value['realized_argv'] = [item.replace(original['attempt_directory'], str(attempt)) for item in value['realized_argv']]
        validate_genomic_overlap_independent_pair_manifest(value, plan=plan, comparison=pair)
        path.write_bytes(canonical(value))
        manifests[pair['comparison_key']] = value
    batch_path = attempt / 'bundle.json'
    if batch_path.exists():
        batch = json.loads(batch_path.read_bytes())
        batch.update(identity=native_identity(plan), plan_sha256=digest(plan),
                     driver_argv=genomic_overlap_driver_argv(plan), realized_environment=environment)
        probe = batch['software_verification']['version_probe']
        if probe is not None:
            probe['environment'] = environment
        for pair in batch['pairs']:
            key = pair['comparison']['comparison_key']
            if key in manifests:
                pair['manifest'] = manifests[key]
        for row in batch['files']:
            if row['specification']['role'] == 'pair_manifest' and row['declaration']['state'] == 'present':
                raw = (attempt / row['specification']['relative_path']).read_bytes()
                row['declaration'].update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        validate_genomic_overlap_batch(batch, plan=plan)
        batch_path.write_bytes(canonical(batch))
    (tmp_path / 'SYNTHETIC_FIXTURE.json').write_bytes(canonical({
        'source_packet': '427/check005', 'case': case,
        'producer_action_authority': 'synthetic', 'closure_reference_authority': 'synthetic',
        'rebased_control_records': 'synthetic', 'native_table_bytes': 'copied_unchanged', 'original_plan': plan}))
    return plan


def collect(store, plan, *, driver_started=True, **changes):
    return capture.capture_genomic_overlap_native_files(store, original_plan=plan,
        source_action_receipt_ref=ACTION_REF, writer_closure_receipt_ref=CLOSURE_REF,
        driver_started=driver_started, **changes)


def row(value, key):
    return next(item for item in value['files'] if item['specification']['file_key'] == key)


def path(plan, key):
    specification = next(item for item in plan['requested_job']['native_genomic_overlap']['outputs'] if item['file_key'] == key)
    return Path(plan['attempt_directory']) / specification['relative_path']


def read_retained(value):
    return Path(value['retained']['path']).read_bytes()


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / 'store') as value:
        yield value


@pytest.fixture(autouse=True)
def no_execution_or_network(monkeypatch):
    def prohibited(*args, **kwargs):
        pytest.fail('native capture attempted execution or network')
    monkeypatch.setattr(subprocess, 'Popen', prohibited)
    monkeypatch.setattr(subprocess, 'run', prohibited)
    monkeypatch.setattr(socket, 'create_connection', prohibited)


def count_copies(monkeypatch):
    original = shared.capture_native_file
    calls = []
    def counted(store, **kwargs):
        calls.append((kwargs['directory'], kwargs['relative_path']))
        return original(store, **kwargs)
    monkeypatch.setattr(shared, 'capture_native_file', counted)
    return calls


def test_three_set_complete_order_actual_store_joins_and_one_copy_per_path(tmp_path, store, monkeypatch):
    plan = synthetic_producer(tmp_path)
    before = deepcopy(plan)
    calls = count_copies(monkeypatch)
    result = collect(store, plan)
    assert plan == before
    assert result['driver_state'] == 'sealed_batch' and result['driver_started'] is True
    assert result['failures'] == []
    assert result['source_action_receipt_ref'] == ACTION_REF and result['writer_closure_receipt_ref'] == CLOSURE_REF
    assert result['original_plan_sha256'] == digest(plan)
    expected = genomic_overlap_output_files(plan['requested_job']['native_genomic_overlap']['request'])
    assert [r['specification'] for r in result['files']] == expected[:-1]
    assert len(result['files']) == 25
    assert len(calls) == 23 and set(Counter(calls).values()) == {1}
    assert all(directory == plan['attempt_directory'] for directory, _ in calls)
    assert calls[0][1] == 'bundle.json'
    for item in result['files']:
        assert item['declaration_source'] == 'batch'
        if item['capture']['observed'] is not None:
            identity = item['capture']['observed']
            assert item['retained']['file'] == identity
            assert Path(item['retained']['path']) == shared.retained_native_file(store, identity)
            assert read_retained(item) == path(plan, item['specification']['file_key']).read_bytes()
    assert result['batch_file'] == result['batch']['file']
    assert Path(result['batch']['path']) == shared.retained_native_file(store, result['batch_file'])
    widths = [[int(line.split(b'\t')[-1]) for line in read_retained(row(result, f'p{i}:stdout')).splitlines()] for i in range(3)]
    assert widths == [[3, 5], [5], [2]]
    assert [sum(values) for values in widths] == [8, 5, 2]
    assert store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0] == 0
    (tmp_path / 'ACTUAL_STORE_CAPTURE.json').write_bytes(canonical(result))


@pytest.mark.parametrize('driver_started', [True, None])
def test_absent_batch_independent_seals_and_shared_canonical_capture(tmp_path, store, monkeypatch, driver_started):
    plan = synthetic_producer(tmp_path)
    path(plan, 'batch_manifest').unlink()
    calls = count_copies(monkeypatch)
    result = collect(store, plan, driver_started=driver_started)
    assert result['driver_state'] == 'unsealed_attempt' and result['driver_started'] is driver_started
    assert result['batch'] is result['batch_file'] is None
    assert len(calls) == 26 and set(Counter(calls).values()) == {1}
    assert len(result['files']) == 25
    for index in range(3):
        seal = row(result, f'p{index}:manifest')
        assert seal['declaration_source'] == 'none' and seal['capture'] is None and seal['retained']
        for suffix in ('stdout', 'stderr'):
            assert row(result, f'p{index}:{suffix}')['declaration_source'] == 'pair'
        assert row(result, f's{index}:canonical')['declaration_source'] == 'pair'
    assert row(result, 's0:original')['capture'] is None
    assert any(f['field_path'] == '/batch' and f['code'] == 'native_output_unavailable' for f in result['failures'])
    (tmp_path / 'INDEPENDENT_SEAL_CAPTURE.json').write_bytes(canonical(result))


@pytest.mark.parametrize('bad_batch', ['invalid_json', 'no_lf', 'two_lf', 'duplicate_key', 'nonfinite', 'wrong_plan', 'wrong_pair', 'extra_field'])
def test_rejected_batch_preserves_diagnostic_identity_and_uses_independent_seals(tmp_path, store, bad_batch):
    plan = synthetic_producer(tmp_path)
    batch_path = path(plan, 'batch_manifest')
    raw = batch_path.read_bytes()
    if bad_batch == 'invalid_json':
        raw = b'not-json\xff\n'
    elif bad_batch == 'no_lf':
        raw = raw[:-1]
    elif bad_batch == 'two_lf':
        raw += b'\n'
    elif bad_batch == 'duplicate_key':
        raw = b'{"a":1,"a":2}\n'
    elif bad_batch == 'nonfinite':
        raw = b'{"a":NaN}\n'
    else:
        value = json.loads(raw)
        if bad_batch == 'wrong_plan':
            value['plan_sha256'] = '0' * 64
        elif bad_batch == 'wrong_pair':
            value['pairs'][0]['comparison']['a_set_key'] = 'C'
        else:
            value['extra'] = True
        raw = canonical(value)
    batch_path.write_bytes(raw)
    result = collect(store, plan)
    assert result['driver_state'] == 'unsealed_attempt' and result['batch'] is None
    assert store.get_artifact(result['batch_file']['artifact_ref']) == raw
    code = 'original_attempt_mismatch' if bad_batch in ('wrong_plan', 'wrong_pair', 'extra_field') else 'native_output_malformed'
    assert any(f['code'] == code and f['artifact_ref'] == result['batch_file']['artifact_ref'] for f in result['failures'])
    assert all(row(result, f'p{i}:stdout')['capture']['outcome'] == 'verified' for i in range(3))


def test_conflicting_pair_declarations_keep_one_undeclared_capture_and_all_seals(tmp_path, store, monkeypatch):
    plan = synthetic_producer(tmp_path)
    path(plan, 'batch_manifest').unlink()
    seal_path = path(plan, 'p1:manifest')
    seal = json.loads(seal_path.read_bytes())
    seal['files'][0]['declaration']['sha256'] = '0' * 64
    seal_path.write_bytes(canonical(seal))
    calls = count_copies(monkeypatch)
    result = collect(store, plan)
    conflict = row(result, 's0:canonical')
    assert conflict['declaration_source'] == 'none' and conflict['capture'] is None
    assert read_retained(conflict) == path(plan, 's0:canonical').read_bytes()
    assert len(calls) == 26 and set(Counter(calls).values()) == {1}
    failures = [f for f in result['failures'] if f['code'] == 'original_attempt_mismatch']
    assert [f['comparison_key'] for f in failures] == ['AB', 'AC']
    assert all(f['set_key'] == 'A' for f in failures)
    assert json.loads(read_retained(row(result, 'p1:manifest'))) == seal
    assert row(result, 's1:canonical')['capture']['outcome'] == 'verified'
    assert row(result, 's2:canonical')['capture']['outcome'] == 'verified'
    assert row(result, 'p2:stdout')['capture']['outcome'] == 'verified'


@pytest.mark.parametrize('key', ['s2:original', 's2:parsed', 's2:canonical', 'p2:stdout', 'p2:stderr', 'p2:manifest'])
@pytest.mark.parametrize('change', ['missing', 'changed'])
def test_declared_loss_or_mismatch_keeps_original_positions_and_diagnostic_bytes(tmp_path, store, key, change):
    plan = synthetic_producer(tmp_path)
    source = path(plan, key)
    if change == 'missing':
        source.unlink()
    else:
        source.write_bytes(b'changed-original-native-bytes\n')
    result = collect(store, plan)
    item = row(result, key)
    assert result['driver_state'] == 'sealed_batch' and len(result['files']) == 25
    assert item['capture']['outcome'] == ('unavailable' if change == 'missing' else 'digest_mismatch')
    if change == 'missing':
        assert item['capture']['observed'] is item['retained'] is None
    else:
        assert read_retained(item) == b'changed-original-native-bytes\n'
        assert item['retained']['file'] == item['capture']['observed']
    problem = next(f for f in result['failures'] if f['field_path'].endswith('/capture'))
    assert problem['set_key'] == ('C' if key.startswith('s2:') else None)
    assert problem['comparison_key'] == ('BC' if key.startswith('p2:') else None)
    assert problem['code'] == (('input_unavailable' if change == 'missing' else 'input_digest_mismatch')
        if key == 's2:original' else ('native_output_unavailable' if change == 'missing' else 'artifact_digest_mismatch'))
    assert row(result, 'p0:stdout')['capture']['outcome'] == 'verified'


@pytest.mark.parametrize('case', ['empty_c', 'invalid_c', 'partial_c', 'missing_c', 'wrong_c', 'missing_binary', 'no_hit', 'synthetic_nonzero', 'synthetic_canonical_failure'])
def test_retained_native_failure_and_absence_states_are_preserved(tmp_path, store, case):
    plan = synthetic_producer(tmp_path, case)
    batch = json.loads(path(plan, 'batch_manifest').read_bytes())
    result = collect(store, plan)
    assert result['driver_state'] == 'sealed_batch'
    assert result['failures'] == []
    assert [item['capture']['declared'] for item in result['files']] == [item['declaration'] for item in batch['files']]
    for original, current in zip(batch['files'], result['files']):
        assert current['capture']['outcome'] == ('verified' if original['declaration']['state'] == 'present' else 'declared_absent')
    assert json.loads(Path(result['batch']['path']).read_bytes()) == batch
    if case == 'empty_c':
        assert row(result, 's2:original')['retained']['path'] == row(result, 's2:canonical')['retained']['path']
        assert row(result, 's2:original')['retained']['file']['format'] != row(result, 's2:canonical')['retained']['file']['format']
        assert row(result, 'p1:stdout')['capture']['outcome'] == 'declared_absent'
    if case == 'synthetic_nonzero':
        assert batch['pairs'][0]['manifest']['returncode'] != 0
        assert read_retained(row(result, 'p0:stdout'))
        assert row(result, 'p2:stdout')['capture']['outcome'] == 'verified'


def test_absent_declarations_do_not_capture_unrelated_new_bytes(tmp_path, store, monkeypatch):
    plan = synthetic_producer(tmp_path, 'empty_c')
    source = path(plan, 'p1:stdout')
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b'unrelated bytes after original declared absence')
    calls = count_copies(monkeypatch)
    result = collect(store, plan)
    item = row(result, 'p1:stdout')
    assert item['capture']['outcome'] == 'declared_absent' and item['retained'] is None
    assert (plan['attempt_directory'], item['specification']['relative_path']) not in calls


def test_killed_attempt_retains_first_seal_and_actual_unsealed_partial_bytes(tmp_path, store, monkeypatch):
    plan = synthetic_producer(tmp_path, 'killed')
    calls = count_copies(monkeypatch)
    result = collect(store, plan)
    assert result['driver_state'] == 'unsealed_attempt' and result['batch_file'] is None
    assert row(result, 'p0:manifest')['retained'] is not None
    assert row(result, 'p0:stdout')['declaration_source'] == 'pair'
    assert row(result, 'p1:manifest')['capture'] is None
    assert len(result['files']) == 25 and set(Counter(calls).values()) == {1}
    assert any(f['comparison_key'] == 'AC' and f['code'] == 'native_output_partial' for f in result['failures'])


def test_independently_sealed_failed_pair_keeps_partial_stdout_and_absent_stderr(tmp_path, store):
    plan = synthetic_producer(tmp_path, 'synthetic_nonzero')
    path(plan, 'batch_manifest').unlink()
    source = path(plan, 'p0:manifest')
    manifest = json.loads(source.read_bytes())
    manifest['files'][3]['declaration'].update(state='absent', sha256=None, size_bytes=None)
    source.write_bytes(canonical(manifest))
    path(plan, 'p0:stderr').unlink()
    result = collect(store, plan)
    assert result['driver_state'] == 'unsealed_attempt'
    assert json.loads(read_retained(row(result, 'p0:manifest'))) == manifest
    assert manifest['outcome'] == 'failed' and manifest['returncode'] != 0
    assert row(result, 'p0:stdout')['capture']['outcome'] == 'verified'
    assert read_retained(row(result, 'p0:stdout'))
    assert row(result, 'p0:stderr')['capture']['outcome'] == 'declared_absent'
    assert row(result, 'p2:stdout')['capture']['outcome'] == 'verified'


@pytest.mark.parametrize('driver_started', [True, None])
def test_all_fixed_files_missing_preserves_unknowns_without_observed_fingerprints(tmp_path, store, driver_started):
    plan = synthetic_producer(tmp_path)
    for specification in plan['requested_job']['native_genomic_overlap']['outputs']:
        source = Path(plan['attempt_directory']) / specification['relative_path']
        source.unlink(missing_ok=True)
    result = collect(store, plan, driver_started=driver_started)
    assert result['driver_state'] == 'unsealed_attempt'
    assert result['batch_file'] is result['batch'] is None
    assert len(result['files']) == 25
    assert all(item['capture'] is item['retained'] is None for item in result['files'])
    assert {f['set_key'] for f in result['failures'] if f['code'] == 'input_unavailable'} == {'A', 'B', 'C'}
    assert not any(f['code'] in ('native_output_malformed', 'invalid_coordinate', 'zero_width_interval') for f in result['failures'])
    assert store.db.execute('SELECT COUNT(*) FROM artifacts').fetchone()[0] == 0


@pytest.mark.parametrize('malformation', ['wrong_identity', 'malformed_json'])
def test_rejected_independent_seal_does_not_create_declarations(tmp_path, store, malformation):
    plan = synthetic_producer(tmp_path)
    path(plan, 'batch_manifest').unlink()
    source = path(plan, 'p0:manifest')
    if malformation == 'wrong_identity':
        manifest = json.loads(source.read_bytes())
        manifest['identity']['run_id'] = 'foreign-run'
        source.write_bytes(canonical(manifest))
    else:
        source.write_bytes(b'{bad-seal\n')
    result = collect(store, plan)
    assert row(result, 'p0:stdout')['declaration_source'] == 'none'
    assert row(result, 'p0:stdout')['capture'] is None and row(result, 'p0:stdout')['retained']
    assert read_retained(row(result, 'p0:manifest')) == source.read_bytes()
    assert row(result, 'p2:stdout')['declaration_source'] == 'pair'
    code = 'original_attempt_mismatch' if malformation == 'wrong_identity' else 'native_output_malformed'
    assert any(f['comparison_key'] == 'AB' and f['code'] == code for f in result['failures'])


def test_unsealed_wrong_original_bytes_are_diagnostics_without_fabricated_declaration(tmp_path, store):
    plan = synthetic_producer(tmp_path)
    path(plan, 'batch_manifest').unlink()
    path(plan, 's2:original').write_bytes(b'chr1\t3\t4\n')
    result = collect(store, plan)
    assert row(result, 's2:original')['capture'] is None
    assert read_retained(row(result, 's2:original')) == b'chr1\t3\t4\n'
    assert any(f['code'] == 'input_digest_mismatch' and f['set_key'] == 'C' for f in result['failures'])


def test_not_started_does_not_access_even_existing_native_files(tmp_path, store, monkeypatch):
    plan = synthetic_producer(tmp_path)
    def prohibited(*args, **kwargs):
        pytest.fail('never-started driver files were accessed')
    monkeypatch.setattr(shared, 'capture_native_file', prohibited)
    monkeypatch.setattr(shared, 'capture_declared_native_files', prohibited)
    monkeypatch.setattr(shared, 'retained_native_file', prohibited)
    result = collect(store, plan, driver_started=False)
    assert result['driver_state'] == 'not_started' and result['batch_file'] is result['batch'] is None
    assert all(item['capture'] is item['retained'] is None for item in result['files'])
    assert len(result['failures']) == 26
    assert all(f['partial_artifact_refs'] == [CLOSURE_REF] and f['stage'] == 'native' for f in result['failures'])
    assert store.db.execute('SELECT COUNT(*) FROM artifacts').fetchone()[0] == 0


@pytest.mark.parametrize('damage', ['remove', 'corrupt'])
def test_post_capture_retention_loss_keeps_returned_capture_identity(tmp_path, store, monkeypatch, damage):
    plan = synthetic_producer(tmp_path)
    wanted = hashlib.sha256(path(plan, 'p0:stdout').read_bytes()).hexdigest()
    real = shared.retained_native_file
    calls = Counter()
    def lose_after_capture(actual_store, identity):
        calls[identity['sha256']] += 1
        if identity['sha256'] == wanted and calls[wanted] == 2:
            actual = real(actual_store, identity)
            if damage == 'remove':
                actual.unlink()
            else:
                actual.write_bytes(b'changed retained file')
        return real(actual_store, identity)
    monkeypatch.setattr(shared, 'retained_native_file', lose_after_capture)
    result = collect(store, plan)
    item = row(result, 'p0:stdout')
    assert item['capture']['outcome'] == 'verified'
    assert item['capture']['observed']['sha256'] == wanted and item['retained'] is None
    assert any(f['artifact_ref'] == item['capture']['observed']['artifact_ref'] and
        f['code'] == ('native_output_unavailable' if damage == 'remove' else 'artifact_digest_mismatch')
        for f in result['failures'])


@pytest.mark.parametrize('key', ['batch_manifest', 'p0:manifest', 's0:original'])
def test_undeclared_retention_loss_keeps_actual_identity_in_located_diagnostic(tmp_path, store, monkeypatch, key):
    plan = synthetic_producer(tmp_path)
    wanted = hashlib.sha256(path(plan, key).read_bytes()).hexdigest()
    if key != 'batch_manifest':
        path(plan, 'batch_manifest').unlink()
    real = shared.retained_native_file
    calls = Counter()
    def lose_after_capture(actual_store, identity):
        calls[identity['sha256']] += 1
        if identity['sha256'] == wanted and calls[wanted] == 2:
            real(actual_store, identity).unlink()
        return real(actual_store, identity)
    monkeypatch.setattr(shared, 'retained_native_file', lose_after_capture)
    result = collect(store, plan)
    assert result['driver_state'] == 'unsealed_attempt'
    failure = next(f for f in result['failures'] if f['expected_value'] is not None and
        type(f['expected_value']) is dict and f['expected_value'].get('sha256') == wanted)
    actual_identity = failure['expected_value']
    assert failure['artifact_ref'] == actual_identity['artifact_ref']
    if key == 'batch_manifest':
        assert result['batch_file'] == actual_identity and result['batch'] is None
    else:
        assert row(result, key)['capture'] is row(result, key)['retained'] is None


def test_storage_failure_before_identity_is_not_reported_as_missing_producer(tmp_path, store, monkeypatch):
    plan = synthetic_producer(tmp_path)
    def fail(*args, **kwargs):
        raise shared.NativeFileCaptureError('retained_artifact_unavailable')
    monkeypatch.setattr(shared, 'capture_native_file', fail)
    with pytest.raises(shared.NativeFileCaptureError, match='retained_artifact_unavailable'):
        collect(store, plan)


@pytest.mark.parametrize('failure', ['bad_plan', 'bad_driver_started', 'missing_action_ref', 'missing_closure_ref'])
def test_invalid_call_rejects_before_store_access(tmp_path, store, monkeypatch, failure):
    plan = synthetic_producer(tmp_path)
    kwargs = {'original_plan': plan, 'source_action_receipt_ref': ACTION_REF,
              'writer_closure_receipt_ref': CLOSURE_REF, 'driver_started': True}
    if failure == 'bad_plan':
        plan['requested_job']['native_genomic_overlap']['outputs'].reverse()
    else:
        key, value = {'bad_driver_started': ('driver_started', 1),
            'missing_action_ref': ('source_action_receipt_ref', ''),
            'missing_closure_ref': ('writer_closure_receipt_ref', None)}[failure]
        kwargs[key] = value
    monkeypatch.setattr(shared, 'capture_native_file', lambda *a, **k: pytest.fail('invalid request accessed producer'))
    with pytest.raises(ValueError):
        capture.capture_genomic_overlap_native_files(store, **kwargs)


def test_record_validator_is_pure_detached_and_preserves_later_byte_loss(tmp_path, store, monkeypatch):
    plan = synthetic_producer(tmp_path)
    original = collect(store, plan)
    Path(original['batch']['path']).unlink()
    def prohibited(*args, **kwargs):
        pytest.fail('pure record validator performed I/O')
    monkeypatch.setattr(Path, 'read_bytes', prohibited)
    monkeypatch.setattr(shared, 'capture_native_file', prohibited)
    monkeypatch.setattr(shared, 'retained_native_file', prohibited)
    checked = capture.validate_genomic_overlap_native_capture(original, original_plan=plan)
    assert checked == original and checked is not original
    checked['files'][0]['capture']['declared']['format'] = 'mutated-detached-return'
    assert checked != original


@pytest.mark.parametrize('change', ['extra', 'wrong_plan', 'wrong_order', 'missing_row', 'wrong_spec_format',
    'wrong_declared_format', 'wrong_retained_identity', 'wrong_retained_format', 'wrong_capture_outcome',
    'wrong_capture_failure', 'noncanonical_path', 'path_alias_conflict', 'wrong_batch_identity',
    'unsealed_with_batch', 'not_started_with_observations', 'bool_size', 'bad_failure_location', 'nan'])
def test_record_validator_rejects_join_and_state_tampering(tmp_path, store, change):
    plan = synthetic_producer(tmp_path)
    value = collect(store, plan)
    target = row(value, 'p0:stdout')
    if change == 'extra':
        value['extra'] = True
    elif change == 'wrong_plan':
        value['original_plan_sha256'] = '0' * 64
    elif change == 'wrong_order':
        value['files'][0], value['files'][1] = value['files'][1], value['files'][0]
    elif change == 'missing_row':
        value['files'].pop()
    elif change == 'wrong_spec_format':
        target['specification']['format'] = 'foreign'
    elif change == 'wrong_declared_format':
        target['capture']['declared']['format'] = 'foreign'
    elif change == 'wrong_retained_identity':
        target['retained']['file'] = deepcopy(row(value, 'p1:stdout')['retained']['file'])
    elif change == 'wrong_retained_format':
        target['retained']['file']['format'] = 'foreign'
    elif change == 'wrong_capture_outcome':
        target['capture']['outcome'] = 'declared_absent'
    elif change == 'wrong_capture_failure':
        target['capture']['failure'] = 'capture_file_unavailable'
    elif change == 'noncanonical_path':
        target['retained']['path'] += '/..'
    elif change == 'path_alias_conflict':
        target['retained']['path'] = row(value, 'p1:stdout')['retained']['path']
    elif change == 'wrong_batch_identity':
        value['batch_file']['sha256'] = '0' * 64
    elif change == 'unsealed_with_batch':
        value['driver_state'] = 'unsealed_attempt'
    elif change == 'not_started_with_observations':
        value['driver_started'] = False
        value['driver_state'] = 'not_started'
    elif change == 'bool_size':
        target['capture']['observed']['size_bytes'] = True
    elif change == 'bad_failure_location':
        value['failures'] = [{'code': 'input_unavailable', 'stage': 'capture', 'set_key': 'FOREIGN',
            'comparison_key': None, 'artifact_ref': None, 'locator': None, 'field_path': '/files/4',
            'expected_value': None, 'observed_value': None, 'partial_artifact_refs': [], 'requirement': 'complete_input'}]
    else:
        target['capture']['declared']['size_bytes'] = float('nan')
    with pytest.raises(ValueError):
        capture.validate_genomic_overlap_native_capture(value, original_plan=plan)
