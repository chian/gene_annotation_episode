"""Constructed parsed inputs only; no source, image, model or episode execution."""
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import literature_controlled_response_calculations as old
from gene_annotation_episode import literature_controlled_response_owner_calculations as owner
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001'
DESIGN = BASE / 'a105_controlled_adapter_design_065'
INPUT_SCHEMA = json.loads((DESIGN / 'OWNER_INPUT_SCHEMA_004.json').read_text())
OUTPUT_SCHEMA = json.loads((DESIGN / 'OWNER_OUTPUT_SCHEMA_004.json').read_text())
ROLES = old.PRIMITIVE_ORDER
EFFECT, VARIANCE, SE, PRECISION, SCORE, INDEX = old.COMPONENTS[6:]
SHAPES = json.loads((DESIGN / 'OWNER_SHAPE_EXAMPLES_004.json').read_text())


def arm(value, condition, physical, *, control=False):
    return {'value': value, 'threshold': None, 'relation': 'eq', 'approximate': False,
        'unit': 'nmol/min', 'status': 'point', 'endpoint_id': 'constructed_initial_rate',
        'normalization_id': 'constructed_common_basis',
        'subject_construct_id': 'constructed_empty' if control else 'constructed_protein',
        'condition_id': condition, 'physical_observation_id': physical,
        'source_observation_id': 'constructed_source_' + physical, 'origin': 'synthetic',
        'digitization_interval': None,
        'protein_arrangement': 'protein_free_control' if control else 'protein_present',
        'meaning_statuses': dict.fromkeys(old._MEANINGS, 'known')}


def distinct():
    arms = {role: arm(value, 'c1' if i < 2 else 'c0', role, control=i % 2 == 1)
            for i, (role, value) in enumerate(zip(ROLES, (12, 2, 5, 1)))}
    return {'version': 'controlled_response_owner_inputs_v2', 'arms': arms,
        'relationships': {'condition1_target': {'status': 'known', 'canonical_id': 'c1'},
            'condition0_target': {'status': 'known', 'canonical_id': 'c0'},
            'condition_levels_relation': 'different', 'subject_construct_across_conditions': 'same',
            'condition1_control_application': 'matched_condition_control',
            'condition0_control_application': 'matched_condition_control',
            'control_reference_reuse': 'distinct_observations', 'nonintended_conditions': 'unknown',
            'intended_factor': 'constructed_intended_change'},
        'covariance': {'primitive_order': list(ROLES), 'physical_observation_ids': list(ROLES),
            'units': ['nmol/min'] * 4, 'matrix': [[v if i == j else 0 for j in range(4)]
                for i, v in enumerate((1, .25, .36, .09))]},
        'variance_status': 'known', 'model_kind': 'none'}


def shared():
    inputs = distinct()
    inputs['arms'] = dict(zip(ROLES, (arm(10, 'c1', 'A'), arm(4, 'reference', 'B', control=True),
        arm(8, 'c0', 'C'), arm(4, 'reference', 'B', control=True))))
    inputs['relationships'].update(condition1_control_application='shared_reference_assumption',
        condition0_control_application='shared_reference_assumption',
        control_reference_reuse='same_reference_with_stated_invariance')
    inputs['covariance'] = {'physical_observation_ids': ['A', 'C'], 'units': ['nmol/min'] * 2,
                            'matrix': [[.25, .1], [.1, .25]]}
    return inputs


def graph(row, value=4.05, lower=3.95, upper=4.15):
    row.update(value=value, origin='graph_derived', approximate=True, relation='interval',
        source_observation_id=row['source_observation_id'] + '_graph',
        digitization_interval={'lower': lower, 'upper': upper})


def unavailable(row, status='missing', *, unit=None):
    row.update(value=None, threshold=None, relation='none', status=status, unit=unit,
               digitization_interval=None, approximate=False)
    if status == 'missing':
        row['source_observation_id'] = None


def no_covariance(inputs):
    inputs.update(covariance=None, variance_status='unknown')
    return inputs


def calculate(inputs):
    before = deepcopy(inputs)
    Draft202012Validator(INPUT_SCHEMA).validate(inputs)
    result = owner.populate_controlled_response_owner(inputs)
    assert inputs == before and result['inputs'] == before
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)
    json.dumps(result, allow_nan=False)
    return result


