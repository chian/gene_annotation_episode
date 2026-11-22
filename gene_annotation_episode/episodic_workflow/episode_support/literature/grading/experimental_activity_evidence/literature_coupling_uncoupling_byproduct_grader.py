"""Coupling_uncoupling_byproduct grader: judges ONE by-product (uncoupling) assay of a coupled reaction by its own standards.
DRAFT 2026-11-22 (class reaction_coupling), copied from the shape of literature_spectro_direct_grader.py.

Hand-built and private to coupling_uncoupling_byproduct. Deterministic; no model call, no store access.
Input: the record of one assay (forms/.../literature_coupling_uncoupling_byproduct_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_coupling_uncoupling_byproduct_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(blank_percent, recovery_fraction, uncoupled_share, productive_share, replicate_count, each with its refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact coupled_product_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw coupled product formation above its own control. It is recorded in native as 'coupled' with its refs and its support
(class decision of the reaction_coupling draft: 'interaction_detected' reads "coupled product formation detected"). It is only used by the converter
when no effect can be filled.

Native values retained: every record quantity as given, the preparations, the plain choices, and blank_percent, recovery_fraction, uncoupled_share (with
uncoupled_share_source, uncoupled_share_refs and uncoupled_share_supports), routes_accounted (the answer, its refs and support: the productive share by
difference is derived on the sheet side only on yes), replicate_count, replicate_independent, coupled, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_coupling_uncoupling_byproduct_criteria import (
    COUPLING_UNCOUPLING_BYPRODUCT_CRITERIA, PERCENT_PER_FRACTION)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_coupling_uncoupling_byproduct_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in COUPLING_UNCOUPLING_BYPRODUCT_CRITERIA)
CHOICES = ('spread_kind', 'byproduct_species', 'detection_reagent')   # the plain choice fields of the record, kept in native (recorded only; no criterion rests on one)
COUPLED = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact coupled_product_detected_above_control


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _fraction(record, name):
    """A stated share as a fraction (a percent is turned into a fraction by the fixed factor), or None."""
    value = _value(record, name)
    if value is None:
        return None
    return value / PERCENT_PER_FRACTION if record['quantities'][name]['unit'] == 'percent' else value


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
        raise ValueError(f'a {status} result needs support refs: {reason}')
    return {'status': status, 'reason': reason, 'support_refs': refs if status in ('supported', 'conflicting') else []}


def _facts(record, *names):
    items = [record['facts'][n] for n in names]
    status, reason = _shared_rule([item['answer'] for item in items])
    return _result(status, reason, _refs(*items))


def _no_enzyme_blank(record, native):
    return _facts(record, 'no_enzyme_control')


def _blank_signal_share(record, native):
    value = _value(record, 'blank_percent_of_signal')
    if value is None:
        return _result('unknown', 'blank_share_not_stated', [])
    native.update({'blank_percent': value, 'blank_refs': _refs(record['quantities']['blank_percent_of_signal'])})
    return _result('unknown', 'blank_share_recorded_for_the_sheet', [])


def _inactive_enzyme_control(record, native):
    return _facts(record, 'inactive_enzyme_control')


def _substrate_dependent_turnover(record, native):
    return _facts(record, 'no_substrate_control')


def _byproduct_identity_control(record, native):
    names = ('catalase_control', 'sod_control')
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'byproduct_identity_control_stated', refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _reductant_interference_excluded(record, native):
    return _facts(record, 'reductant_interference_excluded')


def _byproduct_not_consumed(record, native):
    return _facts(record, 'byproduct_not_consumed')


def _standard_series(record, native):
    return _facts(record, 'standard_series')


def _standard_recovery(record, native):
    value = _fraction(record, 'standard_recovery')
    if value is None:
        return _result('unknown', 'recovery_not_stated', [])
    native.update({'recovery_fraction': value, 'recovery_refs': _refs(record['quantities']['standard_recovery'])})
    return _result('unknown', 'recovery_recorded_for_the_sheet', [])


def _uncoupled_share(record, native):
    quantities = record['quantities']
    stated = _fraction(record, 'uncoupled_fraction')
    ratio, coefficient = _value(record, 'byproduct_per_cofactor'), _value(record, 'byproduct_coefficient')
    if stated is not None:
        used, share, source = [quantities['uncoupled_fraction']], stated, 'uncoupled_fraction'
    elif ratio is not None and coefficient is not None:
        used, share, source = [quantities['byproduct_per_cofactor'], quantities['byproduct_coefficient']], ratio / coefficient, 'byproduct_per_cofactor_over_coefficient'
    elif ratio is not None:
        return _result('unknown', 'byproduct_coefficient_not_stated', [])
    else:
        return _result('unknown', 'uncoupled_share_not_stated', [])
    native.update({'uncoupled_share': share, 'uncoupled_share_source': source, 'uncoupled_share_refs': _refs(*used), 'uncoupled_share_supports': [item['support'] for item in used]})
    return _result('unknown', 'uncoupled_share_recorded_for_the_sheet', [])


def _productive_share_bound(record, native):
    value = _fraction(record, 'productive_fraction')
    if value is None:
        return _result('unknown', 'productive_share_not_stated', [])
    native.update({'productive_share': value, 'productive_share_refs': _refs(record['quantities']['productive_fraction'])})
    return _result('unknown', 'productive_share_recorded_for_the_sheet', [])


def _uncoupling_routes_accounted(record, native):
    return _facts(record, 'uncoupling_routes_accounted')


def _product_identity(record, native):
    return _facts(record, 'product_measured_too')


def _same_mixture_and_window(record, native):
    return _facts(record, 'same_mixture', 'same_window')


def _same_preparation(record, native):
    return _facts(record, 'same_preparation')


def _replicates(record, native):
    count = _value(record, 'replicate_count')
    independent = record['facts']['independent_replicates']
    refs = _refs(record['quantities']['replicate_count'], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', 'replicates_not_independent', refs)
    if count is None:
        return _result('unknown', 'replicate_count_or_independence_unknown', [])
    native.update({'replicate_count': count, 'replicate_independent': independent['answer'], 'replicate_refs': refs})
    return _result('unknown', 'replicate_count_recorded_for_the_sheet', [])


def _native_reaction(record, native):
    return _facts(record, 'native_substrate')


def _purified_enzyme(record, native):
    return _facts(record, 'purified_enzyme')


EVALUATORS = {'no_enzyme_blank': _no_enzyme_blank, 'blank_signal_share': _blank_signal_share, 'inactive_enzyme_control': _inactive_enzyme_control,
              'substrate_dependent_turnover': _substrate_dependent_turnover, 'byproduct_identity_control': _byproduct_identity_control,
              'reductant_interference_excluded': _reductant_interference_excluded, 'byproduct_not_consumed': _byproduct_not_consumed,
              'standard_series': _standard_series, 'standard_recovery': _standard_recovery, 'uncoupled_share': _uncoupled_share,
              'productive_share_bound': _productive_share_bound, 'uncoupling_routes_accounted': _uncoupling_routes_accounted, 'product_identity': _product_identity,
              'same_mixture_and_window': _same_mixture_and_window, 'same_preparation': _same_preparation, 'replicates': _replicates,
              'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_coupling_uncoupling_byproduct(record):
    """Grade one by-product (uncoupling) assay record. Returns the criterion answers and native values."""
    coupled = record['facts']['coupled_product_detected_above_control']
    routes = record['facts']['uncoupling_routes_accounted']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              **{name: record[name] for name in CHOICES},
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'coupled': COUPLED.get(coupled['answer']), 'coupled_refs': list(coupled['source_refs']) if coupled['answer'] in COUPLED else [], 'coupled_support': coupled['support'],
              'routes_accounted': {'answer': routes['answer'], 'refs': list(routes['source_refs']), 'support': routes['support']},
              'blank_percent': None, 'blank_refs': [], 'recovery_fraction': None, 'recovery_refs': [], 'uncoupled_share': None, 'uncoupled_share_source': None,
              'uncoupled_share_refs': [], 'uncoupled_share_supports': [], 'productive_share': None, 'productive_share_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, COUPLING_UNCOUPLING_BYPRODUCT_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'coupling_uncoupling_byproduct', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
