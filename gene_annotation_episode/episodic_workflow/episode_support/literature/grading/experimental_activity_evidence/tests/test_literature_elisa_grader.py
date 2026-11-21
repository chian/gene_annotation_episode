"""ELISA grader: each criterion's rule on records, with the arithmetic worked by hand."""
import math

import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_elisa_record import fact, point, unavailable
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_grader import CRITERIA, grade_elisa
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.elisa_cases import sparse_record, synthetic_record

HANDED = {'signal_window', 'concentration_series', 'direct_vs_competition', 'replicates'}      # the detector range, the wash dissociation and the equilibrium are ruled by their facts in the synthetic record


def status(record, criterion):
    """The status after the sheet side has judged the facts the grader recorded (the grader holds no threshold; the sheet-side constants are in the converter)."""
    return _criterion(grade_elisa(record), criterion)['status']


def grader_status(record, criterion):
    return grade_elisa(record)['criteria'][criterion]['status']


def reason(record, criterion):
    return grade_elisa(record)['reasons'][criterion]


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_complete_synthetic_record_is_supported_everywhere_once_the_sheet_has_judged_what_the_grader_recorded():
    graded = grade_elisa(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA and len(CRITERIA) == 14
    handed = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed == HANDED
    assert all(graded['criteria'][name]['status'] == 'unknown' and graded['criteria'][name]['support_refs'] == [] for name in handed)
    assert {_criterion(graded, name)['status'] for name in CRITERIA} == {'supported'} and all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['kd_nM'] == 20.0 and native['ki_nM'] == 30.0 and native['ec50_nM'] == 28.0 and native['ic50_nM'] == 45.0
    assert native['constant_name'] == 'kd' and native['constant_nM'] == 20.0 and graded['experiment_type'] == 'elisa'
    assert native['signal_over_background'] == pytest.approx(20.0) and native['incubation_min'] == 90.0
    assert native['concentration_count'] == 12 and native['concentration_low_over_constant'] == pytest.approx(0.05) and native['concentration_high_over_constant'] == pytest.approx(102.4)
    assert native['fit_model'] == 'four_parameter_logistic' and native['detection_format'] == 'indirect' and native['blocking_agent'] == 'bsa'


def test_sparse_record_is_unknown_or_not_applicable_never_conflicting_and_never_supported():
    graded = grade_elisa(sparse_record())
    assert {c['status'] for c in graded['criteria'].values()} <= {'unknown', 'not_applicable'}
    assert graded['native']['kd_nM'] == 20.0 and graded['criteria']['signal_window']['status'] == 'unknown'


def test_the_signal_window_is_the_plateau_over_the_background():
    r = synthetic_record()
    assert (grader_status(r, 'signal_window'), reason(r, 'signal_window')) == ('unknown', 'signal_window_recorded_for_the_sheet')
    r['quantities']['signal_maximum'] = point(0.6, 'OD', 'm', ['s'])                     # 0.6 / 0.06 = 10: above the minimum of 5, the full degree
    assert grade_elisa(r)['native']['signal_over_background'] == pytest.approx(10.0) and grade_elisa(r)['native']['signal_window_refs'] == ['s', 'span_exp_synthetic_elisa_1']
    assert _criterion(grade_elisa(r), 'signal_window') == {'status': 'supported', 'support_refs': ['s', 'span_exp_synthetic_elisa_1'], 'degree': 1.0}
    r['quantities']['signal_maximum'] = point(0.18, 'OD', 'm', ['s'])                    # 0.18 / 0.06 = 3: on the log of the ratio from 1 up to 5, log 3 / log 5
    assert status(r, 'signal_window') == 'supported' and _criterion(grade_elisa(r), 'signal_window')['degree'] == pytest.approx(math.log(3) / math.log(5))
    r['quantities']['signal_maximum'] = point(0.06, 'OD', 'm', ['s'])                    # 1: the plateau is the background
    assert status(r, 'signal_window') == 'conflicting' and 'degree' not in _criterion(grade_elisa(r), 'signal_window')
    r['quantities']['signal_maximum'] = point(0.03, 'OD', 'm', ['s'])                    # 0.5: below the background
    assert status(r, 'signal_window') == 'conflicting'
    r['quantities']['signal_maximum'] = point(1.2, 'OD', 'm', ['s'])
    missing(r, 'signal_background')
    assert reason(r, 'signal_window') == 'signal_or_background_not_given' and status(r, 'signal_window') == 'unknown'


def plateau_degree(od):
    """The softened detector range worked by hand: (10^4 - 10^OD) / (10^4 - 10^2), full credit at 2 OD and none at 4 OD."""
    return (10 ** 4 - 10 ** od) / (10 ** 4 - 10 ** 2)


def test_the_detector_range_fact_decides_then_the_plateau_absorbance():
    r = synthetic_record()
    r['quantities']['signal_maximum'] = point(2.8, 'OD', 'm', ['s'])
    assert status(r, 'detector_range') == 'supported' and reason(r, 'detector_range') == 'facts_answered_yes'      # the stated fact outranks the number
    r['facts']['signal_in_linear_range'] = fact('unknown')
    assert (grader_status(r, 'detector_range'), reason(r, 'detector_range')) == ('unknown', 'plateau_recorded_for_the_sheet')
    assert grade_elisa(r)['native']['plateau_absorbance'] == 2.8 and grade_elisa(r)['native']['plateau_refs'] == ['s']
    verdict = _criterion(grade_elisa(r), 'detector_range')                                   # above the linear range: partial credit, not a step to conflicting
    assert verdict['status'] == 'supported' and verdict['support_refs'] == ['s'] and verdict['degree'] == pytest.approx(plateau_degree(2.8)) and 0.9 < verdict['degree'] < 1
    r['quantities']['signal_maximum'] = point(2.0, 'OD', 'm', ['s'])                       # exactly the researched limit: full credit, judged as before (no degree)
    assert _criterion(grade_elisa(r), 'detector_range') == {'status': 'supported', 'support_refs': ['s']}
    r['quantities']['signal_maximum'] = point(4.0, 'OD', 'm', ['s'])                       # the end of the reader's photometric range: conflicting, no degree
    assert _criterion(grade_elisa(r), 'detector_range') == {'status': 'conflicting', 'support_refs': ['s']}
    missing(r, 'signal_maximum')
    assert reason(r, 'detector_range') == 'fact_unknown' and status(r, 'detector_range') == 'unknown'
    r['facts']['signal_in_linear_range'] = fact('no', ['s'])
    assert reason(r, 'detector_range') == 'fact_answered_no' and status(r, 'detector_range') == 'conflicting'


@pytest.mark.parametrize('criterion, name', [('saturation', 'saturation_reached'), ('blank_subtraction', 'blank_subtracted'), ('specificity_control', 'nonspecific_binding_checked'),
                                             ('wash_dissociation', 'wash_dissociation_considered'), ('avidity', 'avidity_excluded'), ('coated_protein_activity', 'coated_protein_active'),
                                             ('detection_interference', 'detection_does_not_interfere')])
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
    assert (grader_status(r, 'equilibrium'), reason(r, 'equilibrium')) == ('unknown', 'incubation_recorded_for_the_sheet') and grade_elisa(r)['native']['incubation_min'] == 90.0
    assert status(r, 'equilibrium') == 'supported'                                         # 90 min at the 20 nM constant: T_FAST 1.5 min, so a curve, not a cliff
    assert grade_elisa(r)['native']['constant_refs'] == ['span_exp_synthetic_elisa_1'] and _criterion(grade_elisa(r), 'equilibrium')['degree'] == pytest.approx(math.log(60) / math.log(100))
    r['quantities']['incubation_time'] = point(29.0, 'min', 'i', ['s'])
    verdict = _criterion(grade_elisa(r), 'equilibrium')                                    # below the 30 min floor: proportional, not conflicting
    assert verdict['status'] == 'supported' and verdict['degree'] == pytest.approx(math.log(29 / 1.5) / math.log(100)) and grade_elisa(r)['native']['incubation_refs'] == ['s']
    assert set(verdict['support_refs']) == {'s', 'span_exp_synthetic_elisa_1'}
    r['quantities']['incubation_time'] = point(1.5, 'min', 'i', ['s'])                     # exactly T_FAST (30 x 1 / 20): the zero end
    assert status(r, 'equilibrium') == 'conflicting'
    r['quantities']['incubation_time'] = point(0.4, 'h', 'i', ['s'])                       # 24 min: d_kon log(16)/log(100) = 0.602, d_floor 0.8
    assert _criterion(grade_elisa(r), 'equilibrium')['degree'] == pytest.approx(math.log(16) / math.log(100))
    for name in ('kd', 'ki', 'ec50', 'ic50'):                                              # no constant: unknown, also below the floor
        missing(r, name)
    assert status(r, 'equilibrium') == 'unknown' and grade_elisa(r)['native']['constant_refs'] == []
    r = synthetic_record()
    r['facts']['equilibrium_reached'] = fact('unknown')
    missing(r, 'incubation_time')
    assert (grader_status(r, 'equilibrium'), reason(r, 'equilibrium')) == ('unknown', 'fact_unknown')
    r['quantities']['incubation_time'] = point(0.4, 'h', 'i', ['s'])
    r['facts']['equilibrium_reached'] = fact('yes', ['s'])                                 # the stated fact outranks the short step
    assert status(r, 'equilibrium') == 'supported'
    r['facts']['equilibrium_reached'] = fact('no', ['s'])
    assert reason(r, 'equilibrium') == 'fact_answered_no'


def test_the_series_must_have_enough_points_and_span_the_constant():
    r = synthetic_record()                                                                 # 12 points, 0.05 x to 102.4 x the KD
    assert (grader_status(r, 'concentration_series'), reason(r, 'concentration_series')) == ('unknown', 'concentration_series_recorded_for_the_sheet')
    native = grade_elisa(r)['native']
    assert native['concentration_count'] == 12 and native['concentration_span_refs'] == ['span_exp_synthetic_elisa_1'] and native['concentration_count_refs'] == ['span_exp_synthetic_elisa_1']
    assert _criterion(grade_elisa(r), 'concentration_series') == {'status': 'supported', 'support_refs': ['span_exp_synthetic_elisa_1'], 'degree': 1.0}
    r['concentration_series']['value'] = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0]    # 8 points: 0.05 x to 6.4 x the KD: the high end gives a degree on the occupancy scale
    assert status(r, 'concentration_series') == 'supported' and _criterion(grade_elisa(r), 'concentration_series')['degree'] == pytest.approx((6.4 / 7.4 - 0.5) / (10 / 11 - 0.5))
    r['concentration_series']['value'] = [4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0, 512.0]  # lowest 4 nM = 0.2 x the KD (allowed), highest 512 = 25.6 x
    assert _criterion(grade_elisa(r), 'concentration_series')['degree'] == 1.0
    r['concentration_series']['value'] = [12.0, 16.0, 32.0, 64.0, 128.0, 256.0, 512.0, 1024.0]   # lowest 0.6 x the KD: 0.375 on the occupancy scale
    assert _criterion(grade_elisa(r), 'concentration_series')['degree'] == pytest.approx(0.375)
    r['concentration_series']['value'] = [20.0, 32.0, 64.0, 128.0, 256.0, 512.0, 1024.0, 2048.0]  # lowest 1 x the KD: the zero-agreement limit
    assert status(r, 'concentration_series') == 'conflicting' and 'degree' not in _criterion(grade_elisa(r), 'concentration_series')
    r['concentration_series']['value'] = [4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0]      # highest 1 x the KD: the zero-agreement limit
    assert status(r, 'concentration_series') == 'conflicting'
    r['concentration_series']['value'] = [4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 200.0]        # 7 points, 0.2 x to 10 x: 3 of the 4 residual degrees of freedom, a degree of 0.75
    assert status(r, 'concentration_series') == 'supported' and grade_elisa(r)['native']['concentration_count'] == 7
    assert _criterion(grade_elisa(r), 'concentration_series')['degree'] == pytest.approx(0.75)
    r['concentration_series']['value'] = [4.0, 16.0, 64.0, 128.0, 200.0]                   # 5 points: one residual degree of freedom, a degree of 0.25
    assert _criterion(grade_elisa(r), 'concentration_series')['degree'] == pytest.approx(0.25)
    r['concentration_series']['value'] = [4.0, 16.0, 64.0, 200.0]                          # 4 points: the four-parameter curve is fitted exactly, no residual
    assert _criterion(grade_elisa(r), 'concentration_series') == {'status': 'supported', 'support_refs': ['span_exp_synthetic_elisa_1'], 'degree': 0.0}      # no credit, never conflicting
    r['concentration_series'] = {**r['concentration_series'], 'status': 'unavailable', 'value': None}
    assert reason(r, 'concentration_series') == 'concentration_series_recorded_for_the_sheet' and status(r, 'concentration_series') == 'unknown'      # the stated 12 points are enough, the span cannot be judged
    assert grade_elisa(r)['native']['concentration_low_over_constant'] is None
    r['quantities']['titration_point_count'] = point(6, 'count', 'n', ['s'])               # six points: partial credit for the count, the span still cannot be judged
    assert status(r, 'concentration_series') == 'unknown'
    r['quantities']['titration_point_count'] = point(4, 'count', 'n', ['s'])               # four points: no residual, but the span cannot be judged without the list: still unknown (a short count is never conflicting)
    assert status(r, 'concentration_series') == 'unknown'
    r['quantities']['titration_point_count'] = point(10, 'count', 'n', ['s'])
    assert status(r, 'concentration_series') == 'unknown'
    missing(r, 'titration_point_count')
    assert (grader_status(r, 'concentration_series'), reason(r, 'concentration_series')) == ('unknown', 'constant_or_series_missing')


