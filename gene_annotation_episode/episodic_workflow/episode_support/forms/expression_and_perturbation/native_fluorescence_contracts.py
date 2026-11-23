"""Original selected fluorescence jobs and attributable retained parse batches.

Only stdlib and the unchanged scientific data validators are imported here.
Validation performs no decoding, file access, acquisition or calculation.
"""
from gene_annotation_episode.episodic_workflow.episode_support.tools.retained_native_read_profiles import retained_policy_matches
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS
from copy import deepcopy
import os
from pathlib import PurePosixPath
import re
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation import fluorescence_event_contracts as core
from gene_annotation_episode.episodic_workflow.episode_support.jobs.fluorescence_execution_common import canonical, closed, digest, require, same, unique, validate_failure
OPERATIONS = ('perform_facs_cell_sorting', 'analyze_cytokine_production_in_cd4_tcells')
MODE = 'supplied_event_population'
PARSERS = ('csv', 'table_snapshot', 'fcs_encoded')
PREPARATION_METHODS = ('fcs_scale_flowio_1_4_0', 'spill_compensate_flowutils_1_2_2')
REPORT_PROFILES = ('biomni_facs_log_548', 'biomni_cytokine_log_548', 'biomni_cytokine_csv_548')
RUN_PLAN_FILENAME = 'fluorescence-plan.json'
ATTEMPT_DIRECTORY_NAME = 'fluorescence-attempt'
DRIVER_MODULE = 'gene_annotation_episode.native_fluorescence_driver'
POLICY = {'memory_bytes': ENVIRONMENT_BOUNDS['memory_bytes'], 'scratch_bytes': 4294967296}
IMPLEMENTATION_NAMES = ('__init__.py', 'fluorescence_execution_common.py', 'fluorescence_event_contracts.py', 'fluorescence_event_readers.py', 'native_fluorescence_contracts.py', 'native_fluorescence_storage.py', 'native_fluorescence_driver.py')

def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def array(items, **kw):
    return {'type': 'array', 'items': items, **kw}

def nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}
TEXT = {'type': 'string', 'minLength': 1, 'pattern': '^[^\\u0000-\\u001f\\u007f]+$'}
LABEL = {'type': 'string'}
SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
COUNT = {'type': 'integer', 'minimum': 0}
NULL = {'type': 'null'}
PIN_SCHEMA = obj({'path': TEXT})
FILE_SCHEMA = obj({'artifact_ref': TEXT, 'sha256': SHA, 'size_bytes': COUNT, 'format': TEXT})
LOCATION_SCHEMA = obj({name: nullable({'type': 'integer', 'minimum': 1 if name.startswith('line_') else 0}) for name in ('record_ordinal', 'line_start', 'line_end', 'byte_start', 'byte_end')})
ASSOCIATION_SCHEMA = obj({'namespace': TEXT, 'identifier': TEXT, 'file': FILE_SCHEMA, 'source_key': nullable(TEXT), 'location': LOCATION_SCHEMA})
SOURCE_SCHEMA = obj({'key': TEXT, 'file': FILE_SCHEMA, 'dataset_position': COUNT, 'format_profile': TEXT, 'extent': {'const': 'unavailable'}, 'native_event_count': NULL, 'metadata': array(obj({'name': LABEL, 'value': LABEL}))})
SAMPLE_SCHEMA = obj({'key': TEXT, 'primary_domain_key': TEXT, **{name: nullable(LABEL) for name in ('label', 'condition', 'biological_replicate', 'technical_replicate')}, 'associations': array(ASSOCIATION_SCHEMA)})
CHANNEL_SCHEMA = obj({'key': TEXT, 'ordinal': COUNT, **{name: nullable(LABEL) for name in ('native_name', 'label', 'unit')}, 'analyte': nullable(ASSOCIATION_SCHEMA), 'measurement_origin': {'enum': ['observed', 'supplied_predicted']}})
PREPARATION_SCHEMA = obj({'state': {'enum': ['not_applied', 'applied', 'unknown', 'failed']}, 'method': nullable(TEXT), 'parameters_file': nullable(FILE_SCHEMA)})
BASIS_SCHEMA = obj({'key': TEXT, 'evidence_file': FILE_SCHEMA})
DOMAIN_SCHEMA = obj({'key': TEXT, 'sample_key': TEXT, 'source_key': TEXT, 'parent_domain_key': nullable(TEXT), 'state': {'enum': ['available', 'unavailable', 'failed']}, 'scale_kind': {'enum': ['encoded', 'scaled', 'as_supplied']}, 'compensation': PREPARATION_SCHEMA, 'transformation': PREPARATION_SCHEMA, 'correspondence': nullable(array(obj({'source_ordinal': COUNT, 'event_ordinal': COUNT}))), 'comparison_basis': nullable(BASIS_SCHEMA)})
DOMAIN_SCHEMA['properties']['scaling'] = deepcopy(PREPARATION_SCHEMA)
CSV_SCHEMA = obj({'encoding': {'enum': ['utf-8', 'utf-8-sig']}, 'delimiter': {'type': 'string', 'minLength': 1, 'maxLength': 1}, 'quotechar': {'type': 'string', 'minLength': 1, 'maxLength': 1}, 'escapechar': nullable({'type': 'string', 'minLength': 1, 'maxLength': 1}), 'doublequote': {'type': 'boolean'}, 'header': {'type': 'boolean'}, 'missing_tokens': array(LABEL)})
EVENT_INPUT_SCHEMA = obj({'parser': {'enum': list(PARSERS)}, 'path': TEXT, 'source': SOURCE_SCHEMA, 'sample': SAMPLE_SCHEMA, 'channels': array(CHANNEL_SCHEMA), 'domain': DOMAIN_SCHEMA, 'format_spec': nullable(CSV_SCHEMA)})
POPULATION_SCHEMA = obj({'key': TEXT, 'sample_key': TEXT, 'kind': {'enum': ['all', 'subset']}, 'event_ordinals': nullable(array(COUNT, uniqueItems=True))})
BOUND_SCHEMA = nullable(obj({'value': {'type': 'number'}, 'inclusive': {'type': 'boolean'}}))
GATE_SCHEMA = obj({'key': TEXT, 'sample_key': TEXT, 'parent': obj({'kind': {'enum': ['population', 'gate']}, 'key': TEXT}), 'kind': {'enum': ['threshold', 'pass_all']}, 'domain_key': nullable(TEXT), 'channel_key': nullable(TEXT), 'lower': BOUND_SCHEMA, 'upper': BOUND_SCHEMA})
CONTROL_SCHEMA = obj({'key': TEXT, 'target_gate_key': TEXT, 'control_gate_key': TEXT, 'denominator': {'enum': ['parent', 'evaluable']}, 'comparison_basis': BASIS_SCHEMA})
PARAMETERS_SCHEMA = obj({'fraction_requests': array(obj({'gate_key': TEXT, 'denominator': {'enum': ['parent', 'evaluable']}})), 'intensity_requests': array(obj({'gate_key': TEXT, 'domain_key': TEXT, 'channel_key': TEXT})), 'control_requests': array(obj({'control_key': TEXT, 'include_legacy_clipping': {'type': 'boolean'}})), 'native_comparison_requests': {'type': 'array', 'maxItems': 0}})
SOFTWARE_SCHEMA = obj({'version': {'const': 'fluorescence_software'}, 'python': PIN_SCHEMA, 'python_version': TEXT, 'python_home': TEXT, 'module_root': TEXT, 'implementation_files': array(PIN_SCHEMA, minItems=1), 'dependency_roots': array(TEXT, uniqueItems=True), 'distributions': array(obj({'name': TEXT, 'version': TEXT, 'requires': array(LABEL)})), 'runtime_files': array(PIN_SCHEMA, minItems=1)})
JOB_SCHEMA = obj({'version': {'const': 'native_fluorescence_job'}, 'operation': {'enum': list(OPERATIONS)}, 'mode': {'const': MODE}, 'inputs': array(EVENT_INPUT_SCHEMA, minItems=1), 'support_inputs': array(obj({'file': FILE_SCHEMA, 'path': TEXT})), 'definitions': obj({'populations': array(POPULATION_SCHEMA), 'gates': array(GATE_SCHEMA), 'control_pairs': array(CONTROL_SCHEMA), 'native_reports': {'type': 'array', 'maxItems': 0}}), 'parameters': PARAMETERS_SCHEMA, 'software': SOFTWARE_SCHEMA, 'output_prefix': TEXT})
OUTPUT_CHANNEL_SCHEMA = obj({k: deepcopy(v) for k, v in CHANNEL_SCHEMA['properties'].items()
    if k != 'measurement_origin'})
