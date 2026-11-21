"""FP converter: turns the FP grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to FP, deterministic. Input: the result of grade_fp.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components, the same ones the SPR, ITC, BLI and GCI converters fill), the
dependence keys the merger needs, and for every sheet component that an FP
measurement cannot honestly fill, the reason it stays null.

Quantities filled
-----------------
effect            the reported binding constant in nM (point operand): the
                  KD of a direct titration, or, when the record has no KD,
                  the Ki of a competition experiment (the grader's
                  'constant_name' says which; the measurement key names it:
                  fp_kd or fp_ki). Neither given leaves effect null.
effect_variance   variance of that constant, nM_squared, only when the
                  source's spread (kd_spread for a KD, ki_spread for a Ki)
                  allows it: standard_error -> se^2; standard_deviation ->
                  sd^2 / n, and only when the replicates criterion is
                  supported (n independent titrations); confidence_interval
                  -> not converted (needs its level and degrees of freedom).
                  Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).

Dependence keys handed to the merger (the same four keys as the SPR, ITC, BLI
and GCI converters): analyte_preparation_ref = the titrant,
immobilized_preparation_ref = the labelled tracer partner, surface_ref = None
(FP has no surface), dataset_ref = the dataset.

Criteria mapping (FP criteria -> sheet criteria), declared in CRITERIA_MAP
--------------------------------------------------------------------------
binding_controls              free_probe_baseline + specificity_control +
                              surface_adsorption
binding_regime                tracer_concentration + concentration_series +
                              equilibrium + direct_vs_competition
binding_parameter_definition  fit_model + intensity_change
calibration_applicability     assay_window (the polarization span against the
                              plate reader's resolution: FP's counterpart of
                              the SPR Rmax check)
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in
'_recorded_for_the_sheet'; JUDGES maps each such criterion and reason to its judgement). Continuous comparisons give a degree: supported with degree 1.0 up to
the full-agreement limit, falling linearly to 0 at the zero-agreement limit, conflicting at or beyond it (assay_window against MIN_WINDOW_MP / WINDOW_ZERO_AGREEMENT_MP;
tracer_concentration against TRACER_MAX_OVER_KD / TRACER_ZERO_AGREEMENT_OVER_KD unless tight binding is handled; concentration_series' lowest and highest concentration
against LOW_FACTOR / LOW_ZERO_AGREEMENT_FACTOR and HIGH_FACTOR / HIGH_ZERO_AGREEMENT_FACTOR, the weaker of the two, after a count of at least MIN_CONCENTRATIONS;
intensity_change against INTENSITY_CHANGE_MAX_PERCENT / INTENSITY_ZERO_AGREEMENT_PERCENT; direct_vs_competition against AGREEMENT_FACTOR / AGREEMENT_ZERO_FACTOR). Counts and yes/no
facts carry no degree: replicates conflicting below MIN_REPLICATES, else supported when the independence is yes, else unknown; equilibrium from an incubation shorter than
MIN_INCUBATION_MIN is conflicting, otherwise unknown (a long incubation alone does not show equilibrium, so no degree). A sheet criterion that is supported carries the
smallest degree of its members that have one.
Quote support (literature_quote_support.py, SUPPORT_DEGREE direct 1.0 / implied 0.7 / about_something_else 0.3): when any stated field a member criterion reads has
support 'implied' or 'about_something_else', a supported sheet criterion gets the weakest support degree as its degree (the product with its degree where it had one);
support never changes a status, and a conflicting or unknown criterion keeps no degree.
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no FP counterpart (binding_species, measurement_identity,
matrix_interference, background_alternatives, attribution_supported,
assertion_relevance, condition_scope, binding_comparison) are not selected,
and the sheet reports them as not selected.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_fp_criteria import NM_PER_UNIT

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_fp_converted_v1'
CRITERIA_MAP = {'binding_controls': ('free_probe_baseline', 'specificity_control', 'surface_adsorption'), 'binding_regime': ('tracer_concentration', 'concentration_series', 'equilibrium', 'direct_vs_competition'), 'binding_parameter_definition': ('fit_model', 'intensity_change'), 'calibration_applicability': ('assay_window',), 'sampling_basis': ('replicates',)}
MIN_WINDOW_MP = 70.0  # EXPERT_REVIEW: smallest polarization window (bound minus free, in mP) that a typical plate reader (reproducibility of a few mP) resolves into a titration curve; 100 mP or more is common practice, this allows for a lower but still usable window; the full-agreement limit.
WINDOW_ZERO_AGREEMENT_MP = 20.0  # EXPERT_REVIEW: window (mP) at or below which the sheet takes the titration as unresolved (conflicting): with a reproducibility of a few mP a window of 20 mP or less is lost in the noise of the plate reader.
MIN_CONCENTRATIONS = 8  # EXPERT_REVIEW: fewest titrant concentrations for a usable FP titration (FP titrations are usually 12 to 24 point dilution series); a count, no degree.
LOW_FACTOR = 0.2  # EXPERT_REVIEW: the lowest titrant concentration must be at most this multiple of the reported constant (the baseline of the curve must be defined); the full-agreement limit.
LOW_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the constant at or above which the lowest concentration leaves the curve with no baseline at all (half the sites are already bound), conflicting.
HIGH_FACTOR = 10.0  # EXPERT_REVIEW: the highest titrant concentration must be at least this multiple of the reported constant, because FP has no other way to know the bound plateau than to reach it (about 90 percent saturation); the full-agreement limit.
HIGH_ZERO_AGREEMENT_FACTOR = 1.0  # EXPERT_REVIEW: multiple of the constant at or below which the highest concentration reaches no more than half saturation, so the plateau is not seen at all, conflicting.
TRACER_MAX_OVER_KD = 1.0  # EXPERT_REVIEW: the tracer concentration may be at most this multiple of the KD for the 1:1 hyperbola to give the KD (above it the apparent KD is raised by tracer depletion); the full-agreement limit.
TRACER_ZERO_AGREEMENT_OVER_KD = 10.0  # EXPERT_REVIEW: tracer over KD at or above which the apparent KD is dominated by the tracer concentration (an order of magnitude of depletion), conflicting unless tight binding is handled.
INTENSITY_CHANGE_MAX_PERCENT = 30.0  # EXPERT_REVIEW: a change of the total fluorescence intensity larger than this on binding makes the bound and free tracers contribute unequally to the polarization, so the fraction bound is wrong unless it is corrected; the full-agreement limit.
INTENSITY_ZERO_AGREEMENT_PERCENT = 100.0  # EXPERT_REVIEW: change of the total intensity (percent) at or above which the intensity at least doubles on binding and the polarization cannot be read as a fraction bound, conflicting.
MIN_INCUBATION_MIN = 5.0  # EXPERT_REVIEW: an incubation shorter than this (minutes) is too short to call any FP titration at equilibrium without a time course; conflicting below it, unknown otherwise (no degree).
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent titrations (separate dilution series); a count, no degree.
AGREEMENT_FACTOR = 3.0  # EXPERT_REVIEW: allowed fold gap between a direct-titration KD and a competition Ki (a Ki depends on the tracer's own KD and its uncertainty, so the standard is looser than for two direct estimates); the full-agreement limit.
AGREEMENT_ZERO_FACTOR = 10.0  # EXPERT_REVIEW: fold gap at or above which a direct KD and a competition Ki are different quantities (an order of magnitude), conflicting.
NULL_REASONS = {'recovery': 'fp_has_no_matrix_recovery_measurement', 'attributed_signal': 'fp_specificity_control_is_not_an_attribution_fraction', 'total_signal': 'fp_specificity_control_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_fp_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_fp_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


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


def _judge_window(native):
    return _scaled(native['window_mP'], MIN_WINDOW_MP, WINDOW_ZERO_AGREEMENT_MP, native['window_refs'])


def _judge_tracer(native):
    if native['tight_binding_handled']:
        return _verdict('supported', native['tracer_refs'])      # the quadratic or tight-binding analysis does not depend on the tracer over the KD
    return _scaled(native['tracer_over_kd'], TRACER_MAX_OVER_KD, TRACER_ZERO_AGREEMENT_OVER_KD, native['tracer_refs'])


def _judge_series(native):
    refs = native['series_refs']
    if native['concentration_count'] < MIN_CONCENTRATIONS:
        return _verdict('conflicting', refs)
    low = _agreement(native['concentration_low_over_constant'], LOW_FACTOR, LOW_ZERO_AGREEMENT_FACTOR)
    high = _agreement(native['concentration_high_over_constant'], HIGH_FACTOR, HIGH_ZERO_AGREEMENT_FACTOR)
    if low is None or high is None:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(low, high))


def _judge_incubation(native):
    return _verdict('conflicting' if native['incubation_min'] < MIN_INCUBATION_MIN else 'unknown', native['incubation_refs'])


def _judge_intensity(native):
    return _scaled(native['intensity_change_percent'], INTENSITY_CHANGE_MAX_PERCENT, INTENSITY_ZERO_AGREEMENT_PERCENT, native['intensity_change_refs'])


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


def _judge_estimates(native):
    return _scaled(native['estimate_fold'], AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR, native['estimate_refs'])


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('assay_window', 'window_recorded_for_the_sheet'): _judge_window, ('tracer_concentration', 'tracer_over_kd_recorded_for_the_sheet'): _judge_tracer,
          ('concentration_series', 'series_recorded_for_the_sheet'): _judge_series, ('equilibrium', 'incubation_recorded_for_the_sheet'): _judge_incubation,
          ('intensity_change', 'intensity_change_recorded_for_the_sheet'): _judge_intensity, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates,
          ('direct_vs_competition', 'estimates_recorded_for_the_sheet'): _judge_estimates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _variance(graded):
    """Return (variance_nM_squared or None, reason or None, refs)."""
    native = graded['native']
    name = native['constant_name'] + '_spread' if native['constant_name'] else 'kd_spread'
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


def convert_fp(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    if native['constant_nM'] is None:
        null_components['effect'] = 'neither_kd_nor_ki_given_as_a_point_value'
    else:
        constant = native['quantities'][native['constant_name']]
        quantities['effect'] = _operand(native['constant_nM'], 'nM', 'fp_' + native['constant_name'] + ':' + ref, constant['source_refs'], constant['origin'], native['constant_name'])
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'fp_variance:' + ref, variance_refs, 'derived', native['constant_name'] + '_spread')
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
    dependence = {'analyte_preparation_ref': preparations['titrant_preparation_ref'], 'immobilized_preparation_ref': preparations['tracer_preparation_ref'], 'surface_ref': None, 'dataset_ref': preparations['dataset_ref']}
    return {'version': VERSION, 'experiment_type': 'fp', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dependence, 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': native['quantities'][native['constant_name']]['support'] if native['constant_nM'] is not None else None}
