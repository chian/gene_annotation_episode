"""BRET grader: judges ONE BRET / NanoBRET experiment (bioluminescence resonance energy transfer in cells: a luciferase donor on one protein, a fluorescent acceptor or tracer on the other; a saturation titration over the acceptor-to-donor ratio gives BRETmax and BRET50, a tracer titration or displacement gives an apparent KD or Ki) by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis or AUC graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_bret_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_bret_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on);
``_result`` refuses to build one without them. Where only a fact with no span would decide, the criterion returns 'unknown' with a declared reason.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown;
else all 'not_applicable' -> not_applicable; else supported. The other criteria have their own rules (declared).

A BRET experiment has two outcomes. With a tracer titration or a displacement it reports an apparent KD or a Ki (native 'kd_nM' / 'ki_nM', the KD first); without one it reports only the
interaction (a BRET ratio, a BRET50, a saturation). The native values carry the qualitative statement of the record, 'interaction' ('detected' when the interaction fact is yes, 'not_detected' when it is no, else None), with the spans that state it ('interaction_refs');
the converter hands it to the merger as the experiment's qualitative effect when the record has no constant.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs (bret50_control_over_pair/bret50_refs, signal_over_control/signal_refs,
titration_point_count/titration_refs, low_over_bret50/high_over_bret50/range_refs, fit_r_squared/fit_refs, replicate_count/replicate_independent/replicate_refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet'; the BRET converter judges it.

Support: native 'support' holds, for each criterion, the supports ('direct', 'implied', 'about_something_else') of the stated fields it reads
(its declared 'reads'), copied from the record and not judged here; the converter judges them.

Native values retained: every record quantity as given, plus kd_nM, ki_nM, constant_name, constant_nM, tracer_nM, bret50_control_over_pair, signal_over_control, low_over_bret50, high_over_bret50, interaction, interaction_refs, preparations, bret_format, donor,
acceptor, expression and spread_kind.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bret_criteria import (
    BRET_CRITERIA, NM_PER_UNIT, RATIO_PER_SIGNAL_UNIT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_bret_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in BRET_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact interaction_detected
CONSTANTS = ('kd', 'ki')                                  # the order in which the binding constant of a record is taken
NO_BRET50 = 'no_bret50_reported'


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


def _format_fact(record, name, formats, reason):
    """The fact decides; an unknown fact is not applicable for a run stated as one of ``formats``."""
    item = record['facts'][name]
    status, why = _shared_rule([item['answer']])
    if status == 'unknown' and record['bret_format'] in formats:
        return _result('not_applicable', reason, [])
    return _result(status, why, item['source_refs'])


def _interaction_observed(record, native):
    return _one_fact(record, 'interaction_detected')


def _saturation_shown(record, native):
    return _format_fact(record, 'saturation_shown', ('competition_displacement', 'ligand_induced_change'), 'not_a_saturation_run')


def _bret50_specificity(record, native):
    pair, control = _value(record, 'bret50'), _value(record, 'bret50_negative_control')
    if pair is None or control is None:
        return _result('unknown', 'bret50_comparison_not_given', [])
    native.update({'bret50_control_over_pair': control / pair, 'bret50_refs': _refs(record['quantities']['bret50'], record['quantities']['bret50_negative_control'])})
    return _result('unknown', 'bret50_comparison_recorded_for_the_sheet', [])


def _signal_over_control(record, native):
    pair, control = _scaled(record, 'bret_ratio_pair', RATIO_PER_SIGNAL_UNIT), _scaled(record, 'bret_ratio_negative_control', RATIO_PER_SIGNAL_UNIT)
    if pair is None or control is None:
        return _result('unknown', 'signal_over_control_not_given', [])
    native.update({'signal_over_control': pair / control, 'signal_refs': _refs(record['quantities']['bret_ratio_pair'], record['quantities']['bret_ratio_negative_control'])})
    return _result('unknown', 'signal_over_control_recorded_for_the_sheet', [])


def _donor_only_control(record, native):
    return _one_fact(record, 'donor_only_control_done')


def _acceptor_only_control(record, native):
    return _one_fact(record, 'acceptor_only_control_done')


def _negative_control(record, native):
    items = [record['facts']['negative_control_pair_used'], record['facts']['negative_control_no_specific_signal']]
    status, reason = _shared_rule([item['answer'] for item in items])
    deciding = [item for item in items if item['answer'] == 'no'] if status == 'conflicting' else items
    return _result(status, reason, _refs(*deciding))


def _expression_matching(record, native):
    return _one_fact(record, 'expression_levels_measured')


def _titration_points(record, native):
    count = _value(record, 'titration_point_count')
    if count is None:
        return _result('unknown', 'titration_point_count_not_given', [])
    native.update({'titration_point_count': count, 'titration_refs': _refs(record['quantities']['titration_point_count'])})
    return _result('unknown', 'titration_point_count_recorded_for_the_sheet', [])


def _ratio_range(record, native):
    bret50 = _value(record, 'bret50')
    if bret50 is None:
        return _result('not_applicable', NO_BRET50, [])
    lowest, highest = _value(record, 'ratio_lowest'), _value(record, 'ratio_highest')
    if lowest is None or highest is None:
        return _result('unknown', 'ratio_range_not_given', [])
    native.update({'low_over_bret50': lowest / bret50, 'high_over_bret50': highest / bret50,
                   'range_refs': _refs(record['quantities']['ratio_lowest'], record['quantities']['ratio_highest'], record['quantities']['bret50'])})
    return _result('unknown', 'ratio_range_recorded_for_the_sheet', [])


def _competition(record, native):
    return _format_fact(record, 'tracer_displaced_by_competitor', ('saturation_titration', 'ligand_induced_change'), 'not_a_competition_run')


def _orientation(record, native):
    return _one_fact(record, 'fusion_orientation_swapped')


def _background_correction(record, native):
    return _one_fact(record, 'background_subtracted')


def _fit_quality(record, native):
    r_squared = record['quantities']['fit_r_squared']
    if r_squared['status'] != 'point':
        return _result('unknown', 'fit_r_squared_not_given', [])
    native.update({'fit_r_squared': r_squared['value'], 'fit_refs': _refs(r_squared)})
    return _result('unknown', 'fit_r_squared_recorded_for_the_sheet', [])


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


EVALUATORS = {'interaction_observed': _interaction_observed, 'saturation_shown': _saturation_shown, 'bret50_specificity': _bret50_specificity, 'signal_over_control': _signal_over_control, 'donor_only_control': _donor_only_control, 'acceptor_only_control': _acceptor_only_control, 'negative_control': _negative_control, 'expression_matching': _expression_matching, 'titration_points': _titration_points, 'ratio_range': _ratio_range, 'competition': _competition, 'orientation': _orientation, 'background_correction': _background_correction, 'fit_quality': _fit_quality, 'replicates': _replicates}


def grade_bret(record):
    """Grade one BRET experiment record. Returns the criterion answers and native values."""
    found = record['facts']['interaction_detected']
    nm = {name: _scaled(record, name, NM_PER_UNIT) for name in CONSTANTS}
    constant_name = next((name for name in CONSTANTS if nm[name] is not None), None)
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'bret_format': record['bret_format'], 'donor': record['donor'], 'acceptor': record['acceptor'], 'expression': record['expression'], 'spread_kind': record['spread_kind'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'interaction': INTERACTION.get(found['answer']), 'interaction_refs': list(found['source_refs']) if found['answer'] in INTERACTION else [], 'kd_nM': nm['kd'], 'ki_nM': nm['ki'], 'constant_name': constant_name, 'constant_nM': None if constant_name is None else nm[constant_name], 'tracer_nM': _scaled(record, 'tracer_concentration', NM_PER_UNIT), 'bret50_control_over_pair': None, 'bret50_refs': [], 'signal_over_control': None, 'signal_refs': [], 'titration_point_count': None, 'titration_refs': [], 'low_over_bret50': None, 'high_over_bret50': None, 'range_refs': [], 'fit_r_squared': None, 'fit_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, BRET_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'bret', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
