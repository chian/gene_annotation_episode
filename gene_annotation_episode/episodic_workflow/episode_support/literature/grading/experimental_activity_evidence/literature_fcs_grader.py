"""FCS grader: judges ONE fluorescence correlation spectroscopy (or dual-colour cross-correlation) binding titration by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET, MST or Trp graders).
Deterministic; no model call, no store access.
Input: the record of one titration (forms/.../literature_fcs_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_fcs_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration, each reading its unit
conversions by name from that file.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on); ``_result``
refuses to build one without them. Where only a fact or a choice with no span would decide (the fit model with no reported KD), the
criterion returns 'unknown' with a declared reason.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(diffusion_ratio/diffusion_refs, expected_diffusion_ratio/mass_consistency_refs, fraction_bound_maximum/fraction_bound_maximum_refs,
particle_number (or labelled_nM with the detection volume, as a derived particle_number_used), count_rate_kHz (the particle number times the brightness) and labelled_range_refs, diffusion_time_scatter (the spread of the free diffusion time over that time), brightness_kHz and free_diffusion_time_us (for the acquisition), labelled_over_kd/tight_binding_analysis/labelled_over_kd_refs,
concentration_count/concentration_count_refs and the span over the KD/concentration_span_refs, incubation_min/incubation_refs,
acquisition_total_s/measurement_repeats_given/acquisition_refs, replicate_count/replicate_independent/replicate_refs) and returns 'unknown'
with a reason ending in '_recorded_for_the_sheet'; the FCS converter judges it. What stays with the grader is what a stated fact says (a stated
'no' is conflicting) and the choice among facts.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable):
any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. diffusion_change,
mass_consistency, saturation, diffusion_model, crosstalk, labelled_range,
labelled_over_kd, concentration_series, equilibrium, acquisition, fit_model and
replicates have their own rules (declared).

The reported constant of a series is the KD (native 'constant_name' says so, or None).

Support: native['support'] keeps, per criterion, the 'support' facts of the stated fields the criterion reads (from its declared 'reads';
literature_quote_support.criterion_supports). The grader only carries them; it never judges them and no status depends on them.

Native values retained: every record quantity as given, plus kd_nM, constant_name, constant_nM, labelled_nM,
labelled_over_kd, particle_number, diffusion_ratio, expected_diffusion_ratio, mass_ratio, incubation_min,
acquisition_total_s, concentration_count, concentration_low_over_constant, concentration_high_over_constant,
the recorded facts and refs named above, preparations, spread_kind, fit_model, diffusion_model and readout_signal.
The stated yes/no result (fact binding_detected) is kept as native 'interaction' ('detected', 'not_detected' or None),
with the spans that state it ('interaction_refs') and its quote support ('interaction_support'); the converter hands it to
the sheet as the experiment's stated result when the source gave no binding constant.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fcs_criteria import FCS_CRITERIA, MIN_PER_UNIT, NM_PER_UNIT, S_PER_UNIT, US_PER_UNIT, CUBE_ROOT_EXPONENT, PARTICLES_PER_NM_PER_FL

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_fcs_grade_v1'
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the stated yes/no result of the fact binding_detected
CRITERIA = tuple(criterion['id'] for criterion in FCS_CRITERIA)
CONSTANTS = ('kd',)       # the reported constant of a series: only a KD is a binding constant
SINGLE_COLOUR_READOUTS = ('diffusion_time', 'diffusion_coefficient', 'brightness')
NOT_THE_DIFFUSION = ('brightness', 'cross_correlation')


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _scaled(record, name, scale):
    value = _value(record, name)
    return None if value is None else value * scale[record['quantities'][name]['unit']]


def _nm(record, name):
    return _scaled(record, name, NM_PER_UNIT)


def _minutes(record, name):
    return _scaled(record, name, MIN_PER_UNIT)


def _seconds(record, name):
    return _scaled(record, name, S_PER_UNIT)


def _refs(*items):
    refs = []
    for item in items:
        refs += item['source_refs']
    return list(dict.fromkeys(refs))


def _answers(record, names):
    return [record['facts'][name]['answer'] for name in names]


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


def _diffusion_ratio(record):
    """(the slow-over-fast diffusion ratio, its refs): from the two times when both are given, else from the two coefficients."""
    free_time, bound_time = _scaled(record, 'free_diffusion_time', US_PER_UNIT), _scaled(record, 'bound_diffusion_time', US_PER_UNIT)
    if free_time is not None and bound_time is not None:
        return bound_time / free_time, _refs(record['quantities']['free_diffusion_time'], record['quantities']['bound_diffusion_time'])
    free_coefficient, bound_coefficient = _value(record, 'free_diffusion_coefficient'), _value(record, 'bound_diffusion_coefficient')
    if free_coefficient is not None and bound_coefficient is not None:
        return free_coefficient / bound_coefficient, _refs(record['quantities']['free_diffusion_coefficient'], record['quantities']['bound_diffusion_coefficient'])
    return None, []


def _diffusion_change(record, native):
    ratio, refs = _diffusion_ratio(record)
    if ratio is None:
        if record['readout_signal'] in NOT_THE_DIFFUSION:
            return _result('not_applicable', 'readout_is_not_the_diffusion', [])
        return _result('unknown', 'diffusion_values_not_given', [])
    native['diffusion_refs'] = refs
    spread, free_time = native['free_diffusion_time_spread_us'], native['free_diffusion_time_us']
    if spread is not None and free_time is not None:
        native['diffusion_time_scatter'] = spread / free_time      # the paper's own scatter of the free diffusion time, relative to that time
        native['diffusion_refs'] = list(dict.fromkeys(refs + _refs(record['quantities']['free_diffusion_time_spread'], record['quantities']['free_diffusion_time'])))
    return _result('unknown', 'diffusion_ratio_recorded_for_the_sheet', [])


def _mass_consistency(record, native):
    ratio, refs = _diffusion_ratio(record)
    mass = _value(record, 'mass_ratio')
    if ratio is None or mass is None:
        if ratio is None and mass is None and record['readout_signal'] in NOT_THE_DIFFUSION:
            return _result('not_applicable', 'readout_is_not_the_diffusion', [])
        return _result('unknown', 'mass_ratio_or_diffusion_not_given', [])
    expected = mass ** CUBE_ROOT_EXPONENT
    native['expected_diffusion_ratio'] = expected
    native['mass_consistency_refs'] = list(dict.fromkeys(_refs(record['quantities']['mass_ratio']) + refs))
    return _result('unknown', 'mass_consistency_recorded_for_the_sheet', [])


def _saturation(record, native):
    maximum = _value(record, 'fraction_bound_maximum')
    if maximum is None:
        return _result('unknown', 'fraction_bound_maximum_not_given', [])
    native.update({'fraction_bound_maximum': maximum, 'fraction_bound_maximum_refs': _refs(record['quantities']['fraction_bound_maximum'])})
    return _result('unknown', 'fraction_bound_maximum_recorded_for_the_sheet', [])


def _diffusion_model(record, native):
    model = record['diffusion_model']
    if model is None:
        if record['readout_signal'] in NOT_THE_DIFFUSION:
            return _result('not_applicable', 'readout_is_not_the_diffusion', [])
        return _result('unknown', 'diffusion_model_not_stated', [])
    if model == 'two_component':
        fixed = record['facts']['free_diffusion_time_fixed']
        if fixed['answer'] == 'yes':
            return _result('supported', 'two_component_with_free_time_fixed', fixed['source_refs'])
        if fixed['answer'] == 'no':
            return _result('conflicting', 'two_component_with_free_time_not_fixed', fixed['source_refs'])
        return _result('unknown', 'free_time_fixing_not_stated', [])
    if model == 'one_component':
        ratio, refs = _diffusion_ratio(record)
        if ratio is None:
            return _result('unknown', 'one_component_needs_free_and_bound_reference_values', [])
        return _result('supported', 'one_component_with_reference_values', refs)
    return _result('unknown', 'diffusion_model_anomalous_or_other', [])


def _triplet_state(record, native):
    return _one_fact(record, 'triplet_state_modelled')


def _volume_calibration(record, native):
    return _one_fact(record, 'confocal_volume_calibrated')


def _brightness(record, native):
    return _one_fact(record, 'brightness_change_accounted')


def _crosstalk(record, native):
    item = record['facts']['crosstalk_corrected']
    if item['answer'] == 'unknown' and record['readout_signal'] in SINGLE_COLOUR_READOUTS:
        return _result('not_applicable', 'single_colour_readout', [])
    return _one_fact(record, 'crosstalk_corrected')


def _background(record, native):
    return _one_fact(record, 'background_corrected')


def _aggregates(record, native):
    return _one_fact(record, 'aggregates_checked')


def _photobleaching(record, native):
    return _one_fact(record, 'photobleaching_or_saturation_checked')


def _surface_adsorption(record, native):
    return _one_fact(record, 'surface_adsorption_prevented')


def _labelling(record, native):
    return _one_fact(record, 'labelling_does_not_alter_binding')


def _specificity_control(record, native):
    return _one_fact(record, 'nonbinding_control_done')


def _labelled_range(record, native):
    particles, labelled, volume = native['particle_number'], native['labelled_nM'], _value(record, 'detection_volume')
    brightness = native['brightness_kHz']
    if particles is not None:
        native['particle_number_used'] = particles
        refs, reason = _refs(record['quantities']['particle_number']), 'particle_number_recorded_for_the_sheet'
    elif labelled is not None and volume is not None:
        native['particle_number_used'], native['particle_number_derived'] = labelled * volume * PARTICLES_PER_NM_PER_FL, True      # a unit conversion of two stated values
        refs, reason = _refs(record['quantities']['labelled_concentration'], record['quantities']['detection_volume']), 'particle_number_derived_from_volume_recorded_for_the_sheet'
    elif labelled is None:
        return _result('unknown', 'labelled_concentration_not_given', [])
    else:
        native['labelled_range_refs'] = _refs(record['quantities']['labelled_concentration'])
        return _result('unknown', 'labelled_concentration_recorded_for_the_sheet', [])
    if brightness is not None:
        native['count_rate_kHz'] = native['particle_number_used'] * brightness      # the total count rate the detector sees
        refs = list(dict.fromkeys(refs + _refs(record['quantities']['brightness'])))
    native['labelled_range_refs'] = refs
    return _result('unknown', reason, [])


def _labelled_over_kd(record, native):
    labelled, kd = native['labelled_nM'], native['kd_nM']
    below = record['facts']['labelled_partner_at_or_below_kd']
    tight = record['facts']['tight_binding_considered']
    tight_analysis = record['fit_model'] == 'quadratic' or tight['answer'] == 'yes'
    if labelled is not None and kd is not None:
        native.update({'labelled_over_kd': labelled / kd, 'tight_binding_analysis': tight_analysis,
                       'labelled_over_kd_refs': _refs(record['quantities']['labelled_concentration'], record['quantities']['kd'], tight)})
        return _result('unknown', 'labelled_over_kd_recorded_for_the_sheet', [])
    if below['answer'] not in ('yes', 'no'):
        return _result('unknown', 'labelled_or_kd_missing', [])
    refs = _refs(below, tight)
    if below['answer'] == 'yes':
        return _result('supported', 'labelled_at_or_below_kd', _refs(below))
    if tight_analysis:
        return _result('supported', 'labelled_above_kd_with_tight_binding_analysis', refs)
    return _result('conflicting', 'labelled_above_kd_without_tight_binding_analysis', refs)


def _concentration_series(record, native):
    constant = native['constant_nM']
    series = record['concentration_series']
    values = series['value']
    counted = len(values) if values is not None else _value(record, 'titration_point_count')
    refs = _refs(series, record['quantities']['titration_point_count'])
    if counted is None:
        return _result('unknown', 'kd_or_series_missing', [])
    native.update({'concentration_count': counted, 'concentration_count_refs': refs})
    if constant is not None and values is not None:
        nm = [v * NM_PER_UNIT[series['unit']] for v in values]
        native.update({'concentration_low_over_constant': min(nm) / constant, 'concentration_high_over_constant': max(nm) / constant,
                       'concentration_span_refs': _refs(series, record['quantities']['kd'])})
    return _result('unknown', 'concentration_series_recorded_for_the_sheet', [])


def _equilibrium(record, native):
    item = record['facts']['equilibrium_reached']
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        return _result(status, reason, item['source_refs'])
    if native['incubation_min'] is None:
        return _result('unknown', 'fact_unknown', [])
    native['incubation_refs'] = _refs(record['quantities']['incubation_time'])
    return _result('unknown', 'incubation_recorded_for_the_sheet', [])


def _acquisition(record, native):
    seconds = native['measurement_s']
    if seconds is None:
        return _result('unknown', 'measurement_time_not_given', [])
    repeats = _value(record, 'measurement_repeat_count')
    native['acquisition_total_s'] = seconds * (repeats if repeats is not None else 1)
    native.update({'measurement_repeats_given': repeats is not None, 'acquisition_refs': _refs(record['quantities']['measurement_time'], record['quantities']['measurement_repeat_count'], record['quantities']['brightness'], record['quantities']['free_diffusion_time'])})
    return _result('unknown', 'acquisition_recorded_for_the_sheet', [])


def _fit_model(record, native):
    if record['fit_model'] is None:
        return _result('unknown', 'fit_model_not_stated', [])
    # the model is a statement about how the reported constant was obtained: its quoted span is its support, and with no reported KD
    # there is no span to support it
    refs = _refs(record['quantities']['kd'])
    if not refs:
        return _result('unknown', 'model_stated_without_a_reported_kd', [])
    return _result('supported', 'model_stated', refs)


def _replicates(record, native):
    count = _value(record, 'replicate_count')
    independent = record['facts']['independent_titrations']
    refs = _refs(record['quantities']['replicate_count'], independent)
    if independent['answer'] == 'no':
        return _result('conflicting', 'replicates_not_independent', refs)
    if count is None:
        return _result('unknown', 'replicate_count_or_independence_unknown', [])
    native.update({'replicate_count': count, 'replicate_independent': independent['answer'], 'replicate_refs': refs})
    return _result('unknown', 'replicate_count_recorded_for_the_sheet', [])


EVALUATORS = {'diffusion_change': _diffusion_change, 'mass_consistency': _mass_consistency, 'saturation': _saturation, 'diffusion_model': _diffusion_model, 'triplet_state': _triplet_state, 'volume_calibration': _volume_calibration, 'brightness': _brightness, 'crosstalk': _crosstalk, 'background': _background, 'aggregates': _aggregates, 'photobleaching': _photobleaching, 'surface_adsorption': _surface_adsorption, 'labelling': _labelling, 'specificity_control': _specificity_control, 'labelled_range': _labelled_range, 'labelled_over_kd': _labelled_over_kd, 'concentration_series': _concentration_series, 'equilibrium': _equilibrium, 'acquisition': _acquisition, 'fit_model': _fit_model, 'replicates': _replicates}


def grade_fcs(record):
    """Grade one FCS binding titration record. Returns the criterion answers and native values."""
    nm = {name: _nm(record, name) for name in CONSTANTS}
    constant_name = next((name for name in CONSTANTS if nm[name] is not None), None)
    ratio, _ = _diffusion_ratio(record)
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'spread_kind': record['spread_kind'], 'fit_model': record['fit_model'], 'diffusion_model': record['diffusion_model'], 'readout_signal': record['readout_signal'], 'choice_support': dict(record['choice_support']), 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'kd_nM': nm['kd'], 'constant_name': constant_name, 'constant_nM': None if constant_name is None else nm[constant_name], 'labelled_nM': _nm(record, 'labelled_concentration'), 'labelled_over_kd': None, 'particle_number': _value(record, 'particle_number'), 'diffusion_ratio': ratio, 'expected_diffusion_ratio': None, 'mass_ratio': _value(record, 'mass_ratio'), 'incubation_min': _minutes(record, 'incubation_time'), 'measurement_s': _seconds(record, 'measurement_time'), 'acquisition_total_s': None, 'concentration_count': None, 'concentration_low_over_constant': None, 'concentration_high_over_constant': None, 'diffusion_refs': [], 'free_diffusion_time_us': _scaled(record, 'free_diffusion_time', US_PER_UNIT), 'free_diffusion_time_spread_us': _scaled(record, 'free_diffusion_time_spread', US_PER_UNIT), 'diffusion_time_scatter': None, 'brightness_kHz': _value(record, 'brightness'), 'particle_number_used': None, 'particle_number_derived': False, 'count_rate_kHz': None, 'mass_consistency_refs': [], 'fraction_bound_maximum': None, 'fraction_bound_maximum_refs': [], 'labelled_range_refs': [], 'tight_binding_analysis': None, 'labelled_over_kd_refs': [], 'concentration_count_refs': [], 'concentration_span_refs': [], 'incubation_refs': [], 'measurement_repeats_given': None, 'acquisition_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    stated = record['facts']['binding_detected']      # the experiment's stated yes/no result: a fact kept for the sheet, read by no criterion
    known = stated['answer'] in INTERACTION
    native.update({'interaction': INTERACTION.get(stated['answer']), 'interaction_refs': list(stated['source_refs']) if known else [], 'interaction_support': stated['support'] if known else None})
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, FCS_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'fcs', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
