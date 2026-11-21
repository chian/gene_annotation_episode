"""AlphaScreen converter: turns the AlphaScreen grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to this method, deterministic. Input: the result of grade_alpha.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR, ITC, BLI, GCI, FP, FRET, MST, Trp, FCS and ELISA converters fill), the
dependence keys the merger needs, and for every sheet component that a bead assay cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the reported binding constant in nM (point operand): the
                  apparent KD of a titration, or, when the record has
                  no KD, the Ki of a competition (the measurement key names it:
                  alpha_kd or alpha_ki). Neither given leaves effect null; an EC50
                  or an IC50 alone is a half-maximal concentration, not a
                  dissociation constant (it depends on the partner and bead
                  concentrations and on the competing pair) and is not carried into the effect.
effect_variance   variance of that constant, nM_squared, only when the
                  source's spread (kd_spread for a KD, ki_spread for a Ki)
                  allows it: standard_error -> se^2; standard_deviation ->
                  sd^2 / n, and only when the replicates criterion is
                  supported (n independent experiments); confidence_interval
                  -> not converted (needs its level and degrees of freedom).
                  Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).

Dependence keys handed to the merger (the same four keys as the other
converters): analyte_preparation_ref = the titrant,
immobilized_preparation_ref = the partner held at a constant concentration, surface_ref = None (the plate is
not a surface reference), dataset_ref = the dataset.

Criteria mapping (AlphaScreen criteria -> sheet criteria), declared in CRITERIA_MAP
------------------------------------------------------------------------------------
binding_controls              specificity_control + capture_artifacts + avidity +
                              interference_counter_screen + light_protection
binding_regime                partner_depletion + hook_effect + concentration_series +
                              equilibrium + direct_vs_competition
binding_parameter_definition  fit_model
calibration_applicability     signal_window + assay_quality + detector_range (the signal
                              over the background, the Z' factor and the linear range of the
                              reader: this method's counterpart of the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Continuous comparisons (a ratio, a fold, an index) are supported with a degree of 1.0 up to the full-agreement limit, the degree falling
linearly to 0 at the zero-agreement limit, and conflicting (no degree) at or beyond it: signal_window (signal over background, MIN_SIGNAL_OVER_BACKGROUND down to
SIGNAL_WINDOW_ZERO_AGREEMENT), assay_quality (Z-prime, MIN_Z_PRIME down to Z_PRIME_ZERO_AGREEMENT), direct_vs_competition (the fold gap of the KD and the Ki, AGREEMENT_FACTOR up to
AGREEMENT_ZERO_FACTOR) and concentration_series (the lowest and the highest concentration over the constant, the smaller of the two degrees, after the count minimum
MIN_CONCENTRATIONS, which fails without a degree). Count minimums and yes/no facts get no degree: equilibrium (an incubation below MIN_INCUBATION_MIN conflicts, otherwise
unknown) and replicates (conflicting below MIN_REPLICATES, else supported when the independence is yes, else unknown). A sheet criterion that is supported carries the smallest
degree of its members that have one (the sheet reads no degree; it travels with the interpretation and the merger carries it per result).
Quote support (literature_quote_support.py, SUPPORT_DEGREE: direct 1.0, implied 0.7, about_something_else 0.3, defined once there with the
reason of each): a supported sheet criterion whose members read a stated field with support 'implied' or 'about_something_else' (the grader's
native['support'], per member) has its degree multiplied by the weakest factor; where it had no degree the degree becomes that factor; 'direct' leaves it as it
is. The variance_correspondence reads the support of the spread, its kind and, for a standard deviation, the replicate count. Support never
changes a status, and a conflicting or unknown criterion keeps no degree.
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no counterpart here (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported,
assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_alpha_criteria import NM_PER_UNIT
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_alphascreen_converted_v1'
BINDING_CONSTANTS = ('kd', 'ki')
CRITERIA_MAP = {'binding_controls': ('specificity_control', 'capture_artifacts', 'avidity', 'interference_counter_screen', 'light_protection'), 'binding_regime': ('partner_depletion', 'hook_effect', 'concentration_series', 'equilibrium', 'direct_vs_competition'), 'binding_parameter_definition': ('fit_model',), 'calibration_applicability': ('signal_window', 'assay_quality', 'detector_range'), 'sampling_basis': ('replicates',)}
MIN_SIGNAL_OVER_BACKGROUND = 10.0  # EXPERT_REVIEW: smallest signal-to-background ratio for the curve to have a defined bottom and top; the background of the amplified bead signal is a few hundred counts per second and usual windows are tens to thousands, so a ratio below ten leaves a curve whose bottom is within the scatter of the background.
SIGNAL_WINDOW_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: signal-to-background ratio at or below which the sheet takes the curve as having no window at all (conflicting); a ratio of 1 is a top signal that is the background; in between the degree falls linearly.
MIN_Z_PRIME = 0.5  # EXPERT_REVIEW: smallest Z' factor of the controls; 0.5 is the usual limit of an excellent assay window (Zhang, Chung and Oldenburg, 1999), below it positive and negative controls overlap too much for the curve to be read.
Z_PRIME_ZERO_AGREEMENT = 0.0  # EXPERT_REVIEW: Z' factor at or below which the sheet takes the controls as not separated at all (conflicting); a Z' of 0 is the limit at which the three-sigma bands of the positive and negative controls touch (Zhang et al., 1999: below 0 the assay is not usable); in between the degree falls linearly.
MIN_CONCENTRATIONS = 8  # EXPERT_REVIEW: fewest titrant concentrations for a usable titration (a four-parameter curve has four free parameters, and the bottom, the top and the transition are not all defined with fewer than eight points; usual series have eight to twelve dilutions).
LOW_FACTOR = 0.2  # EXPERT_REVIEW: the lowest concentration must be at most this multiple of the reported constant (the bottom baseline of the curve must be defined).
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the constant at or above which the lowest concentration leaves no bottom baseline (conflicting); at the constant the curve is already half way up.
HIGH_FACTOR = 10.0  # EXPERT_REVIEW: the highest concentration must be at least this multiple of the reported constant, because the plateau is only known by reaching it (about 90 percent saturation); a hook effect above the plateau does not lower this need.
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the constant at or below which the highest concentration does not reach even half the curve (conflicting).
MIN_INCUBATION_MIN = 30.0  # EXPERT_REVIEW: a binding step of the partners shorter than this (minutes) is too short to call the binding at equilibrium without a time course (usual protocols incubate the partners 30 to 60 minutes before the beads; below half an hour it is a kinetic readout).
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent experiments (separate plates, dilution series or days); technical wells of one plate do not count.
AGREEMENT_FACTOR = 3.0  # EXPERT_REVIEW: allowed fold gap between a titration KD and a competition Ki (a Ki depends on the concentration and the affinity of the pair it competes with, so the standard is looser than for two direct estimates).
AGREEMENT_ZERO_FACTOR = 10.0  # EXPERT_REVIEW: fold gap of the KD and the Ki at or beyond which the sheet takes them as disagreeing (conflicting); an order of magnitude is more than the competing pair can explain and points to different binding events; in between the degree falls linearly.
NULL_REASONS = {'recovery': 'an_alphascreen_has_no_matrix_recovery_measurement', 'attributed_signal': 'an_alphascreen_specificity_control_is_not_an_attribution_fraction', 'total_signal': 'an_alphascreen_specificity_control_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_alphascreen_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_alphascreen_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _degree(value, full, zero):
    """How far the value agrees: 1.0 at the full-agreement limit (and beyond it), falling linearly to 0 at the zero-agreement limit; zero or less at or past it. Either direction (zero below or above full)."""
    return (value - zero) / (full - zero)


def _degree_verdict(value, full, zero, refs):
    degree = _degree(value, full, zero)
    if degree <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, degree))


def _judge_signal_window(native):
    return _degree_verdict(native['signal_over_background'], MIN_SIGNAL_OVER_BACKGROUND, SIGNAL_WINDOW_ZERO_AGREEMENT, native['signal_window_refs'])


def _judge_z_prime(native):
    return _degree_verdict(native['z_prime'], MIN_Z_PRIME, Z_PRIME_ZERO_AGREEMENT, native['z_prime_refs'])


def _judge_equilibrium(native):
    if native['incubation_min'] < MIN_INCUBATION_MIN:
        return _verdict('conflicting', native['incubation_refs'])
    return _verdict('unknown', [])


def _judge_concentration_series(native):
    if native['concentration_count'] < MIN_CONCENTRATIONS:
        return _verdict('conflicting', native['concentration_count_refs'])
    low, high = native['concentration_low_over_constant'], native['concentration_high_over_constant']
    if low is None:
        return _verdict('unknown', [])      # the span can only be judged from the list and the constant
    degrees = (_degree(low, LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR), _degree(high, HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR))
    if min(degrees) <= 0:
        return _verdict('conflicting', native['concentration_span_refs'])
    return _verdict('supported', native['concentration_span_refs'], min(1.0, *degrees))


def _judge_estimates(native):
    return _degree_verdict(native['estimate_fold'], AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, native['estimate_refs'])


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('signal_window', 'signal_window_recorded_for_the_sheet'): _judge_signal_window, ('assay_quality', 'z_prime_recorded_for_the_sheet'): _judge_z_prime,
          ('equilibrium', 'incubation_recorded_for_the_sheet'): _judge_equilibrium, ('concentration_series', 'concentration_series_recorded_for_the_sheet'): _judge_concentration_series,
          ('direct_vs_competition', 'estimates_recorded_for_the_sheet'): _judge_estimates, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _binding_constant(native):
    """The name of the binding constant the effect carries (kd, else ki), or None."""
    return next((name for name in BINDING_CONSTANTS if native[name + '_nM'] is not None), None)


def _variance(graded, constant_name):
    """Return (variance_nM_squared or None, reason or None, refs)."""
    native = graded['native']
    if constant_name is None:
        return None, 'no_effect_to_carry_a_variance', []
    name = constant_name + '_spread'
    spread = native['quantities'][name]
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, name + '_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] * NM_PER_UNIT[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_experiments_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def _variance_supports(native, constant_name):
    """The supports of the stated fields the variance rests on: the spread of the constant, its kind and, for a standard deviation, the replicate count."""
    quantities = native['quantities']
    names = [constant_name + '_spread'] + (['replicate_count'] if native['spread_kind'] == 'standard_deviation' else [])
    found = [quantities[name]['support'] for name in names] + [native['choice_support']['spread_kind']]
    return [support for support in found if support is not None]


def convert_alpha(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    constant_name = _binding_constant(native)
    if constant_name is None:
        only_half_maximal = native['ec50_nM'] is not None or native['ic50_nM'] is not None
        null_components['effect'] = 'only_a_half_maximal_concentration_given_not_a_binding_constant' if only_half_maximal else 'neither_kd_nor_ki_given_as_a_point_value'
    else:
        constant = native['quantities'][constant_name]
        quantities['effect'] = _operand(native[constant_name + '_nM'], 'nM', 'alpha_' + constant_name + ':' + ref, constant['source_refs'], constant['origin'], constant_name)
    variance, variance_reason, variance_refs = _variance(graded, constant_name)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'alpha_variance:' + ref, variance_refs, 'derived', constant_name + '_spread')
    null_components.update(NULL_REASONS)
    interpretations = {}
    for sheet_criterion, members in CRITERIA_MAP.items():
        graded_members = [_criterion(graded, m) for m in members if graded['criteria'][m]['status'] != 'not_applicable']
        if not graded_members:
            continue
        statuses = [m['status'] for m in graded_members]
        status = 'conflicting' if 'conflicting' in statuses else 'unknown' if 'unknown' in statuses else 'supported'
        refs = list(dict.fromkeys(r for m in graded_members for r in m['support_refs']))
        interpretations[sheet_criterion] = {'status': status, 'support_refs': refs if status == 'supported' else []}
        degrees = [m['degree'] for m in graded_members if 'degree' in m]
        if status == 'supported' and degrees:
            interpretations[sheet_criterion]['degree'] = min(degrees)      # the weakest member: a degree of a member is not averaged away
        supports = [s for m in members if graded['criteria'][m]['status'] != 'not_applicable' for s in native['support'][m]]
        interpretations[sheet_criterion] = apply_support(interpretations[sheet_criterion], supports)      # thin quote support lowers a supported degree
    if variance is not None:
        interpretations['variance_correspondence'] = apply_support({'status': 'supported', 'support_refs': variance_refs}, _variance_supports(native, constant_name))
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['titrant_preparation_ref'], 'immobilized_preparation_ref': preparations['fixed_partner_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    return {'version': VERSION, 'experiment_type': 'alphascreen', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': native['quantities'][constant_name]['support'] if constant_name is not None else None}
