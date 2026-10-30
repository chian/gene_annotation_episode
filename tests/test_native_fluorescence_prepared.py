"""Finite selected-producer integration under the root's bounded529 runner.

Control tests explicitly stub only software trust; numerical tests use the
actual installed libraries. The subprocess cases authenticate the full pinned
software closure as well. Synthetic input is not an acquired molecular assay.
"""
from copy import deepcopy
import errno
import json
import os
from pathlib import Path
import subprocess

import pytest
from jsonschema import Draft202012Validator

from fluorescence_flowio_test_support import require_bounded_runtime

require_bounded_runtime()

from gene_annotation_episode import fluorescence_event_contracts as core
from gene_annotation_episode import fluorescence_event_preparation as preparation
from gene_annotation_episode import fluorescence_preparation_readers as readers
from gene_annotation_episode import fluorescence_native_reports as report_parser
from gene_annotation_episode import native_fluorescence_driver as driver
from gene_annotation_episode.fluorescence_execution_common import canonical, digest, identity, validate_failure
from gene_annotation_episode.native_fluorescence_contracts import (
    JOB_SCHEMA, JOB_V2_SCHEMA, OPERATIONS, fluorescence_output_files, validate_fluorescence_bindings,
    validate_fluorescence_job, validate_fluorescence_manifest, validate_fluorescence_prepared_batch,
    validate_fluorescence_report_batch,
)
from gene_annotation_episode.native_fluorescence_storage import read_json
from gene_annotation_episode.native_fluorescence_tool_info import fluorescence_tool_contracts
from native_fluorescence_prepared_test_support import (
    COMPENSATE, FACS, SCALE, actual_software, add_facs_report, file_input,
    prepared_job, selected_preparation, v2_job,
)
from test_native_fluorescence_contracts import event_input, job, plan
from test_native_fluorescence_driver import finite_driver, output


def run_selected(selected, directory, monkeypatch):
    original = plan(directory, selected_job=selected)
    finite_driver(monkeypatch, original)
    return original, driver.run_fluorescence_driver(original)


def binding(selected, methods, profiles):
    return dict(version='native_fluorescence_binding_v2',
        **{key: deepcopy(selected[key]) for key in ('operation', 'mode', 'software')},
        parsers=sorted({row['parser'] for row in selected['inputs']}),
        preparation_methods=methods, report_profiles=profiles)


def values(parse):
    return [[cell['measurement']['value'] for cell in event['values']] for event in parse['events']]


@pytest.mark.parametrize('operation', OPERATIONS)
def test_v1_stays_closed_and_v2_has_exact_selected_roles(tmp_path, operation):
    old = job(tmp_path / 'v1', operation=operation)
    before = canonical(old)
    assert canonical(validate_fluorescence_job(old)) == before
    assert 'preparations' not in JOB_SCHEMA['properties']
    assert 'report_inputs' not in JOB_SCHEMA['properties']
    old['preparations'] = []
    with pytest.raises(ValueError):
        validate_fluorescence_job(old)
    selected = prepared_job(tmp_path / 'v2', operation=operation)
    frozen = canonical(selected)
    assert canonical(validate_fluorescence_job(selected)) == frozen
    Draft202012Validator(JOB_V2_SCHEMA).validate(selected)
    roles = [row['role'] for row in fluorescence_output_files(selected)]
    expected = ['event_input:0', *[f'support_input:{index}' for index in range(len(selected['support_inputs']))],
        'event_batch:0', 'report_input:0', 'preparation_parameters:0', 'prepared_data:0', 'prepared_batch:0',
        'preparation_parameters:1', 'prepared_data:1', 'prepared_batch:1', 'report_batch:0', 'manifest']
    assert roles == expected
    assert fluorescence_output_files(selected)[-1]['format'] == 'fluorescence_native_manifest_v2'


@pytest.mark.parametrize('fault', ['forward', 'self', 'bool', 'sample', 'domain', 'source', 'channel', 'unit',
    'analyte', 'report_source', 'report_field', 'report_number', 'comparison', 'gate_domain', 'support_missing', 'support_extra'])
