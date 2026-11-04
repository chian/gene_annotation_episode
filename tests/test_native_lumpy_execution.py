"""Engineered one-command controls; none of these fixtures executes LUMPY."""
from copy import deepcopy
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import native_lumpy_execution as native
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_atac_differential_contracts import canonical, digest, _dependency_roots
from gene_annotation_episode.native_flux_balance_storage import file_pin
from gene_annotation_episode.progress_records import validate_resource_observation
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.practical_execution_state import PracticalState


def fake_software():
    """Deliberately invented metadata pins, never a working software witness."""
    modules = (native.DRIVER_MODULE, 'gene_annotation_episode.native_atac_differential_reference')
    dependencies = ('jsonschema', 'attrs', 'referencing', 'rpds-py', 'jsonschema-specifications')
    return dict(driver_runtime=dict(python_executable='/fixture/python', python_sha256='0' * 64,
        python_version='3.12.0', module_root='/fixture/source',
        implementation_files=[dict(module=name, sha256=digest(name)) for name in modules],
        dependencies=[dict(distribution=name, version='engineered-metadata',
            package_root='/fixture/deps/' + name, files=[dict(path='/fixture/deps/' + name + '/__init__.py',
                sha256=digest(name), size_bytes=1)]) for name in dependencies]),
        native_runtime=dict(executable=dict(path='/fixture/native/bin/lumpy', sha256='1' * 64, size_bytes=1),
            loader=dict(path='/fixture/native/loader', sha256='2' * 64, size_bytes=1), libraries=[
                dict(name='libfixture.so.1', file=dict(path='/fixture/native/lib/libfixture.so.1',
                    sha256='3' * 64, size_bytes=1))], reported_version=None))


def _file(raw, format):
    sha = hashlib.sha256(raw).hexdigest()
    return dict(artifact_ref='artifact_' + sha, sha256=sha, size_bytes=len(raw), format=format)


def _bam():
    """A real BAM header envelope with zero alignment records, not native calls."""
    text = b'@HD\tVN:1.6\n@SQ\tSN:engineered-contig\tLN:100\n@RG\tID:received-rg\tSM:received-sample\n'
    name = b'engineered-contig\0'
    body = b'BAM\x01' + struct.pack('<i', len(text)) + text + struct.pack('<ii', 1, len(name)) + name + struct.pack('<i', 100)
    return gzip.compress(body, mtime=0), text


def job_fixture(directory, *, kinds=('paired_end', 'split_read'), software=None):
    directory.mkdir(parents=True, exist_ok=True)
    bam, _ = _bam()
    histogram = b'# engineered supplied histogram; never executed\n1\t1\n'
    signals, bindings = [], []
    for ordinal, kind in enumerate(kinds):
        key = 'signal-' + str(ordinal)
        path = directory / ('supplied,' + key + ':original.bam')
        path.write_bytes(bam)
        signal = dict(kind=kind, signal_key=key, output_sample_label='explicit-output-' + str(ordinal),
            declared_sample_id='received-sample', reference_id=None, bam=_file(bam, 'bam'), read_group='received-rg')
        bindings.append(dict(input_key=key + ':bam', file=signal['bam'], path=str(path)))
        if kind == 'paired_end':
            path = directory / ('supplied,' + key + ':original.histo')
            path.write_bytes(histogram)
            signal.update(histogram=_file(histogram, 'lumpy_insert_histogram'), parameters=dict(
                mean='3.0500e2', stdev='30.000', read_length=150, min_non_overlap=150,
                discordant_z=4, back_distance=20, weight=1, min_mapping_threshold=0))
            bindings.append(dict(input_key=key + ':histogram', file=signal['histogram'], path=str(path)))
        else:
            signal['parameters'] = dict(back_distance=10, min_non_overlap=0, weight=1,
                min_mapping_threshold=0, min_clip=0)
        signals.append(signal)
    request = dict(version=native.REQUEST_VERSION, operation=native.OPERATION, mode=native.MODE,
        run_key='engineered-pe-sr', signals=signals,
        parameters=dict(minimum_sample_weight=4, trim_threshold='0.000', probability_output=True))
    return dict(request=request, software=fake_software() if software is None else deepcopy(software), input_bindings=bindings)


