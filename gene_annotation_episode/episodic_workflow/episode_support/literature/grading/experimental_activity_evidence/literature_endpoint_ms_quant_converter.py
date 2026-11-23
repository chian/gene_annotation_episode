"""Endpoint_ms_quant converter: turns the grader's result into what the A105 endpoint_conversion sheet takes.

DRAFT of 2026-11-22 (owner to correct). Hand-built, private to endpoint_ms_quant, deterministic. Input: the result of grade_endpoint_ms_quant.
Output: the sheet's input (the 'extraction' grade_assay takes, with assay_type 'endpoint_conversion'), the sheet itself (grade_assay run on
it), the dependence keys the merger needs, the qualitative effect when no quantity is stated, and for every sheet component that an end-point
measurement cannot honestly fill, the reason it stays null. It follows the shape of literature_spectro_direct_converter.py; the class core is
the one of A105_ENDPOINT_CONVERSION_INVENTORY.md and the direction rule is literature_endpoint_conversion_direction.py.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity (ENDPOINT_STRENGTH_ANCHORS): the share converted net of the paper's own control
                  (fraction), the share converted as stated (fraction), the completion time ratio (dimensionless), the completion time (min) or the
                  product amount (uM). Several may be stated; the one used is the best-determined, in the class order ENDPOINT_EFFECT_ORDER
                  (literature_endpoint_conversion_direction.select_endpoint_effect). A stated value in another unit of the record's vocabulary is
                  multiplied by its exact factor (UNIT_FACTORS, FIXED_BY_DEFINITION): the value is the paper's, only its unit spelling changes (percent into
                  a fraction, s and h into min, nM and mM into uM). An amount in pmol, nmol or umol becomes a concentration only when the passage also
                  states the reaction volume; without it that quantity is not an effect. The record's quantity name is the sheet's quantity kind
                  (quantity_kind of the extraction names the kind of the effect, which the direction function reads).
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS). The paper's own control is never subtracted here: a control-corrected share is an effect
only when the paper states it (conversion_difference); the control beside the test is judged in signal_above_control.
qualitative_effect  only when NO effect is stated: the paper's own statement of conversion above its control (the fact conversion_detected_above_control):
                  'interaction_detected' (read "conversion detected"), 'interaction_not_detected' (read "conversion not detected") or
                  'interaction_not_stated', with the refs of the fact; direction_field_support is the quote support of that one fact. A stated effect fixes the
                  direction; the statement is then not used.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
background_alternatives     spontaneous_reaction_control + signal_above_control
attribution_supported       enzyme_dependence
matrix_interference         internal_standard + matrix_matched_calibration
calibration_applicability   calibration_range + calibration_points + quantification_floor
product_identity            product_identification
endpoint_alignment          endpoint_time_stated + reaction_stopped + same_time_across_arms
conversion_denominator      initial_substrate
assertion_relevance         native_reaction
condition_scope             purified_enzyme
sampling_basis              replicates
variance_correspondence     supported only when a variance was computed
Sheet criteria with no counterpart here (measurement_identity) are not selected: no record field states the product's name (a name would be free text), so the
identity of the estimate is carried by the identity block (target and partner) and not by a criterion of this type.
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps each
such criterion and reason to its judgement). Each judgement is a researched value of THIS method made gradual (SOP step 3): full agreement at the researched good
value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the method gives (never a step), unknown when the paper states
nothing. A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support)
lowers the degree of a supported criterion and never changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else
supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is not selected.

Conflicting is kept for what the paper itself states or shows against the standard: a fact answered no, and a test signal no larger than the paper's own control
(signal_above_control, two numbers of the same measurement). The three comparisons of the read amount with a range or a limit (calibration_range,
quantification_floor) and the count of calibration levels fall to degree 0 and stay supported, never conflicting: the amount stated for the end point is often the
amount in the reaction while the calibration is made in the diluted, quenched sample, so a ratio across that dilution is a reason for less credit, not proof of failure.

How the class decisions apply here (owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None (no immobilized
enzyme, no surface). Qualitative statements keep the existing vocabulary, read for this class. Direction and strength of a stated quantity:
literature_endpoint_conversion_direction (larger is stronger; for the completion time smaller is stronger), controls, blanks and the rest lower the WEIGHT only. A
result stated in words alone counts the contract's STATED_ONLY_STRENGTH of the type's value (not done here).

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong value misleads
and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every number is EXPERT_REVIEW, owner
to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
BACKGROUND_SHARE_FULL 0.10 -> BACKGROUND_SHARE_ZERO 1.0, judged linearly in the share b of the test signal that the control also shows (b = control / test).
  Q1 product that forms without the enzyme (spontaneous hydrolysis or isomerisation, a contaminant at the product's mass, carry-over in the autosampler) counted
  as the enzyme's. Q2 practice, not a guideline value: a background under about a tenth of the signal is taken as a small correction (bioanalytical validation
  guidance, FDA 2018 and EMA 2011, allows a blank response up to a fifth of the lowest standard; from memory, to verify); the zero end is arithmetic: at
  b = 1 the test shows nothing the control does not. Q3 relative to the paper's own control, both numbers stated by the paper; right. Q4 the enzyme-dependent share
  of the signal is 1 - b, so the degree is that share over its full-credit value 0.9, linear in b; at or beyond b = 1 the paper's own numbers show no conversion
  above its control (conflicting). A wrong 0.10 moves the degree of a real conversion, never its direction. Q5 the same idea as the signal-over-control ramps of the
  other classes (a signal no larger than the paper's own control is conflicting).
CALIBRATION_POINTS_FULL 6 -> CALIBRATION_POINTS_ZERO 2, linear in the residual degrees of freedom (count - 2).
  Q1 a calibration fitted to too few levels to show it is a line (or a curve) at all. Q2 general: a calibration curve of a blank, a zero sample and at least six
  non-zero levels (FDA Bioanalytical Method Validation 2018, EMA 2011, ICH M10 2022; from memory), the exact 6 a reading of those guidances. Q3 absolute (a count).
  Q4 a straight calibration has two parameters (slope and intercept), so two levels leave no residual degree of freedom (degree 0, supported, never conflicting:
  fewer levels are weaker evidence); each added level is one more point the line must pass through: the degree rises linearly with count - 2 (four levels give 1/2).
  Q5 the same residual-degree-of-freedom count as the substrate series of spectro_direct and the titration points of SPR.
RANGE_EDGE 1.0 (the amount at the edge of the calibration standards), READ_BELOW_ZERO_FACTOR 0.1 and READ_ABOVE_ZERO_FACTOR 10, judged linearly in the log10 of the amount
over the lowest standard and over the highest standard.
  Q1 a product amount read outside the calibration range is extrapolated: below the lowest standard it is near the noise floor, above the highest standard the
  electrospray or detector response is no longer proportional. Q2 general: a quantified amount must lie inside the calibration range (FDA 2018, EMA 2011; a sample
  above the range is diluted and re-analysed, which the guidance accepts; from memory); the decade at each end is a practice estimate: the response of an
  electrospray source is linear over about three to four orders (from memory), and the lowest standard sits near the limit of quantification, about three times
  the limit of detection, so a read a decade below it is below the limit of detection. Q3 relative to the paper's own calibration standards; right. Q4 a
  concentration response is multiplicative, so the position is judged in the log of the ratio; the degree is 1 inside the range, falling to 0 a decade outside it; never
  conflicting because the amount stated for the end point may be the amount in the reaction while the standards are in the diluted sample (a fact answered no is
  the grader's conflicting). Q5 the log-ratio ramps of the fold gaps of the binding assays.
LOQ_OVER_LOD 3.0 -> FLOOR_ZERO_OVER_LOD 1.0, judged linearly in the log of the amount over the limit of detection.
  Q1 an amount stated as measured that is at or under the method's own detection floor. Q2 general: the limit of detection is 3.3 sigma / slope and the limit of
  quantification 10 sigma / slope (ICH Q2(R1), from memory), so the limit of quantification is about three times the limit of detection. Q3 relative to the paper's own
  limit, and the limit of quantification is used first when stated (its amount over the limit, times LOQ_OVER_LOD, is the amount over the limit of detection). Q4 an amount
  at the limit of quantification is fully credited, one at the limit of detection or below is detected but not quantified (degree 0, never conflicting, for the
  dilution reason above); log scale because the response is multiplicative. Q5 as the range ramp above.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a conversion from one reaction, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4 precision of a mean
  (1 / sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the controls, the enzyme dependence, the internal standard, the matrix-matched calibration, the product identification, the quench, the same
time, the initial substrate, the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting, silence is
unknown. They have no researched value to soften. NOT judged, and why: the identity of the internal standard (an isotope-labelled standard follows the product through
the ion source better than a structural analogue, but a yes/no fact cannot carry that, and a degree for it would be an unreasoned number); the mass accuracy (kept as the
fact accurate_mass_match, a number in ppm would be a second threshold); the pH and the temperature (the claim carries no condition and the identity block records them).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this method,
decided 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? The amount of a named product at one time, identified by its mass and turned into a concentration by an
  internal-standard calibration: absolute, but the response of an ion source differs by orders of magnitude between compounds, so the number means something only
  with its calibration.
  Is there a reference range we would trust if the paper stated less (as for KD)? No: a conversion fraction depends on the loading the paper chose; there is no
  natural range of conversions of enzymes; what makes it trustworthy is the controls and the calibration.
  What does an unstated control or calibration do to the number's meaning? An unstated no-enzyme blank is the dominant false positive for a weak conversion
  (spontaneous chemistry, a contaminant at the product's mass); an unstated internal standard or matrix-matched calibration leaves ion suppression, which changes the
  size of an amount by a factor (it rarely removes a product that was identified by its mass); an unstated quench lets the reaction go on in the autosampler for hours.
  If we assume it is fine and are wrong, how badly does the score mislead? A background counted as conversion: the direction is wrong for a weak conversion and the
  size wrong for a strong one; an unquantified matrix effect: the size only.
  Consistent with KD? The default 0.85 is just under the KD anchor 0.90 and level with the chromatographic activity assay; the criteria that guard against a false
  conversion are lower, the benign ones equal the anchor or sit just above it.
  default 0.85. background_alternatives 0.75 (the blank is what separates conversion from spontaneous chemistry). attribution_supported 0.85 (the mass already
  narrows a second reaction; enzyme dependence is usual practice). matrix_interference 0.80 (ion suppression is the characteristic error of the method and a paper
  may leave it unsaid). calibration_applicability 0.85 (an amount needs a calibration; a conversion share needs only responses of the same compound). endpoint_alignment
  0.80 (an unstated quench in a long autosampler queue turns the end point into a later point). product_identity 0.90, sampling_basis 0.90 (benign when unstated: a product
  seen by mass is identified, triplicates are usual). conversion_denominator, assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_conversion_direction import select_endpoint_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, apply_support

VERSION = 'a105_endpoint_ms_quant_converted'
CRITERIA_MAP = {'background_alternatives': ('spontaneous_reaction_control', 'signal_above_control'), 'attribution_supported': ('enzyme_dependence',),
                'matrix_interference': ('internal_standard', 'matrix_matched_calibration'), 'calibration_applicability': ('calibration_range', 'calibration_points', 'quantification_floor'),
                'product_identity': ('product_identification',), 'endpoint_alignment': ('endpoint_time_stated', 'reaction_stopped', 'same_time_across_arms'),
                'conversion_denominator': ('initial_substrate',), 'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',), 'sampling_basis': ('replicates',)}
BACKGROUND_SHARE_FULL = 0.10  # EXPERT_REVIEW, owner to confirm: the control shows at most a tenth of the test signal: a small correction (practice; bioanalytical validation guidance allows a blank response up to a fifth of the lowest standard, from memory, not verified); full agreement up to it.
BACKGROUND_SHARE_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: the control shows all of the test signal: nothing above the paper's own control (arithmetic, no agreement and conflicting); the degree falls linearly in the share b = control / test, that is, in the enzyme-dependent share 1 - b.
CALIBRATION_POINTS_FULL = 6  # EXPERT_REVIEW, owner to confirm: fewest non-zero levels of a usable calibration curve (FDA 2018, EMA 2011, ICH M10: a blank, a zero and at least six levels, from memory, not verified); full agreement from it.
CALIBRATION_POINTS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: a straight calibration has two parameters (slope and intercept), so two levels leave no residual degree of freedom (degree 0, supported, never conflicting: fewer levels are weaker evidence); between this and CALIBRATION_POINTS_FULL the degree rises linearly with the residual degrees of freedom (count - 2).
RANGE_EDGE = 1.0  # FIXED_BY_DEFINITION: the read amount at the edge of the calibration standards (a ratio of 1 over the lowest or the highest standard); full agreement inside the range.
READ_BELOW_ZERO_FACTOR = 0.1  # EXPERT_REVIEW, owner to confirm: a read amount a decade below the lowest standard is below the limit of detection (the lowest standard sits near the limit of quantification, about three times the limit of detection): no agreement (degree 0, supported, never conflicting: the standards may be in the diluted sample); falls from RANGE_EDGE linearly in the log10 of the ratio.
READ_ABOVE_ZERO_FACTOR = 10.0  # EXPERT_REVIEW, owner to confirm: a read amount a decade above the highest standard is beyond the roughly three to four decades over which an electrospray response is proportional (from memory, not verified): no agreement (degree 0, supported, never conflicting for the dilution reason); falls from RANGE_EDGE linearly in the log10 of the ratio.
LOQ_OVER_LOD = 3.0  # EXPERT_REVIEW, owner to confirm: the limit of quantification is about three times the limit of detection (ICH Q2(R1): 10 sigma over 3.3 sigma, from memory, not verified); an amount at the limit of quantification gets full agreement.
FLOOR_ZERO_OVER_LOD = 1.0  # EXPERT_REVIEW, owner to confirm: an amount at the limit of detection is seen but not quantified: no agreement (degree 0, supported, never conflicting); falls from LOQ_OVER_LOD linearly in the log of the amount over the limit of detection.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The anchor unit of each effect quantity (literature_row_contract.ENDPOINT_STRENGTH_ANCHORS) and the exact factor from each unit of the record's vocabulary to it.
UNIT_FACTORS = {  # FIXED_BY_DEFINITION: exact unit conversions (a percent is a hundredth; 60 s is 1 min and 60 min is 1 h; 1 mM is 1000 uM and 1 nM is 1e-3 uM); the stated number is the paper's.
    'conversion_fraction': ('fraction', {'percent': 0.01, 'fraction': 1.0}),
    'conversion_difference': ('fraction', {'percent': 0.01, 'fraction': 1.0}),
    'completion_time_ratio': ('dimensionless', {'fold': 1.0}),
    'completion_time': ('min', {'s': 1.0 / 60.0, 'min': 1.0, 'h': 60.0}),
    'endpoint_amount': ('uM', {'nM': 1.0e-3, 'uM': 1.0, 'mM': 1.0e3}),
}
MOL_PER_UNIT = {'pmol': 1.0e-12, 'nmol': 1.0e-9, 'umol': 1.0e-6}  # FIXED_BY_DEFINITION: an amount in mol.
LITRES_PER_UNIT = {'uL': 1.0e-6, 'mL': 1.0e-3}  # FIXED_BY_DEFINITION: a volume in litres.
UM_PER_M = 1.0e6  # FIXED_BY_DEFINITION: micromolar per molar.
KIND_WITHOUT_EFFECT = 'conversion_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'endpoint_ms_quant_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_conversion_is_not_an_attribution_fraction', 'total_signal': 'a_conversion_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_an_endpoint_ms_quant_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_endpoint_ms_quant_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "conversion detected" / "conversion not detected" / "conversion not stated" for this class


def _verdict(status, refs, degree=None):
    verdict = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
    if degree is not None:
        verdict['degree'] = degree
    return verdict


def _clip(degree):
    return max(0.0, min(1.0, degree))


def _linear(value, full, zero):
    """1.0 at the full-agreement limit, 0 at the zero-agreement limit, linear in between (either orientation), kept inside [0, 1]."""
    return _clip((zero - value) / (zero - full))


def _log_ramp(value, full, zero):
    """The same ramp on the log scale of a ratio (a multiplicative error)."""
    return _clip((math.log(value) - math.log(zero)) / (math.log(full) - math.log(zero)))


def _judge_background(native):
    refs = native['background_refs']
    if native['background_share'] >= BACKGROUND_SHARE_ZERO:
        return _verdict('conflicting', refs)      # the paper's own numbers: the test shows nothing the control does not
    return _verdict('supported', refs, _linear(native['background_share'], BACKGROUND_SHARE_FULL, BACKGROUND_SHARE_ZERO))


def _judge_range(native):
    below = _log_ramp(native['read_over_calibration_low'], RANGE_EDGE, READ_BELOW_ZERO_FACTOR)
    above = _log_ramp(native['read_over_calibration_high'], RANGE_EDGE, READ_ABOVE_ZERO_FACTOR)
    return _verdict('supported', native['range_refs'], min(below, above))


def _judge_points(native):
    return _verdict('supported', native['points_refs'], _linear(native['calibration_points'], CALIBRATION_POINTS_FULL, CALIBRATION_POINTS_ZERO))


def _judge_floor(native):
    quantification, detection = native['read_over_quantification_limit'], native['read_over_detection_limit']
    over_detection = quantification * LOQ_OVER_LOD if quantification is not None else detection      # the limit of quantification is used first when the paper states it
    return _verdict('supported', native['floor_refs'], _log_ramp(over_detection, LOQ_OVER_LOD, FLOOR_ZERO_OVER_LOD))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('signal_above_control', 'background_share_recorded_for_the_sheet'): _judge_background, ('calibration_range', 'calibration_range_recorded_for_the_sheet'): _judge_range,
          ('calibration_points', 'calibration_points_recorded_for_the_sheet'): _judge_points, ('quantification_floor', 'quantification_floor_recorded_for_the_sheet'): _judge_floor,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _anchor_value(native, quantity, operand):
    """The stated operand in the anchor unit of ``quantity``, or None when it is an amount in mol and the reaction volume is not stated."""
    factors = UNIT_FACTORS[quantity][1]
    if operand['unit'] in factors:
        return operand['value'] * factors[operand['unit']]
    volume = native['quantities']['reaction_volume']
    if volume['status'] != 'point':
        return None
    return operand['value'] * MOL_PER_UNIT[operand['unit']] / (volume['value'] * LITRES_PER_UNIT[volume['unit']]) * UM_PER_M


def _stated_effect(native, quantity, ref):
    """The stated quantity as an effect operand in its anchor unit, or None when it is not stated or not usable (its 'support' is the extraction's)."""
    operand = native['quantities'][quantity]
    if operand['status'] != 'point':
        return None
    value = _anchor_value(native, quantity, operand)
    if value is None:
        return None
    unit, factors = UNIT_FACTORS[quantity]
    key = 'endpoint_ms_quant_' + quantity + ':' + ref
    if operand['unit'] in factors:
        return _operand(value, unit, key, operand['source_refs'], operand['origin'], quantity, operand['support'])
    volume = native['quantities']['reaction_volume']      # an amount turned into a concentration by the stated reaction volume
    return _operand(value, unit, key, list(dict.fromkeys([*operand['source_refs'], *volume['source_refs']])), 'derived', quantity, max([operand['support'], volume['support']], key=SUPPORTS.index))


def _variance(graded, quantity, ref):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of ``quantity``."""
    native = graded['native']
    spread = native['quantities'][quantity + '_spread']
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, quantity + '_spread_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = _anchor_value(native, quantity, spread)
    if sd is None:
        return None, 'reaction_volume_not_stated', []
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_endpoint_ms_quant(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated = {quantity: _stated_effect(native, quantity, ref) for quantity in UNIT_FACTORS}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_endpoint_quantity_given_as_a_point_value_in_a_usable_unit'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_endpoint_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = chosen, effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, UNIT_FACTORS[chosen][0] + '_squared', 'endpoint_ms_quant_' + chosen + '_variance:' + ref, variance_refs, 'derived', chosen + '_spread')
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
    extraction = {'version': INPUT_VERSION, 'assay_type': 'endpoint_conversion', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'endpoint_ms_quant', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no stated quantity: the paper's own statement of conversion above its control stands, scored like any stated result (literature_direction, the qualitative path)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['conversion']], 'support_refs': list(native['conversion_refs'])}
        if native['conversion'] is not None:
            result['direction_field_support'] = native['conversion_support']      # the support class of the fact conversion_detected_above_control, the one field the statement is derived from
    return result
