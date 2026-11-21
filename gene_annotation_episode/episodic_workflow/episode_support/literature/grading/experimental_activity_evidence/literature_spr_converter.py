"""SPR converter: turns the SPR grader's result into what the A105 ligand_binding sheet takes.

Hand-built, private to SPR, deterministic. Input: the result of grade_spr.
Output: the sheet's input (the 'extraction' grade_assay takes, with
assay_type 'ligand_binding' and quantity_kind 'binding_parameter'), the
sheet itself (grade_assay run on it, so the cells are the existing sheet's
components), the dependence keys the merger needs, and for every sheet
component that a KD measurement cannot honestly fill, the reason it stays
null.

Quantities filled
-----------------
effect            the SPR KD in nM (point operand), only when the source
                  gave a KD as a point value. A KD the source did not give
                  leaves effect null.
effect_variance   variance of that KD estimate, nM_squared, only when the
                  source's spread allows it: standard_error -> se^2;
                  standard_deviation -> sd^2 / n, and only when the
                  replicates criterion is supported (n independent
                  replicates); confidence_interval -> not converted (needs
                  its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery,
attributed signal/total signal, condition test/reference, the assertion and
alternative predictions. They belong to calibration of a different detector,
to a nuisance-condition control SPR does not supply, or to the target's
assertion, not to the experiment. The sheet therefore leaves the cells
recovery_deviation, attributed_fraction, condition_response, both prediction
errors and source_log_evidence_ratio unavailable.

Criteria mapping (SPR criteria -> sheet criteria)
-------------------------------------------------
binding_controls              reference_subtraction + baseline_regeneration
binding_regime                concentration_series + mass_transport +
                              steady_state_vs_kinetic
binding_parameter_definition  fit_model + kinetic_consistency
binding_species               immobilized_activity
calibration_applicability     rmax_consistency
sampling_basis                replicates
variance_correspondence       supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and
hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps
each such criterion and reason to its judgement): concentration_series
conflicting below MIN_CONCENTRATIONS concentrations, else judged on the lowest
over the KD (full agreement at most LOW_FACTOR) and the highest over the KD
(full agreement at least HIGH_FACTOR); fit_model judged on chi-squared over Rmax
(full agreement at most CHI2_OVER_RMAX_MAX), unknown for a 1:1 model whose
bivalence is not answered no; rmax_consistency judged on the observed over
theoretical Rmax (full agreement from RMAX_RATIO_MIN to RMAX_RATIO_MAX);
replicates conflicting below MIN_REPLICATES, else supported when the
independence is yes, else unknown; kinetic_consistency judged on the relative
gap of koff/kon from the KD (full agreement at most KINETIC_TOLERANCE);
steady_state_vs_kinetic judged on the fold gap (full agreement at most
AGREEMENT_FACTOR). A continuous comparison is supported with a degree of 1.0 at
its full-agreement limit, falling linearly to 0 at its zero-agreement limit (the
*_ZERO_* constants), and conflicting (no degree) at or beyond that limit. A sheet
criterion that is supported carries the smallest degree of its members that
have one (the sheet reads no degree; it travels with the interpretation and the
merger carries it per result).
Quote support: the extraction records for each stated field how well its quote supports it ('direct', 'implied',
'about_something_else'); the grader only keeps it (native 'support', per criterion, from the fields the criterion
reads) and the judgement is made here with literature_quote_support.apply_support. A supported sheet criterion
whose fields include an 'implied' one has its degree multiplied by 0.7, an 'about_something_else' one by 0.3 (the
weakest field counts once; the degree is that factor where there was none; 'direct' changes nothing). Support never
changes a status, and unknown or conflicting criteria carry no degree. The constants (SUPPORT_DEGREE) and their
reasons are in literature_quote_support.py.
Combined status: any conflicting -> conflicting; else any unknown ->
unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet
criteria with no SPR counterpart (measurement_identity, matrix_interference,
background_alternatives, attribution_supported, assertion_relevance,
condition_scope, binding_comparison) are not selected, and the sheet reports
them as not selected.
"""
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_binding_reader import _SCALES
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_spr_converted_v1'
CRITERIA_MAP = {'binding_controls': ('reference_subtraction', 'baseline_regeneration'), 'binding_regime': ('concentration_series', 'mass_transport', 'steady_state_vs_kinetic'), 'binding_parameter_definition': ('fit_model', 'kinetic_consistency'), 'binding_species': ('immobilized_activity',), 'calibration_applicability': ('rmax_consistency',), 'sampling_basis': ('replicates',)}
MIN_CONCENTRATIONS = 5  # EXPERT_REVIEW: fewest analyte concentrations for a usable titration series.
LOW_FACTOR = 0.2  # EXPERT_REVIEW: the lowest concentration should be at most this multiple of KD (0.1x with a factor of 2 slack); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW: lowest concentration at the KD itself leaves the lower half of the binding curve undefined, so no agreement; falls linearly from LOW_FACTOR.
HIGH_FACTOR = 5.0  # EXPERT_REVIEW: the highest concentration should be at least this multiple of KD (10x with a factor of 2 slack); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW: highest concentration at the KD itself never reaches saturation, so no agreement; falls linearly from HIGH_FACTOR.
CHI2_OVER_RMAX_MAX = 0.10  # EXPERT_REVIEW: fit chi-squared above this fraction of Rmax marks a poor fit (instrument-software rule of thumb); full agreement up to it.
CHI2_OVER_RMAX_ZERO = 0.30  # EXPERT_REVIEW: chi-squared at three times the rule of thumb is a fit that does not describe the data (no agreement); falls linearly from CHI2_OVER_RMAX_MAX.
RMAX_RATIO_MIN = 0.3  # EXPERT_REVIEW: observed/theoretical Rmax below this means a mostly inactive surface or wrong stoichiometry; full agreement from it.
RMAX_RATIO_ZERO_MIN = 0.1  # EXPERT_REVIEW: a tenth of the theoretical Rmax or less is an essentially inactive surface (no agreement); falls linearly from RMAX_RATIO_MIN.
RMAX_RATIO_MAX = 1.2  # EXPERT_REVIEW: observed/theoretical Rmax above this means non-specific binding or aggregation; full agreement up to it.
RMAX_RATIO_ZERO_MAX = 2.0  # EXPERT_REVIEW: twice the theoretical Rmax or more is mostly non-specific signal (no agreement); falls linearly from RMAX_RATIO_MAX.
MIN_REPLICATES = 3  # EXPERT_REVIEW: fewest independent replicate experiments.
KINETIC_TOLERANCE = 0.20  # EXPERT_REVIEW: allowed relative gap between KD and koff/kon; full agreement up to it.
KINETIC_ZERO_TOLERANCE = 0.8  # EXPERT_REVIEW: a relative gap of 80 percent (koff/kon below a fifth or above 1.8 times the KD) means the rates do not describe the KD (no agreement); 0.8 and not 1.0 because a gap below the KD can never reach 1.0; falls linearly from KINETIC_TOLERANCE.
AGREEMENT_FACTOR = 2.0  # EXPERT_REVIEW: allowed fold gap between steady-state KD and kinetic KD; full agreement up to it.
AGREEMENT_ZERO_FACTOR = 10.0  # EXPERT_REVIEW: a tenfold gap between the two KD estimates is a different binding event (no agreement); falls linearly from AGREEMENT_FACTOR.
NULL_REASONS = {'recovery': 'spr_has_no_matrix_recovery_measurement', 'attributed_signal': 'spr_double_referencing_is_not_an_attribution_fraction', 'total_signal': 'spr_double_referencing_is_not_an_attribution_fraction', 'condition_test': 'no_matched_nuisance_condition_response_in_an_spr_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_spr_record', 'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _graded(refs, *limits):
    """Each limit is (value, full_agreement_limit, zero_agreement_limit). Conflicting when any value is at or beyond its zero limit; else supported with the smallest degree, 1.0 at the full limit falling linearly to 0 at the zero limit."""
    degrees = [(zero - value) / (zero - full) for value, full, zero in limits]
    if min(degrees) <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, *degrees))


