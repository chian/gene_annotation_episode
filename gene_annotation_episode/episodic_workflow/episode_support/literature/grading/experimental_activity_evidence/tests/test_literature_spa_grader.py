"""SPA grader: each criterion's rule on records, with the arithmetic worked by hand."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spa_record import fact, point, unavailable
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_criteria import SPA_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_grader import CRITERIA, grade_spa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spa_cases import real_record, sparse_record, synthetic_record


def status(record, criterion):
    """The status of the criterion after the sheet side has judged the facts the grader recorded (the grader holds no threshold; the sheet-side constants are in the converter)."""
    return _criterion(grade_spa(record), criterion)['status']


def grader_status(record, criterion):
    return grade_spa(record)['criteria'][criterion]['status']


def reason(record, criterion):
    return grade_spa(record)['reasons'][criterion]


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_complete_synthetic_record_is_supported_everywhere_once_the_sheet_has_judged_the_recorded_numbers():
    graded = grade_spa(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA and len(CRITERIA) == 18
    handed = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed == {'ligand_depletion', 'nonspecific_fraction', 'nonspecific_excess', 'bead_only_control', 'radioligand_range', 'competition_radioligand_level', 'hill_slope', 'cheng_prusoff', 'replicates'}      # the equilibrium is stated by its fact
    assert all(graded['criteria'][name]['status'] == 'unknown' and graded['criteria'][name]['support_refs'] == [] for name in handed)
    assert {_criterion(graded, name)['status'] for name in CRITERIA} == {'supported'}
    assert all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['percent_bound'] == 6.0 and native['bead_only_percent'] == 8.0 and native['hill_slope'] == 1.0 and native['replicate_count'] == 3 and native['replicate_independent'] == 'yes'
    assert native['kd_nM'] == 2.0 and native['ki_nM'] == 5.0 and native['ic50_nM'] == 7.5 and graded['experiment_type'] == 'spa'
    assert native['constant_name'] == 'kd' and native['constant_nM'] == 2.0 and native['incubation_min'] == 120.0 and native['settling_min'] == 30.0
    assert native['concentration_count'] == 10 and native['concentration_low_over_kd'] == pytest.approx(0.05) and native['concentration_high_over_kd'] == pytest.approx(25.6)
    assert native['radioligand_over_kd'] == pytest.approx(0.5) and native['nonspecific_excess_ratio'] == 500.0
    assert native['calculated_ki_nM'] == pytest.approx(5.0) and native['ki_over_calculated'] == pytest.approx(1.0)      # 7.5 / (1 + 1 / 2)
    assert native['assay_format'] == 'saturation' and native['radioligand_isotope'] == 'tritium' and native['bead_type'] == 'ysi' and native['capture_method'] == 'metal_chelate'
    assert native['preparation_type'] == 'purified_protein' and native['counter'] == 'microbeta'


def test_an_spa_has_no_filter_and_no_wash_criterion():
    assert not {'filter_binding', 'wash_dissociation'} & set(CRITERIA)
    assert {'homogeneous_format', 'nonproximity_signal', 'bead_only_control', 'quench_interference', 'bead_settling'} <= set(CRITERIA)


def test_sparse_record_is_unknown_or_not_applicable_never_conflicting_and_never_supported():
    graded = grade_spa(sparse_record())
    assert {c['status'] for c in graded['criteria'].values()} <= {'unknown', 'not_applicable'}
    assert graded['native']['kd_nM'] == 2.0 and graded['criteria']['ligand_depletion']['status'] == 'unknown'


FACTS_WITH_A_NO = ('homogeneous_no_wash_format', 'nonspecific_binding_determined', 'nonproximity_signal_checked', 'bead_only_control_done', 'equilibrium_reached', 'ligand_depletion_checked', 'quench_interference_checked', 'bead_settling_controlled', 'radioligand_purity_checked', 'nonlinear_fit_used', 'cheng_prusoff_applied_with_own_kd', 'independent_experiments')


# A supported or a conflicting criterion rests on quoted spans: the ELISA lesson (the sheet refuses an interpretation without support).
def variants():
    out = [synthetic_record(), sparse_record(), real_record()]
    for name in FACTS_WITH_A_NO:
        for answer in ('no', 'unknown', 'not_applicable'):
            record = synthetic_record()
            record['facts'][name] = fact(answer, ['s'] if answer == 'no' else [])
            if name == 'ligand_depletion_checked':
                missing(record, 'percent_bound')
            if name == 'bead_only_control_done':
                missing(record, 'bead_only_fraction')
            if name == 'cheng_prusoff_applied_with_own_kd':
                missing(record, 'ic50')
            out.append(record)
    for name, quantity in (('ligand_depletion_checked', 'percent_bound'), ('bead_only_control_done', 'bead_only_fraction'), ('cheng_prusoff_applied_with_own_kd', 'ic50')):
        record = synthetic_record()                                # a fact answered yes with the numbers missing
        record['facts'][name] = fact('yes', ['s'])
        missing(record, quantity)
        out.append(record)
    for model, form in (('competitive_binding', 'saturation'), ('competitive_binding', 'competition'), ('one_site', 'competition'), ('two_site', 'saturation'), ('hill', None), ('other', None), (None, None)):
        record = synthetic_record()
        record['fit_model'], record['assay_format'] = model, form
        out.append(record)
    record = synthetic_record()                                    # a model stated while no constant is reported
    record['fit_model'], record['assay_format'] = 'competitive_binding', 'saturation'
    for constant in ('kd', 'bmax', 'ki', 'ic50'):
        missing(record, constant)
    out.append(record)
    for quantity, fact_name, values in (('percent_bound', 'ligand_depletion_checked', (10.0, 10.1, None)), ('bead_only_fraction', 'bead_only_control_done', (20.0, 20.1, None))):
        for percent in values:
            record = synthetic_record()
            record['facts'][fact_name] = fact('unknown')
            if percent is None:
                missing(record, quantity)
            else:
                record['quantities'][quantity] = point(percent, 'percent', 'p', ['s'])
            out.append(record)
    for fraction in (50.0, 50.5, None):
        record = synthetic_record()
        if fraction is None:
            missing(record, 'nonspecific_fraction')
        else:
            record['quantities']['nonspecific_fraction'] = point(fraction, 'percent', 'f', ['s'])
        out.append(record)
    for fold, ligand in ((99.0, None), (100.0, None), (None, 100.0), (None, 400.0), (None, None)):
        record = synthetic_record()
        for name, value, unit in (('nonspecific_excess', fold, 'ratio'), ('nonspecific_ligand_concentration', ligand, 'nM')):
            if value is None:
                missing(record, name)
            else:
                record['quantities'][name] = point(value, unit, name, ['s'])
        out.append(record)
    record = synthetic_record()
    missing(record, 'nonspecific_excess')
    missing(record, 'kd')
    out.append(record)
    for minutes in (10.0, 30.0):
        record = synthetic_record()
        record['facts']['equilibrium_reached'] = fact('unknown')
        record['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        out.append(record)
    for level in (2.0, 2.2, None):             # against the KD of 2 nM: exactly the KD, just above it, not given
        record = synthetic_record()
        if level is None:
            missing(record, 'radioligand_concentration')
        else:
            record['quantities']['radioligand_concentration'] = point(level, 'nM', 'l', ['s'])
        out.append(record)
    for slope in (0.8, 0.79, 1.2, 1.21, None):
        record = synthetic_record()
        if slope is None:
            missing(record, 'hill_slope')
        else:
            record['quantities']['hill_slope'] = point(slope, 'ratio', 'h', ['s'])
        out.append(record)
    for ki, ic50, level, kd in ((7.5, 7.5, 1.0, 2.0), (7.5, 7.5, 1.0, 2.0), (3.34, 7.5, 1.0, 2.0), (7.51, 7.5, 1.0, 2.0)):
        record = synthetic_record()
        record['quantities']['ki'] = point(ki, 'nM', 'k', ['s'])
        record['quantities']['ic50'] = point(ic50, 'nM', 'c', ['s'])
        record['quantities']['radioligand_concentration'] = point(level, 'nM', 'l', ['s'])
        record['quantities']['kd'] = point(kd, 'nM', 'd', ['s'])
        out.append(record)
    record = synthetic_record()                                    # a saturation experiment with no competition constant
    record['facts']['cheng_prusoff_applied_with_own_kd'] = fact('unknown')
    for name in ('ki', 'ic50'):
        missing(record, name)
    out.append(record)
    for count, independent in ((2, 'yes'), (3, 'no'), (None, 'yes'), (3, 'unknown')):
        record = synthetic_record()
        record['facts']['independent_experiments'] = fact(independent, ['s'] if independent != 'unknown' else [])
        if count is None:
            missing(record, 'replicate_count')
        else:
            record['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        out.append(record)
    for series, low, high in (([0.1, 0.2], None, None), ([0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0], None, None), ([0.51, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0], None, None), ([0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 9.9], None, None), (None, 0.5, 10.0), (None, 0.6, 10.0), (None, 0.5, 9.0), (None, None, None)):
        record = synthetic_record()
        if series is None:
            record['concentration_series'] = {**record['concentration_series'], 'status': 'unavailable', 'value': None}
            record['quantities']['titration_point_count'] = point(8, 'count', 'n', ['s'])
            for name, value in (('radioligand_range_lowest', low), ('radioligand_range_highest', high)):
                if value is None:
                    missing(record, name)
                else:
                    record['quantities'][name] = point(value, 'nM', name, ['s'])
        else:
            record['concentration_series']['value'] = series
        out.append(record)
    return out


def test_every_supported_or_conflicting_criterion_carries_support_refs():
    seen = set()
    for record in variants():
        graded = grade_spa(record)
        for name, outcome in graded['criteria'].items():
            if outcome['status'] in ('supported', 'conflicting'):
                seen.add((name, outcome['status'], graded['reasons'][name]))
                assert outcome['support_refs'], (record['experiment_ref'], name, graded['reasons'][name])
            else:
                assert outcome['support_refs'] == []
    # every supported or conflicting case the criteria declare was reached by some variant, and so was checked for its refs
    declared = {(criterion['id'], status, why) for criterion in SPA_CRITERIA for status, why, _ in criterion['returns'] if status in ('supported', 'conflicting')}
    assert seen == declared


def test_a_decided_criterion_cannot_be_built_without_support_refs():
    record = synthetic_record()
    record['facts']['radioligand_purity_checked'] = fact('yes')           # a fact answered yes with no span: it cannot be supported
    with pytest.raises(ValueError, match='needs support refs'):
        grade_spa(record)


def test_the_bound_fraction_is_recorded_for_the_sheet_else_the_fact_decides():
    r = synthetic_record()
    r['quantities']['percent_bound'] = point(10.0, 'percent', 'p', ['s'])
    graded = grade_spa(r)
    assert (graded['criteria']['ligand_depletion'], graded['reasons']['ligand_depletion']) == ({'status': 'unknown', 'support_refs': []}, 'percent_bound_recorded_for_the_sheet')
    assert graded['native']['percent_bound'] == 10.0 and graded['native']['percent_bound_refs'] == ['s']
    assert status(r, 'ligand_depletion') == 'supported'                                 # the sheet's judgement at its limit
    r['quantities']['percent_bound'] = point(40.0, 'percent', 'p', ['s'])
    assert status(r, 'ligand_depletion') == 'conflicting'
    r['facts']['ligand_depletion_checked'] = fact('yes', ['s'])                         # a stated percent outranks the fact
    assert status(r, 'ligand_depletion') == 'conflicting'
    missing(r, 'percent_bound')
    assert (status(r, 'ligand_depletion'), reason(r, 'ligand_depletion')) == ('supported', 'facts_answered_yes')
    r['facts']['ligand_depletion_checked'] = fact('no', ['s'])
    assert (status(r, 'ligand_depletion'), reason(r, 'ligand_depletion')) == ('conflicting', 'fact_answered_no')
    r['facts']['ligand_depletion_checked'] = fact('unknown')
    assert (status(r, 'ligand_depletion'), reason(r, 'ligand_depletion')) == ('unknown', 'fact_unknown')


def test_the_signal_without_the_captured_target_is_recorded_for_the_sheet_else_the_fact_decides():
    r = synthetic_record()                                                              # 8 percent of the total signal
    assert (grader_status(r, 'bead_only_control'), reason(r, 'bead_only_control')) == ('unknown', 'bead_only_percent_recorded_for_the_sheet')
    assert grade_spa(r)['native']['bead_only_percent'] == 8.0 and grade_spa(r)['native']['bead_only_refs'] == ['span_exp_synthetic_spa_1']
    assert status(r, 'bead_only_control') == 'supported'
    r['quantities']['bead_only_fraction'] = point(60.0, 'percent', 'b', ['s'])
    assert status(r, 'bead_only_control') == 'conflicting'
    r['facts']['bead_only_control_done'] = fact('yes', ['s'])                           # a stated percent outranks the fact
    assert status(r, 'bead_only_control') == 'conflicting'
    missing(r, 'bead_only_fraction')
    assert (status(r, 'bead_only_control'), reason(r, 'bead_only_control')) == ('supported', 'facts_answered_yes')
    r['facts']['bead_only_control_done'] = fact('no', ['s'])
    assert (status(r, 'bead_only_control'), reason(r, 'bead_only_control')) == ('conflicting', 'fact_answered_no')
    r['facts']['bead_only_control_done'] = fact('unknown')
    assert (status(r, 'bead_only_control'), reason(r, 'bead_only_control')) == ('unknown', 'fact_unknown')


def test_the_nonspecific_fraction_is_recorded_for_the_sheet():
    r = synthetic_record()
    r['quantities']['nonspecific_fraction'] = point(50.0, 'percent', 'f', ['s'])
    assert (grader_status(r, 'nonspecific_fraction'), reason(r, 'nonspecific_fraction')) == ('unknown', 'nonspecific_fraction_recorded_for_the_sheet')
    assert grade_spa(r)['native']['nonspecific_fraction_percent'] == 50.0 and grade_spa(r)['native']['nonspecific_fraction_refs'] == ['s']
    assert status(r, 'nonspecific_fraction') == 'supported'
    r['quantities']['nonspecific_fraction'] = point(90.0, 'percent', 'f', ['s'])
    assert status(r, 'nonspecific_fraction') == 'conflicting'
    missing(r, 'nonspecific_fraction')
    assert (status(r, 'nonspecific_fraction'), reason(r, 'nonspecific_fraction')) == ('unknown', 'nonspecific_fraction_not_given')


@pytest.mark.parametrize('criterion, name', [('nonspecific_binding', 'nonspecific_binding_determined'), ('nonproximity_signal', 'nonproximity_signal_checked'), ('homogeneous_format', 'homogeneous_no_wash_format'), ('radioligand_quality', 'radioligand_purity_checked'), ('quench_interference', 'quench_interference_checked'), ('bead_settling', 'bead_settling_controlled'), ('nonlinear_fit', 'nonlinear_fit_used')])
def test_a_one_fact_criterion_follows_its_fact(criterion, name):
    r = synthetic_record()
    assert (status(r, criterion), reason(r, criterion)) == ('supported', 'facts_answered_yes')
    r['facts'][name] = fact('no', ['s'])
    assert (status(r, criterion), reason(r, criterion)) == ('conflicting', 'fact_answered_no')
    r['facts'][name] = fact('unknown')
    assert (status(r, criterion), reason(r, criterion)) == ('unknown', 'fact_unknown')
    r['facts'][name] = fact('not_applicable')
    assert (status(r, criterion), reason(r, criterion)) == ('not_applicable', 'fact_not_applicable')


def test_the_nonspecific_excess_is_the_stated_fold_else_the_concentration_over_the_kd():
    r = synthetic_record()                                                                 # stated 500 fold; 1000 nM over the KD 2 nM = 500
    assert reason(r, 'nonspecific_excess') == 'excess_recorded_for_the_sheet' and status(r, 'nonspecific_excess') == 'supported'
    r['quantities']['nonspecific_excess'] = point(100.0, 'ratio', 'e', ['s'])              # exactly the sheet's minimum, allowed
    assert grade_spa(r)['native']['nonspecific_excess_ratio'] == 100.0 and grade_spa(r)['native']['nonspecific_excess_refs'] == ['s'] and status(r, 'nonspecific_excess') == 'supported'
    r['quantities']['nonspecific_excess'] = point(5.0, 'ratio', 'e', ['s'])
    assert status(r, 'nonspecific_excess') == 'conflicting'
    missing(r, 'nonspecific_excess')                                                       # 1000 nM / 2 nM = 500
    assert grade_spa(r)['native']['nonspecific_excess_ratio'] == 500.0 and status(r, 'nonspecific_excess') == 'supported'
    r['quantities']['nonspecific_ligand_concentration'] = point(0.4, 'uM', 'c', ['s'])     # 400 nM / 2 nM = 200
    assert grade_spa(r)['native']['nonspecific_excess_ratio'] == 200.0 and status(r, 'nonspecific_excess') == 'supported'
    r['quantities']['nonspecific_ligand_concentration'] = point(0.01, 'uM', 'c', ['s'])    # 10 nM / 2 nM = 5
    assert grade_spa(r)['native']['nonspecific_excess_ratio'] == 5.0 and status(r, 'nonspecific_excess') == 'conflicting'
    missing(r, 'kd')
    assert (status(r, 'nonspecific_excess'), reason(r, 'nonspecific_excess')) == ('unknown', 'excess_not_given')


def test_the_equilibrium_fact_then_a_short_incubation():
    r = synthetic_record()
    r['facts']['equilibrium_reached'] = fact('unknown')
    assert reason(r, 'equilibrium') == 'incubation_recorded_for_the_sheet' and grade_spa(r)['native']['incubation_min'] == 120.0 and grade_spa(r)['native']['incubation_refs'] == ['span_exp_synthetic_spa_1']
    assert grader_status(r, 'equilibrium') == 'unknown' and status(r, 'equilibrium') == 'unknown'      # a 120 min incubation is not short
    r['quantities']['incubation_time'] = point(29.0, 'min', 'i', ['s'])
    assert grader_status(r, 'equilibrium') == 'unknown' and status(r, 'equilibrium') == 'conflicting' and _criterion(grade_spa(r), 'equilibrium')['support_refs'] == ['s']
    r['quantities']['incubation_time'] = point(30.0, 'min', 'i', ['s'])                    # exactly the sheet's minimum
    assert status(r, 'equilibrium') == 'unknown'
    r['quantities']['incubation_time'] = point(0.4, 'h', 'i', ['s'])                       # 24 min
    assert status(r, 'equilibrium') == 'conflicting'
    missing(r, 'incubation_time')
    assert (grader_status(r, 'equilibrium'), reason(r, 'equilibrium')) == ('unknown', 'fact_unknown')
    r['quantities']['incubation_time'] = point(0.4, 'h', 'i', ['s'])
    r['quantities']['incubation_time'] = point(16.0, 'h', 'i', ['s'])                      # 960 min: long, so not conflicting, and not stated: unknown
    assert status(r, 'equilibrium') == 'unknown'
    r['facts']['equilibrium_reached'] = fact('yes', ['s'])                                 # the stated fact outranks the short time
    r['quantities']['incubation_time'] = point(0.4, 'h', 'i', ['s'])
    assert status(r, 'equilibrium') == 'supported'
    r['facts']['equilibrium_reached'] = fact('no', ['s'])
    assert reason(r, 'equilibrium') == 'fact_answered_no'


def test_the_series_must_have_enough_points_and_span_the_kd():
    r = synthetic_record()                                                                 # 10 points, 0.05 x to 25.6 x the KD of 2 nM
    graded = grade_spa(r)
    assert graded['reasons']['radioligand_range'] == 'concentration_series_recorded_for_the_sheet' and graded['criteria']['radioligand_range'] == {'status': 'unknown', 'support_refs': []}
    assert graded['native']['concentration_count'] == 10 and graded['native']['concentration_count_refs'] == ['span_exp_synthetic_spa_1'] and graded['native']['concentration_span_refs'] == ['span_exp_synthetic_spa_1']
    assert status(r, 'radioligand_range') == 'supported'
    r['concentration_series']['value'] = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0]      # 8 points: lowest 0.5 nM = 0.25 x the KD (the sheet's full-agreement limit), highest 32 x
    assert status(r, 'radioligand_range') == 'supported' and _criterion(grade_spa(r), 'radioligand_range')['degree'] == 1.0
    r['concentration_series']['value'] = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0]     # lowest 0.5 x the KD: partial (0.5 - 1.0 on the way to the zero limit of 1.0)
    assert grade_spa(r)['native']['concentration_low_over_kd'] == 0.5 and _criterion(grade_spa(r), 'radioligand_range')['degree'] == pytest.approx((1.0 - 0.5) / (1.0 - 0.25))
    r['concentration_series']['value'] = [2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0]    # lowest at the KD: conflicting
    assert status(r, 'radioligand_range') == 'conflicting'
    r['concentration_series']['value'] = [0.5, 1.0, 2.0, 4.0, 8.0, 9.0, 9.5, 10.0]         # highest 10 nM = 5 x the KD (full agreement)
    assert status(r, 'radioligand_range') == 'supported' and _criterion(grade_spa(r), 'radioligand_range')['degree'] == 1.0
    r['concentration_series']['value'] = [0.5, 1.0, 2.0, 2.5, 3.0, 3.5, 3.8, 4.0]          # highest 2 x the KD: partial, 0.25
    assert grade_spa(r)['native']['concentration_high_over_kd'] == 2.0 and _criterion(grade_spa(r), 'radioligand_range')['degree'] == pytest.approx(0.25)
    r['concentration_series']['value'] = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.5, 2.0]          # highest at the KD: conflicting
    assert status(r, 'radioligand_range') == 'conflicting'
    r['concentration_series']['value'] = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0]             # 7 points: below the sheet's count minimum
    assert status(r, 'radioligand_range') == 'conflicting' and _criterion(grade_spa(r), 'radioligand_range')['support_refs'] == ['span_exp_synthetic_spa_1'] and 'degree' not in _criterion(grade_spa(r), 'radioligand_range')
    r['concentration_series'] = {**r['concentration_series'], 'status': 'unavailable', 'value': None}
    assert status(r, 'radioligand_range') == 'supported'                                   # 10 stated points are enough, the stated lowest 0.1 nM and highest 51.2 nM span
    r['quantities']['titration_point_count'] = point(6, 'count', 'n', ['s'])
    assert status(r, 'radioligand_range') == 'conflicting' and grade_spa(r)['native']['concentration_count'] == 6
    r['quantities']['titration_point_count'] = point(10, 'count', 'n', ['s'])
    r['quantities']['radioligand_range_highest'] = point(9.0, 'nM', 'h', ['s'])            # 4.5 x: a degree just below 1
    assert status(r, 'radioligand_range') == 'supported' and _criterion(grade_spa(r), 'radioligand_range')['degree'] == pytest.approx((4.5 - 1.0) / (5.0 - 1.0))
    missing(r, 'radioligand_range_highest')                                                # the count is recorded but the span cannot be read
    assert (grader_status(r, 'radioligand_range'), reason(r, 'radioligand_range')) == ('unknown', 'concentration_series_recorded_for_the_sheet') and status(r, 'radioligand_range') == 'unknown'
    missing(r, 'titration_point_count')
    assert reason(r, 'radioligand_range') == 'kd_or_series_missing' and status(r, 'radioligand_range') == 'unknown'


def test_the_competition_radioligand_concentration_over_the_kd_is_recorded_for_the_sheet():
    r = synthetic_record()                                                                 # 1 nM over the KD of 2 nM = 0.5
    assert (grader_status(r, 'competition_radioligand_level'), reason(r, 'competition_radioligand_level')) == ('unknown', 'radioligand_over_kd_recorded_for_the_sheet')
    assert grade_spa(r)['native']['radioligand_over_kd'] == 0.5 and len(grade_spa(r)['native']['radioligand_over_kd_refs']) == 1
    assert status(r, 'competition_radioligand_level') == 'supported'
    r['quantities']['radioligand_concentration'] = point(2.0, 'nM', 'l', ['s'])            # exactly the KD, the sheet's full-agreement limit
    assert status(r, 'competition_radioligand_level') == 'supported' and _criterion(grade_spa(r), 'competition_radioligand_level')['degree'] == 1.0
    r['quantities']['radioligand_concentration'] = point(11.0, 'nM', 'l', ['s'])           # 5.5 x the KD: halfway to the zero limit of 10 x
    assert _criterion(grade_spa(r), 'competition_radioligand_level')['degree'] == pytest.approx(0.5)
    r['quantities']['radioligand_concentration'] = point(2.0, 'uM', 'l', ['s'])            # 1000 x
    assert status(r, 'competition_radioligand_level') == 'conflicting' and 'degree' not in _criterion(grade_spa(r), 'competition_radioligand_level')
    missing(r, 'kd')
    assert (status(r, 'competition_radioligand_level'), reason(r, 'competition_radioligand_level')) == ('unknown', 'radioligand_concentration_or_kd_not_given')


def test_the_fit_model_must_be_stated_and_fit_the_format_and_a_constant_must_support_it():
    r = synthetic_record()
    assert (status(r, 'fit_model'), reason(r, 'fit_model')) == ('supported', 'model_stated')
    r['fit_model'] = 'competitive_binding'
    assert reason(r, 'fit_model') == 'competition_model_for_saturation' and status(r, 'fit_model') == 'conflicting'
    r['assay_format'] = 'competition'
    assert status(r, 'fit_model') == 'supported'
    r['fit_model'] = 'one_site'                                                            # a one-site model is also the usual competition model
    assert status(r, 'fit_model') == 'supported'
    r['assay_format'] = None
    r['fit_model'] = 'competitive_binding'
    assert status(r, 'fit_model') == 'supported'
    r['fit_model'] = None
    assert reason(r, 'fit_model') == 'fit_model_not_stated' and status(r, 'fit_model') == 'unknown'
    for model, form in (('one_site', 'saturation'), ('competitive_binding', 'saturation'), ('two_site', 'competition')):
        r['fit_model'], r['assay_format'] = model, form
        for name in ('kd', 'bmax', 'ki', 'ic50'):
            r['quantities'][name] = unavailable('nM', name, 'not_given_in_the_inspected_source_text')   # no reported constant: no span supports the model
        assert reason(r, 'fit_model') == 'model_stated_without_a_reported_constant' and status(r, 'fit_model') == 'unknown'


def test_the_hill_slope_must_be_near_one():
    r = synthetic_record()
    assert (grader_status(r, 'hill_slope'), reason(r, 'hill_slope')) == ('unknown', 'hill_slope_recorded_for_the_sheet') and grade_spa(r)['native']['hill_slope'] == 1.0
    for slope, expected, degree in ((1.0, 'supported', 1.0), (0.8, 'supported', 1.0), (1.2, 'supported', 1.0), (0.65, 'supported', 0.5), (1.6, 'supported', 0.5), (0.5, 'conflicting', None), (2.0, 'conflicting', None), (0.3, 'conflicting', None)):
        r['quantities']['hill_slope'] = point(slope, 'ratio', 'h', ['s'])
        assert status(r, 'hill_slope') == expected, slope
        assert _criterion(grade_spa(r), 'hill_slope').get('degree') == (pytest.approx(degree) if degree is not None else None), slope
    assert _criterion(grade_spa(r), 'hill_slope')['support_refs'] == ['s']
    missing(r, 'hill_slope')
    assert (status(r, 'hill_slope'), reason(r, 'hill_slope')) == ('unknown', 'hill_slope_not_given')


def test_the_cheng_prusoff_ki_must_agree_with_the_ic50_the_radioligand_concentration_and_the_kd():
    r = synthetic_record()                                                                 # Ki 5 nM; 7.5 / (1 + 1 / 2) = 5
    assert (grader_status(r, 'cheng_prusoff'), reason(r, 'cheng_prusoff')) == ('unknown', 'cheng_prusoff_gap_recorded_for_the_sheet')
    native = grade_spa(r)['native']
    assert native['ki_nM'] == 5.0 and native['calculated_ki_nM'] == pytest.approx(5.0) and native['ki_over_calculated'] == pytest.approx(1.0) and len(native['cheng_prusoff_refs']) == 1
    assert status(r, 'cheng_prusoff') == 'supported'
    r['quantities']['ki'] = point(7.5, 'nM', 'k', ['s'])                                   # 7.5 / 5 = 1.5 exactly the sheet's full-agreement fold
    assert status(r, 'cheng_prusoff') == 'supported' and _criterion(grade_spa(r), 'cheng_prusoff')['degree'] == 1.0
    r['quantities']['ki'] = point(12.5, 'nM', 'k', ['s'])                                  # 2.5 fold: (5 - 2.5) / (5 - 1.5)
    assert _criterion(grade_spa(r), 'cheng_prusoff')['degree'] == pytest.approx(2.5 / 3.5) and 's' in _criterion(grade_spa(r), 'cheng_prusoff')['support_refs']
    r['quantities']['ki'] = point(25.0, 'nM', 'k', ['s'])                                  # fivefold: the zero-agreement limit
    assert status(r, 'cheng_prusoff') == 'conflicting' and 'degree' not in _criterion(grade_spa(r), 'cheng_prusoff')
    r['quantities']['ki'] = point(1.0, 'nM', 'k', ['s'])                                   # 5 / 1 = fivefold the other way
    assert status(r, 'cheng_prusoff') == 'conflicting'
    r['quantities']['ki'] = point(2.0, 'nM', 'k', ['s'])                                   # 2.5 fold the other way
    assert _criterion(grade_spa(r), 'cheng_prusoff')['degree'] == pytest.approx(2.5 / 3.5)
    r['quantities']['ki'] = point(5.0, 'nM', 'k', ['s'])
    r['quantities']['ic50'] = point(0.0075, 'uM', 'c', ['s'])                              # 7.5 nM: the same
    assert status(r, 'cheng_prusoff') == 'supported'
    r['facts']['cheng_prusoff_applied_with_own_kd'] = fact('no', ['s'])                    # a stated no fails, even when the numbers agree
    assert (status(r, 'cheng_prusoff'), reason(r, 'cheng_prusoff')) == ('conflicting', 'fact_answered_no') and grader_status(r, 'cheng_prusoff') == 'conflicting'
    r['facts']['cheng_prusoff_applied_with_own_kd'] = fact('yes', ['s'])
    r['quantities']['ki'] = point(40.0, 'nM', 'k', ['s'])                                  # stated yes, but the numbers do not agree (eightfold)
    assert reason(r, 'cheng_prusoff') == 'cheng_prusoff_gap_recorded_for_the_sheet' and status(r, 'cheng_prusoff') == 'conflicting'
    missing(r, 'ic50')                                                                     # not all four: the fact decides
    assert (status(r, 'cheng_prusoff'), reason(r, 'cheng_prusoff')) == ('supported', 'facts_answered_yes')
    r['facts']['cheng_prusoff_applied_with_own_kd'] = fact('unknown')
    assert (status(r, 'cheng_prusoff'), reason(r, 'cheng_prusoff')) == ('unknown', 'fact_unknown')
    missing(r, 'ki')                                                                       # a saturation experiment with no competition constant
    assert (status(r, 'cheng_prusoff'), reason(r, 'cheng_prusoff')) == ('not_applicable', 'no_competition_constant')
    r['assay_format'] = None                                                               # the format is not stated: unknown, not applicable
    assert status(r, 'cheng_prusoff') == 'unknown'


def test_replicates_are_independent_experiments_and_wells_do_not_count():
    r = synthetic_record()
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('unknown', 'replicate_count_recorded_for_the_sheet')
    assert grade_spa(r)['native']['replicate_count'] == 3 and grade_spa(r)['native']['replicate_independent'] == 'yes' and status(r, 'replicates') == 'supported'
    for count, independent, expected in ((3, 'yes', 'supported'), (10, 'yes', 'supported'), (2, 'yes', 'conflicting'), (2, 'unknown', 'conflicting'), (3, 'unknown', 'unknown')):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_experiments'] = fact(independent, ['s'] if independent != 'unknown' else [])
        assert status(r, 'replicates') == expected, (count, independent)
        assert 'degree' not in _criterion(grade_spa(r), 'replicates')
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    r['facts']['independent_experiments'] = fact('no', ['s'])
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('conflicting', 'replicates_not_independent')       # a fact, judged by the grader
    r['facts']['independent_experiments'] = fact('unknown')
    assert reason(r, 'replicates') == 'replicate_count_recorded_for_the_sheet' and status(r, 'replicates') == 'unknown'      # a count of 3, independence unknown: the sheet cannot support it
    r['facts']['independent_experiments'] = fact('yes', ['s'])
    missing(r, 'replicate_count')
    assert reason(r, 'replicates') == 'replicate_count_or_independence_unknown'
    r['quantities']['technical_replicate_count'] = point(4, 'count', 'w', ['s'])           # triplicate or quadruplicate wells do not make replicates
    assert status(r, 'replicates') == 'unknown'


def test_an_ic50_alone_is_not_a_binding_constant_but_is_kept_apart_from_the_kd():
    r = synthetic_record()
    for name in ('kd', 'ki'):
        missing(r, name)
    native = grade_spa(r)['native']
    assert native['kd_nM'] is None and native['ki_nM'] is None and native['ic50_nM'] == 7.5 and native['constant_name'] is None


def test_the_grader_keeps_the_support_of_the_fields_each_criterion_reads_and_does_not_judge_it():
    r = synthetic_record()
    r['facts']['quench_interference_checked']['support'] = 'implied'
    r['quantities']['replicate_count']['support'] = 'about_something_else'
    r['choice_support']['fit_model'] = 'implied'
    graded = grade_spa(r)
    support = graded['native']['support']
    assert set(support) == set(CRITERIA)
    assert support['quench_interference'] == ['implied'] and 'about_something_else' in support['replicates'] and 'implied' in support['fit_model']
    assert support['bead_settling'] == ['direct']
    assert graded['criteria']['quench_interference']['status'] == 'supported'      # the status is the grader's own: support does not change it
    assert grade_spa(sparse_record())['native']['support']['quench_interference'] == []      # an unknown fact is not stated: no support
