"""PLA converter: the researched values kept as EXPERT_REVIEW constants and made gradual around them (owner rule, step 3 of A105_EXPERIMENT_SOP.md), the qualitative effect and the criteria mapping."""
import ast
import inspect
from math import log, sqrt

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_pla_record import FACTS, PREPARATION_KEYS, QUANTITIES, UNITS, fact, point, unavailable
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_pla_converter
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pla_converter import CRITERIA_MAP, _criterion, convert_pla
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pla_grader import CRITERIA, grade_pla

STATED = {'puncta_per_cell_target': 12.0, 'puncta_per_cell_control': 3.0, 'puncta_per_cell_knockdown': 4.0, 'puncta_spread_target': None, 'puncta_spread_control': None, 'protein_depletion_percent': None,
          'cells_counted': 60.0, 'amplification_time': 100.0, 'replicate_count': 3.0}      # the spreads and the depletion are unstated unless a test states them


def record(spread_kind=None, **values):
    """A PLA record stating every fact as yes and every quantity of STATED (overridden by ``values``; None makes it unavailable); ``spread_kind`` is the choice that names the spread."""
    stated = {**STATED, **values}
    quantities = {name: unavailable(UNITS[name][0], name, 'not_stated_in_passage') if stated[name] is None else point(stated[name], UNITS[name][0], name, ['span_' + name]) for name in QUANTITIES}
    return {'version': 'a105_pla_record_v1', 'experiment_type': 'pla', 'experiment_ref': 'exp_pla_1', 'source_ref': 'src_pla_1', 'assertion_ref': 'assert_pla_1',
            'preparations': {'component_a_preparation_ref': 'prep_a', 'component_b_preparation_ref': 'prep_b', 'dataset_ref': 'dataset_pla_1'}, 'quantities': quantities,
            'cell_system': 'cultured_cells', 'fixation': 'paraformaldehyde', 'quantification_software': 'imagej', 'puncta_spread_kind': spread_kind, 'facts': {name: fact('yes', ['span_' + name]) for name in FACTS},
            'choice_support': {'cell_system': 'direct', 'fixation': 'direct', 'quantification_software': 'direct', 'puncta_spread_kind': None if spread_kind is None else 'direct'}, 'spans': {}}


def judged(name, spread_kind=None, **values):
    return _criterion(grade_pla(record(spread_kind, **values)), name)


def test_the_fold_is_also_read_in_standard_errors_of_the_difference_when_the_spreads_are_stated():
    # test 12, control 3: fold 4 (full on the fold); SE of the difference sqrt(se_t^2 + se_c^2) with the SE as stated
    tight = judged('puncta_enrichment', 'standard_error', puncta_spread_target=1.0, puncta_spread_control=0.5)
    assert tight['degree'] == 1.0 and 'span_puncta_spread_target' in tight['support_refs'] and 'span_puncta_spread_control' in tight['support_refs']
    error = sqrt(4.5 ** 2 + 4.5 ** 2)                                                      # difference 9 over 6.4 standard errors: z 1.41, 0.71 of the 2 needed
    wide = judged('puncta_enrichment', 'standard_error', puncta_spread_target=4.5, puncta_spread_control=4.5)
    assert wide['status'] == 'supported' and wide['degree'] == pytest.approx(9.0 / error / 2.0)
    # a standard deviation is divided by sqrt(replicates) (3); the SD as it is when the count is not stated (the conservative reading)
    assert judged('puncta_enrichment', 'standard_deviation', puncta_spread_target=4.5 * sqrt(3), puncta_spread_control=4.5 * sqrt(3))['degree'] == pytest.approx(wide['degree'])
    assert judged('puncta_enrichment', 'standard_deviation', replicate_count=None, puncta_spread_target=4.5, puncta_spread_control=4.5)['degree'] == pytest.approx(wide['degree'])
    spreads = (0.1, 1.0, 3.0, 6.0, 12.0)                                                   # a wider spread never raises the degree; never conflicting for a fold above 1
    degrees = [judged('puncta_enrichment', 'standard_error', puncta_spread_target=s, puncta_spread_control=s)['degree'] for s in spreads]
    assert degrees == sorted(degrees, reverse=True) and degrees[0] > degrees[-1] > 0
    # no kind, or one spread only: no spread judgement, the fold decides as before
    assert judged('puncta_enrichment', None, puncta_spread_target=4.5, puncta_spread_control=4.5)['degree'] == 1.0
    assert judged('puncta_enrichment', 'standard_error', puncta_spread_target=4.5)['degree'] == 1.0
    assert judged('puncta_enrichment', 'standard_error', puncta_per_cell_target=3.0, puncta_spread_target=0.1, puncta_spread_control=0.1)['status'] == 'conflicting'   # fold 1: still against


