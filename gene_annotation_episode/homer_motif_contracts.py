"""Closed native HOMER measurement records; no execution or enrichment policy.

The local primitive schemas describe shape only. Their semantic authorities are
the unchanged shared numerical and source-location validators.
"""
from copy import deepcopy
import hashlib
import json
import math
import re

from jsonschema import Draft202012Validator, validators

from .bvbrc_alignment_values import native_number, validate_native_number, validate_numeric_cell
from . import phylogeny_calculation_contracts as locations


SHEET_VERSION = 'homer_motif_sheet_v1'
COMPONENTS_VERSION = 'homer_motif_components_v1'
RETURN_VERSION = 'homer_motif_return_v1'
OPERATION = 'find_enriched_motifs_with_homer'
ROLES = ('known_results', 'known_pwm', 'denovo_pwm', 'denovo_combined_pwm',
    'denovo_nonredundant_pwm', 'sequence_table', 'group_weights',
    'normalization_table', 'native_log')
OUTCOMES = ('succeeded', 'failed', 'not_run', 'unknown')
NUMBER_FIELDS = {
    'site_threshold': 'native_site_detection_score', 'p_value': 'probability',
    'ln_p_value': 'natural_log_probability', 'q_value': 'probability',
    'target_weight': 'relative_weight', 'target_percentage': 'percent',
    'background_weight': 'relative_weight', 'background_percentage': 'percent',
}
TABLE_COLUMNS = {'p_value': 2, 'ln_p_value': 3, 'q_value': 4, 'target_weight': 5,
    'target_percentage': 6, 'background_weight': 7, 'background_percentage': 8}
_PRECISION = {'site_threshold': 'fixed_6', 'p_value': 'integer_exponent',
    'ln_p_value': 'fixed_6', 'q_value': 'fixed_4', 'target_weight': 'fixed_1',
    'target_percentage': 'fixed_2', 'background_weight': 'fixed_1', 'background_percentage': 'fixed_2'}
_PWM_STATS = re.compile(r'T:([^()]+)\(([^%]*)%\),B:([^()]+)\(([^%]*)%\),P:(.*)\Z')
AUXILIARY_FIELDS = {
    'Tpos': dict(unit='bp', definition='native_weighted_site_center_mean', population='target_site_occurrences',
        coordinate_origin='native_scan_offset_not_authenticated', weighting='sequence_weight_per_site',
        denominator='sum_of_target_site_weights', qualifications=['native_scan_offset_not_authenticated']),
    'Bpos': dict(unit='bp', definition='native_weighted_site_center_mean', population='background_site_occurrences',
        coordinate_origin='native_scan_offset_not_authenticated', weighting='sequence_weight_per_site',
        denominator='sum_of_background_site_weights', qualifications=['native_scan_offset_not_authenticated']),
    'Tstd': dict(unit='bp', definition='native_position_spread', population='target_site_occurrences',
        coordinate_origin='native_scan_offset_not_authenticated', weighting='squared_weighted_residual_divided_by_site_weight_sum',
        denominator='sum_of_target_site_weights', qualifications=['not_standard_error_of_mean', 'native_scan_offset_not_authenticated']),
    'Bstd': dict(unit='bp', definition='native_position_spread', population='background_site_occurrences',
        coordinate_origin='native_scan_offset_not_authenticated', weighting='squared_weighted_residual_divided_by_site_weight_sum',
        denominator='sum_of_background_site_weights', qualifications=['not_standard_error_of_mean', 'native_scan_offset_not_authenticated']),
    'StrandBias': dict(unit='log2_ratio', definition='native_target_plus_minus_strand_weight_log2_ratio',
        population='target_site_occurrences', coordinate_origin='not_applicable', weighting='sequence_weight_per_site',
        denominator='weighted_minus_strand_site_mass', qualifications=['native_small_mass_plus_minus_10_or_zero_sentinels']),
    'Multiplicity': dict(unit='weighted_sites_per_weighted_positive_sequence', definition='native_target_unique_center_site_multiplicity',
        population='motif_positive_target_sequences', coordinate_origin='not_applicable', weighting='native_unique_center_site_sequence_weights',
        denominator='weighted_target_sequences_with_sites', qualifications=['native_default_one_if_denominator_le_0_01']),
}
_SOURCE = {'type': 'string', 'pattern': '^source_[0-9a-f]{24,64}$',
    'format': 'reference', 'x-reference-namespace': 'source'}
_ARTIFACT = {'type': 'string', 'pattern': '^artifact_[0-9a-f]{64}$'}
_TEXT = {'type': 'string', 'minLength': 1}
_INT = {'type': 'integer', 'minimum': 0}
_STATES = ['available', 'missing', 'not_measured', 'failed', 'truncated', 'incompatible']
_STRICT = validators.extend(Draft202012Validator, type_checker=
    Draft202012Validator.TYPE_CHECKER.redefine_many({
        'integer': lambda _, x: type(x) is int,
        'number': lambda _, x: type(x) is int or type(x) is float and math.isfinite(x),
    }))


