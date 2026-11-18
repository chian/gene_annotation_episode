"""Pure four-arm source-response arithmetic within A105.

This accepts already parsed, explicitly interpreted inputs, never model-selected
scientific numbers or source documents. Source custody, condition/normalization
interpretation, reader partials, selected execution and annotation credit belong
elsewhere. The controlled effect is conditional on actual control applicability;
it does not establish isolated causal protein action or proton coupling.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import permutations
import math
from gene_annotation_episode.episodic_workflow.root.a105.experimental_activity_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.grading.literature_experimental_contracts import ExperimentalContractError, RATE_UNITS
PRIMITIVE_ORDER = ('protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0')
COMPONENTS = tuple((name + '_response' for name in PRIMITIVE_ORDER)) + ('condition1_controlled_response', 'condition0_controlled_response', 'controlled_response_difference', 'contrast_variance', 'contrast_standard_uncertainty', 'contrast_precision', 'source_profile_log_ratio', 'source_signed_index')
ARM_FIELDS = ('value', 'threshold', 'relation', 'approximate', 'unit', 'status', 'endpoint_id', 'normalization_id', 'subject_construct_id', 'condition_id', 'physical_observation_id', 'source_observation_id', 'origin', 'digitization_interval', 'protein_arrangement', 'meaning_statuses')
RELATIONSHIP_FIELDS = ('condition1_target', 'condition0_target', 'condition_levels_relation', 'condition1_control_application', 'condition0_control_application', 'subject_construct_across_conditions', 'control_reference_reuse', 'nonintended_conditions', 'intended_factor')
_MEANINGS = ('endpoint', 'normalization', 'subject_construct', 'condition', 'physical_observation')
_STATES = ('known', 'unknown', 'conflicting')
_ARRANGEMENTS = ('protein_present', 'protein_free_control', 'empty_vector_control', 'other_specified', 'unknown', 'conflicting')
_APPLICATIONS = ('matched_condition_control', 'shared_reference_assumption', 'unknown', 'conflicting')
_REUSE = ('distinct_observations', 'same_reference_with_stated_invariance', 'unknown', 'conflicting')
_BASE_UNITS = {'amount_rate': 'umol/min', 'concentration_rate': 'uM/min', 'turnover_rate': 'per_min', 'specific_amount_rate': 'umol/min/mg'}
_FORMULAS = ('source_response',) * 4 + ('condition_control_difference',) * 2 + ('four_arm_condition_difference', 'linear_joint_covariance', 'square_root_variance', 'inverse_variance', 'signed_known_normal_profile', 'tanh_half_signed_profile')
def _fail(code, field):
    raise ExperimentalContractError(code, field)

def _closed(value, fields, field):
    if not isinstance(value, dict) or set(value) != set(fields):
        _fail('closed_fields_required', field)

def _enum(value, allowed, field):
    if not isinstance(value, str) or value not in allowed:
        _fail('unsupported_value', field)

def _identity(value, field, *, nullable=True):
    if value is None and nullable:
        return
    if not isinstance(value, str) or not value.strip():
        _fail('nonempty_identity_required', field)

def _finite(value, field, *, nullable=False):
    if value is None and nullable:
        return
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail('finite_number_required', field)

def _q(value):
    return Fraction(str(value))

def _scale(unit):
    return _q(RATE_UNITS[unit][1])

def _determinant(matrix):
    size = len(matrix)
    total = Fraction(0)
    for perm in permutations(range(size)):
        inversions = sum((perm[i] > perm[j] for i in range(size) for j in range(i + 1, size)))
        product = Fraction((-1) ** inversions)
        for i in range(size):
            product *= matrix[i][perm[i]]
        total += product
    return total

def _operand_reasons(arm):
    if arm is None:
        return {'missing_arm'}
    reasons = set()
    if arm['unit'] is None:
        reasons.add('unknown_unit')
    status_reason = {'missing': 'missing_arm', 'ambiguous': 'ambiguous_source_literal', 'conflicting': 'conflicting_source_literal', 'unsupported': 'unsupported_source_expression'}
    if arm['status'] in status_reason:
        reasons.add(status_reason[arm['status']])
    return reasons

def _identity_reasons(arms, meaning):
    states = [arm['meaning_statuses'][meaning] for arm in arms if arm is not None]
    if 'conflicting' in states:
        return {'conflicting_' + meaning if meaning in ('endpoint', 'normalization') else 'conflicting_' + ('subject_correspondence' if meaning == 'subject_construct' else 'condition_correspondence')}
    if len(states) != len(arms) or 'unknown' in states:
        return {'unknown_' + meaning if meaning in ('endpoint', 'normalization') else 'unknown_' + ('subject_correspondence' if meaning == 'subject_construct' else 'condition_correspondence')}
    if len({arm[meaning + '_id'] for arm in arms}) != 1:
        return {'different_' + meaning if meaning in ('endpoint', 'normalization') else 'different_' + ('subject_correspondence' if meaning == 'subject_construct' else 'condition_correspondence')}
    return set()

def _alias_reasons(left, right):
    """Test consistency of an asserted common physical/source observation."""
    reasons = set()
    for meaning in _MEANINGS[:-1]:
        a, b = (left[meaning + '_id'], right[meaning + '_id'])
        if a is not None and b is not None and (a != b):
            reasons |= {'conflicting_' + meaning if meaning in ('endpoint', 'normalization') else 'conflicting_' + ('subject_correspondence' if meaning == 'subject_construct' else 'condition_correspondence')}
    if left['protein_arrangement'] != right['protein_arrangement']:
        reasons.add('conflicting_protein_arrangement')
    if left['unit'] is None or right['unit'] is None:
        return reasons | {'unknown_unit'}
    if RATE_UNITS[left['unit']][0] != RATE_UNITS[right['unit']][0]:
        return reasons | {'incompatible_unit_dimension'}
    for field in ('status', 'relation', 'approximate'):
        if left[field] != right[field]:
            reasons.add('conflicting_source_literal')
    for field in ('value', 'threshold'):
        a, b = (left[field], right[field])
        if (a is None) != (b is None) or (a is not None and _q(a) * _scale(left['unit']) != _q(b) * _scale(right['unit'])):
            reasons.add('conflicting_source_literal')
    a, b = (left['digitization_interval'], right['digitization_interval'])
    if (a is None) != (b is None) or (a is not None and any((_q(a[side]) * _scale(left['unit']) != _q(b[side]) * _scale(right['unit']) for side in ('lower', 'upper')))):
        reasons.add('conflicting_source_literal')
    return reasons

def _common_alias_reasons(arms):
    reasons = set()
    for i, left in enumerate(arms):
        if left is None:
            continue
        for right in arms[:i]:
            if right is None:
                continue
            same_owner = left['physical_observation_id'] is not None and left['physical_observation_id'] == right['physical_observation_id']
            same_source = left['source_observation_id'] is not None and left['source_observation_id'] == right['source_observation_id']
            if same_owner or same_source:
                reasons |= _alias_reasons(left, right)
                if same_source and left['physical_observation_id'] is not None and (right['physical_observation_id'] is not None) and (not same_owner):
                    reasons.add('conflicting_source_literal')
    return reasons

def _unit(arms):
    units = [arm['unit'] for arm in arms if arm is not None and arm['unit'] is not None]
    dimensions = {RATE_UNITS[unit][0] for unit in units}
    return _BASE_UNITS[next(iter(dimensions))] if len(dimensions) == 1 else None

def _pair_reasons(inputs, indices, label):
    arms = [inputs['arms'][PRIMITIVE_ORDER[i]] for i in indices]
    reasons = set().union(*(_operand_reasons(arm) for arm in arms))
    for meaning in ('endpoint', 'normalization'):
        reasons |= _identity_reasons(arms, meaning)
    if len({RATE_UNITS[arm['unit']][0] for arm in arms if arm and arm['unit']}) > 1:
        reasons.add('incompatible_unit_dimension')
    for arm, allowed in zip(arms, (('protein_present',), ('protein_free_control', 'empty_vector_control'))):
        if arm is None:
            continue
        arrangement = arm['protein_arrangement']
        if arrangement not in allowed:
            reasons.add({'unknown': 'unknown_protein_arrangement', 'conflicting': 'conflicting_protein_arrangement'}.get(arrangement, 'incompatible_control_arrangement'))
    target = inputs['relationships'][label + '_target']
    application = inputs['relationships'][label + '_control_application']
    if target['status'] != 'known':
        reasons.add(target['status'] + '_condition_correspondence')
    for i, arm in enumerate(arms):
        if arm is None:
            continue
        state = arm['meaning_statuses']['condition']
        if state != 'known':
            reasons.add(state + '_condition_correspondence')
        elif target['status'] == 'known' and (i == 0 or application == 'matched_condition_control') and (arm['condition_id'] != target['canonical_id']):
            reasons.add('different_condition_correspondence')
    if application in ('unknown', 'conflicting'):
        reasons.add(application + '_control_application')
    reasons |= _common_alias_reasons(arms)
    return reasons

@dataclass(frozen=True)
class _Range:
    point: Fraction | None
    lower: Fraction | None
    upper: Fraction | None
    lower_closed: bool = True
    upper_closed: bool = True
    kinds: frozenset = frozenset()

def _range(arm):
    scale = _scale(arm['unit'])
    if arm['status'] == 'point':
        point = _q(arm['value']) * scale
        interval = arm['digitization_interval']
        return _Range(point, _q(interval['lower']) * scale, _q(interval['upper']) * scale, kinds=frozenset(('conditional_digitization',))) if interval else _Range(point, point, point)
    threshold = _q(arm['threshold']) * scale
    return _Range(None, None, threshold, upper_closed=arm['relation'] == 'le', kinds=frozenset(('reported_limit',))) if arm['relation'] in ('lt', 'le') else _Range(None, threshold, None, lower_closed=arm['relation'] == 'ge', kinds=frozenset(('reported_limit',)))

def _linear(arms, coefficients):
    groups = {}
    for i, (arm, coefficient) in enumerate(zip(arms, coefficients)):
        key = ('owner', arm['physical_observation_id']) if arm['physical_observation_id'] is not None else ('role', i)
        if key in groups:
            old, count = groups[key]
            groups[key] = (old, count + coefficient)
        else:
            groups[key] = (arm, coefficient)
    point = lower = upper = Fraction(0)
    lower_closed = upper_closed = True
    kinds = set()
    for arm, coefficient in groups.values():
        if coefficient == 0:
            continue
        value = _range(arm)
        kinds |= value.kinds
        point = None if point is None or value.point is None else point + coefficient * value.point
        lo, hi = (value.lower, value.upper) if coefficient > 0 else (value.upper, value.lower)
        lc, uc = (value.lower_closed, value.upper_closed) if coefficient > 0 else (value.upper_closed, value.lower_closed)
        lower = None if lower is None or lo is None else lower + coefficient * lo
        upper = None if upper is None or hi is None else upper + coefficient * hi
        lower_closed &= lc
        upper_closed &= uc
    return _Range(point, lower, upper, lower_closed, upper_closed, frozenset(kinds))

def _number(value):
    if value is None:
        return None
    try:
        result = float(value)
    except (OverflowError, ValueError):
        return None
    return result if math.isfinite(result) and (result != 0 or value == 0) else None

def _origin(arms, *, raw=False):
    origins = {arm['origin'] for arm in arms if arm is not None}
    return 'synthetic' if 'synthetic' in origins else 'graph_derived' if 'graph_derived' in origins else next(iter(origins)) if raw and origins else 'calculated'

def _qualifications(inputs, arms, *, cross=False, covariance=False, model=False):
    result = set()
    if any((arm is not None and arm['origin'] == 'synthetic' for arm in arms)):
        result.add('synthetic_fixture')
    if any((arm is not None and arm['approximate'] for arm in arms)):
        result.add('approximate_source_reading')
    if any((arm is not None and arm['digitization_interval'] is not None for arm in arms)):
        result.add('conditional_digitization')
    if cross:
        relationships = inputs['relationships']
        state = relationships['nonintended_conditions']
        if state != 'matched':
            result.add('nonintended_conditions_' + state)
        if relationships['control_reference_reuse'] == 'unknown':
            result.add('unknown_control_reuse')
    if covariance and inputs['variance_status'] == 'estimated':
        result.add('estimated_covariance')
    if model and inputs['model_kind'] == 'known_joint_normal_source_means':
        result.add('known_normal_source_means')
    return result

def _cell(value, unit, formula, arms, *, reasons=(), qualifications=(), raw=False):
    reasons, qualifications = (set(reasons), set(qualifications))
    result = {'value': None, 'lower': None, 'upper': None, 'relation': 'none', 'approximate': any((arm is not None and arm['approximate'] for arm in arms)), 'unit': unit, 'status': 'unavailable', 'origin': _origin(arms, raw=raw), 'unavailable_reason': None, 'formula_code': formula, 'conditional_on': sorted(qualifications), 'bound_kind': 'none', 'bound_state': {'lower': 'unknown', 'upper': 'unknown'}}
    if reasons:
        result['status'] = 'conflicting' if any((reason.startswith('conflicting_') for reason in reasons)) else 'unsupported' if 'unsupported_source_expression' in reasons else 'partial' if raw and reasons == {'unknown_unit'} and (arms[0]['status'] in ('point', 'bound')) else 'unavailable'
    elif value is not None:
        bounded = bool(value.kinds)
        result['bound_kind'] = 'mixed' if len(value.kinds) > 1 else next(iter(value.kinds)) if value.kinds else 'none'
        result['value'] = _number(value.point)
        if value.point is not None and result['value'] is None:
            reasons.add('numeric_range_failure')
        if bounded:
            for side in ('lower', 'upper'):
                exact = getattr(value, side)
                converted = _number(exact)
                result[side] = converted
                result['bound_state'][side] = 'unbounded' if exact is None else 'available' if converted is not None else 'numeric_range_failure'
                if exact is not None and converted is None:
                    reasons.add('numeric_range_failure')
        else:
            result['bound_state'] = dict.fromkeys(('lower', 'upper'), 'not_applicable')
        lower, upper = (result['lower'], result['upper'])
        if lower is not None and upper is not None:
            result['relation'] = 'interval'
        elif lower is not None:
            result['relation'] = 'ge' if value.lower_closed else 'gt'
        elif upper is not None:
            result['relation'] = 'le' if value.upper_closed else 'lt'
        elif result['value'] is not None:
            result['relation'] = 'eq'
        available = any((result[name] is not None for name in ('value', 'lower', 'upper')))
        result['status'] = 'partial' if reasons and available else 'available' if result['value'] is not None else 'bounded' if available else 'unavailable'
        if not available and (not reasons):
            reasons.add('uninformative_bounds')
    result['unavailable_reason'] = sorted(reasons) or None
    return result

def _point(value):
    return None if value is None else _Range(value, value, value)

def _sqrt(value):
    with localcontext() as context:
        context.prec = 80
        return (Decimal(value.numerator) / Decimal(value.denominator)).sqrt()

def _bounded_index(score):
    if score == 0:
        return Fraction(0)
    if abs(score) > 100:
        return Fraction(1 if score > 0 else -1)
    half = _number(score / 2)
    if half is None:
        return None
    result = math.tanh(half)
    return result if result != 0 else None

__all__ = ['PRIMITIVE_ORDER', 'COMPONENTS', 'ARM_FIELDS', 'RELATIONSHIP_FIELDS']
