"""Native arithmetic and withdrawal of categorical drafts; no models or jobs."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.evidence_axis_contracts import validate_evidence_axis_entry
from gene_annotation_episode.evidence_axis_scoring import score_axis, validate_evidence_unit
from test_evidence_axis_contracts import axis_entry, judgment


WITNESS = 'observation_' + 'a' * 24


def criterion(name, *, test=None):
    return {'criterion_id': name, 'question': f'Is {name} established?',
            'required_metric_ids': [], 'required_evidence': [f'{name}_evidence'],
            'outcomes': {'met': 'The declared condition is witnessed.',
                         'not_met': 'The declared condition is contradicted.',
                         'unknown': 'The declared inputs are missing.'},
            'deterministic_test': test}


def route(name, operation, metrics=(), *, eligible=(), bands=(), grade=None,
          grade_scores=None, unit='bits', polarity='supporting'):
    return {'route_id': name, 'operation': operation, 'metric_ids': list(metrics),
            'eligible_when': list(eligible), 'score_unit': unit, 'direction': 'higher',
            'polarity': polarity, 'interpretation': 'Explicit proposed engineering fixture.',
            'grade_criterion': grade, 'grade_scores': grade_scores or {}, 'bands': list(bands)}


def entry_with(*routes):
    entry = axis_entry()
    entry['scoring_rubric'] = {'version': 'evidence_axis_scoring_v1',
                             'status': 'proposed', 'routes': list(routes)}
    return entry


def fact(metric='bit_score', value=40, *, unit='bits', direction='higher', **atom):
    return {'metric_id': metric, 'observation': WITNESS, 'measurement_index': 0,
            'native_field': metric, 'native_value': {'type': 'number', 'value': value,
                'unit_ref': None, **atom}, 'declared_native_unit': unit,
            'direction': direction, 'source': 'source_' + 'b' * 24,
            'source_subjects': [], 'subjects': [], 'dependencies': [],
            'method': {'provider': 'synthetic_program', 'recorded_source_version': 'v1',
                       'request_record': None}}


def evidence(entry, *, values=(), outcomes=None, grades=None, experiment='original_experiment_1',
             representation='representation_1', origin='dataset'):
    judged = {'criteria': [], 'qualitative_grades': [],
              'evidence_chain': judgment(WITNESS)['evidence_chain']}
    for definition in entry['judgment_criteria']:
        name = definition['criterion_id']
        outcome = (outcomes or {}).get(name, 'met')
        judged['criteria'].append({'criterion_id': name, 'outcome': outcome,
            'witnesses': [] if outcome == 'unknown' else [WITNESS],
            'missing_inputs': [definition['required_evidence'][0]] if outcome == 'unknown' else []})
    for definition in entry['qualitative_grading']:
        name = definition['criterion_id']
        grade = (grades or {}).get(name, 'unknown')
        judged['qualitative_grades'].append({'criterion_id': name, 'grade': grade,
            'witnesses': [] if grade == 'unknown' else [WITNESS]})
    return {'experiment_id': experiment, 'representation_id': representation, 'origin': origin,
            'measurements': [{'measurement_id': f'measurement_{index}', 'fact': row}
                             for index, row in enumerate(values)],
            'judgment': judged, 'witnesses': [WITNESS]}


def scored(entry, unit):
    return score_axis(entry, [unit])['experiments'][0]['routes']


def test_actual_native_values_and_log_censoring_are_numeric_not_fabricated_confidence():
    entry = entry_with(route('native_bits', 'identity', ['bit_score']),
                       route('log_metric', 'neg_log10', ['bit_score'], unit='negative_log10_native'))
    result = scored(entry, evidence(entry, values=[fact(value=1e-20)]))
    assert result[0]['score'] == 1e-20
    assert result[1]['score'] == pytest.approx(20)
    bounded = scored(entry, evidence(entry, values=[fact(value=1e-20, bound='less_than')]))[1]
    assert bounded['status'] == 'bounded' and bounded['score'] is None
    assert bounded['score_bounds'] == {'lower': 20, 'upper': None,
        'lower_inclusive': False, 'upper_inclusive': False}
    zero = scored(entry, evidence(entry, values=[fact(value=0)]))[1]
    assert zero['status'] == 'unavailable' and zero['score'] is None
    assert zero['reason'] == 'zero_without_positive_reported_threshold'
    raw = fact(value=17.25, qualifier='approximate', uncertainty={
        'representation': 'plus_minus', 'magnitude': .2, 'statistic': 'unspecified'})
    assert scored(entry, evidence(entry, values=[raw]))[0]['measurements'][0]['fact'] == raw


def test_actual_count_ratio_and_missing_operands_are_distinct_from_zero():
    entry = entry_with(route('coverage', 'ratio', ['bit_score', 'structural_distance'], unit='fraction'))
    for metric in entry['native_measurements']:
        metric['units'] = ['count']
    numerator = fact(value=3, unit='count')
    denominator = fact('structural_distance', 4, unit='count', direction='lower')
    assert scored(entry, evidence(entry, values=[numerator, denominator]))[0]['score'] == .75
    missing = scored(entry, evidence(entry, values=[numerator]))[0]
    assert missing['status'] == 'unavailable' and missing['score'] is None
    denominator['native_value']['value'] = 0
    result = scored(entry, evidence(entry, values=[numerator, denominator]))[0]
    assert result['score'] is None and result['reason'].startswith('ratio_requires_')
    denominator['native_value']['value'] = 2
    result = scored(entry, evidence(entry, values=[numerator, denominator]))[0]
    assert result['score'] is None and result['reason'] == 'ratio_numerator_exceeds_denominator'


def test_declared_metric_domains_distinguish_probabilities_from_e_values():
    entry = entry_with(route('e_log', 'neg_log10', ['bit_score']))
    entry['native_measurements'][0]['valid_range'] = {'minimum': 0, 'maximum': None}
    assert scored(entry, evidence(entry, values=[fact(value=10)]))[0]['score'] == -1
    entry['native_measurements'][0]['valid_range']['maximum'] = 1
    invalid_p = scored(entry, evidence(entry, values=[fact(value=1.2)]))[0]
    assert invalid_p['status'] == 'unavailable'
    assert invalid_p['reason'] == 'native_value_outside_declared_range'
    # P < 2 supplies no tighter threshold than its declared [0,1] domain.
    weak_bound = scored(entry, evidence(entry, values=[fact(value=2, bound='less_than')]))[0]
    assert weak_bound['score'] is None
    assert weak_bound['score_bounds'] == {'lower': 0, 'upper': None,
        'lower_inclusive': True, 'upper_inclusive': False}


def test_same_method_requires_real_comparison_and_parameter_context():
    entry = entry_with(route('native', 'identity', ['bit_score'], eligible=['actual_subject']))
    entry['judgment_criteria'][0]['deterministic_test'] = {
        'operation': 'same_method', 'metric_ids': ['bit_score']}
    raw = fact(value=10)
    result = scored(entry, evidence(entry, values=[raw], outcomes={'actual_subject': 'unknown'}))[0]
    assert result['reason'] == 'eligibility_unknown'
    raw['comparison_context'] = {'method': 'real_program', 'version': 'v2',
        'parameters': 'actual_parameter_record', 'reference_set': 'reference_release_1',
        'comparison': 'same_query_against_same_reference'}
    assert scored(entry, evidence(entry, values=[raw], outcomes={'actual_subject': 'unknown'}))[0]['score'] == 10


@pytest.mark.parametrize('outcome', ['met', 'not_met', 'unknown'])
def test_ordinal_assurance_is_withdrawn_regardless_of_reported_conditions(outcome):
    bands = [{'score': 0, 'requires': []},
             {'score': .25, 'requires': ['assay']},
             {'score': .5, 'requires': ['assay', 'controls']},
             {'score': 1, 'requires': ['assay', 'controls', 'alternative_excluded']}]
    entry = entry_with(route('controlled_experiment', 'ordinal', bands=bands,
                             unit='ordinal_evidence_level'))
    entry['judgment_criteria'] = [criterion(name) for name in
                                 ('assay', 'controls', 'alternative_excluded')]
    result = scored(entry, evidence(entry, values=[fact(value=100000)],
        outcomes={name: outcome for name in ('assay', 'controls', 'alternative_excluded')}))[0]
    assert result['status'] == 'unavailable'
    assert result['reason'] == 'categorical_scoring_route_withdrawn'
    assert result['score'] is None and result['score_bounds'] is None
    assert score_axis(entry, [])['withdrawn_routes'] == [{
        'route_id': 'controlled_experiment', 'reason': 'categorical_scoring_route_withdrawn'}]


@pytest.mark.parametrize('kind', ['organism_function_plausibility',
                                 'experimental_interpretation_without_numeric_measure'])
def test_explicit_overall_plausibility_grade_is_withdrawn_including_zero_grade(kind):
    entry = entry_with(route('plausibility', 'grade', grade='ecology',
                             grade_scores={'contradicted': 0, 'plausible': 1, 'corroborated': 2},
                             unit='ordinal_evidence_level', polarity='opposing'))
    entry['judgment_criteria'].append(criterion('ecology'))
    entry['qualitative_grading'] = [{'criterion_id': 'ecology',
        'kind': kind,
        'reason_no_native_metric': 'The fixture uses explicit categorical environmental interpretation.',
        'ordered_levels': [{'code': name, 'meaning': f'Concrete fixture condition: {name}.'}
                           for name in ('contradicted', 'plausible', 'corroborated')]}]
    for grade in ('contradicted', 'plausible', 'corroborated', 'unknown'):
        output = scored(entry, evidence(entry, grades={'ecology': grade}))[0]
        assert output['status'] == 'unavailable' and output['polarity'] == 'opposing'
        assert output['reason'] == 'categorical_scoring_route_withdrawn'
        assert output['score'] is None and output['score_bounds'] is None
    assert score_axis(entry, [evidence(entry)])['annotation_aggregate'] is None


def test_same_experiment_in_literature_and_dataset_is_not_counted_twice_and_conflicts_survive():
    entry = entry_with(route('native_bits', 'identity', ['bit_score']))
    data = evidence(entry, values=[fact(value=32)])
    paper = deepcopy(data)
    paper.update(representation_id='paper_figure_2', origin='literature')
    paper['measurements'][0]['fact']['source'] = 'source_' + 'c'*24
    paper['measurements'][0]['fact']['observation'] = 'observation_' + 'd'*24
    result = score_axis(entry, [data, paper])
    assert result['experiment_count'] == 1 and result['representation_count'] == 2
    output = result['experiments'][0]['routes']
    assert len(output) == 1 and output[0]['score'] == 32
    assert len(output[0]['measurements'][0]['representations']) == 2
    paper['measurements'][0]['fact']['native_value']['value'] = 33
    conflict = score_axis(entry, [data, paper])['experiments'][0]['routes'][0]
    assert conflict['status'] == 'conflicted' and conflict['score'] is None
    # Two actually different experiments are retained separately, still not summed.
    paper['experiment_id'] = 'original_experiment_2'
    assert score_axis(entry, [data, paper])['experiment_count'] == 2


@pytest.mark.parametrize(('operation', 'atom', 'expected'), [
    ('all_zero', {'value': 0}, 'met'),
    ('all_zero', {'value': 1}, 'not_met'),
    ('all_zero', {'value': 0, 'bound': 'greater_or_equal'}, 'unknown'),
    ('all_nonpositive', {'value': 0, 'bound': 'less_or_equal'}, 'met'),
    ('all_nonpositive', {'value': 0, 'bound': 'greater_than'}, 'not_met'),
    ('all_nonpositive', {'value': 2, 'bound': 'less_than'}, 'unknown'),
    ('all_nonpositive', {'value': -2, 'qualifier': 'approximate'}, 'unknown'),
])
def test_numeric_tests_derive_from_actual_atoms_and_bounds(operation, atom, expected):
    entry = entry_with(route('native', 'identity', ['bit_score'], eligible=['actual_subject']))
    entry['judgment_criteria'][0]['deterministic_test'] = {
        'operation': operation, 'metric_ids': ['bit_score']}
    value = atom.pop('value')
    unit = evidence(entry, values=[fact(value=value, **atom)], outcomes={'actual_subject': 'unknown'})
    assert score_axis(entry, [unit])['experiments'][0]['criterion_outcomes']['actual_subject'] == expected


def test_native_arithmetic_cannot_be_overruled_by_model_claim_and_good_other_route_survives():
    entry = entry_with(route('requires_zero', 'identity', ['bit_score'], eligible=['actual_subject']),
                       route('raw_value', 'identity', ['bit_score'], polarity='non_discriminating'))
    entry['judgment_criteria'][0]['deterministic_test'] = {
        'operation': 'all_zero', 'metric_ids': ['bit_score']}
    result = score_axis(entry, [evidence(entry, values=[fact(value=4)])])['experiments'][0]
    assert result['criterion_conflicts'] == ['actual_subject']
    assert result['routes'][0]['status'] == 'conflicted'
    assert result['routes'][1]['score'] == 4


def test_missing_and_witness_contracts_and_new_rubric_link_validation():
    entry = entry_with(route('native', 'identity', ['bit_score']))
    unit = evidence(entry, values=[fact()])
    with pytest.raises(ValueError, match='witness_unavailable'):
        score_axis(entry, [unit], resolve_witness=lambda _: False)
    with pytest.raises(ValueError, match='representation_duplicate'):
        score_axis(entry, [unit, unit])
    unit['measurements'][0]['fact']['native_value']['value'] = float('inf')
    with pytest.raises(ValueError, match='nonfinite'):
        validate_evidence_unit(entry, unit)
    entry['scoring_rubric']['routes'][0]['metric_ids'] = ['invented_metric']
    with pytest.raises(ValueError, match='scoring_metrics_invalid'):
        validate_evidence_axis_entry(entry)


def test_historical_axis_descriptors_remain_readable_without_reinstating_recipes():
    entries = Path('research/slotted_process_library/publications/2026-10-23-002/entries')
    current = [json.loads(path.read_text()) for path in sorted(entries.glob('A*.json'))]
    assert current
    for entry in current:
        checked = validate_evidence_axis_entry(entry)
        assert checked['scoring_rubric']['routes'], entry['id']
        output = score_axis(entry, [])
        assert output['status'] == 'proposed' and output['annotation_aggregate'] is None
        expected = {row['route_id'] for row in checked['scoring_rubric']['routes']
                    if row['operation'] == 'ordinal'}
        assert {row['route_id'] for row in output['withdrawn_routes']} == expected


@pytest.mark.parametrize('axis_id', ['A108', 'A110'])
def test_organism_and_chemical_category_grades_cannot_be_recreated_from_conditions(axis_id):
    path = Path('research/slotted_process_library/publications/2026-10-23-002/entries') / (axis_id + '.json')
    entry = json.loads(path.read_text())
    native_metric = next(row for row in entry['native_measurements']
                         if row['binding']['kind'] == 'recorded_measurement') if axis_id == 'A108' else next(
                         row for row in entry['native_measurements'] if row['metric_id'] == 'atom_balance_residual')
    measured = fact(native_metric['metric_id'], 0, unit=native_metric['units'][0],
                    direction=native_metric['direction'])
    for outcome in ('met', 'not_met', 'unknown'):
        output = score_axis(entry, [evidence(entry, values=[measured], outcomes={
            row['criterion_id']: outcome for row in entry['judgment_criteria']})])
        for result in output['experiments'][0]['routes']:
            if result['operation'] == 'ordinal':
                assert result['reason'] == 'categorical_scoring_route_withdrawn'
                assert result['score'] is None and result['score_bounds'] is None
        native = next(row for row in output['experiments'][0]['routes']
                      if row['measurements'] and row['operation'] == 'identity')
        assert native['score'] == 0
        assert native['measurements'][0]['fact'] == measured
