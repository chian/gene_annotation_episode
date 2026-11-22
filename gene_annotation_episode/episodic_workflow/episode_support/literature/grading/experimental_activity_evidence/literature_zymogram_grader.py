"""Zymogram grader: judges ONE in-gel activity staining experiment (zymography, activity staining after a native gel) by its own standards.

Hand-built and private to zymogram. Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_zymogram_record.py).
Output: for each criterion an interpretation status in the existing A105 vocabulary (supported / unknown / conflicting / not_applicable)
with support refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_zymogram_criteria.py
(the single source). This file only evaluates them: one short function per criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(band_over_expected, replicate_count, each with its refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet', and no refs;
the converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. Two criteria have their own declared rule: band_assignment (either fact yes is enough, a fact
no still fails) and inhibitor_sensitivity (a band the inhibitor did not change is unknown, not conflicting).

The record's per-field 'support' (how well each stated field's quote supports it) is not judged here: it is read out per criterion
(native 'support': criterion id -> the supports of the stated fields it reads) for the converter.

The qualitative statement of the experiment is the fact activity_band_detected ('yes' is 'detected', 'no' is 'not_detected'): the paper itself
saying whether it saw an activity band at the position of the enzyme. It is recorded in native as 'activity' with its refs and its support (class
decision of 2026-11-21: 'interaction_detected' reads "activity detected"). A zymogram states no rate and no constant, so this is the whole result;
the converter hands it to the sheet.

Native values retained: every record quantity as given, the two choices and the preparations, band_over_expected, replicate_count,
replicate_independent, activity, each with its refs.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_zymogram_criteria import ZYMOGRAM_CRITERIA
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_zymogram_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in ZYMOGRAM_CRITERIA)
ACTIVITY = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact activity_band_detected


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


def _substrate_dependence_control(record, native):
    return _one_fact(record, 'no_substrate_control_clean')


def _inactive_sample_control(record, native):
    return _one_fact(record, 'inactive_sample_clean')


def _stain_positive_control(record, native):
    return _one_fact(record, 'positive_control_band_shown')


def _band_position(record, native):
    band, expected = _value(record, 'band_mass'), _value(record, 'expected_mass')
    if band is None or expected is None:
        return _result('unknown', 'band_or_expected_mass_missing', [])
    native['band_over_expected'] = band / expected
    native['band_position_refs'] = _refs(record['quantities']['band_mass'], record['quantities']['expected_mass'])
    return _result('unknown', 'band_position_recorded_for_the_sheet', [])


def _band_assignment(record, native):
    items = [record['facts']['deletion_sample_lacks_band'], record['facts']['band_assigned_to_target']]
    answers = [item['answer'] for item in items]
    if 'no' in answers:
        return _result('conflicting', 'fact_answered_no', _refs(*[item for item in items if item['answer'] == 'no']))
    if 'yes' in answers:
        return _result('supported', 'band_assigned_to_the_enzyme', _refs(*[item for item in items if item['answer'] == 'yes']))
    status, reason = _shared_rule(answers)
    return _result(status, reason, [])


def _inhibitor_sensitivity(record, native):
    item = record['facts']['inhibitor_abolishes_band']
    if item['answer'] == 'yes':
        return _result('supported', 'inhibitor_abolished_the_band', item['source_refs'])
    if item['answer'] == 'no':
        return _result('unknown', 'inhibitor_did_not_change_the_band', [])
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, [])


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


def _purified_enzyme(record, native):
    return _one_fact(record, 'purified_enzyme')


EVALUATORS = {'substrate_dependence_control': _substrate_dependence_control, 'inactive_sample_control': _inactive_sample_control, 'stain_positive_control': _stain_positive_control,
              'band_position': _band_position, 'band_assignment': _band_assignment, 'inhibitor_sensitivity': _inhibitor_sensitivity, 'replicates': _replicates,
              'native_substrate': _native_substrate, 'purified_enzyme': _purified_enzyme}


def grade_zymogram(record):
    """Grade one in-gel activity staining record. Returns the criterion answers and native values."""
    detected = record['facts']['activity_band_detected']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']),
              'gel_kind': record['gel_kind'], 'detection_kind': record['detection_kind'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()},
              'activity': ACTIVITY.get(detected['answer']), 'activity_refs': list(detected['source_refs']) if detected['answer'] in ACTIVITY else [], 'activity_support': detected['support'],
              'band_over_expected': None, 'band_position_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    native['support'] = criterion_supports(record, ZYMOGRAM_CRITERIA)      # kept for the sheet: the grader does not judge it
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'zymogram', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