def test_exact_schema_and_detached_contracts():
    assert owner.__all__ == ['controlled_response_owner_arguments_schema',
        'validate_controlled_response_owner_inputs', 'populate_controlled_response_owner']
    schema = owner.controlled_response_owner_arguments_schema()
    assert schema == INPUT_SCHEMA
    schema['$defs']['Arm']['properties']['value']['anyOf'][0]['type'] = 'string'
    assert owner.controlled_response_owner_arguments_schema() == INPUT_SCHEMA
    inputs = shared()
    validated = owner.validate_controlled_response_owner_inputs(inputs)
    assert validated == inputs
    validated['arms'][ROLES[0]]['value'] = 123
    assert inputs['arms'][ROLES[0]]['value'] == 10
    result = calculate(inputs)
    result['inputs']['arms'][ROLES[0]]['value'] = 123
    assert inputs['arms'][ROLES[0]]['value'] == 10


@pytest.mark.parametrize('name', list(SHAPES['examples']))
def test_every_reviewed_shape_has_actual_algorithm_and_qualified_output(name):
    inputs = deepcopy(SHAPES['examples'][name])
    expected = SHAPES['expected_semantics'][name]
    if name == 'invalid_FULL_covariance_despite_canceled_B':
        with pytest.raises(ExperimentalContractError, match='positive_semidefinite_covariance_required'):
            owner.populate_controlled_response_owner(inputs)
        return
    result = calculate(inputs)
    cells = result['cells']
    if 'effect_umol_per_min' in expected:
        assert cells[EFFECT]['value'] == expected['effect_umol_per_min']
    if 'effect' in expected:
        assert cells[EFFECT]['value'] is expected['effect']
    if 'variance_umol_squared_per_min_squared' in expected:
        assert cells[VARIANCE]['value'] == expected['variance_umol_squared_per_min_squared']
    if 'required_qualification' in expected:
        assert expected['required_qualification'] in cells[EFFECT]['conditional_on']
    assert all(set(row) == set(old.CELL_FIELDS) for row in cells.values())


def test_unknown_active_owner_not_covered_by_all_known_covariance_ids():
    fixture = json.loads((DESIGN / 'ACTIVE_UNKNOWN_OWNER_CASE_006.json').read_text())
    result = calculate(fixture['inputs'])
    trace = result['contrast_dependencies']
    assert trace['required_covariance_owner_ids'] == trace['provided_covariance_owner_ids']
    assert trace['covariance_state'] == 'incomplete_active_coverage'
    assert result['cells'][EFFECT]['value'] == .00205
    assert (result['cells'][EFFECT]['lower'], result['cells'][EFFECT]['upper']) == (.00195, .00215)
    assert all(result['cells'][name]['value'] is None for name in old.COMPONENTS[7:])
    assert 'incomplete_active_covariance' in result['cells'][VARIANCE]['unavailable_reason']


def test_raw_and_local_cells_match_unchanged006_for_distinct_inputs():
    inputs = distinct()
    legacy = {**deepcopy(inputs), 'version': old.INPUT_VERSION}
    result = calculate(inputs)
    assert result['cells'] == old.populate_controlled_response(legacy)['cells']
    assert result['cells'][EFFECT]['value'] == .006
    assert result['cells'][VARIANCE]['value'] == 1.7e-6


def test_old_sheet_populator_is_never_called(monkeypatch):
    monkeypatch.setattr(old, 'populate_controlled_response', lambda *_: pytest.fail('whole legacy sheet called'))
    assert calculate(shared())['cells'][EFFECT]['value'] == .002


def test_mixed_control_readings_cancel_from_effect_not_from_local_results():
    inputs = shared()
    graph(inputs['arms'][ROLES[3]])
    result = calculate(inputs)
    cells, trace = result['cells'], result['contrast_dependencies']
    assert cells[old.COMPONENTS[4]]['value'] == .006
    assert cells[old.COMPONENTS[5]]['value'] == .00395
    assert (cells[old.COMPONENTS[5]]['lower'], cells[old.COMPONENTS[5]]['upper']) == (.00385, .00405)
    assert cells[EFFECT]['value'] == .002
    assert cells[EFFECT]['lower'] is cells[EFFECT]['upper'] is None
    assert cells[EFFECT]['approximate'] is False
    assert cells[EFFECT]['bound_kind'] == 'none'
    assert cells[VARIANCE]['value'] == 3e-7
    assert trace['groups'] == [
        {'physical_observation_id': 'A', 'roles': [ROLES[0]], 'coefficient': 1, 'known_owner': True},
        {'physical_observation_id': 'B', 'roles': [ROLES[1], ROLES[3]], 'coefficient': 0, 'known_owner': True},
        {'physical_observation_id': 'C', 'roles': [ROLES[2]], 'coefficient': -1, 'known_owner': True}]
    assert trace['active_roles'] == trace['model_active_roles'] == [ROLES[0], ROLES[2]]
    assert trace['canceled_roles'] == [ROLES[1], ROLES[3]]
    assert trace['reading_conflict_roles'] == []


