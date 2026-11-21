"""Pull-down / co-IP converter: the qualitative effect, the empty sheet cells, the criteria mapping and the null reasons."""
import ast
import inspect
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_pulldown_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_pulldown_converter as sheet
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_converter import CRITERIA_MAP, _criterion, convert_pulldown
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_grader import CRITERIA, grade_pulldown
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.pulldown_cases import sparse_record, synthetic_record


def convert(record):
    return convert_pulldown(grade_pulldown(record))


def test_every_criterion_is_mapped_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(CRITERIA) and len(mapped) == len(set(mapped)) == 17


def test_a_pulldown_has_no_effect_and_no_variance_but_a_qualitative_effect():
    converted = convert(synthetic_record())
    assert converted['extraction']['quantities']['effect'] is None and converted['extraction']['quantities']['effect_variance'] is None
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] is None and cells['effect_variance']['value'] is None and cells['effect_precision']['value'] is None
    assert converted['null_components']['effect'] == 'qualitative_assay_reports_no_binding_constant' and converted['null_components']['effect_variance'] == 'qualitative_assay_reports_no_binding_constant'
    assert converted['qualitative_effect'] == {'statement': 'interaction_detected', 'support_refs': ['span_exp_synthetic_pulldown_1'], 'fold_enrichment': 12.0}
    assert converted['extraction']['assay_type'] == 'ligand_binding' and converted['extraction']['quantity_kind'] == 'relative_binding_response' and converted['experiment_type'] == 'pulldown'
    assert converted['dependence'] == {'analyte_preparation_ref': 'prep_prey_a', 'immobilized_preparation_ref': 'prep_bait_a', 'surface_ref': None, 'dataset_ref': 'dataset_pulldown_1'}
    assert converted['null_components']['recovery'] == 'a_pulldown_has_no_matrix_recovery_measurement'
    assert {name: item['status'] for name, item in converted['extraction']['interpretations'].items()} == dict.fromkeys(CRITERIA_MAP, 'supported')
    assert all(item['support_refs'] for item in converted['extraction']['interpretations'].values())


def test_no_number_of_the_record_is_put_into_the_effect():
    converted = convert(synthetic_record())                      # the fold enrichment (12) and the percent of the input (4) are not binding constants
    assert 12.0 not in [cell['value'] for cell in converted['sheet']['cells'].values()]
    assert converted['sheet']['cells']['measured_effect']['reasons'] == ['effect_not_selected']


def test_the_statement_is_detected_not_detected_or_not_stated():
    record = synthetic_record()
    record['facts']['prey_detected_in_eluate'] = fact('no', ['s'])
    assert convert(record)['qualitative_effect'] == {'statement': 'interaction_not_detected', 'support_refs': ['s'], 'fold_enrichment': 12.0}
    record['facts']['prey_detected_in_eluate'] = fact('unknown')
    assert convert(record)['qualitative_effect'] == {'statement': 'interaction_not_stated', 'support_refs': [], 'fold_enrichment': 12.0}
    assert convert(sparse_record())['qualitative_effect']['fold_enrichment'] is None


def test_a_conflicting_member_makes_its_sheet_criterion_conflicting_an_unknown_one_unknown():
    record = synthetic_record()
    record['facts']['prey_absent_in_negative_control'] = fact('no', ['s'])                 # a sticky prey
    record['facts']['input_lane_shown'] = fact('unknown')
    record['quantities']['wash_count'] = point(0, 'count', 'w', ['s'])                     # the paper states no wash: conflicting
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'conflicting' and interpretations['binding_controls']['support_refs'] == []
    assert interpretations['binding_regime']['status'] == 'conflicting'
    assert interpretations['binding_species']['status'] == 'supported' and interpretations['sampling_basis']['status'] == 'supported'
    record = synthetic_record()
    record['facts']['input_lane_shown'] = fact('unknown')
    record['quantities']['wash_count'] = point(1, 'count', 'w', ['s'])                     # one wash, under the researched three: partial credit, not a conflict
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'unknown' and interpretations['binding_regime']['status'] == 'supported'
    assert interpretations['binding_regime']['degree'] == pytest.approx(1 / 3)