def _judge_series(native):
    refs = native['concentration_refs']
    if native['concentration_count'] < MIN_CONCENTRATIONS:
        return _verdict('conflicting', refs)
    return _graded(refs, (native['concentration_low_over_kd'], LOW_FACTOR, LOW_ZERO_FACTOR), (native['concentration_high_over_kd'], HIGH_FACTOR, HIGH_ZERO_FACTOR))


def _judge_fit(native):
    verdict = _graded(native['fit_refs'], (native['chi2_over_rmax'], CHI2_OVER_RMAX_MAX, CHI2_OVER_RMAX_ZERO))
    if verdict['status'] == 'supported' and native['fit_model'] == '1:1_langmuir' and native['fit_bivalent_answer'] != 'no':
        return _verdict('unknown', [])
    return verdict


def _judge_rmax(native):
    return _graded(native['rmax_refs'], (native['rmax_ratio'], RMAX_RATIO_MIN, RMAX_RATIO_ZERO_MIN), (native['rmax_ratio'], RMAX_RATIO_MAX, RMAX_RATIO_ZERO_MAX))


def _judge_replicates(native):
    if native['replicate_count'] < MIN_REPLICATES:
        return _verdict('conflicting', native['replicate_refs'])
    return _verdict('supported' if native['replicate_independent'] == 'yes' else 'unknown', native['replicate_refs'])