def require(condition, code):
    if not condition:
        raise ValueError('homer_' + code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=True, allow_nan=False).encode()


def identity(kind, value):
    return kind + ':' + hashlib.sha256(canonical(value)).hexdigest()


def native_path(value):
    require(type(value) is str and bool(value) and '\\' not in value
        and not value.startswith('/') and all(p not in ('', '.', '..') for p in value.split('/')),
        'native_relative_path_invalid')


def field_number(field, token, location):
    require(field in NUMBER_FIELDS, 'native_number_field_invalid')
    bounds = {}
    if field in ('p_value', 'q_value'): bounds = dict(minimum=0, maximum=1)
    elif field == 'ln_p_value': bounds = dict(maximum=0)
    elif field in ('target_weight', 'background_weight'): bounds = dict(minimum=0)
    elif field in ('target_percentage', 'background_percentage'): bounds = dict(minimum=0, maximum=100)
    return native_number(token, source_location=location, **bounds)


def expected_precision(kind, field):
    return 'scientific_3' if kind == 'known_table' and field == 'ln_p_value' else _PRECISION[field]


def native_precision(token, expected):
    if expected.startswith('fixed_'):
        pattern = r'[+-]?[0-9]+\.[0-9]{' + expected.removeprefix('fixed_') + '}'
    elif expected == 'scientific_3': pattern = r'[+-]?[0-9]\.[0-9]{3}[eE][+-][0-9]+'
    elif expected == 'integer_exponent': pattern = r'1e-?[0-9]+'
    else: return 'native_token'
    return expected if re.fullmatch(pattern, token) else 'native_token'


def representation_tokens(kind, fields):
    if kind == 'known_table':
        if len(fields) != 9: return {}
        return {field: fields[column][:-1] if field.endswith('percentage') and fields[column].endswith('%')
            else fields[column] for field, column in TABLE_COLUMNS.items()}
    if len(fields) < 6: return {}
    result = dict(site_threshold=fields[2], ln_p_value=fields[3])
    stats = _PWM_STATS.fullmatch(fields[5])
    if stats is not None:
        result.update(zip(('target_weight', 'target_percentage', 'background_weight',
            'background_percentage', 'p_value'), stats.groups()))
    return result


def known_pwm_ordinal(path):
    match = re.fullmatch(r'(?:[^/]+/)*known([1-9][0-9]*)\.motif', path)
    try: return int(match[1]) - 1 if match else None
    except (ValueError, OverflowError): return None


def sidecar_matches(source, target):
    if source['name'] != target['name'] or source['consensus'] != target['consensus']:
        return False
    for field in ('p_value', 'target_weight', 'target_percentage', 'background_weight', 'background_percentage'):
        a = source['representations'][0]['numbers'][field]['number']
        b = target['representations'][0]['numbers'][field]['number']
        if a is None or b is None or a['raw_token'] != b['raw_token']: return False
    return True


def auxiliary_number(field, token, location):
    require(field in AUXILIARY_FIELDS, 'auxiliary_field_invalid')
    bounds = dict(minimum=0) if field in ('Tstd', 'Bstd', 'Multiplicity') else {}
    return native_number(token, source_location=location, **bounds)


def native_group(token):
    if re.fullmatch(r'[+-]?[0-9]+', token) is None: return None
    unsigned = token.lstrip('+-').lstrip('0')
    if not unsigned: return 'background'
    return 'target' if not token.startswith('-') and unsigned == '1' else None


def population_memberships(sequence_rows, group_rows):
    indices = [{}, {}]
    for rows, index in zip((sequence_rows, group_rows), indices):
        for row in rows:
            if row['member_id']: index.setdefault(row['member_id'], []).append(row)
    order = list(dict.fromkeys(r['member_id'] for r in sequence_rows + group_rows if r['member_id']))
    result = []
    for member in order:
        a, b = indices[0].get(member, []), indices[1].get(member, [])
        state = 'missing' if not a or not b else 'ambiguous' if len(a) != 1 or len(b) != 1 else 'unique'
        # Weight availability qualifies the numerical sum, not an already
        # observed unambiguous member/group association.
        if state == 'unique' and (a[0]['state'] != 'complete' or b[0]['state'] != 'complete'
                or b[0]['group'] is None): state = 'invalid'
        result.append(dict(member_id=member, sequence_ordinals=[r['ordinal_0based'] for r in a],
            group_ordinals=[r['ordinal_0based'] for r in b], group=b[0]['group'] if len(b) == 1 else None, state=state))
    return result


def physical_population_complete(files, sequence_ids, group_ids, sequence_rows, group_rows, memberships):
    population_files = [f for f in files if f['file_id'] in sequence_ids + group_ids]
    return (len(sequence_ids) == len(group_ids) == 1 and bool(sequence_rows) and bool(group_rows)
        and all(f['capture']['state'] == 'complete' and f['decode_state'] == 'complete' for f in population_files)
        and all(r['state'] == 'complete' and not r['issues'] for r in sequence_rows)
        and all(r['state'] == 'complete' and r['group'] is not None for r in group_rows)
        and all(m['state'] == 'unique' for m in memberships))


