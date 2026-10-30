"""Pure selected-preparation/report declarations and immutable envelopes.

No decoder, preparation implementation, report parser or calculator is imported
here. The result worker checks retained parameters and data against its actual
parent parse; these ports check only the supplied envelope relationships.
"""
from copy import deepcopy
from pathlib import PurePosixPath
import re

from . import fluorescence_event_contracts as core
from .fluorescence_execution_common import closed, digest, require, same


def _identity(domain):
    return {key: domain[key] for key in ('key', 'source_key', 'sample_key')}


def validate_selected_software(software, *, methods, profiles):
    """Require only the extra closure imported by this selected v2 path."""
    required = {'native_fluorescence_prepared_contracts.py'}
    if methods or profiles:
        required.add('native_fluorescence_prepared_driver.py')
    if methods:
        required.update(('fluorescence_preparation_contracts.py', 'fluorescence_preparation_readers.py',
            'fluorescence_event_preparation.py', 'fluorescence_fcs_reader.py'))
    if profiles:
        required.update(('fluorescence_native_report_contracts.py', 'fluorescence_native_reports.py'))
    implementation = {row['path'] for row in software['implementation_files']}
    root = PurePosixPath(software['module_root']) / 'gene_annotation_episode'
    require({str(root / name) for name in required} <= implementation,
        'fluorescence_selected_implementation_closure_missing')
    if not methods:
        return
    from .native_fluorescence_contracts import _parser_software
    _parser_software(software, ['fcs_encoded'])
    distributions = {re.sub(r'[-_.]+', '-', row['name']).lower(): row for row in software['distributions']}
    paths = [PurePosixPath(row['path']) for row in software['runtime_files']]
    packages = [('numpy', None)]
    if 'spill_compensate_flowutils_1_2_2' in methods:
        packages.append(('flowutils', '1.2.2'))
    for name, version in packages:
        distribution = distributions.get(name)
        require(distribution is not None and (version is None or distribution['version'] == version),
            'fluorescence_installed_' + name + '_required')
        version = distribution['version']
        require(any(path.name == '__init__.py' and path.parent.name == name for path in paths)
            and any(path.name == 'METADATA' and re.fullmatch(re.escape(name + '-' + version) + r'\.dist-info',
                path.parent.name, re.IGNORECASE) for path in paths),
            'fluorescence_installed_' + name + '_required')


def add_preparation_declarations(job, *, sources, samples, domains, channels):
    """Extend a declaration graph, never manufacture a prepared Domain."""
    if not job['preparations']:
        return
    from .fluorescence_preparation_contracts import SCALE_METHOD, validate_preparation_request
    originals = [_identity(row['domain']) for row in job['inputs']]
    previous, by_domain = [], {}
    for binding in job['inputs']:
        require(binding['domain']['parent_domain_key'] is None
            or binding['domain']['parent_domain_key'] in domains, 'fluorescence_domain_parent_mismatch')
        by_domain[binding['domain']['key']] = binding['channels']
    occupied = set(sources) | set(samples) | set(domains) | set(channels)
    for request in job['preparations']:
        require(type(request) is dict and type(request.get('input')) is dict, 'invalid_fluorescence_preparation')
        selected = originals if request['input'].get('kind') == 'event_input' else previous
        validate_preparation_request(request, input_domains=selected)
        parent = selected[request['input']['index']]
        output = request['output']
        new_keys = [output['key'], output['source_key'], *[row['key'] for row in output['channels']]]
        require(len(new_keys) == len(set(new_keys)) and not occupied.intersection(new_keys),
            'fluorescence_preparation_key_collision')
        require(request['key'] not in occupied and (request['key'] == output['key'] or request['key'] not in new_keys),
            'fluorescence_preparation_key_collision')
        occupied.update(new_keys)
        occupied.add(request['key'])
        require(output['sample_key'] in samples, 'fluorescence_preparation_sample_mismatch')
        previous_channels = by_domain[parent['key']]
        require(len(previous_channels) == len(output['channels']), 'fluorescence_preparation_channel_mismatch')
        for old, new in zip(previous_channels, output['channels']):
            require(all(same(old[key], new[key]) for key in ('ordinal', 'native_name', 'label', 'analyte')),
                'fluorescence_preparation_channel_mismatch')
            prospective_time = (request['recipe']['method'] == SCALE_METHOD
                and old['native_name'] is not None and old['native_name'].lower() == 'time')
            require(prospective_time or same(old['unit'], new['unit']), 'fluorescence_preparation_unit_mismatch')
            channels[new['key']] = dict(new, domain_key=output['key'])
        previous.append(_identity(output))
        # This identity graph is deliberately not a validated/executed Domain.
        domains[output['key']] = dict(_identity(output), parent_domain_key=parent['key'])
        sources[output['source_key']] = None
        by_domain[output['key']] = output['channels']


