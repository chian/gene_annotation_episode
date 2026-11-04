"""Bind existing reader results to reusable A105 assay assessments.

Numerical inputs are possessed typed components or authenticated source spans.
Assay selection and source interpretations belong to the investigating episode.
This adapter does not manufacture scientific applicability or independent data.
"""
from copy import deepcopy
from importlib import import_module
import math
import re

from .domain import REF, ContractError, identity, obj, validate_schema
from .literature_assay_inputs import _Sources, _witness_schema, SOURCE_KINDS
from .literature_partner_source_fields import (
    number_selector_schema, read_source_number, _unit_contexts, _unit_continuation,
    _contexts, _interval_contexts, _relation, _LOWER, _soft_break_numeric_token,
)
from .literature_assay_grading import INPUT_VERSION, ROLES, REQUIRED_ROLES, assay_grading_input_schema
from .literature_experimental_contracts import ExperimentalContractError

# These are existing input representations, not additional assay graders.
SOURCE_SCHEMAS = {
    'literature_rate_cells': ('literature_rate_storage', 'rate_cells_schema'),
    'literature_rate_source_cells': ('literature_rate_storage', 'rate_source_cells_schema'),
    'literature_rate_source_meaning_cells': ('literature_rate_meaning_delivery', 'rate_source_meaning_cells_schema'),
    'literature_rate_observation_cells': ('literature_rate_observation_storage', 'rate_observation_cells_schema'),
    'literature_rate_replicate_cells': ('literature_rate_replicate_storage', 'rate_replicate_cells_schema'),
    'literature_assay_cells': ('literature_assay_storage', 'assay_cells_schema'),
    'literature_controlled_response_component_cells': ('literature_controlled_response_storage', 'controlled_response_cells_schema'),
    'literature_compiled_assay_cells': ('literature_compiled_assay_storage', 'compiled_assay_cells_schema'),
    'literature_compiled_assay_v2_cells': ('literature_compiled_assay_storage', 'compiled_assay_v2_cells_schema'),
    'literature_compiled_assay_v3_cells': ('literature_compiled_assay_storage', 'compiled_assay_v3_cells_schema'),
    'literature_completion_time_cells': ('literature_completion_time_storage', 'completion_time_cells_schema'),
    'literature_product_partition_cells': ('literature_product_partition_storage', 'product_partition_cells_schema'),
    'literature_product_coupling_cells': ('literature_product_coupling_storage', 'product_coupling_cells_schema'),
    'literature_endpoint_signal_cells': ('literature_endpoint_signal_storage', 'endpoint_signal_cells_schema'),
    'literature_concentration_window_cells': ('literature_concentration_window_storage', 'concentration_window_cells_schema'),
    'literature_parent_depletion_cells': ('literature_parent_depletion_storage', 'parent_depletion_cells_schema'),
    'literature_stoichiometric_balance_cells': ('literature_stoichiometric_balance_storage', 'stoichiometric_balance_cells_schema'),
    'literature_calibration_recovery_cells': ('literature_calibration_recovery_storage', 'calibration_recovery_cells_schema'),
    'literature_kinetic_cells': ('literature_kinetic_storage', 'kinetic_cells_schema'),
    'literature_kinetic_summary_precision_cells': ('literature_kinetic_summary_precision_storage', 'summary_precision_cells_schema'),
    'literature_kinetic_model_cells': ('literature_kinetic_model_storage', 'kinetic_model_cells_schema'),
    'literature_rate_grid_cells': ('literature_rate_observation_storage', 'rate_grid_cells_schema'),
    'literature_binding_cells': ('literature_binding_storage', 'binding_cells_schema'),
    'literature_binding_model_cells': ('literature_binding_model_storage', 'binding_model_cells_schema'),
    'literature_binding_interaction_cells': ('literature_binding_interaction_storage', 'binding_interaction_cells_schema'),
    'literature_binding_interaction_model_cells': ('literature_binding_interaction_model_storage', 'binding_interaction_model_cells_schema'),
    'literature_transport_cells': ('literature_transport_storage', 'transport_response_cells_schema'),
    'literature_channel_cells': ('literature_channel_storage', 'channel_cells_schema'),
    'literature_ion_discrimination_cells': ('literature_ion_discrimination_storage', 'ion_discrimination_cells_schema'),
    'literature_ratio_cells': ('literature_ratio_storage', 'ratio_cells_schema'),
    'literature_ratio_source_cells': ('literature_ratio_source_storage', 'ratio_source_cells_schema'),
    'literature_gel_component_cells': ('literature_gel_native_contracts', 'gel_cells_schema'),
    'literature_amount_cells': ('literature_amount_storage', 'amount_cells_schema'),
    'literature_active_site_cells': ('literature_active_site_storage', 'active_site_cells_schema'),
    'literature_optical_cells': ('literature_optical_storage', 'optical_cells_schema'),
    'literature_partner_cells': ('literature_partner_storage', 'partner_cells_schema'),
}


