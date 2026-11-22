"""Transport_fluorescent_reporter grader: judges ONE fluorescent-reporter transport experiment in cells (a fluorescent substrate analogue, an indicator dye or a genetically encoded sensor read in cells with the transporter) by its own standards. DRAFT of 2026-11-22, owner to correct.

Hand-built and private to transport_fluorescent_reporter. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_transport_fluorescent_reporter_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_transport_fluorescent_reporter_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(z_prime, the series count and its two ratios over the Km, replicate_count, each with its refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. A 'supported' or 'conflicting' result always carries support refs (the quoted spans of the stated
fields it rests on); ``_result`` refuses to build one without them.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact transport_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw transport above its own control. It is recorded in native as 'transport' with its refs and its support (class
decision of the transport_response inventory, section 4.3: 'interaction_detected' reads "transport detected"). It is only used by the converter
when no effect is stated.

Native values retained: every record quantity as given, the series and the preparations, spread_kind, km_nM, and z_prime, concentration_count,
concentration_low_over_km, concentration_high_over_km, replicate_count, replicate_independent, transport, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_fluorescent_reporter_criteria import TRANSPORT_FLUORESCENT_REPORTER_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_transport_fluorescent_reporter_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in TRANSPORT_FLUORESCENT_REPORTER_CRITERIA)
TRANSPORT = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact transport_detected_above_control


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


def _control_cells(record, native):
    return _one_fact(record, 'untransfected_control_done')


def _no_substrate_baseline(record, native):
    return _one_fact(record, 'no_substrate_control_done')


def _background_fluorescence(record, native):
    return _one_fact(record, 'background_fluorescence_subtracted')


def _signal_drift(record, native):
    return _one_fact(record, 'signal_drift_controlled')


def _indicator_calibration(record, native):
    return _one_fact(record, 'indicator_calibrated')


def _assay_window(record, native):
    value = _value(record, 'z_prime_factor')
    if value is None:
        return _result('unknown', 'z_prime_not_stated', [])
    native.update({'z_prime': value, 'z_prime_refs': _refs(record['quantities']['z_prime_factor'])})
    return _result('unknown', 'z_prime_recorded_for_the_sheet', [])


def _substrate_identity(record, native):
    return _one_fact(record, 'analogue_is_native_substrate')


def _analogue_competition(record, native):
    return _one_fact(record, 'competitor_control_done')


def _indicator_specificity(record, native):
    return _one_fact(record, 'indicator_specificity_shown')


def _expression_confirmed(record, native):
    return _one_fact(record, 'expression_confirmed')


def _membrane_integrity(record, native):
    return _one_fact(record, 'cells_intact_checked')


def _linear_interval(record, native):
    return _one_fact(record, 'linear_interval_shown')


def _substrate_concentration_stated(record, native):
    if _value(record, 'substrate_concentration') is None:
        return _result('unknown', 'substrate_concentration_not_stated', [])
    return _result('supported', 'substrate_concentration_stated', _refs(record['quantities']['substrate_concentration']))


def _substrate_series(record, native):
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


EVALUATORS = {'control_cells': _control_cells, 'no_substrate_baseline': _no_substrate_baseline, 'background_fluorescence': _background_fluorescence,
              'signal_drift': _signal_drift, 'indicator_calibration': _indicator_calibration, 'assay_window': _assay_window, 'substrate_identity': _substrate_identity,
              'analogue_competition': _analogue_competition, 'indicator_specificity': _indicator_specificity, 'expression_confirmed': _expression_confirmed,
              'membrane_integrity': _membrane_integrity, 'linear_interval': _linear_interval, 'substrate_concentration_stated': _substrate_concentration_stated,
              'substrate_series': _substrate_series, 'replicates': _replicates}


def grade_transport_fluorescent_reporter(record):
    """Grade one fluorescent-reporter transport experiment record. Returns the criterion answers and native values."""
    detected = record['facts']['transport_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'km_nM': _nm(record, 'km'),
              'transport': TRANSPORT.get(detected['answer']), 'transport_refs': list(detected['source_refs']) if detected['answer'] in TRANSPORT else [], 'transport_support': detected['support'],
              'z_prime': None, 'z_prime_refs': [], 'concentration_count': None, 'concentration_low_over_km': None, 'concentration_high_over_km': None, 'concentration_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, TRANSPORT_FLUORESCENT_REPORTER_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'transport_fluorescent_reporter', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
