"""Distribution_chiral grader: judges ONE chiral product-distribution experiment by its own standards (DRAFT 2026-11-22, owner to confirm).

Hand-built and private to distribution_chiral. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_distribution_chiral_record.py), after the merge of its leaf records.
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_distribution_chiral_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(peak_resolution, the minor isomer's share and the detection limit, replicate_count, each with its refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet', and no refs; the converter judges it. The only numbers here are the unit conversions and identities declared in the criteria file.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact product_detected ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying whether the
stereo-isomeric product was formed. It is recorded in native as 'product' with its refs and its support (class decision: 'interaction_detected' reads "product detected").
It is only used by the converter when no excess or ratio is stated.

Native values retained: every record quantity as given, the choices (spread_kind, configuration, technique) and the preparations, and peak_resolution, minor_share,
detection_limit, replicate_count, replicate_independent, product, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_distribution_chiral_criteria import (
    DISTRIBUTION_CHIRAL_CRITERIA, ISOMERS_IN_A_PAIR, PERCENT_PER_FRACTION)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_distribution_chiral_grade'
CRITERIA = tuple(criterion['id'] for criterion in DISTRIBUTION_CHIRAL_CRITERIA)
PRODUCT = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact product_detected


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _fraction(record, name):
    """A share (excess or detection limit) as a fraction, or None when not stated."""
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


def _one_fact(record, name):
    item = record['facts'][name]
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, item['source_refs'])


def _minor_share(record):
    """(the minor isomer's share of the total as a fraction, the operand it comes from) of the first stated result (excess, then enantiomer ratio, then diastereomer ratio), or (None, None)."""
    excess = _fraction(record, 'enantiomeric_excess')
    if excess is not None:
        return (1 - excess) / ISOMERS_IN_A_PAIR, record['quantities']['enantiomeric_excess']
    for name in ('enantiomer_ratio', 'diastereomer_ratio'):
        ratio = _value(record, name)
        if ratio is not None:
            return 1 / (1 + ratio), record['quantities'][name]
    return None, None


def _racemic_standard_run(record, native):
    return _one_fact(record, 'racemic_standard_run')


def _configuration_assigned_by_standard(record, native):
    return _one_fact(record, 'configuration_assigned_by_standard')


def _isomer_response_factors(record, native):
    if _value(record, 'diastereomer_ratio') is not None:
        return _one_fact(record, 'response_factors_calibrated')
    if _value(record, 'enantiomeric_excess') is not None or _value(record, 'enantiomer_ratio') is not None:
        return _result('not_applicable', 'isomers_are_enantiomers', [])
    return _result('unknown', 'isomer_kind_not_stated', [])


def _isomer_pair_one_measurement(record, native):
    stated = [record['quantities'][name] for name in ('enantiomeric_excess', 'enantiomer_ratio', 'diastereomer_ratio') if record['quantities'][name]['status'] == 'point']
    if not stated:
        return _result('unknown', 'no_isomer_measure_stated', [])
    return _result('supported', 'isomer_pair_stated_as_one_measurement', _refs(*stated))


def _no_enzyme_control(record, native):
    return _one_fact(record, 'no_enzyme_control_done')


def _product_configurational_stability(record, native):
    return _one_fact(record, 'product_configurationally_stable')


def _inactive_enzyme_control(record, native):
    return _one_fact(record, 'inactive_enzyme_control_done')


def _peak_resolution(record, native):
    resolved = record['facts']['isomer_peaks_baseline_resolved']
    resolution = _value(record, 'peak_resolution')
    refs = _refs(record['quantities']['peak_resolution'], resolved)
    if resolved['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if resolution is not None:
        native.update({'peak_resolution': resolution, 'peak_resolution_refs': refs})
        return _result('unknown', 'peak_resolution_recorded_for_the_sheet', [])
    if resolved['answer'] == 'yes':
        return _result('supported', 'isomer_peaks_baseline_resolved_stated', refs)
    return _result('unknown', 'peak_resolution_not_stated', [])


def _minor_isomer_detection(record, native):
    limit = _fraction(record, 'minor_isomer_detection_limit')
    minor, source = _minor_share(record)
    if limit is None or minor is None:
        return _result('unknown', 'detection_limit_or_result_missing', [])
    native.update({'minor_share': minor, 'detection_limit': limit, 'detection_refs': _refs(record['quantities']['minor_isomer_detection_limit'], source)})
    return _result('unknown', 'detection_limit_recorded_for_the_sheet', [])


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


def _native_substrate(record, native):
    return _one_fact(record, 'native_substrate')


def _purified_enzyme(record, native):
    return _one_fact(record, 'purified_enzyme')


EVALUATORS = {'racemic_standard_run': _racemic_standard_run, 'configuration_assigned_by_standard': _configuration_assigned_by_standard, 'isomer_response_factors': _isomer_response_factors,
              'isomer_pair_one_measurement': _isomer_pair_one_measurement, 'no_enzyme_control': _no_enzyme_control, 'product_configurational_stability': _product_configurational_stability,
              'inactive_enzyme_control': _inactive_enzyme_control, 'peak_resolution': _peak_resolution, 'minor_isomer_detection': _minor_isomer_detection, 'replicates': _replicates,
              'native_substrate': _native_substrate, 'purified_enzyme': _purified_enzyme}


def grade_distribution_chiral(record):
    """Grade one chiral product-distribution experiment record. Returns the criterion answers and native values."""
    detected = record['facts']['product_detected']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'configuration': record['configuration'], 'technique': record['technique'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'product': PRODUCT.get(detected['answer']), 'product_refs': list(detected['source_refs']) if detected['answer'] in PRODUCT else [], 'product_support': detected['support'],
              'peak_resolution': None, 'peak_resolution_refs': [], 'minor_share': None, 'detection_limit': None, 'detection_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, DISTRIBUTION_CHIRAL_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'distribution_chiral', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
