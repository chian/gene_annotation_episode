"""AlphaScreen grader: judges ONE AlphaScreen / AlphaLISA binding experiment (bead-based proximity luminescence, titration, cross-titration or competition) by its own standards.

Hand-built and private to this method (it shares no grading logic with the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS or ELISA graders).
Deterministic; no model call, no store access.
Input: the record of one experiment (forms/.../literature_alpha_record.py).
Output: for each criterion an interpretation status in the existing A105
vocabulary (supported / unknown / conflicting / not_applicable) with support
refs, the reason code that decided it, and the native values retained.

WHAT each criterion asks, its rule in words, its threshold constants and the
status it returns in each case are declared in literature_alpha_criteria.py (the
single source). This file only evaluates them: one short function per
criterion, in the same order as the declaration, each reading its unit
conversions by name from that file.

A criterion returns 'supported' or 'conflicting' only with support refs (the quoted spans of the stated fields it rests on);
``_result`` refuses to build one without them. Where only a fact with no span or a model with no reported constant would decide, the
criterion returns 'unknown' with a declared reason.

The grader holds NO threshold that judges goodness. Where a number would be compared with a limit it records the number with its refs
(signal_over_background/signal_window_refs, z_prime/z_prime_refs, incubation_min/incubation_refs, concentration_count/concentration_count_refs
and the span over the constant/concentration_span_refs, estimate_fold/estimate_refs, replicate_count/replicate_independent/replicate_refs) and
returns 'unknown' with a reason ending in '_recorded_for_the_sheet'; the AlphaScreen converter judges it. What stays with the grader is what a
stated fact says (a stated 'no' is conflicting) and the choice among facts.

Shared rule for yes/no facts (answers yes / no / unknown / not_applicable):
any 'no' -> conflicting; else any 'unknown' -> unknown; else all
'not_applicable' -> not_applicable; else supported. signal_window,
assay_quality, equilibrium, concentration_series, fit_model,
direct_vs_competition and replicates have their own rules (declared).

The reported constant of a series is the apparent KD of a saturation titration, else the Ki, else the EC50, else the IC50 (native
'constant_name' says which). An EC50 or an IC50 is a half-maximal concentration, not a dissociation constant: it serves to judge
the span of the series and is never the binding constant of the converter.

Support: native['support'] keeps, per criterion, the 'support' facts of the stated fields the criterion reads (from its declared 'reads';
literature_quote_support.criterion_supports). The grader only carries them; it never judges them and no status depends on them.

Partner depletion: the fact decides when stated; otherwise, with a reported constant, a design that is not a cross-titration and a stated partner
concentration (the partners of the record are held at a constant concentration), the largest partner concentration over the constant is recorded
(partner_over_constant, partner_name, partner_refs) and the sheet judges it. Equilibrium: incubation_min is the time the partners were together (the incubation before
the beads plus the step after the beads when stated); with only the step after the beads stated it is None.

Native values retained: every record quantity as given, plus kd_nM, ki_nM, ec50_nM, ic50_nM, constant_name, constant_nM,
signal_over_background, incubation_min, partner_over_constant, concentration_count, concentration_low_over_constant, concentration_high_over_constant,
the recorded facts and refs named above, preparations, assay_format, titration_design, donor_bead, acceptor_bead, spread_kind and fit_model.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_criteria import ALPHA_CRITERIA, MIN_PER_UNIT, NM_PER_UNIT

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import criterion_supports

VERSION = 'a105_alphascreen_grade_v1'
CRITERIA = tuple(criterion['id'] for criterion in ALPHA_CRITERIA)
CONSTANTS = ('kd', 'ki', 'ec50', 'ic50')       # the order in which a series' reported constant is taken
DIRECT_MODELS = ('one_site', 'quadratic', 'bell_shaped_hook')    # models of a titration, not of a competition
PARTNER_CONCENTRATIONS = ('labelled_partner_concentration', 'tagged_partner_concentration')    # the partners held at a constant concentration


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


def _total_incubation_min(record):
    """The time the partners were together before the read, in minutes: the incubation before the beads plus the step after the beads when that is stated too.
    None when the incubation before the beads is not stated (the step after the beads alone leaves the time before it unknown)."""
    before = _minutes(record, 'incubation_time')
    if before is None:
        return None
    return before + (_minutes(record, 'bead_incubation_time') or 0.0)


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


def _signal_window(record, native):
    stated = _value(record, 'signal_to_background')
    maximum, background = _value(record, 'signal_maximum'), _value(record, 'signal_background')
    if stated is not None:
        native['signal_over_background'] = stated
        refs = _refs(record['quantities']['signal_to_background'])
    elif maximum is not None and background is not None:
        native['signal_over_background'] = maximum / background
        refs = _refs(record['quantities']['signal_maximum'], record['quantities']['signal_background'])
    else:
        return _result('unknown', 'signal_window_not_given', [])
    native['signal_window_refs'] = refs
    return _result('unknown', 'signal_window_recorded_for_the_sheet', [])


def _assay_quality(record, native):
    z_prime = _value(record, 'z_prime')
    if z_prime is None:
        return _result('unknown', 'z_prime_not_given', [])
    native.update({'z_prime': z_prime, 'z_prime_refs': _refs(record['quantities']['z_prime'])})
    return _result('unknown', 'z_prime_recorded_for_the_sheet', [])


def _detector_range(record, native):
    return _one_fact(record, 'signal_in_linear_range')


def _interference_counter_screen(record, native):
    return _one_fact(record, 'counter_screen_done')


def _hook_effect(record, native):
    return _one_fact(record, 'hook_effect_handled')


def _partner_depletion(record, native):
    item = record['facts']['partner_concentration_below_kd']
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        return _result(status, reason, item['source_refs'])
    constant = native['constant_nM']
    # a cross-titration titrates both partners: none is held at a constant concentration, so a stated partner concentration is not a depleting one
    if constant is None or record['titration_design'] == 'cross_titration':
        return _result('unknown', 'fact_unknown', [])
    stated = [(name, _nm(record, name)) for name in PARTNER_CONCENTRATIONS if _nm(record, name) is not None]
    if not stated:
        return _result('unknown', 'fact_unknown', [])
    name, largest = max(stated, key=lambda pair: pair[1])      # the partner that can deplete the titrated one most
    native.update({'partner_over_constant': largest / constant, 'partner_name': name, 'partner_refs': _refs(record['quantities'][name], record['quantities'][native['constant_name']])})
    return _result('unknown', 'partner_concentration_recorded_for_the_sheet', [])


def _equilibrium(record, native):
    item = record['facts']['equilibrium_reached']
    status, reason = _shared_rule([item['answer']])
    if status != 'unknown':
        return _result(status, reason, item['source_refs'])
    if native['incubation_min'] is None:
        return _result('unknown', 'fact_unknown', [])
    # the partners go on binding while the beads are on: the time together is the step before the beads plus the step after them when that is stated
    steps = [record['quantities'][name] for name in ('incubation_time', 'bead_incubation_time') if _value(record, name) is not None]
    native['incubation_refs'] = _refs(*steps)
    return _result('unknown', 'incubation_recorded_for_the_sheet', [])


def _specificity_control(record, native):
    return _one_fact(record, 'nonspecific_binding_checked')


def _capture_artifacts(record, native):
    return _one_fact(record, 'capture_does_not_alter_binding')


def _light_protection(record, native):
    return _one_fact(record, 'light_protected')


def _avidity(record, native):
    return _one_fact(record, 'avidity_excluded')


def _concentration_series(record, native):
    constant = native['constant_nM']
    series = record['concentration_series']
    values = series['value']
    counted = len(values) if values is not None else _value(record, 'titration_point_count')
    refs = _refs(series, record['quantities']['titration_point_count'])
    if counted is None:
        return _result('unknown', 'constant_or_series_missing', [])
    native.update({'concentration_count': counted, 'concentration_count_refs': refs})
    if constant is not None and values is not None:
        nm = [v * NM_PER_UNIT[series['unit']] for v in values]
        native.update({'concentration_low_over_constant': min(nm) / constant, 'concentration_high_over_constant': max(nm) / constant,
                       'concentration_span_refs': _refs(series, record['quantities'][native['constant_name']])})
    return _result('unknown', 'concentration_series_recorded_for_the_sheet', [])


def _fit_model(record, native):
    model, form = record['fit_model'], record['assay_format']
    if model is None:
        return _result('unknown', 'fit_model_not_stated', [])
    # the model is a statement about how the reported constants were obtained: their quoted spans are its support (the model
    # has no span of its own), and with no reported constant there is nothing to support either a verdict for or against it
    refs = _refs(*(record['quantities'][name] for name in CONSTANTS))
    if not refs:
        return _result('unknown', 'model_stated_without_a_reported_constant', [])
    if model == 'competitive_binding' and form == 'saturation_titration':
        return _result('conflicting', 'competition_model_for_saturation_titration', refs)
    if model in DIRECT_MODELS and form == 'competition':
        return _result('conflicting', 'direct_model_for_competition', refs)
    return _result('supported', 'model_stated', refs)


def _direct_vs_competition(record, native):
    kd, ki = native['kd_nM'], native['ki_nM']
    if kd is None or ki is None:
        if record['facts']['single_estimate_method']['answer'] == 'yes':
            return _result('not_applicable', 'single_estimate_method', record['facts']['single_estimate_method']['source_refs'])
        return _result('unknown', 'kd_or_ki_missing', [])
    native.update({'estimate_fold': max(kd, ki) / min(kd, ki), 'estimate_refs': _refs(record['quantities']['kd'], record['quantities']['ki'])})
    return _result('unknown', 'estimates_recorded_for_the_sheet', [])


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


EVALUATORS = {'signal_window': _signal_window, 'assay_quality': _assay_quality, 'detector_range': _detector_range, 'interference_counter_screen': _interference_counter_screen, 'hook_effect': _hook_effect, 'partner_depletion': _partner_depletion, 'equilibrium': _equilibrium, 'specificity_control': _specificity_control, 'capture_artifacts': _capture_artifacts, 'light_protection': _light_protection, 'avidity': _avidity, 'concentration_series': _concentration_series, 'fit_model': _fit_model, 'direct_vs_competition': _direct_vs_competition, 'replicates': _replicates}


def grade_alpha(record):
    """Grade one AlphaScreen / AlphaLISA binding experiment record. Returns the criterion answers and native values."""
    nm = {name: _nm(record, name) for name in CONSTANTS}
    constant_name = next((name for name in CONSTANTS if nm[name] is not None), None)
    native = {'experiment_ref': record['experiment_ref'], 'source_ref': record['source_ref'], 'assertion_ref': record['assertion_ref'], 'preparations': dict(record['preparations']), 'assay_format': record['assay_format'], 'titration_design': record['titration_design'], 'donor_bead': record['donor_bead'], 'acceptor_bead': record['acceptor_bead'], 'spread_kind': record['spread_kind'], 'fit_model': record['fit_model'], 'choice_support': dict(record['choice_support']), 'quantities': {name: dict(operand) for name, operand in record['quantities'].items()}, 'concentration_series': dict(record['concentration_series']), 'kd_nM': nm['kd'], 'ki_nM': nm['ki'], 'ec50_nM': nm['ec50'], 'ic50_nM': nm['ic50'], 'constant_name': constant_name, 'constant_nM': None if constant_name is None else nm[constant_name], 'signal_over_background': None, 'incubation_min': _total_incubation_min(record), 'partner_over_constant': None, 'partner_name': None, 'partner_refs': [],'concentration_count': None, 'concentration_low_over_constant': None, 'concentration_high_over_constant': None, 'signal_window_refs': [], 'z_prime': None, 'z_prime_refs': [], 'incubation_refs': [], 'concentration_count_refs': [], 'concentration_span_refs': [], 'estimate_fold': None, 'estimate_refs': [], 'replicate_count': None, 'replicate_independent': None, 'replicate_refs': []}
    outcomes = {name: EVALUATORS[name](record, native) for name in CRITERIA}
    native['support'] = criterion_supports(record, ALPHA_CRITERIA)      # kept for the sheet: the grader does not judge it
    return {'version': VERSION, 'experiment_type': 'alphascreen', 'experiment_ref': record['experiment_ref'], 'criteria': {name: {'status': o['status'], 'support_refs': o['support_refs']} for name, o in outcomes.items()}, 'reasons': {name: o['reason'] for name, o in outcomes.items()}, 'native': native}
