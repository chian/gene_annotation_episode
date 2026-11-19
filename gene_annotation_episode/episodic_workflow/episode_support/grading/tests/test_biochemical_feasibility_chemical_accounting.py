"""The restored A110 chemical accounting (R11 to R13) and the A110 scoring index (R16), run on real declared panels.

R11: exact atom and charge residuals, explicit electron terms only, unknown inputs stay unknown, nothing is balanced
automatically and there is no combined score. R12: the conditional Gibbs cell is qualified only when every
applicability prerequisite holds; the pathway energy sum and the carrier-pool restoration are separate cells. R13:
the input panel declares species, reactions, pathway and carrier pools with source locators and an explicit energy
convention. R16: the index is the minimum over the necessary qualified tests; an unknown test leaves it unknown, a
negative test can oppose, an unresolved application neither supports nor refutes."""
import pytest

from gene_annotation_episode.episodic_workflow.episode_support.calculations.biochemical_feasibility_evidence.chemical_accounting import (
    calculate)
from gene_annotation_episode.episodic_workflow.episode_support.grading.biochemical_feasibility_evidence.contribution import (
    prerequisite_scalar, require_attribution)


def species(identifier, formula, charge, kind='chemical', compartment='cytosol'):
    return {'id': identifier, 'entity_id': 'CHEBI:' + identifier, 'compartment': compartment, 'kind': kind,
            'formula': formula, 'charge': charge, 'source_locator': 'table 1 row ' + identifier}


def participant(name, coefficient):
    return {'species_id': name, 'coefficient': coefficient, 'source_locator': 'equation 1'}


def panel(product_formula='H2O'):
    conditions = {'key': 'std', 'temperature_kelvin': 298.15, 'description': 'standard', 'source_locator': 'methods'}
    reaction = {'id': 'r1', 'entity_id': 'RHEA:1', 'source_locator': 'equation 1', 'conditions': conditions,
                'participants': [participant('H2', '-2'), participant('O2', '-1'), participant('H2O', '2')],
                'standard_gibbs': {'value_kj_per_mol': -474.2, 'convention': 'chemical', 'conditions': conditions,
                                   'source_locator': 'table 2'},
                'activities': [{'species_id': name, 'value': 1, 'unit': 'dimensionless_activity',
                                'source_locator': 'methods'} for name in ('H2', 'O2', 'H2O')]}
    return {'version': 'a110_chemical_panel_v1', 'dataset_id': 'fixture', 'origin': 'synthetic',
            'species': [species('H2', 'H2', 0), species('O2', 'O2', 0), species('H2O', product_formula, 0)],
            'reactions': [reaction], 'pathway': [{'reaction_id': 'r1', 'multiplier': '1', 'source_locator': 'scheme'}],
            'carrier_pools': [], 'reported_constraints': None}


SELECTION = {'reaction_ids': ['r1'], 'include_declared_pathway': True, 'include_reported_constraints': True}


def test_a_balanced_declared_equation_is_accounted_exactly_and_never_scored():
    result = calculate(panel(), SELECTION)
    [reaction] = result['reactions']
    assert reaction['accounting']['atom_balance'] == 'balanced'
    assert reaction['accounting']['charge_balance'] == 'balanced'
    assert result['combined_scientific_score'] is None
    assert result['reported_constraints'] == {'status': 'unavailable', 'missing': ['reported_constraints_unreported']}
    assert result['pathway']['steps'] and result['pathway']['carrier_pools'] == []
    assert 'complete_balanced_chemical_equation_not_established' not in reaction['conditional_gibbs'][
        'applicability_missing']


def test_an_imbalanced_or_unknown_formula_is_not_balanced_automatically():
    imbalanced = calculate(panel('H2O2'), SELECTION)['reactions'][0]
    assert imbalanced['accounting']['atom_balance'] == 'imbalanced'
    assert 'complete_balanced_chemical_equation_not_established' in imbalanced['conditional_gibbs'][
        'applicability_missing']
    assert imbalanced['conditional_gibbs']['qualified_for_declared_chemical_conditions'] is False
    unknown = calculate(panel(None), SELECTION)['reactions'][0]
    assert unknown['accounting']['atom_balance'] == 'unknown'


def test_the_index_is_the_minimum_of_the_necessary_tests_and_unknown_stays_unknown():
    both = prerequisite_scalar({'balance': .5, 'energy': .2}, required=('balance', 'energy'))
    assert both['value'] == pytest.approx(.2)
    assert both['interpretation'] == 'defined_root_index; not_a_function_probability'
    unknown = prerequisite_scalar({'balance': .5}, required=('balance', 'energy'))
    assert unknown['value'] is None and unknown['missing_inputs'] == ['energy']
    opposed = prerequisite_scalar({'balance': -.4}, required=('balance', 'energy'))
    assert opposed['value'] == pytest.approx(-.4) and opposed['status'] == 'partial'
    unresolved = require_attribution(both, missing=('target_application_unresolved',))
    assert unresolved['value'] is None and unresolved['direction'] == 'unknown'