@pytest.mark.parametrize('status', ['missing', 'unsupported', 'ambiguous', 'conflicting'])
@pytest.mark.parametrize('unit', [None, 'nmol/min'])
def test_present_canceled_science_needs_no_numeric_reading_or_unit(status, unit):
    inputs = shared()
    for index in (1, 3):
        unavailable(inputs['arms'][ROLES[index]], status, unit=unit)
    result = calculate(inputs)
    assert result['cells'][EFFECT]['value'] == .002
    assert result['cells'][VARIANCE]['value'] == 3e-7
    assert all(result['cells'][name]['value'] is None for name in old.COMPONENTS[4:6])
    assert 'canceled_reading_unavailable' in result['cells'][EFFECT]['conditional_on']
    if unit is None:
        assert 'canceled_unit_unknown' in result['cells'][EFFECT]['conditional_on']
    if status == 'conflicting':
        assert 'canceled_source_reading_conflict' in result['cells'][EFFECT]['conditional_on']
        assert result['contrast_dependencies']['reading_conflict_roles'] == [ROLES[1], ROLES[3]]


def test_disjoint_canceled_data_are_qualifications_and_true_owner_conflict_is_not():
    inputs = shared()
    graph(inputs['arms'][ROLES[3]], 9, 8.9, 9.1)
    result = calculate(inputs)
    assert result['cells'][EFFECT]['value'] == .002
    assert 'canceled_reading_domain_conflict' in result['cells'][EFFECT]['conditional_on']
    assert result['contrast_dependencies']['reading_conflict_roles'] == [ROLES[1], ROLES[3]]
    inputs['arms'][ROLES[3]]['physical_observation_id'] = None
    inputs['arms'][ROLES[3]]['meaning_statuses']['physical_observation'] = 'conflicting'
    result = calculate(inputs)
    assert result['cells'][EFFECT]['value'] is None
    assert 'conflicting_owner_context' in result['cells'][EFFECT]['unavailable_reason']
    assert result['cells'][old.COMPONENTS[4]]['value'] == .006


@pytest.mark.parametrize('meaning', ['endpoint', 'normalization', 'condition'])
def test_canceled_scientific_context_failure_is_not_a_numeric_unknown(meaning):
    inputs = shared()
    inputs['arms'][ROLES[3]][meaning + '_id'] = 'different'
    result = calculate(inputs)
    assert result['cells'][EFFECT]['value'] is None
    assert 'conflicting_owner_context' in result['cells'][EFFECT]['unavailable_reason']


@pytest.mark.parametrize('value', ['unknown', 'conflicting'])
def test_canceled_control_application_must_still_be_established(value):
    inputs = shared()
    inputs['relationships']['condition0_control_application'] = value
    result = calculate(inputs)
    assert result['cells'][EFFECT]['value'] is None
    assert value + '_control_application' in result['cells'][EFFECT]['unavailable_reason']


def test_explicit_canceled_dimension_disagreement_is_not_missing_unit():
    inputs = shared()
    inputs['arms'][ROLES[3]]['unit'] = 'uM/min'
    result = calculate(inputs)
    assert result['cells'][EFFECT]['value'] is None
    assert 'incompatible_unit_dimension' in result['cells'][EFFECT]['unavailable_reason']


def test_one_source_cannot_be_assigned_two_distinct_known_owners():
    inputs = distinct()
    inputs['arms'][ROLES[3]]['source_observation_id'] = inputs['arms'][ROLES[1]]['source_observation_id']
    result = calculate(inputs)
    assert result['cells'][EFFECT]['value'] is None
    assert 'conflicting_source_owner_binding' in result['cells'][EFFECT]['unavailable_reason']


@pytest.mark.parametrize('state', ['matched', 'different', 'unknown', 'conflicting'])
def test_nonintended_conditions_remain_qualifications_not_new_gates(state):
    inputs = shared()
    inputs['relationships']['nonintended_conditions'] = state
    result = calculate(inputs)
    assert result['cells'][EFFECT]['value'] == .002
    if state != 'matched':
        assert 'nonintended_conditions_' + state in result['cells'][EFFECT]['conditional_on']


