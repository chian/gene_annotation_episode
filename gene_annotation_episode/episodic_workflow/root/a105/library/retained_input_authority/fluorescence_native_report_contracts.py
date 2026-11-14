"""Closed data ports for three source-defined fluorescence report formats.

These declarations never authenticate a historical execution or calculate a
scientific component. Association support refers to exact selected identities;
display labels are not join keys.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority import fluorescence_event_contracts as core
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.native_fluorescence_contracts import _input, path_value
FACS_PROFILE = 'biomni_facs_log_548_v1'
CYTOKINE_LOG_PROFILE = 'biomni_cytokine_log_548_v1'
CYTOKINE_CSV_PROFILE = 'biomni_cytokine_csv_548_v1'
PROFILE_SOURCES = {FACS_PROFILE: dict(operation='perform_facs_cell_sorting', source_file_sha256='45f8edb43c079cab4727211ae6cecbf603577b4d886cd05295fabdd561a763af', function_sha256='c400891a22aa723c1fb8d42cce9f2c7b9a8241f9a8c16467780c7c2b6e138fb7'), CYTOKINE_LOG_PROFILE: dict(operation='analyze_cytokine_production_in_cd4_tcells', source_file_sha256='ef97b6bfdd52a935078e0ea4cdd8641edb2d4c1ff7f77f206b551a293fb6bdb4', function_sha256='9d4f5b14cdd5337b4b807dfbe04790a164501ad6bad6fb270bdb6937c0a7a6ba')}
PROFILE_SOURCES[CYTOKINE_CSV_PROFILE] = deepcopy(PROFILE_SOURCES[CYTOKINE_LOG_PROFILE])
CSV_COLUMNS = {'IFN-γ', 'IL-17', 'IFN-γ (background-subtracted)', 'IL-17 (background-subtracted)'}
_CODE = 'invalid_native_report'

def _need(condition):
    core._need(condition, _CODE)

def _keys(value, names):
    core._keys(value, names, _CODE)

def _unique(values):
    core._unique(values, _CODE)

def _domain_identity(domain):
    return {name: domain[name] for name in ('key', 'source_key', 'sample_key')}

def _context(*, definitions, event_inputs, preparations):
    """Validate selected relationships without inventing an event universe."""
    _keys(definitions, 'populations gates control_pairs native_reports')
    _need(type(definitions['native_reports']) is list and (not definitions['native_reports']))
    core._list(event_inputs, _CODE)
    core._list(preparations, _CODE)
    sources, samples, domains, channels, by_domain = ({}, {}, {}, {}, {})
    originals, declared = ([], [])
    for item in event_inputs:
        _input(item)
        for name, index in (('source', sources), ('sample', samples)):
            row = item[name]
            _need(row['key'] not in index or core.canonical(index[row['key']]) == core.canonical(row))
            index[row['key']] = row
        domain = item['domain']
        _need(domain['key'] not in domains)
        domains[domain['key']] = domain
        originals.append(_domain_identity(domain))
        by_domain[domain['key']] = []
        for original in item['channels']:
            channel = {k: v for k, v in original.items() if k != 'measurement_origin'}
            channel['domain_key'] = domain['key']
            _need(channel['key'] not in channels)
            channels[channel['key']] = channel
            by_domain[domain['key']].append(channel)
    if preparations:
        from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.fluorescence_preparation_contracts import SCALE_METHOD, validate_preparation_request
    preparation_keys = []
    for item in preparations:
        _need(type(item) is dict and type(item.get('input')) is dict)
        selected = originals if item['input'].get('kind') == 'event_input' else declared
        validate_preparation_request(item, input_domains=selected)
        preparation_keys.append(item['key'])
        parent = selected[item['input']['index']]
        output = item['output']
        _need(output['key'] not in domains and output['source_key'] not in sources)
        _need(output['sample_key'] in samples)
        previous = by_domain[parent['key']]
        _need(len(output['channels']) == len(previous))
        for old, new in zip(previous, output['channels']):
            _need(all((new[k] == old[k] for k in ('ordinal', 'native_name', 'label', 'analyte'))))
            prospective_time = item['recipe']['method'] == SCALE_METHOD and old['native_name'] is not None and (old['native_name'].lower() == 'time')
            if not prospective_time:
                _need(new['unit'] == old['unit'])
        declared.append(_domain_identity(output))
        domains[output['key']] = dict(_domain_identity(output), parent_domain_key=parent['key'])
        sources[output['source_key']] = None
        by_domain[output['key']] = []
        for original in output['channels']:
            channel = dict(original, domain_key=output['key'])
            _need(channel['key'] not in channels)
            channels[channel['key']] = channel
            by_domain[output['key']].append(channel)
    _unique(preparation_keys)
    populations = core._collection(definitions['populations'], core._population, 'invalid_population')
    gates = core._collection(definitions['gates'], core._gate, 'invalid_gate')
    controls = core._collection(definitions['control_pairs'], core._control, 'invalid_control')
    for sample in samples.values():
        core._sample(sample, sources=sources)
        primary = domains.get(sample['primary_domain_key'])
        _need(primary is not None and primary['sample_key'] == sample['key'] and (primary['parent_domain_key'] is None))
    for channel in channels.values():
        core._channel(channel, sources=sources)
    for domain in domains.values():
        current, seen = (domain, set())
        while current['parent_domain_key'] is not None:
            _need(current['key'] not in seen)
            seen.add(current['key'])
            current = domains.get(current['parent_domain_key'])
            _need(current is not None and current['sample_key'] == domain['sample_key'])
        _need(current['key'] == samples[domain['sample_key']]['primary_domain_key'])
    for population in populations.values():
        _need(population['sample_key'] in samples)
    for gate in gates.values():
        parents = gates if gate['parent']['kind'] == 'gate' else populations
        parent = parents.get(gate['parent']['key'])
        _need(gate['sample_key'] in samples and parent is not None and (parent['sample_key'] == gate['sample_key']))
        if gate['kind'] == 'threshold':
            domain, channel = (domains.get(gate['domain_key']), channels.get(gate['channel_key']))
            _need(domain is not None and channel is not None and (domain['sample_key'] == gate['sample_key']) and (channel['domain_key'] == domain['key']))
        current, seen = (gate, set())
        while current['parent']['kind'] == 'gate':
            _need(current['key'] not in seen and current['parent']['key'] in gates)
            seen.add(current['key'])
            current = gates[current['parent']['key']]
    for control in controls.values():
        _need(control['target_gate_key'] in gates and control['control_gate_key'] in gates)
    return dict(source_key=sources, sample_key=samples, domain_key=domains, channel_key=channels, population_key=populations, gate_key=gates, control_key=controls, native_report_key={}, by_domain=by_domain)

def _locator(value, profile):
    if profile == FACS_PROFILE:
        _keys(value, 'kind metric occurrence')
        _need(value['kind'] == 'facs_metric')
        core._enum(value['metric'], {'original_count', 'selected_count', 'selected_percent', 'selected_mean', 'selected_median', 'lower_remaining_count', 'upper_remaining_count'}, _CODE)
        core._integer(value['occurrence'], _CODE)
    elif profile == CYTOKINE_LOG_PROFILE:
        _keys(value, 'kind condition_ordinal metric marker_occurrence')
        _need(value['kind'] == 'cytokine_log_metric')
        core._integer(value['condition_ordinal'], _CODE)
        core._enum(value['metric'], {'parent_count', 'original_count', 'marker_percent'}, _CODE)
        if value['metric'] == 'marker_percent':
            core._integer(value['marker_occurrence'], _CODE)
        else:
            _need(value['marker_occurrence'] is None)
    else:
        _keys(value, 'kind row_ordinal column_ordinal condition_label column_label')
        _need(value['kind'] == 'cytokine_csv_cell')
        core._integer(value['row_ordinal'], _CODE)
        core._integer(value['column_ordinal'], _CODE, minimum=1)
        core._text(value['condition_label'], _CODE, nullable=False)
        core._enum(value['column_label'], CSV_COLUMNS, _CODE)

def _metric_link(field, profile):
    request, locator = (field['component_request'], field['locator'])
    if request is None:
        return
    if profile == FACS_PROFILE:
        kind, metrics = {'original_count': ('population', {'parent_event_count'}), 'selected_count': ('population', {'selected_event_count'}), 'selected_percent': ('fraction', {'selected_percent'}), 'selected_mean': ('intensity', {'selected_intensity_mean'}), 'selected_median': ('intensity', {'selected_intensity_median'}), 'lower_remaining_count': ('population', {'selected_event_count'}), 'upper_remaining_count': ('population', {'selected_event_count'})}[locator['metric']]
    elif profile == CYTOKINE_LOG_PROFILE and locator['metric'] != 'marker_percent':
        kind = 'population'
        metrics = {'parent_event_count', 'selected_event_count'}
    elif profile == CYTOKINE_CSV_PROFILE and locator['column_label'].endswith(' (background-subtracted)'):
        kind, metrics = ('control', {'legacy_nonnegative_difference_percentage_points'})
    else:
        kind, metrics = ('fraction', {'selected_percent'})
    _need(request['kind'] == kind and request['metric'] in metrics)
    if kind == 'fraction':
        _need(request['denominator'] == 'parent')

def validate_report_input(value: dict, *, definitions: dict, event_inputs: list[dict], preparations: list[dict]) -> dict:
    """Validate selection only. Association bytes are separate fallible data."""
    context = _context(definitions=definitions, event_inputs=event_inputs, preparations=preparations)
    _keys(value, 'file path source_key profile fields association_file')
    core._file(value['file'], _CODE)
    path_value(value['path'], absolute=True)
    core._key(value['source_key'], _CODE)
    core._enum(value['profile'], PROFILE_SOURCES, _CODE)
    if value['association_file'] is not None:
        core._file(value['association_file'], _CODE)
    core._list(value['fields'], _CODE)
    for field in value['fields']:
        _keys(field, 'key locator component_request')
        core._key(field['key'], _CODE)
        _locator(field['locator'], value['profile'])
        if field['component_request'] is not None:
            core._cell_request(field['component_request'], _CODE, indexes=context)
            _metric_link(field, value['profile'])
    keys = [value['source_key'], *(field['key'] for field in value['fields'])]
    _unique(keys)
    _need(not set(keys).intersection(context['source_key']))
    _unique([core.canonical(field['locator']) for field in value['fields']])
    return deepcopy(value)