def validate_report_declarations(job):
    if not job['report_inputs']:
        return set()
    from .fluorescence_native_report_contracts import validate_report_input
    occupied = set()
    for row in job['inputs']:
        occupied.update((row['source']['key'], row['sample']['key'], row['domain']['key']))
        occupied.update(channel['key'] for channel in row['channels'])
    for row in job['preparations']:
        occupied.update((row['key'], row['output']['source_key'], row['output']['key']))
        occupied.update(channel['key'] for channel in row['output']['channels'])
    report_keys = set()
    for row in job['report_inputs']:
        validate_report_input(row, definitions=job['definitions'], event_inputs=job['inputs'],
            preparations=job['preparations'])
        keys = [row['source_key'], *[field['key'] for field in row['fields']]]
        require(not occupied.intersection(keys), 'fluorescence_report_key_collision')
        occupied.update(keys)
        report_keys.update(field['key'] for field in row['fields'])
    return report_keys


def _selected_plan(original_plan, index, collection):
    from .native_fluorescence_contracts import validate_fluorescence_run_plan
    plan = validate_fluorescence_run_plan(original_plan)
    job = plan['requested_job']['native_fluorescence']
    require(job['version'] == 'native_fluorescence_job_v2' and type(index) is int
        and 0 <= index < len(job[collection]), 'invalid_fluorescence_' + collection + '_index')
    return plan, job, job[collection][index]


def _file(value, format_):
    core._file(value, 'invalid_source')
    require(value['format'] == format_, 'fluorescence_prepared_file_format_mismatch')


def _parent_declaration(job, request):
    selected = request['input']
    if selected['kind'] == 'event_input':
        return job['inputs'][selected['index']]['domain']
    return job['preparations'][selected['index']]['output']


def validate_prepared_batch(value, *, original_plan, preparation_index, parent_batch_file):
    from .fluorescence_preparation_contracts import SCALE_METHOD, STATUSES, preparation_problem
    plan, job, request = _selected_plan(original_plan, preparation_index, 'preparations')
    closed(value, 'version original_plan_sha256 preparation_index preparation_request_sha256 software_sha256 '
        'parent_batch_file recipe_file parameters_file prepared_file parse status problems')
    require(value['version'] == 'fluorescence_prepared_batch_v1' and value['original_plan_sha256'] == digest(plan)
        and type(value['preparation_index']) is int and value['preparation_index'] == preparation_index
        and value['preparation_request_sha256'] == core.digest(request)
        and value['software_sha256'] == digest(job['software']), 'fluorescence_prepared_batch_binding_mismatch')
    _file(parent_batch_file, 'fluorescence_parsed_batch_v1' if request['input']['kind'] == 'event_input'
        else 'fluorescence_prepared_batch_v1')
    require(same(value['parent_batch_file'], parent_batch_file) and same(value['recipe_file'], request['recipe_file']),
        'fluorescence_prepared_batch_binding_mismatch')
    _file(value['parameters_file'], 'fluorescence_resolved_preparation_v1')
    if value['prepared_file'] is not None:
        _file(value['prepared_file'], 'fluorescence_prepared_event_data_v1')
    require(type(value['status']) is str and value['status'] in STATUSES and type(value['problems']) is list,
        'fluorescence_prepared_batch_status_mismatch')
    for row in value['problems']:
        closed(row, 'code domain_key channel_key event_ordinal')
        preparation_problem(**row)
        require(row['domain_key'] == request['output']['key'] and (row['channel_key'] is None or
            row['channel_key'] in {channel['key'] for channel in request['output']['channels']}),
            'fluorescence_prepared_batch_problem_mismatch')
    require(len({core.canonical(row) for row in value['problems']}) == len(value['problems']),
        'fluorescence_prepared_batch_problem_mismatch')
    parsed = core.validate_event_parse_result(value['parse'])
    source, domain, output = parsed['source'], parsed['domain'], request['output']
    parent = _parent_declaration(job, request)
    samples = {row['sample']['key']: row['sample'] for row in job['inputs']}
    require(same(parsed['sample'], samples[output['sample_key']])
        and source['key'] == output['source_key'] and same(source['file'], value['prepared_file'])
        and source['dataset_position'] == 0 and source['format_profile'] == 'fluorescence_prepared_event_data_v1'
        and source['native_event_count'] is None and source['metadata'] == []
        and domain['key'] == output['key'] and domain['source_key'] == output['source_key']
        and domain['sample_key'] == output['sample_key'] and domain['parent_domain_key'] == parent['key']
        and same(domain['comparison_basis'], output['comparison_basis'])
        and same(parsed['channels'], [dict(channel, domain_key=output['key']) for channel in output['channels']]),
        'fluorescence_prepared_batch_parse_mismatch')
    present = value['prepared_file'] is not None
    require(present == (value['status'] in ('complete', 'partial')), 'fluorescence_prepared_batch_status_mismatch')
    field = 'scaling' if request['recipe']['method'] == SCALE_METHOD else 'compensation'
    require(same(domain.get(field), {'state': 'applied' if present else 'failed',
        'method': request['recipe']['method'], 'parameters_file': value['parameters_file']}),
        'fluorescence_prepared_batch_parameters_mismatch')
    if present:
        require(domain['state'] == 'available' and source['extent'] in ('complete', 'partial'),
            'fluorescence_prepared_batch_status_mismatch')
        if field == 'scaling':
            require(domain['scale_kind'] == 'scaled', 'fluorescence_prepared_batch_parse_mismatch')
        if value['status'] == 'complete':
            require(source['extent'] == 'complete' and not value['problems'], 'fluorescence_prepared_batch_status_mismatch')
    else:
        require(domain['state'] == ('failed' if value['status'] == 'failed' else 'unavailable')
            and source['extent'] == 'unavailable' and not parsed['events'] and domain['correspondence'] == []
            and bool(value['problems']), 'fluorescence_prepared_batch_status_mismatch')
    return deepcopy(value)


