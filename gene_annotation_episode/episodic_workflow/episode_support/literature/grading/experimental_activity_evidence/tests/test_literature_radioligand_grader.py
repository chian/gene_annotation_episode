"""Radioligand grader: each criterion's rule on records, with the arithmetic worked by hand."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_radioligand_record import fact, point, unavailable
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_criteria import RADIOLIGAND_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_grader import CRITERIA, grade_radioligand
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.radioligand_cases import real_record, sparse_record, synthetic_record

HANDED = {'ligand_depletion', 'nonspecific_fraction', 'nonspecific_excess', 'radioligand_range', 'competition_radioligand_level', 'hill_slope', 'cheng_prusoff', 'replicates'}      # the equilibrium is ruled by its fact in the synthetic record


def status(record, criterion):
    """The status after the sheet side has judged the facts the grader recorded (the grader holds no threshold; the sheet-side constants are in the converter)."""
    return _criterion(grade_radioligand(record), criterion)['status']


def grader_status(record, criterion):
    return grade_radioligand(record)['criteria'][criterion]['status']


def reason(record, criterion):
    return grade_radioligand(record)['reasons'][criterion]


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_complete_synthetic_record_is_supported_everywhere_once_the_sheet_has_judged_what_the_grader_recorded():
    graded = grade_radioligand(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA and len(CRITERIA) == 15
    handed = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed == HANDED
    assert all(graded['criteria'][name]['status'] == 'unknown' and graded['criteria'][name]['support_refs'] == [] for name in handed)
    assert {_criterion(graded, name)['status'] for name in CRITERIA} == {'supported'} and all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['kd_nM'] == 2.0 and native['ki_nM'] == 5.0 and native['ic50_nM'] == 7.5 and graded['experiment_type'] == 'radioligand'
    assert native['constant_name'] == 'kd' and native['constant_nM'] == 2.0 and native['incubation_min'] == 60.0
    assert native['concentration_count'] == 10 and native['concentration_low_over_kd'] == pytest.approx(0.05) and native['concentration_high_over_kd'] == pytest.approx(25.6)
    assert native['radioligand_over_kd'] == pytest.approx(0.5) and native['nonspecific_excess_ratio'] == 500.0
    assert native['calculated_ki_nM'] == pytest.approx(5.0) and native['ki_over_calculated'] == pytest.approx(1.0)      # 7.5 / (1 + 1 / 2)
    assert native['assay_format'] == 'saturation' and native['radioligand_isotope'] == 'tritium' and native['separation_method'] == 'filtration' and native['preparation_type'] == 'membrane'


def test_sparse_record_is_unknown_or_not_applicable_never_conflicting_and_never_supported():
    graded = grade_radioligand(sparse_record())
    assert {c['status'] for c in graded['criteria'].values()} <= {'unknown', 'not_applicable'}
    assert graded['native']['kd_nM'] == 2.0 and graded['criteria']['ligand_depletion']['status'] == 'unknown'


# A supported or a conflicting criterion rests on quoted spans: the ELISA lesson (the sheet refuses an interpretation without support).
def variants():
    out = [synthetic_record(), sparse_record(), real_record()]
    for name in ('ligand_depletion_checked', 'nonspecific_binding_determined', 'equilibrium_reached', 'radioligand_purity_checked', 'filter_binding_checked', 'wash_dissociation_considered', 'nonlinear_fit_used', 'cheng_prusoff_applied_with_own_kd', 'independent_experiments'):
        for answer in ('no', 'unknown', 'not_applicable'):
            record = synthetic_record()
            record['facts'][name] = fact(answer, ['s'] if answer == 'no' else [])
            if name == 'ligand_depletion_checked':
                missing(record, 'percent_bound')
            if name == 'cheng_prusoff_applied_with_own_kd':
                missing(record, 'ic50')
            out.append(record)
    record = synthetic_record()                                    # a fact answered yes with the numbers missing
    record['facts']['ligand_depletion_checked'] = fact('yes', ['s'])
    missing(record, 'percent_bound')
    out.append(record)
    record = synthetic_record()
    record['facts']['cheng_prusoff_applied_with_own_kd'] = fact('yes', ['s'])
    missing(record, 'ic50')
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
    for percent in (10.0, 10.1, None):
        record = synthetic_record()
        record['facts']['ligand_depletion_checked'] = fact('unknown')
        if percent is None:
            missing(record, 'percent_bound')
        else:
            record['quantities']['percent_bound'] = point(percent, 'percent', 'p', ['s'])
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
    for method in ('scintillation_proximity', 'centrifugation', 'filtration', None):
        for name in ('filter_binding_checked', 'wash_dissociation_considered'):
            record = synthetic_record()
            record['separation_method'] = method
            record['facts'][name] = fact('unknown')
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
        graded = grade_radioligand(record)
        for name, outcome in graded['criteria'].items():
            if outcome['status'] in ('supported', 'conflicting'):
                seen.add((name, outcome['status'], graded['reasons'][name]))
                assert outcome['support_refs'], (record['experiment_ref'], name, graded['reasons'][name])
            else:
                assert outcome['support_refs'] == []
    # every supported or conflicting case the criteria declare was reached by some variant, and so was checked for its refs
    declared = {(criterion['id'], status, why) for criterion in RADIOLIGAND_CRITERIA for status, why, _ in criterion['returns'] if status in ('supported', 'conflicting')}
    assert seen == declared


def sheet_variants():
    """The records of variants() and those that reach the zero-agreement limits, for the sheet's judgement of what the grader recorded."""
    out = variants()
    for name, value, unit in (('percent_bound', 50.0, 'percent'), ('nonspecific_fraction', 90.0, 'percent'), ('nonspecific_excess', 1.0, 'ratio'), ('radioligand_concentration', 20.0, 'nM'), ('hill_slope', 0.5, 'ratio'), ('hill_slope', 1.5, 'ratio'),
                              ('ki', 40.0, 'nM'), ('replicate_count', 2, 'count')):
        record = synthetic_record()
        record['quantities'][name] = point(value, unit, name, ['s'])
        out.append(record)
    record = synthetic_record()
    record['concentration_series']['value'] = [2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0]       # the lowest at the KD
    out.append(record)
    record = synthetic_record()
    record['concentration_series']['value'] = [0.1, 0.2, 0.4, 0.8, 1.0, 1.5, 1.8, 2.0]              # the highest at the KD
    out.append(record)
    return out


