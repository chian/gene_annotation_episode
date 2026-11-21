"""BLI grader: judges ONE bio-layer interferometry experiment by BLI's own standards.

Hand-built and private to BLI (it shares no grading logic with the SPR or ITC graders).
Deterministic; no model call, no store access.
Input: the record of one BLI experiment (forms/.../literature_bli_record.py).
Output: for each BLI criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_bli_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration, each reading its thresholds
by name from that file.

The grader holds NO threshold that judges goodness. Where a number would be
compared with a limit it records the number with its refs (loading_level_nm and
response_max_nm, concentration_count and the two ratios over the KD,
fit_r_squared, dissociation_decay, replicate_count, kd_from_rates_nM,
steady_kinetic_fold, each with its refs) and returns 'unknown' with a reason
ending in '_recorded_for_the_sheet', and no refs; the BLI converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable):
any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. Criteria that ask whether
EITHER of two things was done (reference subtraction, avidity and mass
transport) take a 'yes' of either as enough, and otherwise use the shared rule.

Native values retained: every record quantity as given, plus kd_nM,
kd_from_rates_nM, dissociation_time_s, dissociation_decay, concentration_count,
concentration_low_over_kd, concentration_high_over_kd, loading_level_nm,
response_max_nm, loading_documented, partner_mass_kda, baseline_noise_nm (and their refs partner_mass_refs, noise_refs), fit_r_squared, fit_bivalent_answer,
steady_kinetic_fold, replicate_count, replicate_independent and the refs of each
(loading_refs, concentration_refs, fit_refs, dissociation_refs, replicate_refs,
kinetic_refs, steady_kinetic_refs), preparations, spread_kind, fit_model and
biosensor_type.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_bli_criteria import BLI_CRITERIA, NM_PER_M, SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_bli_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in BLI_CRITERIA)
TIME_TO_S = {'s': 1.0, 'min': SECONDS_PER_MINUTE}


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


def _either_rule(record, names, supported_reason):
    answers = _answers(record, names)
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', supported_reason, refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _reference_subtraction(record, native):
    return _either_rule(record, ('reference_sensor_subtracted', 'buffer_reference_subtracted'), 'reference_subtraction_stated')


def _nonspecific_binding_control(record, native):
    item = record['facts']['nonspecific_binding_checked']
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, item['source_refs'])


def _baseline_and_regeneration(record, native):
    names = ('baseline_stable', 'regeneration')
    status, reason = _shared_rule(_answers(record, names))
    return _result(status, reason, _refs(*(record['facts'][n] for n in names)))


def _loading_and_response(record, native):
    documented = record['facts']['loading_step_documented']
    loading, response = _value(record, 'loading_level'), _value(record, 'response_max')
    refs = _refs(documented, record['quantities']['loading_level'], record['quantities']['response_max'])
    if documented['answer'] == 'no':
        return _result('conflicting', 'loading_step_not_documented', refs)
    if loading is None and response is None:
        return _result('unknown', 'loading_or_response_missing', [])
    native.update({'loading_level_nm': loading, 'response_max_nm': response, 'loading_documented': documented['answer'], 'loading_refs': refs})
    return _result('unknown', 'loading_and_response_recorded_for_the_sheet', [])


def _concentration_series(record, native):
    kd = native['kd_nM']
    series = record['concentration_series']
    values = series['value']
    if kd is None or values is None:
        return _result('unknown', 'kd_or_series_missing', [])
    scale = _SCALES[series['unit']]
    nm = [v * scale for v in values]
    native['concentration_count'] = len(nm)
    native['concentration_low_over_kd'] = min(nm) / kd
    native['concentration_high_over_kd'] = max(nm) / kd
    native['concentration_refs'] = _refs(series, record['quantities']['kd'])
    return _result('unknown', 'concentration_series_recorded_for_the_sheet', [])


def _fit_model(record, native):
    model = record['fit_model']
    bivalent = record['facts']['analyte_bivalent_or_oligomeric']
    r_squared = _value(record, 'fit_r_squared')
    refs = _refs(bivalent, record['quantities']['fit_r_squared'])
    if model is None:
        return _result('unknown', 'fit_model_not_stated', [])
    if model == '1:1' and bivalent['answer'] == 'yes':
        return _result('conflicting', 'one_to_one_model_for_bivalent_or_oligomeric_analyte', refs)
    if r_squared is None:
        return _result('unknown', 'no_fit_quality_evidence', [])
    native.update({'fit_r_squared': r_squared, 'fit_bivalent_answer': bivalent['answer'], 'fit_refs': refs})
    return _result('unknown', 'r_squared_recorded_for_the_sheet', [])


def _avidity_and_mass_transport(record, native):
    return _either_rule(record, ('avidity_rebinding_considered', 'mass_transport_considered'), 'avidity_or_transport_considered')


def _dissociation_window(record, native):
    koff, time = _value(record, 'koff'), native['dissociation_time_s']
    if koff is None or time is None:
        return _result('unknown', 'koff_or_dissociation_time_missing', [])
    native['dissociation_decay'] = 1 - math.exp(-koff * time)
    native['dissociation_refs'] = _refs(record['quantities']['koff'], record['quantities']['dissociation_time'])
    return _result('unknown', 'dissociation_decay_recorded_for_the_sheet', [])


def _replicates(record, native):
    count = _value(record, 'replicate_count')
    independent = record['facts']['independent_sensors']
    refs = _refs(record['quantities']['replicate_count'], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', 'replicates_not_independent', refs)
    if count is None:
        return _result('unknown', 'replicate_count_or_independence_unknown', [])
    native.update({'replicate_count': count, 'replicate_independent': independent['answer'], 'replicate_refs': refs})
    return _result('unknown', 'replicate_count_recorded_for_the_sheet', [])


def _immobilized_activity(record, native):
    item = record['facts']['immobilized_partner_active']
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, item['source_refs'])


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


EVALUATORS = {'reference_subtraction': _reference_subtraction, 'nonspecific_binding_control': _nonspecific_binding_control, 'baseline_and_regeneration': _baseline_and_regeneration, 'loading_and_response': _loading_and_response, 'concentration_series': _concentration_series, 'fit_model': _fit_model, 'avidity_and_mass_transport': _avidity_and_mass_transport, 'dissociation_window': _dissociation_window, 'replicates': _replicates, 'immobilized_activity': _immobilized_activity, 'kinetic_consistency': _kinetic_consistency, 'steady_state_vs_kinetic': _steady_state_vs_kinetic}


def grade_bli(record):
    """Grade one BLI experiment record. Returns the criterion answers and native values."""
    time = _value(record, 'dissociation_time')
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'], 'fit_model': record['fit_model'], 'biosensor_type': record['biosensor_type'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'kd_nM': _nm(record, 'kd'), 'kd_from_rates_nM': None, 'dissociation_time_s': None if time is None else time * TIME_TO_S[record['quantities']['dissociation_time']['unit']], 'dissociation_decay': None, 'concentration_count': None, 'concentration_low_over_kd': None, 'concentration_high_over_kd': None, 'concentration_refs': [], 'loading_level_nm': None, 'response_max_nm': None, 'loading_documented': None, 'loading_refs': [], 'fit_r_squared': None, 'fit_bivalent_answer': None, 'fit_refs': [], 'dissociation_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': [], 'kinetic_refs': [], 'steady_kinetic_fold': None, 'steady_kinetic_refs': []}
    native.update({'partner_mass_kda': _value(record, 'partner_mass'), 'partner_mass_refs': _refs(record['quantities']['partner_mass']), 'baseline_noise_nm': _value(record, 'baseline_noise'), 'noise_refs': _refs(record['quantities']['baseline_noise'])})      # facts the sheet judges the loading and the response against (None when not stated)
    native['support'] = criterion_supports(record, BLI_CRITERIA)      # kept for the sheet: the grader does not judge it (criterion id -> supports of the stated fields it reads)
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'bli', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