def reported_group_weight_complete(files, populations, group):
    require(group in ('target', 'background'), 'population_group_invalid')
    return (physical_population_complete(files, populations['sequence_file_ids'], populations['group_file_ids'],
        populations['sequence_rows'], populations['group_rows'], populations['memberships'])
        and all(r['weight'] is not None and r['weight']['state'] == 'available'
            for r in populations['group_rows'] if r['group'] == group))


def population_state(files, sequence_ids, group_ids, sequence_rows, group_rows, memberships):
    populations = dict(sequence_file_ids=sequence_ids, group_file_ids=group_ids,
        sequence_rows=sequence_rows, group_rows=group_rows, memberships=memberships)
    complete = all(reported_group_weight_complete(files, populations, group) for group in ('target', 'background'))
    return 'complete' if complete else 'partial' if sequence_rows or group_rows else 'unavailable'


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
    d['Artifact'] = _object(dict(raw_artifact_ref=_ARTIFACT, source_ref=_SOURCE,
        sha256=digest, size_bytes=_INT))
    artifact_location = _object(dict(raw_artifact_ref=_ARTIFACT, source_ref=_SOURCE, sha256=digest))
    d['Location'] = _object(dict(artifact=artifact_location,
        byte_start_0based=_nullable(_INT), byte_end_0based_exclusive=_nullable(_INT),
        line_start_1based=_nullable({'type': 'integer', 'minimum': 1}),
        line_end_1based_inclusive=_nullable({'type': 'integer', 'minimum': 1}),
        xml_path=_nullable(_TEXT)))
    d['Evidence'] = _object(dict(content=_object(dict(source_ref=_SOURCE,
        artifact_field={'enum': ['artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref']},
        artifact_ref=_ARTIFACT, sha256=digest, byte_count=_INT)), pointer={'type': 'string'}))
    d['NativeNumber'] = _object(dict(raw_token={'type': 'string'}, value=_nullable({'type': 'number'}),
        state={'enum': _STATES}, token_kind={'enum': ['malformed', 'blank', 'native_na',
            'nonfinite', 'overflow', 'underflow', 'finite']}, source_location=_ref('Location')))
    uncertainty = _nullable(_object(dict(kind={'enum': ['confidence_interval', 'standard_error',
        'standard_deviation', 'native_unknown']}, lower=_nullable({'type': 'number'}),
        upper=_nullable({'type': 'number'}), value=_nullable({'type': 'number'}), method_id=_TEXT)))
    d['NumericCell'] = _object(dict(value=_nullable({'type': 'number'}), state={'enum': _STATES},
        unit=_TEXT, origin={'enum': ['native_observation', 'calculated', 'fitted']},
        numerator=_nullable({'type': 'number'}), denominator=_nullable({'type': 'number'}),
        population_id=_TEXT, method_id=_TEXT, evidence=_array(_ref('Evidence')),
        uncertainty=uncertainty, requirement_ids={'type': 'array', 'items': _TEXT, 'uniqueItems': True}))
    d['Capture'] = _object(dict(state={'enum': ['complete', 'truncated', 'missing']},
        byte_start_0based={'const': 0}, byte_end_0based_exclusive=_INT,
        original_size_bytes=_nullable(_INT)))
    d['File'] = _object(dict(file_id=_TEXT, role={'enum': list(ROLES)}, native_relative_path=_TEXT,
        artifact=_nullable(_ref('Artifact')), capture=_ref('Capture'),
        decode_state={'enum': ['complete', 'partial', 'unavailable']}, issues=_array(_TEXT)))
    d['Invocation'] = _object(dict(invocation_id=_TEXT, operation={'const': OPERATION},
        selected_window_bp=_nullable({'type': 'integer', 'minimum': 1}),
        selected_motif_lengths={'type': 'array', 'items': {'type': 'integer', 'minimum': 1}, 'uniqueItems': True},
        native_parameters={'type': 'object'}, software=_array(_object(dict(name=_TEXT,
            version=_nullable(_TEXT), sha256=digest)))))
    d['Execution'] = _object(dict(wrapper_returncode=_nullable({'type': 'integer'}),
        **{key: {'enum': list(OUTCOMES)} for key in
            ('wrapper_outcome', 'known_outcome', 'denovo_outcome')}))
    d['Selector'] = _object(dict(series_ids={'type': 'array', 'items': _TEXT, 'uniqueItems': True},
        offset=_INT, limit=_INT))
    d['ReportedNumber'] = _object(dict(availability={'enum': ['provided', 'not_provided']},
        number=_nullable(_ref('NativeNumber')), unit=_TEXT,
        precision={'enum': ['native_token', 'fixed_1', 'fixed_2', 'fixed_3', 'fixed_4',
            'fixed_6', 'scientific_3', 'integer_exponent', 'not_provided']}))
    d['PwmRow'] = _object(dict(ordinal_0based=_INT, raw_fields=_array({'type': 'string'}),
        location=_ref('Location'), cells=_array(_ref('NativeNumber'))))
    d['AuxiliaryMeasurement'] = _object(dict(field={'enum': list(AUXILIARY_FIELDS)},
        extra_field_ordinal_0based=_INT, token_ordinal_0based=_INT, raw_field={'type': 'string'},
        reported=_ref('ReportedNumber'), definition=_TEXT, population=_TEXT, coordinate_origin=_TEXT,
        weighting=_TEXT, denominator=_TEXT, qualifications=_array(_TEXT)))
    d['Representation'] = _object(dict(kind={'enum': ['known_table', 'native_pwm']},
        raw_fields=_array({'type': 'string'}), location=_ref('Location'),
        numbers=_object({key: _ref('ReportedNumber') for key in NUMBER_FIELDS}),
        native_gap_field=_nullable({'type': 'string'}), extra_fields=_array({'type': 'string'}),
        native_auxiliary_measurements=_array(_ref('AuxiliaryMeasurement')),
        native_auxiliary_absent_fields={'type': 'array', 'items': {'enum': list(AUXILIARY_FIELDS)}, 'uniqueItems': True},
        pwm_rows=_array(_ref('PwmRow')), issues=_array(_TEXT)))
    d['Observation'] = _object(dict(occurrence_id=_TEXT, ordinal_0based=_INT,
        location=_ref('Location'), raw_fields=_array({'type': 'string'}),
        parse_state={'enum': ['complete', 'qualified', 'malformed', 'truncated']},
        name=_nullable({'type': 'string'}), consensus=_nullable({'type': 'string'}),
        pwm_state={'enum': ['provided', 'not_provided', 'partial', 'conflict']},
        representations=_array(_ref('Representation')), issues=_array(_TEXT)))
    d['Series'] = _object(dict(series_id=_TEXT, file_id=_TEXT,
        role={'enum': ['known_results', 'denovo_pwm', 'denovo_combined_pwm', 'denovo_nonredundant_pwm']},
        phase={'const': 'final_saved_output'}, capture_state={'enum': ['complete', 'truncated', 'missing']},
        native_outcome={'enum': list(OUTCOMES)}, raw_header=_array({'type': 'string'}),
        displayed_totals=_object(dict(target=_nullable(_ref('NativeNumber')),
            background=_nullable(_ref('NativeNumber')),
            meaning={'const': 'wrapper_inferred_from_first_rounded_motif'})),
        observations=_array(_ref('Observation')), issues=_array(_TEXT)))
    d['Sidecar'] = _object(dict(file_id=_TEXT, native_ordinal_0based=_nullable(_INT),
        linked_series_id=_nullable(_TEXT), linked_ordinal_0based=_nullable(_INT),
        state={'enum': ['linked', 'unlinked', 'ambiguous', 'conflict']},
        observations=_array(_ref('Observation')), issues=_array(_TEXT)))
    d['PopulationRow'] = _object(dict(ordinal_0based=_INT, member_id=_nullable({'type': 'string'}),
        raw_fields=_array({'type': 'string'}), location=_ref('Location'),
        state={'enum': ['complete', 'malformed', 'truncated']},
        length_bp=_nullable(_INT), group=_nullable({'enum': ['target', 'background']}),
        weight=_nullable(_ref('NativeNumber')), issues=_array(_TEXT)))
    d['Membership'] = _object(dict(member_id=_TEXT, sequence_ordinals=_array(_INT), group_ordinals=_array(_INT),
        group=_nullable({'enum': ['target', 'background']}),
        state={'enum': ['unique', 'missing', 'ambiguous', 'invalid']}))
    d['Populations'] = _object(dict(state={'enum': ['complete', 'partial', 'unavailable']},
        sequence_file_ids=_array(_TEXT), group_file_ids=_array(_TEXT),
        sequence_rows=_array(_ref('PopulationRow')), group_rows=_array(_ref('PopulationRow')),
        memberships=_array(_ref('Membership')), issues=_array(_TEXT)))
    d['AuxiliaryRow'] = _object(dict(file_id=_TEXT, ordinal_0based=_INT,
        phase={'enum': ['native_diagnostic', 'native_normalization_report_unspecified']},
        raw_fields=_array({'type': 'string'}), raw_hex=_nullable({'type': 'string'}),
        location=_ref('Location'), complete={'type': 'boolean'}))
    d['Sheet'] = _object(dict(version={'const': SHEET_VERSION}, invocation=_ref('Invocation'),
        execution=_ref('Execution'), files=_array(_ref('File')), series=_array(_ref('Series')),
        sidecars=_array(_ref('Sidecar')), populations=_ref('Populations'),
        auxiliary_rows=_array(_ref('AuxiliaryRow')), issues=_array(_TEXT)))
    d['Count'] = _object(dict(series_id=_TEXT, role=_TEXT, captured_occurrences=_INT,
        selected_occurrences=_INT, capture_state={'enum': ['complete', 'truncated', 'missing']},
        native_outcome={'enum': list(OUTCOMES)}))
    d['PopulationFacts'] = _object(dict(state={'enum': ['complete', 'partial', 'unavailable']},
        selected_window_bp=_nullable({'type': 'integer', 'minimum': 1}),
        captured_sequence_occurrences=_INT, captured_group_occurrences=_INT,
        unique_joined_target_members=_INT, unique_joined_background_members=_INT,
        observed_sequence_lengths_bp=_array(_INT),
        reported_weight_completeness=_object({group: {'enum': ['complete', 'unavailable']}
            for group in ('target', 'background')}),
        meaning={'const': 'captured_input_occurrences_not_effective_native_denominators'}))
    d['WeightSum'] = _object(dict(group={'enum': ['target', 'background']},
        meaning={'const': 'reported_input_weight_sum'}, basis={'const': 'derived_from_reported_weights'},
        cell=_ref('NumericCell'), issues=_array(_TEXT)))
    d['SeriesMetadata'] = _object(dict(series_id=_TEXT,
        role=deepcopy(d['Series']['properties']['role']),
        requested_motif_length_bp=_nullable({'type': 'integer', 'minimum': 1,
            'description': 'Caller-selected length in bp identified by the native per-length output filename; not observed PWM length. Null for other or unclassified representations.'}),
        capture_state=deepcopy(d['Series']['properties']['capture_state']),
        native_outcome=deepcopy(d['Series']['properties']['native_outcome'])))
    d['SeriesCatalog'] = {**_array(_ref('SeriesMetadata')),
        'description': 'All series actually represented in the retained sheet, in stored order, including missing or truncated captures. Their IDs remain available for later saved-data selection.'}
    d['Components'] = _object(dict(version={'const': COMPONENTS_VERSION}, selector=_ref('Selector'),
        available_series=_ref('SeriesCatalog'),
        execution=_ref('Execution'), selected_series=_array(_ref('Series')), counts=_array(_ref('Count')),
        population_facts=_ref('PopulationFacts'), reported_input_weight_sums=_array(_ref('WeightSum')),
        issues=_array(_TEXT)))
    # Public projection has no raw-file references, hashes, locations or invocation controls.
    for name in ('NativeNumber', 'ReportedNumber', 'PwmRow', 'AuxiliaryMeasurement', 'Representation', 'Observation', 'Series',
            'NumericCell', 'WeightSum'):
        public = deepcopy(d[name])
        def project(node):
            if type(node) is dict:
                if '$ref' in node and node['$ref'].split('/')[-1] in (
                        'NativeNumber', 'ReportedNumber', 'PwmRow', 'AuxiliaryMeasurement', 'Representation', 'Observation', 'NumericCell'):
                    node['$ref'] = '#/$defs/Public' + node['$ref'].split('/')[-1]
                if node.get('type') == 'object':
                    for key in ('source_location', 'location', 'file_id', 'evidence', 'requirement_ids'):
                        node.get('properties', {}).pop(key, None)
                        if key in node.get('required', []): node['required'].remove(key)
                for child in node.values(): project(child)
            elif type(node) is list:
                for child in node: project(child)
        project(public)
        d['Public' + name] = public
    d['Return'] = _object(dict(version={'const': RETURN_VERSION}, source_ref=_SOURCE,
        selector=_ref('Selector'), execution=_ref('Execution'),
        available_series=_ref('SeriesCatalog'),
        selected_series=_array(_ref('PublicSeries')), counts=_array(_ref('Count')),
        population_facts=_ref('PopulationFacts'), reported_input_weight_sums=_array(_ref('PublicWeightSum')),
        issues=_array(_TEXT)))
    return d