def validate_report_batch(value, *, original_plan, report_index):
    from .fluorescence_native_report_contracts import make_fluorescence_report_binding, validate_report_parse_result
    plan, job, request = _selected_plan(original_plan, report_index, 'report_inputs')
    closed(value, 'version original_plan_sha256 report_index report_input_sha256 software_sha256 report_file association_file parse')
    require(value['version'] == 'fluorescence_report_batch_v1' and value['original_plan_sha256'] == digest(plan)
        and type(value['report_index']) is int and value['report_index'] == report_index
        and value['report_input_sha256'] == digest(request) and value['software_sha256'] == digest(job['software'])
        and same(value['report_file'], request['file']), 'fluorescence_report_batch_binding_mismatch')
    if value['association_file'] is not None:
        core._file(value['association_file'], 'invalid_source')
        require(same(value['association_file'], request['association_file']), 'fluorescence_report_batch_binding_mismatch')
    binding = make_fluorescence_report_binding(request, definitions=job['definitions'], event_inputs=job['inputs'],
        preparations=job['preparations'])
    validate_report_parse_result(value['parse'], binding=binding)
    if value['association_file'] is None and any(row['component_request'] is not None for row in request['fields']):
        require(core.issue('native_population_unknown', 'input', source_key=request['source_key']) in value['parse']['issues'],
            'fluorescence_report_batch_association_mismatch')
    return deepcopy(value)


def _declared_file(file, declaration):
    if file is None:
        require(declaration['state'] == 'absent', 'fluorescence_manifest_batch_mismatch')
    else:
        core._file(file, 'invalid_source')
        require(declaration['state'] == 'present' and all(same(file[key], declaration[key])
            for key in ('sha256', 'size_bytes', 'format')), 'fluorescence_manifest_batch_mismatch')


def validate_prepared_manifest_rows(value, *, job, declarations):
    if job['preparations']:
        from .fluorescence_preparation_contracts import STATUSES
    require(type(value['preparations']) is list and len(value['preparations']) == len(job['preparations'])
        and type(value['reports']) is list and len(value['reports']) == len(job['report_inputs']),
        'fluorescence_manifest_prepared_mismatch')
    for index, (row, request) in enumerate(zip(value['preparations'], job['preparations'])):
        closed(row, 'preparation_index parent_batch_file parameters_file prepared_file batch_file status')
        require(type(row['preparation_index']) is int and row['preparation_index'] == index
            and type(row['status']) is str and row['status'] in STATUSES, 'fluorescence_manifest_prepared_mismatch')
        selected = request['input']
        parents = value['inputs'] if selected['kind'] == 'event_input' else value['preparations']
        parent = parents[selected['index']]['batch_file']
        require(row['parent_batch_file'] is None or same(row['parent_batch_file'], parent),
            'fluorescence_manifest_prepared_parent_mismatch')
        for name, role in (('parameters_file', 'preparation_parameters'), ('prepared_file', 'prepared_data'),
                ('batch_file', 'prepared_batch')):
            _declared_file(row[name], declarations[f'{role}:{index}'])
        if row['batch_file'] is None:
            require(row['parameters_file'] is None and row['prepared_file'] is None
                and row['status'] in ('unavailable', 'incompatible', 'failed'), 'fluorescence_manifest_prepared_mismatch')
        else:
            require(parent is not None and same(row['parent_batch_file'], parent) and row['parameters_file'] is not None
                and (row['prepared_file'] is not None) == (row['status'] in ('complete', 'partial')),
                'fluorescence_manifest_prepared_mismatch')
    for index, (row, request) in enumerate(zip(value['reports'], job['report_inputs'])):
        closed(row, 'report_index source_file batch_file extent')
        require(type(row['report_index']) is int and row['report_index'] == index
            and row['extent'] in ('complete', 'partial', 'unavailable'), 'fluorescence_manifest_report_mismatch')
        _declared_file(row['source_file'], declarations[f'report_input:{index}'])
        _declared_file(row['batch_file'], declarations[f'report_batch:{index}'])
        require(row['source_file'] is None or same(row['source_file'], request['file']),
            'fluorescence_manifest_report_mismatch')
        require((row['batch_file'] is not None and row['source_file'] is not None)
            or row['batch_file'] is None and row['extent'] == 'unavailable', 'fluorescence_manifest_report_mismatch')
