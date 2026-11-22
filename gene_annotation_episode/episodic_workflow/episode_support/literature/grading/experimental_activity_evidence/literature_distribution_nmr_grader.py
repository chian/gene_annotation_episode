"""Distribution_nmr grader: judges ONE quantitative NMR measurement of a product mixture by its own standards.

Hand-built and private to distribution_nmr. Deterministic; no model call, no store access.
Input: the record of one measurement (forms/.../literature_distribution_nmr_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_distribution_nmr_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(relaxation_delay_s and longest_t1_s, signal_to_noise_minor, replicate_count, each with its refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact claimed_product_detected ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying
whether the spectrum showed the product the experiment tests for. It is kept in native as 'interaction' with its refs ('interaction_refs') and its quote
support ('interaction_support') and read by no criterion; the converter hands it to the sheet only when no effect is stated (class decision: for the
product_distribution class 'interaction_detected' reads "product detected").

Native values retained: every record quantity as given, spread_kind, nucleus and the preparations, and relaxation_delay_s, longest_t1_s, relaxation_refs,
signal_to_noise_minor, signal_to_noise_refs, replicate_count, replicate_independent, replicate_refs, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_distribution_nmr_criteria import DISTRIBUTION_NMR_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_distribution_nmr_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in DISTRIBUTION_NMR_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the stated yes/no result of the fact claimed_product_detected
SECONDS_PER_UNIT = {'s': 1.0, 'ms': 1.0e-3}   # FIXED_BY_DEFINITION: a millisecond is a thousandth of a second.


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _seconds(record, name):
    value = _value(record, name)
    return None if value is None else value * SECONDS_PER_UNIT[record['quantities'][name]['unit']]


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


def _shares_from_resolved_signals(record, native):
    return _one_fact(record, 'integrals_from_resolved_signals')


def _species_assigned_with_standards(record, native):
    return _one_fact(record, 'species_assigned_with_standards')


def _relaxation_delay(record, native):
    adequate = record['facts']['relaxation_delay_adequate']
    delay = _seconds(record, 'relaxation_delay')
    if adequate['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', adequate['source_refs'])
    if adequate['answer'] == 'yes':
        return _result('supported', 'relaxation_delay_adequate_stated', adequate['source_refs'])
    if delay is None:
        return _result('unknown', 'relaxation_not_stated', [])
    native.update({'relaxation_delay_s': delay, 'longest_t1_s': _seconds(record, 'longest_t1'),
                   'relaxation_refs': _refs(record['quantities']['relaxation_delay'], record['quantities']['longest_t1'])})
    return _result('unknown', 'relaxation_recorded_for_the_sheet', [])


def _denominator_and_coverage(record, native):
    names = ('fractions_share_one_denominator', 'all_products_identified')
    status, reason = _shared_rule([record['facts'][n]['answer'] for n in names])
    return _result(status, reason, _refs(*(record['facts'][n] for n in names)))


def _no_enzyme_spectrum(record, native):
    return _one_fact(record, 'no_enzyme_control_done')


def _inactive_enzyme_spectrum(record, native):
    return _one_fact(record, 'inactive_enzyme_control_done')


def _minor_signal_to_noise(record, native):
    value = _value(record, 'signal_to_noise_minor')
    if value is None:
        return _result('unknown', 'signal_to_noise_not_stated', [])
    native.update({'signal_to_noise_minor': value, 'signal_to_noise_refs': _refs(record['quantities']['signal_to_noise_minor'])})
    return _result('unknown', 'signal_to_noise_recorded_for_the_sheet', [])


def _stable_composition(record, native):
    stable, both = record['facts']['distribution_stable_over_time'], record['facts']['approached_from_both_sides']
    if stable['answer'] == 'no':
        return _result('conflicting', 'composition_still_changing', stable['source_refs'])
    yes = [item for item in (stable, both) if item['answer'] == 'yes']
    if yes:
        return _result('supported', 'equilibrium_evidence_stated', _refs(*yes))
    if stable['answer'] == 'not_applicable' and both['answer'] == 'not_applicable':
        return _result('not_applicable', 'fact_not_applicable', [])
    return _result('unknown', 'equilibrium_evidence_not_stated', [])


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


EVALUATORS = {'shares_from_resolved_signals': _shares_from_resolved_signals, 'species_assigned_with_standards': _species_assigned_with_standards,
              'relaxation_delay': _relaxation_delay, 'denominator_and_coverage': _denominator_and_coverage, 'no_enzyme_spectrum': _no_enzyme_spectrum,
              'inactive_enzyme_spectrum': _inactive_enzyme_spectrum, 'minor_signal_to_noise': _minor_signal_to_noise, 'stable_composition': _stable_composition,
              'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_distribution_nmr(record):
    """Grade one quantitative NMR product-mixture record. Returns the criterion answers and native values."""
    stated = record['facts']['claimed_product_detected']
    known = stated['answer'] in INTERACTION
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'nucleus': record['nucleus'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'interaction': INTERACTION.get(stated['answer']), 'interaction_refs': list(stated['source_refs']) if known else [], 'interaction_support': stated['support'] if known else None,
              'relaxation_delay_s': None, 'longest_t1_s': None, 'relaxation_refs': [], 'signal_to_noise_minor': None, 'signal_to_noise_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, DISTRIBUTION_NMR_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'distribution_nmr', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
