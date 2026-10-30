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
VERSION_V2 = 'a105_compiled_assay_inputs_v2'
POPULATION_V2 = 'a105_compiled_assay_population_v2'
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


def compiled_assay_population_schema(version=1):
    props = assay_arguments_schema()['properties']
    schema = obj({'source_ref': deepcopy(REF), 'source_kind': {'enum': list(SOURCE_KINDS)},
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
    if version == 2:
        del schema['properties']['covariance_source_ref']
        schema['properties'].update(population_version={'const': POPULATION_V2},
            covariance_source_refs={'type': 'array', 'items': deepcopy(REF), 'uniqueItems': True})
        schema['required'] = list(schema['properties'])
    elif version != 1:
        raise ValueError('unsupported_compiled_assay_population_version')
    return schema


def compiled_assay_operation_schema():
    return {'anyOf': [compiled_assay_population_schema(), compiled_assay_population_schema(2)]}


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


def _covariance_v2(references, operands, relationships, sources):
    """Read actual joint blocks; marginal blocks never imply missing cross terms."""
    import numpy as np
    from .literature_compiled_assay_calculations import _role_reason
    blocks, owner_facts, pair_facts, owner_statuses = [], {}, {}, {}
    eligibility = {'operands': operands, 'relationships': relationships}
    for reference in references:
        raw = sources.source(reference, 'original')
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    _fail('duplicate_json_key', 'covariance_source_refs')
                result[key] = value
            return result
        try:
            data = json.loads(raw['content'].decode('utf8'), object_pairs_hook=pairs,
                parse_float=lambda token: _numeric(token, 'covariance'),
                parse_constant=lambda token: _fail('finite_number_required', 'covariance'))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ExperimentalContractError('covariance_json_required', 'covariance_source_refs') from error
        _keys(data, ('version', 'primitive_order', 'operand_keys', 'primitive_units', 'dependency_keys',
                     'covariance', 'origin', 'basis', 'variance_status'), 'covariance')
        order = data['primitive_order']
        if (data['version'] != 'a105_compiled_assay_covariance_v2' or not isinstance(order, list)
                or not order or any(type(role) is not str or role not in ROLES for role in order)
                or len(set(order)) != len(order)):
            _fail('compiled_covariance_order_or_version_mismatch', 'covariance')
        if any(operands[role] is None or _role_reason(eligibility, role) is not None for role in order):
            _fail('eligible_covariance_owners_required', 'covariance')
        owners = [operands[role]['quantity_key'] for role in order]
        if data['operand_keys'] != owners:
            _fail('compiled_covariance_owner_mismatch', 'covariance.operand_keys')
        if (data['primitive_units'] != [operands[role]['unit'] for role in order]
                or any(operands[role]['unit'] != UNITS[role] for role in order)):
            _fail('compiled_covariance_unit_mismatch', 'covariance.primitive_units')
        deps = [list(dict.fromkeys((*operands[role]['canonical_physical_keys'],
                                   *operands[role]['recorded_dependency_keys']))) for role in order]
        if data['dependency_keys'] != deps:
            _fail('compiled_covariance_dependency_mismatch', 'covariance.dependency_keys')
        if (data['basis'] != 'joint_covariance_of_canonical_compilation_operands'
                or data['origin'] not in ('reported', 'derived', 'synthetic')):
            _fail('compiled_covariance_basis_mismatch', 'covariance')
        status = data['variance_status']
        if status not in ('known', 'estimated', 'unknown'):
            _fail('unsupported_variance_status', 'covariance.variance_status')
        matrix = data['covariance']; n = len(order)
        if matrix is None and status != 'unknown':
            _fail('component_joint_covariance_required', 'covariance')
        if matrix is not None:
            if not isinstance(matrix, list) or len(matrix) != n or any(not isinstance(row, list) or len(row) != n for row in matrix):
                _fail('named_subset_covariance_shape_mismatch', 'covariance')
            for row in matrix:
                for value in row:
                    try:
                        finite = type(value) in (int, float) and math.isfinite(value)
                    except OverflowError:
                        finite = False
                    if not finite:
                        _fail('finite_number_required', 'covariance')
            # Compare the retained numbers before float projection: distinct
            # large JSON integers can round to the same binary float.
            if any(matrix[i][j] != matrix[j][i] for i in range(n) for j in range(i)):
                _fail('symmetric_covariance_required', 'covariance')
            array = np.asarray(matrix, dtype=float)
            if not np.array_equal(array, array.T):
                _fail('symmetric_covariance_required', 'covariance')
            scale = float(np.max(np.abs(array)))
            try:
                eig = np.linalg.eigvalsh(array / scale) if scale else np.zeros(n)
            except np.linalg.LinAlgError:
                _fail('covariance_eigendecomposition_failed', 'covariance')
            if (np.any(np.diag(array) < 0) or not np.all(np.isfinite(eig))
                    or float(np.min(eig)) < -64 * np.finfo(float).eps * n):
                _fail('positive_semidefinite_covariance_required', 'covariance')
            for i in range(n):
                for j in range(i):
                    if owners[i] == owners[j] and (matrix[i] != matrix[j]
                            or any(row[i] != row[j] for row in matrix)):
                        _fail('shared_measurement_covariance_mismatch', 'covariance')
        for i, role in enumerate(order):
            owner = owners[i]
            fact = (operands[role]['value'], operands[role]['unit'], deps[i])
            if owner in owner_facts and owner_facts[owner] != fact:
                _fail('shared_compilation_quantity_mismatch', 'covariance')
            if owner in owner_statuses and owner_statuses[owner] != status:
                _fail('overlapping_covariance_status_ambiguity', 'covariance')
            owner_facts[owner], owner_statuses[owner] = fact, status
            if matrix is not None:
                for j, other in enumerate(owners):
                    key = (owner, other)
                    if key in pair_facts and pair_facts[key] != matrix[i][j]:
                        _fail('overlapping_covariance_entry_mismatch', 'covariance')
                    pair_facts[key] = matrix[i][j]
        blocks.append({'source_ref': reference, 'artifact_ref': raw['artifact_ref'], 'data': data})
    return blocks


def read_compiled_assay_inputs(arguments, *, read_source, read_component, read_record):
    """Read scientific context and exact authorized numerical component rows."""
    args = deepcopy(arguments)
    v2 = args.get('population_version') == POPULATION_V2
    validate_schema(args, compiled_assay_population_schema(2 if v2 else 1))
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
    covariance = None if v2 else _covariance(args['covariance_source_ref'], operands, sources)
    blocks = _covariance_v2(args['covariance_source_refs'], operands, relationships, sources) if v2 else None
    return {'version': VERSION_V2 if v2 else VERSION, 'source_ref': args['source_ref'], 'artifact_ref': original['artifact_ref'],
        'source_kind': args['source_kind'], 'assay': assay, 'operands': operands,
        'relationships': relationships, 'correction_stages': stages, 'covariance_source': covariance,
        'distinct_residual_observation': residual, 'residual_relationship': residual_link,
        'variance_status': args['variance_status'], 'observation_model': args['observation_model'],
        'model_witnesses': witnesses, 'source_refs': list(sources.references),
        **({'covariance_sources': blocks} if v2 else {})}


__all__ = ['VERSION', 'VERSION_V2', 'POPULATION_V2', 'ROLES', 'UNITS', 'ALLOWLIST', 'LINKS', 'LINK_LIMITS', 'STAGES', 'STAGE_VALUES',
    'compiled_assay_population_schema', 'compiled_assay_operation_schema', 'selector_schema', 'source_schema', 'read_compiled_assay_inputs']

# Prospective common-assessment branch. Deliberately not added to the selected
# operation catalog here: storage, typed delivery and rendering have other owners.
COMMON_REQUEST = 'a105_common_assessment_request_v1'
COMMON_POPULATION = 'a105_common_assessment_population_v1'
COMMON_INPUTS = 'a105_common_assessment_inputs_v1'
COMMON_ARMS = ('reference', 'test')
COMMON_BASE_ROLES = ('product', 'reporter', 'kcat', 'Km', 'Kd', 'free_substrate',
                     'background', 'recovery', 'active_fraction', 'nuisance_response')
COMMON_ROLES = tuple(base + '_' + arm for base in COMMON_BASE_ROLES for arm in COMMON_ARMS)
COMMON_CONTEXT = ('organism', 'molecule', 'construct', 'substrate', 'product_or_ligand', 'system', 'conditions')
COMMON_ARM_CONTEXT = ('construct', 'assay', 'endpoint', 'denominator', 'preparation', 'conditions', 'sampling_unit', 'intended_change', 'additional_differences')
COMMON_GROUPS = ('product', 'reporter', 'kinetic', 'binding', 'correction')
COMMON_LINKS = ('same_estimand', 'compatible_supported', 'different_with_declared_model', 'incompatible', 'unknown', 'conflicting')
COMMON_ASSUMPTIONS = ('equilibrium', 'one_site', 'free_substrate_treatment', 'binding_catalysis_applicability',
    'turnover_proportional_to_occupancy', 'fixed_post_binding_rate', 'equal_recovery', 'equal_active_fraction', 'equal_nuisance_response')
COMMON_MODEL_STATUSES = ('supported', 'stipulated_sensitivity', 'unknown', 'conflicting')
COMMON_UNITS = dict(product='per_min', reporter='per_min', kcat='per_min', Km='uM', Kd='uM',
    free_substrate='uM', background='per_min', recovery='dimensionless', active_fraction='dimensionless', nuisance_response='dimensionless')
COMMON_PARAMETER_KINDS = dict(Kd='reported_spectral_binding_Kd', free_substrate='free_substrate_concentration',
    background='same_scale_other_contribution_rate', recovery='applicable_reporter_recovery',
    active_fraction='active_molecules_per_nominal_molecule', nuisance_response='nuisance_response_excluding_intended_change')
COMMON_REASONS = ('estimate_not_selected', 'source_number_unavailable', 'source_unit_unsupported',
    'native_nondetection_not_point', 'bounded_estimate_unsupported', 'approximate_estimate_unsupported',
    'source_parameter_meaning_unknown', 'source_parameter_meaning_conflicting', 'native_component_unavailable',
    'received_parameter_kind_mismatch', 'received_parameter_unit_mismatch', 'received_construct_unresolved',
    'source_construct_mismatch', 'normalization_relationship_unknown', 'endpoint_relationship_unknown',
    'relationship_incompatible', 'relationship_conflicting', 'subject_relationship_unresolved',
    'model_not_selected', 'model_assumption_unknown', 'model_assumption_conflicting',
    'positive_operand_required', 'zero_denominator', 'numerical_model_range', 'joint_covariance_not_selected',
    'joint_covariance_incomplete', 'covariance_status_unknown', 'positive_variance_required',
    'correction_factorization_unresolved', 'correction_applicability_unresolved',
    'correction_conversion_unimplemented', 'exact_source_conversion_unimplemented',
    'unrequested_numerical_scope_unresolved', 'no_independent_replication_inferred')


def _common_array(schema, unique=False):
    return {'type': 'array', 'items': deepcopy(schema), **({'uniqueItems': True} if unique else {})}


def _common_exact_schema():
    return obj({'numerator': {'type': 'string', 'pattern': '^-?[0-9]+$'},
        'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}})


def _common_meaning_schema(values):
    return interpretation_schema(values)


def _common_selection_schema():
    from .literature_partner_source_fields import number_selector_schema
    native = {'anyOf': [obj({'kind': {'const': 'received_component'}, 'namespace': {'const': ns},
        'sheet_ref': deepcopy(REF), 'component': {'enum': list(names)}}) for ns, names in (
        ('literature_product_coupling_cells', ('reported_product_activity', 'reported_cofactor_activity')),
        ('literature_kinetic_cells', ('numerator_parameter', 'denominator_parameter')),
        ('literature_calibration_recovery_cells', ('recovery',)))]}
    parameter = obj({'kind': {'const': 'source_parameter'},
        'source_kind': {'enum': ['primary_source', 'supplied_model', 'synthetic_fixture']},
        'parameter_kind': _common_meaning_schema(tuple(COMMON_PARAMETER_KINDS.values())),
        'layout': {'enum': ['table', 'single_record']}, 'record': _nullable(_witness_schema()),
        'number': _nullable(number_selector_schema()), 'row_label': _witness_schema(),
        'quantity_label': _witness_schema(), 'unit': _witness_schema(),
        'semantics': _common_meaning_schema(('reported_point', 'reported_nondetection', 'unknown', 'conflicting')),
        'method': _nullable(_witness_schema()), 'assay': _nullable(_witness_schema()),
        'conditions': _nullable(_witness_schema()), 'normalization': _nullable(_witness_schema()),
        'population': _nullable(_witness_schema()),
        'physical_identity': _nullable(_witness_schema()),
        'reported_spread': _nullable(number_selector_schema())})
    return {'anyOf': [native, parameter]}


def common_assessment_population_schema():
    """Prospective closed scientific request, separate from episode TASK text."""
    from .literature_compiled_assay_calculations import COMMON_COMPONENTS
    links = obj({name: _common_meaning_schema(COMMON_LINKS)
        for name in ('endpoint', 'normalization', 'preparation', 'conditions')})
    model = obj({'kind': {'const': 'one_site_equilibrium'},
        'scope': {'enum': ['supported_physical', 'conditional_sensitivity']},
        'substrate_ownership': {'enum': ['shared_owner', 'separate_owners']},
        'substrate_uncertainty': {'enum': ['fixed_scenario', 'selected_estimate_covariance']},
        'assumptions': obj({name: _common_meaning_schema(COMMON_MODEL_STATUSES) for name in COMMON_ASSUMPTIONS})})
    return obj({'version': {'const': COMMON_REQUEST}, 'population_version': {'const': COMMON_POPULATION},
        'source_ref': deepcopy(REF), 'source_kind': {'enum': ['primary_source', 'synthetic_fixture']},
        'assertion': obj({**{name: _nullable(_witness_schema()) for name in COMMON_CONTEXT},
            'resolution': {'enum': ['identified_product_formation', 'saturation_turnover', 'low_substrate_efficiency', 'binding_occupancy_alternative']},
            'question': {'enum': ['existence', 'relative_effect', 'named_alternative']}}),
        'arms': obj({arm: obj({name: _nullable(_witness_schema()) for name in COMMON_ARM_CONTEXT}) for arm in COMMON_ARMS}),
        'subject_relationship': _common_meaning_schema(('same_construct_supported', 'intended_variant', 'different', 'unknown', 'conflicting')),
        'relationships': obj({group: deepcopy(links) for group in COMMON_GROUPS}),
        'product_reporter_relationship': _common_meaning_schema(('author_assigned_pair', 'different', 'unknown', 'conflicting')),
        'sampling_relationship': _common_meaning_schema(('shared_units', 'paired_units_supported', 'independent_units_supported', 'unknown', 'conflicting')),
        'estimates': obj({role: _nullable(_common_selection_schema()) for role in COMMON_ROLES}),
        'model': _nullable(model),
        'correction_factorization': _common_meaning_schema(COMMON_MODEL_STATUSES),
        'covariance_source_refs': _common_array(REF, True),
        'requested_cells': _common_array({'enum': list(COMMON_COMPONENTS)}, True)})


def _common_location_schema():
    return obj({'source_ref': deepcopy(REF), 'artifact_ref': deepcopy(REF),
        'representation': {'enum': ['original', 'text']},
        'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})


def common_assessment_inputs_schema():
    """Host-only retained inputs; not a parent return or a model-facing sheet."""
    estimate = obj({'role': {'enum': list(COMMON_ROLES)}, 'selection': _common_selection_schema(),
        'value': {'type': ['number', 'null']}, 'exact_value': _nullable(_common_exact_schema()),
        'native_value': {'type': ['number', 'null']}, 'native_exact_value': _nullable(_common_exact_schema()),
        'native_unit': {'type': ['string', 'null']},
        'unit': {'type': ['string', 'null']}, 'status': {'enum': ['point', 'unavailable']},
        'native_semantics': {'enum': ['reported_point', 'reported_nondetection', 'reported_negligible', 'unknown', 'conflicting']},
        'origin': {'enum': ['reported', 'derived', 'calculated', 'synthetic', 'proposed']},
        'numeric_origin': {'enum': ['received_exact_component', 'original_source_token', 'saved_canonical_decimal']},
        'owner_key': {'type': 'string'}, 'physical_owner_key': {'type': ['string', 'null']},
        'population_key': {'type': ['string', 'null']}, 'assay_key': {'type': ['string', 'null']}, 'dependency_keys': _common_array({'type': 'string'}, True),
        'locations': _common_array(_common_location_schema()),
        'source_missing_reasons': _common_array({'enum': list(COMMON_REASONS)}, True),
        'implementation_reasons': _common_array({'enum': list(COMMON_REASONS)}, True),
        'reported_spread': _nullable(obj({'exact_value': _nullable(_common_exact_schema()),
            'statistic': {'enum': ['unspecified', 'sd', 'sem']}, 'unit': {'type': ['string','null']}, 'location': _common_location_schema()}))})
    covariance = obj({'source_ref': deepcopy(REF), 'artifact_ref': deepcopy(REF),
        'roles': _common_array({'enum': list(COMMON_ROLES)}, True), 'owner_keys': _common_array({'type': 'string'}),
        'units': _common_array({'type': 'string'}), 'dependency_keys': _common_array(_common_array({'type': 'string'})),
        'matrix_exact': _nullable(_common_array(_common_array(_common_exact_schema()))),
        'variance_status': {'enum': ['known', 'estimated', 'unknown']}, 'origin': {'enum': ['reported', 'derived', 'synthetic']},
        'basis': {'const': 'joint_covariance_of_selected_estimates'}})
    return obj({'version': {'const': COMMON_INPUTS}, 'request': common_assessment_population_schema(),
        'estimates': obj({role: _nullable(estimate) for role in COMMON_ROLES}),
        'covariance_blocks': _common_array(covariance), 'source_refs': _common_array(REF, True),
        'source_artifacts': _common_array(obj({'source_ref': deepcopy(REF), 'representation': {'enum': ['original', 'text']}, 'artifact_ref': deepcopy(REF)})),
        'numerical_scope_locations': _common_array(_common_location_schema()),
        'component_snapshots': _common_array({'anyOf': [_common_snapshot_schema('literature_product_coupling_cells'),
                                                      _common_snapshot_schema('literature_kinetic_cells'),
                                                      _common_snapshot_schema('literature_calibration_recovery_cells')]})})


def _common_snapshot_schema(namespace):
    if namespace == 'literature_product_coupling_cells':
        from .literature_product_coupling_storage import product_coupling_cells_schema
        row = product_coupling_cells_schema()['items']
    elif namespace == 'literature_kinetic_cells':
        from .literature_kinetic_storage import kinetic_cells_schema
        row = kinetic_cells_schema()['items']
    else:
        from .literature_calibration_recovery_storage import calibration_recovery_cells_schema
        row = calibration_recovery_cells_schema()['items']
    return obj({'selection': _common_selection_schema(), 'row': row})


def _common_exact(value):
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def _common_q(value):
    result = Fraction(int(value['numerator']), int(value['denominator']))
    if _common_exact(result) != value:
        _fail('canonical_exact_fraction_required', 'common.exact_value')
    return result


def _common_float(value):
    try:
        result = float(value)
        return result if math.isfinite(result) and (result != 0 or value == 0) else None
    except (ValueError, OverflowError):
        return None


def _common_location(witness):
    return {name: witness[name] for name in ('source_ref', 'artifact_ref', 'representation', 'start', 'end')}


def _common_interpret(value, sources, field):
    result = _interpretation(value, (value['value'],), sources, field)
    needed = 0 if result['value'] in ('unknown',) else 2 if result['value'] == 'conflicting' else 1
    if len({(w['artifact_ref'], w['start'], w['end']) for w in result['witnesses']}) < needed:
        _fail('interpretation_witness_required', field)
    return result


def _common_visible(text):
    import html
    import re
    return html.unescape(re.sub(r'<[^>]+>', '', text)).strip()


def _common_source_estimate(role, selected, sources, request):
    from .literature_measurement_validation_inputs import _table_cells, _associate, _visible_span
    from .literature_kinetic_inputs import _number as read_spread
    from .literature_product_coupling_inputs import _number
    base, arm = role.rsplit('_', 1)
    if base not in COMMON_PARAMETER_KINDS or selected['parameter_kind']['value'] != COMMON_PARAMETER_KINDS[base]:
        _fail('common_parameter_role_mismatch', role)
    for name in ('parameter_kind', 'semantics'):
        _common_interpret(selected[name], sources, role + '.' + name)
    witnesses = {name: None if selected[name] is None else sources.witness(selected[name], role + '.' + name)
        for name in ('row_label', 'quantity_label', 'unit', 'record', 'method', 'assay', 'conditions', 'normalization', 'population', 'physical_identity')}
    origin = {'primary_source':'reported','supplied_model':'proposed','synthetic_fixture':'synthetic'}[selected['source_kind']]
    number = None if selected['number'] is None else _number(selected['number'], sources, origin)
    if base != 'free_substrate':
        construct = request['arms'][arm]['construct']
        if construct is None or _common_visible(construct['quote']) != _common_visible(witnesses['row_label']['quote']):
            _fail('common_source_construct_mismatch', role)
    label = _common_visible(witnesses['quantity_label']['quote'])
    import re
    if base == 'Kd' and re.fullmatch(r'K\s*[_ ]?d(?:\s*\([^)]*\))?', label, re.I) is None:
        _fail('spectral_Kd_column_meaning_required', role)
    if number is not None:
        numeric = {**number['selector']['witness'], 'start': number['number_start_bytes'], 'end': number['number_end_bytes']}
        for name in ('row_label', 'quantity_label', 'unit'):
            w = witnesses[name]
            _visible_span(sources, w, w['start'], w['end'], role+'.'+name)
            if (w['artifact_ref'], w['representation']) != (numeric['artifact_ref'], numeric['representation']):
                _fail('borrowed_source_quantity_witness', role)
        table, cells = _table_cells(sources, numeric)
        if selected['layout'] == 'table':
            cell = next((c for c in cells if c['start'] <= numeric['start'] < numeric['end'] <= c['end']), None)
            row = next((c for c in cells if c['start'] <= witnesses['row_label']['start'] < witnesses['row_label']['end'] <= c['end']), None)
            if table is None or cell is None or row is None or row['row'] != cell['row'] or max(row['columns']) >= min(cell['columns']):
                _fail('common_source_row_mismatch', role)
            _associate(number, witnesses['quantity_label'], sources, role+'.column')
            _associate(number, witnesses['unit'], sources, role+'.unit')
        else:
            record = witnesses['record']
            if table is not None or record is None or any(w is not None and
                    (w['artifact_ref'] != record['artifact_ref'] or not record['start'] <= w['start'] < w['end'] <= record['end'])
                    for w in (numeric, witnesses['row_label'], witnesses['quantity_label'], witnesses['unit'])):
                _fail('common_single_record_association_required', role)
            # A single-record layout is a narrow labelled field, not a paragraph
            # containing several unassociated quantities. Complete table cells
            # take the explicit table path above.
            rest = record['quote'].encode()
            for w in (numeric, witnesses['row_label'], witnesses['quantity_label'], witnesses['unit']):
                a, z = w['start']-record['start'], w['end']-record['start']
                rest = rest[:a] + b' '*(z-a) + rest[z:]
            if re.search(rb'(?<![A-Za-z0-9_])[0-9]+(?:\.[0-9]+)?', rest):
                _fail('ambiguous_common_single_record_numbers', role)
    unit_text = _common_visible(witnesses['unit']['quote']).replace('μ', 'u').replace('µ', 'u')
    unit_scales = {'M': Fraction(10**6), 'mM': Fraction(1000), 'uM': Fraction(1), 'nM': Fraction(1,1000)} if base in ('Kd','free_substrate') else (
        {'min−1': Fraction(1), 'min-1': Fraction(1), 'per_min': Fraction(1), 's-1': Fraction(60)} if base == 'background' else
        {'fraction': Fraction(1), 'dimensionless': Fraction(1), '%': Fraction(1,100)})
    scale = unit_scales.get(unit_text)
    from .literature_partner_source_fields import _unit_contexts
    uw=witnesses['unit'];before,after=_unit_contexts(sources,uw,0,len(uw['quote']))
    if before[-1:].isalpha() or before[-1:] in ('/','_','^') or after[:1].isalnum() or after[:1] in ('/','_','^','⁻'):
        _fail('partial_common_source_unit',role)
    if number is not None:
        nw=number['selector'];_,tail=_unit_contexts(sources,nw['witness'],nw['number_start'],nw['number_end'])
        tail=_common_visible(tail).lstrip()
        tail=re.sub(r'^(?:±|\+\s*/\s*-)\s*[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?\s*','',tail)
        explicit=re.match(r'(?:per_min|min[−-]1|s[−-]1|dimensionless|fraction|mM|uM|µM|μM|nM|M|%)(?![A-Za-z])',tail)
        if explicit and unit_scales.get(explicit.group().replace('µ','u').replace('μ','u'))!=scale:
            _fail('common_explicit_unit_mismatch',role)
    source_reasons, implementation = [], []
    if base == 'Kd' and witnesses['method'] is None: source_reasons.append('source_parameter_meaning_unknown')
    if number is None or number['native_exact_value'] is None: source_reasons.append('source_number_unavailable')
    if scale is None: implementation.append('source_unit_unsupported')
    semantics = selected['semantics']['value']
    if semantics in ('reported_nondetection',): source_reasons.append('native_nondetection_not_point')
    elif semantics != 'reported_point': source_reasons.append('source_parameter_meaning_'+semantics)
    if number is not None:
        if number['relation'] in ('lt','le','gt','ge','range'): implementation.append('bounded_estimate_unsupported')
        if number['relation'] == 'approximate': implementation.append('approximate_estimate_unsupported')
        if number['capability_reason'] and 'source_number_unavailable' not in source_reasons:
            source_reasons.append('source_number_unavailable')
    raw = None if number is None or number['native_exact_value'] is None else _common_q(number['native_exact_value'])
    value = raw*scale if raw is not None and scale is not None else None
    floating = None if value is None else _common_float(value)
    if value is not None and floating is None: implementation.append('numerical_model_range')
    location = [] if number is None else [{**_common_location(number['selector']['witness']),
        'start': number['number_start_bytes'], 'end': number['number_end_bytes']}]
    owner = number['measurement_key'] if number else identity('common_unavailable_estimate', selected)
    spread = None
    if selected['reported_spread'] is not None:
        spread_number = read_spread(selected['reported_spread'], sources, 'spread')
        sn=spread_number['selector'];sw=sn['witness']
        spread_number.update(number_start_bytes=sw['start']+len(sw['quote'][:sn['number_start']].encode()),
            number_end_bytes=sw['start']+len(sw['quote'][:sn['number_end']].encode()))
        if number is not None:
            _associate(spread_number, witnesses['quantity_label'], sources, role+'.spread')
            if selected['layout'] == 'table':
                _, cells = _table_cells(sources, {**spread_number['selector']['witness'],
                    'start': spread_number['number_start_bytes'], 'end': spread_number['number_end_bytes']})
                spread_cell = next((c for c in cells if c['start'] <= spread_number['number_start_bytes'] < spread_number['number_end_bytes'] <= c['end']), None)
                if spread_cell != cell: _fail('common_spread_estimate_cell_mismatch', role)
        if Fraction(spread_number['raw_number'].replace('−','-'))<0: _fail('nonnegative_common_reported_spread_required',role)
        loc = {**_common_location(spread_number['selector']['witness']),
            'start': spread_number['number_start_bytes'], 'end': spread_number['number_end_bytes']}
        location.append(loc)
        spread = {'exact_value': _common_exact(Fraction(spread_number['raw_number'].replace('−','-'))), 'statistic': 'unspecified', 'unit': unit_text, 'location': loc}
    return dict(role=role, selection=deepcopy(selected), value=None if source_reasons or implementation else floating,
        exact_value=None if value is None or source_reasons or implementation else _common_exact(value),
        native_value=None if raw is None else _common_float(raw), native_exact_value=None if raw is None else _common_exact(raw), native_unit=unit_text,
        unit=COMMON_UNITS[base] if scale is not None else None, status='unavailable' if source_reasons or implementation else 'point',
        native_semantics=semantics, origin=origin, numeric_origin='original_source_token', owner_key=owner,
        physical_owner_key=None if witnesses['physical_identity'] is None else identity('common_physical_owner', _common_location(witnesses['physical_identity'])),
        population_key=None if witnesses['population'] is None else identity('common_population', _common_location(witnesses['population'])),
        assay_key=None if witnesses['assay'] is None else identity('common_assay',_common_location(witnesses['assay'])),
        dependency_keys=[owner], locations=location, source_missing_reasons=source_reasons,
        implementation_reasons=implementation, reported_spread=spread)


def _common_received_estimate(role, selected, row, request, read_record, sources):
    base, arm = role.rsplit('_', 1)
    namespace = selected['namespace']; implementation=[]; source_reasons=[]; locations=[]
    numeric_origin='saved_canonical_decimal'; exact=None; semantics='reported_point'; physical=None; population=None; assay=None; spread=None
    def authenticate_anchor(a):
        source=read_record(a['source_ref'])
        representation='original' if source.get('artifact_ref')==a['artifact_ref'] else 'text' if source.get('text_ref')==a['artifact_ref'] else None
        if representation is None: _fail('common_kinetic_anchor_artifact_mismatch',role)
        return sources.witness({k:a[k] for k in ('source_ref','start','end','quote')} | {'representation':representation},role+'.anchor')
    if namespace == 'literature_calibration_recovery_cells':
        from .literature_calibration_recovery_storage import calibration_recovery_cells_schema
        validate_schema([row],calibration_recovery_cells_schema())
        if base!='recovery': _fail('common_received_role_mismatch',role)
        exact=row['exact_value'];value=row['value'];unit=row['unit'];origin=row['origin'];numeric_origin='received_exact_component'
        owner=identity('common_selected_derived_estimate',selected);owners=row['input_measurement_keys']
        # Existing recovery rows do not bind their measurement population to the
        # new common arm. Preserve the available control value without claiming
        # that conversion/applicability is already implemented.
        implementation.append('correction_conversion_unimplemented')
    elif namespace == 'literature_product_coupling_cells':
        from .literature_product_coupling_storage import product_coupling_cells_schema
        validate_schema([row], product_coupling_cells_schema())
        wanted = {'product':'reported_product_activity','reporter':'reported_cofactor_activity'}.get(base)
        if wanted != selected['component']: _fail('common_received_role_mismatch', role)
        actual_role = 'product' if base=='product' else 'cofactor'
        quantity = row['quantity_meanings'][actual_role]
        if quantity is None: _fail('common_received_quantity_meaning_required', role)
        wanted_endpoint='product_formation' if base=='product' else 'cofactor_consumption'
        if quantity['endpoint_role']['value'] != wanted_endpoint: source_reasons.append('endpoint_relationship_unknown')
        semantics=row['native_measurement_semantics']; exact=row['exact_value']; numeric_origin='received_exact_component'
        owners=row['input_measurement_keys']; owner=quantity['measurement_key']
        if owner is None or owner not in owners: _fail('common_received_measurement_owner_mismatch', role)
        physical=quantity['physical_identity_key']; locations=deepcopy(row['withheld_locations'])
        experiment=row['source_meanings']['experiment']
        assay=None if experiment is None else identity('common_assay',_common_location(experiment))
        # A received row's context was already scoped by218. Source row/construct
        # binding still requires an explicit common arm witness; a broad masked
        # construct cannot certify a cross-arm numerical comparison.
        meaning=row['source_meanings']['construct']; expected=request['arms'][arm]['construct']
        if meaning is None or expected is None:
            source_reasons.append('received_construct_unresolved')
        elif meaning['status'] != 'selected':
            implementation.append('unrequested_numerical_scope_unresolved')
        elif _common_visible(meaning['display_text']) != _common_visible(expected['quote']):
            _fail('common_received_construct_mismatch', role)
        if semantics in ('reported_nondetection','reported_negligible'): source_reasons.append('native_nondetection_not_point')
        elif semantics != 'reported_point': source_reasons.append('source_parameter_meaning_'+semantics)
        if row['relation'] != 'point': implementation.append('bounded_estimate_unsupported')
        origin=row['origin']; unit=row['unit']; value=row['value']
    else:
        from .literature_kinetic_storage import kinetic_cells_schema
        from .literature_kinetic_inputs import _normalize, _UNIT_TABLES
        validate_schema([row], kinetic_cells_schema())
        if base not in ('kcat','Km'): _fail('common_received_role_mismatch', role)
        side=selected['component'].removesuffix('_parameter'); own=row[side]
        if own['parameter_kind'] != base: _fail('common_received_parameter_kind_mismatch', role)
        expected=request['arms'][arm]['construct']; cref=own['subject']['construct']
        if cref is None or expected is None: source_reasons.append('received_construct_unresolved')
        else:
            construct=read_record(cref); anchor=construct.get('anchor')
            if anchor is None: source_reasons.append('received_construct_unresolved')
            elif _common_visible(anchor['quote']) != _common_visible(expected['quote']): _fail('common_received_construct_mismatch', role)
        value=row['value']; unit=row['unit']; origin=row['origin']; owners=[]; owner=own['measurement_ref']
        if owner is None: owner=identity('common_unavailable_estimate',selected)
        else:
            measurement=read_record(owner); anchor=measurement.get('anchor')
            if anchor is not None:
                owner=identity('literature_measurement', {'artifact_ref':anchor['artifact_ref'],
                    'number_start':anchor['start'],'number_end':anchor['end']})
                if anchor['source_ref'] != own['measurement_source_ref']:
                    _fail('common_kinetic_anchor_source_mismatch',role)
                meta=read_record(own['source_unit_ref']) if own['source_unit_ref'] else {}
                uanchor=meta.get('anchor'); scale=_UNIT_TABLES[base].get(_normalize(uanchor['quote'])) if uanchor else None
                # Only own public anchors, never neighboring private sheet data.
                authenticated=authenticate_anchor(anchor)
                if uanchor is not None: authenticate_anchor(uanchor)
                if scale and row['status']=='populated' and row['relation']=='eq' and not row['approximate']:
                    import re
                    if re.fullmatch(r'[+−-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+−-]?\d+)?', anchor['quote']):
                        exact=Fraction(anchor['quote'].replace('−','-'))*scale[1]
                        if _common_float(exact) != value: _fail('common_kinetic_anchor_value_mismatch', role)
                        numeric_origin='original_source_token'
                locations.append(_common_location(authenticated))
        uncertainty=own['uncertainty'];spread_ref=uncertainty['magnitude_ref'];spread_value=own['uncertainty_values']['magnitude']
        if spread_ref is not None and spread_value is not None and uncertainty['statistic'] in ('sd','sem','unspecified'):
            spread_anchor=read_record(spread_ref).get('anchor')
            if spread_anchor is not None:
                sw=authenticate_anchor(spread_anchor)
                spread={'exact_value':_common_exact(Fraction(str(spread_value))),'statistic':uncertainty['statistic'],
                    'unit':uncertainty['canonical_unit'],'location':_common_location(sw)}
                locations.append(_common_location(sw))
        owners=[owner]; physical=own['physical_observation_ref'];assay=own['context']['experiment']
        if row['approximate']: implementation.append('approximate_estimate_unsupported')
        if row['relation'] not in ('eq','none'): implementation.append('bounded_estimate_unsupported')
        if own['input_status'] not in ('point',): source_reasons.append('native_component_unavailable')
    if unit != COMMON_UNITS[base] and namespace!='literature_calibration_recovery_cells': implementation.append('received_parameter_unit_mismatch')
    if row['status'] != 'populated' or value is None: source_reasons.append('native_component_unavailable')
    if exact is None and value is not None: exact=Fraction(str(value))
    elif isinstance(exact, dict): exact=_common_q(exact)
    if exact is not None and value is not None and _common_float(exact)!=value: _fail('common_received_exact_value_mismatch',role)
    return dict(role=role,selection=deepcopy(selected), value=None if source_reasons or implementation else value,
        exact_value=None if source_reasons or implementation or exact is None else _common_exact(exact),
        native_value=value,native_exact_value=None if exact is None else _common_exact(exact),native_unit=unit,unit=unit,
        status='unavailable' if source_reasons or implementation else 'point',native_semantics=semantics,
        origin=origin,numeric_origin=numeric_origin,owner_key=owner,physical_owner_key=physical,population_key=population,assay_key=assay,
        dependency_keys=list(dict.fromkeys(owners)),locations=locations,source_missing_reasons=list(dict.fromkeys(source_reasons)),
        implementation_reasons=list(dict.fromkeys(implementation)),reported_spread=spread)


def _common_covariance(reference, sources, estimates):
    raw=sources.source(reference,'original')
    def pairs(items):
        result={}
        for key,val in items:
            if key in result: _fail('duplicate_json_key','common.covariance')
            result[key]=val
        return result
    try:
        data=json.loads(raw['content'].decode(),object_pairs_hook=pairs,parse_float=Fraction,parse_int=Fraction,
            parse_constant=lambda token:_fail('finite_number_required','common.covariance'))
    except (UnicodeError, ValueError) as error:
        raise ExperimentalContractError('common_covariance_json_required','covariance') from error
    _keys(data,('version','roles','owner_keys','units','dependency_keys','covariance','basis','variance_status','origin'),'common.covariance')
    roles=data['roles']
    if data['version']!='a105_common_assessment_covariance_v1' or not isinstance(roles,list) or not roles or len(set(roles))!=len(roles) or any(r not in COMMON_ROLES or estimates[r] is None or estimates[r]['status']!='point' for r in roles):
        _fail('common_covariance_eligible_roles_required','covariance')
    owners=[estimates[r]['owner_key'] for r in roles];units=[estimates[r]['unit'] for r in roles];deps=[estimates[r]['dependency_keys'] for r in roles]
    if data['owner_keys']!=owners or data['units']!=units or data['dependency_keys']!=deps:
        _fail('common_covariance_owner_unit_dependency_mismatch','covariance')
    if data['basis']!='joint_covariance_of_selected_estimates' or data['variance_status'] not in ('known','estimated','unknown') or data['origin'] not in ('reported','derived','synthetic'):
        _fail('common_covariance_basis_status_required','covariance')
    matrix=data['covariance'];n=len(roles)
    if matrix is None:
        if data['variance_status']!='unknown': _fail('common_covariance_matrix_required','covariance')
    else:
        if not isinstance(matrix,list) or len(matrix)!=n or any(not isinstance(row,list) or len(row)!=n for row in matrix) or any(type(v) is not Fraction for row in matrix for v in row):
            _fail('common_covariance_shape_numeric_required','covariance')
        if any(matrix[i][j]!=matrix[j][i] for i in range(n) for j in range(i)):
            _fail('common_covariance_exact_symmetry_required','covariance')
        # Exact Schur complements establish PSD without float-rounding away a
        # negative direction or accepting unequal JSON integers as symmetric.
        work=deepcopy(matrix)
        for k in range(n):
            pivot=next((i for i in range(k,n) if work[i][i]>0),None)
            if any(work[i][i]<0 for i in range(k,n)): _fail('common_covariance_psd_required','covariance')
            if pivot is None:
                if any(work[i][j]!=0 for i in range(k,n) for j in range(k,n)): _fail('common_covariance_psd_required','covariance')
                break
            work[k],work[pivot]=work[pivot],work[k]
            for row in work: row[k],row[pivot]=row[pivot],row[k]
            p=work[k][k]
            for i in range(k+1,n):
                for j in range(k+1,n): work[i][j]-=work[i][k]*work[k][j]/p
        for i in range(n):
            for j in range(i):
                if owners[i]==owners[j] and (matrix[i]!=matrix[j] or estimates[roles[i]]['exact_value']!=estimates[roles[j]]['exact_value']):
                    _fail('common_shared_owner_covariance_mismatch','covariance')
        matrix=[[_common_exact(v) for v in row] for row in matrix]
    return {k:deepcopy(data[k]) for k in ('roles','owner_keys','units','dependency_keys','basis','variance_status','origin')} | {
        'source_ref':reference,'artifact_ref':raw['artifact_ref'],'matrix_exact':matrix}


def read_common_assessment_inputs(request, *, read_source, read_component, read_record):
    """Bind selected received rows/source numerals once; no private sheet reads.

    Callbacks must enforce actual receipt, scope and lineage. Invalid attempted
    access propagates as an action failure. Scientific unknowns retain partials.
    This function is not a restoration API; its complete result must be saved.
    """
    args=deepcopy(request);validate_schema(args,common_assessment_population_schema())
    sources=_Sources(read_source);sources.source(args['source_ref'],'original')
    def authenticate(value):
        if isinstance(value,dict):
            if set(value)==set(_witness_schema()['properties']): sources.witness(value,'common.witness')
            else:
                for child in value.values(): authenticate(child)
        elif isinstance(value,list):
            for child in value: authenticate(child)
    authenticate(args)
    _common_interpret(args['subject_relationship'],sources,'subject_relationship')
    _common_interpret(args['sampling_relationship'],sources,'sampling_relationship')
    _common_interpret(args['product_reporter_relationship'],sources,'product_reporter_relationship')
    _common_interpret(args['correction_factorization'],sources,'correction_factorization')
    for group,links in args['relationships'].items():
        for name,v in links.items(): _common_interpret(v,sources,group+'.'+name)
    if args['model']:
        for name,v in args['model']['assumptions'].items(): _common_interpret(v,sources,'model.'+name)
    estimates={};snapshots=[];locations=[]
    for role,selected in args['estimates'].items():
        if selected is None: estimates[role]=None;continue
        if selected['kind']=='source_parameter':
            estimate=_common_source_estimate(role,selected,sources,args)
        else:
            rows=read_component(deepcopy(selected))
            if len(rows)!=1 or rows[0]['sheet_ref']!=selected['sheet_ref'] or rows[0]['component']!=selected['component']:
                _fail('selected_component_not_received',role)
            estimate=_common_received_estimate(role,selected,rows[0],args,read_record,sources)
            snapshots.append({'selection':deepcopy(selected),'row':deepcopy(rows[0])})
        estimates[role]=estimate;locations.extend(estimate['locations'])
    owners={}
    for role,estimate in estimates.items():
        if estimate is None: continue
        fact=(estimate['exact_value'],estimate['unit'],estimate['native_semantics'])
        owner=estimate['owner_key']
        if owner in owners and owners[owner]!=fact:
            _fail('common_shared_estimate_meaning_mismatch',role)
        owners[owner]=fact
    model=args['model']
    if model is not None and model['substrate_ownership']=='shared_owner':
        a,b=(estimates['free_substrate_'+arm] for arm in COMMON_ARMS)
        if a is not None and b is not None and (a['owner_key']!=b['owner_key'] or a['exact_value']!=b['exact_value']):
            _fail('common_shared_substrate_owner_required','model.substrate_ownership')
    if model is not None and model['substrate_ownership']=='separate_owners':
        a,b=(estimates['free_substrate_'+arm] for arm in COMMON_ARMS)
        if a is not None and b is not None and a['owner_key']==b['owner_key']:
            _fail('common_separate_substrate_owners_required','model.substrate_ownership')
    blocks=[_common_covariance(ref,sources,estimates) for ref in args['covariance_source_refs']]
    pairs={};statuses={}
    for block in blocks:
        for i,owner in enumerate(block['owner_keys']):
            status=block['variance_status']
            if owner in statuses and statuses[owner]!=status: _fail('common_covariance_overlap_status_mismatch','covariance')
            statuses[owner]=status
            if block['matrix_exact']:
                for j,other in enumerate(block['owner_keys']):
                    key=(owner,other);value=block['matrix_exact'][i][j]
                    if key in pairs and pairs[key]!=value: _fail('common_covariance_overlap_mismatch','covariance')
                    pairs[key]=value
        content=sources.source(block['source_ref'],'original')['content']
        if content: locations.append(dict(source_ref=block['source_ref'],artifact_ref=block['artifact_ref'],representation='original',start=0,end=len(content)))
    result=dict(version=COMMON_INPUTS,request=args,estimates=estimates,covariance_blocks=blocks,
        source_refs=list(sources.references),source_artifacts=[dict(source_ref=ref,representation=rep,artifact_ref=v['artifact_ref'])
            for (ref,rep),v in sources.cache.items()],numerical_scope_locations=locations,component_snapshots=snapshots)
    validate_schema(result,common_assessment_inputs_schema());return result


__all__ += ['COMMON_REQUEST','COMMON_POPULATION','COMMON_INPUTS','COMMON_ROLES','COMMON_ASSUMPTIONS','COMMON_REASONS',
    'common_assessment_population_schema','common_assessment_inputs_schema','read_common_assessment_inputs']
