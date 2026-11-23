"""Transport_fluorescent_reporter converter: turns the grader's result into what the A105 transport_response sheet takes. DRAFT of 2026-11-22, owner to correct.

Hand-built, private to transport_fluorescent_reporter, deterministic. Input: the result of grade_transport_fluorescent_reporter. Output: the sheet's input
(the 'extraction' grade_assay takes, with assay_type 'transport_response'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for
every sheet component that a fluorescence reading in cells cannot honestly fill, the reason it stays null. It follows the shape of the spectro_direct converter with the
transport_response class core (the class's effect quantities and their order are in literature_transport_response_direction and the registration note of the class).

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity: the Km of the transported substrate (uM, kind transport_parameter) or the fold of the signal over the
                  paper's own control (dimensionless, kind transport_rate_ratio). Both may be stated; the one used is the better determined, in the class order
                  TRANSPORT_EFFECT_ORDER (literature_transport_response_direction.select_transport_effect): the Km first (it needs no amount of transporter and no calibration of the
                  signal), then the fold. A fluorescence signal is in arbitrary units, so no rate per mass, turnover or conductance is ever stated by this method and none is read. A stated
                  value in another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the value is the paper's, only its unit
                  spelling changes ('fold' is the paper's word for the dimensionless ratio). quantity_kind of the extraction names the kind of the effect (KIND_OF_QUANTITY), which the
                  direction function reads.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it: standard_error -> se^2; standard_deviation -> sd^2 / n and
                  only when the replicates criterion is supported; confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal, condition test/reference, the assertion and alternative predictions.
qualitative_effect  only when NO effect is stated and the paper states whether it saw transport above its own control: statement 'interaction_detected' (read "transport detected") or
                  'interaction_not_detected' (read "transport not detected"), with the refs of the fact that states it, and direction_field_support the quote support of that one fact
                  (transport_detected_above_control). A result stated in words alone counts less than a measured one through the contract's stated_strength; that is not done here.
                  A stated effect fixes the direction; the statement is then not used.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives    control_cells + no_substrate_baseline
matrix_interference        background_fluorescence + signal_drift
calibration_applicability  indicator_calibration + assay_window
attribution_supported      expression_confirmed
assertion_relevance        substrate_identity
transport_specificity      analogue_competition + indicator_specificity
membrane_system            membrane_integrity
transport_endpoint         linear_interval
transport_driving_force    substrate_concentration_stated
transport_response_model   substrate_series
sampling_basis             replicates
variance_correspondence    supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each such
criterion and reason to its judgement). Each judgement is a researched value of THIS assay made gradual (SOP step 3): full agreement at the researched good value, falling
smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the assay gives (never a step), unknown when the paper states nothing, never conflicting
for a short count. A value at or beyond its zero end is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported carries the smallest
degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status:
any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not
selected. Sheet criteria with no counterpart here (measurement_identity, condition_scope) are not selected.

How the class decisions apply here (owner to confirm). Preparations: the cell culture or transfection that carries the transporter is analyte_preparation_ref, the other keys stay
None (cells are not immobilized, there is no electrode). Qualitative statements keep the existing vocabulary. Direction and strength of a stated Km or fold:
literature_transport_response_direction (the anchors per quantity are in the contract); controls, calibration and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads and whether the
shape fits, Q5 consistency with the other assays). Every literature citation is from memory and is NOT verified; every number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
Z_PRIME_FULL 0.5 -> Z_PRIME_ZERO 0.0, judged linearly in Z'.
  Q1 an assay window in which the signal of the cells with the transporter is not separated from that of the control cells: a fold computed from overlapping distributions is noise.
  Q2 general for plate and screening fluorescence assays: Z' = 1 - 3 (sd_test + sd_control) / |mean_test - mean_control|; 0.5 to 1 is an excellent assay, 0 to 0.5 marginal, at or below 0 the
  two three-sigma bands touch (Zhang, Chung and Oldenburg 1999, J Biomol Screen 4:67; from memory). Papers that never screen state no Z'; then the criterion is unknown. Q3 absolute, and
  built from the paper's own two distributions, which is the right reference: it already contains the control. Q4 Z' is a linear function of the ratio of the summed spread to the
  separation, so the degree is linear in Z' (a value of 0.25 gives 0.5); a wrong 0.5 moves only the degree. A stated Z' is a number above 0 (the extraction refuses numbers at or below 0), so
  the zero end is approached and never reached here: the criterion is supported with a small degree and never conflicting. Q5 no other transport type has a Z'.
MIN_SUBSTRATE_CONCENTRATIONS 6, SUBSTRATE_CONCENTRATIONS_ZERO 2.
  Q1 a Km fitted to too few concentrations to show that the response is a saturable hyperbola and not a straight line or a sigmoid. Q2 general: a concentration-response of about six to ten
  concentrations (plate dose-response practice and the NCBI Assay Guidance Manual, from memory); the exact 6 is a judgement. Q3 absolute (a count). Q4 the hyperbola has two parameters (Km and the
  maximum), so two concentrations are used up by the fit and leave no residual degree of freedom (supported with degree 0, never conflicting); each added concentration is one more point
  the curve must pass through: the degree rises linearly with count - 2 (4 give 1/2, 5 give 3/4). Q5 the same residual-degree-of-freedom count as the enzyme saturation series of spectro_direct.
LOW_FACTOR 0.2 -> LOW_ZERO_FACTOR 1.0, HIGH_FACTOR 10 -> HIGH_ZERO_FACTOR 1.0 (the lowest and highest substrate over the Km).
  Q1 a series that does not bracket the Km, so Km and maximum trade off (no saturation) or the curvature is unseen (no low end). Q2 general: 0.2 to 10 times the Km. Q3 relative to the paper's own
  Km (the grader records both ratios): right. Q4 the signal is a fraction S / (S + Km) of its maximum, so both ends are judged linearly in that fractional saturation (1/6 at 0.2 Km, 10/11 at
  10 Km; 1/2 at the Km, the zero end of both). Q5 working rule d of the SOP: the top is 10 where the maximum is a free signal amplitude known only by reaching it, which is the case for an
  uncalibrated fluorescence signal in arbitrary units (as for the fluorescence and optical binding assays); 5 would do where the maximum is fixed independently, which a relative reading never is.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a fold from one experiment, whose culture-to-culture and transfection-to-transfection spread is unseen (wells and cells of one preparation are technical repeats). Q2 general (triplicate
  practice; cell fluorescence assays are known for day-to-day variation of expression and loading). Q3 absolute count. Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the
  variance. Q5 exactly the shared replicate rule.
Facts with no number (the control cells, the no-substrate control, the background subtraction, the signal drift, the indicator calibration, whether the analogue is the native substrate, the competitor,
the indicator specificity, the expression, the cell integrity, the linear interval): the paper's own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched
value to soften. NOT judged, and why: the substrate concentration's value (it is the paper's own condition; the criterion only asks that it be stated, and a concentration far below or above the Km is
visible in the series criterion); the dye or sensor itself and its dynamic range (not collected: papers state them in Methods in many forms, and a wrong one shows in the fold, which the strength
scale already reads); the pH and the temperature (the claim carries no condition, and the identity block records the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this assay, owner to confirm:
  What does it measure; absolute or relative? The change of a fluorescence signal of cells while a substrate or an ion moves, almost always a relative reading (a fold over the paper's own
  control), absolute only after a calibration of the indicator; and what is read is often an analogue or a surrogate ion, not the substrate.
  Is there a reference range we would trust if the paper stated less (as for KD)? No: a fold over a control depends on the host cell's own transport, on dye loading and on the dynamic range
  of the indicator; there is no established range to assume.
  What does an unstated control or calibration do to what the number means? An unstated control cell line or no-substrate control is the dominant false positive of the method (endogenous
  uptake, dye binding to the cell surface, esterase or leakage artefacts); an unstated calibration leaves a relative fold usable as a fold but not as an amount; an unstated bleaching or leakage
  control leaves a drift that can make or hide a slope.
  If we assume it is fine and are wrong, how badly does the score mislead? A background counted as transport by this protein: the direction is wrong for a weak fold and the size for a strong one;
  worse than a rate by a direct assay (a purified enzyme), comparable to the cell-based proximity assays of binding.
  Consistent with KD? Well under it: default 0.65, level with AlphaScreen, split reporter and CETSA (relative cell or bead signals); the criteria that guard against a false transport are lower,
  the benign ones close to the default.
  default 0.65. background_alternatives 0.50 (the control cells and the no-substrate control are what separate transport by this protein from the host's own, as for the PLA and yeast
  two-hybrid controls). matrix_interference 0.55 (autofluorescence, bleaching and leakage are real, ordinary artefacts of a fluorescence reading). assertion_relevance 0.55 (the fluorescent molecule is
  often an analogue that other carriers also take up; unstated, the claim for the native substrate is open). calibration_applicability 0.55 (a relative signal; the fold stands but its size is open).
  transport_specificity 0.60 (competition by the natural substrate or an inhibitor is what shows the analogue goes through this carrier). membrane_system 0.65 (a viability check is ordinary
  practice, but a leaky cell takes up a dye; the default). attribution_supported 0.70 (expression is usually shown but often not said). transport_driving_force 0.70 (the substrate concentration and
  the buffer are stated in Methods; benign). sampling_basis 0.80 (triplicates are usual). transport_endpoint and transport_response_model take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_response_direction import select_transport_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_transport_fluorescent_reporter_converted'
CRITERIA_MAP = {'background_alternatives': ('control_cells', 'no_substrate_baseline'), 'matrix_interference': ('background_fluorescence', 'signal_drift'),
                'calibration_applicability': ('indicator_calibration', 'assay_window'), 'attribution_supported': ('expression_confirmed',),
                'assertion_relevance': ('substrate_identity',), 'transport_specificity': ('analogue_competition', 'indicator_specificity'),
                'membrane_system': ('membrane_integrity',), 'transport_endpoint': ('linear_interval',), 'transport_driving_force': ('substrate_concentration_stated',),
                'transport_response_model': ('substrate_series',), 'sampling_basis': ('replicates',)}
Z_PRIME_FULL = 0.5  # EXPERT_REVIEW, owner to confirm: a Z' factor of 0.5 or more is an excellent assay window (Zhang, Chung and Oldenburg 1999, J Biomol Screen 4:67, from memory, not verified); full agreement from it.
Z_PRIME_ZERO = 0.0  # EXPERT_REVIEW, owner to confirm: at a Z' of 0 the three-sigma bands of the cells with the transporter and the control cells touch (from memory, not verified): no separation (no agreement); the degree falls linearly in Z' from Z_PRIME_FULL to here (Z' is linear in the ratio of the summed spread to the separation). A stated Z' is above 0, so this end is approached and not reached.
MIN_SUBSTRATE_CONCENTRATIONS = 6  # EXPERT_REVIEW, owner to confirm: fewest substrate concentrations of a usable concentration-response (about six to ten, plate dose-response practice and the NCBI Assay Guidance Manual, from memory, not verified); full agreement from it.
SUBSTRATE_CONCENTRATIONS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: a hyperbola has two parameters (Km, maximum), so two concentrations are used up by the fit and leave no residual degree of freedom (degree 0, supported, never conflicting: a short series is weaker evidence); between this and MIN_SUBSTRATE_CONCENTRATIONS the degree rises linearly with the residual degrees of freedom (count - 2).
LOW_FACTOR = 0.2  # EXPERT_REVIEW, owner to confirm: the lowest substrate should be at most this multiple of the Km (the signal is 1/6 of its maximum there, from memory, not verified); full agreement up to it.
LOW_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: lowest substrate at the Km itself leaves the lower half of the hyperbola undefined (no agreement); falls from LOW_FACTOR linearly in the fractional saturation S / (S + Km).
HIGH_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: the highest substrate should be at least this multiple of the Km (the signal is 10/11 of its maximum there); the maximum of an uncalibrated fluorescence signal is a free amplitude known only by reaching it (SOP rule d: 10 for a free plateau); full agreement from it.
HIGH_ZERO_FACTOR = 1.0  # EXPERT_REVIEW, owner to confirm: highest substrate at the Km itself never reaches saturation (no agreement); falls from HIGH_FACTOR linearly in the fractional saturation S / (S + Km).
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments (separate days, cultures or transfections; wells of one preparation are technical repeats); full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.TRANSPORT_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (1 mM is 1000 uM; 1 nM is 0.001 uM; a fold is the dimensionless ratio); the stated number is the paper's.
    'transport_km': ('uM', {'nM': 1.0e-3, 'uM': 1.0, 'mM': 1.0e3}),
    'fold_over_control': ('dimensionless', {'fold': 1.0}),
}
# The record's quantity that states each effect quantity (its spread is the record quantity + '_spread').
RECORD_QUANTITY = {'transport_km': 'km', 'fold_over_control': 'fold_over_control'}
# The quantity_kind (QUANTITY_KINDS['transport_response']) that names the kind of each effect quantity; literature_transport_response_direction.TRANSPORT_QUANTITY_OF_KIND reads it back.
KIND_OF_QUANTITY = {'transport_km': 'transport_parameter', 'fold_over_control': 'transport_rate_ratio'}
KIND_WITHOUT_EFFECT = 'transport_rate_ratio'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing): the fold over the control is this method's own readout
NULL_REASONS = {'recovery': 'a_fluorescence_reporter_experiment_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_fold_over_control_is_not_an_attribution_fraction', 'total_signal': 'a_fold_over_control_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_transport_fluorescent_reporter_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_transport_fluorescent_reporter_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENT = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected'}   # read "transport detected" / "transport not detected" for this class


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _share(value, full, zero):
    """1.0 at the full-agreement limit, 0 at the zero-agreement limit, linear in between (either orientation; not capped)."""
    return (zero - value) / (zero - full)


def _graded(refs, *limits):
    """Each limit is (value, full_agreement_limit, zero_agreement_limit), all on the criterion's own scale. Conflicting when any value is at or beyond its zero limit; else supported with the smallest degree, 1.0 at the full limit falling linearly on that scale to 0 at the zero limit."""
    degrees = [_share(value, full, zero) for value, full, zero in limits]
    if min(degrees) <= 0:
        return _verdict('conflicting', refs)
    return _verdict('supported', refs, min(1.0, *degrees))