def test_a_lysate_coip_without_direct_binding_leaves_the_species_criterion_unknown_not_conflicting():
    record = synthetic_record()
    record['facts']['direct_interaction_shown'] = fact('unknown')
    assert convert(record)['extraction']['interpretations']['binding_species']['status'] == 'unknown'


def test_a_not_applicable_member_is_dropped():
    record = synthetic_record()
    record['facts']['quantification_with_normalization'] = fact('not_applicable')
    interpretations = convert(record)['extraction']['interpretations']
    assert 'calibration_applicability' not in interpretations                    # its only member is not applicable: the sheet criterion is not selected
    record = synthetic_record()
    record['facts']['direct_interaction_shown'] = fact('not_applicable')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_species']['status'] == 'supported' and interpretations['binding_species']['support_refs'] == ['span_exp_synthetic_pulldown_1']


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    assert (sheet.MIN_WASH_NACL_MM, sheet.WASH_NACL_ZERO_AGREEMENT_MM, sheet.MIN_WASH_DETERGENT_PERCENT, sheet.WASH_DETERGENT_ZERO_AGREEMENT_PERCENT, sheet.MIN_WASHES, sheet.WASH_COUNT_ZERO_AGREEMENT) == (150.0, 50.0, 0.05, 0.0, 3, 0)
    assert (sheet.MIN_INCUBATION_MIN, sheet.INCUBATION_ZERO_AGREEMENT_MIN, sheet.MIN_FOLD_ENRICHMENT, sheet.ENRICHMENT_ZERO_AGREEMENT_FOLD, sheet.MIN_REPLICATES) == (30.0, 5.0, 3.0, 1.0, 3)


def test_every_number_a_judge_uses_is_a_named_expert_review_constant():
    source = inspect.getsource(sheet)
    judges = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef) and (node.name.startswith('_judge_') or node.name in ('_degree', '_linear'))]
    numbers = {node.value for fn in judges for node in ast.walk(fn) if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)}
    assert numbers <= {0.0, 1.0}                                                           # the bounds of a degree only; every limit is a module constant
    for name in ('MIN_WASH_NACL_MM', 'WASH_NACL_ZERO_AGREEMENT_MM', 'MIN_WASH_DETERGENT_PERCENT', 'WASH_DETERGENT_ZERO_AGREEMENT_PERCENT', 'MIN_WASHES', 'WASH_COUNT_ZERO_AGREEMENT',
                 'MIN_INCUBATION_MIN', 'INCUBATION_ZERO_AGREEMENT_MIN', 'MIN_FOLD_ENRICHMENT', 'ENRICHMENT_ZERO_AGREEMENT_FOLD', 'SPREAD_Z_FULL', 'MIN_REPLICATES'):
        assert any(line.startswith(name + ' = ') and '# EXPERT_REVIEW:' in line for line in source.splitlines()), name


def sweep(quantity, values, unit, criterion, **facts):
    """The sheet's verdict for each stated value of one quantity, on the synthetic record."""
    out = []
    for value in values:
        record = synthetic_record()
        record['quantities'][quantity] = point(value, unit, 'q', ['s'])
        if quantity == 'fold_enrichment':                                                  # the fold alone: the spread of the synthetic record is tested on its own
            for spread in ('fold_enrichment_sd', 'fold_enrichment_sem'):
                record['quantities'][spread] = {**record['quantities'][spread], 'status': 'unavailable', 'value': None}
        for name, answer in facts.items():
            record['facts'][name] = fact(answer, ['s'])
        out.append(_criterion(grade_pulldown(record), criterion))
    return out