def requested(job, directory):
    driver = job['software']['driver_runtime']
    environment = dict(PYTHONPATH=os.pathsep.join([driver['module_root'], *_dependency_roots(driver)]),
        PYTHONHOME=sys.base_prefix, PYTHONNOUSERSITE='1', PYTHONSAFEPATH='1', PYTHONDONTWRITEBYTECODE='1',
        OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', TMP=str(directory / 'tmp'), TEMP=str(directory / 'tmp'),
        TMPDIR=str(directory / 'tmp'), XDG_CACHE_HOME=str(directory / 'cache'), PIP_CACHE_DIR=str(directory / 'cache/pip'))
    return native.requested_job_from_lumpy(job, environment=environment)


def practical_assignment(directory, job):
    return dict(version='practical_assignment_v1', assignment_id='engineered-lumpy-assignment',
        resource_kind='local', resource_id='local', workspace=str(directory), endpoint='usable_handoff',
        requested_job=requested(job, directory), progress_requirements=[dict(key='handoff', credit=1,
            predicate=dict(kind='requested_job_handoff'))], completion_keys=['handoff'],
        initial_context=dict(revision=0, cwd=str(directory), environment={}), inventory_snapshot={},
        constraints=deepcopy(native.POLICY))


def plan_fixture(directory, *, job=None):
    job = job_fixture(directory) if job is None else job
    assignment = practical_assignment(directory, job)
    operation, run, episode = 'selected-start', 'engineered-lumpy-run', 'local-child'
    root = directory / '.episode-operations' / digest(dict(run=run, episode=episode)) / digest(operation)
    identity = dict(run_id=run, episode_id=episode, resource_id='local', execution_id=str(root / 'native.json'),
        attempt_id=digest(operation), operation_key=operation, requested_job_sha256=digest(assignment['requested_job']),
        assignment_sha256=digest(assignment))
    return native.lumpy_plan(assignment, identity, policy=native.POLICY)


def output_path(plan, key):
    return Path(plan['attempt_directory']) / next(row['relative_path'] for row in plan['outputs'] if row['file_key'] == key)


def mocked_command(monkeypatch, *, returncode=0):
    """An explicit engineered process observation, with no program execution."""
    calls = []
    monkeypatch.setattr(native, 'verify_driver_runtime', lambda value: None)
    monkeypatch.setattr(native, '_verify_native_runtime', lambda value: None)
    def run(argv, *, stdout, stderr, **kwargs):
        calls.append(dict(argv=list(argv), cwd=str(kwargs['cwd']), environment=deepcopy(kwargs['env'])))
        stdout.write(b'##engineered retained bytes; deliberately not validated VCF\n')
        stderr.write(b'engineered retained stderr prefix\n')
        return SimpleNamespace(returncode=returncode)
    monkeypatch.setattr(native.subprocess, 'run', run)
    return calls


def _elf(*, soname=None, needed=(), interpreter=None, search_path=None, machine=62):
    """Small synthetic ELF metadata, intentionally not executable machine code."""
    strings = bytearray(b'\0')
    def string(value):
        index = len(strings)
        strings.extend(value.encode('ascii') + b'\0')
        return index
    entries = [(5, 0x400)]
    if soname is not None:
        entries.append((14, string(soname)))
    entries.extend((1, string(value)) for value in needed)
    if search_path is not None:
        entries.append((29, string(search_path)))
    entries.extend([(10, len(strings)), (0, 0)])
    dynamic = b''.join(struct.pack('<qQ', *entry) for entry in entries)
    interp = None if interpreter is None else interpreter.encode('ascii') + b'\0'
    raw = bytearray(0x800)
    raw[:16] = b'\x7fELF\x02\x01\x01' + bytes(9)
    raw[16:64] = struct.pack('<HHIQQQIHHHHHH', 3, machine, 1, 0, 64, 0, 0, 64, 56,
        2 + int(interp is not None), 0, 0, 0)
    rows = [(1, 5, 0, 0, 0, len(raw), len(raw), 0x1000),
        (2, 6, 0x200, 0x200, 0x200, len(dynamic), len(dynamic), 8)]
    if interp is not None:
        rows.append((3, 4, 0x600, 0x600, 0x600, len(interp), len(interp), 1))
    for index, row in enumerate(rows):
        raw[64 + 56 * index:64 + 56 * (index + 1)] = struct.pack('<IIQQQQQQ', *row)
    raw[0x200:0x200 + len(dynamic)] = dynamic
    raw[0x400:0x400 + len(strings)] = strings
    if interp is not None:
        raw[0x600:0x600 + len(interp)] = interp
    return bytes(raw)


