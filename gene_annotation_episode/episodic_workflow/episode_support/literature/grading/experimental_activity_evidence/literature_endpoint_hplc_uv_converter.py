"""Endpoint_hplc_uv converter: turns the grader's result into what the A105 endpoint_conversion sheet takes. DRAFT of 2026-11-22, owner to correct.

Hand-built, private to endpoint_hplc_uv, deterministic. Input: the result of grade_endpoint_hplc_uv. Output: the sheet's input (the 'extraction'
grade_assay takes, with assay_type 'endpoint_conversion'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for every
sheet component that an HPLC end point cannot honestly fill, the reason it stays null. It follows the shape of literature_spectro_direct_converter.py;
the class core (the effect quantities, their order, their anchors) is the endpoint_conversion class's: literature_endpoint_conversion_direction.py and
the constants ENDPOINT_* of literature_row_contract.py.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its quantity, the best-determined in the class order ENDPOINT_EFFECT_ORDER
                  (literature_endpoint_conversion_direction.select_endpoint_effect):
                    conversion_difference  (fraction)  the share converted over the paper's own control: the stated net_conversion_percent / 100, or,
                                           when no net value is stated but the test and the control conversion both are, the test minus the control
                                           (exact arithmetic on the paper's two numbers, origin 'derived')
                    conversion_fraction    (fraction)  the stated conversion_percent / 100, used only when no control conversion is stated
                    endpoint_amount        (uM)        the stated product concentration, in uM by the exact factor of its unit
                  A stated value in another unit of the record's vocabulary is multiplied by its exact factor (FIXED_BY_DEFINITION: a percent is a
                  hundredth; 1 mM is 1000 uM, 1 nM is 0.001 uM): the value is the paper's, only its unit spelling changes. quantity_kind of the
                  extraction names the kind of the effect, which the direction function reads. completion_time and completion_time_ratio are never
                  filled by this type: the time a reaction needs to finish is the endpoint_time_course_completion type's.
                  When the test and the control conversion are both stated and the test is not above the control, the result is NOT an effect: no effect is
                  filled (and neither the raw share nor the product amount stands in for it, because the paper's own control is at least as high), the
                  criterion signal_over_control is conflicting, and only the paper's own sentence (conversion_detected_above_control) can give a direction.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). A difference computed from two values has no stated
                  spread: null. Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal, condition test/reference, the assertion and
alternative predictions.
qualitative_effect  only when NO effect is filled: statement 'interaction_detected' (read "conversion detected"), 'interaction_not_detected' (read
                  "conversion not detected") or 'interaction_not_stated', with the refs of the fact conversion_detected_above_control that states it. The
                  direction_field_support is then the quote support of that one fact (None when it is not stated). A stated effect fixes the direction;
                  the statement is then not used. A result stated in words alone counts less than a measured one (the contract's stated_strength).

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
measurement_identity       estimate_defined
calibration_applicability  standard_curve_range + standard_curve_points + detection_limit_share
matrix_interference        matrix_matched_calibration
background_alternatives    spontaneous_reaction_control + zero_time_sample
attribution_supported      enzyme_dependence + signal_over_control
endpoint_alignment         endpoint_time_stated + reaction_stopped
conversion_denominator     denominator_established
product_identity           product_identified + mass_balance
assertion_relevance        native_reaction
condition_scope            purified_enzyme
sampling_basis             replicates
variance_correspondence    supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet';
JUDGES maps each such criterion and reason to its judgement). Each judgement is a researched value of THIS assay made gradual (SOP step 3): full
agreement at the researched good value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the assay gives
(never a step), unknown when the paper states nothing, never conflicting for a short count. A value at or beyond its zero end is conflicting (what the
paper itself shows against the standard). A sheet criterion that is supported carries the smallest degree of its members that have one. Quote support
(literature_quote_support.apply_support) lowers the degree of a supported criterion and never changes a status. Combined status: any conflicting ->
conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet criterion whose members are all not_applicable is
not selected.

How the class decisions apply here (owner to confirm). Preparations: the enzyme preparation is analyte_preparation_ref, the other keys stay None (no
immobilized enzyme, no surface). Qualitative statements keep the existing vocabulary, read "conversion detected / not detected / not stated". Direction
and strength of a stated result: literature_endpoint_conversion_direction (larger is stronger for the shares and the amount, never opposing); controls,
blanks, the end-point alignment and the rest lower the WEIGHT only.

Range review (SOP step 3; Q1 what it catches, Q2 general or lab-specific, Q3 absolute or relative to something the paper states, Q4 how badly a wrong
value misleads and whether the shape fits, Q5 consistency with the other assays). Every literature citation is from memory and not verified; every
number is EXPERT_REVIEW, owner to confirm.
-----------------------------------------------------------------------------------------------------------------------------------
CURVE_EDGE_RATIO 1 -> CURVE_LOW_ZERO_FACTOR 0.1 and CURVE_HIGH_ZERO_FACTOR 5, judged on the log of the read product concentration over the lowest and over
the highest standard.
  Q1 a product read outside the concentrations the standard curve covers is an extrapolation of the detector response: below the lowest standard the
  peak nears the detection limit and the integration error grows; above the highest the detector response bends over. Q2 general: method validation
  (ICH Q2(R1), from memory) sets the quantification limit at a signal-to-noise of 10 and the detection limit at 3, so the lowest standard (usually at or
  above the quantification limit) is at least about three times above the detection limit; a reading a tenth of it is below the detection limit of any
  ordinary UV method. For the top, calibrations usually end near 0.5 to 1 absorbance unit and a UV flow cell is no longer linear near 1.5 to 2 (stray
  light, Beer-Lambert), a factor of 2 to 5 above the top standard; at 5 times the peak is saturated. Q3 relative to the paper's own curve, and the grader
  records both ratios. The read amount and the curve are compared as the passage states them: when the paper dilutes the sample before the injection the
  two are on different scales, which no field records (a grader gap, only the degree of this one criterion is affected). Q4 the error of an extrapolation
  grows with the distance from the calibrated range; the scale is the log of the ratio because concentrations run over decades; inside the range the
  degree is full, at the zero end the criterion is conflicting (the paper's own numbers show the amount is not in the range of its standard). A wrong end
  moves one degree, never a direction. Q5 the same log-ratio ramp as the series ends of the binding assays.
MIN_CALIBRATION_POINTS 5, CALIBRATION_POINTS_ZERO 2.
  Q1 a standard curve of too few concentrations cannot show that the response is linear. Q2 general: five concentrations is the usual minimum for a
  linearity claim (ICH Q2(R1), from memory); the exact 5 is a judgement. Q3 absolute (a count). Q4 a straight line has two parameters, so two points
  leave no residual degree of freedom (degree 0, supported, never conflicting: a short curve is weaker evidence, not evidence against); each added point
  is one more the line must pass through: the degree rises linearly with points - 2 (3 give 1/3, 4 give 2/3). Q5 the same residual-degree-of-freedom count
  as the SPR steady-state KD and the saturation curve of spectro_direct.
DETECTION_LIMIT_FULL_SHARE 0.02 -> DETECTION_LIMIT_ZERO_SHARE 0.5, judged on the log of the detection limit over the starting substrate.
  Q1 a method whose limit is a large part of the substrate can not see a small conversion, so a non-detection says little and a small reported share
  is uncertain. Q2 general: the limit of HPLC-UV for a chromophoric product is of the order of a micromolar (a refractive-index detector is about two
  orders worse), against assay substrates of 0.1 to 10 mM, i.e. a limit of about 0.01 to 1 percent of the substrate (UV) and some percent (RI), from
  memory. The full end 0.02 is the same two percent as the noise end of a net conversion in the class scale (below it the class reads no effect); the
  zero end 0.5 is a limit at half the substrate, where only a conversion above half could be seen. Q3 relative to the paper's own substrate, which the
  grader records with the limit. Q4 limits span orders of magnitude so the scale is the log of the share (a limit of 10 percent gives about 0.5); a wrong
  end moves one degree. Q5 the same log-ratio ramp as the other ratio judgements.
CONTROL_SHARE_FULL 0.1 -> CONTROL_SHARE_ZERO 1.0, judged on the share b = control conversion / test conversion (linear).
  Q1 a conversion that is mostly the spontaneous conversion of the substrate (or a contaminating activity shown by an inactive-enzyme control) is not
  the enzyme's. Q2 general: when the control is at most a tenth of the signal, the subtraction changes the result by at most a tenth, which is within the
  usual replicate spread of an HPLC peak area (a few to ten percent); from memory. At a control equal to the test nothing is attributed to the enzyme.
  Q3 relative to the paper's own control, which the grader records beside the test. Q4 the error of a control-corrected result is proportional to the
  share of the signal that is subtracted, so the scale is linear in that share (b = 0.5 gives about 0.56); at or beyond 1 the test is no larger than the
  paper's own control and the criterion is conflicting (SOP step 3 rule 5); the size of the effect itself is read by the strength scale, not here. Q5 a
  ramp that falls as the background share grows, like the consumed-share ramp of spectro_direct.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a conversion from one reaction, whose reaction-to-reaction spread is unseen. Q2 general (triplicate practice). Q3 absolute count of independent
  reactions; repeated injections of one reaction are not replicates (the form keeps them in their own field). Q4 precision of a mean (1 / sqrt(n)), the
  same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the controls, the zero-time sample, the enzyme dependence, the product identification, the mass balance, the stop step, the
denominator, the matrix control, the native substrate and the purified enzyme): the paper's own statement decides; yes is supported, no is conflicting,
silence is unknown. They have no researched value to soften. NOT judged, and why: the end-point time (it is stated, not compared: whether it is long
against the half-time of the reaction needs the rate, which this record does not hold); the detector, the wavelength and the enzyme concentration
(recorded for the reviewer); the repeated injections (technical repeats); the pH and the temperature (the claim carries no condition, and the identity
block records the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for
this assay, drafted 2026-11-22, owner to confirm:
  What does it measure; absolute or relative? How much of the substrate was converted (or how much product there is) after one stated time, against an
  authentic standard of the product: an absolute share or concentration, with substrate and product separated and both visible. But an end point is not
  a constant of the enzyme: it depends on the enzyme amount and the time the paper chose, so the number alone does not say how fast or how well.
  Is there a reference range we would trust if the paper stated less (as for KD)? No such range as for kcat or KD; the strength scale has only a noise
  floor (a few percent) and a near-complete conversion, so an unstated detail cannot be filled from a trusted range.
  What does an unstated control or calibration do to the number's meaning? A no-enzyme control left unsaid is usually benign for a large conversion but
  is the false positive of a small one (autohydrolysis of esters, phosphates and sugars over hours); the contaminating activity of a host enzyme in a
  purified preparation is shown by no blank, only by the enzyme dependence; a peak named from a retention time alone can be the wrong compound, but a
  quantification against an authentic standard is the method's core, so an unstated calibration range is a magnitude risk, not an existence risk.
  If we assume it is fine and are wrong, how badly does the score mislead? A background or a host activity counted as the enzyme's: the direction is wrong
  for a small conversion; a calibration or timing gap changes the size, not the existence; less severe than a pull-down band, about as severe as a rate.
  Consistent with KD and spectro_direct? The default 0.85 equals spectro_direct (an absolute readout with resolved species, but no trusted reference
  range) and is under the KD anchor 0.90; the criteria that guard against a false conversion are lower, the benign ones are at or just under the anchor.
  default 0.85. background_alternatives 0.75 (a real gap: the blank and the time-zero sample separate conversion from spontaneous chemistry).
  attribution_supported 0.80 (a contaminating host activity is shown only by the enzyme dependence, often left unsaid). matrix_interference 0.80 (a
  co-eluting peak from the buffer, a cofactor or a lysate adds to the product peak; the standard in matrix and the internal standard show it).
  calibration_applicability 0.90, endpoint_alignment 0.90, sampling_basis 0.90 (benign when unstated: quantification against a standard is the method's
  core and a wrong range changes the size; a stop step and a time are routine in an end-point protocol; triplicates are usual).
  measurement_identity, conversion_denominator, product_identity, assertion_relevance, condition_scope take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_conversion_direction import select_endpoint_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import SUPPORTS, apply_support

VERSION = 'a105_endpoint_hplc_uv_converted_v1'
CRITERIA_MAP = {'measurement_identity': ('estimate_defined',), 'calibration_applicability': ('standard_curve_range', 'standard_curve_points', 'detection_limit_share'),
                'matrix_interference': ('matrix_matched_calibration',), 'background_alternatives': ('spontaneous_reaction_control', 'zero_time_sample'),
                'attribution_supported': ('enzyme_dependence', 'signal_over_control'), 'endpoint_alignment': ('endpoint_time_stated', 'reaction_stopped'),
                'conversion_denominator': ('denominator_established',), 'product_identity': ('product_identified', 'mass_balance'),
                'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',), 'sampling_basis': ('replicates',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
UM_PER_UNIT = {'nM': 1.0e-3, 'uM': 1.0, 'mM': 1.0e3}  # FIXED_BY_DEFINITION: exact factors of a concentration unit to micromolar.
CURVE_EDGE_RATIO = 1.0  # FIXED_BY_DEFINITION: the edge of the paper's own standard curve, where the read amount is at the end of the calibrated range (full agreement up to it).
CURVE_LOW_ZERO_FACTOR = 0.1  # EXPERT_REVIEW, owner to confirm: a product read at a tenth of the lowest standard is below the detection limit of an ordinary UV method (ICH Q2(R1): LOQ at S/N 10, LOD at S/N 3; from memory, not verified); no agreement there; falls from the lowest standard linearly in the log of the ratio.
CURVE_HIGH_ZERO_FACTOR = 5.0  # EXPERT_REVIEW, owner to confirm: a product read at 5 times the highest standard is beyond the linear range of a UV flow cell (calibrations end near 0.5 to 1 AU and linearity is lost near 1.5 to 2 AU; from memory, not verified); no agreement there; falls from the highest standard linearly in the log of the ratio.
MIN_CALIBRATION_POINTS = 5  # EXPERT_REVIEW, owner to confirm: fewest concentrations of a standard curve that can show a linear response (ICH Q2(R1) names five, from memory, not verified); full agreement from it.
CALIBRATION_POINTS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: a straight line has two parameters, so two points leave no residual degree of freedom (degree 0, supported, never conflicting: a short curve is weaker evidence); between this and MIN_CALIBRATION_POINTS the degree rises linearly with the residual degrees of freedom (points - 2).
DETECTION_LIMIT_FULL_SHARE = 0.02  # EXPERT_REVIEW, owner to confirm: a detection limit of 2 percent of the starting substrate (the noise end of a net conversion in the class scale) lets a 2 percent conversion be seen; full agreement up to it. From memory, not verified.
DETECTION_LIMIT_ZERO_SHARE = 0.5  # EXPERT_REVIEW, owner to confirm: a limit at half the starting substrate sees only conversions above a half (no agreement); falls from DETECTION_LIMIT_FULL_SHARE linearly in the log of the share, because limits run over decades.
CONTROL_SHARE_FULL = 0.1  # EXPERT_REVIEW, owner to confirm: a control at most a tenth of the test signal changes the control-corrected result by at most a tenth, within the usual spread of an HPLC peak area; full agreement up to it. From memory, not verified.
CONTROL_SHARE_ZERO = 1.0  # EXPERT_REVIEW, owner to confirm: a control as large as the test attributes nothing to the enzyme (the test is no larger than the paper's own control: conflicting); falls from CONTROL_SHARE_FULL linearly in the share, because the error of a corrected result is proportional to the share subtracted.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate reactions; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent reactions falls as 1 / sqrt(n); never conflicting for a stated count.
# The effect quantities this type can fill, in the class's own names (QUANTITY_KINDS['endpoint_conversion']), their anchor unit (ENDPOINT_STRENGTH_ANCHORS) and the
# spread field of each (the difference computed from two stated values has none).
ANCHOR_UNIT = {'conversion_difference': 'fraction', 'conversion_fraction': 'fraction', 'endpoint_amount': 'uM'}
SPREAD_OF = {'conversion_difference': 'net_conversion_spread', 'conversion_fraction': 'conversion_spread', 'endpoint_amount': 'product_amount_spread'}
KIND_WITHOUT_EFFECT = 'conversion_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'an_hplc_endpoint_has_no_matrix_recovery_measurement', 'attributed_signal': 'a_conversion_is_not_an_attribution_fraction', 'total_signal': 'a_conversion_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_an_endpoint_hplc_uv_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_endpoint_hplc_uv_record',
                'assertion_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'alternative_prediction': 'prediction_belongs_to_the_target_assertion_not_the_experiment', 'effect_degrees_of_freedom': 'no_student_t_model_selected'}
STATEMENTS = {'detected': 'interaction_detected', 'not_detected': 'interaction_not_detected', None: 'interaction_not_stated'}   # read "conversion detected" / "conversion not detected" / "conversion not stated" for this class


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


def _log(value, full, zero):
    """A ratio limit on the log scale, for _graded."""
    return math.log(value), math.log(full), math.log(zero)


def _judge_curve(native):
    # the read amount against the two ends of its own standard curve: only the side it lies outside of is ramped; inside the range the degree is full
    refs = native['curve_refs']
    low, high = native['read_over_curve_low'], native['read_over_curve_high']
    limits = []
    if low < CURVE_EDGE_RATIO:
        limits.append(_log(low, CURVE_EDGE_RATIO, CURVE_LOW_ZERO_FACTOR))
    if high > CURVE_EDGE_RATIO:
        limits.append(_log(high, CURVE_EDGE_RATIO, CURVE_HIGH_ZERO_FACTOR))
    if not limits:
        return _verdict('supported', refs, 1.0)
    return _graded(refs, *limits)


def _judge_points(native):
    # never conflicting: a short curve is weaker evidence; degree 0 at no residual degree of freedom
    return _verdict('supported', native['calibration_points_refs'], max(0.0, min(1.0, _share(native['calibration_points'], MIN_CALIBRATION_POINTS, CALIBRATION_POINTS_ZERO))))


def _judge_detection_limit(native):
    return _graded(native['detection_limit_refs'], _log(native['detection_limit_over_substrate'], DETECTION_LIMIT_FULL_SHARE, DETECTION_LIMIT_ZERO_SHARE))


def _judge_control(native):
    # the share of the test signal that the control accounts for; at or beyond 1 the test is no larger than the paper's own control
    return _graded(native['control_refs'], (native['control_percent'] / native['test_percent'], CONTROL_SHARE_FULL, CONTROL_SHARE_ZERO))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('standard_curve_range', 'standard_curve_range_recorded_for_the_sheet'): _judge_curve, ('standard_curve_points', 'calibration_points_recorded_for_the_sheet'): _judge_points,
          ('detection_limit_share', 'detection_limit_recorded_for_the_sheet'): _judge_detection_limit, ('signal_over_control', 'control_comparison_recorded_for_the_sheet'): _judge_control,
          ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _anchored(value, unit):
    """A stated value in the anchor unit of its quantity, by the exact factor of its unit (a percent to a fraction, a concentration to uM)."""
    return value / PERCENT_PER_FRACTION if unit == 'percent' else value * UM_PER_UNIT[unit]


def _stated(native, name, quantity, ref):
    """The stated record quantity ``name`` as an effect operand of ``quantity`` in its anchor unit, or None when not stated (its 'support' is the extraction's)."""
    operand = native['quantities'][name]
    if operand['status'] != 'point':
        return None
    return _operand(_anchored(operand['value'], operand['unit']), ANCHOR_UNIT[quantity], 'endpoint_hplc_uv_' + quantity + ':' + ref, operand['source_refs'], operand['origin'], name, operand['support'])


def _difference(native, ref):
    """The conversion difference: the stated net value, or the test minus the control when both are stated (origin 'derived'); None when neither is possible.
    Returns (operand or None, whether it is the paper's own stated net value)."""
    net = _stated(native, 'net_conversion_percent', 'conversion_difference', ref)
    if net is not None:
        return net, True
    test, control = _stated(native, 'conversion_percent', 'conversion_difference', ref), _stated(native, 'control_conversion_percent', 'conversion_difference', ref)
    if test is None or control is None:
        return None, False
    refs = list(dict.fromkeys([*test['source_refs'], *control['source_refs']]))
    return _operand(test['value'] - control['value'], 'fraction', 'endpoint_hplc_uv_conversion_difference:' + ref, refs, 'derived', 'conversion_percent', max(test['support'], control['support'], key=SUPPORTS.index)), False


def _variance(graded, quantity, ref, stated_net):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of the chosen ``quantity``."""
    native = graded['native']
    if quantity == 'conversion_difference' and not stated_net:
        return None, 'conversion_difference_computed_from_two_values_has_no_stated_spread', []
    spread_name = SPREAD_OF[quantity]
    spread = native['quantities'][spread_name]
    kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, spread_name + '_not_given', []
    if kind is None:
        return None, 'spread_kind_not_stated', []
    sd = _anchored(spread['value'], spread['unit'])
    if kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_endpoint_hplc_uv(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    difference, stated_net = _difference(native, ref)
    stated = {'conversion_difference': difference, 'conversion_fraction': _stated(native, 'conversion_percent', 'conversion_fraction', ref),
              'endpoint_amount': _stated(native, 'product_amount', 'endpoint_amount', ref)}
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if difference is not None and difference['value'] <= 0:      # the test is no better than the paper's own control: not an effect, and no raw value stands in for it
        null_components['effect'] = 'conversion_not_above_the_papers_own_control'
        null_components['effect_variance'] = 'no_effect'
    elif all(operand is None for operand in stated.values()):
        null_components['effect'] = 'no_conversion_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_endpoint_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = chosen, effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref, stated_net)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, ANCHOR_UNIT[chosen] + '_squared', 'endpoint_hplc_uv_' + chosen + '_variance:' + ref, variance_refs, 'derived', SPREAD_OF[chosen])
    null_components.update({role: reason for role, reason in NULL_REASONS.items()})
    interpretations = {}
    for sheet_criterion, members in CRITERIA_MAP.items():
        graded_members = [_criterion(graded, m) for m in members if graded['criteria'][m]['status'] != 'not_applicable']
        if not graded_members:
            continue
        statuses = [m['status'] for m in graded_members]
        status = 'conflicting' if 'conflicting' in statuses else 'unknown' if 'unknown' in statuses else 'supported'
        refs = list(dict.fromkeys(r for m in graded_members for r in m['support_refs']))
        interpretations[sheet_criterion] = {'status': status, 'support_refs': refs if status in ('supported', 'conflicting') else []}
        degrees = [m['degree'] for m in graded_members if 'degree' in m]
        if status == 'supported' and degrees:
            interpretations[sheet_criterion]['degree'] = min(degrees)      # the weakest member: a degree of a member is not averaged away
        supports = [s for m in members if graded['criteria'][m]['status'] != 'not_applicable' for s in native['support'][m]]
        interpretations[sheet_criterion] = apply_support(interpretations[sheet_criterion], supports)      # weak quote support lowers the degree of a supported criterion, never its status
    if quantities['effect_variance'] is not None:
        interpretations['variance_correspondence'] = {'status': 'supported', 'support_refs': quantities['effect_variance']['source_refs']}
    extraction = {'version': INPUT_VERSION, 'assay_type': 'endpoint_conversion', 'assertion_ref': native['assertion_ref'], 'quantity_kind': quantity_kind, 'quantities': quantities, 'interpretations': interpretations, 'prediction_model': None}
    result = {'version': VERSION, 'experiment_type': 'endpoint_hplc_uv', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no effect: the experiment's stated yes/no result stands, scored like any stated result (literature_direction, the qualitative path)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['conversion']], 'support_refs': list(native['conversion_refs'])}
        if native['conversion'] is not None:
            result['direction_field_support'] = native['conversion_support']      # the support class of the fact conversion_detected_above_control, the one field the statement is derived from
    return result
