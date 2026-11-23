"""ELISA grader: judges ONE ELISA-style binding experiment (plate-based solid-phase binding, saturation titration or competition) by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp or FCS graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_elisa_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_elisa_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration, each reading its unit
conversions by name from that file.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on); ``_result``
refuses to build one without them. Where only a fact or a choice with no span would decide (the fit model with no reported constant), the
criterion returns 'unknown' with a declared reason.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(signal_over_background/signal_window_refs, plateau_absorbance/plateau_refs, incubation_min/incubation_refs,
concentration_count/concentration_count_refs and the span over the constant/concentration_span_refs, estimate_fold/estimate_refs,
replicate_count/replicate_independent/replicate_refs; added after the range review: the reader linear limit the paper states,
detector_linear_limit/linear_limit_refs; koff_per_s, wash_min/wash_loss_refs; the Cheng-Prusoff Ki ki_cheng_prusoff_nM from the IC50, the displaced ligand's
concentration and KD, with conversion_fold/conversion_refs against a reported Ki) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the ELISA
converter judges it. What stays with the grader is what a stated fact says (a stated 'no' is conflicting) and the choice among facts.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable):
any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. signal_window,
detector_range, equilibrium, concentration_series, fit_model,
direct_vs_competition and replicates have their own rules (declared).

The reported constant of a series is the apparent KD of a saturation titration, else the Ki, else the EC50, else the IC50 (native
'constant_name' says which). An EC50 or an IC50 is a half-maximal concentration, not a dissociation constant: it serves to judge
the span of the series and is never the binding constant of the converter.

Support: native['support'] keeps, per criterion, the 'support' facts of the stated fields the criterion reads (from its declared 'reads';
literature_quote_support.criterion_supports). The grader only carries them; it never judges them and no status depends on them.

Native values retained: every record quantity as given, plus kd_nM, ki_nM, ec50_nM, ic50_nM, constant_name, constant_nM,
signal_over_background, incubation_min, concentration_count, concentration_low_over_constant, concentration_high_over_constant,
the recorded facts and refs named above, preparations, assay_format, detection_format, spread_kind, fit_model, readout_signal, enzyme_conjugate and blocking_agent.
The stated yes/no result (fact binding_detected) is kept as native 'interaction' ('detected', 'not_detected' or None),
with the spans that state it ('interaction_refs') and its quote support ('interaction_support'); the converter hands it to
the sheet as the experiment's stated result when the source gave no effect operand.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_elisa_criteria import ELISA_CRITERIA, MIN_PER_UNIT, NM_PER_UNIT

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_elisa_grade'
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the stated yes/no result of the fact binding_detected
CRITERIA = tuple(criterion['id'] for criterion in ELISA_CRITERIA)
CONSTANTS = ('kd', 'ki', 'ec50', 'ic50')       # the order in which a series' reported constant is taken


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


def _signal_window(record, native):
    maximum, background = _value(record, 'signal_maximum'), _value(record, 'signal_background')
    if maximum is None or background is None:
        return _result('unknown', 'signal_or_background_not_given', [])
    native['signal_over_background'] = maximum / background
    native['signal_window_refs'] = _refs(record['quantities']['signal_maximum'], record['quantities']['signal_background'])
    return _result('unknown', 'signal_window_recorded_for_the_sheet', [])


def _detector_range(record, native):
    item = record['facts']['signal_in_linear_range']
    limit = _value(record, 'detector_linear_limit')
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        return _result(status, reason, item['source_refs'])
    maximum = _value(record, 'signal_maximum')
    if maximum is None:
        return _result('unknown', 'fact_unknown', [])
    native.update({'plateau_absorbance': maximum, 'plateau_refs': _refs(record['quantities']['signal_maximum']),
                   'detector_linear_limit': limit, 'linear_limit_refs': _refs(record['quantities']['detector_linear_limit'])})
    return _result('unknown', 'plateau_recorded_for_the_sheet', [])


def _saturation(record, native):
    return _one_fact(record, 'saturation_reached')


def _blank_subtraction(record, native):
    return _one_fact(record, 'blank_subtracted')


def _specificity_control(record, native):
    return _one_fact(record, 'nonspecific_binding_checked')


def _wash_dissociation(record, native):
    item = record['facts']['wash_dissociation_considered']
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        return _result(status, reason, item['source_refs'])
    koff, minutes = _value(record, 'koff'), _minutes(record, 'wash_duration')
    if koff is None or minutes is None:
        return _result('unknown', 'fact_unknown', [])
    native.update({'koff_per_s': koff, 'wash_min': minutes, 'wash_loss_refs': _refs(record['quantities']['koff'], record['quantities']['wash_duration'])})
    return _result('unknown', 'wash_loss_recorded_for_the_sheet', [])


def _equilibrium(record, native):
    item = record['facts']['equilibrium_reached']
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        return _result(status, reason, item['source_refs'])
    if native['incubation_min'] is None:
        return _result('unknown', 'fact_unknown', [])
    native['incubation_refs'] = _refs(record['quantities']['incubation_time'])
    if native['constant_name'] is not None:
        native['constant_refs'] = _refs(record['quantities'][native['constant_name']])      # the constant the sheet scales the incubation by
    return _result('unknown', 'incubation_recorded_for_the_sheet', [])


def _avidity(record, native):
    return _one_fact(record, 'avidity_excluded')


def _coated_protein_activity(record, native):
    return _one_fact(record, 'coated_protein_active')


def _detection_interference(record, native):
    return _one_fact(record, 'detection_does_not_interfere')


def _concentration_series(record, native):
    constant = native['constant_nM']
    series = record['concentration_series']
    values = series['value']
    counted = len(values) if values is not None else _value(record, 'titration_point_count')
    refs = _refs(series, record['quantities']['titration_point_count'])
    if counted is None:
        return _result('unknown', 'constant_or_series_missing', [])
    native.update({'concentration_count': counted, 'concentration_count_refs': refs})
    if constant is not None and values is not None:
        nm = [v * NM_PER_UNIT[series['unit']] for v in values]
        native.update({'concentration_low_over_constant': min(nm) / constant, 'concentration_high_over_constant': max(nm) / constant,
                       'concentration_span_refs': _refs(series, record['quantities'][native['constant_name']])})
    return _result('unknown', 'concentration_series_recorded_for_the_sheet', [])


def _fit_model(record, native):
    model, form = record['fit_model'], record['assay_format']
    if model is None:
        return _result('unknown', 'fit_model_not_stated', [])
    # the model and the format are choices that hold no span: the quoted spans of the reported constants the model was fitted to are the
    # support of a decision on them (supported or conflicting), and with no reported constant there is no span to support it
    refs = _refs(*(record['quantities'][name] for name in CONSTANTS))
    if not refs:
        return _result('unknown', 'model_stated_without_a_reported_constant', [])
    if model == 'competitive_binding' and form == 'saturation_titration':
        return _result('conflicting', 'competition_model_for_saturation_titration', refs)
    if model in ('1:1', 'hill') and form == 'competition':
        return _result('conflicting', 'direct_model_for_competition', refs)
    return _result('supported', 'model_stated', refs)


def _direct_vs_competition(record, native):
    quantities = record['quantities']
    kd, ki = native['kd_nM'], native['ki_nM']
    ic50, tracer, tracer_kd = native['ic50_nM'], native['tracer_concentration_nM'], native['tracer_kd_nM']
    derived, derived_refs = None, []
    if ic50 is not None and tracer is not None and tracer_kd is not None:
        # Cheng-Prusoff: the Ki that the IC50 gives for a competitor of a ligand at a stated concentration with a stated KD (arithmetic of stated numbers).
        derived = ic50 / (1 + tracer / tracer_kd)
        derived_refs = _refs(quantities['ic50'], quantities['tracer_concentration'], quantities['tracer_kd'])
        native.update({'ki_cheng_prusoff_nM': derived, 'cheng_prusoff_refs': derived_refs})
    if kd is not None and (ki is not None or derived is not None):
        other = ki if ki is not None else derived
        native.update({'estimate_fold': max(kd, other) / min(kd, other),
                       'estimate_refs': _refs(quantities['kd'], quantities['ki']) if ki is not None else _refs(quantities['kd'], {'source_refs': derived_refs})})
    if ki is not None and derived is not None:
        native.update({'conversion_fold': max(ki, derived) / min(ki, derived), 'conversion_refs': _refs(quantities['ki'], {'source_refs': derived_refs})})
    if native['estimate_fold'] is None and native['conversion_fold'] is None:
        if record['facts']['single_estimate_method']['answer'] == 'yes':
            return _result('not_applicable', 'single_estimate_method', record['facts']['single_estimate_method']['source_refs'])
        return _result('unknown', 'kd_or_ki_missing', [])
    return _result('unknown', 'estimates_recorded_for_the_sheet', [])


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


EVALUATORS = {'signal_window': _signal_window, 'detector_range': _detector_range, 'saturation': _saturation, 'blank_subtraction': _blank_subtraction, 'specificity_control': _specificity_control, 'wash_dissociation': _wash_dissociation, 'equilibrium': _equilibrium, 'avidity': _avidity, 'coated_protein_activity': _coated_protein_activity, 'detection_interference': _detection_interference, 'concentration_series': _concentration_series, 'fit_model': _fit_model, 'direct_vs_competition': _direct_vs_competition, 'replicates': _replicates}


def grade_elisa(record):
    """Grade one ELISA-style binding experiment record. Returns the criterion answers and native values."""
    nm = {name: _nm(record, name) for name in CONSTANTS}
    constant_name = next((name for name in CONSTANTS if nm[name] is not None), None)
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'assay_format': record['assay_format'], 'detection_format': record['detection_format'], 'spread_kind': record['spread_kind'], 'fit_model': record['fit_model'], 'readout_signal': record['readout_signal'], 'enzyme_conjugate': record['enzyme_conjugate'], 'blocking_agent': record['blocking_agent'], 'choice_support': dict(record['choice_support']), 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'kd_nM': nm['kd'], 'ki_nM': nm['ki'], 'ec50_nM': nm['ec50'], 'ic50_nM': nm['ic50'], 'tracer_concentration_nM': _nm(record, 'tracer_concentration'), 'tracer_kd_nM': _nm(record, 'tracer_kd'), 'ki_cheng_prusoff_nM': None, 'cheng_prusoff_refs': [], 'conversion_fold': None, 'conversion_refs': [], 'detector_linear_limit': None, 'linear_limit_refs': [], 'koff_per_s': None, 'wash_min': None, 'wash_loss_refs': [], 'constant_name': constant_name, 'constant_nM': None if constant_name is None else nm[constant_name], 'signal_over_background': None, 'incubation_min': _minutes(record, 'incubation_time'), 'concentration_count': None, 'concentration_low_over_constant': None, 'concentration_high_over_constant': None, 'signal_window_refs': [], 'plateau_absorbance': None, 'plateau_refs': [], 'incubation_refs': [], 'constant_refs': [], 'concentration_count_refs': [], 'concentration_span_refs': [], 'estimate_fold': None, 'estimate_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    stated = record['facts']['binding_detected']      # the experiment's stated yes/no result: a fact kept for the sheet, read by no criterion
    known = stated['answer'] in INTERACTION
    native.update({'interaction': INTERACTION.get(stated['answer']), 'interaction_refs': list(stated['source_refs']) if known else [], 'interaction_support': stated['support'] if known else None})
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, ELISA_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'elisa', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