def test_every_criterion_the_sheet_decides_carries_support_refs_too():
    judged_cases = set()
    for record in sheet_variants():
        graded = grade_radioligand(record)
        for name in graded['criteria']:
            outcome = _criterion(graded, name)
            if outcome['status'] in ('supported', 'conflicting'):
                assert outcome['support_refs'], (record['experiment_ref'], name, graded['reasons'][name])
                if graded['reasons'][name].endswith('_recorded_for_the_sheet'):
                    judged_cases.add((name, outcome['status']))
            else:
                assert outcome['support_refs'] == []
    assert judged_cases >= {(name, state) for name in sorted(HANDED | {'equilibrium'}) for state in ('supported', 'conflicting')} - {('equilibrium', 'supported')}


def test_a_decided_criterion_cannot_be_built_without_support_refs():
    record = synthetic_record()
    record['facts']['radioligand_purity_checked'] = fact('yes')           # a fact answered yes with no span: it cannot be supported
    with pytest.raises(ValueError, match='needs support refs'):
        grade_radioligand(record)


def test_the_bound_fraction_is_at_most_ten_percent_else_the_fact_decides():
    r = synthetic_record()
    r['quantities']['percent_bound'] = point(10.0, 'percent', 'p', ['s'])               # exactly the limit, allowed, the full degree
    assert (grader_status(r, 'ligand_depletion'), reason(r, 'ligand_depletion')) == ('unknown', 'percent_bound_recorded_for_the_sheet')
    assert grade_radioligand(r)['native']['percent_bound'] == 10.0 and grade_radioligand(r)['native']['percent_bound_refs'] == ['s']
    assert _criterion(grade_radioligand(r), 'ligand_depletion') == {'status': 'supported', 'support_refs': ['s'], 'degree': 1.0}
    r['quantities']['percent_bound'] = point(30.0, 'percent', 'p', ['s'])               # halfway from 10 to 50: a degree of 0.5
    assert status(r, 'ligand_depletion') == 'supported' and _criterion(grade_radioligand(r), 'ligand_depletion')['degree'] == pytest.approx(0.5)
    r['quantities']['percent_bound'] = point(50.0, 'percent', 'p', ['s'])               # the zero-agreement limit
    assert status(r, 'ligand_depletion') == 'conflicting' and 'degree' not in _criterion(grade_radioligand(r), 'ligand_depletion')
    r['quantities']['percent_bound'] = point(60.0, 'percent', 'p', ['s'])
    r['facts']['ligand_depletion_checked'] = fact('yes', ['s'])                         # a stated percent outranks the fact
    assert status(r, 'ligand_depletion') == 'conflicting'
    missing(r, 'percent_bound')
    assert (status(r, 'ligand_depletion'), reason(r, 'ligand_depletion')) == ('supported', 'facts_answered_yes')
    r['facts']['ligand_depletion_checked'] = fact('no', ['s'])
    assert (status(r, 'ligand_depletion'), reason(r, 'ligand_depletion')) == ('conflicting', 'fact_answered_no')
    r['facts']['ligand_depletion_checked'] = fact('unknown')
    assert (status(r, 'ligand_depletion'), reason(r, 'ligand_depletion')) == ('unknown', 'fact_unknown')