def test_declarations_reject_wrong_topology_joins_and_unselected_numbers(tmp_path, fault):
    selected = prepared_job(tmp_path)
    first, second = selected['preparations']
    if fault == 'forward': first['input'] = dict(kind='preparation', index=1)
    if fault == 'self': second['input']['index'] = 1
    if fault == 'bool': first['input']['index'] = False
    if fault == 'sample': second['output']['sample_key'] = 'other-sample'
    if fault == 'domain': second['output']['key'] = first['output']['key']
    if fault == 'source': second['output']['source_key'] = selected['inputs'][0]['source']['key']
    if fault == 'channel': second['output']['channels'][0]['key'] = first['output']['channels'][0]['key']
    if fault == 'unit': first['output']['channels'][0]['unit'] = 'concentration'
    if fault == 'analyte': second['output']['channels'][0]['label'] = 'inferred molecular identity'
    if fault == 'report_source': selected['report_inputs'][0]['source_key'] = first['output']['source_key']
    if fault == 'report_field': selected['report_inputs'][0]['fields'][0]['key'] = first['output']['channels'][0]['key']
    if fault == 'report_number': selected['report_inputs'][0]['fields'][0]['value'] = 100
    if fault == 'comparison': selected['parameters']['native_comparison_requests'] = ['undeclared-report']
    if fault == 'gate_domain':
        selected['definitions']['gates'][0].update(kind='threshold', domain_key=first['output']['key'],
            channel_key=second['output']['channels'][0]['key'], lower=dict(value=1, inclusive=True))
    if fault == 'support_missing': selected['support_inputs'].pop()
    if fault == 'support_extra': selected['support_inputs'].append(file_input(tmp_path, 'extra', b'extra'))
    with pytest.raises(ValueError):
        validate_fluorescence_job(selected)


@pytest.mark.parametrize('fault', ['implementation', 'flowio', 'flowutils', 'numpy', 'numpy_metadata',
    'flowutils_metadata', 'method_duplicate', 'profile_duplicate', 'unknown_method', 'unknown_profile'])
def test_selected_capabilities_require_declared_installed_closure(tmp_path, fault):
    selected = prepared_job(tmp_path)
    row = binding(selected, [SCALE, COMPENSATE], [FACS])
    if fault == 'implementation':
        row['software']['implementation_files'] = [pin for pin in row['software']['implementation_files']
            if not pin['path'].endswith('fluorescence_event_preparation.py')]
    elif fault in ('flowio', 'flowutils', 'numpy'):
        row['software']['distributions'] = [d for d in row['software']['distributions'] if d['name'].lower() != fault]
    elif fault.endswith('_metadata'):
        name = fault.removesuffix('_metadata')
        row['software']['runtime_files'] = [pin for pin in row['software']['runtime_files']
            if not (('/' + name + '-') in pin['path'] and pin['path'].endswith('/METADATA'))]
    elif fault == 'method_duplicate': row['preparation_methods'].append(SCALE)
    elif fault == 'profile_duplicate': row['report_profiles'].append(FACS)
    elif fault == 'unknown_method': row['preparation_methods'].append('arbitrary_callable')
    elif fault == 'unknown_profile': row['report_profiles'].append('arbitrary_report')
    with pytest.raises(ValueError):
        validate_fluorescence_bindings([row])


