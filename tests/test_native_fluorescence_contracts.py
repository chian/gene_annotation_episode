"""Control/authority regressions, with explicitly synthetic supplied events.

These fixtures declare software shapes only. Actual installed software and the
native lifecycle are verified separately by the coordinator's bounded run.
"""
from copy import deepcopy
from pathlib import Path

import pytest

from gene_annotation_episode import fluorescence_event_contracts as core
from gene_annotation_episode.fluorescence_execution_common import canonical, digest, identity, same, validate_failure
from gene_annotation_episode.fluorescence_event_readers import parse_fluorescence_csv
from gene_annotation_episode.native_fluorescence_contracts import (
    ATTEMPT_DIRECTORY_NAME, IMPLEMENTATION_NAMES, OPERATIONS, POLICY, fluorescence_environment,
    fluorescence_output_files, requested_job_from_fluorescence, unavailable_fluorescence_input,
    validate_fluorescence_bindings, validate_fluorescence_job, validate_fluorescence_manifest,
    validate_fluorescence_native_capture, validate_fluorescence_parsed_batch,
    validate_fluorescence_run_plan, validate_fluorescence_software,
)


def pin(path):
    return {'path': str(path), 'sha256': '1' * 64, 'size_bytes': 1}


def software(*, fcs=False):
    module = Path('/declared-software/modules')
    value = {'version': 'fluorescence_software_v1', 'python': pin('/declared-software/python/bin/python3'),
        'python_version': 'declared fixture interpreter', 'python_home': '/declared-software/python',
        'module_root': str(module), 'implementation_files': [pin(module / 'gene_annotation_episode' / name)
            for name in IMPLEMENTATION_NAMES], 'dependency_roots': [], 'distributions': [],
        'runtime_files': [pin('/declared-software/python/lib/python3.12/json/__init__.py')]}
    if fcs:
        value['implementation_files'].append(pin(module / 'gene_annotation_episode/fluorescence_fcs_reader.py'))
        value['dependency_roots'] = ['/declared-software/dependencies']
        value['distributions'] = [{'name': 'FlowIO', 'version': '1.4.0', 'requires': []}]
        value['runtime_files'].extend([pin('/declared-software/dependencies/flowio/__init__.py'),
            pin('/declared-software/dependencies/flowio-1.4.0.dist-info/METADATA')])
    return value


def event_input(directory, raw=b'signal\n10\n20\n', *, index=0, parser='csv', name='signal'):
    path = Path(directory) / ('input-' + str(index) + '.bin')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    source, sample, domain, channel = (f'{label}-{index}' for label in ('source', 'sample', 'domain', 'channel'))
    preparation = {'state': 'not_applied', 'method': None, 'parameters_file': None}
    return {'parser': parser, 'path': str(path), 'source': {'key': source,
        'file': identity(raw, format='fcs' if parser == 'fcs_encoded' else 'csv' if parser == 'csv' else 'json'),
        'dataset_position': 0, 'format_profile': 'fcs_flowio_1_4_0_encoded' if parser == 'fcs_encoded' else parser,
        'extent': 'unavailable', 'native_event_count': None, 'metadata': [{'name': 'origin', 'value': 'synthetic α'}]},
        'sample': {'key': sample, 'primary_domain_key': domain, 'label': 'sample α', 'condition': None,
            'biological_replicate': None, 'technical_replicate': None, 'associations': []},
        'channels': [{'key': channel, 'ordinal': 0, 'native_name': name, 'label': None,
            'unit': 'arbitrary_instrument_units', 'analyte': None, 'measurement_origin': 'supplied_predicted'}],
        'domain': {'key': domain, 'sample_key': sample, 'source_key': source, 'parent_domain_key': None,
            'state': 'available', 'scale_kind': 'encoded' if parser == 'fcs_encoded' else 'as_supplied',
            'compensation': deepcopy(preparation), 'transformation': deepcopy(preparation),
            'correspondence': None, 'comparison_basis': None},
        'format_spec': {'encoding': 'utf-8', 'delimiter': ',', 'quotechar': '"', 'escapechar': None,
            'doublequote': True, 'header': True, 'missing_tokens': ['']} if parser == 'csv' else None}


