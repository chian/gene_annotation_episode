"""One-time, reviewable finite contract expansion from sealed207 descriptions."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import pprint

HERE = Path(__file__).resolve().parent
PACKAGE = HERE / 'candidate/gene_annotation_episode'
CONTRACT = HERE.parent / 'tool_graders_fastqutils_samstat_contract_2026-10-25_207'
catalog = json.loads((CONTRACT / 'NATIVE_FIELDS_002.json').read_text())
enums = json.loads((CONTRACT / 'ENUM_ADDITIONS_001.json').read_text())
schema_path = PACKAGE / 'bvbrc_fastqutils_schemas.json'
old_bytes = schema_path.read_bytes()
(PACKAGE / 'bvbrc_fastqutils_legacy_cutadapt_schemas.json').write_bytes(old_bytes)
schema = json.loads(old_bytes)
mirrors = []
categories = {
    'fastq_read_count': 'native_metrics', 'gc_acgt_fraction': 'component_metrics',
    'fastq_records': 'sections', 'fastq_quality_characters': 'populations',
    'samstat_html': 'formats', 'missing_artifact': 'diagnostics',
    'base_closed_1': 'axes', 'expected_errors': 'units', 'composition_v1': 'calculation_methods',
}
def extend(node, pointer=''):
    if isinstance(node, dict):
        if 'enum' in node:
            for marker, category in categories.items():
                if marker in node['enum']:
                    additions = [v for v in enums[category] if v not in node['enum']]
                    node['enum'].extend(additions)
                    mirrors.append({'pointer': pointer+'/enum', 'category': category, 'added': additions})
        for key, child in node.items():
            extend(child, pointer+'/'+key)
    elif isinstance(node, list):
        for index, child in enumerate(node):
            extend(child, pointer+'/'+str(index))
extend(schema)
d = schema['$defs']
d['CalculationRequest']['oneOf'].append({
    'type': 'object', 'properties': {
        'calculation_id': deepcopy(d['CalculationBinding']['properties']['calculation_id']),
        'method': {'const': 'samstat_report_mapping_v1'},
        'populations': {'type': 'array', 'items': {'$ref': '#/$defs/PopulationSelector'},
                        'minItems': 1, 'maxItems': 2, 'uniqueItems': True}},
    'required': ['calculation_id', 'method', 'populations'], 'additionalProperties': False})
schema_path.write_text(json.dumps(schema, indent=2)+'\n')

position_axes = ['base_closed_1', 'base_offset_from_end_0', 'read_fraction_bin_0_100', 'native_label']
record_pops = ['samstat_report_records', 'samstat_mapq_ge30', 'samstat_mapq_10_29',
               'samstat_mapq_0_9', 'samstat_unmapped']
specs = {}
for metric in enums['native_metrics']:
    source_metric = metric
    if metric.endswith('_rounded_bin_mean') and ('mismatch_' in metric or '_open_' in metric):
        source_metric = metric.replace('_rounded_bin_mean', '_count')
    fields = [f for f in catalog['fields'] if source_metric in f['proposed_metrics']]
    assert fields, metric
    legacy_only = all(f['versions'] == ['2.2.3'] for f in fields)
    modern_only = all(f['versions'] == ['2.5.0'] for f in fields)
    formats = ['samstat_html_2_2_3'] if legacy_only else (['samstat_html_2_5_0'] if modern_only else ['samstat_html_2_2_3','samstat_html_2_5_0'])
    meaning, precision, units, axes, section, domain = ('observed_count', 'exact_for_retained_population',
        ['alignment_records'], ['none'], 'samstat_summary', 'nonnegative_integer')
    popkeys = record_pops + ['samstat_report_sequences']
    allowed_precisions = None
    if metric.startswith('samstat_base_') or metric.startswith('samstat_mismatch_') and 'unavailable' not in metric:
        units, axes = ['bases'], position_axes
        section = 'samstat_mismatch' if '_mismatch_' in metric else 'samstat_base_start'
    if '_open_' in metric:
        units, axes = ['events'], position_axes
        section = 'samstat_insertion' if '_insertion_' in metric else 'samstat_deletion'
    if metric.endswith('_rounded_bin_mean'):
        units, meaning, precision, domain = ['scaled_native_count'], 'native_normalized', 'native_rounded', 'nonnegative_integer'
        axes = ['native_label']
    if metric == 'samstat_length_density':
        units, axes, section, meaning, precision, domain = ['inverse_bp'], ['length_closed'], 'samstat_length', 'native_estimate', 'native_estimator', 'nonnegative_number'
    if metric in ('samstat_alignment_bin_count','samstat_reported_bin_fraction','samstat_reported_bin_percent'):
        section, axes = 'samstat_mapping', ['none','mapq','native_label']
    if metric == 'samstat_reported_bin_fraction':
        units, meaning, precision, domain = ['fraction'], 'native_normalized', 'native_rounded', 'number_0_1'
    if metric.endswith('_percent') or metric == 'samstat_beyond_axis_percent_upper_bound':
        units, meaning, precision, domain = ['percent'], 'native_normalized', 'native_rounded', 'number_0_100'
    if metric in ('samstat_paired_flag_percent', 'samstat_proper_pair_flag_percent') or metric.endswith('_record_count_display'):
        section = 'samstat_pair_flags'
    if metric.endswith('_record_count_display'):
        meaning, precision = 'observed_native', 'native_rounded'
        allowed_precisions = ['exact_for_retained_population', 'native_rounded']
    if metric.startswith('samstat_legacy_'):
        meaning, precision, domain, axes, section = 'native_normalized', 'native_rounded', 'nonnegative_number', position_axes, 'samstat_quality_start'
        units = ['dimensionless'] if 'quality_index' in metric else (['phred_deviation'] if metric.endswith('_sem') else ['phred'])
    if metric == 'samstat_error_probability_mean_phred':
        units, meaning, precision, domain = ['phred'], 'native_normalized', 'native_rounded', 'nonnegative_number'
    if metric in ('samstat_min_length','samstat_max_length','samstat_uniform_length','samstat_median_length','samstat_n50_length'):
        units, meaning, precision, domain, section = ['bp','kbp','Mbp'], 'observed_native', 'exact_for_retained_population', 'nonnegative_number', 'samstat_length'
        if metric in ('samstat_median_length','samstat_n50_length'):
            meaning = 'native_estimate'
        allowed_precisions = ['exact_for_retained_population','native_rounded','native_estimator','not_reported']
    if metric in ('samstat_min_read_quality_bin','samstat_max_read_quality_bin'):
        units, meaning, axes, section = ['phred'], 'observed_native', ['quality_score'], 'samstat_quality_start'
    if metric == 'samstat_gap_compressed_median_identity_percent':
        meaning, precision, section = 'native_estimate', 'native_estimator', 'samstat_identity'
    if metric == 'samstat_sequence_total_count':
        units, popkeys = ['reads'], ['samstat_report_sequences']
    if metric == 'samstat_total_base_count':
        units = ['bases']
    if metric == 'samstat_position_minimum_records':
        units, meaning, section = ['reads'], 'native_configuration', 'samstat_notes'
    if metric in ('samstat_mismatch_unavailable_record_count','samstat_identity_unavailable_record_count','samstat_mapped_note_record_count','samstat_secondary_excluded_count','samstat_supplementary_excluded_count','samstat_beyond_axis_percent','samstat_beyond_axis_percent_upper_bound'):
        section = 'samstat_notes'
    if metric == 'samstat_secondary_excluded_count':
        popkeys = ['samstat_excluded_secondary']
    if metric == 'samstat_supplementary_excluded_count':
        popkeys = ['samstat_excluded_supplementary']
    if metric == 'samstat_alignment_total_count':
        allowed_precisions = ['exact_for_retained_population', 'not_reported']
        formats.append('samstat_bvbrc_error_html')
    descriptions = [{k: deepcopy(v) for k,v in f.items() if k not in ('native_examples','proposed_metrics')} for f in fields]
    spec = dict(metric=metric, formats=formats, section_key=section,
        native_fields=list(dict.fromkeys(v for f in fields for v in f['native_fields'])),
        units=units, axis_kinds=axes, population_keys=popkeys, meaning=meaning, precision=precision,
        value_domain=domain, interpretation=' '.join(f['population'] for f in fields),
        denominator=' '.join(f['denominator'] for f in fields), coordinates=' '.join(f['coordinates'] for f in fields),
        uncertainty=' '.join(dict.fromkeys(f['uncertainty'] for f in fields)),
        missing_behavior=' '.join(f['missing_input_behavior'] for f in fields),
        reviewed_source='207 NATIVE_FIELDS_002.json / PARSER_CALCULATOR_PORTS_002.md', native_source_definitions=descriptions)
    if allowed_precisions:
        spec['allowed_precisions'] = allowed_precisions
    if metric.endswith('_rounded_bin_mean'):
        spec['interpretation'] += ' Clustered native rounded mean per allocated position; never an exact cardinality.'
        spec['denominator'] = 'Number of allocated positions in native cluster, not records or event count. Original unclustered counts are not recoverable.'
    if metric == 'samstat_beyond_axis_percent_upper_bound':
        spec['interpretation'] += ' Value is a strict upper bound: actual percentage is less than value.'
    specs[metric] = spec

components = {}
for metric, numerator in [('samstat_report_mapped_record_fraction','T-U'), ('samstat_report_ge30_record_fraction','H')]:
    components[metric] = dict(metric=metric, method='samstat_report_mapping_v1', formula=f'({numerator})/T',
        input_fields=['selected same-document/version disjoint samstat_report_records populations',
                      'four exact samstat_alignment_bin_count operands per population: ge30,10_29,0_9,unmapped',
                      'optional native samstat_alignment_total_count as consistency check'],
        units=['fraction'], meaning='native_report_derived', uncertainty='not_estimated',
        population='Contributing primary records in2.5.0; secondary-excluded, supplementary-retained records in2.2.3. No FASTQ/molecule/pair inference.',
        denominator='T=sum of four exact native count bins across selected nonoverlapping strata; U=unmapped sum; H=ge30 sum including MAPQ255.',
        requirements='One or two explicitly selected strata from one supported alignment-mode document/version; complete unique exact count bins; no all+mate overlap; optional total must agree.',
        missing_behavior='Zero denominator undefined; absent/truncated bin missing/truncated; conflicting populations/counts incompatible; prefix or partial document yields partial; unproved input scope remains report-population-only.',
        source_contract='207 PARSER_CALCULATOR_PORTS_002.md section6; calculator separately implemented')
assert len(specs)==59 and len(components)==2
(PACKAGE/'bvbrc_fastqutils_samstat_specs.py').write_text(
    '"""Finite SAMstat native measurements and component descriptions. No executable scoring language.\n\n'
    'Source: sealed207 revision002. Version-specific native definitions remain explicit;\n'
    'formats/populations/rounding do not establish deployment provenance.\n"""\n\n'
    +'SAMSTAT_METRICS = '+pprint.pformat(specs,sort_dicts=False,width=110)+'\n\n'
    +'SAMSTAT_COMPONENTS = '+pprint.pformat(components,sort_dicts=False,width=110)+'\n')
(HERE/'ENUM_SPEC_MANIFEST_001.json').write_text(json.dumps(dict(
    source_contract_sha256=hashlib.sha256((CONTRACT/'NATIVE_FIELDS_002.json').read_bytes()).hexdigest(),
    native_metrics=list(specs), component_metrics=list(components), enum_mirrors=mirrors,
    frozen_208_schema_sha256=hashlib.sha256(old_bytes).hexdigest(),
    calculation_request=d['CalculationRequest']['oneOf'][-1]),indent=2)+'\n')
print('Created59 native descriptions,2 component descriptions; expanded',len(mirrors),'finite enum mirrors.')
