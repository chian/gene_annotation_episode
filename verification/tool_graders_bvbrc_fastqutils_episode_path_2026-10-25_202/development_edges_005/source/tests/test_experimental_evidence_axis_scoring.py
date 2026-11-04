"""Preserve native experimental quantities while withdrawing assurance ladders.

These synthetic checks establish native arithmetic and custody/identity behavior,
not biological experiments, completed scoring sheets or a live caller policy.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.evidence_axis_contracts import native_metric_facts, validate_evidence_axis_entry
from gene_annotation_episode.evidence_axis_scoring import score_axis
from gene_annotation_episode.state import Store


REPO = Path(__file__).resolve().parents[1]
PUBLICATION = REPO/'research/slotted_process_library/publications/2026-10-23-002'


def axis(axis_id):
    return validate_evidence_axis_entry(json.loads((PUBLICATION/'entries'/f'{axis_id}.json').read_text()))


def judgment(entry, met, *, unknown=(), witness='synthetic-experiment-witness'):
    met, unknown = set(met), set(unknown)
    return {'criteria': [
        {'criterion_id': row['criterion_id'],
         'outcome': 'met' if row['criterion_id'] in met else 'unknown' if row['criterion_id'] in unknown else 'not_met',
         'witnesses': [] if row['criterion_id'] in unknown else [witness],
         'missing_inputs': [row['required_evidence'][0]] if row['criterion_id'] in unknown else []}
        for row in entry['judgment_criteria']],
        'qualitative_grades': [],
        'evidence_chain': {name: [witness] for name in entry['transfer_chain']}}


def unit(entry, met, *, unknown=(), experiment='original-experiment-1', representation='paper-1',
         origin='literature', measurements=(), witness='synthetic-experiment-witness'):
    return {'experiment_id': experiment, 'representation_id': representation, 'origin': origin,
        'measurements': list(measurements), 'judgment': judgment(entry, met, unknown=unknown, witness=witness),
        'witnesses': [witness]}


def result_route(output, route_id):
    rows = [row for row in output['experiments'][0]['routes'] if row['route_id'] == route_id]
    assert len(rows) == 1
    return rows[0]


def assert_withdrawn(row):
    assert row['status'] == 'unavailable'
    assert row['reason'] == 'categorical_scoring_route_withdrawn'
    assert row['score'] is None and row['score_bounds'] is None


POSITIVE_CASES = {
    'A105': ('molecular_activity_assurance', [
        'source_effect_connected_to_target', 'preparation_dependent_signal',
        'assay_competence_and_attribution', 'molecular_endpoint_identified'],
        'molecular_specificity_bounded', 'orthogonal_endpoint_test'),
    'A106': ('component_contribution_assurance', [
        'contribution_connected_to_target', 'perturbation_identified',
        'controlled_contribution_effect', 'restoration_or_independent_perturbation'],
        'causal_role_discriminated', 'orthogonal_contribution_test'),
    'A111': ('homolog_structural_state_assurance', [
        'structural_fact_mapped_to_target', 'experimental_structural_origin',
        'structural_feature_observed', 'structural_state_identified', 'structural_claim_bounded'],
        'structural_alternative_discriminated', 'orthogonal_structural_interpretation_test'),
}


@pytest.mark.parametrize('axis_id', POSITIVE_CASES)
def test_assurance_levels_are_withdrawn_for_partial_and_complete_conditions(axis_id):
    entry = axis(axis_id)
    route_id, base, discriminator, orthogonal = POSITIVE_CASES[axis_id]
    for met in ([], base, [*base, discriminator], [*base, discriminator, orthogonal]):
        output = score_axis(entry, [unit(entry, met)])
        row = result_route(output, route_id)
        assert_withdrawn(row)
        for result in output['experiments'][0]['routes']:
            if result['operation'] == 'ordinal':
                assert_withdrawn(result)
        assert row['polarity'] == 'supporting'
        assert row['score_unit'] == 'ordinal_evidence_level'
        assert output['annotation_aggregate'] is None


@pytest.fixture
def native_assays(tmp_path):
    with Store(tmp_path/'workspace') as store:
        target = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs'][0]

        def record(activity, kd, *, bounded=False):
            artifact = store.artifact(json.dumps({'scope': 'Synthetic engineering assay only',
                'activity': activity, 'dissociation_constant': kd}), 'application/json')
            source = store.put('source', {'provider': 'synthetic.experimental_scoring_fixture',
                'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact,
                'request_ref': None, 'version': 'fixture-1', 'retrieved_at': None}, origin='tool')
            rate_unit = store.put('term', {'namespace': 'fixture', 'accession': 'rate',
                'label': 'synthetic reported rate unit', 'term_type': 'unit',
                'source_ref': source['id'], 'anchor': None}, origin='tool')
            concentration_unit = store.put('term', {'namespace': 'fixture', 'accession': 'concentration',
                'label': 'synthetic reported concentration unit', 'term_type': 'unit',
                'source_ref': source['id'], 'anchor': None}, origin='tool')
            rate = {'type': 'number', 'value': activity, 'unit_ref': rate_unit['id']}
            if bounded:
                rate['bound'] = 'greater_than'
            obs = store.put('observation', {'subject_refs': [target], 'source_subject_refs': [target],
                'kind': 'biochemical_assay', 'source_ref': source['id'], 'measurements': [
                    {'name': 'activity', 'value': rate},
                    {'name': 'dissociation_constant', 'value': {'type': 'number', 'value': kd,
                                                              'unit_ref': concentration_unit['id']}}],
                'dependencies': [], 'anchor': None}, origin='tool')
            facts = native_metric_facts(axis('A105'), store, observation_refs=[obs['id']],
                received_record_refs=[obs['id'], source['id']])['native_facts']
            return obs, [{'measurement_id': fact['metric_id'], 'fact': fact} for fact in facts]

        yield store, record


def test_native_activity_survives_while_categorical_assurance_stays_unavailable(native_assays):
    _, record = native_assays
    entry = axis('A105')
    route_id, base, specificity, _ = POSITIVE_CASES['A105']
    met = [*base, specificity]
    scores = []
    native_values = []
    for activity, kd in ((2.0, 50.0), (2000.0, .005)):
        observation, facts = record(activity, kd)
        output = score_axis(entry, [unit(entry, met, measurements=facts, witness=observation['id'])])
        scores.append(result_route(output, route_id)['score'])
        raw = result_route(output, 'native_molecular_activity')
        native_values.append(raw['score'])
        assert raw['polarity'] == 'non_discriminating'
    assert scores == [None, None]
    assert native_values == [2.0, 2000.0]


def test_a_source_bound_and_native_unit_survive_scoring_without_becoming_zero_or_an_exact_point(native_assays):
    _, record = native_assays
    entry = axis('A105')
    observation, facts = record(2.0, 10.0, bounded=True)
    output = score_axis(entry, [unit(entry, POSITIVE_CASES['A105'][1], measurements=facts,
                                    witness=observation['id'])])
    raw = result_route(output, 'native_molecular_activity')
    assert raw['status'] == 'bounded' and raw['score'] is None
    assert raw['score_bounds'] == {'lower': 2.0, 'upper': None,
        'lower_inclusive': False, 'upper_inclusive': False}
    retained = raw['measurements'][0]['fact']['native_value']
    assert retained == observation['measurements'][0]['value']
    assert retained['unit_ref'] is not None


def test_a_paper_and_its_underlying_dataset_are_one_experiment_with_no_origin_bonus(native_assays):
    _, record = native_assays
    entry = axis('A105')
    observation, facts = record(2.0, 10.0)
    met = [*POSITIVE_CASES['A105'][1], 'molecular_specificity_bounded']
    paper = unit(entry, met, measurements=facts, witness=observation['id'])
    data = deepcopy(paper)
    data.update(representation_id='deposited-dataset-1', origin='dataset')
    one = score_axis(entry, [paper])
    both = score_axis(entry, [paper, data])
    assert both['experiment_count'] == 1 and both['representation_count'] == 2
    assert_withdrawn(result_route(one, 'molecular_activity_assurance'))
    assert_withdrawn(result_route(both, 'molecular_activity_assurance'))
    raw = result_route(both, 'native_molecular_activity')
    assert len(raw['measurements']) == 1
    assert len(raw['measurements'][0]['representations']) == 2


@pytest.mark.parametrize('axis_id', POSITIVE_CASES)
def test_withdrawal_applies_to_literature_and_dataset_representations_identically(axis_id):
    entry = axis(axis_id)
    route_id, base, discriminator, orthogonal = POSITIVE_CASES[axis_id]
    met = [*base, discriminator, orthogonal]
    paper = unit(entry, met, origin='literature', representation='paper-representation')
    dataset = unit(entry, met, origin='dataset', representation='dataset-representation')
    literature_result = score_axis(entry, [paper])
    dataset_result = score_axis(entry, [dataset])
    assert result_route(literature_result, route_id) == result_route(dataset_result, route_id)
    together = score_axis(entry, [paper, dataset])
    assert together['experiment_count'] == 1
    assert_withdrawn(result_route(together, route_id))


def test_contradictory_representations_are_reported_instead_of_selecting_the_larger_activity(native_assays):
    _, record = native_assays
    entry = axis('A105')
    observation, facts = record(2.0, 10.0)
    paper = unit(entry, POSITIVE_CASES['A105'][1], measurements=facts, witness=observation['id'])
    data = deepcopy(paper)
    data.update(representation_id='dataset-with-conflict', origin='dataset')
    data['measurements'][0]['fact']['native_value']['value'] = 200.0
    output = score_axis(entry, [paper, data])
    raw = result_route(output, 'native_molecular_activity')
    assert raw['status'] == 'conflicted' and raw['score'] is None


@pytest.mark.parametrize('axis_id', POSITIVE_CASES)
def test_missing_homolog_correspondence_does_not_silently_transfer_experimental_evidence(axis_id):
    entry = axis(axis_id)
    route_id, base, discriminator, orthogonal = POSITIVE_CASES[axis_id]
    transfer = {'A105': 'source_effect_connected_to_target', 'A106': 'contribution_connected_to_target',
                'A111': 'structural_fact_mapped_to_target'}[axis_id]
    met = set([*base, discriminator, orthogonal]) - {transfer}
    output = score_axis(entry, [unit(entry, met, unknown=[transfer])])
    row = result_route(output, route_id)
    assert_withdrawn(row)
    assert output['experiments'][0]['criterion_outcomes'][transfer] == 'unknown'


def test_withdrawn_negative_assurance_does_not_fabricate_bounds_from_nonsignificance():
    entry = axis('A105')
    met = ['source_effect_connected_to_target', 'assay_competence_and_attribution',
        'competent_molecular_exclusion', 'molecular_specificity_bounded']
    competent = result_route(score_axis(entry, [unit(entry, met)]), 'molecular_exclusion_assurance')
    assert competent['polarity'] == 'opposing'
    assert_withdrawn(competent)
    missing_limit = set(met) - {'competent_molecular_exclusion'}
    nonsignificant = result_route(score_axis(entry, [unit(entry, missing_limit,
        unknown=['competent_molecular_exclusion'])]), 'molecular_exclusion_assurance')
    assert_withdrawn(nonsignificant)


def test_structural_resolution_occupancy_and_distances_are_unknown_without_actual_native_measurements():
    entry = axis('A111')
    _, base, discriminator, _ = POSITIVE_CASES['A111']
    output = score_axis(entry, [unit(entry, [*base, discriminator])])
    for route_id in ('native_resolution', 'native_occupancy', 'native_contact_distance'):
        row = result_route(output, route_id)
        assert row['status'] == 'unavailable' and row['score'] is None
    assert_withdrawn(result_route(output, 'homolog_structural_state_assurance'))


def native_probability_unit(entry, probability, *, bound=None, matched=True):
    """Trusted-host formal fixture for a retained-native field, not a Store extractor.

    All identities explicitly label synthetic data. Production must obtain this
    fact from the actual retained test/contrast and its scoped witness path.
    """
    atom = {'type': 'number', 'value': probability, 'unit_ref': None}
    if bound is not None:
        atom['bound'] = bound
    fact = {'metric_id': 'claim_test_probability', 'observation': 'synthetic-native-test-observation',
        'measurement_index': 0, 'native_field': 'q_value', 'native_value': atom,
        'declared_native_unit': 'reported_q_value', 'direction': 'lower',
        'source': 'synthetic-retained-dataset', 'source_subjects': ['synthetic-tested-protein'],
        'subjects': ['synthetic-tested-protein'], 'dependencies': ['synthetic-matched-controls'],
        'method': {'provider': 'synthetic.formal_test_fixture',
                   'recorded_source_version': 'fixture-1', 'request_record': None}}
    met = [*POSITIVE_CASES['A105'][1], 'molecular_specificity_bounded']
    if matched:
        met.append('positive_test_targets_claim')
    return unit(entry, met, origin='dataset', representation='synthetic-native-dataset',
        measurements=[{'measurement_id': 'original-contrast-q', 'fact': fact}])


def test_matched_native_q_value_is_scored_by_its_declared_formula_not_by_retyping_a_confidence():
    entry = axis('A105')
    output = score_axis(entry, [native_probability_unit(entry, .0001)])
    native = result_route(output, 'positive_native_claim_test')
    assert native['status'] == 'scored' and native['score'] == 4.0
    assert native['score_unit'] == 'negative_log10_native_tail_probability'
    assert native['polarity'] == 'supporting'
    # A valid native transform does not reinstate the withdrawn assurance score.
    assert_withdrawn(result_route(output, 'molecular_activity_assurance'))
    assert output['annotation_aggregate'] is None


def test_censored_native_probability_gives_a_score_bound_and_zero_does_not_make_infinity():
    entry = axis('A105')
    bounded = result_route(score_axis(entry, [native_probability_unit(entry, .0001, bound='less_than')]),
                           'positive_native_claim_test')
    assert bounded['status'] == 'bounded' and bounded['score'] is None
    assert bounded['score_bounds'] == {'lower': 4.0, 'upper': None,
        'lower_inclusive': False, 'upper_inclusive': False}
    zero = result_route(score_axis(entry, [native_probability_unit(entry, 0.0)]),
                        'positive_native_claim_test')
    assert zero['status'] == 'unavailable' and zero['score'] is None
    assert zero['reason'] == 'zero_without_positive_reported_threshold'


def test_an_unrelated_small_q_value_and_invalid_probability_cannot_supply_claim_evidence():
    entry = axis('A105')
    unrelated = result_route(score_axis(entry, [native_probability_unit(entry, .0001, matched=False)]),
                             'positive_native_claim_test')
    assert unrelated['status'] == 'ineligible' and unrelated['score'] is None
    invalid = result_route(score_axis(entry, [native_probability_unit(entry, 1.1)]),
                           'positive_native_claim_test')
    assert invalid['status'] == 'unavailable' and invalid['score'] is None
    assert invalid['reason'] == 'native_value_outside_declared_range'


def test_experimental_axis_provenance_rows_are_exact_copies_of_the_preserved_sources():
    crosswalk = json.loads((PUBLICATION/'SOURCE_CROSSWALK_A105_A106_A111.json').read_text())
    for link in crosswalk['rows']:
        original_path = REPO/link['original_path']
        assert hashlib.sha256(original_path.read_bytes()).hexdigest() == link['original_file_sha256']
        index = int(link['original_pointer'].rsplit('/', 1)[1])
        original = json.loads(original_path.read_text())['evidence'][index]
        assert axis(link['axis_id'])['evidence'][link['evidence_index']] == original