def job(directory, *, inputs=None, operation=OPERATIONS[0]):
    inputs = inputs if inputs is not None else [event_input(directory)]
    populations, gates = [], []
    for i, binding in enumerate(inputs):
        populations.append({'key': f'population-{i}', 'sample_key': binding['sample']['key'],
            'kind': 'all', 'event_ordinals': None})
        gates.append({'key': f'gate-{i}', 'sample_key': binding['sample']['key'],
            'parent': {'kind': 'population', 'key': f'population-{i}'}, 'kind': 'pass_all',
            'domain_key': None, 'channel_key': None, 'lower': None, 'upper': None})
    return {'version': 'native_fluorescence_job_v1', 'operation': operation, 'mode': 'supplied_event_population',
        'inputs': inputs, 'support_inputs': [], 'definitions': {'populations': populations, 'gates': gates,
            'control_pairs': [], 'native_reports': []},
        'parameters': {'fraction_requests': [{'gate_key': 'gate-0', 'denominator': 'parent'}],
            'intensity_requests': [], 'control_requests': [], 'native_comparison_requests': []},
        'software': software(fcs=any(r['parser'] == 'fcs_encoded' for r in inputs)), 'output_prefix': 'output'}


def plan(directory, *, selected_job=None, operation_key='selected α', assignment=None):
    selected_job = selected_job or job(Path(directory) / 'inputs')
    requested = requested_job_from_fluorescence(selected_job, environment=fluorescence_environment(
        selected_job['software'], attempt_directory=str(Path(directory) / 'caller-temporaries')))
    run, episode = 'run-fixture', 'episode-fixture'
    root = Path(directory) / 'workspace/.episode-operations' / digest({'run': run, 'episode': episode}) / digest(operation_key)
    return validate_fluorescence_run_plan({'version': 'fluorescence_run_plan_v1', 'identity': {'run_id': run,
        'episode_id': episode, 'resource_id': 'declared-local', 'execution_id': str(root / 'native.json'),
        'attempt_id': digest(operation_key), 'operation_key': operation_key, 'requested_job_sha256': digest(requested),
        'assignment_sha256': digest(assignment) if assignment is not None else '2' * 64},
        'requested_job': requested, 'attempt_directory': str(root / ATTEMPT_DIRECTORY_NAME), 'policy': POLICY,
        'outputs': fluorescence_output_files(selected_job)})


def parsed_batch(original_plan, index=0):
    selected_job = original_plan['requested_job']['native_fluorescence']
    binding = selected_job['inputs'][index]
    parsed = parse_fluorescence_csv(Path(binding['path']).read_bytes(),
        **{k: binding[k] for k in ('source', 'sample', 'channels', 'domain', 'format_spec')})
    return {'version': 'fluorescence_parsed_batch_v1', 'original_plan_sha256': digest(original_plan),
        'input_index': index, 'input_binding_sha256': digest(binding),
        'software_sha256': digest(selected_job['software']), 'parse': parsed}


def manifest(original_plan):
    selected = original_plan['requested_job']['native_fluorescence']
    assert len(selected['inputs']) == 1 and selected['support_inputs'] == []
    batch = identity(core.canonical(parsed_batch(original_plan)) + b'\n', format='fluorescence_parsed_batch_v1')
    files = [selected['inputs'][0]['source']['file'], batch]
    declarations = [{'role': output['role'], 'declaration': {'relative_path': output['relative_path'],
        'format': output['format'], 'state': 'present', 'sha256': file['sha256'], 'size_bytes': file['size_bytes']}}
        for output, file in zip(original_plan['outputs'][:-1], files)]
    return {'version': 'fluorescence_native_manifest_v1', 'original_plan_sha256': digest(original_plan),
        'identity': deepcopy(original_plan['identity']), 'requested_job_sha256': digest(original_plan['requested_job']),
        'operation': selected['operation'], 'mode': selected['mode'], 'software_sha256': digest(selected['software']),
        'outputs': declarations, 'inputs': [{'input_index': 0, 'source_file': files[0], 'batch_file': batch, 'extent': 'complete'}],
        'support': [], 'failures': []}


