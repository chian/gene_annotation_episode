"""Source relationships and possessed saved operands for within-assay arithmetic.

Scientific meanings are explicit episode interpretations. A selected component
is authorized through its own repository's exact fact view; a source reference
alone never grants the private numerical contents of an upstream child sheet.
"""
from copy import deepcopy
from fractions import Fraction
import json
import math

from .domain import REF, identity, obj, validate_schema
from .literature_assay_inputs import (
    ASSAY_LITERAL_FIELDS, ARRANGEMENTS, ENDPOINTS, SOURCE_KINDS, PRIMITIVE_ORDER,
    _Sources, _interpretation, _keys, _nullable, _numeric, _witness_schema,
    assay_arguments_schema,
)
from .literature_experimental_contracts import ExperimentalContractError

VERSION = 'a105_compiled_assay_inputs_v1'
ROLES = PRIMITIVE_ORDER
UNITS = dict(q='uM/min', g='uM/min', k='dimensionless', E='uM', u='uM/min', v='uM/min')
NS_ASSAY = 'literature_assay_cells'
NS_OPTICAL = 'literature_optical_cells'
NS_RECOVERY = 'literature_calibration_recovery_cells'
NS_ACTIVE = 'literature_active_site_cells'
NS_AMOUNT = 'literature_amount_cells'
NS_NATIVE = 'literature_rate_source_meaning_cells'
NS_REPLICATE = 'literature_rate_replicate_cells'
RATE_NAMES = ('reference_rate', 'test_rate', 'rate_difference')
ALLOWLIST = {
    'q': {NS_ASSAY: ('net_rate', 'corrected_activity'), NS_OPTICAL: ('net_rate',),
          NS_NATIVE: RATE_NAMES, NS_REPLICATE: RATE_NAMES},
    'g': {NS_ASSAY: ('contaminant_rate',), NS_NATIVE: RATE_NAMES, NS_REPLICATE: RATE_NAMES},
    'k': {NS_ASSAY: ('recovery',), NS_RECOVERY: ('recovery',)},
    'E': {NS_ASSAY: ('protein_amount',), NS_ACTIVE: ('active_site_concentration', 'total_monomer_concentration'),
          NS_AMOUNT: ('numerator_amount', 'denominator_amount')},
    'u': {NS_ASSAY: ('condition_test_rate',), NS_NATIVE: RATE_NAMES[:2], NS_REPLICATE: RATE_NAMES[:2]},
    'v': {NS_ASSAY: ('condition_reference_rate',), NS_NATIVE: RATE_NAMES[:2], NS_REPLICATE: RATE_NAMES[:2]},
}
LINKS = {
    'q': ('net_background_corrected_assay_endpoint', 'already_normalized_assay_activity'),
    'g': ('additional_contaminant_contribution',),
    'k': ('applicable_reporter_standard',),
    'E': ('same_assay_active_molecules', 'same_assay_total_molecules'),
    'u': ('test_nuisance_control_excludes_intended_change',),
    'v': ('reference_nuisance_control_excludes_intended_change',),
}
LINK_LIMITS = ('different_assay_or_endpoint', 'unknown', 'conflicting')
STAGES = ('background', 'contaminant', 'recovery', 'molecule_amount', 'nuisance_condition')
STAGE_VALUES = ('not_applied', 'already_applied', 'unknown', 'conflicting')
RESIDUAL_LINKS = ('additional_corrected_scale_variance', 'different_or_already_included', 'unknown', 'conflicting')


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def interpretation_schema(values):
    return obj({'value': {'enum': list(values)}, 'witnesses': {'type': 'array', 'items': _witness_schema()}})


def selector_schema(role=None):
    allowed = ALLOWLIST[role] if role else {ns: tuple(dict.fromkeys(
        name for choices in ALLOWLIST.values() for name in choices.get(ns, ())))
        for ns in dict.fromkeys(ns for choices in ALLOWLIST.values() for ns in choices)}
    return {'anyOf': [obj({'namespace': {'const': ns}, 'sheet_ref': deepcopy(REF),
        'component': {'enum': list(names)}}) for ns, names in allowed.items()]}


def compiled_assay_population_schema():
    props = assay_arguments_schema()['properties']
    return obj({'source_ref': deepcopy(REF), 'source_kind': {'enum': list(SOURCE_KINDS)},
        'assay': deepcopy(props['assay']),
        'operands': obj({role: _nullable(selector_schema(role)) for role in ROLES}),
        'relationships': obj({role: interpretation_schema((*LINKS[role], *LINK_LIMITS)) for role in ROLES}),
        'correction_stages': obj({name: interpretation_schema(STAGE_VALUES) for name in STAGES}),
        'covariance_source_ref': _nullable(deepcopy(REF)),
        'distinct_residual_variance': deepcopy(props['distinct_residual_variance']),
        'residual_relationship': interpretation_schema(RESIDUAL_LINKS),
        'variance_status': {'enum': ['known', 'estimated', 'unknown']},
        'observation_model': {'enum': ['none', 'known_normal_nonnegative_presence']},
        'model_witnesses': {'type': 'array', 'items': _witness_schema()}})