def test_the_fall_of_the_specific_puncta_is_read_against_the_measured_depletion():
    # test 12, control 3, knockdown 7: a 56 % fall of the specific puncta. Unstated depletion: the researched ends 70 / 20 (degree 0.72)
    assert judged('specificity_control', puncta_per_cell_knockdown=7.0)['degree'] == pytest.approx((5 / 9 * 100 - 20) / 50)
    shallow = judged('specificity_control', puncta_per_cell_knockdown=7.0, protein_depletion_percent=60.0)       # ends 42 / 12: 56 % is more than enough
    assert shallow['degree'] == 1.0 and 'span_protein_depletion_percent' in shallow['support_refs']
    assert judged('specificity_control', puncta_per_cell_knockdown=7.0, protein_depletion_percent=100.0)['degree'] == pytest.approx((5 / 9 * 100 - 20) / 50)
    assert judged('specificity_control', puncta_per_cell_knockdown=7.0, protein_depletion_percent=250.0)['degree'] == pytest.approx((5 / 9 * 100 - 20) / 50)   # capped at the full depletion
    degrees = [judged('specificity_control', puncta_per_cell_knockdown=7.0, protein_depletion_percent=d)['degree'] for d in (40.0, 60.0, 80.0, 100.0)]
    assert degrees == sorted(degrees, reverse=True) and 0 < degrees[-1] < 1                # the same fall is weaker evidence after a deeper depletion
    # a fall within the depletion's own scaled noise end is conflicting (30 % depletion: ends 21 / 6; the fall 5 % is below 6)
    assert judged('specificity_control', puncta_per_cell_knockdown=12.0 - 0.05 * 9.0, protein_depletion_percent=30.0)['status'] == 'conflicting'


def test_every_criterion_is_mapped_to_exactly_one_sheet_criterion():
    assert set(PREPARATION_KEYS) == set(record()['preparations'])
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(CRITERIA) and len(mapped) == len(set(mapped))


def test_the_researched_values_are_kept():
    c = literature_pla_converter
    assert (c.FOLD_FULL_AGREEMENT, c.FOLD_ZERO_AGREEMENT) == (3.0, 1.0)
    assert (c.REDUCTION_FULL_AGREEMENT_PERCENT, c.REDUCTION_ZERO_AGREEMENT_PERCENT) == (70.0, 20.0)
    assert (c.CELLS_COUNTED_FULL_CREDIT, c.REPLICATES_FULL_CREDIT) == (50, 3)


def test_a_full_record_is_supported_with_the_degrees_of_the_curves():
    interpretations = convert_pla(grade_pla(record()))['extraction']['interpretations']
    assert {name: item['status'] for name, item in interpretations.items()} == dict.fromkeys(CRITERIA_MAP, 'supported')
    assert judged('puncta_enrichment')['degree'] == 1.0                                  # fold 4 >= 3
    assert judged('specificity_control')['degree'] == 1.0                                # specific fall (12 - 4) / (12 - 3) = 89 % >= 70 %
    assert judged('cells_counted')['degree'] == 1.0 and judged('replicates')['degree'] == 1.0
    assert interpretations['binding_controls']['degree'] == 1.0 and interpretations['sampling_basis']['degree'] == 1.0
    specific = (12 - 7) / (12 - 3) * 100                                                  # a partial knockdown: 56 % of the specific puncta
    partial = convert_pla(grade_pla(record(puncta_per_cell_knockdown=7.0)))['extraction']['interpretations']
    assert partial['binding_controls']['degree'] == pytest.approx((specific - 20) / (70 - 20))


@pytest.mark.parametrize('name, field, better', [
    ('puncta_enrichment', 'puncta_per_cell_target', (3.5, 4.0, 6.0, 9.0, 12.0, 300.0)),       # more test puncta over the same control
    ('puncta_enrichment', 'puncta_per_cell_control', (11.0, 9.0, 6.0, 4.0, 1.0, 0.0)),        # a lower control under the same test
    ('specificity_control', 'puncta_per_cell_knockdown', (9.5, 8.0, 6.0, 4.0, 2.0, 0.0)),     # a deeper fall after the depletion
    ('cells_counted', 'cells_counted', (1.0, 5.0, 10.0, 25.0, 49.0, 50.0, 500.0)),
    ('replicates', 'replicate_count', (1.0, 2.0, 3.0, 5.0)),
])
def test_a_better_value_never_lowers_the_degree_and_the_degree_is_bounded(name, field, better):
    verdicts = [judged(name, **{field: value}) for value in better]
    assert all(v['status'] == 'supported' and v['support_refs'] for v in verdicts)
    degrees = [v['degree'] for v in verdicts]
    assert all(0 <= d <= 1 for d in degrees) and degrees == sorted(degrees) and degrees[0] < degrees[-1]


