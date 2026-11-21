"""Dialysis grader: judges ONE equilibrium dialysis / ultrafiltration binding experiment (a ligand and a protein are separated from each other's bound form across a semipermeable membrane: equilibrium dialysis, rapid equilibrium dialysis, ultrafiltration, ultracentrifugation; the free and the total ligand concentration are measured; the result is a fraction bound or a percent unbound, or a KD and Bmax from a saturation series, or a Ki) by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS, ELISA, AlphaScreen, radioligand, SPA, pull-down, EMSA or SEC graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_dialysis_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words and the status it returns in each case are declared in literature_dialysis_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(percent_bound, equilibration_h, recovery_percent, adsorption_percent, volume_shift_percent, salt_mM, bound_over_protein, protein_over_kd, percent_unbound,
concentration_count and the span over the KD, replicate_count/replicate_independent, each with its *_refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet' and no refs; the dialysis converter (literature_dialysis_converter.py) judges it. A fact stated as no stays the grader's own
conflicting. When binding_observed is decided by a stated fraction and not by its fact, the grader leaves 'interaction' empty: the qualitative statement is
the sheet's reading of the judgement.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on);
``_result`` refuses to build one without them. Where only a fact with no span would decide, the criterion returns 'unknown' (or
'not_applicable' when it needs a KD and none is reported) with a declared reason.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable): any 'no' -> conflicting; else any 'unknown' -> unknown;
else all 'not_applicable' -> not_applicable; else supported. The other criteria have their own rules (declared).

A dialysis has two outcomes. With a KD (or a Ki) it is a quantitative result (native 'kd_nM' / 'ki_nM'); without one (a percent bound or a percent unbound at one concentration) it
is qualitative. The native values carry the qualitative statement of the record, 'interaction' ('detected' when binding is observed, 'not_detected' when it is stated not to be, else None),
with the spans that state it ('interaction_refs'); it is decided by the criterion binding_observed. The converter hands it to the merger as the experiment's qualitative effect when the record has
no KD and no Ki.

Support: native 'support' holds, for each criterion, the supports ('direct', 'implied', 'about_something_else') of the stated fields it reads
(its declared 'reads'), copied from the record and not judged here; the converter judges them.

Native values retained: every record quantity as given, plus kd_nM, ki_nM, constant_name, constant_nM, percent_bound, percent_unbound, protein_nM, bound_nM, bound_over_protein, protein_over_kd, salt_mM, equilibration_h,
concentration_count, concentration_low_over_kd, concentration_high_over_kd, interaction, interaction_refs, preparations, separation_method, device_type, detection, spread_kind and fit_model.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_dialysis_criteria import (
    DIALYSIS_CRITERIA, H_PER_UNIT, MM_PER_SALT_UNIT, NM_PER_UNIT, PERCENT_FULL)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_dialysis_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in DIALYSIS_CRITERIA)
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the qualitative statement of the fact binding_detected
CONSTANTS = ('kd', 'ki')                                  # the order in which the binding constant of a record is taken
REPORTED = ('kd', 'bmax', 'ki')                           # the fitted values whose spans support a fit model
NOT_EQUILIBRIUM = ('ultrafiltration', 'ultracentrifugation')
# The percent bound of a record, from the first of these that is stated: (field, how the stated value becomes the percent bound).
BOUND_FROM = (('percent_bound', lambda value: value), ('percent_unbound', lambda value: PERCENT_FULL - value),
              ('fraction_bound', lambda value: value * PERCENT_FULL), ('fraction_unbound', lambda value: PERCENT_FULL - value * PERCENT_FULL))
# The percent unbound of a record, likewise.
UNBOUND_FROM = (('percent_unbound', lambda value: value), ('fraction_unbound', lambda value: value * PERCENT_FULL),
                ('percent_bound', lambda value: PERCENT_FULL - value), ('fraction_bound', lambda value: PERCENT_FULL - value * PERCENT_FULL))


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _scaled(record, name, scale):
    value = _value(record, name)
    return None if value is None else value * scale[record['quantities'][name]['unit']]


def _nm(record, name):
    return _scaled(record, name, NM_PER_UNIT)


def _refs(*items):
    refs = []
    for item in items:
        refs += item['source_refs']
    return list(dict.fromkeys(refs))


def _percent(record, sources):
    """(the percent, the refs of the field it comes from) from the first stated field of ``sources``, or (None, [])."""
    for name, convert in sources:
        value = _value(record, name)
        if value is not None:
            return convert(value), _refs(record['quantities'][name])
    return None, []


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


def _recorded_or_fact(record, native, quantity, fact_name, number_key, refs_key, handed):
    """A stated number is recorded with its refs for the sheet to judge; without it the fact decides."""
    value = _value(record, quantity)
    if value is None:
        return _one_fact(record, fact_name)
    native.update({number_key: value, refs_key: _refs(record['quantities'][quantity])})
    return _result('unknown', handed, [])


def _binding_observed(record, native):
    item = record['facts']['binding_detected']
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        outcome = _result(status, reason, item['source_refs'])
        native['interaction'] = INTERACTION.get(item['answer'])
        native['interaction_refs'] = list(item['source_refs']) if item['answer'] in INTERACTION else []
        return outcome
    percent, refs = _percent(record, BOUND_FROM)
    if percent is None:
        return _result('unknown', 'fact_unknown', [])
    native['percent_bound_refs'] = refs      # whether binding is shown, and so the qualitative statement, is the sheet's judgement of native['percent_bound']
    return _result('unknown', 'percent_bound_recorded_for_the_sheet', [])


def _equilibrium(record, native):
    item = record['facts']['equilibrium_time_course_shown']
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        return _result(status, reason, item['source_refs'])
    if record['separation_method'] in NOT_EQUILIBRIUM:
        return _result('not_applicable', 'method_is_not_equilibrium_dialysis', [])
    hours = native['equilibration_h']
    if hours is None:
        return _result('unknown', 'fact_unknown', [])
    native['equilibration_refs'] = _refs(record['quantities']['equilibration_time'])
    return _result('unknown', 'equilibration_time_recorded_for_the_sheet', [])


def _recovery(record, native):
    return _recorded_or_fact(record, native, 'recovery', 'recovery_checked', 'recovery_percent', 'recovery_refs', 'recovery_recorded_for_the_sheet')


def _device_adsorption(record, native):
    return _recorded_or_fact(record, native, 'membrane_adsorption', 'adsorption_checked_and_corrected', 'adsorption_percent', 'adsorption_refs', 'adsorption_recorded_for_the_sheet')


def _volume_shift(record, native):
    item = record['facts']['volume_shift_corrected']
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        return _result(status, reason, item['source_refs'])
    shift = _value(record, 'volume_shift')
    if shift is not None:
        native.update({'volume_shift_percent': shift, 'volume_shift_refs': _refs(record['quantities']['volume_shift'])})
        return _result('unknown', 'volume_shift_recorded_for_the_sheet', [])
    if native['salt_mM'] is None:
        return _result('unknown', 'fact_unknown', [])
    native['salt_refs'] = list(record['quantities']['salt_concentration']['source_refs'])
    return _result('unknown', 'salt_recorded_for_the_sheet', [])


def _ligand_stability(record, native):
    return _one_fact(record, 'ligand_stable')


def _free_measured_directly(record, native):
    return _one_fact(record, 'free_ligand_measured_directly')


def _protein_retained(record, native):
    return _one_fact(record, 'protein_retained')


def _buffer_only_control(record, native):
    return _one_fact(record, 'buffer_only_control_equal')


def _ligand_depletion(record, native):
    protein = native['protein_nM']
    bound, total, free = _nm(record, 'bound_ligand_concentration'), _nm(record, 'ligand_total_concentration'), _nm(record, 'free_ligand_concentration')
    if bound is not None:
        refs = _refs(record['quantities']['bound_ligand_concentration'])
    elif total is not None and free is not None and total > free:
        bound, refs = total - free, _refs(record['quantities']['ligand_total_concentration'], record['quantities']['free_ligand_concentration'])
    if bound is None or protein is None:
        return _result('unknown', 'bound_or_protein_concentration_not_given', [])
    native['bound_nM'] = bound
    native['bound_over_protein'] = bound / protein
    native['bound_over_protein_refs'] = _refs({'source_refs': refs}, record['quantities']['protein_concentration'])
    return _result('unknown', 'bound_over_protein_recorded_for_the_sheet', [])


def _protein_level(record, native):
    protein, kd = native['protein_nM'], native['kd_nM']
    if protein is None or kd is None:
        item = record['facts']['protein_at_or_above_kd']
        status, reason = _shared_rule([item['answer']])
        if status == 'unknown' and kd is None:
            return _result('not_applicable', 'no_kd_reported', [])
        return _result(status, reason, item['source_refs'])
    native['protein_over_kd'] = protein / kd
    native['protein_over_kd_refs'] = _refs(record['quantities']['protein_concentration'], record['quantities']['kd'])
    return _result('unknown', 'protein_over_kd_recorded_for_the_sheet', [])


def _free_fraction_measurable(record, native):
    percent, refs = _percent(record, UNBOUND_FROM)
    if percent is None:
        return _result('not_applicable', 'no_fraction_reported', [])
    native['percent_unbound_refs'] = refs
    return _result('unknown', 'percent_unbound_recorded_for_the_sheet', [])


def _concentration_series(record, native):
    kd = native['kd_nM']
    if kd is None and native['ki_nM'] is None:
        return _result('not_applicable', 'no_binding_constant_reported', [])
    series = record['concentration_series']
    values = series['value']
    counted = len(values) if values is not None else _value(record, 'titration_point_count')
    if counted is not None:
        native.update({'concentration_count': counted, 'concentration_count_refs': _refs(series, record['quantities']['titration_point_count'])})
    if values is not None:
        low, high = min(values) * NM_PER_UNIT[series['unit']], max(values) * NM_PER_UNIT[series['unit']]
        refs = _refs(series)
    else:
        low, high = _nm(record, 'ligand_range_lowest'), _nm(record, 'ligand_range_highest')
        refs = _refs(record['quantities']['ligand_range_lowest'], record['quantities']['ligand_range_highest'])
    if kd is None or low is None or high is None:
        # the count, when there is one, is still handed to the sheet; with neither a count nor a span nothing is recorded
        return _result('unknown', 'kd_or_series_missing' if counted is None else 'concentration_series_recorded_for_the_sheet', [])
    native.update({'concentration_low_over_kd': low / kd, 'concentration_high_over_kd': high / kd, 'concentration_span_refs': _refs({'source_refs': refs}, record['quantities']['kd'])})
    return _result('unknown', 'concentration_series_recorded_for_the_sheet', [])


def _fit_model(record, native):
    # the model is a statement about how the reported constants were obtained: their quoted spans are its support (the model
    # has no span of its own), and with no reported constant there is nothing to support it
    refs = _refs(*(record['quantities'][name] for name in REPORTED))
    if record['fit_model'] is None:
        return _result('unknown', 'fit_model_not_stated', []) if refs else _result('not_applicable', 'no_binding_constant_reported', [])
    if not refs:
        return _result('unknown', 'model_stated_without_a_reported_constant', [])
    return _result('supported', 'model_stated', refs)


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


EVALUATORS = {'binding_observed': _binding_observed, 'equilibrium': _equilibrium, 'recovery': _recovery, 'device_adsorption': _device_adsorption, 'volume_shift': _volume_shift, 'ligand_stability': _ligand_stability, 'free_measured_directly': _free_measured_directly, 'protein_retained': _protein_retained, 'buffer_only_control': _buffer_only_control, 'ligand_depletion': _ligand_depletion, 'protein_level': _protein_level, 'free_fraction_measurable': _free_fraction_measurable, 'concentration_series': _concentration_series, 'fit_model': _fit_model, 'replicates': _replicates}


def grade_dialysis(record):
    """Grade one dialysis / ultrafiltration binding experiment record. Returns the criterion answers and native values."""
    nm = {name: _nm(record, name) for name in CONSTANTS}
    constant_name = next((name for name in CONSTANTS if nm[name] is not None), None)
    bound_percent, _ = _percent(record, BOUND_FROM)
    unbound_percent, _ = _percent(record, UNBOUND_FROM)
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'separation_method': record['separation_method'], 'device_type': record['device_type'], 'detection': record['detection'], 'spread_kind': record['spread_kind'], 'fit_model': record['fit_model'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'kd_nM': nm['kd'], 'ki_nM': nm['ki'], 'constant_name': constant_name, 'constant_nM': None if constant_name is None else nm[constant_name], 'percent_bound': bound_percent, 'percent_unbound': unbound_percent, 'protein_nM': _nm(record, 'protein_concentration'), 'bound_nM': None, 'bound_over_protein': None, 'protein_over_kd': None, 'salt_mM': _scaled(record, 'salt_concentration', MM_PER_SALT_UNIT), 'equilibration_h': _scaled(record, 'equilibration_time', H_PER_UNIT), 'concentration_count': None, 'concentration_low_over_kd': None, 'concentration_high_over_kd': None, 'interaction': None, 'interaction_refs': [], 'percent_bound_refs': [], 'equilibration_refs': [], 'recovery_percent': None, 'recovery_refs': [], 'adsorption_percent': None, 'adsorption_refs': [], 'volume_shift_percent': None, 'volume_shift_refs': [], 'salt_refs': [], 'bound_over_protein_refs': [], 'protein_over_kd_refs': [], 'percent_unbound_refs': [], 'concentration_count_refs': [], 'concentration_span_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, DIALYSIS_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'dialysis', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
