"""Endpoint_enzymatic_assay converter: turns the grader's result into what the A105 endpoint_conversion sheet takes. DRAFT (2026-11-22), owner to correct.

Hand-built, private to endpoint_enzymatic_assay, deterministic. Input: the result of grade_endpoint_enzymatic_assay. Output: the sheet's input (the
'extraction' grade_assay takes, with assay_type 'endpoint_conversion'), the sheet itself (grade_assay run on it), the dependence keys the merger needs, and for
every sheet component that an end-point determination cannot honestly fill, the reason it stays null. Modelled on literature_spectro_direct_converter.py; the
class core is the endpoint_conversion class's (literature_endpoint_conversion_direction.py, A105_ENDPOINT_CONVERSION_INVENTORY.md), not the activity class's.

Quantities filled
-----------------
effect            ONE stated quantity in the anchor unit of its kind (ENDPOINT_STRENGTH_ANCHORS): the control-corrected share converted (kind
                  conversion_difference, fraction), the share converted (conversion_fraction, fraction) or the product amount (endpoint_amount, uM). Several
                  may be stated; the one used is the best-determined, in the class order ENDPOINT_EFFECT_ORDER
                  (literature_endpoint_conversion_direction.select_endpoint_effect). A stated value in another unit of the record's vocabulary is turned by
                  its exact factor (FIXED_BY_DEFINITION: a percent is a hundredth; nM, mM in uM; pmol, umol in nmol; uL in mL; a product amount in nmol over a
                  reaction volume in mL is a concentration in uM): the value is the paper's, only its unit spelling changes. A product amount in mol with no
                  stated reaction volume cannot become a concentration, and a share above 1 (above 100 percent) is not a fraction: neither is filled as an
                  effect (the reason is in null_components) and the next stated quantity, or the stated yes/no result, takes over. quantity_kind of the
                  extraction names the kind of the effect, which the direction function reads.
effect_variance   variance of that effect, in the anchor unit squared, only when the passage's spread of THAT quantity allows it:
                  standard_error -> se^2; standard_deviation -> sd^2 / n and only when the replicates criterion is supported;
                  confidence_interval -> not converted (needs its level and degrees of freedom). Otherwise null.
effect_precision  the sheet computes 1 / variance from the above.
Every other role stays null, with a reason (NULL_REASONS): recovery, attributed signal/total signal, condition test/reference, the assertion
and alternative predictions.
qualitative_effect  only when NO effect is filled: the paper's own statement whether it saw conversion above its control. statement 'interaction_detected' (read
                  "conversion detected"), 'interaction_not_detected' (read "conversion not detected") or 'interaction_not_stated', with the refs of the fact
                  conversion_detected_above_control that states it; direction_field_support is the quote support of that one fact (None when not stated). A
                  stated effect fixes the direction; the statement is then not used. A result stated in words alone counts less than a measured one: the
                  contract's stated_strength does that, nothing here.

Criteria mapping (grader criteria -> sheet criteria), CRITERIA_MAP
------------------------------------------------------------------
measurement_identity      estimate_identity
calibration_applicability standard_series_through_second_enzyme + standard_curve_fit + standard_series_size + read_inside_standard_series + non_detection_limit
matrix_interference       matrix_effect_addressed
background_alternatives   first_enzyme_controls
attribution_supported     enzyme_dependence
endpoint_alignment        endpoint_time_alignment + reporter_completion (the end point is the end of the first reaction AND of the second)
conversion_denominator    initial_substrate
product_identity          second_enzyme_specificity + product_identity (identity rests on the second enzyme's specificity, or on an independent identification)
assertion_relevance       native_reaction
condition_scope           purified_enzyme
sampling_basis            replicates
variance_correspondence   supported only when a variance was computed
The thresholds are judged here, not in the grader (it records facts only and hands them over with a reason ending in '_recorded_for_the_sheet'; JUDGES maps
each such criterion and reason to its judgement). Each judgement is a researched value of THIS assay made gradual (SOP step 3): full agreement at the researched
good value, falling smoothly to zero at a researched no-longer-meaningful value on the scale the physics of the assay gives (never a step), unknown when the paper
states nothing, never conflicting for a short count or a short time. A value at or beyond the zero end of a ramp that the paper's own numbers fix (R squared, the
read amount against its standards, the detection limit) is conflicting (what the paper itself shows against the standard). A sheet criterion that is supported
carries the smallest degree of its members that have one. Quote support (literature_quote_support.apply_support) lowers the degree of a supported criterion and
never changes a status. Combined status: any conflicting -> conflicting; else any unknown -> unknown; else supported. not_applicable members are dropped; a sheet
criterion whose members are all not_applicable is not selected. Sheet criteria with no counterpart here (none besides variance_correspondence, filled below) are
not selected.

How the class decisions apply here (owner to confirm). Preparations: the first enzyme's preparation is analyte_preparation_ref, the other keys stay None (no
immobilized enzyme, no surface). Qualitative statements keep the existing vocabulary. Direction and strength of a stated result:
literature_endpoint_conversion_direction (larger is stronger for a share and an amount); controls, blanks, the end-point alignment and the rest lower the WEIGHT
only. The class is not pooled (the effect is one of three quantities in different units).

THE VALUES BELOW ARE A FIRST DRAFT FOR THE OWNER (2026-11-22): every number is EXPERT_REVIEW, owner to confirm, and every literature statement is from the
drafter's memory of the method literature, NOT web-verified and NOT checked against a method paper; verify before relying on any of them. The owner's questions
are asked of each value (Q1 failure caught, Q2 general or lab-specific, Q3 absolute or relative, Q4 how badly a wrong value misleads and whether the shape fits,
Q5 consistency with the other assays).
-----------------------------------------------------------------------------------------------------------------------------------
R_SQUARED_SHORTFALL_FULL 0.01 -> R_SQUARED_SHORTFALL_ZERO 0.2 (standard_curve_fit), judged linearly in the log of 1 - R squared.
  Q1 a standard curve whose points do not lie on one line, so a read amount taken from it carries the scatter of the curve. Q2 general: the validation
  guideline for analytical procedures (ICH Q2) asks that the correlation coefficient of the linearity line be reported, and an R squared of 0.99 or better is the
  common practice for a calibration of an end-point enzymatic or colorimetric assay (from memory); an end-point kit states 'linear' at that level. Q3 absolute
  (a share of the variance), and the paper states it itself. Q4 1 - R squared is the share of the variance the line does not explain; it runs over decades, so
  the degree falls linearly in its log: R squared 0.99 gives degree 1, 0.98 about 0.77, 0.95 about 0.46, 0.9 about 0.23; at 0.8 a fifth of the variance is
  unexplained and the curve is no calibration (conflicting). Q5 a log ramp on a ratio of
  the same kind as the log ramps of the other assays; no other assay judges a curve fit.
MIN_STANDARD_POINTS 5 -> STANDARD_POINTS_ZERO 2 (standard_series_size).
  Q1 a standard curve drawn through too few standards, so its line, its linearity and its range are not shown. Q2 general: ICH Q2 recommends at least five
  concentrations for a linearity line (from memory); the exact 5 is that recommendation. Q3 absolute (a count). Q4 a straight line has two parameters (slope and
  intercept), so two standards use them up and leave no residual degree of freedom (degree 0, supported, never conflicting); each added standard is one more
  residual degree of freedom, so the degree rises linearly with count - 2 (3 give 1/3, 4 give 2/3, 5 give 1). Q5 the same residual-degree-of-freedom count as
  the series of the activity and binding assays.
READ_OVER_HIGH_FULL 1 -> READ_OVER_HIGH_ZERO 4 and READ_OVER_LOW_FULL 1 -> READ_OVER_LOW_ZERO 0.1 (read_inside_standard_series), each judged linearly in the log of the ratio.
  Q1 a read amount taken beyond the highest standard (an extrapolation of a line whose linearity was not shown there) or below the lowest (a signal at the blank's
  noise). Q2 general: a calibration is used only inside its range (ICH Q2: the range is the interval between the upper and lower concentration for which
  linearity, accuracy and precision are shown; from memory). The upper zero end 4: end-point enzymatic assays flatten at the top because the second enzyme or
  the cofactor, or the detector (absorbance above about 1.5 to 2), runs out, and a few tens of percent of error appear within a factor of two to four beyond the
  top standard; the choice of 4 is a judgement. The lower zero end 0.1: the blank-subtracted line of an enzymatic end point passes through the origin, so a read
  below the lowest standard is an interpolation toward the blank, and what limits it is the noise; the lowest standard is usually near the quantitation limit (a
  signal about ten times the noise), so a tenth of it is a signal about equal to the noise (no reading); from memory, a judgement. Q3 relative to the paper's own
  standards, which the grader records. Q4 a wrong value moves the degree of the calibration criterion, never the direction; the degree falls with the log of the
  distance because the relative error of an extrapolated reading grows with that distance (in the high direction) and as the inverse of the amount (low). Q5 the
  same idea as the concentration ends of the binding and activity assays (a series must bracket the quantity read).
INCUBATION_FULL_MIN 10 -> INCUBATION_ZERO_MIN 1 (reporter_completion, only when the paper does not state the fact 'second reaction went to completion'), judged linearly in
  the log of the time. Q1 the second reaction read before it ended, so the signal is a point on a rate and not the end of it. Q2 general: commercial and
  published end-point determinations of formate (formate dehydrogenase), D-glucose (glucose oxidase and peroxidase) and ammonia (glutamate dehydrogenase) read after
  about 10 to 30 minutes at 25 to 37 C (from memory); the first-order approach to completion needs about 4.6 half-times for 99 percent, which is ten minutes only for a
  half-time of a couple of minutes, a usual enzyme load. Q3 absolute but only a proxy: the real question (is the signal at its plateau) is the stated fact, and the
  fact decides first. Q4 a wrong value only lowers the degree; a time alone is not the paper against completion, so a short time gives degree 0, supported, never
  conflicting (as the cross-assay rule a for a time with no stated constant: no conflict without the paper's own number). Q5 the same shape as the time ramps of
  the binding assays, linear in log time.
LIMIT_FULL_FRACTION 0.05 -> LIMIT_ZERO_FRACTION 0.5 (non_detection_limit, only for a stated non-detection), judged linearly in the log of the detection limit over the initial
  substrate. Q1 a 'no conversion' that the assay could not have seen: a non-detection says as much as its limit allows. Q2 general: the limit of detection is what a
  non-detection is bounded by (ICH Q2); 0.05 is the noise end of the class's own scale for a share converted (ENDPOINT_STRENGTH_ANCHORS conversion_fraction), so a limit
  at or under 5 percent of the substrate sees what the class counts as signal; at half of the substrate a non-detection means nothing. Q3 relative to the paper's own
  initial substrate (the grader records both). Q4 only a non-detection is judged, so a wrong value lowers the weight of an absent result; at or beyond the zero end the
  paper's own numbers show the assay could not see a conversion (conflicting for this criterion; it never changes the direction). Q5 the same noise end as the
  strength scale, so one number is not told two ways.
MIN_REPLICATES 3, degree min(1, sqrt(n / 3)).
  Q1 a result from one experiment, whose preparation-to-preparation spread is unseen. Q2 general (triplicate practice). Q3 absolute count. Q4 precision of a mean (1 /
  sqrt(n)), the same sd^2 / n used for the variance. Q5 exactly the shared replicate rule.
Facts with no number (the controls, the specificity of the second enzyme, the matrix and recovery checks, the independent identification, the enzyme dependence, the
initial substrate, the native substrate, the purified enzyme, the stop of the reaction): the paper's own statement decides; yes is supported, no is conflicting, silence
is unknown. They have no researched value to soften. NOT judged, and why: the second enzyme's amount (a paper states it as units per millilitre of its own assay; whether it
suffices is the stated plateau fact and the incubation); the reporter's own absorbance or fluorescence (a decrease of NADH and an increase of NADPH run in opposite
directions, so no ratio to the blank fits both, and the standard curve already carries the signal's scale); the pH and the temperature (the claim carries no condition,
and the identity block records the temperature).

The unknown weight (WEIGHT_UNKNOWN_BY_TYPE and WEIGHT_UNKNOWN_BY_CRITERION in literature_row_contract.py; SOP step 3 rule 4). Questions answered for this assay,
owner to confirm:
  What does it measure; absolute or relative? The amount of one named small molecule in the stopped reaction, read through a SECOND enzyme from a reporter and a
  standard series of the same analyte: absolute (an amount or a share of the substrate), with a trusted reading when the series was run through the same assay.
  Is there a reference range we would trust if the paper stated less? Partly: the end-point determinations of formate, glucose, ammonia, ethanol and lactate are
  routine and their analytical ranges are known (micromolar to millimolar), so the standard series is usually fine; what a paper may not state is the blank.
  What does an unstated control or calibration do to the number's meaning? The blank is the real hazard: a contaminating analyte in the substrate, the buffer or the
  first enzyme's stock (ammonium sulphate in a protein stock is the standard case for an ammonia read) is counted as product, and the amount read is then too high
  by the contamination. An unstated specificity check leaves open that the second enzyme reads the substrate itself. An unstated matrix check leaves open
  inhibition of the second enzyme by the reaction buffer (low reading, not a false positive). An unstated standard series is benign (the method cannot be read
  without one) and so is an unstated replicate count.
  If we assume it is fine and are wrong, how badly does the score mislead? A contaminated blank or a cross-reacting second enzyme makes a false conversion: wrong
  for a weak conversion, an overstatement for a strong one; worse than a KD (a magnitude only), less bad than a pull-down band (a pure artefact).
  Consistent with KD? Below the activity anchor (spectro_direct 0.85): there are two enzymes to go wrong, not one.
  default 0.80. background_alternatives 0.65 (the blank is what separates conversion from a contaminating analyte). product_identity 0.70 (identity rests on the
  second enzyme's specificity, which is often assumed and not shown). matrix_interference 0.75. calibration_applicability 0.85 and sampling_basis 0.90 (benign when
  unstated: the standard series is the method itself, and triplicates are usual). The others take the default.
"""
import math

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import INPUT_VERSION, ROLES, grade_assay
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_endpoint_conversion_direction import select_endpoint_effect
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_quote_support import apply_support

