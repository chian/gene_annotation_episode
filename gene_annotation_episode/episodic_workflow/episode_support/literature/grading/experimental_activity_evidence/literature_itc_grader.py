"""ITC grader: judges ONE isothermal titration calorimetry experiment by ITC's own standards.

Hand-built and private to ITC (it shares no grading logic with the SPR grader).
Deterministic; no model call, no store access.
Input: the record of one ITC experiment (forms/.../literature_itc_record.py).
Output: for each ITC criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_itc_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration, each reading its thresholds
by name from that file.

The grader holds NO threshold that judges goodness. Where a number would be
compared with a limit it records the number with its refs (n_over_expected,
c_value, injection_count, temperature_K, replicate_count, stoichiometry_n, the
free-energy gap, each with its refs) and returns 'unknown' with a reason ending
in '_recorded_for_the_sheet', and no refs; the ITC converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable):
any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

Native values retained: every record quantity as given, plus kd_nM,
temperature_K, enthalpy_kJ_per_mol, entropy_J_per_mol_K, n_over_expected,
c_value, final_ligand_over_kd, titration_mode, enthalpy_ionization_corrected, dg_from_kd_kJ_per_mol, dg_from_parts_kJ_per_mol, dg_gap_kJ_per_mol,
injection_count, temperature_control, replicate_count, replicate_independent,
stoichiometry_n, stoichiometry_free, concentration_facts_unknown and the refs of
each (n_over_expected_refs, c_value_refs, injection_refs, temperature_refs,
replicate_refs, stoichiometry_refs, dg_refs), preparations, spread_kind and
fit_model.
The stated yes/no result (fact binding_detected) is kept as native 'interaction' ('detected', 'not_detected' or None),
with the spans that state it ('interaction_refs') and its quote support ('interaction_support'); the converter hands it to
the sheet as the experiment's stated result when the source gave no binding constant.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_itc_criteria import GAS_CONSTANT_J_PER_MOL_K, ITC_CRITERIA, J_PER_KJ, KCAL_TO_KJ, KELVIN_OFFSET, NM_PER_M
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_itc_grade'
CRITERIA = tuple(criterion['id'] for criterion in ITC_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the stated yes/no result of the fact binding_detected
ENTHALPY_TO_KJ = {'kJ/mol': 1.0, 'kcal/mol': KCAL_TO_KJ}
ENTROPY_TO_J = {'J/mol/K': 1.0, 'cal/mol/K': KCAL_TO_KJ, 'kJ/mol/K': J_PER_KJ}


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _nm(record, name):
    value = _value(record, name)
    return None if value is None else value * _SCALES[record['quantities'][name]['unit']]


def _kelvin(record):
    value = _value(record, 'temperature')
    if value is None:
        return None
    return value + KELVIN_OFFSET if record['quantities']['temperature']['unit'] == 'C' else value


def _scaled(record, name, table):
    value = _value(record, name)
    return None if value is None else value * table[record['quantities'][name]['unit']]


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
    return {'status': status, 'reason': reason, 'support_refs': refs if status in ('supported', 'conflicting') else []}


def _heat_of_dilution_control(record, native):
    items = [record['facts'][n] for n in ('dilution_control_performed', 'dilution_control_subtracted', 'baseline_corrected')]
    status, reason = _shared_rule([i['answer'] for i in items])
    return _result(status, reason, _refs(*items))


def _concentration_accuracy_and_active_fraction(record, native):
    items = [record['facts'][n] for n in ('concentrations_determined', 'active_fraction_determined')]
    n, expected = _value(record, 'stoichiometry'), _value(record, 'expected_stoichiometry')
    refs = _refs(*items, record['quantities']['stoichiometry'], record['quantities']['expected_stoichiometry'])
    if n is not None and expected is not None:
        native['n_over_expected'] = n / expected
    facts_status, facts_reason = _shared_rule([i['answer'] for i in items])
    if facts_status == 'conflicting':
        return _result('conflicting', facts_reason, refs)
    if native['n_over_expected'] is None:
        return _result('unknown', 'n_or_expected_stoichiometry_missing', [])
    native.update({'n_over_expected_refs': refs, 'concentration_facts_unknown': facts_status == 'unknown'})
    return _result('unknown', 'n_over_expected_recorded_for_the_sheet', [])


def _c_value_window(record, native):
    n, cell, kd = _value(record, 'stoichiometry'), _nm(record, 'cell_concentration'), native['kd_nM']
    if n is None or cell is None or kd is None:
        return _result('unknown', 'n_cell_concentration_or_kd_missing', [])
    native['c_value'] = n * cell / kd
    native['c_value_refs'] = _refs(*(record['quantities'][name] for name in ('stoichiometry', 'cell_concentration', 'kd')))
    ratio = _value(record, 'final_molar_ratio')
    if ratio is not None:
        native['final_ligand_over_kd'] = ratio * native['c_value'] / n      # r x [cell] / KD: the final total ligand in units of KD (c = n [cell] / KD)
        native['final_ratio_refs'] = _refs(record['quantities']['final_molar_ratio'])
    return _result('unknown', 'c_value_recorded_for_the_sheet', [])


def _fit_model_appropriate(record, native):
    model = record['fit_model']
    heterogeneous = record['facts']['binding_sites_heterogeneous']
    residuals = record['facts']['residuals_reported']
    refs = _refs(heterogeneous, residuals)
    if model is None:
        return _result('unknown', 'fit_model_not_stated', [])
    if model == 'one_set_of_sites' and heterogeneous['answer'] == 'yes':
        return _result('conflicting', 'one_set_model_for_heterogeneous_sites', refs)
    if residuals['answer'] != 'yes':
        return _result('unknown', 'no_residual_evidence', [])
    if model == 'one_set_of_sites' and heterogeneous['answer'] != 'no':
        return _result('unknown', 'site_heterogeneity_unknown_for_one_set_model', [])
    return _result('supported', 'model_stated_with_residual_evidence', refs)


def _injections_sufficient(record, native):
    count = _value(record, 'injection_count')
    mode = record['titration_mode']
    if mode in ('single_injection', 'continuous'):
        native.update({'titration_mode': mode, 'injection_refs': _refs(record['quantities']['injection_count'])})
        return _result('unknown', 'titration_mode_recorded_for_the_sheet', [])
    if count is None:
        return _result('unknown', 'injection_count_missing', [])
    native.update({'injection_count': count, 'injection_refs': _refs(record['quantities']['injection_count'])})
    return _result('unknown', 'injection_count_recorded_for_the_sheet', [])


def _buffer_matching(record, native):
    item = record['facts']['buffer_matching']
    status = {'dialysed_together': 'supported', 'matched_by_stated_procedure': 'supported', 'not_matched': 'conflicting'}.get(item['answer'], 'unknown')
    reason = {'supported': 'buffers_matched', 'conflicting': 'buffers_not_matched', 'unknown': 'buffer_matching_unknown'}[status]
    return _result(status, reason, item['source_refs'])


def _temperature_stated_and_controlled(record, native):
    temperature = native['temperature_K']
    controlled = record['facts']['temperature_controlled']
    refs = _refs(record['quantities']['temperature'], controlled)
    if controlled['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if temperature is None:
        return _result('unknown', 'temperature_not_stated', [])
    native.update({'temperature_refs': refs, 'temperature_control': controlled['answer']})
    return _result('unknown', 'temperature_recorded_for_the_sheet', [])


def _replicate_titrations_independent(record, native):
    count = _value(record, 'replicate_count')
    independent = record['facts']['independent_titrations']
    refs = _refs(record['quantities']['replicate_count'], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', 'replicates_not_independent', refs)
    if count is None:
        return _result('unknown', 'replicate_count_or_independence_unknown', [])
    native.update({'replicate_count': count, 'replicate_independent': independent['answer'], 'replicate_refs': refs})
    return _result('unknown', 'replicate_count_recorded_for_the_sheet', [])


def _stoichiometry_consistency(record, native):
    n = _value(record, 'stoichiometry')
    free = record['facts']['n_fitted_freely']
    if n is None:
        return _result('unknown', 'stoichiometry_not_given', [])
    refs = _refs(record['quantities']['stoichiometry'], free)
    if free['answer'] == 'no':
        return _result('conflicting', 'stoichiometry_was_fixed', refs)
    native.update({'stoichiometry_n': n, 'stoichiometry_free': free['answer'], 'stoichiometry_refs': refs})
    return _result('unknown', 'stoichiometry_recorded_for_the_sheet', [])


def _thermodynamic_consistency(record, native):
    kd, enthalpy, temperature = native['kd_nM'], native['enthalpy_kJ_per_mol'], native['temperature_K']
    if kd is None or enthalpy is None or temperature is None:
        return _result('unknown', 'kd_enthalpy_or_temperature_missing', [])
    entropy = native['entropy_J_per_mol_K']
    if entropy is None:
        return _result('not_applicable', 'entropy_not_given_check_not_possible', [])
    native['dg_from_kd_kJ_per_mol'] = GAS_CONSTANT_J_PER_MOL_K * temperature * math.log(kd / NM_PER_M) / J_PER_KJ
    native['dg_from_parts_kJ_per_mol'] = enthalpy - temperature * entropy / J_PER_KJ
    native['dg_gap_kJ_per_mol'] = abs(native['dg_from_kd_kJ_per_mol'] - native['dg_from_parts_kJ_per_mol'])
    native['dg_refs'] = _refs(*(record['quantities'][name] for name in ('kd', 'enthalpy', 'entropy', 'temperature')))
    native['enthalpy_ionization_corrected'] = record['facts']['enthalpy_buffer_ionization_corrected']['answer']
    return _result('unknown', 'free_energy_gap_recorded_for_the_sheet', [])


EVALUATORS = {'heat_of_dilution_control': _heat_of_dilution_control, 'concentration_accuracy_and_active_fraction': _concentration_accuracy_and_active_fraction, 'c_value_window': _c_value_window, 'fit_model_appropriate': _fit_model_appropriate, 'injections_sufficient': _injections_sufficient, 'buffer_matching': _buffer_matching, 'temperature_stated_and_controlled': _temperature_stated_and_controlled, 'replicate_titrations_independent': _replicate_titrations_independent, 'stoichiometry_consistency': _stoichiometry_consistency, 'thermodynamic_consistency': _thermodynamic_consistency}


def grade_itc(record):
    """Grade one ITC experiment record. Returns the criterion answers and native values."""
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'], 'fit_model': record['fit_model'], 'titration_mode': record['titration_mode'], 'final_ligand_over_kd': None, 'final_ratio_refs': [], 'enthalpy_ionization_corrected': None, 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'kd_nM': _nm(record, 'kd'), 'temperature_K': _kelvin(record), 'enthalpy_kJ_per_mol': _scaled(record, 'enthalpy', ENTHALPY_TO_KJ), 'entropy_J_per_mol_K': _scaled(record, 'entropy', ENTROPY_TO_J), 'n_over_expected': None, 'c_value': None, 'dg_from_kd_kJ_per_mol': None, 'dg_from_parts_kJ_per_mol': None, 'dg_gap_kJ_per_mol': None, 'n_over_expected_refs': [], 'concentration_facts_unknown': None, 'c_value_refs': [], 'injection_count': None, 'injection_refs': [], 'temperature_refs': [], 'temperature_control': None, 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': [], 'stoichiometry_n': None, 'stoichiometry_free': None, 'stoichiometry_refs': [], 'dg_refs': []}
    native['support'] = criterion_supports(record, ITC_CRITERIA)      # kept for the sheet: the grader does not judge it (criterion id -> supports of the stated fields it reads)
    stated = record['facts']['binding_detected']      # the experiment's stated yes/no result: a fact kept for the sheet, read by no criterion
    known = stated['answer'] in INTERACTION
    native.update({'interaction': INTERACTION.get(stated['answer']), 'interaction_refs': list(stated['source_refs']) if known else [], 'interaction_support': stated['support'] if known else None})
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'itc', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