def test_each_schema_keeps_its_own_capabilities_software_and_parser(tmp_path):
    selected = prepared_job(tmp_path)
    first = binding(selected, [SCALE], [])
    second = binding(selected, [COMPENSATE], [FACS])
    second['software']['python_version'] = 'separately declared software'
    schema = fluorescence_tool_contracts([first, second], resource_kind='local', resource_id='here')[0]['input_schema']
    validator = Draft202012Validator(schema)
    request = plan(tmp_path, selected_job=selected)['requested_job']
    assert not validator.is_valid(request)  # No row supplies the combined work.
    request['native_fluorescence']['preparations'] = [selected['preparations'][0]]
    request['native_fluorescence']['report_inputs'] = []
    assert validator.is_valid(request)
    request['native_fluorescence']['report_inputs'] = selected['report_inputs']
    assert not validator.is_valid(request)
    request['native_fluorescence']['software'] = second['software']
    assert not validator.is_valid(request)


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('separate_matrix', [False, True])
def test_actual_scaling_compensation_lineage_and_report_envelopes(tmp_path, monkeypatch, operation, separate_matrix):
    selected = prepared_job(tmp_path, operation=operation, separate_matrix=separate_matrix)
    before = canonical(selected)
    from gene_annotation_episode import fluorescence_event_calculations as calculations
    monkeypatch.setattr(calculations, 'calculate_fluorescence_sheet', lambda *a, **k: pytest.fail('producer calculated scores'))
    calls = []
    scaling, compensation = preparation.prepare_fcs_scaling, preparation.prepare_spill_compensation
    def scale(*args, **kwargs):
        calls.append(('scale', kwargs['request']['key']))
        return scaling(*args, **kwargs)
    def compensate(*args, **kwargs):
        calls.append(('compensate', kwargs['request']['key']))
        return compensation(*args, **kwargs)
    monkeypatch.setattr(preparation, 'prepare_fcs_scaling', scale)
    monkeypatch.setattr(preparation, 'prepare_spill_compensation', compensate)
    original, manifest = run_selected(selected, tmp_path, monkeypatch)
    assert canonical(selected) == before
    assert calls == [('scale', 'scaled'), ('compensate', 'compensated')]
    assert manifest['failures'] == []
    assert [row['status'] for row in manifest['preparations']] == ['complete', 'complete']
    raw_batch = read_json(output(original, 'event_batch:0'))
    first, second = [read_json(output(original, f'prepared_batch:{index}')) for index in range(2)]
    assert values(raw_batch['parse']) == [[220, 120, 10], [40, 200, 20]]
    assert values(first['parse']) == [[110, 60, 1], [20, 100, 2]]
    for actual, expected in zip(values(second['parse']), [[100, 50, 1], [0, 100, 2]]):
        assert actual == pytest.approx(expected, abs=1e-12)
    assert first['parse']['channels'][2]['unit'] == second['parse']['channels'][2]['unit'] == 'seconds'
    assert second['parse']['domain']['scaling'] == first['parse']['domain']['scaling']
    assert second['parent_batch_file'] == manifest['preparations'][0]['batch_file']
    assert first['preparation_request_sha256'] == core.digest(selected['preparations'][0])
    assert validate_fluorescence_prepared_batch(first, original_plan=original, preparation_index=0,
        parent_batch_file=manifest['inputs'][0]['batch_file']) == first
    assert validate_fluorescence_prepared_batch(second, original_plan=original, preparation_index=1,
        parent_batch_file=manifest['preparations'][0]['batch_file']) == second
    report = read_json(output(original, 'report_batch:0'))
    assert validate_fluorescence_report_batch(report, original_plan=original, report_index=0) == report
    assert report['parse']['reports'][0]['value'] == 100
    assert report['parse']['reports'][0]['raw'] == '100.00'
    assert report['parse']['issues'] == []
    assert report['parse']['provenance']['producer_execution'] == 'unverified'
    for item in original['outputs']:
        path = output(original, item['role'])
        if item['role'].startswith(('event_batch:', 'prepared_batch:', 'prepared_data:', 'preparation_parameters:', 'report_batch:')):
            assert path.read_bytes() == core.canonical(read_json(path)) + b'\n'
    assert output(original, 'manifest').read_bytes() == canonical(manifest) + b'\n'
    assert output(original, 'event_input:0').read_bytes() == Path(selected['inputs'][0]['path']).read_bytes()
    assert output(original, 'report_input:0').read_bytes() == Path(selected['report_inputs'][0]['path']).read_bytes()