# These route existing measurements by scientific quantity, not source case.
# Variance, error bars and previous evidence scores are not measured effects.
EFFECT_ROUTES = {
    'literature_binding_cells': ('ligand_binding', {
        'reference_parameter': ('binding_parameter',), 'test_parameter': ('binding_parameter',),
        'native_parameter_ratio': ('binding_parameter_ratio',),
        'log_native_parameter_ratio': ('log_binding_parameter_ratio',)}),
    'literature_binding_model_cells': ('ligand_binding', {
        'log_parameter_contrast': ('log_binding_parameter_ratio',)}),
    'literature_binding_interaction_cells': ('ligand_binding', {
        **{name: ('binding_parameter',) for name in ('parameter_rr', 'parameter_rt', 'parameter_tr', 'parameter_tt')},
        'reference_subject_ratio': ('binding_parameter_ratio',), 'test_subject_ratio': ('binding_parameter_ratio',),
        'interaction_ratio': ('binding_discrimination_ratio',), 'log_interaction': ('log_binding_discrimination',)}),
    'literature_binding_interaction_model_cells': ('ligand_binding', {}),
    'literature_transport_cells': ('transport_response', {
        'apparent_km': ('transport_parameter',), 'test_saturation': ('substrate_saturation',),
        'reference_saturation': ('substrate_saturation',), 'condition_response': ('substrate_response_ratio',),
        'log_condition_response': ('log_substrate_response',)}),
    'literature_channel_cells': ('transport_response', {
        'current': ('electrical_current',), 'reported_conductance': ('electrical_conductance',),
        'chord_conductance': ('electrical_conductance',), 'charge_equivalent_rate': ('charge_equivalent_rate',)}),
    'literature_ion_discrimination_cells': ('transport_response', {
        'preferred_activity': ('transport_rate',), 'alternative_activity': ('transport_rate',),
        'activity_ratio': ('transport_rate_ratio',), 'log_activity_ratio': ('log_transport_rate_ratio',),
        'reported_selectivity': ('transport_rate_ratio',)}),
    **{namespace: ('protein_signal', {'reported_ratio': ('signal_ratio',),
        'difference_from_reference': ('signal_difference',), 'log_reported_ratio': ('log_signal_ratio',)})
        for namespace in ('literature_ratio_cells', 'literature_ratio_source_cells')},
    'literature_gel_component_cells': ('protein_signal', {
        **{name: ('band_display_fraction',) for name in ('shifted_display_fraction', 'off_band_display_fraction',
            'display_black_pixel_fraction', 'display_total_ratio_to_protein_lane', 'protein_associated_display_shift',
            'competitor_residual_display_fraction', 'displaced_display_fraction', 'factorized_competitor_sensitive_shift',
            'direct_competitor_sensitive_shift')},
        **{name: ('band_display_darkness',) for name in ('background_corrected_band_darkness',
            'shifted_display_darkness', 'free_display_darkness', 'selected_total_display_darkness')}}),
    'literature_amount_cells': ('protein_amount', {
        'numerator_amount': ('protein_amount',), 'denominator_amount': ('protein_amount',),
        'amount_difference': ('protein_amount_difference',), 'amount_ratio': ('protein_amount_ratio',),
        'reciprocal_amount_ratio': ('protein_amount_ratio',)}),
    'literature_active_site_cells': ('protein_amount', {
        **{name: ('protein_amount',) for name in ('protein_mass_concentration', 'total_monomer_concentration', 'active_site_concentration')},
        'sites_per_total_monomer': ('sites_per_monomer',), 'conditional_active_monomer_fraction': ('active_fraction',),
        'reported_active_fraction': ('active_fraction',)}),
    'literature_optical_cells': ('activity_rate', {'net_rate': ('rate', 'rate_difference')}),
    'literature_partner_cells': ('activity_rate', {
        **{name: ('rate',) for name in ('reference_rate', 'omitted_rate', 'addback_rate')},
        **{name: ('partner_rate_difference',) for name in ('partner_loss', 'addback_gain')},
        **{name: ('partner_response_fraction',) for name in ('partner_loss_fraction', 'addback_fraction', 'restored_reference_fraction')}}),
    'literature_kinetic_cells': ('activity_rate', {
        'numerator_parameter': ('kinetic_parameter', 'turnover', 'catalytic_efficiency', 'rate'),
        'denominator_parameter': ('kinetic_parameter', 'turnover', 'catalytic_efficiency', 'rate'),
        'parameter_difference': ('kinetic_parameter_difference', 'rate_difference'),
        'parameter_ratio': ('kinetic_parameter_ratio', 'rate_ratio'),
        'log_parameter_contrast': ('log_kinetic_parameter_ratio',)}),
    'literature_kinetic_model_cells': ('activity_rate', {}),
}