def test_the_nonspecific_fraction_is_at_most_half_of_the_total_binding():
    r = synthetic_record()
    r['quantities']['nonspecific_fraction'] = point(50.0, 'percent', 'f', ['s'])         # exactly the limit, allowed, the full degree
    assert (grader_status(r, 'nonspecific_fraction'), reason(r, 'nonspecific_fraction')) == ('unknown', 'nonspecific_fraction_recorded_for_the_sheet')
    assert grade_radioligand(r)['native']['nonspecific_percent'] == 50.0 and grade_radioligand(r)['native']['nonspecific_fraction_refs'] == ['s']
    assert _criterion(grade_radioligand(r), 'nonspecific_fraction') == {'status': 'supported', 'support_refs': ['s'], 'degree': 1.0}
    r['quantities']['nonspecific_fraction'] = point(70.0, 'percent', 'f', ['s'])         # halfway from 50 to 90: a degree of 0.5
    assert status(r, 'nonspecific_fraction') == 'supported' and _criterion(grade_radioligand(r), 'nonspecific_fraction')['degree'] == pytest.approx(0.5)
    r['quantities']['nonspecific_fraction'] = point(90.0, 'percent', 'f', ['s'])         # the zero-agreement limit
    assert status(r, 'nonspecific_fraction') == 'conflicting' and 'degree' not in _criterion(grade_radioligand(r), 'nonspecific_fraction')
    missing(r, 'nonspecific_fraction')
    assert (status(r, 'nonspecific_fraction'), reason(r, 'nonspecific_fraction')) == ('unknown', 'nonspecific_fraction_not_given')


@pytest.mark.parametrize('criterion, name', [('nonspecific_binding', 'nonspecific_binding_determined'), ('radioligand_quality', 'radioligand_purity_checked'), ('nonlinear_fit', 'nonlinear_fit_used')])
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
    assert (grader_status(r, 'nonspecific_excess'), reason(r, 'nonspecific_excess')) == ('unknown', 'excess_recorded_for_the_sheet')
    assert status(r, 'nonspecific_excess') == 'supported' and _criterion(grade_radioligand(r), 'nonspecific_excess')['degree'] == 1.0
    r['quantities']['nonspecific_excess'] = point(100.0, 'ratio', 'e', ['s'])              # exactly the minimum, allowed
    assert _criterion(grade_radioligand(r), 'nonspecific_excess') == {'status': 'supported', 'support_refs': ['s'], 'degree': 1.0}
    assert grade_radioligand(r)['native']['nonspecific_excess_refs'] == ['s']
    r['quantities']['nonspecific_excess'] = point(50.5, 'ratio', 'e', ['s'])               # halfway from 1 up to 100: a degree of 0.5
    assert status(r, 'nonspecific_excess') == 'supported' and _criterion(grade_radioligand(r), 'nonspecific_excess')['degree'] == pytest.approx(0.5)
    r['quantities']['nonspecific_excess'] = point(1.0, 'ratio', 'e', ['s'])                # the zero-agreement limit
    assert status(r, 'nonspecific_excess') == 'conflicting' and 'degree' not in _criterion(grade_radioligand(r), 'nonspecific_excess')
    missing(r, 'nonspecific_excess')                                                       # 1000 nM / 2 nM = 500
    assert grade_radioligand(r)['native']['nonspecific_excess_ratio'] == 500.0 and status(r, 'nonspecific_excess') == 'supported'
    r['quantities']['nonspecific_ligand_concentration'] = point(0.4, 'uM', 'c', ['s'])     # 400 nM / 2 nM = 200
    assert grade_radioligand(r)['native']['nonspecific_excess_ratio'] == 200.0 and status(r, 'nonspecific_excess') == 'supported'
    r['quantities']['nonspecific_ligand_concentration'] = point(0.1, 'uM', 'c', ['s'])     # 100 nM / 2 nM = 50: a degree of 49 / 99
    assert reason(r, 'nonspecific_excess') == 'excess_recorded_for_the_sheet' and _criterion(grade_radioligand(r), 'nonspecific_excess')['degree'] == pytest.approx(49.0 / 99.0)
    assert len(_criterion(grade_radioligand(r), 'nonspecific_excess')['support_refs']) == 2
    missing(r, 'kd')
    assert (status(r, 'nonspecific_excess'), reason(r, 'nonspecific_excess')) == ('unknown', 'excess_not_given')


