"""Parsed v3 owner inputs (controlled_response_owner_inputs): refusals, reasons and hand-checked cells.

Constructed parsed inputs only (the owner-calculation test builders); no source,
image, model or episode execution. Cell values are in canonical umol/min, so a
nmol/min reading is scaled by 1/1000.
"""
from fractions import Fraction
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.experimental_activity_evidence import literature_controlled_response_owner_calculations as owner
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.experimental_activity_evidence.tests.test_literature_controlled_response_owner_calculations import ROLES, distinct, shared, graph
A, B1, C, B0 = ROLES


def refused(inputs, code):
    with pytest.raises(ExperimentalContractError) as error:
        owner.populate_controlled_response_owner(inputs)
    assert error.value.code == code


def no_covariance(inputs):
    inputs.update(covariance=None, variance_status='unknown')
    return inputs


def cells(inputs):
    return owner.populate_controlled_response_owner(inputs)['cells']


@pytest.mark.parametrize('change,code', [
    (lambda x: x['arms'][A].update(status='estimated'), 'unsupported_value'),
    (lambda x: x['arms'][A].update(unit='mol/min'), 'unsupported_value'),
    (lambda x: x['relationships'].update(nonintended_conditions='similar'), 'unsupported_value'),
    (lambda x: x['arms'][A].update(endpoint_id=' '), 'nonempty_identity_required'),
    (lambda x: x['relationships'].update(intended_factor=''), 'nonempty_identity_required'),
    (lambda x: x['covariance']['physical_observation_ids'].__setitem__(0, ' '), 'nonempty_identity_required'),
    (lambda x: x['arms'][A].update(approximate=0), 'boolean_required'),
    (lambda x: x['arms'][A].update(endpoint_id=None), 'meaning_identity_mismatch'),
    (lambda x: x['relationships']['condition1_target'].update(canonical_id=None), 'meaning_identity_mismatch'),
    (lambda x: x.update(version='unrecognized_version'), 'unsupported_input_version'),
    (lambda x: x['covariance'].update(primitive_order=list(reversed(ROLES))), 'covariance_order_mismatch'),
    (lambda x: x['arms'][A].update(status='bound', value=None, threshold=10, relation='eq'), 'bound_contract_mismatch'),
    (lambda x: x['arms'][A].update(status='missing', relation='none', threshold=None), 'unavailable_measurement_must_be_null'),
    (lambda x: x['arms'][A].update(status='missing', value=None, relation='none'), 'missing_source_identity_must_be_null'),
], ids=['status', 'unit', 'relationship', 'blank_meaning_id', 'blank_intended_factor', 'blank_covariance_owner', 'approximate_int', 'known_meaning_without_id', 'known_target_without_id', 'version', 'role_order', 'bound_relation', 'missing_with_value', 'missing_with_source_id'])
def test_parsed_owner_input_contract_failures_name_their_field(change, code):
    inputs = distinct()
    change(inputs)
    refused(inputs, code)


def test_shared_measurement_rows_must_share_their_measurement_context():
    inputs = distinct()
    inputs['arms'][B0].update(physical_observation_id=B1, source_observation_id='constructed_source_' + B1)
    inputs['covariance']['physical_observation_ids'][3] = B1
    inputs['covariance']['matrix'][1][1] = inputs['covariance']['matrix'][3][3] = 0.25
    inputs['covariance']['matrix'][1][3] = inputs['covariance']['matrix'][3][1] = 0.25
    refused(inputs, 'shared_measurement_context_mismatch')


def test_protein_and_control_sharing_a_source_reading_are_conflicting_literals():
    """The condition-one control claims the protein reading's source token but reports another value."""
    inputs = no_covariance(distinct())
    graph(inputs['arms'][B1], 2, 1.5, 2.5)
    inputs['arms'][B1]['source_observation_id'] = inputs['arms'][A]['source_observation_id']
    cell = cells(inputs)['condition1_controlled_response']
    assert cell['status'] == 'conflicting' and cell['value'] is None
    assert {'conflicting_source_literal', 'conflicting_protein_arrangement', 'conflicting_subject_correspondence'} <= set(cell['unavailable_reason'])


def test_protein_and_control_on_one_owner_compare_their_readings():
    inputs = no_covariance(distinct())
    inputs['arms'][B1]['physical_observation_id'] = A
    inputs['arms'][B1]['unit'] = 'uM/min'
    cell = cells(inputs)['condition1_controlled_response']
    assert {'incompatible_unit_dimension', 'conflicting_protein_arrangement'} <= set(cell['unavailable_reason'])


def test_pair_readings_of_different_dimension_have_no_condition_response():
    inputs = no_covariance(distinct())
    inputs['arms'][B1]['unit'] = 'uM/min'
    sheet = cells(inputs)
    assert 'incompatible_unit_dimension' in sheet['condition1_controlled_response']['unavailable_reason']
    # The condition-zero pair is untouched: (5 - 1) nmol/min = 0.004 umol/min.
    assert sheet['condition0_controlled_response']['value'] == 0.004


def test_protein_reading_of_another_condition_is_a_different_correspondence():
    inputs = no_covariance(distinct())
    inputs['arms'][A]['condition_id'] = 'c0'
    cell = cells(inputs)['condition1_controlled_response']
    assert cell['status'] == 'unavailable' and 'different_condition_correspondence' in cell['unavailable_reason']