def _elf_runtime(directory, *, defect=None):
    root = directory / 'native'
    (root / 'bin').mkdir(parents=True)
    (root / 'lib').mkdir()
    loader_name, library_name = 'ld-fixture.so.2', 'libfixture.so.1'
    binary = _elf(needed=[library_name], interpreter='/original-system/' + loader_name,
        search_path='/unbound/path' if defect == 'rpath' else '$ORIGIN/../lib')
    loader = _elf(soname=loader_name)
    library = _elf(soname='libwrong.so.1' if defect == 'soname' else library_name,
        needed=['libabsent.so.1'] if defect == 'needed' else [loader_name], machine=183 if defect == 'machine' else 62)
    for path, raw in ((root / 'bin/lumpy', binary), (root / 'loader', loader), (root / 'lib' / library_name, library)):
        path.write_bytes(raw)
        path.chmod(0o555 if path.name in ('lumpy', 'loader') else 0o444)
    return dict(executable=file_pin(root / 'bin/lumpy'), loader=file_pin(root / 'loader'), libraries=[]
        if defect == 'undeclared' else [dict(name=library_name, file=file_pin(root / 'lib' / library_name))], reported_version=None)


def test_exact_pe_sr_argv_preserves_declared_numbers_associations_and_occurrences(tmp_path):
    job = job_fixture(tmp_path)
    plan = plan_fixture(tmp_path, job=job)
    argv = native.lumpy_command_argv(plan)
    runtime = job['software']['native_runtime']
    assert argv[:5] == [runtime['loader']['path'], '--inhibit-cache', '--library-path',
        '/fixture/native/lib', runtime['executable']['path']]
    assert argv[5:10] == ['-P', '-msw', '4', '-tt', '0.000']
    assert argv.count('-pe') == argv.count('-sr') == 1
    pe, sr = argv[argv.index('-pe') + 1], argv[argv.index('-sr') + 1]
    assert pe == ','.join(['bam_file:' + str(Path(plan['attempt_directory']) / 'inputs/000000.bam'),
        'histo_file:' + str(Path(plan['attempt_directory']) / 'inputs/000000.histo'),
        'mean:3.0500e2', 'stdev:30.000', 'read_length:150', 'min_non_overlap:150', 'discordant_z:4',
        'back_distance:20', 'weight:1', 'id:explicit-output-0', 'min_mapping_threshold:0', 'read_group:received-rg'])
    assert sr.endswith('min_non_overlap:0,back_distance:10,weight:1,id:explicit-output-1,min_mapping_threshold:0,min_clip:0,read_group:received-rg')
    assert all(row['path'] not in pe + sr for row in job['input_bindings'])
    assert [row['input_key'] for row in job['input_bindings']] == ['signal-0:bam', 'signal-0:histogram', 'signal-1:bam']
    assert job['request']['signals'][0]['bam'] == job['request']['signals'][1]['bam']
    assert job['request']['signals'][0]['declared_sample_id'] != job['request']['signals'][0]['output_sample_label']
    assert not {'-b', '-e', 'lumpyexpress', 'samtools', 'bcftools', 'snpeff'}.intersection(argv)
    assert [row['role'] for row in plan['outputs']] == ['vcf', 'stderr', 'bam_header', 'bam_header', 'seal']


@pytest.mark.parametrize('defect', ['bool_integer', 'float_integer', 'zero_required', 'nonfinite', 'underflow',
    'grammar_label', 'grammar_group', 'duplicate_signal', 'file_identity', 'extra_native_option'])
