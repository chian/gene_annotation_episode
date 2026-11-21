"""GCI grader: judges ONE grating-coupled interferometry experiment by GCI's own standards.

Hand-built and private to GCI (it shares no grading logic with the SPR, ITC or BLI graders).
Deterministic; no model call, no store access.
Input: the record of one GCI experiment (forms/.../literature_gci_record.py).
Output: for each GCI criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_gci_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration, each reading its thresholds
by name from that file.

The grader holds NO threshold that judges goodness. Where a number would be
compared with a limit it records the number with its refs (the surface level and
the response in pg/mm2, concentration_count and the two ratios over the KD,
replicate_count, kd_from_rates_nM, steady_kinetic_fold, each with its refs) and
returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and no
refs; the GCI converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable):
any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. The criterion that asks
whether EITHER of two things was done (reference subtraction) takes a 'yes' of
either as enough, and otherwise uses the shared rule.

Native values retained: every record quantity as given, plus kd_nM,
kd_from_rates_nM, immobilization_level_pg_mm2, response_max_pg_mm2,
concentration_count, concentration_low_over_kd, concentration_high_over_kd,
rmax_theoretical_pg_mm2, rmax_ratio, dissociation_time_s, dissociation_decay,
dissociation_response_pg_mm2, pulse_kinetics, steady_kinetic_fold, replicate_count, replicate_independent and
the refs of each (surface_refs, concentration_refs, replicate_refs, kinetic_refs,
steady_kinetic_refs), preparations, spread_kind, fit_model and chip_type.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_gci_criteria import GCI_CRITERIA, NM_PER_M, NM_PER_UNIT, PG_MM2_PER_RU, PG_MM2_PER_UNIT, S_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_gci_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in GCI_CRITERIA)


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _nm(record, name):
    value = _value(record, name)
    return None if value is None else value * NM_PER_UNIT[record['quantities'][name]['unit']]


def _pg_mm2(record, name):
    value = _value(record, name)
    if value is None:
        return None
    unit = record['quantities'][name]['unit']
    return value * (PG_MM2_PER_RU if unit == 'RU' else PG_MM2_PER_UNIT[unit])


def _refs(*items):
    refs = []
    for item in items:
        refs += item['source_refs']
    return list(dict.fromkeys(refs))


def _answers(record, names):
    return [record['facts'][name]['answer'] for name in names]


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


def _one_fact(record, name):
    item = record['facts'][name]
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, item['source_refs'])


def _reference_subtraction(record, native):
    names = ('reference_channel_subtracted', 'double_referenced')
    answers = _answers(record, names)
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'reference_subtraction_stated', refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _bulk_solvent_correction(record, native):
    return _one_fact(record, 'bulk_solvent_corrected')


def _nonspecific_binding_control(record, native):
    return _one_fact(record, 'nonspecific_binding_checked')


def _baseline_and_regeneration(record, native):
    names = ('baseline_stable', 'regeneration')
    status, reason = _shared_rule(_answers(record, names))
    return _result(status, reason, _refs(*(record['facts'][n] for n in names)))


def _surface_level_and_response(record, native):
    level, response = native['immobilization_level_pg_mm2'], native['response_max_pg_mm2']
    if level is None and response is None:
        return _result('unknown', 'level_or_response_missing', [])
    native['surface_refs'] = _refs(record['quantities']['immobilization_level'], record['quantities']['response_max'])
    return _result('unknown', 'surface_level_and_response_recorded_for_the_sheet', [])


def _rmax_consistency(record, native):
    names = ('response_max', 'immobilization_level', 'analyte_mass', 'ligand_mass', 'stoichiometry')
    level, response = native['immobilization_level_pg_mm2'], native['response_max_pg_mm2']
    analyte, ligand, stoichiometry = (_value(record, n) for n in ('analyte_mass', 'ligand_mass', 'stoichiometry'))
    if level is None or response is None or analyte is None or ligand is None or stoichiometry is None:
        return _result('unknown', 'rmax_operand_missing', [])
    theoretical = analyte / ligand * level * stoichiometry
    native['rmax_theoretical_pg_mm2'] = theoretical
    native['rmax_ratio'] = response / theoretical
    native['rmax_refs'] = _refs(*(record['quantities'][n] for n in names))
    return _result('unknown', 'rmax_ratio_recorded_for_the_sheet', [])


def _concentration_series(record, native):
    kd = native['kd_nM']
    series = record['concentration_series']
    values = series['value']
    if kd is None or values is None:
        return _result('unknown', 'kd_or_series_missing', [])
    scale = NM_PER_UNIT[series['unit']]
    nm = [v * scale for v in values]
    native['concentration_count'] = len(nm)
    native['concentration_low_over_kd'] = min(nm) / kd
    native['concentration_high_over_kd'] = max(nm) / kd
    native['concentration_refs'] = _refs(series, record['quantities']['kd'], record['facts']['repeated_pulse_kinetics_used'])
    native['pulse_kinetics'] = record['facts']['repeated_pulse_kinetics_used']['answer'] == 'yes'
    return _result('unknown', 'concentration_series_recorded_for_the_sheet', [])


def _dissociation_window(record, native):
    koff, time = _value(record, 'koff'), _value(record, 'dissociation_time')
    if koff is None or time is None:
        return _result('unknown', 'koff_or_dissociation_time_missing', [])
    native['dissociation_time_s'] = time * S_PER_UNIT[record['quantities']['dissociation_time']['unit']]
    native['dissociation_decay'] = 1 - math.exp(-koff * native['dissociation_time_s'])
    native['dissociation_response_pg_mm2'] = native['response_max_pg_mm2']
    native['dissociation_refs'] = _refs(record['quantities']['koff'], record['quantities']['dissociation_time'], *([record['quantities']['response_max']] if native['response_max_pg_mm2'] is not None else []))
    return _result('unknown', 'dissociation_decay_recorded_for_the_sheet', [])


def _fit_model(record, native):
    model = record['fit_model']
    bivalent = record['facts']['analyte_bivalent_or_oligomeric']
    if model is None:
        return _result('unknown', 'fit_model_not_stated', [])
    if model == '1:1' and bivalent['answer'] == 'yes':
        return _result('conflicting', 'one_to_one_model_for_bivalent_or_oligomeric_analyte', bivalent['source_refs'])
    if model == '1:1' and bivalent['answer'] != 'no':
        return _result('unknown', 'bivalence_or_oligomer_state_unknown_for_one_to_one_model', [])
    return _result('supported', 'model_stated', bivalent['source_refs'])


def _mass_transport(record, native):
    return _one_fact(record, 'mass_transport_checked')


def _replicates(record, native):
    count = _value(record, 'replicate_count')
    independent = record['facts']['independent_channels_or_chips']
    refs = _refs(record['quantities']['replicate_count'], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', 'replicates_not_independent', refs)
    if count is None:
        return _result('unknown', 'replicate_count_or_independence_unknown', [])
    native.update({'replicate_count': count, 'replicate_independent': independent['answer'], 'replicate_refs': refs})
    return _result('unknown', 'replicate_count_recorded_for_the_sheet', [])


def _immobilized_activity(record, native):
    return _one_fact(record, 'immobilized_partner_active')


def _kinetic_consistency(record, native):
    kd, kon, koff = native['kd_nM'], _value(record, 'kon'), _value(record, 'koff')
    if kd is None or kon is None or koff is None:
        return _result('unknown', 'kd_kon_or_koff_missing', [])
    native['kd_from_rates_nM'] = koff / kon * NM_PER_M
    native['kinetic_refs'] = _refs(*(record['quantities'][n] for n in ('kd', 'kon', 'koff')))
    return _result('unknown', 'kd_from_rates_recorded_for_the_sheet', [])


def _steady_state_vs_kinetic(record, native):
    steady, kd = _nm(record, 'kd_steady_state'), native['kd_nM']
    if steady is None or kd is None:
        if record['facts']['single_estimate_method']['answer'] == 'yes':
            return _result('not_applicable', 'single_estimate_method', record['facts']['single_estimate_method']['source_refs'])
        return _result('unknown', 'steady_state_or_kinetic_kd_missing', [])
    native['steady_kinetic_fold'] = max(steady, kd) / min(steady, kd)
    native['steady_kinetic_refs'] = _refs(record['quantities']['kd_steady_state'], record['quantities']['kd'])
    return _result('unknown', 'estimate_fold_recorded_for_the_sheet', [])


EVALUATORS = {'reference_subtraction': _reference_subtraction, 'bulk_solvent_correction': _bulk_solvent_correction, 'nonspecific_binding_control': _nonspecific_binding_control, 'baseline_and_regeneration': _baseline_and_regeneration, 'surface_level_and_response': _surface_level_and_response, 'rmax_consistency': _rmax_consistency, 'concentration_series': _concentration_series, 'dissociation_window': _dissociation_window, 'fit_model': _fit_model, 'mass_transport': _mass_transport, 'replicates': _replicates, 'immobilized_activity': _immobilized_activity, 'kinetic_consistency': _kinetic_consistency, 'steady_state_vs_kinetic': _steady_state_vs_kinetic}


def grade_gci(record):
    """Grade one GCI experiment record. Returns the criterion answers and native values."""
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'], 'fit_model': record['fit_model'], 'chip_type': record['chip_type'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'kd_nM': _nm(record, 'kd'), 'kd_from_rates_nM': None, 'immobilization_level_pg_mm2': _pg_mm2(record, 'immobilization_level'), 'response_max_pg_mm2': _pg_mm2(record, 'response_max'), 'concentration_count': None, 'concentration_low_over_kd': None, 'concentration_high_over_kd': None, 'concentration_refs': [], 'pulse_kinetics': None, 'surface_refs': [], 'rmax_theoretical_pg_mm2': None, 'rmax_ratio': None, 'rmax_refs': [], 'dissociation_time_s': None, 'dissociation_decay': None, 'dissociation_response_pg_mm2': None, 'dissociation_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': [], 'kinetic_refs': [], 'steady_kinetic_fold': None, 'steady_kinetic_refs': []}
    native['support'] = criterion_supports(record, GCI_CRITERIA)      # kept for the sheet: the grader does not judge it (criterion id -> supports of the stated fields it reads)
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'gci', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