def test_a_count_below_its_researched_value_gets_partial_credit_not_a_step():
    assert judged('cells_counted', cells_counted=50.0)['degree'] == 1.0
    assert judged('cells_counted', cells_counted=49.0) == {'status': 'supported', 'support_refs': ['span_cells_counted'], 'degree': pytest.approx(sqrt(49 / 50))}
    assert judged('cells_counted', cells_counted=25.0)['degree'] == pytest.approx(sqrt(0.5))
    assert 0 < judged('cells_counted', cells_counted=1.0)['degree'] < judged('cells_counted', cells_counted=10.0)['degree'] < 1
    cells = [judged('cells_counted', cells_counted=float(n))['degree'] for n in range(1, 61)]
    assert max(b - a for a, b in zip(cells, cells[1:])) < 0.1                               # smooth: no jump between neighbouring counts
    assert [judged('replicates', replicate_count=n)['degree'] for n in (1.0, 2.0, 3.0, 4.0)] == [pytest.approx((1 / 3) ** 0.5), pytest.approx((2 / 3) ** 0.5), 1.0, 1.0]      # sqrt(n / 3), the precision of the mean
    assert judged('replicates', replicate_count=2.0)['status'] == 'supported'               # fewer than three independent experiments is weaker, not against


def test_the_ramps_are_gradual_between_their_researched_ends():
    assert judged('puncta_enrichment', puncta_per_cell_target=sqrt(3.0) * 3.0)['degree'] == pytest.approx(0.5)  # fold sqrt(3), halfway between 1 and 3 on the log scale
    assert judged('puncta_enrichment', puncta_per_cell_target=8.9)['degree'] == pytest.approx(log(8.9 / 3) / log(3))
    assert judged('puncta_enrichment', puncta_per_cell_target=1.01 * 3.0)['degree'] < 0.02                       # just above the control: almost nothing, no step
    assert judged('specificity_control', puncta_per_cell_knockdown=12.0 - 0.45 * 9.0)['degree'] == pytest.approx(0.5)  # a 45 % fall of the specific puncta, halfway between 20 % and 70 %


def test_the_fold_is_judged_on_the_log_scale():
    # equal ratio steps count equally: 1 -> sqrt(3) and sqrt(3) -> 3 give the same credit; fold 2 gets log 2 / log 3, more than the old linear 0.5
    assert judged('puncta_enrichment', puncta_per_cell_target=6.0)['degree'] == pytest.approx(log(2) / log(3)) and judged('puncta_enrichment', puncta_per_cell_target=6.0)['degree'] > 0.5
    folds = [1.05, 1.2, 1.5, 2.0, 2.5, 2.99]
    degrees = [judged('puncta_enrichment', puncta_per_cell_target=f * 3.0)['degree'] for f in folds]
    assert degrees == sorted(degrees) and all(0 < d < 1 for d in degrees)


def test_the_knockdown_is_judged_by_the_fall_of_the_specific_puncta():
    # test 6, control 3, knockdown 3: every specific punctum is gone (100 %), though only half the total puncta fell; the old total-puncta reading gave 0.6
    verdict = judged('specificity_control', puncta_per_cell_target=6.0, puncta_per_cell_knockdown=3.0)
    assert verdict == {'status': 'supported', 'support_refs': ['span_puncta_per_cell_target', 'span_puncta_per_cell_knockdown', 'span_puncta_per_cell_control'], 'degree': 1.0}
    assert judged('specificity_control', puncta_per_cell_target=6.0, puncta_per_cell_knockdown=1.0)['degree'] == 1.0     # below the control: capped
    # no control stated: the fall of the total puncta, as before (never larger than the specific fall: the conservative reading)
    total = judged('specificity_control', puncta_per_cell_control=None, puncta_per_cell_knockdown=12.0 * (1 - 0.45))
    assert total == {'status': 'supported', 'support_refs': ['span_puncta_per_cell_target', 'span_puncta_per_cell_knockdown'], 'degree': pytest.approx(0.5)}
    assert judged('specificity_control', puncta_per_cell_knockdown=12.0 * (1 - 0.45))['degree'] > total['degree']
    # a test not above its control: the specific puncta are not defined, the total fall decides
    assert judged('specificity_control', puncta_per_cell_control=12.0, puncta_per_cell_knockdown=12.0 * (1 - 0.45))['degree'] == pytest.approx(0.5)
    # the specific fall never lowers the degree below the total-fall reading (monotone in the control)
    controls = (None, 0.0, 1.0, 3.0, 6.0, 9.0)
    degrees = [judged('specificity_control', puncta_per_cell_control=c, puncta_per_cell_knockdown=8.0)['degree'] for c in controls]
    assert degrees == sorted(degrees) and degrees[0] < degrees[-1]