def test_invalid_native_request_is_denied_before_dispatch(tmp_path, defect, monkeypatch):
    value = job_fixture(tmp_path)['request']
    if defect == 'bool_integer': value['parameters']['minimum_sample_weight'] = True
    elif defect == 'float_integer': value['signals'][1]['parameters']['min_clip'] = 1.0
    elif defect == 'zero_required': value['signals'][0]['parameters']['mean'] = '0'
    elif defect == 'nonfinite': value['parameters']['trim_threshold'] = 'NaN'
    elif defect == 'underflow': value['signals'][0]['parameters']['stdev'] = '1e-9999'
    elif defect == 'grammar_label': value['signals'][0]['output_sample_label'] = 'sample,injected:1'
    elif defect == 'grammar_group': value['signals'][0]['read_group'] = 'group:injected'
    elif defect == 'duplicate_signal': value['signals'][1]['signal_key'] = value['signals'][0]['signal_key']
    elif defect == 'file_identity': value['signals'][0]['bam']['artifact_ref'] = 'artifact_' + 'f' * 64
    else: value['signals'][0]['parameters']['unselected_option'] = 1
    monkeypatch.setattr(native.subprocess, 'run', lambda *_a, **_k: pytest.fail('invalid request dispatched'))
    with pytest.raises(ValueError): native.validate_lumpy_request(value)


def test_source_legal_zero_and_signed_values_are_not_replaced_by_policy(tmp_path):
    value = job_fixture(tmp_path)['request']
    value['parameters'].update(minimum_sample_weight=-1, trim_threshold='-2.5', probability_output=False)
    value['signals'][0]['parameters'].update(back_distance=-2, min_mapping_threshold=0)
    value['signals'][1]['parameters'].update(min_non_overlap=0, min_clip=0, min_mapping_threshold=0)
    value['signals'][1]['read_group'] = None
    assert native.validate_lumpy_request(value) == value


def test_bound_schema_rejects_unselected_software_and_extra_commands(tmp_path):
    job = job_fixture(tmp_path)
    selected = requested(job, tmp_path)
    schema = native.lumpy_execution_schema('RequestedJob', bindings=[dict(operation=native.OPERATION,
        mode=native.MODE, software=job['software'])])
    Draft202012Validator(schema).validate(selected)
    extra = deepcopy(selected); extra['argv'].append('--extra')
    assert not Draft202012Validator(schema).is_valid(extra)
    changed = deepcopy(selected); changed['native_lumpy']['software']['native_runtime']['reported_version'] = 'unselected'
    assert not Draft202012Validator(schema).is_valid(changed)


@pytest.mark.parametrize('defect', ['order', 'file', 'same_path_conflict'])
def test_flat_input_bindings_authenticate_every_occurrence(tmp_path, defect):
    job = job_fixture(tmp_path)
    if defect == 'order': job['input_bindings'].reverse()
    elif defect == 'file': job['input_bindings'][0]['file'] = job['input_bindings'][1]['file']
    else: job['input_bindings'][1]['path'] = job['input_bindings'][0]['path']
    with pytest.raises(ValueError, match='lumpy_input_binding_conflict'): native.validate_lumpy_native_job(job)


def test_supplied_elf_metadata_closure_is_validated_without_program_execution(tmp_path, monkeypatch):
    runtime = _elf_runtime(tmp_path)
    monkeypatch.setattr(native.subprocess, 'run', lambda *_a, **_k: pytest.fail('ELF metadata executed a program'))
    metadata = native._verify_native_runtime(runtime)
    assert metadata['executable']['needed'] == ['libfixture.so.1']
    assert metadata['loader']['soname'] == 'ld-fixture.so.2'
    assert metadata['libfixture.so.1']['needed'] == ['ld-fixture.so.2']
    assert metadata['executable']['search_paths'] == ['$ORIGIN/../lib']
    assert all(row['elf_class'] == 2 and row['byte_order'] == 1 for row in metadata.values())


@pytest.mark.parametrize('defect', ['undeclared', 'needed', 'soname', 'machine', 'rpath'])
def test_elf_closure_rejects_unbound_dependencies_and_metadata_conflicts(tmp_path, defect):
    with pytest.raises(ValueError, match='native_dependency_unavailable'):
        native._verify_native_runtime(_elf_runtime(tmp_path, defect=defect))


