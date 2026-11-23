"""Pull-down / co-IP grader: judges ONE pull-down or co-immunoprecipitation experiment (a tagged or antibody-captured bait on beads from a lysate or from purified proteins, wash, elution, detection of the prey by western blot or mass spectrometry; qualitative to semi-quantitative) by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand or SPA graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_pulldown_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_pulldown_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(nacl_wash_mM/nacl_wash_refs, detergent_percent/detergent_wash_refs, wash_count/wash_count_refs, incubation_min/incubation_refs,
fold_enrichment/fold_enrichment_refs (with fold_enrichment_sd/_sem and their refs), positive_control/positive_control_refs, replicate_count/replicate_independent/replicate_refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet' and no refs; the pull-down converter (literature_pulldown_converter.py) judges it. A fact stated as no stays the
grader's own conflicting.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on);
``_result`` refuses to build one without them.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown;
else all 'not_applicable' -> not_applicable; else supported. negative_control, positive_control, wash_stringency, wash_count, incubation,
direct_interaction, enrichment and replicates have their own rules (declared).

A pull-down reports no binding constant. The native values carry instead the qualitative statement of the record, 'interaction'
('detected' when the prey is stated in the eluate of the specific capture, 'not_detected' when it is stated not to be, else None), with the
spans that state it ('interaction_refs'); the converter hands it to the merger as the experiment's qualitative effect.

Native values retained: every record quantity as given, plus interaction, interaction_refs, nacl_wash_mM, incubation_min,
preparations, detection_method, capture_format, protein_source, nuclease_treatment and crosslinker, and 'support': for each criterion the
supports ('direct', 'implied', 'about_something_else') of the stated fields it reads, copied from the record and not judged here.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pulldown_criteria import (
    MIN_PER_UNIT, MM_PER_UNIT, PULLDOWN_CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_pulldown_grade'
CRITERIA = tuple(criterion['id'] for criterion in PULLDOWN_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact prey_detected_in_eluate


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _scaled(record, name, scale):
    value = _value(record, name)
    return None if value is None else value * scale[record['quantities'][name]['unit']]


def _refs(*items):
    refs = []
    for item in items:
        refs += item['source_refs']
    return list(dict.fromkeys(refs))


def _shared_rule(answers):
    if 'no' in answers:
        return 'conflicting', 'fact_answered_no'
    if 'unknown' in answers:
        return 'unknown', 'fact_unknown'
    if all(a == 'not_applicable' for a in answers):
        return 'not_applicable', 'fact_not_applicable'
    return 'supported', 'facts_answered_yes'


def _result(status, reason, refs):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' criterion needs support refs: ' + reason)
    return {'status': status, 'reason': reason, 'support_refs': refs if status in ('supported', 'conflicting') else []}


def _one_fact(record, name):
    item = record['facts'][name]
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, item['source_refs'])


def _recorded(record, native, name, number_key, refs_key, handed, not_given):
    """A stated number is recorded with its refs for the sheet to judge; ``handed`` / ``not_given`` are the reason codes."""
    value = _value(record, name)
    if value is None:
        return _result('unknown', not_given, [])
    native.update({number_key: value, refs_key: _refs(record['quantities'][name])})
    return _result('unknown', handed, [])


def _prey_in_eluate(record, native):
    return _one_fact(record, 'prey_detected_in_eluate')


def _negative_control(record, native):
    done, absent = record['facts']['negative_control_done'], record['facts']['prey_absent_in_negative_control']
    if absent['answer'] == 'no':
        return _result('conflicting', 'prey_found_in_negative_control', absent['source_refs'])
    if done['answer'] == 'no':
        return _result('conflicting', 'negative_control_not_done', done['source_refs'])
    if absent['answer'] == 'yes':
        return _result('supported', 'prey_absent_from_control', absent['source_refs'])
    if done['answer'] == 'not_applicable' and absent['answer'] == 'not_applicable':
        return _result('not_applicable', 'fact_not_applicable', [])
    return _result('unknown', 'negative_control_result_unknown', [])


def _positive_control(record, native):
    """A stated yes or no is recorded for the sheet: whether a missing prey is a real absence depends on the prey's own statement, which the sheet reads."""
    item = record['facts']['positive_control_detected']
    if item['answer'] == 'not_applicable':
        return _result('not_applicable', 'fact_not_applicable', [])
    if item['answer'] == 'unknown':
        return _result('unknown', 'fact_unknown', [])
    native.update({'positive_control': item['answer'], 'positive_control_refs': list(item['source_refs'])})
    return _result('unknown', 'positive_control_recorded_for_the_sheet', [])


def _bait_minus_control(record, native):
    return _one_fact(record, 'bait_minus_control_done')


def _input_lane(record, native):
    return _one_fact(record, 'input_lane_shown')