@pytest.mark.parametrize('quantity, unit, criterion, researched, values, facts', [
    ('wash_count', 'count', 'wash_count', 3, (1, 2, 3, 4, 6, 10), {}),
    ('replicate_count', 'count', 'replicates', 3, (1, 2, 3, 4, 6, 10), {'independent_experiments': 'yes'}),
    ('nacl_wash', 'mM', 'wash_stringency', 150.0, (60.0, 100.0, 140.0, 149.0, 150.0, 300.0, 500.0), {}),
    ('incubation_time', 'min', 'incubation', 30.0, (6.0, 10.0, 20.0, 29.0, 30.0, 120.0), {'prey_detected_in_eluate': 'no'}),      # the incubation guards a negative
    ('fold_enrichment', 'ratio', 'enrichment', 3.0, (1.1, 1.5, 2.0, 2.9, 3.0, 12.0), {}),
])
def test_each_judge_is_monotone_bounded_and_gives_partial_credit_just_below_its_researched_value(quantity, unit, criterion, researched, values, facts):
    verdicts = sweep(quantity, values, unit, criterion, **facts)
    assert {v['status'] for v in verdicts} == {'supported'} and all('s' in v['support_refs'] for v in verdicts)
    degrees = [v['degree'] for v in verdicts]
    assert degrees == sorted(degrees) and all(0.0 <= d <= 1.0 for d in degrees)                 # a better value never lowers the degree; bounded
    assert all(d == 1.0 for value, d in zip(values, degrees) if value >= researched)              # full agreement at and beyond the researched value
    below = [d for value, d in zip(values, degrees) if value < researched]
    assert below and all(0.0 < d < 1.0 for d in below)                                            # no step: partial credit below it, never 0 or a conflict


def test_a_value_not_stated_is_unknown_not_zero():
    for quantity, criterion in (('wash_count', 'wash_count'), ('replicate_count', 'replicates'), ('incubation_time', 'incubation'), ('fold_enrichment', 'enrichment')):
        record = synthetic_record()
        record['quantities'][quantity] = {**record['quantities'][quantity], 'status': 'unavailable', 'value': None}
        verdict = _criterion(grade_pulldown(record), criterion)
        assert verdict == {'status': 'unknown', 'support_refs': []} and 'degree' not in verdict


def test_each_judge_uses_the_scale_its_own_physics_gives():
    one, two = sweep('replicate_count', (1, 2), 'count', 'replicates', independent_experiments='yes')       # precision of a mean: sqrt
    assert one['degree'] == pytest.approx(math.sqrt(1 / 3)) and two['degree'] == pytest.approx(math.sqrt(2 / 3))
    one, two = sweep('wash_count', (1, 2), 'count', 'wash_count')                                          # log-reduction per wash: linear in the count
    assert one['degree'] == pytest.approx(1 / 3) and two['degree'] == pytest.approx(2 / 3)
    salt, = sweep('nacl_wash', (100.0,), 'mM', 'wash_stringency')                                          # Debye screening: linear in sqrt(salt)
    assert salt['degree'] == pytest.approx((math.sqrt(100) - math.sqrt(50)) / (math.sqrt(150) - math.sqrt(50)))
    fold, = sweep('fold_enrichment', (2.0,), 'ratio', 'enrichment')                                        # a ratio of intensities: linear in log fold
    assert fold['degree'] == pytest.approx(math.log(2) / math.log(3))
    time, = sweep('incubation_time', (10.0,), 'min', 'incubation', prey_detected_in_eluate='no')           # unknown association times: linear in log time
    assert time['degree'] == pytest.approx(math.log(2) / math.log(6))