def test_freezer_accepts_original_supplied_locations_and_returns_frozen_native_paths(tmp_path, monkeypatch):
    from gene_annotation_episode import native_atac_differential_software as software
    source = _elf_runtime(tmp_path / 'original')
    original = deepcopy(source)
    # The source paths deliberately do not obey the returned frozen layout.
    for pin in [source['executable'], source['loader'], source['libraries'][0]['file']]:
        before = Path(pin['path']); after = before.with_name(before.name + '.original')
        before.rename(after); pin['path'] = str(after)
    driver = fake_software()['driver_runtime']
    monkeypatch.setattr(software, 'freeze_driver_runtime', lambda **_kwargs: deepcopy(driver))
    target = tmp_path / 'snapshot'
    value = native.freeze_lumpy_software_binding(module_root='/explicit-source', snapshot_directory=target, native_runtime=source)
    runtime = value['native_runtime']
    assert runtime['executable']['path'] == str(target / 'native/bin/lumpy')
    assert runtime['loader']['path'] == str(target / 'native/loader')
    assert runtime['libraries'][0]['file']['path'] == str(target / 'native/lib/libfixture.so.1')
    assert runtime['reported_version'] is None
    assert runtime['executable']['sha256'] == original['executable']['sha256']
    for pin in [runtime['executable'], runtime['loader'], runtime['libraries'][0]['file']]:
        assert file_pin(pin['path']) == pin and not Path(pin['path']).stat().st_mode & 0o222
    assert all(Path(pin['path']).exists() for pin in [source['executable'], source['loader'], source['libraries'][0]['file']])


@pytest.mark.parametrize('returncode', [0, 7])
def test_one_engineered_call_retains_partial_bytes_headers_and_original_outcome_without_retry(tmp_path, monkeypatch, returncode):
    plan = plan_fixture(tmp_path)
    calls = mocked_command(monkeypatch, returncode=returncode)
    seal = native.run_lumpy(plan)
    assert seal['outcome'] == ('succeeded' if returncode == 0 else 'failed') and seal['returncode'] == returncode
    assert len(calls) == 1 and calls[0]['argv'] == native.lumpy_command_argv(plan)
    assert [row['input_ordinal'] for row in seal['input_inspections']] == [0, 1]
    assert all(row['producer_outcome'] == 'succeeded' for row in seal['input_inspections'])
    assert output_path(plan, 'header:signal-0').read_bytes() == output_path(plan, 'header:signal-1').read_bytes() == _bam()[1]
    assert output_path(plan, 'vcf').read_bytes() == b'##engineered retained bytes; deliberately not validated VCF\n'
    assert any(row['code'] == 'native_nonzero_exit' for row in seal['failures']) is (returncode != 0)
    before = output_path(plan, 'seal').read_bytes()
    assert native.run_lumpy(plan) == seal and len(calls) == 1
    assert output_path(plan, 'seal').read_bytes() == before == canonical(seal)


def test_header_failure_qualifies_successful_native_exit_without_inventing_valid_vcf(tmp_path, monkeypatch):
    job = job_fixture(tmp_path, kinds=('split_read',))
    raw = b'not a BAM envelope'
    Path(job['input_bindings'][0]['path']).write_bytes(raw)
    job['request']['signals'][0]['bam'] = job['input_bindings'][0]['file'] = _file(raw, 'bam')
    plan = plan_fixture(tmp_path, job=job)
    calls = mocked_command(monkeypatch)
    seal = native.run_lumpy(plan)
    assert len(calls) == 1 and seal['outcome'] == 'succeeded' and seal['returncode'] == 0
    assert seal['input_inspections'][0]['producer_outcome'] == 'failed'
    assert seal['input_inspections'][0]['supplied_extent'] == 'unknown'
    assert any(row['code'] == 'input_unavailable' and row['stage'] == 'reference' for row in seal['failures'])