def test_full_role_covariance_and_owner_subset_agree_without_reading_preference():
    inputs = shared()
    graph(inputs['arms'][ROLES[3]])
    expected = calculate(inputs)['cells'][VARIANCE]
    inputs['covariance'] = {'primitive_order': list(ROLES),
        'physical_observation_ids': ['A', 'B', 'C', 'B'], 'units': ['nmol/min'] * 4,
        'matrix': [[.25, .01, .1, .01], [.01, .04, .02, .04],
                   [.1, .02, .25, .02], [.01, .04, .02, .04]]}
    assert calculate(inputs)['cells'][VARIANCE] == expected
    assert calculate(inputs)['contrast_dependencies']['provided_covariance_owner_ids'] == ['A', 'B', 'C']


def test_covariance_both_unit_factors_and_repeated_rows_in_base_units():
    inputs = shared()
    inputs['arms'][ROLES[3]].update(value=.00405, unit='umol/min')
    inputs['covariance'] = {'primitive_order': list(ROLES),
        'physical_observation_ids': ['A', 'B', 'C', 'B'],
        'units': ['nmol/min', 'nmol/min', 'nmol/min', 'umol/min'],
        'matrix': [[.25, 0, .1, 0], [0, .04, 0, .00004],
                   [.1, 0, .25, 0], [0, .00004, 0, .00000004]]}
    result = calculate(inputs)
    assert result['cells'][EFFECT]['value'] == .002
    assert result['cells'][VARIANCE]['value'] == 3e-7
    inputs['covariance']['units'] = ['umol/min'] * 4
    inputs['covariance']['matrix'] = [[.00000025, 0, .0000001, 0], [0, .00000004, 0, .00000004],
        [.0000001, 0, .00000025, 0], [0, .00000004, 0, .00000004]]
    assert calculate(inputs)['cells'][VARIANCE]['value'] == 3e-7


def test_missing_active_covariance_is_not_filled_zero():
    inputs = shared()
    inputs['covariance'] = {'physical_observation_ids': ['A'], 'units': ['nmol/min'], 'matrix': [[.25]]}
    result = calculate(inputs)
    assert result['cells'][EFFECT]['value'] == .002
    assert result['contrast_dependencies']['covariance_state'] == 'incomplete_active_coverage'
    assert result['cells'][VARIANCE]['unavailable_reason'] == ['incomplete_active_covariance']


def test_full_role_covariance_accepts_missing_canceled_numbers_and_mean_units():
    inputs = shared()
    for i in (1, 3):
        unavailable(inputs['arms'][ROLES[i]])
    inputs['covariance'] = {'primitive_order': list(ROLES),
        'physical_observation_ids': ['A', 'B', 'C', 'B'], 'units': ['nmol/min'] * 4,
        'matrix': [[.25, 0, .1, 0], [0, .04, 0, .04],
                   [.1, 0, .25, 0], [0, .04, 0, .04]]}
    result = calculate(inputs)
    assert result['cells'][EFFECT]['value'] == .002
    assert result['cells'][VARIANCE]['value'] == 3e-7
    assert result['contrast_dependencies']['covariance_state'] == 'available'
    assert result['inputs']['arms'][ROLES[1]]['unit'] is None


def test_role_covariance_alias_units_have_one_physical_dimension_even_if_unused():
    inputs = shared()
    for i in (1, 3):
        unavailable(inputs['arms'][ROLES[i]])
    inputs['covariance'] = {'primitive_order': list(ROLES),
        'physical_observation_ids': ['A', 'B', 'C', 'B'],
        'units': ['nmol/min', 'nmol/min', 'nmol/min', 'nM/min'],
        'matrix': [[.25, 0, .1, 0], [0, .04, 0, .04],
                   [.1, 0, .25, 0], [0, .04, 0, .04]]}
    with pytest.raises(ExperimentalContractError, match='covariance_unit_mismatch'):
        owner.populate_controlled_response_owner(inputs)


@pytest.mark.parametrize('mutation,code', [
    (lambda x: x['covariance']['matrix'][0].__setitem__(0, -.1), 'positive_semidefinite_covariance_required'),
    (lambda x: x['covariance']['matrix'][0].__setitem__(1, .2), 'symmetric_covariance_required'),
    (lambda x: x['covariance']['physical_observation_ids'].__setitem__(0, 'absent'), 'covariance_owner_mismatch'),
    (lambda x: x['covariance']['units'].__setitem__(0, 'uM/min'), 'covariance_unit_mismatch'),
    (lambda x: x['covariance']['matrix'].__setitem__(0, [1]), 'square_covariance_required'),
    (lambda x: x.update(covariance=None), 'covariance_status_mismatch'),
    (lambda x: x.update(variance_status='unknown'), 'covariance_status_mismatch'),
    (lambda x: x['covariance'].update(extra=0), 'closed_fields_required'),
])
def test_invalid_direct_covariance_is_actionable(mutation, code):
    inputs = shared()
    mutation(inputs)
    with pytest.raises(ExperimentalContractError, match=code):
        owner.populate_controlled_response_owner(inputs)


