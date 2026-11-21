"""Proximity-labeling grader: judges ONE proximity-labeling experiment (a bait fused to a biotin ligase such as BioID or TurboID, or to the peroxidase APEX2, or a split version, biotinylates proteins within about 10 to 20 nm in living cells; the biotinylated proteins are captured on streptavidin and identified by western blot or mass spectrometry; a candidate partner is called proximal when it is enriched over a control; qualitative or semi-quantitative, no binding constant) by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis or AUC graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_proximity_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_proximity_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on);
``_result`` refuses to build one without them.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown;
else all 'not_applicable' -> not_applicable; else supported.

A proximity-labeling experiment reports no binding constant. The native values carry the qualitative statement of the record, 'interaction' ('detected' when the candidate is stated enriched, i.e. proximal,
'not_detected' when it is stated not to be, else None), with the spans that state it ('interaction_refs'); the converter hands it to the merger as the experiment's qualitative effect.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs (fold_enrichment/fold_refs/fold_matched_control, fdr_percent/fdr_refs,
expression_ratio/expression_refs, replicate_count/replicate_independent/replicate_refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the proximity converter judges it.

Support: native 'support' holds, for each criterion, the supports ('direct', 'implied', 'about_something_else') of the stated fields it reads
(its declared 'reads'), copied from the record and not judged here; the converter judges them.

Native values retained: every record quantity as given, plus fold_enrichment (a ratio), fdr_percent, expression_ratio, interaction, interaction_refs, preparations, ligase, fusion_site, cell_system, readout and quantification.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_proximity_criteria import (
    LOG2_BASE, PERCENT_PER_FRACTION, PROXIMITY_CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_proximity_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in PROXIMITY_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact candidate_enriched


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


def _not_enriched(record):
    return record['facts']['candidate_enriched']['answer'] == 'no'


def _proximity_observed(record, native):
    item = record['facts']['candidate_enriched']
    if item['answer'] in INTERACTION:
        return _result('supported', 'candidate_enrichment_stated', item['source_refs'])      # a stated result, positive or negative; its direction is the qualitative statement
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, item['source_refs'])


def _enrichment_magnitude(record, native):
    if _not_enriched(record):
        return _result('not_applicable', 'candidate_stated_not_enriched', [])
    operand = record['quantities']['enrichment_fold']
    if operand['status'] != 'point':
        return _result('unknown', 'enrichment_fold_not_given', [])
    ratio = LOG2_BASE ** operand['value'] if operand['unit'] == 'log2_ratio' else operand['value']
    native.update({'fold_enrichment': ratio, 'fold_refs': _refs(operand), 'fold_matched_control': record['facts']['fold_over_matched_control']['answer']})
    return _result('unknown', 'enrichment_fold_recorded_for_the_sheet', [])


def _enrichment_significance(record, native):
    if _not_enriched(record):
        return _result('not_applicable', 'candidate_stated_not_enriched', [])
    test = record['facts']['statistical_test_used']
    if test['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', test['source_refs'])
    rate = record['quantities']['enrichment_fdr']
    if rate['status'] != 'point':
        return _one_fact(record, 'statistical_test_used')
    percent = rate['value'] * PERCENT_PER_FRACTION if rate['unit'] == 'fraction' else rate['value']
    native.update({'fdr_percent': percent, 'fdr_refs': _refs(rate)})
    return _result('unknown', 'enrichment_fdr_recorded_for_the_sheet', [])


def _ligase_only_control(record, native):
    return _one_fact(record, 'ligase_only_control')


def _unlabeled_control(record, native):
    return _one_fact(record, 'unlabeled_control')


def _unrelated_bait_control(record, native):
    return _one_fact(record, 'unrelated_bait_control')


def _biotinylation_dependence(record, native):
    return _one_fact(record, 'biotinylation_confirmed')


def _streptavidin_capture(record, native):
    return _one_fact(record, 'streptavidin_capture')


def _expression_level(record, native):
    checked = record['facts']['bait_expression_checked']
    if checked['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', checked['source_refs'])
    ratio = record['quantities']['bait_expression_ratio']
    if ratio['status'] != 'point':
        return _one_fact(record, 'bait_expression_checked')
    native.update({'expression_ratio': ratio['value'], 'expression_refs': _refs(ratio)})
    return _result('unknown', 'expression_ratio_recorded_for_the_sheet', [])


def _localization(record, native):
    return _one_fact(record, 'bait_localization_checked')


def _orthogonal_validation(record, native):
    return _one_fact(record, 'orthogonal_validation')


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


EVALUATORS = {'proximity_observed': _proximity_observed, 'enrichment_magnitude': _enrichment_magnitude, 'enrichment_significance': _enrichment_significance, 'ligase_only_control': _ligase_only_control, 'unlabeled_control': _unlabeled_control, 'unrelated_bait_control': _unrelated_bait_control, 'biotinylation_dependence': _biotinylation_dependence, 'streptavidin_capture': _streptavidin_capture, 'expression_level': _expression_level, 'localization': _localization, 'orthogonal_validation': _orthogonal_validation, 'replicates': _replicates}


def grade_proximity(record):
    """Grade one proximity-labeling experiment record. Returns the criterion answers and native values."""
    enriched = record['facts']['candidate_enriched']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'ligase': record['ligase'], 'fusion_site': record['fusion_site'], 'cell_system': record['cell_system'], 'readout': record['readout'], 'quantification': record['quantification'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'interaction': INTERACTION.get(enriched['answer']), 'interaction_refs': list(enriched['source_refs']) if enriched['answer'] in INTERACTION else [], 'fold_enrichment': None, 'fold_refs': [], 'fold_matched_control': None, 'fdr_percent': None, 'fdr_refs': [], 'expression_ratio': None, 'expression_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, PROXIMITY_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'proximity', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