def test_what_the_papers_own_numbers_show_against_the_standard_is_conflicting():
    for target, control in ((3.0, 3.0), (2.0, 3.0), (0.0, 0.0)):
        assert judged('puncta_enrichment', puncta_per_cell_target=target, puncta_per_cell_control=control)['status'] == 'conflicting'
    assert judged('puncta_enrichment', puncta_per_cell_target=1.0, puncta_per_cell_control=0.0) == {'status': 'supported', 'support_refs': ['span_puncta_per_cell_target', 'span_puncta_per_cell_control'], 'degree': 1.0}
    for knockdown in (10.5, 12.0, 15.0):                                                     # a fall within the count's own variation (17 % of the specific puncta), none, a rise
        assert judged('specificity_control', puncta_per_cell_knockdown=knockdown)['status'] == 'conflicting'


def test_with_nothing_of_the_record_to_compare_the_judgement_is_unknown_not_zero():
    assert judged('puncta_enrichment', puncta_per_cell_control=None) == {'status': 'unknown', 'support_refs': []}
    assert judged('cells_counted', cells_counted=None) == {'status': 'unknown', 'support_refs': []}
    graded = record(replicate_count=1.0)
    graded['facts']['independent_experiments'] = fact('unknown')
    assert _criterion(grade_pla(graded), 'replicates') == {'status': 'unknown', 'support_refs': []}
    graded['facts']['independent_experiments'] = fact('no', ['s'])
    assert _criterion(grade_pla(graded), 'replicates')['status'] == 'conflicting'           # a stated no is a fact of the record


def test_support_lowers_the_degree_and_never_changes_a_status():
    weak = record()
    weak['quantities']['cells_counted'] = point(60.0, 'count', 'cells_counted', ['s'], support='implied')
    weak['quantities']['puncta_per_cell_control'] = point(12.0, 'puncta_per_cell', 'c', ['s'], support='implied')
    direct = record(puncta_per_cell_control=12.0)
    weak_i, direct_i = (convert_pla(grade_pla(r))['extraction']['interpretations'] for r in (weak, direct))
    assert weak_i['sampling_basis']['degree'] == pytest.approx(0.7) and direct_i['sampling_basis']['degree'] == 1.0
    assert {k: v['status'] for k, v in weak_i.items()} == {k: v['status'] for k, v in direct_i.items()}
    assert weak_i['binding_parameter_definition']['status'] == 'conflicting'


def test_the_statement_is_detected_not_detected_or_not_stated():
    graded = record()
    assert convert_pla(grade_pla(graded))['qualitative_effect'] == {'statement': 'interaction_detected', 'support_refs': ['span_proximity_signal_detected'], 'puncta_fold_over_control': 4.0}
    graded['facts']['proximity_signal_detected'] = fact('no', ['s'])
    assert convert_pla(grade_pla(graded))['qualitative_effect']['statement'] == 'interaction_not_detected'
    graded['facts']['proximity_signal_detected'] = fact('unknown')
    converted = convert_pla(grade_pla(graded))
    assert converted['qualitative_effect']['statement'] == 'interaction_not_stated' and converted['direction_field_support'] is None
    assert converted['extraction']['quantities']['effect'] is None and converted['null_components']['effect'] == 'qualitative_assay_reports_no_binding_constant'


def test_every_number_a_judge_uses_is_a_named_expert_review_constant():
    source = inspect.getsource(literature_pla_converter)
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
    inline = {n.value for f in functions for n in ast.walk(f) if isinstance(n, ast.Constant) and type(n.value) in (int, float)}
    assert inline <= {0, 1}
    for name in ('FOLD_FULL_AGREEMENT', 'FOLD_ZERO_AGREEMENT', 'REDUCTION_FULL_AGREEMENT_PERCENT', 'REDUCTION_ZERO_AGREEMENT_PERCENT', 'CELLS_COUNTED_FULL_CREDIT', 'REPLICATES_FULL_CREDIT', 'SPREAD_Z_FULL'):
        assert name in source
    assert source.count('EXPERT_REVIEW:') >= 7
    assert not [name for name in vars(literature_pla_converter) if name.startswith('MIN_')]   # no lone minimum is a pass/fail cut any more