def test_unknown_control_reuse_and_estimated_covariance_are_carried_as_qualifications():
    """Effect (12 - 2) - (5 - 1) = 6 nmol/min = 0.006 umol/min.

    Variance with distinct owners: 1 + 0.25 + 0.36 + 0.09 = 1.7 (nmol/min)^2 = 1.7e-6 (umol/min)^2.
    """
    inputs = distinct()
    inputs['relationships']['control_reference_reuse'] = 'unknown'
    inputs['variance_status'] = 'estimated'
    sheet = cells(inputs)
    effect, variance, score = (sheet['controlled_response_difference'], sheet['contrast_variance'], sheet['source_profile_log_ratio'])
    assert effect['value'] == 0.006 and 'unknown_control_reuse' in effect['conditional_on']
    assert variance['value'] == float(Fraction(17, 10 ** 7)) and 'estimated_covariance' in variance['conditional_on']
    assert score['value'] is None and 'estimated_covariance' in score['unavailable_reason']


def test_raw_reading_beyond_double_range_in_canonical_unit_is_a_range_failure():
    # 1e306 mmol/min = 1e309 umol/min, which no double represents.
    inputs = no_covariance(distinct())
    inputs['arms'][A].update(value=1e306, unit='mmol/min')
    cell = cells(inputs)['protein_condition1_response']
    assert cell['value'] is None and cell['status'] == 'unavailable' and cell['unavailable_reason'] == ['numeric_range_failure']


def test_reported_limit_beyond_double_range_in_canonical_unit_is_a_bound_range_failure():
    # A > 1e306 mmol/min: the lower limit is 1e309 umol/min and the upper side is unbounded.
    inputs = no_covariance(distinct())
    inputs['arms'][A].update(status='bound', value=None, threshold=1e306, relation='gt', unit='mmol/min')
    cell = cells(inputs)['protein_condition1_response']
    assert cell['bound_state'] == {'lower': 'numeric_range_failure', 'upper': 'unbounded'}
    assert (cell['lower'], cell['upper']) == (None, None)
    assert cell['status'] == 'unavailable' and cell['unavailable_reason'] == ['numeric_range_failure']


def test_two_upper_limits_bound_nothing_about_their_difference():
    # protein < 10 and control < 2: protein - control has neither a lower nor an upper bound.
    inputs = no_covariance(distinct())
    inputs['arms'][A].update(status='bound', value=None, threshold=10, relation='lt')
    inputs['arms'][B1].update(status='bound', value=None, threshold=2, relation='lt')
    cell = cells(inputs)['condition1_controlled_response']
    assert (cell['value'], cell['lower'], cell['upper']) == (None, None, None)
    assert cell['status'] == 'unavailable' and cell['unavailable_reason'] == ['uninformative_bounds']


def test_canceled_shared_control_without_a_unit_is_a_qualified_cancellation():
    """Shared B cancels: effect = A - C = (10 - 8) nmol/min = 0.002 umol/min."""
    inputs = shared()
    for role in (B1, B0):
        inputs['arms'][role]['unit'] = None
    sheet = owner.populate_controlled_response_owner(inputs)
    assert 'canceled_unit_unknown' in sheet['contrast_dependencies']['canceled_reading_qualifications']
    assert sheet['cells']['controlled_response_difference']['value'] == 0.002


def test_active_lower_limit_leaves_a_one_sided_effect_and_no_variance():
    """A > 10 nmol/min with shared B canceled: A - C > (10 - 8) nmol/min = 0.002 umol/min."""
    inputs = shared()
    inputs['arms'][A].update(status='bound', value=None, threshold=10, relation='gt')
    sheet = owner.populate_controlled_response_owner(inputs)['cells']
    effect = sheet['controlled_response_difference']
    assert (effect['value'], effect['lower'], effect['upper'], effect['relation']) == (None, 0.002, None, 'gt')
    assert effect['status'] == 'bounded' and effect['bound_kind'] == 'reported_limit'
    assert 'unresolved_censoring_model' in sheet['contrast_variance']['unavailable_reason']
    assert 'unresolved_censoring_model' in sheet['source_profile_log_ratio']['unavailable_reason']


def test_owner_reading_dependencies_qualify_canceled_and_block_active_disagreement():
    """Shared B (+1 condition-zero control, -1 condition-one control) cancels; A and B0 on one owner add to +2."""
    inputs = shared()
    inputs['arms'][B0].update(value=5, status='point')
    inputs['arms'][B1].update(value=None, status='conflicting', relation='none')
    dependencies = owner.populate_controlled_response_owner(inputs)['contrast_dependencies']
    assert {'canceled_reading_unavailable', 'canceled_source_reading_conflict', 'canceled_representation_difference'} <= set(dependencies['canceled_reading_qualifications'])
    inputs = shared()
    inputs['arms'][B0]['value'] = 5
    dependencies = owner.populate_controlled_response_owner(inputs)['contrast_dependencies']
    # 4 and 5 nmol/min are disjoint exact readings of one canceled owner.
    assert {'canceled_reading_domain_conflict', 'canceled_source_reading_conflict'} <= set(dependencies['canceled_reading_qualifications'])
    for value, reason in ((11, 'conflicting_source_literal'), (10, 'unresolved_active_reading_model')):
        inputs = no_covariance(shared())
        row = inputs['arms'][B0]
        row.update({k: inputs['arms'][A][k] for k in ('physical_observation_id', 'source_observation_id')}, value=value)
        if value == 10:
            row['approximate'] = True
        dependencies = owner.populate_controlled_response_owner(inputs)['contrast_dependencies']
        assert reason in dependencies['active_reading_reasons']