@pytest.mark.parametrize('defect', ['input_missing', 'digest_conflict', 'software_unavailable'])
def test_unavailable_selected_inputs_or_software_cannot_reach_dispatch(tmp_path, monkeypatch, defect):
    plan = plan_fixture(tmp_path)
    calls = mocked_command(monkeypatch)
    first = plan['requested_job']['native_lumpy']['input_bindings'][0]
    if defect == 'input_missing': Path(first['path']).unlink()
    elif defect == 'digest_conflict': Path(first['path']).write_bytes(b'changed source body')
    else:
        def unavailable(_value): raise ValueError('native_dependency_unavailable')
        monkeypatch.setattr(native, '_verify_native_runtime', unavailable)
    seal = native.run_lumpy(plan)
    assert calls == [] and seal['outcome'] == 'not_run'
    assert seal['returncode'] is seal['started_at'] is seal['finished_at'] is None
    assert seal['failures'] and output_path(plan, 'seal').exists()
    assert not output_path(plan, 'vcf').exists()
    if defect == 'software_unavailable':
        assert all(row['staging_state'] == 'not_attempted' and row['staged']['state'] == row['staging_temporary']['state'] == 'absent'
            for row in seal['inputs'])
    else:
        assert seal['inputs'][0]['staging_state'] == 'failed'
        assert [row['input_ordinal'] for row in seal['input_inspections']] == [1]
        if defect == 'digest_conflict':
            temporary = seal['inputs'][0]['staging_temporary']
            assert temporary['state'] == 'present' and temporary['sha256'] == hashlib.sha256(b'changed source body').hexdigest()
    assert native.run_lumpy(plan) == seal and calls == []


def test_partial_failed_staging_is_sealed_as_observed_bytes_and_never_reissued(tmp_path, monkeypatch):
    plan = plan_fixture(tmp_path)
    calls = mocked_command(monkeypatch)
    original_stage = native._stage
    stage_calls = []
    def stage(binding, spec, *, directory, policy):
        stage_calls.append(binding['input_key'])
        if binding['input_key'] != 'signal-0:bam':
            return original_stage(binding, spec, directory=directory, policy=policy)
        path = Path(directory) / spec['relative_path']
        path.with_name('.' + path.name + '.staging').write_bytes(b'actual partial staging prefix')
        raise OSError('engineered interrupted source read')
    monkeypatch.setattr(native, '_stage', stage)
    seal = native.run_lumpy(plan)
    first = seal['inputs'][0]
    assert calls == [] and seal['outcome'] == 'not_run' and first['staging_state'] == 'failed'
    assert first['staged']['state'] == 'absent'
    assert first['staging_temporary']['state'] == 'present'
    assert first['staging_temporary']['sha256'] == hashlib.sha256(b'actual partial staging prefix').hexdigest()
    assert [row['input_ordinal'] for row in seal['input_inspections']] == [1]
    before = list(stage_calls)
    assert native.run_lumpy(plan) == seal and stage_calls == before and calls == []


def test_runtime_change_after_verified_staging_seals_not_run_without_retry(tmp_path, monkeypatch):
    plan = plan_fixture(tmp_path)
    calls = mocked_command(monkeypatch)
    checks = []
    def verify(_value):
        checks.append('metadata-check')
        if len(checks) > 1: raise ValueError('native_dependency_unavailable')
    monkeypatch.setattr(native, '_verify_native_runtime', verify)
    seal = native.run_lumpy(plan)
    assert calls == [] and seal['outcome'] == 'not_run'
    assert all(row['staging_state'] == 'verified' for row in seal['inputs'])
    assert len(seal['input_inspections']) == 2
    assert any(row['stage'] == 'execution' and row['code'] == 'native_dependency_unavailable' for row in seal['failures'])
    assert native.run_lumpy(plan) == seal and len(checks) == 2 and calls == []