@pytest.mark.parametrize('problem', ['recipe_missing', 'recipe_tampered', 'recipe_wrong_object', 'recipe_malformed',
    'matrix_missing', 'parent_missing', 'parent_failed', 'backend_unavailable'])
def test_missing_preparation_dependencies_do_not_invent_payloads_or_execute_extra_work(tmp_path, monkeypatch, problem):
    selected = prepared_job(tmp_path, separate_matrix=True)
    target = selected['preparations'][1]
    support = next(row for row in selected['support_inputs'] if row['file'] == target['recipe_file'])
    if problem == 'recipe_missing': Path(support['path']).unlink()
    elif problem == 'recipe_tampered': Path(support['path']).write_bytes(b'changed')
    elif problem in ('recipe_wrong_object', 'recipe_malformed'):
        raw = b'{broken' if problem == 'recipe_malformed' else b'{"different":"recipe"}'
        Path(support['path']).write_bytes(raw)
        support['file'] = target['recipe_file'] = identity(raw, format='json')
    elif problem == 'matrix_missing':
        matrix = next(row for row in selected['support_inputs'] if row['file'] == target['recipe']['parameters']['matrix_file'])
        Path(matrix['path']).unlink()
    elif problem == 'parent_missing': Path(selected['inputs'][0]['path']).unlink()
    elif problem == 'parent_failed': selected['inputs'][0]['domain']['state'] = 'failed'
    elif problem == 'backend_unavailable':
        monkeypatch.setattr(readers, '_load_flowutils', lambda: None)
    calls = []
    actual = preparation.prepare_spill_compensation
    def compensate(*args, **kwargs):
        calls.append(kwargs['request']['key'])
        return actual(*args, **kwargs)
    monkeypatch.setattr(preparation, 'prepare_spill_compensation', compensate)
    original, manifest = run_selected(selected, tmp_path, monkeypatch)
    assert calls == (['compensated'] if problem == 'backend_unavailable' else [])
    if problem.startswith('parent_'):
        assert all(row['status'] == 'unavailable' for row in manifest['preparations'])
        assert all(row['parameters_file'] is None for row in manifest['preparations'])
    else:
        assert manifest['preparations'][0]['status'] == 'complete'
        assert output(original, 'prepared_batch:0').exists()
        second = manifest['preparations'][1]
        assert second['prepared_file'] is None
        if problem == 'backend_unavailable':
            assert second['status'] == 'unavailable' and second['parameters_file'] is not None
            batch = read_json(output(original, 'prepared_batch:1'))
            assert batch['parse']['source']['file'] is None and batch['parse']['events'] == []
            assert {row['code'] for row in batch['problems']} == {'backend_unavailable'}
        else:
            assert second['parameters_file'] is None and second['batch_file'] is None
            assert second['status'] == ('incompatible' if problem in ('recipe_wrong_object', 'recipe_malformed') else 'unavailable')
    assert manifest['reports'][0]['extent'] == 'complete'
    assert read_json(output(original, 'report_batch:0'))['parse']['reports'][0]['value'] == 100


@pytest.mark.parametrize('problem', ['missing', 'tampered', 'malformed', 'wrong_association'])
def test_missing_or_bad_report_association_preserves_actual_numbers_and_requested_link(tmp_path, monkeypatch, problem):
    selected = v2_job(tmp_path)
    report = add_facs_report(selected, tmp_path)
    support = selected['support_inputs'][0]
    if problem == 'missing': Path(support['path']).unlink()
    elif problem == 'tampered': Path(support['path']).write_bytes(b'changed')
    else:
        raw = b'{broken' if problem == 'malformed' else b'{"version":"wrong"}'
        Path(support['path']).write_bytes(raw)
        support['file'] = report['association_file'] = identity(raw, format='json')
    original, manifest = run_selected(selected, tmp_path, monkeypatch)
    batch = read_json(output(original, 'report_batch:0'))
    assert batch['parse']['reports'][0]['value'] == 100
    assert batch['parse']['reports'][0]['component_request'] == report['fields'][0]['component_request']
    assert batch['parse']['issues'] == [core.issue('native_population_unknown', 'input', source_key=report['source_key'])]
    assert (batch['association_file'] is None) == (problem in ('missing', 'tampered'))
    assert manifest['reports'][0]['extent'] == 'complete'


