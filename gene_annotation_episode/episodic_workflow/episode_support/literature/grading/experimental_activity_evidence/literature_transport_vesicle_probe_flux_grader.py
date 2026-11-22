"""Transport_vesicle_probe_flux grader: judges ONE continuous vesicle flux experiment read by a probe by its own standards.

Hand-built and private to transport_vesicle_probe_flux. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_transport_vesicle_probe_flux_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_transport_vesicle_probe_flux_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(release_percent and control_release_percent, rate_constant_per_s and dead_time_s, replicate_count, each with its refs) and returns 'unknown' with a reason
ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact transport_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper itself saying
whether it saw transport above its own protein-free vesicles. It is recorded in native as 'transport' with its refs and its support (class decision of
2026-11-22: 'interaction_detected' reads "transport detected"). It is only used by the converter when no effect is stated.

The fact flux_faster_than_apparatus_response is recorded in native as 'flux_bound' (True when the paper says so) with its refs: a rate the paper itself calls a
limit is a bound, and the converter does not give it a spread.

Native values retained: every record quantity as given, the preparations and the two plain choices (spread_kind, probe_kind), and release_percent,
control_release_percent, rate_constant_per_s, dead_time_s, replicate_count, replicate_independent, transport, flux_bound, each with its refs.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import SECONDS_PER_MINUTE
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_vesicle_probe_flux_criteria import (
    TRANSPORT_VESICLE_PROBE_FLUX_CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_transport_vesicle_probe_flux_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in TRANSPORT_VESICLE_PROBE_FLUX_CRITERIA)
TRANSPORT = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact transport_detected_above_control
SECONDS_PER_UNIT = {'ms': 1.0e-3, 's': 1.0, 'min': SECONDS_PER_MINUTE}   # FIXED_BY_DEFINITION: a time unit of the record in seconds
RATE_PER_SECOND_PER_UNIT = {'s^-1': 1.0, 'min^-1': 1.0 / SECONDS_PER_MINUTE}   # FIXED_BY_DEFINITION: a first-order rate constant of the record in s^-1
LN2 = math.log(2.0)   # FIXED_BY_DEFINITION: a first-order half-time is ln 2 over the rate constant


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


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


def _protein_free_vesicle_control(record, native):
    return _one_fact(record, 'protein_free_vesicle_control_done')


def _release_over_control(record, native):
    release, control = _value(record, 'release_fraction'), _value(record, 'control_release_fraction')
    if release is None or control is None:
        return _result('unknown', 'release_or_control_release_not_stated', [])
    native.update({'release_percent': release, 'control_release_percent': control,
                   'release_over_control_refs': _refs(*(record['quantities'][n] for n in ('release_fraction', 'control_release_fraction', 'release_time')))})
    return _result('unknown', 'release_over_control_recorded_for_the_sheet', [])


def _protein_amount_in_vesicles(record, native):
    return _one_fact(record, 'protein_quantified_in_vesicles')


def _second_ion_control(record, native):
    return _one_fact(record, 'second_ion_control_done')


def _probe_selectivity(record, native):
    return _one_fact(record, 'probe_selective_for_ion')


def _ionophore_control(record, native):
    return _one_fact(record, 'ionophore_control_done')


def _gradient_defined(record, native):
    return _one_fact(record, 'gradient_defined')


def _detergent_reference(record, native):
    return _one_fact(record, 'detergent_reference_done')


def _time_resolution(record, native):
    bound = record['facts']['flux_faster_than_apparatus_response']
    if bound['answer'] == 'yes':
        return _result('supported', 'flux_stated_as_a_limit', bound['source_refs'])
    constant, half_time, dead = _value(record, 'rate_constant'), _value(record, 'half_time'), _value(record, 'dead_time')
    rate = None
    if constant is not None:
        rate_operand = record['quantities']['rate_constant']
        rate = constant * RATE_PER_SECOND_PER_UNIT[rate_operand['unit']]
    elif half_time is not None:
        rate_operand = record['quantities']['half_time']
        rate = LN2 / (half_time * SECONDS_PER_UNIT[rate_operand['unit']])
    if rate is None or dead is None:
        if bound['answer'] == 'no':
            return _result('supported', 'flux_stated_as_resolved', bound['source_refs'])
        return _result('unknown', 'time_resolution_not_stated', [])
    native.update({'rate_constant_per_s': rate, 'dead_time_s': dead * SECONDS_PER_UNIT[record['quantities']['dead_time']['unit']],
                   'time_resolution_refs': _refs(rate_operand, record['quantities']['dead_time'])})
    return _result('unknown', 'time_resolution_recorded_for_the_sheet', [])


def _probe_calibration(record, native):
    return _one_fact(record, 'probe_calibrated')


def _vesicle_integrity(record, native):
    return _one_fact(record, 'vesicle_integrity_checked')


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


EVALUATORS = {'protein_free_vesicle_control': _protein_free_vesicle_control, 'release_over_control': _release_over_control,
              'protein_amount_in_vesicles': _protein_amount_in_vesicles, 'second_ion_control': _second_ion_control, 'probe_selectivity': _probe_selectivity,
              'ionophore_control': _ionophore_control, 'gradient_defined': _gradient_defined, 'detergent_reference': _detergent_reference,
              'time_resolution': _time_resolution, 'probe_calibration': _probe_calibration, 'vesicle_integrity': _vesicle_integrity, 'replicates': _replicates,
              'native_substrate': _native_substrate, 'purified_protein': _purified_protein}


def grade_transport_vesicle_probe_flux(record):
    """Grade one continuous vesicle flux record. Returns the criterion answers and native values."""
    detected = record['facts']['transport_detected_above_control']
    bound = record['facts']['flux_faster_than_apparatus_response']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'spread_kind': record['spread_kind'], 'probe_kind': record['probe_kind'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'transport': TRANSPORT.get(detected['answer']), 'transport_refs': list(detected['source_refs']) if detected['answer'] in TRANSPORT else [], 'transport_support': detected['support'],
              'flux_bound': bound['answer'] == 'yes', 'flux_bound_refs': list(bound['source_refs']) if bound['answer'] == 'yes' else [],
              'release_percent': None, 'control_release_percent': None, 'release_over_control_refs': [], 'rate_constant_per_s': None, 'dead_time_s': None, 'time_resolution_refs': [],
              'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, TRANSPORT_VESICLE_PROBE_FLUX_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'transport_vesicle_probe_flux', 'experiment_ref': record['experiment_ref'],
            'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()},
            'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