def _judge_kinetic(native):
    gap = abs(native['kd_from_rates_nM'] / native['kd_nM'] - 1)
    return _graded(native['kinetic_refs'], (gap, KINETIC_TOLERANCE, KINETIC_ZERO_TOLERANCE))


def _judge_steady_kinetic(native):
    return _graded(native['steady_kinetic_refs'], (native['steady_kinetic_fold'], AGREEMENT_FACTOR, AGREEMENT_ZERO_FACTOR))


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('concentration_series', 'concentration_series_recorded_for_the_sheet'): _judge_series, ('fit_model', 'chi_squared_over_rmax_recorded_for_the_sheet'): _judge_fit,
          ('rmax_consistency', 'rmax_ratio_recorded_for_the_sheet'): _judge_rmax, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates,
          ('kinetic_consistency', 'kd_from_rates_recorded_for_the_sheet'): _judge_kinetic, ('steady_state_vs_kinetic', 'estimate_fold_recorded_for_the_sheet'): _judge_steady_kinetic}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component):
    return {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}


def _variance(graded):
    """Return (variance_nM_squared or None, reason or None, refs)."""
    native = graded['native']
    spread = native['quantities']['kd_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, 'kd_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = spread['value'] * _SCALES[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_spr(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    kd = native['quantities']['kd']
    if native['kd_nM'] is None:
        null_components['effect'] = 'kd_not_given_as_a_point_value'
    else:
        quantities['effect'] = _operand(native['kd_nM'], 'nM', 'spr_kd:' + ref, kd['source_refs'], kd['origin'], 'kd')
    variance, variance_reason, variance_refs = _variance(graded)
    if variance is None:
        null_components['effect_variance'] = variance_reason
    else:
        quantities['effect_variance'] = _operand(variance, 'nM_squared', 'spr_kd_variance:' + ref, variance_refs, 'derived', 'kd_spread')
    null_components.update({role: reason for role, reason in NULL_REASONS.items()})
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
    return {'version': VERSION, 'experiment_type': 'spr', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction, 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': kd['support'] if native['kd_nM'] is not None else None}