def test_the_equilibrium_fact_then_a_short_incubation():
    r = synthetic_record()
    r['facts']['equilibrium_reached'] = fact('unknown')
    assert (grader_status(r, 'equilibrium'), reason(r, 'equilibrium')) == ('unknown', 'incubation_recorded_for_the_sheet') and grade_radioligand(r)['native']['incubation_min'] == 60.0
    assert status(r, 'equilibrium') == 'unknown'                                           # a 60 min incubation is not short
    r['quantities']['incubation_time'] = point(29.0, 'min', 'i', ['s'])
    assert status(r, 'equilibrium') == 'conflicting' and grade_radioligand(r)['native']['incubation_refs'] == ['s'] and _criterion(grade_radioligand(r), 'equilibrium')['support_refs'] == ['s']
    r['quantities']['incubation_time'] = point(30.0, 'min', 'i', ['s'])                    # exactly the minimum
    assert status(r, 'equilibrium') == 'unknown'
    r['quantities']['incubation_time'] = point(0.4, 'h', 'i', ['s'])                       # 24 min
    assert status(r, 'equilibrium') == 'conflicting'
    r['facts']['equilibrium_reached'] = fact('yes', ['s'])                                 # the stated fact outranks the short time
    assert status(r, 'equilibrium') == 'supported'
    r['facts']['equilibrium_reached'] = fact('no', ['s'])
    assert reason(r, 'equilibrium') == 'fact_answered_no'


