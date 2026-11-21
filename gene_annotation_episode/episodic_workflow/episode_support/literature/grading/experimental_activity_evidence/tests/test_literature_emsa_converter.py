"""EMSA converter: the quantitative effect and variance (an apparent KD), the qualitative effect (no KD), the criteria mapping and the null reasons."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_emsa_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_converter import CRITERIA_MAP, _criterion, convert_emsa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_grader import CRITERIA, grade_emsa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.emsa_cases import qualitative_record, sparse_record, synthetic_record

SHEET_CRITERIA = ('binding_controls', 'binding_regime', 'binding_parameter_definition', 'calibration_applicability', 'sampling_basis')


def convert(record):
    return convert_emsa(grade_emsa(record))


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_every_criterion_is_mapped_to_exactly_one_sheet_criterion():
    mapped = [member for members in CRITERIA_MAP.values() for member in members]
    assert sorted(mapped) == sorted(CRITERIA) and len(mapped) == len(set(mapped)) == 17


def test_the_apparent_kd_is_the_effect_and_its_standard_error_squared_is_the_variance():
    converted = convert(synthetic_record())
    effect = converted['extraction']['quantities']['effect']
    assert effect['value'] == 20.0 and effect['unit'] == 'nM' and effect['measurement_keys'] == ['emsa_kd:exp_synthetic_emsa_1'] and effect['native_component'] == 'kd'
    variance = converted['extraction']['quantities']['effect_variance']
    assert variance['value'] == pytest.approx(4.0) and variance['unit'] == 'nM_squared' and variance['origin'] == 'derived'      # 2 nM squared
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] == pytest.approx(20.0) and cells['effect_variance']['value'] == pytest.approx(4.0) and cells['effect_precision']['value'] == pytest.approx(0.25)
    assert converted['extraction']['assay_type'] == 'ligand_binding' and converted['extraction']['quantity_kind'] == 'binding_parameter' and converted['experiment_type'] == 'emsa'
    assert {name: item['status'] for name, item in converted['extraction']['interpretations'].items()} == dict.fromkeys((*SHEET_CRITERIA, 'variance_correspondence'), 'supported')
    assert all(item['support_refs'] for item in converted['extraction']['interpretations'].values())
    assert converted['dependence'] == {'analyte_preparation_ref': 'prep_protein_a', 'immobilized_preparation_ref': 'prep_probe_a', 'surface_ref': None, 'dataset_ref': 'dataset_emsa_1'}
    assert converted['null_components']['recovery'] == 'an_emsa_has_no_matrix_recovery_measurement'
    assert 'qualitative_effect' not in converted and 'effect' not in converted['null_components']                          # a quantitative result is pooled, never also counted as qualitative


def test_the_kind_of_the_spread_decides_whether_a_variance_exists():
    record = synthetic_record()
    record['spread_kind'] = 'standard_deviation'                                 # sd 2 nM over 3 independent experiments: 4 / 3
    assert convert(record)['extraction']['quantities']['effect_variance']['value'] == pytest.approx(4.0 / 3)
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])      # two independent experiments: below MIN_REPLICATES, partial credit, still supported: 4 / 2
    assert convert(record)['extraction']['quantities']['effect_variance']['value'] == pytest.approx(2.0)
    record['quantities']['replicate_count'] = point(1, 'count', 'n', ['s'])      # one gel: replicates supported with partial credit, but one gel has no gel-to-gel spread
    converted = convert(record)
    assert converted['extraction']['interpretations']['sampling_basis']['status'] == 'supported'
    assert converted['extraction']['quantities']['effect_variance'] is None and converted['null_components']['effect_variance'] == 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate'
    record['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    record['facts']['independent_experiments'] = fact('unknown')                 # independence not stated: replicates unknown, no variance from an SD
    assert convert(record)['null_components']['effect_variance'] == 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate'
    record['facts']['independent_experiments'] = fact('yes', ['s'])
    assert converted['extraction']['quantities']['effect']['value'] == 20.0     # the effect stays, only the variance is null
    record['spread_kind'] = 'confidence_interval'
    assert convert(record)['null_components']['effect_variance'] == 'confidence_interval_not_converted'
    record['spread_kind'] = None
    assert convert(record)['null_components']['effect_variance'] == 'spread_kind_not_stated'
    record['spread_kind'] = 'standard_error'
    missing(record, 'kd_spread')
    assert convert(record)['null_components']['effect_variance'] == 'kd_spread_not_given'
    record['quantities']['kd_spread'] = point(0.002, 'uM', 's', ['s'])          # 2 nM
    assert convert(record)['extraction']['quantities']['effect_variance']['value'] == pytest.approx(4.0)


def test_the_kd_in_another_unit_is_converted_to_nm():
    record = synthetic_record()
    record['quantities']['kd'] = point(0.02, 'uM', 'k', ['s'])
    assert convert(record)['extraction']['quantities']['effect']['value'] == pytest.approx(20.0)


def test_without_a_kd_the_effect_is_empty_and_the_result_is_qualitative():
    converted = convert(qualitative_record())
    assert converted['extraction']['quantities']['effect'] is None and converted['extraction']['quantities']['effect_variance'] is None
    cells = converted['sheet']['cells']
    assert cells['measured_effect']['value'] is None and cells['effect_variance']['value'] is None and cells['effect_precision']['value'] is None
    assert converted['null_components']['effect'] == 'qualitative_assay_reports_no_binding_constant' and converted['null_components']['effect_variance'] == 'qualitative_assay_reports_no_binding_constant'
    assert converted['qualitative_effect'] == {'statement': 'interaction_detected', 'support_refs': ['span_exp_qualitative_emsa_1'], 'fraction_shifted': None}
    assert converted['extraction']['quantity_kind'] == 'relative_binding_response' and converted['experiment_type'] == 'emsa'
    assert converted['dependence'] == {'analyte_preparation_ref': 'prep_protein_q', 'immobilized_preparation_ref': 'prep_probe_q', 'surface_ref': None, 'dataset_ref': 'dataset_emsa_q'}
    # the KD criteria do not apply to it, so the sheet criteria that they belong to are decided by the other members
    assert {name: item['status'] for name, item in converted['extraction']['interpretations'].items()} == dict.fromkeys(SHEET_CRITERIA, 'supported')
    assert 'variance_correspondence' not in converted['extraction']['interpretations']


def test_no_number_of_a_qualitative_record_is_put_into_the_effect_but_the_fraction_shifted_is_carried_beside_it():
    record = qualitative_record()
    record['quantities']['fraction_shifted_highest'] = point(92.0, 'percent', 'f', ['s'])         # a shifted fraction is not a binding constant
    converted = convert(record)
    assert 92.0 not in [cell['value'] for cell in converted['sheet']['cells'].values()]
    assert converted['sheet']['cells']['measured_effect']['reasons'] == ['effect_not_selected']
    assert converted['qualitative_effect']['fraction_shifted'] == 92.0


def test_the_statement_is_detected_not_detected_or_not_stated():
    record = qualitative_record()
    record['facts']['shift_detected'] = fact('no', ['s'])
    assert convert(record)['qualitative_effect'] == {'statement': 'interaction_not_detected', 'support_refs': ['s'], 'fraction_shifted': None}
    record['facts']['shift_detected'] = fact('unknown')
    assert convert(record)['qualitative_effect'] == {'statement': 'interaction_not_stated', 'support_refs': [], 'fraction_shifted': None}
    sparse = convert(sparse_record())
    assert sparse['qualitative_effect']['statement'] == 'interaction_detected' and sparse['extraction']['interpretations']['binding_parameter_definition']['status'] == 'unknown'     # the number of shifted species is not stated


def test_a_conflicting_member_makes_its_sheet_criterion_conflicting_an_unknown_one_unknown():
    record = synthetic_record()
    record['facts']['mutant_probe_does_not_shift'] = fact('no', ['s'])                    # the mutant probe shifted
    record['facts']['probe_alone_lane_shown'] = fact('unknown')
    record['quantities']['protein_concentration_highest'] = point(20.0, 'nM', 'h', ['s'])      # only the KD: the plateau is not reached (the zero-agreement limit)
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'conflicting' and interpretations['binding_controls']['support_refs'] == []
    assert interpretations['binding_regime']['status'] == 'conflicting'
    assert interpretations['binding_parameter_definition']['status'] == 'supported' and interpretations['sampling_basis']['status'] == 'supported'
    record = synthetic_record()
    record['facts']['probe_alone_lane_shown'] = fact('unknown')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'unknown' and interpretations['binding_regime']['status'] == 'supported'


def test_a_not_applicable_member_is_dropped():
    record = synthetic_record()
    record['facts']['free_probe_quantified'] = fact('not_applicable')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'supported' and interpretations['calibration_applicability']['support_refs'] == ['span_exp_synthetic_emsa_1']
    record['facts']['free_probe_quantified'] = fact('not_applicable')
    missing(record, 'fraction_shifted_highest')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'unknown'          # the saturation criterion is unknown without the fraction
    missing(record, 'kd')
    interpretations = convert(record)['extraction']['interpretations']
    assert 'calibration_applicability' not in interpretations                           # both members not applicable: the sheet criterion is not selected


def test_the_sheet_holds_the_threshold_constants_with_their_values():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_emsa_converter as sheet
    assert (sheet.MIN_COMPETITOR_EXCESS, sheet.MAX_PROBE_OVER_KD, sheet.PROBE_OVER_KD_ZERO_AGREEMENT) == (50.0, 1.0, 10.0)
    assert (sheet.LOW_FACTOR, sheet.LOW_ZERO_AGREEMENT_FACTOR, sheet.HIGH_FACTOR, sheet.HIGH_ZERO_AGREEMENT_FACTOR) == (0.25, 1.0, 5.0, 1.0)
    assert (sheet.MIN_TITRATION_POINTS, sheet.MIN_FRACTION_SHIFTED_HIGHEST, sheet.FRACTION_SHIFTED_ZERO_AGREEMENT, sheet.MAX_SHIFTED_SPECIES, sheet.ONE_SITE_MODELS, sheet.MIN_REPLICATES) == (6, 80.0, 50.0, 1, ('one_site', 'quadratic'), 3)
    assert (sheet.TITRATION_FIT_PARAMETERS, sheet.MIN_EXPERIMENTS_FOR_A_SPREAD, sheet.DEPLETION_MODELS) == (2, 2, ('quadratic',))
    assert (sheet.FAST_ASSOCIATION_RATE_PER_M_PER_S, sheet.SLOW_ASSOCIATION_RATE_PER_M_PER_S, sheet.EQUILIBRATION_HALF_LIVES) == (1e8, 1e6, 5.0)
    assert not hasattr(sheet, 'MIN_INCUBATION_MIN')      # no absolute floor: with no KD the incubation is unknown
    assert not hasattr(sheet, 'TITRATION_POINTS_ZERO_AGREEMENT') and not hasattr(sheet, 'REPLICATES_ZERO_AGREEMENT')      # no conflicting end for a count any more


def test_every_sheet_constant_is_named_and_marked_for_expert_review():
    import inspect
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_emsa_converter as sheet
    source = inspect.getsource(sheet).splitlines()
    for name in ('MIN_COMPETITOR_EXCESS', 'MAX_PROBE_OVER_KD', 'PROBE_OVER_KD_ZERO_AGREEMENT', 'LOW_FACTOR', 'LOW_ZERO_AGREEMENT_FACTOR', 'HIGH_FACTOR', 'HIGH_ZERO_AGREEMENT_FACTOR',
                 'MIN_TITRATION_POINTS', 'TITRATION_FIT_PARAMETERS', 'MIN_FRACTION_SHIFTED_HIGHEST', 'FRACTION_SHIFTED_ZERO_AGREEMENT', 'MAX_SHIFTED_SPECIES', 'ONE_SITE_MODELS', 'MIN_REPLICATES',
                 'MIN_EXPERIMENTS_FOR_A_SPREAD', 'DEPLETION_MODELS', 'FAST_ASSOCIATION_RATE_PER_M_PER_S', 'SLOW_ASSOCIATION_RATE_PER_M_PER_S', 'EQUILIBRATION_HALF_LIVES'):
        lines = [line for line in source if line.startswith(name + ' = ')]
        assert len(lines) == 1 and '# EXPERT_REVIEW:' in lines[0], name


def judged_with(field, value, unit, criterion, **facts):
    record = synthetic_record()
    record['quantities'][field] = point(value, unit, 'v', ['s'])
    for name, answer in facts.items():
        record['facts'][name] = fact(answer, ['s'] if answer != 'unknown' else [])
    return _criterion(grade_emsa(record), criterion)


@pytest.mark.parametrize('criterion, field, full, expected', [
    # (n - p + 1) / (6 - p + 1) with p = 2 fit parameters, n counted as p below it: the KD itself is one unit of credit
    ('titration_points', 'titration_point_count', 6, {1: 0.2, 2: 0.2, 3: 0.4, 4: 0.6, 5: 0.8, 6: 1.0, 7: 1.0, 11: 1.0, 30: 1.0}),
    # sqrt(n / 3): the precision of the mean KD over n independent gels
    ('replicates', 'replicate_count', 3, {1: (1 / 3) ** 0.5, 2: (2 / 3) ** 0.5, 3: 1.0, 4: 1.0, 10: 1.0}),
])
def test_a_count_is_a_curve_full_at_the_researched_value_low_partial_credit_below_and_never_conflicting(criterion, field, full, expected):
    ranks = []
    for count, degree in expected.items():
        verdict = judged_with(field, count, 'count', criterion)
        assert verdict['status'] == 'supported' and 's' in verdict['support_refs'], count      # a short series or a single gel is weak evidence, never evidence against (replicates also carry the independence fact's span)
        assert verdict['degree'] == pytest.approx(degree) and 0.0 < verdict['degree'] <= 1.0, count
        ranks.append(verdict['degree'])
    assert ranks == sorted(ranks)                                                       # more points or experiments never lower the degree
    below = judged_with(field, full - 1, 'count', criterion)
    assert below['status'] == 'supported' and 0.0 < below['degree'] < 1.0              # no step: just below the researched value is partial credit, not a fail


def test_the_smallest_series_and_a_single_gel_get_low_credit_not_a_conflict_in_the_sheet():
    record = synthetic_record()
    record['quantities']['titration_point_count'] = point(2, 'count', 't', ['s'])
    record['quantities']['replicate_count'] = point(1, 'count', 'n', ['s'])
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_regime']['status'] == 'supported' and interpretations['binding_regime']['degree'] == pytest.approx(0.2)
    assert interpretations['sampling_basis']['status'] == 'supported' and interpretations['sampling_basis']['degree'] == pytest.approx((1 / 3) ** 0.5)


@pytest.mark.parametrize('criterion, field, unit, worse_to_better, full_at', [
    ('probe_concentration', 'probe_concentration', 'nM', (400.0, 200.0, 199.0, 110.0, 60.0, 21.0, 20.0, 10.0, 0.5), 20.0),          # KD 20 nM: 10x the zero end, 1x the full end
    ('saturation', 'fraction_shifted_highest', 'percent', (30.0, 50.0, 51.0, 65.0, 79.0, 80.0, 95.0), 80.0),
    ('protein_range', 'protein_concentration_highest', 'nM', (10.0, 20.0, 21.0, 60.0, 99.0, 100.0, 640.0), 100.0),             # 1x the KD the zero end, 5x the full end
    ('protein_range', 'protein_concentration_lowest', 'nM', (40.0, 20.0, 19.0, 12.5, 5.1, 5.0, 1.0), 5.0),                       # 1x the KD the zero end, 0.25x the full end
])
def test_a_ratio_curve_is_monotone_bounded_and_gradual_around_its_researched_ends(criterion, field, unit, worse_to_better, full_at):
    degrees = []
    for value in worse_to_better:
        verdict = judged_with(field, value, unit, criterion)
        degree = verdict['degree'] if verdict['status'] == 'supported' else 0.0
        assert verdict['status'] in ('supported', 'conflicting') and 0.0 <= degree <= 1.0, value
        if value == full_at:
            assert degree == 1.0, value
        degrees.append(degree)
    assert degrees == sorted(degrees)                                                   # a better value never lowers the degree
    assert 0.0 < sorted(d for d in degrees if d < 1.0)[-1] < 1.0                         # just short of the full end is partial credit, not a step


def test_a_quadratic_fit_is_not_penalised_for_a_probe_above_the_kd():
    for probe in (0.5, 110.0, 400.0):                                                    # up to 20 x the KD
        record = synthetic_record()
        record['fit_model'] = 'quadratic'
        record['quantities']['probe_concentration'] = point(probe, 'nM', 'p', ['s'])
        verdict = _criterion(grade_emsa(record), 'probe_concentration')
        assert verdict['status'] == 'supported' and 'degree' not in verdict and verdict['support_refs'], probe      # the fit solves for the probe depletion
    assert judged_with('probe_concentration', 400.0, 'nM', 'probe_concentration')['status'] == 'conflicting'           # the one-site fit of the synthetic record is still judged


def test_an_incubation_is_a_curve_between_the_fast_and_the_slow_association_time_of_the_kd():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_converter import _equilibration_min, SLOW_ASSOCIATION_RATE_PER_M_PER_S
    assert _equilibration_min(20.0) == pytest.approx(0.8664 / 60, rel=1e-3) and _equilibration_min(20.0, SLOW_ASSOCIATION_RATE_PER_M_PER_S) == pytest.approx(86.64 / 60, rel=1e-3)      # 20 nM: 0.87 s to 87 s
    assert _equilibration_min(0.005) == pytest.approx(57.76, abs=0.01) and _equilibration_min(0.005, SLOW_ASSOCIATION_RATE_PER_M_PER_S) == pytest.approx(5776.0, abs=1.0)      # 5 pM: 58 min to 96 h
    assert _equilibration_min(1e4) == pytest.approx(1.733e-3 / 60, rel=1e-3) and _equilibration_min(1e4, SLOW_ASSOCIATION_RATE_PER_M_PER_S) == pytest.approx(0.1733 / 60, rel=1e-3)      # 10 uM: 1.7 ms to 0.17 s
    record = synthetic_record()                                                          # KD 20 nM, T_FAST 0.8664 s, T_SLOW 86.64 s, degree = ln(t / 0.8664 s) / ln(100)
    record['facts']['equilibrium_reached'] = fact('unknown')
    kd_refs = record['quantities']['kd']['source_refs']
    last = -1.0
    for seconds, expected in ((0.5, None), (0.8664, None), (5.0, 0.3806), (30.0, 0.7698), (60.0, 0.9202), (86.64, 1.0), (600.0, 1.0)):
        record['quantities']['incubation_time'] = point(seconds / 60, 'min', 'i', ['s'])
        verdict = _criterion(grade_emsa(record), 'equilibrium')
        if expected is None:
            assert verdict['status'] == 'conflicting' and 'degree' not in verdict and verdict['support_refs'] == list(dict.fromkeys(['s', *kd_refs])), seconds      # at or below T_FAST: the zero end
            continue
        assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(expected, abs=1e-3) and verdict['support_refs'] == list(dict.fromkeys(['s', *kd_refs])), seconds
        assert verdict['degree'] >= last                                                 # a longer incubation never lowers the degree
        last = verdict['degree']
    record = synthetic_record(kd=0.005)                                                  # 5 pM: T_FAST 57.76 min, T_SLOW 5776 min (96 h)
    record['facts']['equilibrium_reached'] = fact('unknown')
    for minutes, expected in ((30.0, None), (57.0, None), (120.0, 0.1588), (600.0, 0.5083), (5776.0, 1.0), (7000.0, 1.0)):
        record['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        verdict = _criterion(grade_emsa(record), 'equilibrium')
        assert verdict['status'] == ('conflicting' if expected is None else 'supported'), minutes
        if expected is not None:
            assert verdict['degree'] == pytest.approx(expected, abs=1e-3), minutes
    record = qualitative_record()                                                        # no KD: no scale for the time, unknown whatever the time (no floor)
    record['facts']['equilibrium_reached'] = fact('unknown')
    for minutes in (0.1, 1.0, 14.0, 15.0, 30.0):
        record['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        assert _criterion(grade_emsa(record), 'equilibrium') == {'status': 'unknown', 'support_refs': []}, minutes
    record['facts']['equilibrium_reached'] = fact('yes', ['s'])                         # a stated time course outweighs the incubation
    assert _criterion(grade_emsa(record), 'equilibrium')['status'] == 'supported'


def test_the_probe_over_the_kd_is_judged_on_the_log_of_the_depletion_bias():
    # KD 20 nM; b(r) = 1 + r / 2, degree = (ln 6 - ln b(r)) / (ln 6 - ln 1.5); 1 at or below r = 1, conflicting from r = 10
    for probe, expected in ((10.0, 1.0), (20.0, 1.0), (60.0, 0.6315), (110.0, 0.3390), (180.0, 0.0628)):
        verdict = judged_with('probe_concentration', probe, 'nM', 'probe_concentration')
        assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(expected, abs=1e-3), probe
    assert judged_with('probe_concentration', 200.0, 'nM', 'probe_concentration')['status'] == 'conflicting'


def test_the_protein_range_is_judged_on_the_occupancy_between_its_own_ends():
    # occupancy x / (1 + x): the low end full at 0.25 x KD (0.2), zero at 1 x (0.5); the high end full at 5 x (0.8333), zero at 1 x (0.5)
    for lowest, expected in ((5.0, 1.0), (10.0, 0.5556), (15.0, 0.2381), (20.0, None)):                    # x = 0.25, 0.5, 0.75, 1 (KD 20 nM); occupancy 0.3333 gives (0.5 - 1/3) / 0.3
        verdict = judged_with('protein_concentration_lowest', lowest, 'nM', 'protein_range')
        assert (verdict['status'] == 'conflicting') if expected is None else (verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(expected, abs=1e-3)), lowest
    for highest, expected in ((100.0, 1.0), (60.0, 0.75), (40.0, 0.5), (30.0, 0.3), (20.0, None)):         # x = 5, 3, 2, 1.5, 1
        verdict = judged_with('protein_concentration_highest', highest, 'nM', 'protein_range')
        assert (verdict['status'] == 'conflicting') if expected is None else (verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(expected, abs=1e-3)), highest


def test_a_competitor_that_did_not_abolish_the_shift_is_against_specificity_only_at_a_fair_excess():
    for excess, expected in ((10.0, 'unknown'), (49.0, 'unknown'), (50.0, 'conflicting'), (200.0, 'conflicting')):
        verdict = judged_with('specific_competitor_excess', excess, 'ratio', 'specific_competition', shift_abolished_by_specific_competitor='no')
        assert verdict['status'] == expected and 'degree' not in verdict, excess


def test_replicates_without_stated_independence_are_unknown_not_zero():
    for count in (1, 2, 3, 10):
        assert judged_with('replicate_count', count, 'count', 'replicates', independent_experiments='unknown') == {'status': 'unknown', 'support_refs': []}
    record = synthetic_record()
    missing(record, 'replicate_count')
    assert _criterion(grade_emsa(record), 'replicates')['status'] == 'unknown'
    record = synthetic_record()
    missing(record, 'titration_point_count')
    assert _criterion(grade_emsa(record), 'titration_points')['status'] == 'unknown'


def test_the_degree_travels_into_the_sheet_criterion_and_is_the_weakest_member_degree():
    record = synthetic_record()                                                          # KD 20 nM
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_regime']['degree'] == 1.0 and interpretations['calibration_applicability']['degree'] == 1.0 and interpretations['binding_parameter_definition']['degree'] == 1.0
    assert interpretations['sampling_basis']['degree'] == 1.0 and 'degree' not in interpretations['binding_controls']      # three independent experiments: the full end of the replicates curve
    record['quantities']['probe_concentration'] = point(110.0, 'nM', 'p', ['s'])         # 5.5 x the KD: log-bias degree 0.339 (and the same for the one-site model)
    record['quantities']['fraction_shifted_highest'] = point(65.0, 'percent', 'f', ['s'])  # degree 0.5
    record['quantities']['protein_concentration_highest'] = point(60.0, 'nM', 'h', ['s'])  # 3 x the KD: occupancy degree 0.75
    converted = convert(record)
    interpretations = converted['extraction']['interpretations']
    assert interpretations['binding_regime']['status'] == 'supported' and interpretations['binding_regime']['degree'] == pytest.approx(0.3390, abs=1e-3)
    assert interpretations['calibration_applicability']['degree'] == pytest.approx(0.5) and interpretations['binding_parameter_definition']['degree'] == pytest.approx(0.3390, abs=1e-3)
    assert converted['sheet']['interpretations']['binding_regime']['degree'] == interpretations['binding_regime']['degree']      # it travels into the sheet
    record['quantities']['titration_point_count'] = point(2, 'count', 't', ['s'])        # two lanes: 0.2, now the weakest member of binding_regime
    record['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])              # two independent experiments: sqrt(2 / 3)
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_regime']['status'] == 'supported' and interpretations['binding_regime']['degree'] == pytest.approx(0.2)
    assert interpretations['sampling_basis']['status'] == 'supported' and interpretations['sampling_basis']['degree'] == pytest.approx((2 / 3) ** 0.5)
    record['quantities']['fraction_shifted_highest'] = point(40.0, 'percent', 'f', ['s'])
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['calibration_applicability']['status'] == 'conflicting' and 'degree' not in interpretations['calibration_applicability']


def test_several_species_with_no_kd_are_not_applicable_and_dropped_by_the_sheet():
    record = synthetic_record()
    record['quantities']['shifted_species_count'] = point(2, 'count', 's', ['s'])
    assert convert(record)['extraction']['interpretations']['binding_parameter_definition']['status'] == 'conflicting'      # one-site fit for two species
    record['fit_model'] = 'hill'
    assert convert(record)['extraction']['interpretations']['binding_parameter_definition']['status'] == 'supported'
    missing(record, 'kd')
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_parameter_definition']['status'] == 'supported' and interpretations['binding_parameter_definition']['support_refs'] == ['span_exp_synthetic_emsa_1']      # only the shift is left


def test_a_criterion_resting_on_a_weak_quote_gets_the_support_degree_and_a_direct_one_is_unchanged():
    base = convert(synthetic_record())['extraction']['interpretations']
    assert base['binding_controls']['status'] == base['sampling_basis']['status'] == 'supported' and base['sampling_basis']['degree'] == 1.0
    record = synthetic_record()
    record['facts']['shift_abolished_by_specific_competitor']['support'] = 'implied'            # a fact: supported with no degree before
    record['quantities']['replicate_count']['support'] = 'about_something_else'
    interpretations = convert(record)['extraction']['interpretations']
    assert interpretations['binding_controls']['status'] == 'supported' and interpretations['binding_controls']['degree'] == pytest.approx(min(base['binding_controls'].get('degree', 1.0), 0.7))
    assert interpretations['sampling_basis']['status'] == 'supported' and interpretations['sampling_basis']['degree'] == pytest.approx(0.3)
    assert interpretations['binding_regime'] == base['binding_regime'] and interpretations['calibration_applicability'] == base['calibration_applicability']
    record['facts']['shift_abolished_by_specific_competitor'] = fact('no', ['s'], 'about_something_else')      # a status is never changed by support: conflicting keeps no degree
    verdict = convert(record)['extraction']['interpretations']['binding_controls']
    assert verdict['status'] == 'conflicting' and 'degree' not in verdict
    record = synthetic_record()
    record['quantities']['kd_spread']['support'] = 'implied'
    assert convert(record)['extraction']['interpretations']['variance_correspondence']['degree'] == pytest.approx(0.7)
    record = synthetic_record()
    record['choice_support']['fit_model'] = 'implied'
    assert convert(record)['extraction']['interpretations']['binding_parameter_definition']['degree'] == pytest.approx(0.7)


def test_the_qualitative_effect_is_not_touched_by_support():
    record = qualitative_record()
    record['facts']['shift_detected']['support'] = 'about_something_else'
    effect = convert(record)['qualitative_effect']
    assert effect['statement'] == 'interaction_detected' and effect['support_refs']


def test_a_competitor_is_judged_against_the_protein_of_the_competition_reactions_when_it_is_stated():
    # probe 0.5 nM; the competitor is excess x 0.5 nM; the protein of the competition reactions is 100 nM, so the competitor over the protein is excess / 200
    # (the fixed 50 fold of the probe would call 100 fold conflicting; against 100 nM of protein it is only 0.5 times the protein: not a test of specificity)
    for excess, expected in ((100.0, 'unknown'), (900.0, 'unknown'), (1000.0, 'conflicting'), (4000.0, 'conflicting')):
        record = synthetic_record()
        record['quantities']['specific_competitor_excess'] = point(excess, 'ratio', 'x', ['s'])
        record['quantities']['competition_protein_concentration'] = point(0.1, 'uM', 'p', ['sp'])
        record['facts']['shift_abolished_by_specific_competitor'] = fact('no', ['s'])
        verdict = _criterion(grade_emsa(record), 'specific_competition')
        assert verdict['status'] == expected and 'degree' not in verdict, excess
        assert verdict['support_refs'] == ([] if expected == 'unknown' else ['s', 'sp'])
    # a small protein concentration makes the same 100 fold a fair test; with no protein concentration the fixed excess is used
    record = synthetic_record()
    record['facts']['shift_abolished_by_specific_competitor'] = fact('no', ['s'])
    record['quantities']['competition_protein_concentration'] = point(5.0, 'nM', 'p', ['sp'])
    assert _criterion(grade_emsa(record), 'specific_competition')['status'] == 'conflicting'
    missing(record, 'competition_protein_concentration')
    assert _criterion(grade_emsa(record), 'specific_competition')['status'] == 'conflicting'      # 100 fold, no protein: the fixed excess
    record['quantities']['specific_competitor_excess'] = point(10.0, 'ratio', 'x', ['s'])
    assert _criterion(grade_emsa(record), 'specific_competition')['status'] == 'unknown'


def test_the_competitor_over_the_protein_never_gets_less_conflicting_as_the_excess_grows():
    order = {'unknown': 0, 'conflicting': 1}
    last = 0
    for excess in (1.0, 10.0, 100.0, 500.0, 1000.0, 5000.0):
        record = synthetic_record()
        record['quantities']['specific_competitor_excess'] = point(excess, 'ratio', 'x', ['s'])
        record['quantities']['competition_protein_concentration'] = point(100.0, 'nM', 'p', ['sp'])
        record['facts']['shift_abolished_by_specific_competitor'] = fact('no', ['s'])
        now = order[_criterion(grade_emsa(record), 'specific_competition')['status']]
        assert now >= last
        last = now


def test_saturation_is_read_against_the_fitted_plateau_when_it_is_stated():
    # 70 percent shifted at the top is a partial plateau against 100 percent of the probe (degree 0.67) but a full one when the fitted plateau is 80 percent
    # (the inactive part of the probe caps the shift): 70 / 80 = 87.5 percent of the plateau
    record = synthetic_record()
    record['quantities']['fraction_shifted_highest'] = point(70.0, 'percent', 'f', ['s'])
    assert _criterion(grade_emsa(record), 'saturation')['degree'] == pytest.approx(2 / 3)
    record['quantities']['plateau_shifted_fraction'] = point(80.0, 'percent', 'pl', ['spl'])
    verdict = _criterion(grade_emsa(record), 'saturation')
    assert verdict['status'] == 'supported' and verdict['degree'] == 1.0 and verdict['support_refs'] == ['s', 'spl']
    # monotone in the shifted fraction and bounded; a plateau below the shifted fraction is capped at full agreement; a low shift of a high plateau is still weak
    last = -1.0
    for percent in (30.0, 40.0, 50.0, 60.0, 64.0, 70.0, 80.0, 95.0):
        record['quantities']['fraction_shifted_highest'] = point(percent, 'percent', 'f', ['s'])
        verdict = _criterion(grade_emsa(record), 'saturation')
        degree = verdict['degree'] if verdict['status'] == 'supported' else 0.0
        assert 0.0 <= degree <= 1.0 and degree >= last
        last = degree
    record['quantities']['plateau_shifted_fraction'] = point(95.0, 'percent', 'pl', ['spl'])
    record['quantities']['fraction_shifted_highest'] = point(40.0, 'percent', 'f', ['s'])
    assert _criterion(grade_emsa(record), 'saturation')['status'] == 'conflicting'      # 42 percent of the plateau
    record['quantities']['fraction_shifted_highest'] = point(60.0, 'percent', 'f', ['s'])
    verdict = _criterion(grade_emsa(record), 'saturation')
    assert verdict['status'] == 'supported' and 0.0 < verdict['degree'] < 1.0      # 63 percent of the plateau: partial, not a step
    missing(record, 'fraction_shifted_highest')
    assert _criterion(grade_emsa(record), 'saturation')['status'] == 'unknown'      # a plateau alone does not say how far the titration reached
