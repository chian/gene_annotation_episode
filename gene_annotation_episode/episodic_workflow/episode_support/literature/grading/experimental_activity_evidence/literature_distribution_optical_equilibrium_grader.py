"""Distribution_optical_equilibrium grader: judges ONE optical equilibrium measurement of a reaction mixture by its own standards.

Hand-built and private to distribution_optical_equilibrium. Deterministic; no model call, no store access.
Input: the record of one measurement (forms/.../literature_distribution_optical_equilibrium_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_distribution_optical_equilibrium_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(absorbance_max, plateau_change_percent, replicate_count, each with its refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact claimed_product_detected ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying
whether the signal showed the product the experiment tests for. It is kept in native as 'interaction' with its refs ('interaction_refs') and its quote
support ('interaction_support') and read by no criterion; the converter hands it to the sheet only when no effect is stated (class decision: for the
product_distribution class 'interaction_detected' reads "product detected").

Native values retained: every record quantity as given, spread_kind, readout and the preparations, and absorbance_max, absorbance_refs,
plateau_change_percent, plateau_refs, replicate_count, replicate_independent, replicate_refs, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_distribution_optical_equilibrium_criteria import DISTRIBUTION_OPTICAL_EQUILIBRIUM_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_distribution_optical_equilibrium_grade'
CRITERIA = tuple(criterion['id'] for criterion in DISTRIBUTION_OPTICAL_EQUILIBRIUM_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the stated yes/no result of the fact claimed_product_detected


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


def _pure_species_spectra(record, native):
    return _one_fact(record, 'pure_species_spectra_measured')


def _extinction_coefficient_stated(record, native):
    if _value(record, 'extinction_coefficient') is None or _value(record, 'wavelength') is None:
        return _result('unknown', 'extinction_coefficient_or_wavelength_missing', [])
    return _result('supported', 'extinction_coefficient_and_wavelength_stated', _refs(record['quantities']['extinction_coefficient'], record['quantities']['wavelength']))


def _denominator_and_coverage(record, native):
    names = ('all_absorbing_species_accounted', 'constant_refers_to_one_step')
    status, reason = _shared_rule([record['facts'][n]['answer'] for n in names])
    return _result(status, reason, _refs(*(record['facts'][n] for n in names)))


def _absorbance_range(record, native):
    value = _value(record, 'absorbance_max')
    if value is None:
        return _result('unknown', 'absorbance_not_stated', [])
    native.update({'absorbance_max': value, 'absorbance_refs': _refs(record['quantities']['absorbance_max'])})
    return _result('unknown', 'absorbance_recorded_for_the_sheet', [])


def _no_enzyme_sample(record, native):
    return _one_fact(record, 'no_enzyme_control_done')


def _inactive_enzyme_sample(record, native):
    return _one_fact(record, 'inactive_enzyme_control_done')


def _plateau_stability(record, native):
    stable = record['facts']['plateau_stable']
    change = _value(record, 'plateau_change_percent')
    refs = _refs(record['quantities']['plateau_change_percent'], stable)
    if stable['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if change is not None:
        native.update({'plateau_change_percent': change, 'plateau_refs': refs})
        return _result('unknown', 'plateau_change_recorded_for_the_sheet', [])
    if stable['answer'] == 'yes':
        return _result('supported', 'plateau_stable_stated', refs)
    return _result('unknown', 'plateau_not_stated', [])


def _equilibrium_from_both_sides(record, native):
    items = [record['facts'][n] for n in ('approached_from_both_sides', 'same_value_at_several_initial_concentrations')]
    yes = [item for item in items if item['answer'] == 'yes']
    if yes:
        return _result('supported', 'equilibrium_evidence_stated', _refs(*yes))
    if all(item['answer'] == 'not_applicable' for item in items):
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


EVALUATORS = {'pure_species_spectra': _pure_species_spectra, 'extinction_coefficient_stated': _extinction_coefficient_stated,
              'denominator_and_coverage': _denominator_and_coverage, 'absorbance_range': _absorbance_range, 'no_enzyme_sample': _no_enzyme_sample,
              'inactive_enzyme_sample': _inactive_enzyme_sample, 'plateau_stability': _plateau_stability, 'equilibrium_from_both_sides': _equilibrium_from_both_sides,
              'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_distribution_optical_equilibrium(record):
    """Grade one optical equilibrium record. Returns the criterion answers and native values."""
    stated = record['facts']['claimed_product_detected']
    known = stated['answer'] in INTERACTION
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'readout': record['readout'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'interaction': INTERACTION.get(stated['answer']), 'interaction_refs': list(stated['source_refs']) if known else [], 'interaction_support': stated['support'] if known else None,
              'absorbance_max': None, 'absorbance_refs': [], 'plateau_change_percent': None, 'plateau_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, DISTRIBUTION_OPTICAL_EQUILIBRIUM_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'distribution_optical_equilibrium', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