def test_the_series_must_have_enough_points_and_span_the_kd():
    r = synthetic_record()                                                                 # 10 points, 0.05 x to 25.6 x the KD of 2 nM
    assert (grader_status(r, 'radioligand_range'), reason(r, 'radioligand_range')) == ('unknown', 'radioligand_range_recorded_for_the_sheet')
    native = grade_radioligand(r)['native']
    assert native['concentration_count'] == 10 and native['concentration_count_refs'] == ['span_exp_synthetic_radioligand_1'] and native['concentration_span_refs'] == ['span_exp_synthetic_radioligand_1']
    assert _criterion(grade_radioligand(r), 'radioligand_range') == {'status': 'supported', 'support_refs': ['span_exp_synthetic_radioligand_1'], 'degree': 1.0}
    r['concentration_series']['value'] = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0]      # 8 points: lowest 0.5 nM = 0.25 x the KD (allowed), highest 32 x: the full degree
    assert _criterion(grade_radioligand(r), 'radioligand_range')['degree'] == 1.0
    r['concentration_series']['value'] = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0]    # lowest 1 nM = 0.5 x the KD: a degree of (0.5 - 1) / (0.25 - 1) = 2 / 3
    assert status(r, 'radioligand_range') == 'supported' and _criterion(grade_radioligand(r), 'radioligand_range')['degree'] == pytest.approx(2.0 / 3.0)
    r['concentration_series']['value'] = [2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0]  # lowest 2 nM = 1 x the KD: the zero-agreement limit
    assert status(r, 'radioligand_range') == 'conflicting' and 'degree' not in _criterion(grade_radioligand(r), 'radioligand_range')
    r['concentration_series']['value'] = [0.5, 1.0, 2.0, 4.0, 8.0, 9.0, 9.5, 10.0]         # highest 10 nM = 5 x the KD (allowed): the full degree
    assert _criterion(grade_radioligand(r), 'radioligand_range')['degree'] == 1.0
    r['concentration_series']['value'] = [0.5, 0.6, 0.8, 1.0, 1.5, 2.0, 3.0, 6.0]          # highest 6 nM = 3 x the KD: a degree of (3 - 1) / (5 - 1) = 0.5
    assert status(r, 'radioligand_range') == 'supported' and _criterion(grade_radioligand(r), 'radioligand_range')['degree'] == pytest.approx(0.5)
    r['concentration_series']['value'] = [0.5, 0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0]          # highest 2 nM = 1 x the KD: the zero-agreement limit
    assert status(r, 'radioligand_range') == 'conflicting'
    r['concentration_series']['value'] = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0]             # 7 points: fewer than eight, no degree
    assert status(r, 'radioligand_range') == 'conflicting' and 'degree' not in _criterion(grade_radioligand(r), 'radioligand_range')
    r['concentration_series'] = {**r['concentration_series'], 'status': 'unavailable', 'value': None}
    assert reason(r, 'radioligand_range') == 'radioligand_range_recorded_for_the_sheet' and status(r, 'radioligand_range') == 'supported'     # 10 stated points are enough, the stated lowest 0.1 nM and highest 51.2 nM span
    r['quantities']['titration_point_count'] = point(6, 'count', 'n', ['s'])
    assert status(r, 'radioligand_range') == 'conflicting'
    r['quantities']['titration_point_count'] = point(10, 'count', 'n', ['s'])
    r['quantities']['radioligand_range_highest'] = point(9.0, 'nM', 'h', ['s'])            # 4.5 x: a degree of 3.5 / 4
    assert status(r, 'radioligand_range') == 'supported' and _criterion(grade_radioligand(r), 'radioligand_range')['degree'] == pytest.approx(3.5 / 4.0)
    missing(r, 'radioligand_range_highest')
    assert reason(r, 'radioligand_range') == 'radioligand_range_recorded_for_the_sheet' and status(r, 'radioligand_range') == 'unknown'       # the count is known, the span is not
    missing(r, 'titration_point_count')
    assert (grader_status(r, 'radioligand_range'), reason(r, 'radioligand_range')) == ('unknown', 'kd_or_series_missing')


def test_the_competition_radioligand_concentration_is_at_most_the_kd():
    r = synthetic_record()                                                                 # 1 nM over the KD of 2 nM = 0.5
    assert (grader_status(r, 'competition_radioligand_level'), reason(r, 'competition_radioligand_level')) == ('unknown', 'radioligand_over_kd_recorded_for_the_sheet')
    assert grade_radioligand(r)['native']['radioligand_over_kd'] == pytest.approx(0.5) and grade_radioligand(r)['native']['radioligand_level_refs'] == ['span_exp_synthetic_radioligand_1']
    assert _criterion(grade_radioligand(r), 'competition_radioligand_level') == {'status': 'supported', 'support_refs': ['span_exp_synthetic_radioligand_1'], 'degree': 1.0}
    r['quantities']['radioligand_concentration'] = point(2.0, 'nM', 'l', ['s'])            # exactly the KD, allowed
    assert _criterion(grade_radioligand(r), 'competition_radioligand_level')['degree'] == 1.0
    r['quantities']['radioligand_concentration'] = point(11.0, 'nM', 'l', ['s'])           # 5.5 x the KD: a degree of (10 - 5.5) / 9 = 0.5
    assert status(r, 'competition_radioligand_level') == 'supported' and _criterion(grade_radioligand(r), 'competition_radioligand_level')['degree'] == pytest.approx(0.5)
    r['quantities']['radioligand_concentration'] = point(20.0, 'nM', 'l', ['s'])           # 10 x the KD: the zero-agreement limit
    assert status(r, 'competition_radioligand_level') == 'conflicting' and 'degree' not in _criterion(grade_radioligand(r), 'competition_radioligand_level')
    r['quantities']['radioligand_concentration'] = point(2.0, 'uM', 'l', ['s'])            # 1000 x
    assert status(r, 'competition_radioligand_level') == 'conflicting'
    missing(r, 'kd')
    assert (status(r, 'competition_radioligand_level'), reason(r, 'competition_radioligand_level')) == ('unknown', 'radioligand_concentration_or_kd_not_given')


