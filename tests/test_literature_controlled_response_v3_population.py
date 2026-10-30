"""Separate population preserves real alternatives and numerical partials."""
from copy import deepcopy as cp
import pytest
from test_literature_controlled_response_v3_inputs import Fixture, ROLES
from gene_annotation_episode import literature_controlled_response_v3_inputs as source
from gene_annotation_episode import literature_controlled_response_v3_population as population
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


def test_ready_source_separate_numerical_population_and_reconstruction():
    f = Fixture(); extraction = f.read(); before = cp(extraction)
    result = population.populate_controlled_response_v3(extraction)
    assert extraction == before
    assert result['final_sheet']['cells']['controlled_response_difference']['value'] == .002
    assert result['final_sheet']['cells']['contrast_variance']['value'] == 3e-7
    assert result['local_sheet']['pairs'][0]['variance']['value'] == 4.5e-7
    assert population.validate_controlled_response_v3_population(extraction, result) == result
    result['local_sheet']['pairs'][0]['variance']['value'] = 0
    with pytest.raises(ExperimentalContractError, match='controlled_v3_population_reconstruction_mismatch'):
        population.validate_controlled_response_v3_population(extraction, result)


def test_real_alternatives_not_averaged_and_unresolved_contrast_not_final():
    result = population.populate_controlled_response_v3(Fixture(companion=True, joints=True).read())
    assert result['final_sheet'] is None
    assert result['partial_sheet'] is not None
    assert len(result['alternatives']) == 2
    assert [r['sheet']['cells']['controlled_response_difference']['value'] for r in result['alternatives']] == [.002,.00205]
    assert result['alternatives'][0]['sheet']['cells']['source_profile_log_ratio']['value'] is not None
    assert result['alternatives'][1]['sheet']['cells']['source_profile_log_ratio']['value'] is None
    assert result['local_sheet']['pairs'][0]['difference']['value'] == .00395
    components = {r['component'] for r in result['unaffected_components']}
    assert 'protein_condition0_response' in components
    assert 'controlled_response_difference' not in components
    assert 'protein_condition1_response' not in components
    assert len(result['conditional_components']) == 24


def test_no_joint_alternatives_preserves_independently_supported_local_results():
    result = population.populate_controlled_response_v3(Fixture(companion=True).read())
    assert result['alternatives'] == [] and result['conditional_components'] == []
    assert result['final_sheet'] is None
    assert result['local_sheet']['pairs'][0]['difference']['value'] == .00395
    assert all(r['component'] != 'controlled_response_difference' for r in result['unaffected_components'])
    assert any(r['component'] == 'protein_condition0_response' for r in result['unaffected_components'])


def test_mixed_source_origins_retain_local_cells_without_fake_group_origin():
    f = Fixture(companion=True)
    f.args['companion_readings'][0]['reading']['source_kind'] = 'primary_source'
    # Covariance is a synthetic fixture, so it cannot be used as primary-source
    # sampling uncertainty for that graph. Its actual magnitude still survives.
    extraction = f.read()
    assert extraction['partial_projection_state'] == 'unsupported_origin_projection'
    assert extraction['partial_calculation_inputs'] is None
    result = population.populate_controlled_response_v3(extraction)
    assert result['final_sheet'] is None and result['partial_sheet'] is None
    assert result['local_sheet']['raw'][0]['cell']['origin'] == 'synthetic'
    assert result['local_sheet']['raw'][4]['cell']['origin'] == 'graph_derived'
    assert result['local_sheet']['pairs'][0]['difference']['value'] == .00395
    assert any(r['component'] == 'protein_condition0_response' for r in result['unaffected_components'])


def test_selected_source_companion_can_supply_final_without_preferred_primary():
    f = Fixture(companion=True, authority=True, joints=True)
    primary = f.args['arms'][ROLES[0]]
    companion = f.args['companion_readings'][0]['reading']
    primary['measurement'], companion['measurement'] = companion['measurement'], primary['measurement']
    f.args['reading_reconciliations'][0]['authority']['reading']['reading_key'] = 'A-display'
    extraction = f.read()
    assert extraction['final_projection_basis']['covariance_scope'] == 'joint'
    assert extraction['final_projection_basis']['scope_index'] == 1
    result = population.populate_controlled_response_v3(extraction)
    assert result['final_sheet']['inputs']['arms'][ROLES[0]]['value'] == 10
    assert result['final_sheet']['cells']['controlled_response_difference']['value'] == .002


def test_unavailable_or_invalid_covariance_retains_real_magnitudes():
    result = population.populate_controlled_response_v3(Fixture(9).read())
    assert result['final_sheet']['cells']['controlled_response_difference']['value'] == .002
    assert result['final_sheet']['cells']['contrast_variance']['value'] is None
    assert result['local_sheet']['pairs'][0]['difference']['value'] == .00395
    assert result['local_sheet']['pairs'][0]['variance']['value'] is None


def test_final_companion_uses_actual_joint_covariance_lineage():
    import json
    f = Fixture(companion=True, authority=True, joints=True)
    primary, companion = f.args['arms'][ROLES[0]], f.args['companion_readings'][0]['reading']
    primary['measurement'], companion['measurement'] = companion['measurement'], primary['measurement']
    f.args['reading_reconciliations'][0]['authority']['reading']['reading_key'] = 'A-display'
    reference = 'source_' + 'a'*24
    doc = cp(f.doc); doc['covariance'] = [[2*v for v in row] for row in doc['covariance']]
    f.data[reference] = (json.dumps(doc, indent=2)+'\n').encode()
    scope = f.args['joint_scopes'][1]
    scope['covariance_selection']['source_ref'] = reference
    for binding in scope['covariance_selection']['bindings'].values():
        if binding is None: continue
        binding['label_witness']['source_ref'] = reference
        for witness in binding['correspondence']['witnesses']: witness['source_ref'] = reference
    extraction = f.read()
    result = population.populate_controlled_response_v3(extraction)
    assert result['final_sheet']['cells']['contrast_variance']['value'] == 6e-7
    assert result['local_sheet']['pairs'][0]['variance']['value'] == 4.5e-7
    # Alternatives differ, so no unqualified final variance is called unaffected.
    assert all(row['component'] != 'contrast_variance' for row in result['unaffected_components'])
    dependency = next(row['dependencies'] for row in result['conditional_components']
        if row['assignment_index'] == 1 and row['component'] == 'contrast_variance')
    assert extraction['component_local_inputs']['source_covariances'][dependency['covariance_index']]['source_ref'] == reference


def test_actual_saved_population_schema_rejects_boolean_numeric_alias():
    extraction = Fixture(11).read()
    result = population.populate_controlled_response_v3(extraction)
    assert result['final_sheet']['cells']['contrast_variance']['value'] == 0
    result['final_sheet']['cells']['contrast_variance']['value'] = False
    with pytest.raises(ExperimentalContractError, match='controlled_v3_population_schema_invalid'):
        population.validate_controlled_response_v3_population(extraction, result)
