"""MST grader: judges ONE MST (microscale thermophoresis) binding experiment (in solution, in capillaries) by MST's own standards.

Hand-built and private to MST (it shares no grading logic with the SPR, ITC, BLI, GCI, FP or FRET graders).
Deterministic; no model call, no store access.
Input: the record of one MST experiment (forms/.../literature_mst_record.py).
Output: for each MST criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_mst_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration, each reading its thresholds
by name from that file.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs (signal_to_noise/fnorm_amplitude/fnorm_noise/signal_refs,
labelled_over_kd/labelled_refs/tight_binding_handled, concentration_count/count_refs and the low/high over the constant/series_refs, incubation_min/incubation_refs, fhot_s/fhot_refs,
replicate_count/replicate_independent/replicate_refs, estimate_fold/estimate_refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the MST converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable):
any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. initial_fluorescence,
labelling_scheme and readout_window have their own rules (declared).

The reported constant of a series is the KD of a direct titration, else the Ki of
a competition, else the EC50 (native 'constant_name' says which).
The detected partner's concentration is judged against the KD only (a Ki is not
the detected partner's KD).

Native values retained: every record quantity as given, plus kd_nM, ki_nM,
ec50_nM, constant_name, constant_nM, labelled_nM, labelled_over_kd, fhot_s,
incubation_min, concentration_count, concentration_low_over_constant,
concentration_high_over_constant, preparations, assay_format, spread_kind,
fit_model, readout_signal, capillary_type and label_type.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_criteria import MIN_PER_UNIT, MST_CRITERIA, NM_PER_UNIT, S_PER_UNIT

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_mst_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in MST_CRITERIA)
CONSTANTS = ('kd', 'ki', 'ec50')       # the order in which a series' reported constant is taken
LABEL_FREE = 'label_free_intrinsic_fluorescence'


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _nm(record, name):
    value = _value(record, name)
    return None if value is None else value * NM_PER_UNIT[record['quantities'][name]['unit']]


def _minutes(record, name):
    value = _value(record, name)
    return None if value is None else value * MIN_PER_UNIT[record['quantities'][name]['unit']]


def _seconds(record, name):
    value = _value(record, name)
    return None if value is None else value * S_PER_UNIT[record['quantities'][name]['unit']]


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
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('mst_criterion_decided_without_support_refs:' + reason)
    return {'status': status, 'reason': reason, 'support_refs': refs if status in ('supported', 'conflicting') else []}


def _one_fact(record, name):
    item = record['facts'][name]
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, item['source_refs'])


def _signal_amplitude(record, native):
    noise, amplitude, fnorm_noise = _value(record, 'signal_to_noise'), _value(record, 'fnorm_amplitude'), _value(record, 'fnorm_noise')
    if noise is None and amplitude is None:
        return _result('unknown', 'signal_not_given', [])
    native.update({'signal_to_noise': noise, 'fnorm_amplitude': amplitude, 'fnorm_noise': fnorm_noise, 'signal_refs': _refs(record['quantities']['signal_to_noise'], record['quantities']['fnorm_amplitude'], record['quantities']['fnorm_noise'])})
    return _result('unknown', 'signal_recorded_for_the_sheet', [])


def _initial_fluorescence(record, native):
    consistent, checked = record['facts']['initial_fluorescence_consistent'], record['facts']['initial_fluorescence_checked']
    refs = _refs(consistent, checked)
    if consistent['answer'] == 'yes':
        return _result('supported', 'initial_fluorescence_consistent', refs)
    if consistent['answer'] == 'no':
        return _result('conflicting', 'initial_fluorescence_changes_with_titrant', refs)
    if checked['answer'] == 'no':
        return _result('conflicting', 'initial_fluorescence_not_checked', refs)
    if consistent['answer'] == 'not_applicable' and checked['answer'] == 'not_applicable':
        return _result('not_applicable', 'fact_not_applicable', [])
    return _result('unknown', 'initial_fluorescence_result_not_stated', [])


def _fluorescence_level(record, native):
    return _one_fact(record, 'fluorescence_intensity_in_range')


def _aggregation_adsorption(record, native):
    return _one_fact(record, 'aggregation_or_adsorption_checked')


def _labelled_concentration(record, native):
    labelled, kd = native['labelled_nM'], native['kd_nM']
    below = record['facts']['labelled_partner_at_or_below_kd']
    tight = record['facts']['tight_binding_considered']
    refs = _refs(record['quantities']['labelled_concentration'], record['quantities']['kd'], below, tight)
    handled = record['fit_model'] == 'quadratic' or tight['answer'] == 'yes'
    if labelled is not None and kd is not None:
        native.update({'labelled_over_kd': labelled / kd, 'labelled_refs': refs, 'tight_binding_handled': handled})
        return _result('unknown', 'labelled_over_kd_recorded_for_the_sheet', [])
    if below['answer'] in ('yes', 'no'):
        above = below['answer'] == 'no'
    else:
        return _result('unknown', 'labelled_or_kd_missing', [])
    if not above:
        return _result('supported', 'labelled_at_or_below_kd', refs)
    if handled:
        return _result('supported', 'labelled_above_kd_with_tight_binding_analysis', refs)
    return _result('conflicting', 'labelled_above_kd_without_tight_binding_analysis', refs)


def _concentration_series(record, native):
    constant = native['constant_nM']
    series = record['concentration_series']
    values = series['value']
    counted = len(values) if values is not None else _value(record, 'titration_point_count')
    if counted is None:
        return _result('unknown', 'constant_or_series_missing', [])
    native.update({'concentration_count': counted, 'count_refs': _refs(series, record['quantities']['titration_point_count'])})
    if constant is not None and values is not None:         # the span can only be judged from the list and the reported constant
        nm = [v * NM_PER_UNIT[series['unit']] for v in values]
        native.update({'concentration_low_over_constant': min(nm) / constant, 'concentration_high_over_constant': max(nm) / constant,
                       'series_refs': _refs(series, record['quantities'][native['constant_name']])})
    return _result('unknown', 'series_recorded_for_the_sheet', [])


def _equilibrium(record, native):
    item = record['facts']['equilibrium_reached']
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        return _result(status, reason, item['source_refs'])
    minutes = native['incubation_min']
    if minutes is None:
        return _result('unknown', 'fact_unknown', [])
    binding_constant = native['constant_name'] in ('kd', 'ki')      # an EC50 is not a binding constant: it gives the sheet no association scale
    native['incubation_constant_nM'] = native['constant_nM'] if binding_constant else None      # the fact the sheet needs next to the time: the reported KD (else Ki) in nM
    native['incubation_refs'] = _refs(record['quantities']['incubation_time'], *([record['quantities'][native['constant_name']]] if binding_constant else []))
    return _result('unknown', 'incubation_recorded_for_the_sheet', [])


def _labelling_scheme(record, native):
    harmless = record['facts']['labelling_does_not_alter_binding']
    kind = record['label_type']
    refs = _refs(harmless)
    if harmless['answer'] == 'no':
        return _result('conflicting', 'labelling_alters_binding', refs)
    if harmless['answer'] == 'yes':
        return _result('supported', 'labelling_shown_not_to_alter_binding', refs)
    if kind == LABEL_FREE:           # the label type is a choice that holds no span: a decision on it alone has no support
        return _result('unknown', 'label_free_stated_without_a_span', [])
    if kind is not None:
        return _result('unknown', 'label_not_shown_harmless', [])
    if harmless['answer'] == 'not_applicable':
        return _result('not_applicable', 'fact_not_applicable', [])
    return _result('unknown', 'labelling_not_stated', [])


def _specificity_control(record, native):
    return _one_fact(record, 'nonspecific_binding_checked')


def _readout_window(record, native):
    readout, time = record['readout_signal'], native['fhot_s']
    if readout == 'initial_fluorescence':
        return _result('not_applicable', 'initial_fluorescence_readout', [])
    if readout is None:
        return _result('unknown', 'readout_signal_not_stated', [])
    if readout == 't_jump':          # the readout is a choice that holds no span: a decision on it alone has no support
        return _result('unknown', 'temperature_jump_readout_stated_without_a_span', [])
    if time is None:
        return _result('unknown', 'fhot_time_not_stated', [])
    native['fhot_refs'] = _refs(record['quantities']['fhot_time'])
    return _result('unknown', 'fhot_time_recorded_for_the_sheet', [])


def _fit_model(record, native):
    model, form = record['fit_model'], record['assay_format']
    if model is None:
        return _result('unknown', 'fit_model_not_stated', [])
    # the model and the format are choices that hold no span: the quoted spans of the reported constants the model was fitted to are the
    # support of a decision on them (supported or conflicting), and with no reported constant there is no span to support it
    refs = _refs(*(record['quantities'][name] for name in CONSTANTS))
    if not refs:
        return _result('unknown', 'model_stated_without_a_reported_constant', [])
    if model == 'competitive_binding' and form == 'direct_titration':
        return _result('conflicting', 'competition_model_for_direct_titration', refs)
    if model in ('1:1', 'hill') and form == 'competition':
        return _result('conflicting', 'direct_model_for_competition', refs)
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


def _direct_vs_competition(record, native):
    kd, ki = native['kd_nM'], native['ki_nM']
    if kd is None or ki is None:
        if record['facts']['single_estimate_method']['answer'] == 'yes':
            return _result('not_applicable', 'single_estimate_method', record['facts']['single_estimate_method']['source_refs'])
        return _result('unknown', 'kd_or_ki_missing', [])
    native.update({'estimate_fold': max(kd, ki) / min(kd, ki), 'estimate_refs': _refs(record['quantities']['kd'], record['quantities']['ki'])})
    return _result('unknown', 'estimates_recorded_for_the_sheet', [])


EVALUATORS = {'signal_amplitude': _signal_amplitude, 'initial_fluorescence': _initial_fluorescence, 'fluorescence_level': _fluorescence_level, 'aggregation_adsorption': _aggregation_adsorption, 'labelled_concentration': _labelled_concentration, 'concentration_series': _concentration_series, 'equilibrium': _equilibrium, 'labelling_scheme': _labelling_scheme, 'specificity_control': _specificity_control, 'readout_window': _readout_window, 'fit_model': _fit_model, 'replicates': _replicates, 'direct_vs_competition': _direct_vs_competition}


def grade_mst(record):
    """Grade one MST experiment record. Returns the criterion answers and native values."""
    nm = {name: _nm(record, name) for name in CONSTANTS}
    constant_name = next((name for name in CONSTANTS if nm[name] is not None), None)
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'assay_format': record['assay_format'], 'spread_kind': record['spread_kind'], 'fit_model': record['fit_model'], 'readout_signal': record['readout_signal'], 'capillary_type': record['capillary_type'], 'label_type': record['label_type'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'kd_nM': nm['kd'], 'ki_nM': nm['ki'], 'ec50_nM': nm['ec50'], 'constant_name': constant_name, 'constant_nM': None if constant_name is None else nm[constant_name], 'labelled_nM': _nm(record, 'labelled_concentration'), 'labelled_over_kd': None, 'fhot_s': _seconds(record, 'fhot_time'), 'incubation_min': _minutes(record, 'incubation_time'), 'concentration_count': None, 'concentration_low_over_constant': None, 'concentration_high_over_constant': None, 'signal_to_noise': None, 'fnorm_amplitude': None, 'fnorm_noise': None, 'signal_refs': [], 'labelled_refs': [], 'tight_binding_handled': None, 'count_refs': [], 'series_refs': [], 'incubation_refs': [], 'incubation_constant_nM': None, 'fhot_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': [], 'estimate_fold': None, 'estimate_refs': []}
    native['support'] = criterion_supports(record, MST_CRITERIA)      # kept for the sheet: criterion -> supports of the stated fields it reads; the grader does not judge them
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'mst', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