def test_missing_report_never_calls_parser_on_fabricated_empty_bytes(tmp_path, monkeypatch):
    selected = v2_job(tmp_path)
    report = add_facs_report(selected, tmp_path)
    Path(report['path']).unlink()
    monkeypatch.setattr(report_parser, 'parse_fluorescence_native_reports', lambda *a, **k: pytest.fail('absent report parsed'))
    original, manifest = run_selected(selected, tmp_path, monkeypatch)
    assert manifest['reports'] == [dict(report_index=0, source_file=None, batch_file=None, extent='unavailable')]
    assert not output(original, 'report_batch:0').exists()
    assert manifest['inputs'][0]['extent'] == 'complete'


@pytest.mark.parametrize('profile,raw,locator,value,token', [
    ('biomni_facs_log_548_v1',
        b'# FACS-based Cell Sorting and Enrichment Research Log\n## Enrichment Results\nSorted population: 1 cells\n',
        dict(kind='facs_metric', metric='selected_count', occurrence=0), 1, '1'),
    ('biomni_cytokine_log_548_v1',
        '# Cytokine Production Analysis by Flow Cytometry\nProcessing selected condition from file: sample.fcs\n'
        '- Identified channels: CD4=CD4-A, Cytokines=IFN-A\n- IFN-γ+ frequency: 33.33% of CD4+ T cells\n'.encode(),
        dict(kind='cytokine_log_metric', condition_ordinal=0, metric='marker_percent', marker_occurrence=0), 33.33, '33.33'),
    ('biomni_cytokine_csv_548_v1', ',IFN-γ\nselected,33.333333333333336\n'.encode(),
        dict(kind='cytokine_csv_cell', row_ordinal=0, column_ordinal=1, condition_label='selected', column_label='IFN-γ'),
        33.333333333333336, '33.333333333333336'),
])
def test_selected_report_profiles_retain_their_literal_numbers(tmp_path, monkeypatch, profile, raw, locator, value, token):
    selected = v2_job(tmp_path)
    report = dict(**file_input(tmp_path, 'selected-report', raw, 'text'), source_key='native-source', profile=profile,
        fields=[dict(key='native-field', locator=locator, component_request=None)], association_file=None)
    selected['report_inputs'] = [report]
    selected['parameters']['native_comparison_requests'] = ['native-field']
    monkeypatch.setattr(preparation, 'prepare_fcs_scaling', lambda *a, **k: pytest.fail('undeclared scaling'))
    monkeypatch.setattr(preparation, 'prepare_spill_compensation', lambda *a, **k: pytest.fail('undeclared compensation'))
    original, manifest = run_selected(selected, tmp_path, monkeypatch)
    parsed = read_json(output(original, 'report_batch:0'))['parse']
    row = parsed['reports'][0]
    assert row['value'] == value and row['raw'] == token
    assert raw[row['location']['byte_start']:row['location']['byte_end']].decode() == token
    assert parsed['provenance']['producer_execution'] == 'unverified'
    assert manifest['preparations'] == [] and manifest['reports'][0]['extent'] == 'complete'


