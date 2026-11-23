"""Transport_planar_bilayer grader: judges ONE planar lipid bilayer recording by its own standards.

Hand-built and private to transport_planar_bilayer. Deterministic; no model call, no store access.
Input: the record of one recording (forms/.../literature_transport_planar_bilayer_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_transport_planar_bilayer_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(stated_conductance_pS beside current_over_driving_force_pS, permeability_ratio with named_ion_preferred, amplitude_over_noise, event_count,
replicate_count, each with its refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs; the converter judges it.
The only numbers here are unit scales that hold by definition (FIXED_BY_DEFINITION).

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact transport_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw current or channel events above its own control. It is recorded in native as 'transport' with its refs and its
support (class decision of 2026-11-22: 'interaction_detected' reads "transport detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the preparations, spread_kind, and stated_conductance_pS, current_over_driving_force_pS,
driving_force_refs, permeability_ratio, named_ion_preferred, permeability_refs, amplitude_over_noise, noise_refs, event_count, event_refs,
replicate_count, replicate_independent, replicate_refs, transport, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_planar_bilayer_criteria import TRANSPORT_PLANAR_BILAYER_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_transport_planar_bilayer_grade'
CRITERIA = tuple(criterion['id'] for criterion in TRANSPORT_PLANAR_BILAYER_CRITERIA)
TRANSPORT = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact transport_detected_above_control
PA_PER_UNIT = {'pA': 1.0, 'nA': 1.0e3}   # FIXED_BY_DEFINITION: 1 nA is 1000 pA.
PS_PER_UNIT = {'pS': 1.0, 'nS': 1.0e3}   # FIXED_BY_DEFINITION: 1 nS is 1000 pS.
PS_PER_PA_PER_MV = 1.0e3   # FIXED_BY_DEFINITION: 1 pA over 1 mV is 1 nS, that is 1000 pS (siemens are amperes per volt).


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _scaled(record, name, scales):
    value = _value(record, name)
    return None if value is None else value * scales[record['quantities'][name]['unit']]


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


def _protein_free_control(record, native):
    return _one_fact(record, 'protein_free_bilayer_control_done')


def _bilayer_integrity(record, native):
    return _one_fact(record, 'bilayer_integrity_checked')


def _solutions_stated(record, native):
    return _one_fact(record, 'solutions_stated')


def _driving_force_correction(record, native):
    fact = record['facts']['driving_force_corrected']
    if fact['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', fact['source_refs'])
    conductance, current = _scaled(record, 'unitary_conductance', PS_PER_UNIT), _scaled(record, 'unitary_current', PA_PER_UNIT)
    voltage, reversal = _value(record, 'holding_voltage'), _value(record, 'reversal_potential')
    if None not in (conductance, current, voltage, reversal) and voltage != reversal:
        native.update({'stated_conductance_pS': conductance, 'current_over_driving_force_pS': current / abs(voltage - reversal) * PS_PER_PA_PER_MV,
                       'driving_force_refs': _refs(*(record['quantities'][n] for n in ('unitary_conductance', 'unitary_current', 'holding_voltage', 'reversal_potential')), fact)})
        return _result('unknown', 'driving_force_recorded_for_the_sheet', [])
    status, reason = _shared_rule([fact['answer']])
    if status == 'supported':
        return _result('supported', 'driving_force_corrected_stated', fact['source_refs'])
    return _result(status, 'driving_force_correction_not_stated' if status == 'unknown' else reason, fact['source_refs'])


def _bi_ionic_gradient(record, native):
    return _one_fact(record, 'bi_ionic_gradient_done')


def _ion_preference(record, native):
    fact = record['facts']['named_ion_preferred']
    ratio = _value(record, 'permeability_ratio')
    if fact['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', fact['source_refs'])
    if ratio is not None:
        native.update({'permeability_ratio': ratio, 'named_ion_preferred': fact['answer'], 'permeability_refs': _refs(record['quantities']['permeability_ratio'], fact)})
        return _result('unknown', 'permeability_ratio_recorded_for_the_sheet', [])
    status, reason = _shared_rule([fact['answer']])
    if status == 'supported':
        return _result('supported', 'named_ion_preferred_stated', fact['source_refs'])
    return _result(status, 'ion_preference_not_stated' if status == 'unknown' else reason, fact['source_refs'])


def _blocker_control(record, native):
    return _one_fact(record, 'blocker_control_done')


def _signal_over_noise(record, native):
    current, noise = _scaled(record, 'unitary_current', PA_PER_UNIT), _scaled(record, 'baseline_noise', PA_PER_UNIT)
    if current is None or noise is None:
        return _result('unknown', 'current_or_noise_missing', [])
    native.update({'amplitude_over_noise': current / noise, 'noise_refs': _refs(record['quantities']['unitary_current'], record['quantities']['baseline_noise'])})
    return _result('unknown', 'amplitude_over_noise_recorded_for_the_sheet', [])


def _events_analysed(record, native):
    count = _value(record, 'event_count')
    if count is None:
        return _result('unknown', 'event_count_not_stated', [])
    native.update({'event_count': count, 'event_refs': _refs(record['quantities']['event_count'])})
    return _result('unknown', 'event_count_recorded_for_the_sheet', [])


def _replicates(record, native):
    count = _value(record, 'bilayer_count')
    independent = record['facts']['independent_bilayers']
    refs = _refs(record['quantities']['bilayer_count'], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', 'replicates_not_independent', refs)
    if count is None:
        return _result('unknown', 'replicate_count_or_independence_unknown', [])
    native.update({'replicate_count': count, 'replicate_independent': independent['answer'], 'replicate_refs': refs})
    return _result('unknown', 'replicate_count_recorded_for_the_sheet', [])


def _purified_protein(record, native):
    return _one_fact(record, 'purified_protein')


EVALUATORS = {'protein_free_control': _protein_free_control, 'bilayer_integrity': _bilayer_integrity, 'solutions_stated': _solutions_stated,
              'driving_force_correction': _driving_force_correction, 'bi_ionic_gradient': _bi_ionic_gradient, 'ion_preference': _ion_preference,
              'blocker_control': _blocker_control, 'signal_over_noise': _signal_over_noise, 'events_analysed': _events_analysed, 'replicates': _replicates,
              'purified_protein': _purified_protein}


def grade_transport_planar_bilayer(record):
    """Grade one planar lipid bilayer recording record. Returns the criterion answers and native values."""
    detected = record['facts']['transport_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'transport': TRANSPORT.get(detected['answer']), 'transport_refs': list(detected['source_refs']) if detected['answer'] in TRANSPORT else [], 'transport_support': detected['support'],
              'stated_conductance_pS': None, 'current_over_driving_force_pS': None, 'driving_force_refs': [], 'permeability_ratio': None, 'named_ion_preferred': None, 'permeability_refs': [],
              'amplitude_over_noise': None, 'noise_refs': [], 'event_count': None, 'event_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, TRANSPORT_PLANAR_BILAYER_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'transport_planar_bilayer', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
