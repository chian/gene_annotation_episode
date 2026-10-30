"""Compose existing A105 numerical fields without calculating a new grade.

The host first validates the original form's schemas, recorded facts and scope.
The extra checks here concern only relationships between *delivered* rows.
``read_public_record(ref)`` must return an already-possessed public record (with
its id and record_type), or None. It is not a private sheet/source accessor.
No source acquisition, numeric parsing, calculation or scientific inference is
performed by this module. Frozen native schemas remain the host's authority.
"""
from collections.abc import Mapping
from copy import deepcopy
from importlib import import_module

from jsonschema import Draft202012Validator

from .communication import CODE, plain
from .domain import ContractError, canonical, obj

VERSION = 'a105_source_evidence_worksheet_v1'
VERSION_V2 = 'a105_source_evidence_worksheet_v2'
NATIVE = 'literature_kinetic_cells'
SUMMARY = 'literature_kinetic_summary_precision_cells'

# source: (existing assignment key, schema module, factory, presentation role)
FAMILIES = {
    'literature_concentration_window_cells': ('requested_concentration_window_components',
        'literature_concentration_window_storage', 'concentration_window_cells_schema',
        'observed_concentration_window_and_product_fate'),
    NATIVE: ('requested_kinetic_components', 'literature_kinetic_storage', 'kinetic_cells_schema',
        'reported_kinetic_estimates_and_descriptive_contrasts'),
    SUMMARY: ('requested_kinetic_summary_precision_components', 'literature_kinetic_summary_precision_storage',
        'summary_precision_cells_schema', 'summary_random_precision'),
    'literature_measurement_comparison_cells': ('requested_measurement_comparison_components',
        'literature_measurement_comparison_storage', 'measurement_comparison_cells_schema',
        'measurement_comparison_validity'),
    'literature_endpoint_signal_cells': ('requested_endpoint_signal_components', 'literature_endpoint_signal_storage',
        'endpoint_signal_cells_schema', 'finite_endpoint_readout_contribution'),
    'literature_product_coupling_cells': ('requested_product_coupling_components', 'literature_product_coupling_storage',
        'product_coupling_cells_schema', 'product_reporter_stoichiometric_relationship'),
    'literature_calibration_recovery_cells': ('requested_calibration_recovery_components', 'literature_calibration_recovery_storage',
        'calibration_recovery_cells_schema', 'calibration_standard_recovery'),
    'literature_compiled_assay_v2_cells': ('requested_compiled_assay_components_v2', 'literature_compiled_assay_storage',
        'compiled_assay_v2_cells_schema', 'within_assay_measurement_equation'),
    'literature_compiled_assay_v3_cells': ('requested_compiled_assay_components_v3', 'literature_compiled_assay_storage',
        'compiled_assay_v3_cells_schema', 'functional_quantity_model_comparison'),
    'literature_channel_cells': ('requested_channel_components', 'literature_channel_storage',
        'channel_cells_schema', 'source_electrical_activity'),
    'literature_ion_discrimination_cells': ('requested_ion_discrimination_components',
        'literature_ion_discrimination_storage', 'ion_discrimination_cells_schema',
        'source_ion_discrimination'),
    'literature_parent_depletion_cells': ('requested_parent_depletion_components',
        'literature_parent_depletion_storage', 'parent_depletion_cells_schema',
        'finite_parent_compound_removal'),
    'literature_stoichiometric_balance_cells': ('requested_stoichiometric_balance_components',
        'literature_stoichiometric_balance_storage', 'stoichiometric_balance_cells_schema',
        'source_soluble_product_stoichiometric_balance'),
    'literature_completion_time_cells': ('requested_completion_time_components',
        'literature_completion_time_storage', 'completion_time_cells_schema',
        'source_preparation_completion_time'),
    'literature_product_partition_cells': ('requested_product_partition_components',
        'literature_product_partition_storage', 'product_partition_cells_schema',
        'reported_selected_product_partition'),
    'literature_assay_grading_cells': ('requested_assay_grading_components',
        'literature_assay_grading_storage', 'assay_grading_cells_schema',
        'assay_type_experimental_evidence'),
    'literature_a105_aggregation_cells': ('requested_a105_aggregation_components',
        'literature_a105_aggregation_storage', 'aggregation_cells_schema',
        'a105_across_experiment_aggregation'),
}
QUANTITY_RELATIONS = ('same_reported_parameter', 'same_reported_spread', 'same_count_report',
    'conditional_precision_of_report', 'unresolved', 'conflicting')