SCALING_RECIPE_SCHEMA = obj({'version': {'const': 'fluorescence_preparation_recipe'},
    'method': {'const': PREPARATION_METHODS[0]},
    'parameters': obj({'metadata_policy': {'const': 'strict_present_fcs_metadata'}})})
COMPENSATION_RECIPE_SCHEMA = obj({'version': {'const': 'fluorescence_preparation_recipe'},
    'method': {'const': PREPARATION_METHODS[1]}, 'parameters': obj({'matrix_file': FILE_SCHEMA,
        'dataset_position': COUNT, 'keyword': {'enum': ['spill', 'spillover']},
        'input_domain_basis': BASIS_SCHEMA, 'axes': array(obj({'native_label': TEXT,
            'input_channel_key': TEXT, 'input_ordinal': COUNT}), minItems=1)})})
PREPARATION_REQUEST_SCHEMA = obj({'key': TEXT,
    'input': obj({'kind': {'enum': ['event_input', 'preparation']}, 'index': COUNT}),
    'output': obj({'key': TEXT, 'source_key': TEXT, 'sample_key': TEXT,
        'channels': array(OUTPUT_CHANNEL_SCHEMA, minItems=1), 'comparison_basis': nullable(BASIS_SCHEMA)}),
    'recipe_file': FILE_SCHEMA, 'recipe': {'anyOf': [SCALING_RECIPE_SCHEMA, COMPENSATION_RECIPE_SCHEMA]}})
REPORT_CELL_REQUEST_SCHEMA = {'anyOf': [obj({'kind': {'const': kind},
    **{name: TEXT if name in required else NULL for name in core._CELL_IDENTITIES},
    'denominator': {'enum': ['parent', 'evaluable']} if kind == 'fraction' else {'const': 'none'},
    'metric': {'enum': list(metrics)}}) for kind, required, metrics in (
        ('population', {'gate_key'}, core._POPULATION_METRICS),
        ('fraction', {'gate_key'}, core._FRACTION_METRICS),
        ('intensity', {'gate_key', 'domain_key', 'channel_key'}, core._INTENSITY_METRICS),
        ('control', {'control_key'}, core._CONTROL_METRICS))]}
_REPORT_LOCATORS = (
    obj({'kind': {'const': 'facs_metric'}, 'metric': {'enum': ['original_count', 'selected_count',
        'selected_percent', 'selected_mean', 'selected_median', 'lower_remaining_count', 'upper_remaining_count']},
        'occurrence': COUNT}),
    obj({'kind': {'const': 'cytokine_log_metric'}, 'condition_ordinal': COUNT,
        'metric': {'enum': ['parent_count', 'original_count', 'marker_percent']}, 'marker_occurrence': nullable(COUNT)}),
    obj({'kind': {'const': 'cytokine_csv_cell'}, 'row_ordinal': COUNT,
        'column_ordinal': {'type': 'integer', 'minimum': 1}, 'condition_label': LABEL,
        'column_label': {'enum': ['IFN-γ', 'IL-17', 'IFN-γ (background-subtracted)', 'IL-17 (background-subtracted)']}}))
REPORT_INPUT_SCHEMA = {'anyOf': [obj({'file': FILE_SCHEMA, 'path': TEXT, 'source_key': TEXT,
    'profile': {'const': profile}, 'fields': array(obj({'key': TEXT, 'locator': locator,
        'component_request': nullable(REPORT_CELL_REQUEST_SCHEMA)})), 'association_file': nullable(FILE_SCHEMA)})
    for profile, locator in zip(REPORT_PROFILES, _REPORT_LOCATORS)]}
JOB_SCHEMA['properties'].update(preparations=array(PREPARATION_REQUEST_SCHEMA), report_inputs=array(REPORT_INPUT_SCHEMA))
JOB_SCHEMA['required'] = list(JOB_SCHEMA['properties'])
JOB_SCHEMA['properties']['parameters']['properties']['native_comparison_requests'] = array(TEXT, uniqueItems=True)