def _reciprocal(record, native):
    return _one_fact(record, 'reciprocal_done')


def _competition(record, native):
    return _one_fact(record, 'competition_disrupts_interaction')


def _nuclease(record, native):
    return _one_fact(record, 'interaction_survives_nuclease')


def _specificity(record, native):
    return _one_fact(record, 'specificity_validated')


def _wash_stringency(record, native):
    salt, detergent = native['nacl_wash_mM'], _value(record, 'detergent_wash')
    if salt is None and detergent is None:
        return _result('unknown', 'wash_stringency_not_given', [])
    native.update({'detergent_percent': detergent, 'nacl_wash_refs': _refs(record['quantities']['nacl_wash']), 'detergent_wash_refs': _refs(record['quantities']['detergent_wash'])})
    return _result('unknown', 'wash_recorded_for_the_sheet', [])


def _wash_count(record, native):
    return _recorded(record, native, 'wash_count', 'wash_count', 'wash_count_refs', 'wash_count_recorded_for_the_sheet', 'wash_count_not_given')


def _incubation(record, native):
    if native['incubation_min'] is None:
        return _result('unknown', 'incubation_time_not_given', [])
    native['incubation_refs'] = _refs(record['quantities']['incubation_time'])
    return _result('unknown', 'incubation_recorded_for_the_sheet', [])


def _expression_level(record, native):
    return _one_fact(record, 'endogenous_expression_levels')


def _direct_interaction(record, native):
    item = record['facts']['direct_interaction_shown']
    if item['answer'] == 'yes':
        return _result('supported', 'facts_answered_yes', item['source_refs'])
    if item['answer'] == 'not_applicable':
        return _result('not_applicable', 'fact_not_applicable', [])
    return _result('unknown', 'direct_interaction_not_shown', [])


def _enrichment(record, native):
    """The fold with its stated spread (SD and SEM kept apart: they differ by sqrt(n)); a spread without a fold is not recorded."""
    outcome = _recorded(record, native, 'fold_enrichment', 'fold_enrichment', 'fold_enrichment_refs', 'fold_enrichment_recorded_for_the_sheet', 'enrichment_not_given')
    if native['fold_enrichment'] is not None:
        for name in ('fold_enrichment_sd', 'fold_enrichment_sem'):
            if _value(record, name) is not None:
                native.update({name: _value(record, name), name + '_refs': _refs(record['quantities'][name])})
    return outcome


def _quantification(record, native):
    return _one_fact(record, 'quantification_with_normalization')


def _replicates(record, native):
    count = _value(record, 'replicate_count')
    independent = record['facts']['independent_experiments']
    refs = _refs(record['quantities']['replicate_count'], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', 'replicates_not_independent', refs)
    if count is None:
        return _result('unknown', 'replicate_count_or_independence_unknown', [])
    native.update({'replicate_count': count, 'replicate_independent': independent['answer'], 'replicate_refs': refs})
    return _result('unknown', 'replicate_count_recorded_for_the_sheet', [])


EVALUATORS = {'prey_in_eluate': _prey_in_eluate, 'negative_control': _negative_control, 'positive_control': _positive_control, 'bait_minus_control': _bait_minus_control, 'input_lane': _input_lane, 'reciprocal': _reciprocal, 'competition': _competition, 'nuclease': _nuclease, 'specificity': _specificity, 'wash_stringency': _wash_stringency, 'wash_count': _wash_count, 'incubation': _incubation, 'expression_level': _expression_level, 'direct_interaction': _direct_interaction, 'enrichment': _enrichment, 'quantification': _quantification, 'replicates': _replicates}


def grade_pulldown(record):
    """Grade one pull-down or co-IP experiment record. Returns the criterion answers and native values."""
    detected = record['facts']['prey_detected_in_eluate']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'detection_method': record['detection_method'], 'capture_format': record['capture_format'], 'protein_source': record['protein_source'], 'nuclease_treatment': record['nuclease_treatment'], 'crosslinker': record['crosslinker'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'interaction': INTERACTION.get(detected['answer']), 'interaction_refs': list(detected['source_refs']) if detected['answer'] in INTERACTION else [], 'nacl_wash_mM': _scaled(record, 'nacl_wash', MM_PER_UNIT), 'incubation_min': _scaled(record, 'incubation_time', MIN_PER_UNIT), 'nacl_wash_refs': [], 'detergent_percent': None, 'detergent_wash_refs': [], 'wash_count': None, 'wash_count_refs': [], 'incubation_refs': [], 'fold_enrichment': None, 'fold_enrichment_refs': [], 'fold_enrichment_sd': None, 'fold_enrichment_sd_refs': [], 'fold_enrichment_sem': None, 'fold_enrichment_sem_refs': [], 'positive_control': None, 'positive_control_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, PULLDOWN_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'pulldown', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