def homer_record_schema(kind):
    definitions = _definitions()
    require(kind in ('Sheet', 'Selector', 'Components', 'Return', 'Invocation', 'Execution', 'File'), 'schema_kind_invalid')
    pending, reachable = [kind], {}
    while pending:
        name = pending.pop()
        if name in reachable: continue
        reachable[name] = deepcopy(definitions[name])
        def refs(node):
            if type(node) is dict:
                if '$ref' in node: yield node['$ref'].removeprefix('#/$defs/')
                for child in node.values(): yield from refs(child)
            elif type(node) is list:
                for child in node: yield from refs(child)
        pending.extend(refs(reachable[name]))
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$ref': '#/$defs/' + kind, '$defs': reachable}


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
            elif keys == {'value', 'state', 'unit', 'origin', 'numerator', 'denominator',
                    'population_id', 'method_id', 'evidence', 'uncertainty', 'requirement_ids'}:
                validate_numeric_cell(node)
            elif keys == {'artifact', 'byte_start_0based', 'byte_end_0based_exclusive',
                    'line_start_1based', 'line_end_1based_inclusive', 'xml_path'}:
                locations.location(node)
            elif keys == {'availability', 'number', 'unit', 'precision'}:
                require((node['availability'] == 'provided') == (node['number'] is not None), 'number_availability_conflict')
                require((node['availability'] == 'not_provided') == (node['precision'] == 'not_provided'), 'number_precision_conflict')
            reference_record = keys in ({'raw_artifact_ref', 'source_ref', 'sha256'},
                {'raw_artifact_ref', 'source_ref', 'sha256', 'size_bytes'},
                {'source_ref', 'artifact_field', 'artifact_ref', 'sha256', 'byte_count'}) or node.get('version') == RETURN_VERSION
            for key, child in node.items():
                if reference_record and key in ('source_ref', 'raw_artifact_ref', 'artifact_ref') and child is not None:
                    pattern = r'source_[0-9a-f]{24,64}' if key == 'source_ref' else r'artifact_[0-9a-f]{64}'
                    require(re.fullmatch(pattern, child) is not None, 'reference_invalid')
                semantics(child)
        elif type(node) is list:
            for child in node: semantics(child)
    semantics(value)
    if kind in ('Components', 'Return'):
        series, counts = value['selected_series'], value['counts']
        catalog = {item['series_id']: item for item in value['available_series']}
        require(len(catalog) == len(value['available_series']), 'series_catalog_identity_conflict')
        require(all(item['requested_motif_length_bp'] is None or item['role'] == 'denovo_pwm'
            for item in catalog.values()), 'series_catalog_length_conflict')
        require([s['series_id'] for s in series] == value['selector']['series_ids']
            and len(series) == len(counts), 'selected_series_count_conflict')
        require(sum(len(s['observations']) for s in series) <= value['selector']['limit'], 'selected_window_conflict')
        for item, count in zip(series, counts):
            metadata = catalog.get(item['series_id'])
            require(metadata is not None and all(metadata[key] == item[key]
                for key in ('role', 'capture_state', 'native_outcome')), 'series_catalog_selection_conflict')
            require(count['series_id'] == item['series_id'] and count['role'] == item['role']
                and count['capture_state'] == item['capture_state'] and count['native_outcome'] == item['native_outcome']
                and count['selected_occurrences'] == len(item['observations'])
                and count['captured_occurrences'] >= count['selected_occurrences'], 'selected_series_count_conflict')
        require([s['group'] for s in value['reported_input_weight_sums']] == ['target', 'background'], 'weight_sum_groups_invalid')
        for summary in value['reported_input_weight_sums']:
            cell = summary['cell']
            require(cell['unit'] == 'relative_weight' and cell['origin'] == 'calculated'
                and cell['method_id'] == 'homer_reported_input_weight_fsum_v1', 'weight_sum_meaning_conflict')
            require(cell['state'] != 'available' or value['population_facts']['reported_weight_completeness'][summary['group']] == 'complete',
                'weight_sum_population_conflict')
            if kind == 'Return':
                validate_numeric_cell(dict(cell, evidence=[], requirement_ids=[]))
    return deepcopy(value)