def path_value(value, *, absolute):
    require(type(value) is str and bool(value) and (not any((c in value for c in '\x00\r\n\\'))), 'invalid_fluorescence_path')
    path = PurePosixPath(value)
    require(path.is_absolute() == absolute and str(path) == value and ('..' not in path.parts) and (value not in ('.', '/')) and (not value.startswith('//')), 'invalid_fluorescence_path')
    return path

def _list(value):
    require(type(value) is list, 'invalid_fluorescence_contract')

def _key(value):
    core._key(value, 'invalid_parameters')

def _sha(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None, 'invalid_fluorescence_digest')

def _pin(value):
    closed(value, 'path')
    path_value(value['path'], absolute=True)

def validate_fluorescence_software(value):
    closed(value, SOFTWARE_SCHEMA['properties'])
    require(value['version'] == 'fluorescence_software', 'invalid_fluorescence_software')
    _key(value['python_version'])
    for name in ('python_home', 'module_root'):
        path_value(value[name], absolute=True)
    for name in ('implementation_files', 'runtime_files', 'dependency_roots', 'distributions'):
        _list(value[name])
    require(bool(value['implementation_files']) and bool(value['runtime_files']), 'fluorescence_software_closure_missing')
    roots = [path_value(v, absolute=True) for v in value['dependency_roots']]
    require(len(set(roots)) == len(roots), 'duplicate_fluorescence_dependency_root')
    pins = [value['python'], *value['implementation_files'], *value['runtime_files']]
    for pin in pins:
        _pin(pin)
    require(len({p['path'] for p in pins}) == len(pins), 'duplicate_fluorescence_software_pin')
    module_root = PurePosixPath(value['module_root'])
    implementation = {p['path'] for p in value['implementation_files']}
    require(all((PurePosixPath(p).is_relative_to(module_root) for p in implementation)) and {str(module_root / 'gene_annotation_episode' / n) for n in IMPLEMENTATION_NAMES} <= implementation, 'fluorescence_implementation_closure_missing')
    require(any((PurePosixPath(p['path']).is_relative_to(PurePosixPath(value['python_home']) / 'lib') for p in value['runtime_files'])), 'fluorescence_standard_library_binding_missing')
    require(all((any((PurePosixPath(p['path']).is_relative_to(r) for p in value['runtime_files'])) for r in roots)), 'fluorescence_dependency_root_unbound')
    names = []
    for row in value['distributions']:
        closed(row, 'name version requires')
        _key(row['name'])
        _key(row['version'])
        _list(row['requires'])
        require(all((type(v) is str for v in row['requires'])), 'invalid_fluorescence_software')
        names.append(re.sub('[-_.]+', '-', row['name']).lower())
    require(len(set(names)) == len(names), 'duplicate_fluorescence_distribution')
    canonical(value)
    return deepcopy(value)

def _parser_software(software, parsers):
    if 'fcs_encoded' not in parsers:
        return
    distribution = next((r for r in software['distributions'] if re.sub('[-_.]+', '-', r['name']).lower() == 'flowio'), None)
    paths = [PurePosixPath(r['path']) for r in software['runtime_files']]
    require(distribution is not None and distribution['version'] == '1.4.0' and (str(PurePosixPath(software['module_root']) / 'gene_annotation_episode/fluorescence_fcs_reader.py') in {r['path'] for r in software['implementation_files']}) and any((p.name == 'METADATA' and re.fullmatch('flowio-1\\.4\\.0\\.dist-info', p.parent.name, re.IGNORECASE) for p in paths)) and any((p.name == '__init__.py' and p.parent.name == 'flowio' for p in paths)), 'fluorescence_installed_flowio_1_4_0_required')

def _input(binding):
    closed(binding, EVENT_INPUT_SCHEMA['properties'])
    require(type(binding['parser']) is str and binding['parser'] in PARSERS, 'invalid_fluorescence_parser')
    path_value(binding['path'], absolute=True)
    request = {k: binding[k] for k in ('source', 'sample', 'channels', 'domain')}
    core.validate_event_input_request(**request)
    require(binding['source']['extent'] == 'unavailable' and binding['source']['native_event_count'] is None, 'fluorescence_source_placeholder_required')
    if binding['parser'] == 'csv':
        core.validate_csv_request(**request, format_spec=binding['format_spec'])
    else:
        require(binding['format_spec'] is None, 'invalid_fluorescence_format_spec')
    if binding['parser'] == 'fcs_encoded':
        require(binding['source']['format_profile'] == 'fcs_flowio_1_4_0_encoded', 'invalid_fluorescence_fcs_profile')
        domain = binding['domain']
        require(domain['scale_kind'] == 'encoded' and domain['parent_domain_key'] is None and (domain['correspondence'] is None) and (domain['key'] == binding['sample']['primary_domain_key']), 'invalid_fluorescence_fcs_domain')