def source_schema(namespace):
    if namespace == NS_ASSAY:
        from .literature_assay_storage import assay_cells_schema
        return assay_cells_schema()
    if namespace == NS_OPTICAL:
        from .literature_optical_storage import optical_cells_schema
        return optical_cells_schema()
    if namespace == NS_RECOVERY:
        from .literature_calibration_recovery_storage import calibration_recovery_cells_schema
        return calibration_recovery_cells_schema()
    if namespace == NS_ACTIVE:
        from .literature_active_site_storage import active_site_cells_schema
        return active_site_cells_schema()
    if namespace == NS_AMOUNT:
        from .literature_amount_storage import amount_cells_schema
        return amount_cells_schema()
    if namespace == NS_NATIVE:
        from .literature_rate_meaning_delivery import rate_source_meaning_cells_schema
        return rate_source_meaning_cells_schema()
    if namespace == NS_REPLICATE:
        from .literature_rate_replicate_storage import rate_replicate_cells_schema
        return rate_replicate_cells_schema()
    _fail('unsupported_compilation_namespace', 'namespace')


def _point_reason(row):
    if row.get('approximate'):
        return 'approximate_operand_requires_unimplemented_compilation'
    if row.get('status') not in ('populated', 'point') or row.get('value') is None:
        if row.get('status') == 'bounded' or row.get('bound') not in (None, 'none'):
            return 'bounded_operand_compilation_unimplemented'
        return 'selected_component_unavailable'
    if row.get('bound') not in (None, 'none'):
        return 'bounded_operand_compilation_unimplemented'
    value = row['value']
    if type(value) not in (int, float) or not math.isfinite(value):
        _fail('finite_number_required', 'component.value')
    return None


def _intrinsic_reason(role, selector, row):
    namespace, component = selector['namespace'], selector['component']
    if role == 'k' and namespace == NS_RECOVERY:
        if row['control_kind'] != 'reporter_standard':
            return ('enzyme_activity_spike_is_not_reporter_recovery' if row['control_kind'] == 'enzyme_activity_spike'
                    else 'reporter_recovery_meaning_' + row['control_kind'])
        if row['applicability'] != 'same_matrix_same_endpoint_supported':
            return 'recovery_applicability_' + row['applicability']
        if row['interpretation_scope_unavailable_reason'] is not None:
            return 'recovery_control_scope_unavailable'
    if role == 'E' and namespace == NS_ACTIVE:
        if row['rate_application_status'] == 'not_applied_already_active_normalized':
            return 'amount_correction_already_applied'
        meanings = {name: value['value'] for name, value in row['interpretations'].items()}
        if meanings['amount_linkage'] != 'same_preparation_and_assay':
            return 'active_amount_linkage_' + meanings['amount_linkage']
        if component == 'active_site_concentration' and any(meanings[name] != expected for name, expected in (
                ('active_estimate_meaning', 'titrated_active_sites'), ('site_stoichiometry', 'one_site_per_monomer'),
                ('titrant_to_site_stoichiometry', 'reported_one_to_one'), ('molecular_basis', 'per_monomer'))):
            return 'active_sites_to_molecules_not_established'
    if role == 'E' and namespace == NS_AMOUNT:
        selected = row['numerator' if component == 'numerator_amount' else 'denominator']
        if selected['qualification'] in ('unknown', 'conflicting') or selected['basis_status'] in ('unknown', 'conflicting'):
            return 'molar_amount_basis_not_established'
    if namespace == NS_ASSAY and row.get('endpoint_kind') in ('growth', 'abundance', 'ligand_binding', 'other_measured_endpoint'):
        return 'endpoint_requires_different_model'
    return None


