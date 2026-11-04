"""Numerical and dependency tests on actual constructed reader outcomes."""
from copy import deepcopy as cp
import math
import pytest
from test_literature_controlled_response_v3_inputs import Fixture, ROLES
from gene_annotation_episode import literature_controlled_response_local_calculations as local
from gene_annotation_episode import literature_controlled_response_owner_calculations as owner
from gene_annotation_episode import literature_controlled_response_calculations as legacy
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


def forbidden(*args, **kwargs):
    raise AssertionError('whole four-arm calculator forbidden for component-local work')


def inputs(index=0):
    return Fixture(index).read()['component_local_inputs']


def test_real_pair_magnitude_sampling_variance_graph_bounds_and_components(monkeypatch):
    data = inputs()
    monkeypatch.setattr(owner, 'populate_controlled_response_owner', forbidden)
    monkeypatch.setattr(owner, 'validate_controlled_response_owner_inputs', forbidden)
    monkeypatch.setattr(legacy, 'populate_controlled_response', forbidden)
    monkeypatch.setattr(legacy, 'validate_controlled_response_inputs', forbidden)
    monkeypatch.setattr(legacy, '_pair_reasons', forbidden)
    result = local.populate_controlled_response_local(data)
    pair = result['pairs'][0]
    assert pair['difference']['value'] == .00395
    assert pair['difference']['lower'] == .00385 and pair['difference']['upper'] == .00405
    assert pair['variance']['value'] == 4.5e-7
    assert pair['standard_uncertainty']['value'] == math.sqrt(4.5e-7)
    assert pair['variance']['conditional_on'] == ['approximate_source_reading','conditional_digitization','shared_reference_assumption','synthetic_fixture']
    assert result['raw'][0]['cell']['value'] == .01
    assert local.validate_controlled_response_local_sheet(data, result) == result
    assert data == result['inputs']


def test_unrelated_origin_and_number_dont_contaminate_pair():
    data = inputs()
    before = local.populate_controlled_response_local(data)['pairs'][0]
    data['readings'][0]['arm']['origin'] = 'reported'
    data['readings'][0]['source_kind'] = 'primary_source'
    data['readings'][0]['arm']['value'] = 500
    assert local.populate_controlled_response_local(data)['pairs'][0] == before


def test_variance_dependency_does_not_use_point_values_count_or_interval_width():
    data = inputs()
    original = local.populate_controlled_response_local(data)['pairs'][0]
    data['readings'][2]['arm']['value'] = 800
    data['readings'][2]['reported_uncertainty']['count'] = 100
    graph = data['readings'][3]['arm']
    graph['digitization_interval'] = dict(lower=0, upper=900)
    changed = local.populate_controlled_response_local(data)['pairs'][0]
    assert changed['difference'] != original['difference']
    for component in ('variance','standard_uncertainty'):
        assert changed[component] == original[component]
        dependency = changed['dependencies'][component]
        assert dependency['numeric_readings'] == [] and dependency['uncertainty_readings'] == []
        assert dependency['full_source_covariance_required']
        assert all('value' not in r['fields'] and 'digitization_interval' not in r['fields'] for r in dependency['numeric_fields'])


def test_unknown_owner_preserves_difference_not_covariance():
    result = local.populate_controlled_response_local(inputs(4))['pairs'][0]
    assert result['difference']['value'] == .00395
    assert result['variance']['value'] is None
    assert 'unknown_covariance_owner' in result['variance']['unavailable_reason']


def test_full_invalid_unused_row_cannot_be_repaired_by_good_marginal():
    result = local.populate_controlled_response_local(inputs(9))
    assert result['full_covariance_checks'][0]['source_validation'] == 'invalid'
    assert result['pairs'][0]['difference']['value'] == .00395
    assert 'source_full_covariance_invalid' in result['pairs'][0]['variance']['unavailable_reason']


@pytest.mark.parametrize('mutation', [
    lambda d: d['source_covariances'][0].update(source_validation='invalid'),
    lambda d: d['source_covariances'][0]['matrix_tokens'][0].__setitem__(0,'999'),
    lambda d: d['source_covariances'][0]['exact_matrix'][0][0].update(numerator='999'),
    lambda d: d['source_covariances'][0]['variables'][0].update(description='invented'),
    lambda d: d['source_covariances'][0]['variables'][0]['label_witness']['canonical_locator'].update(start=0),
    lambda d: d['source_covariances'][0].update(byte_sha256='0'*64),
])
def test_unchecked_validity_flags_and_retained_lexical_tampering_rejected(mutation):
    data = inputs(); mutation(data)
    with pytest.raises(ExperimentalContractError, match='local_covariance_document_mismatch'):
        local.populate_controlled_response_local(data)