def validate_homer_selector(selector):
    return validated('Selector', selector)


def validate_homer_sheet(sheet):
    sheet = validated('Sheet', sheet)
    files = sheet['files']
    require(len({f['native_relative_path'] for f in files}) == len(files), 'duplicate_file_path')
    by_id = {f['file_id']: f for f in files}
    require(len(by_id) == len(files), 'duplicate_file_identity')
    for file in files:
        native_path(file['native_relative_path'])
        require(file['file_id'] == identity('homer_file', [file['role'], file['native_relative_path'], file['artifact']]),
            'file_identity_conflict')
        extent, artifact = file['capture'], file['artifact']
        require(type(extent['byte_start_0based']) is int and extent['byte_start_0based'] == 0, 'prefix_capture_required')
        if extent['state'] == 'missing':
            require(artifact is None and extent['byte_end_0based_exclusive'] == 0, 'missing_capture_conflict')
        else:
            require(artifact is not None and artifact['size_bytes'] == extent['byte_end_0based_exclusive'], 'capture_size_conflict')
            total = extent['original_size_bytes']
            require(total is None or total >= artifact['size_bytes'], 'capture_size_conflict')
            require(extent['state'] != 'complete' or total == artifact['size_bytes'], 'capture_size_conflict')
            require(extent['state'] != 'truncated' or total is None or total > artifact['size_bytes'], 'capture_size_conflict')
    def check_location(location, file=None):
        candidates = [file] if file is not None else files
        require(any(f['artifact'] is not None and location['artifact'] == {
            key: f['artifact'][key] for key in ('raw_artifact_ref', 'source_ref', 'sha256')}
            and location['byte_start_0based'] is not None
            and location['byte_end_0based_exclusive'] <= f['artifact']['size_bytes'] for f in candidates),
            'source_location_file_conflict')
    def check_observation(row, file):
        check_location(row['location'], file)
        for rep in row['representations']:
            check_location(rep['location'])
            tokens = representation_tokens(rep['kind'], rep['raw_fields'])
            if row['parse_state'] in ('complete', 'qualified') and len(rep['raw_fields']) >= 2:
                expected = rep['raw_fields'][:2] if rep['kind'] == 'known_table' else rep['raw_fields'][1::-1]
                require([row['name'], row['consensus']] == expected, 'native_motif_identity_conflict')
            for field, value in rep['numbers'].items():
                require(value['unit'] == NUMBER_FIELDS[field], 'native_number_unit_conflict')
                if value['number'] is not None:
                    n = value['number']
                    require(n == field_number(field, n['raw_token'], n['source_location']), 'native_number_field_conflict')
                    require(tokens.get(field) == n['raw_token'], 'native_number_raw_field_conflict')
                    require(value['precision'] == native_precision(n['raw_token'], expected_precision(rep['kind'], field)),
                        'native_number_precision_conflict')
                    check_location(n['source_location'])
                    require(n['source_location']['artifact'] == rep['location']['artifact']
                        and rep['location']['byte_start_0based'] <= n['source_location']['byte_start_0based']
                        <= n['source_location']['byte_end_0based_exclusive'] <= rep['location']['byte_end_0based_exclusive'],
                        'native_number_representation_location_conflict')
                elif row['parse_state'] in ('complete', 'qualified'):
                    require(field not in tokens, 'native_number_not_provided_conflict')
            if rep['kind'] == 'native_pwm':
                require(rep['numbers']['q_value']['availability'] == 'not_provided', 'pwm_q_not_provided')
            else:
                require(rep['numbers']['site_threshold']['availability'] == 'not_provided', 'table_threshold_not_provided')
            present_auxiliary = []
            for auxiliary in rep['native_auxiliary_measurements']:
                field, reported = auxiliary['field'], auxiliary['reported']
                metadata = AUXILIARY_FIELDS[field]
                require(all(auxiliary[key] == value for key, value in metadata.items() if key != 'unit'),
                    'auxiliary_meaning_conflict')
                require(reported['availability'] == 'provided' and reported['number'] is not None
                    and reported['unit'] == metadata['unit'], 'auxiliary_number_conflict')
                number = reported['number']
                expected_precision_value = 'fixed_2' if field == 'Multiplicity' else 'fixed_1'
                require(auxiliary['raw_field'] == field + ':' + number['raw_token']
                    and number == auxiliary_number(field, number['raw_token'], number['source_location'])
                    and reported['precision'] == native_precision(number['raw_token'], expected_precision_value),
                    'auxiliary_number_conflict')
                extra, token = auxiliary['extra_field_ordinal_0based'], auxiliary['token_ordinal_0based']
                require(extra < len(rep['extra_fields']) and token < len(rep['extra_fields'][extra].split(','))
                    and rep['extra_fields'][extra].split(',')[token] == auxiliary['raw_field'], 'auxiliary_raw_field_conflict')
                check_location(number['source_location'])
                require(number['source_location']['artifact'] == rep['location']['artifact']
                    and rep['location']['byte_start_0based'] <= number['source_location']['byte_start_0based']
                    <= number['source_location']['byte_end_0based_exclusive'] <= rep['location']['byte_end_0based_exclusive'],
                    'auxiliary_representation_location_conflict')
                present_auxiliary.append(field)
            require(rep['native_auxiliary_absent_fields'] == [field for field in AUXILIARY_FIELDS
                if field not in present_auxiliary], 'auxiliary_absence_conflict')
            for ordinal, pwm in enumerate(rep['pwm_rows']):
                check_location(pwm['location'])
                require(pwm['ordinal_0based'] == ordinal and pwm['location']['artifact'] == rep['location']['artifact']
                    and rep['location']['byte_start_0based'] <= pwm['location']['byte_start_0based']
                    <= pwm['location']['byte_end_0based_exclusive'] <= rep['location']['byte_end_0based_exclusive'],
                    'pwm_row_location_conflict')
                require(not pwm['cells'] or len(pwm['cells']) == len(pwm['raw_fields']), 'pwm_cell_count_conflict')
                for token, number in zip(pwm['raw_fields'], pwm['cells']):
                    require(number == native_number(token, source_location=pwm['location'], minimum=0, maximum=1),
                        'pwm_cell_conflict')
            if rep['kind'] == 'native_pwm' and row['pwm_state'] == 'provided':
                require(row['consensus'] is not None and len(rep['pwm_rows']) == len(row['consensus'])
                    and all(len(p['raw_fields']) == len(p['cells']) == 4 for p in rep['pwm_rows']),
                    'pwm_matrix_extent_conflict')
    series_ids = [s['series_id'] for s in sheet['series']]
    require(len(set(series_ids)) == len(series_ids), 'duplicate_series_identity')
    for series in sheet['series']:
        require(series['file_id'] in by_id and by_id[series['file_id']]['role'] == series['role'], 'series_file_conflict')
        require(series['series_id'] == identity('homer_series', series['file_id']), 'series_identity_conflict')
        require(series['capture_state'] == by_id[series['file_id']]['capture']['state']
            and series['native_outcome'] == sheet['execution'][
                'known_outcome' if series['role'] == 'known_results' else 'denovo_outcome'], 'series_state_conflict')
        if series['role'] == 'known_results':
            header = series['raw_header']
            for group, column, title in (('target', 5, 'Target'), ('background', 7, 'Background')):
                number = series['displayed_totals'][group]
                if number is not None:
                    require(len(header) == 9, 'displayed_total_conflict')
                    match = re.fullmatch(r'# of ' + title + r' Sequences with Motif\(of ([0-9]+)\)', header[column])
                    require(match is not None and number == native_number(match[1],
                        source_location=number['source_location'], integer=True, minimum=0), 'displayed_total_conflict')
                    check_location(number['source_location'], by_id[series['file_id']])
        previous = -1
        for row in series['observations']:
            require(row['ordinal_0based'] > previous, 'observation_order_conflict')
            previous = row['ordinal_0based']
            require(row['occurrence_id'] == identity('homer_occurrence', [series['file_id'], previous]), 'occurrence_identity_conflict')
            check_observation(row, by_id[series['file_id']])
    for sidecar in sheet['sidecars']:
        require(sidecar['file_id'] in by_id and by_id[sidecar['file_id']]['role'] == 'known_pwm', 'sidecar_file_conflict')
        require(sidecar['native_ordinal_0based'] == known_pwm_ordinal(by_id[sidecar['file_id']]['native_relative_path']),
            'sidecar_ordinal_conflict')
        for row in sidecar['observations']:
            require(row['occurrence_id'] == identity('homer_occurrence', [sidecar['file_id'], row['ordinal_0based']]),
                'occurrence_identity_conflict')
            check_observation(row, by_id[sidecar['file_id']])
        if sidecar['state'] == 'linked':
            targets = [r for s in sheet['series'] if s['series_id'] == sidecar['linked_series_id']
                and s['role'] == 'known_results' for r in s['observations']
                if r['ordinal_0based'] == sidecar['linked_ordinal_0based']]
            require(sidecar['native_ordinal_0based'] == sidecar['linked_ordinal_0based']
                and len(targets) == len(sidecar['observations']) == 1, 'sidecar_link_conflict')
            source, target = sidecar['observations'][0], targets[0]
            require(sum(s['native_ordinal_0based'] == sidecar['native_ordinal_0based'] for s in sheet['sidecars']) == 1
                and sidecar_matches(source, target)
                and all(r in target['representations'] for r in source['representations']), 'sidecar_link_conflict')
        else:
            require(sidecar['linked_series_id'] is None and sidecar['linked_ordinal_0based'] is None, 'sidecar_link_conflict')
    for series in sheet['series']:
        if series['role'] == 'known_results':
            for row in series['observations']:
                linked = [rep for s in sheet['sidecars'] if s['state'] == 'linked'
                    and s['linked_series_id'] == series['series_id'] and s['linked_ordinal_0based'] == row['ordinal_0based']
                    for observation in s['observations'] for rep in observation['representations']]
                require(len(row['representations']) >= 1 and row['representations'][0]['kind'] == 'known_table'
                    and row['representations'][1:] == linked, 'known_representation_link_conflict')
    population = sheet['populations']
    for role, key in (('sequence_table', 'sequence_file_ids'), ('group_weights', 'group_file_ids')):
        require(population[key] == [f['file_id'] for f in files if f['role'] == role], 'population_file_conflict')
    for key, role in (('sequence_rows', 'sequence_table'), ('group_rows', 'group_weights')):
        for row in population[key]:
            candidates = [by_id[f] for f in population['sequence_file_ids' if role == 'sequence_table' else 'group_file_ids']]
            require(any(row['location']['artifact'] == {k: f['artifact'][k]
                for k in ('raw_artifact_ref', 'source_ref', 'sha256')} for f in candidates if f['artifact']),
                'population_row_file_conflict')
            check_location(row['location'])
            require(bool(row['raw_fields']) and row['member_id'] == (row['raw_fields'][0] or None), 'population_member_conflict')
            require(row['location']['line_start_1based'] == row['ordinal_0based'] + 1, 'population_ordinal_conflict')
            if row['state'] == 'complete':
                require(len(row['raw_fields']) >= 2, 'population_row_conflict')
                if role == 'sequence_table':
                    require(row['length_bp'] == len(row['raw_fields'][1]) and row['group'] is None and row['weight'] is None,
                        'sequence_row_conflict')
                elif row['weight'] is not None:
                    require(len(row['raw_fields']) >= 3 and row['weight'] == native_number(row['raw_fields'][2],
                        source_location=row['location'], minimum=0), 'group_weight_conflict')
                if role == 'group_weights':
                    token = row['raw_fields'][1]
                    group = native_group(token)
                    require(row['group'] == group, 'group_code_conflict')
                    require(row['weight'] is not None or bool(row['issues']), 'missing_reported_weight_conflict')
    expected = population_memberships(population['sequence_rows'], population['group_rows'])
    require(population['memberships'] == expected, 'population_membership_conflict')
    require(population['state'] == population_state(files, population['sequence_file_ids'], population['group_file_ids'],
        population['sequence_rows'], population['group_rows'], expected), 'population_state_conflict')
    for row in sheet['auxiliary_rows']:
        require(row['file_id'] in by_id, 'auxiliary_file_conflict')
        check_location(row['location'], by_id[row['file_id']])
    return sheet


__all__ = ['SHEET_VERSION', 'COMPONENTS_VERSION', 'RETURN_VERSION', 'OPERATION',
    'ROLES', 'OUTCOMES', 'NUMBER_FIELDS', 'homer_record_schema',
    'validate_homer_sheet', 'validate_homer_selector']