def test_the_filter_and_the_wash_do_not_apply_to_a_method_that_has_none_unless_the_passage_states_them():
    r = synthetic_record()
    for name in ('filter_binding_checked', 'wash_dissociation_considered'):
        r['facts'][name] = fact('unknown')
    assert reason(r, 'filter_binding') == 'fact_unknown' and reason(r, 'wash_dissociation') == 'fact_unknown'
    r['separation_method'] = 'scintillation_proximity'
    assert (status(r, 'filter_binding'), reason(r, 'filter_binding')) == ('not_applicable', 'separation_is_not_filtration')
    assert (status(r, 'wash_dissociation'), reason(r, 'wash_dissociation')) == ('not_applicable', 'no_wash_in_scintillation_proximity')
    r['separation_method'] = 'centrifugation'
    assert reason(r, 'filter_binding') == 'separation_is_not_filtration' and reason(r, 'wash_dissociation') == 'fact_unknown'
    r['facts']['filter_binding_checked'] = fact('yes', ['s'])                              # a stated fact outranks the method
    assert (status(r, 'filter_binding'), reason(r, 'filter_binding')) == ('supported', 'facts_answered_yes')
    r['facts']['wash_dissociation_considered'] = fact('no', ['s'])
    assert (status(r, 'wash_dissociation'), reason(r, 'wash_dissociation')) == ('conflicting', 'fact_answered_no')


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
    r['quantities']['hill_slope'] = point(1.0, 'ratio', 'h', ['s'])
    assert (grader_status(r, 'hill_slope'), reason(r, 'hill_slope')) == ('unknown', 'hill_slope_recorded_for_the_sheet')
    assert grade_radioligand(r)['native']['hill_slope'] == 1.0 and grade_radioligand(r)['native']['hill_slope_refs'] == ['s']
    for slope, expected, degree in ((1.0, 'supported', 1.0), (0.8, 'supported', 1.0), (1.2, 'supported', 1.0), (0.65, 'supported', 0.5), (1.35, 'supported', 0.5), (0.5, 'conflicting', None), (1.5, 'conflicting', None), (0.3, 'conflicting', None), (2.0, 'conflicting', None)):
        r['quantities']['hill_slope'] = point(slope, 'ratio', 'h', ['s'])
        assert status(r, 'hill_slope') == expected, slope
        assert _criterion(grade_radioligand(r), 'hill_slope').get('degree') == (pytest.approx(degree) if degree is not None else None), slope
    missing(r, 'hill_slope')
    assert (status(r, 'hill_slope'), reason(r, 'hill_slope')) == ('unknown', 'hill_slope_not_given')