def test_unicode_request_and_report_use_their_distinct_frozen_digest_encodings(tmp_path, monkeypatch):
    selected = prepared_job(tmp_path, compensate=False)
    selected['preparations'][0]['key'] = 'scaling α'
    selected['report_inputs'][0]['source_key'] = 'native.report α'
    original, manifest = run_selected(selected, tmp_path, monkeypatch)
    prepared = read_json(output(original, 'prepared_batch:0'))
    request = selected['preparations'][0]
    assert prepared['preparation_request_sha256'] == core.digest(request) != digest(request)
    prepared['preparation_request_sha256'] = digest(request)
    with pytest.raises(ValueError, match='binding_mismatch'):
        validate_fluorescence_prepared_batch(prepared, original_plan=original, preparation_index=0,
            parent_batch_file=manifest['inputs'][0]['batch_file'])
    report = read_json(output(original, 'report_batch:0'))
    request = selected['report_inputs'][0]
    assert report['report_input_sha256'] == digest(request) != core.digest(request)
    report['report_input_sha256'] = core.digest(request)
    with pytest.raises(ValueError, match='binding_mismatch'):
        validate_fluorescence_report_batch(report, original_plan=original, report_index=0)


def test_partial_input_preserves_unavailable_cells_and_exact_parent_lineage(tmp_path, monkeypatch):
    supplied = event_input(tmp_path, raw=b'A,B\n110,60\n,100\n')
    supplied['channels'] = [dict(supplied['channels'][0], key=f'raw.c{index}', ordinal=index, native_name=name)
        for index, name in enumerate(('A', 'B'))]
    source = prepared_job(tmp_path / 'matrix-source', scale=False, compensate=False, report=False)
    selected = v2_job(tmp_path, inputs=[supplied])
    selected['software'] = source['software']
    basis = file_input(tmp_path, 'basis.txt', b'explicit input matrix basis', 'text')
    selected['support_inputs'].append(basis)
    supplied['domain']['comparison_basis'] = dict(key='linear', evidence_file=basis['file'])
    matrix_input = source['inputs'][0]
    selected['support_inputs'].append(dict(file=matrix_input['source']['file'], path=matrix_input['path']))
    selected_preparation(selected, tmp_path, method=COMPENSATE, key='compensated', matrix_file=matrix_input['source']['file'])
    original, manifest = run_selected(selected, tmp_path, monkeypatch)
    batch = read_json(output(original, 'prepared_batch:0'))
    assert batch['status'] == 'partial'
    assert values(batch['parse'])[0] == pytest.approx([100, 50])
    assert values(batch['parse'])[1] == [None, None]
    assert [row['event_ordinal'] for row in batch['parse']['events']] == [0, 1]
    assert batch['parent_batch_file'] == manifest['inputs'][0]['batch_file']


@pytest.mark.parametrize('error', [MemoryError('selected interruption'), OSError(errno.ENOSPC, 'selected scratch failure')])
def test_later_preparation_failure_preserves_earlier_immutable_envelopes(tmp_path, monkeypatch, error):
    selected = prepared_job(tmp_path)
    original = plan(tmp_path, selected_job=selected)
    finite_driver(monkeypatch, original)
    def failed(*args, **kwargs):
        raise error
    monkeypatch.setattr(preparation, 'prepare_spill_compensation', failed)
    with pytest.raises(type(error)):
        driver.run_fluorescence_driver(original)
    assert output(original, 'event_batch:0').exists() and output(original, 'prepared_batch:0').exists()
    assert not output(original, 'prepared_batch:1').exists() and not output(original, 'manifest').exists()
    first = read_json(output(original, 'prepared_batch:0'))
    assert values(first['parse']) == [[110, 60, 1], [20, 100, 2]]


@pytest.mark.parametrize('role', ['preparation_parameters:1', 'prepared_data:1', 'prepared_batch:1', 'report_input:1', 'report_batch:1'])
def test_failure_indices_resolve_against_their_exact_role_collections(tmp_path, role):
    selected = prepared_job(tmp_path)
    add_facs_report(selected, tmp_path, key='second.report')
    original = plan(tmp_path, selected_job=selected)
    failure = validate_failure(dict(code='capture_file_unavailable', stage='capture', input_index=1, role=role))
    from gene_annotation_episode.native_fluorescence_contracts import validate_fluorescence_native_capture
    capture = dict(version='fluorescence_native_capture_v1', original_plan_sha256=digest(original),
        files=[dict(**row, retained=None) for row in original['outputs']],
        source_action_receipt_ref='artifact_' + '1' * 64, writer_closure_receipt_ref='artifact_' + '2' * 64,
        driver_started=True, failures=[failure])
    assert validate_fluorescence_native_capture(capture, original_plan=original) == capture
    capture['failures'][0].update(input_index=2, role=role.replace(':1', ':2'))
    with pytest.raises(ValueError, match='failure_index'):
        validate_fluorescence_native_capture(capture, original_plan=original)