def _saturation(ratio):
    """Fractional saturation S / (S + Km) of a substrate S given as S / Km: where on the hyperbola it sits."""
    return ratio / (1 + ratio)


def _judge_window(native):
    return _graded(native['z_prime_refs'], (native['z_prime'], Z_PRIME_FULL, Z_PRIME_ZERO))


def _judge_series(native):
    # the two ratios keep their ramps (conflicting at their zero end), judged on the fractional saturation; the lower end is judged only when the series
    # has one distinct from its upper end (one concentration is a short series, not a badly placed one). The count only lowers the degree, never conflicts.
    refs = native['concentration_refs']
    low, high = native['concentration_low_over_km'], native['concentration_high_over_km']
    limits = [(_saturation(high), _saturation(HIGH_FACTOR), _saturation(HIGH_ZERO_FACTOR))]
    if low < high:
        limits.append((_saturation(low), _saturation(LOW_FACTOR), _saturation(LOW_ZERO_FACTOR)))
    verdict = _graded(refs, *limits)
    if verdict['status'] == 'conflicting':
        return verdict
    count_degree = max(0.0, min(1.0, _share(native['concentration_count'], MIN_SUBSTRATE_CONCENTRATIONS, SUBSTRATE_CONCENTRATIONS_ZERO)))
    return _verdict('supported', refs, min(verdict['degree'], count_degree))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('assay_window', 'z_prime_recorded_for_the_sheet'): _judge_window, ('substrate_series', 'substrate_series_recorded_for_the_sheet'): _judge_series,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _stated_effect(native, quantity, ref):
    """The stated quantity as an effect operand in its anchor unit, or None when not stated (its 'support' is the extraction's)."""
    operand = native['quantities'][RECORD_QUANTITY[quantity]]
    if operand['status'] != 'point':
        return None
    unit, factors = UNIT_FACTORS[quantity]
    return _operand(operand['value'] * factors[operand['unit']], unit, 'transport_fluorescent_reporter_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], RECORD_QUANTITY[quantity], operand['support'])


def _variance(graded, quantity, ref):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of ``quantity``."""
    native = graded['native']
    spread = native['quantities'][RECORD_QUANTITY[quantity] + '_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, RECORD_QUANTITY[quantity] + '_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    unit, factors = UNIT_FACTORS[quantity]
    sd = spread['value'] * factors[spread['unit']]
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_transport_fluorescent_reporter(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_transport_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_transport_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = KIND_OF_QUANTITY[chosen], effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'transport_fluorescent_reporter_' + chosen + '_variance:' + ref, variance_refs, 'derived', RECORD_QUANTITY[chosen] + '_spread')
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
    if quantities['effect_variance'] is not None:
        interpretations['variance_correspondence'] = {'status': 'supported', 'support_refs': quantities['effect_variance']['source_refs']}
    extraction = {'version': INPUT_VERSION, 'assay_type': 'transport_response', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'transport_fluorescent_reporter', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None and native['transport'] is not None:      # no stated quantity: the paper's own statement of transport above its control fixes the direction
        result['qualitative_effect'] = {'statement': STATEMENT[native['transport']], 'support_refs': list(native['transport_refs'])}
        result['direction_field_support'] = native['transport_support']      # the support class of the fact transport_detected_above_control, the one field the statement is derived from
    return result
