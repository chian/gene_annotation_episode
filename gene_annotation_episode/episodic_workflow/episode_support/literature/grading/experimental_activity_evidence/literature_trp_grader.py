"""Trp grader: judges ONE intrinsic tryptophan (and tyrosine) fluorescence quenching / enhancement binding titration by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET or MST graders).
Deterministic; no model call, no store access.
Input: the record of one titration (forms/.../literature_trp_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_trp_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration, each reading its thresholds
by name from that file.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs (fluorescence_change_percent/change_refs,
excitation_nm/excitation_refs, ligand_absorbance/absorbance_refs, added_volume_percent/added_volume_refs, protein_over_kd/protein_refs/tight_binding_handled,
concentration_count/count_refs and the low/high over the KD/series_refs, incubation_min/incubation_refs, replicate_count/replicate_independent/replicate_refs) and returns 'unknown'
with a reason ending in '_recorded_for_the_sheet'; the Trp converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable):
any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. inner_filter, dilution,
specificity_control, equilibrium, protein_concentration and fit_model have their
own rules (declared).

The reported constant of a series is the KD only (native 'constant_name' says so, or None): a Stern-Volmer
constant Ksv is a quenching efficiency, not a binding constant, and is kept apart.

Native values retained: every record quantity as given, plus kd_nM, constant_name, constant_nM, protein_nM,
protein_over_kd, excitation_nm, incubation_min, concentration_count, concentration_low_over_constant,
concentration_high_over_constant, preparations, spread_kind, fit_model, change_direction and emission_shift_direction.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_trp_criteria import MIN_PER_UNIT, NM_PER_UNIT, TRP_CRITERIA

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_trp_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in TRP_CRITERIA)
CONSTANTS = ('kd',)       # the reported constant of a series: only a KD is a binding constant


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _nm(record, name):
    value = _value(record, name)
    return None if value is None else value * NM_PER_UNIT[record['quantities'][name]['unit']]


def _minutes(record, name):
    value = _value(record, name)
    return None if value is None else value * MIN_PER_UNIT[record['quantities'][name]['unit']]


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


def _signal_amplitude(record, native):
    change = _value(record, 'fluorescence_change')
    if change is None:
        return _result('unknown', 'fluorescence_change_not_given', [])
    native.update({'fluorescence_change_percent': change, 'change_refs': _refs(record['quantities']['fluorescence_change'])})
    return _result('unknown', 'fluorescence_change_recorded_for_the_sheet', [])


def _excitation_selectivity(record, native):
    wavelength = native['excitation_nm']
    if wavelength is None:
        return _result('unknown', 'excitation_wavelength_not_stated', [])
    native['excitation_refs'] = _refs(record['quantities']['excitation_wavelength'])
    return _result('unknown', 'excitation_recorded_for_the_sheet', [])


def _inner_filter(record, native):
    corrected, negligible = record['facts']['inner_filter_corrected'], record['facts']['ligand_absorbance_negligible']
    absorbance = _value(record, 'ligand_absorbance')
    refs = _refs(corrected, negligible, record['quantities']['ligand_absorbance'])
    if corrected['answer'] == 'yes':
        return _result('supported', 'inner_filter_corrected', refs)
    if absorbance is not None:
        native.update({'ligand_absorbance': absorbance, 'absorbance_refs': refs})
        return _result('unknown', 'ligand_absorbance_recorded_for_the_sheet', [])
    if negligible['answer'] == 'yes':
        return _result('supported', 'ligand_absorbance_negligible', refs)
    if 'no' in (corrected['answer'], negligible['answer']):
        return _result('conflicting', 'inner_filter_not_corrected', refs)
    if corrected['answer'] == 'not_applicable' and negligible['answer'] == 'not_applicable':
        return _result('not_applicable', 'fact_not_applicable', [])
    return _result('unknown', 'inner_filter_not_addressed', [])


def _dilution(record, native):
    corrected = record['facts']['dilution_corrected']
    added = _value(record, 'added_volume_fraction')
    refs = _refs(corrected, record['quantities']['added_volume_fraction'])
    if corrected['answer'] == 'yes':
        return _result('supported', 'dilution_corrected', refs)
    if added is not None:
        native.update({'added_volume_percent': added, 'added_volume_refs': refs})
        return _result('unknown', 'added_volume_recorded_for_the_sheet', [])
    if corrected['answer'] == 'no':
        return _result('conflicting', 'dilution_not_corrected', refs)
    if corrected['answer'] == 'not_applicable':
        return _result('not_applicable', 'fact_not_applicable', [])
    return _result('unknown', 'dilution_not_addressed', [])


def _buffer_blank(record, native):
    return _one_fact(record, 'buffer_blank_subtracted')


def _ligand_fluorescence(record, native):
    return _one_fact(record, 'ligand_only_control_measured')


def _specificity_control(record, native):
    names = ('nonbinding_control_done', 'trp_analogue_control_done', 'signal_localised_to_binding_site')
    answers = _answers(record, names)
    if 'yes' in answers:
        return _result('supported', 'a_specificity_control_done', _refs(*(record['facts'][n] for n in names if record['facts'][n]['answer'] == 'yes')))
    status, reason = _shared_rule(answers)
    return _result(status, reason, _refs(*(record['facts'][n] for n in names)))


def _photobleaching(record, native):
    return _one_fact(record, 'photobleaching_checked')


def _saturation(record, native):
    return _one_fact(record, 'signal_saturates')


def _concentration_series(record, native):
    constant = native['constant_nM']
    series = record['concentration_series']
    values = series['value']
    counted = len(values) if values is not None else _value(record, 'titration_point_count')
    ends = _value(record, 'concentration_lowest') is not None or _value(record, 'concentration_highest') is not None
    if counted is None and not ends:
        return _result('unknown', 'kd_or_series_missing', [])
    if counted is not None:
        native.update({'concentration_count': counted, 'count_refs': _refs(series, record['quantities']['titration_point_count'])})
    if constant is not None and values is not None:         # the span is formed from the list and the KD
        nm = [v * NM_PER_UNIT[series['unit']] for v in values]
        native.update({'concentration_low_over_constant': min(nm) / constant, 'concentration_high_over_constant': max(nm) / constant,
                       'series_refs': _refs(series, record['quantities']['kd'])})
    elif constant is not None and values is None:           # a passage that gives a range and not a list: its stated ends (either may be missing) and the KD
        low, high = _nm(record, 'concentration_lowest'), _nm(record, 'concentration_highest')
        if low is not None or high is not None:
            native.update({'concentration_low_over_constant': None if low is None else low / constant,
                           'concentration_high_over_constant': None if high is None else high / constant,
                           'series_refs': _refs(record['quantities']['concentration_lowest'], record['quantities']['concentration_highest'], record['quantities']['kd'])})
    return _result('unknown', 'series_recorded_for_the_sheet', [])


def _protein_concentration(record, native):
    protein, kd = native['protein_nM'], native['kd_nM']
    below = record['facts']['protein_at_or_below_kd']
    tight = record['facts']['tight_binding_considered']
    refs = _refs(record['quantities']['protein_concentration'], record['quantities']['kd'], below, tight)
    handled = record['fit_model'] == 'quadratic' or tight['answer'] == 'yes'
    if protein is not None and kd is not None:
        native.update({'protein_over_kd': protein / kd, 'protein_refs': refs, 'tight_binding_handled': handled})
        return _result('unknown', 'protein_over_kd_recorded_for_the_sheet', [])
    if below['answer'] in ('yes', 'no'):
        above = below['answer'] == 'no'
    else:
        return _result('unknown', 'protein_or_kd_missing', [])
    if not above:
        return _result('supported', 'protein_at_or_below_kd', refs)
    if handled:
        return _result('supported', 'protein_above_kd_with_tight_binding_analysis', refs)
    return _result('conflicting', 'protein_above_kd_without_tight_binding_analysis', refs)


def _equilibrium(record, native):
    item = record['facts']['equilibrium_reached']
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        return _result(status, reason, item['source_refs'])
    minutes = native['incubation_min']
    if minutes is None:
        return _result('unknown', 'fact_unknown', [])
    native['incubation_refs'] = _refs(record['quantities']['incubation_time'])
    return _result('unknown', 'incubation_recorded_for_the_sheet', [])


def _quenching_mechanism(record, native):
    return _one_fact(record, 'quenching_is_static')


def _fit_model(record, native):
    model = record['fit_model']
    if model is None:
        return _result('unknown', 'fit_model_not_stated', [])
    refs = _refs(record['quantities']['kd'], record['quantities']['ksv'])
    if model == 'stern_volmer':
        return _result('conflicting', 'stern_volmer_fit_gives_ksv_not_kd', refs)
    # the model is a statement about how the reported constant was obtained: its quoted span is its support
    return _result('supported', 'model_stated', refs)


def _replicates(record, native):
    count = _value(record, 'replicate_count')
    independent = record['facts']['independent_titrations']
    refs = _refs(record['quantities']['replicate_count'], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', 'replicates_not_independent', refs)
    if count is None:
        return _result('unknown', 'replicate_count_or_independence_unknown', [])
    native.update({'replicate_count': count, 'replicate_independent': independent['answer'], 'replicate_refs': refs})
    return _result('unknown', 'replicate_count_recorded_for_the_sheet', [])


EVALUATORS = {'signal_amplitude': _signal_amplitude, 'excitation_selectivity': _excitation_selectivity, 'inner_filter': _inner_filter, 'dilution': _dilution, 'buffer_blank': _buffer_blank, 'ligand_fluorescence': _ligand_fluorescence, 'specificity_control': _specificity_control, 'photobleaching': _photobleaching, 'saturation': _saturation, 'concentration_series': _concentration_series, 'protein_concentration': _protein_concentration, 'equilibrium': _equilibrium, 'quenching_mechanism': _quenching_mechanism, 'fit_model': _fit_model, 'replicates': _replicates}


def grade_trp(record):
    """Grade one intrinsic fluorescence quenching titration record. Returns the criterion answers and native values."""
    nm = {name: _nm(record, name) for name in CONSTANTS}
    constant_name = next((name for name in CONSTANTS if nm[name] is not None), None)
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'], 'fit_model': record['fit_model'], 'change_direction': record['change_direction'], 'emission_shift_direction': record['emission_shift_direction'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'kd_nM': nm['kd'], 'constant_name': constant_name, 'constant_nM': None if constant_name is None else nm[constant_name], 'protein_nM': _nm(record, 'protein_concentration'), 'protein_over_kd': None, 'excitation_nm': _value(record, 'excitation_wavelength'), 'incubation_min': _minutes(record, 'incubation_time'), 'concentration_count': None, 'concentration_low_over_constant': None, 'concentration_high_over_constant': None, 'fluorescence_change_percent': None, 'change_refs': [], 'excitation_refs': [], 'ligand_absorbance': None, 'absorbance_refs': [], 'added_volume_percent': None, 'added_volume_refs': [], 'protein_refs': [], 'tight_binding_handled': None, 'count_refs': [], 'series_refs': [], 'incubation_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': [], }
    native['support'] = criterion_supports(record, TRP_CRITERIA)      # kept for the sheet: criterion -> supports of the stated fields it reads; the grader does not judge them
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'trp_quenching', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