QUANTITY_RELATIONS_V2 = (*QUANTITY_RELATIONS, 'same_physical_measurement')
ASSERTION_RELATIONS = ('measures_asserted_endpoint', 'addresses_named_weakness',
    'does_not_establish_assertion', 'unknown', 'conflicting')
_SCOPES = {
    'literature_completion_time_cells': 'source_preparation_completion_time',
    'literature_product_partition_cells': 'reported_selected_product_partition',
    'literature_assay_grading_cells': 'assay_type_experimental_evidence',
    'literature_a105_aggregation_cells': 'a105_across_experiment_aggregation',
    'literature_concentration_window_cells': 'source_concentration_window',
    NATIVE: 'source_kinetic_parameter_contrast', SUMMARY: 'source_kinetic_summary_precision',
    'literature_measurement_comparison_cells': 'source_measurement_comparison',
    'literature_endpoint_signal_cells': 'source_endpoint_signal_contribution',
    'literature_product_coupling_cells': 'source_product_coupling',
    'literature_calibration_recovery_cells': 'source_calibration_recovery',
    'literature_compiled_assay_v2_cells': 'compiled_source_endpoint',
    'literature_compiled_assay_v3_cells': 'common_assertion_contrast',
    'literature_channel_cells': 'source_electrical_activity',
    'literature_ion_discrimination_cells': 'source_ion_discrimination',
    'literature_parent_depletion_cells':'finite_parent_compound_removal',
    'literature_stoichiometric_balance_cells':'source_soluble_product_stoichiometric_balance',
}


def _fail(code):
    raise ContractError('a105_worksheet_' + code)


def _schema(source):
    _, module, factory, _ = FAMILIES[source]
    return getattr(import_module('.' + module, __package__), factory)()


def _components(source):
    return _schema(source)['items']['properties']['component']['enum']