def test_invalid_canceled_row_in_full_matrix_cannot_be_rescued():
    inputs = shared()
    inputs['covariance'] = {'primitive_order': list(ROLES), 'physical_observation_ids': ['A', 'B', 'C', 'B'],
        'units': ['nmol/min'] * 4, 'matrix': [[.25, 0, .1, 0], [0, -.04, 0, -.04],
                   [.1, 0, .25, 0], [0, -.04, 0, -.04]]}
    with pytest.raises(ExperimentalContractError, match='positive_semidefinite_covariance_required'):
        owner.populate_controlled_response_owner(inputs)
    inputs['covariance']['matrix'][1][1] = inputs['covariance']['matrix'][3][3] = .04
    inputs['covariance']['matrix'][1][3] = inputs['covariance']['matrix'][3][1] = 0
    with pytest.raises(ExperimentalContractError, match='shared_measurement_covariance_mismatch'):
        owner.populate_controlled_response_owner(inputs)


def test_exact_psd_has_no_float_tolerance_or_jitter():
    inputs = shared()
    inputs['covariance']['matrix'] = [[0, 1e-300], [1e-300, 1e308]]
    with pytest.raises(ExperimentalContractError, match='positive_semidefinite_covariance_required'):
        owner.populate_controlled_response_owner(inputs)


@pytest.mark.parametrize('value', [7, 8, 10])
def test_signed_normal_model_uses_only_actual_active_covariance(value):
    inputs = shared()
    graph(inputs['arms'][ROLES[3]])
    inputs['arms'][ROLES[0]]['value'] = value
    inputs['model_kind'] = 'known_joint_normal_source_means'
    result = calculate(inputs)
    e = Fraction(value - 8, 1000)
    score = e * abs(e) / (2 * Fraction(3, 10_000_000))
    assert result['cells'][SCORE]['value'] == float(score)
    assert result['cells'][INDEX]['value'] == math.tanh(float(score / 2))
    assert 'canceled_graph_reading' in result['cells'][SCORE]['conditional_on']
    assert 'unresolved_reading_model' not in (result['cells'][SCORE]['unavailable_reason'] or [])


def test_estimated_covariance_never_promoted_after_cancellation():
    inputs = shared()
    inputs.update(variance_status='estimated', model_kind='known_joint_normal_source_means')
    result = calculate(inputs)
    assert result['cells'][VARIANCE]['value'] == 3e-7
    assert result['cells'][SCORE]['unavailable_reason'] == ['estimated_covariance']


def test_graph_active_owner_keeps_its_bounds_and_blocks_normal_profile():
    inputs = shared()
    graph(inputs['arms'][ROLES[0]], 10, 9.9, 10.1)
    inputs['model_kind'] = 'known_joint_normal_source_means'
    result = calculate(inputs)
    assert result['cells'][EFFECT]['value'] == .002
    assert (result['cells'][EFFECT]['lower'], result['cells'][EFFECT]['upper']) == (.0019, .0021)
    assert result['cells'][VARIANCE]['value'] == 3e-7
    assert result['cells'][SCORE]['unavailable_reason'] == ['unresolved_reading_model']
    assert result['cells'][EFFECT]['origin'] == 'synthetic'
    assert result['cells'][EFFECT]['approximate'] is True


def test_active_censoring_vs_canceled_censoring():
    inputs = shared()
    inputs['model_kind'] = 'known_joint_normal_source_means'
    for i in (1, 3):
        inputs['arms'][ROLES[i]].update(value=None, threshold=4, status='bound', relation='lt')
    assert calculate(inputs)['cells'][SCORE]['value'] is not None
    inputs['arms'][ROLES[0]].update(value=None, threshold=10, status='bound', relation='lt')
    result = calculate(inputs)
    assert result['cells'][EFFECT]['upper'] == .002
    assert result['cells'][EFFECT]['relation'] == 'lt'
    assert result['cells'][VARIANCE]['unavailable_reason'] == ['unresolved_censoring_model']