VERSION = 'a105_endpoint_enzymatic_assay_converted'
CRITERIA_MAP = {'measurement_identity': ('estimate_identity',),
                'calibration_applicability': ('standard_series_through_second_enzyme', 'standard_curve_fit', 'standard_series_size', 'read_inside_standard_series', 'non_detection_limit'),
                'matrix_interference': ('matrix_effect_addressed',), 'background_alternatives': ('first_enzyme_controls',), 'attribution_supported': ('enzyme_dependence',),
                'endpoint_alignment': ('endpoint_time_alignment', 'reporter_completion'), 'conversion_denominator': ('initial_substrate',),
                'product_identity': ('second_enzyme_specificity', 'product_identity'), 'assertion_relevance': ('native_reaction',), 'condition_scope': ('purified_enzyme',),
                'sampling_basis': ('replicates',)}
PERCENT_PER_FRACTION = 100.0  # FIXED_BY_DEFINITION: a percent is a hundredth.
UM_PER_UNIT = {'nM': 1.0e-3, 'uM': 1.0, 'mM': 1.0e3}  # FIXED_BY_DEFINITION: a concentration unit in micromolar.
NMOL_PER_UNIT = {'pmol': 1.0e-3, 'nmol': 1.0, 'umol': 1.0e3}  # FIXED_BY_DEFINITION: an amount unit in nanomoles (nmol per mL is micromolar).
ML_PER_UNIT = {'uL': 1.0e-3, 'mL': 1.0}  # FIXED_BY_DEFINITION: a volume unit in millilitres.
R_SQUARED_SHORTFALL_FULL = 0.01  # EXPERT_REVIEW, owner to confirm: 1 - R squared of the standard curve at 0.01 (R squared 0.99, the usual practice for an end-point calibration, ICH Q2 asks it be reported; from memory); full agreement up to it.
R_SQUARED_SHORTFALL_ZERO = 0.2  # EXPERT_REVIEW, owner to confirm: a fifth of the variance unexplained (R squared 0.8): the curve is no calibration (no agreement); falls from the full end linearly in the log of 1 - R squared, which runs over decades.
MIN_STANDARD_POINTS = 5  # EXPERT_REVIEW, owner to confirm: fewest different standards of a usable curve (ICH Q2 recommends at least five concentrations for a linearity line; from memory); full agreement from it.
STANDARD_POINTS_ZERO = 2  # EXPERT_REVIEW, owner to confirm: a line has two parameters (slope, intercept), so two standards leave no residual degree of freedom (degree 0, supported, never conflicting); between this and MIN_STANDARD_POINTS the degree rises linearly with the residual degrees of freedom (count - 2).
READ_OVER_HIGH_FULL = 1.0  # EXPERT_REVIEW, owner to confirm: a read amount at or under the highest standard is inside the range (ICH Q2: the range is where linearity is shown); full agreement up to it.
READ_OVER_HIGH_ZERO = 4.0  # EXPERT_REVIEW, owner to confirm: four times the highest standard: the second enzyme, the cofactor or the detector (absorbance above about 1.5 to 2) has saturated and the extrapolated line is no reading (no agreement); falls from the full end linearly in the log of the ratio. A judgement, from memory.
READ_OVER_LOW_FULL = 1.0  # EXPERT_REVIEW, owner to confirm: a read amount at or over the lowest standard is inside the range; full agreement from it.
READ_OVER_LOW_ZERO = 0.1  # EXPERT_REVIEW, owner to confirm: a tenth of the lowest standard (usually near the quantitation limit, a signal about ten times the noise) is a signal about equal to the noise (no agreement); falls from the full end linearly in the log of the ratio. A judgement, from memory.
INCUBATION_FULL_MIN = 10.0  # EXPERT_REVIEW, owner to confirm: end-point determinations with a second enzyme are read after about 10 to 30 minutes (formate, D-glucose, ammonia kits and methods; from memory); full agreement from it, used only when the paper does not state that the second reaction was complete.
INCUBATION_ZERO_MIN = 1.0  # EXPERT_REVIEW, owner to confirm: a minute with the second enzyme is a rate reading for an ordinary enzyme load, not an end point (no agreement, degree 0, supported, never conflicting: a time alone is not the paper against completion); falls from the full end linearly in log time.
LIMIT_FULL_FRACTION = 0.05  # EXPERT_REVIEW, owner to confirm: a detection limit at or under 5 percent of the initial substrate (the noise end of the class's conversion_fraction scale, ENDPOINT_STRENGTH_ANCHORS) lets a stated non-detection stand; full agreement up to it.
LIMIT_ZERO_FRACTION = 0.5  # EXPERT_REVIEW, owner to confirm: a detection limit at half of the initial substrate means a non-detection says nothing (no agreement); falls from the full end linearly in the log of the limit over the substrate.
MIN_REPLICATES = 3  # EXPERT_REVIEW, owner to confirm: fewest independent replicate experiments; full agreement from it. Below it the degree is min(1, sqrt(n / MIN_REPLICATES)): the standard error of a mean over n independent experiments falls as 1 / sqrt(n); never conflicting for a stated count.
# The kind of each effect (QUANTITY_KINDS['endpoint_conversion']), the record quantity that states it and its anchor unit (literature_row_contract.ENDPOINT_STRENGTH_ANCHORS).
QUANTITY_OF_KIND = {'conversion_difference': 'net_conversion_percent', 'conversion_fraction': 'conversion_percent', 'endpoint_amount': 'product_amount'}
ANCHOR_UNIT = {'conversion_difference': 'fraction', 'conversion_fraction': 'fraction', 'endpoint_amount': 'uM'}
KIND_WITHOUT_EFFECT = 'conversion_fraction'  # the kind of an extraction that fills no effect (a qualitative statement, or nothing)
NULL_REASONS = {'recovery': 'endpoint_enzymatic_assay_states_no_recovery_percent', 'attributed_signal': 'an_endpoint_conversion_is_not_an_attribution_fraction', 'total_signal': 'an_endpoint_conversion_is_not_an_attribution_fraction',
                'condition_test': 'no_matched_nuisance_condition_response_in_an_endpoint_enzymatic_assay_record', 'condition_reference': 'no_matched_nuisance_condition_response_in_an_endpoint_enzymatic_assay_record',
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


def _judge_r_squared(native):
    shortfall = max(1.0 - native['r_squared'], R_SQUARED_SHORTFALL_FULL)      # at or under the full end the degree is 1 whatever the shortfall (a perfect fit has shortfall 0)
    return _graded(native['r_squared_refs'], _log(shortfall, R_SQUARED_SHORTFALL_FULL, R_SQUARED_SHORTFALL_ZERO))


def _judge_standard_points(native):
    degree = max(0.0, min(1.0, _share(native['standard_points'], MIN_STANDARD_POINTS, STANDARD_POINTS_ZERO)))      # a short series lowers the degree and never conflicts
    return _verdict('supported', native['standard_points_refs'], degree)


def _judge_read_position(native):
    # each end that the paper gives keeps its ramp (conflicting at its zero end, from the paper's own numbers); the ends not given are not judged
    limits = []
    if native['read_over_standard_high'] is not None:
        limits.append(_log(native['read_over_standard_high'], READ_OVER_HIGH_FULL, READ_OVER_HIGH_ZERO))
    if native['read_over_standard_low'] is not None:
        limits.append(_log(native['read_over_standard_low'], READ_OVER_LOW_FULL, READ_OVER_LOW_ZERO))
    return _graded(native['standard_refs'], *limits)


def _judge_incubation(native):
    degree = max(0.0, min(1.0, _share(math.log(native['incubation_minutes']), math.log(INCUBATION_FULL_MIN), math.log(INCUBATION_ZERO_MIN))))      # a short time lowers the degree and never conflicts
    return _verdict('supported', native['incubation_refs'], degree)


def _judge_limit(native):
    return _graded(native['limit_refs'], _log(native['limit_over_initial'], LIMIT_FULL_FRACTION, LIMIT_ZERO_FRACTION))


def _judge_replicates(native):
    if native['replicate_independent'] != 'yes':
        return _verdict('unknown', native['replicate_refs'])      # independence not stated (a stated no is the grader's conflicting)
    return _verdict('supported', native['replicate_refs'], min(1.0, math.sqrt(native['replicate_count'] / MIN_REPLICATES)))      # precision of the mean, see MIN_REPLICATES


# (criterion, the reason with which the grader hands it to the sheet) -> the sheet's judgement of the recorded facts
JUDGES = {('standard_curve_fit', 'r_squared_recorded_for_the_sheet'): _judge_r_squared, ('standard_series_size', 'standard_points_recorded_for_the_sheet'): _judge_standard_points,
          ('read_inside_standard_series', 'read_position_recorded_for_the_sheet'): _judge_read_position, ('reporter_completion', 'incubation_recorded_for_the_sheet'): _judge_incubation,
          ('non_detection_limit', 'detection_limit_recorded_for_the_sheet'): _judge_limit, ('replicates', 'replicate_count_recorded_for_the_sheet'): _judge_replicates}


def _criterion(graded, name):
    """The answer for one criterion: the grader's own, or, where it handed the recorded facts to the sheet, the sheet's judgement of them (the grader holds no threshold)."""
    judge = JUDGES.get((name, graded['reasons'][name]))
    return graded['criteria'][name] if judge is None else judge(graded['native'])


def _operand(value, unit, key, refs, origin, component, support=None):
    operand = {'value': value, 'unit': unit, 'status': 'point', 'reason': None, 'measurement_keys': [key], 'source_refs': refs, 'origin': origin, 'native_component': component}
    return operand if support is None else {**operand, 'support': support}


def _in_anchor(native, name, kind):
    """(the quantity ``name`` of the record in the anchor unit of ``kind``, None) or (None, the reason it cannot be put there)."""
    operand = native['quantities'][name]
    if operand['status'] != 'point':
        return None, name + '_not_stated'
    unit = operand['unit']
    if ANCHOR_UNIT[kind] == 'fraction':
        return (operand['value'] / PERCENT_PER_FRACTION if unit == 'percent' else operand['value']), None
    if unit in UM_PER_UNIT:
        return operand['value'] * UM_PER_UNIT[unit], None
    volume = native['quantities']['reaction_volume']
    if volume['status'] != 'point':
        return None, 'amount_in_moles_without_reaction_volume'
    return operand['value'] * NMOL_PER_UNIT[unit] / (volume['value'] * ML_PER_UNIT[volume['unit']]), None      # nmol per mL is micromolar


def _stated_effects(native, ref):
    """({kind: effect operand in the anchor unit} of the stated quantities that can be an effect, [reason of each stated quantity that cannot])."""
    stated, unusable = {}, []
    for kind, quantity in QUANTITY_OF_KIND.items():
        operand = native['quantities'][quantity]
        if operand['status'] != 'point':
            continue
        value, reason = _in_anchor(native, quantity, kind)
        if reason is None and ANCHOR_UNIT[kind] == 'fraction' and value > 1.0:
            reason = 'conversion_above_one_is_not_a_fraction'
        if reason is not None:
            unusable.append(reason)
            continue
        stated[kind] = _operand(value, ANCHOR_UNIT[kind], 'endpoint_enzymatic_assay_' + kind + ':' + ref, operand['source_refs'], operand['origin'], quantity, operand['support'])
    return stated, unusable


def _variance(graded, kind, ref):
    """Return (variance in the anchor unit squared or None, reason or None, refs) of the spread of the quantity that states ``kind``."""
    native = graded['native']
    quantity = QUANTITY_OF_KIND[kind]
    spread = native['quantities'][quantity + '_spread']
    spread_kind = native['spread_kind']
    if spread['status'] != 'point':
        return None, quantity + '_spread_not_given', []
    if spread_kind is None:
        return None, 'spread_kind_not_stated', []
    sd, reason = _in_anchor(native, quantity + '_spread', kind)
    if reason is not None:
        return None, reason, []
    if spread_kind == 'standard_error':
        return sd * sd, None, spread['source_refs']
    if spread_kind == 'standard_deviation':
        count = native['quantities']['replicate_count']
        if _criterion(graded, 'replicates')['status'] != 'supported':
            return None, 'sd_needs_independent_replicates_to_become_a_variance_of_the_estimate', []
        return sd * sd / count['value'], None, list(dict.fromkeys([*spread['source_refs'], *count['source_refs']]))
    return None, 'confidence_interval_not_converted', []


def convert_endpoint_enzymatic_assay(graded):
    native = graded['native']
    ref = graded['experiment_ref']
    quantities = dict.fromkeys(ROLES)
    null_components = {}
    stated, unusable = _stated_effects(native, ref)
    quantity_kind, effect_support = KIND_WITHOUT_EFFECT, None
    if not stated:
        null_components['effect'] = unusable[0] if unusable else 'no_endpoint_quantity_given_as_a_point_value'
        null_components['effect_variance'] = 'no_effect'
    else:
        chosen, effect = select_endpoint_effect(stated)
        quantities['effect'] = {key: value for key, value in effect.items() if key != 'support'}
        quantity_kind, effect_support = chosen, effect['support']
        variance, variance_reason, variance_refs = _variance(graded, chosen, ref)
        if variance is None:
            null_components['effect_variance'] = variance_reason
        else:
            quantities['effect_variance'] = _operand(variance, ANCHOR_UNIT[chosen] + '_squared', 'endpoint_enzymatic_assay_' + chosen + '_variance:' + ref, variance_refs, 'derived', QUANTITY_OF_KIND[chosen] + '_spread')
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
    result = {'version': VERSION, 'experiment_type': 'endpoint_enzymatic_assay', 'experiment_ref': ref, 'source_ref': native['source_ref'], 'dependence': dict(native['preparations']), 'extraction': extraction,
              'sheet': grade_assay(extraction), 'null_components': null_components, 'direction_field_support': effect_support}
    if quantities['effect'] is None:      # no usable quantity: the paper's own yes/no statement of conversion above its control stands (scored like any stated result, literature_direction's qualitative path)
        result['qualitative_effect'] = {'statement': STATEMENTS[native['conversion']], 'support_refs': list(native['conversion_refs'])}
        if native['conversion'] is not None:
            result['direction_field_support'] = native['conversion_support']      # the support class of the fact conversion_detected_above_control, the one field the statement is derived from
    return result
