"""Spectro_direct grader: facts only. Each criterion on built records; no threshold, no judgement, silence is unknown."""
import pytest

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_spectro_direct_record import fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spectro_direct_grader import CRITERIA, grade_spectro_direct
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.spectro_direct_cases import (
    sparse_record, synthetic_record)

RECORDED = {'absorbance_range': 'absorbance_recorded_for_the_sheet', 'initial_rate_regime': 'consumed_recorded_for_the_sheet', 'enzyme_substrate_ratio': 'enzyme_ratio_recorded_for_the_sheet',
            'substrate_range': 'substrate_series_recorded_for_the_sheet', 'replicates': 'replicate_count_recorded_for_the_sheet'}


def test_a_complete_record_supports_the_fact_criteria_and_hands_the_numbers_to_the_sheet():
    graded = grade_spectro_direct(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA
    for name in CRITERIA:
        if name in RECORDED:
            assert graded['criteria'][name]['status'] == 'unknown' and graded['reasons'][name] == RECORDED[name] and graded['criteria'][name]['support_refs'] == []
        else:
            assert graded['criteria'][name]['status'] == 'supported' and graded['criteria'][name]['support_refs'], name
    native = graded['native']
    assert native['consumed_percent'] == 5.0 and native['enzyme_over_substrate_plus_km'] == pytest.approx(20 / 240000)      # 20 nM of enzyme over 200 uM + 40 uM, both in nM
    assert native['concentration_count'] == 7 and native['concentration_low_over_km'] == pytest.approx(0.25) and native['concentration_high_over_km'] == pytest.approx(25)
    assert native['absorbance_max'] == 0.9 and native['replicate_count'] == 3 and native['replicate_independent'] == 'yes'
    assert native['activity'] == 'detected'


def test_silence_is_unknown_never_no_and_nothing_is_recorded():
    graded = grade_spectro_direct(sparse_record())
    assert {o['status'] for o in graded['criteria'].values()} == {'unknown'}
    native = graded['native']
    assert native['consumed_percent'] is None and native['enzyme_over_substrate_plus_km'] is None and native['concentration_count'] is None and native['absorbance_max'] is None
    assert native['replicate_count'] is None and native['activity'] is None


def test_a_fact_answered_no_is_conflicting_and_carries_its_refs():
    record = synthetic_record()
    for name in ('no_enzyme_control', 'inactive_enzyme_control'):
        record['facts'][name] = fact('no', ['s'])
    record['facts']['product_identified'] = fact('no', ['s'])
    graded = grade_spectro_direct(record)
    assert graded['criteria']['spontaneous_reaction_control'] == {'status': 'conflicting', 'support_refs': ['s']}
    assert graded['criteria']['product_identity']['status'] == 'conflicting'
    record['facts']['no_enzyme_control'] = fact('yes', ['s'])
    assert grade_spectro_direct(record)['criteria']['spontaneous_reaction_control']['status'] == 'supported'      # either control stated as done is enough


def test_a_stated_no_without_refs_raises():
    record = synthetic_record()
    record['facts']['purified_enzyme'] = fact('no')
    with pytest.raises(ValueError, match='needs support refs'):
        grade_spectro_direct(record)


def test_the_initial_rate_regime_reads_the_number_then_the_fact():
    record = synthetic_record()
    record['quantities']['substrate_consumed_percent'] = {**record['quantities']['substrate_consumed_percent'], 'status': 'unavailable', 'value': None}
    assert grade_spectro_direct(record)['reasons']['initial_rate_regime'] == 'linear_progress_curve_stated'
    record['facts']['linear_progress_curve'] = fact('unknown')
    assert grade_spectro_direct(record)['reasons']['initial_rate_regime'] == 'rate_regime_not_stated'
    record['facts']['linear_progress_curve'] = fact('no', ['s'])
    assert grade_spectro_direct(record)['criteria']['initial_rate_regime']['status'] == 'conflicting'
    record = synthetic_record()
    record['facts']['linear_progress_curve'] = fact('no', ['s'])
    assert grade_spectro_direct(record)['reasons']['initial_rate_regime'] == 'fact_answered_no'      # a stated no wins over a stated number


def test_independent_replicates_stated_no_is_conflicting_and_a_count_alone_is_recorded():
    record = synthetic_record()
    record['facts']['independent_replicates'] = fact('no', ['s'])
    assert grade_spectro_direct(record)['reasons']['replicates'] == 'replicates_not_independent'
    record['facts']['independent_replicates'] = fact('unknown')
    graded = grade_spectro_direct(record)
    assert graded['reasons']['replicates'] == 'replicate_count_recorded_for_the_sheet' and graded['native']['replicate_independent'] == 'unknown'
    record['quantities']['replicate_count'] = {**record['quantities']['replicate_count'], 'status': 'unavailable', 'value': None}
    assert grade_spectro_direct(record)['reasons']['replicates'] == 'replicate_count_or_independence_unknown'


def test_the_statement_of_activity_is_the_papers_own():
    record = synthetic_record()
    record['facts']['activity_detected_above_control'] = fact('no', ['s'])
    native = grade_spectro_direct(record)['native']
    assert native['activity'] == 'not_detected' and native['activity_refs'] == ['s']


def test_the_extinction_coefficient_needs_its_wavelength():
    record = synthetic_record()
    record['quantities']['wavelength'] = point(340.0, 'nm', 'w', ['s'])
    record['quantities']['extinction_coefficient'] = {**record['quantities']['extinction_coefficient'], 'status': 'unavailable', 'value': None}
    assert grade_spectro_direct(record)['reasons']['extinction_coefficient_stated'] == 'extinction_coefficient_or_wavelength_missing'


def test_the_support_of_the_fields_each_criterion_reads_is_kept_not_judged():
    record = synthetic_record()
    record['facts']['purified_enzyme'] = fact('yes', ['s'], 'implied')
    graded = grade_spectro_direct(record)
    assert graded['native']['support']['purified_enzyme'] == ['implied'] and graded['criteria']['purified_enzyme']['status'] == 'supported'