def test_zero_variance_is_exact_but_no_precision_or_profile():
    inputs = shared()
    inputs['model_kind'] = 'known_joint_normal_source_means'
    inputs['covariance']['matrix'] = [[.25, .25], [.25, .25]]
    result = calculate(inputs)
    assert result['cells'][VARIANCE]['value'] == result['cells'][SE]['value'] == 0
    for key in (PRECISION, SCORE, INDEX):
        assert result['cells'][key]['value'] is None
        assert result['cells'][key]['unavailable_reason'] == ['nonpositive_variance_for_model']


def test_partial_independent_cell_ranges_are_not_a_cascade():
    inputs = distinct()
    inputs['model_kind'] = 'known_joint_normal_source_means'
    for i, role in enumerate(ROLES):
        inputs['arms'][role]['value'] = 2e-160 if i == 0 else 1e-160 if i == 2 else 0
    inputs['covariance']['matrix'] = [[1e-320 if i == j else 0 for j in range(4)] for i in range(4)]
    result = calculate(inputs)
    assert result['cells'][VARIANCE]['value'] is None
    assert result['cells'][SE]['value'] == pytest.approx(2e-163, abs=0, rel=1e-14)
    assert result['cells'][SCORE]['value'] == .125
    assert result['cells'][INDEX]['value'] == math.tanh(.0625)


def test_canceled_huge_native_readings_do_not_overflow_active_effect():
    inputs = shared()
    for i in (1, 3):
        inputs['arms'][ROLES[i]].update(value=1e308, unit='mmol/min')
    result = calculate(inputs)
    assert result['cells'][old.COMPONENTS[1]]['value'] is None
    assert result['cells'][EFFECT]['value'] == .002
    assert result['cells'][VARIANCE]['value'] == 3e-7


@pytest.mark.parametrize('value', [True, False, float('nan'), float('inf'), '10', 10**1000])
def test_finite_json_numeric_contract_including_canceled_values(value):
    inputs = shared()
    inputs['arms'][ROLES[1]]['value'] = value
    with pytest.raises(ExperimentalContractError, match='finite_number_required'):
        owner.populate_controlled_response_owner(inputs)


@pytest.mark.parametrize('mutation', [
    lambda x: x.update(extra=1),
    lambda x: x['arms'][ROLES[0]].update(extra=1),
    lambda x: x['relationships'].update(extra=1),
    lambda x: x['arms'][ROLES[0]]['meaning_statuses'].update(extra='known'),
])
def test_closed_input_prevents_undeclared_scientific_shortcuts(mutation):
    inputs = shared()
    mutation(inputs)
    with pytest.raises(ExperimentalContractError, match='closed_fields_required'):
        owner.populate_controlled_response_owner(inputs)


@pytest.mark.parametrize('index', [0, 3], ids=['active', 'canceled'])
@pytest.mark.parametrize('approximate', [False, True])
def test_synthetic_graph_retains_origin_bounds_and_actual_dependencies(index, approximate):
    inputs = shared()
    inputs['model_kind'] = 'known_joint_normal_source_means'
    row = inputs['arms'][ROLES[index]]
    graph(row, 10, 9.9, 10.1) if index == 0 else graph(row)
    row.update(origin='synthetic', approximate=approximate)
    assert owner.validate_controlled_response_owner_inputs(inputs) == inputs
    result = calculate(inputs)
    cells = result['cells']
    assert result['inputs']['arms'][ROLES[index]] == row
    assert cells[old.COMPONENTS[index]]['origin'] == 'synthetic'
    assert cells[old.COMPONENTS[index]]['bound_kind'] == 'conditional_digitization'
    assert 'conditional_digitization' in cells[old.COMPONENTS[index]]['conditional_on']
    assert cells[EFFECT]['value'] == .002
    assert cells[VARIANCE]['value'] == 3e-7
    if index == 0:
        assert (cells[EFFECT]['lower'], cells[EFFECT]['upper']) == (.0019, .0021)
        assert cells[EFFECT]['bound_kind'] == 'conditional_digitization'
        for component in (SCORE, INDEX):
            assert cells[component]['unavailable_reason'] == ['unresolved_reading_model']
    else:
        assert cells[EFFECT]['lower'] is cells[EFFECT]['upper'] is None
        assert cells[old.COMPONENTS[5]]['value'] == .00395
        assert (cells[old.COMPONENTS[5]]['lower'], cells[old.COMPONENTS[5]]['upper']) == (.00385, .00405)
        assert cells[SCORE]['value'] == float(Fraction(20, 3))
        assert cells[INDEX]['value'] == math.tanh(float(Fraction(10, 3)))
        assert 'canceled_graph_reading' in cells[SCORE]['conditional_on']
        assert 'canceled_graph_reading' in result['contrast_dependencies']['canceled_reading_qualifications']