def test_the_cheng_prusoff_ki_must_agree_with_the_ic50_the_radioligand_concentration_and_the_kd():
    r = synthetic_record()                                                                 # Ki 5 nM; 7.5 / (1 + 1 / 2) = 5
    assert (grader_status(r, 'cheng_prusoff'), reason(r, 'cheng_prusoff')) == ('unknown', 'cheng_prusoff_recorded_for_the_sheet')
    native = grade_radioligand(r)['native']
    assert native['cheng_prusoff_fold'] == pytest.approx(1.0) and native['calculated_ki_nM'] == pytest.approx(5.0) and native['cheng_prusoff_refs'] == ['span_exp_synthetic_radioligand_1']
    assert _criterion(grade_radioligand(r), 'cheng_prusoff') == {'status': 'supported', 'support_refs': ['span_exp_synthetic_radioligand_1'], 'degree': 1.0}
    r['quantities']['ki'] = point(7.5, 'nM', 'k', ['s'])                                   # 7.5 / 5 = 1.5 exactly the factor, allowed: the full degree
    assert status(r, 'cheng_prusoff') == 'supported' and _criterion(grade_radioligand(r), 'cheng_prusoff')['degree'] == pytest.approx(1.0)
    r['quantities']['ki'] = point(16.25, 'nM', 'k', ['s'])                                 # 16.25 / 5 = 3.25: halfway from 1.5 to 5, a degree of 0.5
    assert status(r, 'cheng_prusoff') == 'supported' and _criterion(grade_radioligand(r), 'cheng_prusoff')['degree'] == pytest.approx(0.5)
    r['quantities']['ki'] = point(25.0, 'nM', 'k', ['s'])                                  # 25 / 5 = 5: the zero-agreement limit
    assert status(r, 'cheng_prusoff') == 'conflicting' and 'degree' not in _criterion(grade_radioligand(r), 'cheng_prusoff')
    r['quantities']['ki'] = point(1.0, 'nM', 'k', ['s'])                                   # 5 / 1 = 5 the other way
    assert status(r, 'cheng_prusoff') == 'conflicting'
    r['quantities']['ki'] = point(2.0, 'nM', 'k', ['s'])                                   # 5 / 2 = 2.5 the other way: a degree of (5 - 2.5) / 3.5
    assert _criterion(grade_radioligand(r), 'cheng_prusoff')['degree'] == pytest.approx(2.5 / 3.5)
    r['quantities']['ki'] = point(5.0, 'nM', 'k', ['s'])
    r['quantities']['ic50'] = point(0.0075, 'uM', 'c', ['s'])                              # 7.5 nM: the same
    assert status(r, 'cheng_prusoff') == 'supported'
    r['facts']['cheng_prusoff_applied_with_own_kd'] = fact('no', ['s'])                    # a stated no fails, even when the numbers agree
    assert (status(r, 'cheng_prusoff'), reason(r, 'cheng_prusoff')) == ('conflicting', 'fact_answered_no')
    r['facts']['cheng_prusoff_applied_with_own_kd'] = fact('yes', ['s'])
    r['quantities']['ki'] = point(40.0, 'nM', 'k', ['s'])                                  # stated yes, but the numbers do not agree (8 fold)
    assert reason(r, 'cheng_prusoff') == 'cheng_prusoff_recorded_for_the_sheet' and status(r, 'cheng_prusoff') == 'conflicting'
    missing(r, 'ic50')                                                                     # not all four: the fact decides
    assert (status(r, 'cheng_prusoff'), reason(r, 'cheng_prusoff')) == ('supported', 'facts_answered_yes')
    r['facts']['cheng_prusoff_applied_with_own_kd'] = fact('unknown')
    assert (status(r, 'cheng_prusoff'), reason(r, 'cheng_prusoff')) == ('unknown', 'fact_unknown')
    missing(r, 'ki')                                                                       # a saturation experiment with no competition constant
    assert (status(r, 'cheng_prusoff'), reason(r, 'cheng_prusoff')) == ('not_applicable', 'no_competition_constant')
    r['assay_format'] = None                                                               # the format is not stated: unknown, not applicable
    assert status(r, 'cheng_prusoff') == 'unknown'


def test_replicates_are_independent_experiments_and_tubes_do_not_count():
    r = synthetic_record()
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('unknown', 'replicate_count_recorded_for_the_sheet') and status(r, 'replicates') == 'supported'
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    assert status(r, 'replicates') == 'conflicting' and grade_radioligand(r)['native']['replicate_count'] == 2 and grade_radioligand(r)['native']['replicate_independent'] == 'yes'
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    assert status(r, 'replicates') == 'supported' and _criterion(grade_radioligand(r), 'replicates')['support_refs'] == ['s', 'span_exp_synthetic_radioligand_1']
    r['facts']['independent_experiments'] = fact('no', ['s'])
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('conflicting', 'replicates_not_independent')
    r['facts']['independent_experiments'] = fact('unknown')
    assert status(r, 'replicates') == 'unknown'
    r['facts']['independent_experiments'] = fact('yes', ['s'])
    missing(r, 'replicate_count')
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('unknown', 'replicate_count_or_independence_unknown')
    r['quantities']['technical_replicate_count'] = point(4, 'count', 'w', ['s'])           # triplicate or quadruplicate tubes do not make replicates
    assert status(r, 'replicates') == 'unknown'


def test_an_ic50_alone_is_not_a_binding_constant_but_is_kept_apart_from_the_kd():
    r = synthetic_record()
    for name in ('kd', 'ki'):
        missing(r, name)
    native = grade_radioligand(r)['native']
    assert native['kd_nM'] is None and native['ki_nM'] is None and native['ic50_nM'] == 7.5 and native['constant_name'] is None