def test_the_series_is_judged_against_the_ec50_or_the_ic50_when_there_is_no_kd_or_ki():
    r = synthetic_record()
    for name in ('kd', 'ki'):
        missing(r, name)
    graded = grade_elisa(r)                                                                # the EC50 28 nM: 1 / 28 = 0.036 and 2048 / 28 = 73
    assert graded['native']['constant_name'] == 'ec50' and graded['native']['concentration_high_over_constant'] == pytest.approx(2048 / 28)
    missing(r, 'ec50')
    graded = grade_elisa(r)                                                                # the IC50 45 nM
    assert graded['native']['constant_name'] == 'ic50' and graded['native']['concentration_high_over_constant'] == pytest.approx(2048 / 45)
    assert _criterion(graded, 'concentration_series')['status'] == 'supported' and graded['native']['concentration_span_refs'] == ['span_exp_synthetic_elisa_1']


def test_the_fit_model_must_be_stated_and_fit_the_format():
    r = synthetic_record()
    assert (status(r, 'fit_model'), reason(r, 'fit_model')) == ('supported', 'model_stated')
    r['fit_model'] = 'competitive_binding'
    assert reason(r, 'fit_model') == 'competition_model_for_saturation_titration' and status(r, 'fit_model') == 'conflicting'
    r['assay_format'] = 'competition'
    assert status(r, 'fit_model') == 'supported'
    r['fit_model'] = 'hill'
    assert reason(r, 'fit_model') == 'direct_model_for_competition'
    r['fit_model'] = 'four_parameter_logistic'
    assert status(r, 'fit_model') == 'supported'                                          # a four-parameter curve fits both formats
    r['assay_format'] = None
    r['fit_model'] = 'competitive_binding'
    assert status(r, 'fit_model') == 'supported'
    r['fit_model'] = None
    assert reason(r, 'fit_model') == 'fit_model_not_stated' and status(r, 'fit_model') == 'unknown'
    r['fit_model'] = '1:1'
    for name in ('kd', 'ki', 'ec50', 'ic50'):
        r['quantities'][name] = unavailable('nM', name, 'not_given_in_the_inspected_source_text')   # no reported constant: no span supports the model
    assert reason(r, 'fit_model') == 'model_stated_without_a_reported_constant' and status(r, 'fit_model') == 'unknown'
    r['fit_model'], r['assay_format'] = 'competitive_binding', 'saturation_titration'       # a mismatch of two choices that hold no span: not conflicting without a constant's span
    assert (status(r, 'fit_model'), reason(r, 'fit_model')) == ('unknown', 'model_stated_without_a_reported_constant')
    r['fit_model'], r['assay_format'] = 'hill', 'competition'
    assert (status(r, 'fit_model'), reason(r, 'fit_model')) == ('unknown', 'model_stated_without_a_reported_constant')
    r['quantities']['kd'] = point(20.0, 'nM', 'kd', ['span_kd'])                           # with a constant reported its span supports the mismatch
    assert (status(r, 'fit_model'), reason(r, 'fit_model')) == ('conflicting', 'direct_model_for_competition') and grade_elisa(r)['criteria']['fit_model']['support_refs'] == ['span_kd']


