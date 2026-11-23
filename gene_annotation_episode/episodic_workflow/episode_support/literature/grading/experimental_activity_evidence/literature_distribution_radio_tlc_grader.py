"""Distribution_radio_tlc grader: judges ONE radiolabelled product-distribution experiment (TLC, radio-HPLC or gel with counting or phosphor imaging) by its
own standards. DRAFT 2026-11-22 (class product_distribution), built from the shape of literature_spectro_direct_grader.py.

Hand-built and private to distribution_radio_tlc. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_distribution_radio_tlc_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_distribution_radio_tlc_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(lane_recovery_fraction, background_over_smallest_species, replicate_count, each with its refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact claimed_product_detected ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying
whether the product named as the partner was found among the labelled products. It is recorded in native as 'product' with its refs and its support
(class decision: 'interaction_detected' reads "product detected"). It is only used by the converter when no share or ratio is stated.

Native values retained: every record quantity as given, the choices (spread_kind, label, readout) and the preparations, and lane_recovery_fraction,
background_over_smallest_species, replicate_count, replicate_independent, product, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_distribution_radio_tlc_criteria import (
    DISTRIBUTION_RADIO_TLC_CRITERIA, FRACTION_PER_UNIT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_distribution_radio_tlc_grade'
CRITERIA = tuple(criterion['id'] for criterion in DISTRIBUTION_RADIO_TLC_CRITERIA)
PRODUCT = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact claimed_product_detected


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
        raise ValueError(f'a {status} result needs support refs: {reason}')
    return {'status': status, 'reason': reason, 'support_refs': refs if status in ('supported', 'conflicting') else []}


def _one_fact(record, name):
    item = record['facts'][name]
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, item['source_refs'])


def _species_assigned_with_standards(record, native):
    return _one_fact(record, 'cold_standards_co_run')


def _label_retained_by_all_products(record, native):
    return _one_fact(record, 'label_retained_by_all_products')


def _shares_of_one_lane_total(record, native):
    return _one_fact(record, 'fractions_share_one_denominator')


def _lane_recovery_stated(record, native):
    value = _value(record, 'lane_recovery')
    if value is None:
        return _result('unknown', 'lane_recovery_not_stated', [])
    operand = record['quantities']['lane_recovery']
    native.update({'lane_recovery_fraction': value * FRACTION_PER_UNIT[operand['unit']], 'lane_recovery_refs': _refs(operand)})
    return _result('unknown', 'lane_recovery_recorded_for_the_sheet', [])


def _equal_label_per_molecule(record, native):
    return _one_fact(record, 'equal_label_per_molecule')


def _detection_efficiency_matched(record, native):
    return _one_fact(record, 'detection_efficiency_matched')


def _spots_resolved(record, native):
    return _one_fact(record, 'spots_resolved')


def _background_beside_smallest_band(record, native):
    background, smallest = record['quantities']['counts_background'], record['quantities']['smallest_species_counts']
    subtracted = record['facts']['background_subtracted']
    if background['status'] == 'point' and smallest['status'] == 'point' and background['unit'] == smallest['unit']:
        native.update({'background_over_smallest_species': background['value'] / smallest['value'], 'background_refs': _refs(background, smallest)})
        return _result('unknown', 'background_recorded_for_the_sheet', [])
    if subtracted['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', _refs(subtracted))
    if subtracted['answer'] == 'yes':
        return _result('supported', 'background_subtracted_stated', _refs(subtracted))
    return _result('unknown', 'background_not_stated', [])


def _within_linear_range_of_imager(record, native):
    return _one_fact(record, 'within_linear_range_of_imager')


def _substrate_blank_lane(record, native):
    no_enzyme, zero_time = record['facts']['no_enzyme_lane_run'], record['facts']['zero_time_lane_run']
    if no_enzyme['answer'] == 'yes':
        return _result('supported', 'no_enzyme_lane_stated', _refs(no_enzyme))
    if no_enzyme['answer'] == 'no' and zero_time['answer'] != 'yes':
        return _result('conflicting', 'fact_answered_no', _refs(no_enzyme))
    if zero_time['answer'] == 'yes':
        return _result('unknown', 'only_zero_time_lane_stated', [])
    return _result('unknown', 'fact_unknown', [])


def _inactive_enzyme_lane(record, native):
    return _one_fact(record, 'inactive_enzyme_lane_run')


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
    return _one_fact(record, 'native_substrate')


def _purified_enzyme(record, native):
    return _one_fact(record, 'purified_enzyme')


EVALUATORS = {'species_assigned_with_standards': _species_assigned_with_standards, 'label_retained_by_all_products': _label_retained_by_all_products,
              'shares_of_one_lane_total': _shares_of_one_lane_total, 'lane_recovery_stated': _lane_recovery_stated, 'equal_label_per_molecule': _equal_label_per_molecule,
              'detection_efficiency_matched': _detection_efficiency_matched, 'spots_resolved': _spots_resolved, 'background_beside_smallest_band': _background_beside_smallest_band,
              'within_linear_range_of_imager': _within_linear_range_of_imager, 'substrate_blank_lane': _substrate_blank_lane, 'inactive_enzyme_lane': _inactive_enzyme_lane,
              'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_distribution_radio_tlc(record):
    """Grade one radiolabelled product-distribution record. Returns the criterion answers and native values."""
    detected = record['facts']['claimed_product_detected']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'label': record['label'], 'readout': record['readout'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'product': PRODUCT.get(detected['answer']), 'product_refs': list(detected['source_refs']) if detected['answer'] in PRODUCT else [], 'product_support': detected['support'],
              'lane_recovery_fraction': None, 'lane_recovery_refs': [], 'background_over_smallest_species': None, 'background_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, DISTRIBUTION_RADIO_TLC_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'distribution_radio_tlc', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
