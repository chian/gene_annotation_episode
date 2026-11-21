"""CETSA grader: judges ONE cellular thermal shift assay (CETSA: melt curve and isothermal dose-response ITDR-CETSA) experiment (a compound is added to intact cells, a lysate or a tissue, the sample is heated and the target protein that stays soluble is read by western blot, AlphaScreen or mass spectrometry; a ligand that binds the target stabilises it, so the melt curve shifts to a higher melting temperature, or at one temperature the soluble fraction rises with the compound concentration, giving an EC50 that is an apparent engagement constant derived from the thermal shift; mostly a qualitative statement of target engagement) by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA, SEC, dialysis or AUC graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_cetsa_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_cetsa_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on);
``_result`` refuses to build one without them. Where only a fact with no span would decide, the criterion returns 'unknown' (or
'not_applicable' where the criterion belongs to the other format or needs an EC50 that is not reported) with a declared reason.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown;
else all 'not_applicable' -> not_applicable; else supported. The other criteria have their own rules (declared).

A CETSA has two outcomes. With an EC50 of an isothermal dose-response it reports an apparent engagement constant (native 'ec50_nM', derived from the thermal shift, not a dissociation constant); without one it reports only the
target engagement and perhaps the shift of the melting temperature. The native values carry the qualitative statement of the record, 'interaction' ('detected' when a target engagement is stated, 'not_detected' when it is stated not to have
happened, else None), with the spans that state it ('interaction_refs'); the converter hands it to the merger as the experiment's qualitative effect when the record has no EC50.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs (shift_celsius/shift_refs, temperature_count/temperature_count_refs,
concentration_count/concentration_count_refs, low_over_ec50/high_over_ec50/range_refs, replicate_count/replicate_independent/replicate_refs) and returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the CETSA converter judges it.

Support: native 'support' holds, for each criterion, the supports ('direct', 'implied', 'about_something_else') of the stated fields it reads
(its declared 'reads'), copied from the record and not judged here; the converter judges them.

Native values retained: every record quantity as given, plus ec50_nM, lowest_nM, highest_nM, shift_celsius (signed), low_over_ec50, high_over_ec50, interaction, interaction_refs, preparations, sample_format, experiment_format, readout and spread_kind.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_cetsa_criteria import (
    CETSA_CRITERIA, NM_PER_UNIT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_cetsa_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in CETSA_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact target_engagement_shown
NO_EC50 = 'no_apparent_engagement_constant_reported'


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _scaled(record, name, scale):
    value = _value(record, name)
    return None if value is None else value * scale[record['quantities'][name]['unit']]


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


def _format_fact(record, name, only_format_field, only_format, reason):
    """The fact decides; an unknown fact is not applicable when the record states the format (or sample) the criterion does not belong to."""
    item = record['facts'][name]
    status, fact_reason = _shared_rule([item['answer']])
    if status == 'unknown' and record[only_format_field] == only_format:
        return _result('not_applicable', reason, [])
    return _result(status, fact_reason, item['source_refs'])


def _engagement_observed(record, native):
    return _one_fact(record, 'target_engagement_shown')


def _thermal_shift(record, native):
    shift, vehicle, ligand = _value(record, 'tm_shift'), _value(record, 'tm_vehicle'), _value(record, 'tm_ligand')
    quantities = record['quantities']
    if shift is not None:
        native.update({'shift_celsius': shift, 'shift_refs': _refs(quantities['tm_shift'])})
    elif vehicle is not None and ligand is not None:
        native.update({'shift_celsius': ligand - vehicle, 'shift_refs': _refs(quantities['tm_ligand'], quantities['tm_vehicle'])})
    else:
        return _result('unknown', 'thermal_shift_not_given', [])
    return _result('unknown', 'thermal_shift_recorded_for_the_sheet', [])


def _vehicle_control(record, native):
    return _one_fact(record, 'vehicle_control_done')


def _loading_control(record, native):
    return _one_fact(record, 'loading_control_used')


def _counted_fact(record, native, fact_name, count_name, count_key, format_field_value, reason):
    """A fact that fails when no; else a stated count is recorded for the sheet; else the fact decides (not applicable for the other format)."""
    item = record['facts'][fact_name]
    if item['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', item['source_refs'])
    count = _value(record, count_name)
    if count is None:
        field, value = format_field_value
        if item['answer'] == 'unknown' and record[field] == value:
            return _result('not_applicable', reason, [])
        return _one_fact(record, fact_name)
    native.update({count_key: count, count_key + '_refs': _refs(record['quantities'][count_name])})
    return _result('unknown', count_key + '_recorded_for_the_sheet', [])


def _temperature_series(record, native):
    return _counted_fact(record, native, 'melt_curve_measured', 'temperature_count', 'temperature_count', ('experiment_format', 'itdr'), 'isothermal_format_has_no_melt_curve')


def _isothermal_window(record, native):
    return _format_fact(record, 'isothermal_temperature_in_window', 'experiment_format', 'melt_curve', 'melt_curve_format_has_no_isothermal_temperature')


def _dose_response(record, native):
    return _counted_fact(record, native, 'dose_dependent_shown', 'concentration_count', 'concentration_count', ('experiment_format', 'melt_curve'), 'melt_curve_format_has_no_dose_response')


def _concentration_range(record, native):
    if native['ec50_nM'] is None:
        return _result('not_applicable', NO_EC50, [])
    lowest, highest = native['lowest_nM'], native['highest_nM']
    if lowest is None or highest is None:
        return _result('unknown', 'concentration_range_not_given', [])
    quantities = record['quantities']
    native.update({'low_over_ec50': lowest / native['ec50_nM'], 'high_over_ec50': highest / native['ec50_nM'],
                   'range_refs': _refs(quantities['compound_concentration_lowest'], quantities['compound_concentration_highest'], quantities['engagement_ec50'])})
    return _result('unknown', 'concentration_range_recorded_for_the_sheet', [])


def _negative_control(record, native):
    return _one_fact(record, 'negative_control_done')


def _specificity_control(record, native):
    return _one_fact(record, 'specificity_control_done')


def _cell_integrity(record, native):
    return _format_fact(record, 'cell_integrity_checked', 'sample_format', 'cell_lysate', 'lysate_has_no_living_cells')


def _total_level_control(record, native):
    return _one_fact(record, 'total_target_level_controlled')


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


EVALUATORS = {'engagement_observed': _engagement_observed, 'thermal_shift': _thermal_shift, 'vehicle_control': _vehicle_control, 'loading_control': _loading_control, 'temperature_series': _temperature_series, 'isothermal_window': _isothermal_window, 'dose_response': _dose_response, 'concentration_range': _concentration_range, 'negative_control': _negative_control, 'specificity_control': _specificity_control, 'cell_integrity': _cell_integrity, 'total_level_control': _total_level_control, 'replicates': _replicates}


def grade_cetsa(record):
    """Grade one CETSA experiment record. Returns the criterion answers and native values."""
    engagement = record['facts']['target_engagement_shown']
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'sample_format': record['sample_format'], 'experiment_format': record['experiment_format'], 'readout': record['readout'], 'spread_kind': record['spread_kind'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'interaction': INTERACTION.get(engagement['answer']), 'interaction_refs': list(engagement['source_refs']) if engagement['answer'] in INTERACTION else [], 'ec50_nM': _scaled(record, 'engagement_ec50', NM_PER_UNIT), 'lowest_nM': _scaled(record, 'compound_concentration_lowest', NM_PER_UNIT), 'highest_nM': _scaled(record, 'compound_concentration_highest', NM_PER_UNIT), 'shift_celsius': None, 'shift_refs': [], 'temperature_count': None, 'temperature_count_refs': [], 'concentration_count': None, 'concentration_count_refs': [], 'low_over_ec50': None, 'high_over_ec50': None, 'range_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, CETSA_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'cetsa', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
