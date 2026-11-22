"""Protein_film_electrochem grader: judges ONE protein-film electrochemistry experiment by its own standards.

Hand-built and private to protein_film_electrochem. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_protein_film_electrochem_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_protein_film_electrochem_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(film_loss_percent, the series count and its two ratios over the Km, replicate_count, each with its refs) and returns 'unknown' with a reason
ending in '_recorded_for_the_sheet', and no refs; the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported.

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact activity_detected_above_control ('yes' is 'detected', 'no' is 'not_detected'): the paper
itself saying whether it saw catalytic current above its own control. It is recorded in native as 'activity' with its refs and its support (class
decision of 2026-11-21: 'interaction_detected' reads "activity detected"). It is only used by the converter when no effect is stated.

Native values retained: every record quantity as given, the series and the preparations, spread_kind, the answer of the fact
electroactive_coverage_determined (coverage_determined; the converter derives a turnover frequency from a current density only when it is yes), and
film_loss_percent, concentration_count, concentration_low_over_km, concentration_high_over_km, replicate_count, replicate_independent, activity,
each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_protein_film_electrochem_criteria import PROTEIN_FILM_ELECTROCHEM_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_protein_film_electrochem_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in PROTEIN_FILM_ELECTROCHEM_CRITERIA)
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


def _bare_electrode_control(record, native):
    return _one_fact(record, 'bare_electrode_control')


def _substrate_free_baseline(record, native):
    return _one_fact(record, 'no_substrate_control')


def _substrate_dependence(record, native):
    return _one_fact(record, 'substrate_dependent_current')


def _product_identity(record, native):
    return _one_fact(record, 'product_identified')


def _potential_reference(record, native):
    return _one_fact(record, 'potential_referenced')


def _electrode_area(record, native):
    return _one_fact(record, 'electrode_area_stated')


def _mass_transport_excluded(record, native):
    return _one_fact(record, 'mass_transport_excluded')


def _steady_state_wave(record, native):
    return _one_fact(record, 'steady_state_wave')


def _electroactive_amount(record, native):
    return _one_fact(record, 'electroactive_coverage_determined')


def _film_stability(record, native):
    corrected = record['facts']['film_loss_corrected']
    loss = _value(record, 'film_loss_percent')
    if corrected['answer'] == 'yes':
        return _result('supported', 'film_loss_correction_stated', corrected['source_refs'])
    if loss is not None:
        native.update({'film_loss_percent': loss, 'film_loss_refs': _refs(record['quantities']['film_loss_percent'], corrected)})
        return _result('unknown', 'film_loss_recorded_for_the_sheet', [])
    if corrected['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', corrected['source_refs'])
    return _result('unknown', 'film_loss_not_stated', [])


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


def _native_reaction(record, native):
    return _one_fact(record, 'native_substrate')


def _purified_enzyme(record, native):
    return _one_fact(record, 'purified_enzyme')


EVALUATORS = {'bare_electrode_control': _bare_electrode_control, 'substrate_free_baseline': _substrate_free_baseline, 'substrate_dependence': _substrate_dependence,
              'product_identity': _product_identity, 'potential_reference': _potential_reference, 'electrode_area': _electrode_area,
              'mass_transport_excluded': _mass_transport_excluded, 'steady_state_wave': _steady_state_wave, 'electroactive_amount': _electroactive_amount,
              'film_stability': _film_stability, 'substrate_range': _substrate_range, 'replicates': _replicates, 'native_reaction': _native_reaction,
              'purified_enzyme': _purified_enzyme}


def grade_protein_film_electrochem(record):
    """Grade one protein-film electrochemistry record. Returns the criterion answers and native values."""
    detected = record['facts']['activity_detected_above_control']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'],
              'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'km_nM': _nm(record, 'km'),
              'coverage_determined': record['facts']['electroactive_coverage_determined']['answer'],
              'activity': ACTIVITY.get(detected['answer']), 'activity_refs': list(detected['source_refs']) if detected['answer'] in ACTIVITY else [], 'activity_support': detected['support'],
              'film_loss_percent': None, 'film_loss_refs': [], 'concentration_count': None, 'concentration_low_over_km': None, 'concentration_high_over_km': None,
              'concentration_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, PROTEIN_FILM_ELECTROCHEM_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'protein_film_electrochem', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
