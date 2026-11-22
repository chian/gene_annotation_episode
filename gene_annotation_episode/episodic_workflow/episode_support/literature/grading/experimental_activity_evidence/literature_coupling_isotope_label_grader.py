"""Coupling_isotope_label grader: judges ONE isotope-label flow experiment by its own standards.

Hand-built and private to coupling_isotope_label. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_coupling_isotope_label_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_coupling_isotope_label_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(label_purity_fraction, control_over_test, atoms_found_over_expected, replicate_count, each with its refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact label_detected_in_product ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying whether
it found the label of the claimed source in the product above its own control. It is recorded in native as 'label_flow' with its refs and its support (class
decision of 2026-11-22: 'interaction_detected' reads "label flow from the claimed source into the product detected"). It is only used by the converter when no
effect is stated.

Native values retained: every record quantity as given, the preparations, the three plain choices (spread_kind, label_source, readout), and label_purity_fraction,
control_over_test, atoms_found_over_expected, replicate_count, replicate_independent, label_flow, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_coupling_isotope_label_criteria import (
    COUPLING_ISOTOPE_LABEL_CRITERIA, FRACTION_PER_UNIT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_coupling_isotope_label_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in COUPLING_ISOTOPE_LABEL_CRITERIA)
LABEL_FLOW = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact label_detected_in_product


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


def _unlabelled_control(record, native):
    return _one_fact(record, 'unlabelled_control')


def _back_exchange_control(record, native):
    return _one_fact(record, 'back_exchange_control')


def _label_position(record, native):
    return _one_fact(record, 'label_position_determined')


def _spontaneous_labelling_control(record, native):
    names = ('no_enzyme_control', 'inactive_enzyme_control')
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'spontaneous_labelling_control_stated', refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _control_label_level(record, native):
    control, test = _fraction(record, 'label_in_control'), _fraction(record, 'label_incorporation')
    if control is None or test is None:
        return _result('unknown', 'control_or_test_label_missing', [])
    native['control_over_test'] = control / test
    native['control_refs'] = _refs(record['quantities']['label_in_control'], record['quantities']['label_incorporation'])
    return _result('unknown', 'control_label_recorded_for_the_sheet', [])


def _product_identity(record, native):
    return _one_fact(record, 'product_identified_by_mass_shift')


def _label_purity(record, native):
    purity = _fraction(record, 'label_purity')
    if purity is None:
        return _result('unknown', 'label_purity_not_stated', [])
    native['label_purity_fraction'] = purity
    native['label_purity_refs'] = _refs(record['quantities']['label_purity'])
    return _result('unknown', 'label_purity_recorded_for_the_sheet', [])


def _natural_abundance_correction(record, native):
    return _one_fact(record, 'natural_abundance_corrected')


def _label_stoichiometry(record, native):
    found, expected = _value(record, 'label_atoms_per_product'), _value(record, 'label_atoms_expected')
    if found is None or expected is None:
        return _result('unknown', 'label_atoms_missing', [])
    native['atoms_found_over_expected'] = found / expected
    native['atoms_refs'] = _refs(record['quantities']['label_atoms_per_product'], record['quantities']['label_atoms_expected'])
    return _result('unknown', 'label_atoms_recorded_for_the_sheet', [])


def _matched_runs(record, native):
    names = ('same_preparation', 'same_window')
    status, reason = _shared_rule([record['facts'][n]['answer'] for n in names])
    return _result(status, reason, _refs(*(record['facts'][n] for n in names)))


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


EVALUATORS = {'unlabelled_control': _unlabelled_control, 'back_exchange_control': _back_exchange_control, 'label_position': _label_position,
              'spontaneous_labelling_control': _spontaneous_labelling_control, 'control_label_level': _control_label_level, 'product_identity': _product_identity,
              'label_purity': _label_purity, 'natural_abundance_correction': _natural_abundance_correction, 'label_stoichiometry': _label_stoichiometry,
              'matched_runs': _matched_runs, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme, 'replicates': _replicates}


def grade_coupling_isotope_label(record):
    """Grade one isotope-label flow record. Returns the criterion answers and native values."""
    detected = record['facts']['label_detected_in_product']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'label_source': record['label_source'], 'readout': record['readout'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'label_flow': LABEL_FLOW.get(detected['answer']), 'label_flow_refs': list(detected['source_refs']) if detected['answer'] in LABEL_FLOW else [], 'label_flow_support': detected['support'],
              'label_purity_fraction': None, 'label_purity_refs': [], 'control_over_test': None, 'control_refs': [], 'atoms_found_over_expected': None, 'atoms_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, COUPLING_ISOTOPE_LABEL_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'coupling_isotope_label', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