def _dependencies(selector, row, *, read_record):
    """Select mean dependencies, excluding neighboring arms/context/spreads.

    Different opaque key namespaces are never evidence of independence. Native
    projections without numerical operand anchors retain that explicit unknown.
    """
    namespace, component = selector['namespace'], selector['component']
    anchors, opaque, refs = [], [], []
    def anchor(value):
        if isinstance(value, dict) and all(name in value for name in ('artifact_ref', 'start', 'end')):
            item = {name: value[name] for name in ('artifact_ref', 'start', 'end')}
            if item not in anchors:
                anchors.append(item)
    if namespace == NS_ASSAY:
        refs.extend(row['input_measurement_refs'])
    elif namespace == NS_OPTICAL:
        for role in ('sample_slope', 'blank_slope', 'epsilon', 'path_length'):
            ref = row['operands'][role]['measurement_ref']
            if ref:
                refs.append(ref)
    elif namespace == NS_AMOUNT:
        role = 'numerator' if component == 'numerator_amount' else 'denominator'
        ref = row[role]['measurement_ref']
        if ref:
            refs.append(ref)
    elif namespace == NS_ACTIVE:
        for operand in row['operands']:
            reading = operand['reading']
            if reading is not None:
                anchor(reading['number'])
            elif operand['measurement_key']:
                opaque.append(operand['measurement_key'])
    elif namespace == NS_RECOVERY:
        opaque.extend(row['input_measurement_keys'])
    elif namespace == NS_REPLICATE:
        roles = ('reference',) if component == 'reference_rate' else ('test',) if component == 'test_rate' else ('reference', 'test')
        for role in roles:
            observed = row['groups'][role].get('observed')
            if observed:
                opaque.extend(identity('reported_rate_observation', {'source': row['evidence_source_ref'],
                    'experiment': row.get('observed_experiment'), 'observation': oid})
                    for unit in observed['units'] for oid in unit['observation_ids'])
    for reference in dict.fromkeys(refs):
        record = read_record(reference)
        anchor(record.get('anchor'))
        if record.get('anchor') is None:
            opaque.append(reference)
    canonical = [identity('physical_source_span', item) for item in anchors]
    return {'canonical_physical_keys': list(dict.fromkeys(canonical)),
            'recorded_dependency_keys': list(dict.fromkeys(opaque)),
            'physical_identity_status': 'partly_canonical' if canonical else 'cross_component_identity_unknown'}


def _quantity(selector, row, role, *, read_record):
    point_reason = _point_reason(row)
    reason = point_reason or _intrinsic_reason(role, selector, row)
    unit = row.get('unit'); multiplier = Fraction(1)
    if role == 'k' and unit == 'fraction':
        canonical_unit = 'dimensionless'
    elif role == 'E' and unit == 'nM':
        canonical_unit, multiplier = 'uM', Fraction(1, 1000)
    else:
        canonical_unit = unit
    native_normalized = role == 'q' and unit == 'per_min'
    if canonical_unit != UNITS[role] and not native_normalized:
        reason = reason or 'operand_unit_incompatible_with_compilation'
    value = None
    if point_reason is None and (canonical_unit == UNITS[role] or native_normalized):
        exact = Fraction(str(row['value'])) * multiplier
        try:
            value = float(exact)
        except (OverflowError, ValueError):
            reason = 'numerical_model_range'
        if value is not None and (not math.isfinite(value) or value == 0 and exact != 0):
            value, reason = None, 'numerical_model_range'
    deps = _dependencies(selector, row, read_record=read_record)
    selector_key = identity('selected_source_component', selector)
    raw_point = selector['namespace'] in (NS_ASSAY, NS_AMOUNT) or (selector['namespace'] == NS_ACTIVE and selector['component'] == 'active_site_concentration') or (selector['namespace'] == NS_NATIVE and selector['component'] in ('reference_rate', 'test_rate'))
    if raw_point and len(deps['canonical_physical_keys']) == 1:
        quantity_key = identity('compilation_quantity', {'physical': deps['canonical_physical_keys'][0], 'unit': canonical_unit})
    else:
        quantity_key = selector_key
    return {'selection': deepcopy(selector), 'row': deepcopy(row), 'value': value, 'unit': canonical_unit,
        'native_normalized': native_normalized, 'unavailable_reason': reason,
        'component_key': selector_key, 'quantity_key': quantity_key, **deps}


