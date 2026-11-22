"""Transport_patch_clamp grader: judges ONE patch-clamp experiment on cells by its own standards. DRAFT 2026-11-22, owner to correct.

Hand-built and private to transport_patch_clamp. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_transport_patch_clamp_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_transport_patch_clamp_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(series_resistance_mohm, seal_resistance_gohm, reversal_minus_nernst_mv, cell_count and batch_count, each with its refs) and returns 'unknown' with a
reason ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact transport_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper itself
saying whether it saw a current (transport) above its own control. It is recorded in native as 'transport' with its refs and its support (class decision of
2026-11-22: 'interaction_detected' reads "transport detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the two plain choices (spread_kind, patch_configuration) and the preparations, and
series_resistance_mohm, seal_resistance_gohm, reversal_minus_nernst_mv, cell_count, batch_count, replicate_independent, transport, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_patch_clamp_criteria import (
    TRANSPORT_PATCH_CLAMP_CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_transport_patch_clamp_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in TRANSPORT_PATCH_CLAMP_CRITERIA)
TRANSPORT = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact transport_detected_above_control
GOHM_PER_UNIT = {'MOhm': 1.0e-3, 'GOhm': 1.0}   # FIXED_BY_DEFINITION: the unit of a resistance to GOhm (1 MOhm is 1e-3 GOhm)


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


def _host_cell_control(record, native):
    return _one_fact(record, 'untransfected_control_done')


def _inactive_mutant_control(record, native):
    return _one_fact(record, 'inactive_mutant_control_done')


def _substrate_free_control(record, native):
    return _one_fact(record, 'substrate_free_control_done')


def _ion_substitution(record, native):
    return _one_fact(record, 'ion_substitution_done')


def _blocker_control(record, native):
    return _one_fact(record, 'blocker_control_done')


def _series_resistance_error(record, native):
    value = _value(record, 'series_resistance')
    compensated = record['facts']['series_resistance_compensated']
    if value is not None:
        native.update({'series_resistance_mohm': value, 'series_resistance_refs': _refs(record['quantities']['series_resistance'])})
        return _result('unknown', 'series_resistance_recorded_for_the_sheet', [])
    if compensated['answer'] == 'yes':
        return _result('supported', 'series_resistance_compensation_stated', compensated['source_refs'])
    return _result('unknown', 'series_resistance_not_stated', [])


def _seal_and_leak(record, native):
    value = _value(record, 'seal_resistance')
    leak = record['facts']['leak_subtracted']
    if value is not None:
        native.update({'seal_resistance_gohm': value * GOHM_PER_UNIT[record['quantities']['seal_resistance']['unit']], 'seal_resistance_refs': _refs(record['quantities']['seal_resistance'])})
        return _result('unknown', 'seal_recorded_for_the_sheet', [])
    if leak['answer'] == 'yes':
        return _result('supported', 'leak_subtraction_stated', leak['source_refs'])
    return _result('unknown', 'seal_not_stated', [])


def _voltage_stated(record, native):
    if _value(record, 'holding_voltage') is None:
        return _result('unknown', 'holding_voltage_not_stated', [])
    return _result('supported', 'holding_voltage_stated', _refs(record['quantities']['holding_voltage']))


def _conductance_fact(record, name, quantities):
    """A fact only a conductance or a charge flow needs: its answer by the shared rule; an unstated fact is not applicable when none of ``quantities`` is stated."""
    item = record['facts'][name]
    status, reason = _shared_rule([item['answer']])
    if status == 'unknown' and all(_value(record, quantity) is None for quantity in quantities):
        return _result('not_applicable', 'no_conductance_or_charge_rate_stated', [])
    return _result(status, reason, item['source_refs'])


def _unitary_events_resolved(record, native):
    return _conductance_fact(record, 'single_channel_resolved', ('unitary_conductance',))


def _driving_force_correction(record, native):
    return _conductance_fact(record, 'driving_force_corrected', ('unitary_conductance', 'charge_rate'))


def _reversal_potential_match(record, native):
    reversal, nernst = _value(record, 'reversal_potential'), _value(record, 'nernst_potential')
    if reversal is None or nernst is None:
        return _result('unknown', 'reversal_or_nernst_missing', [])
    native['reversal_minus_nernst_mv'] = reversal - nernst
    native['reversal_refs'] = _refs(record['quantities']['reversal_potential'], record['quantities']['nernst_potential'])
    return _result('unknown', 'reversal_recorded_for_the_sheet', [])


def _replicates(record, native):
    cells, batches = _value(record, 'cell_count'), _value(record, 'batch_count')
    independent = record['facts']['independent_preparations']
    refs = _refs(record['quantities']['cell_count'], record['quantities']['batch_count'], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', 'replicates_not_independent', refs)
    if cells is None and batches is None:
        return _result('unknown', 'replicate_count_or_independence_unknown', [])
    native.update({'cell_count': cells, 'batch_count': batches, 'replicate_independent': independent['answer'], 'replicate_refs': refs})
    return _result('unknown', 'replicate_count_recorded_for_the_sheet', [])


def _native_substrate(record, native):
    return _one_fact(record, 'native_substrate')


EVALUATORS = {'host_cell_control': _host_cell_control, 'inactive_mutant_control': _inactive_mutant_control, 'substrate_free_control': _substrate_free_control,
              'ion_substitution': _ion_substitution, 'blocker_control': _blocker_control, 'series_resistance_error': _series_resistance_error,
              'seal_and_leak': _seal_and_leak, 'voltage_stated': _voltage_stated, 'unitary_events_resolved': _unitary_events_resolved,
              'driving_force_correction': _driving_force_correction, 'reversal_potential_match': _reversal_potential_match, 'replicates': _replicates,
              'native_substrate': _native_substrate}


def grade_transport_patch_clamp(record):
    """Grade one patch-clamp record. Returns the criterion answers and native values."""
    detected = record['facts']['transport_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'patch_configuration': record['patch_configuration'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'transport': TRANSPORT.get(detected['answer']), 'transport_refs': list(detected['source_refs']) if detected['answer'] in TRANSPORT else [], 'transport_support': detected['support'],
              'series_resistance_mohm': None, 'series_resistance_refs': [], 'seal_resistance_gohm': None, 'seal_resistance_refs': [], 'reversal_minus_nernst_mv': None, 'reversal_refs': [],
              'cell_count': None, 'batch_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, TRANSPORT_PATCH_CLAMP_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'transport_patch_clamp', 'experiment_ref': record['experiment_ref'],
            'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()},
            'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