def test_a_weaker_regime_is_low_credit_never_conflicting_but_no_wash_and_no_enrichment_stay_conflicting():
    for quantity, unit, criterion, values, facts in (('nacl_wash', 'mM', 'wash_stringency', (0.0, 20.0, 50.0), {}), ('detergent_wash', 'percent', 'wash_stringency', (0.0,), {}),
                                                     ('incubation_time', 'min', 'incubation', (0.5, 5.0), {'prey_detected_in_eluate': 'no'})):
        for verdict in sweep(quantity, values, unit, criterion, **facts):
            assert verdict['status'] == 'supported' and verdict['degree'] == 0.0 and 's' in verdict['support_refs'], (quantity, verdict)
    salt, = sweep('nacl_wash', (500.0,), 'mM', 'wash_stringency')
    detergent_free, = sweep('detergent_wash', (0.0,), 'percent', 'wash_stringency')
    assert salt['degree'] == 1.0 and detergent_free['degree'] == 0.0          # the weaker component decides: the two remove different binders
    for quantity, unit, criterion, value in (('wash_count', 'count', 'wash_count', 0), ('fold_enrichment', 'ratio', 'enrichment', 1.0), ('fold_enrichment', 'ratio', 'enrichment', 0.5)):
        verdict, = sweep(quantity, (value,), unit, criterion)
        assert verdict == {'status': 'conflicting', 'support_refs': ['s']}, (quantity, value)


def test_a_detected_prey_gets_full_incubation_credit_at_any_time_and_a_negative_or_unstated_one_the_curve():
    for value in (0.5, 5.0, 10.0, 30.0, 960.0):
        assert sweep('incubation_time', (value,), 'min', 'incubation')[0] == {'status': 'supported', 'support_refs': ['s'], 'degree': 1.0}      # the synthetic prey is detected
    for answer in ('no', 'unknown'):
        record = synthetic_record()
        record['facts']['prey_detected_in_eluate'] = fact(answer, ['s'] if answer == 'no' else [])
        record['quantities']['incubation_time'] = point(10.0, 'min', 'i', ['s'])
        assert _criterion(grade_pulldown(record), 'incubation')['degree'] == pytest.approx(math.log(2) / math.log(6)), answer


@pytest.mark.parametrize('quantity, unit, criterion, values, facts', [
    ('nacl_wash', 'mM', 'wash_stringency', (0.0, 30.0, 50.0, 51.0, 75.0, 100.0, 149.0, 150.0, 1000.0), {}),
    ('detergent_wash', 'percent', 'wash_stringency', (0.0, 0.001, 0.01, 0.049, 0.05, 1.0), {}),
    ('incubation_time', 'min', 'incubation', (0.0, 4.0, 5.0, 5.5, 15.0, 29.9, 30.0, 960.0), {'prey_detected_in_eluate': 'no'}),
    ('fold_enrichment', 'ratio', 'enrichment', (1.01, 1.2, 1.5, 2.0, 2.99, 3.0, 50.0), {}),
    ('wash_count', 'count', 'wash_count', (1, 2, 3, 8), {}),
])
def test_monotone_and_bounded_over_the_whole_range_including_the_zero_end(quantity, unit, criterion, values, facts):
    degrees = [v['degree'] for v in sweep(quantity, values, unit, criterion, **facts)]
    assert degrees == sorted(degrees) and all(0.0 <= d <= 1.0 for d in degrees) and degrees[-1] == 1.0


def test_the_unknown_weight_is_never_part_of_a_degree():
    source = inspect.getsource(sheet)
    code = source.split('"""', 2)[2]                                                       # after the module docstring, which names the weight only to explain it
    assert 'WEIGHT_UNKNOWN' not in code and 'literature_row_contract' not in code


