"""Redox_mediator grader: judges ONE artificial redox-mediator enzyme assay by its own standards.

Hand-built and private to redox_mediator. Deterministic; no model call, no store access.
Input: the record of one assay (forms/.../literature_redox_mediator_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_redox_mediator_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(consumed_percent, mediator_over_km, the series count and its two ratios over the Km, absorbance_max, replicate_count, each with its refs) and
returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact activity_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw the dye change above its own control. It is recorded in native as 'activity' with its refs and its support (class
decision of 2026-11-21: 'interaction_detected' reads "activity detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the series and the preparations, spread_kind, mediator_kind, mediator_role, and consumed_percent,
mediator_over_km, concentration_count, concentration_low_over_km, concentration_high_over_km, absorbance_max, replicate_count, replicate_independent,
activity, each with its refs. The kind and the role of the mediator are recorded only: no criterion reads them.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_redox_mediator_criteria import REDOX_MEDIATOR_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_redox_mediator_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in REDOX_MEDIATOR_CRITERIA)
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


def _dye_background_control(record, native):
    names = ('no_enzyme_control', 'inactive_enzyme_control')
    answers = [record['facts'][n]['answer'] for n in names]
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'dye_background_control_stated', refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _substrate_independent_signal(record, native):
    return _one_fact(record, 'no_substrate_control')


def _enzyme_dependence(record, native):
    return _one_fact(record, 'rate_proportional_to_enzyme')


def _product_identity(record, native):
    return _one_fact(record, 'product_identified')


def _electron_stoichiometry(record, native):
    return _one_fact(record, 'electron_stoichiometry_stated')


def _extinction_coefficient_stated(record, native):
    if _value(record, 'extinction_coefficient') is None or _value(record, 'wavelength') is None:
        return _result('unknown', 'extinction_coefficient_or_wavelength_missing', [])
    return _result('supported', 'extinction_coefficient_and_wavelength_stated', _refs(record['quantities']['extinction_coefficient'], record['quantities']['wavelength']))


def _absorbance_range(record, native):
    value = _value(record, 'absorbance_max')
    if value is None:
        return _result('unknown', 'absorbance_not_stated', [])
    native.update({'absorbance_max': value, 'absorbance_refs': _refs(record['quantities']['absorbance_max'])})
    return _result('unknown', 'absorbance_recorded_for_the_sheet', [])


def _oxygen_reoxidation(record, native):
    excluded, reoxidised = record['facts']['oxygen_excluded'], record['facts']['reduced_dye_reoxidised_by_oxygen']
    if excluded['answer'] == 'yes':
        return _result('supported', 'oxygen_excluded_stated', excluded['source_refs'])
    if reoxidised['answer'] == 'no':
        return _result('not_applicable', 'dye_not_reoxidised_by_oxygen_stated', [])
    if excluded['answer'] == 'no' and reoxidised['answer'] == 'yes':
        return _result('conflicting', 'run_in_air_with_oxygen_sensitive_dye', _refs(excluded, reoxidised))
    if excluded['answer'] == 'no':
        return _result('unknown', 'run_in_air_reoxidation_not_stated', [])
    return _result('unknown', 'oxygen_exclusion_not_stated', [])


def _initial_rate_regime(record, native):
    linear = record['facts']['linear_progress_curve']
    consumed = _value(record, 'dye_consumed_percent')
    refs = _refs(record['quantities']['dye_consumed_percent'], linear)
    if linear['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if consumed is not None:
        native.update({'consumed_percent': consumed, 'consumed_refs': refs})
        return _result('unknown', 'consumed_recorded_for_the_sheet', [])
    if linear['answer'] == 'yes':
        return _result('supported', 'linear_progress_curve_stated', refs)
    return _result('unknown', 'rate_regime_not_stated', [])


def _mediator_saturation(record, native):
    concentration, km = _nm(record, 'mediator_concentration'), _nm(record, 'mediator_km')
    if concentration is None or km is None:
        return _result('unknown', 'mediator_concentration_or_km_missing', [])
    native['mediator_over_km'] = concentration / km
    native['mediator_refs'] = _refs(record['quantities']['mediator_concentration'], record['quantities']['mediator_km'])
    return _result('unknown', 'mediator_recorded_for_the_sheet', [])


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


def _native_electron_partner(record, native):
    return _one_fact(record, 'native_electron_partner_used')


def _purified_enzyme(record, native):
    return _one_fact(record, 'purified_enzyme')


EVALUATORS = {'dye_background_control': _dye_background_control, 'substrate_independent_signal': _substrate_independent_signal, 'enzyme_dependence': _enzyme_dependence,
              'product_identity': _product_identity, 'electron_stoichiometry': _electron_stoichiometry, 'extinction_coefficient_stated': _extinction_coefficient_stated,
              'absorbance_range': _absorbance_range, 'oxygen_reoxidation': _oxygen_reoxidation, 'initial_rate_regime': _initial_rate_regime,
              'mediator_saturation': _mediator_saturation, 'substrate_range': _substrate_range, 'active_enzyme_amount': _active_enzyme_amount, 'replicates': _replicates,
              'native_reaction': _native_reaction, 'native_electron_partner': _native_electron_partner, 'purified_enzyme': _purified_enzyme}


def grade_redox_mediator(record):
    """Grade one artificial redox-mediator assay record. Returns the criterion answers and native values."""
    detected = record['facts']['activity_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'],
              'mediator_kind': record['mediator_kind'], 'mediator_role': record['mediator_role'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'km_nM': _nm(record, 'km'),
              'activity': ACTIVITY.get(detected['answer']), 'activity_refs': list(detected['source_refs']) if detected['answer'] in ACTIVITY else [], 'activity_support': detected['support'],
              'consumed_percent': None, 'consumed_refs': [], 'mediator_over_km': None, 'mediator_refs': [], 'concentration_count': None, 'concentration_low_over_km': None, 'concentration_high_over_km': None,
              'concentration_refs': [], 'absorbance_max': None, 'absorbance_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, REDOX_MEDIATOR_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'redox_mediator', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
