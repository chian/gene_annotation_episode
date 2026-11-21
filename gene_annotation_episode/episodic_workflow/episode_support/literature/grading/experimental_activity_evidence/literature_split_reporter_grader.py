"""Split-reporter grader: judges ONE split-reporter (protein-fragment complementation: split luciferase such as NanoBiT, split GFP / BiFC, split beta-lactamase, split TEV) experiment (two fragments of a reporter are fused to the two candidate partners; when the partners come together the reporter is reconstituted and its signal reports proximity or interaction in cells, in a lysate or with purified proteins; a titration or a kinetic time course of a reversible reporter can give an apparent KD) by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis or AUC graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_split_reporter_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_split_reporter_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on);
``_result`` refuses to build one without them. Where only a fact with no span would decide, the criterion returns 'unknown' (or
'not_applicable' when no KD is reported and the criterion needs one) with a declared reason.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown;
else all 'not_applicable' -> not_applicable; else supported.

A split reporter has two outcomes. With a titration of a reversible reporter it can report an apparent KD (native 'kd_nM', labelled as derived from the split reporter); without one it reports only that a signal
was seen. The native values carry the qualitative statement of the record, 'interaction' ('detected' when a signal is stated, 'not_detected' when it is
stated not to be, else None), with the spans that state it ('interaction_refs'); the converter hands it to the merger as the experiment's qualitative
effect when the record has no KD.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs (signal_to_background/signal_to_background_refs,
signal_over_negative_control/signal_over_negative_control_refs, orientation_pairs_tested/orientation_pairs_refs, concentration_count/concentration_count_refs, low_over_kd/high_over_kd/range_refs,
replicate_count/replicate_independent/replicate_refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the split-reporter converter judges it.

Support: native 'support' holds, for each criterion, the supports ('direct', 'implied', 'about_something_else') of the stated fields it reads
(its declared 'reads'), copied from the record and not judged here; the converter judges them.

Native values retained: every record quantity as given, plus kd_nM, lowest_nM, highest_nM, interaction, interaction_refs, the recorded numbers above, preparations, reporter_system, assay_system, readout_mode and spread_kind.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_split_reporter_criteria import (
    NM_PER_UNIT, SPLIT_REPORTER_CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_split_reporter_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in SPLIT_REPORTER_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact interaction_detected
NO_KD = 'no_apparent_kd_reported'


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


def _interaction_observed(record, native):
    return _one_fact(record, 'interaction_detected')


def _ratio(record, native, criterion, quantity):
    value = _value(record, quantity)
    if value is None:
        return _result('unknown', criterion + '_not_given', [])
    native.update({quantity: value, quantity + '_refs': _refs(record['quantities'][quantity])})
    return _result('unknown', criterion + '_recorded_for_the_sheet', [])


def _signal_to_background(record, native):
    return _ratio(record, native, 'signal_to_background', 'signal_to_background')


def _negative_control_ratio(record, native):
    return _ratio(record, native, 'negative_control_ratio', 'signal_over_negative_control')


def _fragment_alone_control(record, native):
    return _one_fact(record, 'fragment_alone_control_negative')


def _unrelated_pair_control(record, native):
    return _one_fact(record, 'unrelated_pair_control_negative')


def _binding_mutant_control(record, native):
    return _one_fact(record, 'binding_mutant_control_negative')


def _positive_control(record, native):
    return _one_fact(record, 'positive_control_done')


def _fusion_orientations(record, native):
    item = record['facts']['signal_in_several_orientations']
    if item['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', item['source_refs'])
    count = _value(record, 'orientation_pairs_tested')
    if count is None:
        return _one_fact(record, 'signal_in_several_orientations')
    native.update({'orientation_pairs_tested': count, 'orientation_pairs_refs': _refs(record['quantities']['orientation_pairs_tested'])})
    return _result('unknown', 'orientation_pairs_recorded_for_the_sheet', [])


def _expression_verified(record, native):
    return _one_fact(record, 'expression_verified')


def _saturable_titration(record, native):
    return _one_fact(record, 'saturable_titration_shown')


def _titration_series(record, native):
    if native['kd_nM'] is None:
        return _result('not_applicable', NO_KD, [])
    count = _value(record, 'concentration_count')
    if count is None:
        return _result('unknown', 'concentration_count_not_given', [])
    native.update({'concentration_count': count, 'concentration_count_refs': _refs(record['quantities']['concentration_count'])})
    return _result('unknown', 'concentration_count_recorded_for_the_sheet', [])


def _titration_range(record, native):
    if native['kd_nM'] is None:
        return _result('not_applicable', NO_KD, [])
    lowest, highest = native['lowest_nM'], native['highest_nM']
    if lowest is None or highest is None:
        return _result('unknown', 'titration_range_not_given', [])
    native.update({'low_over_kd': lowest / native['kd_nM'], 'high_over_kd': highest / native['kd_nM'],
                   'range_refs': _refs(record['quantities']['loaded_concentration_lowest'], record['quantities']['loaded_concentration_highest'], record['quantities']['kd'])})
    return _result('unknown', 'titration_range_recorded_for_the_sheet', [])


def _reversible_reporter(record, native):
    return _one_fact(record, 'complementation_reversible')


def _background_correction(record, native):
    return _one_fact(record, 'background_subtracted')


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


EVALUATORS = {'interaction_observed': _interaction_observed, 'signal_to_background': _signal_to_background, 'negative_control_ratio': _negative_control_ratio, 'fragment_alone_control': _fragment_alone_control, 'unrelated_pair_control': _unrelated_pair_control, 'binding_mutant_control': _binding_mutant_control, 'positive_control': _positive_control, 'fusion_orientations': _fusion_orientations, 'expression_verified': _expression_verified, 'saturable_titration': _saturable_titration, 'titration_series': _titration_series, 'titration_range': _titration_range, 'reversible_reporter': _reversible_reporter, 'background_correction': _background_correction, 'replicates': _replicates}


def grade_split_reporter(record):
    """Grade one split-reporter experiment record. Returns the criterion answers and native values."""
    found = record['facts']['interaction_detected']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'reporter_system': record['reporter_system'], 'assay_system': record['assay_system'], 'readout_mode': record['readout_mode'], 'spread_kind': record['spread_kind'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'interaction': INTERACTION.get(found['answer']), 'interaction_refs': list(found['source_refs']) if found['answer'] in INTERACTION else [], 'kd_nM': _scaled(record, 'kd', NM_PER_UNIT), 'lowest_nM': _scaled(record, 'loaded_concentration_lowest', NM_PER_UNIT), 'highest_nM': _scaled(record, 'loaded_concentration_highest', NM_PER_UNIT), 'signal_to_background': None, 'signal_to_background_refs': [], 'signal_over_negative_control': None, 'signal_over_negative_control_refs': [], 'orientation_pairs_tested': None, 'orientation_pairs_refs': [], 'concentration_count': None, 'concentration_count_refs': [], 'low_over_kd': None, 'high_over_kd': None, 'range_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, SPLIT_REPORTER_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'split_reporter', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