def test_the_degree_travels_into_the_sheet_criterion_and_is_the_weakest_member_degree():
    record = synthetic_record()
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_regime']['degree'] == 1.0 and interpretations['binding_parameter_definition']['degree'] == 1.0     # continuous members at full agreement
    assert interpretations['sampling_basis']['degree'] == 1.0 and 'degree' not in interpretations['binding_controls']                # three independent experiments: full; facts carry none
    record['quantities']['incubation_time'] = point(17.5, 'min', 'i', ['s'])                      # the prey is detected: 1.0
    record['quantities']['nacl_wash'] = point(100.0, 'mM', 'n', ['s'])                            # sqrt scale: about 0.566
    record['quantities']['fold_enrichment'] = point(2.0, 'ratio', 'f', ['s'])                     # log scale: about 0.631
    for spread in ('fold_enrichment_sd', 'fold_enrichment_sem'):
        record['quantities'][spread] = {**record['quantities'][spread], 'status': 'unavailable', 'value': None}
    salt = (math.sqrt(100) - math.sqrt(50)) / (math.sqrt(150) - math.sqrt(50))
    converted = convert(record)
    interpretations = converted['extraction']['interpretations']
    assert interpretations['binding_regime']['status'] == 'supported' and interpretations['binding_regime']['degree'] == pytest.approx(salt)
    assert interpretations['binding_parameter_definition']['degree'] == pytest.approx(math.log(2) / math.log(3))
    assert converted['sheet']['interpretations']['binding_regime']['degree'] == interpretations['binding_regime']['degree']            # it travels into the sheet
    record['quantities']['wash_count'] = point(1, 'count', 'w', ['s'])                            # 1/3, now the weakest member
    assert convert(record)['extraction']['interpretations']['binding_regime']['degree'] == pytest.approx(1 / 3)
    record['quantities']['wash_count'] = point(0, 'count', 'w', ['s'])                            # no wash: conflicting, no degree
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_regime']['status'] == 'conflicting' and 'degree' not in interpretations['binding_regime']


def test_a_criterion_resting_on_a_weak_quote_gets_the_support_degree_and_a_direct_one_is_unchanged():
    base = convert(synthetic_record())['extraction']['interpretations']
    assert base['sampling_basis']['degree'] == 1.0 and 'degree' not in base['binding_controls']
    record = synthetic_record()
    record['facts']['reciprocal_done']['support'] = 'implied'                                  # a fact: supported with no degree before
    record['quantities']['replicate_count']['support'] = 'about_something_else'                # 1.0 from the count, times 0.3
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'supported' and interpretations['binding_controls']['degree'] == pytest.approx(0.7)
    assert interpretations['sampling_basis']['status'] == 'supported' and interpretations['sampling_basis']['degree'] == pytest.approx(0.3)
    assert interpretations['binding_regime'] == base['binding_regime'] and interpretations['calibration_applicability'] == base['calibration_applicability']
    record['facts']['competition_disrupts_interaction']['support'] = 'about_something_else'      # the weakest member decides
    assert convert(record)['extraction']['interpretations']['binding_controls']['degree'] == pytest.approx(0.3)


def test_the_support_degree_multiplies_a_degree_the_sheet_already_gave_and_never_changes_a_status():
    record = synthetic_record()
    record['quantities']['nacl_wash'] = point(100.0, 'mM', 'n', ['s'], support='implied')          # about 0.566 from the comparison, times 0.7
    interpretations = convert(record)['extraction']['interpretations']
    salt = (math.sqrt(100) - math.sqrt(50)) / (math.sqrt(150) - math.sqrt(50))
    assert interpretations['binding_regime']['status'] == 'supported' and interpretations['binding_regime']['degree'] == pytest.approx(salt * 0.7)
    record['quantities']['fold_enrichment'] = point(0.8, 'ratio', 'f', ['s'], support='about_something_else')      # conflicting: no degree
    verdict = convert(record)['extraction']['interpretations']['binding_parameter_definition']
    assert verdict['status'] == 'conflicting' and 'degree' not in verdict
    record = synthetic_record()
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'], support='implied')         # sqrt(2/3) from the count, times 0.7
    verdict = convert(record)['extraction']['interpretations']['sampling_basis']
    assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(math.sqrt(2 / 3) * 0.7)
    record = synthetic_record()
    record['facts']['prey_detected_in_eluate']['support'] = 'implied'
    converted = convert(record)
    assert converted['extraction']['interpretations']['binding_parameter_definition']['degree'] == pytest.approx(0.7)
    assert converted['qualitative_effect']['statement'] == 'interaction_detected' and converted['qualitative_effect']['support_refs']      # the qualitative effect stays as it was