@pytest.mark.parametrize('value,lower,upper', [(10, 10, 11), (10, 9, 10), (10, 10, 10)])
def test_synthetic_interval_includes_both_endpoints(value, lower, upper):
    inputs = shared()
    graph(inputs['arms'][ROLES[0]], value, lower, upper)
    inputs['arms'][ROLES[0]]['origin'] = 'synthetic'
    result = calculate(inputs)
    assert result['cells'][EFFECT]['lower'] == float(Fraction(str(lower)) / 1000 - Fraction(8, 1000))
    assert result['cells'][EFFECT]['upper'] == float(Fraction(str(upper)) / 1000 - Fraction(8, 1000))


@pytest.mark.parametrize('index', [0, 3], ids=['active', 'canceled'])
@pytest.mark.parametrize('patch,code', [
    ({'digitization_interval': {'lower': 11, 'upper': 9}}, 'digitization_interval_mismatch'),
    ({'digitization_interval': {'lower': 10.1, 'upper': 11}}, 'digitization_interval_mismatch'),
    ({'digitization_interval': {'lower': 8, 'upper': 9.9}}, 'digitization_interval_mismatch'),
    ({'digitization_interval': {'lower': float('nan'), 'upper': 11}}, 'finite_number_required'),
    ({'digitization_interval': {'lower': 9, 'upper': float('inf')}}, 'finite_number_required'),
    ({'digitization_interval': {'lower': True, 'upper': 11}}, 'finite_number_required'),
    ({'digitization_interval': {'lower': 9}}, 'closed_fields_required'),
    ({'digitization_interval': None}, 'digitization_interval_required'),
    ({'relation': 'eq'}, 'digitization_interval_mismatch'),
    ({'status': 'bound', 'value': None, 'threshold': 10, 'relation': 'lt'}, 'digitization_interval_mismatch'),
    ({'status': 'ambiguous', 'value': None, 'relation': 'none'}, 'digitization_interval_mismatch'),
    ({'status': 'point', 'value': None}, 'point_contract_mismatch'),
    ({'status': 'point', 'threshold': 10}, 'point_contract_mismatch'),
    ({'origin': 'reported'}, 'digitization_interval_mismatch'),
])
def test_synthetic_graph_validation_is_required_even_for_canceled_owners(index, patch, code):
    inputs = shared()
    row = inputs['arms'][ROLES[index]]
    graph(row, 10, 9, 11)
    row['origin'] = 'synthetic'
    row.update(patch)
    before = deepcopy(inputs)
    for function in (owner.validate_controlled_response_owner_inputs, owner.populate_controlled_response_owner):
        with pytest.raises(ExperimentalContractError, match=code):
            function(inputs)
    # NaN is deliberately invalid; compare retained fields through identity of
    # the original object rather than equality of independently copied NaNs.
    assert inputs.keys() == before.keys()
    assert inputs['arms'][ROLES[index]] is row


def test_synthetic_graph_cannot_bypass_science_or_full_covariance():
    inputs = shared()
    graph(inputs['arms'][ROLES[3]])
    inputs['arms'][ROLES[3]]['origin'] = 'synthetic'
    inputs['arms'][ROLES[3]]['normalization_id'] = None
    inputs['arms'][ROLES[3]]['meaning_statuses']['normalization'] = 'unknown'
    result = calculate(inputs)
    assert 'unknown_normalization' in result['cells'][EFFECT]['unavailable_reason']
    assert result['cells'][EFFECT]['value'] is None
    inputs['covariance'] = {'primitive_order': list(ROLES), 'physical_observation_ids': ['A', 'B', 'C', 'B'],
        'units': ['nmol/min'] * 4, 'matrix': [[.25, 0, .1, 0], [0, -.04, 0, -.04],
        [.1, 0, .25, 0], [0, -.04, 0, -.04]]}
    with pytest.raises(ExperimentalContractError, match='positive_semidefinite_covariance_required'):
        owner.populate_controlled_response_owner(inputs)


def test_synthetic_point_does_not_acquire_graph_method_qualification():
    inputs = shared()
    inputs['model_kind'] = 'known_joint_normal_source_means'
    result = calculate(inputs)
    assert result['cells'][SCORE]['value'] is not None
    assert 'canceled_graph_reading' not in result['cells'][SCORE]['conditional_on']