def _definitions(job):
    """Validate declaration joins without manufacturing an event universe."""
    definitions = job['definitions']
    closed(definitions, 'populations gates control_pairs native_reports')
    require(definitions['native_reports'] == [] and type(definitions['native_reports']) is list, 'fluorescence_native_report_import_unimplemented')
    sources, samples, domains, channels = ({}, {}, {}, {})
    for binding in job['inputs']:
        for name, index in (('source', sources), ('sample', samples)):
            row = binding[name]
            require(row['key'] not in index or same(index[row['key']], row), 'fluorescence_conflicting_input_alias')
            index[row['key']] = row
        domain = binding['domain']
        require(domain['key'] not in domains, 'fluorescence_duplicate_input_domain')
        domains[domain['key']] = domain
        for channel in binding['channels']:
            require(channel['key'] not in channels, 'fluorescence_duplicate_input_channel')
            channels[channel['key']] = {k: v for k, v in channel.items() if k != 'measurement_origin'}
            channels[channel['key']]['domain_key'] = domain['key']
    from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.native_fluorescence_prepared_contracts import add_preparation_declarations
    add_preparation_declarations(job, sources=sources, samples=samples, domains=domains, channels=channels)
    populations = core._collection(definitions['populations'], core._population, 'invalid_population')
    gates = core._collection(definitions['gates'], core._gate, 'invalid_gate')
    controls = core._collection(definitions['control_pairs'], core._control, 'invalid_control')
    for sample in samples.values():
        core._sample(sample, sources=sources)
        primary = domains.get(sample['primary_domain_key'])
        require(primary is not None and primary['sample_key'] == sample['key'] and (primary['parent_domain_key'] is None), 'fluorescence_primary_domain_missing')
    for channel in channels.values():
        core._channel(channel, sources=sources)
    for domain in domains.values():
        current, seen = (domain, set())
        while current['parent_domain_key'] is not None:
            require(current['key'] not in seen, 'fluorescence_domain_cycle')
            seen.add(current['key'])
            current = domains.get(current['parent_domain_key'])
            require(current is not None and current['sample_key'] == domain['sample_key'], 'fluorescence_domain_parent_mismatch')
        require(current['key'] == samples[domain['sample_key']]['primary_domain_key'], 'fluorescence_primary_domain_missing')
    for row in populations.values():
        require(row['sample_key'] in samples, 'fluorescence_population_sample_mismatch')
    for gate in gates.values():
        parent = (gates if gate['parent']['kind'] == 'gate' else populations).get(gate['parent']['key'])
        require(gate['sample_key'] in samples and parent is not None and (parent['sample_key'] == gate['sample_key']), 'fluorescence_gate_parent_mismatch')
        if gate['kind'] == 'threshold':
            domain, channel = (domains.get(gate['domain_key']), channels.get(gate['channel_key']))
            require(domain is not None and channel is not None and (domain['sample_key'] == gate['sample_key']) and (channel['domain_key'] == domain['key']), 'fluorescence_gate_domain_mismatch')
        current, seen = (gate, set())
        while current['parent']['kind'] == 'gate':
            require(current['key'] not in seen and current['parent']['key'] in gates, 'fluorescence_gate_cycle')
            seen.add(current['key'])
            current = gates[current['parent']['key']]
    for pair in controls.values():
        require(pair['target_gate_key'] in gates and pair['control_gate_key'] in gates, 'fluorescence_control_gate_mismatch')
    parameters = job['parameters']
    core._keys(parameters, 'fraction_requests intensity_requests control_requests native_comparison_requests', 'invalid_parameters')
    for rows in parameters.values():
        core._list(rows, 'invalid_parameters')
        core._unique([core.canonical(row) for row in rows], 'invalid_parameters')
    from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.native_fluorescence_prepared_contracts import validate_report_declarations
    report_keys = validate_report_declarations(job)
    for key in parameters['native_comparison_requests']:
        _key(key)
        require(key in report_keys, 'fluorescence_parameter_report_missing')
    for row in parameters['fraction_requests']:
        core._keys(row, 'gate_key denominator', 'invalid_parameters')
        core._key(row['gate_key'], 'invalid_parameters')
        core._enum(row['denominator'], {'parent', 'evaluable'}, 'invalid_parameters')
        require(row['gate_key'] in gates, 'fluorescence_parameter_gate_missing')
    for row in parameters['intensity_requests']:
        core._keys(row, 'gate_key domain_key channel_key', 'invalid_parameters')
        for key in ('gate_key', 'domain_key', 'channel_key'):
            core._key(row[key], 'invalid_parameters')
        gate, domain, channel = (gates.get(row['gate_key']), domains.get(row['domain_key']), channels.get(row['channel_key']))
        require(gate is not None and domain is not None and (channel is not None) and (gate['sample_key'] == domain['sample_key']) and (channel['domain_key'] == domain['key']), 'fluorescence_parameter_domain_mismatch')
    for row in parameters['control_requests']:
        core._keys(row, 'control_key include_legacy_clipping', 'invalid_parameters')
        core._key(row['control_key'], 'invalid_parameters')
        require(row['control_key'] in controls and type(row['include_legacy_clipping']) is bool, 'fluorescence_parameter_control_mismatch')
    core._unique([row['control_key'] for row in parameters['control_requests']], 'invalid_parameters')