def test_unicode_control_and_numerical_encodings_are_distinct():
    value = {'sample': 'α'}
    assert canonical(value) == '{"sample":"α"}'.encode()
    assert core.canonical(value) == b'{"sample":"\\u03b1"}'
    assert digest(value) != core.digest(value)
    assert not same({'n': 1}, {'n': True})


@pytest.mark.parametrize('operation', OPERATIONS)
def test_both_operation_names_use_same_supplied_event_contract(tmp_path, operation):
    value = job(tmp_path, operation=operation)
    before = deepcopy(value)
    validated = validate_fluorescence_job(value)
    assert value == before == validated and validated is not value
    assert validate_fluorescence_software(value['software'])['distributions'] == []
    assert validate_fluorescence_bindings([{'operation': operation, 'mode': value['mode'],
        'parsers': ['csv', 'table_snapshot'], 'software': value['software']}])


def test_definitions_with_missing_future_subset_and_correspondence_are_not_rewritten(tmp_path):
    first = event_input(tmp_path, index=0)
    second = event_input(tmp_path, index=1)
    second['sample'] = deepcopy(first['sample'])
    second['domain'].update(sample_key=first['sample']['key'], parent_domain_key=first['domain']['key'],
        correspondence=[{'source_ordinal': 0, 'event_ordinal': 999}])
    value = job(tmp_path, inputs=[first, second])
    value['definitions']['populations'][0].update(kind='subset', event_ordinals=[0, 999])
    before = deepcopy(value)
    assert validate_fluorescence_job(value) == before
    assert value == before


@pytest.mark.parametrize('change', ['count', 'extent', 'duplicate_domain', 'native_report', 'comparison', 'support_extra', 'unknown_gate'])
def test_malformed_or_unsupported_jobs_reject_before_work(tmp_path, change):
    value = job(tmp_path)
    if change == 'count': value['inputs'][0]['source']['native_event_count'] = 1
    if change == 'extent': value['inputs'][0]['source']['extent'] = 'complete'
    if change == 'duplicate_domain': value['inputs'].append(deepcopy(value['inputs'][0]))
    if change == 'native_report': value['definitions']['native_reports'] = [{}]
    if change == 'comparison': value['parameters']['native_comparison_requests'] = ['native']
    if change == 'support_extra': value['support_inputs'] = [{'file': identity(b'extra', format='json'), 'path': '/extra'}]
    if change == 'unknown_gate': value['parameters']['fraction_requests'][0]['gate_key'] = 'unknown'
    with pytest.raises(ValueError): validate_fluorescence_job(value)


def test_support_operands_exactly_cover_supplied_associations_and_preparation(tmp_path):
    value = job(tmp_path)
    file = identity(b'mapping', format='json')
    value['inputs'][0]['sample']['associations'] = [{'namespace': 'gene', 'identifier': 'declared', 'file': file,
        'source_key': None, 'location': {k: None for k in ('record_ordinal', 'line_start', 'line_end', 'byte_start', 'byte_end')}}]
    with pytest.raises(ValueError, match='support_input_mismatch'): validate_fluorescence_job(value)
    value['support_inputs'] = [{'file': file, 'path': str(tmp_path / 'mapping.json')}]
    assert validate_fluorescence_job(value) == value
    value['support_inputs'].append(deepcopy(value['support_inputs'][0]))
    with pytest.raises(ValueError, match='support_input_mismatch'): validate_fluorescence_job(value)


def test_fcs_binding_requires_installation_declaration_not_source_fixture(tmp_path):
    value = job(tmp_path, inputs=[event_input(tmp_path, parser='fcs_encoded')])
    assert validate_fluorescence_job(value)
    value['software']['runtime_files'] = [p for p in value['software']['runtime_files'] if not p['path'].endswith('METADATA')]
    with pytest.raises(ValueError, match='installed_flowio'): validate_fluorescence_job(value)


