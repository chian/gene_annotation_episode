"""Closed native HOMER measurement records; no execution or enrichment policy.

The local primitive schemas describe shape only. Their semantic authorities are
the unchanged shared numerical and source-location validators.
"""
from copy import deepcopy
import json
import math
import re
from jsonschema import Draft202012Validator, validators
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority.bvbrc_alignment_values import validate_native_number, validate_numeric_cell
from gene_annotation_episode.episodic_workflow.root.a105.library.retained_input_authority import phylogeny_calculation_contracts as locations
SHEET_VERSION = 'homer_motif_sheet_v1'
COMPONENTS_VERSION = 'homer_motif_components_v1'
RETURN_VERSION = 'homer_motif_return_v1'
OPERATION = 'find_enriched_motifs_with_homer'
ROLES = ('known_results', 'known_pwm', 'denovo_pwm', 'denovo_combined_pwm', 'denovo_nonredundant_pwm', 'sequence_table', 'group_weights', 'normalization_table', 'native_log')
OUTCOMES = ('succeeded', 'failed', 'not_run', 'unknown')
NUMBER_FIELDS = {'site_threshold': 'native_site_detection_score', 'p_value': 'probability', 'ln_p_value': 'natural_log_probability', 'q_value': 'probability', 'target_weight': 'relative_weight', 'target_percentage': 'percent', 'background_weight': 'relative_weight', 'background_percentage': 'percent'}
AUXILIARY_FIELDS = {'Tpos': dict(unit='bp', definition='native_weighted_site_center_mean', population='target_site_occurrences', coordinate_origin='native_scan_offset_not_authenticated', weighting='sequence_weight_per_site', denominator='sum_of_target_site_weights', qualifications=['native_scan_offset_not_authenticated']), 'Bpos': dict(unit='bp', definition='native_weighted_site_center_mean', population='background_site_occurrences', coordinate_origin='native_scan_offset_not_authenticated', weighting='sequence_weight_per_site', denominator='sum_of_background_site_weights', qualifications=['native_scan_offset_not_authenticated']), 'Tstd': dict(unit='bp', definition='native_position_spread', population='target_site_occurrences', coordinate_origin='native_scan_offset_not_authenticated', weighting='squared_weighted_residual_divided_by_site_weight_sum', denominator='sum_of_target_site_weights', qualifications=['not_standard_error_of_mean', 'native_scan_offset_not_authenticated']), 'Bstd': dict(unit='bp', definition='native_position_spread', population='background_site_occurrences', coordinate_origin='native_scan_offset_not_authenticated', weighting='squared_weighted_residual_divided_by_site_weight_sum', denominator='sum_of_background_site_weights', qualifications=['not_standard_error_of_mean', 'native_scan_offset_not_authenticated']), 'StrandBias': dict(unit='log2_ratio', definition='native_target_plus_minus_strand_weight_log2_ratio', population='target_site_occurrences', coordinate_origin='not_applicable', weighting='sequence_weight_per_site', denominator='weighted_minus_strand_site_mass', qualifications=['native_small_mass_plus_minus_10_or_zero_sentinels']), 'Multiplicity': dict(unit='weighted_sites_per_weighted_positive_sequence', definition='native_target_unique_center_site_multiplicity', population='motif_positive_target_sequences', coordinate_origin='not_applicable', weighting='native_unique_center_site_sequence_weights', denominator='weighted_target_sequences_with_sites', qualifications=['native_default_one_if_denominator_le_0_01'])}
_SOURCE = {'type': 'string', 'pattern': '^source_[0-9a-f]{24,64}$', 'format': 'reference', 'x-reference-namespace': 'source'}
_ARTIFACT = {'type': 'string', 'pattern': '^artifact_[0-9a-f]{64}$'}
_TEXT = {'type': 'string', 'minLength': 1}
_INT = {'type': 'integer', 'minimum': 0}
_STATES = ['available', 'missing', 'not_measured', 'failed', 'truncated', 'incompatible']
_STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine_many({'integer': lambda _, x: type(x) is int, 'number': lambda _, x: type(x) is int or (type(x) is float and math.isfinite(x))}))

def require(condition, code):
    if not condition:
        raise ValueError('homer_' + code)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()

def _object(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)