def test_estimated_covariance_allowed_without_inventing_normal_statistic():
    f = Fixture(); f.doc['variance_status'] = 'estimated'; f.covariance()
    f.args['local_pair_assignments'][0]['covariance_selection'] = cp(f.args['covariance'])
    f.args['local_pair_assignments'][0]['variance_status'] = cp(f.args['variance_status'])
    result = local.populate_controlled_response_local(f.read()['component_local_inputs'])['pairs'][0]
    assert result['variance']['value'] == 4.5e-7
    assert 'estimated_covariance' in result['variance']['conditional_on']
    assert set(result) == {'pair_key','difference','variance','standard_uncertainty','dependencies'}


@pytest.mark.parametrize('factor', [0, 1e-320])
def test_zero_variance_and_independently_representable_se(factor):
    f = Fixture()
    f.doc['covariance'] = [[v*factor for v in row] for row in f.doc['covariance']]
    f.covariance()
    f.args['local_pair_assignments'][0]['covariance_selection'] = cp(f.args['covariance'])
    f.args['local_pair_assignments'][0]['variance_status'] = cp(f.args['variance_status'])
    pair = local.populate_controlled_response_local(f.read()['component_local_inputs'])['pairs'][0]
    if factor == 0:
        assert pair['variance']['value'] == pair['standard_uncertainty']['value'] == 0
    else:
        assert pair['variance']['value'] is None
        assert pair['variance']['unavailable_reason'] == ['numeric_range_failure']
        assert pair['standard_uncertainty']['value'] > 0


def test_absent_primary_vs_selected_missing_and_unresolved_selector():
    f = Fixture(local=False); f.args['arms'][ROLES[0]] = None
    f.args['covariance']['bindings'][ROLES[0]] = None
    data = f.read()['component_local_inputs']
    result = local.populate_controlled_response_local(data)
    assert result['raw'][0]['cell']['origin'] is None
    assert result['raw'][0]['cell']['unavailable_reason'] == ['missing_arm']
    assert result['raw'][1]['cell']['origin'] == 'synthetic'
    data = inputs(); data['pairs'][0]['protein']['reading_key'] = 'not-selected'
    with pytest.raises(ExperimentalContractError, match='local_reading_selector_unresolved'): local.populate_controlled_response_local(data)
    data = inputs(1)
    assert data['readings'][1]['arm'] is not None and data['readings'][1]['source_kind'] == 'synthetic_fixture'
    assert local.populate_controlled_response_local(data)['raw'][1]['cell']['origin'] == 'synthetic'


def test_pair_unknown_support_scoped_and_duplicate_reading_rejected():
    data = inputs(); data['pairs'][0]['joint_admissibility'] = 'unknown'
    result = local.populate_controlled_response_local(data)
    assert result['raw'][2]['cell']['value'] == .008
    assert 'unknown_joint_applicability' in result['pairs'][0]['difference']['unavailable_reason']
    data = inputs(); data['readings'].append(cp(data['readings'][0]))
    with pytest.raises(ExperimentalContractError, match='duplicate_local_reading_selector'): local.populate_controlled_response_local(data)


def test_origin_relabel_and_nomination_binding_divergence_rejected():
    data = inputs(); data['readings'][0]['arm']['origin'] = 'reported'
    with pytest.raises(ExperimentalContractError, match='local_reading_origin_mismatch'):
        local.populate_controlled_response_local(data)
    data = inputs(); data['pairs'][0]['protein_binding']['selection']['owner_witness']['quote'] = 'changed'
    result = local.populate_controlled_response_local(data)['pairs'][0]
    assert result['difference']['value'] == .00395
    assert 'local_covariance_binding_conflicting' in result['variance']['unavailable_reason']


def test_saved_sheet_actual_types_checked_boolean_is_not_numerical_zero():
    f = Fixture(); f.doc['covariance'] = [[0 for v in row] for row in f.doc['covariance']]
    f.covariance()
    f.args['local_pair_assignments'][0]['covariance_selection'] = cp(f.args['covariance'])
    f.args['local_pair_assignments'][0]['variance_status'] = cp(f.args['variance_status'])
    data = f.read()['component_local_inputs']; result = local.populate_controlled_response_local(data)
    assert result['pairs'][0]['variance']['value'] == 0
    result['pairs'][0]['variance']['value'] = False
    with pytest.raises(ExperimentalContractError, match='local_sheet_schema_invalid'):
        local.validate_controlled_response_local_sheet(data, result)
