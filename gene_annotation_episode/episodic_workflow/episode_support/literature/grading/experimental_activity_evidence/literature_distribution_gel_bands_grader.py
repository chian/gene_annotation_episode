"""Distribution_gel_bands grader: judges ONE electrophoretic product-distribution experiment by its own standards (DRAFT 2026-11-22, owner to correct).

Hand-built and private to distribution_gel_bands. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_distribution_gel_bands_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_distribution_gel_bands_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(share_over_detection_limit, recovery_fraction, conversion_fraction, replicate_count, each with its refs) and returns 'unknown' with a reason
ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact claimed_product_detected ('yes' is 'detected', 'no' is 'not_detected'): the paper itself
saying whether the named product was found among the products. It is recorded in native as 'product' with its refs and its support (class decision:
'interaction_detected' reads "product detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the preparations, spread_kind, labelling, and share_over_detection_limit, recovery_fraction,
conversion_fraction, replicate_count, replicate_independent, product, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_distribution_gel_bands_criteria import (
    DISTRIBUTION_GEL_BANDS_CRITERIA, FRACTION_PER_UNIT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_distribution_gel_bands_grade'
CRITERIA = tuple(criterion['id'] for criterion in DISTRIBUTION_GEL_BANDS_CRITERIA)
PRODUCT = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact claimed_product_detected


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _fraction(record, name):
    value = _value(record, name)
    return None if value is None else value * FRACTION_PER_UNIT[record['quantities'][name]['unit']]


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


def _either_fact(record, names, supported_reason):
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', supported_reason, refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _size_markers(record, native):
    return _one_fact(record, 'size_markers_run')


def _band_resolution(record, native):
    return _one_fact(record, 'bands_resolved')


def _equal_response(record, native):
    return _either_fact(record, ('end_labelled_so_equal_response', 'response_corrected_for_length'), 'equal_response_stated')


def _denominator_coverage(record, native):
    return _one_fact(record, 'all_bands_in_denominator')


def _linear_range(record, native):
    return _one_fact(record, 'within_linear_range')


def _minor_band_limit(record, native):
    share, limit = _fraction(record, 'product_fraction'), _fraction(record, 'minor_species_detection_limit')
    if share is None or limit is None:
        return _result('unknown', 'share_or_limit_missing', [])
    native.update({'share_over_detection_limit': share / limit, 'limit_refs': _refs(record['quantities']['product_fraction'], record['quantities']['minor_species_detection_limit'])})
    return _result('unknown', 'limit_recorded_for_the_sheet', [])


def _lane_signal_accounted(record, native):
    recovery = _fraction(record, 'total_recovery')
    if recovery is None:
        return _result('unknown', 'recovery_not_stated', [])
    native.update({'recovery_fraction': recovery, 'recovery_refs': _refs(record['quantities']['total_recovery'])})
    return _result('unknown', 'recovery_recorded_for_the_sheet', [])


def _reaction_quenched(record, native):
    return _one_fact(record, 'reaction_quenched_before_loading')


def _background_subtraction(record, native):
    return _one_fact(record, 'background_subtracted')


def _background_lane(record, native):
    return _either_fact(record, ('no_enzyme_lane', 'substrate_only_lane'), 'background_lane_stated')


def _inactive_enzyme_lane(record, native):
    return _one_fact(record, 'inactive_enzyme_lane')


def _single_hit_regime(record, native):
    primary = record['facts']['primary_products_only']
    conversion = _fraction(record, 'substrate_conversion')
    refs = _refs(record['quantities']['substrate_conversion'], primary)
    if primary['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if conversion is not None:
        native.update({'conversion_fraction': conversion, 'conversion_refs': refs})
        return _result('unknown', 'conversion_recorded_for_the_sheet', [])
    if primary['answer'] == 'yes':
        return _result('supported', 'primary_products_stated', refs)
    return _result('unknown', 'single_hit_not_stated', [])


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


EVALUATORS = {'size_markers': _size_markers, 'band_resolution': _band_resolution, 'equal_response': _equal_response, 'denominator_coverage': _denominator_coverage,
              'linear_range': _linear_range, 'minor_band_limit': _minor_band_limit, 'lane_signal_accounted': _lane_signal_accounted, 'reaction_quenched': _reaction_quenched,
              'background_subtraction': _background_subtraction, 'background_lane': _background_lane, 'inactive_enzyme_lane': _inactive_enzyme_lane,
              'single_hit_regime': _single_hit_regime, 'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_distribution_gel_bands(record):
    """Grade one electrophoretic product-distribution record. Returns the criterion answers and native values."""
    detected = record['facts']['claimed_product_detected']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'labelling': record['labelling'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'product': PRODUCT.get(detected['answer']), 'product_refs': list(detected['source_refs']) if detected['answer'] in PRODUCT else [], 'product_support': detected['support'],
              'share_over_detection_limit': None, 'limit_refs': [], 'recovery_fraction': None, 'recovery_refs': [], 'conversion_fraction': None, 'conversion_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, DISTRIBUTION_GEL_BANDS_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'distribution_gel_bands', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
