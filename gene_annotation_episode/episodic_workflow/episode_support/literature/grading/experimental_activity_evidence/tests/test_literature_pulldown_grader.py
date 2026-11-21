"""Pull-down / co-IP grader: each criterion's rule on records, with the thresholds exercised on both sides."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_pulldown_record import FACTS, fact, point
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_converter import _criterion
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_criteria import PULLDOWN_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_grader import CRITERIA, grade_pulldown
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.tests.pulldown_cases import real_record, sparse_record, synthetic_record


def status(record, criterion):
    """The status of the criterion after the sheet side has judged the facts the grader recorded (the grader holds no threshold; the sheet-side constants are in the converter)."""
    return _criterion(grade_pulldown(record), criterion)['status']


def judged(record, criterion):
    return _criterion(grade_pulldown(record), criterion)


def grader_status(record, criterion):
    return grade_pulldown(record)['criteria'][criterion]['status']


def reason(record, criterion):
    return grade_pulldown(record)['reasons'][criterion]


def missing(record, name):
    record['quantities'][name] = {**record['quantities'][name], 'status': 'unavailable', 'value': None}


def test_complete_synthetic_record_is_supported_everywhere_once_the_sheet_has_judged_the_recorded_numbers():
    graded = grade_pulldown(synthetic_record())
    assert tuple(graded['criteria']) == CRITERIA and len(CRITERIA) == 16
    handed = {name for name, why in graded['reasons'].items() if why.endswith('_recorded_for_the_sheet')}
    assert handed == {'wash_stringency', 'wash_count', 'incubation', 'enrichment', 'replicates'}
    assert all(graded['criteria'][name]['status'] == 'unknown' and graded['criteria'][name]['support_refs'] == [] for name in handed)
    assert {_criterion(graded, name)['status'] for name in CRITERIA} == {'supported'} and all(_criterion(graded, name)['support_refs'] for name in CRITERIA)
    native = graded['native']
    assert native['wash_count'] == 4 and native['fold_enrichment'] == 12.0 and native['detergent_percent'] == 0.1 and native['replicate_count'] == 3 and native['replicate_independent'] == 'yes'
    assert graded['experiment_type'] == 'pulldown' and native['interaction'] == 'detected' and native['interaction_refs'] == ['span_exp_synthetic_pulldown_1']
    assert native['nacl_wash_mM'] == 300.0 and native['incubation_min'] == 120.0
    assert native['detection_method'] == 'western_blot' and native['capture_format'] == 'gst' and native['protein_source'] == 'cell_lysate'


def test_a_pulldown_has_no_binding_constant_field_and_no_kd_criterion():
    record = synthetic_record()
    assert not {'kd', 'ki', 'ic50', 'kon', 'koff'} & set(record['quantities'])
    assert not {'kd', 'ki', 'ic50'} & set(CRITERIA) and 'kd_nM' not in grade_pulldown(record)['native']
    assert {'negative_control', 'bait_minus_control', 'input_lane', 'reciprocal', 'competition', 'nuclease', 'wash_stringency', 'direct_interaction'} <= set(CRITERIA)


def test_sparse_record_is_unknown_never_conflicting_and_only_the_stated_detection_is_supported():
    graded = grade_pulldown(sparse_record())
    assert {name for name, c in graded['criteria'].items() if c['status'] == 'supported'} == {'prey_in_eluate'}
    assert {c['status'] for name, c in graded['criteria'].items() if name != 'prey_in_eluate'} == {'unknown'}
    assert graded['native']['interaction'] == 'detected'


# A supported or a conflicting criterion rests on quoted spans: the ELISA lesson (the sheet refuses an interpretation without support).
def variants():
    out = [synthetic_record(), sparse_record(), real_record()]
    for name in FACTS:
        for answer in ('no', 'unknown', 'not_applicable'):
            record = synthetic_record()
            record['facts'][name] = fact(answer, ['s'] if answer == 'no' else [])
            out.append(record)
    for done, absent in (('yes', 'unknown'), ('unknown', 'yes'), ('not_applicable', 'not_applicable'), ('no', 'yes'), ('yes', 'no'), ('unknown', 'unknown')):
        record = synthetic_record()
        record['facts']['negative_control_done'] = fact(done, ['s'] if done == 'no' else [])
        record['facts']['prey_absent_in_negative_control'] = fact(absent, ['s'] if absent in ('yes', 'no') else [])
        out.append(record)
    for salt, unit, detergent in ((149.0, 'mM', 0.1), (150.0, 'mM', 0.1), (0.15, 'M', None), (None, None, 0.049), (None, None, 0.05), (None, None, None), (100.0, 'mM', 0.01), (300.0, 'mM', 0.049)):
        record = synthetic_record()
        for name, value, quantity_unit in (('nacl_wash', salt, unit), ('detergent_wash', detergent, 'percent')):
            if value is None:
                missing(record, name)
            else:
                record['quantities'][name] = point(value, quantity_unit, name, ['s'])
        out.append(record)
    for name, values, unit in (('wash_count', (2, 3, None), 'count'), ('incubation_time', (29.0, 30.0, 0.4, None), 'min'), ('fold_enrichment', (2.9, 3.0, None), 'ratio'), ('replicate_count', (2, 3, None), 'count')):
        for value in values:
            record = synthetic_record()
            if value is None:
                missing(record, name)
            else:
                record['quantities'][name] = point(value, 'h' if value == 0.4 else unit, name, ['s'])
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
        graded = grade_pulldown(record)
        for name, outcome in graded['criteria'].items():
            if outcome['status'] in ('supported', 'conflicting'):
                seen.add((name, outcome['status'], graded['reasons'][name]))
                assert outcome['support_refs'], (record['experiment_ref'], name, graded['reasons'][name])
            else:
                assert outcome['support_refs'] == []
    # every supported or conflicting case the criteria declare was reached by some variant, and so was checked for its refs
    declared = {(criterion['id'], status, why) for criterion in PULLDOWN_CRITERIA for status, why, _ in criterion['returns'] if status in ('supported', 'conflicting')}
    assert seen == declared


def test_a_decided_criterion_cannot_be_built_without_support_refs():
    record = synthetic_record()
    record['facts']['input_lane_shown'] = fact('yes')               # a fact answered yes with no span: it cannot be supported
    with pytest.raises(ValueError, match='needs support refs'):
        grade_pulldown(record)


@pytest.mark.parametrize('criterion, name', [('prey_in_eluate', 'prey_detected_in_eluate'), ('bait_minus_control', 'bait_minus_control_done'), ('input_lane', 'input_lane_shown'), ('reciprocal', 'reciprocal_done'),
                                             ('competition', 'competition_disrupts_interaction'), ('nuclease', 'interaction_survives_nuclease'), ('specificity', 'specificity_validated'),
                                             ('expression_level', 'endogenous_expression_levels'), ('quantification', 'quantification_with_normalization')])
def test_a_one_fact_criterion_follows_its_fact(criterion, name):
    r = synthetic_record()
    assert (status(r, criterion), reason(r, criterion)) == ('supported', 'facts_answered_yes')
    r['facts'][name] = fact('no', ['s'])
    assert (status(r, criterion), reason(r, criterion)) == ('conflicting', 'fact_answered_no')
    r['facts'][name] = fact('unknown')
    assert (status(r, criterion), reason(r, criterion)) == ('unknown', 'fact_unknown')
    r['facts'][name] = fact('not_applicable')
    assert (status(r, criterion), reason(r, criterion)) == ('not_applicable', 'fact_not_applicable')


def test_the_negative_control_needs_the_control_and_the_prey_absent_from_it():
    r = synthetic_record()
    assert (status(r, 'negative_control'), reason(r, 'negative_control')) == ('supported', 'prey_absent_from_control')
    r['facts']['prey_absent_in_negative_control'] = fact('no', ['s'])                      # the prey sticks to the control: a sticky prey
    assert (status(r, 'negative_control'), reason(r, 'negative_control')) == ('conflicting', 'prey_found_in_negative_control')
    r['facts']['prey_absent_in_negative_control'] = fact('unknown')
    assert (status(r, 'negative_control'), reason(r, 'negative_control')) == ('unknown', 'negative_control_result_unknown')          # the control is done, its result is not stated
    r['facts']['negative_control_done'] = fact('no', ['s'])
    assert (status(r, 'negative_control'), reason(r, 'negative_control')) == ('conflicting', 'negative_control_not_done')
    r['facts']['negative_control_done'] = fact('not_applicable')
    r['facts']['prey_absent_in_negative_control'] = fact('not_applicable')
    assert status(r, 'negative_control') == 'not_applicable'


def test_the_wash_salt_and_detergent_are_recorded_for_the_sheet():
    r = synthetic_record()                                                                 # 300 mM and 0.1 percent
    graded = grade_pulldown(r)
    assert (graded['criteria']['wash_stringency'], graded['reasons']['wash_stringency']) == ({'status': 'unknown', 'support_refs': []}, 'wash_recorded_for_the_sheet')
    assert graded['native']['nacl_wash_mM'] == 300.0 and graded['native']['detergent_percent'] == 0.1 and graded['native']['nacl_wash_refs'] == ['span_exp_synthetic_pulldown_1']
    assert status(r, 'wash_stringency') == 'supported'
    r['quantities']['nacl_wash'] = point(0.15, 'M', 'n', ['s'])                            # 150 mM in molar: the sheet's full-agreement limit
    assert grade_pulldown(r)['native']['nacl_wash_mM'] == 150.0 and judged(r, 'wash_stringency')['status'] == 'supported' and judged(r, 'wash_stringency')['degree'] == 1.0
    r['quantities']['nacl_wash'] = point(100.0, 'mM', 'n', ['s'])                          # halfway between the zero limit (50) and the full limit (150)
    assert judged(r, 'wash_stringency')['degree'] == pytest.approx(0.5) and 's' in judged(r, 'wash_stringency')['support_refs']
    r['quantities']['nacl_wash'] = point(50.0, 'mM', 'n', ['s'])                           # the zero limit
    assert status(r, 'wash_stringency') == 'conflicting' and judged(r, 'wash_stringency')['support_refs'] == ['s'] and 'degree' not in judged(r, 'wash_stringency')
    r['quantities']['nacl_wash'] = point(300.0, 'mM', 'n', ['s'])
    r['quantities']['detergent_wash'] = point(0.05, 'percent', 'd', ['s2'])                # the sheet's full-agreement limit
    assert judged(r, 'wash_stringency')['degree'] == 1.0
    r['quantities']['detergent_wash'] = point(0.04, 'percent', 'd', ['s2'])                # 0.04 / 0.05
    assert status(r, 'wash_stringency') == 'supported' and judged(r, 'wash_stringency')['degree'] == pytest.approx(0.8)
    r['quantities']['detergent_wash'] = point(0.0, 'percent', 'd', ['s2'])                 # no detergent: the zero limit decides
    assert status(r, 'wash_stringency') == 'conflicting' and judged(r, 'wash_stringency')['support_refs'] == ['s2']
    r['quantities']['nacl_wash'] = point(100.0, 'mM', 'n', ['s'])                          # a conflicting component decides over a partial one
    assert status(r, 'wash_stringency') == 'conflicting'
    missing(r, 'nacl_wash')                                                                # only the detergent is stated
    r['quantities']['detergent_wash'] = point(0.025, 'percent', 'd', ['s2'])
    assert judged(r, 'wash_stringency') == {'status': 'supported', 'support_refs': ['s2'], 'degree': pytest.approx(0.5)}
    r['quantities']['detergent_wash'] = point(0.1, 'percent', 'd', ['s2'])
    assert grader_status(r, 'wash_stringency') == 'unknown' and status(r, 'wash_stringency') == 'supported'
    missing(r, 'detergent_wash')
    assert (grader_status(r, 'wash_stringency'), reason(r, 'wash_stringency')) == ('unknown', 'wash_stringency_not_given')


def test_the_number_of_washes_is_recorded_and_the_sheet_judges_the_count():
    r = synthetic_record()
    assert (grader_status(r, 'wash_count'), reason(r, 'wash_count')) == ('unknown', 'wash_count_recorded_for_the_sheet')
    for count, expected in ((3, 'supported'), (2, 'conflicting'), (5, 'supported')):
        r['quantities']['wash_count'] = point(count, 'count', 'w', ['s'])
        assert status(r, 'wash_count') == expected, count
        assert grade_pulldown(r)['native']['wash_count'] == count and 'degree' not in judged(r, 'wash_count') and judged(r, 'wash_count')['support_refs'] == ['s']
    missing(r, 'wash_count')
    assert (status(r, 'wash_count'), reason(r, 'wash_count')) == ('unknown', 'wash_count_not_given')


def test_the_incubation_time_is_recorded_in_minutes_and_the_sheet_judges_it_with_a_degree():
    r = synthetic_record()
    assert (grader_status(r, 'incubation'), reason(r, 'incubation')) == ('unknown', 'incubation_recorded_for_the_sheet') and grade_pulldown(r)['native']['incubation_min'] == 120.0
    for value, unit, expected, degree in ((30.0, 'min', 'supported', 1.0), (16.0, 'h', 'supported', 1.0), (1800.0, 's', 'supported', 1.0), (17.5, 'min', 'supported', 0.5), (1500.0, 's', 'supported', 0.8), (5.0, 'min', 'conflicting', None), (0.05, 'h', 'conflicting', None)):
        r['quantities']['incubation_time'] = point(value, unit, 'i', ['s'])
        verdict = judged(r, 'incubation')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), (value, unit)
        assert verdict['support_refs'] == ['s']
    missing(r, 'incubation_time')
    assert (status(r, 'incubation'), reason(r, 'incubation')) == ('unknown', 'incubation_time_not_given')


def test_the_fold_enrichment_over_the_control_is_recorded_and_judged_with_a_degree():
    r = synthetic_record()
    assert (grader_status(r, 'enrichment'), reason(r, 'enrichment')) == ('unknown', 'fold_enrichment_recorded_for_the_sheet') and grade_pulldown(r)['native']['fold_enrichment'] == 12.0
    for value, expected, degree in ((3.0, 'supported', 1.0), (12.0, 'supported', 1.0), (2.0, 'supported', 0.5), (2.5, 'supported', 0.75), (1.0, 'conflicting', None), (0.5, 'conflicting', None)):
        r['quantities']['fold_enrichment'] = point(value, 'ratio', 'f', ['s'])
        verdict = judged(r, 'enrichment')
        assert verdict['status'] == expected and verdict.get('degree') == (pytest.approx(degree) if degree is not None else None), value
        assert verdict['support_refs'] == ['s'] and grade_pulldown(r)['native']['fold_enrichment_refs'] == ['s']
    missing(r, 'fold_enrichment')
    assert (status(r, 'enrichment'), reason(r, 'enrichment')) == ('unknown', 'enrichment_not_given')


def test_a_direct_interaction_is_a_gain_and_its_absence_is_never_a_conflict():
    r = synthetic_record()
    assert (status(r, 'direct_interaction'), reason(r, 'direct_interaction')) == ('supported', 'facts_answered_yes')
    for answer in ('no', 'unknown'):                                                       # a lysate co-IP shows a complex, which the claim accepts
        r['facts']['direct_interaction_shown'] = fact(answer, ['s'] if answer == 'no' else [])
        assert (status(r, 'direct_interaction'), reason(r, 'direct_interaction')) == ('unknown', 'direct_interaction_not_shown')
    r['facts']['direct_interaction_shown'] = fact('not_applicable')
    assert status(r, 'direct_interaction') == 'not_applicable'


def test_replicates_are_independent_experiments_and_lanes_do_not_count():
    r = synthetic_record()
    assert (grader_status(r, 'replicates'), reason(r, 'replicates')) == ('unknown', 'replicate_count_recorded_for_the_sheet')
    assert grade_pulldown(r)['native']['replicate_count'] == 3 and grade_pulldown(r)['native']['replicate_independent'] == 'yes' and status(r, 'replicates') == 'supported'
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


def test_the_qualitative_statement_follows_the_detection_fact():
    r = synthetic_record()
    assert grade_pulldown(r)['native']['interaction'] == 'detected'
    r['facts']['prey_detected_in_eluate'] = fact('no', ['span_no'])
    native = grade_pulldown(r)['native']
    assert native['interaction'] == 'not_detected' and native['interaction_refs'] == ['span_no']
    for answer in ('unknown', 'not_applicable'):
        r['facts']['prey_detected_in_eluate'] = fact(answer)
        native = grade_pulldown(r)['native']
        assert native['interaction'] is None and native['interaction_refs'] == []


def test_the_grader_keeps_the_support_of_the_fields_each_criterion_reads_and_does_not_judge_it():
    r = synthetic_record()
    r['facts']['reciprocal_done']['support'] = 'implied'
    r['quantities']['replicate_count']['support'] = 'about_something_else'
    graded = grade_pulldown(r)
    support = graded['native']['support']
    assert set(support) == set(CRITERIA)
    assert support['reciprocal'] == ['implied'] and 'about_something_else' in support['replicates'] and support['nuclease'] == ['direct']
    assert graded['criteria']['reciprocal']['status'] == 'supported'      # the status is the grader's own: support does not change it
    assert grade_pulldown(sparse_record())['native']['support']['reciprocal'] == []      # an unknown fact is not stated: no support