def source_schema(namespace):
    if namespace not in SOURCE_SCHEMAS:
        raise ContractError('assay_grading_reader_namespace_unsupported')
    module, factory = SOURCE_SCHEMAS[namespace]
    return getattr(import_module('.' + module, __package__), factory)()


def assay_grading_population_schema(*, legacy=False):
    schema = deepcopy(assay_grading_input_schema())
    props = schema['properties']
    del props['version']
    props.update(source_ref=deepcopy(REF), source_kind={'enum': list(SOURCE_KINDS)})
    received = obj({'kind': {'const': 'received_component'},
        'namespace': {'enum': list(SOURCE_SCHEMAS)}, 'sheet_ref': deepcopy(REF),
        'component': {'type': 'string', 'minLength': 1}})
    received['description'] = ('Use a saved numerical reader component, including a single reported '
        'kinetic parameter from literature.kinetic.populate: namespace literature_kinetic_cells, '
        'its returned sheet_ref, and component numerator_parameter.')
    literal = obj({'kind': {'const': 'source_number'}, 'number': number_selector_schema(),
        'unit': _witness_schema(), 'origin': {'enum': ['reported', 'proposed', 'synthetic']}})
    literal['description'] = ('Scalar shortcut for a number followed immediately by its printed unit '
        'in the same source representation. A shared table-header unit uses the appropriate typed '
        'reader instead. For a reported Km, kcat or catalytic efficiency, literature.kinetic.populate '
        'accepts separate number and unit witnesses and returns a received_component for this grader.')
    from .experimental_database_measurements import measurement_schema
    props['quantities'] = obj({role: {'anyOf': [deepcopy(received), deepcopy(literal),
                               *([measurement_schema()] if role == 'effect' else []), {'type': 'null'}]}
                              for role in ROLES})
    props['quantities']['required'] = list(REQUIRED_ROLES)
    schema['required'] = list(props)
    # Historical selections predate this binding. New population requires it;
    # old committed selections remain readable without inventing an identity.
    props['experiment_ref'] = {**deepcopy(REF), 'x-reference-namespace': 'reference',
        'description': 'Possessed source-anchored assay reference identifying this experiment. Reuse it for another assessment of the same experiment; different experiments use distinct references even when they share a protocol type or paper.'}
    if not legacy:
        schema['required'].append('experiment_ref')
    return schema


def _unit(raw):
    compact = re.sub(r'\s+', '', raw).replace('µ', 'u').replace('μ', 'u')
    aliases = {'%': ('fraction', .01), 'fraction': ('fraction', 1.),
        'dimensionless': ('dimensionless', 1.), '1': ('dimensionless', 1.), 'count': ('count', 1.),
        'pA': ('pA', 1.), 'pS': ('pS', 1.),
        'mg/ml': ('mg/ml', 1.), 'mg/mL': ('mg/ml', 1.),
        'min': ('min', 1.), 's': ('s', 1.), 'h': ('min', 60.),
        'uM': ('uM', 1.), 'mM': ('uM', 1000.), 'nM': ('uM', .001), 'M': ('uM', 1000000.),
        'pM': ('uM', .000001), 'fM': ('uM', .000000001),
        'uM/min': ('uM/min', 1.), 'mM/min': ('uM/min', 1000.),
        'per_min': ('per_min', 1.), 'min^-1': ('per_min', 1.), 'permin': ('per_min', 1.),
        'per_s': ('per_min', 60.), 's^-1': ('per_min', 60.),
        'U/mg': ('U/mg', 1.), 'umol/min/mg': ('umol/min/mg', 1.),
        'umol/(min*mg)': ('umol/min/mg', 1.),
        'pmol/min/mg': ('pmol/min/mg', 1.), 'uM_inverse_min_inverse': ('uM_inverse_min_inverse', 1.)}
    for token, (canonical, factor) in tuple(aliases.items()):
        for suffix in ('_squared', '^2'):
            aliases[token + suffix] = (canonical + '_squared', factor * factor)
    if compact not in aliases:
        raise ContractError('assay_grading_source_unit_unsupported')
    return aliases[compact]


