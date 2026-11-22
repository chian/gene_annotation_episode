"""Product_immunodetection grader: judges ONE antibody-detected enzyme reaction by its own standards.

Hand-built and private to product_immunodetection. Deterministic; no model call, no store access.
Input: the record of one reaction (forms/.../literature_product_immunodetection_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_product_immunodetection_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(converted_percent, enzyme_over_substrate_plus_km, the series count and its two ratios over the Km, standard_point_count, z_prime,
signal_to_background, replicate_count, each with its refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs;
the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact activity_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw product above its own control. It is recorded in native as 'activity' with its refs and its support (class
decision of 2026-11-21: 'interaction_detected' reads "activity detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the two series and the preparations, spread_kind, and converted_percent,
enzyme_over_substrate_plus_km, concentration_count, concentration_low_over_km, concentration_high_over_km, standard_point_count, z_prime,
signal_to_background, replicate_count, replicate_independent, activity, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_product_immunodetection_criteria import PRODUCT_IMMUNODETECTION_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_product_immunodetection_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in PRODUCT_IMMUNODETECTION_CRITERIA)
ACTIVITY = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact activity_detected_above_control
AMOUNT_BASED = ('catalytic_efficiency', 'turnover', 'specific_activity')   # the effect quantities that are amounts of product per time (a fold over the control is not)


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


def _spontaneous_reaction_control(record, native):
    names = ('no_enzyme_control', 'inactive_enzyme_control')
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'spontaneous_reaction_control_stated', refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _cofactor_dependence(record, native):
    return _one_fact(record, 'no_cofactor_control')


def _substrate_independent_signal(record, native):
    return _one_fact(record, 'no_substrate_control')


def _antibody_product_specificity(record, native):
    return _one_fact(record, 'antibody_specific_for_product')


def _enzyme_dependence(record, native):
    return _one_fact(record, 'rate_proportional_to_enzyme')


def _product_identity(record, native):
    return _one_fact(record, 'product_identified')


def _product_calibration(record, native):
    curve = record['facts']['product_standard_curve']
    series = record['standard_series']
    amounts = [record['quantities'][name] for name in AMOUNT_BASED if _value(record, name) is not None]
    if curve['answer'] == 'no':
        if amounts:
            return _result('conflicting', 'standard_curve_not_used_for_an_amount_based_quantity', _refs(curve, *amounts))
        return _result('not_applicable', 'relative_readout_needs_no_standard_curve', [])
    if series['status'] == 'point':
        native.update({'standard_point_count': len(series['value']), 'standard_refs': _refs(series)})
        return _result('unknown', 'standard_series_recorded_for_the_sheet', [])
    if curve['answer'] == 'yes':
        return _result('supported', 'product_standard_curve_stated', curve['source_refs'])
    if curve['answer'] == 'not_applicable':
        return _result('not_applicable', 'fact_not_applicable', [])
    return _result('unknown', 'product_standard_curve_not_stated', [])


def _assay_window(record, native):
    z_prime, background = _value(record, 'z_prime'), _value(record, 'signal_to_background')
    if z_prime is None and background is None:
        return _result('unknown', 'assay_window_not_stated', [])
    native.update({'z_prime': z_prime, 'signal_to_background': background, 'window_refs': _refs(record['quantities']['z_prime'], record['quantities']['signal_to_background'])})
    return _result('unknown', 'assay_window_recorded_for_the_sheet', [])


def _signal_range(record, native):
    return _one_fact(record, 'signal_within_standard_range')


def _initial_rate_regime(record, native):
    linear = record['facts']['linear_in_time']
    converted = _value(record, 'substrate_converted_percent')
    refs = _refs(record['quantities']['substrate_converted_percent'], linear)
    if linear['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if converted is not None:
        native.update({'converted_percent': converted, 'converted_refs': refs})
        return _result('unknown', 'converted_recorded_for_the_sheet', [])
    if linear['answer'] == 'yes':
        return _result('supported', 'linear_in_time_stated', refs)
    return _result('unknown', 'rate_regime_not_stated', [])


def _enzyme_substrate_ratio(record, native):
    enzyme, substrate, km = _nm(record, 'enzyme_concentration'), _nm(record, 'substrate_concentration'), _nm(record, 'km')
    if enzyme is None or substrate is None or km is None:
        return _result('unknown', 'enzyme_substrate_or_km_missing', [])
    native['enzyme_over_substrate_plus_km'] = enzyme / (substrate + km)
    native['enzyme_ratio_refs'] = _refs(*(record['quantities'][n] for n in ('enzyme_concentration', 'substrate_concentration', 'km')))
    return _result('unknown', 'enzyme_ratio_recorded_for_the_sheet', [])


def _substrate_range(record, native):
    km = native['km_nM']
    series = record['concentration_series']
    values = series['value']
    if km is None or values is None:
        return _result('unknown', 'km_or_series_missing', [])
    scale = _SCALES[series['unit']]
    nm = [v * scale for v in values]
    native['concentration_count'] = len(nm)
    native['concentration_low_over_km'] = min(nm) / km
    native['concentration_high_over_km'] = max(nm) / km
    native['concentration_refs'] = _refs(series, record['quantities']['km'])
    return _result('unknown', 'substrate_series_recorded_for_the_sheet', [])


def _active_enzyme_amount(record, native):
    return _one_fact(record, 'active_site_concentration_determined')


def _replicates(record, native):
    count = _value(record, 'replicate_count')
    independent = record['facts']['independent_replicates']
    refs = _refs(record['quantities']['replicate_count'], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', 'replicates_not_independent', refs)
    if count is None:
        return _result('unknown', 'replicate_count_or_independence_unknown', [])
    native.update({'replicate_count': count, 'replicate_independent': independent['answer'], 'replicate_refs': refs})
    return _result('unknown', 'replicate_count_recorded_for_the_sheet', [])


def _native_reaction(record, native):
    return _one_fact(record, 'native_substrate')


def _purified_enzyme(record, native):
    return _one_fact(record, 'purified_enzyme')


EVALUATORS = {'spontaneous_reaction_control': _spontaneous_reaction_control, 'cofactor_dependence': _cofactor_dependence, 'substrate_independent_signal': _substrate_independent_signal,
              'antibody_product_specificity': _antibody_product_specificity, 'enzyme_dependence': _enzyme_dependence, 'product_identity': _product_identity,
              'product_calibration': _product_calibration, 'assay_window': _assay_window, 'signal_range': _signal_range, 'initial_rate_regime': _initial_rate_regime,
              'enzyme_substrate_ratio': _enzyme_substrate_ratio, 'substrate_range': _substrate_range, 'active_enzyme_amount': _active_enzyme_amount, 'replicates': _replicates,
              'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_product_immunodetection(record):
    """Grade one antibody-detected enzyme reaction record. Returns the criterion answers and native values."""
    detected = record['facts']['activity_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'standard_series': dict(record['standard_series']),
              'km_nM': _nm(record, 'km'),
              'activity': ACTIVITY.get(detected['answer']), 'activity_refs': list(detected['source_refs']) if detected['answer'] in ACTIVITY else [], 'activity_support': detected['support'],
              'converted_percent': None, 'converted_refs': [], 'enzyme_over_substrate_plus_km': None, 'enzyme_ratio_refs': [], 'concentration_count': None, 'concentration_low_over_km': None, 'concentration_high_over_km': None,
              'concentration_refs': [], 'standard_point_count': None, 'standard_refs': [], 'z_prime': None, 'signal_to_background': None, 'window_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, PRODUCT_IMMUNODETECTION_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'product_immunodetection', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