def test_new_profile_uses_no_legacy_envelope_or_populator(monkeypatch):
    for name in ('_validate', '_validate_arm', 'populate_controlled_response'):
        monkeypatch.setattr(old, name, lambda *_: pytest.fail('legacy envelope or populator called'))
    inputs = shared()
    graph(inputs['arms'][ROLES[3]])
    inputs['arms'][ROLES[3]]['origin'] = 'synthetic'
    assert calculate(inputs)['cells'][EFFECT]['value'] == .002


def test_legacy_still_rejects_synthetic_interval_and_accepts_real_graph():
    inputs = no_covariance(distinct())
    graph(inputs['arms'][ROLES[0]], 12, 11, 13)
    inputs['version'] = old.INPUT_VERSION
    assert old.validate_controlled_response_inputs(inputs) == inputs
    inputs['arms'][ROLES[0]]['origin'] = 'synthetic'
    for function in (old.validate_controlled_response_inputs, old.populate_controlled_response):
        with pytest.raises(ExperimentalContractError, match='digitization_interval_mismatch:arms.protein_condition1'):
            function(inputs)


def structural_counterexamples():
    # The immutable legacy contract supplies an independent acceptance oracle.
    # Mutations cover all closed fields and each semantic identity, alongside
    # cross-field status, relation, source, target, unit and model constraints.
    baseline = no_covariance(distinct())
    cases = []
    for path in ((), ('arms',), ('relationships',), ('arms', ROLES[0]),
                 ('arms', ROLES[0], 'meaning_statuses'), ('relationships', 'condition1_target')):
        source = baseline
        for key in path:
            source = source[key]
        for key in [*source, 'extra']:
            changed = deepcopy(baseline)
            target = changed
            for part in path:
                target = target[part]
            if key == 'extra':
                target[key] = 'unrecognized'
            else:
                del target[key]
            cases.append(changed)
    for field, value in [('status', 'invented'), ('relation', 'invented'), ('origin', 'invented'),
                         ('protein_arrangement', 'invented'), ('approximate', 1), ('unit', 'mg'),
                         ('value', True), ('threshold', float('inf')), ('value', None),
                         ('relation', 'interval'), ('source_observation_id', None),
                         ('source_observation_id', ''), ('status', 'missing')]:
        changed = deepcopy(baseline)
        changed['arms'][ROLES[0]][field] = value
        cases.append(changed)
    for meaning in old._MEANINGS:
        for state, identity in [('unknown', 'still_known'), ('known', None), ('invalid', None), ('known', ' ')]:
            changed = deepcopy(baseline)
            row = changed['arms'][ROLES[0]]
            row['meaning_statuses'][meaning] = state
            row[meaning + '_id'] = identity
            cases.append(changed)
    for field, value in [('model_kind', 'invalid'), ('variance_status', 'invalid')]:
        changed = deepcopy(baseline); changed[field] = value; cases.append(changed)
    for key in baseline['relationships']:
        changed = deepcopy(baseline)
        changed['relationships'][key] = {'status': 'known', 'canonical_id': None} if key.endswith('_target') else 42
        cases.append(changed)
    return cases


@pytest.mark.parametrize('inputs', structural_counterexamples())
def test_owner_and_legacy_structural_rejections_agree(inputs):
    legacy = deepcopy(inputs)
    if 'version' in legacy:
        legacy['version'] = old.INPUT_VERSION
    errors = []
    for function, candidate in ((owner.validate_controlled_response_owner_inputs, inputs),
                                (old.validate_controlled_response_inputs, legacy)):
        with pytest.raises(ExperimentalContractError) as caught:
            function(candidate)
        errors.append((caught.value.code, caught.value.field))
    assert errors[0] == errors[1]


@pytest.mark.parametrize('origin', ['reported', 'synthetic', 'graph_derived'])
def test_unchanged_distinct_owner_cells_match_legacy_across_origins(origin):
    inputs = distinct()
    for row in inputs['arms'].values():
        row['origin'] = origin
    if origin == 'graph_derived':
        graph(inputs['arms'][ROLES[0]], 12, 11, 13)
    inputs['model_kind'] = 'known_joint_normal_source_means'
    legacy = {**deepcopy(inputs), 'version': old.INPUT_VERSION}
    assert calculate(inputs)['cells'] == old.populate_controlled_response(legacy)['cells']