def _array(items):
    return {'type': 'array', 'items': items}

def _ref(name):
    return {'$ref': '#/$defs/' + name}

def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}

def _definitions():
    d = {}
    digest = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
    d['Artifact'] = _object(dict(raw_artifact_ref=_ARTIFACT, source_ref=_SOURCE, sha256=digest, size_bytes=_INT))
    artifact_location = _object(dict(raw_artifact_ref=_ARTIFACT, source_ref=_SOURCE, sha256=digest))
    d['Location'] = _object(dict(artifact=artifact_location, byte_start_0based=_nullable(_INT), byte_end_0based_exclusive=_nullable(_INT), line_start_1based=_nullable({'type': 'integer', 'minimum': 1}), line_end_1based_inclusive=_nullable({'type': 'integer', 'minimum': 1}), xml_path=_nullable(_TEXT)))
    d['Evidence'] = _object(dict(content=_object(dict(source_ref=_SOURCE, artifact_field={'enum': ['artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref']}, artifact_ref=_ARTIFACT, sha256=digest, byte_count=_INT)), pointer={'type': 'string'}))
    d['NativeNumber'] = _object(dict(raw_token={'type': 'string'}, value=_nullable({'type': 'number'}), state={'enum': _STATES}, token_kind={'enum': ['malformed', 'blank', 'native_na', 'nonfinite', 'overflow', 'underflow', 'finite']}, source_location=_ref('Location')))
    uncertainty = _nullable(_object(dict(kind={'enum': ['confidence_interval', 'standard_error', 'standard_deviation', 'native_unknown']}, lower=_nullable({'type': 'number'}), upper=_nullable({'type': 'number'}), value=_nullable({'type': 'number'}), method_id=_TEXT)))
    d['NumericCell'] = _object(dict(value=_nullable({'type': 'number'}), state={'enum': _STATES}, unit=_TEXT, origin={'enum': ['native_observation', 'calculated', 'fitted']}, numerator=_nullable({'type': 'number'}), denominator=_nullable({'type': 'number'}), population_id=_TEXT, method_id=_TEXT, evidence=_array(_ref('Evidence')), uncertainty=uncertainty, requirement_ids={'type': 'array', 'items': _TEXT, 'uniqueItems': True}))
    d['Capture'] = _object(dict(state={'enum': ['complete', 'truncated', 'missing']}, byte_start_0based={'const': 0}, byte_end_0based_exclusive=_INT, original_size_bytes=_nullable(_INT)))
    d['File'] = _object(dict(file_id=_TEXT, role={'enum': list(ROLES)}, native_relative_path=_TEXT, artifact=_nullable(_ref('Artifact')), capture=_ref('Capture'), decode_state={'enum': ['complete', 'partial', 'unavailable']}, issues=_array(_TEXT)))
    d['Invocation'] = _object(dict(invocation_id=_TEXT, operation={'const': OPERATION}, selected_window_bp=_nullable({'type': 'integer', 'minimum': 1}), selected_motif_lengths={'type': 'array', 'items': {'type': 'integer', 'minimum': 1}, 'uniqueItems': True}, native_parameters={'type': 'object'}, software=_array(_object(dict(name=_TEXT, version=_nullable(_TEXT), sha256=digest)))))
    d['Execution'] = _object(dict(wrapper_returncode=_nullable({'type': 'integer'}), **{key: {'enum': list(OUTCOMES)} for key in ('wrapper_outcome', 'known_outcome', 'denovo_outcome')}))
    d['Selector'] = _object(dict(series_ids={'type': 'array', 'items': _TEXT, 'uniqueItems': True}, offset=_INT, limit=_INT))
    d['ReportedNumber'] = _object(dict(availability={'enum': ['provided', 'not_provided']}, number=_nullable(_ref('NativeNumber')), unit=_TEXT, precision={'enum': ['native_token', 'fixed_1', 'fixed_2', 'fixed_3', 'fixed_4', 'fixed_6', 'scientific_3', 'integer_exponent', 'not_provided']}))
    d['PwmRow'] = _object(dict(ordinal_0based=_INT, raw_fields=_array({'type': 'string'}), location=_ref('Location'), cells=_array(_ref('NativeNumber'))))
    d['AuxiliaryMeasurement'] = _object(dict(field={'enum': list(AUXILIARY_FIELDS)}, extra_field_ordinal_0based=_INT, token_ordinal_0based=_INT, raw_field={'type': 'string'}, reported=_ref('ReportedNumber'), definition=_TEXT, population=_TEXT, coordinate_origin=_TEXT, weighting=_TEXT, denominator=_TEXT, qualifications=_array(_TEXT)))
    d['Representation'] = _object(dict(kind={'enum': ['known_table', 'native_pwm']}, raw_fields=_array({'type': 'string'}), location=_ref('Location'), numbers=_object({key: _ref('ReportedNumber') for key in NUMBER_FIELDS}), native_gap_field=_nullable({'type': 'string'}), extra_fields=_array({'type': 'string'}), native_auxiliary_measurements=_array(_ref('AuxiliaryMeasurement')), native_auxiliary_absent_fields={'type': 'array', 'items': {'enum': list(AUXILIARY_FIELDS)}, 'uniqueItems': True}, pwm_rows=_array(_ref('PwmRow')), issues=_array(_TEXT)))
    d['Observation'] = _object(dict(occurrence_id=_TEXT, ordinal_0based=_INT, location=_ref('Location'), raw_fields=_array({'type': 'string'}), parse_state={'enum': ['complete', 'qualified', 'malformed', 'truncated']}, name=_nullable({'type': 'string'}), consensus=_nullable({'type': 'string'}), pwm_state={'enum': ['provided', 'not_provided', 'partial', 'conflict']}, representations=_array(_ref('Representation')), issues=_array(_TEXT)))
    d['Series'] = _object(dict(series_id=_TEXT, file_id=_TEXT, role={'enum': ['known_results', 'denovo_pwm', 'denovo_combined_pwm', 'denovo_nonredundant_pwm']}, phase={'const': 'final_saved_output'}, capture_state={'enum': ['complete', 'truncated', 'missing']}, native_outcome={'enum': list(OUTCOMES)}, raw_header=_array({'type': 'string'}), displayed_totals=_object(dict(target=_nullable(_ref('NativeNumber')), background=_nullable(_ref('NativeNumber')), meaning={'const': 'wrapper_inferred_from_first_rounded_motif'})), observations=_array(_ref('Observation')), issues=_array(_TEXT)))
    d['Sidecar'] = _object(dict(file_id=_TEXT, native_ordinal_0based=_nullable(_INT), linked_series_id=_nullable(_TEXT), linked_ordinal_0based=_nullable(_INT), state={'enum': ['linked', 'unlinked', 'ambiguous', 'conflict']}, observations=_array(_ref('Observation')), issues=_array(_TEXT)))
    d['PopulationRow'] = _object(dict(ordinal_0based=_INT, member_id=_nullable({'type': 'string'}), raw_fields=_array({'type': 'string'}), location=_ref('Location'), state={'enum': ['complete', 'malformed', 'truncated']}, length_bp=_nullable(_INT), group=_nullable({'enum': ['target', 'background']}), weight=_nullable(_ref('NativeNumber')), issues=_array(_TEXT)))
    d['Membership'] = _object(dict(member_id=_TEXT, sequence_ordinals=_array(_INT), group_ordinals=_array(_INT), group=_nullable({'enum': ['target', 'background']}), state={'enum': ['unique', 'missing', 'ambiguous', 'invalid']}))
    d['Populations'] = _object(dict(state={'enum': ['complete', 'partial', 'unavailable']}, sequence_file_ids=_array(_TEXT), group_file_ids=_array(_TEXT), sequence_rows=_array(_ref('PopulationRow')), group_rows=_array(_ref('PopulationRow')), memberships=_array(_ref('Membership')), issues=_array(_TEXT)))
    d['AuxiliaryRow'] = _object(dict(file_id=_TEXT, ordinal_0based=_INT, phase={'enum': ['native_diagnostic', 'native_normalization_report_unspecified']}, raw_fields=_array({'type': 'string'}), raw_hex=_nullable({'type': 'string'}), location=_ref('Location'), complete={'type': 'boolean'}))
    d['Sheet'] = _object(dict(version={'const': SHEET_VERSION}, invocation=_ref('Invocation'), execution=_ref('Execution'), files=_array(_ref('File')), series=_array(_ref('Series')), sidecars=_array(_ref('Sidecar')), populations=_ref('Populations'), auxiliary_rows=_array(_ref('AuxiliaryRow')), issues=_array(_TEXT)))
    d['Count'] = _object(dict(series_id=_TEXT, role=_TEXT, captured_occurrences=_INT, selected_occurrences=_INT, capture_state={'enum': ['complete', 'truncated', 'missing']}, native_outcome={'enum': list(OUTCOMES)}))
    d['PopulationFacts'] = _object(dict(state={'enum': ['complete', 'partial', 'unavailable']}, selected_window_bp=_nullable({'type': 'integer', 'minimum': 1}), captured_sequence_occurrences=_INT, captured_group_occurrences=_INT, unique_joined_target_members=_INT, unique_joined_background_members=_INT, observed_sequence_lengths_bp=_array(_INT), reported_weight_completeness=_object({group: {'enum': ['complete', 'unavailable']} for group in ('target', 'background')}), meaning={'const': 'captured_input_occurrences_not_effective_native_denominators'}))
    d['WeightSum'] = _object(dict(group={'enum': ['target', 'background']}, meaning={'const': 'reported_input_weight_sum'}, basis={'const': 'derived_from_reported_weights'}, cell=_ref('NumericCell'), issues=_array(_TEXT)))
    d['SeriesMetadata'] = _object(dict(series_id=_TEXT, role=deepcopy(d['Series']['properties']['role']), requested_motif_length_bp=_nullable({'type': 'integer', 'minimum': 1, 'description': 'Caller-selected length in bp identified by the native per-length output filename; not observed PWM length. Null for other or unclassified representations.'}), capture_state=deepcopy(d['Series']['properties']['capture_state']), native_outcome=deepcopy(d['Series']['properties']['native_outcome'])))
    d['SeriesCatalog'] = {**_array(_ref('SeriesMetadata')), 'description': 'All series actually represented in the retained sheet, in stored order, including missing or truncated captures. Their IDs remain available for later saved-data selection.'}
    d['Components'] = _object(dict(version={'const': COMPONENTS_VERSION}, selector=_ref('Selector'), available_series=_ref('SeriesCatalog'), execution=_ref('Execution'), selected_series=_array(_ref('Series')), counts=_array(_ref('Count')), population_facts=_ref('PopulationFacts'), reported_input_weight_sums=_array(_ref('WeightSum')), issues=_array(_TEXT)))
    for name in ('NativeNumber', 'ReportedNumber', 'PwmRow', 'AuxiliaryMeasurement', 'Representation', 'Observation', 'Series', 'NumericCell', 'WeightSum'):
        public = deepcopy(d[name])

        def project(node):
            if type(node) is dict:
                if '$ref' in node and node['$ref'].split('/')[-1] in ('NativeNumber', 'ReportedNumber', 'PwmRow', 'AuxiliaryMeasurement', 'Representation', 'Observation', 'NumericCell'):
                    node['$ref'] = '#/$defs/Public' + node['$ref'].split('/')[-1]
                if node.get('type') == 'object':
                    for key in ('source_location', 'location', 'file_id', 'evidence', 'requirement_ids'):
                        node.get('properties', {}).pop(key, None)
                        if key in node.get('required', []):
                            node['required'].remove(key)
                for child in node.values():
                    project(child)
            elif type(node) is list:
                for child in node:
                    project(child)
        project(public)
        d['Public' + name] = public
    d['Return'] = _object(dict(version={'const': RETURN_VERSION}, source_ref=_SOURCE, selector=_ref('Selector'), execution=_ref('Execution'), available_series=_ref('SeriesCatalog'), selected_series=_array(_ref('PublicSeries')), counts=_array(_ref('Count')), population_facts=_ref('PopulationFacts'), reported_input_weight_sums=_array(_ref('PublicWeightSum')), issues=_array(_TEXT)))
    return d

