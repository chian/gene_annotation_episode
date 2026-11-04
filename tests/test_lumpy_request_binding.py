"""Compact LUMPY metadata controls; these tests do not commission or run a caller."""
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import lumpy_request_binding as compact
from gene_annotation_episode import native_lumpy_execution as native
from gene_annotation_episode.launch_instructions import SELECTION_SCHEMA
from gene_annotation_episode.practical_execution_records import validate_assignment
from gene_annotation_episode.state import Store

from test_native_lumpy_execution import job_fixture, plan_fixture, requested


def _forbidden(*args, **kwargs):
    raise AssertionError("metadata control must not read an input body or execute a program")


@pytest.fixture(autouse=True)
def no_native_work(monkeypatch):
    for name in ('run_lumpy', 'prepare_local_lumpy', 'freeze_lumpy_software_binding',
            'verify_driver_runtime', '_verify_native_runtime', '_invoke'):
        monkeypatch.setattr(native, name, _forbidden)


def _with_reused_files(job):
    """Three signal occurrences deliberately share the same BAM identity/path."""
    job = deepcopy(job)
    paired, split = job['request']['signals']
    split['bam'] = deepcopy(paired['bam'])
    repeated = deepcopy(paired)
    repeated['signal_key'] = paired['signal_key'] + '-again'
    job['request']['signals'].append(repeated)
    paths = {row['file']['artifact_ref']: row['path'] for row in job['input_bindings']}
    job['input_bindings'] = [dict(input_key=signal['signal_key'] + ':' + key,
        file=deepcopy(signal[key]), path=paths[signal[key]['artifact_ref']])
        for signal in job['request']['signals']
        for key in (('bam', 'histogram') if signal['kind'] == 'paired_end' else ('bam',))]
    return native.validate_lumpy_native_job(job)


def _public_request(job):
    value = deepcopy(job['request'])
    for signal in value['signals']:
        for key in (('bam', 'histogram') if signal['kind'] == 'paired_end' else ('bam',)):
            signal[key] = {field: signal[key][field] for field in ('artifact_ref', 'format')}
    return value


def _selection(job):
    return dict(version=compact.ASSIGNMENT_VERSION, resource_id='local', resource_kind='local',
        binding_ordinal_0based=0, endpoint='completed_job_outputs', request=_public_request(job),
        progress_requirements=[dict(key='handoff', credit=0, predicate=dict(kind='requested_job_handoff')),
            dict(key='outputs', credit=1, predicate=dict(kind='requested_job_outputs',
                output_roles=['vcf', 'stderr', 'seal', 'bam_headers']))],
        completion_keys=['outputs'], constraints=deepcopy(native.POLICY))


def _binding(job):
    return dict(operation=native.OPERATION, mode=native.MODE, software=deepcopy(job['software']))


def _schema_properties(value):
    if isinstance(value, list):
        return set().union(*(_schema_properties(item) for item in value)) if value else set()
    if not isinstance(value, dict):
        return set()
    result = set(value.get('properties', {}))
    for item in value.values():
        result.update(_schema_properties(item))
    return result


@pytest.fixture
def materialization(tmp_path, monkeypatch):
    """Real Store metadata, with no received context, action, receipt or admission claim."""
    job = _with_reused_files(job_fixture(tmp_path / 'inputs'))
    # Plausible prefix layout for PYTHONHOME; these invented pins are never executed.
    job['software']['driver_runtime']['python_executable'] = '/engineering/runtime/bin/python'
    store = Store(tmp_path / 'store')
    try:
        for occurrence in job['input_bindings']:
            reference = store.artifact(Path(occurrence['path']).read_bytes())
            assert reference == occurrence['file']['artifact_ref']
        monkeypatch.setattr(store, 'get_artifact', _forbidden)
        row = dict(resource_id='local', selection=_selection(job), binding=_binding(job),
            workspace=str(tmp_path / 'workspace'), store_path=str(store.path),
            assignment_id='engineering-metadata-only',
            input_files=[deepcopy(occurrence['file']) for occurrence in job['input_bindings']])
        yield store, row, job
    finally:
        store.close()


