"""PLA grader: judges ONE proximity ligation assay (PLA: in situ PLA, Duolink) experiment (two proteins are probed in fixed cells or tissue with two primary antibodies from different species and oligonucleotide-linked secondary antibodies; where the two proteins are within about 40 nm the oligonucleotides are ligated, amplified by rolling-circle amplification and detected as one fluorescent punctum; the puncta are counted per cell; qualitative proximity evidence, no binding constant) by its own standards.

Hand-built and private to this method (it shares no grading logic with the other experiment graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_pla_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_pla_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on);
``_result`` refuses to build one without them. Where only a fact with no span would decide, the criterion returns 'unknown' with a declared reason.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown;
else all 'not_applicable' -> not_applicable; else supported. The other criteria have their own rules (declared).

A PLA reports no binding constant. The native values carry the qualitative statement of the record, 'interaction' ('detected' when a proximity signal is stated,
'not_detected' when it is stated not to be, else None), with the spans that state it ('interaction_refs'); the converter hands it to the merger as the experiment's qualitative effect.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs (puncta_target / puncta_control /
puncta_fold_over_control / puncta_refs, puncta_reduction_percent / reduction_refs, cells_counted / cells_counted_refs, replicate_count / replicate_independent / replicate_refs)
and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the PLA converter judges it.

Support: native 'support' holds, for each criterion, the supports ('direct', 'implied', 'about_something_else') of the stated fields it reads
(its declared 'reads'), copied from the record and not judged here; the converter judges them.

Native values retained: every record quantity as given, plus puncta_target, puncta_control, puncta_fold_over_control (None when the control has 0 puncta or a number is not stated), puncta_reduction_percent (signed),
puncta_spread_target / puncta_spread_control / puncta_spread_kind / spread_refs (when both spreads and their kind are stated), protein_depletion_percent / depletion_refs (when stated),
cells_counted, interaction, interaction_refs, preparations, cell_system, fixation and quantification_software.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_pla_criteria import (
    PERCENT_PER_FRACTION, PLA_CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_pla_grade'
CRITERIA = tuple(criterion['id'] for criterion in PLA_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact proximity_signal_detected


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
        raise ValueError('a ' + status + ' criterion needs support refs: ' + reason)
    return {'status': status, 'reason': reason, 'support_refs': refs if status in ('supported', 'conflicting') else []}


def _one_fact(record, name):
    item = record['facts'][name]
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, item['source_refs'])


def _proximity_observed(record, native):
    return _one_fact(record, 'proximity_signal_detected')


def _puncta_enrichment(record, native):
    target, control = _value(record, 'puncta_per_cell_target'), _value(record, 'puncta_per_cell_control')
    if target is None or control is None:
        return _result('unknown', 'puncta_enrichment_not_given', [])
    native.update({'puncta_target': target, 'puncta_control': control, 'puncta_fold_over_control': None if control == 0 else target / control,
                   'puncta_refs': _refs(record['quantities']['puncta_per_cell_target'], record['quantities']['puncta_per_cell_control'])})
    spread_target, spread_control = _value(record, 'puncta_spread_target'), _value(record, 'puncta_spread_control')
    if spread_target is not None and spread_control is not None and record['puncta_spread_kind'] is not None:      # the spread of both counts and what it is: recorded, judged by the sheet
        native.update({'puncta_spread_target': spread_target, 'puncta_spread_control': spread_control, 'puncta_spread_kind': record['puncta_spread_kind'],
                       'spread_refs': _refs(record['quantities']['puncta_spread_target'], record['quantities']['puncta_spread_control'])})
    return _result('unknown', 'puncta_enrichment_recorded_for_the_sheet', [])


def _single_antibody_control(record, native):
    return _one_fact(record, 'single_antibody_controls_negative')


def _no_primary_control(record, native):
    return _one_fact(record, 'no_primary_control_negative')


def _specificity_control(record, native):
    item = record['facts']['specificity_control_reduces_signal']
    if item['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', item['source_refs'])
    target, knockdown = _value(record, 'puncta_per_cell_target'), _value(record, 'puncta_per_cell_knockdown')
    if target is None or knockdown is None or target == 0:
        return _one_fact(record, 'specificity_control_reduces_signal')
    native.update({'puncta_reduction_percent': (target - knockdown) / target * PERCENT_PER_FRACTION,
                   'reduction_refs': _refs(record['quantities']['puncta_per_cell_target'], record['quantities']['puncta_per_cell_knockdown'])})
    depletion = _value(record, 'protein_depletion_percent')
    if depletion is not None:
        native.update({'protein_depletion_percent': depletion, 'depletion_refs': _refs(record['quantities']['protein_depletion_percent'])})
    return _result('unknown', 'puncta_reduction_recorded_for_the_sheet', [])


def _positive_control(record, native):
    return _one_fact(record, 'positive_control_pair_done')


def _antibody_species(record, native):
    return _one_fact(record, 'primary_antibodies_different_species')


def _antibody_validation(record, native):
    return _one_fact(record, 'antibodies_validated')


def _compartment(record, native):
    return _one_fact(record, 'puncta_in_expected_compartment')


def _cells_counted(record, native):
    count = _value(record, 'cells_counted')
    if count is None:
        return _result('unknown', 'cells_counted_not_given', [])
    native.update({'cells_counted': count, 'cells_counted_refs': _refs(record['quantities']['cells_counted'])})
    return _result('unknown', 'cells_counted_recorded_for_the_sheet', [])


def _blinded_quantification(record, native):
    return _one_fact(record, 'quantification_blinded')


def _statistical_test(record, native):
    return _one_fact(record, 'statistical_test_done')


def _replicates(record, native):
    count = _value(record, 'replicate_count')
    independent = record['facts']['independent_experiments']
    refs = _refs(record['quantities']['replicate_count'], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', 'replicates_not_independent', refs)
    if count is None:
        return _result('unknown', 'replicate_count_or_independence_unknown', [])
    native.update({'replicate_count': count, 'replicate_independent': independent['answer'], 'replicate_refs': refs})
    return _result('unknown', 'replicate_count_recorded_for_the_sheet', [])


EVALUATORS = {'proximity_observed': _proximity_observed, 'puncta_enrichment': _puncta_enrichment, 'single_antibody_control': _single_antibody_control, 'no_primary_control': _no_primary_control, 'specificity_control': _specificity_control, 'positive_control': _positive_control, 'antibody_species': _antibody_species, 'antibody_validation': _antibody_validation, 'compartment': _compartment, 'cells_counted': _cells_counted, 'blinded_quantification': _blinded_quantification, 'statistical_test': _statistical_test, 'replicates': _replicates}


def grade_pla(record):
    """Grade one PLA experiment record. Returns the criterion answers and native values."""
    detected = record['facts']['proximity_signal_detected']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'cell_system': record['cell_system'], 'fixation': record['fixation'], 'quantification_software': record['quantification_software'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'interaction': INTERACTION.get(detected['answer']), 'interaction_refs': list(detected['source_refs']) if detected['answer'] in INTERACTION else [], 'puncta_target': None, 'puncta_control': None, 'puncta_fold_over_control': None, 'puncta_refs': [], 'puncta_reduction_percent': None, 'reduction_refs': [], 'puncta_spread_target': None, 'puncta_spread_control': None, 'puncta_spread_kind': None, 'spread_refs': [], 'protein_depletion_percent': None, 'depletion_refs': [], 'cells_counted': None, 'cells_counted_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, PLA_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'pla', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
