"""FRET grader: judges ONE FRET / TR-FRET binding experiment (in solution) by FRET's own standards.

Hand-built and private to FRET (it shares no grading logic with the SPR, ITC, BLI, GCI or FP graders).
Deterministic; no model call, no store access.
Input: the record of one FRET experiment (forms/.../literature_fret_record.py).
Output: for each FRET criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_fret_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration, each reading its thresholds
by name from that file.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs (ratio_fold/window_refs,
delay_us/integration_us/gating_refs, labelled_over_kd/labelled_refs/tight_binding_handled, concentration_count and the low/high over the constant/series_refs,
incubation_min/incubation_refs, replicate_count/replicate_independent/replicate_refs, estimate_fold/estimate_refs) and returns 'unknown' with a reason ending in
'_recorded_for_the_sheet'; the FRET converter judges it.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable):
any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. The criteria that ask
whether EITHER of two controls was done (specificity_control) take a 'yes' of
either as enough, and otherwise use the shared rule; spectral_crosstalk takes a
stated correction as enough; time_gating and labelling_scheme have their own
rules (declared).

The reported constant of a series is the KD of a direct titration, else the Ki of
a competition, else the EC50, else the IC50 (native 'constant_name' says which).
The labelled concentration is judged against the KD only (a Ki is not the labelled
partner's KD).

Native values retained: every record quantity as given, plus kd_nM, ki_nM,
ec50_nM, ic50_nM, constant_name, constant_nM, labelled_nM (the limiting labelled
partner), labelled_over_kd, ratio_fold, delay_us, integration_us, incubation_min,
concentration_count, concentration_low_over_constant,
concentration_high_over_constant, preparations, assay_format, spread_kind,
fit_model, plate_type, donor_acceptor_pair, donor_lanthanide, series_format, z_prime and koff_per_s.
The stated yes/no result (fact binding_detected) is kept as native 'interaction' ('detected', 'not_detected' or None),
with the spans that state it ('interaction_refs') and its quote support ('interaction_support'); the converter hands it to
the sheet as the experiment's stated result when the source gave no binding constant.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fret_criteria import FRET_CRITERIA, MIN_PER_UNIT, NM_PER_UNIT, PER_S_PER_UNIT, US_PER_UNIT

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_fret_grade_v1'
INTERACTION = {'yes': 'detected', 'no': 'not_detected'}   # the stated yes/no result of the fact binding_detected
CRITERIA = tuple(criterion['id'] for criterion in FRET_CRITERIA)
CONSTANTS = ('kd', 'ki', 'ec50', 'ic50')       # the order in which a series' reported constant is taken
SHORT_LIVED_PAIRS = ('fluorescent_protein_pair', 'organic_dye_pair')


def _value(record, name):
    operand = record['quantities'][name]
    return operand['value'] if operand['status'] == 'point' else None


def _nm(record, name):
    value = _value(record, name)
    return None if value is None else value * NM_PER_UNIT[record['quantities'][name]['unit']]


def _minutes(record, name):
    value = _value(record, name)
    return None if value is None else value * MIN_PER_UNIT[record['quantities'][name]['unit']]


def _us(record, name):
    value = _value(record, name)
    return None if value is None else value * US_PER_UNIT[record['quantities'][name]['unit']]


def _per_s(record, name):
    value = _value(record, name)
    return None if value is None else value * PER_S_PER_UNIT[record['quantities'][name]['unit']]


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
    return {'status': status, 'reason': reason, 'support_refs': refs if status in ('supported', 'conflicting') else []}


def _one_fact(record, name):
    item = record['facts'][name]
    status, reason = _shared_rule([item['answer']])
    return _result(status, reason, item['source_refs'])


def _assay_window(record, native):
    low, high, z_prime = _value(record, 'ratio_minimum'), _value(record, 'ratio_maximum'), _value(record, 'z_prime')
    if (low is None or high is None) and z_prime is None:
        return _result('unknown', 'minimum_or_maximum_missing', [])
    refs = _refs(record['quantities']['z_prime']) if low is None or high is None else _refs(record['quantities']['ratio_minimum'], record['quantities']['ratio_maximum'], record['quantities']['z_prime'])
    native.update({'ratio_fold': None if low is None or high is None else high / low, 'z_prime': z_prime, 'window_refs': refs})
    return _result('unknown', 'window_recorded_for_the_sheet', [])


def _ratiometric_readout(record, native):
    return _one_fact(record, 'ratiometric_readout_used')


def _spectral_crosstalk(record, native):
    names = ('donor_only_control_measured', 'acceptor_only_control_measured')
    corrected = record['facts']['crosstalk_corrected']
    refs = _refs(corrected, *(record['facts'][n] for n in names))
    if corrected['answer'] == 'yes':
        return _result('supported', 'crosstalk_corrected', refs)
    if corrected['answer'] == 'no':
        return _result('conflicting', 'fact_answered_no', refs)
    status, reason = _shared_rule(_answers(record, names))
    if status == 'not_applicable' and corrected['answer'] != 'not_applicable':
        status, reason = 'unknown', 'fact_unknown'      # the controls do not apply but the correction is not stated
    return _result(status, reason, refs)


def _time_gating(record, native):
    item = record['facts']['time_resolved_read']
    delay = native['delay_us']
    refs = _refs(item, record['quantities']['delay_time'], record['quantities']['integration_time'])
    if item['answer'] == 'no':
        return _result('not_applicable', 'not_time_resolved', [])
    if item['answer'] == 'not_applicable':
        return _result('not_applicable', 'fact_not_applicable', [])
    if item['answer'] == 'unknown' and delay is None:
        return _result('unknown', 'time_resolved_read_not_stated', [])
    if record['donor_acceptor_pair'] in SHORT_LIVED_PAIRS:
        return _result('conflicting', 'time_gating_with_short_lived_donor', refs)
    if delay is None:
        return _result('unknown', 'delay_not_stated', [])
    native['gating_refs'] = refs
    return _result('unknown', 'gating_recorded_for_the_sheet', [])


def _labelled_concentration(record, native):
    labelled, kd = native['labelled_nM'], native['kd_nM']
    below = record['facts']['labelled_partner_at_or_below_kd']
    tight = record['facts']['tight_binding_considered']
    refs = _refs(record['quantities']['donor_concentration'], record['quantities']['acceptor_concentration'], record['quantities']['kd'], below, tight)
    handled = record['fit_model'] == 'quadratic' or tight['answer'] == 'yes'
    if labelled is not None and kd is not None:
        native.update({'labelled_over_kd': labelled / kd, 'labelled_refs': refs, 'tight_binding_handled': handled})
        return _result('unknown', 'labelled_over_kd_recorded_for_the_sheet', [])
    if below['answer'] in ('yes', 'no'):
        above = below['answer'] == 'no'
    else:
        return _result('unknown', 'labelled_or_kd_missing', [])
    if not above:
        return _result('supported', 'labelled_at_or_below_kd', refs)
    if handled:
        return _result('supported', 'labelled_above_kd_with_tight_binding_analysis', refs)
    return _result('conflicting', 'labelled_above_kd_without_tight_binding_analysis', refs)


def _concentration_series(record, native):
    constant = native['constant_nM']
    series = record['concentration_series']
    values = series['value']
    if constant is None or values is None:
        return _result('unknown', 'constant_or_series_missing', [])
    scale = NM_PER_UNIT[series['unit']]
    nm = [v * scale for v in values]
    native.update({'concentration_count': len(nm), 'concentration_low_over_constant': min(nm) / constant, 'concentration_high_over_constant': max(nm) / constant,
                   'series_refs': _refs(series, record['quantities'][native['constant_name']])})
    return _result('unknown', 'series_recorded_for_the_sheet', [])


def _equilibrium(record, native):
    item = record['facts']['equilibrium_reached']
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        return _result(status, reason, item['source_refs'])
    minutes = native['incubation_min']
    if minutes is None:
        return _result('unknown', 'fact_unknown', [])
    koff = native['koff_per_s']
    scale = record['quantities']['koff'] if koff is not None else record['quantities'][native['constant_name']] if native['constant_name'] is not None else None     # what the sheet scales the time against: the stated koff, else the reported constant
    native['incubation_refs'] = _refs(record['quantities']['incubation_time'], *([] if scale is None else [scale]))
    return _result('unknown', 'incubation_recorded_for_the_sheet', [])


def _labelling_scheme(record, native):
    indirect, harmless = record['facts']['indirect_labelling_used'], record['facts']['labelling_does_not_alter_binding']
    refs = _refs(indirect, harmless)
    if harmless['answer'] == 'no':
        return _result('conflicting', 'labelling_alters_binding', refs)
    if harmless['answer'] == 'yes':
        return _result('supported', 'labelling_shown_not_to_alter_binding', refs)
    if indirect['answer'] == 'no':
        return _result('supported', 'direct_labelling', refs)
    if indirect['answer'] == 'yes':
        return _result('unknown', 'indirect_labelling_not_shown_harmless', [])
    if indirect['answer'] == 'not_applicable' and harmless['answer'] == 'not_applicable':
        return _result('not_applicable', 'fact_not_applicable', [])
    return _result('unknown', 'labelling_not_stated', [])


def _compound_interference(record, native):
    return _one_fact(record, 'compound_interference_checked')


def _specificity_control(record, native):
    names = ('nonspecific_binding_checked', 'unlabelled_competitor_displaces')
    answers = _answers(record, names)
    refs = _refs(*(record['facts'][n] for n in names))
    if 'yes' in answers:
        return _result('supported', 'specificity_control_stated', refs)
    status, reason = _shared_rule(answers)
    return _result(status, reason, refs)


def _fit_model(record, native):
    model, form = record['fit_model'], record['assay_format']
    if model is None:
        return _result('unknown', 'fit_model_not_stated', [])
    if model == 'competitive_binding' and form == 'direct_titration':
        return _result('conflicting', 'competition_model_for_direct_titration', [])
    if model in ('1:1', 'hill') and form == 'competition':
        return _result('conflicting', 'direct_model_for_competition', [])
    # the model is a statement about how the reported constants were obtained: their quoted spans are its support
    return _result('supported', 'model_stated', _refs(record['quantities']['kd'], record['quantities']['ki']))


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


def _direct_vs_competition(record, native):
    kd, ki = native['kd_nM'], native['ki_nM']
    if kd is None or ki is None:
        if record['facts']['single_estimate_method']['answer'] == 'yes':
            return _result('not_applicable', 'single_estimate_method', record['facts']['single_estimate_method']['source_refs'])
        return _result('unknown', 'kd_or_ki_missing', [])
    native.update({'estimate_fold': max(kd, ki) / min(kd, ki), 'estimate_refs': _refs(record['quantities']['kd'], record['quantities']['ki'])})
    return _result('unknown', 'estimates_recorded_for_the_sheet', [])


EVALUATORS = {'assay_window': _assay_window, 'ratiometric_readout': _ratiometric_readout, 'spectral_crosstalk': _spectral_crosstalk, 'time_gating': _time_gating, 'labelled_concentration': _labelled_concentration, 'concentration_series': _concentration_series, 'equilibrium': _equilibrium, 'labelling_scheme': _labelling_scheme, 'compound_interference': _compound_interference, 'specificity_control': _specificity_control, 'fit_model': _fit_model, 'replicates': _replicates, 'direct_vs_competition': _direct_vs_competition}


def grade_fret(record):
    """Grade one FRET experiment record. Returns the criterion answers and native values."""
    nm = {name: _nm(record, name) for name in CONSTANTS}
    constant_name = next((name for name in CONSTANTS if nm[name] is not None), None)
    labelled = [value for value in (_nm(record, 'donor_concentration'), _nm(record, 'acceptor_concentration')) if value is not None]
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'assay_format': record['assay_format'], 'spread_kind': record['spread_kind'], 'fit_model': record['fit_model'], 'plate_type': record['plate_type'], 'donor_acceptor_pair': record['donor_acceptor_pair'], 'donor_lanthanide': record['donor_lanthanide'], 'series_format': record['series_format'], 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'kd_nM': nm['kd'], 'ki_nM': nm['ki'], 'ec50_nM': nm['ec50'], 'ic50_nM': nm['ic50'], 'constant_name': constant_name, 'constant_nM': None if constant_name is None else nm[constant_name], 'labelled_nM': min(labelled) if labelled else None, 'labelled_over_kd': None, 'ratio_fold': None, 'z_prime': None, 'koff_per_s': _per_s(record, 'koff'), 'delay_us': _us(record, 'delay_time'), 'integration_us': _us(record, 'integration_time'), 'incubation_min': _minutes(record, 'incubation_time'), 'concentration_count': None, 'concentration_low_over_constant': None, 'concentration_high_over_constant': None, 'window_refs': [], 'gating_refs': [], 'labelled_refs': [], 'tight_binding_handled': None, 'series_refs': [], 'incubation_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': [], 'estimate_fold': None, 'estimate_refs': []}
    native['support'] = criterion_supports(record, FRET_CRITERIA)      # kept for the sheet: criterion -> supports of the stated fields it reads; the grader does not judge them
    stated = record['facts']['binding_detected']      # the experiment's stated yes/no result: a fact kept for the sheet, read by no criterion
    known = stated['answer'] in INTERACTION
    native.update({'interaction': INTERACTION.get(stated['answer']), 'interaction_refs': list(stated['source_refs']) if known else [], 'interaction_support': stated['support'] if known else None})
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    return {'version': VERSION, 'experiment_type': 'fret', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