@pytest.mark.parametrize('defect', ['identity', 'argv', 'returncode', 'staged_identity', 'inspection_ordinal'])
def test_seal_cannot_relabel_original_command_input_or_outcome(tmp_path, monkeypatch, defect):
    plan = plan_fixture(tmp_path)
    calls = mocked_command(monkeypatch)
    seal = native.run_lumpy(plan)
    if defect == 'identity': seal['identity']['episode_id'] = 'different-child'
    elif defect == 'argv': seal['argv'].append('-e')
    elif defect == 'returncode': seal['returncode'] = 7
    elif defect == 'staged_identity': seal['inputs'][0]['staged']['sha256'] = 'f' * 64
    else: seal['input_inspections'].pop(0)
    with pytest.raises(ValueError): native.validate_lumpy_seal(seal, plan=plan)
    assert len(calls) == 1


@pytest.mark.parametrize('defect', ['changed', 'missing', 'symlink'])
def test_completed_outputs_cannot_be_resealed_or_reexecuted_after_tamper(tmp_path, monkeypatch, defect):
    plan = plan_fixture(tmp_path)
    calls = mocked_command(monkeypatch)
    native.run_lumpy(plan)
    original = output_path(plan, 'seal').read_bytes()
    path = output_path(plan, 'vcf')
    if defect == 'changed': path.write_bytes(b'changed retained output')
    elif defect == 'missing': path.unlink()
    else:
        other = path.with_name('other.vcf'); path.rename(other); path.symlink_to(other)
    with pytest.raises((ValueError, OSError)): native.run_lumpy(plan)
    assert len(calls) == 1 and output_path(plan, 'seal').read_bytes() == original


def test_orphaned_original_attempt_never_starts_another_command(tmp_path, monkeypatch):
    plan = plan_fixture(tmp_path)
    calls = mocked_command(monkeypatch)
    directory = Path(plan['attempt_directory']); directory.mkdir(parents=True)
    native._immutable(directory / native.OWNER_FILENAME, plan)
    with pytest.raises(ValueError, match='unsealed_native_attempt'): native.run_lumpy(plan)
    assert calls == [] and not output_path(plan, 'seal').exists()


@pytest.mark.parametrize('terminal,quiescent,closed', [(False, False, False), (True, False, False), (True, True, True)])
def test_observed_semantic_roles_and_bounded_reads_preserve_writer_state(tmp_path, monkeypatch, terminal, quiescent, closed):
    plan = plan_fixture(tmp_path)
    mocked_command(monkeypatch)
    native.run_lumpy(plan)
    outputs, logs, available = native.lumpy_observed_files(plan, dict(terminal=terminal, quiescent=quiescent),
        log_window_bytes=8, log_roles=('stderr',))
    assert available is True and [row['role'] for row in outputs] == ['vcf', 'stderr', 'bam_header:signal-0', 'bam_header:signal-1', 'seal']
    assert all(row['available'] and row['writer_closed'] is closed for row in outputs)
    assert len(logs) == 1 and logs[0]['role'] == 'stderr'
    assert logs[0]['observed_size'] == len(b'engineered retained stderr prefix\n')
    window = native.read_lumpy_output(plan, path=str(output_path(plan, 'vcf')), offset=2, limit=10)
    assert window['returned_bytes'] == 10 and window['text_utf8'] == 'engineered'
    with pytest.raises(ValueError, match='native_lumpy_original_output_path_required'):
        native.read_lumpy_output(plan, path=plan['requested_job']['native_lumpy']['input_bindings'][0]['path'], offset=0, limit=10)


@pytest.mark.parametrize('stdout_bytes', [b'', b'engineered wrapper stdout\n'])
def test_stdout_and_stderr_logs_have_matching_shared_resource_outputs(tmp_path, monkeypatch, stdout_bytes):
    """A real shared observation validator over explicitly engineered execution."""
    plan = plan_fixture(tmp_path)
    calls = mocked_command(monkeypatch)
    native.run_lumpy(plan)
    wrapper_stdout = Path(plan['identity']['execution_id']).parent / 'stdout.log'
    wrapper_stdout.write_bytes(stdout_bytes)
    outputs, logs, available = native.lumpy_observed_files(plan, dict(terminal=True, quiescent=True),
        log_window_bytes=4096, log_roles=('stdout', 'stderr'))
    stdout, = [row for row in outputs if row['role'] == 'stdout']
    assert stdout == dict(role='stdout', available=True, bytes=len(stdout_bytes), writer_closed=True)
    stdout_log, = [row for row in logs if row['role'] == 'stdout']
    assert stdout_log == dict(role='stdout', path=str(wrapper_stdout), offset=0,
        observed_size=len(stdout_bytes), bytes_base64=base64.b64encode(stdout_bytes).decode())
    assert {row['role'] for row in logs} == {'stdout', 'stderr'} and len(calls) == 1
    observation = dict(observed_at='2026-11-01T00:00:00+00:00', state='completed', returncode=0,
        failure_code=None, result_available=available, measurements=[], outputs=outputs, logs=logs,
        provenance_refs=[], native=dict(engineered_lifecycle=True, terminal=True, quiescent=True))
    assert validate_resource_observation(observation) == observation
    missing = deepcopy(observation)
    missing['outputs'] = [row for row in outputs if row['role'] != 'stdout']
    with pytest.raises(ContractError, match='invalid_resource_progress_observation'):
        validate_resource_observation(missing)