@pytest.mark.parametrize('change', ['plan', 'software', 'binding', 'input_index', 'sample', 'metadata', 'origin', 'unit', 'domain', 'label', 'bool_ordinal'])
def test_batch_authentication_rejects_altered_binding_or_declared_meaning(tmp_path, change):
    original = plan(tmp_path)
    value = parsed_batch(original)
    if change == 'plan': value['original_plan_sha256'] = '0' * 64
    if change == 'software': value['software_sha256'] = '0' * 64
    if change == 'binding': value['input_binding_sha256'] = '0' * 64
    if change == 'input_index': value['input_index'] = True
    if change == 'sample': value['parse']['sample']['label'] = 'guessed'
    if change == 'metadata': value['parse']['source']['metadata'].append({'name': 'invented', 'value': 'marker'})
    if change == 'origin': value['parse']['events'][0]['values'][0]['measurement']['state'] = 'observed'
    if change == 'unit': value['parse']['channels'][0]['unit'] = 'concentration'
    if change == 'domain': value['parse']['domain']['scale_kind'] = 'scaled'
    if change == 'label': value['parse']['channels'][0]['label'] = 'inferred marker'
    if change == 'bool_ordinal': value['parse']['channels'][0]['ordinal'] = False
    with pytest.raises(ValueError): validate_fluorescence_parsed_batch(value, original_plan=original, input_index=0)


def test_actual_observed_column_name_can_fill_only_a_null_binding(tmp_path):
    binding = event_input(tmp_path, raw='α\n1\n'.encode(), name=None)
    original = plan(tmp_path, selected_job=job(tmp_path, inputs=[binding]))
    batch = parsed_batch(original)
    copied = validate_fluorescence_parsed_batch(batch, original_plan=original, input_index=0)
    assert copied['parse']['channels'][0]['native_name'] == 'α'
    assert copied is not batch and copied['parse'] is not batch['parse']


@pytest.mark.parametrize('change', [None, 'prefix', 'appended_namespace', 'native_count', 'filled_name', 'filled_label'])
def test_fcs_observed_metadata_fields_have_exact_limited_binding_rules(tmp_path, change):
    binding = event_input(tmp_path, parser='fcs_encoded', name=None)
    original = plan(tmp_path, selected_job=job(tmp_path, inputs=[binding]))
    # Explicit control fixture for the decoded-metadata interface. This is not
    # an authentic FCS parse or a claimed installed FlowIO result.
    parsed = unavailable_fluorescence_input(binding, code='source_unavailable')
    parsed['source']['metadata'].extend([{'name': 'flowio.header.version', 'value': '3.1'},
        {'name': 'flowio.text.tot', 'value': '8'}, {'name': 'flowio.text.p1n', 'value': 'native name'},
        {'name': 'flowio.text.p1s', 'value': 'native label'}])
    parsed['source']['native_event_count'] = 8
    parsed['channels'][0].update(native_name='native name', label='native label')
    value = {'version': 'fluorescence_parsed_batch_v1', 'original_plan_sha256': digest(original),
        'input_index': 0, 'input_binding_sha256': digest(binding),
        'software_sha256': digest(original['requested_job']['native_fluorescence']['software']), 'parse': parsed}
    if change == 'prefix': parsed['source']['metadata'][0]['value'] = 'altered supplied metadata'
    if change == 'appended_namespace': parsed['source']['metadata'].append({'name': 'inferred.marker', 'value': 'unasked'})
    if change == 'native_count': parsed['source']['native_event_count'] = 7
    if change == 'filled_name': parsed['channels'][0]['native_name'] = 'guessed name'
    if change == 'filled_label': parsed['channels'][0]['label'] = 'guessed marker'
    if change is None:
        assert validate_fluorescence_parsed_batch(value, original_plan=original, input_index=0) == value
    else:
        with pytest.raises(ValueError): validate_fluorescence_parsed_batch(value, original_plan=original, input_index=0)


@pytest.mark.parametrize('change', ['plan', 'request', 'software', 'identity', 'output_order', 'index', 'source', 'batch', 'absent_batch'])
def test_manifest_authentication_rejects_conflicting_producer_or_row_relationship(tmp_path, change):
    original = plan(tmp_path)
    value = manifest(original)
    assert validate_fluorescence_manifest(value, original_plan=original) == value
    if change == 'plan': value['original_plan_sha256'] = '0' * 64
    if change == 'request': value['requested_job_sha256'] = '0' * 64
    if change == 'software': value['software_sha256'] = '0' * 64
    if change == 'identity': value['identity']['operation_key'] = 'another selection'
    if change == 'output_order': value['outputs'].reverse()
    if change == 'index': value['inputs'][0]['input_index'] = True
    if change == 'source': value['inputs'][0]['source_file'] = identity(b'other', format='csv')
    if change == 'batch': value['inputs'][0]['batch_file'] = identity(b'other', format='fluorescence_parsed_batch_v1')
    if change == 'absent_batch':
        value['outputs'][1]['declaration'].update(state='absent', sha256=None, size_bytes=None)
    with pytest.raises(ValueError): validate_fluorescence_manifest(value, original_plan=original)