def _covariance(reference, operands, sources):
    if reference is None:
        return None
    raw = sources.source(reference, 'original')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail('duplicate_json_key', 'covariance_source_ref')
            result[key] = value
        return result
    try:
        data = json.loads(raw['content'].decode('utf8'), object_pairs_hook=pairs,
            parse_float=lambda token: _numeric(token, 'covariance'),
            parse_constant=lambda _token: _fail('finite_number_required', 'covariance'))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ExperimentalContractError('covariance_json_required', 'covariance_source_ref') from error
    _keys(data, ('version', 'primitive_order', 'operand_keys', 'primitive_units', 'dependency_keys',
                 'covariance', 'origin', 'basis'), 'covariance')
    if data['version'] != 'a105_compiled_assay_covariance_v1' or data['primitive_order'] != list(ROLES):
        _fail('compiled_covariance_order_or_version_mismatch', 'covariance')
    if any(operands[role] is None for role in ROLES):
        _fail('complete_covariance_owners_required', 'covariance')
    if data['operand_keys'] != [operands[role]['quantity_key'] for role in ROLES]:
        _fail('compiled_covariance_owner_mismatch', 'covariance.operand_keys')
    if (data['primitive_units'] != [operands[role]['unit'] for role in ROLES]
            or any(operands[role]['unit'] != UNITS[role] for role in ROLES)):
        _fail('compiled_covariance_unit_mismatch', 'covariance.primitive_units')
    dependencies = [list(dict.fromkeys((*operands[role]['canonical_physical_keys'],
                                       *operands[role]['recorded_dependency_keys']))) for role in ROLES]
    if data['dependency_keys'] != dependencies:
        _fail('compiled_covariance_dependency_mismatch', 'covariance.dependency_keys')
    if data['basis'] != 'joint_covariance_of_canonical_compilation_operands' or data['origin'] not in ('reported', 'derived', 'synthetic'):
        _fail('compiled_covariance_basis_mismatch', 'covariance')
    return {'source_ref': reference, 'artifact_ref': raw['artifact_ref'], 'data': data}


def read_compiled_assay_inputs(arguments, *, read_source, read_component, read_record):
    """Read scientific context and exact authorized numerical component rows."""
    args = deepcopy(arguments); validate_schema(args, compiled_assay_population_schema())
    sources = _Sources(read_source); original = sources.source(args['source_ref'], 'original')
    assay = {}
    for name in ASSAY_LITERAL_FIELDS:
        selected = args['assay'][name]
        w = sources.witness(selected, 'assay.' + name) if selected is not None else None
        assay[name] = {'value': w['quote'], 'witness': w} if w else None
    for name, choices in (('endpoint', ENDPOINTS), ('arrangement', ARRANGEMENTS)):
        assay[name] = _interpretation(args['assay'][name], choices, sources, 'assay.' + name)
    relationships = {role: _interpretation(args['relationships'][role], (*LINKS[role], *LINK_LIMITS), sources, 'relationships.' + role) for role in ROLES}
    stages = {name: _interpretation(args['correction_stages'][name], STAGE_VALUES, sources, 'correction_stages.' + name) for name in STAGES}
    operands = {}
    for role, selector in args['operands'].items():
        if selector is None:
            operands[role] = None
            continue
        rows = read_component(selector)
        if len(rows) != 1 or rows[0]['sheet_ref'] != selector['sheet_ref'] or rows[0]['component'] != selector['component']:
            _fail('selected_component_not_received', 'operands.' + role)
        validate_schema(rows, source_schema(selector['namespace']))
        operands[role] = _quantity(selector, rows[0], role, read_record=read_record)
    residual = args['distinct_residual_variance']
    residual = sources.measurement(residual, 'distinct_residual_variance', 'distinct_residual_variance') if residual else None
    residual_link = _interpretation(args['residual_relationship'], RESIDUAL_LINKS, sources, 'residual_relationship')
    if residual is not None:
        witness = residual['witness']
        residual_key = identity('physical_source_span', {
            'artifact_ref': witness['artifact_ref'],
            'start': witness['start'] + len(witness['quote'][:residual['number_start']].encode()),
            'end': witness['start'] + len(witness['quote'][:residual['number_end']].encode())})
        if any(operand is not None and residual_key in operand['canonical_physical_keys'] for operand in operands.values()):
            _fail('residual_reuses_selected_mean_measurement', 'distinct_residual_variance')

    witnesses = [sources.witness(w, 'model_witnesses') for w in args['model_witnesses']]
    if (args['variance_status'] != 'unknown' or args['observation_model'] != 'none') and not witnesses:
        _fail('model_witness_required', 'model_witnesses')
    covariance = _covariance(args['covariance_source_ref'], operands, sources)
    return {'version': VERSION, 'source_ref': args['source_ref'], 'artifact_ref': original['artifact_ref'],
        'source_kind': args['source_kind'], 'assay': assay, 'operands': operands,
        'relationships': relationships, 'correction_stages': stages, 'covariance_source': covariance,
        'distinct_residual_observation': residual, 'residual_relationship': residual_link,
        'variance_status': args['variance_status'], 'observation_model': args['observation_model'],
        'model_witnesses': witnesses, 'source_refs': list(sources.references)}


__all__ = ['VERSION', 'ROLES', 'UNITS', 'ALLOWLIST', 'LINKS', 'LINK_LIMITS', 'STAGES', 'STAGE_VALUES',
    'compiled_assay_population_schema', 'selector_schema', 'source_schema', 'read_compiled_assay_inputs']
