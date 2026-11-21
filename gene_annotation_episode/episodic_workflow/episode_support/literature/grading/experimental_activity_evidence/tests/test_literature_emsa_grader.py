"""EMSA grader: each criterion's rule on records, with the thresholds exercised on both sides."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_emsa_record import FACTS, fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_criteria import EMSA_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_emsa_grader import CRITERIA, grade_emsa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.emsa_cases import (
    multiple_species_record, qualitative_record, real_record, sparse_record, synthetic_record)

KD_DEPENDENT = ('probe_concentration', 'protein_range', 'titration_points', 'saturation', 'fit_model')


def status(record, criterion):
    """The status of the criterion after the sheet side has judged the facts the grader recorded (the grader holds no threshold; the sheet-side constants are in the converter)."""
    return _criterion(grade_emsa(record), criterion)['status']


def judged(record, criterion):
    return _criterion(grade_emsa(record), criterion)


def grader_status(record, criterion):
    return grade_emsa(record)['criteria'][criterion]['status']


def reason(record, criterion):
    return grade_emsa(record)['reasons'][criterion]


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_complete_synthetic_record_is_supported_everywhere_once_the_sheet_has_judged_the_recorded_numbers():
    graded = grade_emsa(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA and len(CRITERIA) == 17
    handed = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed == {'probe_concentration', 'protein_range', 'titration_points', 'saturation', 'single_complex', 'fit_model', 'replicates'}      # the competition and the equilibrium are stated by their facts; the fit is one-site with a stated probe
    assert all(graded['criteria'][name]['status'] == 'unknown' and graded['criteria'][name]['support_refs'] == [] for name in handed)
    assert {_criterion(graded, name)['status'] for name in CRITERIA} == {'supported'} and all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['titration_point_count'] == 11 and native['fraction_shifted_percent'] == 92.0 and native['shifted_species_count'] == 1 and native['replicate_count'] == 3 and native['replicate_independent'] == 'yes'
    assert graded['experiment_type'] == 'emsa' and native['interaction'] == 'detected' and native['interaction_refs'] == ['span_exp_synthetic_emsa_1']
    assert native['kd_nM'] == 20.0 and native['probe_nM'] == 0.5 and native['probe_over_kd'] == pytest.approx(0.025)
    assert native['protein_low_over_kd'] == pytest.approx(0.05) and native['protein_high_over_kd'] == pytest.approx(32.0) and native['incubation_min'] == 30.0
    assert native['probe_type'] == 'dsdna' and native['probe_label'] == 'p32' and native['gel_type'] == 'native_polyacrylamide' and native['fit_model'] == 'one_site'


def test_the_criteria_are_the_emsa_ones_and_there_is_no_other_binding_constant_criterion():
    assert not {'ki', 'ic50', 'kon', 'koff'} & set(CRITERIA)
    assert {'specific_competition', 'nonspecific_competition', 'mutant_probe', 'probe_alone_lane', 'protein_identity', 'probe_concentration', 'protein_range', 'complex_stability', 'single_complex', 'fit_model'} <= set(CRITERIA)


def test_sparse_record_is_unknown_never_conflicting_and_only_the_stated_shift_is_supported():
    graded = grade_emsa(sparse_record())
    assert {name for name, c in graded['criteria'].items() if c['status'] == 'supported'} == {'shift_observed'}
    assert {name for name, c in graded['criteria'].items() if c['status'] == 'conflicting'} == set()
    assert {name for name, c in graded['criteria'].items() if c['status'] == 'not_applicable'} == {'probe_concentration', 'protein_range', 'titration_points', 'saturation', 'fit_model'}
    assert graded['native']['interaction'] == 'detected'


def test_a_record_with_no_apparent_kd_does_not_apply_the_kd_criteria_and_does_not_fail_them():
    graded = grade_emsa(qualitative_record())
    for name in KD_DEPENDENT:
        assert graded['criteria'][name]['status'] == 'not_applicable' and graded['reasons'][name] == 'no_apparent_kd_reported', name
    assert {_criterion(graded, name)['status'] for name in CRITERIA if name not in KD_DEPENDENT} == {'supported'}
    assert graded['native']['kd_nM'] is None and graded['native']['interaction'] == 'detected'


# A supported or a conflicting criterion rests on quoted spans: the ELISA lesson (the sheet refuses an interpretation without support).
def variants():
    out = [synthetic_record(), qualitative_record(), sparse_record(), real_record(), multiple_species_record()]
    for name in FACTS:
        for answer in ('no', 'unknown', 'not_applicable'):
            record = synthetic_record()
            record['facts'][name] = fact(answer, ['s'] if answer == 'no' else [])
            out.append(record)
    for supershift, purified in (('yes', 'unknown'), ('unknown', 'yes'), ('no', 'no'), ('no', 'yes'), ('no', 'unknown'), ('not_applicable', 'not_applicable'), ('no', 'not_applicable'), ('unknown', 'unknown')):
        record = synthetic_record()
        for name, answer in (('supershift_confirms_protein_identity', supershift), ('protein_purified', purified)):
            record['facts'][name] = fact(answer, ['s'] if answer in ('yes', 'no') else [])
        out.append(record)
    for excess, answer in ((None, 'no'), (49.0, 'no'), (50.0, 'no'), (10.0, 'yes'), (None, 'unknown')):
        record = synthetic_record()
        record['facts']['shift_abolished_by_specific_competitor'] = fact(answer, ['s'] if answer in ('yes', 'no') else [])
        if excess is None:
            missing(record, 'specific_competitor_excess')
        else:
            record['quantities']['specific_competitor_excess'] = point(excess, 'ratio', 'x', ['s'])
        out.append(record)
    for value in (14.0, 15.0, 0.2, None):                                  # incubation, with the equilibrium fact unknown
        record = synthetic_record()
        record['facts']['equilibrium_reached'] = fact('unknown')
        if value is None:
            missing(record, 'incubation_time')
        else:
            record['quantities']['incubation_time'] = point(value, 'h' if value == 0.2 else 'min', 'i', ['s'])
        out.append(record)
    for probe, unit in ((20.0, 'nM'), (20.1, 'nM'), (0.5, 'uM'), (None, None)):          # the probe against the KD (20 nM), with and without the number
        for answer in ('yes', 'no', 'unknown', 'not_applicable'):
            record = synthetic_record()
            record['facts']['probe_at_or_below_kd'] = fact(answer, ['s'] if answer in ('yes', 'no') else [])
            if probe is None:
                missing(record, 'probe_concentration')
            else:
                record['quantities']['probe_concentration'] = point(probe, unit, 'p', ['s'])
            out.append(record)
    for low, high in ((5.0, 100.0), (5.1, 100.0), (5.0, 99.0), (None, 100.0), (5.0, None)):
        for answer in ('yes', 'no', 'unknown'):
            record = synthetic_record()
            record['facts']['protein_range_brackets_kd'] = fact(answer, ['s'] if answer in ('yes', 'no') else [])
            for name, value in (('protein_concentration_lowest', low), ('protein_concentration_highest', high)):
                if value is None:
                    missing(record, name)
                else:
                    record['quantities'][name] = point(value, 'nM', name, ['s'])
            out.append(record)
    for name, values, unit in (('titration_point_count', (5, 6, None), 'count'), ('fraction_shifted_highest', (79.0, 80.0, None), 'percent'), ('shifted_species_count', (1, 2, None), 'count'), ('replicate_count', (2, 3, None), 'count')):
        for value in values:
            record = synthetic_record()
            if value is None:
                missing(record, name)
            else:
                record['quantities'][name] = point(value, unit, name, ['s'])
            out.append(record)
    for model in (None, 'one_site', 'hill', 'quadratic', 'two_site', 'other'):
        for species in (1, 2):
            record = synthetic_record()
            record['fit_model'] = model
            record['quantities']['shifted_species_count'] = point(species, 'count', 's', ['s'])
            out.append(record)
        record = synthetic_record()                                         # a probe above the KD with each model
        record['fit_model'] = model
        record['quantities']['probe_concentration'] = point(50.0, 'nM', 'p', ['s'])
        out.append(record)
    for count, independent in ((2, 'yes'), (3, 'no'), (None, 'yes'), (3, 'unknown')):
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
        graded = grade_emsa(record)
        for name, outcome in graded['criteria'].items():
            if outcome['status'] in ('supported', 'conflicting'):
                seen.add((name, outcome['status'], graded['reasons'][name]))
                assert outcome['support_refs'], (record['experiment_ref'], name, graded['reasons'][name])
            else:
                assert outcome['support_refs'] == []
    # every supported or conflicting case the criteria declare was reached by some variant, and so was checked for its refs
    declared = {(criterion['id'], status, why) for criterion in EMSA_CRITERIA for status, why, _ in criterion['returns'] if status in ('supported', 'conflicting')}
    assert seen == declared


def test_a_decided_criterion_cannot_be_built_without_support_refs():
    record = synthetic_record()
    record['facts']['probe_alone_lane_shown'] = fact('yes')               # a fact answered yes with no span: it cannot be supported
    with pytest.raises(ValueError, match='needs support refs'):
        grade_emsa(record)


@pytest.mark.parametrize('criterion, name', [('shift_observed', 'shift_detected'), ('nonspecific_competition', 'shift_not_abolished_by_nonspecific_competitor'), ('mutant_probe', 'mutant_probe_does_not_shift'),
                                             ('probe_alone_lane', 'probe_alone_lane_shown'), ('nonspecific_protein_control', 'nonspecific_protein_control_done'), ('free_probe_quantified', 'free_probe_quantified'),
                                             ('complex_stability', 'complex_survives_gel_run')])
def test_a_one_fact_criterion_follows_its_fact(criterion, name):
    r = synthetic_record()
    assert (status(r, criterion), reason(r, criterion)) == ('supported', 'facts_answered_yes')
    r['facts'][name] = fact('no', ['s'])
    assert (status(r, criterion), reason(r, criterion)) == ('conflicting', 'fact_answered_no')
    r['facts'][name] = fact('unknown')
    assert (status(r, criterion), reason(r, criterion)) == ('unknown', 'fact_unknown')
    r['facts'][name] = fact('not_applicable')
    assert (status(r, criterion), reason(r, criterion)) == ('not_applicable', 'fact_not_applicable')


def test_a_specific_competitor_that_did_not_abolish_the_shift_is_recorded_with_its_excess_for_the_sheet_to_judge():
    r = synthetic_record()                                                                 # 100-fold excess, abolished
    assert (status(r, 'specific_competition'), reason(r, 'specific_competition')) == ('supported', 'facts_answered_yes')
    r['facts']['shift_abolished_by_specific_competitor'] = fact('no', ['s_no'])
    graded = grade_emsa(r)                                                                  # a stated 100-fold excess: recorded, handed over
    assert (graded['criteria']['specific_competition'], graded['reasons']['specific_competition']) == ({'status': 'unknown', 'support_refs': []}, 'competition_excess_recorded_for_the_sheet')
    assert graded['native']['specific_competitor_excess'] == 100.0 and graded['native']['specific_competition_refs'] == ['s_no']
    assert judged(r, 'specific_competition') == {'status': 'conflicting', 'support_refs': ['s_no']}
    r['quantities']['specific_competitor_excess'] = point(50.0, 'ratio', 'x', ['s'])        # exactly the sheet's minimum: a fair test, so it fails
    assert status(r, 'specific_competition') == 'conflicting'
    r['quantities']['specific_competitor_excess'] = point(49.0, 'ratio', 'x', ['s'])
    assert judged(r, 'specific_competition') == {'status': 'unknown', 'support_refs': []} and grader_status(r, 'specific_competition') == 'unknown'
    missing(r, 'specific_competitor_excess')                                                # no excess stated: the fact decides, in the grader
    assert (grader_status(r, 'specific_competition'), reason(r, 'specific_competition')) == ('conflicting', 'fact_answered_no') and status(r, 'specific_competition') == 'conflicting'
    r['quantities']['specific_competitor_excess'] = point(10.0, 'ratio', 'x', ['s'])
    r['facts']['shift_abolished_by_specific_competitor'] = fact('yes', ['s'])              # a small excess that abolished the shift is fine
    assert status(r, 'specific_competition') == 'supported'
    r['facts']['shift_abolished_by_specific_competitor'] = fact('unknown')
    assert (status(r, 'specific_competition'), reason(r, 'specific_competition')) == ('unknown', 'fact_unknown')


def test_the_protein_is_known_by_a_purified_protein_or_a_supershift():
    r = synthetic_record()
    assert (status(r, 'protein_identity'), reason(r, 'protein_identity')) == ('supported', 'protein_identity_confirmed')
    r['facts']['protein_purified'] = fact('no', ['s'])                                     # a crude extract, but the supershift confirms the protein
    assert status(r, 'protein_identity') == 'supported' and grade_emsa(r)['criteria']['protein_identity']['support_refs'] == ['span_exp_synthetic_emsa_1']
    r['facts']['supershift_confirms_protein_identity'] = fact('no', ['s'])                 # a crude extract and an antibody that did not confirm
    assert (status(r, 'protein_identity'), reason(r, 'protein_identity')) == ('conflicting', 'protein_identity_not_confirmed')
    r['facts']['supershift_confirms_protein_identity'] = fact('unknown')
    assert (status(r, 'protein_identity'), reason(r, 'protein_identity')) == ('unknown', 'protein_identity_unknown')
    r['facts']['supershift_confirms_protein_identity'] = fact('not_applicable')
    r['facts']['protein_purified'] = fact('not_applicable')
    assert (status(r, 'protein_identity'), reason(r, 'protein_identity')) == ('not_applicable', 'fact_not_applicable')


def test_equilibrium_is_the_fact_and_a_short_incubation_fails_only_when_the_fact_is_not_stated():
    r = synthetic_record()
    assert (status(r, 'equilibrium'), reason(r, 'equilibrium')) == ('supported', 'facts_answered_yes')
    r['facts']['equilibrium_reached'] = fact('unknown')
    for value, unit, expected in ((15.0, 'min', 'unknown'), (14.0, 'min', 'conflicting'), (0.2, 'h', 'conflicting'), (800.0, 's', 'conflicting'), (900.0, 's', 'unknown'), (1.0, 'h', 'unknown')):
        r['quantities']['incubation_time'] = point(value, unit, 'i', ['s'])
        assert status(r, 'equilibrium') == expected, (value, unit)
    assert (grader_status(r, 'equilibrium'), reason(r, 'equilibrium')) == ('unknown', 'incubation_recorded_for_the_sheet') and grade_emsa(r)['native']['incubation_min'] == 60.0     # the grader records it; the sheet judges it
    r['quantities']['incubation_time'] = point(5.0, 'min', 'i', ['s'])
    assert judged(r, 'equilibrium') == {'status': 'conflicting', 'support_refs': ['s']} and grade_emsa(r)['native']['incubation_refs'] == ['s']
    r['facts']['equilibrium_reached'] = fact('yes', ['s'])                                  # a stated time course outweighs a short incubation
    assert status(r, 'equilibrium') == 'supported'
    missing(r, 'incubation_time')
    r['facts']['equilibrium_reached'] = fact('unknown')
    assert (status(r, 'equilibrium'), reason(r, 'equilibrium')) == ('unknown', 'fact_unknown')


def test_the_probe_over_the_kd_is_recorded_and_the_sheet_judges_it_with_a_degree():
    r = synthetic_record()                                                                 # 0.5 nM probe, 20 nM KD
    graded = grade_emsa(r)
    assert (graded['criteria']['probe_concentration'], graded['reasons']['probe_concentration']) == ({'status': 'unknown', 'support_refs': []}, 'probe_over_kd_recorded_for_the_sheet')
    assert graded['native']['probe_over_kd'] == pytest.approx(0.025) and graded['native']['probe_over_kd_refs'] == ['span_exp_synthetic_emsa_1']
    assert status(r, 'probe_concentration') == 'supported'
    r['quantities']['probe_concentration'] = point(20.0, 'nM', 'p', ['s'])                 # exactly the KD, the sheet's full-agreement limit
    assert judged(r, 'probe_concentration')['status'] == 'supported' and judged(r, 'probe_concentration')['degree'] == 1.0
    r['quantities']['probe_concentration'] = point(110.0, 'nM', 'p', ['s'])                # 5.5 x the KD: halfway to the zero limit of 10 x
    assert judged(r, 'probe_concentration')['degree'] == pytest.approx(0.5)
    r['quantities']['probe_concentration'] = point(0.2, 'uM', 'p', ['s'])                  # 200 nM in micromolar: ten times the KD, the zero limit
    assert status(r, 'probe_concentration') == 'conflicting' and 'degree' not in judged(r, 'probe_concentration') and grade_emsa(r)['native']['probe_nM'] == pytest.approx(200.0)
    r['facts']['probe_at_or_below_kd'] = fact('yes', ['s'])                                # the numbers decide, not the fact
    assert status(r, 'probe_concentration') == 'conflicting'
    missing(r, 'probe_concentration')                                                      # without the number the fact decides
    assert (status(r, 'probe_concentration'), reason(r, 'probe_concentration')) == ('supported', 'facts_answered_yes')
    r['facts']['probe_at_or_below_kd'] = fact('no', ['s'])
    assert (status(r, 'probe_concentration'), reason(r, 'probe_concentration')) == ('conflicting', 'fact_answered_no')
    r['facts']['probe_at_or_below_kd'] = fact('unknown')
    assert (status(r, 'probe_concentration'), reason(r, 'probe_concentration')) == ('unknown', 'fact_unknown')
    missing(r, 'kd')                                                                       # a record with no KD: nothing to bias
    assert (status(r, 'probe_concentration'), reason(r, 'probe_concentration')) == ('not_applicable', 'no_apparent_kd_reported')
    r['facts']['probe_at_or_below_kd'] = fact('yes', ['s'])
    assert status(r, 'probe_concentration') == 'supported'


def test_the_protein_concentrations_over_the_kd_are_recorded_and_the_sheet_judges_the_span_with_a_degree():
    r = synthetic_record()                                                                 # KD 20 nM: lowest 1 nM, highest 640 nM
    graded = grade_emsa(r)
    assert (graded['criteria']['protein_range'], graded['reasons']['protein_range']) == ({'status': 'unknown', 'support_refs': []}, 'protein_range_recorded_for_the_sheet')
    assert graded['native']['protein_low_over_kd'] == pytest.approx(0.05) and graded['native']['protein_high_over_kd'] == pytest.approx(32.0) and graded['native']['protein_range_refs'] == ['span_exp_synthetic_emsa_1']
    assert status(r, 'protein_range') == 'supported'
    for low, high, expected, degree in ((5.0, 100.0, 'supported', 1.0), (12.5, 100.0, 'supported', 0.5), (5.0, 60.0, 'supported', 0.5), (12.5, 60.0, 'supported', 0.5), (5.0, 20.0, 'conflicting', None), (20.0, 640.0, 'conflicting', None)):
        r['quantities']['protein_concentration_lowest'] = point(low, 'nM', 'l', ['s'])
        r['quantities']['protein_concentration_highest'] = point(high, 'nM', 'h', ['s'])
        verdict = judged(r, 'protein_range')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), (low, high)
    r['quantities']['protein_concentration_lowest'] = point(0.005, 'uM', 'l', ['s'])        # 5 nM in micromolar
    r['quantities']['protein_concentration_highest'] = point(0.1, 'uM', 'h', ['s'])
    assert status(r, 'protein_range') == 'supported'
    missing(r, 'protein_concentration_highest')
    assert (status(r, 'protein_range'), reason(r, 'protein_range')) == ('supported', 'facts_answered_yes')
    r['facts']['protein_range_brackets_kd'] = fact('no', ['s'])
    assert (status(r, 'protein_range'), reason(r, 'protein_range')) == ('conflicting', 'fact_answered_no')
    r['facts']['protein_range_brackets_kd'] = fact('unknown')
    assert (status(r, 'protein_range'), reason(r, 'protein_range')) == ('unknown', 'fact_unknown')
    missing(r, 'kd')
    assert (status(r, 'protein_range'), reason(r, 'protein_range')) == ('not_applicable', 'no_apparent_kd_reported')


def test_the_titration_needs_enough_points_and_the_shifted_fraction_a_plateau():
    r = synthetic_record()
    assert (grader_status(r, 'titration_points'), reason(r, 'titration_points')) == ('unknown', 'titration_points_recorded_for_the_sheet') and grade_emsa(r)['native']['titration_point_count'] == 11
    for count, expected in ((6, 'supported'), (5, 'conflicting'), (12, 'supported')):
        r['quantities']['titration_point_count'] = point(count, 'count', 't', ['s'])
        assert status(r, 'titration_points') == expected, count
        assert judged(r, 'titration_points')['support_refs'] == ['s'] and 'degree' not in judged(r, 'titration_points')
    missing(r, 'titration_point_count')
    assert (status(r, 'titration_points'), reason(r, 'titration_points')) == ('unknown', 'titration_point_count_not_given')
    assert (grader_status(r, 'saturation'), reason(r, 'saturation')) == ('unknown', 'fraction_shifted_recorded_for_the_sheet') and grade_emsa(r)['native']['fraction_shifted_percent'] == 92.0
    for percent, expected, degree in ((80.0, 'supported', 1.0), (100.0, 'supported', 1.0), (65.0, 'supported', 0.5), (79.0, 'supported', 29 / 30), (50.0, 'conflicting', None), (40.0, 'conflicting', None)):
        r['quantities']['fraction_shifted_highest'] = point(percent, 'percent', 'f', ['s'])
        verdict = judged(r, 'saturation')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), percent
        assert verdict['support_refs'] == ['s']
    missing(r, 'fraction_shifted_highest')
    assert (status(r, 'saturation'), reason(r, 'saturation')) == ('unknown', 'fraction_shifted_not_given')
    missing(r, 'kd')                                                                       # no KD: the plateau and the points are not applicable
    assert (status(r, 'saturation'), reason(r, 'saturation')) == ('not_applicable', 'no_apparent_kd_reported') and status(r, 'titration_points') == 'not_applicable'


def test_one_shifted_species_is_fine_and_several_need_a_model_with_more_than_one_site():
    r = synthetic_record()
    assert (grader_status(r, 'single_complex'), reason(r, 'single_complex')) == ('unknown', 'shifted_species_recorded_for_the_sheet') and grade_emsa(r)['native']['shifted_species_count'] == 1
    assert judged(r, 'single_complex') == {'status': 'supported', 'support_refs': ['span_exp_synthetic_emsa_1']} and grade_emsa(r)['native']['shifted_species_refs'] == ['span_exp_synthetic_emsa_1']
    r['quantities']['shifted_species_count'] = point(2, 'count', 's', ['s'])
    assert judged(r, 'single_complex') == {'status': 'conflicting', 'support_refs': ['s', 'span_exp_synthetic_emsa_1']}       # the synthetic fit is one-site; the refs of the count and of the KD
    r['fit_model'] = 'quadratic'
    assert status(r, 'single_complex') == 'conflicting'
    for model in ('hill', 'two_site', 'other'):
        r['fit_model'] = model
        assert status(r, 'single_complex') == 'supported' and judged(r, 'single_complex')['support_refs'] == ['s', 'span_exp_synthetic_emsa_1']
    r['fit_model'] = None
    assert status(r, 'single_complex') == 'unknown'
    missing(r, 'kd')
    assert (grader_status(r, 'single_complex'), status(r, 'single_complex')) == ('unknown', 'not_applicable')                   # several species and no apparent KD: not applicable, judged by the sheet
    missing(r, 'shifted_species_count')
    assert (status(r, 'single_complex'), reason(r, 'single_complex')) == ('unknown', 'shifted_species_count_not_given')
    assert status(multiple_species_record(), 'single_complex') == 'conflicting'


def test_a_one_site_model_is_judged_by_the_sheet_against_the_probe_and_a_quadratic_one_is_not():
    r = synthetic_record()                                                                 # one-site model, probe 0.025 x the KD
    assert (grader_status(r, 'fit_model'), reason(r, 'fit_model')) == ('unknown', 'one_site_probe_over_kd_recorded_for_the_sheet')
    assert judged(r, 'fit_model') == {'status': 'supported', 'support_refs': ['span_exp_synthetic_emsa_1'], 'degree': 1.0}
    r['quantities']['probe_concentration'] = point(110.0, 'nM', 'p', ['s'])                # 5.5 x the KD
    assert judged(r, 'fit_model')['status'] == 'supported' and judged(r, 'fit_model')['degree'] == pytest.approx(0.5)
    r['quantities']['probe_concentration'] = point(200.0, 'nM', 'p', ['s'])                # ten times the KD
    assert status(r, 'fit_model') == 'conflicting'
    assert grade_emsa(r)['native']['fit_model_probe_refs'] == ['span_exp_synthetic_emsa_1', 's'] and judged(r, 'fit_model')['support_refs'] == ['span_exp_synthetic_emsa_1', 's']          # the spans of the KD and of the probe concentration
    missing(r, 'probe_concentration')                                                      # no probe stated: the model is only stated, as the grader answers
    assert (grader_status(r, 'fit_model'), reason(r, 'fit_model')) == ('supported', 'model_stated')
    r['quantities']['probe_concentration'] = point(200.0, 'nM', 'p', ['s'])
    r['fit_model'] = 'quadratic'
    assert (status(r, 'fit_model'), reason(r, 'fit_model')) == ('supported', 'model_stated')
    r['fit_model'] = None
    assert (status(r, 'fit_model'), reason(r, 'fit_model')) == ('unknown', 'fit_model_not_stated')
    missing(r, 'kd')
    assert (status(r, 'fit_model'), reason(r, 'fit_model')) == ('not_applicable', 'no_apparent_kd_reported')
    r['fit_model'] = 'one_site'
    assert (status(r, 'fit_model'), reason(r, 'fit_model')) == ('not_applicable', 'no_apparent_kd_reported')


def test_replicates_are_independent_experiments_and_lanes_do_not_count():
    r = synthetic_record()
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('unknown', 'replicate_count_recorded_for_the_sheet')
    assert grade_emsa(r)['native']['replicate_count'] == 3 and grade_emsa(r)['native']['replicate_independent'] == 'yes' and status(r, 'replicates') == 'supported'
    for count, independent, expected in ((3, 'yes', 'supported'), (10, 'yes', 'supported'), (2, 'yes', 'conflicting'), (2, 'unknown', 'conflicting'), (3, 'unknown', 'unknown')):
        r['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        r['facts']['independent_experiments'] = fact(independent, ['s'] if independent != 'unknown' else [])
        assert status(r, 'replicates') == expected, (count, independent)
        assert 'degree' not in judged(r, 'replicates')
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    r['facts']['independent_experiments'] = fact('no', ['s'])
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('conflicting', 'replicates_not_independent')       # a fact, judged by the grader
    r['facts']['independent_experiments'] = fact('yes', ['s'])
    missing(r, 'replicate_count')
    assert (status(r, 'replicates'), reason(r, 'replicates')) == ('unknown', 'replicate_count_or_independence_unknown')


def test_the_qualitative_statement_follows_the_shift_fact():
    r = synthetic_record()
    assert grade_emsa(r)['native']['interaction'] == 'detected'
    r['facts']['shift_detected'] = fact('no', ['span_no'])
    native = grade_emsa(r)['native']
    assert native['interaction'] == 'not_detected' and native['interaction_refs'] == ['span_no']
    for answer in ('unknown', 'not_applicable'):
        r['facts']['shift_detected'] = fact(answer)
        native = grade_emsa(r)['native']
        assert native['interaction'] is None and native['interaction_refs'] == []


def test_the_grader_keeps_the_support_of_the_fields_each_criterion_reads_and_does_not_judge_it():
    r = synthetic_record()
    r['facts']['shift_detected']['support'] = 'implied'
    r['quantities']['replicate_count']['support'] = 'about_something_else'
    graded = grade_emsa(r)
    support = graded['native']['support']
    assert set(support) == set(CRITERIA)
    assert support['shift_observed'] == ['implied'] and 'about_something_else' in support['replicates']
    assert graded['criteria']['shift_observed']['status'] == 'supported'      # the status is the grader's own: support does not change it
    assert grade_emsa(sparse_record())['native']['support']['specific_competition'] == []      # an unknown fact is not stated: no support
