"""Transport_medium_analysis converter: turns the grader's result into what the A105 transport_response sheet takes.

DRAFT 2026-11-22 (first draft of the type, owner to correct). Hand-built, private to transport_medium_analysis, deterministic. Input: the result
of grade_transport_medium_analysis. Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'transport_response'), the sheet
itself (grade_assay run on it), the dependence keys the merger needs, and for every sheet component that a medium analysis cannot honestly fill,
the reason it stays null. It follows the shape of literature_spectro_direct_converter.py with the transport_response class core
(docs/axis_restructure_20261117/A105_TRANSPORT_RESPONSE_INVENTORY.md; registration note CLASS_transport_response.md).

What the experiment is: cells (or vesicles) take up or release an UNLABELLED substrate and the substrate in the medium, or in cells separated
from it, is measured at stated times by HPLC, LC-MS, an enzymatic analyzer or ion analysis. Its result is an INTERVAL or appearance measure: the
balance of export, re-uptake, lysis and metabolism over the interval. A ten-minute disappearance is not an initial rate (the CstA/YbdD note of the
old review), and an extracellular appearance does not isolate one transporter (the YjeH note). The criteria below ask for exactly what separates
the two.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity (literature_row_contract.TRANSPORT_STRENGTH_ANCHORS): the rate over the paper's own
                  control cells (fold_over_control, 'dimensionless') or the rate per mass of cells (normalized_rate, 'nmol/min/mg'). Both may be stated;
                  the one used is the best-determined, in the class order TRANSPORT_EFFECT_ORDER (literature_transport_response_direction.select_transport_effect:
                  the fold over the paper's own control comes before the rate per mass, which depends on expression, the substrate level and the
                  normalizer). A stated value in another unit of the record's vocabulary is multiplied by its exact factor (UNIT_FACTORS,
                  FIXED_BY_DEFINITION): the value is the paper's, only its unit spelling changes ('fold' is read as 'dimensionless'; umol/min/g is
                  nmol/min/mg). quantity_kind of the extraction names the kind of the effect (KIND_OF_QUANTITY: 'transport_rate_ratio' or
                  'transport_rate'), which the direction function reads. A rate that is not per mass of cells (per cell, per culture volume) is not in the
                  record, so it is never an effect.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS).
qualitative_effect  only when NO effect is stated: the paper's own statement whether it saw transport above its own control (the fact
                  transport_detected_above_control): statement 'interaction_detected' (read "transport detected"), 'interaction_not_detected' (read
                  "transport not detected") or 'interaction_not_stated', with the refs of the fact that states it; direction_field_support is the quote
                  support of that one fact. A stated effect fixes the direction; the statement is then not used. A result stated in words alone counts
                  less than a measured one (the contract's stated_strength); that is not re-implemented here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives    cell_free_control + zero_time_sample
attribution_supported      control_strain + expression_confirmed
calibration_applicability  calibration_in_medium
matrix_interference        internal_standard
transport_endpoint         initial_rate_regime + time_points + separation_timing
transport_specificity      substrate_identity + metabolism_excluded + reuptake_excluded
membrane_system            lysis_excluded
transport_driving_force    energy_source
assertion_relevance        native_substrate
sampling_basis             replicates
variance_correspondence    supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity, condition_scope, transport_response_model) are not selected; the model criterion is
optional for a rate or a fold and is required only for a Km, which this type does not report.
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet';
JUDGES maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS experiment made gradual (SOP step 3):
full agreement at the researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics gives (never
a step), unknown when the paper states nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting (what the paper
itself shows against the standard). A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support
(literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status: any conflicting ->
conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable
is not selected.

How the class decisions apply here (owner to confirm). Preparations: the cell culture is analyte_preparation_ref; the other keys stay None (no
reconstituted vesicle batch, no electrode). Qualitative statements keep the existing vocabulary. Direction and strength of a stated result:
literature_transport_response_direction (larger is stronger for both effect quantities); controls, blanks, the interval and the rest lower the WEIGHT
only. Results of the class are not pooled.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong
value misleads and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every
number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
MOVED_FULL_PERCENT 10 -> MOVED_ZERO_PERCENT 90, judged on the bias of the average rate (criterion initial_rate_regime).
  Q1 an "initial rate" that is really the average over a time course that has already bent because the pool it draws on (the medium for an uptake,
  the cells for an export) is used up; the rate is then too low. Q2 general: an initial velocity is the slope while at most about 10 percent of the
  substrate has been moved (Cornish-Bowden's rule for initial velocities, applied here to a depletion; general practice of uptake assays is to read the
  linear part of the time course), from memory. Q3 relative to the paper's own starting amount, which the passage states as a share; right. Q4 the
  physics gives the shape: for a first-order decline (substrate far below the Km of the transporter, the worst case) the rate averaged over the window
  is f / -ln(1 - f) of the initial rate, f the fraction moved: 0.95 at 10 percent, 0.90 at 20, 0.72 at 50, 0.39 at 90 (bias 0.05, 0.10, 0.28, 0.61). The
  degree is linear in that bias between the two ends. At or beyond 90 percent the "rate" is an end point (conflicting). Q5 the same idea and the same
  numbers as the consumed share of spectro_direct (an enzyme progress curve and a transport depletion obey the same first-order depletion).
MIN_TIME_POINTS 5, TIME_POINTS_ZERO 2 (criterion time_points; the count includes the zero-time sample when one was taken).
  Q1 a rate taken from two samples, which is an interval average that cannot show whether the time course was linear (the CstA/YbdD ten-minute
  measurement had a start and an end sample only). Q2 general practice: a slope of the initial part is defined by several sampling times in the linear
  part (four to six are usual; NCBI Assay Guidance Manual on enzyme and kinetic assays asks for a progress curve), from memory; the exact 5 is a judgement.
  Q3 absolute (a count). Q4 a straight line has two parameters, so two points leave no residual degree of freedom (degree 0, supported, never conflicting:
  an interval average is weaker evidence, not evidence against); each added point is one more residual degree of freedom: the degree rises linearly with
  count - 2 (3 points give 1/3, 4 give 2/3). Q5 the same residual-degree-of-freedom count as the substrate series of spectro_direct and the SPR
  steady-state series.
SEPARATION_RATIO_FULL 0.05 -> SEPARATION_RATIO_ZERO 1.0, judged on the share of the measured signal that accrued after the nominal stop,
  b = r / (1 + r), r the separation delay over the interval (criterion separation_timing).
  Q1 a delayed centrifugation or filtration adds an unknown extra reaction interval (the CstA/YbdD samples were spun for 5 min after a 10 min
  incubation), so the amount belongs to a longer interval than the stated one. Q2 physics: a transport that goes on during the delay adds
  rate x delay to rate x interval, so the share of the signal that accrued after the stop is delay / (interval + delay) = r / (1 + r); cooling to 4 C
  slows but does not stop most transporters, so the full share is taken as the worst case. A delay of 5 percent of the interval is within the
  usual error of timing a sample (about 5 percent, from memory). Q3 relative to the paper's own interval; right, and the grader records both. Q4 the
  error is the share b itself: 0.05 at r = 0.05, 0.09 at r = 0.1, 0.33 at r = 0.5 (a 5 min spin after 10 min), 0.5 at r = 1; at r = 1 half the signal belongs to
  time the paper does not count, so no agreement (conflicting). The degree is linear in b. Q5 a bias that grows with the departure, as for the consumed share.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a rate from one experiment, whose culture-to-culture spread is unseen. Q2 general (triplicate practice of biological replicates). Q3 absolute count.
  Q4 precision of a mean (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the cell-free blank, the zero-time sample, the control strain, the expression, the calibration in the medium, the internal
standard, the identity of the substrate, the exclusion of metabolism, of re-uptake and of lysis, the energy source and the native substrate): the paper's
own statement decides; yes is supported, no is conflicting, silence is unknown. They have no researched value to soften. NOT judged, and why: the
analyzer's calibration range against the concentrations measured (papers rarely state both, and a detector outside its range shows in the paper's own
spread); the temperature and pH (the claim carries no condition, and the identity block records the temperature); the rate per cell, which the record
does not hold (the sheet's transport_rate units have no per-cell unit).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for
this assay, drafted 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The amount of an unlabelled substrate against calibration standards, turned into an absolute rate per
  mass of cells over an interval: absolute in units, but an interval balance of export, re-uptake, lysis and metabolism, not a transport constant.
  Is there a reference range we would trust if the paper stated less (as for KD)? No: a rate per mg of cells depends on expression, the substrate level
  and the normalizer, and there is no general range for it as for kcat; so the type default is below the enzyme-rate types.
  What does an unstated control or calibration do to the number's meaning? An unstated cell-free blank is usually benign (chemical loss of a
  nutrient is small); an unstated control strain, an unstated exclusion of metabolism or of re-uptake and an unstated stop are the usual failures of
  this method: the substrate may disappear by metabolism, or appear by lysis, and the paper then measures something other than the protein.
  If we assume it is fine and are wrong, how badly does the score mislead? A host or metabolic contribution counted as the protein's transport: the
  direction can be wrong for a weak signal and the magnitude for a strong one (the YjeH deletion strain still exported most of the amino acid).
  Consistent with KD? The default 0.75 is below the KD anchor 0.90 and below the activity types (0.85); the criteria that guard against a false
  transport are lower, the routine ones (calibration, replicates) are near the anchor.
  default 0.75. background_alternatives 0.80 (a chemical loss is small and the zero-time sample is routine). attribution_supported 0.60 (the strain
  contrast and the expression are what tie the signal to the protein; a deletion strain of a host with other transporters still shows most of the signal).
  matrix_interference 0.80 (an internal standard is the practice of mass spectrometry and often unsaid for HPLC). calibration_applicability 0.90 (standards
  in the medium are routine analytical practice). transport_endpoint 0.65 (an unstated interval regime, time points and stop usually mean a two-point
  interval average). transport_specificity 0.65 (metabolism and re-uptake unaddressed is the commonest failure of a medium analysis).
  membrane_system 0.75 (lysis is a real but often small contribution, and viability is often unsaid). transport_driving_force 0.85 (a carbon or energy
  source is routine). sampling_basis 0.85 (triplicates are usual). assertion_relevance takes the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_transport_response_direction import select_transport_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_transport_medium_analysis_converted'
CRITERIA_MAP = {'background_alternatives': ('cell_free_control', 'zero_time_sample'), 'attribution_supported': ('control_strain', 'expression_confirmed'),
                'calibration_applicability': ('calibration_in_medium',), 'matrix_interference': ('internal_standard',),
                'transport_endpoint': ('initial_rate_regime', 'time_points', 'separation_timing'),
                'transport_specificity': ('substrate_identity', 'metabolism_excluded', 'reuptake_excluded'), 'membrane_system': ('lysis_excluded',),
                'transport_driving_force': ('energy_source',), 'assertion_relevance': ('native_substrate',), 'sampling_basis': ('replicates',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
ZERO_TIME_POINTS_COUNTED = 1  # FIXED_BY_DEFINITION: a zero-time sample is one more point on the line the slope is fitted to.
MOVED_FULL_PERCENT = 10.0  # EXPERT_REVIEW, owner to confirm: at most about 10 percent of the starting substrate moved in the window of an initial rate (Cornish-Bowden's rule for initial velocities, applied to a depletion; general practice of uptake assays, from memory, not verified); full agreement up to it.
MOVED_ZERO_PERCENT = 90.0  # EXPERT_REVIEW, owner to confirm: at 90 percent moved the rate averaged over a first-order decline (the worst case) is 0.39 of the initial rate, a factor 2.6 off: an end point, not a rate (no agreement); the degree falls linearly in the bias 1 - f / -ln(1 - f) of the average rate from the full end to here.
MIN_TIME_POINTS = 5  # EXPERT_REVIEW, owner to confirm: fewest sampling times (the zero-time sample counted) that define the slope of an initial rate well (four to six are usual; NCBI Assay Guidance Manual asks for a progress curve, from memory, not verified; the exact 5 is a judgement); full agreement from it.
TIME_POINTS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: a straight line has two parameters, so two sampling times leave no residual degree of freedom (degree 0, supported, never conflicting: an interval average is weaker evidence, not evidence against); between this and MIN_TIME_POINTS the degree rises linearly with the residual degrees of freedom (count - 2).
SEPARATION_RATIO_FULL = 0.05  # EXPERT_REVIEW, owner to confirm: separation delay over the interval; a delay of 5 percent of the interval is within the usual error of timing a sample (about 5 percent, from memory, not verified): the share b = r / (1 + r) of the signal that accrued after the stop is then 0.048; full agreement up to it.
SEPARATION_RATIO_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: delay as long as the interval: half of the measured signal (b = 0.5) belongs to time the paper does not count (no agreement, the worst case of a transport that does not slow when the sample is cooled); the degree falls linearly in b from the full end to here.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.TRANSPORT_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (1 umol is 1e3 nmol and 1 pmol is 1e-3 nmol; umol per g is nmol per mg because 1 g is 1e3 mg and 1 umol is 1e3 nmol; 'fold' is read as the dimensionless ratio); the stated number is the paper's.
    'normalized_rate': ('nmol/min/mg', {'pmol/min/mg': 1.0e-3, 'nmol/min/mg': 1.0, 'umol/min/mg': 1.0e3, 'umol/min/g': 1.0}),
    'fold_over_control': ('dimensionless', {'fold': 1.0}),
}
# The quantity_kind (QUANTITY_KINDS['transport_response']) that names the kind of each effect quantity; literature_transport_response_direction.transport_quantity reads it back.
KIND_OF_QUANTITY = {'normalized_rate': 'transport_rate', 'fold_over_control': 'transport_rate_ratio'}
KIND_WITHOUT_EFFECT = 'transport_rate'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'a_medium_analysis_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_medium_rate_is_not_an_attribution_fraction', 'total_signal': 'a_medium_rate_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_a_transport_medium_analysis_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_a_transport_medium_analysis_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "transport detected" / "transport not detected" / "transport not stated" for this class


def _verdict(status, refs, degree=None):
    if status in ('supported', 'conflicting') and not refs:
        raise ValueError('a ' + status + ' judgement needs support refs')
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


def _average_rate_bias(fraction):
    """The shortfall 1 - f / -ln(1 - f) of the rate averaged over a first-order decline that has moved the fraction f of the starting substrate."""
    return 1.0 - fraction / -math.log1p(-fraction)


def _signal_after_stop(ratio):
    """The share r / (1 + r) of the measured signal that accrued after the nominal stop, for a separation delay of r times the interval."""
    return ratio / (1.0 + ratio)


def _judge_regime(native):
    refs = native['moved_refs']
    fraction, zero = native['moved_percent'] / PERCENT_PER_FRACTION, MOVED_ZERO_PERCENT / PERCENT_PER_FRACTION
    if fraction >= zero:
        return _verdict('conflicting', refs)
    return _graded(refs, (_average_rate_bias(fraction), _average_rate_bias(MOVED_FULL_PERCENT / PERCENT_PER_FRACTION), _average_rate_bias(zero)))


def _judge_time_points(native):
    # the count only lowers the degree, never conflicts: two points are an interval average, weaker evidence and not evidence against
    count = native['time_point_count'] + (ZERO_TIME_POINTS_COUNTED if native['zero_time_sample'] == 'yes' else 0)
    return _verdict('supported', native['time_points_refs'], max(0.0, min(1.0, _share(count, MIN_TIME_POINTS, TIME_POINTS_ZERO))))


def _judge_separation(native):
    return _graded(native['separation_refs'], (_signal_after_stop(native['separation_delay_over_interval']), _signal_after_stop(SEPARATION_RATIO_FULL), _signal_after_stop(SEPARATION_RATIO_ZERO)))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('initial_rate_regime', 'moved_recorded_for_the_sheet'): _judge_regime, ('time_points', 'time_points_recorded_for_the_sheet'): _judge_time_points,
          ('separation_timing', 'separation_recorded_for_the_sheet'): _judge_separation, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _stated_effect(native, quantity, ref):
    """The stated quantity as an effect operand in its anchor unit, or None when not stated (its 'support' is the extraction's)."""
    operand = native['quantities'][quantity]
    if operand['status'] != 'point':
        return None
    unit, factors = UNIT_FACTORS[quantity]
    return _operand(operand['value'] * factors[operand['unit']], unit, 'transport_medium_analysis_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])


def _variance(graded, quantity, ref):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of ``quantity``."""
    native = graded['native']
    spread = native['quantities'][quantity + '_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, quantity + '_spread_not_given', []
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


def convert_transport_medium_analysis(graded):
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
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'transport_medium_analysis_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    converted = {'version': VERSION, 'experiment_type': 'transport_medium_analysis', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
                 'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated quantity: the paper's own statement of transport above its control stands (the result is stated in words), scored like any stated result (literature_direction, the qualitative path)
        converted['qualitative_effect'] = {'statement': STATEMENTS[native['transport']], 'support_refs': list(native['transport_refs'])}
        if native['transport'] is not None:
            converted['direction_field_support'] = native['transport_support']      # the support class of the fact transport_detected_above_control, the one field the statement is derived from
    return converted
