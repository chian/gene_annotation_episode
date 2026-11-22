"""Distribution_enzymatic_endpoint grader: judges ONE enzymatic end-point determination of a product mixture by its own standards.

Hand-built and private to distribution_enzymatic_endpoint. Deterministic; no model call, no store access.
Input: the record of one determination (forms/.../literature_distribution_enzymatic_endpoint_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_distribution_enzymatic_endpoint_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(total_recovery_percent, absorbance_max, cross_reactivity_percent, replicate_count, each with its refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact claimed_product_detected ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying
whether the enzymatic analysis found the product the experiment tests for. It is kept in native as 'interaction' with its refs ('interaction_refs') and its quote
support ('interaction_support') and read by no criterion; the converter hands it to the sheet only when no effect is stated (class decision: for the
product_distribution class 'interaction_detected' reads "product detected").

Native values retained: every record quantity as given, spread_kind, reporter_signal and the preparations, and total_recovery_percent, recovery_refs,
absorbance_max, absorbance_refs, cross_reactivity_percent, cross_reactivity_refs, replicate_count, replicate_independent, replicate_refs, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_distribution_enzymatic_endpoint_criteria import DISTRIBUTION_ENZYMATIC_ENDPOINT_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_distribution_enzymatic_endpoint_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in DISTRIBUTION_ENZYMATIC_ENDPOINT_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the stated yes/no result of the fact claimed_product_detected
PERCENT_PER_UNIT = {'fraction': 100.0, 'percent': 1.0}   # FIXED_BY_DEFINITION: a fraction is a hundred percent.


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _percent(record, name):
    value = _value(record, name)
    return None if value is None else value * PERCENT_PER_UNIT[record['quantities'][name]['unit']]


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


def _analysis_enzyme_specificity(record, native):
    return _one_fact(record, 'analysis_enzyme_specificity_shown')


def _standard_curve_per_species(record, native):
    return _one_fact(record, 'standard_curve_for_each_species')


def _denominator_and_coverage(record, native):
    names = ('fractions_share_one_denominator', 'all_species_assayed')
    status, reason = _shared_rule([record['facts'][n]['answer'] for n in names])
    return _result(status, reason, _refs(*(record['facts'][n] for n in names)))


def _closure(record, native):
    value = _percent(record, 'total_recovery')
    if value is None:
        return _result('unknown', 'recovery_not_stated', [])
    native.update({'total_recovery_percent': value, 'recovery_refs': _refs(record['quantities']['total_recovery'])})
    return _result('unknown', 'recovery_recorded_for_the_sheet', [])


def _analysis_run_to_completion(record, native):
    return _one_fact(record, 'analysis_run_to_completion')


def _signals_inside_standard_curve(record, native):
    return _one_fact(record, 'signals_inside_standard_curve')


def _reporter_absorbance_range(record, native):
    value = _value(record, 'reporter_absorbance_max')
    if value is None:
        return _result('unknown', 'absorbance_not_stated', [])
    native.update({'absorbance_max': value, 'absorbance_refs': _refs(record['quantities']['reporter_absorbance_max'])})
    return _result('unknown', 'absorbance_recorded_for_the_sheet', [])


def _cross_reactivity(record, native):
    value = _percent(record, 'analysis_enzyme_cross_reactivity')
    if value is None:
        return _one_fact(record, 'analysis_enzyme_specificity_shown')
    native.update({'cross_reactivity_percent': value, 'cross_reactivity_refs': _refs(record['quantities']['analysis_enzyme_cross_reactivity'])})
    return _result('unknown', 'cross_reactivity_recorded_for_the_sheet', [])


def _first_enzyme_quenched(record, native):
    return _one_fact(record, 'first_enzyme_quenched_before_analysis')


def _reagent_blank(record, native):
    return _one_fact(record, 'reagent_blank_done')


def _no_enzyme_sample(record, native):
    return _one_fact(record, 'no_enzyme_control_done')


def _products_stable_until_analysis(record, native):
    return _one_fact(record, 'products_stable_until_analysis')


def _inactive_enzyme_sample(record, native):
    return _one_fact(record, 'inactive_enzyme_control_done')


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


EVALUATORS = {'analysis_enzyme_specificity': _analysis_enzyme_specificity, 'standard_curve_per_species': _standard_curve_per_species,
              'denominator_and_coverage': _denominator_and_coverage, 'closure': _closure, 'analysis_run_to_completion': _analysis_run_to_completion,
              'signals_inside_standard_curve': _signals_inside_standard_curve, 'reporter_absorbance_range': _reporter_absorbance_range,
              'cross_reactivity': _cross_reactivity, 'first_enzyme_quenched': _first_enzyme_quenched, 'reagent_blank': _reagent_blank,
              'no_enzyme_sample': _no_enzyme_sample, 'products_stable_until_analysis': _products_stable_until_analysis,
              'inactive_enzyme_sample': _inactive_enzyme_sample, 'stable_composition': _stable_composition, 'replicates': _replicates,
              'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_distribution_enzymatic_endpoint(record):
    """Grade one enzymatic end-point determination record. Returns the criterion answers and native values."""
    stated = record['facts']['claimed_product_detected']
    known = stated['answer'] in INTERACTION
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'reporter_signal': record['reporter_signal'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'interaction': INTERACTION.get(stated['answer']), 'interaction_refs': list(stated['source_refs']) if known else [], 'interaction_support': stated['support'] if known else None,
              'total_recovery_percent': None, 'recovery_refs': [], 'absorbance_max': None, 'absorbance_refs': [], 'cross_reactivity_percent': None, 'cross_reactivity_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, DISTRIBUTION_ENZYMATIC_ENDPOINT_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'distribution_enzymatic_endpoint', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
