"""Dialysis grader: each criterion's rule on records, with the researched values exercised on both sides (the lone minimums give partial credit just below them)."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_dialysis_record import FACTS, fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_criteria import DIALYSIS_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_grader import CRITERIA, grade_dialysis
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.dialysis_cases import (
    low_binding_record, qualitative_record, real_kd_record, real_record, sparse_record, synthetic_record)

NO_CONSTANT = ('protein_level', 'concentration_series', 'fit_model')       # the criteria that need a KD (or a fit): not applicable for a record that reports no constant


def status(record, criterion):
    """The status of the criterion after the sheet side has judged the facts the grader recorded (the grader holds no threshold; the sheet-side constants are in the converter)."""
    return _criterion(grade_dialysis(record), criterion)['status']


def judged(record, criterion):
    return _criterion(grade_dialysis(record), criterion)


def grader_status(record, criterion):
    return grade_dialysis(record)['criteria'][criterion]['status']


def degree_of(record, criterion):
    return judged(record, criterion).get('degree')


def reason(record, criterion):
    return grade_dialysis(record)['reasons'][criterion]


def missing(record, *names):
    for name in names:
        record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None, 'source_refs': []}


def put(record, name, value, unit=None, refs=('s',)):
    record['quantities'][name] = point(value, unit or record['quantities'][name]['unit'], name, list(refs))


def answer(record, name, value):
    record['facts'][name] = fact(value, ['s'] if value in ('yes', 'no') else [])


def test_complete_synthetic_record_is_supported_everywhere_once_the_sheet_has_judged_the_recorded_numbers():
    graded = grade_dialysis(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA and len(CRITERIA) == 15
    handed = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed == {'recovery', 'device_adsorption', 'ligand_depletion', 'protein_level', 'free_fraction_measurable', 'concentration_series', 'replicates'}      # binding, equilibrium and the volume shift are stated by their facts
    assert all(graded['criteria'][name]['status'] == 'unknown' and graded['criteria'][name]['support_refs'] == [] for name in handed)
    assert {_criterion(graded, name)['status'] for name in CRITERIA} == {'supported'} and all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['recovery_percent'] == 95.0 and native['adsorption_percent'] == 5.0 and native['volume_shift_percent'] is None and native['replicate_count'] == 3 and native['replicate_independent'] == 'yes'
    assert graded['experiment_type'] == 'dialysis' and native['interaction'] == 'detected' and native['interaction_refs'] == ['span_exp_synthetic_dialysis_1']
    assert native['kd_nM'] == 200.0 and native['ki_nM'] == 500.0 and native['constant_name'] == 'kd' and native['constant_nM'] == 200.0
    assert native['percent_bound'] == 60.0 and native['percent_unbound'] == 40.0 and native['protein_nM'] == 1000.0 and native['salt_mM'] == 150.0 and native['equilibration_h'] == 6.0
    assert native['bound_nM'] == 300.0 and native['bound_over_protein'] == pytest.approx(0.3) and native['protein_over_kd'] == pytest.approx(5.0)
    assert native['concentration_count'] == 6 and native['concentration_low_over_kd'] == pytest.approx(0.25) and native['concentration_high_over_kd'] == pytest.approx(8.0)
    assert (native['separation_method'], native['device_type'], native['detection'], native['spread_kind'], native['fit_model']) == ('rapid_equilibrium_dialysis', 'red_device', 'lc_msms', 'standard_error', 'one_site')


def test_the_criteria_are_the_dialysis_ones_and_no_kinetic_constant_is_judged():
    assert not {'kon', 'koff', 'ic50', 'hill_slope'} & set(CRITERIA)
    assert {'binding_observed', 'equilibrium', 'recovery', 'device_adsorption', 'volume_shift', 'ligand_stability', 'free_measured_directly', 'protein_retained', 'buffer_only_control', 'ligand_depletion', 'protein_level',
            'free_fraction_measurable', 'concentration_series', 'fit_model', 'replicates'} == set(CRITERIA)


def test_sparse_record_is_unknown_never_conflicting_and_only_the_stated_binding_is_supported():
    graded = grade_dialysis(sparse_record())
    assert {name for name, c in graded['criteria'].items() if c['status'] == 'supported'} == {'binding_observed'}
    assert {name for name, c in graded['criteria'].items() if c['status'] == 'conflicting'} == set()
    assert {name for name, c in graded['criteria'].items() if c['status'] == 'not_applicable'} == {*NO_CONSTANT, 'free_fraction_measurable'}
    assert graded['native']['interaction'] == 'detected' and graded['reasons']['equilibrium'] == 'fact_unknown' and graded['reasons']['ligand_depletion'] == 'bound_or_protein_concentration_not_given'


def test_a_record_with_no_kd_and_no_ki_does_not_apply_the_kd_criteria_and_does_not_fail_them():
    graded = grade_dialysis(qualitative_record())
    for name, why in (('protein_level', 'no_kd_reported'), ('concentration_series', 'no_binding_constant_reported'), ('fit_model', 'no_binding_constant_reported')):
        assert graded['criteria'][name]['status'] == 'not_applicable' and graded['reasons'][name] == why, name
    assert {_criterion(graded, name)['status'] for name in CRITERIA if name not in NO_CONSTANT} == {'supported'}
    native = graded['native']
    assert native['kd_nM'] is None and native['ki_nM'] is None and native['constant_name'] is None and native['interaction'] == 'detected' and native['percent_bound'] == 60.0


# A supported or a conflicting criterion rests on quoted spans: the ELISA lesson (the sheet refuses an interpretation without support).
DECIDING = ('recovery', 'membrane_adsorption', 'volume_shift', 'salt_concentration', 'protein_concentration', 'kd', 'ki', 'percent_bound', 'percent_unbound', 'fraction_bound', 'fraction_unbound', 'equilibration_time', 'bound_ligand_concentration', 'ligand_total_concentration')


def variants():
    out = [synthetic_record(), qualitative_record(), sparse_record(), real_record(), real_kd_record(), low_binding_record()]
    for name in FACTS:
        for value in ('no', 'unknown', 'not_applicable'):
            record = synthetic_record()
            answer(record, name, value)
            out.append(record)
            record = synthetic_record()                                         # the same fact with the numbers that could decide in its place removed
            missing(record, *DECIDING)
            answer(record, name, value)
            out.append(record)
        record = synthetic_record()
        missing(record, *DECIDING)
        out.append(record)
    for fraction in (('percent_bound', 60.0), ('percent_bound', 5.0), ('percent_bound', 4.9), ('percent_unbound', 95.0), ('percent_unbound', 96.0), ('fraction_bound', 0.6), ('fraction_bound', 0.04), ('fraction_unbound', 0.4), ('fraction_unbound', 0.96),
                     ('percent_unbound', 1.0), ('percent_unbound', 0.9), ('percent_bound', 99.5), ('fraction_unbound', 0.005), ('fraction_bound', 0.995)):
        for decider in ('unknown', 'yes'):
            record = synthetic_record()
            missing(record, 'percent_bound', 'percent_unbound', 'fraction_bound', 'fraction_unbound')
            put(record, fraction[0], fraction[1], 'ratio' if fraction[0].startswith('fraction') else 'percent')
            answer(record, 'binding_detected', decider)
            out.append(record)
    for hours, unit, method, decider in ((6.0, 'h', 'rapid_equilibrium_dialysis', 'unknown'), (4.0, 'h', 'equilibrium_dialysis', 'unknown'), (3.9, 'h', 'equilibrium_dialysis', 'unknown'), (240.0, 'min', 'equilibrium_dialysis', 'unknown'), (239.0, 'min', 'equilibrium_dialysis', 'unknown'),
                                         (1.0, 'h', 'ultrafiltration', 'unknown'), (1.0, 'h', 'ultracentrifugation', 'unknown'), (1.0, 'h', 'ultrafiltration', 'yes'), (1.0, 'h', 'ultrafiltration', 'no'), (None, None, None, 'unknown'), (None, None, 'equilibrium_dialysis', 'unknown')):
        record = synthetic_record()
        answer(record, 'equilibrium_time_course_shown', decider)
        record['separation_method'] = method
        if hours is None:
            missing(record, 'equilibration_time')
        else:
            put(record, 'equilibration_time', hours, unit)
        out.append(record)
    for name, fact_name, values in (('recovery', 'recovery_checked', (95.0, 80.0, 79.9, 50.0)), ('membrane_adsorption', 'adsorption_checked_and_corrected', (5.0, 15.0, 15.1, 40.0))):
        for value in values:
            for decider in ('yes', 'no', 'unknown'):
                record = synthetic_record()
                put(record, name, value)
                answer(record, fact_name, decider)
                out.append(record)
    for shift, salt, unit, decider in ((3.0, 150.0, 'mM', 'unknown'), (10.0, 150.0, 'mM', 'unknown'), (10.1, 150.0, 'mM', 'unknown'), (None, 150.0, 'mM', 'unknown'), (None, 100.0, 'mM', 'unknown'), (None, 99.0, 'mM', 'unknown'), (None, 0.1, 'M', 'unknown'), (None, 0.05, 'M', 'unknown'), (None, None, None, 'unknown'),
                                       (50.0, 150.0, 'mM', 'yes'), (3.0, 150.0, 'mM', 'no'), (3.0, 150.0, 'mM', 'not_applicable')):
        record = synthetic_record()
        answer(record, 'volume_shift_corrected', decider)
        for name, value, quantity_unit in (('volume_shift', shift, 'percent'), ('salt_concentration', salt, unit)):
            if value is None:
                missing(record, name)
            else:
                put(record, name, value, quantity_unit)
        out.append(record)
    for bound, total, free, protein, unit in ((300.0, None, None, 1000.0, 'nM'), (1000.0, None, None, 1000.0, 'nM'), (1001.0, None, None, 1000.0, 'nM'), (None, 500.0, 200.0, 1000.0, 'nM'), (None, 1500.0, 200.0, 1000.0, 'nM'), (None, 200.0, 500.0, 1000.0, 'nM'),
                                              (300.0, None, None, None, 'nM'), (None, None, None, 1000.0, 'nM'), (300.0, None, None, 1.0, 'uM'), (2.0, None, None, 1.0, 'uM')):
        record = synthetic_record()
        missing(record, 'bound_ligand_concentration', 'ligand_total_concentration', 'free_ligand_concentration', 'protein_concentration')
        for name, value in (('bound_ligand_concentration', bound), ('ligand_total_concentration', total), ('free_ligand_concentration', free)):
            if value is not None:
                put(record, name, value, 'nM')
        if protein is not None:
            put(record, 'protein_concentration', protein, unit)
        out.append(record)
    for protein, unit, kd, decider in ((1000.0, 'nM', 200.0, 'unknown'), (1.0, 'uM', 5000.0, 'unknown'), (1.0, 'uM', 5100.0, 'unknown'), (1.0, 'uM', None, 'yes'), (1.0, 'uM', None, 'no'), (1.0, 'uM', None, 'unknown'), (None, None, 200.0, 'yes'), (None, None, 200.0, 'no'), (None, None, 200.0, 'unknown'), (None, None, 200.0, 'not_applicable'),
                                       (1.0, 'uM', None, 'not_applicable')):
        record = synthetic_record()
        answer(record, 'protein_at_or_above_kd', decider)
        for name, value, quantity_unit in (('protein_concentration', protein, unit), ('kd', kd, 'nM')):
            if value is None:
                missing(record, name)
            else:
                put(record, name, value, quantity_unit)
        out.append(record)
    for series, lowest, highest, count, kd, ki in ((None, None, None, None, 200.0, 500.0), ([50.0, 100.0, 200.0, 400.0, 800.0], None, None, None, 200.0, 500.0), ([100.0, 200.0, 400.0, 800.0, 1600.0, 3200.0], None, None, None, 200.0, 500.0), ([120.0, 200.0, 400.0, 800.0, 1600.0, 3200.0], None, None, None, 200.0, 500.0),
                                                    ([50.0, 100.0, 200.0, 400.0, 600.0, 780.0], None, None, None, 200.0, 500.0), ([0.1, 0.2, 0.4, 0.8, 1.6, 3.2], 'uM', None, None, 200.0, 500.0), (None, 50.0, 1600.0, 6, 200.0, 500.0), (None, 50.0, 1600.0, 5, 200.0, 500.0), (None, 50.0, 1600.0, None, 200.0, 500.0), (None, 120.0, 1600.0, None, 200.0, 500.0),
                                                    (None, 50.0, None, None, 200.0, 500.0), (None, None, None, 6, 200.0, 500.0), (None, 50.0, 1600.0, 6, None, 500.0), (None, 50.0, 1600.0, 4, None, 500.0), (None, 50.0, 1600.0, 6, None, None)):
        record = synthetic_record()
        missing(record, 'ligand_range_lowest', 'ligand_range_highest', 'titration_point_count', 'kd', 'ki')
        record['concentration_series'] = {**record['concentration_series'], 'status': 'unavailable', 'value': None}
        if series is not None:
            record['concentration_series'] = point(list(series), 'uM' if lowest == 'uM' else 'nM', 'series', ['s'])
            lowest = None if lowest == 'uM' else lowest
        for name, value in (('ligand_range_lowest', lowest), ('ligand_range_highest', highest), ('titration_point_count', count), ('kd', kd), ('ki', ki)):
            if value is not None:
                put(record, name, value, 'count' if name == 'titration_point_count' else 'nM')
        out.append(record)
    for model in ('one_site', 'two_site', 'hill', 'other', None):
        for constants in (('kd', 'bmax', 'ki'), ('kd',), ('bmax',), ('ki',), ()):
            record = synthetic_record()
            record['fit_model'] = model
            missing(record, *[name for name in ('kd', 'bmax', 'ki') if name not in constants])
            out.append(record)
    for count, independent in ((2, 'yes'), (3, 'no'), (None, 'yes'), (3, 'unknown'), (3, 'yes')):
        record = synthetic_record()
        answer(record, 'independent_experiments', independent)
        if count is None:
            missing(record, 'replicate_count')
        else:
            put(record, 'replicate_count', count, 'count')
        out.append(record)
    return out


def test_every_supported_or_conflicting_criterion_carries_support_refs():
    seen = set()
    for record in variants():
        graded = grade_dialysis(record)
        for name, outcome in graded['criteria'].items():
            if outcome['status'] in ('supported', 'conflicting'):
                seen.add((name, outcome['status'], graded['reasons'][name]))
                assert outcome['support_refs'], (record['experiment_ref'], name, graded['reasons'][name])
            else:
                assert outcome['support_refs'] == []
    # every supported or conflicting case the criteria declare was reached by some variant, and so was checked for its refs
    declared = {(criterion['id'], status, why) for criterion in DIALYSIS_CRITERIA for status, why, _ in criterion['returns'] if status in ('supported', 'conflicting')}
    assert seen == declared


def test_every_returned_status_and_reason_is_declared_on_the_variants():
    declared = {c['id']: {(status, why) for status, why, _ in c['returns']} for c in DIALYSIS_CRITERIA}
    for record in variants():
        graded = grade_dialysis(record)
        for name, outcome in graded['criteria'].items():
            assert (outcome['status'], graded['reasons'][name]) in declared[name], (name, outcome['status'], graded['reasons'][name])


def test_a_decided_criterion_cannot_be_built_without_support_refs():
    record = synthetic_record()
    record['facts']['ligand_stable'] = fact('yes')                         # a fact answered yes with no span: it cannot be supported
    with pytest.raises(ValueError, match='needs support refs'):
        grade_dialysis(record)


@pytest.mark.parametrize('criterion, name', [('ligand_stability', 'ligand_stable'), ('free_measured_directly', 'free_ligand_measured_directly'), ('protein_retained', 'protein_retained'), ('buffer_only_control', 'buffer_only_control_equal')])
def test_a_one_fact_criterion_follows_its_fact(criterion, name):
    r = synthetic_record()
    assert (status(r, criterion), reason(r, criterion)) == ('supported', 'facts_answered_yes')
    r['facts'][name] = fact('no', ['s'])
    assert (status(r, criterion), reason(r, criterion)) == ('conflicting', 'fact_answered_no')
    r['facts'][name] = fact('unknown')
    assert (status(r, criterion), reason(r, criterion)) == ('unknown', 'fact_unknown')
    r['facts'][name] = fact('not_applicable')
    assert (status(r, criterion), reason(r, criterion)) == ('not_applicable', 'fact_not_applicable')


def test_binding_is_observed_by_the_fact_or_by_a_stated_fraction_of_at_least_the_minimum_percent():
    r = synthetic_record()
    assert (status(r, 'binding_observed'), reason(r, 'binding_observed')) == ('supported', 'facts_answered_yes')
    r['facts']['binding_detected'] = fact('no', ['s_no'])
    assert (status(r, 'binding_observed'), reason(r, 'binding_observed')) == ('conflicting', 'fact_answered_no')
    native = grade_dialysis(r)['native']
    assert native['interaction'] == 'not_detected' and native['interaction_refs'] == ['s_no']
    r['facts']['binding_detected'] = fact('unknown')                                        # the stated percent bound is recorded: 60; the sheet judges it
    graded = grade_dialysis(r)
    assert (graded['criteria']['binding_observed'], graded['reasons']['binding_observed']) == ({'status': 'unknown', 'support_refs': []}, 'percent_bound_recorded_for_the_sheet')
    assert graded['native']['percent_bound'] == 60.0 and graded['native']['percent_bound_refs'] == ['span_exp_synthetic_dialysis_1'] and graded['native']['interaction'] is None    # the statement is the sheet's reading
    assert status(r, 'binding_observed') == 'supported'
    for value, expected, degree in ((5.0, 'supported', 0.0), (10.0, 'supported', 0.5), (4.9, 'conflicting', None), (60.0, 'supported', 1.0), (0.5, 'conflicting', None)):
        put(r, 'percent_bound', value, 'percent')
        assert status(r, 'binding_observed') == expected, value
        assert degree_of(r, 'binding_observed') == (pytest.approx(degree) if degree is not None else None) and judged(r, 'binding_observed')['support_refs'] == ['s']      # the direction flips at the researched 5; the credit rises from 0 there to 1 at 15
    assert reason(r, 'binding_observed') == 'percent_bound_recorded_for_the_sheet'
    missing(r, 'percent_bound')                                                             # the percent unbound is read as 100 minus it
    for value, expected in ((40.0, 'supported'), (95.0, 'supported'), (96.0, 'conflicting')):
        put(r, 'percent_unbound', value, 'percent')
        assert status(r, 'binding_observed') == expected, value
    assert grade_dialysis(r)['native']['percent_bound'] == pytest.approx(4.0)
    missing(r, 'percent_unbound')                                                           # then the fraction bound times 100
    put(r, 'fraction_bound', 0.04, 'ratio')
    assert status(r, 'binding_observed') == 'conflicting' and grade_dialysis(r)['native']['percent_bound'] == pytest.approx(4.0)
    put(r, 'fraction_bound', 0.6, 'ratio')
    assert status(r, 'binding_observed') == 'supported' and judged(r, 'binding_observed')['support_refs'] == ['s']
    missing(r, 'fraction_bound')                                                            # then 100 minus the fraction unbound times 100
    put(r, 'fraction_unbound', 0.96, 'ratio')
    assert status(r, 'binding_observed') == 'conflicting'
    put(r, 'fraction_unbound', 0.4, 'ratio')
    assert status(r, 'binding_observed') == 'supported' and grade_dialysis(r)['native']['percent_bound'] == pytest.approx(60.0)
    missing(r, 'fraction_unbound')
    assert (status(r, 'binding_observed'), reason(r, 'binding_observed')) == ('unknown', 'fact_unknown') and grade_dialysis(r)['native']['interaction'] is None
    r['facts']['binding_detected'] = fact('not_applicable')
    assert (status(r, 'binding_observed'), reason(r, 'binding_observed')) == ('not_applicable', 'fact_not_applicable')
    low = grade_dialysis(low_binding_record())                                              # 3 percent bound: not shown, whatever else the record says
    assert low['native']['percent_bound'] == 3.0 and _criterion(low, 'binding_observed')['status'] == 'conflicting' and low['native']['interaction'] is None


def test_the_stated_fact_wins_over_the_fraction():
    r = synthetic_record()
    put(r, 'percent_bound', 1.0, 'percent')
    assert status(r, 'binding_observed') == 'supported' and reason(r, 'binding_observed') == 'facts_answered_yes'      # the passage says binding was observed; the fraction is not consulted


def test_equilibrium_is_shown_by_a_time_course_or_by_a_time_of_at_least_the_minimum_hours():
    r = synthetic_record()
    assert (status(r, 'equilibrium'), reason(r, 'equilibrium')) == ('supported', 'facts_answered_yes')
    r['facts']['equilibrium_time_course_shown'] = fact('no', ['s'])
    assert (status(r, 'equilibrium'), reason(r, 'equilibrium')) == ('conflicting', 'fact_answered_no')
    r['facts']['equilibrium_time_course_shown'] = fact('unknown')
    graded = grade_dialysis(r)                                                                                                    # 6 h: recorded for the sheet
    assert (graded['criteria']['equilibrium'], graded['reasons']['equilibrium']) == ({'status': 'unknown', 'support_refs': []}, 'equilibration_time_recorded_for_the_sheet')
    assert graded['native']['equilibration_h'] == 6.0 and graded['native']['equilibration_refs'] == ['span_exp_synthetic_dialysis_1'] and status(r, 'equilibrium') == 'supported'
    for value, unit, expected, degree in ((4.0, 'h', 'supported', 1.0), (240.0, 'min', 'supported', 1.0), (36.0, 'h', 'supported', 1.0), (2.5, 'h', 'supported', 0.785), (150.0, 'min', 'supported', 0.785), (1.0, 'h', 'conflicting', None), (30.0, 'min', 'conflicting', None)):
        put(r, 'equilibration_time', value, unit)
        assert status(r, 'equilibrium') == expected, (value, unit)
        assert degree_of(r, 'equilibrium') == (pytest.approx(degree, abs=0.002) if degree is not None else None), (value, unit)      # the exponential approach to equilibrium: 2.5 h is 0.785
    assert reason(r, 'equilibrium') == 'equilibration_time_recorded_for_the_sheet' and grade_dialysis(r)['native']['equilibration_h'] == pytest.approx(0.5)
    r['separation_method'] = 'ultrafiltration'                                              # not an equilibrium method: the time does not apply
    assert (status(r, 'equilibrium'), reason(r, 'equilibrium')) == ('not_applicable', 'method_is_not_equilibrium_dialysis')
    r['separation_method'] = 'ultracentrifugation'
    assert status(r, 'equilibrium') == 'not_applicable'
    r['facts']['equilibrium_time_course_shown'] = fact('yes', ['s'])                        # a stated time course is still judged
    assert status(r, 'equilibrium') == 'supported'
    r['facts']['equilibrium_time_course_shown'] = fact('no', ['s'])
    assert status(r, 'equilibrium') == 'conflicting'
    r['facts']['equilibrium_time_course_shown'] = fact('unknown')
    r['separation_method'] = 'equilibrium_dialysis'
    missing(r, 'equilibration_time')
    assert (status(r, 'equilibrium'), reason(r, 'equilibrium')) == ('unknown', 'fact_unknown')
    r['facts']['equilibrium_time_course_shown'] = fact('not_applicable')
    assert (status(r, 'equilibrium'), reason(r, 'equilibrium')) == ('not_applicable', 'fact_not_applicable')


@pytest.mark.parametrize('criterion, quantity, fact_name, native_key, handed, rows', [
    ('recovery', 'recovery', 'recovery_checked', 'recovery_percent', 'recovery_recorded_for_the_sheet', ((95.0, 'supported', 1.0), (80.0, 'supported', 1.0), (65.0, 'supported', 0.5), (50.0, 'conflicting', None), (20.0, 'conflicting', None))),
    ('device_adsorption', 'membrane_adsorption', 'adsorption_checked_and_corrected', 'adsorption_percent', 'adsorption_recorded_for_the_sheet', ((5.0, 'supported', 1.0), (15.0, 'supported', 1.0), (27.5, 'supported', 0.5), (40.0, 'conflicting', None), (70.0, 'conflicting', None)))])
def test_a_stated_loss_is_recorded_for_the_sheet_and_without_it_the_fact_decides(criterion, quantity, fact_name, native_key, handed, rows):
    r = synthetic_record()
    assert (grader_status(r, criterion), reason(r, criterion)) == ('unknown', handed) and status(r, criterion) == 'supported'
    r['facts'][fact_name] = fact('unknown')                                                 # no statement about a correction: the stated number counts whole
    for value, expected, degree in rows:
        put(r, quantity, value)
        assert grade_dialysis(r)['native'][native_key] == value and judged(r, criterion)['support_refs'] == ['s']
        assert status(r, criterion) == expected and degree_of(r, criterion) == (pytest.approx(degree) if degree is not None else None), value
    r['facts'][fact_name] = fact('no', ['s'])                                               # the number decides, not the fact
    assert status(r, criterion) == 'conflicting'
    missing(r, quantity)
    r['facts'][fact_name] = fact('yes', ['s'])
    assert (status(r, criterion), reason(r, criterion)) == ('supported', 'facts_answered_yes')
    r['facts'][fact_name] = fact('no', ['s'])
    assert (status(r, criterion), reason(r, criterion)) == ('conflicting', 'fact_answered_no')
    r['facts'][fact_name] = fact('unknown')
    assert (status(r, criterion), reason(r, criterion)) == ('unknown', 'fact_unknown')
    r['facts'][fact_name] = fact('not_applicable')
    assert (status(r, criterion), reason(r, criterion)) == ('not_applicable', 'fact_not_applicable')


def test_the_volume_shift_is_corrected_small_or_ruled_out_by_the_salt():
    r = synthetic_record()
    assert (status(r, 'volume_shift'), reason(r, 'volume_shift')) == ('supported', 'facts_answered_yes')
    r['facts']['volume_shift_corrected'] = fact('no', ['s'])
    assert (status(r, 'volume_shift'), reason(r, 'volume_shift')) == ('conflicting', 'fact_answered_no')
    r['facts']['volume_shift_corrected'] = fact('unknown')
    graded = grade_dialysis(r)                                                                                                  # 3 percent: recorded for the sheet
    assert (graded['criteria']['volume_shift'], graded['reasons']['volume_shift']) == ({'status': 'unknown', 'support_refs': []}, 'volume_shift_recorded_for_the_sheet')
    assert graded['native']['volume_shift_percent'] == 3.0 and graded['native']['volume_shift_refs'] == ['span_exp_synthetic_dialysis_1'] and status(r, 'volume_shift') == 'supported'
    for value, expected, degree in ((10.0, 'supported', 1.0), (20.0, 'supported', 0.5), (30.0, 'conflicting', None), (40.0, 'conflicting', None)):
        put(r, 'volume_shift', value, 'percent')
        assert status(r, 'volume_shift') == expected and degree_of(r, 'volume_shift') == (pytest.approx(degree) if degree is not None else None), value
    missing(r, 'volume_shift')                                                              # no shift stated: the salt of the buffer (150 mM)
    graded = grade_dialysis(r)
    assert (graded['criteria']['volume_shift']['status'], graded['reasons']['volume_shift']) == ('unknown', 'salt_recorded_for_the_sheet') and graded['native']['salt_refs'] == ['span_exp_synthetic_dialysis_1']
    assert judged(r, 'volume_shift') == {'status': 'supported', 'support_refs': ['span_exp_synthetic_dialysis_1'], 'degree': 1.0}      # at or above the researched 100 mM: full agreement
    # the full-agreement salt is 100 mM scaled by the protein over plasma level (0.6 mM); at 300 uM protein that is 50 mM; below it the degree is salt over that salt: never a conflict, unknown at no salt
    put(r, 'protein_concentration', 300.0, 'uM')
    degrees = []
    for value, unit, expected, degree in ((0.1, 'M', 'supported', 1.0), (100.0, 'mM', 'supported', 1.0), (50.0, 'mM', 'supported', 1.0), (25.0, 'mM', 'supported', 0.5), (10.0, 'mM', 'supported', 0.2), (0.0, 'mM', 'unknown', None)):
        put(r, 'salt_concentration', value, unit)
        verdict = judged(r, 'volume_shift')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), (value, unit)
        if expected == 'supported':
            degrees.append(verdict['degree'])
    assert degrees == sorted(degrees, reverse=True)                                         # less salt never raises the degree
    put(r, 'salt_concentration', 0.05, 'M')
    assert reason(r, 'volume_shift') == 'salt_recorded_for_the_sheet' and grade_dialysis(r)['native']['salt_mM'] == pytest.approx(50.0)
    missing(r, 'salt_concentration')
    assert (status(r, 'volume_shift'), reason(r, 'volume_shift')) == ('unknown', 'fact_unknown')
    r['facts']['volume_shift_corrected'] = fact('not_applicable')
    assert (status(r, 'volume_shift'), reason(r, 'volume_shift')) == ('not_applicable', 'fact_not_applicable')
    r['facts']['volume_shift_corrected'] = fact('yes', ['s'])
    put(r, 'volume_shift', 50.0, 'percent')                                                  # a stated correction is not second-guessed by the number
    assert status(r, 'volume_shift') == 'supported'


def test_the_bound_ligand_must_not_exceed_the_protein():
    r = synthetic_record()                                                                  # 300 nM bound against 1000 nM protein
    assert (grader_status(r, 'ligand_depletion'), reason(r, 'ligand_depletion')) == ('unknown', 'bound_over_protein_recorded_for_the_sheet') and grade_dialysis(r)['native']['bound_over_protein'] == pytest.approx(0.3)
    assert status(r, 'ligand_depletion') == 'supported' and grade_dialysis(r)['native']['bound_over_protein_refs'] == ['span_exp_synthetic_dialysis_1']
    for value, expected, degree in ((1000.0, 'supported', 1.0), (2000.0, 'supported', 0.5), (3000.0, 'conflicting', None), (5000.0, 'conflicting', None)):
        put(r, 'bound_ligand_concentration', value, 'nM')
        assert status(r, 'ligand_depletion') == expected and degree_of(r, 'ligand_depletion') == (pytest.approx(degree) if degree is not None else None), value
    missing(r, 'bound_ligand_concentration')                                                # the total minus the free: 500 - 200
    assert (status(r, 'ligand_depletion'), reason(r, 'ligand_depletion')) == ('supported', 'bound_over_protein_recorded_for_the_sheet') and grade_dialysis(r)['native']['bound_nM'] == pytest.approx(300.0)
    assert judged(r, 'ligand_depletion')['support_refs'] == ['span_exp_synthetic_dialysis_1']
    put(r, 'ligand_total_concentration', 4500.0, 'nM')
    assert status(r, 'ligand_depletion') == 'conflicting' and grade_dialysis(r)['native']['bound_nM'] == pytest.approx(4300.0)
    put(r, 'ligand_total_concentration', 100.0, 'nM')                                       # the total is not above the free: no bound ligand can be derived
    assert (status(r, 'ligand_depletion'), reason(r, 'ligand_depletion')) == ('unknown', 'bound_or_protein_concentration_not_given') and grade_dialysis(r)['native']['bound_nM'] is None
    put(r, 'ligand_total_concentration', 500.0, 'nM')
    missing(r, 'protein_concentration')
    assert (status(r, 'ligand_depletion'), reason(r, 'ligand_depletion')) == ('unknown', 'bound_or_protein_concentration_not_given')
    put(r, 'protein_concentration', 1.0, 'uM')                                              # 1000 nM in micromolar
    assert status(r, 'ligand_depletion') == 'supported' and grade_dialysis(r)['native']['protein_nM'] == pytest.approx(1000.0)


def test_the_protein_concentration_must_be_at_least_the_minimum_fraction_of_the_kd():
    r = synthetic_record()                                                                  # 1000 nM protein, KD 200 nM
    assert (grader_status(r, 'protein_level'), reason(r, 'protein_level')) == ('unknown', 'protein_over_kd_recorded_for_the_sheet') and grade_dialysis(r)['native']['protein_over_kd'] == pytest.approx(5.0)
    assert status(r, 'protein_level') == 'supported' and grade_dialysis(r)['native']['protein_over_kd_refs'] == ['span_exp_synthetic_dialysis_1']
    put(r, 'protein_concentration', 1.0, 'uM')
    put(r, 'kd', 5000.0, 'nM')                                                              # exactly 0.2: the sheet's full-agreement limit
    assert status(r, 'protein_level') == 'supported' and degree_of(r, 'protein_level') == pytest.approx(1.0)
    put(r, 'kd', 8000.0, 'nM')                                                              # 0.125: halfway between 0.05 and 0.2
    assert status(r, 'protein_level') == 'supported' and degree_of(r, 'protein_level') == pytest.approx(0.5)
    put(r, 'kd', 20000.0, 'nM')                                                             # exactly 0.05: the zero limit
    assert status(r, 'protein_level') == 'conflicting' and degree_of(r, 'protein_level') is None
    r['facts']['protein_at_or_above_kd'] = fact('yes', ['s'])                               # the numbers decide, not the fact
    assert status(r, 'protein_level') == 'conflicting'
    missing(r, 'kd')                                                                        # without the KD the fact decides
    assert (status(r, 'protein_level'), reason(r, 'protein_level')) == ('supported', 'facts_answered_yes')
    r['facts']['protein_at_or_above_kd'] = fact('no', ['s'])
    assert (status(r, 'protein_level'), reason(r, 'protein_level')) == ('conflicting', 'fact_answered_no')
    r['facts']['protein_at_or_above_kd'] = fact('unknown')
    assert (status(r, 'protein_level'), reason(r, 'protein_level')) == ('not_applicable', 'no_kd_reported')
    put(r, 'kd', 200.0, 'nM')
    missing(r, 'protein_concentration')
    assert (status(r, 'protein_level'), reason(r, 'protein_level')) == ('unknown', 'fact_unknown')
    r['facts']['protein_at_or_above_kd'] = fact('not_applicable')
    assert (status(r, 'protein_level'), reason(r, 'protein_level')) == ('not_applicable', 'fact_not_applicable')


def test_the_free_fraction_must_be_measurable_and_the_stated_percent_unbound_comes_first():
    r = synthetic_record()
    assert (grader_status(r, 'free_fraction_measurable'), reason(r, 'free_fraction_measurable')) == ('unknown', 'percent_unbound_recorded_for_the_sheet') and grade_dialysis(r)['native']['percent_unbound'] == 40.0
    assert status(r, 'free_fraction_measurable') == 'supported' and grade_dialysis(r)['native']['percent_unbound_refs'] == ['span_exp_synthetic_dialysis_1']
    for value, expected, degree in ((1.0, 'supported', 1.0), (40.0, 'supported', 1.0), (0.5, 'supported', 0.5), (0.0, 'conflicting', None)):
        put(r, 'percent_unbound', value, 'percent')
        assert status(r, 'free_fraction_measurable') == expected and degree_of(r, 'free_fraction_measurable') == (pytest.approx(degree) if degree is not None else None), value
    put(r, 'percent_unbound', 0.5, 'percent')
    assert reason(r, 'free_fraction_measurable') == 'percent_unbound_recorded_for_the_sheet'
    missing(r, 'percent_unbound')                                                           # then the fraction unbound times 100 (0.4 -> 40 percent)
    assert status(r, 'free_fraction_measurable') == 'supported' and grade_dialysis(r)['native']['percent_unbound'] == pytest.approx(40.0)
    put(r, 'fraction_unbound', 0.005, 'ratio')                                              # 0.5 percent: half way to the minimum
    assert status(r, 'free_fraction_measurable') == 'supported' and degree_of(r, 'free_fraction_measurable') == pytest.approx(0.5)
    missing(r, 'fraction_unbound')                                                          # then 100 minus the percent bound (99.5 -> 0.5)
    put(r, 'percent_bound', 99.5, 'percent')
    assert degree_of(r, 'free_fraction_measurable') == pytest.approx(0.5) and grade_dialysis(r)['native']['percent_unbound'] == pytest.approx(0.5)
    put(r, 'percent_bound', 100.0, 'percent')                                               # nothing free
    assert status(r, 'free_fraction_measurable') == 'conflicting'
    put(r, 'percent_bound', 99.5, 'percent')
    put(r, 'percent_bound', 60.0, 'percent')
    assert status(r, 'free_fraction_measurable') == 'supported'
    missing(r, 'percent_bound', 'fraction_bound')
    assert (status(r, 'free_fraction_measurable'), reason(r, 'free_fraction_measurable')) == ('not_applicable', 'no_fraction_reported')


def test_the_series_needs_enough_concentrations_that_bracket_the_kd():
    r = synthetic_record()                                                                  # six concentrations from 0.25 to 8 times the KD
    graded = grade_dialysis(r)
    assert (graded['criteria']['concentration_series'], graded['reasons']['concentration_series']) == ({'status': 'unknown', 'support_refs': []}, 'concentration_series_recorded_for_the_sheet')
    assert graded['native']['concentration_count'] == 6 and graded['native']['concentration_count_refs'] == ['span_exp_synthetic_dialysis_1'] and graded['native']['concentration_span_refs'] == ['span_exp_synthetic_dialysis_1']
    assert status(r, 'concentration_series') == 'supported' and degree_of(r, 'concentration_series') == 1.0
    r['concentration_series'] = point([50.0, 100.0, 200.0, 400.0, 800.0], 'nM', 'series', ['s'])
    assert status(r, 'concentration_series') == 'supported' and grade_dialysis(r)['native']['concentration_count'] == 5 and degree_of(r, 'concentration_series') == pytest.approx(0.75)      # one below the researched six: partial credit, not a conflict
    for series, expected, degree in (([100.0, 200.0, 400.0, 800.0, 1600.0, 3200.0], 'supported', 1.0), ([100.0, 200.0, 400.0, 800.0, 1600.0, 3200.0, 6400.0], 'supported', 1.0), ([100.0, 200.0, 300.0, 400.0, 600.0, 800.0], 'supported', 1.0),
                                     ([150.0, 200.0, 400.0, 800.0, 1600.0, 3200.0], 'supported', 3 / 7), ([100.0, 200.0, 400.0, 800.0, 1100.0, 1600.0], 'supported', 1.0), ([100.0, 200.0, 300.0, 400.0, 500.0, 500.0], 'supported', 5 / 7),
                                     ([200.0, 400.0, 800.0, 1600.0, 3200.0, 6400.0], 'conflicting', None), ([50.0, 100.0, 150.0, 175.0, 190.0, 200.0], 'conflicting', None),
                                     ([100.0, 400.0, 800.0, 1600.0], 'supported', 0.5), ([100.0, 1600.0], 'supported', 0.0), ([150.0, 400.0, 800.0, 1600.0, 3200.0], 'supported', 3 / 7)):      # the weakest of the count, the low end and the high end; the ends are linear in occupancy x / (1 + x): 0.75 x KD low = 3/7, 2.5 x KD high = (5/7 - 1/2) / (3/10) = 5/7
        r['concentration_series'] = point(series, 'nM', 'series', ['s'])
        verdict = judged(r, 'concentration_series')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), series
    r['concentration_series'] = point([0.1, 0.2, 0.4, 0.8, 1.6, 3.2], 'uM', 'series', ['s'])      # micromolar: 100 nM to 3200 nM
    assert status(r, 'concentration_series') == 'supported' and grade_dialysis(r)['native']['concentration_low_over_kd'] == pytest.approx(0.5)
    r['concentration_series'] = {**r['concentration_series'], 'status': 'unavailable', 'value': None}      # no list: the stated lowest and highest and the stated number of points
    assert status(r, 'concentration_series') == 'supported' and grade_dialysis(r)['native']['concentration_count'] == 6
    degrees = []
    for count, expected, degree in ((2, 'supported', 0.0), (3, 'supported', 0.25), (4, 'supported', 0.5), (5, 'supported', 0.75), (6, 'supported', 1.0), (10, 'supported', 1.0)):
        put(r, 'titration_point_count', count, 'count')                                     # linear in the residual degrees of freedom of the one-site fit: (n - 2) / (6 - 2)
        verdict = judged(r, 'concentration_series')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), count
        degrees.append(verdict.get('degree', 0.0))
    assert degrees == sorted(degrees)                                                       # more concentrations never lower the degree
    put(r, 'titration_point_count', 2, 'count')
    assert judged(r, 'concentration_series')['support_refs'] == ['span_exp_synthetic_dialysis_1', 's']      # two points: degree 0, supported (never conflicting)
    put(r, 'titration_point_count', 5, 'count')
    assert judged(r, 'concentration_series')['support_refs'] == ['span_exp_synthetic_dialysis_1', 's']      # a count that sets the degree is cited with the span
    missing(r, 'titration_point_count')
    assert status(r, 'concentration_series') == 'supported'
    put(r, 'ligand_range_lowest', 400.0, 'nM')                                              # 2 x the KD: beyond the zero limit of 1 x the KD
    assert status(r, 'concentration_series') == 'conflicting'
    put(r, 'ligand_range_lowest', 150.0, 'nM')                                              # 0.75 x the KD: degree 3/7 in occupancy (was halfway in x)
    assert status(r, 'concentration_series') == 'supported' and degree_of(r, 'concentration_series') == pytest.approx(3 / 7)
    missing(r, 'ligand_range_highest')
    assert (grader_status(r, 'concentration_series'), reason(r, 'concentration_series')) == ('unknown', 'kd_or_series_missing')
    put(r, 'ligand_range_lowest', 50.0, 'nM')
    put(r, 'ligand_range_highest', 1600.0, 'nM')
    missing(r, 'kd')                                                                        # a Ki only: the span cannot be judged, the count can
    assert (status(r, 'concentration_series'), reason(r, 'concentration_series')) == ('unknown', 'kd_or_series_missing')
    put(r, 'titration_point_count', 4, 'count')                                             # below the six, but above the fit's two: no span to bracket, unknown
    assert (grader_status(r, 'concentration_series'), reason(r, 'concentration_series'), status(r, 'concentration_series')) == ('unknown', 'concentration_series_recorded_for_the_sheet', 'unknown')
    put(r, 'titration_point_count', 2, 'count')                                             # no more points than the fit's parameters, and no span: still unknown, never conflicting
    assert status(r, 'concentration_series') == 'unknown'
    missing(r, 'ki')
    assert (status(r, 'concentration_series'), reason(r, 'concentration_series')) == ('not_applicable', 'no_binding_constant_reported')


def test_a_fit_model_is_supported_by_a_reported_constant_and_does_not_apply_without_any():
    r = synthetic_record()
    assert (status(r, 'fit_model'), reason(r, 'fit_model')) == ('supported', 'model_stated')
    r['fit_model'] = None
    assert (status(r, 'fit_model'), reason(r, 'fit_model')) == ('unknown', 'fit_model_not_stated')
    r['fit_model'] = 'two_site'
    missing(r, 'kd', 'ki')                                                                  # a Bmax still supports it
    assert (status(r, 'fit_model'), reason(r, 'fit_model')) == ('supported', 'model_stated')
    missing(r, 'bmax')
    assert (status(r, 'fit_model'), reason(r, 'fit_model')) == ('unknown', 'model_stated_without_a_reported_constant')
    r['fit_model'] = None
    assert (status(r, 'fit_model'), reason(r, 'fit_model')) == ('not_applicable', 'no_binding_constant_reported')


def test_replicates_are_independent_experiments_and_cells_of_one_experiment_do_not_count():
    r = synthetic_record()
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('unknown', 'replicate_count_recorded_for_the_sheet')
    assert grade_dialysis(r)['native']['replicate_count'] == 3 and grade_dialysis(r)['native']['replicate_independent'] == 'yes' and status(r, 'replicates') == 'supported'
    degrees = []
    for count, independent, expected, degree in ((1, 'yes', 'supported', (1 / 3) ** 0.5), (2, 'yes', 'supported', (2 / 3) ** 0.5), (3, 'yes', 'supported', 1.0), (10, 'yes', 'supported', 1.0),
                                                 (1, 'unknown', 'unknown', None), (2, 'unknown', 'unknown', None), (3, 'unknown', 'unknown', None)):
        put(r, 'replicate_count', count, 'count')                                           # precision of the mean: sqrt(n / 3), capped at 1
        answer(r, 'independent_experiments', independent)
        verdict = judged(r, 'replicates')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), (count, independent)
        if independent == 'yes':
            degrees.append(verdict.get('degree', 0.0))
    assert degrees == sorted(degrees)                                                       # more experiments never lower the degree; two get partial credit, not a conflict
    put(r, 'replicate_count', 3, 'count')
    r['facts']['independent_experiments'] = fact('no', ['s'])
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('conflicting', 'replicates_not_independent')       # a fact, judged by the grader
    r['facts']['independent_experiments'] = fact('yes', ['s'])
    missing(r, 'replicate_count')
    assert (status(r, 'replicates'), reason(r, 'replicates')) == ('unknown', 'replicate_count_or_independence_unknown')
    put(r, 'technical_replicate_count', 9, 'count')                                         # nine cells of one experiment are not replicates
    assert status(r, 'replicates') == 'unknown'


def test_a_kd_is_the_constant_and_a_ki_is_taken_only_without_one():
    r = synthetic_record()
    assert grade_dialysis(r)['native']['constant_name'] == 'kd'
    missing(r, 'kd')
    native = grade_dialysis(r)['native']
    assert native['constant_name'] == 'ki' and native['constant_nM'] == 500.0
    missing(r, 'ki')
    assert grade_dialysis(r)['native']['constant_name'] is None


def test_the_qualitative_statement_follows_the_binding_criterion():
    r = qualitative_record()
    assert grade_dialysis(r)['native']['interaction'] == 'detected'
    r['facts']['binding_detected'] = fact('no', ['span_no'])
    native = grade_dialysis(r)['native']
    assert native['interaction'] == 'not_detected' and native['interaction_refs'] == ['span_no']
    for value in ('unknown', 'not_applicable'):
        r['facts']['binding_detected'] = fact(value)
        missing(r, 'percent_bound', 'percent_unbound', 'fraction_bound', 'fraction_unbound')
        native = grade_dialysis(r)['native']
        assert native['interaction'] is None and native['interaction_refs'] == [] and native['percent_bound'] is None


def test_the_grader_keeps_the_support_of_the_fields_each_criterion_reads_and_does_not_judge_it():
    r = synthetic_record()
    r['facts']['protein_retained']['support'] = 'implied'
    r['quantities']['replicate_count']['support'] = 'about_something_else'
    graded = grade_dialysis(r)
    support = graded['native']['support']
    assert set(support) == set(CRITERIA)
    assert support['protein_retained'] == ['implied'] and 'about_something_else' in support['replicates']
    assert graded['criteria']['protein_retained']['status'] == 'supported'      # the status is the grader's own: support does not change it
    assert grade_dialysis(sparse_record())['native']['support']['protein_retained'] == []      # an unknown fact is not stated: no support


def test_the_grader_records_the_spread_the_limit_of_quantification_and_the_correction_for_the_sheet():
    r = synthetic_record()
    r['facts']['binding_detected'] = fact('unknown')
    put(r, 'percent_bound_spread', 4.0, 'percent', refs=('s_sd',))
    native = grade_dialysis(r)['native']
    assert native['percent_bound_spread'] == 4.0 and native['percent_bound_spread_refs'] == ['s_sd']
    put(r, 'detection_lloq', 2.0, 'nM', refs=('s_l',))
    graded = grade_dialysis(r)                                                              # the percent unbound is stated: the free concentration over the limit is recorded beside it
    assert graded['native']['free_over_lloq'] == pytest.approx(100.0) and graded['native']['free_over_lloq_refs'] == ['span_exp_synthetic_dialysis_1', 's_l']
    assert graded['reasons']['free_fraction_measurable'] == 'percent_unbound_recorded_for_the_sheet' and graded['native']['adsorption_corrected'] == 'yes' and graded['native']['adsorption_corrected_refs'] == ['span_exp_synthetic_dialysis_1']
    missing(r, 'percent_bound_spread', 'detection_lloq')
    native = grade_dialysis(r)['native']
    assert native['percent_bound_spread'] is None and native['free_over_lloq'] is None
    r['facts']['adsorption_checked_and_corrected'] = fact('unknown')
    assert grade_dialysis(r)['native']['adsorption_corrected'] is None
