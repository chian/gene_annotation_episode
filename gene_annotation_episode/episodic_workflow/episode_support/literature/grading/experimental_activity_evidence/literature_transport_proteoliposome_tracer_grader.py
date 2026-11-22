"""Transport_proteoliposome_tracer grader: judges ONE proteoliposome tracer transport experiment by its own standards (a purified transporter reconstituted into liposomes, an
imposed driving force, uptake or efflux of a labelled substrate, protein-free liposomes as the control). DRAFT built 2026-11-22 on the shape of
literature_spectro_direct_grader.py, owner to correct.

Hand-built and private to transport_proteoliposome_tracer. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_transport_proteoliposome_tracer_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_transport_proteoliposome_tracer_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(equilibrium_percent, the series count and its two ratios over the Km, replicate_count, each with its refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

A 'supported' or 'conflicting' result always carries support refs (``_result`` raises without them).

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact transport_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying whether it saw
transport above its own control. It is recorded in native as 'transport' with its refs and its support (class decision of 2026-11-22: 'interaction_detected' reads "transport
detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the series and the preparations, spread_kind, driving_force, flux_direction, and equilibrium_percent,
concentration_count, concentration_low_over_km, concentration_high_over_km, replicate_count, replicate_independent, transport, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_proteoliposome_tracer_criteria import TRANSPORT_PROTEOLIPOSOME_TRACER_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_transport_proteoliposome_tracer_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in TRANSPORT_PROTEOLIPOSOME_TRACER_CRITERIA)
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


def _empty_liposome_control(record, native):
    return _one_fact(record, 'empty_liposome_control_done')


def _inactive_protein_control(record, native):
    return _one_fact(record, 'inactive_protein_control_done')


def _no_gradient_control(record, native):
    return _one_fact(record, 'no_gradient_control_done')


def _gradient_verified(record, native):
    return _one_fact(record, 'gradient_verified')


def _leak_check(record, native):
    return _one_fact(record, 'leak_checked')


def _competitor_control(record, native):
    return _one_fact(record, 'competitor_control_done')


def _substrate_identity(record, native):
    return _one_fact(record, 'substrate_identity_shown')


def _protein_amount_basis(record, native):
    return _one_fact(record, 'protein_quantified_after_reconstitution')


def _active_fraction(record, native):
    return _one_fact(record, 'active_fraction_determined')


def _initial_rate_regime(record, native):
    linear = record['facts']['linear_interval_shown']
    equilibrium = _value(record, 'uptake_percent_of_equilibrium')
    refs = _refs(record['quantities']['uptake_percent_of_equilibrium'], linear)
    if linear['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    if equilibrium is not None:
        native.update({'equilibrium_percent': equilibrium, 'equilibrium_refs': refs})
        return _result('unknown', 'equilibrium_recorded_for_the_sheet', [])
    if linear['answer'] == 'yes':
        return _result('supported', 'linear_interval_stated', refs)
    return _result('unknown', 'rate_regime_not_stated', [])


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


def _native_substrate(record, native):
    return _one_fact(record, 'native_substrate')


def _purified_protein(record, native):
    return _one_fact(record, 'purified_protein')


EVALUATORS = {'empty_liposome_control': _empty_liposome_control, 'inactive_protein_control': _inactive_protein_control, 'no_gradient_control': _no_gradient_control,
              'gradient_verified': _gradient_verified, 'leak_check': _leak_check, 'competitor_control': _competitor_control, 'substrate_identity': _substrate_identity,
              'protein_amount_basis': _protein_amount_basis, 'active_fraction': _active_fraction, 'initial_rate_regime': _initial_rate_regime,
              'substrate_range': _substrate_range, 'replicates': _replicates, 'native_substrate': _native_substrate, 'purified_protein': _purified_protein}


def grade_transport_proteoliposome_tracer(record):
    """Grade one proteoliposome tracer transport record. Returns the criterion answers and native values."""
    detected = record['facts']['transport_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'driving_force': record['driving_force'], 'flux_direction': record['flux_direction'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'km_nM': _nm(record, 'km'),
              'transport': TRANSPORT.get(detected['answer']), 'transport_refs': list(detected['source_refs']) if detected['answer'] in TRANSPORT else [], 'transport_support': detected['support'],
              'equilibrium_percent': None, 'equilibrium_refs': [], 'concentration_count': None, 'concentration_low_over_km': None, 'concentration_high_over_km': None,
              'concentration_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, TRANSPORT_PROTEOLIPOSOME_TRACER_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'transport_proteoliposome_tracer', 'experiment_ref': record['experiment_ref'],
            'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