def test_the_kd_and_the_ki_must_agree_within_the_factor():
    r = synthetic_record()                                                                 # 30 / 20 = 1.5
    assert (grader_status(r, 'direct_vs_competition'), reason(r, 'direct_vs_competition')) == ('unknown', 'estimates_recorded_for_the_sheet')
    assert grade_elisa(r)['native']['estimate_fold'] == pytest.approx(1.5) and grade_elisa(r)['native']['estimate_refs'] == ['span_exp_synthetic_elisa_1']
    assert _criterion(grade_elisa(r), 'direct_vs_competition') == {'status': 'supported', 'support_refs': ['span_exp_synthetic_elisa_1'], 'degree': 1.0}
    r['quantities']['ki'] = point(120.0, 'nM', 'k', ['s'])                                 # 6 fold: degree on the log of the fold
    assert status(r, 'direct_vs_competition') == 'supported' and _criterion(grade_elisa(r), 'direct_vs_competition')['degree'] == pytest.approx(math.log(10 / 6) / math.log(10 / 3))
    r['quantities']['ki'] = point(200.0, 'nM', 'k', ['s'])                                 # 10 fold: the zero-agreement limit
    assert status(r, 'direct_vs_competition') == 'conflicting' and 'degree' not in _criterion(grade_elisa(r), 'direct_vs_competition')
    r['quantities']['ki'] = point(2.0, 'nM', 'k', ['s'])                                   # 20 / 2 = 10 the other way
    assert status(r, 'direct_vs_competition') == 'conflicting'
    r['quantities']['ki'] = point(4.0, 'nM', 'k', ['s'])                                   # 20 / 4 = 5 the other way: degree on the log of the fold
    assert _criterion(grade_elisa(r), 'direct_vs_competition')['degree'] == pytest.approx(math.log(10 / 5) / math.log(10 / 3))
    r['quantities']['ki'] = point(0.05, 'uM', 'k', ['s'])                                  # 50 nM: 2.5
    assert status(r, 'direct_vs_competition') == 'supported' and _criterion(grade_elisa(r), 'direct_vs_competition')['degree'] == 1.0
    missing(r, 'ki')
    assert reason(r, 'direct_vs_competition') == 'kd_or_ki_missing' and status(r, 'direct_vs_competition') == 'unknown'
    r['facts']['single_estimate_method'] = fact('yes', ['s'])
    assert reason(r, 'direct_vs_competition') == 'single_estimate_method' and status(r, 'direct_vs_competition') == 'not_applicable'


