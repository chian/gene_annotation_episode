"""Chromatographic grader: judges ONE discontinuous chromatographic enzyme assay by its own standards.

Hand-built and private to chromatographic. Deterministic; no model call, no store access.
Input: the record of one assay (forms/.../literature_chromatographic_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_chromatographic_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(consumed_percent, enzyme_over_substrate_plus_km, product_over_detection_limit, time_point_count, the series count and its two ratios over
the Km, replicate_count, each with its refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs; the
converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact activity_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw product above its own control. It is recorded in native as 'activity' with its refs and its support (class
decision of 2026-11-21: 'interaction_detected' reads "activity detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the series and the preparations, spread_kind, and consumed_percent, enzyme_over_substrate_plus_km,
product_over_detection_limit, time_point_count, concentration_count, concentration_low_over_km, concentration_high_over_km, replicate_count,
replicate_independent, activity, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_chromatographic_criteria import CHROMATOGRAPHIC_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_chromatographic_grade'
CRITERIA = tuple(criterion['id'] for criterion in CHROMATOGRAPHIC_CRITERIA)
ACTIVITY = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact activity_detected_above_control


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


def _either_fact(record, names, supported_reason):
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', supported_reason, refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _spontaneous_reaction_control(record, native):
    return _either_fact(record, ('no_enzyme_control', 'inactive_enzyme_control'), 'spontaneous_reaction_control_stated')


def _substrate_independent_signal(record, native):
    return _one_fact(record, 'no_substrate_control')


def _starting_material_blank(record, native):
    return _one_fact(record, 'zero_time_sample')


def _enzyme_dependence(record, native):
    return _one_fact(record, 'rate_proportional_to_enzyme')


def _product_identity(record, native):
    return _either_fact(record, ('product_matches_authentic_standard', 'product_identified_by_mass'), 'product_identity_stated')


def _calibration_standard(record, native):
    return _one_fact(record, 'calibration_with_authentic_standard')


def _calibration_range(record, native):
    return _one_fact(record, 'within_calibrated_range')


def _product_over_detection_limit(record, native):
    product, limit = _nm(record, 'product_concentration'), _nm(record, 'detection_limit')
    if product is None or limit is None:
        return _result('unknown', 'product_or_detection_limit_missing', [])
    native['product_over_detection_limit'] = product / limit
    native['detection_refs'] = _refs(record['quantities']['product_concentration'], record['quantities']['detection_limit'])
    return _result('unknown', 'detection_ratio_recorded_for_the_sheet', [])


def _internal_standard(record, native):
    return _one_fact(record, 'internal_standard_used')


def _reaction_stopped(record, native):
    return _one_fact(record, 'reaction_quenched')


def _time_points(record, native):
    count = _value(record, 'time_point_count')
    if count is None:
        return _result('unknown', 'time_points_not_stated', [])
    native.update({'time_point_count': count, 'time_point_refs': _refs(record['quantities']['time_point_count'])})
    return _result('unknown', 'time_points_recorded_for_the_sheet', [])


def _initial_rate_regime(record, native):
    linear = record['facts']['linear_progress_curve']
    consumed = _value(record, 'substrate_consumed_percent')
    refs = _refs(record['quantities']['substrate_consumed_percent'], linear)
    if linear['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if consumed is not None:
        native.update({'consumed_percent': consumed, 'consumed_refs': refs})
        return _result('unknown', 'consumed_recorded_for_the_sheet', [])
    if linear['answer'] == 'yes':
        return _result('supported', 'linear_progress_curve_stated', refs)
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


EVALUATORS = {'spontaneous_reaction_control': _spontaneous_reaction_control, 'substrate_independent_signal': _substrate_independent_signal, 'starting_material_blank': _starting_material_blank,
              'enzyme_dependence': _enzyme_dependence, 'product_identity': _product_identity, 'calibration_standard': _calibration_standard, 'calibration_range': _calibration_range,
              'product_over_detection_limit': _product_over_detection_limit, 'internal_standard': _internal_standard, 'reaction_stopped': _reaction_stopped, 'time_points': _time_points,
              'initial_rate_regime': _initial_rate_regime, 'enzyme_substrate_ratio': _enzyme_substrate_ratio, 'substrate_range': _substrate_range,
              'active_enzyme_amount': _active_enzyme_amount, 'replicates': _replicates, 'native_reaction': _native_reaction, 'purified_enzyme': _purified_enzyme}


def grade_chromatographic(record):
    """Grade one discontinuous chromatographic assay record. Returns the criterion answers and native values."""
    detected = record['facts']['activity_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'km_nM': _nm(record, 'km'),
              'activity': ACTIVITY.get(detected['answer']), 'activity_refs': list(detected['source_refs']) if detected['answer'] in ACTIVITY else [], 'activity_support': detected['support'],
              'consumed_percent': None, 'consumed_refs': [], 'enzyme_over_substrate_plus_km': None, 'enzyme_ratio_refs': [], 'product_over_detection_limit': None, 'detection_refs': [],
              'time_point_count': None, 'time_point_refs': [], 'concentration_count': None, 'concentration_low_over_km': None, 'concentration_high_over_km': None,
              'concentration_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, CHROMATOGRAPHIC_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'chromatographic', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
