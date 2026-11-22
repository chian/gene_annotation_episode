"""Co-localization grader: judges ONE microscopy co-localization / recruitment experiment (fluorescence microscopy shows that one labelled protein is found where the other is: two labelled proteins co-localize in cells, one is recruited to the site that the other makes, in a native or a heterologous host or as purified proteins in droplets, on beads or on a membrane, and the localization is lost when the partner is absent or its binding region is removed; qualitative nearness evidence, no binding constant) by its own standards.

Hand-built and private to this method (it shares no grading logic with the other experiment graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_colocalization_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_colocalization_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on);
``_result`` refuses to build one without them. Where only a fact with no span would decide, the criterion returns 'unknown' with a declared reason.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown;
else all 'not_applicable' -> not_applicable; else supported. The other criteria have their own rules (declared).

A co-localization reports no binding constant. The native values carry the qualitative statement of the record, 'interaction' ('detected' when a co-localization or a recruitment is stated,
'not_detected' when it is stated not to be, else None), with the spans that state it ('interaction_refs'); the converter hands it to the merger as the experiment's qualitative effect.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs (colocalization_fraction /
colocalization_pearson / colocalization_enrichment / readout_refs, objects_counted / objects_counted_refs, replicate_count / replicate_independent / replicate_refs)
and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the co-localization converter judges it.

Support: native 'support' holds, for each criterion, the supports ('direct', 'implied', 'about_something_else') of the stated fields it reads
(its declared 'reads'), copied from the record and not judged here; the converter judges them.

Native values retained: every record quantity as given, plus colocalization_fraction, colocalization_pearson, colocalization_enrichment and readout_refs (each None or empty when not stated),
objects_counted and objects_counted_refs, replicate_count / replicate_independent / replicate_refs, interaction, interaction_refs, preparations and imaging_mode.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_colocalization_criteria import (
    COLOCALIZATION_CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_colocalization_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in COLOCALIZATION_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact colocalization_observed
NO_NATIVE_BRIDGE = ('heterologous_host', 'purified_proteins')   # the facts that say no native third protein could bridge the two


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


def _colocalization_observed(record, native):
    return _one_fact(record, 'colocalization_observed')


def _colocalization_readout(record, native):
    names = ('fraction_colocalized', 'pearson_coefficient', 'enrichment_ratio')
    stated = [name for name in names if _value(record, name) is not None]
    if not stated:
        return _result('unknown', 'colocalization_readout_not_given', [])
    native.update({'colocalization_fraction': _value(record, 'fraction_colocalized'), 'colocalization_pearson': _value(record, 'pearson_coefficient'), 'colocalization_enrichment': _value(record, 'enrichment_ratio'),
                   'readout_refs': _refs(*[record['quantities'][name] for name in stated])})
    return _result('unknown', 'colocalization_readout_recorded_for_the_sheet', [])


def _specificity_control(record, native):
    items = [record['facts']['unrelated_protein_not_recruited'], record['facts']['lost_without_partner']]
    answers = [item['answer'] for item in items]
    if 'no' in answers:
        return _result('conflicting', 'fact_answered_no', _refs(*[item for item in items if item['answer'] == 'no']))
    if 'yes' in answers:      # one stated control is a control
        return _result('supported', 'facts_answered_yes', _refs(*[item for item in items if item['answer'] == 'yes']))
    return _result('unknown', 'fact_unknown', [])


def _directness(record, native):
    items = [record['facts']['lost_with_binding_region_removed'], record['facts']['follows_partner_when_moved']]
    answers = [item['answer'] for item in items]
    if 'no' in answers:
        return _result('conflicting', 'fact_answered_no', _refs(*[item for item in items if item['answer'] == 'no']))
    if 'yes' in answers:
        return _result('supported', 'facts_answered_yes', _refs(*[item for item in items if item['answer'] == 'yes']))
    systems = [record['facts'][name] for name in NO_NATIVE_BRIDGE if record['facts'][name]['answer'] == 'yes']
    if systems:
        return _result('supported', 'system_without_a_native_bridge', _refs(*systems))
    return _result('unknown', 'native_host_or_system_unknown', [])


def _expression_validity(record, native):
    expression = record['facts']['expressed_near_native_level']
    fusion = record['facts']['fusion_functional']
    expression_answer = 'not_applicable' if record['facts']['purified_proteins']['answer'] == 'yes' else expression['answer']   # purified proteins have no expression level
    status, reason = _shared_rule([expression_answer, fusion['answer']])
    if status == 'conflicting':
        deciding = [item for answer, item in ((expression_answer, expression), (fusion['answer'], fusion)) if answer == 'no']
    else:
        deciding = [item for answer, item in ((expression_answer, expression), (fusion['answer'], fusion)) if answer == 'yes']
    return _result(status, reason, _refs(*deciding))


def _objects_counted(record, native):
    quantified = record['facts']['quantified_over_many_cells']
    if quantified['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', quantified['source_refs'])
    count = _value(record, 'objects_counted')
    if count is None:
        return _one_fact(record, 'quantified_over_many_cells')
    native.update({'objects_counted': count, 'objects_counted_refs': _refs(record['quantities']['objects_counted'])})
    return _result('unknown', 'objects_counted_recorded_for_the_sheet', [])


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


EVALUATORS = {'colocalization_observed': _colocalization_observed, 'colocalization_readout': _colocalization_readout, 'specificity_control': _specificity_control, 'directness': _directness, 'expression_validity': _expression_validity, 'objects_counted': _objects_counted, 'replicates': _replicates}


def grade_colocalization(record):
    """Grade one co-localization experiment record. Returns the criterion answers and native values."""
    detected = record['facts']['colocalization_observed']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'imaging_mode': record['imaging_mode'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'interaction': INTERACTION.get(detected['answer']), 'interaction_refs': list(detected['source_refs']) if detected['answer'] in INTERACTION else [], 'colocalization_fraction': None, 'colocalization_pearson': None, 'colocalization_enrichment': None, 'readout_refs': [], 'objects_counted': None, 'objects_counted_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, COLOCALIZATION_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'colocalization', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
