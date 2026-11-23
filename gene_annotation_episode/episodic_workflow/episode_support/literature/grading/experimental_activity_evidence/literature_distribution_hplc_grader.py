"""Distribution_hplc grader: judges ONE HPLC product-distribution experiment (a reaction or an equilibrium mixture is separated by liquid chromatography
with a UV, diode-array, fluorescence, refractive-index, ELSD or CAD detector and the peak areas are turned into the share of one named product, a
product ratio or an equilibrium composition) by its own standards.

Hand-built and private to distribution_hplc. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_distribution_hplc_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_distribution_hplc_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(peak_resolution, total_recovery, the detection limit with the share it is compared with, replicate_count, each with its refs) and returns
'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs; the converter judges it. A percent is turned into a fraction by the fixed
factor 0.01 (FIXED_BY_DEFINITION), which is a unit spelling and no judgement.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. The criteria that accept either of two ways of showing the same thing (species_assigned_with_standards,
response_factors_calibrated, equilibrium_evidence) are supported as soon as one fact is yes.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact claimed_product_detected ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying
whether the product it is about was found among the products. It is recorded in native as 'product' with its refs and its support (class decision of
2026-11-22: 'interaction_detected' reads "product detected", 'interaction_not_detected' reads "product not detected"). It is only used by the converter
when no effect is stated.

Native values retained: every record quantity as given, the preparations, spread_kind, fraction_basis, detector, and total_recovery, closure_refs,
denominator_status, peak_resolution, resolution_refs, detection_limit, limit_share, limit_refs, replicate_count, replicate_independent, replicate_refs,
product, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_distribution_hplc_criteria import DISTRIBUTION_HPLC_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_distribution_hplc_grade'
CRITERIA = tuple(criterion['id'] for criterion in DISTRIBUTION_HPLC_CRITERIA)
PRODUCT = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact claimed_product_detected
FRACTION_FACTORS = {'fraction': 1.0, 'percent': 0.01}   # FIXED_BY_DEFINITION: a percent is a hundredth
SHARE_QUANTITIES = ('product_fraction', 'equilibrium_fraction')   # the shares the detection limit is compared with, in the class's order of preference
EQUILIBRIUM_QUANTITIES = ('equilibrium_fraction', 'equilibrium_ratio')


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _fraction(record, name):
    value = _value(record, name)
    return None if value is None else value * FRACTION_FACTORS[record['quantities'][name]['unit']]


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


def _species_assigned_with_standards(record, native):
    return _either_fact(record, ('authentic_standard_for_each_species', 'identity_confirmed_by_mass_or_nmr'), 'species_assignment_stated')


def _response_factors_calibrated(record, native):
    return _either_fact(record, ('response_factors_calibrated', 'calibration_curves_for_each_species'), 'response_calibration_stated')


def _shared_denominator_and_closure(record, native):
    facts = [record['facts'][n] for n in ('fractions_share_one_denominator', 'all_products_identified')]
    status, reason = _shared_rule([item['answer'] for item in facts])
    if status == 'conflicting':
        return _result('conflicting', reason, _refs(*facts))
    recovery = _fraction(record, 'total_recovery')
    if recovery is not None:
        native.update({'total_recovery': recovery, 'closure_refs': _refs(*facts, record['quantities']['total_recovery']), 'denominator_status': status})
        return _result('unknown', 'closure_recorded_for_the_sheet', [])
    return _result(status, reason, _refs(*facts))


def _peak_resolution_recorded(record, native):
    resolved = record['facts']['peaks_resolved']
    value = _value(record, 'peak_resolution')
    refs = _refs(record['quantities']['peak_resolution'], resolved)
    if resolved['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if value is not None:
        native.update({'peak_resolution': value, 'resolution_refs': refs})
        return _result('unknown', 'resolution_recorded_for_the_sheet', [])
    if resolved['answer'] == 'yes':
        return _result('supported', 'peaks_resolved_stated', refs)
    return _result('unknown', 'resolution_not_stated', [])


def _reaction_stopped_before_injection(record, native):
    return _one_fact(record, 'enzyme_removed_or_quenched_before_injection')


def _calibration_range_covers_signals(record, native):
    in_range = record['facts']['signals_within_calibration_range']
    limit = _fraction(record, 'detection_limit')
    if in_range['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', _refs(in_range))
    if limit is not None:
        share_name = next((name for name in SHARE_QUANTITIES if _value(record, name) is not None), None)
        if share_name is not None:
            native.update({'detection_limit': limit, 'limit_share': _fraction(record, share_name), 'limit_refs': _refs(record['quantities']['detection_limit'], record['quantities'][share_name])})
            return _result('unknown', 'detection_limit_recorded_for_the_sheet', [])
        if native['product'] == 'not_detected':
            native.update({'detection_limit': limit, 'limit_refs': _refs(record['quantities']['detection_limit'], record['facts']['claimed_product_detected'])})
            return _result('unknown', 'detection_limit_recorded_for_the_sheet', [])
    if in_range['answer'] == 'yes':
        return _result('supported', 'signals_within_range_stated', _refs(in_range))
    return _result('unknown', 'calibration_range_not_stated', [])


def _no_enzyme_injection(record, native):
    return _one_fact(record, 'no_enzyme_control_done')


def _products_stable_through_workup(record, native):
    return _one_fact(record, 'products_stable_under_assay_and_workup')


def _inactive_enzyme_injection(record, native):
    return _one_fact(record, 'inactive_enzyme_control_done')


def _equilibrium_evidence(record, native):
    names = ('distribution_stable_over_time', 'approached_from_both_sides')
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'equilibrium_evidence_stated', refs)
    if 'no' in answers:
        return _result('conflicting', 'fact_answered_no', refs)
    if any(_value(record, name) is not None for name in EQUILIBRIUM_QUANTITIES):
        return _result('unknown', 'equilibrium_evidence_not_stated', [])
    return _result('not_applicable', 'no_equilibrium_result_stated', [])


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


EVALUATORS = {'species_assigned_with_standards': _species_assigned_with_standards, 'response_factors_calibrated': _response_factors_calibrated,
              'shared_denominator_and_closure': _shared_denominator_and_closure, 'peak_resolution_recorded': _peak_resolution_recorded,
              'reaction_stopped_before_injection': _reaction_stopped_before_injection, 'calibration_range_covers_signals': _calibration_range_covers_signals,
              'no_enzyme_injection': _no_enzyme_injection, 'products_stable_through_workup': _products_stable_through_workup,
              'inactive_enzyme_injection': _inactive_enzyme_injection, 'equilibrium_evidence': _equilibrium_evidence, 'replicates': _replicates,
              'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_distribution_hplc(record):
    """Grade one HPLC product-distribution record. Returns the criterion answers and native values."""
    detected = record['facts']['claimed_product_detected']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'fraction_basis': record['fraction_basis'], 'detector': record['detector'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'product': PRODUCT.get(detected['answer']), 'product_refs': list(detected['source_refs']) if detected['answer'] in PRODUCT else [], 'product_support': detected['support'],
              'total_recovery': None, 'closure_refs': [], 'denominator_status': None, 'peak_resolution': None, 'resolution_refs': [], 'detection_limit': None, 'limit_share': None,
              'limit_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, DISTRIBUTION_HPLC_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'distribution_hplc', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