def _read_number(selector, sources):
    """Extend the retained scalar reader only for explicit observed lower limits.

    The native reader's default and pinned implementation remain unchanged.
    Its lexical checks before the lower-limit rejection have already run; the
    remaining syntax and numeric-boundary checks run on the original context.
    """
    try:
        return read_source_number(selector, sources=sources, role='rate')
    except ExperimentalContractError as error:
        if error.code != 'lower_bound_source_number_unsupported':
            raise
    witness = sources.witness(selector['witness'], 'number_selector.witness')
    start, end = selector['number_start'], selector['number_end']
    token = witness['quote'][start:end]
    prefix, suffix = _contexts(sources, witness, start, end)
    lower = _LOWER.search(prefix)
    postfix = re.match(r'\s*(?:or\s+(?:more|greater)|and\s+above)\b', suffix, re.I)
    if lower is None and postfix is None:
        raise ExperimentalContractError('lower_bound_source_number_unsupported', 'number')
    # Validate every other scientific/lexical qualifier without treating the
    # deliberately accepted comparator as the old reader's unsupported case.
    _relation(prefix[:lower.start()] if lower else prefix,
        suffix[postfix.end():] if postfix else suffix, role='rate',
        interval_contexts=_interval_contexts(sources, witness, start, end))
    before, after = prefix[-1:], suffix[:1]
    sentence_stop = after == '.' and (len(suffix) == 1 or suffix[1].isspace() or suffix[1] in ')]};:')
    if (_soft_break_numeric_token(sources, witness, start, end, token, pm_spread=False)
            or before and (before in '.eE+−-' or before.isdigit() or before.isalpha() or before == '_')
            or after and (after in '.eE+−-' or after.isdigit()) and not sentence_stop):
        raise ExperimentalContractError('partial_source_numeric_token', 'number_selector')
    if re.search(r'\d,\s*$', prefix) or re.match(r',\s*\d', suffix):
        raise ExperimentalContractError('comma_source_number_unsupported', 'number_selector')
    value = float(token.replace('−', '-'))
    if not math.isfinite(value) or value == 0 and any(c in '123456789' for c in token.lower().split('e', 1)[0]):
        raise ExperimentalContractError('numerical_model_range', 'number_selector')
    marker = re.sub(r'\s+', ' ', lower.group().strip().lower()) if lower else ''
    relation = 'ge' if postfix or marker in ('>=', '≥', 'at least', 'no less than') or 'equal' in marker else 'gt'
    return {'selector': {**deepcopy(selector), 'witness': witness},
        'raw_number': token, 'value': value, 'relation': relation}


def _literal(selection, sources, *, unit_reader=_unit):
    unsupported = None
    try:
        number = _read_number(selection['number'], sources)
    except ExperimentalContractError as error:
        if error.code not in ('approximate_source_number_unsupported', 'lower_bound_source_number_unsupported',
                              'interval_source_number_unsupported', 'untyped_limit_source_number'):
            raise
        unsupported = error.code
        selected = deepcopy(selection['number'])
        selected['witness'] = sources.witness(selected['witness'], 'quantity.number')
        number = {'selector': selected, 'value': None, 'relation': 'unavailable'}
    witness = sources.witness(selection['unit'], 'quantity.unit')
    number_witness = number['selector']['witness']
    if any(number_witness[k] != witness[k] for k in ('source_ref', 'representation', 'artifact_ref')):
        raise ContractError('assay_grading_unit_from_different_source')
    number_end = number_witness['start'] + len(number_witness['quote'][:selection['number']['number_end']].encode())
    raw = sources.source(witness['source_ref'], witness['representation'])['content']
    # The scalar shortcut supports adjacent printed units only. Shared table
    # headers and nonadjacent unit definitions use the existing typed readers.
    try:
        gap = raw[number_end:witness['start']].decode('utf-8')
    except UnicodeError as error:
        raise ContractError('assay_grading_unit_not_adjacent_to_number') from error
    if witness['start'] < number_end or gap.strip():
        raise ContractError('assay_grading_unit_not_adjacent_to_number')
    prefix, suffix = _unit_contexts(sources, witness, 0, len(witness['quote']))
    if (prefix[-1:] and (prefix[-1:].isalpha() or prefix[-1:] in '_µμ/^')) or _unit_continuation(suffix):
        raise ContractError('assay_grading_partial_source_unit')
    try:
        unit, factor = unit_reader(witness['quote'])
    except ContractError as error:
        if str(error) != 'assay_grading_source_unit_unsupported':
            raise
        unit, factor, unsupported = 'unknown', 1., 'source_unit_unsupported'
    selected = number['selector']; location = selected['witness']
    key = identity('physical_source_span', {'artifact_ref': location['artifact_ref'],
        'start': location['start'] + len(location['quote'][:selected['number_start']].encode()),
        'end': location['start'] + len(location['quote'][:selected['number_end']].encode())})
    relation = number['relation']
    # Existing reader retains censoring and approximation; neither is a known
    # normal point estimate merely because its numeric token can be parsed.
    status = 'point' if relation == 'point' else 'bounded' if relation in ('lt', 'le', 'gt', 'ge') else 'unavailable'
    if unsupported:
        status = 'unavailable'
    value = number['value'] * factor if status == 'point' else None
    if value is not None and not math.isfinite(value):
        raise ContractError('assay_grading_numerical_range')
    result = {'value': value, 'unit': unit, 'status': status,
        'reason': None if status == 'point' else unsupported or 'source_number_' + relation,
        'measurement_keys': [key], 'source_refs': list(dict.fromkeys((location['source_ref'], witness['source_ref']))),
        'origin': selection['origin'], 'native_component': 'source_number'}
    if status == 'bounded':
        threshold = number['value'] * factor
        result['bound'] = {'relation': relation,
            'lower': threshold if relation in ('gt', 'ge') else None,
            'upper': threshold if relation in ('lt', 'le') else None}
    return result