def test_public_request_and_tool_schema_expose_file2_without_host_pins(tmp_path):
    job = job_fixture(tmp_path)
    binding = _binding(job)
    selection = _selection(job)
    schema = compact.resource_assignment_schema('local', bindings=[binding])
    assert Draft202012Validator(schema).is_valid(selection)
    assert compact.validate_compact_assignment(selection, 'local', bindings=[binding]) == selection
    runtime_schema = deepcopy(schema)
    assert runtime_schema['properties'].pop('launch_instructions') == SELECTION_SCHEMA
    properties = _schema_properties(runtime_schema)
    assert not properties & {'sha256', 'size_bytes', 'software', 'path', 'workspace', 'input_bindings',
        'python_executable', 'module_root', 'native_runtime', 'argv', 'environment'}
    contracts = compact.lumpy_tool_contracts([binding], resource_kind='local', resource_id='local')
    tool, = contracts
    assert tool['name'] == native.OPERATION and tool['resources'] == 'local'
    assert tool['input_schema'] == schema
    assert tool['invocation_route'] == dict(kind='commission', routes=[dict(
        entry_role='launch', resource_id='local', resource_role='launch_local')])
    tool['input_schema']['properties'].clear()
    assert compact.resource_assignment_schema('local', bindings=[binding]) == schema
    # A public File is exactly its callable identity and declared processing label.
    selection['request']['signals'][0]['bam'] = deepcopy(job['request']['signals'][0]['bam'])
    assert not Draft202012Validator(schema).is_valid(selection)
    assert set(native.lumpy_execution_schema('Request')['properties']['signals']['items']['oneOf'][0]
        ['properties']['bam']['properties']) == {'artifact_ref', 'format', 'sha256', 'size_bytes'}


@pytest.mark.parametrize('changed', ['ordinal_float', 'ordinal_outside_binding', 'resource', 'duplicate_key',
    'missing_completion', 'wrong_endpoint', 'unsupported_output', 'host_field'])
def test_compact_assignment_rejects_changed_selection_contract(tmp_path, changed):
    job = job_fixture(tmp_path)
    selection = _selection(job)
    if changed == 'ordinal_float':
        selection['binding_ordinal_0based'] = 0.0
    elif changed == 'ordinal_outside_binding':
        selection['binding_ordinal_0based'] = 1
    elif changed == 'resource':
        selection['resource_id'] = 'other'
    elif changed == 'duplicate_key':
        selection['progress_requirements'][1]['key'] = 'handoff'
    elif changed == 'missing_completion':
        selection['completion_keys'] = ['not-a-requirement']
    elif changed == 'wrong_endpoint':
        selection['completion_keys'] = ['handoff']
    elif changed == 'unsupported_output':
        selection['progress_requirements'][1]['predicate']['output_roles'] = ['analysis_report']
    else:
        selection['software'] = deepcopy(job['software'])
    with pytest.raises(ValueError):
        compact.validate_compact_assignment(selection, 'local', bindings=[_binding(job)])


def test_launch_schema_selects_only_configured_lumpy_resources(tmp_path):
    job = job_fixture(tmp_path)
    resources = dict(local=dict(native_lumpy=[_binding(job)]), unrelated={})
    schema = compact.launch_assignment_schema(resources)
    selection = _selection(job)
    selection.pop('resource_id')
    launch = dict(version=compact.LAUNCH_VERSION, requests=dict(local=selection), constraints={})
    assert Draft202012Validator(schema).is_valid(launch)
    assert set(schema['properties']['requests']['properties']) == {'local'}
    launch['requests']['unrelated'] = deepcopy(selection)
    assert not Draft202012Validator(schema).is_valid(launch)


def test_private_materialization_preserves_duplicate_occurrences_and_constraints(materialization):
    store, row, job = materialization
    original = deepcopy(row)
    assignment = compact._materialize(store, row)
    assert row == original
    assert validate_assignment(assignment) == assignment
    assert assignment['resource_id'] == row['resource_id']
    assert assignment['workspace'] == row['workspace']
    assert assignment['endpoint'] == row['selection']['endpoint']
    for name in ('constraints', 'progress_requirements', 'completion_keys'):
        assert assignment[name] == row['selection'][name]
    native_job = assignment['requested_job']['native_lumpy']
    assert native_job['request'] == job['request'] and native_job['software'] == job['software']
    assert len(native_job['input_bindings']) == 5
    assert [r['input_key'] for r in native_job['input_bindings']] == [r['input_key'] for r in job['input_bindings']]
    assert [r['file'] for r in native_job['input_bindings']] == row['input_files']
    assert len({r['file']['artifact_ref'] for r in native_job['input_bindings']}) == 2
    for occurrence in native_job['input_bindings']:
        file = occurrence['file']
        assert occurrence['path'] == str(store.path / 'artifacts' / file['sha256'][:2] / file['sha256'])
    assert assignment['initial_context'] == dict(revision=0, cwd=row['workspace'], environment={})


