"""SPA grader: judges ONE scintillation proximity assay (SPA) binding experiment (a radioligand binding to a target captured on scintillant beads, no separation or wash; saturation binding for KD and Bmax, competition binding for IC50 and Ki by the Cheng-Prusoff equation) by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen or radioligand graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_spa_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_spa_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(percent_bound, nonspecific_fraction_percent, nonspecific_excess_ratio, bead_only_percent, incubation_min, concentration_count and the span over the KD,
radioligand_over_kd, hill_slope, ki_over_calculated, replicate_count/replicate_independent, each with its *_refs) and returns 'unknown' with a reason
ending in '_recorded_for_the_sheet' and no refs; the SPA converter (literature_spa_converter.py) judges it. A fact stated as no stays the grader's
own conflicting.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on);
``_result`` refuses to build one without them. Where only a fact with no span or a model with no reported constant would decide, the
criterion returns 'unknown' with a declared reason.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown;
else all 'not_applicable' -> not_applicable; else supported. ligand_depletion, nonspecific_fraction, nonspecific_excess, bead_only_control,
equilibrium, radioligand_range, competition_radioligand_level, fit_model, hill_slope, cheng_prusoff and replicates have their own rules
(declared).

The binding constant of a record is the KD of the radioligand from a saturation experiment, else the Ki (native 'constant_name' says
which). The IC50 is a half-maximal concentration, not a dissociation constant: it serves the Cheng-Prusoff check and is never the
binding constant of the converter.

Native values retained: every record quantity as given, plus kd_nM, ki_nM, ic50_nM, constant_name, constant_nM, radioligand_nM,
nonspecific_ligand_nM, nonspecific_excess_ratio, incubation_min, settling_min, concentration_count, concentration_low_over_kd,
concentration_high_over_kd, radioligand_over_kd, calculated_ki_nM, ki_over_calculated, preparations, assay_format, radioligand_isotope,
bead_type, capture_method, preparation_type, counter, spread_kind and fit_model, and 'support': for each criterion the supports ('direct',
'implied', 'about_something_else') of the stated fields it reads, copied from the record and not judged here.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_spa_criteria import (
    MIN_PER_UNIT, NM_PER_UNIT, SPA_CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_spa_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in SPA_CRITERIA)
CONSTANTS = ('kd', 'ki')                      # the order in which the binding constant of a record is taken
REPORTED = ('kd', 'bmax', 'ki', 'ic50')       # the fitted values whose spans support a fit model


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _scaled(record, name, scale):
    value = _value(record, name)
    return None if value is None else value * scale[record['quantities'][name]['unit']]


def _nm(record, name):
    return _scaled(record, name, NM_PER_UNIT)


def _minutes(record, name):
    return _scaled(record, name, MIN_PER_UNIT)


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


def _percent_else_fact(record, native, quantity, fact_name, number_key, refs_key, handed):
    """A reported percent is recorded for the sheet to judge; with none, the fact decides."""
    percent = _value(record, quantity)
    if percent is None:
        return _one_fact(record, fact_name)
    native.update({number_key: percent, refs_key: _refs(record['quantities'][quantity])})
    return _result('unknown', handed, [])


def _ligand_depletion(record, native):
    return _percent_else_fact(record, native, 'percent_bound', 'ligand_depletion_checked', 'percent_bound', 'percent_bound_refs', 'percent_bound_recorded_for_the_sheet')


def _nonspecific_fraction(record, native):
    percent = _value(record, 'nonspecific_fraction')
    if percent is None:
        return _result('unknown', 'nonspecific_fraction_not_given', [])
    native.update({'nonspecific_fraction_percent': percent, 'nonspecific_fraction_refs': _refs(record['quantities']['nonspecific_fraction'])})
    return _result('unknown', 'nonspecific_fraction_recorded_for_the_sheet', [])


def _nonspecific_binding(record, native):
    return _one_fact(record, 'nonspecific_binding_determined')


def _nonspecific_excess(record, native):
    stated = _value(record, 'nonspecific_excess')
    ligand, kd = native['nonspecific_ligand_nM'], native['kd_nM']
    if stated is not None:
        native['nonspecific_excess_ratio'] = stated
        refs = _refs(record['quantities']['nonspecific_excess'])
    elif ligand is not None and kd is not None:
        native['nonspecific_excess_ratio'] = ligand / kd
        refs = _refs(record['quantities']['nonspecific_ligand_concentration'], record['quantities']['kd'])
    else:
        return _result('unknown', 'excess_not_given', [])
    native['nonspecific_excess_refs'] = refs
    return _result('unknown', 'excess_recorded_for_the_sheet', [])


def _nonproximity_signal(record, native):
    return _one_fact(record, 'nonproximity_signal_checked')


def _bead_only_control(record, native):
    return _percent_else_fact(record, native, 'bead_only_fraction', 'bead_only_control_done', 'bead_only_percent', 'bead_only_refs', 'bead_only_percent_recorded_for_the_sheet')


def _equilibrium(record, native):
    item = record['facts']['equilibrium_reached']
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        return _result(status, reason, item['source_refs'])
    if native['incubation_min'] is None:
        return _result('unknown', 'fact_unknown', [])
    native['incubation_refs'] = _refs(record['quantities']['incubation_time'])
    return _result('unknown', 'incubation_recorded_for_the_sheet', [])


def _radioligand_range(record, native):
    kd = native['kd_nM']
    series = record['concentration_series']
    values = series['value']
    counted = len(values) if values is not None else _value(record, 'titration_point_count')
    if counted is not None:
        native.update({'concentration_count': counted, 'concentration_count_refs': _refs(series, record['quantities']['titration_point_count'])})
    if values is not None:
        low, high = min(values) * NM_PER_UNIT[series['unit']], max(values) * NM_PER_UNIT[series['unit']]
        refs = _refs(series)
    else:
        low, high = _nm(record, 'radioligand_range_lowest'), _nm(record, 'radioligand_range_highest')
        refs = _refs(record['quantities']['radioligand_range_lowest'], record['quantities']['radioligand_range_highest'])
    if kd is None or low is None or high is None:
        # the count, when there is one, is still handed to the sheet; with neither a count nor a span nothing is recorded
        return _result('unknown', 'kd_or_series_missing' if counted is None else 'concentration_series_recorded_for_the_sheet', [])
    native.update({'concentration_low_over_kd': low / kd, 'concentration_high_over_kd': high / kd, 'concentration_span_refs': _refs({'source_refs': refs}, record['quantities']['kd'])})
    return _result('unknown', 'concentration_series_recorded_for_the_sheet', [])


def _competition_radioligand_level(record, native):
    radioligand, kd = native['radioligand_nM'], native['kd_nM']
    if radioligand is None or kd is None:
        return _result('unknown', 'radioligand_concentration_or_kd_not_given', [])
    native['radioligand_over_kd'] = radioligand / kd
    native['radioligand_over_kd_refs'] = _refs(record['quantities']['radioligand_concentration'], record['quantities']['kd'])
    return _result('unknown', 'radioligand_over_kd_recorded_for_the_sheet', [])


def _homogeneous_format(record, native):
    return _one_fact(record, 'homogeneous_no_wash_format')


def _radioligand_quality(record, native):
    return _one_fact(record, 'radioligand_purity_checked')


def _quench_interference(record, native):
    return _one_fact(record, 'quench_interference_checked')


def _bead_settling(record, native):
    return _one_fact(record, 'bead_settling_controlled')


def _nonlinear_fit(record, native):
    return _one_fact(record, 'nonlinear_fit_used')


def _fit_model(record, native):
    model, form = record['fit_model'], record['assay_format']
    if model is None:
        return _result('unknown', 'fit_model_not_stated', [])
    # the model is a statement about how the reported constants were obtained: their quoted spans are its support (the model
    # has no span of its own), and with no reported constant there is nothing to support either a verdict for or against it
    refs = _refs(*(record['quantities'][name] for name in REPORTED))
    if not refs:
        return _result('unknown', 'model_stated_without_a_reported_constant', [])
    if model == 'competitive_binding' and form == 'saturation':
        return _result('conflicting', 'competition_model_for_saturation', refs)
    return _result('supported', 'model_stated', refs)


def _hill_slope(record, native):
    slope = _value(record, 'hill_slope')
    if slope is None:
        return _result('unknown', 'hill_slope_not_given', [])
    native.update({'hill_slope': slope, 'hill_slope_refs': _refs(record['quantities']['hill_slope'])})
    return _result('unknown', 'hill_slope_recorded_for_the_sheet', [])


def _cheng_prusoff(record, native):
    item = record['facts']['cheng_prusoff_applied_with_own_kd']
    if item['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', item['source_refs'])
    ki, ic50, radioligand, kd = native['ki_nM'], native['ic50_nM'], native['radioligand_nM'], native['kd_nM']
    if None not in (ki, ic50, radioligand, kd):
        calculated = ic50 / (1 + radioligand / kd)
        native['calculated_ki_nM'] = calculated
        native['ki_over_calculated'] = ki / calculated
        native['cheng_prusoff_refs'] = _refs(*(record['quantities'][name] for name in ('ki', 'ic50', 'radioligand_concentration', 'kd')))
        return _result('unknown', 'cheng_prusoff_gap_recorded_for_the_sheet', [])
    status, reason = _shared_rule([item['answer']])
    if status == 'unknown' and record['assay_format'] == 'saturation' and ki is None and ic50 is None:
        return _result('not_applicable', 'no_competition_constant', [])
    return _result(status, reason, item['source_refs'])


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


EVALUATORS = {'ligand_depletion': _ligand_depletion, 'nonspecific_fraction': _nonspecific_fraction, 'nonspecific_binding': _nonspecific_binding, 'nonspecific_excess': _nonspecific_excess, 'nonproximity_signal': _nonproximity_signal, 'bead_only_control': _bead_only_control, 'equilibrium': _equilibrium, 'radioligand_range': _radioligand_range, 'competition_radioligand_level': _competition_radioligand_level, 'homogeneous_format': _homogeneous_format, 'radioligand_quality': _radioligand_quality, 'quench_interference': _quench_interference, 'bead_settling': _bead_settling, 'nonlinear_fit': _nonlinear_fit, 'fit_model': _fit_model, 'hill_slope': _hill_slope, 'cheng_prusoff': _cheng_prusoff, 'replicates': _replicates}


def grade_spa(record):
    """Grade one SPA binding experiment record. Returns the criterion answers and native values."""
    nm = {name: _nm(record, name) for name in ('kd', 'ki', 'ic50')}
    constant_name = next((name for name in CONSTANTS if nm[name] is not None), None)
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'assay_format': record['assay_format'], 'radioligand_isotope': record['radioligand_isotope'], 'bead_type': record['bead_type'], 'capture_method': record['capture_method'], 'preparation_type': record['preparation_type'], 'counter': record['counter'], 'spread_kind': record['spread_kind'], 'fit_model': record['fit_model'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'kd_nM': nm['kd'], 'ki_nM': nm['ki'], 'ic50_nM': nm['ic50'], 'constant_name': constant_name, 'constant_nM': None if constant_name is None else nm[constant_name], 'radioligand_nM': _nm(record, 'radioligand_concentration'), 'nonspecific_ligand_nM': _nm(record, 'nonspecific_ligand_concentration'), 'nonspecific_excess_ratio': None, 'incubation_min': _minutes(record, 'incubation_time'), 'settling_min': _minutes(record, 'settling_time'), 'concentration_count': None, 'concentration_low_over_kd': None, 'concentration_high_over_kd': None, 'radioligand_over_kd': None, 'calculated_ki_nM': None, 'ki_over_calculated': None, 'percent_bound': None, 'percent_bound_refs': [], 'nonspecific_fraction_percent': None, 'nonspecific_fraction_refs': [], 'nonspecific_excess_refs': [], 'bead_only_percent': None, 'bead_only_refs': [], 'incubation_refs': [], 'concentration_count_refs': [], 'concentration_span_refs': [], 'radioligand_over_kd_refs': [], 'hill_slope': None, 'hill_slope_refs': [], 'cheng_prusoff_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, SPA_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'spa', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
