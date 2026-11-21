"""AlphaScreen grader: each criterion's rule on records, with the arithmetic worked by hand."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_alpha_record import fact, point, unavailable
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_criteria import ALPHA_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_grader import CRITERIA, grade_alpha
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.alpha_cases import real_record, sparse_record, synthetic_record

HANDED = {'signal_window', 'assay_quality', 'concentration_series', 'direct_vs_competition', 'replicates'}      # the equilibrium is ruled by its fact in the synthetic record


def status(record, criterion):
    """The status after the sheet side has judged the facts the grader recorded (the grader holds no threshold; the sheet-side constants are in the converter)."""
    return _criterion(grade_alpha(record), criterion)['status']


def grader_status(record, criterion):
    return grade_alpha(record)['criteria'][criterion]['status']


def reason(record, criterion):
    return grade_alpha(record)['reasons'][criterion]


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_complete_synthetic_record_is_supported_everywhere_once_the_sheet_has_judged_what_the_grader_recorded():
    graded = grade_alpha(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA and len(CRITERIA) == 15
    handed = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed == HANDED
    assert all(graded['criteria'][name]['status'] == 'unknown' and graded['criteria'][name]['support_refs'] == [] for name in handed)
    assert {_criterion(graded, name)['status'] for name in CRITERIA} == {'supported'} and all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['kd_nM'] == 20.0 and native['ki_nM'] == 30.0 and native['ec50_nM'] == 28.0 and native['ic50_nM'] == 45.0
    assert native['constant_name'] == 'kd' and native['constant_nM'] == 20.0 and graded['experiment_type'] == 'alphascreen'
    assert native['signal_over_background'] == 500.0 and native['incubation_min'] == 60.0
    assert native['concentration_count'] == 12 and native['concentration_low_over_constant'] == pytest.approx(0.05) and native['concentration_high_over_constant'] == pytest.approx(102.4)
    assert native['fit_model'] == 'four_parameter_logistic' and native['titration_design'] == 'fixed_partner_titration' and native['donor_bead'] == 'streptavidin' and native['acceptor_bead'] == 'nickel_chelate'


def test_sparse_record_is_unknown_or_not_applicable_never_conflicting_and_never_supported():
    graded = grade_alpha(sparse_record())
    assert {c['status'] for c in graded['criteria'].values()} <= {'unknown', 'not_applicable'}
    assert graded['native']['kd_nM'] == 20.0 and graded['criteria']['signal_window']['status'] == 'unknown'


def test_the_real_cross_titration_decides_only_the_hook_effect():
    graded = grade_alpha(real_record())
    assert [name for name, item in graded['criteria'].items() if item['status'] == 'supported'] == ['hook_effect']
    assert [name for name, item in graded['criteria'].items() if item['status'] == 'conflicting'] == []
    assert [name for name in graded['criteria'] if _criterion(graded, name)['status'] == 'supported'] == ['hook_effect']      # nothing is handed to the sheet: no number is stated
    assert graded['criteria']['hook_effect']['support_refs'] == ['span_hook'] and graded['reasons']['signal_window'] == 'signal_window_not_given'


# A supported or a conflicting criterion rests on quoted spans: the ELISA lesson (the sheet refuses an interpretation without support).
def variants():
    out = [synthetic_record(), sparse_record(), real_record()]
    for name in ('signal_in_linear_range', 'counter_screen_done', 'hook_effect_handled', 'partner_concentration_below_kd', 'equilibrium_reached', 'nonspecific_binding_checked', 'capture_does_not_alter_binding', 'light_protected', 'avidity_excluded', 'independent_experiments'):
        for answer in ('no', 'unknown', 'not_applicable'):
            record = synthetic_record()
            record['facts'][name] = fact(answer, ['s'] if answer == 'no' else [])
            out.append(record)
    for model, form in (('competitive_binding', 'saturation_titration'), ('bell_shaped_hook', 'competition'), ('one_site', 'competition'), ('quadratic', 'competition'), ('four_parameter_logistic', 'competition'), ('other', None), (None, None)):
        record = synthetic_record()
        record['fit_model'], record['assay_format'] = model, form
        out.append(record)
    record = synthetic_record()                                    # a model stated while no constant is reported
    record['fit_model'], record['assay_format'] = 'competitive_binding', 'saturation_titration'
    for constant in ('kd', 'ki', 'ec50', 'ic50'):
        missing(record, constant)
    out.append(record)
    for maximum, background, ratio in ((100.0, 100.0, None), (300.0, 100.0, None), (900.0, 100.0, None), (None, 100.0, None), (450000.0, 900.0, 5.0), (None, None, 30.0)):
        record = synthetic_record()
        for name, value in (('signal_maximum', maximum), ('signal_background', background), ('signal_to_background', ratio)):
            if value is None:
                missing(record, name)
            else:
                record['quantities'][name] = point(value, record['quantities'][name]['unit'], name, ['s'])
        out.append(record)
    for z_prime in (-0.1, 0.3, 0.5, None):
        record = synthetic_record()
        record['quantities']['z_prime'] = point(z_prime, 'ratio', 'z', ['s']) if z_prime else {**record['quantities']['z_prime'], 'status': 'unavailable', 'value': None}
        out.append(record)
    for minutes in (10.0, 30.0):
        record = synthetic_record()
        record['facts']['equilibrium_reached'] = fact('unknown')
        record['quantities']['incubation_time'] = point(minutes, 'min', 'i', ['s'])
        out.append(record)
    for ki in (200.0, 6.0):
        record = synthetic_record()
        record['quantities']['ki'] = point(ki, 'nM', 'k', ['s'])
        out.append(record)
    for count, independent in ((2, 'yes'), (3, 'no'), (None, 'yes'), (3, 'unknown')):
        record = synthetic_record()
        record['facts']['independent_experiments'] = fact(independent, ['s'] if independent != 'unknown' else [])
        if count is None:
            missing(record, 'replicate_count')
        else:
            record['quantities']['replicate_count'] = point(count, 'count', 'n', ['s'])
        out.append(record)
    for series in ([1.0, 2.0], [4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0, 512.0], [4.1, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0, 512.0], None):
        record = synthetic_record()
        if series is None:
            record['concentration_series'] = {**record['concentration_series'], 'status': 'unavailable', 'value': None}
            record['quantities']['titration_point_count'] = point(6, 'count', 'n', ['s'])
        else:
            record['concentration_series']['value'] = series
        out.append(record)
    return out


def test_every_supported_or_conflicting_criterion_carries_support_refs():
    seen = set()
    for record in variants():
        graded = grade_alpha(record)
        for name, outcome in graded['criteria'].items():
            if outcome['status'] in ('supported', 'conflicting'):
                seen.add((name, outcome['status'], graded['reasons'][name]))
                assert outcome['support_refs'], (record['experiment_ref'], name, graded['reasons'][name])
            else:
                assert outcome['support_refs'] == []
    # every supported or conflicting case the criteria declare was reached by some variant, and so was checked for its refs
    declared = {(criterion['id'], status, why) for criterion in ALPHA_CRITERIA for status, why, _ in criterion['returns'] if status in ('supported', 'conflicting')}
    assert seen == declared


def test_every_criterion_the_sheet_decides_carries_support_refs_too():
    judged_cases = set()
    for record in variants():
        graded = grade_alpha(record)
        for name in graded['criteria']:
            outcome = _criterion(graded, name)
            if outcome['status'] in ('supported', 'conflicting'):
                assert outcome['support_refs'], (record['experiment_ref'], name, graded['reasons'][name])
                if graded['reasons'][name].endswith('_recorded_for_the_sheet'):
                    judged_cases.add((name, outcome['status']))
            else:
                assert outcome['support_refs'] == []
    assert judged_cases >= {(name, state) for name in ('signal_window', 'assay_quality', 'concentration_series', 'direct_vs_competition', 'replicates', 'equilibrium') for state in ('supported', 'conflicting')} - {('equilibrium', 'supported')}


def test_a_decided_criterion_cannot_be_built_without_support_refs():
    record = synthetic_record()
    record['facts']['hook_effect_handled'] = fact('yes')           # a fact answered yes with no span: it cannot be supported
    with pytest.raises(ValueError, match='needs support refs'):
        grade_alpha(record)


def test_the_signal_window_is_the_reported_ratio_else_the_top_signal_over_the_background():
    r = synthetic_record()
    r['quantities']['signal_to_background'] = point(10.0, 'ratio', 's', ['s'])                 # exactly the minimum, allowed, the full degree
    assert (grader_status(r, 'signal_window'), reason(r, 'signal_window')) == ('unknown', 'signal_window_recorded_for_the_sheet')
    assert grade_alpha(r)['native']['signal_over_background'] == 10.0 and grade_alpha(r)['native']['signal_window_refs'] == ['s']
    assert _criterion(grade_alpha(r), 'signal_window') == {'status': 'supported', 'support_refs': ['s'], 'degree': 1.0}
    r['quantities']['signal_to_background'] = point(5.5, 'ratio', 's', ['s'])                  # halfway from 1 up to 10: a degree of 0.5
    assert status(r, 'signal_window') == 'supported' and _criterion(grade_alpha(r), 'signal_window')['degree'] == pytest.approx(0.5)
    r['quantities']['signal_to_background'] = point(1.0, 'ratio', 's', ['s'])                  # no window: the zero-agreement limit
    assert status(r, 'signal_window') == 'conflicting' and 'degree' not in _criterion(grade_alpha(r), 'signal_window')
    missing(r, 'signal_to_background')                                                           # 450000 / 900 = 500
    assert grade_alpha(r)['native']['signal_over_background'] == 500.0 and status(r, 'signal_window') == 'supported'
    assert grade_alpha(r)['native']['signal_window_refs'] == ['span_exp_synthetic_alpha_1']
    r['quantities']['signal_maximum'] = point(900.0, 'cps', 'm', ['s'])                          # 900 / 900 = 1
    assert status(r, 'signal_window') == 'conflicting'
    r['quantities']['signal_maximum'] = point(9000.0, 'cps', 'm', ['s'])                         # exactly 10
    assert status(r, 'signal_window') == 'supported'
    missing(r, 'signal_background')
    assert reason(r, 'signal_window') == 'signal_window_not_given' and status(r, 'signal_window') == 'unknown'


def test_the_z_prime_factor_is_recorded_and_the_sheet_judges_it():
    r = synthetic_record()
    r['quantities']['z_prime'] = point(0.5, 'ratio', 'z', ['s'])                                  # exactly the minimum, allowed
    assert (grader_status(r, 'assay_quality'), reason(r, 'assay_quality')) == ('unknown', 'z_prime_recorded_for_the_sheet')
    assert grade_alpha(r)['native']['z_prime'] == 0.5 and grade_alpha(r)['native']['z_prime_refs'] == ['s']
    assert _criterion(grade_alpha(r), 'assay_quality') == {'status': 'supported', 'support_refs': ['s'], 'degree': 1.0}
    r['quantities']['z_prime'] = point(0.25, 'ratio', 'z', ['s'])                                 # halfway from 0 up to 0.5
    assert _criterion(grade_alpha(r), 'assay_quality')['degree'] == pytest.approx(0.5) and status(r, 'assay_quality') == 'supported'
    r['quantities']['z_prime'] = point(0.0, 'ratio', 'z', ['s'])                                  # the zero-agreement limit
    assert status(r, 'assay_quality') == 'conflicting' and 'degree' not in _criterion(grade_alpha(r), 'assay_quality')
    r['quantities']['z_prime'] = point(-0.2, 'ratio', 'z', ['s'])
    assert status(r, 'assay_quality') == 'conflicting'
    missing(r, 'z_prime')
    assert status(r, 'assay_quality') == 'unknown' and reason(r, 'assay_quality') == 'z_prime_not_given'


@pytest.mark.parametrize('criterion, name', [('detector_range', 'signal_in_linear_range'), ('interference_counter_screen', 'counter_screen_done'), ('hook_effect', 'hook_effect_handled'),
                                             ('partner_depletion', 'partner_concentration_below_kd'), ('specificity_control', 'nonspecific_binding_checked'),
                                             ('capture_artifacts', 'capture_does_not_alter_binding'), ('light_protection', 'light_protected'), ('avidity', 'avidity_excluded')])
def test_a_one_fact_criterion_follows_its_fact(criterion, name):
    r = synthetic_record()
    assert (status(r, criterion), reason(r, criterion)) == ('supported', 'facts_answered_yes')
    r['facts'][name] = fact('no', ['s'])
    assert (status(r, criterion), reason(r, criterion)) == ('conflicting', 'fact_answered_no')
    r['facts'][name] = fact('unknown')
    assert (status(r, criterion), reason(r, criterion)) == ('unknown', 'fact_unknown')
    r['facts'][name] = fact('not_applicable')
    assert (status(r, criterion), reason(r, criterion)) == ('not_applicable', 'fact_not_applicable')


def test_the_equilibrium_fact_then_a_short_binding_step():
    r = synthetic_record()
    r['facts']['equilibrium_reached'] = fact('unknown')
    assert (grader_status(r, 'equilibrium'), reason(r, 'equilibrium')) == ('unknown', 'incubation_recorded_for_the_sheet') and grade_alpha(r)['native']['incubation_min'] == 60.0
    assert status(r, 'equilibrium') == 'unknown'                                           # a 60 min step is not short
    r['quantities']['incubation_time'] = point(29.0, 'min', 'i', ['s'])
    assert status(r, 'equilibrium') == 'conflicting' and grade_alpha(r)['native']['incubation_refs'] == ['s'] and _criterion(grade_alpha(r), 'equilibrium')['support_refs'] == ['s']
    r['quantities']['incubation_time'] = point(30.0, 'min', 'i', ['s'])                    # exactly the minimum
    assert status(r, 'equilibrium') == 'unknown'
    r['quantities']['incubation_time'] = point(0.4, 'h', 'i', ['s'])                       # 24 min
    assert status(r, 'equilibrium') == 'conflicting'
    r['facts']['equilibrium_reached'] = fact('yes', ['s'])                                 # the stated fact outranks the short step
    assert status(r, 'equilibrium') == 'supported'
    r['facts']['equilibrium_reached'] = fact('no', ['s'])
    assert reason(r, 'equilibrium') == 'fact_answered_no'


def test_the_bead_incubation_time_does_not_stand_for_the_binding_step():
    r = synthetic_record()
    r['facts']['equilibrium_reached'] = fact('unknown')
    missing(r, 'incubation_time')
    r['quantities']['bead_incubation_time'] = point(5.0, 'min', 'b', ['s'])
    assert reason(r, 'equilibrium') == 'fact_unknown' and status(r, 'equilibrium') == 'unknown'


def test_the_series_must_have_enough_points_and_span_the_constant():
    r = synthetic_record()                                                                 # 12 points, 0.05 x to 102.4 x the KD
    assert (grader_status(r, 'concentration_series'), reason(r, 'concentration_series')) == ('unknown', 'concentration_series_recorded_for_the_sheet')
    native = grade_alpha(r)['native']
    assert native['concentration_count'] == 12 and native['concentration_span_refs'] == ['span_exp_synthetic_alpha_1'] and native['concentration_count_refs'] == ['span_exp_synthetic_alpha_1']
    assert _criterion(grade_alpha(r), 'concentration_series') == {'status': 'supported', 'support_refs': ['span_exp_synthetic_alpha_1'], 'degree': 1.0}
    r['concentration_series']['value'] = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0]    # 8 points: 0.05 x to 6.4 x the KD: the high end gives a degree (6.4 - 1) / 9
    assert status(r, 'concentration_series') == 'supported' and _criterion(grade_alpha(r), 'concentration_series')['degree'] == pytest.approx(5.4 / 9.0)
    r['concentration_series']['value'] = [4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0, 512.0]  # lowest 4 nM = 0.2 x the KD (allowed), highest 512 = 25.6 x
    assert _criterion(grade_alpha(r), 'concentration_series')['degree'] == 1.0
    r['concentration_series']['value'] = [12.0, 16.0, 32.0, 64.0, 128.0, 256.0, 512.0, 1024.0]   # lowest 0.6 x the KD: a degree of 0.5
    assert _criterion(grade_alpha(r), 'concentration_series')['degree'] == pytest.approx(0.5)
    r['concentration_series']['value'] = [20.0, 32.0, 64.0, 128.0, 256.0, 512.0, 1024.0, 2048.0]  # lowest 1 x the KD: the zero-agreement limit
    assert status(r, 'concentration_series') == 'conflicting' and 'degree' not in _criterion(grade_alpha(r), 'concentration_series')
    r['concentration_series']['value'] = [4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0]      # highest 1 x the KD: the zero-agreement limit
    assert status(r, 'concentration_series') == 'conflicting'
    r['concentration_series']['value'] = [4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 200.0]        # 7 points: fewer than eight, no degree
    assert status(r, 'concentration_series') == 'conflicting' and grade_alpha(r)['native']['concentration_count'] == 7
    r['concentration_series'] = {**r['concentration_series'], 'status': 'unavailable', 'value': None}
    assert reason(r, 'concentration_series') == 'concentration_series_recorded_for_the_sheet' and status(r, 'concentration_series') == 'unknown'      # the stated 12 points are enough, the span cannot be judged
    assert grade_alpha(r)['native']['concentration_low_over_constant'] is None
    r['quantities']['titration_point_count'] = point(6, 'count', 'n', ['s'])
    assert status(r, 'concentration_series') == 'conflicting'
    r['quantities']['titration_point_count'] = point(10, 'count', 'n', ['s'])
    assert status(r, 'concentration_series') == 'unknown'
    missing(r, 'titration_point_count')
    assert (grader_status(r, 'concentration_series'), reason(r, 'concentration_series')) == ('unknown', 'constant_or_series_missing')


def test_the_series_is_judged_against_the_ec50_or_the_ic50_when_there_is_no_kd_or_ki():
    r = synthetic_record()
    for name in ('kd', 'ki'):
        missing(r, name)
    graded = grade_alpha(r)                                                                # the EC50 28 nM: 1 / 28 = 0.036 and 2048 / 28 = 73
    assert graded['native']['constant_name'] == 'ec50' and graded['native']['concentration_high_over_constant'] == pytest.approx(2048 / 28)
    missing(r, 'ec50')
    graded = grade_alpha(r)                                                                # the IC50 45 nM
    assert graded['native']['constant_name'] == 'ic50' and graded['native']['concentration_high_over_constant'] == pytest.approx(2048 / 45)
    assert _criterion(graded, 'concentration_series')['status'] == 'supported' and graded['native']['concentration_span_refs'] == ['span_exp_synthetic_alpha_1']


def test_the_fit_model_must_be_stated_and_fit_the_format_and_a_constant_must_support_it():
    r = synthetic_record()
    assert (status(r, 'fit_model'), reason(r, 'fit_model')) == ('supported', 'model_stated')
    r['fit_model'] = 'competitive_binding'
    assert reason(r, 'fit_model') == 'competition_model_for_saturation_titration' and status(r, 'fit_model') == 'conflicting'
    r['assay_format'] = 'competition'
    assert status(r, 'fit_model') == 'supported'
    for model in ('one_site', 'quadratic', 'bell_shaped_hook'):
        r['fit_model'] = model
        assert reason(r, 'fit_model') == 'direct_model_for_competition' and status(r, 'fit_model') == 'conflicting'
    r['fit_model'] = 'four_parameter_logistic'
    assert status(r, 'fit_model') == 'supported'                                          # a four-parameter curve fits both formats
    r['assay_format'] = None
    r['fit_model'] = 'competitive_binding'
    assert status(r, 'fit_model') == 'supported'
    r['fit_model'] = 'bell_shaped_hook'
    r['assay_format'] = 'saturation_titration'
    assert status(r, 'fit_model') == 'supported'                                          # a bell-shaped model of a hook curve fits a titration
    r['fit_model'] = None
    assert reason(r, 'fit_model') == 'fit_model_not_stated' and status(r, 'fit_model') == 'unknown'
    for model, form in (('one_site', 'saturation_titration'), ('competitive_binding', 'saturation_titration'), ('one_site', 'competition')):
        r['fit_model'], r['assay_format'] = model, form
        for name in ('kd', 'ki', 'ec50', 'ic50'):
            r['quantities'][name] = unavailable('nM', name, 'not_given_in_the_inspected_source_text')   # no reported constant: no span supports the model
        assert reason(r, 'fit_model') == 'model_stated_without_a_reported_constant' and status(r, 'fit_model') == 'unknown'


def test_the_kd_and_the_ki_must_agree_within_the_factor():
    r = synthetic_record()                                                                 # 30 / 20 = 1.5
    assert (grader_status(r, 'direct_vs_competition'), reason(r, 'direct_vs_competition')) == ('unknown', 'estimates_recorded_for_the_sheet')
    assert grade_alpha(r)['native']['estimate_fold'] == pytest.approx(1.5) and grade_alpha(r)['native']['estimate_refs'] == ['span_exp_synthetic_alpha_1']
    assert _criterion(grade_alpha(r), 'direct_vs_competition') == {'status': 'supported', 'support_refs': ['span_exp_synthetic_alpha_1'], 'degree': 1.0}
    r['quantities']['ki'] = point(120.0, 'nM', 'k', ['s'])                                 # 6 fold: degree (10 - 6) / 7
    assert status(r, 'direct_vs_competition') == 'supported' and _criterion(grade_alpha(r), 'direct_vs_competition')['degree'] == pytest.approx(4.0 / 7.0)
    r['quantities']['ki'] = point(200.0, 'nM', 'k', ['s'])                                 # 10 fold: the zero-agreement limit
    assert status(r, 'direct_vs_competition') == 'conflicting' and 'degree' not in _criterion(grade_alpha(r), 'direct_vs_competition')
    r['quantities']['ki'] = point(2.0, 'nM', 'k', ['s'])                                   # 20 / 2 = 10 the other way
    assert status(r, 'direct_vs_competition') == 'conflicting'
    r['quantities']['ki'] = point(4.0, 'nM', 'k', ['s'])                                   # 20 / 4 = 5 the other way: degree 5 / 7
    assert _criterion(grade_alpha(r), 'direct_vs_competition')['degree'] == pytest.approx(5.0 / 7.0)
    r['quantities']['ki'] = point(0.05, 'uM', 'k', ['s'])                                  # 50 nM: 2.5
    assert status(r, 'direct_vs_competition') == 'supported' and _criterion(grade_alpha(r), 'direct_vs_competition')['degree'] == 1.0
    missing(r, 'ki')
    assert reason(r, 'direct_vs_competition') == 'kd_or_ki_missing' and status(r, 'direct_vs_competition') == 'unknown'
    r['facts']['single_estimate_method'] = fact('yes', ['s'])
    assert reason(r, 'direct_vs_competition') == 'single_estimate_method' and status(r, 'direct_vs_competition') == 'not_applicable'


def test_replicates_are_independent_experiments_and_wells_do_not_count():
    r = synthetic_record()
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('unknown', 'replicate_count_recorded_for_the_sheet') and status(r, 'replicates') == 'supported'
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])
    assert status(r, 'replicates') == 'conflicting' and grade_alpha(r)['native']['replicate_count'] == 2 and grade_alpha(r)['native']['replicate_independent'] == 'yes'
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])
    assert status(r, 'replicates') == 'supported' and _criterion(grade_alpha(r), 'replicates')['support_refs'] == ['s', 'span_exp_synthetic_alpha_1']
    r['facts']['independent_experiments'] = fact('no', ['s'])
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('conflicting', 'replicates_not_independent')
    r['facts']['independent_experiments'] = fact('unknown')
    assert status(r, 'replicates') == 'unknown'
    r['facts']['independent_experiments'] = fact('yes', ['s'])
    missing(r, 'replicate_count')
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('unknown', 'replicate_count_or_independence_unknown')
    r['quantities']['technical_replicate_count'] = point(4, 'count', 'w', ['s'])           # triplicate or quadruplicate wells do not make replicates
    assert status(r, 'replicates') == 'unknown'


def test_only_a_ec50_or_an_ic50_is_not_a_binding_constant_but_is_kept_apart_from_the_kd():
    r = synthetic_record()
    for name in ('kd', 'ki'):
        missing(r, name)
    native = grade_alpha(r)['native']
    assert native['kd_nM'] is None and native['ki_nM'] is None and native['ec50_nM'] == 28.0 and native['ic50_nM'] == 45.0
