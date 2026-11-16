"""Constructed parsed inputs only; no source, image, model or episode execution."""
from copy import deepcopy
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.library import literature_controlled_response_calculations as old
from gene_annotation_episode.episodic_workflow.root.a105.library import literature_controlled_response_owner_calculations as owner
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_contracts import ExperimentalContractError
ROLES = old.PRIMITIVE_ORDER
EFFECT, VARIANCE, SE, PRECISION, SCORE, INDEX = old.COMPONENTS[6:]

def arm(value, condition, physical, *, control=False):
    return {'value': value, 'threshold': None, 'relation': 'eq', 'approximate': False, 'unit': 'nmol/min', 'status': 'point', 'endpoint_id': 'constructed_initial_rate', 'normalization_id': 'constructed_common_basis', 'subject_construct_id': 'constructed_empty' if control else 'constructed_protein', 'condition_id': condition, 'physical_observation_id': physical, 'source_observation_id': 'constructed_source_' + physical, 'origin': 'synthetic', 'digitization_interval': None, 'protein_arrangement': 'protein_free_control' if control else 'protein_present', 'meaning_statuses': dict.fromkeys(old._MEANINGS, 'known')}

def distinct():
    arms = {role: arm(value, 'c1' if i < 2 else 'c0', role, control=i % 2 == 1) for i, (role, value) in enumerate(zip(ROLES, (12, 2, 5, 1)))}
    return {'version': 'controlled_response_owner_inputs_v2', 'arms': arms, 'relationships': {'condition1_target': {'status': 'known', 'canonical_id': 'c1'}, 'condition0_target': {'status': 'known', 'canonical_id': 'c0'}, 'condition_levels_relation': 'different', 'subject_construct_across_conditions': 'same', 'condition1_control_application': 'matched_condition_control', 'condition0_control_application': 'matched_condition_control', 'control_reference_reuse': 'distinct_observations', 'nonintended_conditions': 'unknown', 'intended_factor': 'constructed_intended_change'}, 'covariance': {'primitive_order': list(ROLES), 'physical_observation_ids': list(ROLES), 'units': ['nmol/min'] * 4, 'matrix': [[v if i == j else 0 for j in range(4)] for i, v in enumerate((1, 0.25, 0.36, 0.09))]}, 'variance_status': 'known', 'model_kind': 'none'}

def shared():
    inputs = distinct()
    inputs['arms'] = dict(zip(ROLES, (arm(10, 'c1', 'A'), arm(4, 'reference', 'B', control=True), arm(8, 'c0', 'C'), arm(4, 'reference', 'B', control=True))))
    inputs['relationships'].update(condition1_control_application='shared_reference_assumption', condition0_control_application='shared_reference_assumption', control_reference_reuse='same_reference_with_stated_invariance')
    inputs['covariance'] = {'physical_observation_ids': ['A', 'C'], 'units': ['nmol/min'] * 2, 'matrix': [[0.25, 0.1], [0.1, 0.25]]}
    return inputs

def graph(row, value=4.05, lower=3.95, upper=4.15):
    row.update(value=value, origin='graph_derived', approximate=True, relation='interval', source_observation_id=row['source_observation_id'] + '_graph', digitization_interval={'lower': lower, 'upper': upper})

def unavailable(row, status='missing', *, unit=None):
    row.update(value=None, threshold=None, relation='none', status=status, unit=unit, digitization_interval=None, approximate=False)
    if status == 'missing':
        row['source_observation_id'] = None




















def test_role_covariance_alias_units_have_one_physical_dimension_even_if_unused():
    inputs = shared()
    for i in (1, 3):
        unavailable(inputs['arms'][ROLES[i]])
    inputs['covariance'] = {'primitive_order': list(ROLES), 'physical_observation_ids': ['A', 'B', 'C', 'B'], 'units': ['nmol/min', 'nmol/min', 'nmol/min', 'nM/min'], 'matrix': [[0.25, 0, 0.1, 0], [0, 0.04, 0, 0.04], [0.1, 0, 0.25, 0], [0, 0.04, 0, 0.04]]}
    with pytest.raises(ExperimentalContractError, match='covariance_unit_mismatch'):
        owner.populate_controlled_response_owner(inputs)