def _reference(namespace=None, nullable=False):
    result = {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference'}
    if namespace is not None:
        result['x-reference-namespace'] = namespace
    return result


def _context_schema(requests, *, fallback_components=(), version=VERSION):
    if version not in (VERSION, VERSION_V2):
        _fail('request_invalid')
    fields = [r['field'] for r in requests]
    components = list(dict.fromkeys(c for r in requests for c in r['components']))
    empty = not components
    # Empty enums violate JSON Schema. No links can be submitted in this case.
    if empty:
        components = list(fallback_components)
    selector = obj({'field': {'type': 'string', 'enum': fields},
        'sheet_ref': _reference('source'), 'component': {'type': 'string', 'enum': components},
        'quantity': {'type': 'string', 'enum': ['cell_value', 'reported_spread', 'reported_count']}})
    support = {'type': 'array', 'items': _reference(), 'uniqueItems': True}
    quantities = {'type': 'array', 'uniqueItems': True, 'items': obj({
        'left': deepcopy(selector), 'right': deepcopy(selector),
        'relation': {'type': 'string', 'enum': list(QUANTITY_RELATIONS_V2 if version == VERSION_V2 else QUANTITY_RELATIONS)},
        'support_record_refs': deepcopy(support)})}
    assertions = {'type': 'array', 'uniqueItems': True, 'items': obj({
        'selector': deepcopy(selector), 'assertion_ref': _reference('hypothesis', True),
        'relation': {'type': 'string', 'enum': list(ASSERTION_RELATIONS)}, 'support_record_refs': deepcopy(support)})}
    if empty:
        quantities['maxItems'] = assertions['maxItems'] = 0
    return obj({'version': {'type': 'string', 'const': version},
        'assertion_refs': {'type': 'array', 'items': _reference('hypothesis'), 'uniqueItems': True},
        'quantity_links': quantities, 'assertion_links': assertions})


def a105_worksheet_template(section_requests, *, context_field='assessment_context', worksheet_version=VERSION):
    """Return aliases, existing component rosters and host presentation roles.

    No experiment, cell or population operation is selected by constructing a
    form. Supported source formats do not represent completed assay counts.
    """
    if (not isinstance(section_requests, (list, tuple)) or not section_requests
            or not isinstance(context_field, str) or not CODE.fullmatch(context_field)
            or worksheet_version not in (VERSION, VERSION_V2)):
        _fail('request_invalid')
    requests, fields, sources, rosters, roles, vocabulary = [], set(), set(), {}, [], []
    for value in section_requests:
        if not isinstance(value, Mapping) or set(value) != {'field', 'source', 'components'}:
            _fail('request_invalid')
        field, source, selected = value['field'], value['source'], value['components']
        if not isinstance(source, str) or source not in FAMILIES:
            _fail('section_unimplemented')
        allowed = _components(source)
        if (not isinstance(field, str) or not CODE.fullmatch(field) or field == context_field
                or field in fields or source in sources or not isinstance(selected, (list, tuple))
                or any(not isinstance(c, str) or c not in allowed for c in selected)
                or len(set(selected)) != len(selected)):
            _fail('request_invalid')
        request = {'field': field, 'source': source, 'components': list(selected)}
        requests.append(request); fields.add(field); sources.add(source)
        rosters[FAMILIES[source][0]] = list(selected)
        roles.append({**deepcopy(request), 'numerical_role': FAMILIES[source][3]})
        vocabulary.extend(allowed)
    properties = {r['field']: {'$ref': 'episode-fact:' + r['source']} for r in requests}
    properties[context_field] = _context_schema(requests, fallback_components=list(dict.fromkeys(vocabulary)),
        version=worksheet_version)
    return {'submitted_form': obj(properties), 'assignment_rosters': rosters, 'section_roles': roles}


def _source(node):
    if not isinstance(node, Mapping):
        return None
    if isinstance(node.get('$ref'), str) and node['$ref'].startswith('episode-fact:'):
        return node['$ref'].split(':', 1)[1]
    return node.get('x-source')


def _layout(form, schema, assignment):
    """Recognize original context and declarations; never reattest native code."""
    if not isinstance(schema, Mapping) or not isinstance(schema.get('properties'), Mapping):
        return None
    properties = schema['properties']
    contexts = [field for field, node in properties.items() if isinstance(node, Mapping)
        and node.get('properties', {}).get('version', {}).get('const') in (VERSION, VERSION_V2)]
    if not contexts:
        if isinstance(form, Mapping) and any(isinstance(v, Mapping) and v.get('version') in (VERSION, VERSION_V2) for v in form.values()):
            _fail('schema_invalid')
        return None
    if len(contexts) != 1 or not isinstance(form, Mapping) or not isinstance(assignment, Mapping):
        _fail('schema_invalid')
    context_field = contexts[0]
    requests, seen = [], set()
    for field, node in properties.items():
        if field == context_field:
            continue
        source = _source(node)
        if source not in FAMILIES or source in seen:
            _fail('schema_invalid')
        key = FAMILIES[source][0]
        selected = assignment.get(key)
        # Roster vocabulary is checked against the ORIGINAL field's schema, not
        # a newly generated schema/calculator. Alias inputs need construction
        # metadata; the ordinary host expands them before actual admission.
        allowed = node.get('items', {}).get('properties', {}).get('component', {}).get('enum')
        if allowed is None:
            _fail('schema_invalid')
        if (not isinstance(selected, (list, tuple)) or any(not isinstance(c, str) or c not in allowed for c in selected)
                or len(set(selected)) != len(selected)):
            _fail('request_invalid')
        requests.append({'field': field, 'source': source, 'components': list(selected)})
        seen.add(source)
    if not requests or set(form) != set(properties):
        _fail('schema_invalid')
    # Persistence may sort object keys. The original selector enum retains the
    # caller's section order; dictionary insertion order is not an identity.
    try:
        field_order = properties[context_field]['properties']['quantity_links']['items']['properties']['left']['properties']['field']['enum']
        by_field = {r['field']: r for r in requests}
        if (not isinstance(field_order, (list, tuple)) or len(field_order) != len(requests)
                or set(field_order) != set(by_field)):
            _fail('schema_invalid')
        requests = [by_field[field] for field in field_order]
    except (KeyError, TypeError) as cause:
        raise ContractError('a105_worksheet_schema_invalid') from cause
    vocabulary = list(dict.fromkeys(c for r in requests
        for c in properties[r['field']]['items']['properties']['component']['enum']))
    expected = _context_schema(requests, fallback_components=vocabulary,
        version=properties[context_field]['properties']['version']['const'])
    if plain(properties[context_field]) != expected:
        _fail('schema_invalid')
    context = plain(form[context_field])
    if not Draft202012Validator(expected).is_valid(context):
        _fail('context_invalid')
    return context, requests


def _read(reader, reference, *, kind=None, error='link_not_supported'):
    if not isinstance(reference, str):
        _fail(error)
    try:
        record = reader(reference)
    except (LookupError, ContractError) as cause:
        raise ContractError('a105_worksheet_' + error) from cause
    if (not isinstance(record, Mapping) or record.get('id') != reference
            or not isinstance(record.get('record_type'), str)
            or kind is not None and record['record_type'] != kind):
        _fail(error)
    return record


def _anchor(reader, reference):
    record = _read(reader, reference, kind='reference')
    anchor = record.get('anchor')
    if (not isinstance(anchor, Mapping) or not isinstance(anchor.get('source_ref'), str)
            or not isinstance(anchor.get('artifact_ref'), str) or type(anchor.get('start')) is not int
            or type(anchor.get('end')) is not int or not isinstance(anchor.get('quote'), str)
            or not 0 <= anchor['start'] < anchor['end']
            or len(anchor['quote'].encode()) != anchor['end'] - anchor['start']
            or record.get('source_ref') != anchor['source_ref']):
        _fail('link_not_supported')
    return anchor


def _same_location(anchor, location):
    return all(anchor.get(k) == location.get(k) for k in ('source_ref', 'artifact_ref', 'start', 'end'))


def _unit(value):
    return {'uM_inverse_min_inverse': 'uM^-1min^-1'}.get(value, value)


def _source_context(metadata, summary, reader):
    """Match delivered fragments to role-specific original public witnesses."""
    matched_subject = False
    for name, value in summary['source_context'].items():
        fragments = value['fragments']
        if not fragments:
            continue
        reference = metadata['subject'].get(name) if name in metadata['subject'] else metadata['context'].get(name)
        anchor = _anchor(reader, reference)
        for fragment in fragments:
            location = fragment['location']
            if (any(anchor[k] != location[k] for k in ('source_ref', 'artifact_ref'))
                    or not anchor['start'] <= location['start'] < location['end'] <= anchor['end']):
                _fail('link_not_supported')
            raw = anchor['quote'].encode()[location['start'] - anchor['start']:location['end'] - anchor['start']]
            if raw != fragment['text'].encode():
                _fail('link_not_supported')
        if name in ('molecule', 'construct'):
            matched_subject = True
    if not matched_subject:
        _fail('link_not_supported')


def _native_summary(left, right, relation, reader):
    (source, native, selector), (target, summary, other) = left, right
    if source == SUMMARY and target == NATIVE:
        return _native_summary(right, left, relation, reader)
    if source != NATIVE or target != SUMMARY or selector['component'] not in ('numerator_parameter', 'denominator_parameter'):
        _fail('link_not_supported')
    role = selector['component'].removesuffix('_parameter')
    metadata, cell = native[role], summary['cell']
    if (summary['population'] != 'source_cells' or other['quantity'] != 'cell_value'
            or cell['status'] != 'populated' or native['evidence_source_ref'] != summary['evidence_source_ref']
            or metadata['parameter_kind'] in ('unknown', 'conflicting')
            or metadata['parameter_kind'] != summary['parameter_kind']
            or (metadata['source_origin'] == 'synthetic') != (summary['source_kind'] == 'synthetic_fixture')):
        _fail('link_not_supported')
    _source_context(metadata, summary, reader)
    uncertainty = metadata['uncertainty']
    if relation == 'same_reported_parameter':
        if (selector['quantity'] != 'cell_value' or other['component'] != 'source_reported_parameter'
                or native['status'] != 'populated' or native['relation'] != 'eq'
                or native['value'] != cell['value'] or native['approximate'] != cell['approximate']
                or _unit(native['unit']) != cell['unit']):
            _fail('link_not_supported')
        reference, unit_ref = metadata['measurement_ref'], metadata['source_unit_ref']
    elif relation == 'same_reported_spread':
        if (selector['quantity'] != 'reported_spread' or other['component'] != 'source_reported_sd'
                or uncertainty['statistic'] != 'sd' or metadata['uncertainty_values']['magnitude'] != cell['value']
                or _unit(uncertainty['canonical_unit']) != cell['unit']):
            _fail('link_not_supported')
        reference, unit_ref = uncertainty['magnitude_ref'], uncertainty['unit_ref']
    elif relation == 'same_count_report':
        basis = summary['sampling_basis']
        repetition = uncertainty['repetition_basis']
        meanings = {'biological_preparations': ('physical_preparation_count', 'both_same_count'),
            'technical_measurements': ('technical_measurement_count', 'statistical_estimator_count', 'both_same_count')}
        if (selector['quantity'] != 'reported_count'
                or other['component'] not in ('source_source_summary_count', 'source_independent_preparation_count')
                or metadata['uncertainty_values']['count'] != cell['value'] or cell['unit'] != 'count'
                or uncertainty['count_reading_status'] != 'exact' or uncertainty['count_approximate'] is not False
                or uncertainty['count_relation'] != 'point' or repetition != basis['repetition_basis']
                or basis['source_count_meaning'] not in meanings.get(repetition, ())):
            _fail('link_not_supported')
        if other['component'] == 'source_independent_preparation_count':
            conditions = {c['condition']: c['state'] for c in summary['model_conditions']}
            if repetition != 'biological_preparations' or conditions.get('row_footnote_applicability') != 'source_supported':
                _fail('link_not_supported')
        reference, unit_ref = uncertainty['count_ref'], None
    else:
        _fail('link_not_supported')
    for reference in (reference, unit_ref) if unit_ref is not None else (reference,):
        anchor = _anchor(reader, reference)
        if anchor['source_ref'] != summary['evidence_source_ref'] or not any(
                _same_location(anchor, location) for location in summary['dependency_locations']):
            _fail('link_not_supported')


def _same_physical_measurement(left, right, support_refs, reader):
    """Admit one reused original kinetic estimate across two contrast sheets.

    The reader's physical identity is a source witness, not a numeric equality
    heuristic or a declaration that the two contrasts are independent. The
    original parameter token must sit within that witness in both rows.
    """
    (source_a, row_a, selector_a), (source_b, row_b, selector_b) = left, right
    if (source_a != NATIVE or source_b != NATIVE or
            selector_a['quantity'] != 'cell_value' or selector_b['quantity'] != 'cell_value' or
            selector_a['component'] not in ('numerator_parameter', 'denominator_parameter') or
            selector_b['component'] not in ('numerator_parameter', 'denominator_parameter') or
            row_a['sheet_ref'] == row_b['sheet_ref'] or
            row_a['status'] != 'populated' or row_b['status'] != 'populated' or
            row_a['relation'] != 'eq' or row_b['relation'] != 'eq' or
            row_a['evidence_source_ref'] != row_b['evidence_source_ref']):
        _fail('link_not_supported')
    metadata_a = row_a[selector_a['component'].removesuffix('_parameter')]
    metadata_b = row_b[selector_b['component'].removesuffix('_parameter')]
    physical = metadata_a['physical_observation_ref']
    measurement = metadata_a['measurement_ref']
    if (physical is None or measurement is None or
            metadata_b['physical_observation_ref'] != physical or
            metadata_b['measurement_ref'] != measurement or
            set(support_refs) != {physical, measurement} or
            canonical(metadata_a) != canonical(metadata_b) or
            any(row_a[key] != row_b[key] for key in
                ('value', 'unit', 'status', 'relation', 'approximate', 'origin',
                 'threshold', 'unavailable_reason'))):
        _fail('link_not_supported')
    physical_anchor, measurement_anchor = (_anchor(reader, ref) for ref in (physical, measurement))
    if (physical_anchor['source_ref'] != row_a['evidence_source_ref'] or
            measurement_anchor['source_ref'] != row_a['evidence_source_ref'] or
            physical_anchor['artifact_ref'] != measurement_anchor['artifact_ref'] or
            not physical_anchor['start'] <= measurement_anchor['start'] < measurement_anchor['end'] <= physical_anchor['end']):
        _fail('link_not_supported')


def _conditional(left, right):
    if left[1].get('population') == 'scenario_cells':
        left, right = right, left
    source, report, selector = left
    target, scenario, other = right
    if (source != SUMMARY or target != SUMMARY or selector['quantity'] != 'cell_value' or other['quantity'] != 'cell_value'
            or report['component'] not in ('source_reported_sd', 'source_independent_preparation_count')
            or scenario['component'] not in ('scenario_mean_variance', 'scenario_mean_standard_error')
            or report['sheet_ref'] != scenario['sheet_ref'] or report['population'] != 'source_cells'
            or scenario['population'] != 'scenario_cells' or report['cell']['status'] != 'populated'
            or scenario['cell']['status'] != 'populated'):
        _fail('link_not_supported')
    cell = scenario['cell']
    if (cell['qualification'] != 'conditional_on_stipulated_assumptions' or not cell['stipulated_assumptions']
            or not set(cell['stipulated_assumptions']) <= set(cell['conditional_on'])):
        _fail('scenario_source_promotion')
    for name in ('evidence_source_ref', 'source_kind', 'parameter_kind', 'source_context', 'sampling_basis', 'contribution'):
        if report[name] != scenario[name]:
            _fail('link_not_supported')
    if not report['dependency_locations'] or not all(
            loc in scenario['dependency_locations'] for loc in report['dependency_locations']):
        _fail('link_not_supported')
    conditions = {c['condition']: c['state'] for c in scenario['model_conditions']}
    if any(conditions.get(c) != 'unknown' for c in cell['stipulated_assumptions']):
        _fail('scenario_source_promotion')


def validate_a105_worksheet_links(form, schema, assignment, *, read_public_record):
    """Validate admitted relationships, retaining empty/unknown partial reports.

    This is additional semantic validation, not a replacement for the ordinary
    original-schema/fact/custody/reference validation. It does not infer biology
    from citations. Assertion relation meanings belong to the responsible
    episode's explicitly constrained interpretation.
    """
    layout = _layout(form, schema, assignment)
    if layout is None:
        return
    context, requests = layout
    rows = {}
    for request in requests:
        field, source = request['field'], request['source']
        values = form[field]
        if not isinstance(values, (list, tuple)):
            _fail('selector_not_delivered')
        for row in values:
            if (not isinstance(row, Mapping) or row.get('component') not in request['components']
                    or row.get('evaluation_scope') != _SCOPES[source]):
                _fail('selector_not_delivered')
            key = field, row.get('sheet_ref'), row['component']
            if key in rows:
                _fail('duplicate_link')
            rows[key] = source, row

    def resolve(selector):
        key = tuple(selector[k] for k in ('field', 'sheet_ref', 'component'))
        if key not in rows:
            _fail('selector_not_delivered')
        source, row = rows[key]
        quantity = selector['quantity']
        if quantity != 'cell_value':
            if source != NATIVE or row['component'] not in ('numerator_parameter', 'denominator_parameter'):
                _fail('subquantity_not_delivered')
            metadata = row[row['component'].removesuffix('_parameter')]
            if metadata['uncertainty_values']['delivery_status'] != 'requested':
                _fail('subquantity_not_delivered')
        return source, row, selector

    for reference in context['assertion_refs']:
        _read(read_public_record, reference, kind='hypothesis', error='assertion_reference_invalid')
    seen = set()
    for link in context['quantity_links']:
        left, right = resolve(link['left']), resolve(link['right'])
        signature = (link['relation'], *sorted((canonical(link['left']), canonical(link['right']))))
        if signature in seen:
            _fail('duplicate_link')
        seen.add(signature)
        for reference in link['support_record_refs']:
            _read(read_public_record, reference)
        if link['relation'] == 'unresolved':
            continue
        if link['relation'] == 'conflicting':
            if len(link['support_record_refs']) < 2:
                _fail('link_not_supported')
        elif link['relation'] == 'same_physical_measurement':
            _same_physical_measurement(left, right, link['support_record_refs'], read_public_record)
        elif link['relation'] == 'conditional_precision_of_report':
            _conditional(left, right)
        else:
            _native_summary(left, right, link['relation'], read_public_record)
    seen = set()
    for link in context['assertion_links']:
        resolve(link['selector'])
        reference = link['assertion_ref']
        if reference is not None and reference not in context['assertion_refs']:
            _fail('assertion_reference_invalid')
        signature = canonical([link['selector'], reference, link['relation']])
        if signature in seen:
            _fail('duplicate_link')
        seen.add(signature)
        for support in link['support_record_refs']:
            _read(read_public_record, support, error='assertion_reference_invalid')
        if (link['relation'] in ('measures_asserted_endpoint', 'addresses_named_weakness', 'does_not_establish_assertion')
                and (reference is None or not link['support_record_refs'])):
            _fail('assertion_reference_invalid')
        if link['relation'] == 'conflicting' and len(link['support_record_refs']) < 2:
            _fail('assertion_reference_invalid')


__all__ = ['VERSION', 'VERSION_V2', 'a105_worksheet_template', 'validate_a105_worksheet_links']