def test_no_criterion_returns_supported_or_conflicting_without_support_refs():
    for record in (synthetic_record(), sparse_record()):
        graded = grade_elisa(record)
        assert all(c['support_refs'] for c in graded['criteria'].values() if c['status'] in ('supported', 'conflicting'))
    r = synthetic_record()
    r['facts']['independent_experiments'] = fact('no')
    r['quantities']['replicate_count'] = unavailable('count', 'replicate_count', 'not_given_in_the_inspected_source_text')      # a stated 'no' with no span at all: the grader refuses to return it
    with pytest.raises(ValueError):
        grade_elisa(r)


def test_replicates_are_independent_experiments_and_wells_do_not_count():
    r = synthetic_record()
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('unknown', 'replicate_count_recorded_for_the_sheet') and status(r, 'replicates') == 'supported'
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])                     # two of the researched three experiments: partial credit sqrt(2 / 3), not a step
    assert status(r, 'replicates') == 'supported' and grade_elisa(r)['native']['replicate_count'] == 2 and grade_elisa(r)['native']['replicate_independent'] == 'yes'
    assert _criterion(grade_elisa(r), 'replicates')['degree'] == pytest.approx(math.sqrt(2 / 3))
    r['quantities']['replicate_count'] = point(1, 'count', 'n', ['s'])                     # one experiment: low partial credit sqrt(1 / 3), never conflicting
    assert _criterion(grade_elisa(r), 'replicates') == {'status': 'supported', 'support_refs': ['s', 'span_exp_synthetic_elisa_1'], 'degree': pytest.approx(math.sqrt(1 / 3))}
    r['quantities']['replicate_count'] = point(3, 'count', 'n', ['s'])                     # the researched count: full credit, judged as before (no degree)
    assert _criterion(grade_elisa(r), 'replicates') == {'status': 'supported', 'support_refs': ['s', 'span_exp_synthetic_elisa_1']}
    r['facts']['independent_experiments'] = fact('no', ['s'])
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('conflicting', 'replicates_not_independent')
    r['facts']['independent_experiments'] = fact('unknown')
    assert status(r, 'replicates') == 'unknown'
    r['quantities']['replicate_count'] = point(2, 'count', 'n', ['s'])                     # independence not stated: unknown, whatever the partial credit of the count
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
    native = grade_elisa(r)['native']
    assert native['kd_nM'] is None and native['ki_nM'] is None and native['ec50_nM'] == 28.0 and native['ic50_nM'] == 45.0
