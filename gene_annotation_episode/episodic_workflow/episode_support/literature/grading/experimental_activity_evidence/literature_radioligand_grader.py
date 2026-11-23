"""Radioligand grader: judges ONE radioligand binding experiment (saturation binding for KD and Bmax, competition binding for IC50 and Ki by the Cheng-Prusoff equation) by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA or AlphaScreen graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_radioligand_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_radioligand_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration, each reading its unit
conversions by name from that file.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on);
``_result`` refuses to build one without them. Where only a fact with no span or a model with no reported constant would decide, the
criterion returns 'unknown' with a declared reason.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(percent_bound/percent_bound_refs, nonspecific_percent/nonspecific_fraction_refs, nonspecific_excess_ratio/nonspecific_excess_refs,
incubation_min/incubation_refs, concentration_count/concentration_count_refs and the span over the KD/concentration_span_refs,
radioligand_over_kd/radioligand_level_refs, hill_slope/hill_slope_refs, cheng_prusoff_fold/cheng_prusoff_refs,
replicate_count/replicate_independent/replicate_refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the radioligand
converter judges it. What stays with the grader is what a stated fact says (a stated 'no' is conflicting) and the choice among facts.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown;
else all 'not_applicable' -> not_applicable; else supported. ligand_depletion, nonspecific_fraction, nonspecific_excess, equilibrium,
radioligand_range, competition_radioligand_level, filter_binding, wash_dissociation, fit_model, hill_slope, cheng_prusoff and replicates
have their own rules (declared).

The binding constant of a record is the KD of the radioligand from a saturation experiment, else the Ki (native 'constant_name' says
which). The IC50 is a half-maximal concentration, not a dissociation constant: it serves the Cheng-Prusoff check and is never the
binding constant of the converter.

Support: native['support'] keeps, per criterion, the 'support' facts of the stated fields the criterion reads (from its declared 'reads';
literature_quote_support.criterion_supports). The grader only carries them; it never judges them and no status depends on them.

Native values retained: every record quantity as given, plus kd_nM, ki_nM, ic50_nM, constant_name, constant_nM, radioligand_nM,
nonspecific_ligand_nM, nonspecific_excess_ratio, incubation_min, dissociation_rate_per_min, depletion_corrected, concentration_count, concentration_low_over_kd,
concentration_high_over_kd, radioligand_over_kd, calculated_ki_nM, ki_over_calculated, the recorded facts and refs named above, preparations,
assay_format, radioligand_isotope, separation_method, preparation_type, spread_kind and fit_model.
The stated yes/no result (fact binding_detected) is kept as native 'interaction' ('detected', 'not_detected' or None),
with the spans that state it ('interaction_refs') and its quote support ('interaction_support'); the converter hands it to
the sheet as the experiment's stated result when the source gave no effect operand.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_radioligand_criteria import (
    MIN_PER_UNIT, NM_PER_UNIT, PER_MIN_PER_UNIT, RADIOLIGAND_CRITERIA)

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_radioligand_grade'
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the stated yes/no result of the fact binding_detected
CRITERIA = tuple(criterion['id'] for criterion in RADIOLIGAND_CRITERIA)
CONSTANTS = ('kd', 'ki')                      # the order in which the binding constant of a record is taken
REPORTED = ('kd', 'bmax', 'ki', 'ic50')       # the fitted values whose spans support a fit model
NO_FILTER = ('scintillation_proximity', 'centrifugation')


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


def _ligand_depletion(record, native):
    percent = _value(record, 'percent_bound')
    corrected = record['facts']['depletion_corrected']
    if percent is None:
        result = _one_fact(record, 'ligand_depletion_checked')
        if result['status'] == 'unknown' and corrected['answer'] == 'yes':
            return _result('supported', 'depletion_corrected', corrected['source_refs'])
        return result
    native.update({'percent_bound': percent, 'percent_bound_refs': _refs(record['quantities']['percent_bound']),
                   'depletion_corrected': corrected['answer'], 'depletion_corrected_refs': list(corrected['source_refs'])})
    return _result('unknown', 'percent_bound_recorded_for_the_sheet', [])


def _nonspecific_fraction(record, native):
    percent = _value(record, 'nonspecific_fraction')
    if percent is None:
        return _result('unknown', 'nonspecific_fraction_not_given', [])
    native.update({'nonspecific_percent': percent, 'nonspecific_fraction_refs': _refs(record['quantities']['nonspecific_fraction'])})
    return _result('unknown', 'nonspecific_fraction_recorded_for_the_sheet', [])


def _nonspecific_binding(record, native):
    return _one_fact(record, 'nonspecific_binding_determined')


def _nonspecific_excess(record, native):
    stated = _value(record, 'nonspecific_excess')
    ligand, own_kd, kd = native['nonspecific_ligand_nM'], _nm(record, 'nonspecific_ligand_kd'), native['kd_nM']
    same = record['facts']['nonspecific_ligand_is_unlabelled_radioligand']
    if stated is not None:
        native['nonspecific_excess_ratio'] = stated
        refs = _refs(record['quantities']['nonspecific_excess'])
    elif ligand is not None and own_kd is not None:                       # the excess is over the Kd of the unlabelled ligand itself
        native['nonspecific_excess_ratio'] = ligand / own_kd
        refs = _refs(record['quantities']['nonspecific_ligand_concentration'], record['quantities']['nonspecific_ligand_kd'])
    elif ligand is not None and kd is not None and same['answer'] == 'yes':      # the unlabelled ligand is the radioligand itself: its Kd is the radioligand's KD
        native['nonspecific_excess_ratio'] = ligand / kd
        refs = _refs(record['quantities']['nonspecific_ligand_concentration'], record['quantities']['kd'], same)
    else:
        return _result('unknown', 'excess_not_given', [])
    native['nonspecific_excess_refs'] = refs
    return _result('unknown', 'excess_recorded_for_the_sheet', [])


def _equilibrium(record, native):
    item = record['facts']['equilibrium_reached']
    rate = _scaled(record, 'dissociation_rate', PER_MIN_PER_UNIT)          # the off-rate of the radioligand: recorded only with the incubation, for the sheet
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        return _result(status, reason, item['source_refs'])
    if native['incubation_min'] is None:
        return _result('unknown', 'fact_unknown', [])
    native['incubation_refs'] = _refs(record['quantities']['incubation_time'])
    if rate is not None:
        native.update({'dissociation_rate_per_min': rate, 'dissociation_rate_refs': _refs(record['quantities']['dissociation_rate'])})
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
    spanned = not (kd is None or low is None or high is None)
    if spanned:
        native.update({'concentration_low_over_kd': low / kd, 'concentration_high_over_kd': high / kd, 'concentration_span_refs': _refs({'source_refs': refs}, record['quantities']['kd'])})
    if counted is None and not spanned:
        return _result('unknown', 'kd_or_series_missing', [])
    return _result('unknown', 'radioligand_range_recorded_for_the_sheet', [])


def _competition_radioligand_level(record, native):
    radioligand, kd = native['radioligand_nM'], native['kd_nM']
    if radioligand is None or kd is None:
        return _result('unknown', 'radioligand_concentration_or_kd_not_given', [])
    native['radioligand_over_kd'] = radioligand / kd
    native['radioligand_level_refs'] = _refs(record['quantities']['radioligand_concentration'], record['quantities']['kd'])
    return _result('unknown', 'radioligand_over_kd_recorded_for_the_sheet', [])


def _radioligand_quality(record, native):
    return _one_fact(record, 'radioligand_purity_checked')


def _filter_binding(record, native):
    result = _one_fact(record, 'filter_binding_checked')
    if result['status'] == 'unknown' and record['separation_method'] in NO_FILTER:
        return _result('not_applicable', 'separation_is_not_filtration', [])
    return result


def _wash_dissociation(record, native):
    result = _one_fact(record, 'wash_dissociation_considered')
    if result['status'] == 'unknown' and record['separation_method'] == 'scintillation_proximity':
        return _result('not_applicable', 'no_wash_in_scintillation_proximity', [])
    return result


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
        native.update({'cheng_prusoff_fold': max(ki, calculated) / min(ki, calculated),
                       'cheng_prusoff_refs': _refs(*(record['quantities'][name] for name in ('ki', 'ic50', 'radioligand_concentration', 'kd')))})
        return _result('unknown', 'cheng_prusoff_recorded_for_the_sheet', [])
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


EVALUATORS = {'ligand_depletion': _ligand_depletion, 'nonspecific_fraction': _nonspecific_fraction, 'nonspecific_binding': _nonspecific_binding, 'nonspecific_excess': _nonspecific_excess, 'equilibrium': _equilibrium, 'radioligand_range': _radioligand_range, 'competition_radioligand_level': _competition_radioligand_level, 'radioligand_quality': _radioligand_quality, 'filter_binding': _filter_binding, 'wash_dissociation': _wash_dissociation, 'nonlinear_fit': _nonlinear_fit, 'fit_model': _fit_model, 'hill_slope': _hill_slope, 'cheng_prusoff': _cheng_prusoff, 'replicates': _replicates}


def grade_radioligand(record):
    """Grade one radioligand binding experiment record. Returns the criterion answers and native values."""
    nm = {name: _nm(record, name) for name in ('kd', 'ki', 'ic50')}
    constant_name = next((name for name in CONSTANTS if nm[name] is not None), None)
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'assay_format': record['assay_format'], 'radioligand_isotope': record['radioligand_isotope'], 'separation_method': record['separation_method'], 'preparation_type': record['preparation_type'], 'spread_kind': record['spread_kind'], 'fit_model': record['fit_model'], 'choice_support': dict(record['choice_support']), 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'kd_nM': nm['kd'], 'ki_nM': nm['ki'], 'ic50_nM': nm['ic50'], 'constant_name': constant_name, 'constant_nM': None if constant_name is None else nm[constant_name], 'radioligand_nM': _nm(record, 'radioligand_concentration'), 'nonspecific_ligand_nM': _nm(record, 'nonspecific_ligand_concentration'), 'nonspecific_excess_ratio': None, 'incubation_min': _minutes(record, 'incubation_time'), 'concentration_count': None, 'concentration_low_over_kd': None, 'concentration_high_over_kd': None, 'radioligand_over_kd': None, 'calculated_ki_nM': None, 'ki_over_calculated': None, 'percent_bound': None, 'percent_bound_refs': [], 'depletion_corrected': None, 'depletion_corrected_refs': [], 'dissociation_rate_per_min': None, 'dissociation_rate_refs': [], 'nonspecific_percent': None, 'nonspecific_fraction_refs': [], 'nonspecific_excess_refs': [], 'incubation_refs': [], 'concentration_count_refs': [], 'concentration_span_refs': [], 'radioligand_level_refs': [], 'hill_slope': None, 'hill_slope_refs': [], 'cheng_prusoff_fold': None, 'cheng_prusoff_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    stated = record['facts']['binding_detected']      # the experiment's stated yes/no result: a fact kept for the sheet, read by no criterion
    known = stated['answer'] in INTERACTION
    native.update({'interaction': INTERACTION.get(stated['answer']), 'interaction_refs': list(stated['source_refs']) if known else [], 'interaction_support': stated['support'] if known else None})
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, RADIOLIGAND_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'radioligand', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
