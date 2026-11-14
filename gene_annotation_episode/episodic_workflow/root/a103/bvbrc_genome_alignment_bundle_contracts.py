"""Closed GenomeAlignment bundle parameters and requested numerical facts.

These schemas select stored measurements. They are neither a scoring language
nor an acquisition recipe. Native plan validators retain their own meanings.
"""
from copy import deepcopy
import json
from urllib.parse import quote, unquote

from .bvbrc_appservice_contracts import (
    ContractValidationError, _finite_json, _same, _Validator, contract_schema,
)
from .bvbrc_genome_alignment_calculation_contracts import validate_genome_alignment_calculation_plan

PREFIX = 'bvbrc_genome_alignment_bundle_'
REFERENCE_KINDS = ('field', 'request', 'document', 'population', 'method', 'file',
    'record', 'member', 'transformation', 'role', 'requirement', 'reason', 'qualification')
KINDS = ('mauve_v4_segments', 'mauve_backbone', 'mauve_bbcols', 'xmfa_alignment',
         'xmfa_coverage', 'xmfa_coordinates', 'xmfa_inverse_coordinates')


def _require(condition, code):
    if not condition:
        raise ValueError(PREFIX + code)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def _obj(**properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def _arr(items, *, unique=False):
    result = {'type': 'array', 'items': items}
    if unique:
        result['uniqueItems'] = True
    return result


def _enum(*values):
    return {'enum': list(values)}


def _null(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


TEXT = {'type': 'string', 'minLength': 1}
UINT = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
NUMBER = {'type': 'number'}
BOOL = {'type': 'boolean'}
INTERVAL = {'type': 'array', 'prefixItems': [UINT, UINT], 'items': False, 'minItems': 2, 'maxItems': 2}
CELL = _obj(block_index=UINT, record_index=UINT, column_0based=UINT)
QUERY = _obj(member_number=POSITIVE, position_0based=UINT)
OCCURRENCE = _obj(input_binding_id=TEXT, member_id=TEXT, occurrence_index=UINT)
MEMBER = {'oneOf': [_obj(namespace={'const': namespace}, index=minimum) for namespace, minimum in (
    ('mauve1_member_1based', POSITIVE), ('mauve_v4_member_0based', UINT), ('mauve_sidecar_member_0based', UINT))]}
PAIR = _obj(member_a=MEMBER, member_b=MEMBER)
STATE = _enum('available', 'missing', 'not_measured', 'failed', 'truncated', 'incompatible')
SYMBOL = {'type': 'string', 'pattern': '^[ACGTRYSWKMBDHVNacgtryswkmbdhvn-]$', 'format': 'alignment_symbol'}
STRAND = {'type': 'string', 'enum': ['+', '-'], 'format': 'alignment_strand'}
COMPLETENESS = _enum('complete', 'partial', 'truncated', 'unknown')


def _inline_contract(name):
    schema = contract_schema(name)
    def expand(node):
        if type(node) is dict:
            if '$ref' in node:
                return expand(schema['$defs'][node['$ref'].split('/')[-1]])
            return {k: expand(v) for k, v in node.items()}
        if type(node) is list:
            return [expand(v) for v in node]
        return node
    return expand(schema['$defs'][name])


EVIDENCE = _inline_contract('SourceEvidence')


def _member_schema(namespace):
    return _obj(namespace={'const': namespace}, index=POSITIVE if namespace == 'mauve1_member_1based' else UINT)


def _selection_schemas():
    v4 = _member_schema('mauve_v4_member_0based')
    side = _member_schema('mauve_sidecar_member_0based')
    base = {'population_id': TEXT, 'evidence': _arr(EVIDENCE)}
    v4_selection = _obj(schema_version={'const': 'mauve_v4_selection_v1'}, **base,
        members=_arr(v4, unique=True), segments=_arr(_obj(interval_index=UINT, segment_index=UINT,
            column_ranges_0based_half_open=_arr(INTERVAL))), pairs=_arr(_obj(member_a=v4, member_b=v4)),
        case_policy=_enum('preserve', 'uppercase'), denominator=_enum('none', 'native_declared_length', 'validated_staged_length'),
        population_scope=_enum('selected_segments', 'all_observed_document_segments'))
    backbone = _obj(schema_version={'const': 'mauve_backbone_selection_v1'}, **base,
        members=_arr(side, unique=True), row_indices=_arr(UINT, unique=True), minimum_selected_multiplicity=POSITIVE,
        denominator=_enum('none', 'validated_staged_length'), population_scope=_enum('selected_rows', 'all_observed_document_rows'))
    bbcols = _obj(schema_version={'const': 'mauve_bbcols_selection_v1'}, **base,
        members=_arr(side, unique=True), row_indices=_arr(UINT, unique=True), minimum_selected_multiplicity=POSITIVE,
        calculate_bound_block_fraction=BOOL, population_scope=_enum('selected_rows', 'all_observed_document_rows'))
    xmfa = _obj(**base, member_numbers=_arr(POSITIVE, unique=True),
        block_columns=_arr(_obj(block_index=UINT, columns_0based=_arr(UINT, unique=True))), completeness=COMPLETENESS)
    return v4_selection, backbone, bbcols, xmfa


def parameters_schema() -> dict:
    """Return the complete Draft202012 schema; native validators add relations."""
    readers = [_obj(format={'const': 'mauve_v4'}, encoding=_enum('ascii', 'utf-8')),
        _obj(format={'const': 'mauve1_xmfa'}, dialect={'const': 'mauve1'}, alphabet={'const': 'dna'}, encoding=_enum('ascii', 'utf-8')),
        *[_obj(format={'const': fmt}, dialect={'const': dialect}, encoding=_enum('ascii', 'utf-8')) for fmt, dialect in (
            ('mauve_backbone', 'libmems_signed_coordinate_pairs_v1'), ('mauve_bbcols', 'libmems_interval_columns_members_v1'))]]
    slots = {'oneOf': [_obj(slot_id=TEXT, role={'const': role}, source_ref=_null(TEXT), raw_artifact_ref=_null(TEXT), reader=reader)
        for role, reader in [('genome_alignment_primary', {'oneOf': readers[:2]}),
                             ('genome_alignment_backbone', readers[2]), ('genome_alignment_bbcols', readers[3])]]}
    v4, backbone, bbcols, xmfa = _selection_schemas()
    tails = [dict(selection=v4, use_inputs=BOOL), dict(selection=backbone, use_inputs=BOOL),
        dict(selection=bbcols, xmfa_document_slot_id=_null(TEXT)),
        dict(selection=xmfa, selected_pairs=_arr({'type': 'array', 'prefixItems': [POSITIVE, POSITIVE],
            'items': False, 'minItems': 2, 'maxItems': 2}), case_policy=_enum('preserve', 'uppercase')),
        dict(selection=xmfa, basis=_enum('represented', 'multi_member_block', 'cooccupied_column'), use_source_bindings=BOOL),
        dict(cells=_arr(CELL, unique=True), use_source_bindings=BOOL),
        dict(queries=_arr(QUERY, unique=True), use_source_bindings=BOOL)]
    requests = {'oneOf': [_obj(request_id=TEXT, kind={'const': kind}, document_slot_id=TEXT, **tail)
                         for kind, tail in zip(KINDS, tails)]}
    return deepcopy({'$schema': 'https://json-schema.org/draft/2020-12/schema', **_obj(
        schema_version={'const': 'bvbrc_genome_alignment_parameters_v1'}, analysis_id=TEXT,
        document_slots=_arr(slots), calculation_plan=_obj(schema_version={'const': 'bvbrc_genome_alignment_calculation_plan_v1'},
                                                        requests=_arr(requests)))})


def _validate(schema, value, code):
    try:
        _finite_json(value)
    except ContractValidationError as error:
        raise ValueError(PREFIX + code) from error
    _require(_Validator(schema).is_valid(value), code)


def validate_parameters(parameters: dict) -> dict:
    _validate(parameters_schema(), parameters, 'parameters_invalid')
    validate_genome_alignment_calculation_plan(parameters['calculation_plan'], document_slots=tuple(parameters['document_slots']))
    return deepcopy(parameters)


PAIR_FIELDS = ('identical_canonical', 'substitutions', 'a_only_gap', 'b_only_gap', 'both_gap',
               'ambiguous_or_other', 'comparable_canonical', 'identity_fraction')
COVERAGE_FIELDS = ('known_union_bases', 'placement_bases', 'multiply_represented_bases', 'excess_placement_bases',
                   'denominator_bases', 'coverage_fraction', 'complement_bases')
# family -> (request kind, exact location keys, exact saved numerical fields)
NUMERIC_CATALOG = {
    'v4_member': ('mauve_v4_segments', dict(interval_index=UINT, segment_index=UINT, member=MEMBER),
        ('alignment_columns', 'selected_column_count', 'selected_nongap_count', 'selected_gap_count',
         'selected_canonical_count', 'selected_ambiguity_count', 'selected_other_count')),
    'v4_pair': ('mauve_v4_segments', dict(interval_index=UINT, segment_index=UINT, pair=PAIR), PAIR_FIELDS),
    'v4_coverage': ('mauve_v4_segments', dict(member=MEMBER), COVERAGE_FIELDS),
    'backbone_row': ('mauve_backbone', dict(row_index=UINT), ('selected_member_count',)),
    'backbone_span': ('mauve_backbone', dict(row_index=UINT, member=MEMBER), ('span_bases',)),
    'backbone_coverage': ('mauve_backbone', dict(member=MEMBER), COVERAGE_FIELDS),
    'bbcols_row': ('mauve_bbcols', dict(row_index=UINT), ('selected_member_count', 'column_count')),
    'bbcols_interval': ('mauve_bbcols', dict(native_interval_index_0based=UINT),
        ('union_columns', 'column_placements', 'multiply_represented_columns', 'excess_column_placements',
         'bound_block_width', 'selected_block_fraction')),
    'xmfa_block': ('xmfa_alignment', dict(block_index=UINT),
        ('selected_column_count', 'present_member_count', 'zero_member_count', 'omitted_member_count')),
    'xmfa_site': ('xmfa_alignment', dict(block_index=UINT, column_0based=UINT),
        ('present_member_count', 'absent_member_count', 'gap_count', 'nongap_count', 'canonical_count',
         'ambiguity_count', 'other_count', 'literal_entropy_bits', 'canonical_entropy_bits', 'canonical_majority_fraction')),
    'xmfa_symbol': ('xmfa_alignment', dict(block_index=UINT, column_0based=UINT, symbol=SYMBOL), ('count',)),
    'xmfa_pair': ('xmfa_alignment', dict(block_index=UINT, member_a=POSITIVE, member_b=POSITIVE), PAIR_FIELDS),
    'xmfa_coverage': ('xmfa_coverage', dict(member_number=POSITIVE),
        ('source_length', 'known_union_bases', 'placement_bases', 'multiply_represented_bases',
         'excess_placement_bases', 'selected_coverage_fraction', 'complement_bases')),
    'xmfa_original_coverage': ('xmfa_coverage', dict(member_number=POSITIVE, original_member=OCCURRENCE),
        ('original_length', 'known_union_bases', 'coverage_fraction')),
}
NUMERIC_LOCATOR = {'oneOf': [_obj(family={'const': family}, **keys, field=_enum(*fields))
    for family, (_, keys, fields) in NUMERIC_CATALOG.items()]}
SELECTORS = {
    'measurement': _obj(kind={'const': 'measurement'}, request_id=TEXT, metric=NUMERIC_LOCATOR),
    'v4_segment': _obj(kind={'const': 'v4_segment'}, request_id=TEXT, interval_index=UINT, segment_index=UINT, member=MEMBER),
    'backbone_span': _obj(kind={'const': 'backbone_span'}, request_id=TEXT, row_index=UINT, member=MEMBER),
    'bbcols_interval': _obj(kind={'const': 'bbcols_interval'}, request_id=TEXT, native_interval_index_0based=UINT),
    'coverage_intervals': _obj(kind={'const': 'coverage_intervals'}, request_id=TEXT, member=MEMBER, part=_enum('union', 'complement')),
    **{k: _obj(kind={'const': k}, request_id=TEXT, cell=CELL) for k in
       ('xmfa_native_coordinate', 'xmfa_source_coordinate', 'xmfa_original_coordinates')},
    'xmfa_inverse_coordinates': _obj(kind={'const': 'xmfa_inverse_coordinates'}, request_id=TEXT, query=QUERY),
    'request_status': _obj(kind={'const': 'request_status'}, request_id=TEXT),
    **{k: {'oneOf': [_obj(kind={'const': k}, scope={'const': 'all'}, request_id={'type': 'null'}),
                    _obj(kind={'const': k}, scope={'const': 'request'}, request_id=TEXT)]}
       for k in ('missing_requirements', 'qualifications')},
}


def validate_projection_selector(selection: dict) -> dict:
    _validate({'oneOf': list(SELECTORS.values())}, selection, 'selector_invalid')
    # A tagged v4 pair has the native canonical ordering, not a reversed alias.
    metric = selection.get('metric', {})
    if metric.get('family') == 'v4_pair':
        a, b = metric['pair']['member_a'], metric['pair']['member_b']
        _require((a['namespace'], a['index']) < (b['namespace'], b['index']), 'selector_invalid')
    if metric.get('family') == 'xmfa_pair':
        _require(metric['member_a'] != metric['member_b'], 'selector_invalid')
    return deepcopy(selection)


def encode_reference(kind: str, analysis_id: str, identity: str) -> str:
    _require(type(kind) is str and kind in REFERENCE_KINDS, 'reference_kind_unknown')
    _require(type(analysis_id) is str and bool(analysis_id) and type(identity) is str and bool(identity), 'reference_invalid')
    try:
        return 'bvbrc_genome_alignment_' + kind + ':' + quote(analysis_id, safe='') + '/' + quote(identity, safe='')
    except UnicodeError as error:
        raise ValueError(PREFIX + 'reference_invalid') from error


def decode_reference(reference: str) -> tuple[str, str, str]:
    _require(type(reference) is str and reference.startswith('bvbrc_genome_alignment_'), 'reference_invalid')
    prefix, colon, rest = reference.partition(':')
    _require(bool(colon) and rest.count('/') == 1, 'reference_invalid')
    kind = prefix[len('bvbrc_genome_alignment_'):]
    _require(kind in REFERENCE_KINDS, 'reference_kind_unknown')
    try:
        analysis_id, identity = (unquote(x, errors='strict') for x in rest.split('/'))
    except UnicodeError as error:
        raise ValueError(PREFIX + 'reference_invalid') from error
    _require(encode_reference(kind, analysis_id, identity) == reference, 'reference_noncanonical')
    return kind, analysis_id, identity


def _ref(kind):
    return {'type': 'string', 'pattern': '^bvbrc_genome_alignment_' + kind + ':[^/]+/[^/]+$'}


REQ_REFS = _arr(_ref('requirement'), unique=True)
UNCERTAINTY = _obj(kind=_enum('confidence_interval', 'standard_error', 'standard_deviation', 'native_unknown'),
    lower=_null(NUMBER), upper=_null(NUMBER), value=_null(NUMBER), method_ref=_ref('method'))
MEASURE = _obj(value=_null(NUMBER), state=STATE,
    unit=_enum('bits', 'characters', 'column_placements', 'columns', 'fraction', 'members', 'nucleotide_placements', 'nucleotides'),
    origin=_enum('native_observation', 'calculated', 'fitted'), numerator=_null(NUMBER), denominator=_null(NUMBER),
    population_ref=_ref('population'), method_ref=_ref('method'), uncertainty=_null(UNCERTAINTY), requirement_refs=REQ_REFS)
MEMBER_STATE = _enum('present', 'absent_zero', 'missing', 'incompatible')
POPULATION_STATE = _enum('complete_selected', 'partial_selected', 'unknown')
GEOMETRY = {
    'v4_segment': _obj(interval_index=UINT, segment_index=UINT, member=MEMBER, state=MEMBER_STATE,
        native_start=_null(NUMBER), native_start_state=_null(STATE), native_start_token_kind=_null(_enum(
            'finite', 'blank', 'native_na', 'nonfinite', 'overflow', 'underflow', 'malformed')),
        strand=_null(STRAND), native_interval_0based_half_open=_null(INTERVAL),
        symbols_origin=_enum('native_rows', 'source_extracted', 'unavailable'), source_comparison=_enum('match', 'mismatch', 'not_checked', 'not_applicable')),
    'backbone_span': _obj(row_index=UINT, member=MEMBER, state=MEMBER_STATE, interval_0based_half_open=_null(INTERVAL),
        strand=_null(STRAND), selected_by_multiplicity=_null(BOOL)),
    'bbcols_interval': _obj(native_interval_index_0based=UINT, contributing_row_indices=_arr(UINT, unique=True),
        known_union_intervals=_arr(INTERVAL), population_state=POPULATION_STATE),
    'coverage_intervals': _obj(member=MEMBER, part=_enum('union', 'complement'), intervals=_null(_arr(INTERVAL)),
        population_state=_null(POPULATION_STATE), membership_completeness=_null(COMPLETENESS),
        basis=_null(_enum('represented', 'multi_member_block', 'cooccupied_column')),
        denominator_kind=_enum('none', 'native_declared_length', 'validated_staged_length', 'validated_xmfa_source_length')),
    'xmfa_native_coordinate': _obj(cell=CELL, member_number=_null(POSITIVE), aligned_symbol=SYMBOL,
        state=_enum('residue', 'gap', 'absent_zero', 'incompatible'), native_position_1based=_null(POSITIVE),
        native_position_0based=_null(UINT), native_strand=_null(STRAND), forward_symbol=_null(SYMBOL)),
    'xmfa_source_coordinate': _obj(cell=CELL, member_number=_null(POSITIVE), source_state=_enum('resolved', 'missing', 'conflicting', 'not_applicable'),
        source_coordinate=_null(_obj(file_ref=_ref('file'), record_ref=_ref('record'), entry_1based=POSITIVE, position_0based=UINT, strand=STRAND))),
    'xmfa_original_coordinates': _obj(cell=CELL, member_number=_null(POSITIVE), state=_enum('residue', 'gap', 'absent_zero', 'incompatible'),
        original_coordinates=_arr(_obj(member_ref=_ref('member'), position_0based=UINT, original_length=UINT,
            strand=STRAND, transformation_ref=_ref('transformation')))),
    'xmfa_inverse_coordinates': _obj(member_number=POSITIVE, position_0based=UINT,
        state=_enum('unique', 'multiple', 'none_in_document', 'unknown'), matches=_arr(CELL, unique=True), search_completeness=COMPLETENESS),
}


def _selected(schema):
    return _obj(request_ref=_ref('request'), document_ref=_null(_ref('document')),
        state=_enum('resolved', 'missing', 'incompatible'), value=_null(schema), requirement_refs=REQ_REFS)


FACT_SCHEMAS = {'measurement': _selected(MEASURE), **{k: _selected(v) for k, v in GEOMETRY.items()},
    'request_status': _obj(request_ref=_ref('request'), document_ref=_null(_ref('document')), kind=_enum(*KINDS),
        state=_enum('calculated', 'missing', 'incompatible'), measurement_status=_null(_enum('ok', 'partial', 'invalid')), requirement_refs=REQ_REFS),
    'missing_requirements': _arr(_obj(requirement_ref=_ref('requirement'), kind=_inline_contract('AcquisitionRequirement')['properties']['kind'],
        role_ref=_null(_ref('role')), source_refs=_arr(TEXT, unique=True), reason_ref=_ref('reason'))),
    'qualifications': _arr(_obj(qualification_ref=_ref('qualification'), code_ref=_ref('reason'),
        phase=_inline_contract('Diagnostic')['properties']['phase'], severity=_enum('error', 'qualification'))),
}


def requested_form_schema(fields: dict) -> dict:
    _require(type(fields) is dict and all(type(k) is str and k for k in fields), 'requested_form_invalid')
    properties = {}
    for name, selector in fields.items():
        selector = validate_projection_selector(selector)
        properties[name] = deepcopy(FACT_SCHEMAS[selector['kind']]) | {'x-genome-alignment-fact': selector}
    return _obj(**properties)


def validate_requested_form(requested_form: dict) -> dict:
    _require(type(requested_form) is dict and set(requested_form) == {'type', 'properties', 'required', 'additionalProperties'},
             'requested_form_invalid')
    properties, required = requested_form['properties'], requested_form['required']
    _require(type(properties) is dict and all(type(k) is str and k for k in properties), 'requested_form_invalid')
    _require(type(required) is list and all(type(k) is str for k in required) and len(set(required)) == len(required)
             and set(required) == set(properties), 'requested_required_conflict')
    fields = {}
    for name, schema in properties.items():
        _require(type(schema) is dict and 'x-genome-alignment-fact' in schema, 'requested_form_invalid')
        fields[name] = validate_projection_selector(schema['x-genome-alignment-fact'])
    expected = requested_form_schema(fields)
    expected['required'] = list(required)
    _require(_same(requested_form, expected), 'requested_form_noncanonical')
    return deepcopy(requested_form)


def _validate_selector_relationships(selector, request, *, document=None):
    """Check selection membership, deferring native-only keys until bytes exist."""
    kind = selector['kind']
    if kind in ('request_status', 'missing_requirements', 'qualifications'):
        return
    if kind == 'measurement':
        target = selector['metric']; family = target['family']
        expected = (NUMERIC_CATALOG[family][0],)
    else:
        target = selector; family = {'v4_segment': 'v4_member', 'backbone_span': 'backbone_span',
            'bbcols_interval': 'bbcols_interval'}.get(kind, kind)
        expected = {'v4_segment': ('mauve_v4_segments',), 'backbone_span': ('mauve_backbone',),
            'bbcols_interval': ('mauve_bbcols',), 'coverage_intervals': ('mauve_v4_segments', 'mauve_backbone', 'xmfa_coverage'),
            'xmfa_native_coordinate': ('xmfa_coordinates',), 'xmfa_source_coordinate': ('xmfa_coordinates',),
            'xmfa_original_coordinates': ('xmfa_coordinates',), 'xmfa_inverse_coordinates': ('xmfa_inverse_coordinates',)}[kind]
    _require(request['kind'] in expected, 'selector_kind_conflict')
    selection = request.get('selection', {})
    if 'member' in target:
        member = target['member']
        allowed = ([{'namespace': 'mauve1_member_1based', 'index': n} for n in selection['member_numbers']]
                   if request['kind'] == 'xmfa_coverage' else selection['members'])
        _require(member in allowed, 'selector_outside_request')
    if 'member_number' in target:
        _require(target['member_number'] in selection['member_numbers'], 'selector_outside_request')
    if family in ('v4_member', 'v4_pair'):
        _require(any(all(s[k] == target[k] for k in ('interval_index', 'segment_index')) for s in selection['segments']),
                 'selector_outside_request')
        if family == 'v4_pair':
            _require(target['pair'] in selection['pairs'], 'selector_outside_request')
    if 'row_index' in target:
        _require(target['row_index'] in selection['row_indices'], 'selector_outside_request')
    if family == 'bbcols_interval' and document is not None:
        index = target['native_interval_index_0based']
        matching = [r['row_index'] for r in document['rows'] if r['native_interval_index_0based'] is not None
            and r['native_interval_index_0based']['state'] == 'available' and r['native_interval_index_0based']['value'] == index]
        _require(not matching or bool(set(matching) & set(selection['row_indices'])), 'selector_outside_request')
    if 'block_index' in target:
        chosen = [b for b in selection['block_columns'] if b['block_index'] == target['block_index']]
        _require(len(chosen) == 1, 'selector_outside_request')
        if 'column_0based' in target:
            _require(target['column_0based'] in chosen[0]['columns_0based'], 'selector_outside_request')
        if family == 'xmfa_pair':
            _require([target['member_a'], target['member_b']] in request['selected_pairs'], 'selector_outside_request')
    if 'cell' in target:
        _require(target['cell'] in request['cells'], 'selector_outside_request')
    if 'query' in target:
        _require(target['query'] in request['queries'], 'selector_outside_request')


def _validate_selections(parameters, requested_form, *, data=None):
    requests = {r['request_id']: r for r in parameters['calculation_plan']['requests']}
    resolutions = {} if data is None else {r['slot_id']: r for r in data['slot_resolutions']}
    documents = {} if data is None else {p['document']['document_id']: p['document'] for p in data['parsed_artifacts'] if p['document'] is not None}
    for field in requested_form['properties'].values():
        selector = field['x-genome-alignment-fact']; rid = selector['request_id']
        if rid is None:
            continue
        _require(rid in requests, 'selector_request_unknown')
        request = requests[rid]; resolution = resolutions.get(request['document_slot_id'])
        document = None if resolution is None else documents.get(resolution['document_id'])
        _validate_selector_relationships(selector, request, document=document)


__all__ = ['FACT_SCHEMAS', 'REFERENCE_KINDS', 'validate_parameters', 'parameters_schema',
    'validate_projection_selector', 'requested_form_schema', 'validate_requested_form', 'encode_reference', 'decode_reference']
