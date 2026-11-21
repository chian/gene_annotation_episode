"""SEC grader: each criterion's rule on records, with the thresholds exercised on both sides."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_sec_record import FACTS, fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_sec_criteria, literature_sec_grader
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_criteria import SEC_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_sec_grader import CRITERIA, grade_sec
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.sec_cases import (
    qualitative_record, real_record, sparse_record, synthetic_record, weak_complex_record)

KD_DEPENDENT = ('stoichiometry', 'complex_stable_on_column')


def status(record, criterion):
    """The status of the criterion after the sheet side has judged the facts the grader recorded (the grader holds no threshold; the sheet-side constants are in the converter)."""
    return _criterion(grade_sec(record), criterion)['status']


def refs(record, criterion):
    return _criterion(grade_sec(record), criterion)['support_refs']


def grader_status(record, criterion):
    return grade_sec(record)['criteria'][criterion]['status']


def reason(record, criterion):
    return grade_sec(record)['reasons'][criterion]


def missing(record, *names):
    for name in names:
        record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_complete_synthetic_record_is_supported_everywhere_except_the_mass_which_the_sheet_judges():
    graded = grade_sec(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA and len(CRITERIA) == 13
    handed = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed == {'mals_mass', 'elution_shift', 'stoichiometry', 'complex_stable_on_column', 'monodispersity', 'replicates'}      # the resin is ruled out by its fact, no salt is judged
    assert all(graded['criteria'][name]['status'] == 'unknown' and graded['criteria'][name]['support_refs'] == [] for name in handed)
    assert {_criterion(graded, name)['status'] for name in CRITERIA} == {'supported'} and all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert graded['experiment_type'] == 'sec' and native['interaction'] == 'detected' and native['interaction_refs'] == ['span_exp_synthetic_sec_1']
    assert native['kd_nM'] == 200.0 and native['loaded_nM'] == 5000.0 and native['load_over_kd'] == pytest.approx(25.0) and native['shift_ml'] == 1.3 and native['salt_mM'] == 150.0
    assert native['mass_deviation_percent'] == pytest.approx(-2.0 / 54.0 * 100.0)
    assert native['column_type'] == 'superdex' and native['detection'] == 'light_scattering' and native['spread_kind'] == 'standard_error'


def test_the_criteria_are_the_sec_ones_and_there_is_no_other_binding_constant_criterion():
    assert not {'ki', 'ic50', 'kon', 'koff'} & set(CRITERIA)
    assert {'complex_peak_observed', 'elution_shift', 'components_alone', 'complex_composition', 'mals_mass', 'stoichiometry', 'column_calibration', 'resin_interaction', 'complex_stable_on_column', 'monodispersity', 'single_component_control', 'replicates'} <= set(CRITERIA)


def test_sparse_record_is_unknown_never_conflicting_and_only_the_stated_peak_is_supported():
    graded = grade_sec(sparse_record())
    assert {name for name, c in graded['criteria'].items() if c['status'] == 'supported'} == {'complex_peak_observed'}
    assert {name for name, c in graded['criteria'].items() if c['status'] == 'conflicting'} == set()
    assert {name for name, c in graded['criteria'].items() if c['status'] == 'not_applicable'} == set(KD_DEPENDENT)
    assert graded['native']['interaction'] == 'detected'


def test_a_record_with_no_apparent_kd_does_not_apply_the_kd_criteria_and_does_not_fail_them():
    graded = grade_sec(qualitative_record())
    for name in KD_DEPENDENT:
        assert graded['criteria'][name]['status'] == 'not_applicable' and graded['reasons'][name] == 'no_apparent_kd_reported', name
    assert {_criterion(graded, name)['status'] for name in CRITERIA if name not in KD_DEPENDENT} == {'supported'}
    assert graded['reasons']['mals_mass'] == 'mass_deviation_recorded_for_the_sheet'
    assert graded['native']['kd_nM'] is None and graded['native']['interaction'] == 'detected'


# A supported or a conflicting criterion rests on quoted spans: the ELISA lesson (the sheet refuses an interpretation without support).
def variants():
    out = [synthetic_record(), qualitative_record(), sparse_record(), real_record(), weak_complex_record()]
    for name in FACTS:
        for answer in ('no', 'unknown', 'not_applicable'):
            record = synthetic_record()
            record['facts'][name] = fact(answer, ['s'] if answer == 'no' else [])
            out.append(record)
            record = synthetic_record()                                         # the same fact with the numbers that could decide in its place removed
            missing(record, 'complex_mass_measured', 'loaded_concentration', 'polydispersity', 'salt_concentration')
            record['facts'][name] = fact(answer, ['s'] if answer == 'no' else [])
            out.append(record)
        record = synthetic_record()
        missing(record, 'complex_mass_measured', 'loaded_concentration', 'polydispersity', 'salt_concentration')
        out.append(record)
    for shift, earlier, complex_volume in ((0.3, None, None), (0.29, None, None), (None, 12.5, 12.0), (None, 12.5, 12.3), (None, 12.5, 13.0), (None, None, 12.0), (None, 12.5, None), (None, None, None)):
        record = synthetic_record()
        for name, value in (('elution_volume_shift', shift), ('component_elution_volume_earlier', earlier), ('complex_elution_volume', complex_volume)):
            if value is None:
                missing(record, name)
            else:
                record['quantities'][name] = point(value, 'mL', name, ['s'])
        out.append(record)
    for measured, theoretical in ((90.0, 100.0), (89.0, 100.0), (110.0, 100.0), (111.0, 100.0), (51.0, 100.0), (50.0, 100.0), (150.0, 100.0), (None, 100.0), (85.0, None)):
        for answer in ('yes', 'no', 'unknown'):
            record = synthetic_record()
            record['facts']['mals_mass_matches_complex'] = fact(answer, ['s'] if answer in ('yes', 'no') else [])
            for name, value in (('complex_mass_measured', measured), ('complex_mass_theoretical', theoretical)):
                if value is None:
                    missing(record, name)
                else:
                    record['quantities'][name] = point(value, 'kDa', name, ['s'])
            out.append(record)
    for ratio in (1.0, 1.09, 1.12, 0.91, 0.88, 2.0, 0.5, None):
        record = synthetic_record()
        if ratio is None:
            missing(record, 'stoichiometry_ratio')
        else:
            record['quantities']['stoichiometry_ratio'] = point(ratio, 'ratio', 'r', ['s'])
        out.append(record)
    for salt, unit in ((100.0, 'mM'), (99.0, 'mM'), (0.15, 'M'), (0.05, 'M'), (None, None)):
        for answer in ('yes', 'no', 'unknown', 'not_applicable'):
            record = synthetic_record()
            record['facts']['buffer_rules_out_resin_interaction'] = fact(answer, ['s'] if answer in ('yes', 'no') else [])
            if salt is None:
                missing(record, 'salt_concentration')
            else:
                record['quantities']['salt_concentration'] = point(salt, unit, 'salt', ['s'])
            out.append(record)
    for loaded, unit in ((2000.0, 'nM'), (1999.0, 'nM'), (2.0, 'uM'), (1.0, 'uM'), (None, None)):
        for answer in ('yes', 'no', 'unknown', 'not_applicable'):
            record = synthetic_record()                                          # KD 200 nM
            record['facts']['complex_stable_on_column'] = fact(answer, ['s'] if answer in ('yes', 'no') else [])
            if loaded is None:
                missing(record, 'loaded_concentration')
            else:
                record['quantities']['loaded_concentration'] = point(loaded, unit, 'l', ['s'])
            out.append(record)
            record = qualitative_record()
            record['facts']['complex_stable_on_column'] = fact(answer, ['s'] if answer in ('yes', 'no') else [])
            out.append(record)
    for polydispersity in (1.05, 1.06, 1.0, None):
        for answer in ('yes', 'no', 'unknown'):
            record = synthetic_record()
            record['facts']['aggregation_absent'] = fact(answer, ['s'] if answer in ('yes', 'no') else [])
            if polydispersity is None:
                missing(record, 'polydispersity')
            else:
                record['quantities']['polydispersity'] = point(polydispersity, 'ratio', 'p', ['s'])
            out.append(record)
    for count, independent in ((2, 'yes'), (3, 'no'), (None, 'yes'), (3, 'unknown'), (3, 'yes')):
        record = synthetic_record()
        record['facts']['independent_experiments'] = fact(independent, ['s'] if independent != 'unknown' else [])
        if count is None:
            missing(record, 'replicate_count')
        else:
            record['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        out.append(record)
    return out


def test_every_supported_or_conflicting_criterion_carries_support_refs():
    seen = set()
    for record in variants():
        graded = grade_sec(record)
        for name, outcome in graded['criteria'].items():
            if outcome['status'] in ('supported', 'conflicting'):
                seen.add((name, outcome['status'], graded['reasons'][name]))
                assert outcome['support_refs'], (record['experiment_ref'], name, graded['reasons'][name])
            else:
                assert outcome['support_refs'] == []
    # every supported or conflicting case the criteria declare was reached by some variant, and so was checked for its refs
    declared = {(criterion['id'], status, why) for criterion in SEC_CRITERIA for status, why, _ in criterion['returns'] if status in ('supported', 'conflicting')}
    assert seen == declared


def test_a_decided_criterion_cannot_be_built_without_support_refs():
    record = synthetic_record()
    record['facts']['components_run_alone'] = fact('yes')                  # a fact answered yes with no span: it cannot be supported
    with pytest.raises(ValueError, match='needs support refs'):
        grade_sec(record)


@pytest.mark.parametrize('criterion, name', [('complex_peak_observed', 'complex_peak_detected'), ('components_alone', 'components_run_alone'), ('complex_composition', 'complex_peak_analysed_by_sds_page'),
                                             ('titration_depletion', 'free_peak_decreases_with_titration'), ('column_calibration', 'column_calibrated_with_standards'),
                                             ('single_component_control', 'single_component_control_done')])
def test_a_one_fact_criterion_follows_its_fact(criterion, name):
    r = synthetic_record()
    assert (status(r, criterion), reason(r, criterion)) == ('supported', 'facts_answered_yes')
    r['facts'][name] = fact('no', ['s'])
    assert (status(r, criterion), reason(r, criterion)) == ('conflicting', 'fact_answered_no')
    r['facts'][name] = fact('unknown')
    assert (status(r, criterion), reason(r, criterion)) == ('unknown', 'fact_unknown')
    r['facts'][name] = fact('not_applicable')
    assert (status(r, criterion), reason(r, criterion)) == ('not_applicable', 'fact_not_applicable')


def test_the_complex_peak_must_elute_earlier_by_at_least_the_minimum_shift():
    r = synthetic_record()                                                                 # a stated shift of 1.3 mL
    assert (grader_status(r, 'elution_shift'), reason(r, 'elution_shift')) == ('unknown', 'elution_shift_recorded_for_the_sheet')
    for value, expected in ((0.3, 'supported'), (0.29, 'conflicting'), (5.0, 'supported'), (0.05, 'conflicting')):
        r['quantities']['elution_volume_shift'] = point(value, 'mL', 'sh', ['s'])
        assert status(r, 'elution_shift') == expected, value
    assert reason(r, 'elution_shift') == 'elution_shift_recorded_for_the_sheet' and grade_sec(r)['native']['shift_ml'] == 0.05
    missing(r, 'elution_volume_shift')                                                     # without a stated shift it is the earlier component alone minus the complex: 12.5 - 11.2
    assert (status(r, 'elution_shift'), reason(r, 'elution_shift')) == ('supported', 'elution_shift_recorded_for_the_sheet') and grade_sec(r)['native']['shift_ml'] == pytest.approx(1.3)
    assert refs(r, 'elution_shift') == grade_sec(r)['native']['shift_refs'] == ['span_exp_synthetic_sec_1']
    r['quantities']['complex_elution_volume'] = point(12.3, 'mL', 'c', ['s'])
    assert status(r, 'elution_shift') == 'conflicting' and grade_sec(r)['native']['shift_ml'] == pytest.approx(0.2)
    assert refs(r, 'elution_shift') == ['span_exp_synthetic_sec_1', 's']
    r['quantities']['complex_elution_volume'] = point(13.0, 'mL', 'c', ['s'])           # the mixture elutes LATER than the component: no complex peak
    assert status(r, 'elution_shift') == 'conflicting' and grade_sec(r)['native']['shift_ml'] == pytest.approx(-0.5)
    missing(r, 'complex_elution_volume')
    assert (status(r, 'elution_shift'), reason(r, 'elution_shift')) == ('unknown', 'elution_shift_not_given') and grade_sec(r)['native']['shift_ml'] is None
    r['quantities']['complex_elution_volume'] = point(11.2, 'mL', 'c', ['s'])
    missing(r, 'component_elution_volume_earlier')
    assert status(r, 'elution_shift') == 'unknown'


def test_a_stated_shift_wins_over_the_difference_of_the_volumes():
    r = synthetic_record()
    r['quantities']['elution_volume_shift'] = point(0.1, 'mL', 'sh', ['s_shift'])          # stated shift 0.1 although the volumes differ by 1.3: the stated number is the result
    assert status(r, 'elution_shift') == 'conflicting' and refs(r, 'elution_shift') == ['s_shift']


def test_the_mals_mass_is_recorded_as_facts_and_the_grader_judges_no_threshold():
    r = synthetic_record()                                                                 # 52 kDa measured against 54 kDa
    assert (grader_status(r, 'mals_mass'), reason(r, 'mals_mass')) == ('unknown', 'mass_deviation_recorded_for_the_sheet')
    r['quantities']['complex_mass_theoretical'] = point(100.0, 'kDa', 't', ['s_theory'])
    for measured, expected_deviation in ((90.0, -10.0), (110.0, 10.0), (100.0, 0.0), (85.0, -15.0), (51.0, -49.0), (50.0, -50.0), (160.0, 60.0)):
        r['quantities']['complex_mass_measured'] = point(measured, 'kDa', 'm', ['s_mass'])
        graded = grade_sec(r)
        assert (grader_status(r, 'mals_mass'), reason(r, 'mals_mass')) == ('unknown', 'mass_deviation_recorded_for_the_sheet'), measured
        assert graded['native']['mass_deviation_percent'] == pytest.approx(expected_deviation), measured
        assert graded['native']['mass_measured'] == measured and graded['native']['mass_theoretical'] == 100.0
        assert graded['native']['mass_support_refs'] == ['s_mass', 's_theory']
    assert not any(name.startswith('MASS_') for name in dir(literature_sec_criteria))      # no mass threshold is declared in the grader's criteria
    assert not any(name.startswith('MASS_') for name in dir(literature_sec_grader))
    assert SEC_CRITERIA[5]['id'] == 'mals_mass' and SEC_CRITERIA[5]['thresholds'] == ('PERCENT_PER_FRACTION',)   # only the unit conversion, no judgement value
    r['facts']['mals_mass_matches_complex'] = fact('yes', ['s'])                           # both masses stated: the fact does not decide
    assert grader_status(r, 'mals_mass') == 'unknown'
    missing(r, 'complex_mass_theoretical')                                                 # without the expected mass the fact decides
    assert (status(r, 'mals_mass'), reason(r, 'mals_mass')) == ('supported', 'facts_answered_yes')
    assert grade_sec(r)['native']['mass_deviation_percent'] is None and grade_sec(r)['native']['mass_support_refs'] == []
    r['facts']['mals_mass_matches_complex'] = fact('no', ['s'])
    assert (status(r, 'mals_mass'), reason(r, 'mals_mass')) == ('conflicting', 'fact_answered_no')
    r['facts']['mals_mass_matches_complex'] = fact('unknown')
    assert (status(r, 'mals_mass'), reason(r, 'mals_mass')) == ('unknown', 'fact_unknown')
    r['facts']['mals_mass_matches_complex'] = fact('not_applicable')
    assert (status(r, 'mals_mass'), reason(r, 'mals_mass')) == ('not_applicable', 'fact_not_applicable')


def test_a_kd_from_peak_areas_needs_a_one_to_one_complex():
    r = synthetic_record()
    assert (status(r, 'stoichiometry'), reason(r, 'stoichiometry')) == ('supported', 'stoichiometry_recorded_for_the_sheet')
    for ratio, expected in ((1.09, 'supported'), (0.91, 'supported'), (1.12, 'conflicting'), (0.88, 'conflicting'), (2.0, 'conflicting'), (0.5, 'conflicting')):
        r['quantities']['stoichiometry_ratio'] = point(ratio, 'ratio', 'r', ['s'])
        assert status(r, 'stoichiometry') == expected, ratio
    assert reason(r, 'stoichiometry') == 'stoichiometry_recorded_for_the_sheet' and grade_sec(r)['native']['stoichiometry_ratio'] == 0.5
    missing(r, 'stoichiometry_ratio')
    assert (status(r, 'stoichiometry'), reason(r, 'stoichiometry')) == ('unknown', 'stoichiometry_not_given')
    missing(r, 'kd')                                                                       # no KD: a qualitative complex of any stoichiometry is fine
    assert (status(r, 'stoichiometry'), reason(r, 'stoichiometry')) == ('not_applicable', 'no_apparent_kd_reported')
    r['quantities']['stoichiometry_ratio'] = point(2.0, 'ratio', 'r', ['s'])
    assert status(r, 'stoichiometry') == 'not_applicable'
    assert status(weak_complex_record(), 'stoichiometry') == 'conflicting'


def test_the_resin_is_ruled_out_by_the_statement_or_by_a_salt_of_at_least_the_minimum():
    r = synthetic_record()
    assert (status(r, 'resin_interaction'), reason(r, 'resin_interaction')) == ('supported', 'facts_answered_yes')
    r['facts']['buffer_rules_out_resin_interaction'] = fact('no', ['s'])                    # the proteins interacted with the resin, whatever the salt
    assert (status(r, 'resin_interaction'), reason(r, 'resin_interaction')) == ('conflicting', 'fact_answered_no')
    r['facts']['buffer_rules_out_resin_interaction'] = fact('unknown')
    assert (status(r, 'resin_interaction'), reason(r, 'resin_interaction')) == ('supported', 'salt_recorded_for_the_sheet')      # 150 mM
    assert refs(r, 'resin_interaction') == grade_sec(r)['native']['salt_refs'] == ['span_exp_synthetic_sec_1']
    for value, unit, expected in ((100.0, 'mM', 'supported'), (99.0, 'mM', 'unknown'), (0.1, 'M', 'supported'), (0.05, 'M', 'unknown')):
        r['quantities']['salt_concentration'] = point(value, unit, 'salt', ['s'])
        assert status(r, 'resin_interaction') == expected, (value, unit)
    assert reason(r, 'resin_interaction') == 'salt_recorded_for_the_sheet' and grade_sec(r)['native']['salt_mM'] == pytest.approx(50.0)
    missing(r, 'salt_concentration')
    assert (status(r, 'resin_interaction'), reason(r, 'resin_interaction')) == ('unknown', 'fact_unknown')
    r['facts']['buffer_rules_out_resin_interaction'] = fact('not_applicable')
    assert (status(r, 'resin_interaction'), reason(r, 'resin_interaction')) == ('not_applicable', 'fact_not_applicable')


def test_the_injected_concentration_must_be_at_least_ten_times_the_kd_for_the_complex_to_survive_the_dilution():
    r = synthetic_record()                                                                 # 5000 nM injected, KD 200 nM
    assert (status(r, 'complex_stable_on_column'), reason(r, 'complex_stable_on_column')) == ('supported', 'load_over_kd_recorded_for_the_sheet')
    r['quantities']['loaded_concentration'] = point(2000.0, 'nM', 'l', ['s'])               # exactly ten times: allowed
    assert status(r, 'complex_stable_on_column') == 'supported'
    r['quantities']['loaded_concentration'] = point(1999.0, 'nM', 'l', ['s'])
    assert (status(r, 'complex_stable_on_column'), reason(r, 'complex_stable_on_column')) == ('conflicting', 'load_over_kd_recorded_for_the_sheet')
    r['quantities']['loaded_concentration'] = point(1.0, 'uM', 'l', ['s'])                  # 1000 nM in micromolar
    assert status(r, 'complex_stable_on_column') == 'conflicting' and grade_sec(r)['native']['loaded_nM'] == pytest.approx(1000.0)
    r['facts']['complex_stable_on_column'] = fact('yes', ['s'])                             # the numbers decide, not the fact
    assert status(r, 'complex_stable_on_column') == 'conflicting'
    missing(r, 'loaded_concentration')                                                      # without the number the fact decides
    assert (status(r, 'complex_stable_on_column'), reason(r, 'complex_stable_on_column')) == ('supported', 'facts_answered_yes')
    r['facts']['complex_stable_on_column'] = fact('no', ['s'])
    assert (status(r, 'complex_stable_on_column'), reason(r, 'complex_stable_on_column')) == ('conflicting', 'fact_answered_no')
    r['facts']['complex_stable_on_column'] = fact('unknown')
    assert (status(r, 'complex_stable_on_column'), reason(r, 'complex_stable_on_column')) == ('unknown', 'fact_unknown')
    missing(r, 'kd')                                                                        # a record with no KD: nothing to bias
    assert (status(r, 'complex_stable_on_column'), reason(r, 'complex_stable_on_column')) == ('not_applicable', 'no_apparent_kd_reported')
    r['facts']['complex_stable_on_column'] = fact('yes', ['s'])
    assert status(r, 'complex_stable_on_column') == 'supported'                             # a stated stability is still judged
    r['facts']['complex_stable_on_column'] = fact('not_applicable')
    assert (status(r, 'complex_stable_on_column'), reason(r, 'complex_stable_on_column')) == ('not_applicable', 'fact_not_applicable')


def test_a_polydispersity_above_the_maximum_is_aggregation_and_without_it_the_fact_decides():
    r = synthetic_record()
    assert (status(r, 'monodispersity'), reason(r, 'monodispersity')) == ('supported', 'polydispersity_recorded_for_the_sheet')
    for value, expected in ((1.05, 'supported'), (1.06, 'conflicting'), (1.0, 'supported'), (1.5, 'conflicting')):
        r['quantities']['polydispersity'] = point(value, 'ratio', 'p', ['s'])
        assert status(r, 'monodispersity') == expected, value
    assert reason(r, 'monodispersity') == 'polydispersity_recorded_for_the_sheet' and grade_sec(r)['native']['polydispersity'] == 1.5
    r['facts']['aggregation_absent'] = fact('yes', ['s'])                                   # the number decides, not the fact
    assert status(r, 'monodispersity') == 'conflicting'
    missing(r, 'polydispersity')
    assert (status(r, 'monodispersity'), reason(r, 'monodispersity')) == ('supported', 'facts_answered_yes')
    r['facts']['aggregation_absent'] = fact('no', ['s'])
    assert (status(r, 'monodispersity'), reason(r, 'monodispersity')) == ('conflicting', 'fact_answered_no')
    r['facts']['aggregation_absent'] = fact('unknown')
    assert (status(r, 'monodispersity'), reason(r, 'monodispersity')) == ('unknown', 'fact_unknown')
    r['facts']['aggregation_absent'] = fact('not_applicable')
    assert (status(r, 'monodispersity'), reason(r, 'monodispersity')) == ('not_applicable', 'fact_not_applicable')


def test_replicates_are_independent_experiments_and_injections_of_one_sample_do_not_count():
    r = synthetic_record()
    assert reason(r, 'replicates') == 'replicate_count_recorded_for_the_sheet' and status(r, 'replicates') == 'supported'
    native = grade_sec(r)['native']
    assert native['replicate_count'] == 3 and native['replicate_independent'] == 'yes' and native['replicate_refs']
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    assert reason(r, 'replicates') == 'replicate_count_recorded_for_the_sheet' and status(r, 'replicates') == 'conflicting'
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    r['facts']['independent_experiments'] = fact('no', ['s'])
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('conflicting', 'replicates_not_independent')       # a fact, judged by the grader
    r['facts']['independent_experiments'] = fact('unknown')
    assert reason(r, 'replicates') == 'replicate_count_recorded_for_the_sheet' and status(r, 'replicates') == 'unknown'
    r['facts']['independent_experiments'] = fact('yes', ['s'])
    missing(r, 'replicate_count')
    assert status(r, 'replicates') == 'unknown'


def test_the_qualitative_statement_follows_the_complex_peak_fact():
    r = synthetic_record()
    assert grade_sec(r)['native']['interaction'] == 'detected'
    r['facts']['complex_peak_detected'] = fact('no', ['span_no'])
    native = grade_sec(r)['native']
    assert native['interaction'] == 'not_detected' and native['interaction_refs'] == ['span_no']
    for answer in ('unknown', 'not_applicable'):
        r['facts']['complex_peak_detected'] = fact(answer)
        native = grade_sec(r)['native']
        assert native['interaction'] is None and native['interaction_refs'] == []


def test_the_grader_keeps_the_support_of_the_fields_each_criterion_reads_and_does_not_judge_it():
    r = synthetic_record()
    r['facts']['complex_peak_detected']['support'] = 'implied'
    r['quantities']['replicate_count']['support'] = 'about_something_else'
    graded = grade_sec(r)
    support = graded['native']['support']
    assert set(support) == set(CRITERIA)
    assert support['complex_peak_observed'] == ['implied'] and 'about_something_else' in support['replicates']
    assert graded['criteria']['complex_peak_observed']['status'] == 'supported'      # the status is the grader's own: support does not change it
    assert grade_sec(sparse_record())['native']['support']['components_alone'] == []      # an unknown fact is not stated: no support