def test_unavailable_input_keeps_original_identity_and_failed_domain(tmp_path):
    binding = event_input(tmp_path)
    binding['domain']['state'] = 'failed'
    result = unavailable_fluorescence_input(binding, code='retained_artifact_mismatch')
    assert result['source']['file'] == binding['source']['file']
    assert result['source']['native_event_count'] is None and result['events'] == []
    assert result['domain']['state'] == 'failed'
    assert result['issues'][0]['source_key'] == binding['source']['key']


@pytest.mark.parametrize('change', ['identity', 'request', 'policy', 'output', 'overlap'])
def test_original_attempt_structure_cannot_be_retargeted(tmp_path, change):
    value = plan(tmp_path)
    if change == 'identity': value['identity']['attempt_id'] = '0' * 64
    if change == 'request': value['identity']['requested_job_sha256'] = '0' * 64
    if change == 'policy': value['policy']['wall_seconds'] = 60
    if change == 'output': value['outputs'][0]['relative_path'] = 'other/input.bin'
    if change == 'overlap':
        value['requested_job']['native_fluorescence']['inputs'][0]['path'] = str(Path(value['attempt_directory']) / 'in.bin')
        value['identity']['requested_job_sha256'] = digest(value['requested_job'])
    with pytest.raises(ValueError): validate_fluorescence_run_plan(value)


@pytest.mark.parametrize('value', [
    {'code': 'input_file_unavailable', 'stage': 'input', 'input_index': 1, 'role': 'event_input:0'},
    {'code': 'input_file_unavailable', 'stage': 'input', 'input_index': None, 'role': 'event_input:0'},
    {'code': 'invented', 'stage': 'input', 'input_index': None, 'role': None},
])
def test_failure_roles_and_indices_have_constrained_meanings(value):
    with pytest.raises(ValueError): validate_failure(value)


@pytest.mark.parametrize('access', [None, True, False])
def test_input_admission_needs_known_receipt_and_exact_store_path(tmp_path, monkeypatch, access):
    from gene_annotation_episode import fluorescence_operands as operands
    from gene_annotation_episode.state import Store
    selected = job(tmp_path)
    binding = selected['inputs'][0]
    raw = Path(binding['path']).read_bytes()
    with Store(tmp_path / 'retained') as store:
        reference = store.artifact(raw)
        binding['path'] = str(store.path / 'artifacts' / binding['source']['file']['sha256'][:2] / binding['source']['file']['sha256'])
        requested = requested_job_from_fluorescence(selected, environment=fluorescence_environment(selected['software'],
            attempt_directory=str(tmp_path / 'caller-temp')))
        assignment = {'requested_job': requested}
        monkeypatch.setattr(operands, '_received_context', lambda *args: {reference})
        callback = lambda context, ref, kind: access
        if access is False:
            with pytest.raises(ValueError, match='protected_reference_denied'):
                operands.validate_fluorescence_job_inputs(store, None, assignment, reference_access=callback)
            return
        assert operands.validate_fluorescence_job_inputs(store, None, assignment, reference_access=callback) == [reference]
        # A permissive callback never replaces actual received-reference admission.
        monkeypatch.setattr(operands, '_received_context', lambda *args: set())
        with pytest.raises(ValueError, match='not_received'):
            operands.validate_fluorescence_job_inputs(store, None, assignment, reference_access=callback)
        monkeypatch.setattr(operands, '_received_context', lambda *args: {reference})
        assignment['requested_job']['native_fluorescence']['inputs'][0]['path'] = '/unreceived/alias'
        with pytest.raises(ValueError, match='selected_path_mismatch'):
            operands.validate_fluorescence_job_inputs(store, None, assignment, reference_access=callback)
