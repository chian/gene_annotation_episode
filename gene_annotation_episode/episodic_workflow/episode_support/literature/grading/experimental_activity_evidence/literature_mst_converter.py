"""MST converter: turns the MST grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to MST, deterministic. Input: the result of grade_mst.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR, ITC, BLI, GCI, FP and FRET converters fill), the
dependence keys the merger needs, and for every sheet component that an MST
measurement cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the reported binding constant in nM (point operand): the
                  KD of a direct titration, or, when the record has no KD,
                  the Ki of a competition experiment (the measurement key
                  names it: mst_kd or mst_ki). Neither given leaves effect
                  null; an EC50 alone is not a binding constant (it depends on
                  the detected partner's concentration) and is not carried
                  into the effect.
effect_variance   variance of that constant, nM_squared, only when the
                  source's spread (kd_spread for a KD, ki_spread for a Ki)
                  allows it: standard_error -> se^2; standard_deviation ->
                  sd^2 / n, and only when the replicates criterion is
                  supported (n independent titrations); confidence_interval
                  -> not converted (needs its level and degrees of freedom).
                  Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).

Dependence keys handed to the merger (the same four keys as the other
converters): analyte_preparation_ref = the titrant,
immobilized_preparation_ref = the detected partner held fixed, surface_ref = None
(MST in solution has no surface), dataset_ref = the dataset.

Criteria mapping (MST criteria -> sheet criteria), declared in CRITERIA_MAP
----------------------------------------------------------------------------
binding_controls              initial_fluorescence + aggregation_adsorption +
                              specificity_control + fluorescence_level
binding_regime                labelled_concentration + concentration_series +
                              equilibrium + direct_vs_competition
binding_parameter_definition  fit_model + labelling_scheme + readout_window
calibration_applicability     signal_amplitude (the size of the Fnorm change against
                              the noise: MST's counterpart of the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Continuous comparisons give a degree: supported with degree 1.0 up to
the full-agreement limit, falling linearly to 0 at the zero-agreement limit, conflicting at or beyond it (signal_amplitude: the signal-to-noise against MIN_SIGNAL_TO_NOISE /
SIGNAL_TO_NOISE_ZERO_AGREEMENT and the Fnorm change against MIN_FNORM_AMPLITUDE_PERMILLE / FNORM_AMPLITUDE_ZERO_AGREEMENT_PERMILLE, each one that is given, the weaker counts;
readout_window's F-hot time of a thermophoresis readout against MIN_FHOT_S / FHOT_ZERO_AGREEMENT_S; labelled_concentration against LABELLED_MAX_OVER_KD / LABELLED_ZERO_AGREEMENT_OVER_KD
unless tight binding is handled; concentration_series' lowest and highest concentration against LOW_FACTOR / LOW_ZERO_AGREEMENT_FACTOR and HIGH_FACTOR / HIGH_ZERO_AGREEMENT_FACTOR, the
weaker of the two, after a count of at least MIN_CONCENTRATIONS (a count below it is conflicting; a count without a span is unknown); direct_vs_competition against AGREEMENT_FACTOR /
AGREEMENT_ZERO_FACTOR). Counts and yes/no facts carry no degree: replicates conflicting below MIN_REPLICATES, else supported when the independence is yes, else unknown; equilibrium
from an incubation shorter than MIN_INCUBATION_MIN is conflicting, otherwise unknown (a long incubation alone does not show equilibrium, so no degree). A sheet criterion that is
supported carries the smallest degree of its members that have one.
Quote support (literature_quote_support.py, SUPPORT_DEGREE direct 1.0 / implied 0.7 / about_something_else 0.3): when any stated field a member criterion reads has
support 'implied' or 'about_something_else', a supported sheet criterion gets the weakest support degree as its degree (the product with its degree where it had one);
support never changes a status, and a conflicting or unknown criterion keeps no degree.
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no MST counterpart (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported,
assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_mst_criteria import NM_PER_UNIT

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_mst_converted_v1'
BINDING_CONSTANTS = ('kd', 'ki')
CRITERIA_MAP = {'binding_controls': ('initial_fluorescence', 'aggregation_adsorption', 'specificity_control', 'fluorescence_level'), 'binding_regime': ('labelled_concentration', 'concentration_series', 'equilibrium', 'direct_vs_competition'), 'binding_parameter_definition': ('fit_model', 'labelling_scheme', 'readout_window'), 'calibration_applicability': ('signal_amplitude',), 'sampling_basis': ('replicates',)}
MIN_SIGNAL_TO_NOISE = 5.0  # EXPERT_REVIEW: smallest signal-to-noise of the titration curve from which a KD is fitted; the instrument vendor's guidance treats a curve below 5 as not clearly distinguishable from noise; the full-agreement limit.
SIGNAL_TO_NOISE_ZERO_AGREEMENT = 1.0  # EXPERT_REVIEW: signal-to-noise at or below which the signal is the size of the noise (nothing to fit), conflicting.
MIN_FNORM_AMPLITUDE_PERMILLE = 5.0  # EXPERT_REVIEW: smallest change of Fnorm (per mille) between the unbound and the bound state; the noise of one capillary is of the order of 1 per mille, so a change below 5 per mille leaves a signal-to-noise below 5; the full-agreement limit.
FNORM_AMPLITUDE_ZERO_AGREEMENT_PERMILLE = 1.0  # EXPERT_REVIEW: Fnorm change (per mille) at or below which it is the noise of one capillary, conflicting.
MIN_FHOT_S = 1.0  # EXPERT_REVIEW: earliest F-hot time (seconds after the infrared laser is switched on) for a thermophoresis readout; the temperature jump of the dye is over within about a second, and a window starting earlier mixes it into the signal; the full-agreement limit.
FHOT_ZERO_AGREEMENT_S = 0.0  # EXPERT_REVIEW: F-hot time (seconds) at or below which the window starts as the laser is switched on and holds the whole temperature jump, conflicting.
MIN_CONCENTRATIONS = 10  # EXPERT_REVIEW: fewest titrant concentrations for a usable MST titration (the usual series is 16 two-fold dilutions; with fewer than ten the two baselines and the transition are not all defined); a count, no degree.
LOW_FACTOR = 0.2  # EXPERT_REVIEW: the lowest titrant concentration must be at most this multiple of the reported constant (the unbound baseline of the curve must be defined); the full-agreement limit.
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the constant at or above which the lowest concentration leaves the curve with no unbound baseline at all (half the sites are already bound), conflicting.
HIGH_FACTOR = 10.0  # EXPERT_REVIEW: the highest titrant concentration must be at least this multiple of the reported constant, because the bound plateau is only known by reaching it (about 90 percent saturation); the full-agreement limit.
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the constant at or below which the highest concentration reaches no more than half saturation, so the plateau is not seen at all, conflicting.
LABELLED_MAX_OVER_KD = 1.0  # EXPERT_REVIEW: the detected partner may be at most this multiple of the KD for the 1:1 hyperbola to give the KD (above it the apparent KD is raised by depletion of the titrant); the full-agreement limit.
LABELLED_ZERO_AGREEMENT_OVER_KD = 10.0  # EXPERT_REVIEW: detected partner over KD at or above which the apparent KD is dominated by the detected concentration (an order of magnitude of depletion), conflicting unless tight binding is handled.
MIN_INCUBATION_MIN = 10.0  # EXPERT_REVIEW: an incubation shorter than this (minutes) is too short to call a complex at equilibrium without a time course (five half-lives of an off rate of 0.01 per second are about 6 minutes, and a margin is kept for slower complexes); conflicting below it, unknown otherwise (no degree).
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent titrations (separate dilution series); a count, no degree.
AGREEMENT_FACTOR = 3.0  # EXPERT_REVIEW: allowed fold gap between a direct-titration KD and a competition Ki (a Ki depends on the detected partner's own KD and its uncertainty, so the standard is looser than for two direct estimates); the full-agreement limit.
AGREEMENT_ZERO_FACTOR = 10.0  # EXPERT_REVIEW: fold gap at or above which a direct KD and a competition Ki are different quantities (an order of magnitude), conflicting.
NULL_REASONS = {'recovery': 'mst_has_no_matrix_recovery_measurement', 'attributed_signal': 'mst_specificity_control_is_not_an_attribution_fraction', 'total_signal': 'mst_specificity_control_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_mst_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_mst_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _agreement(value, full, zero):
    """The degree of agreement of a measured value: 1.0 at or better than the full-agreement limit, falling linearly to 0 at the zero-agreement limit (either direction); None at or beyond it."""
    fraction = (value - zero) / (full - zero)
    return None if fraction <= 0 else min(1.0, fraction)


def _scaled(value, full, zero, refs):
    degree = _agreement(value, full, zero)
    return _verdict('conflicting', refs) if degree is None else _verdict('supported', refs, degree)


def _judge_signal(native):
    degrees = []
    if native['signal_to_noise'] is not None:
        degrees.append(_agreement(native['signal_to_noise'], MIN_SIGNAL_TO_NOISE, SIGNAL_TO_NOISE_ZERO_AGREEMENT))
    if native['fnorm_amplitude'] is not None:
        degrees.append(_agreement(native['fnorm_amplitude'], MIN_FNORM_AMPLITUDE_PERMILLE, FNORM_AMPLITUDE_ZERO_AGREEMENT_PERMILLE))
    if None in degrees:
        return _verdict('conflicting', native['signal_refs'])
    return _verdict('supported', native['signal_refs'], min(degrees))


def _judge_fhot(native):
    return _scaled(native['fhot_s'], MIN_FHOT_S, FHOT_ZERO_AGREEMENT_S, native['fhot_refs'])


def _judge_labelled(native):
    if native['tight_binding_handled']:
        return _verdict('supported', native['labelled_refs'])      # the quadratic or tight-binding analysis does not depend on the detected partner over the KD
    return _scaled(native['labelled_over_kd'], LABELLED_MAX_OVER_KD, LABELLED_ZERO_AGREEMENT_OVER_KD, native['labelled_refs'])


def _judge_series(native):
    if native['concentration_count'] < MIN_CONCENTRATIONS:
        return _verdict('conflicting', native['count_refs'])
    if native['concentration_low_over_constant'] is None:
        return _verdict('unknown', [])                               # the span can only be judged from the list and the reported constant
    refs = native['series_refs']
    low = _agreement(native['concentration_low_over_constant'], LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR)
    high = _agreement(native['concentration_high_over_constant'], HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR)
    if low is None or high is None:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(low, high))


def _judge_incubation(native):
    return _verdict('conflicting' if native['incubation_min'] < MIN_INCUBATION_MIN else 'unknown', native['incubation_refs'])


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


def _judge_estimates(native):
    return _scaled(native['estimate_fold'], AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, native['estimate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('signal_amplitude', 'signal_recorded_for_the_sheet'): _judge_signal, ('readout_window', 'fhot_time_recorded_for_the_sheet'): _judge_fhot,
          ('labelled_concentration', 'labelled_over_kd_recorded_for_the_sheet'): _judge_labelled, ('concentration_series', 'series_recorded_for_the_sheet'): _judge_series,
          ('equilibrium', 'incubation_recorded_for_the_sheet'): _judge_incubation, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates,
          ('direct_vs_competition', 'estimates_recorded_for_the_sheet'): _judge_estimates}


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
            return None, 'sd_needs_independent_titrations_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_mst(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    constant_name = _binding_constant(native)
    if constant_name is None:
        null_components['effect'] = 'only_a_half_maximal_concentration_given_not_a_binding_constant' if native['ec50_nM'] is not None else 'neither_kd_nor_ki_given_as_a_point_value'
    else:
        constant = native['quantities'][constant_name]
        quantities['effect'] = _operand(native[constant_name + '_nM'], 'nM', 'mst_' + constant_name + ':' + ref, constant['source_refs'], constant['origin'], constant_name)
    variance, variance_reason, variance_refs = _variance(graded, constant_name)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'mst_variance:' + ref, variance_refs, 'derived', constant_name + '_spread')
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
        interpretations[sheet_criterion] = apply_support(interpretations[sheet_criterion], supports)      # weak quote support lowers the degree of a supported criterion, never its status
    if variance is not None:
        interpretations['variance_correspondence'] = {'status': 'supported', 'support_refs': variance_refs}
    extraction = {'version': INPUT_VERSION, 'assay_type': 'ligand_binding', 'assertion_ref': native['assertion_ref'], 'quantity_kind': 'binding_parameter', 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    preparations = native['preparations']
    dependence = {'analyte_preparation_ref': preparations['titrant_preparation_ref'], 'immobilized_preparation_ref': preparations['fixed_partner_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    return {'version': VERSION, 'experiment_type': 'mst', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': native['quantities'][constant_name]['support'] if constant_name is not None else None}
