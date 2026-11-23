"""Y2H grader: judges ONE yeast two-hybrid (Y2H) experiment (a pairwise interaction test in yeast: a bait fused to a DNA-binding domain and a prey fused to an activation domain activate a reporter, read as growth on selective medium or as beta-galactosidase activity, only if the two proteins interact; qualitative or semi-quantitative, no binding constant) by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis or AUC graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_y2h_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_y2h_criteria.py (the
single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on);
``_result`` refuses to build one without them. Where only a fact with no span would decide, the criterion returns 'unknown' with a declared reason.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown;
else all 'not_applicable' -> not_applicable; else supported.

A Y2H has no binding constant. The native values carry the qualitative statement of the record, 'interaction' ('detected' when an interaction is stated, 'not_detected' when it is
stated not to be, else None), with the spans that state it ('interaction_refs'); the converter hands it to the merger as the experiment's qualitative effect.

The grader holds NO threshold that judges goodness and no constant. Where a number would be compared with a limit it records the number with its refs (reporter_fold/reporter_fold_refs,
replicate_count/replicate_independent/replicate_refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the Y2H converter judges it.

Support: native 'support' holds, for each criterion, the supports ('direct', 'implied', 'about_something_else') of the stated fields it reads
(its declared 'reads'), copied from the record and not judged here; the converter judges them.

Gap pass 2026-11-21: the grader also records, for the sheet, the stated spread of the two activities (activity_spread, SD and SEM kept apart, with activity_spread_refs), the growth titre ratio (growth_titre, growth_titre_refs), the 3-AT of the bait-alone test and of the scoring
(bait_alone_three_at_mM, scoring_three_at_mM, bait_alone_three_at_refs) and a stated no of the positive control, the reciprocal orientation and the second reporter (positive_control, reciprocal_orientation, more_than_one_reporter = 'no', with their _refs);
none of these is conflicting here (the sheet judges them). A stated no of interaction_detected is not_applicable here (the qualitative effect carries it).

Native values retained: every record quantity as given, plus reporter_fold, reporter_fold_refs, interaction, interaction_refs, preparations, system_kind, bait_fusion_domain, prey_fusion_domain, yeast_strain and selective_medium_scored.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_y2h_criteria import Y2H_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_y2h_grade'
CRITERIA = tuple(criterion['id'] for criterion in Y2H_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact interaction_detected


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


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
    item = record['facts']['interaction_detected']
    if item['answer'] == 'no':
        return _result('not_applicable', 'negative_statement_carried_by_the_direction', [])      # the statement goes to the qualitative effect
    return _one_fact(record, 'interaction_detected')


def _fact_no_recorded(record, native, name, key, reason):
    """A one-fact criterion whose stated no is recorded for the sheet (native[key] = 'no' with its refs), not conflicting."""
    item = record['facts'][name]
    if item['answer'] == 'no':
        native.update({key: 'no', key + '_refs': list(item['source_refs'])})
        return _result('unknown', reason, [])
    return _one_fact(record, name)


def _bait_autoactivation(record, native):
    item = record['facts']['bait_alone_inactive']
    bait_at, scoring_at = _value(record, 'bait_alone_three_at_concentration'), _value(record, 'three_at_concentration')
    if item['answer'] == 'yes' and bait_at is not None and scoring_at is not None:
        native.update({'bait_alone_three_at_mM': bait_at, 'scoring_three_at_mM': scoring_at, 'bait_alone_three_at_refs': _refs(item, record['quantities']['bait_alone_three_at_concentration'], record['quantities']['three_at_concentration'])})
        return _result('unknown', 'bait_alone_three_at_recorded_for_the_sheet', [])
    return _one_fact(record, 'bait_alone_inactive')


def _prey_autoactivation(record, native):
    return _one_fact(record, 'prey_alone_inactive')


def _non_interacting_control(record, native):
    return _one_fact(record, 'non_interacting_control_done')


def _positive_control(record, native):
    return _fact_no_recorded(record, native, 'positive_control_done', 'positive_control', 'positive_control_failed_recorded_for_the_sheet')


def _reciprocal_orientation(record, native):
    return _fact_no_recorded(record, native, 'reciprocal_orientation_tested', 'reciprocal_orientation', 'one_orientation_only_recorded_for_the_sheet')


def _nonselective_growth(record, native):
    return _one_fact(record, 'nonselective_growth_shown')


def _expression_verified(record, native):
    return _one_fact(record, 'fusion_expression_verified')


def _reporter_concordance(record, native):
    return _fact_no_recorded(record, native, 'more_than_one_reporter_activated', 'more_than_one_reporter', 'one_reporter_only_recorded_for_the_sheet')


SPREADS = ('beta_galactosidase_interaction_sd', 'beta_galactosidase_interaction_sem', 'beta_galactosidase_negative_control_sd', 'beta_galactosidase_negative_control_sem')


def _stated(record, *names):
    return all(_value(record, name) is not None for name in names)


def _reporter_fold(record, native):
    pair, control = _value(record, 'beta_galactosidase_interaction'), _value(record, 'beta_galactosidase_negative_control')
    if pair is None or control is None:
        if _stated(record, 'growth_dilution_interaction', 'growth_dilution_negative_control'):
            return _result('not_applicable', 'growth_titre_is_the_readout', [])
        return _result('unknown', 'reporter_fold_not_given', [])
    spread = {name: _value(record, name) for name in SPREADS if _value(record, name) is not None}
    native.update({'reporter_fold': pair / control, 'reporter_fold_refs': _refs(record['quantities']['beta_galactosidase_interaction'], record['quantities']['beta_galactosidase_negative_control']),
                   'activity_spread': spread, 'activity_spread_refs': _refs(*(record['quantities'][name] for name in spread))})      # a spread without both activities is not recorded
    return _result('unknown', 'reporter_fold_recorded_for_the_sheet', [])


def _growth_titre(record, native):
    pair, control = _value(record, 'growth_dilution_interaction'), _value(record, 'growth_dilution_negative_control')
    if pair is None or control is None:
        if _stated(record, 'beta_galactosidase_interaction', 'beta_galactosidase_negative_control'):
            return _result('not_applicable', 'reporter_fold_is_the_readout', [])
        return _result('unknown', 'growth_titre_not_given', [])
    native.update({'growth_titre': pair / control, 'growth_titre_refs': _refs(record['quantities']['growth_dilution_interaction'], record['quantities']['growth_dilution_negative_control'])})
    return _result('unknown', 'growth_titre_recorded_for_the_sheet', [])


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


EVALUATORS = {'interaction_observed': _interaction_observed, 'bait_autoactivation': _bait_autoactivation, 'prey_autoactivation': _prey_autoactivation, 'non_interacting_control': _non_interacting_control, 'positive_control': _positive_control, 'reciprocal_orientation': _reciprocal_orientation, 'nonselective_growth': _nonselective_growth, 'expression_verified': _expression_verified, 'reporter_concordance': _reporter_concordance, 'reporter_fold': _reporter_fold, 'growth_titre': _growth_titre, 'replicates': _replicates}


def grade_y2h(record):
    """Grade one Y2H experiment record. Returns the criterion answers and native values."""
    found = record['facts']['interaction_detected']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'system_kind': record['system_kind'], 'bait_fusion_domain': record['bait_fusion_domain'], 'prey_fusion_domain': record['prey_fusion_domain'], 'yeast_strain': record['yeast_strain'], 'selective_medium_scored': record['selective_medium_scored'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'interaction': INTERACTION.get(found['answer']), 'interaction_refs': list(found['source_refs']) if found['answer'] in INTERACTION else [], 'reporter_fold': None, 'reporter_fold_refs': [], 'activity_spread': {}, 'activity_spread_refs': [], 'growth_titre': None, 'growth_titre_refs': [], 'bait_alone_three_at_mM': None, 'scoring_three_at_mM': None, 'bait_alone_three_at_refs': [], 'positive_control': None, 'positive_control_refs': [], 'reciprocal_orientation': None, 'reciprocal_orientation_refs': [], 'more_than_one_reporter': None, 'more_than_one_reporter_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, Y2H_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'y2h', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