def _required_support(job):
    files = []
    for row in job['inputs']:
        files.extend((a['file'] for a in row['sample']['associations']))
        files.extend((c['analyte']['file'] for c in row['channels'] if c['analyte'] is not None))
        domain = row['domain']
        files.extend((domain[k]['parameters_file'] for k in ('scaling', 'compensation', 'transformation') if k in domain and domain[k]['parameters_file'] is not None))
        if domain['comparison_basis'] is not None:
            files.append(domain['comparison_basis']['evidence_file'])
    files.extend((row['comparison_basis']['evidence_file'] for row in job['definitions']['control_pairs']))
    for request in job['preparations']:
        files.append(request['recipe_file'])
        output = request['output']
        files.extend((c['analyte']['file'] for c in output['channels'] if c['analyte'] is not None))
        if output['comparison_basis'] is not None:
            files.append(output['comparison_basis']['evidence_file'])
        if request['recipe']['method'] == PREPARATION_METHODS[1]:
            params = request['recipe']['parameters']
            files.extend((params['matrix_file'], params['input_domain_basis']['evidence_file']))
    files.extend((row['association_file'] for row in job['report_inputs'] if row['association_file'] is not None))
    events = {canonical(row['source']['file']) for row in job['inputs']}
    events.update((canonical(row['file']) for row in job['report_inputs']))
    return unique([file for file in files if canonical(file) not in events])

def validate_fluorescence_job(value):
    closed(value, JOB_SCHEMA['properties'])
    require(value['version'] == 'native_fluorescence_job' and value['operation'] in OPERATIONS and (value['mode'] == MODE), 'invalid_fluorescence_job')
    validate_fluorescence_software(value['software'])
    _list(value['inputs'])
    _list(value['support_inputs'])
    require(bool(value['inputs']), 'fluorescence_inputs_required')
    for row in value['inputs']:
        _input(row)
    _list(value['preparations'])
    _list(value['report_inputs'])
    _parser_software(value['software'], [r['parser'] for r in value['inputs']])
    _definitions(value)
    from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.native_fluorescence_prepared_contracts import validate_selected_software
    validate_selected_software(value['software'], methods=[r['recipe']['method'] for r in value['preparations']], profiles=[r['profile'] for r in value['report_inputs']])
    for row in value['support_inputs']:
        closed(row, 'file path')
        core._file(row['file'], 'invalid_source')
        path_value(row['path'], absolute=True)
    supplied = [canonical(r['file']) for r in value['support_inputs']]
    require(len(set(supplied)) == len(supplied) and set(supplied) == {canonical(r) for r in _required_support(value)}, 'fluorescence_support_input_mismatch')
    fcs_datasets = [(r['source']['file']['artifact_ref'], r['source']['dataset_position']) for r in value['inputs'] if r['parser'] == 'fcs_encoded']
    require(len(set(fcs_datasets)) == len(fcs_datasets), 'fluorescence_duplicate_fcs_dataset')
    prefix = path_value(value['output_prefix'], absolute=False)
    require(not prefix.parts[0].startswith('.') and prefix.parts[0] not in ('tmp', 'cache'), 'invalid_fluorescence_output_prefix')
    canonical(value)
    return deepcopy(value)