def test_real_pending_intent_reserves_one_original_handle_without_dispatch_or_input_reads_on_restore(tmp_path):
    job = job_fixture(tmp_path)
    assignment = practical_assignment(tmp_path, job)
    state = PracticalState(tmp_path / 'state', 'engineered-lumpy-run', 'local-child', assignment)
    root = tmp_path / '.episode-operations' / digest(dict(run=state.run_id, episode=state.episode_id)) / digest('selected-start')
    policy = LocalJobPolicy(**native.POLICY)
    with pytest.raises(ValueError, match='selected_pending_start_required'):
        native.prepare_local_lumpy(state, 'selected-start', root=root, policy=policy)
    state.begin('selected-start', 'practical.job.start', {})
    handle = native.prepare_local_lumpy(state, 'selected-start', root=root, policy=policy)
    original = native.read_local_lumpy_plan(assignment, str(handle.path))
    before = handle.path.read_bytes()
    for row in job['input_bindings']: Path(row['path']).unlink()
    assert native.read_local_lumpy_plan(assignment, str(handle.path)) == original
    assert native.prepare_local_lumpy(state, 'selected-start', root=root, policy=policy).path == handle.path
    assert handle.path.read_bytes() == before and not Path(original['attempt_directory']).exists()


@pytest.mark.parametrize('defect', [None, 'command', 'environment', 'request_digest', 'duplicate_path', 'policy'])
def test_original_controls_authenticate_literal_bytes_without_reopening_paths(tmp_path, monkeypatch, defect):
    job = job_fixture(tmp_path)
    assignment = practical_assignment(tmp_path, job)
    state = PracticalState(tmp_path / 'state', 'engineered-lumpy-run', 'local-child', assignment)
    root = tmp_path / '.episode-operations' / digest(dict(run=state.run_id, episode=state.episode_id)) / digest('selected-start')
    state.begin('selected-start', 'practical.job.start', {})
    handle = native.prepare_local_lumpy(state, 'selected-start', root=root, policy=LocalJobPolicy(**native.POLICY))
    plan = native.read_local_lumpy_plan(assignment, str(handle.path))
    original = json.loads(handle.path.read_bytes()); raw = Path(original['paths']['request']).read_bytes()
    if defect == 'command': original['command'].append('--unselected')
    elif defect == 'environment':
        document = json.loads(raw); document['env']['PYTHONPATH'] = '/unselected'; raw = canonical(document)
        original['request_sha256'] = hashlib.sha256(raw).hexdigest()
    elif defect == 'request_digest': original['request_sha256'] = 'f' * 64
    elif defect == 'duplicate_path': original['paths']['status'] = original['paths']['result']
    elif defect == 'policy': original['metadata']['policy']['scratch_bytes'] = 1
    def forbidden(*_args, **_kwargs): raise AssertionError('pure original-control validation reopened paths')
    for name in ('_regular', '_directory', '_read_control'): monkeypatch.setattr(native, name, forbidden)
    if defect is None:
        assert native.validate_lumpy_original_controls(plan, original, raw) == plan
        assert native.validate_lumpy_original_controls(plan, original, raw.decode()) == plan
    else:
        with pytest.raises(ValueError): native.validate_lumpy_original_controls(plan, original, raw)
