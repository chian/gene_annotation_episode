"""Distribution_lcms grader: judges ONE LC-MS or LC-MS/MS product-profile experiment by its own standards. DRAFT 2026-11-22, owner to confirm.

Hand-built and private to distribution_lcms. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_distribution_lcms_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_distribution_lcms_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(product_over_loq with loq_refs, replicate_count with replicate_independent and replicate_refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. Two criteria of two alternative ways to one end (calibration_per_species, matrix_effect_addressed) are supported by either
fact stated yes; sample_handling (two independent safeguards) fails on any fact stated no, else is supported by any fact stated yes.

A 'supported' or 'conflicting' result always carries support refs (the quoted spans of the stated fields it rests on); ``_result`` refuses to build one without them.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact claimed_product_detected ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying whether the
product the experiment is about was found among the products. It is recorded in native as 'product' with its refs and its support (class decision of 2026-11-22:
'interaction_detected' reads "product detected"). It is only used by the converter when no effect is stated. A product share that the passage states as 0 is also
kept as given in native['quantities']['product_fraction'] (value 0): the converter reads it as "product not detected".

Native values retained: every record quantity as given, the choices (spread_kind, fraction_basis, ionization_mode), the preparations, and product_over_loq,
replicate_count, replicate_independent, product, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_distribution_lcms_criteria import DISTRIBUTION_LCMS_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_distribution_lcms_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in DISTRIBUTION_LCMS_CRITERIA)
PRODUCT = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact claimed_product_detected
RANGE_REASON = {'supported': 'signals_within_calibration_range_stated', 'unknown': 'calibration_range_not_stated', 'not_applicable': 'fact_not_applicable'}


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _nm(record, name):
    value = _value(record, name)
    return None if value is None else value * _SCALES[record['quantities'][name]['unit']]


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


def _answered(items, answer):
    return _refs(*[item for item in items if item['answer'] == answer])


def _one_fact(record, name):
    item = record['facts'][name]
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, item['source_refs'])


def _all_facts(record, names):
    items = [record['facts'][name] for name in names]
    status, reason = _shared_rule([item['answer'] for item in items])
    return _result(status, reason, _answered(items, 'no' if status == 'conflicting' else 'yes'))


def _either_fact(record, names, supported_reason):
    items = [record['facts'][name] for name in names]
    if any(item['answer'] == 'yes' for item in items):
        return _result('supported', supported_reason, _answered(items, 'yes'))
    status, reason = _shared_rule([item['answer'] for item in items])
    return _result(status, reason, _answered(items, 'no'))


def _independent_facts(record, names):
    items = [record['facts'][name] for name in names]
    answers = [item['answer'] for item in items]
    if 'no' in answers:
        return _result('conflicting', 'fact_answered_no', _answered(items, 'no'))
    if 'yes' in answers:
        return _result('supported', 'facts_answered_yes', _answered(items, 'yes'))
    status, reason = _shared_rule(answers)
    return _result(status, reason, [])


def _species_assigned_with_standards(record, native):
    return _one_fact(record, 'authentic_standard_for_each_species')


def _calibration_per_species(record, native):
    return _either_fact(record, ('calibrated_per_species', 'isotope_labelled_internal_standard'), 'response_calibration_stated')


def _shared_denominator_and_closure(record, native):
    return _all_facts(record, ('fractions_share_one_denominator', 'all_products_identified'))


def _matrix_effect_addressed(record, native):
    return _either_fact(record, ('ion_suppression_checked', 'matrix_matched_calibration'), 'matrix_effect_addressed_stated')


def _sample_handling(record, native):
    return _independent_facts(record, ('enzyme_removed_or_quenched_before_analysis', 'products_stable_under_assay_and_workup'))


def _calibration_range_covers_signals(record, native):
    stated = record['facts']['signals_within_calibration_range']
    concentration, limit = _nm(record, 'product_concentration'), _nm(record, 'limit_of_quantification')
    if stated['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', stated['source_refs'])
    if concentration is not None and limit is not None:
        native['product_over_loq'] = concentration / limit
        native['loq_refs'] = _refs(record['quantities']['product_concentration'], record['quantities']['limit_of_quantification'])
        return _result('unknown', 'concentration_over_limit_recorded_for_the_sheet', [])
    status, _ = _shared_rule([stated['answer']])
    return _result(status, RANGE_REASON[status], stated['source_refs'])


def _no_enzyme_reaction(record, native):
    return _one_fact(record, 'no_enzyme_control_done')


def _inactive_enzyme_reaction(record, native):
    return _one_fact(record, 'inactive_enzyme_control_done')


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


EVALUATORS = {'species_assigned_with_standards': _species_assigned_with_standards, 'calibration_per_species': _calibration_per_species,
              'shared_denominator_and_closure': _shared_denominator_and_closure, 'matrix_effect_addressed': _matrix_effect_addressed, 'sample_handling': _sample_handling,
              'calibration_range_covers_signals': _calibration_range_covers_signals, 'no_enzyme_reaction': _no_enzyme_reaction,
              'inactive_enzyme_reaction': _inactive_enzyme_reaction, 'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_distribution_lcms(record):
    """Grade one LC-MS product-profile record. Returns the criterion answers and native values."""
    detected = record['facts']['claimed_product_detected']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'fraction_basis': record['fraction_basis'], 'ionization_mode': record['ionization_mode'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'product': PRODUCT.get(detected['answer']), 'product_refs': list(detected['source_refs']) if detected['answer'] in PRODUCT else [], 'product_support': detected['support'],
              'product_over_loq': None, 'loq_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, DISTRIBUTION_LCMS_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'distribution_lcms', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
