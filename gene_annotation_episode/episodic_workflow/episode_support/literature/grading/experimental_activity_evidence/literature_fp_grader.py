"""FP grader: judges ONE fluorescence polarization / anisotropy binding experiment by FP's own standards.

Hand-built and private to FP (it shares no grading logic with the SPR, ITC, BLI or GCI graders).
Deterministic; no model call, no store access.
Input: the record of one FP experiment (forms/.../literature_fp_record.py).
Output: for each FP criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_fp_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration, each reading its thresholds
by name from that file.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs (window_mP/window_refs,
tracer_over_kd/tracer_refs/tight_binding_handled, concentration_count and the low/high over the constant/series_refs, incubation_min/incubation_refs,
intensity_change_percent/intensity_change_refs, replicate_count/replicate_independent/replicate_refs, estimate_fold/estimate_refs) and returns 'unknown' with a
reason ending in '_recorded_for_the_sheet'; the FP converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable):
any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. The criterion that asks
whether EITHER of two controls was done (specificity_control) takes a 'yes' of
either as enough, and otherwise uses the shared rule.

The reported constant is the KD of a direct titration; when the record has no
KD it is the Ki of a competition experiment (native 'constant_name' says
which). The concentration series is judged against it; the tracer
concentration is judged against the KD only (a Ki is not the tracer's KD).

Added after the range review: signal_noise (mP) is recorded with the window (window_noise_mP, window_noise_refs); the intensity change keeps its stated
direction (intensity_change_direction, 'increase' or 'decrease' or None); a competitor series is read against the IC50 when it is given
(series_reference 'ic50', else the constant's name); series_kind and ic50_nM are retained.

Native values retained: every record quantity as given, plus kd_nM, ki_nM,
constant_nM, constant_name, tracer_nM, tracer_over_kd, signal_minimum_mP,
signal_maximum_mP, window_mP, incubation_min, concentration_count,
concentration_low_over_constant, concentration_high_over_constant,
preparations, assay_format, spread_kind, fit_model and plate_type, and 'support': for each criterion the supports ('direct', 'implied',
'about_something_else') of the stated fields it reads, kept for the sheet (the grader does not judge them).
The stated yes/no result (fact binding_detected) is kept as native 'interaction' ('detected', 'not_detected' or None),
with the spans that state it ('interaction_refs') and its quote support ('interaction_support'); the converter hands it to
the sheet as the experiment's stated result when the source gave no binding constant.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_criteria import ANISOTROPY_FACTOR, ANISOTROPY_OFFSET, FP_CRITERIA, MIN_PER_UNIT, MP_PER_POLARIZATION, NM_PER_UNIT

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_fp_grade_v1'
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the stated yes/no result of the fact binding_detected
CRITERIA = tuple(criterion['id'] for criterion in FP_CRITERIA)


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _nm(record, name):
    value = _value(record, name)
    return None if value is None else value * NM_PER_UNIT[record['quantities'][name]['unit']]


def _mp(record, name):
    """A signal end in mP; an anisotropy r is converted to polarization P = F r / (O + r) first."""
    value = _value(record, name)
    if value is None:
        return None
    if record['quantities'][name]['unit'] == 'r':
        return MP_PER_POLARIZATION * ANISOTROPY_FACTOR * value / (ANISOTROPY_OFFSET + value)
    return value


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


def _assay_window(record, native):
    low, high = native['signal_minimum_mP'], native['signal_maximum_mP']
    if low is None or high is None:
        return _result('unknown', 'minimum_or_maximum_missing', [])
    native.update({'window_mP': high - low, 'window_refs': _refs(record['quantities']['signal_minimum'], record['quantities']['signal_maximum'])})
    if native['window_noise_mP'] is not None:      # the paper's own noise of the reads, so the sheet can judge the window against it
        native['window_noise_refs'] = _refs(record['quantities']['signal_noise'])
    return _result('unknown', 'window_recorded_for_the_sheet', [])


def _free_probe_baseline(record, native):
    return _one_fact(record, 'free_probe_baseline_measured')


def _tracer_concentration(record, native):
    tracer, kd = native['tracer_nM'], native['kd_nM']
    below = record['facts']['tracer_at_or_below_kd']
    tight = record['facts']['tight_binding_considered']
    refs = _refs(record['quantities']['tracer_concentration'], record['quantities']['kd'], below, tight)
    handled = record['fit_model'] == 'quadratic' or tight['answer'] == 'yes'
    if tracer is not None and kd is not None:
        native.update({'tracer_over_kd': tracer / kd, 'tracer_refs': refs, 'tight_binding_handled': handled})
        return _result('unknown', 'tracer_over_kd_recorded_for_the_sheet', [])
    if below['answer'] in ('yes', 'no'):
        above = below['answer'] == 'no'
    else:
        return _result('unknown', 'tracer_or_kd_missing', [])
    if not above:
        return _result('supported', 'tracer_at_or_below_kd', refs)
    if handled:
        return _result('supported', 'tracer_above_kd_with_tight_binding_analysis', refs)
    return _result('conflicting', 'tracer_above_kd_without_tight_binding_analysis', refs)


def _concentration_series(record, native):
    # The series is read against the IC50 when it is the competitor series of a competition and the IC50 is given (a competition curve is centred on
    # the IC50, not on the Ki); otherwise against the reported constant.
    on_ic50 = record['series_kind'] == 'competitor' and native['ic50_nM'] is not None
    constant = native['ic50_nM'] if on_ic50 else native['constant_nM']
    series = record['concentration_series']
    values = series['value']
    if constant is None or values is None:
        return _result('unknown', 'constant_or_series_missing', [])
    scale = NM_PER_UNIT[series['unit']]
    nm = [v * scale for v in values]
    reference = 'ic50' if on_ic50 else native['constant_name']
    native.update({'concentration_count': len(nm), 'concentration_low_over_constant': min(nm) / constant, 'concentration_high_over_constant': max(nm) / constant,
                   'series_reference': reference, 'series_refs': _refs(series, record['quantities'][reference])})
    return _result('unknown', 'series_recorded_for_the_sheet', [])


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


def _intensity_change(record, native):
    item = record['facts']['intensity_change_checked']
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        return _result(status, reason, item['source_refs'])
    change = _value(record, 'total_intensity_change')
    if change is None:
        return _result('unknown', 'fact_unknown', [])
    native.update({'intensity_change_percent': change, 'intensity_change_refs': _refs(record['quantities']['total_intensity_change'])})
    return _result('unknown', 'intensity_change_recorded_for_the_sheet', [])


def _specificity_control(record, native):
    names = ('nonspecific_binding_checked', 'unlabelled_competitor_displaces')
    answers = _answers(record, names)
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'specificity_control_stated', refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _surface_adsorption(record, native):
    return _one_fact(record, 'surface_adsorption_prevented')


def _fit_model(record, native):
    model, form = record['fit_model'], record['assay_format']
    if model is None:
        return _result('unknown', 'fit_model_not_stated', [])
    if model == 'competitive_binding' and form == 'direct_titration':
        return _result('conflicting', 'competition_model_for_direct_titration', [])
    if model in ('1:1', 'hill') and form == 'competition':
        return _result('conflicting', 'direct_model_for_competition', [])
    # the model is a statement about how the reported constants were obtained: their quoted spans are its support
    return _result('supported', 'model_stated', _refs(record['quantities']['kd'], record['quantities']['ki']))


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


def _direct_vs_competition(record, native):
    kd, ki = native['kd_nM'], native['ki_nM']
    if kd is None or ki is None:
        if record['facts']['single_estimate_method']['answer'] == 'yes':
            return _result('not_applicable', 'single_estimate_method', record['facts']['single_estimate_method']['source_refs'])
        return _result('unknown', 'kd_or_ki_missing', [])
    native.update({'estimate_fold': max(kd, ki) / min(kd, ki), 'estimate_refs': _refs(record['quantities']['kd'], record['quantities']['ki'])})
    return _result('unknown', 'estimates_recorded_for_the_sheet', [])


EVALUATORS = {'assay_window': _assay_window, 'free_probe_baseline': _free_probe_baseline, 'tracer_concentration': _tracer_concentration, 'concentration_series': _concentration_series, 'equilibrium': _equilibrium, 'intensity_change': _intensity_change, 'specificity_control': _specificity_control, 'surface_adsorption': _surface_adsorption, 'fit_model': _fit_model, 'replicates': _replicates, 'direct_vs_competition': _direct_vs_competition}


def grade_fp(record):
    """Grade one FP experiment record. Returns the criterion answers and native values."""
    kd, ki = _nm(record, 'kd'), _nm(record, 'ki')
    constant_name = 'kd' if kd is not None else 'ki' if ki is not None else None
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'assay_format': record['assay_format'], 'spread_kind': record['spread_kind'], 'fit_model': record['fit_model'], 'plate_type': record['plate_type'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'kd_nM': kd, 'ki_nM': ki, 'constant_name': constant_name, 'constant_nM': kd if kd is not None else ki, 'ic50_nM': _nm(record, 'ic50'), 'series_kind': record['series_kind'], 'series_reference': None, 'intensity_change_direction': record['intensity_change_direction'], 'window_noise_mP': _value(record, 'signal_noise'), 'window_noise_refs': [], 'tracer_nM': _nm(record, 'tracer_concentration'), 'tracer_over_kd': None, 'signal_minimum_mP': _mp(record, 'signal_minimum'), 'signal_maximum_mP': _mp(record, 'signal_maximum'), 'window_mP': None, 'incubation_min': _minutes(record, 'incubation_time'), 'concentration_count': None, 'concentration_low_over_constant': None, 'concentration_high_over_constant': None, 'window_refs': [], 'tracer_refs': [], 'tight_binding_handled': None, 'series_refs': [], 'incubation_refs': [], 'intensity_change_percent': None, 'intensity_change_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': [], 'estimate_fold': None, 'estimate_refs': []}
    native['support'] = criterion_supports(record, FP_CRITERIA)      # kept for the sheet: the grader does not judge it
    stated = record['facts']['binding_detected']      # the experiment's stated yes/no result: a fact kept for the sheet, read by no criterion
    known = stated['answer'] in INTERACTION
    native.update({'interaction': INTERACTION.get(stated['answer']), 'interaction_refs': list(stated['source_refs']) if known else [], 'interaction_support': stated['support'] if known else None})
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'fp', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