@pytest.mark.parametrize('mutation,code', [(lambda x: x['covariance']['matrix'][0].__setitem__(0, -0.1), 'positive_semidefinite_covariance_required'), (lambda x: x['covariance']['matrix'][0].__setitem__(1, 0.2), 'symmetric_covariance_required'), (lambda x: x['covariance']['physical_observation_ids'].__setitem__(0, 'absent'), 'covariance_owner_mismatch'), (lambda x: x['covariance']['units'].__setitem__(0, 'uM/min'), 'covariance_unit_mismatch'), (lambda x: x['covariance']['matrix'].__setitem__(0, [1]), 'square_covariance_required'), (lambda x: x.update(covariance=None), 'covariance_status_mismatch'), (lambda x: x.update(variance_status='unknown'), 'covariance_status_mismatch'), (lambda x: x['covariance'].update(extra=0), 'closed_fields_required')])
def test_invalid_direct_covariance_is_actionable(mutation, code):
    inputs = shared()
    mutation(inputs)
    with pytest.raises(ExperimentalContractError, match=code):
        owner.populate_controlled_response_owner(inputs)

def test_invalid_canceled_row_in_full_matrix_cannot_be_rescued():
    inputs = shared()
    inputs['covariance'] = {'primitive_order': list(ROLES), 'physical_observation_ids': ['A', 'B', 'C', 'B'], 'units': ['nmol/min'] * 4, 'matrix': [[0.25, 0, 0.1, 0], [0, -0.04, 0, -0.04], [0.1, 0, 0.25, 0], [0, -0.04, 0, -0.04]]}
    with pytest.raises(ExperimentalContractError, match='positive_semidefinite_covariance_required'):
        owner.populate_controlled_response_owner(inputs)
    inputs['covariance']['matrix'][1][1] = inputs['covariance']['matrix'][3][3] = 0.04
    inputs['covariance']['matrix'][1][3] = inputs['covariance']['matrix'][3][1] = 0
    with pytest.raises(ExperimentalContractError, match='shared_measurement_covariance_mismatch'):
        owner.populate_controlled_response_owner(inputs)

def test_exact_psd_has_no_float_tolerance_or_jitter():
    inputs = shared()
    inputs['covariance']['matrix'] = [[0, 1e-300], [1e-300, 1e+308]]
    with pytest.raises(ExperimentalContractError, match='positive_semidefinite_covariance_required'):
        owner.populate_controlled_response_owner(inputs)








@pytest.mark.parametrize('value', [True, False, float('nan'), float('inf'), '10', 10 ** 1000])
def test_finite_json_numeric_contract_including_canceled_values(value):
    inputs = shared()
    inputs['arms'][ROLES[1]]['value'] = value
    with pytest.raises(ExperimentalContractError, match='finite_number_required'):
        owner.populate_controlled_response_owner(inputs)

@pytest.mark.parametrize('mutation', [lambda x: x.update(extra=1), lambda x: x['arms'][ROLES[0]].update(extra=1), lambda x: x['relationships'].update(extra=1), lambda x: x['arms'][ROLES[0]]['meaning_statuses'].update(extra='known')])
def test_closed_input_prevents_undeclared_scientific_shortcuts(mutation):
    inputs = shared()
    mutation(inputs)
    with pytest.raises(ExperimentalContractError, match='closed_fields_required'):
        owner.populate_controlled_response_owner(inputs)



@pytest.mark.parametrize('index', [0, 3], ids=['active', 'canceled'])
@pytest.mark.parametrize('patch,code', [({'digitization_interval': {'lower': 11, 'upper': 9}}, 'digitization_interval_mismatch'), ({'digitization_interval': {'lower': 10.1, 'upper': 11}}, 'digitization_interval_mismatch'), ({'digitization_interval': {'lower': 8, 'upper': 9.9}}, 'digitization_interval_mismatch'), ({'digitization_interval': {'lower': float('nan'), 'upper': 11}}, 'finite_number_required'), ({'digitization_interval': {'lower': 9, 'upper': float('inf')}}, 'finite_number_required'), ({'digitization_interval': {'lower': True, 'upper': 11}}, 'finite_number_required'), ({'digitization_interval': {'lower': 9}}, 'closed_fields_required'), ({'digitization_interval': None}, 'digitization_interval_required'), ({'relation': 'eq'}, 'digitization_interval_mismatch'), ({'status': 'bound', 'value': None, 'threshold': 10, 'relation': 'lt'}, 'digitization_interval_mismatch'), ({'status': 'ambiguous', 'value': None, 'relation': 'none'}, 'digitization_interval_mismatch'), ({'status': 'point', 'value': None}, 'point_contract_mismatch'), ({'status': 'point', 'threshold': 10}, 'point_contract_mismatch'), ({'origin': 'reported'}, 'digitization_interval_mismatch')])
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
    assert inputs.keys() == before.keys()
    assert inputs['arms'][ROLES[index]] is row