@pytest.mark.parametrize('changed', ['missing_occurrence', 'reordered', 'sha256', 'size_bytes', 'format'])
def test_private_materialization_rejects_input_metadata_or_order_conflicts(materialization, changed):
    store, row, _ = materialization
    if changed == 'missing_occurrence':
        row['input_files'].pop()
    elif changed == 'reordered':
        row['input_files'][0], row['input_files'][1] = row['input_files'][1], row['input_files'][0]
    elif changed == 'sha256':
        row['input_files'][0]['sha256'] = 'f' * 64
    elif changed == 'size_bytes':
        row['input_files'][0]['size_bytes'] += 1
    else:
        row['input_files'][0]['format'] = 'vcf'
    with pytest.raises(ValueError, match='lumpy_request_input_(selection|metadata)_conflict'):
        compact._materialize(store, row)


@pytest.mark.parametrize('changed', ['resource_kind', 'resource_id', 'argv', 'input_binding'])
def test_materialized_assignment_keeps_native_request_validation(materialization, changed):
    store, row, _ = materialization
    assignment = compact._materialize(store, row)
    if changed == 'resource_kind':
        assignment['resource_kind'] = 'hpc'
    elif changed == 'resource_id':
        assignment.pop('resource_id')
    elif changed == 'argv':
        assignment['requested_job']['argv'][-1] = 'other-plan.json'
    else:
        bindings = assignment['requested_job']['native_lumpy']['input_bindings']
        bindings[0], bindings[1] = bindings[1], bindings[0]
    with pytest.raises(ValueError):
        validate_assignment(assignment)


def test_scientific_view_keeps_parameters_labels_unknowns_and_original_order(tmp_path):
    job = _with_reused_files(job_fixture(tmp_path))
    job['request']['parameters'].update(minimum_sample_weight=-4, trim_threshold='-0.0', probability_output=False)
    job['request']['signals'][0].update(output_sample_label='tumor-A',
        declared_sample_id='caller-declared label', reference_id=None, read_group=None)
    job['request']['signals'][1].update(declared_sample_id=None, reference_id='caller-reference-id', read_group='RG-1')
    original = deepcopy(job)
    view = compact.scientific_job_view(job)
    assert view == _public_request(job) and job == original
    assert len(view['signals']) == 3
    assert view['signals'][0]['parameters'] == job['request']['signals'][0]['parameters']
    assert view['signals'][1]['declared_sample_id'] is None
    assert view['signals'][0]['reference_id'] is None
    assert view['signals'][1]['reference_id'] == 'caller-reference-id'
    assert set(view) == set(job['request'])
    view['signals'][0]['bam']['format'] = 'changed-view'
    assert job == original


@pytest.mark.parametrize('carrier', ['job', 'requested', 'plan', 'binding', 'request', 'request_wrapper',
    'native_request', 'native_request_wrapper', 'assignment'])
def test_execution_projection_recognizes_exact_native_carriers_without_host_pins(tmp_path, carrier):
    job = job_fixture(tmp_path / 'input')
    expected = _public_request(job)
    values = dict(job=job, requested=requested(job, tmp_path),
        plan=plan_fixture(tmp_path / 'plan', job=job), binding=_binding(job), request=expected,
        request_wrapper=dict(request=expected), native_request=job['request'],
        native_request_wrapper=dict(request=job['request']), assignment=_selection(job))
    value = values[carrier]
    original = deepcopy(value)
    result = compact.select_lumpy_execution_values(value)
    if carrier == 'requested':
        assert result == dict(native_lumpy=dict(request=expected))
    elif carrier == 'binding':
        assert result == dict(operation=native.OPERATION, mode=native.MODE)
    elif carrier in {'request', 'native_request'}:
        assert result == expected
    elif carrier == 'assignment':
        assert result == _selection(job)
    else:
        assert result == dict(request=expected)
    assert value == original
    if carrier not in {'requested', 'binding'}:
        assert compact.select_lumpy_execution_values(result) == result


@pytest.mark.parametrize('value', [None, [], {'version': 'unknown_lumpy_v999'}, {'request': None},
    {'request': []}, {'request': 7}, {'request': 'opaque'}, {'software': 'arbitrary input metadata'},
    {'input_schema': {'version': native.REQUEST_VERSION}}])
def test_unrecognized_or_malformed_presentation_values_fall_back_literal(value):
    original = deepcopy(value)
    assert compact.select_lumpy_execution_values(value) is None
    assert value == original