def _native_bound(cell):
    """Retain reported censoring, not an interval over alternate reader choices."""
    relation = cell.get('relation') or cell.get('bound')
    if relation in ('lt', 'le', 'gt', 'ge'):
        threshold = cell.get('threshold')
        if threshold is None:
            threshold = cell.get('value')
        if type(threshold) in (int, float) and math.isfinite(threshold):
            return {'relation': relation, 'lower': threshold if relation in ('gt', 'ge') else None,
                'upper': threshold if relation in ('lt', 'le') else None}
    if cell.get('status') == 'bounded' and 'censor' in str(cell.get('bound_kind', '')):
        lower, upper = cell.get('lower'), cell.get('upper')
        if ((lower is None or type(lower) in (int, float) and math.isfinite(lower)) and
                (upper is None or type(upper) in (int, float) and math.isfinite(upper)) and
                (lower is not None or upper is not None)):
            return {'relation': 'interval' if lower is not None and upper is not None else 'le' if upper is not None else 'ge',
                'lower': lower, 'upper': upper}
    return None


def _component(selection, read_cells, *, schema=None):
    rows = read_cells(selection['namespace'], selection['sheet_ref'], [selection['component']])
    component_field = 'component_key' if selection['namespace'] in (
        'literature_controlled_response_component_cells', 'literature_gel_component_cells') else 'component'
    if len(rows) != 1 or rows[0].get('sheet_ref') != selection['sheet_ref'] or rows[0].get(component_field) != selection['component']:
        raise ContractError('assay_grading_component_not_received')
    validate_schema(rows, source_schema(selection['namespace']) if schema is None else schema)
    row = deepcopy(rows[0]); cell = row.get('cell', row)
    raw_status = cell.get('status')
    value = cell.get('value')
    reason = cell.get('unavailable_reason') or cell.get('unavailable_reasons') or None
    semantics = cell.get('native_semantics', row.get('native_semantics'))
    native_bound = _native_bound(cell)
    if native_bound is not None and semantics not in ('unknown', 'conflicting'):
        status, value, reason = 'bounded', None, 'reported_censoring_event'
    elif semantics in ('reported_nondetection', 'reported_negligible', 'unknown', 'conflicting'):
        status, value, reason = 'unavailable', None, 'native_' + semantics + '_is_not_point'
    elif raw_status in ('bounded', 'reported_limit') or cell.get('bound') not in (None, 'none') or cell.get('relation') not in (None, 'eq', 'point', 'none'):
        status, value, reason = 'bounded', None, 'bounded_component_requires_bound_model'
    elif raw_status not in ('point', 'populated', 'available', 'measured', 'calculated') or value is None:
        status, value, reason = 'unavailable', None, reason or 'native_component_unavailable'
    elif cell.get('approximate'):
        status, value, reason = 'unavailable', None, 'approximate_component_requires_uncertainty_model'
    else:
        status = 'point'
    if isinstance(reason, list):
        reason = ';'.join(reason) or None
    if status == 'point' and reason is not None:
        status, value = 'unavailable', None
    if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
        raise ContractError('assay_grading_finite_number_required')
    unit = cell.get('unit') or 'unknown'
    # These are identical squared-unit spellings, not a rescaling or new error estimate.
    unit = {'uM2/min2': 'uM/min_squared', 'uM2': 'uM_squared',
        'mg2/ml2': 'mg/ml_squared', 'log_parameter_squared': 'dimensionless_squared'}.get(unit, unit)
    try:
        unit, factor = _unit(unit)
    except ContractError:
        factor = 1.
    if value is not None:
        value *= factor
    if native_bound is not None:
        native_bound = {**native_bound, **{key: None if native_bound[key] is None else native_bound[key] * factor
            for key in ('lower', 'upper')}}
    origin = cell.get('origin') or row.get('origin') or ('synthetic' if row.get('source_kind') == 'synthetic_fixture' else 'derived')
    origin = {'calculated': 'derived', 'graph_digitized': 'graph_derived', 'definition_identity': 'derived'}.get(origin, origin)
    if origin not in ('reported', 'derived', 'graph_derived', 'synthetic', 'proposed'):
        origin = 'derived'
    keys = []
    for container in (row, cell):
        for name in ('input_measurement_keys', 'operand_keys', 'measurement_keys', 'input_measurement_refs', 'reference_measurement_refs', 'dependency_keys'):
            keys.extend(v for v in container.get(name, ()) if isinstance(v, str))
    for location in row.get('dependency_locations', ()):
        if all(k in location for k in ('artifact_ref', 'start', 'end')):
            keys.append(identity('physical_source_span', {k: location[k] for k in ('artifact_ref', 'start', 'end')}))
    nested_qualifications, input_origins = [], []
    def metadata(value):
        if isinstance(value, dict):
            for name, child in value.items():
                if name in ('canonical_physical_keys', 'recorded_dependency_keys', 'covariance_owner_ids', 'owner_ids', 'physical_keys', 'opaque_dependency_keys'):
                    keys.extend(v for v in child if isinstance(v, str))
                elif name in ('physical_owner_key', 'owner_key', 'quantity_key', 'measurement_key',
                              'physical_observation_key', 'physical_observation_ref') and isinstance(child, str):
                    keys.append(child)
                elif name == 'variance_status' and child in ('estimated', 'unknown'):
                    nested_qualifications.append(child + '_covariance')
                elif name in ('origin', 'covariance_origin', 'source_origin', 'converted_origin', 'model_origin') and isinstance(child, str):
                    input_origins.append(child)
                elif name == 'input_origins' and isinstance(child, (list, tuple)):
                    input_origins.extend(v for v in child if isinstance(v, str))
                metadata(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                metadata(child)
    # Native formats already scope dependencies to the selected cell. Their
    # wider estimate rosters and legacy full-model context are not its operands.
    for container in (row, cell):
        if isinstance(container.get('dependencies'), (list, dict)):
            metadata(container['dependencies'])
        input_origins.extend(v for v in container.get('input_origins', ()) if isinstance(v, str))
    input_origins.extend(v for v in row.get('source_origins', ()) if isinstance(v, str))
    input_origins.extend(row[name] for name in ('source_origin', 'model_origin', 'covariance_origin')
        if isinstance(row.get(name), str))
    # Visit only selected native operands, never a private saved sheet. Native
    # kinetic projections deliver metadata for both arms, so scope single-arm
    # effects explicitly rather than assigning the other arm's measurements.
    if isinstance(row.get('operands'), (dict, list)):
        metadata(row['operands'])
    if selection['namespace'] in ('literature_kinetic_cells', 'literature_kinetic_model_cells'):
        arm_names = ('numerator',) if selection['component'] == 'numerator_parameter' else (
            ('denominator',) if selection['component'] == 'denominator_parameter' else ('numerator', 'denominator'))
        for arm in arm_names:
            metadata(row.get(arm, {}))
    if selection['namespace'] in ('literature_binding_interaction_cells', 'literature_binding_interaction_model_cells'):
        roles = row['roles']
        selected_roles = {
            'parameter_rr': ('reference_subject_reference_ligand',), 'parameter_rt': ('reference_subject_test_ligand',),
            'parameter_tr': ('test_subject_reference_ligand',), 'parameter_tt': ('test_subject_test_ligand',),
            'reference_subject_ratio': ('reference_subject_reference_ligand', 'reference_subject_test_ligand'),
            'test_subject_ratio': ('test_subject_reference_ligand', 'test_subject_test_ligand'),
        }.get(row['component'], tuple(roles))
        for name in selected_roles:
            fit = roles[name]['physical_fit']
            if fit['status'] == 'known' and fit['canonical_witness_ref']:
                keys.append(fit['canonical_witness_ref'])
    for dependency in row.get('numerical_dependencies', ()):
        source_dependency = dependency['source_dependency']
        keys.append(identity('native_display_measurement', source_dependency))
    covariance = row.get('covariance')
    if isinstance(covariance, dict):
        metadata(covariance)
        if covariance.get('status') in ('estimated', 'unknown'):
            nested_qualifications.append(covariance['status'] + '_covariance')
    scoped_uncertainty = row.get('uncertainty') or cell.get('uncertainty')
    if isinstance(scoped_uncertainty, dict):
        metadata(scoped_uncertainty)
    elif row.get('variance_status') in ('estimated', 'unknown'):
        nested_qualifications.append(row['variance_status'] + '_covariance')
    if row.get('contribution', {}).get('variance_meaning', '').startswith('estimated_'):
        nested_qualifications.append('estimated_covariance')
    if isinstance(row.get('covariance_provenance'), dict):
        metadata(row['covariance_provenance'])
    joint = row.get('joint_scope_context')
    if isinstance(joint, dict) and isinstance(joint.get('effective_model'), dict):
        metadata(joint['effective_model'])
    # A saved-component identity records reuse, never independence. Components
    # lacking physical owners are not silently assigned independent noise.
    if not keys:
        keys.append(identity('saved_component', {k: selection[k] for k in ('namespace', 'sheet_ref', 'component')}))
        nested_qualifications.append('physical_measurement_identity_unknown')
    refs = [selection['sheet_ref']]
    if row.get('evidence_source_ref'):
        refs.append(row['evidence_source_ref'])
    qualifications = list(dict.fromkeys(v for container in (row, cell)
        for name in ('conditional_on', 'qualifications', 'limitations', 'source_qualifications')
        for v in container.get(name, ()) if isinstance(v, str)))
    if row.get('parameter_kind'):
        qualifications.append('native_parameter_definition:' + row['parameter_kind'])
    if row.get('endpoint_kind'):
        qualifications.append('native_endpoint:' + row['endpoint_kind'])
    if selection['namespace'] == 'literature_gel_component_cells':
        qualifications.extend(('display_measurement_not_calibrated_molecular_occupancy',
                               'display_roi_alternatives_are_not_sampling_variance'))
    if selection['namespace'] == 'literature_partner_cells':
        qualifications.append('partner_change_and_nonpartner_control_scope_retained')
    qualifications.extend(nested_qualifications)
    if row.get('kind') == 'conditional':
        qualifications.append('conditional_reader_interpretation_unresolved')
    if row.get('source_kind') == 'synthetic_fixture' or any(v in ('synthetic', 'synthetic_fixture') for v in input_origins):
        origin = 'synthetic'
        qualifications.append('contains_synthetic_inputs')
    elif 'proposed' in input_origins:
        origin = 'proposed'
        qualifications.append('contains_proposed_inputs')
    elif 'graph_derived' in input_origins:
        origin = 'graph_derived'
        qualifications.append('contains_graph_derived_inputs')
    normalized = {'value': value, 'unit': unit, 'status': status, 'reason': reason,
        'measurement_keys': list(dict.fromkeys(keys)), 'source_refs': list(dict.fromkeys(refs)),
        'origin': origin, 'native_component': selection['namespace'] + ':' + selection['component'],
        'qualifications': list(dict.fromkeys(qualifications))}
    if native_bound is not None and status == 'bounded':
        normalized['bound'] = native_bound
    return normalized, row


def _support(reference, *, read_record, sources, hypothesis=False):
    record = read_record(reference)
    if not isinstance(record, dict) or record.get('id') != reference:
        raise ContractError('assay_grading_support_not_received')
    if hypothesis:
        if record.get('record_type') != 'hypothesis':
            raise ContractError('assay_grading_assertion_required')
        return record
    anchor = record.get('anchor')
    if record.get('record_type') != 'reference' or not isinstance(anchor, dict):
        raise ContractError('assay_grading_anchored_support_required')
    if record.get('source_ref') not in (None, anchor['source_ref']):
        raise ContractError('assay_grading_support_source_mismatch')
    original = sources.source(anchor['source_ref'], 'original')
    representation = 'original' if original['artifact_ref'] == anchor['artifact_ref'] else 'text'
    actual = sources.witness({k: anchor[k] for k in ('source_ref', 'start', 'end', 'quote')} |
                             {'representation': representation}, 'interpretation.support')
    if actual['artifact_ref'] != anchor['artifact_ref']:
        raise ContractError('assay_grading_support_artifact_mismatch')
    return record


def read_assay_grading_inputs(arguments, *, read_source, read_cells, read_record, read_database_request=None):
    """Authenticate operands/support; retain unknowns instead of default scores."""
    args = deepcopy(arguments)
    validate_schema(args, assay_grading_population_schema())
    sources = _Sources(read_source)
    sources.source(args['source_ref'], 'original')
    if 'experiment_ref' in args:
        experiment = _support(args['experiment_ref'], read_record=read_record, sources=sources)
        if experiment.get('reference_type') != 'assay':
            raise ContractError('assay_grading_experiment_reference_required')
    _support(args['assertion_ref'], read_record=read_record, sources=sources, hypothesis=True)
    for meaning in args['interpretations'].values():
        for ref in meaning['support_refs']:
            _support(ref, read_record=read_record, sources=sources)
    if args['prediction_model'] is not None:
        for ref in args['prediction_model']['support_refs']:
            _support(ref, read_record=read_record, sources=sources)
    quantities = {}; native = {}
    for role, selection in args['quantities'].items():
        if selection is None:
            quantities[role] = None
        elif selection['kind'] == 'source_number':
            quantities[role] = _literal(selection, sources)
            if args['source_kind'] == 'synthetic_fixture' and selection['number']['witness']['source_ref'] == args['source_ref']:
                quantities[role]['origin'] = 'synthetic'
        elif selection['kind'] == 'database_measurement':
            from .experimental_database_measurements import read_measurement
            quantities[role] = read_measurement(selection, sources=sources, read_record=read_record,
                                               read_database_request=read_database_request, role=role)
        else:
            quantities[role], native[role] = _component(selection, read_cells)
    # Known-variance likelihood must not silently upgrade estimated uncertainty
    # or allow an activity-spike response to become reporter recovery.
    variance = native.get('effect_variance', {})
    model = args['prediction_model']
    if model and model['variance_interpretation'] == 'known':
        if (any(v in ('estimated_covariance', 'unknown_covariance') for v in
                (quantities['effect_variance'] or {}).get('qualifications', ())) or
                variance.get('contribution', {}).get('variance_meaning', '').startswith('estimated_')):
            raise ContractError('assay_grading_known_variance_conflicts_with_reader')
    recovery = native.get('recovery', {})
    if recovery.get('control_kind') not in (None, 'reporter_standard'):
        quantities['recovery'].update(value=None, status='unavailable', reason='enzyme_spike_is_not_reporter_recovery')
    effect = args['quantities']['effect']
    if effect and effect['kind'] == 'received_component':
        namespace = effect['namespace']
        if namespace == 'literature_completion_time_cells' and args['quantity_kind'] not in ('completion_time', 'completion_time_ratio'):
            raise ContractError('assay_grading_completion_time_is_not_rate')
        if namespace == 'literature_product_partition_cells' and args['assay_type'] != 'product_distribution':
            raise ContractError('assay_grading_partition_is_not_rate_or_attribution')
        if namespace in EFFECT_ROUTES:
            assay_type, allowed = EFFECT_ROUTES[namespace]
            component = native['effect'].get('component', effect['component'])
            binding_display = (namespace == 'literature_gel_component_cells'
                and args['assay_type'] == 'ligand_binding' and args['quantity_kind'] == 'band_display_fraction'
                and component in ('shifted_display_fraction', 'protein_associated_display_shift',
                    'competitor_residual_display_fraction', 'displaced_display_fraction',
                    'factorized_competitor_sensitive_shift', 'direct_competitor_sensitive_shift'))
            transport_km = (namespace == 'literature_kinetic_cells'
                and args['assay_type'] == 'transport_response' and args['quantity_kind'] == 'transport_parameter'
                and component in ('numerator_parameter', 'denominator_parameter')
                and native['effect'][component.removesuffix('_parameter')]['parameter_kind'] == 'Km')
            if not (binding_display or transport_km) and (
                    args['assay_type'] != assay_type or args['quantity_kind'] not in allowed.get(component, ())):
                raise ContractError('assay_grading_native_quantity_mismatch')
    result = {k: deepcopy(args[k]) for k in ('assay_type', 'assertion_ref', 'quantity_kind', 'interpretations', 'prediction_model')}
    result.update(version=INPUT_VERSION, quantities=quantities)
    validate_schema(result, assay_grading_input_schema())
    return result


__all__ = ['SOURCE_SCHEMAS', 'source_schema', 'assay_grading_population_schema', 'read_assay_grading_inputs']
