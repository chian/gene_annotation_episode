"""Pure selected-preparation/report declarations and immutable envelopes.

No decoder, preparation implementation, report parser or calculator is imported
here. The result worker checks retained parameters and data against its actual
parent parse; these ports check only the supplied envelope relationships.
"""
from pathlib import PurePosixPath
import re
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.fluorescence_execution_common import require, same

def _identity(domain):
    return {key: domain[key] for key in ('key', 'source_key', 'sample_key')}

def validate_selected_software(software, *, methods, profiles):
    """Require only the extra closure imported by this selected v2 path."""
    required = {'native_fluorescence_prepared_contracts.py'}
    if methods or profiles:
        required.add('native_fluorescence_prepared_driver.py')
    if methods:
        required.update(('fluorescence_preparation_contracts.py', 'fluorescence_preparation_readers.py', 'fluorescence_event_preparation.py', 'fluorescence_fcs_reader.py'))
    if profiles:
        required.update(('fluorescence_native_report_contracts.py', 'fluorescence_native_reports.py'))
    implementation = {row['path'] for row in software['implementation_files']}
    root = PurePosixPath(software['module_root']) / 'gene_annotation_episode'
    require({str(root / name) for name in required} <= implementation, 'fluorescence_selected_implementation_closure_missing')
    if not methods:
        return
    from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.native_fluorescence_contracts import _parser_software
    _parser_software(software, ['fcs_encoded'])
    distributions = {re.sub('[-_.]+', '-', row['name']).lower(): row for row in software['distributions']}
    paths = [PurePosixPath(row['path']) for row in software['runtime_files']]
    packages = [('numpy', None)]
    if 'spill_compensate_flowutils_1_2_2' in methods:
        packages.append(('flowutils', '1.2.2'))
    for name, version in packages:
        distribution = distributions.get(name)
        require(distribution is not None and (version is None or distribution['version'] == version), 'fluorescence_installed_' + name + '_required')
        version = distribution['version']
        require(any((path.name == '__init__.py' and path.parent.name == name for path in paths)) and any((path.name == 'METADATA' and re.fullmatch(re.escape(name + '-' + version) + '\\.dist-info', path.parent.name, re.IGNORECASE) for path in paths)), 'fluorescence_installed_' + name + '_required')

def add_preparation_declarations(job, *, sources, samples, domains, channels):
    """Extend a declaration graph, never manufacture a prepared Domain."""
    if not job['preparations']:
        return
    from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.fluorescence_preparation_contracts import SCALE_METHOD, validate_preparation_request
    originals = [_identity(row['domain']) for row in job['inputs']]
    previous, by_domain = ([], {})
    for binding in job['inputs']:
        require(binding['domain']['parent_domain_key'] is None or binding['domain']['parent_domain_key'] in domains, 'fluorescence_domain_parent_mismatch')
        by_domain[binding['domain']['key']] = binding['channels']
    occupied = set(sources) | set(samples) | set(domains) | set(channels)
    for request in job['preparations']:
        require(type(request) is dict and type(request.get('input')) is dict, 'invalid_fluorescence_preparation')
        selected = originals if request['input'].get('kind') == 'event_input' else previous
        validate_preparation_request(request, input_domains=selected)
        parent = selected[request['input']['index']]
        output = request['output']
        new_keys = [output['key'], output['source_key'], *[row['key'] for row in output['channels']]]
        require(len(new_keys) == len(set(new_keys)) and (not occupied.intersection(new_keys)), 'fluorescence_preparation_key_collision')
        require(request['key'] not in occupied and (request['key'] == output['key'] or request['key'] not in new_keys), 'fluorescence_preparation_key_collision')
        occupied.update(new_keys)
        occupied.add(request['key'])
        require(output['sample_key'] in samples, 'fluorescence_preparation_sample_mismatch')
        previous_channels = by_domain[parent['key']]
        require(len(previous_channels) == len(output['channels']), 'fluorescence_preparation_channel_mismatch')
        for old, new in zip(previous_channels, output['channels']):
            require(all((same(old[key], new[key]) for key in ('ordinal', 'native_name', 'label', 'analyte'))), 'fluorescence_preparation_channel_mismatch')
            prospective_time = request['recipe']['method'] == SCALE_METHOD and old['native_name'] is not None and (old['native_name'].lower() == 'time')
            require(prospective_time or same(old['unit'], new['unit']), 'fluorescence_preparation_unit_mismatch')
            channels[new['key']] = dict(new, domain_key=output['key'])
        previous.append(_identity(output))
        domains[output['key']] = dict(_identity(output), parent_domain_key=parent['key'])
        sources[output['source_key']] = None
        by_domain[output['key']] = output['channels']

def validate_report_declarations(job):
    if not job['report_inputs']:
        return set()
    from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.fluorescence_native_report_contracts import validate_report_input
    occupied = set()
    for row in job['inputs']:
        occupied.update((row['source']['key'], row['sample']['key'], row['domain']['key']))
        occupied.update((channel['key'] for channel in row['channels']))
    for row in job['preparations']:
        occupied.update((row['key'], row['output']['source_key'], row['output']['key']))
        occupied.update((channel['key'] for channel in row['output']['channels']))
    report_keys = set()
    for row in job['report_inputs']:
        validate_report_input(row, definitions=job['definitions'], event_inputs=job['inputs'], preparations=job['preparations'])
        keys = [row['source_key'], *[field['key'] for field in row['fields']]]
        require(not occupied.intersection(keys), 'fluorescence_report_key_collision')
        occupied.update(keys)
        report_keys.update((field['key'] for field in row['fields']))
    return report_keys