def fluorescence_environment(software, *, attempt_directory):
    software = validate_fluorescence_software(software)
    root = path_value(str(attempt_directory), absolute=True)
    return {'PYTHONPATH': os.pathsep.join([software['module_root'], *software['dependency_roots']]), 'PYTHONHOME': software['python_home'], 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1', 'TMPDIR': str(root / 'tmp'), 'TMP': str(root / 'tmp'), 'TEMP': str(root / 'tmp'), 'XDG_CACHE_HOME': str(root / 'cache'), 'PIP_CACHE_DIR': str(root / 'cache/pip')}

def requested_job_from_fluorescence(job, *, environment):
    job = validate_fluorescence_job(job)
    require(type(environment) is dict and all((type(k) is str and re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', k) and (type(v) is str) and ('\x00' not in v) for k, v in environment.items())), 'invalid_fluorescence_environment')
    path_value(environment.get('TMPDIR'), absolute=True)
    expected = fluorescence_environment(job['software'], attempt_directory=str(PurePosixPath(environment['TMPDIR']).parent))
    require(same(environment, expected), 'invalid_fluorescence_environment')
    return {'argv': [job['software']['python']['path'], '-B', '-S', '-m', DRIVER_MODULE, RUN_PLAN_FILENAME], 'environment': deepcopy(environment), 'native_fluorescence': job}

def validate_fluorescence_requested_job(value):
    closed(value, 'argv environment native_fluorescence')
    expected = requested_job_from_fluorescence(value['native_fluorescence'], environment=value['environment'])
    require(same(value, expected), 'fluorescence_requested_job_mismatch')
    return deepcopy(value)

def fluorescence_output_files(job):
    job = validate_fluorescence_job(job)
    prefix = job['output_prefix']
    outputs = [*({'role': f'event_input:{i}', 'relative_path': f'{prefix}/inputs/{i}.bin', 'format': r['source']['file']['format']} for i, r in enumerate(job['inputs'])), *({'role': f'support_input:{i}', 'relative_path': f'{prefix}/support/{i}.bin', 'format': r['file']['format']} for i, r in enumerate(job['support_inputs'])), *({'role': f'event_batch:{i}', 'relative_path': f'{prefix}/parsed/{i}.json', 'format': 'fluorescence_parsed_batch'} for i in range(len(job['inputs'])))]
    outputs.extend(({'role': f'report_input:{i}', 'relative_path': f'{prefix}/reports/{i}.bin', 'format': r['file']['format']} for i, r in enumerate(job['report_inputs'])))
    for i in range(len(job['preparations'])):
        outputs.extend(({'role': f'{role}:{i}', 'relative_path': f'{prefix}/prepared/{i}/{name}', 'format': format_} for role, name, format_ in (('preparation_parameters', 'parameters.json', 'fluorescence_resolved_preparation'), ('prepared_data', 'events.json', 'fluorescence_prepared_event_data'), ('prepared_batch', 'batch.json', 'fluorescence_prepared_batch'))))
    outputs.extend(({'role': f'report_batch:{i}', 'relative_path': f'{prefix}/reports/{i}.json', 'format': 'fluorescence_report_batch'} for i in range(len(job['report_inputs']))))
    return [*outputs, {'role': 'manifest', 'relative_path': f'{prefix}/native-manifest.json', 'format': 'fluorescence_native_manifest'}]

def validate_fluorescence_run_plan(value):
    closed(value, 'version identity requested_job attempt_directory policy outputs')
    require(value['version'] == 'fluorescence_run_plan', 'invalid_fluorescence_run_plan')
    request = validate_fluorescence_requested_job(value['requested_job'])
    owner = value['identity']
    closed(owner, 'run_id episode_id resource_id execution_id attempt_id operation_key requested_job_sha256 assignment_sha256')
    for item in owner.values():
        _key(item)
    for name in ('attempt_id', 'requested_job_sha256', 'assignment_sha256'):
        _sha(owner[name])
    execution = path_value(owner['execution_id'], absolute=True)
    attempt = path_value(value['attempt_directory'], absolute=True)
    from gene_annotation_episode.episodic_workflow.episode_support.findings.evolutionary_history_evidence.terminal_scientific_evidence import terminal_plan_identity
    require(terminal_plan_identity(owner, attempt_directory=str(attempt)) and owner['attempt_id'] == digest(owner['operation_key']) and (owner['requested_job_sha256'] == digest(request)), 'fluorescence_original_attempt_mismatch')
    require(retained_policy_matches(value['policy']), 'fluorescence_original_allocation_mismatch')
    require(same(value['outputs'], fluorescence_output_files(request['native_fluorescence'])), 'fluorescence_output_role_mismatch')
    job = request['native_fluorescence']
    for row in [*job['inputs'], *job['support_inputs'], *job.get('report_inputs', [])]:
        supplied = path_value(row['path'], absolute=True)
        require(not supplied.is_relative_to(execution.parent) and (not execution.parent.is_relative_to(supplied)), 'fluorescence_input_output_overlap')
    return deepcopy(value)

def fluorescence_driver_argv(plan):
    plan = validate_fluorescence_run_plan(plan)
    return [*plan['requested_job']['argv'][:-1], str(PurePosixPath(plan['identity']['execution_id']).parent / RUN_PLAN_FILENAME)]

def _failures(rows, job):
    _list(rows)
    for row in rows:
        validate_failure(row)
        if row['input_index'] is not None:
            prefix = (row['role'] or '').split(':')[0]
            collection = job['support_inputs'] if prefix == 'support_input' else job.get('report_inputs', []) if prefix in ('report_input', 'report_batch') else job.get('preparations', []) if prefix in ('preparation_parameters', 'prepared_data', 'prepared_batch') else job['inputs']
            require(row['input_index'] < len(collection), 'invalid_fluorescence_failure_index')
    require(len(unique(rows)) == len(rows), 'duplicate_fluorescence_failure')

def validate_fluorescence_native_capture(value, *, original_plan):
    plan = validate_fluorescence_run_plan(original_plan)
    closed(value, 'version original_plan_sha256 files source_action_receipt_ref writer_closure_receipt_ref driver_started failures')
    require(value['version'] == 'fluorescence_native_capture' and value['original_plan_sha256'] == digest(plan), 'fluorescence_native_capture_mismatch')
    require(value['driver_started'] is None or type(value['driver_started']) is bool, 'fluorescence_native_capture_mismatch')
    for name in ('source_action_receipt_ref', 'writer_closure_receipt_ref'):
        require(type(value[name]) is str and re.fullmatch('artifact_[0-9a-f]{64}', value[name]) is not None, 'fluorescence_native_capture_authority_required')
    _list(value['files'])
    require(len(value['files']) == len(plan['outputs']), 'fluorescence_output_role_mismatch')
    for row, output in zip(value['files'], plan['outputs']):
        closed(row, 'role relative_path format retained')
        require(same({k: row[k] for k in ('role', 'relative_path', 'format')}, output), 'fluorescence_output_role_mismatch')
        if row['retained'] is not None:
            retained = row['retained']
            closed(retained, 'file path')
            core._file(retained['file'], 'invalid_source')
            require(retained['file']['format'] == row['format'], 'fluorescence_native_capture_format_mismatch')
            path = path_value(retained['path'], absolute=True)
            sha = retained['file']['sha256']
            require(path.name == sha and path.parent.name == sha[:2] and (path.parent.parent.name == 'artifacts'), 'fluorescence_retained_path_mismatch')
    _failures(value['failures'], plan['requested_job']['native_fluorescence'])
    return deepcopy(value)
ENV_SCHEMA = {'type': 'object', 'propertyNames': {'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'}, 'additionalProperties': {'type': 'string', 'pattern': '^[^\\u0000]*$'}}
NATIVE_FLUORESCENCE_REQUESTED_JOB_SCHEMA = obj({'argv': array(TEXT, minItems=1), 'environment': ENV_SCHEMA, 'native_fluorescence': {'anyOf': [JOB_SCHEMA]}})
OWNER_FILENAME = '.native-fluorescence-owner.json'
STARTED_FILENAME = '.native-fluorescence-started.json'