def homer_record_schema(kind):
    definitions = _definitions()
    require(kind in ('Sheet', 'Selector', 'Components', 'Return', 'Invocation', 'Execution', 'File'), 'schema_kind_invalid')
    pending, reachable = ([kind], {})
    while pending:
        name = pending.pop()
        if name in reachable:
            continue
        reachable[name] = deepcopy(definitions[name])

        def refs(node):
            if type(node) is dict:
                if '$ref' in node:
                    yield node['$ref'].removeprefix('#/$defs/')
                for child in node.values():
                    yield from refs(child)
            elif type(node) is list:
                for child in node:
                    yield from refs(child)
        pending.extend(refs(reachable[name]))
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$ref': '#/$defs/' + kind, '$defs': reachable}

def validated(kind, value):
    try:
        canonical(value)
        _STRICT(homer_record_schema(kind)).validate(value)
    except Exception as error:
        raise ValueError('homer_' + kind.lower() + '_invalid') from error

    def semantics(node):
        if type(node) is dict:
            keys = set(node)
            if keys == {'raw_token', 'value', 'state', 'token_kind', 'source_location'}:
                validate_native_number(node)
            elif keys == {'value', 'state', 'unit', 'origin', 'numerator', 'denominator', 'population_id', 'method_id', 'evidence', 'uncertainty', 'requirement_ids'}:
                validate_numeric_cell(node)
            elif keys == {'artifact', 'byte_start_0based', 'byte_end_0based_exclusive', 'line_start_1based', 'line_end_1based_inclusive', 'xml_path'}:
                locations.location(node)
            elif keys == {'availability', 'number', 'unit', 'precision'}:
                require((node['availability'] == 'provided') == (node['number'] is not None), 'number_availability_conflict')
                require((node['availability'] == 'not_provided') == (node['precision'] == 'not_provided'), 'number_precision_conflict')
            reference_record = keys in ({'raw_artifact_ref', 'source_ref', 'sha256'}, {'raw_artifact_ref', 'source_ref', 'sha256', 'size_bytes'}, {'source_ref', 'artifact_field', 'artifact_ref', 'sha256', 'byte_count'}) or node.get('version') == RETURN_VERSION
            for key, child in node.items():
                if reference_record and key in ('source_ref', 'raw_artifact_ref', 'artifact_ref') and (child is not None):
                    pattern = 'source_[0-9a-f]{24,64}' if key == 'source_ref' else 'artifact_[0-9a-f]{64}'
                    require(re.fullmatch(pattern, child) is not None, 'reference_invalid')
                semantics(child)
        elif type(node) is list:
            for child in node:
                semantics(child)
    semantics(value)
    if kind in ('Components', 'Return'):
        series, counts = (value['selected_series'], value['counts'])
        catalog = {item['series_id']: item for item in value['available_series']}
        require(len(catalog) == len(value['available_series']), 'series_catalog_identity_conflict')
        require(all((item['requested_motif_length_bp'] is None or item['role'] == 'denovo_pwm' for item in catalog.values())), 'series_catalog_length_conflict')
        require([s['series_id'] for s in series] == value['selector']['series_ids'] and len(series) == len(counts), 'selected_series_count_conflict')
        require(sum((len(s['observations']) for s in series)) <= value['selector']['limit'], 'selected_window_conflict')
        for item, count in zip(series, counts):
            metadata = catalog.get(item['series_id'])
            require(metadata is not None and all((metadata[key] == item[key] for key in ('role', 'capture_state', 'native_outcome'))), 'series_catalog_selection_conflict')
            require(count['series_id'] == item['series_id'] and count['role'] == item['role'] and (count['capture_state'] == item['capture_state']) and (count['native_outcome'] == item['native_outcome']) and (count['selected_occurrences'] == len(item['observations'])) and (count['captured_occurrences'] >= count['selected_occurrences']), 'selected_series_count_conflict')
        require([s['group'] for s in value['reported_input_weight_sums']] == ['target', 'background'], 'weight_sum_groups_invalid')
        for summary in value['reported_input_weight_sums']:
            cell = summary['cell']
            require(cell['unit'] == 'relative_weight' and cell['origin'] == 'calculated' and (cell['method_id'] == 'homer_reported_input_weight_fsum_v1'), 'weight_sum_meaning_conflict')
            require(cell['state'] != 'available' or value['population_facts']['reported_weight_completeness'][summary['group']] == 'complete', 'weight_sum_population_conflict')
            if kind == 'Return':
                validate_numeric_cell(dict(cell, evidence=[], requirement_ids=[]))
    return deepcopy(value)

def validate_homer_selector(selector):
    return validated('Selector', selector)