@pytest.mark.parametrize('fault', ['parent', 'recipe', 'request_digest', 'control_digest', 'software', 'status', 'parameters', 'domain', 'source', 'channel'])
def test_prepared_envelope_rejects_changed_selected_relationships(tmp_path, monkeypatch, fault):
    original, manifest = run_selected(prepared_job(tmp_path, compensate=False, report=False), tmp_path, monkeypatch)
    batch = read_json(output(original, 'prepared_batch:0'))
    if fault == 'parent': batch['parent_batch_file'] = identity(b'other', format='fluorescence_parsed_batch_v1')
    if fault == 'recipe': batch['recipe_file'] = identity(b'other', format='json')
    if fault == 'request_digest': batch['preparation_request_sha256'] = '0' * 64
    if fault == 'control_digest': batch['original_plan_sha256'] = '0' * 64
    if fault == 'software': batch['software_sha256'] = '0' * 64
    if fault == 'status': batch['status'] = 'failed'
    if fault == 'parameters': batch['parameters_file'] = identity(b'other', format='fluorescence_resolved_preparation_v1')
    if fault == 'domain': batch['parse']['domain']['parent_domain_key'] = 'unselected'
    if fault == 'source': batch['parse']['source']['file'] = identity(b'other', format='fluorescence_prepared_event_data_v1')
    if fault == 'channel': batch['parse']['channels'][0]['unit'] = 'concentration'
    with pytest.raises(ValueError):
        validate_fluorescence_prepared_batch(batch, original_plan=original, preparation_index=0,
            parent_batch_file=manifest['inputs'][0]['batch_file'])


@pytest.fixture(scope='module')
def pinned_software(tmp_path_factory):
    return actual_software(tmp_path_factory.mktemp('prepared-producer-software'))


@pytest.mark.parametrize('operation', OPERATIONS)
def test_actual_selected_producer_authenticates_installed_native_closure(tmp_path, pinned_software, operation):
    selected = prepared_job(tmp_path, operation=operation, separate_matrix=True)
    selected['software'] = deepcopy(pinned_software)
    original = plan(tmp_path, selected_job=selected)
    execution = Path(original['identity']['execution_id']).parent
    execution.mkdir(parents=True)
    plan_path = execution / 'fluorescence-plan.json'
    plan_path.write_bytes(canonical(original) + b'\n')
    from gene_annotation_episode.native_fluorescence_contracts import fluorescence_driver_argv, fluorescence_environment
    env = os.environ.copy()
    env.update(fluorescence_environment(selected['software'], attempt_directory=original['attempt_directory']))
    env.update({name: str(execution) for name in ('TMPDIR', 'TMP', 'TEMP')})
    with (execution / 'stdout.log').open('wb') as stdout, (execution / 'stderr.log').open('wb') as stderr:
        completed = subprocess.run(fluorescence_driver_argv(original), cwd=execution, env=env, stdout=stdout, stderr=stderr)
    assert completed.returncode == 0, (execution / 'stderr.log').read_text()
    manifest = read_json(output(original, 'manifest'))
    assert validate_fluorescence_manifest(manifest, original_plan=original) == manifest
    assert manifest['failures'] == []
    assert all(row['status'] == 'complete' for row in manifest['preparations'])
    second = read_json(output(original, 'prepared_batch:1'))
    for actual, expected in zip(values(second['parse']), [[100, 50, 1], [0, 100, 2]]):
        assert actual == pytest.approx(expected, abs=1e-12)
    assert read_json(output(original, 'report_batch:0'))['parse']['reports'][0]['value'] == 100
