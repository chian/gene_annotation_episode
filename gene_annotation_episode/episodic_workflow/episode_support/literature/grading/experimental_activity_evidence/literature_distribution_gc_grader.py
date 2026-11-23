"""Distribution_gc grader: judges ONE gas-chromatography product distribution by its own standards.

Hand-built and private to distribution_gc. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_distribution_gc_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_distribution_gc_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(retention_index_difference, identified_fraction, share_over_limit, recovery, replicate_count) or records a state (uncorrected_detector) and returns
'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs; the converter judges it. A share given in percent is turned into a fraction
by the exact factor PERCENT_PER_FRACTION of the criteria file (FIXED_BY_DEFINITION).

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact claimed_product_detected ('yes' is 'detected', 'no' is 'not_detected'): the paper itself
saying whether the product was found among the products. It is recorded in native as 'product' with its refs and its support (class decision of
2026-11-22: 'interaction_detected' reads "product detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the preparations, spread_kind, and retention_index_difference, uncorrected_detector,
identified_fraction, share_over_limit, recovery, replicate_count, replicate_independent, product, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_distribution_gc_criteria import (
    DISTRIBUTION_GC_CRITERIA, PERCENT_PER_FRACTION)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_distribution_gc_grade'
CRITERIA = tuple(criterion['id'] for criterion in DISTRIBUTION_GC_CRITERIA)
PRODUCT = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact claimed_product_detected


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _fraction(record, name):
    """A share stated as a fraction or a percent, as a fraction; None when not stated."""
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


def _species_identification(record, native):
    standard, library = record['facts']['identified_by_standard'], record['facts']['identified_by_library_match']
    observed, reference = record['quantities']['retention_index_observed'], record['quantities']['retention_index_reference']
    if standard['answer'] == 'yes':
        return _result('supported', 'identified_by_standard', _refs(standard))
    if library['answer'] == 'yes':
        if observed['status'] != 'point' or reference['status'] != 'point':
            return _result('unknown', 'library_match_without_retention_index', [])
        native.update({'retention_index_difference': abs(observed['value'] - reference['value']), 'identification_refs': _refs(library, observed, reference)})
        return _result('unknown', 'library_identification_recorded_for_the_sheet', [])
    return _result('unknown', 'identification_not_stated', [])


def _response_factors_applied(record, native):
    calibrated = record['facts']['response_factors_calibrated']
    detectors = {'flame_ionization': record['facts']['quantified_by_flame_ionization'], 'mass_spectrometer': record['facts']['quantified_by_mass_spectrometry']}
    if calibrated['answer'] == 'yes':
        return _result('supported', 'response_factors_calibrated', _refs(calibrated))
    if calibrated['answer'] == 'no':
        stated = [name for name, item in detectors.items() if item['answer'] == 'yes']
        if len(stated) != 1:
            return _result('unknown', 'uncorrected_detector_not_stated_or_ambiguous', [])
        native.update({'uncorrected_detector': stated[0], 'uncorrected_refs': _refs(calibrated, detectors[stated[0]])})
        return _result('unknown', 'uncorrected_areas_recorded_for_the_sheet', [])
    return _result('unknown', 'response_factors_not_stated', [])


def _denominator_coverage(record, native):
    item, coverage = record['facts']['all_peaks_in_denominator'], record['quantities']['identified_area_fraction']
    refs = _refs(item, coverage)
    if item['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if coverage['status'] == 'point':
        native.update({'identified_fraction': _fraction(record, 'identified_area_fraction'), 'identified_refs': refs})
        return _result('unknown', 'coverage_recorded_for_the_sheet', [])
    if item['answer'] == 'yes':
        return _result('supported', 'all_peaks_in_denominator_stated', refs)
    return _result('unknown', 'denominator_not_stated', [])


def _detection_limit_ratio(record, native):
    limit, share = _fraction(record, 'minimum_integrated_share'), _fraction(record, 'product_fraction')
    if limit is None or share is None:
        return _result('unknown', 'limit_or_share_not_stated', [])
    native.update({'share_over_limit': share / limit, 'limit_refs': _refs(record['quantities']['minimum_integrated_share'], record['quantities']['product_fraction'])})
    return _result('unknown', 'share_over_limit_recorded_for_the_sheet', [])


def _injector_stability(record, native):
    return _one_fact(record, 'injector_stability_checked')


def _extraction_recovery(record, native):
    recovery = _fraction(record, 'extraction_recovery')
    if recovery is None:
        return _result('unknown', 'recovery_not_stated', [])
    native.update({'recovery': recovery, 'recovery_refs': _refs(record['quantities']['extraction_recovery'])})
    return _result('unknown', 'recovery_recorded_for_the_sheet', [])


def _no_enzyme_control(record, native):
    return _one_fact(record, 'no_enzyme_control_done')


def _product_stability(record, native):
    return _one_fact(record, 'products_stable_under_assay_and_workup')


def _inactive_enzyme_control(record, native):
    return _one_fact(record, 'inactive_enzyme_control_done')


def _native_reaction(record, native):
    return _one_fact(record, 'native_substrate')


def _purified_enzyme(record, native):
    return _one_fact(record, 'purified_enzyme')


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


EVALUATORS = {'species_identification': _species_identification, 'response_factors_applied': _response_factors_applied, 'denominator_coverage': _denominator_coverage,
              'detection_limit_ratio': _detection_limit_ratio, 'injector_stability': _injector_stability, 'extraction_recovery': _extraction_recovery,
              'no_enzyme_control': _no_enzyme_control, 'product_stability': _product_stability, 'inactive_enzyme_control': _inactive_enzyme_control,
              'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme, 'replicates': _replicates}


def grade_distribution_gc(record):
    """Grade one gas-chromatography product distribution record. Returns the criterion answers and native values."""
    detected = record['facts']['claimed_product_detected']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'product': PRODUCT.get(detected['answer']), 'product_refs': list(detected['source_refs']) if detected['answer'] in PRODUCT else [], 'product_support': detected['support'],
              'retention_index_difference': None, 'identification_refs': [], 'uncorrected_detector': None, 'uncorrected_refs': [], 'identified_fraction': None, 'identified_refs': [],
              'share_over_limit': None, 'limit_refs': [], 'recovery': None, 'recovery_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, DISTRIBUTION_GC_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'distribution_gc', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
